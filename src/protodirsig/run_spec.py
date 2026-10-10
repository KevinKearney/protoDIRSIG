"""Read the AUROR_ref job's references from a MANIFOLD run-spec YAML.

Narrow and tree-specific by design: this resolves `manifold_run_specs/auror_ref.yaml` for the stage notebooks
(`notebooks/stage_NN_*.ipynb`). It is not a `dirsig-engine/1` interpreter.

Two resolution roots, one per kind of thing referenced:
- `config_repo`: the engine-asset library (CONOPS and Guide §5; Configuration_v02 A.8)
  for `engine.scenes`, `platform`, `atmosphere.database` and `weather.file`. Each ref name is a path
  under it, with no fallback search.
- `sensor_library`: the sensor library (`manifold_sensors/`), for the `descriptor.sensor` ref (see below).
Nothing resolves against a received run tree. MANIFOLD has none: the executor materializes a fresh
run tree from the run spec for every run (Configuration_v02 §2).

`descriptor.sensor` is a `sensor-spec/1` ref (CONOPS and Guide §4), or the sensor-spec's `sensor` block in place
(`compose(..., inline_sensor=True)`). Unlike every `engine` ref, the ref resolves against `sensor_library`, not
`config_repo`. The ref name is a path under the library (`auror-nir.yaml`). The default library is
`manifold_sensors/`, a sibling of the folder holding the run spec; an inline block still takes its spectral curves
from it. The sensor is loaded and checked here, and `platform_gen` renders the job's `.platform` from it and the
run spec's `settings`.

What it drives: `engine.scenes`, `platform`, `atmosphere`, `weather`, `ephemeris` and
`run.seed` name existing library files that the `scene_ref`, `platform_ref` and
`atmosphere_patches` helpers reference as-is. `engine.motion` and `engine.tasks` are generated,
not resolved: `AurorRun` carries their values, and `motion_tasks` writes the `.ppd` and `.tasks`
files from them. Two motion forms are generated: `kind: static` with a scene-frame position and a `sceneenu`
Euler orientation (a `.ppd`), and `kind: orbit` (proposed): a TLE propagated over a window into ECEF waypoints,
pointed by a LookAt at a scene ENU point with the along-track `up` (a FlexMotion `.motion`). Anything else is
refused. The orbit form's TLE and Earth-orientation tables are library files under `config_repo` (`orbit/`),
hash-verified like every other engine ref.

Imports: the standard library, `yaml`, `lxml`, `protodirsig.spectral` and `protodirsig.dirhash` only. The `dirfm`-bound plugin classes
(`atmosphere_patches`, `platform_ref`) are imported inside `AurorRun.atmosphere_plugin` and `ephemeris_plugin`, the
only places a job's plugins are built, so loading, resolving, checking and composing a run spec load no engine
package (tests/test_import_boundary.py).

Loading is a plain `yaml.safe_load`. `AV_MANIFOLD_Metadata_v02.md` §6.15 specifies a strict
loader (duplicate-key rejection, canonical-JSON hashing, unknown-key rejection). That belongs to
MANIFOLD's registry side, which is not built yet, so it is not built here: a duplicated key in the
YAML silently keeps the last value, and no `content_hash` is computed canonically. A stamped hash
(`scripts/stamp_hashes.py`) is verified when the reference is resolved: on a file ref the sha256 of the file bytes, on
a `.scene` ref the `dirhash/1` digest of the scene directory (`protodirsig.dirhash`), since the geometry and materials
sit beside the `.scene` file. The `sha256:<hash>` placeholder is not verified.
"""
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import lxml.etree as et
import yaml

from protodirsig.dirhash import directory_digest
from protodirsig.spectral import PLACEHOLDER, sha256_file

# dirfm-bound names, imported only when a job is built (AurorRun.atmosphere_plugin, ephemeris_plugin), so loading,
# resolving and composing a run spec needs no engine package. `from protodirsig.run_spec import <name>` still works.
_ENGINE_BOUND = {"PatchedModtranTapeBackend": "protodirsig.atmosphere_patches",
                 "PatchedNewAtmospherePlugin": "protodirsig.atmosphere_patches",
                 "SpiceEphemerisPlugin": "protodirsig.platform_ref"}


def __getattr__(name):                         # PEP 562: the engine-bound names, loaded on first use
    if name in _ENGINE_BOUND:
        import importlib
        return getattr(importlib.import_module(_ENGINE_BOUND[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# The received jsim's MODTRAN-tape recipe: what atm_builder would use to rebuild the database.
# The render reads the existing HDF5 database, not this block, and the run
# spec has no field for it, so it is fixed here as part of the `new_atmosphere` special case.
AUROR_ATMOSPHERE_BACKEND = {"profile": "New Profile", "atmospheric_model": "MidLatitudeSummer",
                            "boundary_aerosol_model": "RuralVis23Km", "multiple_scattering": "Isaac"}


class RunSpecError(ValueError):
    """The run spec asks for something this tree-specific loader does not handle."""


def load_run_spec(path):
    """Parse a run-spec YAML into plain dicts and lists (no schema validation; see module docstring)."""
    spec = yaml.safe_load(Path(path).read_text())
    if not isinstance(spec, dict) or spec.get("spec_version") != "run-spec/1":
        raise RunSpecError(f"{path}: expected a run-spec/1 document, got spec_version "
                           f"{spec.get('spec_version') if isinstance(spec, dict) else spec!r}")
    return spec


def load_sensor_spec(sensor_library, sensor_ref_name):
    """Load the `sensor-spec/1` document `sensor_ref_name` names, resolved against `sensor_library`. Returns the whole document, as `load_run_spec` does. Raises `RunSpecError` if the
    file is missing, does not parse, is not `sensor-spec/1`, or has no `sensor` mapping."""
    path = Path(sensor_library) / sensor_ref_name
    if not path.is_file():
        raise RunSpecError(f"sensor {sensor_ref_name!r} not found in the sensor library ({path})")
    try:
        doc = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise RunSpecError(f"sensor {sensor_ref_name!r} does not parse: {e}") from e
    version = doc.get("spec_version") if isinstance(doc, dict) else doc
    if version != "sensor-spec/1":
        raise RunSpecError(f"sensor {sensor_ref_name!r}: expected a sensor-spec/1 document, got spec_version {version!r}")
    if not isinstance(doc.get("sensor"), dict):
        raise RunSpecError(f"sensor {sensor_ref_name!r}: sensor-spec/1 document has no `sensor` mapping")
    return doc


@dataclass(frozen=True)
class AurorRun:
    """The run spec's values: engine assets resolved to manifold_config_repo files, and the values the
    motion and tasks files are generated from (`motion_tasks`)."""
    name: str
    origin: dict
    scene: Path
    scene_offset: list
    platform: Path
    motion_position: list    # engine.motion.position.xyz, scene frame, metres
    motion_orientation: dict # engine.motion.orientation.euler: order, units, angles (frame is sceneenu)
    tasks_windows: list      # [(start, stop)] seconds relative to `epoch`
    epoch: datetime          # descriptor.collection.epoch, timezone-aware UTC
    output_prefix: str
    split_channels: bool
    integration_samples: int
    atmosphere_db: Path
    weather: Path
    ephemeris: str
    seed: int
    sensor: dict             # the loaded sensor-spec/1 document; `platform_gen` renders the job's .platform from it
    settings: list           # descriptor.settings: one member, for the sensor entry the job models
    sensor_library: Path     # resolution root for the sensor-spec and its spectral curves
    channel_response: str = "tabulated"   # engine.platform.channel_response: tabulated | native (platform_gen)
    motion_kind: str = "static"           # engine.motion.kind: static | orbit
    orbit: dict | None = None             # kind orbit: tle, earth_orientation (Paths), propagator, window_start,
                                          # window_duration, waypoint_spacing (s), lookat_target (scene ENU, m),
                                          # up ("along_track"), scene_origin (lat, lon deg, from the .scene)

    def atmosphere_plugin(self, db=None):
        """`NewAtmosphere` over `db`, or over the resolved library database if not given. Pass the job's
        copy of the database so the jsim references it rather than the read-only original."""
        from protodirsig.atmosphere_patches import PatchedModtranTapeBackend, PatchedNewAtmospherePlugin
        b = AUROR_ATMOSPHERE_BACKEND
        backend = (PatchedModtranTapeBackend().set_profile(b["profile"])
                   .set_atmospheric_model(b["atmospheric_model"])
                   .set_boundary_aerosol_model(b["boundary_aerosol_model"])
                   .set_multiple_scattering(b["multiple_scattering"]))
        return (PatchedNewAtmospherePlugin(Path(db) if db is not None else self.atmosphere_db)
                .set_backend(backend).set_info("", "", "", ""))

    def ephemeris_plugin(self):
        from protodirsig.platform_ref import SpiceEphemerisPlugin
        return SpiceEphemerisPlugin()


def _root_file(root, rel, what, ref=None):
    path = root / rel
    if not path.is_file():
        raise RunSpecError(f"{what} {rel!r} not found: {path} is not a file")
    _verify_hash(path, ref, what)
    return path


def _verify_hash(path, ref, what):
    """A stamped `content_hash` (not the `sha256:<hash>` placeholder) must equal the file's sha256."""
    want = ref.get("content_hash") if isinstance(ref, dict) else None
    if isinstance(want, str) and PLACEHOLDER not in want and sha256_file(path) != want:
        raise RunSpecError(f"{what} {path.name}: content_hash {want[:19]}... does not match the file "
                           f"({sha256_file(path)[:19]}...); run scripts/stamp_hashes.py after an intended edit")


def _verify_directory_hash(directory, ref, what):
    """A stamped `content_hash` (not the placeholder) must equal the `dirhash/1` digest of `directory`."""
    want = ref.get("content_hash") if isinstance(ref, dict) else None
    if isinstance(want, str) and PLACEHOLDER not in want:
        try:
            got = directory_digest(directory)
        except ValueError as e:
            raise RunSpecError(f"{what} directory {directory.name}: cannot be hashed: {e}") from e
        if got != want:
            raise RunSpecError(f"{what} directory {directory.name}: content_hash {want[:19]}... does not match the "
                               f"directory ({got[:19]}...); run scripts/stamp_hashes.py after an intended edit")


def _scene_file(config_repo, ref_name, ref=None):
    # The ref names the `.scene` file itself in the library layout, `scenes/<scene>/<scene>.scene`
    # (Configuration_v02 A.8.3; guide §9), with geometry/, materials/ and maps/ beside it. No
    # fallback search: the earlier nested-then-flat guess against the received tree is gone. A stamped hash is the
    # `dirhash/1` digest of the directory holding the `.scene` file (protodirsig.dirhash), verified here.
    path = _root_file(config_repo, ref_name, "scene")
    _verify_directory_hash(path.parent, ref, "scene")
    return path



def _scene_origin(scene_path):
    """(latitude, longitude) in degrees of the scene's `<sceneorigin>`: the origin of its ENU frame."""
    loc = et.parse(str(scene_path)).getroot().find("sceneorigin/location")
    if loc is None or loc.get("frame") != "geodetic":
        raise RunSpecError(f"scene {scene_path.name}: no geodetic <sceneorigin><location>; an orbit's LookAt target "
                           "and up vector are stated in the scene ENU frame, which needs it")
    return float(loc.findtext("latitude")), float(loc.findtext("longitude"))


def _pointer(path):
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in path) or "/"


def unstamped_refs(spec):
    """The RFC 6901 JSON Pointers of every member of a parsed run spec that still carries a placeholder, in document
    order: each content reference `{name, content_hash}` whose hash is the `sha256:<hash>` placeholder (the sensor
    reference, a curve reference inside an inline sensor block, and every library ref under `engine`: `scenes[]`,
    `platform`, `atmosphere.database`, `weather.file`, `motion.orbit.tle`, `motion.orbit.earth_orientation`), and
    `engine.generator.revision` when it is the `<git-sha>` placeholder (`scripts/stamp_hashes.py` stamps the pinned
    `dirfm` commit). Pure: reads no file. Admission refuses a spec for which this is not empty
    (`LocalRegistry.submit`); `Simulation.validate` reports it (`ConformanceResult.unstamped`)."""
    found = []

    def walk(node, path):
        if isinstance(node, dict):
            want = node.get("content_hash")
            if isinstance(node.get("name"), str) and isinstance(want, str) and PLACEHOLDER in want:
                found.append(_pointer(path))
            if path == ("engine", "generator") and isinstance(node.get("revision"), str) \
                    and PLACEHOLDER in node["revision"]:
                found.append(_pointer((*path, "revision")))
            for k, v in node.items():
                walk(v, (*path, k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, (*path, i))
    if isinstance(spec, dict):
        walk(spec, ())
    return found


def is_inline_sensor(sensor):
    """`descriptor.sensor` given in place: a sensor-spec `sensor` block (`sensor_system` and an `entries` list)."""
    return isinstance(sensor, dict) and "ref" not in sensor and isinstance(sensor.get("sensor_system"), dict) \
        and isinstance(sensor.get("entries"), list)


def default_sensor_library(run_spec_path):
    """`manifold_sensors/`, the sibling of the folder that holds the run spec."""
    return Path(run_spec_path).resolve().parent.parent / "manifold_sensors"


def _check_settings_roi(settings, sensor_doc):
    """Each `settings` member must name a sensor entry; a known `roi` must lie inside that entry's full frame."""
    entries = {e["entry_id"]: e for e in sensor_doc["sensor"]["entries"]}
    for s in settings:
        entry = entries.get(s.get("entry_id"))
        if entry is None:
            raise RunSpecError(f"settings entry_id {s.get('entry_id')!r} matches no sensor entry ({sorted(entries)})")
        roi = s.get("roi")
        if not roi:
            continue
        det = entry["focal_planes"][0]["detector"]
        for size, off, full in (("Width", "OffsetX", "SensorWidth"), ("Height", "OffsetY", "SensorHeight")):
            if det.get(full) is not None and (roi.get(off) or 0) + roi[size] > det[full]:
                raise RunSpecError(f"settings roi {off}+{size} exceeds detector {full} {det[full]} "
                                   f"for entry {s['entry_id']!r}")


def black_level_problem(setting):
    """Why a `settings` member's `black_level` is refused for a DIRSIG run, or None. It is written as the channel's
    `bias`, which DIRSIG adds before the focal-plane conversion (the image moves by bias / G#), so a non-zero value
    gives an image in unphysical units with no signal behind it. Absent or zero is accepted; gain is not restricted."""
    level = setting.get("black_level")
    value = level.get("value") if isinstance(level, dict) else level
    if value in (None, 0):
        return None
    return (f"is {value!r}: DIRSIG applies it as the channel bias before the focal-plane conversion, so a non-zero "
            "black level yields an image in unphysical units without any signal; use 0 or omit it")


def check_settings_black_level(settings):
    for i, s in enumerate(settings):
        problem = black_level_problem(s)
        if problem:
            raise RunSpecError(f"descriptor.settings[{i}].black_level {problem}")


def resolve_auror_run(spec, run_spec_path, config_repo, sensor_library=None):
    """Resolve a loaded run spec: engine assets against `config_repo`, the sensor ref against
    `sensor_library` (default: `default_sensor_library(run_spec_path)`), and the motion/tasks
    values the generator needs. Returns an `AurorRun`."""
    config_repo = Path(config_repo)
    if sensor_library is None:
        sensor_library = default_sensor_library(run_spec_path)
    eng = spec["engine"]
    atm = eng["atmosphere"]
    if atm.get("plugin") != "new_atmosphere":
        raise RunSpecError(
            f"engine.atmosphere.plugin is {atm.get('plugin')!r}; this loader handles only "
            "'new_atmosphere', the non-adopted extension the AUROR_ref spec uses (guide §6). "
            "It is not a general dirsig-engine/1 interpreter, so 'four_curve' and 'basic' are "
            "not supported here.")
    ephemeris = eng.get("ephemeris", {}).get("plugin")
    if ephemeris != "spice":
        raise RunSpecError(f"engine.ephemeris.plugin is {ephemeris!r}; only 'spice' (no inputs) is handled")
    if len(eng["scenes"]) != 1:
        raise RunSpecError(f"expected one engine.scenes entry, got {len(eng['scenes'])}")
    weather = eng.get("weather")
    if weather is None or weather.get("source") != "library":
        raise RunSpecError(f"engine.weather must be a library file for this tree, got {weather!r}")

    # Motion and tasks are generated with dirfm (motion_tasks): PlatformPosition writes a static .ppd, FlexMotion an
    # orbit's waypoint .motion, TASKS one .tasks file. Schema-valid values they cannot express are refused.
    motion = eng["motion"]
    kind = motion.get("kind")
    if kind == "static":
        if motion.get("position", {}).get("frame") != "scene":
            raise RunSpecError(f"engine.motion.position.frame is {motion.get('position', {}).get('frame')!r}; "
                               "dirfm PlatformPosition writes only scene-frame locations ('scene')")
        orient = motion.get("orientation", {})
        if orient.get("kind") != "euler":
            raise RunSpecError(f"engine.motion.orientation.kind is {orient.get('kind')!r}; static motion takes only "
                               "'euler' here ('lookat' is generated, with dirfm FlexMotion, for kind 'orbit')")
        euler = orient.get("euler", {})
        if euler.get("frame") != "sceneenu":
            raise RunSpecError(f"engine.motion.orientation.euler.frame is {euler.get('frame')!r}; dirfm "
                               "PlatformPosition hardcodes rotationframe='sceneenu'")
    elif kind == "orbit":
        orbit_values = _resolve_orbit(motion, eng, config_repo)
    else:
        raise RunSpecError(
            f"engine.motion.kind is {kind!r}; this loader generates 'static' (dirfm PlatformPosition) and 'orbit' "
            "(a TLE propagated to ECEF waypoints, dirfm FlexMotion). 'waypoints' (authored samples) is not built.")
    epoch = datetime.fromisoformat(str(spec["descriptor"]["collection"]["epoch"]).replace("Z", "+00:00"))
    if epoch.tzinfo is None:                 # dirfm TASKS writes a malformed offset for a naive datetime
        raise RunSpecError(f"descriptor.collection.epoch {epoch.isoformat()!r} has no UTC offset")

    scene, plat = eng["scenes"][0], eng["platform"]
    channel_response = plat.get("channel_response", "tabulated")
    if channel_response not in ("tabulated", "native"):
        raise RunSpecError(f"engine.platform.channel_response is {channel_response!r}; expected 'tabulated' or 'native'")
    if plat.get("split_channels"):
        # One spectral state per channel; the NewAtmosphere database has states for the focal plane's bandpass
        # only. The dry run passes and the render fails ("Missing spectral/temporal state"), so refuse it here.
        raise RunSpecError("engine.platform.split_channels true is not handled with new_atmosphere: the database "
                           "holds no per-channel spectral states, so the render fails after the dry run passes")
    desc = spec["descriptor"]
    sensor = desc.get("sensor")
    if is_inline_sensor(sensor):
        sensor_name = f"{desc['meta']['name']} (inline)"
        sensor_doc = {"spec_version": "sensor-spec/1", "meta": {"name": sensor_name}, "sensor": sensor}
    else:
        ref = sensor.get("ref") if isinstance(sensor, dict) else None
        sensor_name = ref.get("name") if isinstance(ref, dict) else None
        if not isinstance(sensor_name, str):
            raise RunSpecError("descriptor.sensor must be a sensor-spec/1 ref ({ref: {name: <name>.yaml}}) or an inline "
                               f"sensor block (sensor_system, entries), got {sensor!r:.80}")
        if (Path(sensor_library) / sensor_name).is_file():
            _verify_hash(Path(sensor_library) / sensor_name, ref, "sensor-spec")
        sensor_doc = load_sensor_spec(sensor_library, sensor_name)
    entries = sensor_doc["sensor"].get("entries") or []
    if len(entries) != 1:
        raise RunSpecError(f"sensor {sensor_name!r} has {len(entries)} entries; one sensor entry per job is "
                           "generated (one run spec per sensor, CONOPS C-18)")
    planes = entries[0].get("focal_planes") or []
    if len(planes) != 1:
        raise RunSpecError(f"sensor entry {entries[0].get('entry_id')!r} has {len(planes)} focal planes; one focal "
                           "plane per entry is generated")
    settings = desc.get("settings")
    if not isinstance(settings, list) or len(settings) != 1:
        got = f"{len(settings)} members" if isinstance(settings, list) else repr(settings)
        raise RunSpecError(f"descriptor.settings must have one member (one sensor entry per job); got {got}")
    _check_settings_roi(settings, sensor_doc)
    check_settings_black_level(settings)
    scene_path = _scene_file(config_repo, scene["ref"]["name"], scene["ref"])
    if kind == "orbit":
        orbit_values["scene_origin"] = _scene_origin(scene_path)
    return AurorRun(
        name=desc["meta"]["name"],
        origin=dict(desc["origin"]),
        scene=scene_path,
        scene_offset=list(scene.get("offset", [0, 0, 0])),
        platform=_root_file(config_repo, plat["ref"]["name"], "platform", plat["ref"]),
        motion_position=[float(v) for v in motion["position"]["xyz"]] if kind == "static" else None,
        motion_orientation={"order": euler["order"], "units": euler["units"],
                            "angles": [float(v) for v in euler["angles"]]} if kind == "static" else None,
        tasks_windows=[(float(w["start"]), float(w["stop"])) for w in eng["tasks"]["windows"]],
        epoch=epoch.astimezone(timezone.utc),
        output_prefix=plat["output_prefix"],
        split_channels=bool(plat["split_channels"]),
        integration_samples=int(plat["integration_samples"]),
        atmosphere_db=_root_file(config_repo, atm["database"]["ref"]["name"], "atmosphere database",
                                  atm["database"]["ref"]),
        weather=_root_file(config_repo, weather["file"]["name"], "weather file", weather["file"]),
        ephemeris=ephemeris,
        seed=int(eng["run"]["seed"]),
        sensor=sensor_doc,
        settings=list(desc["settings"]),
        sensor_library=Path(sensor_library),
        channel_response=channel_response,
        motion_kind=kind,
        orbit=orbit_values if kind == "orbit" else None,
    )


ORBIT_PROPAGATORS = ("skyfield_sgp4",)    # protodirsig.orbit.PROPAGATOR


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _resolve_orbit(motion, eng, config_repo):
    """`engine.motion` of kind `orbit` (proposed): the TLE and Earth-orientation refs resolved and hash-verified
    against `config_repo`, the window checked to cover every task window, the pointing law checked."""
    o = motion.get("orbit")
    if not isinstance(o, dict):
        raise RunSpecError("engine.motion.orbit is missing: kind 'orbit' needs tle, propagator, earth_orientation, "
                           "window and waypoint_spacing")
    if o.get("propagator") not in ORBIT_PROPAGATORS:
        raise RunSpecError(f"engine.motion.orbit.propagator is {o.get('propagator')!r}; expected one of "
                           f"{list(ORBIT_PROPAGATORS)}")
    refs = {}
    for key, what in (("tle", "orbit TLE"), ("earth_orientation", "Earth-orientation tables")):
        ref = o.get(key)
        if not isinstance(ref, dict) or not isinstance(ref.get("name"), str):
            raise RunSpecError(f"engine.motion.orbit.{key} must be a library ref {{name, content_hash}}, got {ref!r}")
        refs[key] = _root_file(config_repo, ref["name"], what, ref)
    w, dt = o.get("window"), o.get("waypoint_spacing")
    if not (isinstance(w, dict) and _number(w.get("start")) and _number(w.get("duration")) and w["duration"] > 0):
        raise RunSpecError(f"engine.motion.orbit.window must be {{start, duration}} in seconds, duration > 0; got {w!r}")
    if not (_number(dt) and dt > 0):
        raise RunSpecError(f"engine.motion.orbit.waypoint_spacing must be a positive number of seconds, got {dt!r}")
    n = w["duration"] / dt
    if abs(n - round(n)) > 1e-9:
        raise RunSpecError(f"engine.motion.orbit.window.duration {w['duration']} is not a whole number of "
                           f"waypoint_spacing {dt} steps")
    lo, hi = float(w["start"]), float(w["start"]) + float(w["duration"])
    for i, tw in enumerate(eng["tasks"]["windows"]):
        if not lo <= float(tw["start"]) <= float(tw["stop"]) <= hi:
            raise RunSpecError(f"engine.tasks.windows[{i}] [{tw['start']}, {tw['stop']}] is outside the orbit window "
                               f"[{lo}, {hi}]: the platform has no waypoints there")
    orient = motion.get("orientation", {})
    look = orient.get("lookat", {}) if isinstance(orient, dict) else {}
    if orient.get("kind") != "lookat":
        raise RunSpecError(f"engine.motion.orientation.kind is {orient.get('kind')!r}; kind 'orbit' is pointed by "
                           "'lookat' (a scene ENU target)")
    target = look.get("target")
    if look.get("frame") != "sceneenu" or not (isinstance(target, list) and len(target) == 3
                                                and all(_number(v) for v in target)):
        raise RunSpecError(f"engine.motion.orientation.lookat must be {{frame: sceneenu, target: [x, y, z]}}, got {look!r}")
    if look.get("up") != "along_track":
        raise RunSpecError(f"engine.motion.orientation.lookat.up is {look.get('up')!r}; only 'along_track' (the "
                           "horizontal velocity direction at the window centre, held fixed) is generated")
    return {"tle": refs["tle"], "earth_orientation": refs["earth_orientation"], "propagator": o["propagator"],
            "window_start": lo, "window_duration": float(w["duration"]), "waypoint_spacing": float(dt),
            "lookat_target": [float(v) for v in target], "up": "along_track"}


def check_library_files(spec, run):
    """Problems that stop the job's `.platform` from being rendered; empty means it can be.

    The library platform file is a template (`platform_gen`). This checks its structure, then renders it
    to a scratch directory so a missing spectral curve, a response outside the job's bandpass, or a
    settings value the generator cannot place is reported here, as a resolution problem, not at execution.
    """
    from tempfile import TemporaryDirectory

    from protodirsig.platform_gen import PlatformGenError, check_template, render_platform
    from protodirsig.spectral import SpectralError
    bad = check_template(run.platform)
    if bad:
        return bad
    if run.orbit is not None:
        bad = _check_orbit_files(run.orbit)
        if bad:
            return bad
    try:
        with TemporaryDirectory() as tmp:
            render_platform(run.platform, run.sensor, run.settings[0]["entry_id"], run.settings,
                            run.integration_samples, run.sensor_library, Path(tmp) / "x.platform", run.channel_response)
    except (PlatformGenError, SpectralError, KeyError) as e:
        return [f"platform could not be rendered from the sensor-spec: {type(e).__name__}: {e}"]
    return []



def _check_orbit_files(o):
    """The orbit's TLE parses and passes its checksums; the Earth-orientation tables load and cover the window."""
    import numpy as np

    from protodirsig.orbit import read_tle
    problems = []
    try:
        read_tle(o["tle"])
    except (AssertionError, ValueError) as e:
        problems.append(f"orbit TLE {o['tle'].name} is not a valid two-line element set: {e or 'checksum or format'}")
    try:
        arrays = np.load(o["earth_orientation"])
        missing = {"tt_jd_minus_arange", "delta_t_1e7", "leap_dates", "leap_offsets"} - set(arrays.files)
        if missing:
            problems.append(f"Earth-orientation tables {o['earth_orientation'].name} lack {sorted(missing)}")
    except (OSError, ValueError) as e:
        problems.append(f"Earth-orientation tables {o['earth_orientation'].name} do not load: {e}")
    return problems


def derive_run_spec(spec, sensor_ref_name, entry_id, roi=None, name=None):
    """A run spec that images the same scenario as a loaded one with another sensor entry.

    A run spec describes its run completely, so a different sensor is a different run spec; there is no
    run-time sensor override. `settings` (exposure, frame rate, gain, black level) carry over; `roi`
    replaces the window when given and is dropped (full frame) when `roi` is `{}`. Composed by
    `compose.merge`, the one composition path: the loaded spec is split into its recipe, scenario and engine
    profile in memory, with `channel_response` removed (a derived sensor is rendered tabulated). The sensor ref
    carries the `sha256:<hash>` placeholder, since no sensor library is named here.
    """
    from protodirsig.compose import RULES, merge
    desc = spec["descriptor"]
    st = copy.deepcopy(desc["settings"][0])
    st["entry_id"] = entry_id
    if roi is not None:
        st.pop("roi", None)
        if roi:
            st["roi"] = dict(roi)
    recipe = {"compose": RULES, "meta": {**desc["meta"], "name": name or f"{desc['meta']['name']}-{entry_id}"},
              "sensor": sensor_ref_name, "scenario": None, "engine_profile": None, "settings": [st],
              "fidelity": desc["fidelity"]}
    engine = copy.deepcopy(spec["engine"])
    engine["platform"].pop("channel_response", None)
    profile = {"origin": desc["origin"], "engine": engine, **({"extras": desc["extras"]} if "extras" in desc else {})}
    layers = {"recipe": ("derived recipe", recipe), "scenario": ("base spec collection", {"collection": desc["collection"]}),
              "engine_profile": ("base spec engine profile", profile)}
    return merge(layers, {"name": sensor_ref_name, "content_hash": "sha256:<hash>"})[0]
