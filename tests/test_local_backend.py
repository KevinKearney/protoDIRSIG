"""LocalBackend against the Backend conformance suite (tests/backend_conformance.py), with real worker subprocesses and
16 x 16 DIRSIG renders (one full-frame run, cancelled while it renders).

The library is a copy of the small layer and sensor files in a temporary directory; the engine assets are the real
`manifold_config_repo`, read only. Each test has a 600 s limit (SIGALRM). The work root is deleted when the class
finishes.
"""
import fcntl
import json
import os
import shutil
import signal
from contextlib import ExitStack, contextmanager
from pathlib import Path

import pytest

from backend_conformance import BackendConformance
from protodirsig.backend import LocalBackend
from test_simulation import CONFIG_REPO, needs_dirsig

ROOT = Path(__file__).resolve().parents[1]
LIMIT_S = 600


@pytest.fixture(autouse=True)
def _time_limit():
    def expire(signum, frame):
        raise TimeoutError(f"test exceeded {LIMIT_S} s")
    old = signal.signal(signal.SIGALRM, expire)
    signal.alarm(LIMIT_S)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, old)


def _pgid_members(pgid):
    """Live (not zombie) processes in a process group, from /proc."""
    out = []
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            stat = (p / "stat").read_text()
        except OSError:
            continue
        fields = stat[stat.rindex(")") + 2:].split()
        if fields[0] not in "ZX" and int(fields[2]) == pgid:
            out.append(int(p.name))
    return out


@needs_dirsig
class TestLocalBackend(BackendConformance):
    @pytest.fixture(scope="class")
    @classmethod
    def library(cls, tmp_path_factory):
        root = tmp_path_factory.mktemp("library")
        for d in ("recipes", "scenarios", "engine_profiles"):
            shutil.copytree(ROOT / "manifold_run_specs" / d, root / "manifold_run_specs" / d)
        shutil.copytree(ROOT / "manifold_sensors", root / "manifold_sensors")
        yield root / "manifold_run_specs"
        shutil.rmtree(root, ignore_errors=True)

    @pytest.fixture(scope="class")
    @classmethod
    def backend(cls, tmp_path_factory, library):
        work = tmp_path_factory.mktemp("work")
        b = LocalBackend(work, CONFIG_REPO, max_parallel=1, library=library)
        yield b
        for run_id in b.store.list_runs():                    # stop anything still active, then delete the renders
            if b.get_run(run_id)["state"] in ("accepted", "running"):
                b.cancel_run(run_id)
        shutil.rmtree(work, ignore_errors=True)

    @contextmanager
    def hold_execution(self, backend):
        with ExitStack() as stack:
            for i in range(backend.max_parallel):
                f = stack.enter_context(open(backend.store.slots / f"slot-{i}.lock", "a"))
                fcntl.flock(f, fcntl.LOCK_EX)
            yield

    def kill_worker(self, backend, run_id):
        pid = backend.store.read_record(run_id)["worker"]["pid"]
        os.kill(pid, signal.SIGKILL)
        backend._poll_children()

    def execution_snapshot(self, backend, run_id):
        d = backend.store.run_dir(run_id)
        return {"execution": json.loads((d / "execution.json").read_text()), "workers_started": len(
            [ln for ln in (d / "worker.log").read_text().splitlines() if "waiting for a slot" in ln])}

    def run_processes(self, backend, run_id):
        backend._poll_children()
        pgid = (backend.store.read_record(run_id).get("worker") or {}).get("pgid")
        return _pgid_members(pgid) if pgid else []

    def passthrough_backend(self, tmp_path, library):
        import json as _json

        from test_passthrough import EXPECTED, VECTOR, stub_engine
        assets = tmp_path / "config_repo"
        shutil.copytree(VECTOR / "tree", assets / "demo_dirs" / "PassthroughVector")
        backend = LocalBackend(tmp_path / "work", assets, library=library, engine=stub_engine(tmp_path))
        recipe = {"compose": "compose/1", "meta": {"name": "conformance-passthrough"},
                  "passthrough": {"directory": {"name": "demo_dirs/PassthroughVector", "content_hash": EXPECTED["digest"]},
                                  "simulation": "demo.jsim"},
                  "engine_profile": "passthrough_runtime",
                  "fidelity": {"modeled": [], "approximated": [], "absent": [], "valid_for": "a conformance case"}}
        _json.dumps(recipe)
        return backend, recipe

    def second_backend(self, backend):
        return LocalBackend(backend.store.root, CONFIG_REPO, max_parallel=backend.max_parallel)

    def test_the_execution_record_of_a_rendered_run(self, backend, rendered):
        rec = backend.store.read_record(rendered["first"]["run_id"])
        for key in ("run_id", "submitted_at", "started_at", "finished_at", "worker", "python", "protodirsig_version",
                    "dirfm", "dirsig", "max_parallel"):
            assert key in rec, key
        assert rec["dirfm"]["generator_revision_matches"] is True and rec["dirsig"]["home"]
        print(json.dumps(rec, indent=1))

    def test_a_running_worker_is_not_reaped(self, backend, library):
        from backend_conformance import variant, wait_for
        recipe = variant(library, "auror_ref", "local_not_reaped", width=20)
        run_id = backend.submit_run(recipe)["run_id"]
        final = wait_for(backend, run_id, ("rendered", "failed", "cancelled"))
        assert final["state"] == "rendered", final["errors"]
        assert "reaped" not in backend.store.read_record(run_id)
