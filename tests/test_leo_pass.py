"""The LEO pass recipe (recipes/leo_pass_tahoe.yaml): composition, and the three-frame render checked independently.

Composition: the composed spec passes the run-spec checks, composes to the same bytes twice, and names no path
outside the libraries (its run-id inputs are the document alone).
"""
from pathlib import Path

import yaml

from protodirsig.compose import HEADER, compose, dump
from protodirsig.simulation import schema_errors

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "manifold_run_specs" / "recipes" / "leo_pass_tahoe.yaml"
GENERATED = ROOT / "manifold_run_specs" / "leo_pass_tahoe.yaml"
CONFIG_REPO = ROOT / "manifold_config_repo"
SENSORS = ROOT / "manifold_sensors"


def test_pass_spec_passes_the_run_spec_checks():
    spec = compose(RECIPE)
    assert schema_errors(spec) == []
    assert spec["engine"]["motion"]["kind"] == "orbit" and len(spec["engine"]["tasks"]["windows"]) == 3


def test_pass_spec_composes_to_the_same_bytes_twice():
    a, b = (dump(compose(RECIPE), "recipes/leo_pass_tahoe.yaml") for _ in range(2))
    assert a == b == GENERATED.read_text()
    assert a.startswith(HEADER.format(recipe="recipes/leo_pass_tahoe.yaml"))


def _strings(node, where=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _strings(v, f"{where}.{k}" if where else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _strings(v, f"{where}[{i}]")
    elif isinstance(node, str):
        yield where, node


def _refs(node, where=""):
    if isinstance(node, dict):
        if set(node) >= {"name", "content_hash"}:
            yield where, node["name"]
        for k, v in node.items():
            yield from _refs(v, f"{where}.{k}" if where else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _refs(v, f"{where}[{i}]")


def test_pass_spec_names_no_path_outside_the_libraries():
    spec = yaml.safe_load(GENERATED.read_text())
    for where, s in _strings(spec):
        assert not s.startswith(("/", "~")) and ".." not in Path(s).parts and "outputs/" not in s, (where, s)
    refs = dict(_refs(spec))
    assert {"engine.motion.orbit.tle", "engine.motion.orbit.earth_orientation"} <= set(refs)
    for where, name in refs.items():
        root = SENSORS if where.startswith("descriptor.sensor") else CONFIG_REPO
        assert (root / name).resolve().is_relative_to(root.resolve()), (where, name)
        assert (root / name).is_file(), (where, name)
