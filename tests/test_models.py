"""The typed models generated from the API schemas (scripts/gen_models.py -> src/protodirsig/models.py)."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from api_schema import errors as schema_errors
from protodirsig import models

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((ROOT / "api" / "examples").glob("*.json"))
MARKER = "(abbreviated)"
spec = importlib.util.spec_from_file_location("gen_models", ROOT / "scripts" / "gen_models.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def _cases():
    """(example file, part, schema stem, body) for every example body whose schema has a model class."""
    out = []
    for path in EXAMPLES:
        ex = json.loads(path.read_text())
        for part in ("request", "response"):
            body, schema = ex[part].get("body"), ex[part].get("schema")
            if isinstance(body, dict) and schema:
                stem = Path(schema).name.removesuffix(".schema.json")
                if hasattr(models, gen.capwords(stem)):
                    out.append((f"{path.stem}.{part}", stem, body))
    return out


CASES = _cases()


def test_every_api_schema_with_an_object_has_a_model():
    stems = {Path(p).name.removesuffix(".schema.json") for p in (ROOT / "api" / "schemas").glob("*.schema.json")}
    assert {gen.capwords(s) for s in stems} - set(models.__all__) == {"RunSpecDocument"}   # a $ref to run-spec/1
    assert len(CASES) >= 25


@pytest.mark.parametrize("name, stem, body", CASES, ids=[c[0] for c in CASES])
def test_every_example_round_trips(name, stem, body):
    cls = getattr(models, gen.capwords(stem))
    obj = cls.from_dict(body)
    assert obj.to_dict() == body
    if MARKER not in json.dumps(body):
        assert schema_errors(stem, obj.to_dict()) == []


def test_nested_models_are_built():
    ex = json.loads((ROOT / "api" / "examples" / "get_run.json").read_text())["response"]["body"]
    status = models.RunStatus.from_dict(ex)
    assert isinstance(status.artifacts, tuple) and all(isinstance(a, models.ArtifactRef) for a in status.artifacts)
    compose = models.ComposeResponse.from_dict(json.loads((ROOT / "api" / "examples" / "compose.json").read_text())
                                               ["response"]["body"])
    run = compose.runs[0]
    assert isinstance(run, models.ComposeResponseRun) and isinstance(run.run_spec, dict)
    assert all(isinstance(v, models.ComposeResponseRunProvenanceEntry) for v in run.provenance.values())


GOOD = {"run_id": "a" * 64, "name": "r", "state": "accepted", "errors": [], "artifacts": []}


@pytest.mark.parametrize("data, where", [
    ({k: v for k, v in GOOD.items() if k != "state"}, "/state"),
    ({**GOOD, "colour": "red"}, "/colour"),
    ({**GOOD, "name": 3}, "/name"),
    ({**GOOD, "state": "rejected"}, "/state"),
    ({**GOOD, "artifacts": [{"name": "x", "sha256": "b" * 64, "media_type": "a/b"}]}, "/artifacts/0/uri"),
    ({**GOOD, "errors": "none"}, "/errors"),
], ids=["missing", "unknown", "wrong_type", "not_in_enum", "nested_missing", "not_an_array"])
def test_bad_input_raises_naming_the_field(data, where):
    with pytest.raises(ValueError, match="^" + where.replace("/", r"\/") + ":"):
        models.RunStatus.from_dict(data)


def test_optional_and_nullable_fields():
    p = models.Problem.from_dict({"type": "urn:x", "title": "t", "status": 404, "detail": "d"})
    assert p.layer is None and p.to_dict() == {"type": "urn:x", "title": "t", "status": 404, "detail": "d"}
    q = models.Problem.from_dict({"type": "urn:x", "title": "t", "status": 422, "layer": None, "field": None})
    assert q.to_dict() == {"type": "urn:x", "title": "t", "status": 422, "layer": None, "field": None}
    assert models.Problem.from_dict({"type": "u", "title": "t", "status": 500, "extension": 1}).to_dict()["extension"] == 1
    assert models.ArtifactRef(name="a", sha256="b" * 64, media_type="a/b", uri="file:///a").to_dict() == \
        {"name": "a", "sha256": "b" * 64, "media_type": "a/b", "uri": "file:///a"}       # frame omitted
    with pytest.raises(Exception):
        models.ArtifactRef(name="a", sha256="b", media_type="a/b", uri="u").name = "c"   # frozen


def test_the_committed_models_are_current():
    assert gen.main(["--check"]) == 0, "run scripts/gen_models.py"


def test_a_schema_change_changes_the_generated_source(tmp_path):
    folder = tmp_path / "schemas"
    shutil.copytree(ROOT / "api" / "schemas", folder)
    doc = json.loads((folder / "artifact_ref.schema.json").read_text())
    doc["properties"]["checksum_algorithm"] = {"description": "An added property.", "type": "string"}
    (folder / "artifact_ref.schema.json").write_text(json.dumps(doc))
    changed = gen.generate(folder)
    assert changed != gen.generate() and "checksum_algorithm: str = None" in changed
