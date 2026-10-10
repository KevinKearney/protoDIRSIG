"""The published contract schemas, applied: `run-spec/1`, `dirsig-engine/1` and `sensor-spec/1` from `manifold_contracts/`.

`schema_violations(spec)` validates a parsed run spec against `manifold_contracts/run-spec-1.schema.json` (which
references the engine and sensor-spec schemas) and returns every violation as `{path, message}`, `path` an RFC 6901
JSON Pointer into the spec. `simulation.schema_errors` formats these as its schema-check messages, so admission
enforces the schemas.

The schemas are read from the repository's `manifold_contracts/` folder, the sibling of `src/` (as
`run_spec.default_sensor_library` locates `manifold_sensors/`); the environment variable `PROTODIRSIG_CONTRACTS`
overrides the folder. Each schema's `$id` is an absolute URI under https://schemas.manifold.example/contracts/, a base
that does not resolve on the network; references between the three schemas are sibling file names resolved against it,
and a `referencing` registry holds each file under its `$id` (and retrieves by file name), so everything resolves offline.

Imports: the standard library, `jsonschema` and `referencing` only; no engine package and nothing from `simulation`.
"""
import json
import os
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

SCHEMA_FILES = ("run-spec-1.schema.json", "dirsig-engine-1.schema.json", "sensor-spec-1.schema.json")
ROOT_SCHEMA = "run-spec-1.schema.json"
MAX_MESSAGE = 200


def contracts_dir():
    """The folder holding the contract schemas: `$PROTODIRSIG_CONTRACTS`, or the repository's `manifold_contracts/`."""
    env = os.environ.get("PROTODIRSIG_CONTRACTS")
    return Path(env) if env else Path(__file__).resolve().parents[2] / "manifold_contracts"


@lru_cache(maxsize=4)
def _validator(folder):
    folder = Path(folder)
    docs = {name: json.loads((folder / name).read_text()) for name in SCHEMA_FILES}

    def retrieve(uri):
        name = uri.rstrip("/").rsplit("/", 1)[-1]
        for file, doc in docs.items():
            if name == file or uri == doc.get("$id"):
                return Resource.from_contents(doc, default_specification=DRAFT202012)
        raise LookupError(f"no contract schema for {uri!r} in {folder}")

    resources = [(doc.get("$id", file), Resource.from_contents(doc, default_specification=DRAFT202012))
                 for file, doc in docs.items()]
    registry = Registry(retrieve=retrieve).with_resources(resources)
    root = docs[ROOT_SCHEMA]
    return Draft202012Validator(root, registry=registry)


def validator():
    """The run-spec/1 validator over the current contracts folder (cached per folder)."""
    return _validator(str(contracts_dir()))


def pointer(path):
    """An RFC 6901 JSON Pointer for a sequence of keys and indices."""
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in path)


def _message(error):
    """The violation's message, without the whole instance that combinators (oneOf, anyOf, not) quote."""
    msg = error.message
    if error.validator in ("oneOf", "anyOf") and error.context:
        branches = {}
        for sub in error.context:                       # group the alternatives' errors by alternative
            branches.setdefault(sub.relative_schema_path[0], []).append(sub)
        closest = min(branches.values(), key=lambda errs: (len(errs), -max(len(e.relative_path) for e in errs)))
        inner = closest[0]
        where = pointer(inner.relative_path)
        return (f"matches none of the allowed forms; closest: {where + ': ' if where else ''}"
                f"{_message(inner)[:MAX_MESSAGE]}")
    if len(msg) <= MAX_MESSAGE:
        return msg
    if error.context:
        inner = best_match(error.context)
        return f"matches none of the allowed forms ({error.validator}); closest: {inner.message[:MAX_MESSAGE]}"
    return msg[:MAX_MESSAGE] + "..."


def schema_violations(spec):
    """Every violation of run-spec/1 (and, through it, dirsig-engine/1 and sensor-spec/1) in a parsed spec, as
    `[{"path": <JSON Pointer>, "message": <text>}]`, sorted by path then message. Empty means the spec conforms."""
    found = {(pointer(e.absolute_path), _message(e)) for e in validator().iter_errors(spec)}
    return [{"path": p, "message": m} for p, m in sorted(found)]


def conforms(spec):
    return validator().is_valid(spec)
