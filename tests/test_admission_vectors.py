"""Admission vectors for engine selection (`manifold_contracts/vectors/admission/`) and the published engine-block
schemas: what a validator in another language needs to reproduce the schema stage of admission.

Each vector is reproduced twice: by the SDK's own admission check (`contract.schema_violations` and `semantic_errors`
against a registry of the vector's engines) and by a plain JSON Schema validator reading only the published files (the
run-spec schema, then the engine id against the vector's registry, then the engine block against the schema at the
published location of its `$id`). The run-spec schema alone accepts every vector: it is not sufficient for admission."""
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry as RefRegistry, Resource
from referencing.jsonschema import DRAFT202012

from manifold.core import contract
from manifold.core.engine import Registry
from manifold.core.identity import canonical_json
from manifold.engines.dirsig.adapter import DirsigAdapter

ROOT = Path(__file__).resolve().parents[1]
VECTORS = sorted((ROOT / "manifold_contracts" / "vectors" / "admission").glob("*.json"))


def _published(schema_id):
    loc = contract.published_location(schema_id)
    assert loc is not None, schema_id
    return json.loads((ROOT / loc).read_text())


def _plain_verdict(vector):
    """The schema stage of admission from the published files alone, as a non-Python validator would do it."""
    folder = ROOT / "manifold_contracts"
    docs = [json.loads((folder / n).read_text()) for n in contract.SCHEMA_FILES]
    refs = RefRegistry().with_resources([(d["$id"], Resource(d, DRAFT202012)) for d in docs])
    spec = vector["run_spec"]
    core = Draft202012Validator(docs[0], registry=refs)
    paths = sorted({"".join(f"/{p}" for p in e.absolute_path) for e in core.iter_errors(spec)})
    if paths:
        return {"admitted": False, "rule": "run-spec-schema", "paths": paths}
    engines = {e["engine_id"]: e["schemas"] for e in vector["registry"]}
    engine_id = spec["descriptor"]["origin"]["engine"]
    if engine_id not in engines:
        return {"admitted": False, "rule": "unregistered-engine", "paths": ["/descriptor/origin/engine"]}
    paths = set()
    for sid in engines[engine_id]:
        v = Draft202012Validator(_published(sid))
        paths |= {"/engine" + "".join(f"/{p}" for p in e.absolute_path) for e in v.iter_errors(spec["engine"])}
    if paths:
        return {"admitted": False, "rule": "engine-block-schema", "paths": sorted(paths)}
    return {"admitted": True, "rule": None, "paths": []}


def test_the_three_cases_are_published():
    assert [p.stem for p in VECTORS] == ["engine_block_invalid", "unregistered_engine", "valid"]


@pytest.mark.parametrize("path", VECTORS, ids=lambda p: p.stem)
def test_a_vector_is_reproduced_by_admission_and_by_a_plain_validator(path):
    vector = json.loads(path.read_text())
    expected = vector["expected"]
    assert vector["run_spec_schema_alone"] is True                       # the core schema alone admits every case
    assert contract.run_spec_violations(vector["run_spec"]) == []
    assert _plain_verdict(vector) == expected
    reg = Registry()
    reg.register("dirsig", DirsigAdapter)
    assert [e["engine_id"] for e in vector["registry"]] == reg.ids()
    found = {v["path"] for v in contract.schema_violations(vector["run_spec"], reg)}
    semantic = contract.semantic_errors(vector["run_spec"], reg)
    if expected["admitted"]:
        assert found == set() and semantic == []
    elif expected["rule"] == "unregistered-engine":
        assert found == set() and any("not a registered engine" in m for m in semantic), semantic
    else:
        assert found == set(expected["paths"])


def test_list_engines_names_each_schema_where_it_is_published(tmp_path):
    from manifold.sim.backend import LocalBackend
    backend = LocalBackend(tmp_path / "work", ROOT / "manifold_config_repo")
    (dirsig,) = [e for e in backend.list_engines()["items"] if e["engine_id"] == "dirsig"]
    (entry,) = dirsig["schemas"]
    assert entry["location"] == "manifold_contracts/dirsig-engine-1.schema.json"
    published = json.loads((ROOT / entry["location"]).read_text())
    assert published["$id"] == entry["schema_id"]
    assert hashlib.sha256(canonical_json(published)).hexdigest() == entry["sha256"]


def test_published_location():
    assert contract.published_location(contract.CONTRACTS_BASE + "x-engine-1.schema.json") == \
        "manifold_contracts/x-engine-1.schema.json"
    for outside in ("urn:manifold:schema:dummy-engine:1", contract.CONTRACTS_BASE + "a/b.json", None,
                    contract.CONTRACTS_BASE):
        assert contract.published_location(outside) is None
