"""Problem details (RFC 9457) for the SDK's errors, naming the authored file and field at fault (R-08).

Every constructor returns a dict that conforms to `api/schemas/problem.schema.json`, with the problem URNs that schema
defines. An error caused by an authored file names that file (`layer`, root-relative like the composer's provenance:
`recipes/<name>.yaml`, `scenarios/...`, `engine_profiles/...`, or `<sensor library>/<file>`) and the field in it
(`field`: a dotted path with list indices in brackets, relative to that file's own structure).

`locate(pointer, sources)` maps an RFC 6901 pointer into a composed run spec to `(layer, field)` with the provenance
the composer returns (`compose_sweep(...).sources[run]` or `compose.explain(...)`), which names the layer that owns
each top-level member. Each layer's key layout (`compose.merge`):

  recipe          meta, settings, fidelity (or fidelity_by_sensor.<sensor file>), sensor or sensors[j], and
                  engine_overrides.<path> for each overridden engine path
  scenario        collection
  engine profile  origin, extras, engine
  sensor file     sensor (the sensor-spec's `sensor` block, inline in the spec or materialized from the reference)

`spec_version` is set by the composition rules, not by a file. A recipe field whose place depends on the recipe's
layout (a settings member's index, which the composer reorders by sensor entry; `fidelity` against
`fidelity_by_sensor`; `sensor` against `sensors[j]`) is named only when the recipe document is given (`recipe=`, a
dict or a path); otherwise the recipe file is named with `field` None. A pointer no layer owns gives `(None, None)`:
nothing is guessed.

The pointers come from three places: a schema violation (`contract.schema_violations`, its `at`), a resolution failure
(`run_spec.RunSpecError.pointer`: a reference's `name` for a missing file, its `content_hash` for a mismatch) and an
unstamped member (`run_spec.unstamped_refs`). An execution failure (`execution_failed`, status 500) and an unknown id
(`not_found`, 404) name no authored file. `errors.ProblemError` and its subclasses carry these dicts as exceptions.

Imports: the standard library, `yaml`, `protodirsig.contract` and `protodirsig.run_spec` only; no engine package.
"""
import re
from pathlib import Path

import yaml

from protodirsig.contract import schema_violations
from protodirsig.run_spec import unstamped_refs

COMPOSE = "urn:protodirsig:problem:compose"
ADMISSION = "urn:protodirsig:problem:admission"
NOT_FOUND = "urn:protodirsig:problem:not-found"
INVALID_REQUEST = "urn:protodirsig:problem:invalid-request"
EXECUTION = "urn:protodirsig:problem:execution"
TITLES = {COMPOSE: "The recipe does not compose", ADMISSION: "The submission failed admission",
          NOT_FOUND: "Not found", INVALID_REQUEST: "The request is not valid",
          EXECUTION: "The run failed while executing"}
NO_LAYER = (NOT_FOUND, EXECUTION)                   # kinds of problem no authored file causes
DESCRIPTOR_MEMBERS = ("meta", "origin", "collection", "sensor", "settings", "fidelity", "extras")


def parse_pointer(pointer):
    """The reference tokens of an RFC 6901 pointer (`""` and `"/"` are the whole document)."""
    if pointer in ("", "/"):
        return []
    if not pointer.startswith("/"):
        raise ValueError(f"{pointer!r} is not a JSON Pointer")
    return [t.replace("~1", "/").replace("~0", "~") for t in pointer[1:].split("/")]


def field_path(tokens, doc=None):
    """A dotted field path with list indices in brackets. A token indexes a list when `doc` (the document the
    tokens walk) holds a list there; without `doc`, a token of digits is taken as an index."""
    out, node = "", doc
    for t in tokens:
        is_index = isinstance(node, list) if doc is not None else str(t).isdigit()
        out += f"[{t}]" if is_index else (f".{t}" if out else str(t))
        if doc is not None:
            try:
                node = node[int(t)] if isinstance(node, list) else node[t]
            except (KeyError, IndexError, TypeError, ValueError):
                doc = node = None                       # past the document: fall back to digits for the rest
    return out


def _layer(sources, member):
    entry = (sources or {}).get(member)
    if isinstance(entry, dict):
        entry = entry.get("layer")
    return entry if isinstance(entry, str) else None


def _load_recipe(recipe):
    if recipe is None or isinstance(recipe, dict):
        return recipe
    return yaml.safe_load(Path(recipe).read_text())


def _sensor_file(sources, spec):
    ref = ((spec or {}).get("descriptor") or {}).get("sensor")
    if isinstance(ref, dict) and isinstance(ref.get("ref"), dict) and isinstance(ref["ref"].get("name"), str):
        return ref["ref"]["name"]
    label = _layer(sources, "descriptor.sensor")
    return label.rsplit("/", 1)[-1] if label else None


def _settings_index(spec, recipe, i):
    """The recipe's settings index of the composed spec's settings member `i`, by its entry_id."""
    try:
        eid = spec["descriptor"]["settings"][int(i)]["entry_id"]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    hits = [j for j, m in enumerate(recipe.get("settings") or []) if isinstance(m, dict) and m.get("entry_id") == eid]
    return hits[0] if len(hits) == 1 else None


def locate(pointer, sources, *, spec=None, recipe=None):
    """`(layer, field)` for a pointer into a composed run spec, from the composer's provenance `sources`; `(None,
    None)` when no single file can be named. `spec` (the composed spec the pointer walks) tells list indices from keys
    and names the run's sensor; `recipe` (the recipe document, or its path) places recipe fields whose position the
    composer changes. See the module docstring for each layer's layout."""
    tokens = parse_pointer(pointer)
    if not tokens or not sources:
        return None, None
    walk = lambda prefix, rest: field_path(rest, _sub(spec, prefix))      # noqa: E731
    if tokens[0] == "engine":
        for member in sorted((m for m in sources if m.startswith("engine.")), key=len, reverse=True):
            path = member.split(".")[1:]
            if tokens[1:1 + len(path)] == path:             # an engine_overrides path: the recipe holds the value
                layer = _layer(sources, member)
                rest = tokens[1 + len(path):]
                return layer, f"engine_overrides.{'.'.join(path)}" + (("." + walk(tokens[:1 + len(path)], rest))
                                                                      if rest else "")
        layer = _layer(sources, "engine")
        return (layer, walk([], tokens)) if layer else (None, None)
    if tokens[0] != "descriptor" or len(tokens) < 2 or tokens[1] not in DESCRIPTOR_MEMBERS:
        return None, None                                   # spec_version (the rules), the root, an unowned key
    member, rest = tokens[1], tokens[2:]
    layer = _layer(sources, f"descriptor.{member}")
    if layer is None:
        return None, None
    doc = _load_recipe(recipe)
    if member == "sensor":
        if rest[:1] == ["ref"]:                             # the reference is written by the composer from the recipe
            if rest[1:2] != ["name"]:
                return layer, None
            recipe_layer = _layer(sources, "descriptor.meta")
            if doc is None:
                return recipe_layer, None
            if "sensors" in doc:
                s = _sensor_file(sources, spec)
                hits = [j for j, x in enumerate(doc["sensors"]) if x == s]
                return recipe_layer, (f"sensors[{hits[0]}]" if len(hits) == 1 else None)
            return recipe_layer, "sensor"
        return layer, walk(["descriptor"], ["sensor", *rest])   # the sensor-spec file holds the block under `sensor`
    if member == "settings":
        if not rest:
            return layer, "settings"
        if doc is None:
            return layer, None
        j = _settings_index(spec, doc, rest[0])
        if j is None:
            return layer, None
        tail = walk(["descriptor", "settings", rest[0]], rest[1:])
        return layer, f"settings[{j}]" + (("." + tail) if tail and not tail.startswith("[") else tail)
    if member == "fidelity":
        if doc is None:
            return layer, None
        s = _sensor_file(sources, spec)
        head = ["fidelity_by_sensor", s] if s in (doc.get("fidelity_by_sensor") or {}) else ["fidelity"]
        tail = walk(["descriptor", "fidelity"], rest)
        return layer, ".".join(head) + (("." + tail) if tail and not tail.startswith("[") else tail)
    return layer, walk(["descriptor"], [member, *rest])  # meta (recipe), collection, origin, extras: same key


def _sub(spec, prefix):
    node = spec
    for t in prefix:
        if isinstance(node, list):
            try:
                node = node[int(t)]
            except (IndexError, ValueError):
                return None
        elif isinstance(node, dict) and t in node:
            node = node[t]
        else:
            return None
    return node


def _problem(type_, status, detail, instance=None, layer=None, field=None, errors=None):
    out = {"type": type_, "title": TITLES[type_], "status": status, "detail": detail}
    if instance is not None:
        out["instance"] = instance
    if type_ not in NO_LAYER:
        out["layer"], out["field"] = layer, field
    if errors is not None:
        out["errors"] = errors
    return out


def from_compose_error(exc, instance=None):
    """The problem for a `compose.ComposeError`: the layer file and field it names, its message as `detail`."""
    return _problem(COMPOSE, 422, str(exc), instance, getattr(exc, "layer", None), getattr(exc, "field", None))


def _where(layer, field, pointer):
    if layer and field:
        return f"{layer}: {field}"
    if layer:
        return f"{layer} (at {pointer or '/'} in the composed run spec)"
    return f"the composed run spec at {pointer or '/'}"


_CLOSEST = re.compile(r"^matches none of the allowed forms; closest: (?:/[^:]*: )?")


def _innermost(message):
    """A oneOf/anyOf message without its wrapper: the closest alternative's own message (whose location `at` names)."""
    while _CLOSEST.match(message):
        message = _CLOSEST.sub("", message, count=1)
    return message


def from_schema_violations(spec, sources, violations, instance=None, *, recipe=None):
    """The admission problem for a run spec that violates the contract schemas. `violations` is
    `contract.schema_violations(spec)` (or the same shape); `sources` the run's composer provenance, or None for a
    spec that was not composed here. `detail` names the first violation by file and field; `errors` lists each
    violation as `{run, detail, layer, field}`, `run` the spec's `meta.name`."""
    run = (((spec or {}).get("descriptor") or {}).get("meta") or {}).get("name") or "run spec"
    doc = _load_recipe(recipe)
    errors = []
    for v in violations:
        at = v.get("at", v.get("path", ""))
        layer, field = locate(at, sources, spec=spec, recipe=doc)
        errors.append({"run": run, "detail": f"{_where(layer, field, at)}: {_innermost(v['message'])}",
                       "layer": layer, "field": field})
    if not errors:
        raise ValueError("no violations: the spec conforms, so there is no problem to report")
    first = errors[0]
    more = f" ({len(errors) - 1} more in `errors`)" if len(errors) > 1 else ""
    return _problem(ADMISSION, 422, f"Run {run} is not valid run-spec/1: {first['detail']}{more}", instance,
                    first["layer"], first["field"], errors)


def from_submission(result, sources=None, instance=None, *, recipe=None):
    """The one problem for a rejected `registry.SubmissionResult` (None for an accepted one): the compose problem when
    `submit_recipe`'s recipe did not compose; otherwise an admission problem with the reasons
    (schema, resolution, stamp and execution) in `detail`; `layer` and `field` from the first schema violation, else
    the first unstamped reference, when `sources` attributes it. `sources` and `recipe` default to the result's own
    (`SubmissionResult.sources`, `.recipe`, set when the SDK composed the spec)."""
    if getattr(result, "accepted", False):
        return None
    if getattr(result, "compose_error", None) is not None:
        return from_compose_error(result.compose_error, instance)
    sources = sources if sources is not None else getattr(result, "sources", None)
    recipe = recipe if recipe is not None else getattr(result, "recipe", None)
    sim = getattr(result, "simulation", None)
    spec = getattr(sim, "spec", None)
    layer = field = None
    if isinstance(spec, dict) and sources:
        doc = _load_recipe(recipe)
        resolution = getattr(getattr(sim, "resolve_exception", None), "pointer", None)
        pointers = [v["at"] for v in schema_violations(spec)] or ([resolution] if resolution else []) or \
            [p if p.endswith("/revision") else p + "/content_hash" for p in unstamped_refs(spec)]
        if pointers:
            layer, field = locate(pointers[0], sources, spec=spec, recipe=doc)
    detail = " ".join(result.reasons) or f"The submission was {result.verdict}."
    return _problem(ADMISSION, 422, detail, instance, layer, field)


def from_resolution_error(exc, spec, sources, recipe=None, instance=None):
    """The admission problem for a reference that does not resolve (a `run_spec.RunSpecError` raised while resolving
    `spec`): `layer` and `field` from the exception's `pointer` through `locate` when the SDK composed the spec
    (`sources`), else null. Nothing is guessed: an error with no pointer, or a member no layer owns, names no file."""
    pointer = getattr(exc, "pointer", None)
    layer, field = locate(pointer, sources, spec=spec, recipe=recipe) if pointer and sources else (None, None)
    run = (((spec or {}).get("descriptor") or {}).get("meta") or {}).get("name") or "run spec"
    where = f" ({layer}: {field})" if layer and field else (f" ({layer})" if layer else "")
    return _problem(ADMISSION, 422, f"Run {run}: a reference does not resolve{where}: {exc}", instance, layer, field)


def admission(detail, instance=None, layer=None, field=None):
    """A plain admission problem (422) for a failed check with no richer constructor (a library-file problem, a
    semantic rule)."""
    return _problem(ADMISSION, 422, detail, instance, layer, field)


def from_validation(report, sources=None, recipe=None, instance=None):
    """The one admission problem for an `admission.ValidationReport` that does not admit (not valid, or an unstamped
    member): every reason in `detail`; `layer` and `field` from the first schema violation, else the resolution
    failure's pointer, else the first unstamped member, when `sources` attributes it. None if the report admits."""
    spec = report.spec
    if report.valid and not report.unstamped:
        return None
    run = (((spec or {}).get("descriptor") or {}).get("meta") or {}).get("name") if isinstance(spec, dict) else None
    reasons = []
    if report.schema_errors:
        reasons.append("Schema check failed: " + "; ".join(report.schema_errors))
    if report.resolution_mismatches:
        reasons.append("Resolution check failed: " + "; ".join(report.resolution_mismatches))
    if report.unstamped:
        reasons.append(f"Stamp check failed: {', '.join(report.unstamped)} carry a placeholder instead of a stamped "
                       "value; run scripts/stamp_hashes.py (and scripts/compose.py for a composed spec)")
    layer = field = None
    if isinstance(spec, dict) and sources:
        try:
            schema = [v["at"] for v in schema_violations(spec)]
        except Exception:  # noqa: BLE001
            schema = []
        resolution = getattr(report.resolve_exception, "pointer", None)
        pointers = schema or ([resolution] if resolution else []) or \
            [p if p.endswith("/revision") else p + "/content_hash" for p in report.unstamped]
        if pointers:
            layer, field = locate(pointers[0], sources, spec=spec, recipe=_load_recipe(recipe))
    return _problem(ADMISSION, 422, f"Run {run or '(unnamed)'} failed admission. " + " ".join(reasons), instance,
                    layer, field)


def execution_failed(run_id, name, message, instance=None):
    """The problem for an accepted run that failed while executing (the engine, the worker or the host): status 500,
    no authored file."""
    return _problem(EXECUTION, 500, f"Run {name} ({run_id}) failed while executing: {message}", instance)


def invalid_request(detail, instance=None, layer=None, field=None):
    """The problem for a request the SDK cannot act on as given (for example a sweep recipe sent to `submit_run`)."""
    return _problem(INVALID_REQUEST, 422, detail, instance, layer, field)


def not_found(kind, identifier, instance=None):
    """The problem for an unknown id or name: `kind` is what was looked up (`run`, `sweep`, `recipe`, ...)."""
    return _problem(NOT_FOUND, 404, f"No {kind} {identifier!r}.", instance)
