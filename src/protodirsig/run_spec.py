"""Read the AUROR_ref job's references from a MANIFOLD run-spec YAML.

Narrow and tree-specific by design: this resolves `run_specs/auror_ref.yaml` (vendored from
eopticDocs `04-guides/auror_ref_run_spec.yaml`) for the stage notebooks
(`notebooks/stage_NN_*.ipynb`). It is not a `dirsig-engine/1` interpreter.

Two resolution roots, one per kind of thing referenced:
- `config_repo`: the engine-asset library (GD_DIRSIG_RunSpec_YAML_v01 §9; Configuration_v02 A.8)
  for `engine.scenes`, `platform`, `atmosphere.database` and `weather.file`. Each ref name is a path
  under it, with no fallback search.
- the run spec's own directory, for the `descriptor.sensor` ref (see below).
Nothing resolves against a received run tree. MANIFOLD has none: the executor materializes a fresh
run tree from the run spec for every run (Configuration_v02 §2).

`descriptor.sensor` is a `sensor-spec/1` ref (GD_DIRSIG_RunSpec_YAML_v01 §7). Unlike every
`engine` ref, it resolves against the run spec's own directory (`run_specs/sensors/...`), not
`config_repo`. It is loaded and checked here, and nothing in the DIRSIG job consumes it.

What it drives: `engine.scenes`, `platform`, `atmosphere`, `weather`, `ephemeris` and
`run.seed` name existing library files that the `scene_ref`, `platform_ref` and
`atmosphere_patches` helpers reference as-is. `engine.motion` and `engine.tasks` are generated,
not resolved: `AurorRun` carries their values, and `motion_tasks` writes the `.ppd` and `.tasks`
files from them. Only `motion.kind: static` with a
scene-frame position and a `sceneenu` Euler orientation is generated; anything else is refused.

Loading is a plain `yaml.safe_load`. `AV_MANIFOLD_Metadata_v02.md` §6.15 specifies a strict
loader (duplicate-key rejection, canonical-JSON hashing, unknown-key rejection). That belongs to
MANIFOLD's registry side, which is not built yet, so it is not built here: a duplicated key in the
YAML silently keeps the last value, and no `content_hash` is checked, the sensor ref's
included (by-name trust, guide §7).
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import lxml.etree as et
import yaml

from protodirsig.atmosphere_patches import PatchedModtranTapeBackend, PatchedNewAtmospherePlugin
from protodirsig.platform_ref import SpiceEphemerisPlugin

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


def load_sensor_spec(run_spec_path, sensor_ref_name):
    """Load the `sensor-spec/1` document `sensor_ref_name` names, resolved against the run spec's
    directory. Returns the whole document, as `load_run_spec` does. Raises `RunSpecError` if the
    file is missing, does not parse, is not `sensor-spec/1`, or has no `sensor` mapping."""
    path = Path(run_spec_path).parent / sensor_ref_name
    if not path.is_file():
        raise RunSpecError(f"sensor {sensor_ref_name!r} not found beside the run spec ({path})")
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
    """The run spec's values: engine assets resolved to config_repo files, and the values the
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
    sensor: dict             # the loaded sensor-spec/1 document; descriptor-side, not used to build the job

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


def _root_file(root, rel, what):
    path = root / rel
    if not path.is_file():
        raise RunSpecError(f"{what} {rel!r} not found: {path} is not a file")
    return path


def _scene_file(config_repo, ref_name):
    # The ref names the `.scene` file itself in the library layout, `scenes/<scene>/<scene>.scene`
    # (Configuration_v02 A.8.3; guide §9), with geometry/, materials/ and maps/ beside it. No
    # fallback search: the earlier nested-then-flat guess against the received tree is gone.
    return _root_file(config_repo, ref_name, "scene")


def resolve_auror_run(spec, run_spec_path, config_repo):
    """Resolve a loaded run spec: engine assets against `config_repo`, the sensor ref against
    `run_spec_path`'s directory, and the motion/tasks values the generator needs. Returns an
    `AurorRun`."""
    config_repo = Path(config_repo)
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
    desc = spec["descriptor"]
    sensor = desc.get("sensor")
    ref = sensor.get("ref") if isinstance(sensor, dict) else None
    sensor_name = ref.get("name") if isinstance(ref, dict) else None
    if not isinstance(sensor_name, str):
        raise RunSpecError("descriptor.sensor must be a sensor-spec/1 ref ({ref: {name: sensors/<name>.yaml}}), "
                           f"got {sensor!r:.80}")
    return AurorRun(
        name=desc["meta"]["name"],
        origin=dict(desc["origin"]),
        scene=_scene_file(config_repo, scene["ref"]["name"]),
        scene_offset=list(scene.get("offset", [0, 0, 0])),
        platform=_root_file(config_repo, plat["ref"]["name"], "platform"),
        motion_position=[float(v) for v in motion["position"]["xyz"]],
        motion_orientation={"order": euler["order"], "units": euler["units"],
                            "angles": [float(v) for v in euler["angles"]]},
        tasks_windows=[(float(w["start"]), float(w["stop"])) for w in eng["tasks"]["windows"]],
        epoch=epoch.astimezone(timezone.utc),
        output_prefix=plat["output_prefix"],
        split_channels=bool(plat["split_channels"]),
        integration_samples=int(plat["integration_samples"]),
        atmosphere_db=_root_file(config_repo, atm["database"]["ref"]["name"], "atmosphere database"),
        weather=_root_file(config_repo, weather["file"]["name"], "weather file"),
        ephemeris=ephemeris,
        seed=int(eng["run"]["seed"]),
        sensor=load_sensor_spec(run_spec_path, sensor_name),
    )


def check_library_files(spec, run):
    """Where the run spec restates a value a resolved library file already sets, compare the two.

    Today that is one value: `engine.platform.integration_samples` against the platform file's
    `capturemethod/temporalintegration/samples`. (Until Stage 05 this also compared motion, tasks
    and epoch against received files; those files are now generated from the spec, so the
    comparison would be circular.) Returns a list of mismatch strings; empty means they agree.
    """
    bad = []
    samples = et.parse(str(run.platform)).getroot().findtext(".//capturemethod/temporalintegration/samples")
    if samples is None or int(samples) != run.integration_samples:
        bad.append(f"integration_samples: run spec {run.integration_samples} vs platform file {samples}")
    return bad
