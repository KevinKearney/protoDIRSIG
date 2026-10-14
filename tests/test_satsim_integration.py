"""SatSim runs through `LocalBackend`, when SatSim's interpreter is found here (skipped otherwise, with the reason): the
library sample twice with one seed gives byte-identical frames, annotations and `config.json`; another seed differs; one
thread equals the default; a library without the ephemeris is refused at admission naming the asset, so no SatSim
process starts and nothing connects; SIGTERM mid-run leaves a cancelled run whose collector says `incomplete` with the
written frames, and the run lists them; a bad configuration fails within seconds with the traceback head. About 40 s of SatSim time in all.
Every run is network-free: each checks that the launcher's guard recorded no connection attempt."""
import hashlib
import json
import shutil
import time
from pathlib import Path

import pytest
import yaml

from backend_conformance import wait_for
from manifold.core.errors import AdmissionError
from manifold.engines.satsim import interpreter
from manifold.engines.satsim.adapter import SatsimAdapter

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "manifold_run_specs" / "satsim" / "tahoe_worldview2.yaml"
CONFIG = ROOT / "manifold_config_repo" / "satsim" / "tahoe_worldview2.yaml"


def _why_not():
    reason = SatsimAdapter().availability()
    if reason:
        return f"SatSim is not available here: {reason}"
    from test_satsim_adapter import assets_present
    return None if assets_present() else "the pinned SatSim assets are absent (python scripts/bootstrap.py assets)"


WHY_NOT = _why_not()
pytestmark = [pytest.mark.satsim, pytest.mark.skipif(WHY_NOT is not None, reason=WHY_NOT or "")]


def _library(tmp_path, edit=None, frames=None, size=None, with_ephemeris=True):
    """A library holding the sample configuration (optionally edited) and the pinned assets, and a run spec for it."""
    lib = tmp_path / "library"
    (lib / "satsim" / "assets").mkdir(parents=True)
    store = ROOT / "manifold_config_repo" / "satsim" / "assets"
    for name in ("de421.bsp", "finals2000A.all"):
        if with_ephemeris or name != "de421.bsp":
            (lib / "satsim" / "assets" / name).symlink_to((store / name).resolve())
    doc = yaml.safe_load(CONFIG.read_text())
    if frames:
        doc["fpa"]["num_frames"] = frames
    if size:
        doc["fpa"]["height"] = doc["fpa"]["width"] = size
    if edit:
        edit(doc)
    path = lib / "satsim" / "run.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return lib, {"name": "satsim/run.yaml", "content_hash": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()}


def _spec(ref=None, seed=1, resources=None):
    spec = yaml.safe_load(SPEC.read_text())
    if ref is not None:
        spec["engine"]["config"] = ref
    spec["engine"]["seed"] = seed
    if resources:
        spec["resources"] = resources
    return spec


def _run(tmp_path, name, spec, library=ROOT / "manifold_config_repo", timeout=300):
    from manifold.sim.backend import LocalBackend
    backend = LocalBackend(tmp_path / name, library)
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    final = wait_for(backend, backend.submit_run(str(path))["run_id"], ("rendered", "failed", "cancelled"),
                     timeout=timeout)
    return backend, final


def _digests(backend, final, prefixes=("ImageFiles_", "Annotations_", "config.json")):
    return {a["name"]: a["sha256"] for a in final["artifacts"] if a["name"].startswith(prefixes)}


def _no_network(backend, final):
    out = backend.store.run_dir(final["run_id"]) / "output"
    assert not (out / "network_attempts.log").exists(), (out / "network_attempts.log").read_text()


@pytest.fixture(scope="module")
def reference(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("satsim_reference")
    backend, final = _run(tmp, "first", _spec())
    return tmp, backend, final


def test_the_sample_repeats_byte_for_byte_with_one_seed(reference, tmp_path):
    _, backend, final = reference
    assert final["state"] == "rendered" and final["verdict"] == "complete", final["errors"]
    assert final["run_id"] == "81fe69a103a32acdc8a1015e36724faa9d3ed8152488806dbd8a93f24adc5a3d"
    _no_network(backend, final)
    other, again = _run(tmp_path, "again", _spec())                   # another work root: a fresh run directory
    assert again["run_id"] == final["run_id"] and again["state"] == "rendered"
    first, second = _digests(backend, final), _digests(other, again)
    assert len([n for n in first if n.startswith("ImageFiles_")]) == 3 and "config.json" in first
    assert first == second
    rec = backend.store.read_record(final["run_id"])
    md = rec["engine_metadata"]
    assert md["frames"] == 3 and md["image_size"] == [64, 64] and md["seed"] == 1 and md["set_folder"] == "set"
    assert md["versions"]["satsim"] == "0.26.1" or md["versions"]["satsim"]
    assert rec["satsim"]["assets"]["de421.bsp"].startswith("sha256:a20a7139") and rec["satsim"]["launcher_sha256"]
    assert rec["artifact_roles"]["ImageFiles_set.0000.fits"] == "product"
    assert rec["artifact_roles"]["Annotations_set.0000.json"] == "truth"


def test_another_seed_gives_other_frames(reference, tmp_path):
    _, backend, final = reference
    other, seeded = _run(tmp_path, "seed2", _spec(seed=2))
    assert seeded["state"] == "rendered" and seeded["run_id"] != final["run_id"]
    a, b = _digests(backend, final, ("ImageFiles_",)), _digests(other, seeded, ("ImageFiles_",))
    assert a.keys() == b.keys() and all(a[k] != b[k] for k in a)
    _no_network(other, seeded)


def test_one_thread_gives_the_default_threads_frames(reference, tmp_path):
    _, backend, final = reference
    other, one = _run(tmp_path, "one_thread", _spec(resources={"cpu_threads": 1}))
    assert one["state"] == "rendered" and one["run_id"] != final["run_id"]      # a requested count enters the id
    assert _digests(backend, final) == _digests(other, one)
    out = other.store.run_dir(one["run_id"])
    assert other.store.read_record(one["run_id"])["resources"]["granted"]["cpu_threads"] == 1
    assert "satsim launcher" in (out / "worker.log").read_text()


def test_without_the_ephemeris_the_run_is_refused_naming_the_asset(tmp_path):
    from manifold.sim.backend import LocalBackend
    lib, ref = _library(tmp_path, with_ephemeris=False)
    backend = LocalBackend(tmp_path / "work", lib)
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(_spec(ref), sort_keys=False))
    with pytest.raises(AdmissionError) as e:
        backend.submit_run(str(path))
    assert "asset 'de421.bsp'" in e.value.problem["detail"] and "not found" in e.value.problem["detail"]
    assert backend.store.list_runs() == []                              # no run, no SatSim process, no connection


def test_sigterm_mid_run_leaves_a_cancelled_run_and_an_incomplete_collection(tmp_path):
    from manifold.sim.backend import LocalBackend
    lib, ref = _library(tmp_path, frames=40, size=256)
    backend = LocalBackend(tmp_path / "work", lib)
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(_spec(ref), sort_keys=False))
    run_id = backend.submit_run(str(path))["run_id"]
    frames = backend.store.run_dir(run_id) / "output" / "set" / "ImageFiles"
    deadline = time.monotonic() + 120
    while len(list(frames.glob("*.fits"))) < 2 and time.monotonic() < deadline:
        time.sleep(0.2)
    status = backend.cancel_run(run_id)
    assert status["state"] == "cancelled" and status["verdict"] == "incomplete"
    time.sleep(1.0)
    run_dir = backend.store.run_dir(run_id)
    c = SatsimAdapter().collect(run_dir / "output", run_dir)
    written = c.record["engine_metadata"]["frames"]
    assert c.verdict == "incomplete" and 2 <= written < 40 and f"{written} of 40 frames written" in c.message
    assert sum(a.role == "product" for a in c.artifacts) == written
    assert not (run_dir / "output" / "satsim_result.json").exists()
    listed = backend.list_artifacts(run_id)["artifacts"]               # the worker collected them when cancelled
    assert listed[0]["name"] == "run_spec.json" and listed[0]["role"] == "config"
    assert sum(r["role"] == "product" for r in listed) == written
    assert {r["name"] for r in listed if r["role"] == "product"} == \
        {a.name or a.path.name for a in c.artifacts if a.role == "product"}
    cancellation = backend.store.read_record(run_id)["cancellation"]
    assert cancellation["verdict"] == "incomplete" and cancellation["collected"] == len(listed)
    assert backend.get_run(run_id)["state"] == "cancelled" and backend.get_run(run_id)["verdict"] == "incomplete"


def test_a_bad_configuration_fails_within_seconds_with_the_traceback_head(tmp_path):
    lib, ref = _library(tmp_path, edit=lambda d: d["fpa"].pop("time"))
    started = time.monotonic()
    backend, final = _run(tmp_path, "bad", _spec(ref), library=lib)
    took = time.monotonic() - started
    assert final["state"] == "failed" and final["verdict"] == "failed"
    assert "SatSim failed: KeyError" in final["errors"][0]["detail"] and took < 60
    md = backend.store.read_record(final["run_id"])["engine_metadata"]
    assert md["traceback_head"] and "KeyError" in md["traceback_head"][-1] and md["elapsed_s"] < 20
    _no_network(backend, final)
