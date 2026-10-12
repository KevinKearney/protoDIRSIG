"""The SatSim adapter without SatSim: interpreter discovery and its order, availability through a stub interpreter,
admission of the pass-through engine block (the schema, the GPU refusal, configuration resolution and its rules), the
declared resources, and the import rule (the SDK and the adapter import with `satsim`, `tensorflow` and `numpy`
blocked). Runs that need SatSim itself are in `tests/test_satsim_integration.py`."""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from manifold.core import admission, contract
from manifold.core.engine import Registry
from manifold.engines.satsim import adapter as satsim_adapter, interpreter
from manifold.engines.satsim.adapter import GPU_UNVERIFIED, SatsimAdapter

ROOT = Path(__file__).resolve().parents[1]
PROBE_CONFIG = ROOT / "docs" / "data" / "satsim_probe_config.yaml"


def stub_python(folder, versions=None, exit_code=0, counter=None):
    """An executable standing in for SatSim's interpreter: prints the probe line (or fails), counting its calls."""
    out = {"python": "3.11.0", "satsim": "0.0-stub", "tensorflow": None, "numpy": None, "astropy": None,
           "skyfield": None, **(versions or {})}
    path = Path(folder) / "python-stub"
    count = f'echo x >> "{counter}"\n' if counter else ""
    body = (f"echo 'Traceback: ModuleNotFoundError: No module named satsim' >&2\nexit {exit_code}\n" if exit_code else
            f"echo 'MANIFOLD_SATSIM_PROBE {json.dumps(out)}'\n")
    path.write_text(f"#!/bin/sh\n{count}{body}")
    path.chmod(0o755)
    return path


def spec_for(ref, seed=1, **engine):
    return {"spec_version": "run-spec/1",
            "descriptor": {"meta": {"name": "satsim-test", "tags": ["satsim"], "description": "test"},
                           "origin": {"kind": "synthetic", "engine": "satsim"},
                           "fidelity": {"modeled": ["as authored"], "approximated": [], "absent": [], "valid_for": "t"},
                           "opaque": {"source": "passthrough"}},
            "engine": {"mode": "passthrough", "config": ref, "seed": seed, "device": "cpu", **engine}}


@pytest.fixture
def library(tmp_path):
    lib = tmp_path / "library"
    (lib / "satsim" / "probe").mkdir(parents=True)
    shutil.copy2(PROBE_CONFIG, lib / "satsim" / "probe" / "config.yaml")
    return lib


def file_ref(lib, name="satsim/probe/config.yaml"):
    return {"name": name, "content_hash": "sha256:" + hashlib.sha256((lib / name).read_bytes()).hexdigest()}


def registry():
    reg = Registry()
    reg.register("satsim", SatsimAdapter)
    return reg


def _check(spec, lib):
    r = admission.validate_spec(spec, None, lib, ROOT / "manifold_sensors", registry=registry())
    return r.schema_errors, r.resolution_mismatches, r.unstamped


# --- interpreter discovery and availability -----------------------------------------------------------------------

def test_discovery_order_env_then_config_file_then_conda(tmp_path):
    a, b = stub_python(tmp_path), tmp_path / "other-python"
    shutil.copy2(a, b)
    conda_base = tmp_path / "conda"
    (conda_base / "condabin").mkdir(parents=True)
    (conda_base / "condabin" / "conda").write_text("#!/bin/sh\nexit 0\n")
    (conda_base / "condabin" / "conda").chmod(0o755)
    (conda_base / "envs" / "satsim" / "bin").mkdir(parents=True)
    shutil.copy2(a, conda_base / "envs" / "satsim" / "bin" / "python")
    cfg = tmp_path / "xdg" / "manifold" / "engines.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(yaml.safe_dump({"satsim": {"python": str(b)}}))
    env = {"PATH": str(conda_base / "condabin"), "HOME": str(tmp_path), "XDG_CONFIG_HOME": str(tmp_path / "xdg")}
    assert interpreter.locate({**env, "MANIFOLD_SATSIM_PYTHON": str(a)}) == (str(a), "$MANIFOLD_SATSIM_PYTHON")
    assert interpreter.locate(env) == (str(b), str(cfg))
    cfg.unlink()
    python, source = interpreter.locate(env)
    assert python == str(conda_base / "envs" / "satsim" / "bin" / "python") and "conda environment 'satsim'" in source
    shutil.rmtree(conda_base / "envs")
    assert "has no environment 'satsim'" in interpreter.locate(env)[1]
    assert "conda is not on PATH" in interpreter.locate({**env, "PATH": str(tmp_path / "empty")})[1]
    python, reason = interpreter.locate({**env, "MANIFOLD_SATSIM_PYTHON": str(tmp_path / "nope")})
    assert python is None and "not a file" in reason            # a misconfiguration is reported, not skipped


def test_availability_probes_once_per_process_and_reports_why_not(tmp_path, monkeypatch):
    counter = tmp_path / "calls"
    good = stub_python(tmp_path, {"satsim": "9.9"}, counter=counter)
    interpreter.clear_cache()
    monkeypatch.setenv("MANIFOLD_SATSIM_PYTHON", str(good))
    a = SatsimAdapter()
    assert a.availability() is None and a.availability() is None
    assert counter.read_text().count("x") == 1                       # cached per process
    assert a.fingerprint()["satsim"]["probe"]["versions"]["satsim"] == "9.9"
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    monkeypatch.setenv("MANIFOLD_SATSIM_PYTHON", str(stub_python(bad_dir, exit_code=1)))
    assert "cannot import satsim (exit status 1)" in a.availability()
    monkeypatch.setenv("MANIFOLD_SATSIM_PYTHON", str(tmp_path / "missing"))
    assert "not a file" in a.availability()
    interpreter.clear_cache()


def test_a_hanging_interpreter_times_out(tmp_path):
    p = tmp_path / "hang"
    p.write_text("#!/bin/sh\nsleep 30\n")
    p.chmod(0o755)
    r = interpreter.probe(str(p), timeout=1)
    assert not r["ok"] and "did not finish in 1 s" in r["reason"]


# --- admission ----------------------------------------------------------------------------------------------------

def test_a_stamped_probe_configuration_is_admitted(library):
    assert _check(spec_for(file_ref(library)), library) == ([], [], [])


@pytest.mark.parametrize("edit, fragment", [
    (lambda e: e.update(device="gpu:0"), GPU_UNVERIFIED),
    (lambda e: e.pop("seed"), "'seed' is a required property"),
    (lambda e: e.update(seed=1.5), "is not of type 'integer'"),
    (lambda e: e.update(extra=1), "Additional properties are not allowed"),
    (lambda e: e.update(mode="layered"), "'passthrough' was expected"),
])
def test_engine_block_refusals(library, edit, fragment):
    spec = spec_for(file_ref(library))
    edit(spec["engine"])
    schema, _, _ = _check(spec, library)
    assert any(fragment in m for m in schema), schema


def test_a_gpu_request_is_refused_as_unverified(library):
    spec = {**spec_for(file_ref(library)), "resources": {"gpu": {"count": 1}}}
    schema, _, _ = _check(spec, library)
    assert any(GPU_UNVERIFIED in m for m in schema) and any("declares at most 0" in m for m in schema), schema


def test_configuration_resolution_refusals(library):
    ref = file_ref(library)
    unstamped = {**ref, "content_hash": "sha256:<hash>"}
    assert _check(spec_for(unstamped), library)[2] == ["/engine/config"]
    wrong = {**ref, "content_hash": "sha256:" + "0" * 64}
    assert "does not match" in _check(spec_for(wrong), library)[1][0]
    assert "not found in the library" in _check(spec_for({**ref, "name": "satsim/nope.yaml"}), library)[1][0]
    assert "inside the library" in _check(spec_for({**ref, "name": "../x.yaml"}), library)[1][0]


def test_configuration_rules(library):
    path = library / "satsim" / "probe" / "config.yaml"
    doc = yaml.safe_load(path.read_text())
    for change, fragment in ((lambda d: d.update(radar={}), "exactly one of the roots"),
                             (lambda d: d["sim"].update(samples=2), "a run is one SatSim set"),
                             (lambda d: d["geometry"]["stars"].update(path="catalog/sstr7"), "must be a directory")):
        d = copy.deepcopy(doc)
        change(d)
        path.write_text(yaml.safe_dump(d))
        _, mismatches, _ = _check(spec_for(file_ref(library)), library)
        assert any(fragment in m for m in mismatches), mismatches


def test_a_directory_configuration_is_hashed_whole(library):
    from manifold.core.dirhash import directory_digest
    folder = library / "satsim" / "probe"
    ref = {"name": "satsim/probe", "content_hash": directory_digest(folder)}
    assert _check(spec_for(ref), library) == ([], [], [])
    (folder / "config.json").write_text("{}")
    assert "exactly one of" in _check(spec_for({**ref, "content_hash": directory_digest(folder)}), library)[1][0]


def test_the_schema_is_published_and_listed(tmp_path):
    a = SatsimAdapter()
    (doc,) = a.schemas()
    assert contract.published_location(doc["$id"]) == "manifold_contracts/satsim-engine-1.schema.json"
    assert json.loads((ROOT / "manifold_contracts" / "satsim-engine-1.schema.json").read_text()) == doc
    assert a.info().modes == ("passthrough",) and a.info().contracts == ("satsim-engine/1",)


def test_resources_declared(monkeypatch, tmp_path):
    monkeypatch.setenv("MANIFOLD_SATSIM_PYTHON", str(stub_python(tmp_path)))
    d = SatsimAdapter().resources()
    assert d.cpu_threads.variables == satsim_adapter.THREAD_VARIABLES and d.cpu_threads.default is None
    assert d.memory_bytes == 1 << 30 and d.gpu.maximum == 0 and d.network == "none"
    assert d.interpreter == str(tmp_path / "python-stub")


# --- import rule --------------------------------------------------------------------------------------------------

BLOCKED = """
import sys
class Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in ("satsim", "tensorflow", "numpy"):
            raise ImportError(f"blocked: {name}")
        return None
sys.meta_path.insert(0, Blocker())
import manifold.core, manifold.core.contract, manifold.core.admission, manifold.core.compose
import manifold.sim, manifold.sim.backend, manifold.sim.worker, manifold.sim.workspace
from manifold.engines.satsim.adapter import SatsimAdapter
a = SatsimAdapter()
a.info(); a.engine_schema(None); a.resources()
print("ok", sorted(m for m in sys.modules if m.split(".")[0] in ("satsim", "tensorflow", "numpy")))
"""


def test_the_sdk_and_the_adapter_import_with_satsim_tensorflow_and_numpy_blocked():
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    res = subprocess.run([sys.executable, "-c", BLOCKED], capture_output=True, text=True, env=env)
    assert res.returncode == 0, res.stderr[-2000:]
    assert res.stdout.strip() == "ok []"
