"""The published contract schemas, applied: `run-spec/1`, `dirsig-engine/1` and `sensor-spec/1` from `manifold_contracts/`.

`schema_violations(spec)` validates a parsed run spec against `manifold_contracts/run-spec-1.schema.json` (which
references the engine and sensor-spec schemas) and returns every violation as `{path, message, at}`, `path` and `at`
RFC 6901 JSON Pointers into the spec. `simulation.schema_errors` formats these as its schema-check messages, so admission
enforces the schemas.

The schemas are read from the first of: the folder named by the environment variable `PROTODIRSIG_CONTRACTS`; the
copy packaged with the library, `protodirsig/_contracts/` (found with `importlib.resources`; the build copies the three
files there from `manifold_contracts/`, see `setup.py`, and a checkout or editable install has none); the repository's
`manifold_contracts/` folder, the sibling of `src/` (as `run_spec.default_sensor_library` locates
`manifold_sensors/`). `manifold_contracts/` is the one tracked copy. Each schema's `$id` is an absolute URI under https://schemas.manifold.example/contracts/, a base
that does not resolve on the network; references between the three schemas are sibling file names resolved against it,
and a `referencing` registry holds each file under its `$id` (and retrieves by file name), so everything resolves offline.

`schema_errors(spec)` is the SDK's schema check: each violation as `"<JSON Pointer>: <message>"`, then
`semantic_errors(spec)`, the rules the schemas cannot express. It lives here, with the constants `DESCRIPTOR_REQUIRED`,
`ENGINE_REQUIRED` and `ENGINE_ENUMS`, so engine-free validation (`admission`) needs no engine package; `simulation`
re-exports them.

Imports: the standard library, `jsonschema` and `referencing` only; no engine package and nothing from `simulation`.
"""
import json
import os
from functools import lru_cache
from importlib import resources
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

SCHEMA_FILES = ("run-spec-1.schema.json", "dirsig-engine-1.schema.json", "sensor-spec-1.schema.json")
ROOT_SCHEMA = "run-spec-1.schema.json"
MAX_MESSAGE = 200


def packaged_contracts_dir():
    """The schemas packaged with the library (`protodirsig/_contracts/`, copied there by the build), or None in a
    checkout or editable install, which has no packaged copy."""
    folder = resources.files("protodirsig") / "_contracts"
    try:
        if folder.joinpath(ROOT_SCHEMA).is_file():
            return Path(str(folder))
    except (FileNotFoundError, NotADirectoryError):
        pass
    return None


def contracts_dir():
    """The folder holding the contract schemas, in this order: `$PROTODIRSIG_CONTRACTS`; the packaged copy
    (`packaged_contracts_dir`); the repository's `manifold_contracts/`."""
    env = os.environ.get("PROTODIRSIG_CONTRACTS")
    if env:
        return Path(env)
    return packaged_contracts_dir() or Path(__file__).resolve().parents[2] / "manifold_contracts"


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


def schema_violations(spec):
    """Every violation of run-spec/1 (and, through it, dirsig-engine/1 and sensor-spec/1) in a parsed spec, as
    `[{"path": <JSON Pointer>, "message": <text>, "at": <JSON Pointer>}]`, sorted by path then message. Empty means
    the spec conforms. `path` is where the validator reports the violation; `at` is the deepest location its message
    names (the same, except under a oneOf/anyOf, where it is the closest alternative's location), the pointer
    `problems.locate` attributes to a layer file and field."""
    found = {(pointer(e.absolute_path), _message(e), pointer(_at(e))) for e in validator().iter_errors(spec)}
    return [{"path": p, "message": m, "at": a} for p, m, a in sorted(found)]


def conforms(spec):
    return validator().is_valid(spec)


# Required members and enumerations as the schemas in manifold_contracts/ state them (Metadata_v02 §6, Configuration_v02
# A.8.1); kept for callers and tests. The schema check itself is schema_violations.
DESCRIPTOR_REQUIRED = ("meta", "origin", "collection", "sensor", "settings", "fidelity")
ENGINE_REQUIRED = ("generator", "scenes", "platform", "motion", "tasks", "atmosphere")
# Enumerated engine fields (A.8.2-A.8.7). `new_atmosphere` is the documented, non-adopted
# extension (CONOPS and Guide §10); A.8.7 adopts only `four_curve` and `basic`.
ENGINE_ENUMS = {
    ("generator", "tool"): {"dirfm"},
    ("generator", "spec_schema"): {"dirsig-engine/1"},
    ("motion", "kind"): {"static", "waypoints", "orbit"},
    ("motion", "orientation", "kind"): {"euler", "lookat"},
    ("motion", "orbit", "propagator"): {"skyfield_sgp4"},           # the orbit form (proposed, CONOPS §3.2)
    ("motion", "orientation", "lookat", "frame"): {"sceneenu"},
    ("motion", "orientation", "lookat", "up"): {"along_track"},
    ("atmosphere", "plugin"): {"four_curve", "basic", "new_atmosphere"},
    ("weather", "source"): {"library", "install"},
    ("ephemeris", "plugin"): {"spice"},
}
_MISSING = object()


def _get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return _MISSING
        d = d[k]
    return d


def schema_errors(spec):
    """Every schema violation in a parsed run spec (empty list = conformant). See module docstring.

    The published schemas (`manifold_contracts/run-spec-1.schema.json` with `dirsig-engine-1.schema.json` and
    `sensor-spec-1.schema.json`, applied by `contract.schema_violations`) as `"<JSON Pointer>: <message>"`, in
    pointer order, then `semantic_errors(spec)`: the rules the schemas cannot express. Duplicates removed.
    """
    msgs = [f"{v['path'] or '/'}: {v['message']}" for v in schema_violations(spec)]
    return list(dict.fromkeys(msgs + semantic_errors(spec)))


def semantic_errors(spec):
    """The schema-check rules JSON Schema cannot express (the loader enforces the others at resolution):

    - an integer member read from YAML as a float (`engine.run.seed`, `engine.platform.integration_samples`):
      JSON Schema's `integer` accepts 42.0, the generator needs an integer;
    - `descriptor.origin.engine` other than `dirsig`: the schemas type the engine block only for dirsig, and this SDK
      checks and executes only `dirsig-engine/1` runs.
    """
    errs = []
    eng = spec.get("engine") if isinstance(spec, dict) else None
    if isinstance(eng, dict):
        seed = _get(eng, ("run", "seed"))
        if isinstance(seed, float):
            errs.append(f"engine.run.seed is {seed!r}, expected an integer")
        samples = _get(eng, ("platform", "integration_samples"))
        if isinstance(samples, float):
            errs.append(f"engine.platform.integration_samples is {samples!r}, expected an integer >= 1")
    origin = _get(spec, ("descriptor", "origin", "engine")) if isinstance(spec, dict) else _MISSING
    if origin is not _MISSING and origin in ("satsim", "usd", "field"):
        errs.append(f"descriptor.origin.engine is {origin!r}; this SDK checks and executes only dirsig runs "
                    "(dirsig-engine/1)")
    return errs
