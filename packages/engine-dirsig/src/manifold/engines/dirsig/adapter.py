"""The DIRSIG engine adapter (`manifold.core.engine.EngineAdapter`): `dirsig-engine/1` engine blocks, layered and
pass-through modes.

Identity: engine id `dirsig`, contract `dirsig-engine/1`, modes `layered` and `passthrough`. Schema: the engine block is
validated against `dirsig-engine-1.schema.json`. Composition rule: a non-zero `black_level` is refused (DIRSIG applies it
as a channel bias). Semantic rules: integer members read from YAML as floats. Resolution: `run_spec.resolve_run` for a
layered block, `resolve_passthrough` for `mode: passthrough`; the library-file check renders the platform template
(`run_spec.check_library_files`).

Execution: `plan` launches `python -m <this package>.runner <run_dir>` in the SDK's own interpreter; the runner calls
`execute`, which builds the job with dirfm and runs the DIRSIG dry run and the render (layered), or runs `scene2hdf` and
`dirsig5` on a copy of the demo directory with a per-run `HOME` (pass-through), and writes `engine_result.json`.
`collect` reads it: no result file means the process stopped before it finished (`incomplete`); a failed outcome is
`failed`; a rendered one lists the artifacts (layered: each capture's image, header and truth products from the
engine's `log_info.json`, with `frame`, after the run-level logs; pass-through: every file the engine wrote, by name).
`fingerprint` gives the `dirfm` revision in use against the spec's `engine.generator.revision`, and the DIRSIG
installation and version, the execution record's `dirfm` and `dirsig` members. `dry_run` runs DIRSIG's own dry run in a
scratch directory. Importing this module loads no engine package (dirfm loads only when a job is built).
"""
import importlib.util
import json
import os
import shutil
import subprocess
import traceback
import uuid
from pathlib import Path

from manifold.core.contract import contracts_dir
from manifold.engines.dirsig.artifacts import RUN_LEVEL, _frames, _header
from manifold.core.engine import (CollectedArtifact, Collection, EngineInfo, EnvironmentPolicy, LaunchPlan, Registry,
                                  ResolveContext, default_registry)
from manifold.engines.dirsig.passthrough_spec import is_passthrough, resolve_passthrough
from manifold.engines.dirsig.run_spec import black_level_problem, check_library_files, resolve_run

REPOSITORY = Path(__file__).resolve().parents[6]    # packages/engine-dirsig/src/manifold/engines/dirsig/
RESULT = "engine_result.json"                     # written by `execute` into the run directory
ENGINE_ID = "dirsig"
CONTRACT = "dirsig-engine/1"
SCHEMA_FILE = "dirsig-engine-1.schema.json"
# Required engine members and enumerations as dirsig-engine-1.schema.json states them (Configuration_v02 A.8.1-A.8.7);
# kept for callers and tests. `new_atmosphere` is the documented, non-adopted extension (CONOPS and Guide §10).
ENGINE_REQUIRED = ("generator", "scenes", "platform", "motion", "tasks", "atmosphere")
ENGINE_ENUMS = {
    ("generator", "tool"): {"dirfm"},
    ("generator", "spec_schema"): {CONTRACT},
    ("motion", "kind"): {"static", "waypoints", "orbit"},
    ("motion", "orientation", "kind"): {"euler", "lookat"},
    ("motion", "orbit", "propagator"): {"skyfield_sgp4"},           # the orbit form (proposed, CONOPS §3.2)
    ("motion", "orientation", "lookat", "frame"): {"sceneenu"},
    ("motion", "orientation", "lookat", "up"): {"along_track"},
    ("atmosphere", "plugin"): {"four_curve", "basic", "new_atmosphere"},
    ("weather", "source"): {"library", "install"},
    ("ephemeris", "plugin"): {"spice"},
}


def registry():
    """A registry that serves this engine: the default one when it already does (a process that imported
    `manifold.sim`), else a registry holding only this adapter. The engine's own modules (the runner, `Simulation`,
    `LocalRegistry`) validate and compose through it, so they work in a process that never imported `manifold.sim`."""
    reg = default_registry()
    if ENGINE_ID in reg.ids():
        return reg
    own = Registry()
    own.register(ENGINE_ID, DirsigAdapter, source=__name__)
    return own


def schema_path():
    """`dirsig-engine-1.schema.json`: the copy packaged with this distribution (`_contracts/`, written by the build), else
    the contract folder `manifold.core.contract.contracts_dir` names (a checkout or an editable install)."""
    packaged = Path(__file__).resolve().parent / "_contracts" / SCHEMA_FILE
    return packaged if packaged.is_file() else contracts_dir() / SCHEMA_FILE


def _version():
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version("eoptic-manifold-engine-dirsig")
    except PackageNotFoundError:
        return "0+unknown"


def _get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


class DirsigAdapter:
    """The DIRSIG adapter. Stateless; one instance serves every run."""

    def info(self):
        return EngineInfo(ENGINE_ID, _version(), (CONTRACT,), ("layered", "passthrough"),
                          "DIRSIG 5 through dirfm (layered) or a library demo directory run as authored (pass-through)")

    def engine_schema(self, engine_block):
        return json.loads(schema_path().read_text())

    def availability(self):
        """None when the engine can run here, else why not: `dirfm` must be importable (checked without importing it)."""
        try:
            if importlib.util.find_spec("dirfm") is None:
                return "dirfm is not installed (pip install -e <dirsig-file-maker checkout>)"
        except (ImportError, ValueError) as e:
            return f"dirfm cannot be imported: {e}"
        return None

    def compose_problems(self, settings):
        """(field, message) for each recipe settings member the engine cannot apply."""
        out = []
        for i, m in enumerate(settings or []):
            problem = black_level_problem(m)
            if problem:
                out.append((f"settings[{i}].black_level", problem))
        return out

    def semantic_rules(self, spec):
        """Integer members read from YAML as floats: JSON Schema's `integer` accepts 42.0, the generator needs an
        integer (`engine.run.seed`, `engine.platform.integration_samples`)."""
        eng = spec.get("engine") if isinstance(spec, dict) else None
        errs = []
        if isinstance(eng, dict):
            seed = _get(eng, ("run", "seed"))
            if isinstance(seed, float):
                errs.append(f"engine.run.seed is {seed!r}, expected an integer")
            samples = _get(eng, ("platform", "integration_samples"))
            if isinstance(samples, float):
                errs.append(f"engine.platform.integration_samples is {samples!r}, expected an integer >= 1")
        return errs

    def resolve(self, descriptor, engine_block, context: ResolveContext):
        spec = {"spec_version": "run-spec/1", "descriptor": descriptor, "engine": engine_block}
        if is_passthrough(spec):
            return resolve_passthrough(spec, context.config_repo)
        return resolve_run(spec, context.run_spec_path, context.config_repo, context.sensor_library)

    def library_problems(self, spec, resolved):
        if is_passthrough(spec):
            return []                                       # no library files beyond the directory: nothing to render
        return check_library_files(spec, resolved)

    # --- execution ----------------------------------------------------------------------------------------------

    def plan(self, context):
        return LaunchPlan(argv=(str(Path(context.run_dir)),), cwd=str(context.run_dir),
                          python_module=__name__.rsplit(".", 1)[0] + ".runner", env=EnvironmentPolicy(),
                          expected_outputs=())

    def execute(self, context, hook=None):
        """Run one run to an outcome, write `engine_result.json` and return it. `hook`, for tests, replaces the
        Simulation factory `(run_spec_path, config_repo, work_dir, sensor_library) -> Simulation`."""
        run_dir = Path(context.run_dir)
        try:
            if is_passthrough(context.spec):
                result = _execute_passthrough(context)
            else:
                result = _execute_layered(context, hook or _simulation)
        except Exception as e:  # noqa: BLE001 -- any failure of an accepted run is an execution failure
            _log(run_dir, traceback.format_exc().rstrip())
            result = {"outcome": "failed", "message": f"{type(e).__name__}: {e}", "record": {}}
        _write_json(run_dir / RESULT, result)
        return result

    def collect(self, output_dir, run_dir):
        run_dir = Path(run_dir)
        path = run_dir / RESULT
        if not path.is_file():
            return Collection((), "incomplete", "the engine process stopped before it finished (no engine_result.json)")
        result = json.loads(path.read_text())
        if result.get("outcome") != "rendered":
            logs = tuple(CollectedArtifact(Path(output_dir) / n, "log") for n in RUN_LEVEL if (Path(output_dir) / n).is_file())
            return Collection(logs, "failed", result.get("message") or "the engine run failed", result.get("record", {}))
        out = Path(output_dir)
        if result.get("mode") == "passthrough":
            files = sorted(p for p in out.rglob("*") if p.is_file()) if out.is_dir() else []
            arts = tuple(CollectedArtifact(p, "product", None, p.relative_to(out).as_posix().replace("/", "_"))
                         for p in files)
        else:
            arts = [CollectedArtifact(out / n, "log") for n in RUN_LEVEL if (out / n).is_file()]
            for frame, image, truth in _frames(run_dir):
                for p, role in [(image, "product"), (_header(image), "metadata")] + \
                        [x for t in truth for x in ((t, "truth"), (_header(t), "metadata"))]:
                    if p is not None:
                        if not p.is_file():
                            return Collection((), "failed", f"artifact references could not be built: capture "
                                              f"{frame}: {p.name} is named by the engine log but was not written",
                                              result.get("record", {}))
                        arts.append(CollectedArtifact(p, role, frame))
            arts = tuple(arts)
        return Collection(arts, "complete", None, result.get("record", {}))

    def fingerprint(self, spec=None):
        dirfm = dirfm_revision()
        spec_revision = None
        try:
            spec_revision = spec["engine"]["generator"]["revision"]
        except (KeyError, TypeError):
            pass
        return {"dirfm": {**dirfm, "generator_revision": spec_revision,
                          "generator_revision_matches": dirfm["revision"] == spec_revision},
                "dirsig": locate_dirsig()}

    def resources(self, spec=None):
        return None

    def dry_run(self, spec, resolved, scratch_root, options=None):
        """(passed, engine_checked, messages) of DIRSIG's own dry run of one run spec, in a scratch directory under
        `scratch_root`. `options["engine"]`: the engine executable for a pass-through run (`auto` locates it)."""
        engine = _engine_path((options or {}).get("engine", "auto"))
        scratch = Path(scratch_root) / uuid.uuid4().hex
        if is_passthrough(spec):
            if engine is None:
                return False, False, ["not performed: no DIRSIG installation was found"]
            from manifold.engines.dirsig.passthrough import run_engine
            try:
                result = run_engine(resolved, scratch, engine, dry_run=True, log=None)
                ok = result["returncode"] == 0
                return ok, True, [] if ok else [f"DIRSIG did not accept the pass-through simulation in a dry run "
                                                f"(--dry_run): exit status {result['returncode']}"]
            finally:
                shutil.rmtree(scratch, ignore_errors=True)
        if locate_dirsig()["home"] is None:
            return False, False, ["not performed: no DIRSIG installation was found (dirsig5 on PATH, $DIRSIG_HOME or "
                                  "~/DIRSIG/<pinned version>)"]
        from manifold.core.compose import dump
        from manifold.engines.dirsig.simulation import Simulation
        scratch.mkdir(parents=True)
        try:
            path = scratch / "run_spec.yaml"
            path.write_text(dump(spec, (spec.get("descriptor") or {}).get("meta", {}).get("name", "run")))
            c = Simulation.from_run_spec(path, (options or {}).get("config_repo"), scratch,
                                         (options or {}).get("sensor_library")).validate("dry_run")
            return c.execution_ok, c.engine_checked, [] if c.execution_ok else [
                f"DIRSIG did not accept the job in a dry run: {c.execution_error}"]
        finally:
            shutil.rmtree(scratch, ignore_errors=True)


# --- helpers ---------------------------------------------------------------------------------------------------------

def _log(run_dir, message):
    from datetime import datetime, timezone
    with open(Path(run_dir) / "worker.log", "a") as f:
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {message}\n")


def _write_json(path, doc):
    tmp = Path(path).with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2, sort_keys=True, default=str))
    os.replace(tmp, path)


def _pins():
    try:
        return json.loads((REPOSITORY / "external" / "pins.json").read_text())
    except (OSError, ValueError):
        return {}


def locate_dirsig():
    """Put a DIRSIG installation on PATH if `dirsig5` is not already there: `$DIRSIG_HOME`, else `~/DIRSIG/<pinned
    version>` (external/pins.json). Returns `{"home", "version", "source"}` (home None if none was found)."""
    pin = _pins().get("dirsig", {})
    found = shutil.which("dirsig5")
    if found:
        home = Path(found).resolve().parent.parent
    else:
        home = None
        for cand in [os.environ.get("DIRSIG_HOME", "")] + ([str(Path.home() / "DIRSIG" / pin["version"])]
                                                            if pin.get("version") else []):
            if cand and (Path(cand) / "bin" / "dirsig5").is_file():
                home = Path(cand)
                os.environ["PATH"] = f"{home / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}"
                break
    if home is not None:
        os.environ.setdefault("DIRSIG_HOME", str(home))
    ver = None
    if home is not None:
        try:
            out = subprocess.run([str(home / "bin" / "dirsig5"), "--version"], capture_output=True, text=True,
                                 timeout=30)
            ver = (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr).strip() else None
        except (OSError, subprocess.TimeoutExpired):
            ver = None
    return {"home": str(home) if home else None, "version": ver, "install": home.name if home else None,
            "source": "dirsig5 --version" if ver else "not found"}


def dirfm_revision():
    """`{"revision", "source"}`: the git HEAD of the dirfm checkout in use, else the pin (and the record says so)."""
    try:
        import dirfm
        top = Path(dirfm.__file__).resolve().parent
        out = subprocess.run(["git", "-C", str(top), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
        if out.returncode == 0 and out.stdout.strip():
            return {"revision": out.stdout.strip(), "source": f"git -C {top} rev-parse HEAD"}
    except (ImportError, OSError, subprocess.TimeoutExpired):
        pass
    return {"revision": _pins().get("dirfm", {}).get("commit"), "source": "external/pins.json (no git checkout found)"}


def engine_version(engine):
    """The first line `<engine> --version` prints, or None."""
    try:
        out = subprocess.run([str(engine), "--version"], capture_output=True, text=True, timeout=60)
        text = (out.stdout or out.stderr).strip()
        return text.splitlines()[0] if text else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _engine_path(option):
    """The `dirsig5` to run: an explicit path, the located installation's for `auto`, or None (none available)."""
    if option and option != "auto":
        return str(option)
    if option == "auto":
        home = locate_dirsig()["home"]
        return str(Path(home) / "bin" / "dirsig5") if home else None
    return None


def _simulation(run_spec_path, config_repo, work_dir, sensor_library):
    from manifold.engines.dirsig.simulation import Simulation
    return Simulation.from_run_spec(run_spec_path, config_repo, work_dir, sensor_library)


def _execute_layered(context, factory):
    run_dir = Path(context.run_dir)
    locate_dirsig()                                                   # PATH and DIRSIG_HOME for dirfm's DIRSIG.run
    sim = factory(run_dir / "run_spec.yaml", Path(context.config_repo), run_dir,
                  Path(context.sensor_library) if context.sensor_library else None)
    check = sim.validate("dry_run")
    shutil.rmtree(run_dir / "validate", ignore_errors=True)          # the dry run's scratch job
    if not check.passed:
        why = check.execution_error or "; ".join(check.resolution_mismatches) or check.schema_error
        return {"outcome": "failed", "message": f"the DIRSIG dry run did not pass: {why}", "record": {}}
    result = sim.run(out_dir=Path(context.output_dir or run_dir / "output"))
    record = {"propagator": result.propagator} if getattr(result, "propagator", None) else {}
    return {"outcome": "rendered", "mode": "layered", "record": record}


def _execute_passthrough(context):
    from manifold.engines.dirsig.passthrough import cache_state, run_engine, throttle_suspect, tool_version
    run_dir = Path(context.run_dir)
    run = resolve_passthrough(context.spec, Path(context.config_repo))   # the digest is verified again here
    engine = _engine_path((context.options or {}).get("engine", "auto"))
    if not engine:
        return {"outcome": "failed", "message": "no DIRSIG installation was found for the pass-through run",
                "record": {}}
    scene2hdf = Path(engine).parent / "scene2hdf"
    record = {"mode": "passthrough", "engine": {"path": str(engine), "version": engine_version(engine)},
              "scene2hdf": {"path": str(scene2hdf), "version": tool_version(scene2hdf)} if scene2hdf.is_file() else None,
              "passthrough": {"directory": str(run.directory), "simulation": run.simulation_rel}}
    home = run_dir / "home"
    result = run_engine(run, run_dir, engine, log=run_dir / "worker.log", home=home)
    hot, freq = result.get("max_cpu_temp_c"), result.get("cpu_freq_khz")
    record.update({"cache": {"mode": "per-run home", "home": "home", **cache_state(home)},
                   "max_cpu_temp_c": hot, "cpu_freq_khz": freq, "throttle_suspect": throttle_suspect(hot, freq),
                   "scene_compile": [{"scene": s, "exit_status": c} for s, c in result["compiled"]]
                   if result.get("compiled") is not None else "no scene2hdf beside the engine",
                   "engine_exit_status": result["returncode"],
                   "engine_command": [Path(result["command"][0]).name, *result["command"][1:]],
                   "moved_from_input": result["moved"]})
    if result["returncode"] != 0:
        return {"outcome": "failed", "mode": "passthrough", "record": record,
                "message": f"the engine exited with status {result['returncode']} (see worker.log)"}
    return {"outcome": "rendered", "mode": "passthrough", "record": record}
