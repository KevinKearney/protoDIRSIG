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
PURE = ["protodirsig.compose", "protodirsig.run_spec", "protodirsig.orbit", "protodirsig.contract", "protodirsig.identity",
        "protodirsig.dirhash", "protodirsig.problems", "protodirsig.errors", "protodirsig.admission",
        "protodirsig.store", "protodirsig.backend", "protodirsig.library",
        "protodirsig.models", "protodirsig.workspace"]
DIRFM_BOUND = {"protodirsig.registry", "protodirsig.simulation", "protodirsig.worker"}   # worker: the engine side of LocalBackend


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
from protodirsig.compose import compose
from protodirsig.run_spec import load_sensor_spec, RunSpecError
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
    specs = sorted(str(p) for p in (ROOT / "manifold_run_specs").glob("*.yaml")
                   if "does not validate yet" not in recipe_header(p))      # placed demos: findings, not runs
    code = BLOCKED + f"""
import json, yaml
from pathlib import Path
from protodirsig import identity
from protodirsig.admission import validate_spec
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
    assert got["engine"] == [] and len(got["runs"]) == len(specs) == 6
    for name, (valid, checked, unstamped, same_id, errors) in got["runs"].items():
        assert (valid, checked, unstamped, same_id) == (True, False, [], True), (name, errors)


def test_importing_the_package_loads_no_engine_package():
    """`import protodirsig` and its `Workspace` load none of dirfm, skyfield, sgp4."""
    code = ("import json, sys, protodirsig\n"
            "light = sorted({m.split('.')[0] for m in sys.modules})\n"
            "protodirsig.Workspace\n"
            "print(json.dumps([light, sorted({m.split('.')[0] for m in sys.modules})]))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    light, with_workspace = (set(x) for x in json.loads(out))
    assert light.isdisjoint(ENGINE + PROPAGATOR) and with_workspace.isdisjoint(ENGINE + PROPAGATOR)
    assert "lxml" not in light and "numpy" not in light                  # the package import itself is light
