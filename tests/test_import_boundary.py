"""The import boundary: composing, loading and resolving a run spec loads no engine package; `orbit` loads none at
import. Each check runs in a fresh interpreter, so modules imported by other tests do not count.

`registry` and `simulation` remain engine-bound: `simulation` assembles and runs the DIRSIG job through dirfm, and
`registry` imports `Simulation`. Phase 2b separates the local backend from the engine; until then they are the
recorded bound set, and a guard test fails when one of them stops loading dirfm, so the list shrinks deliberately.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROPAGATOR = ("skyfield", "sgp4")
ENGINE = ("dirfm",)
PURE = ["manifold.core.compose", "manifold.core.run_spec", "manifold.core.orbit", "manifold.core.contract", "manifold.core.identity",
        "manifold.core.dirhash", "manifold.core.problems", "manifold.core.errors", "manifold.core.admission",
        "manifold.sim.store", "manifold.sim.backend", "manifold.sim.library",
        "manifold.core.models", "manifold.sim.workspace",
        "manifold.engines.dirsig.passthrough", "manifold.sim.worker"]
DIRFM_BOUND = {"manifold.engines.dirsig.registry", "manifold.engines.dirsig.simulation"}


def _loaded(module):
    code = (f"import json, sys, {module}\n"
            f"print(json.dumps(sorted({{m.split('.')[0] for m in sys.modules}})))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    return set(json.loads(out))


@pytest.mark.parametrize("module", PURE + sorted(DIRFM_BOUND))
def test_module_does_not_load_the_propagator(module):
    assert _loaded(module).isdisjoint(PROPAGATOR)


@pytest.mark.parametrize("module", PURE)
def test_module_does_not_load_the_engine_package(module):
    assert _loaded(module).isdisjoint(ENGINE)


def test_the_engine_bound_set_is_as_recorded():
    """If one of these stops loading dirfm, move it to PURE and shrink DIRFM_BOUND."""
    assert {m for m in DIRFM_BOUND if "dirfm" in _loaded(m)} == DIRFM_BOUND


BLOCKED = """
import sys
class Block:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in ("dirfm", "skyfield", "sgp4"):
            raise ImportError(f"blocked: {name}")
sys.meta_path.insert(0, Block())
"""


def test_compose_runs_with_the_engine_packages_unimportable():
    """Composition needs no engine package: dirfm, skyfield and sgp4 raise on import, and compose still completes."""
    recipe = ROOT / "manifold_run_specs" / "recipes" / "auror_ref.yaml"
    code = BLOCKED + f"""
import json
try:
    import dirfm
    raise SystemExit("dirfm imported despite the block")
except ImportError:
    pass
import manifold.sim
from manifold.core.compose import compose
from manifold.core.run_spec import load_sensor_spec, RunSpecError
spec = compose({str(recipe)!r})
print(json.dumps({{"name": spec["descriptor"]["meta"]["name"], "engine": "dirfm" in sys.modules}}))
"""
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout) == {"name": "auror-ref-static-pose", "engine": False}


def test_engine_free_validation_runs_with_the_engine_packages_unimportable():
    """admission.validate_spec completes on every generated run spec with dirfm, skyfield and sgp4 unimportable: valid,
    not engine-checked, nothing unstamped, and the run id identity gives."""
    def recipe_header(spec):                      # the generated header names the recipe the spec came from
        recipe = spec.read_text().splitlines()[0].split(" from ", 1)[1].split(" - ", 1)[0]
        return (ROOT / "manifold_run_specs" / recipe).read_text().split("\n\n", 1)[0]
    def directory_present(spec):                  # a pass-through spec needs its demo directory placed (bootstrap)
        doc = __import__("yaml").safe_load(spec.read_text())
        block = (doc.get("engine") or {}).get("passthrough")
        return block is None or (ROOT / "manifold_config_repo" / block["directory"]["name"]).is_dir()
    specs = sorted(str(p) for p in (ROOT / "manifold_run_specs").glob("*.yaml")
                   if "does not validate yet" not in recipe_header(p) and directory_present(p))
    code = BLOCKED + f"""
import json, yaml
from pathlib import Path
import manifold.sim
from manifold.core import identity
from manifold.core.admission import validate_spec
out = {{}}
for p in {specs!r}:
    spec = yaml.safe_load(Path(p).read_text())
    r = validate_spec(spec, p, {str(ROOT / "manifold_config_repo")!r})
    out[Path(p).name] = [r.valid, r.engine_checked, r.unstamped, r.run_id == identity.run_id(spec, {str(ROOT / "manifold_sensors")!r}),
                         r.schema_errors + r.resolution_mismatches]
print(json.dumps({{"runs": out, "engine": sorted(m for m in ("dirfm", "skyfield", "sgp4") if m in sys.modules)}}))
"""
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    got = json.loads(res.stdout)
    assert got["engine"] == [] and len(got["runs"]) == len(specs) >= 6
    for name, (valid, checked, unstamped, same_id, errors) in got["runs"].items():
        assert (valid, checked, unstamped, same_id) == (True, False, [], True), (name, errors)


def test_importing_the_package_loads_no_engine_package():
    """`import manifold.sim` and its `Workspace` load none of dirfm, skyfield, sgp4."""
    code = ("import json, sys, manifold.sim\n"
            "light = sorted({m.split('.')[0] for m in sys.modules})\n"
            "manifold.sim.Workspace\n"
            "print(json.dumps([light, sorted({m.split('.')[0] for m in sys.modules})]))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    light, with_workspace = (set(x) for x in json.loads(out))
    assert light.isdisjoint(ENGINE + PROPAGATOR) and with_workspace.isdisjoint(ENGINE + PROPAGATOR)
    assert "lxml" not in light and "numpy" not in light                  # the package import itself is light


CORE = sorted(f"manifold.core.{p.stem}" for p in (ROOT / "packages" / "core" / "src" / "manifold" / "core").glob("*.py")
              if p.stem != "__init__") + ["manifold.core"]


def _loaded_names(module):
    code = (f"import json, sys, {module}\n"
            f"print(json.dumps(sorted(sys.modules)))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    return set(json.loads(out))


@pytest.mark.parametrize("module", CORE)
def test_core_imports_nothing_from_sim_no_engine_and_no_numpy(module):
    """`manifold.core` is engine-neutral: importing any of its modules loads no `manifold.sim` module, no engine package
    (`dirfm`, `manifold.engines`), no propagator and no numpy."""
    names = _loaded_names(module)
    assert not {n for n in names if n == "manifold.sim" or n.startswith(("manifold.sim.", "manifold.engines"))}
    assert {n.split(".")[0] for n in names}.isdisjoint(ENGINE + PROPAGATOR + ("numpy",))


def test_the_pure_list_covers_every_core_module():
    """Every core module is in PURE or is a helper whose purity the test above checks."""
    assert {m for m in CORE if m != "manifold.core"} >= {m for m in PURE if m.startswith("manifold.core.")}


def test_no_distribution_ships_the_namespace_init():
    """`manifold` and `manifold.engines` are PEP 420 namespaces: no source tree under packages/ has their `__init__.py`."""
    for dist in (ROOT / "packages").iterdir():
        assert not (dist / "src" / "manifold" / "__init__.py").exists(), dist.name
        assert not (dist / "src" / "manifold" / "engines" / "__init__.py").exists(), dist.name
    import manifold
    assert getattr(manifold, "__file__", None) is None and len(list(manifold.__path__)) >= 2


def test_without_dirfm_the_sdk_imports_and_lists_dirsig_unavailable(tmp_path):
    """dirfm made unimportable by a meta-path blocker: `manifold.core` and `manifold.sim` import, `list_engines` lists
    dirsig as unavailable with the reason, validation still runs engine-free, and a submission is refused at admission."""
    code = BLOCKED.replace('("dirfm", "skyfield", "sgp4")', '("dirfm",)') + f"""
import json
import manifold.core, manifold.sim
from manifold.sim.backend import LocalBackend
from manifold.core.errors import AdmissionError
b = LocalBackend({str(tmp_path / "work")!r}, {str(ROOT / "manifold_config_repo")!r})
items = b.list_engines()["items"]
valid = b.validate({str(ROOT / "manifold_run_specs" / "auror_ref.yaml")!r})["runs"][0]["valid"]
try:
    b.submit_run({str(ROOT / "manifold_run_specs" / "auror_ref.yaml")!r})
    refused = None
except AdmissionError as e:
    refused = e.problem["detail"]
print(json.dumps({{"items": items, "valid": valid, "refused": refused, "dirfm": "dirfm" in sys.modules}}))
"""
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    got = json.loads(res.stdout)
    (dirsig,) = [e for e in got["items"] if e["engine_id"] == "dirsig"]
    assert dirsig["available"] is False and "dirfm" in dirsig["reason"]
    assert got["valid"] is True and got["dirfm"] is False
    assert got["refused"] and "unavailable" in got["refused"] and "dirfm" in got["refused"]
