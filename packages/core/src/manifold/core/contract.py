"""The published contract schemas, applied: `run-spec/1` and `sensor-spec/1` from `manifold_contracts/`, and the
engine block through the registered engine's adapter.

`schema_violations(spec, registry=None)` validates a parsed run spec against `manifold_contracts/run-spec-1.schema.json`
(which leaves the engine block an open object, proposed) and then the engine block against the schema the adapter
registered for `descriptor.origin.engine` gives (`EngineAdapter.engine_schema`), and returns every violation as
`{path, message, at}`, `path` and `at` RFC 6901 JSON Pointers into the spec (engine-block pointers start `/engine`).
An engine id that no adapter serves is not a schema violation: `semantic_errors` reports it, naming the registered
engines. `schema_errors` formats both as the admission's schema-check messages.

The schemas are read from the first of: the folder named by the environment variable `MANIFOLD_CONTRACTS` (the legacy
`PROTODIRSIG_CONTRACTS` is read, with a `DeprecationWarning`, when it is not set); the copy packaged with the library,
`manifold/core/_contracts/` (found with `importlib.resources`; the build copies the files there from
`manifold_contracts/`, see `packages/core/setup.py`, and a checkout or editable install has none); the repository's
`manifold_contracts/` folder, at the repository root above `packages/`. `manifold_contracts/` is the one tracked copy.
Each schema's `$id` is an absolute URI under https://schemas.manifold.example/contracts/, a base that does not resolve
on the network; a `referencing` registry holds each file under its `$id` (and retrieves by file name), so everything
resolves offline. `load_schema(name)` reads any schema of the contracts folder by file name.

`schema_errors(spec)` is the SDK's schema check: each violation as `"<JSON Pointer>: <message>"`, then
`semantic_errors(spec)`, the rules the schemas cannot express (the engine-neutral ones here, the engine's own from its
adapter's `semantic_rules`).

Imports: the standard library, `jsonschema` and `referencing`, and `manifold.core.engine`; no engine package.
"""
import json
from functools import lru_cache
from importlib import resources
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from manifold.core import _names
from manifold.core.engine import engine_id_of, resolve_registry

SCHEMA_FILES = ("run-spec-1.schema.json", "sensor-spec-1.schema.json")
ROOT_SCHEMA = "run-spec-1.schema.json"
MAX_MESSAGE = 200


def packaged_contracts_dir():
    """The schemas packaged with the library (`manifold/core/_contracts/`, copied there by the build), or None in a
    checkout or editable install, which has no packaged copy."""
    folder = resources.files(_names.CORE_PACKAGE) / "_contracts"
    try:
        if folder.joinpath(ROOT_SCHEMA).is_file():
            return Path(str(folder))
    except (FileNotFoundError, NotADirectoryError):
        pass
    return None


def contracts_dir():
    """The folder holding the contract schemas, in this order: `$MANIFOLD_CONTRACTS`; the packaged copy
    (`packaged_contracts_dir`); the repository's `manifold_contracts/`."""
    env = _names.getenv("CONTRACTS")
    if env:
        return Path(env)
    return packaged_contracts_dir() or Path(__file__).resolve().parents[5] / "manifold_contracts"


@lru_cache(maxsize=8)
def _validator(folder, root_schema=ROOT_SCHEMA):
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
    root = docs[root_schema]
    return Draft202012Validator(root, registry=registry)


def validator():
    """The run-spec/1 validator over the current contracts folder (cached per folder)."""
    return _validator(str(contracts_dir()))


def load_schema(name):
    """A schema of the contracts folder, parsed, by file name."""
    return json.loads((contracts_dir() / name).read_text())


@lru_cache(maxsize=16)
def _block_validator(schema_json):
    doc = json.loads(schema_json)
    resource = Resource.from_contents(doc, default_specification=DRAFT202012)
    return Draft202012Validator(doc, registry=Registry().with_resource(doc.get("$id", "urn:engine-block"), resource))


def _adapter(spec, registry):
    engine_id = engine_id_of(spec)
    return resolve_registry(registry).find(engine_id) if engine_id is not None else None


def engine_block_violations(spec, registry=None):
    """The engine block's violations of its adapter's schema, as `schema_violations` gives them (pointers under
    `/engine`); empty when the engine is not registered, the adapter gives no schema, or there is no engine block."""
    eng = spec.get("engine") if isinstance(spec, dict) else None
    adapter = _adapter(spec, registry)
    if adapter is None or not isinstance(eng, dict):
        return []
    schema = adapter.engine_schema(eng)
    if not schema:
        return []
    v = _block_validator(json.dumps(schema, sort_keys=True))
    return sorted({(pointer(["engine", *e.absolute_path]), _message(e), pointer(["engine", *_at(e)]))
                   for e in v.iter_errors(eng)})


def sensor_spec_violations(doc):
    """Every violation of `sensor-spec/1` in a parsed sensor document, as `schema_violations` gives them for a run
    spec (`path`, `message`, `at`), sorted. Empty means the document conforms."""
    v = _validator(str(contracts_dir()), "sensor-spec-1.schema.json")
    found = {(pointer(e.absolute_path), _message(e), pointer(_at(e))) for e in v.iter_errors(doc)}
    return [{"path": p, "message": m, "at": a} for p, m, a in sorted(found)]


def pointer(path):
    """An RFC 6901 JSON Pointer for a sequence of keys and indices."""
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in path)


def _closest(error):
    """For a oneOf/anyOf violation: the first error of the alternative with the fewest errors, else None."""
    if error.validator not in ("oneOf", "anyOf") or not error.context:
        return None
    branches = {}
    for sub in error.context:                           # group the alternatives' errors by alternative
        branches.setdefault(sub.relative_schema_path[0], []).append(sub)
    return min(branches.values(), key=lambda errs: (len(errs), -max(len(e.relative_path) for e in errs)))[0]


def _at(error):
    """The path (keys and indices) of the deepest location a violation's message names: the closest alternative's,
    followed down through nested combinators."""
    path, inner = list(error.absolute_path), _closest(error)
    while inner is not None:
        path += list(inner.relative_path)
        inner = _closest(inner)
    return path


def _message(error):
    """The violation's message, without the whole instance that combinators (oneOf, anyOf, not) quote."""
    msg = error.message
    inner = _closest(error)
    if inner is not None:
        where = pointer(inner.relative_path)
        return (f"matches none of the allowed forms; closest: {where + ': ' if where else ''}"
                f"{_message(inner)[:MAX_MESSAGE]}")
    if len(msg) <= MAX_MESSAGE:
        return msg
    if error.context:
        inner = best_match(error.context)
        return f"matches none of the allowed forms ({error.validator}); closest: {inner.message[:MAX_MESSAGE]}"
    return msg[:MAX_MESSAGE] + "..."


def schema_violations(spec, registry=None):
    """Every violation of run-spec/1 (and, through it, sensor-spec/1) and of the engine block's adapter schema in a
    parsed spec, as `[{"path": <JSON Pointer>, "message": <text>, "at": <JSON Pointer>}]`, sorted by path then message.
    Empty means the spec conforms. `path` is where the validator reports the violation; `at` is the deepest location
    its message names (the same, except under a oneOf/anyOf, where it is the closest alternative's location), the
    pointer `problems.locate` attributes to a layer file and field."""
    found = {(pointer(e.absolute_path), _message(e), pointer(_at(e))) for e in validator().iter_errors(spec)}
    found |= set(engine_block_violations(spec, registry))
    return [{"path": p, "message": m, "at": a} for p, m, a in sorted(found)]


def conforms(spec, registry=None):
    return not schema_violations(spec, registry)


# Required descriptor members as run-spec-1.schema.json states them (Metadata_v02 §6); kept for callers and tests.
DESCRIPTOR_REQUIRED = ("meta", "origin", "collection", "sensor", "settings", "fidelity")
_MISSING = object()


def _get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return _MISSING
        d = d[k]
    return d


def schema_errors(spec, registry=None):
    """Every schema violation in a parsed run spec (empty list = conformant). See module docstring.

    The published schemas and the engine block's adapter schema (`schema_violations`) as `"<JSON Pointer>: <message>"`,
    in pointer order, then `semantic_errors(spec)`: the rules the schemas cannot express. Duplicates removed.
    """
    msgs = [f"{v['path'] or '/'}: {v['message']}" for v in schema_violations(spec, registry)]
    return list(dict.fromkeys(msgs + semantic_errors(spec, registry)))


def semantic_errors(spec, registry=None):
    """The schema-check rules JSON Schema cannot express:

    - `descriptor.origin.engine` that no registered adapter serves (or whose adapter failed to load), naming the
      registered engines: the engine block cannot be checked or executed;
    - `descriptor.opaque` without `engine.mode: passthrough`, or the reverse (the two schemas cannot see each other);
    - the engine's own rules (`EngineAdapter.semantic_rules`), for example an integer member read from YAML as a float.
    """
    errs = []
    if not isinstance(spec, dict):
        return errs
    engine_id = engine_id_of(spec)
    reg = resolve_registry(registry)
    adapter = reg.find(engine_id) if engine_id is not None else None
    if adapter is not None:
        errs += list(adapter.semantic_rules(spec))
    opaque = _get(spec, ("descriptor", "opaque"))
    mode = _get(spec, ("engine", "mode"))
    if (opaque is not _MISSING) != (mode == "passthrough"):
        errs.append("descriptor.opaque and engine.mode: passthrough go together (an opaque descriptor describes a "
                    "pass-through run, and a pass-through run has an opaque descriptor)")
    if engine_id is not None and adapter is None:
        status = "is not a registered engine" if engine_id not in reg.ids() else \
            f"is unavailable ({reg.status(engine_id).reason})"
        errs.append(f"/descriptor/origin/engine: {engine_id!r} {status}; registered engines: "
                    f"{', '.join(reg.ids()) or 'none'}")
    return errs
