"""docs/Engine_author_guide.md against the code: the protocol's members and signatures, the data types' fields and
defaults, the vocabularies, the entry points, the registry and admission names, the two adapters' identities, and the
SatSim sprite-filename limitation the guide states. Engine-free; nothing is run."""
import dataclasses
import inspect
import re
import tomllib
from pathlib import Path

import pytest

from manifold.core import admission, artifacts, contract, engine, identity
from manifold.engines.dirsig import adapter as dirsig
from manifold.engines.satsim import adapter as satsim
from manifold.sim import engines as discovery

ROOT = Path(__file__).resolve().parents[1]
GUIDE = (ROOT / "docs" / "Engine_author_guide.md").read_text(encoding="utf-8")


def _signature(fn):
    """The parameter list as source writes it (no return annotation; a bare `*` before keyword-only parameters)."""
    out, star = [], False
    for p in inspect.signature(fn).parameters.values():
        if p.kind is p.KEYWORD_ONLY and not star:
            out.append("*")
            star = True
        out.append(str(p))
    return "(" + ", ".join(out) + ")"


PROTOCOL = ["info", "engine_schema", "compose_problems", "semantic_rules", "resolve", "library_problems", "plan",
            "collect", "fingerprint", "resources"]


@pytest.mark.parametrize("name", PROTOCOL)
def test_each_protocol_member_is_in_the_table_with_its_signature(name):
    sig = _signature(getattr(engine.EngineAdapter, name)).replace("'", "")
    assert f"| `{name}{sig}` |" in GUIDE, f"{name}{sig}"


def test_the_table_lists_exactly_the_protocol_members():
    listed = re.findall(r"^\| `(\w+)\(self", GUIDE, re.M)
    declared = [n for n in vars(engine.EngineAdapter) if not n.startswith("_") and callable(getattr(engine.EngineAdapter, n))]
    assert listed == PROTOCOL and sorted(declared) == sorted(PROTOCOL)


def test_the_optional_members_are_those_the_adapters_define():
    assert "`dry_run(self, spec, resolved, scratch_root, options=None)`" in GUIDE
    assert _signature(dirsig.DirsigAdapter.dry_run) == "(self, spec, resolved, scratch_root, options=None)"
    assert callable(getattr(satsim.SatsimAdapter, "schemas")) and callable(getattr(satsim.SatsimAdapter, "availability"))
    assert callable(getattr(dirsig.DirsigAdapter, "availability"))


def _fields(cls):
    out = []
    for f in dataclasses.fields(cls):
        if f.default is not dataclasses.MISSING:
            out.append(f"`{f.name}={f.default!r}`".replace("'", '"'))
        elif f.default_factory is not dataclasses.MISSING:
            value = f.default_factory()
            out.append(f"`{f.name}={type(value).__name__}()`" if dataclasses.is_dataclass(value)
                       else f"`{f.name}={value!r}`")
        else:
            out.append(f"`{f.name}`")
    return ", ".join(out)


@pytest.mark.parametrize("cls", [engine.EngineInfo, engine.ResolveContext, engine.RunContext, engine.EnvironmentPolicy,
                                 engine.LaunchPlan, engine.CollectedArtifact, engine.Collection])
def test_each_data_type_row_gives_the_fields_and_defaults(cls):
    row = next(line for line in GUIDE.splitlines() if line.startswith(f"| `{cls.__name__}` |"))
    assert row == f"| `{cls.__name__}` | {_fields(cls)} |", row
    assert cls.__dataclass_params__.frozen


def test_the_vocabularies():
    assert engine.MODES == ("layered", "passthrough") and engine.VERDICTS == ("complete", "incomplete", "failed")
    assert artifacts.ROLES == ("product", "truth", "preview", "log", "config", "metadata")
    assert set(engine.ROLES) == set(artifacts.ROLES) - {"preview"}


def test_the_entry_points_and_dependencies_are_as_stated():
    for pkg, eid, target in (("engine-dirsig", "dirsig", "manifold.engines.dirsig.adapter:DirsigAdapter"),
                             ("engine-satsim", "satsim", "manifold.engines.satsim.adapter:SatsimAdapter")):
        project = tomllib.loads((ROOT / "packages" / pkg / "pyproject.toml").read_text())["project"]
        assert project["entry-points"]["manifold.engines"] == {eid: target}
        assert f"`{eid} = {target.replace(':', ':')}`" in GUIDE
        assert "eoptic-manifold-core==0.0.1" in project["dependencies"]
    block = re.search(r"```toml\n(.*?)```", GUIDE, re.S).group(1)
    assert block in (ROOT / "packages" / "engine-dirsig" / "pyproject.toml").read_text()
    assert discovery.GROUP == "manifold.engines"


def test_the_registry_and_admission_names():
    for name in ("build_registry", "registry", "load_target"):
        assert callable(getattr(discovery, name))
    for name in ("describe", "from_description", "status"):
        assert callable(getattr(engine.Registry, name))
    assert callable(engine.set_default_registry) and issubclass(engine.RegistryNotConfigured, LookupError)
    assert ("`manifold.core.admission.validate_spec" + _signature(admission.validate_spec) + "`") in GUIDE
    assert callable(contract.schema_errors) and callable(contract.semantic_errors) and callable(contract.adapter_schemas)
    assert _signature(identity.run_id) == "(spec, sensor_library)"


def test_the_two_adapters_identify_as_stated():
    d, s = dirsig.DirsigAdapter().info(), satsim.SatsimAdapter().info()
    assert (d.engine_id, d.contracts, d.modes) == ("dirsig", ("dirsig-engine/1",), ("layered", "passthrough"))
    assert (s.engine_id, s.contracts, s.modes) == ("satsim", ("satsim-engine/1",), ("passthrough",))
    assert satsim.THREAD_VARIABLES == ("TF_NUM_INTRAOP_THREADS", "TF_NUM_INTEROP_THREADS", "OMP_NUM_THREADS",
                                       "NUMBA_NUM_THREADS")
    assert {a.env for a in satsim.ASSETS} == {"MANIFOLD_SATSIM_EPHEMERIS", "MANIFOLD_SATSIM_IERS"}
    assert satsim.MEMORY_BYTES == 1 << 30 and satsim.SCRATCH_BYTES == 256 << 20 and satsim.ROOTS == ("fpa", "radar", "passive_rf")
    assert {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"} <= set(satsim.UNSET)
    assert dirsig.DirsigAdapter().resources().cpu_threads.variables == ()
    assert callable(dirsig.registry) and callable(dirsig.schema_path) and callable(dirsig.passthrough_role)


def test_the_sprite_filename_limitation_is_as_stated():
    """The scan covers `$import`, `$cache`, `path` and `file`, not a sprite's `filename` (not fixed; BACKLOG)."""
    def model(key):
        return {"fpa": {}, "geometry": {"obs": {"list": [{"model": {"mode": "sprite", key: "/abs/plate.fits"}}]}}}
    assert satsim.config_problems(model("filename"), None) == []
    assert satsim.config_problems(model("file"), None) != []
    assert [k for k, _ in satsim._references({"a": {"$import": "x", "$cache": "y", "path": "z", "file": "w",
                                                     "filename": "v"}})] == ["a/$import", "a/$cache", "a/path", "a/file"]
