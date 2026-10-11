"""The `Backend` protocol of the SDK API (`api/operations.md`, `sdk-api/1`) and `LocalBackend`, its local implementation.

Implemented here: the library family (`list_resources(kind)` and `get_resource(kind, name)` for the kinds `sensor`,
`scenario`, `engine_profile` and `recipe`, which the facade exposes as `list_sensors`, `get_sensor` and so on, through
`library.LibraryReader`), `compose`, `validate` (levels `none` and `dry_run`), `submit_run`, `submit_sweep`, `get_run`,
`get_sweep`, `cancel_run`, `list_artifacts`, `get_artifact`. A `target` or `recipe` is a library recipe name (a string
with no path separator and no `.yaml` suffix), a file path, or a parsed document (a dict); a recipe has a top-level
`compose` key, a run spec a `spec_version` of `run-spec/1`. A recipe document composes against the backend's library
(`compose.compose_sweep_document`); its `recipe` member in a response has name null and the sha256 of its canonical
JSON.

Every return value is the wire form: a plain dict that validates against the matching schema in `api/schemas/`
(`library_list`, `library_document`, `compose_response`, `validate_response`, `run_status`, `sweep_status`,
`artifact_list`), or for `get_artifact` the
tuple `(bytes, media_type)`. Errors are `errors.ProblemError` subclasses carrying a problem details dict: a recipe that
does not compose or a request the SDK cannot act on is an `InvalidRequestError` or `AdmissionError`, a failed
admission an `AdmissionError` naming the layer file and field, an unknown id a `NotFoundError`. A REST server is then a
thin shell over these calls.

`LocalBackend` keeps every run in a `store.RunStore` under `work_root` (the store is the state: two instances on one
work root see the same runs). Admission is the engine-free level (`admission.validate_spec`) and runs before a run
exists; a sweep is admitted as a whole. A new run gets a worker process (`python -m manifold.sim.worker <run_dir>`, its
own session and process group) that waits for one of `max_parallel` slots, then dry-runs and renders it; the call
returns at once, in state `accepted`. Resubmitting the same run spec returns the existing run and starts nothing.
`cancel_run` moves an active run to `cancelled` first, then terminates the worker's process group. No engine package is
imported at module level; `validate(engine_check="dry_run")` imports `simulation` when called.

In `validate`, the `content_hash` check lists the unstamped members as problems while `passed` stays true: a
placeholder is the authoring state, which validation reports and submission refuses.

POSIX only (`fcntl`, process groups).
"""
import hashlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Protocol, runtime_checkable

import yaml

from manifold.core import identity, problems
from manifold.core import _names
from manifold.core.admission import validate_spec
from manifold.core.compose import MAX_RUNS, ComposeError, compose_sweep, compose_sweep_document
from manifold.core.compose import default_sensor_library as recipe_sensor_library
from manifold.core.contract import schema_violations, semantic_errors
from manifold.core import resources
from manifold.core.engine import engine_id_of
from manifold.core.errors import AdmissionError, InvalidRequestError, NotFoundError
from manifold.sim import engines
from manifold.sim.library import LibraryReader
from manifold.core.run_spec import RunSpecError, default_sensor_library, load_run_spec
from manifold.sim.store import ACTIVE, FINAL, RunStore, process_start, utc_now

TERMINATE_WAIT_S = 10


@runtime_checkable
class Backend(Protocol):
    """The operations of `sdk-api/1`; each returns the wire form (see the module)."""

    def list_resources(self, kind) -> dict: ...

    def get_resource(self, kind, name) -> dict: ...

    def compose(self, recipe, inline_sensor=False, max_runs=MAX_RUNS) -> dict: ...

    def validate(self, target, engine_check="none") -> dict: ...

    def submit_run(self, target) -> dict: ...

    def submit_sweep(self, recipe) -> dict: ...

    def get_run(self, run_id) -> dict: ...

    def get_sweep(self, sweep_id) -> dict: ...

    def cancel_run(self, run_id) -> dict: ...

    def list_artifacts(self, run_id) -> dict: ...

    def get_artifact(self, run_id, name) -> tuple: ...

    def list_engines(self) -> dict: ...


def local_capacity():
    """What this host offers a `LocalBackend` (proposed): its CPU threads, its physical memory, no GPU (GPU slots are
    parsed and checked, and advertised as zero here), no scratch limit, no network access for runs."""
    try:
        memory = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        memory = None
    return resources.Capacity(cpu_threads=os.cpu_count() or 1, memory_bytes=memory, gpus=(), scratch_bytes=None,
                              network=False)


def engine_entry(status, adapter=None):
    """One `engine_list` item (proposed) from a registry `EngineStatus` and, when it loaded, its adapter."""
    info = status.info
    declared, assets = None, []
    if adapter is not None:
        try:
            decl = adapter.resources()
            declared = resources.as_dict(decl) if decl is not None else None
            assets = [resources.as_dict(a) for a in (decl.assets if decl is not None else ())]
        except Exception:  # noqa: BLE001 -- a listing never fails on one engine
            declared, assets = None, []
    return {"engine_id": status.engine_id, "available": status.available,
            "adapter_version": info.adapter_version if info else None,
            "modes": list(info.modes) if info else [], "contracts": list(info.contracts) if info else [],
            "reason": status.reason, "source": status.source, "resources": declared, "assets": assets}


def _sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class _Run:
    """One run to validate or submit: its spec, name, sensor library and, when composed here, provenance."""

    def __init__(self, name, spec, library, sources=None, recipe=None, path=None):
        self.name, self.spec, self.library, self.sources, self.recipe, self.path = name, spec, library, sources, recipe, path


class LocalBackend:
    """The local `Backend`: runs in a store under `work_root`, assets from `config_repo` (read only), one worker
    process per run, at most `max_parallel` rendering at once. `sensor_library` overrides the sensor library a recipe
    or run spec would use by default (the sibling `manifold_sensors/`). `library` is the layer root the library
    family reads (default: the repository's `manifold_run_specs/`)."""

    def __init__(self, work_root, config_repo, *, max_parallel=1, sensor_library=None, library=None, engine=None,
                 registry=None, capacity=None):
        if int(max_parallel) < 1:
            raise ValueError("max_parallel must be at least 1")
        self.store = RunStore(work_root)
        self.config_repo = Path(config_repo).resolve()           # absolute: the job's scene links are made from it
        self.max_parallel = int(max_parallel)
        self.sensor_library = Path(sensor_library).resolve() if sensor_library is not None else None
        self._children = []
        self.library = LibraryReader(library, self.sensor_library)
        self.engine = str(Path(engine).resolve()) if engine is not None else None   # an engine executable override
        self.registry = registry if registry is not None else engines.registry()
        self.capacity = capacity if capacity is not None else local_capacity()

    # --- inputs -------------------------------------------------------------------------------------------------

    @staticmethod
    def _load(path):
        path = Path(path)
        try:
            doc = yaml.safe_load(path.read_text())
        except (OSError, yaml.YAMLError) as e:
            raise InvalidRequestError(f"{path} could not be read as YAML: {e}") from e
        if not isinstance(doc, dict):
            raise InvalidRequestError(f"{path} is not a recipe or a run spec (not a mapping)")
        return doc

    def _input(self, target):
        """`(document, path)` for a target: a library recipe name (no path separator, no `.yaml`), a file path, or a
        document (a dict, path None). An unknown recipe name raises NotFoundError."""
        if isinstance(target, dict):
            return target, None
        if isinstance(target, str) and "/" not in target and "\\" not in target and not target.endswith(".yaml") \
                and not Path(target).exists():
            path = self.library.path("recipe", target)
        else:
            path = Path(target).resolve()
        return self._load(path), path

    @staticmethod
    def _recipe_ref(document, path):
        """The `recipe` member of a compose_response or sweep_status: a file by stem and the digest of its bytes; a
        document with name null and the digest of its canonical JSON."""
        if path is None:
            return {"name": None, "sha256": identity.sha256_hex(identity.canonical_json(document))}
        return {"name": path.stem, "sha256": _sha256_file(path)}

    def _compose(self, recipe, inline_sensor=False, max_runs=MAX_RUNS, error=InvalidRequestError):
        """`(sweep, sensor library, recipe ref, recipe for problems)` for a recipe name, path or document."""
        document, path = self._input(recipe)
        try:
            if path is None:
                library = self.sensor_library or self.library.sensor_library
                sweep = compose_sweep_document(document, self.library.root, inline_sensor=inline_sensor,
                                               sensor_library=library, max_runs=max_runs, registry=self.registry)
            else:
                library = self.sensor_library or recipe_sensor_library(path)
                sweep = compose_sweep(path, inline_sensor=inline_sensor, sensor_library=library, max_runs=max_runs,
                                      registry=self.registry)
        except ComposeError as e:
            raise error(problems.from_compose_error(e)) from e
        return sweep, library, self._recipe_ref(document, path), (document if path is None else path)

    def _runs(self, target, error=InvalidRequestError):
        """`(runs, sweep, recipe ref)`: the runs of a recipe (composed here) or the one run spec a target names."""
        document, path = self._input(target)
        if "compose" in document:
            sweep, library, ref, recipe = self._compose(target, error=error)
            return [_Run(n, s, library, sweep.sources[n], recipe) for n, s in sweep.runs.items()], sweep, ref
        if document.get("spec_version") == "run-spec/1":
            if path is not None:
                try:
                    spec = load_run_spec(path)
                except RunSpecError as e:
                    raise InvalidRequestError(f"{path}: {e}") from e
                library = self.sensor_library or default_sensor_library(path)
            else:
                spec, library = document, self.sensor_library or self.library.sensor_library
            name = ((spec.get("descriptor") or {}).get("meta") or {}).get("name") or (path.stem if path else None)
            return [_Run(name, spec, library, path=path)], None, None
        where = path or "the document"
        raise InvalidRequestError(f"{where} is neither a recipe (compose: compose/1) nor a run spec (spec_version: "
                                  "run-spec/1)")

    def _report(self, run):
        return validate_spec(run.spec, run.path, self.config_repo, run.library, registry=self.registry)

    # --- the library ---------------------------------------------------------------------------------------------

    def list_resources(self, kind):
        """The `library_list` of one kind: `{"items": [{name, sha256}, ...]}`, sorted by name."""
        return {"items": self.library.list(kind)}

    def get_resource(self, kind, name):
        """The `library_document` (for a sensor, `sensor_document`) of one resource: `{name, sha256, document}`.
        NotFoundError for an unknown name; AdmissionError naming the file for one that does not parse or is not of
        its kind."""
        return self.library.get(kind, name)

    # --- compose and validate -----------------------------------------------------------------------------------

    def compose(self, recipe, inline_sensor=False, max_runs=MAX_RUNS):
        """The `compose_response` for a recipe (library name, file path or document); a recipe that does not compose
        raises InvalidRequestError with
        the compose problem (layer and field)."""
        sweep, _, ref, _ = self._compose(recipe, inline_sensor, max_runs)
        return {"sweep_id": sweep.sweep_id, "recipe": ref,
                "is_sweep": sweep.is_sweep,
                "runs": [{"run_id": sweep.run_ids[n], "name": n, "sensor": sweep.sensors[n], "run_spec": s,
                          "provenance": sweep.sources[n]} for n, s in sweep.runs.items()]}

    def _checks(self, run, report):
        """The `checks` of a validate_response run, as problem details located by layer file and field."""
        spec, src, recipe = run.spec, run.sources, run.recipe
        schema = []
        violations = schema_violations(spec, self.registry) if isinstance(spec, dict) else [{"path": "", "message": "not a mapping",
                                                                                "at": ""}]
        if violations:
            schema.append(problems.from_schema_violations(spec if isinstance(spec, dict) else {}, src, violations,
                                                          recipe=recipe))
        schema += [problems.admission(m) for m in (semantic_errors(spec, self.registry) if isinstance(spec, dict) else [])]
        checks = [{"check": "schema", "passed": not schema, "errors": schema}]
        exc = report.resolve_exception
        pointer = getattr(exc, "pointer", None) or ""
        unstamped = [problems.admission(f"{p} carries a placeholder; submission refuses it until "
                                        "scripts/stamp_hashes.py stamps it",
                                        *problems.locate(p if p.endswith("/revision") else p + "/content_hash", src,
                                                         spec=spec, recipe=recipe) if src else (None, None))
                     for p in report.unstamped]
        if exc is None:
            checks.append({"check": "resolution", "passed": True, "errors": []})
            checks.append({"check": "content_hash", "passed": True, "errors": unstamped})
            library = [problems.from_library_problem(m, spec, src, recipe) for m in report.resolution_mismatches]
            checks.append({"check": "library_files", "passed": not library, "errors": library})
        elif pointer.endswith("/content_hash"):
            checks.append({"check": "resolution", "passed": True, "errors": []})
            checks.append({"check": "content_hash", "passed": False,
                           "errors": [problems.from_resolution_error(exc, spec, src, recipe)] + unstamped})
        else:
            checks.append({"check": "resolution", "passed": False,
                           "errors": [problems.from_resolution_error(exc, spec, src, recipe)]})
        return checks

    def validate(self, target, engine_check="none"):
        """The `validate_response` for a run spec or recipe file. `none`: the engine-free checks only, no engine
        process. `dry_run`: also a DIRSIG dry run in a scratch directory under the work root; without a DIRSIG
        installation the run is reported not engine-checked and not valid at that level, with the reason."""
        if engine_check not in ("none", "dry_run"):
            raise InvalidRequestError(f"engine_check is {engine_check!r}; expected 'none' or 'dry_run'")
        runs, _, _ = self._runs(target)
        out = []
        for run in runs:
            report = self._report(run)
            checks = self._checks(run, report)
            valid, engine_checked = report.valid, False
            if engine_check == "dry_run":
                ok, engine_checked, errors = self._dry_run(run, report)
                checks.append({"check": "dry_run", "passed": ok, "errors": errors})
                valid = valid and ok
            out.append({"name": run.name, "run_id": report.run_id, "valid": valid, "engine_checked": engine_checked,
                        "checks": checks})
        return {"engine_check": engine_check, "runs": out}

    def _engine(self):
        """The engine executable passed to the adapter: the `engine` given, else `auto` (the adapter locates its own
        engine); None means none is available."""
        return self.engine or "auto"

    def _dry_run(self, run, report):
        """(passed, engine_checked, problems) of the engine's own dry run of one run spec, through its adapter, in a
        scratch directory under the work root."""
        if not report.valid:
            return False, False, [problems.admission("not attempted: the engine-free checks did not pass")]
        adapter = self.registry.find(engine_id_of(run.spec))
        if adapter is None or not hasattr(adapter, "dry_run"):
            return False, False, [problems.admission("not performed: the engine offers no dry run")]
        ok, checked, messages = adapter.dry_run(run.spec, report.run, self.store.root / "validate",
                                                {"engine": self._engine(), "config_repo": self.config_repo,
                                                 "sensor_library": run.library})
        return ok, checked, [problems.admission(m) for m in messages]

    # --- engines ------------------------------------------------------------------------------------------------

    def list_engines(self):
        """The `engine_list` document (proposed): every engine registered in this environment, available or not."""
        return {"items": [engine_entry(st, self.registry.find(st.engine_id))
                          for st in self.registry.listing()]}

    def engines(self):
        """The engines (alias of `list_engines`)."""
        return self.list_engines()

    # --- submission ---------------------------------------------------------------------------------------------

    def _job(self, run):
        return {"config_repo": str(self.config_repo), "sensor_library": str(Path(run.library).resolve()),
                "max_parallel": self.max_parallel, "engine": self._engine(), "capacity": resources.as_dict(self.capacity),
                "resources": run.spec.get("resources")}         # every request; the stored run spec keeps the id slots

    def _start_worker(self, run_id):
        run_dir = self.store.run_dir(run_id)
        with open(run_dir / "worker.log", "ab") as log:
            proc = subprocess.Popen([sys.executable, "-m", _names.WORKER_MODULE, str(run_dir)], cwd=run_dir,
                                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=True, close_fds=True)
        self._children.append(proc)
        start = process_start(proc.pid) or {}                  # pid and start time: the worker's identity for reap
        self.store.update_record(run_id, {"worker": {"pid": proc.pid, "pgid": proc.pid, **start}})
        return proc

    def _poll_children(self):
        """Collect exited worker processes this backend started (so none lingers as a zombie)."""
        self._children = [p for p in self._children if p.poll() is None]

    def _execution_problem(self, run, instance=None):
        """An admission problem when this backend cannot execute the run although it is valid: its engine is
        registered but unavailable here (the adapter's `availability`), or it requests resources this backend does
        not advertise (`resources.check` against `self.capacity`: a GPU here, where there is none). None otherwise."""
        engine_id = engine_id_of(run.spec)
        if engine_id is None or engine_id not in self.registry.ids():
            return None
        status = self.registry.status(engine_id)
        if not status.available:
            return problems.admission(f"engine {engine_id!r} is unavailable on this backend: {status.reason}", instance)
        adapter = self.registry.get(engine_id)
        try:
            request = resources.parse_request(run.spec.get("resources"))
        except ValueError as e:
            return problems.admission(str(e), instance)
        declared = adapter.resources(run.spec) or resources.ResourceDeclaration()
        found = resources.check(request, declared, self.capacity)
        return problems.admission("; ".join(found), instance) if found else None

    def _create(self, run):
        resolved = identity.resolved_run_spec(run.spec, run.library)
        run_id, created = self.store.create_run(resolved, run.name, self._job(run))
        if created:
            self._start_worker(run_id)
        return run_id, created

    def submit_run(self, target):
        """Admit and start one run (a run spec file or a one-run recipe); returns its `run_status`: `accepted` for a
        new run, the current status for one already submitted (no second worker). A failed admission, including an
        unstamped member, raises AdmissionError naming the layer file and field; nothing is created."""
        runs, sweep, _ = self._runs(target, error=AdmissionError)
        if len(runs) != 1:
            raise InvalidRequestError(f"the recipe composes to {len(runs)} runs (it names several sensors); "
                                      "submit it with submit_sweep", "/runs")
        run = runs[0]
        report = self._report(run)
        problem = problems.from_validation(report, run.sources, run.recipe, "/runs") or self._execution_problem(run,
                                                                                                                "/runs")
        if problem is not None:
            raise AdmissionError(problem)
        run_id, _ = self._create(run)
        if run_id != report.run_id:
            raise RuntimeError(f"the stored run id {run_id} differs from the admitted spec's {report.run_id}")
        return self.store.read_status(run_id)

    def submit_sweep(self, recipe):
        """Admit every run of a sweep recipe as a whole, then create and start them; returns the `sweep_status`. If any
        run fails admission, one AdmissionError lists every failing run in `errors` and nothing is created."""
        runs, sweep, ref = self._runs(recipe, error=AdmissionError)
        if sweep is None:
            raise InvalidRequestError("a run spec, not a recipe; submit it with submit_run", "/sweeps")
        failing = []
        for run in runs:
            p = problems.from_validation(self._report(run), run.sources, run.recipe) or self._execution_problem(run)
            if p is not None:
                failing.append({"run": run.name, "detail": p["detail"], "layer": p["layer"], "field": p["field"]})
        if failing:
            first = failing[0]
            raise AdmissionError({"type": problems.ADMISSION, "title": problems.TITLES[problems.ADMISSION],
                                  "status": 422, "instance": "/sweeps",
                                  "detail": f"{len(failing)} of {len(runs)} runs of the sweep failed admission, so none "
                                            f"was created: {', '.join(f['run'] for f in failing)}",
                                  "layer": first["layer"], "field": first["field"], "errors": failing})
        ids = [self._create(run)[0] for run in runs]
        self.store.create_sweep(sweep.sweep_id, {"recipe": ref,
                                                 "run_ids": ids})
        return self.get_sweep(sweep.sweep_id)

    # --- reads and cancel ---------------------------------------------------------------------------------------

    def get_run(self, run_id):
        self._poll_children()
        return self.store.read_status(run_id)

    def get_sweep(self, sweep_id):
        self._poll_children()
        record = self.store.read_sweep(sweep_id)
        return {"sweep_id": record["sweep_id"], "recipe": record["recipe"],
                "runs": [self.store.read_status(r) for r in record["run_ids"]]}

    def list_artifacts(self, run_id):
        self._poll_children()
        return {"run_id": run_id, "artifacts": self.store.artifacts(run_id)}

    def get_artifact(self, run_id, name):
        """`(bytes, media_type)` of a named artifact; NotFoundError for an unknown run or name."""
        for ref in self.list_artifacts(run_id)["artifacts"]:
            if ref["name"] == name:
                data = Path(ref["uri"].removeprefix("file://")).read_bytes()
                return data, ref["media_type"]
        raise NotFoundError("artifact", f"{run_id}/{name}")

    def cancel_run(self, run_id):
        """Cancel an `accepted` or `running` run: the state becomes `cancelled` first (a worker then never overwrites
        it), then the worker's process group gets SIGTERM, and SIGKILL after 10 s. A final run is returned unchanged."""
        self._poll_children()
        status = self.store.read_status(run_id)
        if status["state"] in FINAL:
            return status
        updated, status = self.store.update_status(run_id, ACTIVE, {"state": "cancelled"})
        if not updated:
            return status
        pgid = (self.store.read_record(run_id).get("worker") or {}).get("pgid")
        if pgid and pgid != os.getpgid(0):
            self._terminate(pgid)
        self.store.update_record(run_id, {"finished_at": utc_now(), "cancelled_at": utc_now()})
        return self.store.read_status(run_id, reap=False)

    def _terminate(self, pgid):
        def alive():
            self._poll_children()
            try:
                os.killpg(pgid, 0)
                return True
            except ProcessLookupError:
                return False
            except PermissionError:
                return True
        for sig, wait in ((signal.SIGTERM, TERMINATE_WAIT_S), (signal.SIGKILL, TERMINATE_WAIT_S)):
            try:
                os.killpg(pgid, sig)
            except ProcessLookupError:
                return
            deadline = time.monotonic() + wait
            while time.monotonic() < deadline:
                if not alive():
                    return
                time.sleep(0.1)
