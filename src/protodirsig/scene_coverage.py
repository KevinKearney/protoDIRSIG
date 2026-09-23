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

A material's span is the intersection of the spans of every file it references; a
multi-curve .ems file contributes its NARROWEST curve.
"""
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import lxml.etree as et

FLAT_PROPS = {"WardBRDF"}                                  # inline, no wavelength dependence
FILE_PROPS = {"ClassicEmissivity", "ShellTarget"}
FILE_KEYS = ("FILENAME", "EMISSIVITY_FILE", "BRDF_FIT_FILE")


@dataclass
class MaterialCoverage:
    id: str
    name: str
    props: list
    files: dict = field(default_factory=dict)              # file name -> (lo, hi, n curves / points)
    unknown: list = field(default_factory=list)            # reasons coverage could not be established

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
    materials: list
    texture_bands: list                                    # (map name, matid, lo, hi) from the .scene

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
    """(narrowest-curve start, narrowest-curve end, number of curves) of a two-column .ems file."""
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


def parse_mat(mat_file, file_dirs):
    """MaterialCoverage for every MATERIAL_ENTRY in a DIRSIG .mat file.

    `file_dirs` are searched in order for referenced .ems/.fit files.
    """
    text = Path(mat_file).read_text()
    out = []
    for body in re.findall(r"MATERIAL_ENTRY\s*\{(.*?)\n\}", text, flags=re.S):
        mid = re.search(r"^\s*ID\s*=\s*(\S+)", body, flags=re.M)
        name = re.search(r"^\s*NAME\s*=\s*(.+)$", body, flags=re.M)
        props = re.findall(r"_PROP_NAME\s*=\s*(\S+)", body)
        m = MaterialCoverage(mid.group(1) if mid else "?", name.group(1).strip() if name else "?", props)
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
                m.files[f] = ems_span(path) if f.endswith(".ems") else fit_span(path)
            except ValueError as e:
                m.unknown.append(str(e))
        out.append(m)
    return out


def scene_coverage(scene_file):
    """Coverage report for the material database a `.scene` file actually references."""
    scene_file = Path(scene_file)
    root = et.parse(str(scene_file)).getroot()
    mat_file = _resolve(root.findtext("matfilename"), scene_file.parent)
    ems = root.findtext("emsdirectory")
    file_dirs = ([_resolve(ems, scene_file.parent)] if ems else []) + [mat_file.parent]
    textures = []
    for tm in root.iterfind("maplist/texturemap"):
        for b in tm.iterfind("bandlist/band/bandpass"):
            textures.append((tm.get("name"), tm.findtext("matidlist/matid"),
                             float(b.findtext("min")), float(b.findtext("max"))))
    return SceneCoverage(scene_file, mat_file, parse_mat(mat_file, file_dirs), textures)
