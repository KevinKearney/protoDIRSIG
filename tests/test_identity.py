"""Run ids and sweep ids (protodirsig.identity): RFC 8785 canonical JSON, the resolved run spec, and the ids'
invariances. Vectors: manifold_contracts/vectors/identity/."""
import copy
import json
import math
import shutil
import struct
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from protodirsig import identity
from protodirsig.compose import compose, compose_sweep
from protodirsig.run_spec import RunSpecError

ROOT = Path(__file__).resolve().parents[1]
IDV = ROOT / "manifold_contracts" / "vectors" / "identity"
COMPOSE = ROOT / "manifold_contracts" / "vectors" / "compose"
SENSORS = ROOT / "manifold_sensors"
RUN_SPECS = ROOT / "manifold_run_specs"
NUMBERS = json.loads((IDV / "numbers.json").read_text())
RUN_IDS = json.loads((IDV / "run_ids.json").read_text())
CJ = identity.canonical_json


@pytest.mark.parametrize("vec", NUMBERS["vectors"], ids=lambda v: v["ieee754"])
def test_rfc8785_number_vectors(vec):
    x = struct.unpack(">d", bytes.fromhex(vec["ieee754"]))[0]
    assert CJ(x) == vec["json"].encode()


def test_key_order_is_by_utf16_code_units():
    k = NUMBERS["key_order"]
    assert CJ(k["input"]) == k["canonical"].encode()
    assert list(json.loads(k["canonical"])) == ["a", "\U0001f600", "\uff5e"]          # UTF-16 order
    assert sorted(k["input"]) == ["a", "～", "\U0001f600"]


def test_string_escaping():
    assert CJ("\x00\x01\x1f") == b'"\\u0000\\u0001\\u001f"'
    assert CJ('"\\') == b'"\\"\\\\"'
    assert CJ("\b\f\n\r\t") == b'"\\b\\f\\n\\r\\t"'
    assert CJ("\x7f/é \U0001f600") == '"\x7f/é \U0001f600"'.encode()     # literal UTF-8, no escaping
    assert CJ({"b": [1, {"a": None}], "a": True}) == b'{"a":true,"b":[1,{"a":null}]}'


def test_integer_and_float_spellings_are_one_number():
    assert CJ(1) == CJ(1.0) == b"1" and CJ(-0.0) == b"0" and CJ(1e21) == b"1e+21" and CJ(2 ** 53) == b"9007199254740992"
    spec = yaml.safe_load((RUN_SPECS / "auror_ref.yaml").read_text())
    other = copy.deepcopy(spec)
    other["engine"]["run"]["seed"] = 42.0
    other["descriptor"]["settings"][0]["gain"]["value"] = 1.0
    assert identity.run_id(spec, SENSORS) == identity.run_id(other, SENSORS)


@pytest.mark.parametrize("bad, exc", [
    (math.nan, ValueError), (math.inf, ValueError), (-math.inf, ValueError),
    (2 ** 53 + 1, ValueError), ({1: "x"}, TypeError), ({"a": {1, 2}}, TypeError), (b"bytes", TypeError),
])
def test_rejections(bad, exc):
    with pytest.raises(exc):
        CJ(bad)


def test_datetimes_are_iso_strings():
    """No loaded spec holds one (every epoch is quoted), but YAML parses an unquoted timestamp as a datetime."""
    aware = datetime(2026, 9, 26, 18, 50, 25, tzinfo=timezone.utc)
    assert CJ({"epoch": aware}) == b'{"epoch":"2026-09-26T18:50:25Z"}' == CJ({"epoch": "2026-09-26T18:50:25Z"})


@pytest.mark.parametrize("rel", sorted(RUN_IDS["run_ids"]))
def test_compose_vector_run_ids(rel):
    spec = yaml.safe_load((COMPOSE / rel).read_text())
    assert identity.run_id(spec, COMPOSE / "manifold_sensors") == RUN_IDS["run_ids"][rel]


def test_sweep_vector_id():
    (recipe,) = (COMPOSE / "sweep_three_sensors" / "recipes").glob("*.yaml")
    sweep = compose_sweep(recipe, sensor_library=COMPOSE / "manifold_sensors")
    assert sweep.sweep_id == RUN_IDS["sweep_ids"]["sweep_three_sensors"]
    assert list(sweep.run_ids.values()) == [RUN_IDS["run_ids"][f"sweep_three_sensors/expected/{sweep.files[n]}.yaml"]
                                            for n in sweep.runs]


def _reordered(node):
    if isinstance(node, dict):
        return {k: _reordered(node[k]) for k in reversed(list(node))}
    if isinstance(node, list):
        return [_reordered(v) for v in node]
    return node


def test_invariances():
    path = RUN_SPECS / "auror_ref.yaml"
    spec = yaml.safe_load(path.read_text())
    rid = identity.run_id(spec, SENSORS)
    assert len(rid) == 64 and int(rid, 16) >= 0
    assert identity.run_id(_reordered(spec), SENSORS) == rid                                   # key order
    respelled = (path.read_text().replace("value: 0.005", "value: 5.0e-3").replace("seed: 42", "seed: 42.0")
                 .replace("name: auror-ref-static-pose", "name: 'auror-ref-static-pose'"))
    assert respelled != path.read_text() and identity.run_id(yaml.safe_load(respelled), SENSORS) == rid   # YAML spelling
    inline = compose(RUN_SPECS / "recipes" / "auror_ref.yaml", inline_sensor=True)
    assert identity.run_id(inline, SENSORS) == rid                                             # sensor inline or by ref
    assert identity.resolved_run_spec(spec, SENSORS) == inline


def test_the_same_recipe_from_another_directory_has_the_same_id(tmp_path):
    root = tmp_path / "elsewhere" / "manifold_run_specs"
    for d in ("recipes", "scenarios", "engine_profiles"):
        shutil.copytree(RUN_SPECS / d, root / d)
    shutil.copytree(SENSORS, tmp_path / "elsewhere" / "manifold_sensors")
    here = compose_sweep(RUN_SPECS / "recipes" / "auror_ref.yaml")
    there = compose_sweep(root / "recipes" / "auror_ref.yaml")
    assert here.run_ids == there.run_ids and here.sweep_id == there.sweep_id


@pytest.mark.parametrize("edit", [
    lambda s: s["descriptor"]["settings"][0]["exposure_time"].update(value=0.004),
    lambda s: s["descriptor"]["settings"][0]["exposure_time"].update(provenance="modeled"),
    lambda s: s["descriptor"]["meta"].update(name="another-name"),
    lambda s: s["engine"]["run"].update(seed=43),
], ids=["settings_value", "settings_provenance_label", "meta_name", "engine_value"])
def test_differences_that_change_the_id(edit):
    spec = yaml.safe_load((RUN_SPECS / "auror_ref.yaml").read_text())
    other = copy.deepcopy(spec)
    edit(other)
    assert identity.run_id(other, SENSORS) != identity.run_id(spec, SENSORS)


def test_a_wrong_sensor_hash_raises():
    spec = yaml.safe_load((RUN_SPECS / "auror_ref.yaml").read_text())
    spec["descriptor"]["sensor"]["ref"]["content_hash"] = "sha256:" + "0" * 64
    with pytest.raises(RunSpecError, match="content_hash .* does not match"):
        identity.run_id(spec, SENSORS)


def _sweep_copy(tmp_path, edit):
    root = tmp_path / "manifold_run_specs"
    for d in ("recipes", "scenarios", "engine_profiles"):
        shutil.copytree(RUN_SPECS / d, root / d, dirs_exist_ok=True)
    shutil.copytree(SENSORS, tmp_path / "manifold_sensors", dirs_exist_ok=True)
    recipe = root / "recipes" / "sensor_sweep_tahoe.yaml"
    doc = yaml.safe_load(recipe.read_text())
    edit(doc)
    recipe.write_text(yaml.safe_dump(doc, sort_keys=False))
    return compose_sweep(recipe)


def test_sweep_ids(tmp_path):
    base = compose_sweep(RUN_SPECS / "recipes" / "sensor_sweep_tahoe.yaml")
    assert len(base.sweep_id) == 64 and base.sweep_id == identity.sweep_id_from_runs(base.run_ids.values())
    reordered = _sweep_copy(tmp_path / "a", lambda d: d["sensors"].reverse())
    assert reordered.sweep_id == base.sweep_id and list(reordered.runs) != list(base.runs)
    fewer = _sweep_copy(tmp_path / "b", lambda d: (d["sensors"].pop(),
                                                   d["settings"].pop(),
                                                   d["fidelity_by_sensor"].popitem()))
    assert len(fewer.runs) == 2 and fewer.sweep_id != base.sweep_id      # adding the third sensor changes the id
    assert identity.short_id(base.sweep_id) == base.sweep_id[:12]
    with pytest.raises(ValueError):
        identity.sweep_id_from_runs([])
