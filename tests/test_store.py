"""The run store (protodirsig.store) and the worker's state machine (protodirsig.worker.main with a stub engine).

The real worker subprocess and DIRSIG are exercised by the backend conformance tests (tests/test_local_backend.py).
"""
import hashlib
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from api_schema import errors as schema_errors
from protodirsig import identity, store as store_mod, worker
from protodirsig.compose import compose
from protodirsig.errors import NotFoundError
from protodirsig.store import ArtifactError, RunStore, artifacts_for

ROOT = Path(__file__).resolve().parents[1]
SENSORS = ROOT / "manifold_sensors"
RECIPE = ROOT / "manifold_run_specs" / "recipes" / "auror_ref.yaml"
JOB = {"config_repo": str(ROOT / "manifold_config_repo"), "sensor_library": str(SENSORS), "max_parallel": 1}


@pytest.fixture
def resolved():
    return identity.resolved_run_spec(compose(RECIPE), SENSORS)


@pytest.fixture
def store(tmp_path):
    return RunStore(tmp_path / "work")


def test_create_run_writes_a_complete_run(store, resolved):
    run_id, created = store.create_run(resolved, "auror-ref-static-pose", JOB)
    assert created and run_id == identity.run_id(compose(RECIPE), SENSORS)
    d = store.run_dir(run_id)
    assert hashlib.sha256((d / "run_spec.json").read_bytes()).hexdigest() == run_id
    assert identity.run_id(yaml.safe_load((d / "run_spec.yaml").read_text()), SENSORS) == run_id
    status = store.read_status(run_id)
    assert schema_errors("run_status", status) == []
    assert status["state"] == "accepted" and [a["name"] for a in status["artifacts"]] == ["run_spec.json"]
    assert status["artifacts"][0]["sha256"] == run_id
    assert json.loads((d / "job.json").read_text())["work_root"] == str(store.root)
    assert store.read_record(run_id)["submitted_at"].endswith("Z")
    assert store.create_run(resolved, "again", JOB) == (run_id, False)
    assert store.list_runs() == [run_id]


def test_create_run_race_creates_once(store, resolved):
    results, barrier = [], threading.Barrier(2)

    def go():
        barrier.wait()
        results.append(store.create_run(resolved, "auror-ref-static-pose", JOB))
    threads = [threading.Thread(target=go) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(c for _, c in results) == [False, True] and len({r for r, _ in results}) == 1
    assert [p.name for p in store.runs.iterdir()] == [results[0][0]]          # no temporary directory left


def test_the_yaml_round_trip_is_checked(store, resolved, monkeypatch):
    real = yaml.safe_dump
    monkeypatch.setattr(store_mod.yaml, "safe_dump", lambda d, **k: real(d, **k).replace("seed: 42", "seed: 43"))
    with pytest.raises(ValueError, match="round trip"):
        store.create_run(resolved, "x", JOB)
    assert list(store.runs.iterdir()) == []


def test_an_incomplete_run_directory_is_replaced(store, resolved):
    run_id = identity.sha256_hex(identity.canonical_json(resolved))
    (store.runs / run_id).mkdir()
    (store.runs / run_id / "junk").write_text("half-written")
    assert store.create_run(resolved, "n", JOB) == (run_id, True)
    assert not (store.runs / run_id / "junk").exists()


def test_compare_and_set_refuses_a_stale_state(store, resolved):
    run_id, _ = store.create_run(resolved, "n", JOB)
    assert store.update_status(run_id, ("accepted",), {"state": "running"})[0]
    updated, status = store.update_status(run_id, ("accepted",), {"state": "cancelled"})
    assert not updated and status["state"] == "running" and store.read_status(run_id, reap=False)["state"] == "running"


def test_unknown_ids_raise_not_found(store):
    for call in (lambda: store.read_status("0" * 64), lambda: store.read_status("nope"),
                 lambda: store.read_sweep("0" * 64), lambda: store.update_status("1" * 64, ("accepted",), {})):
        with pytest.raises(NotFoundError) as e:
            call()
        assert schema_errors("problem", e.value.problem) == [] and e.value.status == 404


def _dead_pid():
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def test_reap_fails_a_run_whose_worker_died(store, resolved):
    run_id, _ = store.create_run(resolved, "n", JOB)
    store.update_record(run_id, {"worker": {"pid": _dead_pid(), "pgid": 0}})
    status = store.read_status(run_id)
    assert status["state"] == "failed" and status["errors"][0]["type"] == "urn:protodirsig:problem:execution"
    assert "no longer running" in status["errors"][0]["detail"] and schema_errors("run_status", status) == []
    assert store.read_record(run_id)["finished_at"]


def test_reap_waits_for_a_worker_to_start(store, resolved):
    run_id, _ = store.create_run(resolved, "n", JOB)
    assert store.read_status(run_id)["state"] == "accepted"                      # no pid yet, but recent
    store.update_record(run_id, {"submitted_at": "2000-01-01T00:00:00Z"})
    assert store.read_status(run_id)["state"] == "failed"


def test_reap_leaves_a_live_worker_alone(store, resolved):
    run_id, _ = store.create_run(resolved, "n", JOB)
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", "protodirsig.worker"])
    try:
        store.update_record(run_id, {"worker": {"pid": proc.pid, "pgid": proc.pid}})
        assert store.read_status(run_id)["state"] == "accepted"
    finally:
        proc.kill()
        proc.wait()


def _fake_output(run_dir, frames=3, collide=False):
    out = run_dir / "output"
    out.mkdir(parents=True, exist_ok=True)
    caps = []
    for t in range(frames):
        img = out / f"Out-t{0 if collide else t:04d}-c0000.img"
        truth = out / f"truth1-t{t:04d}-c0000.img"
        for p, n in ((img, 64), (truth, 32)):
            p.write_bytes(bytes([t]) * n)
            p.with_name(p.name + ".hdr").write_text(f"ENVI\nframe = {t}\n")
        caps.append({"task_index": t, "capture_index": 0, "plugin_data": {"filename": str(img),
                                                                          "truth_filenames": ["", str(truth), ""]}})
    (out / "log_info.json").write_text(json.dumps({"capture_list": list(reversed(caps))}))   # out of order on purpose
    (out / "run_info.json").write_text("{}")


def test_artifact_references(store, resolved):
    run_id, _ = store.create_run(resolved, "n", JOB)
    d = store.run_dir(run_id)
    _fake_output(d)
    refs = artifacts_for(d, final=True)
    for r in refs:
        assert schema_errors("artifact_ref", r) == [], r
        assert hashlib.sha256(Path(r["uri"].removeprefix("file://")).read_bytes()).hexdigest() == r["sha256"]
    run_level = [r for r in refs if "frame" not in r]
    assert [r["name"] for r in run_level] == ["run_spec.json", "run_info.json", "log_info.json"]
    framed = [r for r in refs if "frame" in r]
    assert len(framed) == 12 and sorted({r["frame"] for r in framed}) == [0, 1, 2]
    assert [r["name"] for r in framed if r["frame"] == 1] == ["Out-t0001-c0000.img", "Out-t0001-c0000.img.hdr",
                                                              "truth1-t0001-c0000.img", "truth1-t0001-c0000.img.hdr"]
    assert {r["media_type"] for r in framed} == {"application/octet-stream", "text/plain"}
    assert schema_errors("artifact_list", {"run_id": run_id, "artifacts": refs}) == []
    assert [r["name"] for r in artifacts_for(d)] == ["run_spec.json", "run_info.json", "log_info.json"]


def test_colliding_artifact_names_are_an_error(store, resolved):
    run_id, _ = store.create_run(resolved, "n", JOB)
    _fake_output(store.run_dir(run_id), collide=True)
    with pytest.raises(ArtifactError, match="used twice"):
        artifacts_for(store.run_dir(run_id), final=True)


def test_sweeps_are_created_once(store):
    rec = {"recipe": {"name": "r", "sha256": "a" * 64}, "run_ids": ["b" * 64]}
    assert store.create_sweep("c" * 64, rec) == ({"sweep_id": "c" * 64, **rec}, True)
    assert store.create_sweep("c" * 64, {"recipe": {}, "run_ids": []})[1] is False
    assert store.read_sweep("c" * 64)["run_ids"] == ["b" * 64]


# --- the worker's state machine, in-process, with a stub engine -----------------------------------------------------

class Stub:
    def __init__(self, run_dir, dry_run_ok=True, run_error=None, calls=None):
        self.run_dir, self.dry_run_ok, self.run_error, self.calls = run_dir, dry_run_ok, run_error, calls

    def validate(self, engine_check):
        self.calls.append(("validate", engine_check))
        return SimpleNamespace(passed=self.dry_run_ok, execution_error=None if self.dry_run_ok else "[error] no scene",
                               resolution_mismatches=[], schema_error=None)

    def run(self, out_dir):
        self.calls.append(("run", str(out_dir)))
        if self.run_error:
            raise self.run_error
        _fake_output(self.run_dir)
        return SimpleNamespace(propagator=None)


def _factory(calls, **kw):
    return lambda spec, repo, work, lib: Stub(work, calls=calls, **kw)


def test_worker_renders_and_records(store, resolved):
    run_id, _ = store.create_run(resolved, "n", JOB)
    calls = []
    assert worker.main(store.run_dir(run_id), _factory(calls)) == 0
    status = store.read_status(run_id)
    assert status["state"] == "rendered" and schema_errors("run_status", status) == []
    assert calls[0] == ("validate", "dry_run") and calls[1][0] == "run"
    assert status["artifacts"] == json.loads((store.run_dir(run_id) / "artifacts.json").read_text())
    rec = store.read_record(run_id)
    for key in ("submitted_at", "started_at", "finished_at", "worker", "python", "protodirsig_version", "dirfm",
                "dirsig", "max_parallel"):
        assert key in rec, key
    assert rec["dirfm"]["generator_revision_matches"] is True
    assert "rendered" in (store.run_dir(run_id) / "worker.log").read_text()


def test_worker_fails_a_run_whose_dry_run_fails(store, resolved):
    run_id, _ = store.create_run(resolved, "n", JOB)
    calls = []
    worker.main(store.run_dir(run_id), _factory(calls, dry_run_ok=False))
    status = store.read_status(run_id)
    assert status["state"] == "failed" and [c[0] for c in calls] == ["validate"]
    assert status["errors"][0]["type"] == "urn:protodirsig:problem:execution" and "no scene" in status["errors"][0]["detail"]
    assert schema_errors("run_status", status) == []


def test_worker_fails_a_run_whose_render_raises(store, resolved):
    run_id, _ = store.create_run(resolved, "n", JOB)
    worker.main(store.run_dir(run_id), _factory([], run_error=RuntimeError("dirsig5 exited 1")))
    status = store.read_status(run_id)
    assert status["state"] == "failed" and "dirsig5 exited 1" in status["errors"][0]["detail"]


def test_worker_does_not_run_a_cancelled_run(store, resolved):
    run_id, _ = store.create_run(resolved, "n", JOB)
    store.update_status(run_id, ("accepted",), {"state": "cancelled"})
    calls = []
    worker.main(store.run_dir(run_id), _factory(calls))
    assert calls == [] and store.read_status(run_id)["state"] == "cancelled"


def test_worker_waits_for_a_slot_and_stops_if_cancelled(store, resolved):
    import fcntl
    run_id, _ = store.create_run(resolved, "n", JOB)
    calls = []
    with open(store.slots / "slot-0.lock", "a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        t = threading.Thread(target=worker.main, args=(store.run_dir(run_id), _factory(calls)))
        t.start()
        time.sleep(1.5)
        # in-process, the recorded pid is pytest's, not a protodirsig.worker, so read without reaping
        assert store.read_status(run_id, reap=False)["state"] == "accepted" and t.is_alive()
        store.update_status(run_id, ("accepted",), {"state": "cancelled"})
        t.join(10)
    assert not t.is_alive() and calls == [] and store.read_status(run_id)["state"] == "cancelled"


def test_worker_does_not_overwrite_a_cancel_during_the_render(store, resolved):
    run_id, _ = store.create_run(resolved, "n", JOB)

    class Cancelling(Stub):
        def run(self, out_dir):
            store.update_status(run_id, ("running",), {"state": "cancelled"})
            return super().run(out_dir)
    worker.main(store.run_dir(run_id), lambda s, r, w, lib: Cancelling(w, calls=[]))
    assert store.read_status(run_id)["state"] == "cancelled"
