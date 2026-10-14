"""Validate a document against a schema of the SDK API contract (api/schemas/), offline: references between the API
schemas are file paths; the contract schemas under manifold_contracts/ are found by file name."""
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api" / "schemas"
CONTRACTS = ROOT / "manifold_contracts"


def _retrieve(uri):
    path = Path(uri.removeprefix("file://"))
    if not path.is_file() and (CONTRACTS / path.name).is_file():
        path = CONTRACTS / path.name
    return Resource.from_contents(json.loads(path.read_text()), default_specification=DRAFT202012)


REGISTRY = Registry(retrieve=_retrieve)


@lru_cache(maxsize=None)
def validator(name):
    """A validator for `api/schemas/<name>.schema.json`."""
    return Draft202012Validator({"$ref": (API / f"{name}.schema.json").as_uri()}, registry=REGISTRY)


def errors(name, doc):
    """The schema violations of `doc` against `api/schemas/<name>.schema.json` (empty: it conforms)."""
    return [f"{list(e.absolute_path)}: {e.message[:200]}" for e in validator(name).iter_errors(doc)]
