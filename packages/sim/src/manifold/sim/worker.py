"""The run worker: `python -m manifold.sim.worker <run_dir>`, one process per run, started by `LocalBackend`.

It loads `job.json`, records its pid and process group, waits for one of `max_parallel` slot locks
(`<work_root>/slots/slot-<i>.lock`, polled every second) while the run stays `accepted`, then moves the run from
`accepted` to `running` by compare-and-set (a run cancelled meanwhile is left alone and nothing runs). It finds the
adapter registered for the run's `descriptor.origin.engine` (`engines.registry()`), records the adapter and its
fingerprint, launches the adapter's `LaunchPlan` as a subprocess (its stdout and stderr appended to `worker.log`, in
the worker's process group, so cancelling the run stops it) and asks the adapter to `collect` what the process left:
a `complete` verdict gives the artifact references (`run_spec.json`, then the adapter's artifacts in its order, each
hashed once) in `artifacts.json` and moves the run to `rendered`; `incomplete` or `failed` moves it to `failed` with an
`execution` problem carrying the adapter's message. Each move is a compare-and-set from `running`, so a cancelled run
is never overwritten. The slot is always released, and the outcome is written to `worker.log`.

The execution record (`execution.json`) gains: `started_at`, `finished_at`, `worker` (`pid`, `pgid`, `start_ticks`,
`boot_time`), `python`, the `eoptic-manifold-sim` version (under the key `protodirsig_version`,
`_names.RECORD_VERSION_KEY`), `adapter` (`engine_id`, `version`, `source`), the adapter's fingerprint members (for
DIRSIG `dirfm` and `dirsig`), `resources` (the run's requests, the engine's declaration and the grant reserved in the
work root's resource ledger, released when the run ends), `assets` (each staged read-only under `<run_dir>/assets/`
after its digest is verified again) and `network` (a run whose engine could use the network but which may not runs
with its proxy variables pointed at a closed port; LocalBackend has no network sandbox), the members the adapter's collection adds (for a pass-through run the engine, its tools,
exit status, cache and thermal measurements), `artifact_roles` and `max_parallel`. It is never part of a run id.

Engine-free: the worker imports no engine package; the engine runs in the process the plan describes. `main(run_dir,
hook)` with a `hook` (tests) calls the adapter's private `_execute(context, hook)` in this process instead of launching
the plan.
"""
import fcntl
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from manifold.core import _names, problems, resources
from manifold.core.engine import EngineUnavailable, Registry, RunContext, engine_id_of
from manifold.core.errors import NotFoundError
from manifold.sim import engines
from manifold.sim.store import FINAL, ArtifactError, RunStore, artifact_ref, check_artifact_names, process_start, utc_now

POLL_S = 1.0
CONDA_ENV_DIRS = (Path(sys.prefix).parent, Path.home() / "anaconda3" / "envs", Path.home() / "miniconda3" / "envs")


def _log(run_dir, message):
    with open(Path(run_dir) / "worker.log", "a") as f:
        f.write(f"{utc_now()} {message}\n")


def _sdk_version():
    try:
        return version(_names.DISTRIBUTION)
    except PackageNotFoundError:
        return None


def _acquire_slot(store, run_id, max_parallel):
    """An exclusive slot lock (an open file), or None if the run left `accepted` while waiting."""
    while True:
        if store.read_status(run_id, reap=False)["state"] != "accepted":
            return None
        for i in range(max_parallel):
            f = open(store.slots / f"slot-{i}.lock", "a")
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return f
            except BlockingIOError:
                f.close()
        time.sleep(POLL_S)


def _fail(store, run_id, name, message, run_dir):
    problem = problems.execution_failed(run_id, name, message)
    updated, _ = store.update_status(run_id, ("running",), {"state": "failed", "errors": [problem]})
    _log(run_dir, f"failed: {message}" if updated else f"not recorded (state changed meanwhile): {message}")
    return updated


def python_for(interpreter):
    """The Python a plan names: the SDK's own (None), a path, or the `python` of a named conda environment."""
    if interpreter is None:
        return sys.executable
    if os.sep in str(interpreter):
        return str(Path(interpreter).expanduser())
    for base in CONDA_ENV_DIRS:
        cand = base / str(interpreter) / "bin" / "python"
        if cand.is_file():
            return str(cand)
    raise FileNotFoundError(f"no conda environment named {interpreter!r} under {[str(b) for b in CONDA_ENV_DIRS]}")


def command(plan):
    """The argv of a `LaunchPlan`."""
    if plan.python_module:
        return [python_for(plan.interpreter), "-m", plan.python_module, *plan.argv]
    if plan.interpreter is not None:
        return [python_for(plan.interpreter), *plan.argv]
    return [str(a) for a in plan.argv]


NO_NETWORK = {"HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9", "http_proxy": "http://127.0.0.1:9",
              "https_proxy": "http://127.0.0.1:9", "ALL_PROXY": "http://127.0.0.1:9", "NO_PROXY": "", "no_proxy": ""}


def stage(run_dir, name, source):
    """Make `source` visible read-only to the engine as `<run_dir>/assets/<name>`: a file is copied and made read-only,
    a directory linked (the library is read-only at run time). Returns the staged path."""
    import shutil
    dst = Path(run_dir) / "assets" / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        return dst
    source = Path(source)
    if source.is_dir():
        dst.symlink_to(source.resolve(), target_is_directory=True)
    else:
        shutil.copy2(source, dst)
        dst.chmod(0o444)
    return dst


def environment(plan, run_dir, threads=None, gpu_ids=(), extra=None):
    """The launched process's environment: the worker's, with the plan's policy applied (the granted thread count in
    its thread variables, the granted GPU ids in its GPU variable)."""
    env = dict(os.environ)
    for k in plan.env.unset:
        env.pop(k, None)
    env.update({k: str(v) for k, v in plan.env.set.items()})
    if plan.env.isolate_home:
        home = Path(run_dir) / "home"
        home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(home)
    if threads is not None:
        for var in plan.env.thread_variables:
            env[var] = str(threads)
    if plan.env.gpu_variable:
        env[plan.env.gpu_variable] = ",".join(gpu_ids)
    env.update(extra or {})
    return env


def launch(plan, run_dir, threads=None, gpu_ids=(), extra=None):
    """Run the plan to completion; its stdout and stderr go to `worker.log`. Returns the exit status."""
    run_dir = Path(run_dir)
    with open(run_dir / "worker.log", "ab") as log:
        proc = subprocess.Popen(command(plan), cwd=str(plan.cwd or run_dir),
                                env=environment(plan, run_dir, threads, gpu_ids, extra),
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        return proc.wait()


LEDGER, LEDGER_LOCK = "resources.json", "resources.lock"


class EngineSetMismatch(RuntimeError):
    """The worker cannot rebuild the engine set the backend admitted the run with."""


def engine_set(job):
    """The registry the backend used, rebuilt from `job.json`'s `engines` (each adapter loaded from its import target);
    `EngineSetMismatch` when an engine the backend loaded does not load here, or loads at another version, or the
    reverse. A `job.json` from before the engine set was recorded falls back to discovery."""
    described = job.get("engines")
    if described is None:
        return engines.registry()
    reg = Registry.from_description(described, engines.load_target)
    here = {d["engine_id"]: d for d in reg.describe()}
    for d in described:
        h = here[d["engine_id"]]
        if d.get("loaded") != h["loaded"] or (d.get("loaded") and d.get("adapter_version") != h["adapter_version"]):
            raise EngineSetMismatch(
                f"engine set mismatch: the backend had {d['engine_id']!r} ({d.get('target')}) "
                f"{'at version ' + str(d.get('adapter_version')) if d.get('loaded') else 'not loadable'}, the worker "
                f"{'at version ' + str(h['adapter_version']) if h['loaded'] else 'cannot load it'}")
    return reg


def capacity_of(doc):
    """A `resources.Capacity` from its JSON form in `job.json` (absent: this host's CPUs, no GPU)."""
    if not doc:
        return resources.Capacity(cpu_threads=os.cpu_count() or 1)
    return resources.Capacity(**{**doc, "gpus": tuple(resources.GpuDevice(**g) for g in doc.get("gpus") or ())})


def _ledger(store, update):
    """Apply `update(ledger)` to `<work_root>/slots/resources.json` under an exclusive lock; returns its result."""
    with open(store.slots / LEDGER_LOCK, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = store.slots / LEDGER
        ledger = json.loads(path.read_text()) if path.is_file() and path.read_text().strip() else {}
        result = update(ledger)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(ledger, sort_keys=True))
        os.replace(tmp, path)
        return result


def _finished(store, run_id):
    try:
        return store.read_status(run_id, reap=False)["state"] in FINAL
    except NotFoundError:
        return True


def acquire_resources(store, run_id, request, declared, capacity):
    """Reserve what the run requests (`resources.allocate`) against the runs holding reservations, polling while the
    run stays `running`; a reservation of a finished run is dropped. Returns the `Grant`, or None if the run left
    `running` (cancelled) while it waited."""
    def take(ledger):
        for rid in [r for r in ledger if r != run_id and _finished(store, r)]:
            del ledger[rid]
        in_use = [resources.Grant(g.get("cpu_threads"), g.get("memory_bytes", 0), tuple(g.get("gpu_ids", ())))
                  for rid, g in ledger.items() if rid != run_id]
        grant = resources.allocate(request, declared, capacity, in_use)
        if grant is not None:
            ledger[run_id] = resources.as_dict(grant)
        return grant
    while True:
        if store.read_status(run_id, reap=False)["state"] != "running":
            return None
        grant = _ledger(store, take)
        if grant is not None:
            return grant
        time.sleep(POLL_S)


def release_resources(store, run_id):
    _ledger(store, lambda ledger: ledger.pop(run_id, None))


def main(run_dir, hook=None):
    """Run one run to a final state. Returns the process exit code (0 unless the worker itself could not start)."""
    run_dir = Path(run_dir).resolve()
    job = json.loads((run_dir / "job.json").read_text())
    store = RunStore(job["work_root"])
    run_id = run_dir.name
    name = store.read_status(run_id, reap=False)["name"]
    start = process_start(os.getpid()) or {}
    store.update_record(run_id, {"worker": {"pid": os.getpid(), "pgid": os.getpgid(0), **start},
                                 "max_parallel": job.get("max_parallel", 1)})
    _log(run_dir, f"worker {os.getpid()} waiting for a slot ({job.get('max_parallel', 1)})")
    slot = _acquire_slot(store, run_id, int(job.get("max_parallel", 1)))
    if slot is None:
        _log(run_dir, f"not started: the run is {store.read_status(run_id, reap=False)['state']}")
        return 0
    try:
        updated, status = store.update_status(run_id, ("accepted",), {"state": "running"})
        if not updated:
            _log(run_dir, f"not started: the run is {status['state']}")
            return 0
        store.update_record(run_id, {"started_at": utc_now(), "python": platform.python_version(),
                                     _names.RECORD_VERSION_KEY: _sdk_version()})
        try:
            import yaml
            spec = yaml.safe_load((run_dir / "run_spec.yaml").read_text())
            reg = engine_set(job)
            engine_id = engine_id_of(spec)
            adapter = reg.get(engine_id)
            info = adapter.info()
            store.update_record(run_id, {"adapter": {"engine_id": info.engine_id, "version": info.adapter_version,
                                                     "source": reg.status(engine_id).source},
                                         **dict(adapter.fingerprint(spec))})
        except (EngineUnavailable, EngineSetMismatch) as e:
            _fail(store, run_id, name, str(e), run_dir)
            return 0
        try:
            requested = job.get("resources", spec.get("resources"))
            request = resources.parse_request(requested)
        except ValueError as e:
            _fail(store, run_id, name, str(e), run_dir)
            return 0
        declared = adapter.resources(spec) or resources.ResourceDeclaration()
        grant = acquire_resources(store, run_id, request, declared, capacity_of(job.get("capacity")))
        if grant is None:
            _log(run_dir, f"not started: the run is {store.read_status(run_id, reap=False)['state']}")
            return 0
        store.update_record(run_id, {"resources": {"requested": requested,
                                                   "declared": resources.as_dict(declared),
                                                   "granted": resources.as_dict(grant)}})
        (run_dir / "grant.json").write_text(json.dumps(resources.as_dict(grant), sort_keys=True))
        assets = resources.assets_for(declared, request)
        bad = resources.asset_problems(assets, job["config_repo"])     # verified again: the library may have changed
        if bad:
            _fail(store, run_id, name, "; ".join(bad), run_dir)
            return 0
        staged = {n: stage(run_dir, n, Path(job["config_repo"]) / ref["name"]) for n, ref, _ in assets}
        extra = {env_var: str(staged[n]) for n, _, env_var in assets if env_var}
        guarded = request.network != "allow" and declared.network != "none"
        if guarded:                                         # the engine could reach the network; this run may not
            extra.update(NO_NETWORK)
        store.update_record(run_id, {"assets": [{"name": n, "ref": ref, "staged": f"assets/{n}"} for n, ref, _ in assets],
                                     "network": {"requested": request.network, "declared": declared.network,
                                                 "guard": "proxy variables" if guarded else None}})
        _log(run_dir, "running")
        try:
            context = RunContext(run_dir, spec, job["config_repo"], job.get("sensor_library"), run_dir / "output",
                                 {"engine": job.get("engine", "auto"), "grant": resources.as_dict(grant),
                                  "assets": {n: str(p) for n, p in staged.items()}})
            returncode = None
            if hook is not None:
                adapter._execute(context, hook)
            else:
                plan = adapter.plan(context)
                for n, src in plan.stage.items():
                    stage(run_dir, n, src)
                returncode = launch(plan, run_dir, grant.cpu_threads, grant.gpu_ids, extra)
            collection = adapter.collect(run_dir / "output", run_dir)
            if collection.record:
                store.update_record(run_id, dict(collection.record))
            if collection.verdict != "complete":
                try:                                                  # what the engine left, listed for the user
                    store.write_artifacts(run_id, check_artifact_names(
                        [artifact_ref(run_dir / "run_spec.json")] +
                        [artifact_ref(a.path, name=a.name, frame=a.frame) for a in collection.artifacts]))
                except (ArtifactError, OSError):
                    pass
                why = collection.message or "the engine did not finish"
                _fail(store, run_id, name, why if returncode in (None, 0) else f"{why} (exit status {returncode})",
                      run_dir)
                return 0
            refs = [artifact_ref(run_dir / "run_spec.json")]
            refs += [artifact_ref(a.path, name=a.name, frame=a.frame) for a in collection.artifacts]
            check_artifact_names(refs)
            roles = {"run_spec.json": "config", **{r["name"]: a.role for r, a in zip(refs[1:], collection.artifacts)}}
            store.update_record(run_id, {"artifact_roles": roles})
            store.write_artifacts(run_id, refs)
            updated, status = store.update_status(run_id, ("running",), {"state": "rendered", "artifacts": refs})
            _log(run_dir, f"rendered: {len(refs)} artifacts" if updated else f"rendered, but the run is {status['state']}")
        except ArtifactError as e:
            _fail(store, run_id, name, f"artifact references could not be built: {e}", run_dir)
        except Exception as e:  # noqa: BLE001 -- any failure of an accepted run is an execution problem
            _log(run_dir, traceback.format_exc().rstrip())
            _fail(store, run_id, name, f"{type(e).__name__}: {e}", run_dir)
        return 0
    finally:
        try:
            release_resources(store, run_id)
            store.update_record(run_id, {"finished_at": utc_now()})
        finally:
            fcntl.flock(slot, fcntl.LOCK_UN)
            slot.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"usage: python -m {_names.WORKER_MODULE} <run_dir>")
    sys.exit(main(sys.argv[1]))
