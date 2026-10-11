"""The distribution graph, read from each `pyproject.toml` under `packages/`: `eoptic-manifold-core` depends on no manifold
distribution; `eoptic-manifold-sim` on core only; an engine distribution (`packages/engine-*`) on core only, plus its
own third-party dependencies; the deprecated `protodirsig` shim may depend on all. Dependencies on manifold
distributions are pinned to the shared version (lockstep)."""
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = sorted(p for p in (ROOT / "packages").iterdir() if (p / "pyproject.toml").is_file())
MANIFOLD = re.compile(r"^(eoptic-manifold-[a-z0-9-]+|protodirsig)\b")


def _project(pkg):
    return tomllib.loads((pkg / "pyproject.toml").read_text())["project"]


def _manifold_deps(project):
    deps = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        deps += extra
    return {MANIFOLD.match(d).group(1): d for d in deps if MANIFOLD.match(d)}


def _allowed(name):
    if name == "eoptic-manifold-core":
        return set()
    if name == "eoptic-manifold-sim" or name.startswith("eoptic-manifold-engine-"):
        return {"eoptic-manifold-core"}
    if name == "protodirsig":
        return None                                              # the shim may depend on every manifold distribution
    raise AssertionError(f"unknown distribution {name}: add its rule here")


@pytest.mark.parametrize("pkg", PACKAGES, ids=[p.name for p in PACKAGES])
def test_each_distribution_depends_only_on_what_its_layer_may(pkg):
    project = _project(pkg)
    deps = _manifold_deps(project)
    allowed = _allowed(project["name"])
    if allowed is not None:
        assert set(deps) <= allowed, f"{project['name']} depends on {sorted(set(deps) - allowed)}"


def test_manifold_dependencies_are_lockstep():
    versions = {_project(p)["name"]: _project(p)["version"] for p in PACKAGES}
    for p in PACKAGES:
        for name, spec in _manifold_deps(_project(p)).items():
            assert spec == f"{name}=={versions[name]}", (p.name, spec)


def test_engine_distributions_register_an_entry_point_and_no_engine_ships_the_namespace_init():
    for p in (ROOT / "packages").glob("engine-*"):
        eps = _project(p).get("entry-points", {}).get("manifold.engines", {})
        assert eps, f"{p.name} registers no manifold.engines entry point"
        assert not (p / "src" / "manifold" / "__init__.py").exists()
        assert not (p / "src" / "manifold" / "engines" / "__init__.py").exists()
