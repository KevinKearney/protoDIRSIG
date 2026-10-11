"""Library listing and reading: the four resource kinds runs are composed from, as the SDK API serves them.

`LibraryReader(root)` reads the library under a layer root (`manifold_run_specs/`): `recipes/*.yaml`,
`scenarios/*.yaml`, `engine_profiles/*.yaml`, and the sensor library beside it (`manifold_sensors/*.yaml`, the rule of
`compose.sensor_library_for_root`, unless `sensor_library` is given). The generated run specs at the top of the layer
root are not a resource kind.

Names are what a recipe uses: a sensor by its file name (`auror-nir.yaml`; `get` also accepts the stem), a scenario,
engine profile or recipe by its file stem. `list(kind)` gives `[{name, sha256}]` sorted by name and `get(kind, name)`
`{name, sha256, document}`, the shapes of `api/schemas/library_list.schema.json` (its `items`) and
`library_document.schema.json` (`sensor_document.schema.json` for a sensor); `sha256` is the digest of the file's bytes,
64 lowercase hex digits; a layer file whose header comment says "does not validate yet" (a placed DIRSIG demo) also
carries `status: does-not-validate-yet`. A missing name raises `errors.NotFoundError` (404). A file that does not parse, or is not of
its kind, raises `errors.AdmissionError` whose problem names the file (`layer`) and the offending key (`field`) or null:
a sensor must conform to `sensor-spec/1`; a recipe must carry `compose`, `meta`, `scenario`, `engine_profile`, `settings`,
`sensor` or `sensors`, and only the keys `compose.merge` accepts of a recipe; a scenario must hold `collection` and an
engine profile `origin` and `engine`, and nothing outside what `compose.OWNER` assigns them.

Imports: the standard library, `yaml` and pure `protodirsig` modules (`compose`, `contract`, `errors`, `problems`); no
engine package.
"""
import hashlib
from pathlib import Path

import yaml

from protodirsig import problems
from protodirsig.compose import CONTROL, LAYER_DIR, OWNER, PASSTHROUGH_RECIPE, REQUIRED, sensor_library_for_root
from protodirsig.contract import sensor_spec_violations
from protodirsig.errors import AdmissionError, InvalidRequestError, NotFoundError

KINDS = ("sensor", "scenario", "engine_profile", "recipe")
NOT_YET = "does not validate yet"               # the marker, in a layer file's first comment paragraph
STATUS_NOT_YET = "does-not-validate-yet"        # how listings surface it (`status`)


def file_status(text):
    """`does-not-validate-yet` when the file's header (its text before the first blank line) carries the marker
    "does not validate yet", else None. The marker is how a placed but not yet resolvable library entry (a DIRSIG
    demo's layers) is labelled; the tests that resolve every repository recipe skip such entries."""
    return STATUS_NOT_YET if NOT_YET in text.split("\n\n", 1)[0] else None
REPOSITORY = Path(__file__).resolve().parents[2]


class LibraryReader:
    """Read-only access to one library. `root` is the layer root (default: the repository's `manifold_run_specs/`);
    `sensor_library` the sensor library (default: the sibling `manifold_sensors/`)."""

    def __init__(self, root=None, sensor_library=None):
        self.root = Path(root).resolve() if root is not None else REPOSITORY / "manifold_run_specs"
        self.sensor_library = Path(sensor_library).resolve() if sensor_library is not None \
            else sensor_library_for_root(self.root)

    def folder(self, kind):
        """The folder holding resources of `kind`."""
        if kind == "sensor":
            return self.sensor_library
        if kind == "recipe":
            return self.root / "recipes"
        if kind in LAYER_DIR:
            return self.root / LAYER_DIR[kind]
        raise InvalidRequestError(f"unknown resource kind {kind!r}; expected one of {list(KINDS)}")

    def _name(self, kind, path):
        return path.name if kind == "sensor" else path.stem

    def _layer(self, kind, path):
        """The file as the problem schema names a layer: relative to the layer root, the sensor library by its name."""
        return f"{self.sensor_library.name}/{path.name}" if kind == "sensor" else \
            path.relative_to(self.root).as_posix()

    def list(self, kind):
        """`[{name, sha256}]` for every resource of `kind`, sorted by name."""
        folder = self.folder(kind)
        files = sorted(folder.glob("*.yaml")) if folder.is_dir() else []
        return sorted((self._item(kind, p) for p in files if p.is_file()), key=lambda r: r["name"])

    def _item(self, kind, path):
        data = path.read_bytes()
        item = {"name": self._name(kind, path), "sha256": hashlib.sha256(data).hexdigest()}
        status = None if kind == "sensor" else file_status(data.decode("utf-8", "replace"))
        if status:
            item["status"] = status
        return item

    def path(self, kind, name):
        """The file of a named resource; NotFoundError if there is none. A name is a file name or stem, never a path."""
        folder = self.folder(kind)
        if not isinstance(name, str) or not name or "/" in name or "\\" in name or name.startswith("."):
            raise NotFoundError(kind.replace("_", " "), name)
        candidates = [folder / name] if kind == "sensor" and name.endswith(".yaml") else [folder / f"{name}.yaml"]
        for c in candidates:
            if c.is_file():
                return c
        raise NotFoundError(kind.replace("_", " "), name)

    def get(self, kind, name):
        """`{name, sha256, document}`: the document as authored, checked to be of its kind."""
        path = self.path(kind, name)
        data = path.read_bytes()
        layer = self._layer(kind, path)
        try:
            doc = yaml.safe_load(data)
        except yaml.YAMLError as e:
            raise AdmissionError(problems.admission(f"{layer} does not parse as YAML: {e}", layer=layer)) from e
        self._check(kind, doc, layer)
        out = {"name": self._name(kind, path), "sha256": hashlib.sha256(data).hexdigest(), "document": doc}
        status = None if kind == "sensor" else file_status(data.decode("utf-8", "replace"))
        if status:
            out["status"] = status
        return out

    def _check(self, kind, doc, layer):
        def bad(message, field=None):
            raise AdmissionError(problems.admission(f"{layer}: {field + ': ' if field else ''}{message}",
                                                    layer=layer, field=field))
        if not isinstance(doc, dict):
            bad(f"is not a {kind.replace('_', ' ')} (expected a mapping, got {type(doc).__name__})")
        if kind == "sensor":
            violations = sensor_spec_violations(doc)
            if violations:
                v = violations[0]
                field = problems.field_path(problems.parse_pointer(v["at"]), doc) or None
                bad(f"is not a sensor-spec/1 document: {v['message']}", field)
            return
        allowed = {m for m, owner in OWNER.items() if owner == kind} | set(CONTROL.get(kind, ()))
        for key in doc:
            if key not in allowed:
                bad(f"unknown key; a {kind.replace('_', ' ')} holds {sorted(allowed)}", key)
        if kind == "recipe" and "passthrough" in doc:
            for key in PASSTHROUGH_RECIPE:
                if key not in doc:
                    bad("missing (a pass-through recipe)", key)
            for key in doc:
                if key not in PASSTHROUGH_RECIPE:
                    bad(f"not part of a pass-through recipe, which holds {list(PASSTHROUGH_RECIPE)}", key)
            return
        if kind == "recipe":
            required = [k for k in REQUIRED["recipe"] if k not in ("sensor", "fidelity")]
            for key in required:
                if key not in doc:
                    bad("missing", key)
            if "sensor" not in doc and "sensors" not in doc:
                bad("missing (a recipe names sensor, or sensors for a sweep)", "sensor")
            for key in ("scenario", "engine_profile"):
                if not isinstance(doc[key], str):
                    bad("must be a layer name", key)
        else:
            for key in REQUIRED[kind]:
                if key not in doc:
                    bad("missing", key)
