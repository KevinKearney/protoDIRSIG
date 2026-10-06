"""Spectral coverage of a pre-built DIRSIG scene's REAL material database.

Why this exists (FINDINGS.md, Phase 3): when a scene is referenced through dirfm's
`SCENE._fname` escape hatch, dirfm's own `_check_coverage()` runs against a placeholder
`Dummy` material with no surface properties, so it passes for ANY band — even 5–50 µm. This
module answers the question that check appears to answer: "do this scene's materials cover
band [a, b]?", by reading the `.mat` file the `.scene` actually points at.

Scope is deliberately small — the material kinds this project has met — and it FAILS CLOSED:
a surface property or file it does not understand makes that material "unknown", and
`covers()` returns False for any band until the parser is taught about it.

  inline WardBRDF (DS_WEIGHTS)     -> wavelength-independent: covers every band
  ClassicEmissivity (FILENAME)     -> the .ems file's curves
  ShellTarget (BRDF_FIT_FILE, EMISSIVITY_FILE) -> the .fit LAMBDA entries and the .ems curves
  SimpleReflectance (TXT_FILENAME) -> the two-column wavelength/reflectance table
  MATERIAL_MAP proxy (LUT n:ID)    -> the intersection of its LUT targets' spans

A material's span is the intersection of the spans of every file it references; a
multi-curve .ems file contributes its NARROWEST curve.

Materials come from the scene's `<matfilename>` AND from every bundle reached through the
scene's enabled `<geometrylistinclude>` .glist files (`<localmaterials>`, recursively through
`<basegeometry><glist>`). Bundle materials are what an object like a `geometrylistinclude`d
vehicle actually renders with; a report on `<matfilename>` alone would silently omit them.
ODB includes are not opened (they use the scene's own material database).
"""
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import lxml.etree as et

FLAT_PROPS = {"WardBRDF"}                                  # inline, no wavelength dependence
FILE_PROPS = {"ClassicEmissivity", "ShellTarget", "SimpleReflectance"}
FILE_KEYS = ("FILENAME", "EMISSIVITY_FILE", "BRDF_FIT_FILE", "TXT_FILENAME")


@dataclass
class MaterialCoverage:
    id: str
    name: str
    props: list
    files: dict = field(default_factory=dict)              # file name -> (lo, hi, n curves / points)
    unknown: list = field(default_factory=list)            # reasons coverage could not be established
    source: Path = None                                    # the .mat file this entry came from

    @property
    def span(self):
        """(lo, hi) µm this material is defined over; (-inf, inf) if wavelength-independent; None if unknown."""
        if self.unknown:
            return None
        if not self.files:
            return (-math.inf, math.inf)
        return (max(lo for lo, _, _ in self.files.values()), min(hi for _, hi, _ in self.files.values()))

    def covers(self, lo, hi):
        s = self.span
        return s is not None and s[0] <= lo and hi <= s[1]


@dataclass
class SceneCoverage:
    scene: Path
    mat_file: Path
    materials: list                                        # scene .mat entries, then bundle entries
    texture_bands: list                                    # (map name, matid, lo, hi), enabled maps only
    bundle_mats: list = field(default_factory=list)        # bundle .mat files reached via the glists

    @property
    def unknown(self):
        return [m for m in self.materials if m.unknown]

    @property
    def span(self):
        """Band covered by EVERY material (None if any material is unknown)."""
        if self.unknown:
            return None
        spans = [m.span for m in self.materials]
        return (max(s[0] for s in spans), min(s[1] for s in spans))

    def gaps(self, lo, hi):
        """Materials that do not cover [lo, hi] µm (unknown materials included)."""
        return [m for m in self.materials if not m.covers(lo, hi)]

    def covers(self, lo, hi):
        return not self.gaps(lo, hi)


def _resolve(text, scene_dir):
    return Path(text.strip().replace("$SCENE_DIR", str(scene_dir)))


def ems_span(path):
    """(narrowest-curve start, narrowest-curve end, number of curves) of a two-column curve file
    (.ems, or a SimpleReflectance .txt table)."""
    spans, block = [], []
    for ln in Path(path).read_text().splitlines():
        parts = ln.split()
        if len(parts) == 2:
            block.append(float(parts[0]))
        elif block:
            spans.append((block[0], block[-1]))
            block = []
    if block:
        spans.append((block[0], block[-1]))
    if not spans:
        raise ValueError(f"no wavelength curves in {path}")
    return max(s for s, _ in spans), min(e for _, e in spans), len(spans)


def fit_span(path):
    """(min, max, count) of the LAMBDA entries (µm) in a Shell-target .fit file."""
    lam = [float(x) for x in re.findall(r"LAMBDA\s*=\s*([\d.eE+-]+)", Path(path).read_text())]
    if not lam:
        raise ValueError(f"no LAMBDA entries in {path}")
    return min(lam), max(lam), len(lam)


def _pop_block(body, key):
    """(body with the `key { ... }` block removed, the block's contents or None); braces nest."""
    m = re.search(rf"^\s*{key}\s*\{{", body, flags=re.M)
    if not m:
        return body, None
    depth, i = 1, m.end()
    while depth and i < len(body):
        depth += {"{": 1, "}": -1}.get(body[i], 0)
        i += 1
    return body[:m.start()] + body[i:], body[m.end():i - 1]


def parse_mat(mat_file, file_dirs):
    """MaterialCoverage for every MATERIAL_ENTRY in a DIRSIG .mat file.

    `file_dirs` are searched in order for referenced .ems/.fit/.txt files. A MATERIAL_MAP proxy
    (a classification image plus a LUT of material IDs in the same file) takes the intersection
    of its LUT targets' spans; its IMAGE_FILENAME is a class map, not spectral data.
    """
    text = Path(mat_file).read_text()
    out, remaps = [], {}
    for body in re.findall(r"MATERIAL_ENTRY\s*\{(.*?)\n\}", text, flags=re.S):
        body, mat_map = _pop_block(body, "MATERIAL_MAP")
        mid = re.search(r"^\s*ID\s*=\s*(\S+)", body, flags=re.M)
        name = re.search(r"^\s*NAME\s*=\s*(.+)$", body, flags=re.M)
        props = re.findall(r"_PROP_NAME\s*=\s*(\S+)", body)
        m = MaterialCoverage(mid.group(1) if mid else "?", name.group(1).strip() if name else "?", props,
                             source=Path(mat_file))
        if mat_map is not None:
            remaps[id(m)] = re.findall(r"^\s*\d+\s*:\s*(\S+)\s*$", mat_map, flags=re.M)
            if not remaps[id(m)]:
                m.unknown.append("MATERIAL_MAP without LUT entries")
        for p in props:
            if p not in FLAT_PROPS | FILE_PROPS:
                m.unknown.append(f"surface property {p!r} not understood")
        for key in re.findall(r"^\s*([A-Z_]+)\s*=\s*\S+\.[A-Za-z]{2,4}\s*$", body, flags=re.M):
            if key not in FILE_KEYS:
                m.unknown.append(f"file reference {key!r} not understood")
        for f in re.findall(rf"(?:{'|'.join(FILE_KEYS)})\s*=\s*(\S+)", body):
            path = next((Path(d) / f for d in file_dirs if (Path(d) / f).is_file()), None)
            if path is None:
                m.unknown.append(f"{f} not found in {[str(d) for d in file_dirs]}")
                continue
            try:
                m.files[f] = fit_span(path) if f.endswith(".fit") else ems_span(path)
            except ValueError as e:
                m.unknown.append(str(e))
        out.append(m)
    by_id = {m.id: m for m in out}
    for m in out:
        for target in remaps.get(id(m), []):
            t = by_id.get(target)
            if t is None or target == m.id:
                m.unknown.append(f"MATERIAL_MAP target {target!r} not in {Path(mat_file).name}")
                continue
            m.files.update(t.files)
            m.unknown += [f"via {target}: {u}" for u in t.unknown]
    return out


def _find(name, dirs):
    return next((Path(d) / name for d in dirs if (Path(d) / name).is_file()), None)


def _glist_mats(glist, geom_dirs, scene_dirs, seen):
    """[(.mat path or None, file search dirs, where it was declared)] for the bundles under `glist`."""
    if glist in seen:
        return []
    seen.add(glist)
    out = []
    for obj in et.parse(str(glist)).getroot().iter("object"):
        if obj.get("enabled", "true").lower() == "false":
            continue
        local = obj.get("search_paths", "scene") == "local"
        dirs = [glist.parent] if local else [*geom_dirs, glist.parent]
        lm = obj.findtext("localmaterials")
        if lm:
            mat = _find(lm.strip(), [glist.parent] if local else [glist.parent, *scene_dirs])
            out.append((mat, [mat.parent] if (mat and local) else scene_dirs, f"{glist.name}: {lm.strip()}"))
        for fn in obj.iterfind("basegeometry/glist/filename"):
            sub = _find(fn.text.strip(), dirs)
            if sub is None:
                out.append((None, [], f"{glist.name}: glist {fn.text.strip()}"))
            else:
                out += _glist_mats(sub, geom_dirs, scene_dirs, seen)
    return out


def scene_coverage(scene_file):
    """Coverage report for the material databases a `.scene` file actually references:
    its `<matfilename>` plus every bundle `<localmaterials>` reached through its .glist includes."""
    scene_file = Path(scene_file)
    root = et.parse(str(scene_file)).getroot()
    mat_file = _resolve(root.findtext("matfilename"), scene_file.parent)
    ems = root.findtext("emsdirectory")
    file_dirs = ([_resolve(ems, scene_file.parent)] if ems else []) + [mat_file.parent]
    materials = parse_mat(mat_file, file_dirs)

    geom_dirs = [_resolve(root.findtext(k), scene_file.parent) for k in ("gdbdirectory", "odbdirectory")
                 if root.findtext(k)] or [scene_file.parent]
    bundles, seen = [], set()
    for inc in root.iterfind("geometrylist/geometrylistinclude"):
        if inc.get("enabled", "true").lower() == "false" or not inc.text.strip().endswith(".glist"):
            continue
        glist = _find(inc.text.strip(), geom_dirs)
        if glist is None:
            materials.append(MaterialCoverage("?", f"<include {inc.text.strip()}>", [],
                                              unknown=[f"{inc.text.strip()} not found in {geom_dirs}"]))
            continue
        for mat, dirs, where in _glist_mats(glist, geom_dirs, file_dirs, seen):
            if mat is None:
                materials.append(MaterialCoverage("?", f"<{where}>", [], unknown=[f"{where} not found"]))
            elif mat not in bundles:
                bundles.append(mat)
                materials += parse_mat(mat, dirs)

    textures = []
    for tm in root.iterfind("maplist/texturemap"):
        if tm.get("enabled", "true").lower() == "false":
            continue
        for b in tm.iterfind("bandlist/band/bandpass"):
            textures.append((tm.get("name"), tm.findtext("matidlist/matid"),
                             float(b.findtext("min")), float(b.findtext("max"))))
    return SceneCoverage(scene_file, mat_file, materials, textures, bundles)
