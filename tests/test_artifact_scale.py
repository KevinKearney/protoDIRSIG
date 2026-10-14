"""Artifact listing at scale: a rendered pass-through run with 2,000 output files (LightCurve1 wrote 1,681).

The references are hashed once, when the run completes (`passthrough_artifacts`, written to `artifacts.json` and the
status); listing and fetching read that record and never hash again.
"""
import hashlib
import time
from pathlib import Path

from manifold.core import identity
from manifold.sim import store as store_mod
from manifold.sim.backend import LocalBackend
from manifold.core.compose import compose
from manifold.engines.dirsig.artifacts import passthrough_artifacts

ROOT = Path(__file__).resolve().parents[1]
SENSORS = ROOT / "manifold_sensors"
N = 2000


def test_listing_2000_artifacts_reads_the_record_and_does_not_hash(tmp_path, monkeypatch):
    backend = LocalBackend(tmp_path / "work", ROOT / "manifold_config_repo", sensor_library=SENSORS)
    resolved = identity.resolved_run_spec(compose(ROOT / "manifold_run_specs" / "recipes" / "auror_ref.yaml"), SENSORS)
    run_id, _ = backend.store.create_run(resolved, "scale", {})
    out = backend.store.run_dir(run_id) / "output"
    out.mkdir()
    for i in range(N):
        (out / f"frame{i:05d}.img").write_bytes(i.to_bytes(4, "little") * 16)
    refs = passthrough_artifacts(backend.store.run_dir(run_id))                       # the worker's completion step
    backend.store.write_artifacts(run_id, refs)
    backend.store.update_status(run_id, ("accepted",), {"state": "rendered", "artifacts": refs})

    def no_hashing(*a, **kw):
        raise AssertionError("an artifact was hashed after completion")
    monkeypatch.setattr(store_mod, "artifact_ref", no_hashing)
    t = time.perf_counter()
    listed = backend.list_artifacts(run_id)["artifacts"]
    elapsed = time.perf_counter() - t
    assert len(listed) == N + 1 and listed == refs and elapsed < 1.0
    assert [r["name"] for r in listed[1:]] == sorted(f"frame{i:05d}.img" for i in range(N))
    assert len(backend.get_run(run_id)["artifacts"]) == N + 1                # the status carries every reference
    data, media_type = backend.get_artifact(run_id, f"frame{N - 1:05d}.img")
    assert data == (N - 1).to_bytes(4, "little") * 16 and media_type == "application/octet-stream"
    assert listed[-1]["sha256"] == hashlib.sha256(data).hexdigest()
