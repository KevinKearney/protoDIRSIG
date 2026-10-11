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
DIRSIG `dirfm` and `dirsig`), the members the adapter's collection adds (for a pass-through run the engine, its tools,
exit status, cache and thermal measurements), `artifact_roles` and `max_parallel`. It is never part of a run id.

Engine-free: the worker imports no engine package; the engine runs in the process the plan describes. `main(run_dir,
hook)` with a `hook` (tests) calls the adapter's `execute(context, hook)` in this process instead of launching the plan.
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

from manifold.core import _names, problems
from manifold.core.engine import EngineUnavailable, RunContext, engine_id_of
from manifold.sim import engines
from manifold.sim.store import ArtifactError, RunStore, artifact_ref, check_artifact_names, process_start, utc_now

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


def environment(plan, run_dir, threads=None):
    """The launched process's environment: the worker's, with the plan's policy applied."""
    env = dict(os.environ)
    for k in plan.env.unset:
        env.pop(k, None)
    env.update({k: str(v) for k, v in plan.env.set.items()})
    if plan.env.isolate_home:
        home = Path(run_dir) / "home"
        home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(home)
    for var in plan.env.thread_variables:
        env[var] = str(threads if threads is not None else 1)
    return env


def launch(plan, run_dir, threads=None):
    """Run the plan to completion; its stdout and stderr go to `worker.log`. Returns the exit status."""
    run_dir = Path(run_dir)
    with open(run_dir / "worker.log", "ab") as log:
        proc = subprocess.Popen(command(plan), cwd=str(plan.cwd or run_dir), env=environment(plan, run_dir, threads),
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        return proc.wait()


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
            reg = engines.registry()
            engine_id = engine_id_of(spec)
            adapter = reg.get(engine_id)
            info = adapter.info()
            store.update_record(run_id, {"adapter": {"engine_id": info.engine_id, "version": info.adapter_version,
                                                     "source": reg.status(engine_id).source},
                                         **dict(adapter.fingerprint(spec))})
        except EngineUnavailable as e:
            _fail(store, run_id, name, str(e), run_dir)
            return 0
        _log(run_dir, "running")
        try:
            context = RunContext(run_dir, spec, job["config_repo"], job.get("sensor_library"), run_dir / "output",
                                 {"engine": job.get("engine", "auto")})
            returncode = None
            if hook is not None:
                adapter.execute(context, hook)
            else:
                returncode = launch(adapter.plan(context), run_dir)
            collection = adapter.collect(run_dir / "output", run_dir)
            if collection.record:
                store.update_record(run_id, dict(collection.record))
            if collection.verdict != "complete":
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
            store.update_record(run_id, {"finished_at": utc_now()})
        finally:
            fcntl.flock(slot, fcntl.LOCK_UN)
            slot.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"usage: python -m {_names.WORKER_MODULE} <run_dir>")
    sys.exit(main(sys.argv[1]))
