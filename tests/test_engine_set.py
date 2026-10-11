"""The engine registry is explicit, and the worker runs with exactly the engine set the backend admitted the run with.

Core alone raises `RegistryNotConfigured` with its message when no registry is passed and none is configured, and works
with a registry argument and no `manifold.sim` import. The backend writes its engine set (ids, import targets,
adapter versions) into `job.json`; the worker rebuilds that set (`worker.engine_set`) and fails the run with an
`execution` problem when it cannot (an adapter that does not load, or loads at another version)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from manifold.core.engine import Registry, RegistryNotConfigured
from manifold.sim.worker import EngineSetMismatch, engine_set

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "manifold_run_specs" / "recipes" / "auror_ref.yaml"


def _core_only(code):
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout.strip().splitlines()[-1])


def test_core_without_a_registry_says_how_to_configure_one():
    got = _core_only(f"""
import json, sys
from manifold.core.compose import compose
from manifold.core.engine import RegistryNotConfigured
try:
    compose({str(RECIPE)!r})
    print(json.dumps({{"raised": None}}))
except RegistryNotConfigured as e:
    print(json.dumps({{"raised": str(e), "sim": "manifold.sim" in sys.modules}}))
""")
    assert got == {"raised": "no engine registry configured; pass registry= or import manifold.sim", "sim": False}
    assert RegistryNotConfigured.MESSAGE == got["raised"]


def test_core_alone_works_with_a_registry_argument():
    got = _core_only(f"""
import json, sys
from manifold.core.admission import validate_spec
from manifold.core.compose import compose
from manifold.core.engine import Registry
from manifold.engines.dirsig.adapter import DirsigAdapter
reg = Registry()
reg.register("dirsig", DirsigAdapter)
spec = compose({str(RECIPE)!r}, registry=reg)
r = validate_spec(spec, None, {str(ROOT / "manifold_config_repo")!r}, {str(ROOT / "manifold_sensors")!r}, registry=reg)
print(json.dumps({{"valid": r.valid, "run_id": r.run_id, "sim": "manifold.sim" in sys.modules,
                   "errors": r.schema_errors + r.resolution_mismatches}}))
""")
    assert got["valid"] and got["sim"] is False, got["errors"]
    assert got["run_id"].startswith("489824e0a63e")


def _described(**over):
    from manifold.engines.dirsig.adapter import DirsigAdapter
    reg = Registry()
    reg.register("dirsig", DirsigAdapter)
    d = reg.describe()
    d[0].update(over)
    return d


def test_the_worker_rebuilds_the_backend_engine_set():
    reg = engine_set({"engines": _described()})
    assert reg.ids() == ["dirsig"] and reg.describe()[0]["target"] == "manifold.engines.dirsig.adapter:DirsigAdapter"
    with pytest.raises(EngineSetMismatch, match="at version 9.9.9, the worker at version"):
        engine_set({"engines": _described(adapter_version="9.9.9")})
    with pytest.raises(EngineSetMismatch, match="the worker cannot load it"):
        engine_set({"engines": _described(target="no_such_module:Adapter")})
    assert "dirsig" in engine_set({}).ids()                              # a job.json from before: discovery


def test_a_backend_engine_set_the_worker_cannot_rebuild_fails_the_run(tmp_path):
    """The backend admits with its engine set; job.json is then altered to name an adapter version the worker does
    not have: the run fails with an execution problem naming the mismatch, nothing else is used."""
    import fcntl
    import shutil

    import yaml
    from backend_conformance import wait_for
    from manifold.sim.backend import LocalBackend
    backend = LocalBackend(tmp_path / "work", ROOT / "manifold_config_repo", sensor_library=ROOT / "manifold_sensors")
    variant = tmp_path / "lib"
    for d in ("recipes", "scenarios", "engine_profiles"):
        shutil.copytree(ROOT / "manifold_run_specs" / d, variant / "manifold_run_specs" / d)
    doc = yaml.safe_load(RECIPE.read_text())
    for m in doc["settings"]:
        m["roi"] = {"Width": 16, "Height": 16, "OffsetX": None, "OffsetY": None}
    path = variant / "manifold_run_specs" / "recipes" / "auror_16.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    with open(backend.store.slots / "slot-0.lock", "a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)                             # the worker waits; job.json is edited meanwhile
        run_id = backend.submit_run(str(path))["run_id"]
        job_path = backend.store.run_dir(run_id) / "job.json"
        job = json.loads(job_path.read_text())
        assert [e["engine_id"] for e in job["engines"]] == ["dirsig"]
        job["engines"][0]["adapter_version"] = "0.0.0-not-installed"
        job_path.write_text(json.dumps(job))
    final = wait_for(backend, run_id, ("rendered", "failed"), timeout=120)
    assert final["state"] == "failed" and final["errors"][0]["type"] == "urn:manifold:problem:execution"
    assert "engine set mismatch" in final["errors"][0]["detail"]
