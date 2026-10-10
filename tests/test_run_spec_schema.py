"""manifold_contracts/run-spec-1.schema.json and dirsig-engine-1.schema.json against the repository and the checker.

The schemas are the documented contract, and admission enforces them: `simulation.schema_errors` is
`contract.schema_violations` plus `semantic_errors`. These tests hold that together: every run spec the repository
produces validates; every mutation in a corpus built from two valid specs (one static, one orbit) is rejected by the
schema; `contract` gives the schema's own verdict on every document; `schema_errors` accepts nothing the schema
rejects; and it rejects beyond the schema only the named semantic cases.
"""
import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from protodirsig.simulation import schema_errors

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "manifold_contracts"
SCHEMAS = ("run-spec-1", "dirsig-engine-1", "sensor-spec-1")
VECTORS = CONTRACTS / "vectors" / "compose"
VALID = sorted((ROOT / "manifold_run_specs").glob("*.yaml")) + sorted(
    p for p in list(VECTORS.glob("*/expected.yaml")) + list(VECTORS.glob("*/expected_inline.yaml"))
    + list(VECTORS.glob("*/expected/*.yaml")))
STATIC = ROOT / "manifold_run_specs" / "auror_ref.yaml"
ORBIT = ROOT / "manifold_run_specs" / "leo_pass_tahoe.yaml"


def _retrieve(uri):
    """Offline: a contract schema by its file, or by its file name when a validator rebased it on the relative $id."""
    path = Path(uri.removeprefix("file://"))
    if not path.is_file():
        path = CONTRACTS / path.name
    return Resource.from_contents(json.loads(path.read_text()), default_specification=DRAFT202012)


REGISTRY = Registry(retrieve=_retrieve)
VALIDATOR = Draft202012Validator({"$ref": (CONTRACTS / "run-spec-1.schema.json").as_uri()}, registry=REGISTRY)


def schema_ok(spec):
    return VALIDATOR.is_valid(spec)


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_is_valid_2020_12(name):
    schema = json.loads((CONTRACTS / f"{name}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == name.rsplit("-", 1)[0] + "/" + name.rsplit("-", 1)[1]


def _walk(node, where=""):
    if isinstance(node, dict):
        yield where, node
        for k, v in node.items():
            yield from _walk(v, f"{where}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{where}/{i}")


@pytest.mark.parametrize("name", ["run-spec-1", "dirsig-engine-1"])
def test_every_ref_resolves_offline_and_every_property_is_described(name):
    schema = json.loads((CONTRACTS / f"{name}.schema.json").read_text())
    resolver = REGISTRY.resolver(base_uri=(CONTRACTS / f"{name}.schema.json").as_uri())
    for where, node in _walk(schema):
        if isinstance(node.get("$ref"), str):
            resolver.lookup(node["$ref"])                          # raises if it does not resolve
        if "/if/" in f"{where}/":                                     # a condition, not a definition
            continue
        for prop, sub in (node.get("properties") or {}).items():
            refinement = isinstance(sub, dict) and "type" not in sub and set(sub) <= REFINEMENT
            if isinstance(sub, dict) and not refinement:
                assert "description" in sub or "$ref" in sub, f"{name}{where}/properties/{prop}"


REFINEMENT = {"required", "properties", "not", "minItems", "const"}     # a then/else narrowing an already-described member


def test_the_valid_corpus_is_what_the_repository_produces():
    assert len(VALID) == 15                                       # 6 generated specs, 9 vector specs


@pytest.mark.parametrize("path", VALID, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_composed_spec_validates(path):
    """In the state the repository keeps it in: a .scene ref keeps its sha256:<hash> placeholder, as the layers do."""
    errors = [f"{list(e.absolute_path)}: {e.message[:200]}" for e in VALIDATOR.iter_errors(yaml.safe_load(path.read_text()))]
    assert errors == []


# --- mutation corpus ------------------------------------------------------------------------------

def _at(spec, path):
    d = spec
    for k in path[:-1]:
        d = d[k]
    return d, path[-1]


def _set(path, value):
    def edit(spec):
        d, k = _at(spec, path)
        d[k] = value
    return edit


def _del(path):
    def edit(spec):
        d, k = _at(spec, path)
        del d[k]
    return edit


S, O = "static", "orbit"
MUTATIONS = {}
for k in ("meta", "origin", "collection", "sensor", "settings", "fidelity"):
    MUTATIONS[f"descriptor_without_{k}"] = (S, _del(("descriptor", k)))
for k in ("generator", "scenes", "platform", "motion", "tasks", "atmosphere"):
    MUTATIONS[f"engine_without_{k}"] = (S, _del(("engine", k)))
for name, path in (("top", ()), ("descriptor", ("descriptor",)), ("engine", ("engine",)),
                   ("engine_platform", ("engine", "platform")), ("engine_motion", ("engine", "motion"))):
    MUTATIONS[f"unknown_key_in_{name}"] = (S, _set(path + ("not_a_member",), 1))
for name, base, path in (
        ("generator_tool", S, ("engine", "generator", "tool")),
        ("generator_spec_schema", S, ("engine", "generator", "spec_schema")),
        ("motion_kind", S, ("engine", "motion", "kind")),
        ("orientation_kind", S, ("engine", "motion", "orientation", "kind")),
        ("atmosphere_plugin", S, ("engine", "atmosphere", "plugin")),
        ("weather_source", S, ("engine", "weather", "source")),
        ("ephemeris_plugin", S, ("engine", "ephemeris", "plugin")),
        ("lookat_frame", O, ("engine", "motion", "orientation", "lookat", "frame")),
        ("lookat_up", O, ("engine", "motion", "orientation", "lookat", "up")),
        ("origin_kind", S, ("descriptor", "origin", "kind")),
        ("origin_engine", S, ("descriptor", "origin", "engine")),
        ("quantity_provenance", S, ("descriptor", "settings", 0, "exposure_time", "provenance"))):
    MUTATIONS[f"invalid_{name}"] = (base, _set(path, "bogus"))
MUTATIONS["seed_is_a_string"] = (S, _set(("engine", "run", "seed"), "42"))
MUTATIONS["seed_is_a_boolean"] = (S, _set(("engine", "run", "seed"), True))
MUTATIONS["no_task_windows"] = (S, _set(("engine", "tasks", "windows"), []))
MUTATIONS["integration_samples_zero"] = (S, _set(("engine", "platform", "integration_samples"), 0))
MUTATIONS["channel_response_bogus"] = (S, _set(("engine", "platform", "channel_response"), "bogus"))
MUTATIONS["measured_without_conditions"] = (S, _set(("descriptor", "settings", 0, "exposure_time", "provenance"), "measured"))
MUTATIONS["origin_engine_field_kind_synthetic"] = (S, _set(("descriptor", "origin", "engine"), "field"))
MUTATIONS["targets_without_range"] = (S, _del(("descriptor", "collection", "geometry", "range")))
for k in ("tle", "propagator", "earth_orientation", "window", "waypoint_spacing"):
    MUTATIONS[f"orbit_without_{k}"] = (O, _del(("engine", "motion", "orbit", k)))
MUTATIONS["invalid_orbit_propagator"] = (O, _set(("engine", "motion", "orbit", "propagator"), "dirsig_sgp4"))

BASES = {S: yaml.safe_load(STATIC.read_text()), O: yaml.safe_load(ORBIT.read_text())}


def mutated(name):
    base, edit = MUTATIONS[name]
    spec = copy.deepcopy(BASES[base])
    edit(spec)
    return spec


def test_the_corpus_covers_the_stated_mutations():
    assert len(MUTATIONS) == 43
    assert BASES[S]["engine"]["motion"]["kind"] == "static" and BASES[O]["engine"]["motion"]["kind"] == "orbit"
    assert schema_ok(BASES[S]) and schema_ok(BASES[O])
    assert BASES[S]["descriptor"]["collection"]["targets"]                   # targets_without_range is meaningful


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_every_mutation_is_rejected_by_the_schema(name):
    assert not schema_ok(mutated(name)), name


# --- agreement with schema_errors -----------------------------------------------------------------

# Admission enforces the schemas (schema_errors = contract.schema_violations + semantic_errors), so the checker is
# never narrower than the schema. It is wider only by the semantic rules JSON Schema cannot express, each named here.
SEMANTIC = {
    "seed_is_a_float": (S, _set(("engine", "run", "seed"), 42.0),
                        "JSON Schema's integer accepts 42.0; the generator needs an integer seed"),
    "integration_samples_is_a_float": (S, _set(("engine", "platform", "integration_samples"), 10.0),
                                       "JSON Schema's integer accepts 10.0; the generator needs an integer"),
    "origin_engine_satsim": (S, _set(("descriptor", "origin", "engine"), "satsim"),
                             "the schemas type the engine block only for dirsig; this SDK executes only dirsig runs"),
}


def _semantic(name):
    base, edit, _ = SEMANTIC[name]
    spec = copy.deepcopy(BASES[base])
    edit(spec)
    return spec


def _corpus():
    docs = {f"valid:{p.relative_to(ROOT)}": yaml.safe_load(p.read_text()) for p in VALID}
    docs.update({name: mutated(name) for name in MUTATIONS})
    docs.update({f"semantic:{name}": _semantic(name) for name in SEMANTIC})
    return docs


def test_contract_module_gives_the_schemas_own_verdict():
    """contract.schema_violations is the schema, applied: same verdict as an independent validator, on every document."""
    from protodirsig import contract
    for name, spec in _corpus().items():
        assert (contract.schema_violations(spec) == []) == schema_ok(spec), name
        assert all(v["path"] == "" or v["path"].startswith("/") for v in contract.schema_violations(spec)), name


def test_schema_errors_enforces_the_schema_and_only_named_semantic_rules_beyond_it():
    wider = set()
    for name, spec in _corpus().items():
        accepted = schema_errors(spec) == []
        if accepted:
            assert schema_ok(spec), f"{name}: schema_errors accepts what the schema rejects"
        elif schema_ok(spec):
            wider.add(name)
    assert wider == {f"semantic:{n}" for n in SEMANTIC}, wider


@pytest.mark.parametrize("name", sorted(SEMANTIC))
def test_each_semantic_case_is_caught_by_semantic_errors(name):
    from protodirsig.simulation import semantic_errors
    spec = _semantic(name)
    assert schema_ok(spec) and semantic_errors(spec), name
