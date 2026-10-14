"""The DIRSIG closure walker (round 46 spike): from a run tree's simulation file, follow every reference and return each
reached file with its role (`roles.REFERENCES`, assigned from the referencing element) and its path relative to the
tree root, reporting every violation of Cfg 2.3's path rules rather than normalizing it.

Evidence, not the SDK's implementation (Cfg 4.1, A.4). `walk(root, entry)` returns a `Walk`:

- `files`: `Reached(path, role, referrer, field)`, one per root-relative path, in path order (byte-wise UTF-8). `role` is
  None when no role covers the referencing field (`Walk.unroled`): such a file cannot enter a manifest (Cfg 2.4).
- `violations`: `Violation(kind, text, referrer, field, enabled, orphan)`, `kind` one of `VIOLATION_KINDS`:
  `absolute` (a leading `/`, a drive letter or a UNC prefix), `dotdot` (a `..` segment), `non_nfc`, `symlink` (the
  reached path crosses a symbolic link inside the tree; `text` is the link's root-relative path), `outside_root` (the
  reference resolves lexically outside the root), `form` (a backslash, an empty or `.` segment, a C0 control or DEL),
  `variable` (a `$VARIABLE` other than `$SCENE_DIR` and `$DIRSIG_HOME`). An absolute or escaping reference is reported
  and not followed (Cfg A.4 `E_ABSOLUTE_PATH`).
- `unresolved`: references that name no existing file under any folder searched (Cfg A.4 `E_UNRESOLVED`).
- `install`: references into the DIRSIG installation (`$DIRSIG_HOME/...`): outside the tree and outside identity, covered
  by the engine data hash (Cfg A.6). Not a violation.
- `orphans`: regular files and links under the root that no reference reached (Cfg A.4 `W_ORPHAN`). An orphan that
  parses as a file the walker reads (by its root element) is scanned for path violations, reported with `orphan=True`,
  and not followed.
- `role_conflicts`: a path reached twice under two roles.
- `behind_links`: files under a crossed symbolic link that no reference reached (not orphans: the tree holds the link,
  not the files).

`Walk.passes` is no error (no violation, unresolved reference, unroled file or role conflict); `Walk.clean` is `passes`
and no orphan (an orphan is a warning, Cfg A.4).

Rules, from Cfg A.2 and A.4: an element with `enabled="false"` (or under one) is outside the closure and not followed,
but its text is still checked and its violations reported with `enabled=False` (the text is in a hashed file). A reference
to `<name>.scene.hdf` stands for `<name>.scene` (the compiled scene is not in the manifest). `$SCENE_DIR` is the scene's
folder; directory elements (`gdbdirectory`, `emsdirectory`, ...) are expanded. A reference resolves against an ordered
list of folders: the `.jsim`/`.sim` entries against the entry's folder (DIRSIG runs there, Cfg A.6); a `.scene`'s
geometry lists against its `gdbdirectory`, then the working folder (scene_ref's measured rule); a geometry list's names
against its own folder when the object says `search_paths="local"`, then the `gdbdirectory`, the working folder and the
list's folder; a material file's names against the folder the key's scene directory element names
(`scene_ref.MATERIAL_UNHELD_KEYS`, `MATERIAL_SEARCHED_KEYS`; otherwise `emsdirectory`), the material file's folder and the
working folder. Only the jsim and geometry-list orders are measured; the others are the walker's assumption and are what
the closure test (Cfg A.5) would check.

The walker reads through a symbolic link to continue the walk (it reports the link; it does not replace the path by its
target and copies nothing). Any other leaf text or `externalfile` attribute in a read XML file, and any string in a
`.jsim`'s plugin inputs, that resolves to an existing file is followed with no role (field `<tag>` or `<plugin>.<key>`).

Reuses `scene_ref`: `_material_entries` (the material-file reader), `SKIPPED` (descriptive scene subtrees),
`MATERIAL_UNHELD_KEYS` and `MATERIAL_SEARCHED_KEYS` (the folders DIRSIG searches per material key).
"""
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import lxml.etree as et

from manifold.engines.dirsig import roles as _roles
from manifold.engines.dirsig.scene_ref import (MATERIAL_SEARCHED_KEYS, MATERIAL_UNHELD_KEYS, SKIPPED,
                                               _material_entries)

VIOLATION_KINDS = ("absolute", "dotdot", "non_nfc", "symlink", "outside_root", "form", "variable")
ERROR_KINDS = VIOLATION_KINDS                       # every violation rejects the tree (Cfg 2.3)
SCENE_DIRS = ("odbdirectory", "gdbdirectory", "emsdirectory", "extdirectory", "absdirectory", "srcdirectory",
              "mapdirectory")
ORPHAN_KINDS = {"atmosphericconditions": "atmosphere", "classicscene": "scene", "geometrylist": "geometry_list",
                "platform": "platform", "simulation": "sim"}      # root element -> reader, for scanning orphans only
_ABSOLUTE = re.compile(r"^(/|[A-Za-z]:[/\\]|\\\\)")
_FILE_KEY = re.compile(r"(FILE|FILENAME|SHAPE)$")


@dataclass(frozen=True)
class Reached:
    path: str
    role: str | None
    referrer: str
    field: str


@dataclass(frozen=True)
class Violation:
    kind: str
    text: str
    referrer: str
    field: str
    enabled: bool = True
    orphan: bool = False


@dataclass
class Walk:
    root: Path
    entry: str
    files: list = field(default_factory=list)
    violations: list = field(default_factory=list)
    unresolved: list = field(default_factory=list)      # (text, referrer, field)
    install: list = field(default_factory=list)         # (text, referrer, field)
    orphans: list = field(default_factory=list)
    role_conflicts: list = field(default_factory=list)  # (path, first role, other role, referrer, field)
    behind_links: list = field(default_factory=list)    # files under a crossed link that no reference reached

    @property
    def unroled(self):
        return [f for f in self.files if f.role is None]

    @property
    def links(self):
        """The distinct root-relative symbolic links the reached paths cross."""
        return sorted({v.text for v in self.violations if v.kind == "symlink"})

    def kinds(self):
        """The violation kinds reported, sorted."""
        return sorted({v.kind for v in self.violations})

    @property
    def passes(self):
        """No error: no violation, no unresolved reference, no unroled file and no role conflict (Cfg A.4: an orphan is
        a warning)."""
        return not (self.violations or self.unresolved or self.unroled or self.role_conflicts)

    @property
    def clean(self):
        """`passes` and no orphan."""
        return self.passes and not self.orphans


@dataclass(frozen=True)
class _Ref:
    field: str
    text: str
    bases: tuple            # absolute folders, in search order
    enabled: bool = True
    scene: object = None    # the _Scene context passed to what the reference reaches


@dataclass(frozen=True)
class _Scene:
    folder: Path
    dirs: tuple             # ((element, absolute folder or None), ...)

    def dir(self, tag):
        return dict(self.dirs).get(tag)


def _enabled(el):
    return all(str(a.get("enabled", "true")).strip().lower() not in ("false", "0")
               for a in [el, *el.iterancestors()])


def _parse_xml(path):
    try:
        return et.parse(str(path), et.XMLParser(remove_comments=True)).getroot()
    except (et.XMLSyntaxError, OSError, ValueError):
        return None


def _expand(text, scene):
    """`(text with $SCENE_DIR expanded to a root-relative-able absolute prefix, install flag)`."""
    t = text.strip()
    if t.startswith("$DIRSIG_HOME"):
        return t, True
    if scene is not None and re.match(r"^\$SCENE_DIR(/|$)", t):
        rest = t[len("$SCENE_DIR"):].lstrip("/")
        return (str(scene.folder / rest) if rest else str(scene.folder)), False
    return t, False


def _text_violations(text):
    """Violation kinds of a reference's text alone (before resolution)."""
    kinds = []
    if _ABSOLUTE.match(text):
        kinds.append("absolute")
    if re.match(r"^\$(?!SCENE_DIR\b|DIRSIG_HOME\b)", text):
        kinds.append("variable")
    if not unicodedata.is_normalized("NFC", text):
        kinds.append("non_nfc")
    rel = text[2:] if text.startswith("./") else text            # a walker strips a leading ./ (Cfg 2.3)
    segs = rel.replace("\\", "/").split("/")
    if ".." in segs:
        kinds.append("dotdot")
    if ("\\" in text or any(s in ("", ".") for s in (segs[1:] if "absolute" in kinds else segs))
            or any(ord(c) < 0x20 or ord(c) == 0x7F for c in text)):
        kinds.append("form")
    return kinds


class _Walker:
    def __init__(self, root, entry):
        self.root = Path(os.path.abspath(root))
        self.entry = PurePosixPath(entry).as_posix()
        self.workdir = (self.root / self.entry).parent
        self.result = Walk(self.root, self.entry)
        self.seen = {}

    # --- resolution ---------------------------------------------------------------------------------------------------
    def _rel(self, path):
        rel = os.path.relpath(os.path.normpath(path), self.root)
        return None if rel == ".." or rel.startswith("../") else PurePosixPath(rel).as_posix()

    def _links(self, rel):
        parts, out = rel.split("/"), []
        for i in range(1, len(parts) + 1):
            if (self.root / "/".join(parts[:i])).is_symlink():
                out.append("/".join(parts[:i]))
        return out

    def resolve(self, ref, referrer, orphan=False):
        """The root-relative path `ref` reaches (None if it reaches none), with its violations recorded."""
        raw = ref.text.strip()
        if not raw:
            return None
        text, install = _expand(raw, ref.scene)
        kinds = _text_violations(raw)
        for k in kinds:
            self.result.violations.append(Violation(k, raw, referrer, ref.field, ref.enabled, orphan))
        if install:
            if ref.enabled and not orphan:
                self.result.install.append((raw, referrer, ref.field))
            return None
        if not ref.enabled or orphan or {"absolute", "variable"} & set(kinds):
            return None
        local = text[2:] if text.startswith("./") else text
        local = local.replace("\\", "/")
        if os.path.isabs(local):                     # $SCENE_DIR expanded: already a full path under the root
            candidates = [Path(local)]
        else:
            candidates = [Path(b) / local for b in ref.bases if b is not None]
        escaped = False
        for cand in candidates:
            rel = self._rel(cand)
            if rel is None:
                escaped = True
                continue
            if (self.root / rel).is_file():
                for link in self._links(rel):
                    self.result.violations.append(Violation("symlink", link, referrer, ref.field))
                return rel
        if escaped:
            self.result.violations.append(Violation("outside_root", raw, referrer, ref.field))
        else:
            self.result.unresolved.append((raw, referrer, ref.field))
        return None

    # --- readers ------------------------------------------------------------------------------------------------------
    def _generic(self, root_el, consumed, bases, scene):
        """Every other leaf text or `externalfile` attribute of an XML file, outside the descriptive subtrees."""
        refs = []
        for el in root_el.iter():
            if not isinstance(el.tag, str) or el in consumed or any(a.tag in SKIPPED for a in el.iterancestors()):
                continue
            if el.tag in SKIPPED:
                continue
            if el.get("externalfile"):
                refs.append(_Ref(el.tag, el.get("externalfile"), bases, _enabled(el), scene))
            if len(el) == 0 and (el.text or "").strip() and _looks_like_path(el.text.strip()):
                refs.append(_Ref(el.tag, el.text, bases, _enabled(el), scene))
        return [(None, r) for r in refs]

    def read_jsim(self, path, scene):
        try:
            doc = json.loads(Path(path).read_text())
        except (ValueError, OSError):
            return []
        bases, out = (self.workdir,), []
        for entry in doc if isinstance(doc, list) else [doc]:
            if not isinstance(entry, dict):
                continue
            for s in entry.get("scene_list") or []:
                text = s.get("inputs") if isinstance(s, dict) else s
                if isinstance(text, str):
                    text = text[:-len(".hdf")] if text.endswith(".scene.hdf") else text
                    out.append(("scene_list.inputs", _Ref("scene_list.inputs", text, bases)))
            for plugin in (entry.get("plugin_list") or []) + (entry.get("medium_list") or []):
                if not isinstance(plugin, dict):
                    continue
                for key, value in _strings(plugin.get("inputs")):
                    name = f"{plugin.get('name')}.{key}"
                    if _roles.role_for("jsim", name) or _looks_like_path(value):
                        out.append((name if _roles.role_for("jsim", name) else None, _Ref(name, value, bases)))
        return out

    def read_sim(self, path, scene):
        root_el = _parse_xml(path)
        if root_el is None:
            return []
        bases, out, consumed = (self.workdir,), [], set()
        for el in root_el:
            if isinstance(el.tag, str) and el.get("externalfile"):
                consumed.add(el)
                text = el.get("externalfile")
                text = text[:-len(".hdf")] if el.tag == "scene" and text.endswith(".scene.hdf") else text
                out.append((el.tag if _roles.role_for("sim", el.tag) else None,
                            _Ref(el.tag, text, bases, _enabled(el))))
        return out + self._generic(root_el, consumed, bases, None)

    def read_atmosphere(self, path, scene):
        root_el = _parse_xml(path)
        if root_el is None:
            return []
        bases, out, consumed = (Path(path).parent, self.workdir), [], set()
        for el in root_el.iter("filename"):
            if el.getparent() is not None and el.getparent().tag == "classicdata":
                consumed.add(el)
                out.append(("classicdata.filename", _Ref("classicdata.filename", el.text or "", bases, _enabled(el))))
        for el in root_el.iter("adbfile"):
            consumed.add(el)
            out.append(("adbfile", _Ref("adbfile", el.text or "", bases, _enabled(el))))
        return out + self._generic(root_el, consumed, bases, None)

    def read_platform(self, path, scene):
        root_el = _parse_xml(path)
        if root_el is None:
            return []
        bases, out, consumed = (self.workdir, Path(path).parent), [], set()
        for el in root_el.iter("filename"):
            consumed.add(el)
            out.append(("filename", _Ref("filename", el.text or "", bases, _enabled(el))))
        return out + self._generic(root_el, consumed, bases, None)

    def read_scene(self, path, scene):
        root_el = _parse_xml(path)
        if root_el is None:
            return []
        folder = Path(path).parent
        here = _Scene(folder, ())
        dirs = []
        for tag in SCENE_DIRS:
            text = (root_el.findtext(tag) or "").strip()
            if not text:
                dirs.append((tag, None))
                continue
            expanded, _ = _expand(text, here)
            dirs.append((tag, Path(expanded) if os.path.isabs(expanded) else folder / expanded))
        ctx = _Scene(folder, tuple(dirs))
        consumed, out = {el for tag in SCENE_DIRS for el in root_el.iter(tag)}, []
        for el in root_el.iter("geometrylistinclude"):
            consumed.add(el)
            out.append(("geometrylistinclude", _Ref("geometrylistinclude", el.text or "",
                                                    (ctx.dir("gdbdirectory"), self.workdir), _enabled(el), ctx)))
        for el in root_el.iter("matfilename"):
            consumed.add(el)
            out.append(("matfilename", _Ref("matfilename", el.text or "", (folder, self.workdir), _enabled(el), ctx)))
        for kind in ("materialmap", "texturemap"):
            for m in root_el.iter(kind):
                for el in m.iter("filename"):
                    consumed.add(el)
                    out.append((f"{kind}.filename", _Ref(f"{kind}.filename", el.text or "",
                                                         (ctx.dir("mapdirectory"), self.workdir), _enabled(el), ctx)))
        return out + self._generic(root_el, consumed, (folder, self.workdir), ctx)

    def read_geometry_list(self, path, scene):
        root_el = _parse_xml(path)
        if root_el is None:
            return []
        own = Path(path).parent
        gdb = scene.dir("gdbdirectory") if scene is not None else None
        out, consumed = [], set()
        for el in root_el.iter("filename", "localmaterials"):
            consumed.add(el)
            obj = next((a for a in el.iterancestors("object")), None)
            local = obj is not None and obj.get("search_paths") == "local"
            bases = ((own,) if local else ()) + (gdb, self.workdir, own)
            parent = el.getparent().tag if el.getparent() is not None else ""
            if el.tag == "localmaterials":
                name = "localmaterials"
            elif any(a.tag == "dynamicinstance" for a in el.iterancestors()):
                name = "dynamicinstance.filename"
            elif parent == "glist":
                name = "glist.filename"
            elif any(a.tag == "basegeometry" for a in el.iterancestors()):
                name = "basegeometry.filename"
            else:
                name = f"{parent}.filename"
            out.append((name, _Ref(name, el.text or "", bases, _enabled(el), scene)))
        return out + self._generic(root_el, consumed, (own, gdb, self.workdir), scene)

    def read_material_db(self, path, scene):
        try:
            text = Path(path).read_bytes().decode("utf-8", "surrogateescape")   # names as the bytes DIRSIG reads
        except OSError:
            return []
        searched = {(b, k): tags for b, k, tags in MATERIAL_SEARCHED_KEYS}
        unheld = {(b, k): (tag,) for b, k, tag in MATERIAL_UNHELD_KEYS}
        own, out = Path(path).parent, []
        for block, key, value in _material_entries(text):
            if not _FILE_KEY.search(key):
                continue
            value = value.strip('"')
            name = f"{block}.{key}"
            if not (_roles.role_for("material_db", name) or _looks_like_path(value)):
                continue
            tags = searched.get((block, key)) or unheld.get((block, key)) or (
                ("extdirectory",) if block == "EXTINCTION_PROP" else ("emsdirectory",))
            folders = tuple(scene.dir(t) for t in tags) if scene is not None else ()
            out.append((name, _Ref(name, value, folders + (own, self.workdir), True, scene)))
        return out

    READERS = {"sim": "read_sim", "jsim": "read_jsim", "dirsig:scene": "read_scene",
               "dirsig:geometry_list": "read_geometry_list", "dirsig:material_db": "read_material_db",
               "dirsig:atmosphere": "read_atmosphere", "dirsig:platform": "read_platform"}
    REFERRER = {"sim": "sim", "jsim": "jsim", "dirsig:scene": "scene", "dirsig:geometry_list": "geometry_list",
                "dirsig:material_db": "material_db", "dirsig:atmosphere": "atmosphere", "dirsig:platform": "platform"}

    # --- the walk -----------------------------------------------------------------------------------------------------
    def run(self):
        entry_kind = "jsim" if self.entry.endswith(".jsim") else "sim"
        for kind in _text_violations(self.entry):
            self.result.violations.append(Violation(kind, self.entry, "", "entry"))
        if not (self.root / self.entry).is_file():
            self.result.unresolved.append((self.entry, "", "entry"))
            return self.result
        self._reach(self.entry, _roles.ENTRY_ROLE, "", "entry")
        queue = [(self.entry, entry_kind, None)]
        while queue:
            rel, kind, scene = queue.pop(0)
            reader = self.READERS.get(kind)
            if reader is None:
                continue
            for name, ref in getattr(self, reader)(self.root / rel, scene):
                got = self.resolve(ref, rel)
                if got is None:
                    continue
                role = _roles.role_for(self.REFERRER[kind], name) if name else None
                if self._reach(got, role, rel, ref.field) and role in self.READERS:
                    queue.append((got, role, ref.scene))
        self._orphans()
        self.result.files.sort(key=lambda f: f.path.encode("utf-8"))
        return self.result

    def _reach(self, rel, role, referrer, fld):
        """Record `rel`; True the first time it is reached."""
        if rel in self.seen:
            first = self.seen[rel]
            if first.role != role and role is not None:
                if first.role is None:                       # a generic reach first, a roled one now: take the role
                    self.result.files.remove(first)
                    self.seen[rel] = Reached(rel, role, referrer, fld)
                    self.result.files.append(self.seen[rel])
                    return True
                self.result.role_conflicts.append((rel, first.role, role, referrer, fld))
            return False
        self.seen[rel] = Reached(rel, role, referrer, fld)
        self.result.files.append(self.seen[rel])
        return True

    def _orphans(self):
        for top, dirs, names in os.walk(self.root, followlinks=False):
            for name in sorted(names) + sorted(d for d in dirs if (Path(top) / d).is_symlink()):
                rel = PurePosixPath(os.path.relpath(Path(top) / name, self.root)).as_posix()
                if rel in self.seen or any(f.startswith(rel + "/") for f in self.seen):
                    continue
                self.result.orphans.append(rel)
                path = self.root / rel
                if path.is_file() and not path.is_symlink():
                    self._scan_orphan(rel)
        self.result.orphans.sort(key=lambda p: p.encode("utf-8"))
        for link in self.result.links:
            for top, _, names in os.walk(self.root / link, followlinks=True):
                for name in names:
                    rel = PurePosixPath(os.path.relpath(Path(top) / name, self.root)).as_posix()
                    if rel not in self.seen:
                        self.result.behind_links.append(rel)
        self.result.behind_links.sort(key=lambda p: p.encode("utf-8"))

    def _scan_orphan(self, rel):
        root_el = _parse_xml(self.root / rel) if (self.root / rel).stat().st_size < 50_000_000 else None
        kind = ORPHAN_KINDS.get(root_el.tag) if root_el is not None and isinstance(root_el.tag, str) else None
        if kind is None:
            return
        reader = self.READERS["sim" if kind == "sim" else f"dirsig:{kind}"]
        for _, ref in getattr(self, reader)(self.root / rel, None):
            self.resolve(ref, rel, orphan=True)


def _looks_like_path(text):
    """A string that may name a file: no whitespace, and a `/`, a `\\` or a suffix."""
    t = text.strip()
    return bool(t) and not re.search(r"\s", t) and ("/" in t or "\\" in t or re.search(r"\.[A-Za-z][A-Za-z0-9_]*$", t)
                                                    is not None) and not re.match(r"^[-+0-9.eE,]+$", t)


def _strings(value, prefix=""):
    """`(dotted key, string)` of every string under a JSON value."""
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v, prefix)


def walk(root, entry):
    """Walk the run tree under `root` from its simulation file `entry` (a root-relative path). Returns a `Walk`."""
    return _Walker(root, entry).run()
