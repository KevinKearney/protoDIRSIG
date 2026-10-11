"""Acceptance: an engine is added by installing a distribution, with no change to `manifold.core` or `manifold.sim`.

The dummy engine (`tests/fixtures/engine_dummy/`, its own distribution `eoptic-manifold-engine-dummy`, namespace
`manifold.engines.dummy`) is "installed" by building a throwaway site folder: the package copied, plus an
`eoptic_manifold_engine_dummy-0.0.1.dist-info` holding its metadata and its `manifold.engines` entry point. Every check
runs in a subprocess with that folder on `PYTHONPATH` (inherited by the worker and the engine processes), so this
suite's own process never imports the fixture and its registry is untouched; "uninstalling" is running without it.

Installed, a dummy recipe composes, validates (its schema, its semantic rule and its resource declaration applied), is
admitted, executes through `LocalBackend` in another interpreter (`/usr/bin/python3`) with its declared asset staged
read-only and its granted thread count in its environment, is listed by `list_engines`, is cancellable (SIGTERM
mid-run, after which its collector says `incomplete`), and the unmodified `tests/backend_conformance.py` suite (through
`tests/test_local_backend.py`) still passes. Uninstalled, `list_engines` lists DIRSIG exactly as before and no dummy,
and a dummy run spec is refused as an unregistered engine. A backend given a registry holding only the dummy runs with
that set alone while discovery finds DIRSIG too.

The folder install is the fast path. The real one is `test_the_dummy_installed_from_its_wheel_...`: the fixture is
built into a wheel offline (`pip wheel --no-build-isolation --no-index`), installed with `pip install --no-index
--no-deps` into a throwaway virtual environment layered on this one (`--system-site-packages`), and discovery, one run
and `pip uninstall` are checked in a subprocess under that environment's interpreter.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "engine_dummy"
SYSTEM_PYTHON = Path("/usr/bin/python3")

pytestmark = pytest.mark.skipif(not SYSTEM_PYTHON.exists(), reason="no system interpreter at /usr/bin/python3")


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    """The installed dummy: its package and a `.dist-info` with the entry point, in a folder put on PYTHONPATH."""
    site = tmp_path_factory.mktemp("dummy_site")
    shutil.copytree(FIXTURE / "src" / "manifold" / "engines" / "dummy", site / "manifold" / "engines" / "dummy",
                    ignore=shutil.ignore_patterns("__pycache__"))
    info = site / "eoptic_manifold_engine_dummy-0.0.1.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: eoptic-manifold-engine-dummy\nVersion: 0.0.1\n"
                                   "Requires-Dist: eoptic-manifold-core==0.0.1\n")
    (info / "entry_points.txt").write_text("[manifold.engines]\ndummy = manifold.engines.dummy.adapter:DummyAdapter\n")
    (info / "top_level.txt").write_text("manifold\n")
    assert not (site / "manifold" / "__init__.py").exists() and not (site / "manifold" / "engines" / "__init__.py").exists()
    return site


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    """A layer root with two dummy recipes, the sensor they name, and an engine-asset library holding the asset."""
    top = tmp_path_factory.mktemp("dummy_library")
    layers = top / "manifold_run_specs"
    for d in ("recipes", "scenarios", "engine_profiles"):
        (layers / d).mkdir(parents=True)
    (top / "manifold_sensors").mkdir()
    shutil.copy2(ROOT / "manifold_sensors" / "auror-nir.yaml", top / "manifold_sensors")
    shutil.copy2(ROOT / "manifold_run_specs" / "scenarios" / "tahoe_static_pose.yaml", layers / "scenarios")
    recipe = yaml.safe_load((ROOT / "manifold_run_specs" / "recipes" / "auror_ref.yaml").read_text())
    recipe.pop("engine_overrides")
    for name, engine in (("dummy_quick", {"steps": 3, "sleep_s": 0.05, "label": "quick"}),
                         ("dummy_slow", {"steps": 40, "sleep_s": 0.5, "label": "slow"}),
                         ("dummy_fails", {"steps": 2, "fail": True}),
                         ("dummy_bad_label", {"steps": 1, "label": "two words"})):
        doc = dict(recipe, meta=dict(recipe["meta"], name=name.replace("_", "-")), engine_profile=name)
        (layers / "recipes" / f"{name}.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
        profile = {"origin": {"kind": "synthetic", "engine": "dummy"}, "engine": engine,
                   "resources": {"cpu_threads": 2, "memory_bytes": 1 << 20}}
        (layers / "engine_profiles" / f"{name}.yaml").write_text(yaml.safe_dump(profile, sort_keys=False))
    assets = top / "assets"
    (assets / "dummy").mkdir(parents=True)
    (assets / "dummy" / "table.txt").write_bytes(_table_bytes())
    return top


def _table_bytes():
    """The asset's bytes as the adapter declares them, read from its source (the fixture is never imported here)."""
    import ast
    tree = ast.parse((FIXTURE / "src" / "manifold" / "engines" / "dummy" / "adapter.py").read_text())
    (node,) = [n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "TABLE_BYTES"]
    return ast.literal_eval(node.value)


def test_no_other_test_module_imports_the_fixture():
    me = Path(__file__).name
    for p in sorted((ROOT / "tests").glob("*.py")):
        if p.name != me:
            text = p.read_text()
            assert "engines.dummy" not in text and "engine_dummy" not in text, p.name


def _run(code, site=None, timeout=300):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["MANIFOLD_DUMMY_PYTHON"] = str(SYSTEM_PYTHON)
    if site is not None:
        env["PYTHONPATH"] = str(site)
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=timeout,
                         cwd=ROOT)
    assert res.returncode == 0, res.stderr[-3000:]
    return json.loads(res.stdout.strip().splitlines()[-1])


ACCEPT = """
import json, sys, time
from pathlib import Path
import manifold.sim
from manifold.core.compose import compose_sweep
from manifold.core.errors import AdmissionError
from manifold.sim import engines
from manifold.sim.backend import LocalBackend
from backend_conformance import wait_for
top = Path(sys.argv[1]) if len(sys.argv) > 1 else Path({top!r})
b = LocalBackend(top / "work", top / "assets", library=top / "manifold_run_specs")
out = {{"engines": b.list_engines()["items"]}}
sweep = compose_sweep(top / "manifold_run_specs" / "recipes" / "dummy_quick.yaml")
(spec,) = sweep.runs.values()
out["origin"] = spec["descriptor"]["origin"]
out["validate"] = b.validate("dummy_quick")["runs"][0]
out["bad_label"] = b.validate("dummy_bad_label")["runs"][0]
final = wait_for(b, b.submit_run("dummy_quick")["run_id"], ("rendered", "failed", "cancelled"), timeout=120)
run_dir = b.store.run_dir(final["run_id"])
out["final"] = final
out["record"] = b.store.read_record(final["run_id"])
out["frame0"] = json.loads((run_dir / "output" / "frame-00.txt").read_text())
out["staged_mode"] = oct((run_dir / "assets" / "table").stat().st_mode & 0o777)
failed = wait_for(b, b.submit_run("dummy_fails")["run_id"], ("rendered", "failed", "cancelled"), timeout=120)
out["failed"] = failed
slow = b.submit_run("dummy_slow")["run_id"]
slow_dir = b.store.run_dir(slow)
deadline = time.monotonic() + 60
while not list((slow_dir / "output").glob("frame-*.txt")) and time.monotonic() < deadline:
    time.sleep(0.2)
out["cancel"] = b.cancel_run(slow)["state"]
time.sleep(1.0)
c = engines.registry().get("dummy").collect(slow_dir / "output", slow_dir)
out["after_cancel"] = {{"verdict": c.verdict, "message": c.message, "roles": sorted({{a.role for a in c.artifacts}})}}
print(json.dumps(out, default=str))
"""


def test_the_installed_dummy_engine_runs_end_to_end(site, library):
    code = "import sys; sys.path.insert(0, 'tests')\n" + ACCEPT.format(top=str(library))
    got = _run(code, site)
    ids = [e["engine_id"] for e in got["engines"]]
    assert ids == ["dirsig", "dummy"]
    (dummy,) = [e for e in got["engines"] if e["engine_id"] == "dummy"]
    assert dummy["available"] and dummy["modes"] == ["layered"] and dummy["contracts"] == ["dummy-engine/1"]
    assert dummy["resources"]["cpu_threads"]["maximum"] == 2 and dummy["assets"][0]["name"] == "table"
    assert "eoptic-manifold-engine-dummy 0.0.1" in dummy["source"]
    assert got["origin"] == {"kind": "synthetic", "engine": "dummy"}
    assert got["validate"]["valid"], got["validate"]
    assert not got["bad_label"]["valid"] and "contains whitespace" in json.dumps(got["bad_label"])
    final, rec = got["final"], got["record"]
    assert final["state"] == "rendered", final["errors"]
    names = [a["name"] for a in final["artifacts"]]
    assert names == ["run_spec.json", "frame-00.txt", "frame-01.txt", "frame-02.txt", "dummy.log"]
    assert [a.get("frame") for a in final["artifacts"]] == [None, 0, 1, 2, None]
    assert rec["artifact_roles"] == {"run_spec.json": "config", "frame-00.txt": "product", "frame-01.txt": "product",
                                     "frame-02.txt": "product", "dummy.log": "log"}
    assert rec["adapter"]["engine_id"] == "dummy" and rec["dummy"]["interpreter"] == str(SYSTEM_PYTHON)
    assert rec["resources"]["granted"]["cpu_threads"] == 2 and rec["assets"][0]["staged"] == "assets/table"
    frame = got["frame0"]
    assert frame["interpreter"] != sys.executable and Path(frame["interpreter"]).resolve() == SYSTEM_PYTHON.resolve()
    assert frame["threads"] == "2" and frame["table"] == "dummy table v1" and frame["label"] == "quick"
    assert got["staged_mode"] == "0o444"
    failed = got["failed"]
    assert failed["state"] == "failed" and "end-of-run marker" in failed["errors"][0]["detail"] \
        and "exit status 3" in failed["errors"][0]["detail"]
    assert got["cancel"] == "cancelled"
    assert got["after_cancel"]["verdict"] == "incomplete" and "end-of-run marker" in got["after_cancel"]["message"]
    assert got["after_cancel"]["roles"] == ["log", "product"]


LIST = """
import json, sys
sys.path.insert(0, 'tests')
import manifold.sim
from manifold.core.compose import compose_sweep
from manifold.sim.backend import LocalBackend
from pathlib import Path
top = Path({top!r})
b = LocalBackend(top / "work_list", top / "assets", library=top / "manifold_run_specs")
v = b.validate("dummy_quick")["runs"][0]
print(json.dumps({{"engines": b.list_engines()["items"], "valid": v["valid"], "checks": v["checks"]}}))
"""


def test_uninstalling_removes_only_the_dummy(site, library):
    with_dummy = _run(LIST.format(top=str(library)), site)
    without = _run(LIST.format(top=str(library)))
    assert [e["engine_id"] for e in without["engines"]] == ["dirsig"]
    assert without["engines"] == [e for e in with_dummy["engines"] if e["engine_id"] == "dirsig"]
    assert with_dummy["valid"] and not without["valid"]
    assert "'dummy' is not a registered engine; registered engines: dirsig" in json.dumps(without["checks"])


def test_the_backend_conformance_suite_passes_with_the_dummy_installed(site):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.update(PYTHONPATH=str(site), MANIFOLD_DUMMY_PYTHON=str(SYSTEM_PYTHON))
    res = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_local_backend.py"],
                         capture_output=True, text=True, env=env, cwd=ROOT, timeout=900)
    assert res.returncode == 0, res.stdout[-3000:]
    probe = subprocess.run([sys.executable, "-c", "import manifold.sim\nfrom manifold.sim import engines\n"
                            "print(engines.registry().ids())"], capture_output=True, text=True, env=env, cwd=ROOT)
    assert "dummy" in probe.stdout                                   # the suite ran with the dummy registered


ONLY_DUMMY = """
import json, sys
sys.path.insert(0, 'tests')
import manifold.sim
from pathlib import Path
from manifold.core.engine import Registry
from manifold.sim import engines
from manifold.sim.backend import LocalBackend
from backend_conformance import wait_for
top = Path({top!r})
reg = Registry()
reg.register("dummy", engines.load_target("manifold.engines.dummy.adapter:DummyAdapter"))
b = LocalBackend(top / "work_only", top / "assets", library=top / "manifold_run_specs", registry=reg)
final = wait_for(b, b.submit_run("dummy_quick")["run_id"], ("rendered", "failed"), timeout=120)
job = json.loads((b.store.run_dir(final["run_id"]) / "job.json").read_text())
print(json.dumps({{"discovered": engines.registry().ids(), "listed": [e["engine_id"] for e in b.list_engines()["items"]],
                  "state": final["state"], "errors": final["errors"], "job_engines": [e["engine_id"] for e in job["engines"]]}}))
"""


def test_a_backend_given_a_custom_registry_runs_with_exactly_that_engine_set(site, library):
    """Discovery finds DIRSIG and the dummy; a backend given a registry holding only the dummy lists, admits and runs
    with that set alone, and its worker rebuilds the same set from job.json rather than discovering."""
    got = _run(ONLY_DUMMY.format(top=str(library)), site)
    assert got["discovered"] == ["dirsig", "dummy"]
    assert got["listed"] == ["dummy"] and got["job_engines"] == ["dummy"]
    assert got["state"] == "rendered", got["errors"]


@pytest.fixture(scope="module")
def venv_with_wheel(tmp_path_factory):
    """The dummy built as a wheel offline and installed with pip into a fresh virtual environment layered on this one
    (`--system-site-packages`, so the SDK is the environment's own), with no index and no dependency resolution."""
    src = tmp_path_factory.mktemp("dummy_src") / "engine_dummy"
    shutil.copytree(FIXTURE, src, ignore=shutil.ignore_patterns("__pycache__", "build", "*.egg-info"))
    out = tmp_path_factory.mktemp("dummy_wheel")
    r = subprocess.run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "--no-index",
                        "-w", str(out)], cwd=src, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        pytest.skip(f"the dummy wheel cannot be built offline here: {(r.stderr or r.stdout).strip().splitlines()[-1:]}")
    (whl,) = out.glob("eoptic_manifold_engine_dummy-*.whl")
    venv = tmp_path_factory.mktemp("dummy_venv") / "venv"
    r = subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", "--without-pip", str(venv)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        pytest.skip(f"a virtual environment cannot be created here: {(r.stderr or r.stdout).strip().splitlines()[-1:]}")
    python = venv / "bin" / "python"
    r = subprocess.run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(whl)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    return python, whl


WHEEL_RUN = """
import json, sys
sys.path.insert(0, 'tests')
import manifold.sim
from pathlib import Path
from manifold.sim import engines
from manifold.sim.backend import LocalBackend
from backend_conformance import wait_for
import manifold.engines.dummy.adapter as dummy
top = Path({top!r})
b = LocalBackend(top / "work_wheel", top / "assets", library=top / "manifold_run_specs")
listed = {{e["engine_id"]: e for e in b.list_engines()["items"]}}
final = wait_for(b, b.submit_run("dummy_quick")["run_id"], ("rendered", "failed"), timeout=120)
print(json.dumps({{"prefix": sys.prefix, "dummy_file": dummy.__file__, "ids": sorted(listed),
                  "source": listed["dummy"]["source"], "state": final["state"], "errors": final["errors"],
                  "roles": sorted({{a["role"] for a in final["artifacts"]}})}}))
"""

WHEEL_LIST = """
import json, sys
import manifold.sim
from manifold.sim import engines
print(json.dumps({"prefix": sys.prefix, "ids": engines.registry().ids()}))
"""


def _in_venv(python, code):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["MANIFOLD_DUMMY_PYTHON"] = str(SYSTEM_PYTHON)
    res = subprocess.run([str(python), "-c", code], capture_output=True, text=True, env=env, timeout=300, cwd=ROOT)
    assert res.returncode == 0, res.stderr[-3000:]
    return json.loads(res.stdout.strip().splitlines()[-1])


def test_the_dummy_installed_from_its_wheel_is_discovered_runs_and_uninstalls(venv_with_wheel, library):
    """A real install, not a folder on PYTHONPATH: pip puts the wheel's files and `.dist-info` (with its entry point)
    into the virtual environment's site-packages; discovery finds it there, a run renders, and after `pip uninstall`
    discovery finds DIRSIG alone. The folder tests above stay the fast path."""
    python, whl = venv_with_wheel
    venv = python.parent.parent
    got = _in_venv(python, WHEEL_RUN.format(top=str(library)))
    assert Path(got["prefix"]) == venv and Path(got["dummy_file"]).is_relative_to(venv)
    assert got["ids"] == ["dirsig", "dummy"] and "eoptic-manifold-engine-dummy 0.0.1" in got["source"]
    assert got["state"] == "rendered", got["errors"]
    assert got["roles"] == ["config", "log", "product"]
    r = subprocess.run([str(python), "-m", "pip", "uninstall", "-y", "eoptic-manifold-engine-dummy"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    after = _in_venv(python, WHEEL_LIST)
    assert after["ids"] == ["dirsig"]
    assert not list((venv / "lib").glob("python*/site-packages/manifold/engines/dummy"))
