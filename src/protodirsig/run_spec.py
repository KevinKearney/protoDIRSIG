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

`descriptor.sensor` is a `sensor-spec/1` ref (CONOPS and Guide §4). Unlike every
`engine` ref, it resolves against `sensor_library`, not `config_repo`. The ref name is a path under
the library (`auror-nir.yaml`). The default library is `manifold_sensors/`, a sibling of the folder holding the
run spec. It is loaded and checked here, and `platform_gen` renders the job's `.platform` from it and the
run spec's `settings`.

What it drives: `engine.scenes`, `platform`, `atmosphere`, `weather`, `ephemeris` and
`run.seed` name existing library files that the `scene_ref`, `platform_ref` and
`atmosphere_patches` helpers reference as-is. `engine.motion` and `engine.tasks` are generated,
not resolved: `AurorRun` carries their values, and `motion_tasks` writes the `.ppd` and `.tasks`
files from them. Only `motion.kind: static` with a
scene-frame position and a `sceneenu` Euler orientation is generated; anything else is refused.

Loading is a plain `yaml.safe_load`. `AV_MANIFOLD_Metadata_v02.md` §6.15 specifies a strict
loader (duplicate-key rejection, canonical-JSON hashing, unknown-key rejection). That belongs to
MANIFOLD's registry side, which is not built yet, so it is not built here: a duplicated key in the
YAML silently keeps the last value, and no `content_hash` is computed canonically. A stamped hash (sha256 of the file bytes, `scripts/stamp_hashes.py`)
on a file ref is verified when the file is read; the `sha256:<hash>` placeholder is not (a `.scene` ref stays
a placeholder, since its geometry and materials sit beside it).
"""
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import lxml.etree as et
import yaml

from protodirsig.atmosphere_patches import PatchedModtranTapeBackend, PatchedNewAtmospherePlugin
from protodirsig.platform_ref import SpiceEphemerisPlugin
from protodirsig.spectral import PLACEHOLDER, sha256_file

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

    def atmosphere_plugin(self, db=None):
        """`NewAtmosphere` over `db`, or over the resolved library database if not given. Pass the job's
        copy of the database so the jsim references it rather than the read-only original."""
        b = AUROR_ATMOSPHERE_BACKEND
        backend = (PatchedModtranTapeBackend().set_profile(b["profile"])
                   .set_atmospheric_model(b["atmospheric_model"])
                   .set_boundary_aerosol_model(b["boundary_aerosol_model"])
                   .set_multiple_scattering(b["multiple_scattering"]))
        return (PatchedNewAtmospherePlugin(Path(db) if db is not None else self.atmosphere_db)
                .set_backend(backend).set_info("", "", "", ""))

    def ephemeris_plugin(self):
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


def _scene_file(config_repo, ref_name):
    # The ref names the `.scene` file itself in the library layout, `scenes/<scene>/<scene>.scene`
    # (Configuration_v02 A.8.3; guide §9), with geometry/, materials/ and maps/ beside it. No
    # fallback search: the earlier nested-then-flat guess against the received tree is gone.
    return _root_file(config_repo, ref_name, "scene")


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

    # Motion and tasks are generated with dirfm's PlatformPosition and TASKS (motion_tasks), which
    # write one static .ppd and one .tasks file. Schema-valid values they cannot express are refused.
    motion = eng["motion"]
    if motion.get("kind") != "static":
        raise RunSpecError(
            f"engine.motion.kind is {motion.get('kind')!r}; this loader generates only 'static' motion "
            "(dirfm PlatformPosition). 'waypoints' and 'orbit' need dirfm FlexMotion, a different "
            "generator not built here; that work lives, unfinished, in protodirsig.orbit and "
            "notebooks/dirfm_tutorials/tutorial_orbit_to_ground.ipynb.")
    if motion.get("position", {}).get("frame") != "scene":
        raise RunSpecError(f"engine.motion.position.frame is {motion.get('position', {}).get('frame')!r}; "
                           "dirfm PlatformPosition writes only scene-frame locations ('scene')")
    orient = motion.get("orientation", {})
    if orient.get("kind") != "euler":
        raise RunSpecError(f"engine.motion.orientation.kind is {orient.get('kind')!r}; only 'euler' is generated "
                           "here ('lookat' needs dirfm FlexMotion, not built here)")
    euler = orient.get("euler", {})
    if euler.get("frame") != "sceneenu":
        raise RunSpecError(f"engine.motion.orientation.euler.frame is {euler.get('frame')!r}; dirfm "
                           "PlatformPosition hardcodes rotationframe='sceneenu'")
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
    ref = sensor.get("ref") if isinstance(sensor, dict) else None
    sensor_name = ref.get("name") if isinstance(ref, dict) else None
    if not isinstance(sensor_name, str):
        raise RunSpecError("descriptor.sensor must be a sensor-spec/1 ref ({ref: {name: <name>.yaml}}), "
                           f"got {sensor!r:.80}")
    _verify_hash(Path(sensor_library) / sensor_name, ref, "sensor-spec") if (Path(sensor_library) / sensor_name).is_file() else None
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
    return AurorRun(
        name=desc["meta"]["name"],
        origin=dict(desc["origin"]),
        scene=_scene_file(config_repo, scene["ref"]["name"]),
        scene_offset=list(scene.get("offset", [0, 0, 0])),
        platform=_root_file(config_repo, plat["ref"]["name"], "platform", plat["ref"]),
        motion_position=[float(v) for v in motion["position"]["xyz"]],
        motion_orientation={"order": euler["order"], "units": euler["units"],
                            "angles": [float(v) for v in euler["angles"]]},
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
    )


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
    try:
        with TemporaryDirectory() as tmp:
            render_platform(run.platform, run.sensor, run.settings[0]["entry_id"], run.settings,
                            run.integration_samples, run.sensor_library, Path(tmp) / "x.platform", run.channel_response)
    except (PlatformGenError, SpectralError, KeyError) as e:
        return [f"platform could not be rendered from the sensor-spec: {type(e).__name__}: {e}"]
    return []


def derive_run_spec(spec, sensor_ref_name, entry_id, roi=None, name=None):
    """A copy of a loaded run spec that images the same scenario with another sensor entry.

    A run spec describes its run completely, so a different sensor is a different run spec; there is no
    run-time sensor override. `settings` (exposure, frame rate, gain, black level) carry over; `roi`
    replaces the window when given and is dropped (full frame) when `roi` is `{}`.
    """
    new = copy.deepcopy(spec)
    desc = new["descriptor"]
    desc["sensor"] = {"ref": {"name": sensor_ref_name, "content_hash": "sha256:<hash>"}}
    st = desc["settings"][0]
    st["entry_id"] = entry_id
    if roi is not None:
        st.pop("roi", None)
        if roi:
            st["roi"] = dict(roi)
    desc["meta"]["name"] = name or f"{desc['meta']['name']}-{entry_id}"
    new["engine"]["platform"].pop("channel_response", None)      # a derived sensor is rendered tabulated
    return new
