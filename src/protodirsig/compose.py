"""Compose `run-spec/1` documents from layer files (rules version `compose/1`): one run, or a sweep of runs.

A run is authored as layers and composed into the single run spec MANIFOLD receives. This is the reference for
a MANIFOLD input constructor: what composes here, and passes the run-spec checks, is what that constructor
should accept. The conformance vectors in `manifold_contracts/vectors/compose/` are its test.

Layers, under one root (`manifold_run_specs/`), each owning disjoint members of the composed spec:

  recipes/<name>.yaml          compose, meta, settings, fidelity, and the names of the other layers:
                               sensor (a sensor-library file) or sensors (a list: a sweep), scenario,
                               engine_profile; optionally engine_overrides (values for the paths in
                               ENGINE_OVERRIDES) and fidelity_by_sensor
  scenarios/<name>.yaml        collection                  -> descriptor.collection
  engine_profiles/<name>.yaml  origin, extras, engine      -> descriptor.origin, descriptor.extras, engine
  <sensor library>/<file>      the sensor-spec/1 document  -> descriptor.sensor (a ref, or inline)

The sensor library defaults to `manifold_sensors/`, the sibling of the root (as `run_spec.default_sensor_library`).

Rules: a member present in two layers is an error, not a merge, unless it is in `OVERRIDABLE` (empty).
`engine_overrides` maps a dotted path under `engine` to a value; only paths in `ENGINE_OVERRIDES` are allowed, and
the path's parent must be a mapping the engine profile holds (the leaf itself may be absent).

A recipe names `sensor` (one run) or `sensors` (a sweep: one run per listed sensor), never both. The only axis is
the sensor: no cross product. `settings` is keyed by `entry_id` across the listed sensors; each run takes the
members of its sensor's entries, in the sensor's entry order. A member whose `entry_id` belongs to no listed
sensor, a second member for one entry, a listed sensor with no member, and an `entry_id` shared by two listed
sensors are errors. A sweep run's `meta.name` is `<meta.name>--<sensor file stem>`; tags and description are
shared. `fidelity` is shared; `fidelity_by_sensor: {<sensor file>: {...}}` replaces it for that sensor, and
`fidelity` may be omitted when every listed sensor has one. A sweep has at most `MAX_RUNS` runs, checked before
anything else is loaded. Each run has a `run_id` and the sweep a `sweep_id` (`protodirsig.identity`): the sha256
of the RFC 8785 canonical JSON of the run spec with its sensor in place, and of the sorted list of run ids.

The `roi` check of `run_spec` applies to each composed spec, and for a DIRSIG run the black-level check. No key is
added to the descriptor outside what the layers hold; layer provenance (file and hash per member) and the sweep id
are returned beside the specs, never written into them. Errors name the layer file and the field in it, never a
path in the composed document.

Imports: the standard library, `yaml`, `protodirsig.run_spec` and `protodirsig.spectral`, none of which loads an
engine package, so composing needs no `dirfm`, skyfield or DIRSIG (tests/test_import_boundary.py).
"""
import copy
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from protodirsig import identity
from protodirsig.errors import COMPOSE
from protodirsig.run_spec import RunSpecError, _check_settings_roi, black_level_problem, load_sensor_spec
from protodirsig.spectral import sha256_file

RULES = "compose/1"
SPEC_VERSION = "run-spec/1"
MAX_RUNS = 32                                                      # runs per sweep; compose_sweep(max_runs=...)
# Composed member -> the layer that owns it. `descriptor.<m>` unless noted.
OWNER = {"meta": "recipe", "settings": "recipe", "fidelity": "recipe", "sensor": "recipe",
         "collection": "scenario", "origin": "engine_profile", "extras": "engine_profile", "engine": "engine_profile"}
REQUIRED = {"recipe": ("compose", "meta", "sensor", "scenario", "engine_profile", "settings", "fidelity"),
            "scenario": ("collection",), "engine_profile": ("origin", "engine")}
# Recipe keys that are not composed members (`sensors` and `fidelity_by_sensor` are resolved per run first).
CONTROL = {"recipe": ("compose", "scenario", "engine_profile", "engine_overrides", "sensors", "fidelity_by_sensor",
                      "passthrough")}
# The pass-through recipe form (proposed): the recipe names a library demo directory and its simulation file; the
# engine profile holds runtime members only. No scenario, sensor or settings.
PASSTHROUGH_RECIPE = ("compose", "meta", "passthrough", "engine_profile", "fidelity")
PASSTHROUGH_PROFILE = ("origin", "engine")
PASSTHROUGH_ENGINE = ("generator", "run")
OVERRIDABLE = frozenset()                                          # members two layers may both hold; none yet
ENGINE_OVERRIDES = ("platform.channel_response",)                  # engine paths a recipe may set (engine_overrides)
DESCRIPTOR_ORDER = ("meta", "origin", "collection", "sensor", "settings", "fidelity", "extras")
LAYER_DIR = {"scenario": "scenarios", "engine_profile": "engine_profiles"}
HEADER = "# GENERATED by scripts/compose.py from {recipe} - do not edit\n"


class ComposeError(RunSpecError):
    """A layer that does not compose. `layer` is the layer file (root-relative), `field` the field in it. A
    `ProblemError` whose problem is of type compose (422) and names them."""
    TYPE = COMPOSE

    def __init__(self, layer, field, message):
        self.layer, self.field = str(layer), field
        super().__init__(f"{self.layer}: {field}: {message}" if field else f"{self.layer}: {message}")
        self._members.update(layer=self.layer, field=field)


@dataclass
class ComposedSweep:
    """What `compose_sweep` returns. `runs` maps each run's `meta.name` to its spec, in sensor-list order; `files`
    maps it to the generated file's stem, `sensors` to its sensor file, `sources` to its `explain` record, `run_ids`
    to its run id (64 hex digits). `sweep_id` is derived from the sorted run ids (identity.sweep_id_from_runs)."""
    sweep_id: str
    recipe: str                                                    # root-relative recipe file
    is_sweep: bool                                                 # the recipe names `sensors`
    runs: dict = field(default_factory=dict)
    files: dict = field(default_factory=dict)
    sensors: dict = field(default_factory=dict)
    run_ids: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)


def _load_layer(path, rel):
    if not path.is_file():
        raise ComposeError(rel, None, "not found")
    try:
        doc = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise ComposeError(rel, None, f"does not parse: {e}") from e
    if not isinstance(doc, dict):
        raise ComposeError(rel, None, f"expected a mapping, got {type(doc).__name__}")
    return doc


def merge(layers, sensor_ref, sensor_doc=None, inline_sensor=False):
    """One run's composition: `layers` maps `recipe`, `scenario`, `engine_profile` to `(name, doc)`, the recipe
    naming one `sensor`; `sensor_ref` is the `{name, content_hash}` it resolves to, `sensor_doc` the loaded
    sensor-spec (None skips the entry checks, for `run_spec.derive_run_spec`). Returns `(spec, sources)`, `sources`
    mapping each composed member to the layer name it came from."""
    held = {}                                                      # member -> [layer kinds holding it]
    for kind, (name, doc) in layers.items():
        for key in doc:
            if key in CONTROL.get(kind, ()):
                continue
            if key not in OWNER:
                raise ComposeError(name, key, f"unknown key; a {kind.replace('_', ' ')} holds "
                                   f"{sorted(m for m, o in OWNER.items() if o == kind) + list(CONTROL.get(kind, ()))}")
            held.setdefault(key, []).append(kind)
        for key in REQUIRED[kind]:
            if key not in doc:
                raise ComposeError(name, key, "missing")
    for member, kinds in held.items():
        if len(kinds) > 1 and member not in OVERRIDABLE:
            other = next(k for k in kinds if k != OWNER[member])
            raise ComposeError(layers[other][0], member, f"also in {layers[OWNER[member]][0]}; layers own disjoint "
                               f"members (this one belongs to the {OWNER[member].replace('_', ' ')})")
        if kinds[0] != OWNER[member]:
            raise ComposeError(layers[kinds[0]][0], member,
                               f"belongs to the {OWNER[member].replace('_', ' ')}, not the {kinds[0].replace('_', ' ')}")
    recipe_name, recipe = layers["recipe"]
    if recipe["compose"] != RULES:
        raise ComposeError(recipe_name, "compose", f"is {recipe['compose']!r}; this composer implements {RULES!r}")
    meta = recipe["meta"]
    if not isinstance(meta, dict) or not isinstance(meta.get("name"), str):
        raise ComposeError(recipe_name, "meta.name", "missing or not a string")
    settings = recipe["settings"]
    if not isinstance(settings, list) or not all(isinstance(s, dict) for s in settings):
        raise ComposeError(recipe_name, "settings", "must be a list of mappings keyed by entry_id")

    if sensor_doc is not None:
        entries = [e["entry_id"] for e in sensor_doc["sensor"]["entries"]]
        by_entry = {}
        for i, s in enumerate(settings):
            eid = s.get("entry_id")
            if eid not in entries:
                raise ComposeError(recipe_name, f"settings[{i}].entry_id",
                                   f"{eid!r} names no entry of sensor {sensor_ref['name']} ({entries})")
            if eid in by_entry:
                raise ComposeError(recipe_name, f"settings[{i}].entry_id", f"{eid!r} has two settings members")
            by_entry[eid] = s
        settings = [by_entry[e] for e in entries if e in by_entry]
        try:
            _check_settings_roi(settings, sensor_doc)
        except RunSpecError as e:
            raise ComposeError(recipe_name, "settings", str(e)) from e
        sensor = copy.deepcopy(sensor_doc["sensor"]) if inline_sensor else {"ref": dict(sensor_ref)}
    elif inline_sensor:
        raise ValueError("inline_sensor needs the sensor-spec document")
    else:
        sensor = {"ref": dict(sensor_ref)}

    _, scenario = layers["scenario"]
    profile_name, profile = layers["engine_profile"]
    engine = copy.deepcopy(profile["engine"])
    overrides = recipe.get("engine_overrides") or {}
    if not isinstance(overrides, dict):
        raise ComposeError(recipe_name, "engine_overrides", "must be a mapping of engine paths to values")
    for path, value in overrides.items():
        if path not in ENGINE_OVERRIDES:
            raise ComposeError(recipe_name, f"engine_overrides.{path}",
                               f"not an overridable engine path; the rules allow {list(ENGINE_OVERRIDES)}")
        *parents, leaf = path.split(".")
        node = engine
        for key in parents:
            node = node.get(key) if isinstance(node, dict) else None
        if not isinstance(node, dict):
            raise ComposeError(recipe_name, f"engine_overrides.{path}",
                               f"{profile_name} holds no engine.{'.'.join(parents)} to override")
        node[leaf] = copy.deepcopy(value)
    values = {"meta": recipe["meta"], "origin": profile["origin"], "collection": scenario["collection"],
              "sensor": sensor, "settings": settings, "fidelity": recipe["fidelity"]}
    if "extras" in profile:
        values["extras"] = profile["extras"]
    descriptor = {m: copy.deepcopy(values[m]) for m in DESCRIPTOR_ORDER if m in values}
    spec = {"spec_version": SPEC_VERSION, "descriptor": descriptor, "engine": engine}
    sources = {"spec_version": f"rules {RULES}"}
    sources.update({f"descriptor.{m}": layers[OWNER[m]][0] for m in descriptor if m != "sensor"})
    sources["descriptor.sensor"] = sensor_ref["name"]
    sources["engine"] = profile_name
    sources.update({f"engine.{path}": recipe_name for path in overrides})
    order = ("spec_version", *(f"descriptor.{m}" for m in descriptor), "engine", *(f"engine.{p}" for p in overrides))
    return spec, {k: sources[k] for k in order}


def sensor_library_for_root(layer_root):
    """`manifold_sensors/`, the sibling of a layer root (the folder holding `recipes/`, `scenarios/`,
    `engine_profiles/`): the one rule every reader of the library uses."""
    return Path(layer_root).resolve().parent / "manifold_sensors"


def default_sensor_library(recipe_path):
    """`manifold_sensors/`, the sibling of the layer root (the folder holding `recipes/`)."""
    return sensor_library_for_root(Path(recipe_path).resolve().parent.parent)


def sweep_id(recipe_path):
    """The sweep id of a recipe: 64 hex digits, the sha256 of the canonical JSON of the sorted run ids it composes to
    (identity.sweep_id_from_runs). Composes the recipe; a recipe that does not compose raises ComposeError."""
    return compose_sweep(recipe_path).sweep_id


def _sensor_list(recipe, rel, max_runs):
    """(sensor files, is_sweep), checked before any other layer is read."""
    if "sensor" in recipe and "sensors" in recipe:
        raise ComposeError(rel, "sensors", "a recipe names either sensor (one run) or sensors (a sweep), not both")
    if "sensors" not in recipe:
        if not isinstance(recipe.get("sensor"), str):
            raise ComposeError(rel, "sensor", "missing or not a sensor-library file name (or sensors, for a sweep)")
        return [recipe["sensor"]], False
    sensors = recipe["sensors"]
    if not isinstance(sensors, list) or not sensors or not all(isinstance(s, str) for s in sensors):
        raise ComposeError(rel, "sensors", "must be a non-empty list of sensor-library file names")
    if len(sensors) > max_runs:
        raise ComposeError(rel, "sensors", f"{len(sensors)} runs exceed the cap of {max_runs} runs per sweep")
    for j, s in enumerate(sensors):
        if sensors.index(s) != j:
            raise ComposeError(rel, f"sensors[{j}]", f"{s} is listed twice")
    return sensors, True


def _settings_by_sensor(recipe, rel, sensors, docs):
    """Each listed sensor's settings members, in its entry order (see the module rules)."""
    owner, key = {}, ("sensors" if "sensors" in recipe else "sensor")
    for j, s in enumerate(sensors):
        for e in docs[s]["sensor"]["entries"]:
            if e["entry_id"] in owner:
                raise ComposeError(rel, f"{key}[{j}]" if key == "sensors" else key,
                                   f"entry {e['entry_id']!r} of {s} is also an entry of {owner[e['entry_id']]}; "
                                   "entry_ids must be unique across a sweep's sensors")
            owner[e["entry_id"]] = s
    settings = recipe.get("settings")
    if not isinstance(settings, list) or not all(isinstance(m, dict) for m in settings):
        raise ComposeError(rel, "settings", "must be a list of mappings keyed by entry_id")
    by_entry = {}
    for i, m in enumerate(settings):
        eid = m.get("entry_id")
        if eid not in owner:
            raise ComposeError(rel, f"settings[{i}].entry_id",
                               f"{eid!r} names no entry of the listed sensors ({sorted(owner)})")
        if eid in by_entry:
            raise ComposeError(rel, f"settings[{i}].entry_id", f"{eid!r} has two settings members")
        by_entry[eid] = i
    out = {}
    for j, s in enumerate(sensors):
        entries = [e["entry_id"] for e in docs[s]["sensor"]["entries"]]
        out[s] = [settings[by_entry[e]] for e in entries if e in by_entry]
        if not out[s]:
            raise ComposeError(rel, f"{key}[{j}]" if key == "sensors" else key,
                               f"{s} has no settings member (its entries: {entries})")
    return out, by_entry


DOCUMENT_LAYER = "(recipe document)"                               # the `layer` of an error in a recipe given as a dict


def compose_sweep(recipe_path, *, inline_sensor=False, sensor_library=None, max_runs=MAX_RUNS):
    """Every run the recipe composes to: one for a `sensor` recipe, one per listed sensor for a `sensors` recipe.
    Returns a `ComposedSweep` (runs in sensor-list order, the sweep id, file stems, provenance)."""
    recipe_path = Path(recipe_path).resolve()
    root = recipe_path.parent.parent
    recipe_rel = recipe_path.relative_to(root).as_posix()
    recipe = _load_layer(recipe_path, recipe_rel)
    library = Path(sensor_library).resolve() if sensor_library is not None else default_sensor_library(recipe_path)
    return _compose(recipe, root, recipe_rel, recipe_path.stem, sha256_file(recipe_path), library, inline_sensor,
                    max_runs)


def compose_sweep_document(document, library_root, *, inline_sensor=False, sensor_library=None, max_runs=MAX_RUNS):
    """`compose_sweep` for a recipe given as a parsed document (a dict) against a layer root (the folder holding
    `scenarios/` and `engine_profiles/`): the same rules, errors and outputs. An error in the document itself names
    the layer `(recipe document)` and the field; its provenance hash is `sha256:` + the digest of its RFC 8785
    canonical JSON (`identity.canonical_json`)."""
    if not isinstance(document, dict):
        raise ComposeError(DOCUMENT_LAYER, None, f"expected a mapping, got {type(document).__name__}")
    root = Path(library_root).resolve()
    library = Path(sensor_library).resolve() if sensor_library is not None else sensor_library_for_root(root)
    try:
        digest = "sha256:" + identity.sha256_hex(identity.canonical_json(document))
    except (TypeError, ValueError) as e:
        raise ComposeError(DOCUMENT_LAYER, None, f"is not a JSON document: {e}") from e
    name = (document.get("meta") or {}).get("name") if isinstance(document.get("meta"), dict) else None
    stem = name if isinstance(name, str) and name else "recipe"
    return _compose(copy.deepcopy(document), root, DOCUMENT_LAYER, stem, digest, library, inline_sensor, max_runs)


def compose_document(document, library_root, *, inline_sensor=False, sensor_library=None):
    """`compose` for a recipe given as a parsed document: the one run spec of a one-sensor recipe document."""
    sweep = compose_sweep_document(document, library_root, inline_sensor=inline_sensor, sensor_library=sensor_library)
    if sweep.is_sweep:
        raise ComposeError(sweep.recipe, "sensors", "a sweep recipe composes several runs; use compose_sweep_document")
    (name,) = sweep.runs
    return sweep.runs[name]


def _compose(recipe, root, recipe_rel, recipe_stem, recipe_hash, library, inline_sensor, max_runs):
    """The one composition path: a parsed recipe, its layer root, the label and hash its provenance records."""
    rel = lambda p: p.relative_to(root).as_posix()                  # noqa: E731
    if "passthrough" in recipe:
        return _compose_passthrough(recipe, root, recipe_rel, recipe_stem, recipe_hash, library)
    sensors, is_sweep = _sensor_list(recipe, recipe_rel, max_runs)
    files = {}
    layers = {}
    for kind in ("scenario", "engine_profile"):
        name = recipe.get(kind)
        if not isinstance(name, str):
            raise ComposeError(recipe_rel, kind, "missing or not a layer name")
        path = root / LAYER_DIR[kind] / f"{name}.yaml"
        files[kind] = path
        layers[kind] = (rel(path), _load_layer(path, rel(path)))
    docs, key = {}, ("sensors" if is_sweep else "sensor")
    for j, s in enumerate(sensors):
        try:
            docs[s] = load_sensor_spec(library, s)
        except RunSpecError as e:
            raise ComposeError(recipe_rel, f"{key}[{j}]" if is_sweep else key, str(e)) from e
    by_sensor, by_entry = _settings_by_sensor(recipe, recipe_rel, sensors, docs)
    if (layers["engine_profile"][1].get("origin") or {}).get("engine") == "dirsig":
        for i, m in enumerate(recipe["settings"]):
            problem = black_level_problem(m)
            if problem:
                raise ComposeError(recipe_rel, f"settings[{i}].black_level", problem)
    per_sensor = recipe.get("fidelity_by_sensor") or {}
    if not isinstance(per_sensor, dict):
        raise ComposeError(recipe_rel, "fidelity_by_sensor", "must map sensor files to fidelity blocks")
    for s in per_sensor:
        if s not in sensors:
            raise ComposeError(recipe_rel, f"fidelity_by_sensor.{s}", f"names a sensor the recipe does not list ({sensors})")
    if "fidelity" not in recipe and not all(s in per_sensor for s in sensors):
        raise ComposeError(recipe_rel, "fidelity", "missing (fidelity_by_sensor does not cover every listed sensor)")

    out = ComposedSweep("", recipe_rel, is_sweep)
    base = {k: v for k, v in recipe.items() if k not in ("sensor", "sensors", "fidelity_by_sensor", "fidelity")}
    for s in sensors:
        stem = Path(s).stem
        run = copy.deepcopy(base)
        run["sensor"], run["settings"] = s, copy.deepcopy(by_sensor[s])
        run["fidelity"] = copy.deepcopy(per_sensor.get(s, recipe.get("fidelity")))
        if is_sweep and isinstance(run.get("meta"), dict) and isinstance(run["meta"].get("name"), str):
            run["meta"]["name"] = f"{run['meta']['name']}--{stem}"
        ref = {"name": s, "content_hash": sha256_file(library / s)}
        spec, sources = merge({"recipe": (recipe_rel, run), **layers}, ref, docs[s], inline_sensor)
        name = spec["descriptor"]["meta"]["name"]
        hashes = {recipe_rel: recipe_hash, **{layers[k][0]: sha256_file(files[k]) for k in layers},
                  s: sha256_file(library / s)}
        label = f"{library.name}/{s}"
        out.runs[name] = spec
        out.files[name] = f"{recipe_stem}--{stem}" if is_sweep else recipe_stem
        out.sensors[name] = s
        out.sources[name] = {member: {"layer": label if src == s else src, "content_hash": hashes.get(src)}
                             for member, src in sources.items()}
        out.run_ids[name] = identity.run_id(spec, library)
    out.sweep_id = identity.sweep_id_from_runs(out.run_ids.values())
    return out


def _compose_passthrough(recipe, root, recipe_rel, recipe_stem, recipe_hash, library):
    """A pass-through recipe (proposed): one run whose engine block is `mode: passthrough` with the recipe's
    `passthrough` member, the engine profile's runtime members (`generator`, `run`) and an opaque descriptor."""
    for key in recipe:
        if key not in PASSTHROUGH_RECIPE:
            raise ComposeError(recipe_rel, key, f"not part of a pass-through recipe, which holds {list(PASSTHROUGH_RECIPE)}")
    for key in PASSTHROUGH_RECIPE:
        if key not in recipe:
            raise ComposeError(recipe_rel, key, "missing")
    if recipe["compose"] != RULES:
        raise ComposeError(recipe_rel, "compose", f"is {recipe['compose']!r}; this composer implements {RULES!r}")
    meta = recipe["meta"]
    if not isinstance(meta, dict) or not isinstance(meta.get("name"), str):
        raise ComposeError(recipe_rel, "meta.name", "missing or not a string")
    block = recipe["passthrough"]
    if not isinstance(block, dict) or set(block) != {"directory", "simulation"}:
        raise ComposeError(recipe_rel, "passthrough", "must hold directory ({name, content_hash}) and simulation")
    ref = block["directory"]
    if not isinstance(ref, dict) or not isinstance(ref.get("name"), str) or not isinstance(ref.get("content_hash"), str):
        raise ComposeError(recipe_rel, "passthrough.directory", "must be a library ref {name, content_hash}")
    if not isinstance(block["simulation"], str):
        raise ComposeError(recipe_rel, "passthrough.simulation", "must be the simulation file's path in the directory")
    name = recipe["engine_profile"]
    if not isinstance(name, str):
        raise ComposeError(recipe_rel, "engine_profile", "missing or not a layer name")
    path = root / LAYER_DIR["engine_profile"] / f"{name}.yaml"
    profile_rel = path.relative_to(root).as_posix()
    profile = _load_layer(path, profile_rel)
    for key in profile:
        if key not in PASSTHROUGH_PROFILE:
            raise ComposeError(profile_rel, key, f"not part of a pass-through engine profile, which holds "
                               f"{list(PASSTHROUGH_PROFILE)}")
    for key in PASSTHROUGH_PROFILE:
        if key not in profile:
            raise ComposeError(profile_rel, key, "missing")
    engine_in = profile["engine"]
    if not isinstance(engine_in, dict):
        raise ComposeError(profile_rel, "engine", "must be a mapping")
    for key in engine_in:
        if key not in PASSTHROUGH_ENGINE:
            raise ComposeError(profile_rel, f"engine.{key}", f"a pass-through engine profile holds runtime members "
                               f"only ({list(PASSTHROUGH_ENGINE)}); the demo directory supplies the rest")
    if "generator" not in engine_in:
        raise ComposeError(profile_rel, "engine.generator", "missing")
    engine = {"generator": copy.deepcopy(engine_in["generator"]), "mode": "passthrough",
              "passthrough": copy.deepcopy(block)}
    if "run" in engine_in:
        engine["run"] = copy.deepcopy(engine_in["run"])
    descriptor = {"meta": copy.deepcopy(meta), "origin": copy.deepcopy(profile["origin"]),
                  "fidelity": copy.deepcopy(recipe["fidelity"]), "opaque": {"source": "passthrough"}}
    spec = {"spec_version": SPEC_VERSION, "descriptor": descriptor, "engine": engine}
    hashes = {recipe_rel: recipe_hash, profile_rel: sha256_file(path)}
    labels = {"spec_version": f"rules {RULES}", "descriptor.meta": recipe_rel, "descriptor.origin": profile_rel,
              "descriptor.fidelity": recipe_rel, "descriptor.opaque": f"rules {RULES}", "engine": profile_rel,
              "engine.passthrough": recipe_rel}
    run = meta["name"]
    out = ComposedSweep("", recipe_rel, False)
    out.runs[run] = spec
    out.files[run] = recipe_stem
    out.sensors[run] = None
    out.sources[run] = {m: {"layer": src, "content_hash": hashes.get(src)} for m, src in labels.items()}
    out.run_ids[run] = identity.run_id(spec, library)
    out.sweep_id = identity.sweep_id_from_runs(out.run_ids.values())
    return out


def _single(recipe_path, inline_sensor, sensor_library):
    sweep = compose_sweep(recipe_path, inline_sensor=inline_sensor, sensor_library=sensor_library)
    if sweep.is_sweep:
        raise ComposeError(sweep.recipe, "sensors", "a sweep recipe composes several runs; use compose_sweep")
    (name,) = sweep.runs
    return sweep.runs[name], sweep.sources[name]


def compose(recipe_path, *, inline_sensor=False, sensor_library=None):
    """The `run-spec/1` dict a one-run recipe composes to. `descriptor.sensor` is `{ref: {name, content_hash}}` (the
    hash of the sensor file's bytes), or the sensor-spec's `sensor` block in place with `inline_sensor`. A sweep
    recipe (`sensors`) raises; use `compose_sweep`."""
    return _single(recipe_path, inline_sensor, sensor_library)[0]


def explain(recipe_path, *, sensor_library=None):
    """Each member of a one-run recipe's spec with the layer file it came from and that file's sha256:
    `{member: {"layer": <root-relative file>, "content_hash": ...}}`. For a sweep, `compose_sweep(...).sources`."""
    return _single(recipe_path, False, sensor_library)[1]


def dump(spec, recipe_rel):
    """The generated file's text: the header line, then the spec. The same spec gives the same bytes."""
    return HEADER.format(recipe=recipe_rel) + "\n" + yaml.safe_dump(spec, sort_keys=False, allow_unicode=True,
                                                                     width=110, default_flow_style=False)
