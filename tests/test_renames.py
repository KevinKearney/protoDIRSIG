"""The phase 2b-3 renames: general names in place of AUROR-specific code symbols, the old names kept as aliases of the
same objects for the notebooks."""
import importlib
import inspect
import re

import pytest

from protodirsig import run_spec, simulation
from protodirsig.simulation import Simulation

ALIASES = {("run_spec", "resolve_auror_run"): ("run_spec", "resolve_run"),
           ("run_spec", "AurorRun"): ("run_spec", "ResolvedRun"),
           ("run_spec", "AUROR_ATMOSPHERE_BACKEND"): ("run_spec", "NEW_ATMOSPHERE_BACKEND"),
           ("simulation", "resolve_auror_run"): ("run_spec", "resolve_run")}
MODULES = ("run_spec", "simulation", "registry", "backend", "store", "worker", "admission")


@pytest.mark.parametrize("old, new", ALIASES.items(), ids=lambda x: ".".join(x) if isinstance(x, tuple) else x)
def test_every_old_name_is_the_new_object(old, new):
    mod_old = importlib.import_module(f"protodirsig.{old[0]}")
    mod_new = importlib.import_module(f"protodirsig.{new[0]}")
    assert getattr(mod_old, old[1]) is getattr(mod_new, new[1])


def test_simulation_auror_run_is_a_read_only_alias_of_resolved(tmp_path):
    from test_simulation import CONFIG_REPO, SPEC
    sim = Simulation.from_run_spec(SPEC, CONFIG_REPO, tmp_path)
    assert sim.auror_run is sim.resolved and sim.resolved is not None
    with pytest.raises(AttributeError):
        sim.auror_run = None
    assert isinstance(inspect.getattr_static(Simulation, "auror_run"), property)


def test_no_auror_specific_public_name_remains():
    allowed = {f"{m}.{n}" for m, n in ALIASES} | {"Simulation.auror_run"}
    found = []
    for m in MODULES:
        mod = importlib.import_module(f"protodirsig.{m}")
        for name, obj in vars(mod).items():
            if name.startswith("_"):
                continue
            if re.search("auror", name, re.I) and f"{m}.{name}" not in allowed:
                found.append(f"{m}.{name}")
            if inspect.isclass(obj) and obj.__module__ == mod.__name__:
                found += [f"{name}.{a}" for a in vars(obj) if not a.startswith("_") and re.search("auror", a, re.I)
                          and f"{name}.{a}" not in allowed]
    assert found == []


def test_the_module_docstrings_describe_the_code_not_the_data_set():
    for mod in (run_spec, simulation):
        assert "AUROR_ref job" not in mod.__doc__ and "AUROR_ref-type" not in (Simulation.__doc__ or "")
