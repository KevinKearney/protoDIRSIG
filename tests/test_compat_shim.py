"""The deprecated `protodirsig` compatibility shim (`packages/compat-protodirsig`): every public name that was importable
from `protodirsig` and its submodules before the rename still is, as the same object from `manifold.core` or
`manifold.sim`, and importing the shim warns exactly once. The former names are recorded in
`tests/data/protodirsig_public_names.json` (from the last commit before the rename)."""
import importlib
import json
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORMER = json.loads((ROOT / "tests" / "data" / "protodirsig_public_names.json").read_text())["modules"]
PAIRS = [(m, n) for m in sorted(FORMER) for n in FORMER[m]]

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import protodirsig


def _former(module):
    return protodirsig if module == "__init__" else importlib.import_module(f"protodirsig.{module}")


@pytest.mark.parametrize("module, name", PAIRS, ids=[f"{m}.{n}" for m, n in PAIRS])
def test_every_former_public_name_is_importable(module, name):
    assert hasattr(_former(module), name)


@pytest.mark.parametrize("module", sorted(m for m in FORMER if m != "__init__"))
def test_a_former_submodule_is_the_replacing_module_itself(module):
    new = importlib.import_module(protodirsig.MODULES[module])
    assert _former(module) is new and getattr(protodirsig, module) is new
    assert new.__spec__.name == new.__name__ == protodirsig.MODULES[module]        # its spec is not overwritten


def test_the_table_covers_every_former_submodule_and_nothing_else():
    assert set(protodirsig.MODULES) == set(FORMER) - {"__init__"}


def test_the_former_package_names_and_the_auror_era_aliases():
    from manifold.engines.dirsig import run_spec
    from manifold.sim import Workspace
    from manifold.engines.dirsig.registry import LocalRegistry
    from manifold.engines.dirsig.simulation import Simulation
    from protodirsig import LocalRegistry as old_registry, Workspace as old_workspace
    from protodirsig.run_spec import AUROR_ATMOSPHERE_BACKEND, AurorRun, resolve_auror_run
    from protodirsig.simulation import Simulation as old_simulation, resolve_auror_run as sim_resolve
    assert (old_workspace, old_registry, old_simulation) == (Workspace, LocalRegistry, Simulation)
    assert resolve_auror_run is sim_resolve is run_spec.resolve_run and AurorRun is run_spec.ResolvedRun
    assert AUROR_ATMOSPHERE_BACKEND is run_spec.NEW_ATMOSPHERE_BACKEND
    assert isinstance(protodirsig.__version__, str) and protodirsig.__version__
    with pytest.raises(AttributeError):
        protodirsig.no_such_name


WARN = """
import json, warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    import protodirsig
    import protodirsig.compose, protodirsig.run_spec
    from protodirsig import Workspace
    from protodirsig.workspace import default_work_root
    import protodirsig
print(json.dumps([(c.category.__name__, str(c.message)) for c in w]))
"""


def test_importing_the_shim_warns_exactly_once_naming_the_replacement():
    out = subprocess.run([sys.executable, "-c", WARN], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == [["DeprecationWarning",
                                "the protodirsig package is deprecated; import from manifold.core and manifold.sim instead"]]


def test_the_manifold_packages_do_not_need_the_shim():
    code = "import sys, manifold.core.compose, manifold.sim.workspace; print('protodirsig' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "False"
