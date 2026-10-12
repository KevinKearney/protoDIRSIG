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


ASSET_STORE = ROOT / "manifold_config_repo" / "satsim" / "assets"


def assets_present():
    from manifold.core.resources import asset_problems
    decl = [(a.name, a.ref, a.env) for a in satsim_adapter.ASSETS]
    return not asset_problems(decl, ROOT / "manifold_config_repo")


needs_assets = pytest.mark.skipif(not assets_present(), reason="the pinned SatSim assets are absent (external/assets/"
                                  "satsim; python scripts/bootstrap.py assets)")


@pytest.fixture
def library(tmp_path):
    """A library holding the probe configuration and, linked, the pinned assets (copied when they are tampered)."""
    if not assets_present():
        pytest.skip("the pinned SatSim assets are absent (external/assets/satsim; python scripts/bootstrap.py assets)")
    lib = tmp_path / "library"
    (lib / "satsim" / "probe").mkdir(parents=True)
    shutil.copy2(PROBE_CONFIG, lib / "satsim" / "probe" / "config.yaml")
    (lib / "satsim" / "assets").symlink_to(ASSET_STORE.resolve(), target_is_directory=True)
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


# --- assets ---------------------------------------------------------------------------------------------------------

def test_the_declared_assets_are_the_pinned_ones():
    pins = json.loads((ROOT / "external" / "pins.json").read_text())
    pinned = {p["library"]: p for p in pins.values() if p.get("kind") == "asset"}
    assert sorted(pinned) == sorted(a.ref["name"] for a in satsim_adapter.ASSETS)
    for a in satsim_adapter.ASSETS:
        pin = pinned[a.ref["name"]]
        assert a.ref["content_hash"] == "sha256:" + pin["sha256"] and pin["url"].startswith("https://")
        assert Path(pin["path"]).name == a.name                     # staged under its file name (skyfield's lookup)
    iers = pinned["satsim/assets/finals2000A.all"]
    assert iers["snapshot"] == "2026-10-11" and iers["last_measured"] == "2026-10-08"
    assert SatsimAdapter().fingerprint()["satsim"]["assets"] == {a.name: a.ref["content_hash"]
                                                                 for a in satsim_adapter.ASSETS}


@pytest.mark.parametrize("which", ["de421.bsp", "finals2000A.all"])
def test_an_absent_or_altered_asset_is_refused_naming_it(library, which):
    ref = file_ref(library)
    (library / "satsim" / "assets").unlink()
    (library / "satsim" / "assets").mkdir()
    for a in satsim_adapter.ASSETS:
        if a.name != which:
            (library / "satsim" / "assets" / a.name).symlink_to(ASSET_STORE.resolve() / a.name)
    _, mismatches, _ = _check(spec_for(ref), library)
    assert any(f"asset {which!r}" in m and "not found" in m for m in mismatches), mismatches
    (library / "satsim" / "assets" / which).write_bytes(b"not the pinned bytes")
    _, mismatches, _ = _check(spec_for(ref), library)
    assert any(f"asset {which!r}" in m and "does not match" in m for m in mismatches), mismatches


def _bootstrap():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bootstrap_under_test", ROOT / "scripts" / "bootstrap.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Served:
    def __init__(self, data):
        import io
        self.f = io.BytesIO(data)

    def __enter__(self):
        return self.f

    def __exit__(self, *a):
        return False


def test_bootstrap_verifies_and_fetches_a_pinned_asset_only_when_asked(tmp_path):
    """No network: the opener is a stand-in. Status reads only; a fetch keeps bytes that match the pin and discards
    others, naming the snapshot; an existing different file is never replaced."""
    bs = _bootstrap()
    data = b"ephemeris bytes"
    pin = {"kind": "asset", "path": "store/x.bsp", "library": "satsim/assets/x.bsp", "url": "https://example.invalid/x",
           "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"x": pin}))
    calls = []
    opener = lambda url: calls.append(url) or _Served(data)            # noqa: E731
    lines = []
    assert bs.assets(library=tmp_path / "lib", status_only=True, out=lines.append, pins_path=pins, root=tmp_path,
                     opener=opener) == 1
    assert lines == ["missing   store/x.bsp (x)"] and calls == []
    assert bs.assets(library=tmp_path / "lib", out=lines.append, pins_path=pins, root=tmp_path, opener=opener) == 0
    assert calls == ["https://example.invalid/x"] and (tmp_path / "store" / "x.bsp").read_bytes() == data
    assert oct((tmp_path / "store" / "x.bsp").stat().st_mode & 0o777) == "0o444"
    (tmp_path / "store" / "x.bsp").chmod(0o644)
    (tmp_path / "store" / "x.bsp").write_bytes(b"other")
    with pytest.raises(bs.AssetError, match="not replaced"):
        bs.fetch_pinned(pin, tmp_path, opener)
    (tmp_path / "store" / "x.bsp").unlink()
    snap = {**pin, "snapshot": "2026-10-11"}
    with pytest.raises(bs.AssetError, match="snapshot taken 2026-10-11"):
        bs.fetch_pinned(snap, tmp_path, lambda url: _Served(b"a newer table"))
    assert not (tmp_path / "store" / "x.bsp").exists() and not list((tmp_path / "store").glob(".*part"))


def test_bootstrap_status_and_install_skip_asset_pins(tmp_path):
    bs = _bootstrap()
    pins = {"a": {"kind": "asset", "path": "p", "library": "l", "url": "u", "sha256": "0" * 64, "size": 1}}
    assert bs.status(pins, external=tmp_path) == [] and bs.install(pins, external=tmp_path) == []


# --- launch plan and launcher ---------------------------------------------------------------------------------------

def test_the_plan_stages_the_configuration_and_isolates_the_process(library, tmp_path, monkeypatch):
    from manifold.core.engine import RunContext
    from manifold.sim.worker import command, environment
    monkeypatch.setenv("MANIFOLD_SATSIM_PYTHON", str(stub_python(tmp_path)))
    monkeypatch.setenv("PYTHONPATH", "/somewhere/sdk")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    spec = spec_for(file_ref(library), seed=7)
    plan = SatsimAdapter().plan(RunContext(run_dir, spec, library, None, run_dir / "output"))
    launch = json.loads((run_dir / "input" / "launch.json").read_text())
    assert launch == {"seed": 7, "set": "set", "input_dir": "input", "config": "input/config.yaml"}
    staged = run_dir / "input" / "config.yaml"
    assert staged.read_bytes() == (library / "satsim" / "probe" / "config.yaml").read_bytes()
    assert oct(staged.stat().st_mode & 0o777) == "0o444"
    argv = command(plan)
    assert argv[0] == str(tmp_path / "python-stub") and Path(argv[1]).name == "launcher.py" and argv[2] == str(run_dir)
    env = environment(plan, run_dir, threads=2)
    assert env["HOME"] == str(run_dir / "home") and "PYTHONPATH" not in env and env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert all(env[v] == "2" for v in satsim_adapter.THREAD_VARIABLES)
    assert all(v not in environment(plan, run_dir) or v in os.environ for v in satsim_adapter.THREAD_VARIABLES)
    assert plan.expected_outputs == ("satsim_result.json",)
    fp = SatsimAdapter().fingerprint()["satsim"]
    assert fp["launcher_sha256"] == hashlib.sha256(satsim_adapter.LAUNCHER.read_bytes()).hexdigest()


def test_the_plan_verifies_the_configuration_again(library, tmp_path, monkeypatch):
    from manifold.core.engine import RunContext
    from manifold.core.run_spec import RunSpecError
    monkeypatch.setenv("MANIFOLD_SATSIM_PYTHON", str(stub_python(tmp_path)))
    spec = spec_for(file_ref(library))
    (library / "satsim" / "probe" / "config.yaml").write_text("fpa: {}\n")          # changed after admission
    with pytest.raises(RunSpecError, match="does not match"):
        SatsimAdapter().plan(RunContext(tmp_path, spec, library, None, tmp_path / "output"))


GUARD = """
import json, runpy, socket, sys
from pathlib import Path
run_dir = Path(sys.argv[1])
sys.argv = ["launcher.py", str(run_dir)]
runpy.run_path(%r, run_name="launcher_under_test")
out = []
for call in (lambda: socket.create_connection(("example.invalid", 80)), lambda: socket.getaddrinfo("example.invalid", 80),
             lambda: socket.socket().connect(("127.0.0.1", 9))):
    try:
        call()
        out.append("connected")
    except OSError as e:
        out.append(str(e))
print(json.dumps(out))
"""


def test_the_launcher_refuses_every_connection_and_records_it(tmp_path):
    """The launcher's guard is installed when it is loaded, before anything else: run here with the SDK's interpreter
    and without its main (which needs SatSim)."""
    code = GUARD % str(satsim_adapter.LAUNCHER)
    res = subprocess.run([sys.executable, "-c", code, str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout.strip().splitlines()[-1])
    assert len(out) == 3 and all("network access refused" in m and "network slot is none" in m for m in out)
    assert len((tmp_path / "output" / "network_attempts.log").read_text().splitlines()) == 3


def test_the_launcher_reports_a_failure_with_its_traceback(tmp_path):
    """Without numpy-and-TensorFlow (the system interpreter) the launcher fails after reading its launch file: exit 1
    and a result naming the failure, with the traceback head."""
    system = Path("/usr/bin/python3")
    if not system.exists():
        pytest.skip("no /usr/bin/python3")
    (tmp_path / "input").mkdir()
    (tmp_path / "input" / "launch.json").write_text(json.dumps({"seed": 1, "set": "set", "input_dir": "input",
                                                               "config": "input/config.yaml"}))
    env = {"HOME": str(tmp_path / "home"), "PATH": "/usr/bin:/bin", "MANIFOLD_SATSIM_EPHEMERIS": str(tmp_path / "de421.bsp"),
           "MANIFOLD_SATSIM_IERS": str(tmp_path / "finals2000A.all")}
    res = subprocess.run([str(system), "-I", str(satsim_adapter.LAUNCHER), str(tmp_path)], capture_output=True, text=True,
                         env=env)
    result = json.loads((tmp_path / "output" / "satsim_result.json").read_text())
    if result.get("outcome") == "rendered":
        pytest.skip("the system interpreter has SatSim")
    assert res.returncode == 1 and result["outcome"] == "failed" and "Error" in result["message"]
    assert result["traceback_head"] and result["elapsed_s"] >= 0


def test_the_library_satsim_run_spec_is_admitted_with_its_recorded_id():
    if not assets_present():
        pytest.skip("the pinned SatSim assets are absent")
    spec = yaml.safe_load((ROOT / "manifold_run_specs" / "satsim" / "tahoe_worldview2.yaml").read_text())
    r = admission.validate_spec(spec, None, ROOT / "manifold_config_repo", ROOT / "manifold_sensors", registry=registry())
    assert r.valid and r.unstamped == [], (r.schema_errors, r.resolution_mismatches)
    assert r.run_id == "81fe69a103a32acdc8a1015e36724faa9d3ed8152488806dbd8a93f24adc5a3d"
    probe = [ln for ln in PROBE_CONFIG.read_text().splitlines() if not ln.startswith("#")]
    lib = [ln for ln in (ROOT / "manifold_config_repo" / "satsim" / "tahoe_worldview2.yaml").read_text().splitlines()
           if not ln.startswith("#")]
    assert lib == probe                                               # the probe's sample, promoted unchanged


# --- collection: roles and verdicts on synthetic set folders --------------------------------------------------------

def _fits(path, rows=4, cols=6):
    cards = ["SIMPLE  =                    T", "BITPIX  =                   16", "NAXIS   =                    2",
             f"NAXIS1  = {cols:20d}", f"NAXIS2  = {rows:20d}", "END"]
    header = "".join(c.ljust(80) for c in cards).ljust(2880).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + bytes(2880))


def _set_folder(run_dir, frames=3, written=3, end=True, movie=True, czml=True, name="set"):
    out = run_dir / "output"
    folder = out / name
    (run_dir / "input").mkdir(parents=True, exist_ok=True)
    (run_dir / "input" / "launch.json").write_text(json.dumps({"seed": 3, "set": "set", "input_dir": "input",
                                                              "config": "input/config.yaml"}))
    folder.mkdir(parents=True)
    (folder / "config.json").write_text(json.dumps({"fpa": {"num_frames": frames}, "sim": {}, "_input_dir": "input"}))
    for i in range(written):
        _fits(folder / "ImageFiles" / f"{name}.{i:04d}.fits")
        (folder / "Annotations").mkdir(exist_ok=True)
        (folder / "Annotations" / f"{name}.{i:04d}.json").write_text("{}")
        (folder / "AnnotatedImages").mkdir(exist_ok=True)
        (folder / "AnnotatedImages" / f"{name}.{i:04d}.jpg").write_bytes(b"jpg")
    if end:
        for k in range(1, 8):
            (folder / f"config_pass_{k}.json").write_text("{}")
    if movie:
        (folder / "AnnotatedImages").mkdir(exist_ok=True)
        (folder / "AnnotatedImages" / "movie.png").write_bytes(b"png")
    if czml:
        (folder / "satsim.czml").write_text("[]")
    (run_dir / "worker.log").write_text("running\n")
    return out


def _result(out, **doc):
    (out / "satsim_result.json").write_text(json.dumps({"outcome": "rendered", "seed": 3, "versions": {"satsim": "x"},
                                                        "elapsed_s": 4.2, **doc}))


def test_a_complete_set_is_complete_with_its_roles_and_metadata(tmp_path):
    out = _set_folder(tmp_path)
    _result(out)
    c = SatsimAdapter().collect(out, tmp_path)
    assert c.verdict == "complete" and c.message is None
    roles = {a.name: (a.role, a.frame) for a in c.artifacts}
    assert roles["ImageFiles_set.0001.fits"] == ("product", 1) and roles["Annotations_set.0002.json"] == ("truth", 2)
    assert roles["AnnotatedImages_set.0000.jpg"] == ("preview", 0) and roles["AnnotatedImages_movie.png"] == ("preview", None)
    assert roles["satsim.czml"] == ("metadata", None) and roles["config.json"] == ("config", None)
    assert roles["config_pass_7.json"] == ("config", None) and roles["worker.log"] == ("log", None)
    assert roles["satsim_result.json"] == ("metadata", None)
    assert (out / "worker.log").read_text() == "running\n"                 # the worker log, copied at collection
    md = c.record["engine_metadata"]
    assert md == {"set_folder": "set", "frames": 3, "frames_expected": 3, "image_size": [4, 6], "seed": 3,
                  "versions": {"satsim": "x"}, "elapsed_s": 4.2}


def test_frames_without_the_end_of_run_files_are_incomplete(tmp_path):
    out = _set_folder(tmp_path, frames=40, written=30, end=False, movie=False, czml=False)
    c = SatsimAdapter().collect(out, tmp_path)                             # stopped by a signal: no launcher result
    assert c.verdict == "incomplete" and "30 of 40 frames written" in c.message
    assert "missing config_pass_*.json, AnnotatedImages/movie.png, satsim.czml" in c.message
    assert sum(a.role == "product" for a in c.artifacts) == 30


def test_a_reported_success_with_a_missing_frame_is_incomplete(tmp_path):
    out = _set_folder(tmp_path, frames=3, written=2)
    _result(out)
    c = SatsimAdapter().collect(out, tmp_path)
    assert c.verdict == "incomplete" and "2 of 3 frames" in c.message


def test_a_failure_is_failed_with_the_traceback_head(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    _result(out, outcome="failed", message="KeyError: 'time'", traceback_head=["Traceback ...", "KeyError: 'time'"],
            elapsed_s=3.1)
    c = SatsimAdapter().collect(out, tmp_path)
    assert c.verdict == "failed" and c.message == "SatSim failed: KeyError: 'time'"
    assert c.record["engine_metadata"]["traceback_head"][-1] == "KeyError: 'time'"
    assert c.record["engine_metadata"]["elapsed_s"] == 3.1


def test_a_wall_clock_set_folder_is_accepted_and_named(tmp_path):
    out = _set_folder(tmp_path, name="2026-10-11T20-52-28.123456")
    (tmp_path / "input" / "launch.json").unlink()
    _result(out)
    c = SatsimAdapter().collect(out, tmp_path)
    assert c.verdict == "complete" and c.record["engine_metadata"]["set_folder"] == "2026-10-11T20-52-28.123456"
    assert "ImageFiles_2026-10-11T20-52-28.123456.0000.fits" in {a.name for a in c.artifacts}


def test_a_network_attempt_is_listed_and_counted(tmp_path):
    out = _set_folder(tmp_path)
    _result(out)
    (out / "network_attempts.log").write_text("1 ('example.invalid', 80)\n")
    c = SatsimAdapter().collect(out, tmp_path)
    assert c.record["engine_metadata"]["network_attempts"] == 1
    assert ("network_attempts.log", "log") in {(a.name, a.role) for a in c.artifacts}


def test_the_launcher_fails_at_once_when_an_asset_is_not_staged(tmp_path):
    (tmp_path / "input").mkdir()
    (tmp_path / "input" / "launch.json").write_text(json.dumps({"seed": 1, "set": "set", "input_dir": "input",
                                                               "config": "input/config.yaml"}))
    env = {"HOME": str(tmp_path / "home"), "PATH": "/usr/bin:/bin"}
    res = subprocess.run([sys.executable, "-I", str(satsim_adapter.LAUNCHER), str(tmp_path)], capture_output=True,
                         text=True, env=env)
    result = json.loads((tmp_path / "output" / "satsim_result.json").read_text())
    assert res.returncode == 1 and "asset 'de421.bsp' is not staged" in result["message"]
    assert not (tmp_path / "output" / "network_attempts.log").exists()


def test_the_worker_rebuilds_the_satsim_adapter_the_backend_admitted_with():
    from manifold.sim.worker import EngineSetMismatch, engine_set
    reg = registry()
    reg.find("satsim")                                                    # loaded, as admission loads it
    described = reg.describe()
    assert described[0]["target"] == "manifold.engines.satsim.adapter:SatsimAdapter" and described[0]["loaded"]
    assert engine_set({"engines": described}).describe() == described
    with pytest.raises(EngineSetMismatch, match="'satsim'"):
        engine_set({"engines": [{**described[0], "adapter_version": "9.9.9"}]})
