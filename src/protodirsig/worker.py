"""The run worker: `python -m protodirsig.worker <run_dir>`, one process per run, started by `LocalBackend`.

It loads `job.json`, records its pid and process group, waits for one of `max_parallel` slot locks
(`<work_root>/slots/slot-<i>.lock`, polled every second) while the run stays `accepted`, then moves the run from
`accepted` to `running` by compare-and-set (a run cancelled meanwhile is left alone and nothing runs). It builds the job
from `run_spec.yaml` with the run directory as the work directory, so `input/` and `output/` land there, runs the DIRSIG
dry run and, if it passes, the render; then it hashes the artifacts, writes `artifacts.json` and moves the run to
`rendered`. A dry-run failure or any exception moves the run to `failed` with an `execution` problem. Each move is a
compare-and-set from `running`, so a cancelled run is never overwritten. The slot is always released, and the outcome
is written to `worker.log` (where the backend also sends the process's stdout and stderr).

The execution record (`execution.json`) gains: `started_at`, `finished_at`, `worker` (`pid`, `pgid`), `python`, the
`protodirsig` version, the `dirfm` revision in use and whether it equals the spec's `engine.generator.revision`, the
DIRSIG installation and version, the propagator of an orbit run, and `max_parallel`. It is never part of a run id.

A pass-through run (`engine.mode: passthrough`, proposed) skips the layered job: the engine (`job.json` `engine`, else
the located `dirsig5`) runs the demo directory's simulation file on a copy of the directory under `<run_dir>/input/`,
with `--output_folder <run_dir>/output`; every file in `output/` is an artifact (no frames), and the execution record
gains `mode: passthrough`, the engine's path and version, its exit status and command.

Engine-bound: imports `protodirsig.simulation` (dirfm). The state machine is `main(run_dir, simulation_factory)`; tests
call it in-process with a stub factory.
"""
import fcntl
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from protodirsig import problems
from protodirsig.simulation import Simulation
from protodirsig.passthrough import is_passthrough, resolve_passthrough, run_engine
from protodirsig.store import ArtifactError, RunStore, artifacts_for, passthrough_artifacts, utc_now

REPOSITORY = Path(__file__).resolve().parents[2]
POLL_S = 1.0


def _log(run_dir, message):
    with open(Path(run_dir) / "worker.log", "a") as f:
        f.write(f"{utc_now()} {message}\n")


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


def _protodirsig_version():
    try:
        return version("protodirsig")
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


def _simulation(run_spec_path, config_repo, work_dir, sensor_library):
    return Simulation.from_run_spec(run_spec_path, config_repo, work_dir, sensor_library)


def _fail(store, run_id, name, message, run_dir):
    problem = problems.execution_failed(run_id, name, message)
    updated, _ = store.update_status(run_id, ("running",), {"state": "failed", "errors": [problem]})
    _log(run_dir, f"failed: {message}" if updated else f"not recorded (state changed meanwhile): {message}")
    return updated


def engine_version(engine):
    """The first line `<engine> --version` prints, or None."""
    try:
        out = subprocess.run([str(engine), "--version"], capture_output=True, text=True, timeout=60)
        text = (out.stdout or out.stderr).strip()
        return text.splitlines()[0] if text else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _run_passthrough(store, run_id, name, run_dir, job, spec):
    """A pass-through run: the engine runs the demo directory's simulation file on a copy under `<run_dir>/input/`,
    writing into `<run_dir>/output/`; every file there is an artifact (no frames)."""
    try:
        run = resolve_passthrough(spec, Path(job["config_repo"]))        # the digest is verified again here
        engine = job.get("engine")
        if not engine:
            home = locate_dirsig()["home"]
            engine = str(Path(home) / "bin" / "dirsig5") if home else None
        if not engine:
            _fail(store, run_id, name, "no DIRSIG installation was found for the pass-through run", run_dir)
            return
        store.update_record(run_id, {"mode": "passthrough",
                                     "engine": {"path": str(engine), "version": engine_version(engine)},
                                     "passthrough": {"directory": str(run.directory), "simulation": run.simulation_rel}})
        result = run_engine(run, run_dir, engine, log=run_dir / "worker.log")
        store.update_record(run_id, {"engine_exit_status": result["returncode"],
                                     "engine_command": [Path(result["command"][0]).name, *result["command"][1:]],
                                     "moved_from_input": result["moved"]})
        if result["returncode"] != 0:
            _fail(store, run_id, name, f"the engine exited with status {result['returncode']} (see worker.log)", run_dir)
            return
        refs = passthrough_artifacts(run_dir)
        store.write_artifacts(run_id, refs)
        updated, status = store.update_status(run_id, ("running",), {"state": "rendered", "artifacts": refs})
        _log(run_dir, f"rendered: {len(refs)} artifacts" if updated else f"rendered, but the run is {status['state']}")
    except ArtifactError as e:
        _fail(store, run_id, name, f"artifact references could not be built: {e}", run_dir)
    except Exception as e:  # noqa: BLE001 -- any failure of an accepted run is an execution problem
        _log(run_dir, traceback.format_exc().rstrip())
        _fail(store, run_id, name, f"{type(e).__name__}: {e}", run_dir)


def main(run_dir, simulation_factory=_simulation):
    """Run one run to a final state. Returns the process exit code (0 unless the worker itself could not start)."""
    run_dir = Path(run_dir).resolve()
    job = json.loads((run_dir / "job.json").read_text())
    store = RunStore(job["work_root"])
    run_id = run_dir.name
    name = store.read_status(run_id, reap=False)["name"]
    store.update_record(run_id, {"worker": {"pid": os.getpid(), "pgid": os.getpgid(0)},
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
        dirsig = locate_dirsig()
        dirfm = dirfm_revision()
        spec_revision = None
        try:
            import yaml
            spec = yaml.safe_load((run_dir / "run_spec.yaml").read_text())
            spec_revision = spec["engine"]["generator"]["revision"]
        except (OSError, KeyError, TypeError, ValueError):
            spec = None
        store.update_record(run_id, {"started_at": utc_now(), "python": platform.python_version(),
                                     "protodirsig_version": _protodirsig_version(),
                                     "dirfm": {**dirfm, "generator_revision": spec_revision,
                                               "generator_revision_matches": dirfm["revision"] == spec_revision},
                                     "dirsig": dirsig})
        _log(run_dir, "running")
        if spec is not None and is_passthrough(spec):
            _run_passthrough(store, run_id, name, run_dir, job, spec)
            return 0
        try:
            sim = simulation_factory(run_dir / "run_spec.yaml", Path(job["config_repo"]), run_dir,
                                     Path(job["sensor_library"]) if job.get("sensor_library") else None)
            check = sim.validate("dry_run")
            shutil.rmtree(run_dir / "validate", ignore_errors=True)          # the dry run's scratch job
            if not check.passed:
                why = check.execution_error or "; ".join(check.resolution_mismatches) or check.schema_error
                _fail(store, run_id, name, f"the DIRSIG dry run did not pass: {why}", run_dir)
                return 0
            result = sim.run(out_dir=run_dir / "output")
            if getattr(result, "propagator", None):
                store.update_record(run_id, {"propagator": result.propagator})
            refs = artifacts_for(run_dir, final=True)
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
        sys.exit("usage: python -m protodirsig.worker <run_dir>")
    sys.exit(main(sys.argv[1]))
