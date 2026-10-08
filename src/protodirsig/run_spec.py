"""Read the AUROR_ref job's references from a MANIFOLD run-spec YAML.

Narrow and tree-specific by design: this resolves `run_specs/auror_ref.yaml` (vendored from
eopticDocs `04-guides/auror_ref_run_spec.yaml`) against the received `AUROR_ref/` tree for
the stage notebooks (`notebooks/stage_NN_*.ipynb`). It is not a `dirsig-engine/1` interpreter.

`descriptor.sensor` is a `sensor-spec/1` ref (GD_DIRSIG_RunSpec_YAML_v01 §7). Unlike every
`engine` ref, it resolves against the run spec's own directory (`run_specs/sensors/...`), not the
tree root. It is loaded and checked here, and nothing in the DIRSIG job consumes it.

What it drives: `engine.scenes`, `platform`, `atmosphere`, `weather`, `ephemeris` and
`run.seed`. Each one names an existing file, or a library entry, that the `scene_ref`,
`platform_ref` and `atmosphere_patches` helpers reference as-is.
What it does not drive: `engine.motion` and `engine.tasks`. In a received tree those blocks
describe what `motion/*.ppd` and `tasks/*.tasks` already encode, so the files are referenced and
never regenerated (FINDINGS.md, "2026-10-07 — Stage 01"). `check_received_files` compares the two
instead.

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
# The render reads the existing HDF5 database, not this block (FINDINGS.md, Phase 5), and the run
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
    """The run spec's values resolved to files in the received tree."""
    name: str
    origin: dict
    scene: Path
    scene_offset: list
    platform: Path
    motion: Path
    tasks: Path
    output_prefix: str
    split_channels: bool
    integration_samples: int
    atmosphere_db: Path
    weather: Path
    ephemeris: str
    seed: int
    sensor: dict             # the loaded sensor-spec/1 document; descriptor-side, not used to build the job

    def atmosphere_plugin(self, db=None):
        """`NewAtmosphere` over `db`, or over the tree's own database if not given. Pass the job's
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


def _tree_file(tree, rel, what):
    path = tree / rel
    if not path.is_file():
        raise RunSpecError(f"{what} {rel!r} not found under {tree}")
    return path


def _scene_file(tree, ref_name):
    # `scenes/tahoe` names the config repository's intended layout, `scenes/<scene>/<scene>.scene`
    # (Configuration_v02 A.8.3). The received tree instead has `tahoe.scene` at its root, with
    # geometry/, materials/ and maps/ beside it. That layout question is open in the guide
    # (GD_DIRSIG_RunSpec_YAML_v01 §6). Here it is worked around locally, not resolved: try the
    # nested layout, then the scene's basename at the tree root.
    stem = Path(ref_name).name
    for candidate in (tree / ref_name / f"{stem}.scene", tree / f"{stem}.scene"):
        if candidate.is_file():
            return candidate
    raise RunSpecError(f"scene {ref_name!r}: neither {ref_name}/{stem}.scene nor {stem}.scene "
                       f"exists under {tree}")


def _single(tree, subdir, pattern, what):
    # engine.motion / engine.tasks describe the received files' content but do not name them.
    found = sorted((tree / subdir).glob(pattern))
    if len(found) != 1:
        raise RunSpecError(f"expected exactly one {what} ({subdir}/{pattern}) under {tree}, "
                           f"found {[p.name for p in found]}")
    return found[0]


def resolve_auror_run(spec, tree, run_spec_path):
    """Resolve a loaded run spec against the received tree at `tree`, and its sensor ref against
    `run_spec_path`'s directory. Returns an `AurorRun`."""
    tree = Path(tree)
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
        scene=_scene_file(tree, scene["ref"]["name"]),
        scene_offset=list(scene.get("offset", [0, 0, 0])),
        platform=_tree_file(tree, plat["ref"]["name"], "platform"),
        motion=_single(tree, "motion", "*.ppd", "platform motion file"),
        tasks=_single(tree, "tasks", "*.tasks", "tasks file"),
        output_prefix=plat["output_prefix"],
        split_channels=bool(plat["split_channels"]),
        integration_samples=int(plat["integration_samples"]),
        atmosphere_db=_tree_file(tree, atm["database"]["ref"]["name"], "atmosphere database"),
        weather=_tree_file(tree, weather["file"]["name"], "weather file"),
        ephemeris=ephemeris,
        seed=int(eng["run"]["seed"]),
        sensor=load_sensor_spec(run_spec_path, sensor_name),
    )


def check_received_files(spec, run):
    """Where the run spec restates a value the received files already set, compare the two.

    Covers `engine.motion` (static pose), `engine.tasks` (window), `integration_samples` and
    `descriptor.collection.epoch`. Returns a list of mismatch strings; an empty list means they agree.
    Nothing is regenerated from the spec (see module docstring).
    """
    eng, bad = spec["engine"], []

    def differs(what, spec_val, file_val, tol=1e-6):
        if len(spec_val) != len(file_val) or any(abs(float(a) - float(b)) > tol for a, b in zip(spec_val, file_val)):
            bad.append(f"{what}: run spec {spec_val} vs file {file_val}")

    ppd = et.parse(str(run.motion)).getroot()
    entries = ppd.findall("data/entry")
    motion = eng["motion"]
    if motion["kind"] != "static" or len(entries) != 1:
        bad.append(f"motion: run spec kind {motion['kind']!r}, file has {len(entries)} entries")
    else:
        e, data = entries[0], ppd.find("data")
        differs("motion.position", motion["position"]["xyz"],
                [e.findtext(f"position/location/point/{k}") for k in "xyz"])
        differs("motion.orientation", motion["orientation"]["euler"]["angles"],
                [e.findtext(f"orientation/eulerangles/cartesiantriple/{k}") for k in "xyz"])
        euler = motion["orientation"]["euler"]
        for key, attr in (("frame", "rotationframe"), ("order", "rotationorder"), ("units", "angularunits")):
            if euler[key] != data.get(attr):
                bad.append(f"motion.orientation.{key}: run spec {euler[key]!r} vs file {data.get(attr)!r}")

    tasks = et.parse(str(run.tasks)).getroot().findall("task")
    windows = [[float(t.findtext("start/datetime")), float(t.findtext("stop/datetime"))] for t in tasks]
    spec_windows = [[w["start"], w["stop"]] for w in eng["tasks"]["windows"]]
    if len(windows) != len(spec_windows):
        bad.append(f"tasks: run spec {spec_windows} vs file {windows}")
    else:
        for s, f in zip(spec_windows, windows):
            differs("tasks.window", s, f)

    ref = et.parse(str(run.tasks)).getroot().findtext("reference/datetime")
    file_epoch = datetime.fromisoformat(ref).astimezone(timezone.utc)
    spec_epoch = datetime.fromisoformat(spec["descriptor"]["collection"]["epoch"].replace("Z", "+00:00"))
    if file_epoch != spec_epoch:
        bad.append(f"epoch: run spec {spec_epoch.isoformat()} vs tasks reference {file_epoch.isoformat()}")

    samples = et.parse(str(run.platform)).getroot().findtext(".//capturemethod/temporalintegration/samples")
    if samples is None or int(samples) != run.integration_samples:
        bad.append(f"integration_samples: run spec {run.integration_samples} vs platform file {samples}")
    return bad
