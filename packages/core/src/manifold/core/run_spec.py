"""Load a MANIFOLD run spec and the sensor-spec it names, and check what every engine shares: engine-neutral.

`load_run_spec` parses a run-spec YAML; `load_sensor_spec` loads the `sensor-spec/1` document a `descriptor.sensor`
ref names from the sensor library (`manifold_sensors/`, by default the sibling of the folder holding the run spec,
`default_sensor_library`); `is_inline_sensor` recognizes a sensor block given in place. A stamped `content_hash` is
verified when a reference is resolved (`_verify_hash`: the sha256 of a file; `_verify_directory_hash`: the `dirhash/1`
digest of a directory); the `sha256:<hash>` placeholder is not verified, and `unstamped_refs` lists the members that
still carry it. `RunSpecError` (a `ProblemError`, admission, with the JSON Pointer of the member at fault) is what
resolution raises; `LibraryProblem` is a library-file problem with its pointer.

Resolving an engine block is the engine's: its adapter (`manifold.core.engine.EngineAdapter.resolve`) does it, for
DIRSIG `manifold.engines.dirsig.run_spec.resolve_run`.

Loading is a plain `yaml.safe_load`. `AV_MANIFOLD_Metadata_v02.md` §6.15 specifies a strict
loader (duplicate-key rejection, canonical-JSON hashing, unknown-key rejection). Duplicate-key rejection is not built:
a duplicated key in the YAML silently keeps the last value. The other two are built elsewhere in the SDK, not in this
module: unknown keys are refused by the schema check at admission (`manifold.core.contract`, except in
`descriptor.extras` and the members the schemas leave open), and a run id is the sha256 of the RFC 8785 canonical JSON
of the resolved run spec (`manifold.core.identity`). A ref's `content_hash` is the sha256 of the referenced file's bytes
(or the `dirhash/1` digest of a directory), not a canonical-JSON hash.

Imports: the standard library, `yaml`, `manifold.core.spectral`, `manifold.core.dirhash` and `manifold.core.errors`.
"""
from pathlib import Path

import yaml

from manifold.core.dirhash import directory_digest
from manifold.core.errors import ProblemError
from manifold.core.spectral import PLACEHOLDER, sha256_file


class RunSpecError(ProblemError, ValueError):
    """The run spec asks for something this tree-specific loader does not handle, or a reference does not resolve.

    A `ProblemError` (admission, 422) and a `ValueError`. `pointer` is the RFC 6901 JSON Pointer of the spec member
    being resolved when the error is about one (a reference's `name` for a missing file, its `content_hash` for a hash
    mismatch), else None. `problems.locate` maps it to the layer file and field of a composed spec."""

    def __init__(self, *args, pointer=None):
        super().__init__(args[0] if args else None)
        self.args = args
        self.pointer = pointer


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


class LibraryProblem(str):
    """A library-file problem (`check_library_files`): a string, as before, with the `pointer` of the spec member whose
    file has the problem, so `problems.locate` can name the layer file and field."""

    def __new__(cls, text, pointer=None):
        obj = super().__new__(cls, text)
        obj.pointer = pointer
        return obj

    def __reduce__(self):
        return LibraryProblem, (str(self), self.pointer)


def _member(pointer, key):
    return f"{pointer}/{key}" if pointer else None


def _root_file(root, rel, what, ref=None, pointer=None):
    """The library file `root / rel`, hash-verified against `ref`. `pointer` is the ref's place in the spec."""
    path = root / rel
    if not path.is_file():
        raise RunSpecError(f"{what} {rel!r} not found: {path} is not a file", pointer=_member(pointer, "name"))
    _verify_hash(path, ref, what, pointer)
    return path


def _verify_hash(path, ref, what, pointer=None):
    """A stamped `content_hash` (not the `sha256:<hash>` placeholder) must equal the file's sha256."""
    want = ref.get("content_hash") if isinstance(ref, dict) else None
    if isinstance(want, str) and PLACEHOLDER not in want and sha256_file(path) != want:
        raise RunSpecError(f"{what} {path.name}: content_hash {want[:19]}... does not match the file "
                           f"({sha256_file(path)[:19]}...); run scripts/stamp_hashes.py after an intended edit",
                           pointer=_member(pointer, "content_hash"))


def _verify_directory_hash(directory, ref, what, pointer=None):
    """A stamped `content_hash` (not the placeholder) must equal the `dirhash/1` digest of `directory`."""
    want = ref.get("content_hash") if isinstance(ref, dict) else None
    if isinstance(want, str) and PLACEHOLDER not in want:
        try:
            got = directory_digest(directory)
        except ValueError as e:
            raise RunSpecError(f"{what} directory {directory.name}: cannot be hashed: {e}",
                               pointer=_member(pointer, "name")) from e
        if got != want:
            raise RunSpecError(f"{what} directory {directory.name}: content_hash {want[:19]}... does not match the "
                               f"directory ({got[:19]}...); run scripts/stamp_hashes.py after an intended edit",
                               pointer=_member(pointer, "content_hash"))


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


