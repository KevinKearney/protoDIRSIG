"""The SDK API contract (api/) against itself and the code: schemas, OpenAPI document, examples, citations.

The contract is proposed and describes behavior that is not built yet; these tests keep its parts consistent with
each other, keep every symbol it names as existing code importable, and keep its examples generated from the real
library (scripts/api_examples.py).
"""
import importlib
import importlib.util
import json
import pkgutil
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

import protodirsig
from protodirsig.compose import ComposeError, compose_sweep

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api"
SCHEMAS = sorted((API / "schemas").glob("*.schema.json"))
EXAMPLES = sorted((API / "examples").glob("*.json"))
OPENAPI = yaml.safe_load((API / "openapi.yaml").read_text())
VECTORS = ROOT / "manifold_contracts" / "vectors" / "compose"
CONTRACTS = ROOT / "manifold_contracts"
MARKER = "(abbreviated)"                       # scripts/api_examples.py ABBREVIATION_MARKER


def _load(path):
    return yaml.safe_load(path.read_text()) if path.suffix == ".yaml" else json.loads(path.read_text())


def _retrieve(uri):
    """A schema by its file; a contract schema also by its file name, for references between the contract schemas,
    which are sibling file names under a relative $id (see manifold_contracts/README.md)."""
    path = Path(uri.removeprefix("file://"))
    if not path.is_file() and (CONTRACTS / path.name).is_file():
        path = CONTRACTS / path.name
    return Resource.from_contents(_load(path), default_specification=DRAFT202012)


REGISTRY = Registry(retrieve=_retrieve)


def _validator(ref):
    """A validator for `ref`, a path relative to api/ with an optional JSON-pointer fragment."""
    path, _, frag = ref.partition("#")
    return Draft202012Validator({"$ref": (API / path).as_uri() + (f"#{frag}" if frag else "")}, registry=REGISTRY)


def _operations():
    """The operation table of api/operations.md: one dict per row, by column header."""
    lines = (API / "operations.md").read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("| Operation |"))
    head = [c.strip() for c in lines[start].strip("|").split("|")]
    rows = []
    for ln in lines[start + 2:]:
        if not ln.startswith("|"):
            break
        rows.append(dict(zip(head, (c.strip() for c in ln.strip("|").split("|")))))
    return rows


def _names(cell):
    return re.findall(r"`([a-z_]+)`", cell.split("(")[0])


OPERATIONS = _operations()
OP_NAMES = [n for row in OPERATIONS for n in _names(row["Operation"])]
OP_IDS = {op["operationId"]: (method, path) for path, item in OPENAPI["paths"].items() for method, op in item.items()}


@pytest.mark.parametrize("path", SCHEMAS, ids=lambda p: p.name)
def test_schema_is_valid_and_describes_every_property(path):
    schema = _load(path)
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"

    def walk(node, where):
        if isinstance(node, dict):
            for name, sub in node.get("properties", {}).items():
                assert "description" in sub or "$ref" in sub, f"{path.name}: {where}.{name} has no description"
            for k, v in node.items():
                walk(v, f"{where}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{where}[{i}]")
    walk(schema, "")


def test_the_schemas_the_contract_names_exist():
    assert {p.name.removesuffix(".schema.json") for p in SCHEMAS} == {
        "artifact_ref", "run_status", "sweep_status", "compose_request", "compose_response", "validate_request",
        "validate_response", "problem", "library_list", "library_document", "sensor_document", "submit_run_request",
        "submit_sweep_request", "artifact_list", "run_spec_document"}


def _refs(node):
    if isinstance(node, dict):
        if isinstance(node.get("$ref"), str):
            yield node["$ref"]
        for v in node.values():
            yield from _refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from _refs(v)


def _pointer(doc, frag):
    for part in [p for p in frag.split("/") if p]:
        doc = doc[part]
    return doc


@pytest.mark.parametrize("path", [API / "openapi.yaml", *SCHEMAS], ids=lambda p: p.name)
def test_every_ref_resolves_to_an_existing_file(path):
    """Every `$ref` names an existing file (or this file), and its JSON-pointer fragment, if any, exists in it."""
    for ref in _refs(_load(path)):
        file, _, frag = ref.partition("#")
        target = (path.parent / file).resolve() if file else path
        assert target.is_file(), f"{path.name}: $ref {ref} names a missing file"
        assert _pointer(_load(target), frag) is not None, f"{path.name}: $ref {ref} names a missing location"


def test_openapi_defines_no_inline_component_schemas():
    assert "schemas" not in OPENAPI.get("components", {}), "bodies belong in api/schemas/"


def test_openapi_document_validates():
    osv = pytest.importorskip("openapi_spec_validator", reason="openapi-spec-validator (dev extra) not installed")
    osv.validate(OPENAPI, base_uri=(API / "openapi.yaml").as_uri())
    assert OPENAPI["openapi"].startswith("3.1") and OPENAPI["info"]["version"] == "sdk-api/1"
    assert "proposed" in OPENAPI["info"]["description"].lower()


def test_openapi_paths_are_the_operations_and_follow_the_error_rules():
    assert sorted(OP_IDS) == sorted(OP_NAMES)
    for path, item in OPENAPI["paths"].items():
        for op in item.values():
            codes = set(op["responses"])
            assert op.get("summary") and op.get("description"), op["operationId"]
            assert "409" not in codes, op["operationId"]
            if op["operationId"] in ("submit_run", "submit_sweep"):
                assert {"202", "422"} <= codes
            if "{" in path:
                assert "404" in codes, op["operationId"]


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_validates_against_its_schema_and_operation(path):
    ex = _load(path)
    assert ex["operation"] in OP_IDS and ex["summary"] and ex["description"]
    method, template = OP_IDS[ex["operation"]]
    req, resp = ex["request"], ex["response"]
    assert req["method"].lower() == method
    assert re.fullmatch(re.sub(r"\\\{[a-z_]+\\\}", "[^/]+", re.escape(template)), req["path"]), req["path"]
    if "body" in req:
        errors = [e.message for e in _validator(req["schema"]).iter_errors(req["body"])]
        assert errors == [], errors
    op = OPENAPI["paths"][template][method]
    assert str(resp["status"]) in op["responses"]
    if any(MARKER in json.dumps(spec) for _, spec in _run_specs(resp["body"])):
        pytest.skip("abbreviated run spec in the body is not a complete document; "
                    "test_run_spec_bodies_validate_against_the_run_spec_schema checks its marker instead")
    errors = [e.message for e in _validator(resp["schema"]).iter_errors(resp["body"])]
    assert errors == [], errors


def _run_specs(node, where=""):
    """Every run-spec document in an example body: a mapping whose spec_version is run-spec/1."""
    if isinstance(node, dict):
        if node.get("spec_version") == "run-spec/1":
            yield where, node
        for k, v in node.items():
            yield from _run_specs(v, f"{where}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _run_specs(v, f"{where}[{i}]")


RUN_SPEC_EXAMPLES = sorted(p.name for p in EXAMPLES if any(True for part in ("request", "response")
                                                            for _ in _run_specs(_load(p)[part].get("body"))))


def test_some_example_carries_a_complete_run_spec():
    complete = [n for n in RUN_SPEC_EXAMPLES
                if not any(MARKER in json.dumps(s) for _, s in _run_specs(_load(API / "examples" / n)["response"]["body"]))]
    assert "get_artifact.json" in complete and "compose.json" in RUN_SPEC_EXAMPLES


@pytest.mark.parametrize("name", RUN_SPEC_EXAMPLES)
def test_run_spec_bodies_validate_against_the_run_spec_schema(name):
    """A complete run spec validates against manifold_contracts/run-spec-1.schema.json; an abbreviated one is not a
    complete document, so it must say so (the marker in the body and in the description) and is not validated."""
    ex = _load(API / "examples" / name)
    validator = _validator("../manifold_contracts/run-spec-1.schema.json")
    for part in ("request", "response"):
        for where, spec in _run_specs(ex[part].get("body")):
            if MARKER in json.dumps(spec):
                assert "abbreviated" in ex["description"], f"{name}{where}: cut members but the description does not say so"
                continue
            errors = [f"{list(e.absolute_path)}: {e.message[:160]}" for e in validator.iter_errors(spec)]
            assert errors == [], (name, where, errors)


def test_every_operation_has_an_example():
    assert {_load(p)["operation"] for p in EXAMPLES} == set(OP_NAMES)


def test_examples_are_generated_from_the_current_library():
    spec = importlib.util.spec_from_file_location("api_examples", ROOT / "scripts" / "api_examples.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--check"]) == 0, "run scripts/api_examples.py"


def test_problem_example_names_the_layer_and_field_of_the_triggering_compose_error():
    ex = _load(API / "examples" / "compose.problem.json")
    case = VECTORS / ex["source"]["conformance_vector"]
    (recipe,) = (case / "recipes").glob("*.yaml")
    with pytest.raises(ComposeError) as e:
        compose_sweep(recipe)
    body = ex["response"]["body"]
    assert (body["layer"], body["field"]) == (e.value.layer, e.value.field)
    assert body["detail"] == str(e.value) and body["status"] == 422


def _symbol(dotted):
    """Resolve `module.name`, `Class.method` or `module.Class` against protodirsig's modules."""
    first, *rest = dotted.split(".")
    mods = [importlib.import_module(f"protodirsig.{m.name}") for m in pkgutil.iter_modules(protodirsig.__path__)]
    for start in [m for m in mods if m.__name__ == f"protodirsig.{first}"] + \
                 [getattr(m, first) for m in mods if hasattr(m, first)]:
        obj = start
        try:
            for part in rest:
                obj = getattr(obj, part)
            return obj
        except AttributeError:
            continue
    return None


def test_every_operation_names_existing_code_or_is_a_gap():
    for row in OPERATIONS:
        dotted = [t for t in re.findall(r"`([A-Za-z_][\w.]*)`", row["Today"]) if "." in t]
        assert row["Status"] in ("built", "partial", "gap"), row["Operation"]
        if row["Status"] != "gap":
            assert dotted, f"{row['Operation']}: not a gap, but names no existing code"
        for t in dotted:
            assert _symbol(t) is not None, f"{row['Operation']}: `{t}` does not exist"


def test_requirement_citations():
    req = (API / "requirements.md").read_text()
    ops = (API / "operations.md").read_text()
    ids = re.findall(r"^\| (R-\d\d) \|", req, re.M)
    contract_level = re.search(r"^Contract-level requirements \([^)]*\): (R-\d\d(?:, R-\d\d)*)\.", req, re.M)
    contract_level = contract_level.group(1).split(", ") if contract_level else []
    cited = set(re.findall(r"R-\d\d", ops))
    assert len(ids) == len(set(ids))
    assert [r for r in ids if r not in cited and r not in contract_level] == []
    assert cited <= set(ids)
    for row in OPERATIONS:
        assert re.search(r"R-\d\d", row["Requirements"]), row["Operation"]
        assert re.match(r"(pure|sync|async)\b", row["Mode"]), row["Operation"]


def test_api_folder_is_publishable():
    for path in sorted(p for p in API.rglob("*") if p.is_file()):
        text = path.read_text()
        assert not re.search(r"\bC-\d", text), f"{path.relative_to(ROOT)} cites a C-n row"
        assert ".claude_mem" not in text, f"{path.relative_to(ROOT)} cites .claude_mem"
