#!/usr/bin/env python3
"""Space-to-space coverage map: the realism axes against the measured records, written to `docs/s2s_coverage.md`.

    python scripts/s2s_coverage.py            (re)write docs/s2s_coverage.md from the records
    python scripts/s2s_coverage.py --check    regenerate in memory and compare with the committed document; also refuse
                                              an empty cell without a stated reason and a reason for a cell that has
                                              records; list every problem, exit 1 if any
    python scripts/s2s_coverage.py --print    print the document instead of writing it

The records are `docs/data/s2s_results.jsonl` (`scripts/s2s_measure.py`); each record's parameters are its index entry in
`manifold_run_specs/s2s/index.json` and its committed spec (the window, and the look angle of family II's orbit pair).
A record's id is its `spec` name, the key `s2s_measure.py` writes it under. Every record is classified by the rules in
`RULES` below (they are printed in the document), so the map changes only when the records or the rules do. An empty
cell carries its reason from `EMPTY`; a reason is a statement about the generator's vocabulary, the committed scenes or a
measured limit, with the document or BACKLOG item that records it.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import s2s_measure as sm                                                       # noqa: E402
import s2s_scenarios as s2s                                                    # noqa: E402

DOC = ROOT / "docs" / "s2s_coverage.md"
CLASSES = ("hyperresolved", "resolved", "unresolved")
HYPER_PX, RESOLVED_PX = 10.0, 1.0                  # across, in pixels: > 10 hyperresolved, 1 to 10 resolved, < 1 not


# --- one record's attributes --------------------------------------------------------------------------------------

def attributes(entry):
    """The axis values of one index entry: shape, size (pixels across), size class, label, motion, exposure (s),
    look and solar zenith (degrees, the stated ones), background and window (pixels)."""
    fam, p = sm.family(entry), sm.point(entry)
    spec = yaml.safe_load((s2s.OUT / f"{entry['name']}.yaml").read_text())
    window = spec["descriptor"]["settings"][0]["roi"]["Width"]
    if fam == 1:
        orbit = p["relative_speed"] == s2s.ORBIT
        size = s2s.PLATES[p["object_class"]]["side"] / s2s.footprint(p["range_m"])
        motion = "platform" if orbit else ("target" if p["relative_speed"] else None)
        a = {"shape": "plate", "size_px": size, "labelled": p["object_class"] != "unresolved_plain",
             "motion": motion, "exposure_s": p["exposure_s"], "look_deg": 0.0 if orbit else p["look_deg"],
             "solar_zenith_deg": p["solar_zenith_deg"], "background": "dark"}
    elif fam == 2:
        ex = s2s.expected2(p)
        group = {"static": None, "platform": "platform", "target": "target", "both": "combined",
                 "look": None, "orbit": "platform"}[p["group"]]
        a = {"shape": "plate", "size_px": ex["side_px"], "labelled": True, "motion": group,
             "exposure_s": p["exposure_s"], "look_deg": 0.0 if p["kind"] == "orbit" else p["look_deg"],
             "solar_zenith_deg": 0.0, "background": "dark" if p["kind"] == "orbit" else "barred"}
    else:
        ex = s2s.expected3(p)
        a = {"shape": "sphere", "size_px": ex["diameter_px"], "labelled": p["group"] != "unresolved_plain",
             "motion": None, "exposure_s": 0.005, "look_deg": p["look_deg"],
             "solar_zenith_deg": p["solar_zenith_deg"],
             "background": "barred" if p["kind"] == "background" else "dark"}
    a["size_class"] = ("hyperresolved" if a["size_px"] > HYPER_PX else
                       "resolved" if a["size_px"] >= RESOLVED_PX else "unresolved")
    a["window"] = window
    return a


# --- the rows -----------------------------------------------------------------------------------------------------
# (group, row, rule text, predicate on the attributes)

STILL = lambda a: a["motion"] is None                                                       # noqa: E731
RULES = [
    ("Motion", "Platform motion", "family II's `platform` blur group (the scene moves the other way) and the `orbit` "
     "form (family I's orbit point, family II's orbit pair)", lambda a: a["motion"] == "platform"),
    ("Motion", "Target motion", "family I's moving plates (1000 and 7500 m/s) and family II's `target` blur group",
     lambda a: a["motion"] == "target"),
    ("Motion", "Relative motion combined", "family II's `both` blur group (plates and background moving)",
     lambda a: a["motion"] == "combined"),
    ("Shutter", "Shutter time, still", "an exposure other than the 5 ms baseline, no motion",
     lambda a: STILL(a) and a["exposure_s"] != 0.005),
    ("Shutter", "Shutter time, moving", "an exposure other than 5 ms, with motion (a streak)",
     lambda a: not STILL(a) and a["exposure_s"] != 0.005),
    *[(f"Geometry, {s}s", f"{axis}, {s}", text, (lambda pred, s: lambda a: a["shape"] == s and pred(a))(pred, s))
      for s in ("plate", "sphere") for axis, text, pred in (
          ("Look angle off nadir", "a stated look angle above 0 with the Sun at the zenith (the orbit form's look "
           "angle is the TLE's and is not counted)", lambda a: a["look_deg"] > 0 and a["solar_zenith_deg"] == 0),
          ("Sun angle", "a solar zenith above 0 seen at nadir",
           lambda a: a["solar_zenith_deg"] > 0 and a["look_deg"] == 0),
          ("Phase angle, look and Sun both off zero", "a stated look angle and a solar zenith both above 0",
           lambda a: a["look_deg"] > 0 and a["solar_zenith_deg"] > 0),
          ("Range and sub-pixel position", "still, nadir, Sun at the zenith, 5 ms (the range sweeps, the sub-pixel "
           "offsets and the baselines)", lambda a: STILL(a) and a["exposure_s"] == 0.005 and a["look_deg"] == 0
           and a["solar_zenith_deg"] == 0))],
    ("Shape", "Flat plate", "a square Lambertian plate (families I and II)", lambda a: a["shape"] == "plate"),
    ("Shape", "Sphere", "a Lambertian analytic sphere (family III)", lambda a: a["shape"] == "sphere"),
    ("Shape", "Specular facet", "a facet with a specular BRDF", lambda a: a["shape"] == "facet"),
    ("Background", "Dark sky", "a black backstop (reflectance 0) or nothing behind the target",
     lambda a: a["background"] == "dark"),
    ("Background", "Barred plate", "family II's barred plate behind the target (families II and III)",
     lambda a: a["background"] == "barred"),
    ("Background", "Earth limb or albedo", "an Earth model beside or behind the target",
     lambda a: a["background"] == "earth"),
    ("Sampling", "Unlabelled (no `::IMPORTANT::`)", "the target's instance is not named `::IMPORTANT::`",
     lambda a: not a["labelled"]),
]

# (row, class) -> why the cell is empty
_FACET = ("not in the generator's vocabulary: every generated scene has one material, SimpleReflectance (Lambertian; "
          "`MATERIAL` in `scripts/s2s_scenarios.py`); a specular facet needs a new material in a generated scene "
          "(BACKLOG \"Space-to-space: what round 38 leaves open\")")
_EARTH = ("not expressible: no committed scene holds an Earth model and a run spec takes one `engine.scenes` entry "
          "(BACKLOG \"Space-to-space: what round 30 leaves open\" (7)); the barred plate is the generator's only "
          "background")
_SPHERES = ("family III has one range, 25 km (`SUN3`), so its spheres are 24.5 px (10 m) and 0.61 px (0.25 m) "
            "across; it has no range axis")
_ONE_AXIS = ("family I varies one axis at a time about each class's baseline (`GRID`): the 20 m plate at 25 km "
             "(24.5 px) and the 0.5 m plates at 200 km (0.08 px), and round 38's `COVERAGE` points are the same plates at "
             "25 km (24.5 and 0.61 px); no point between 1 and 10 px")
_SPLIT = ("family III splits the phase angle all into the look or all into the Sun for the 10 m sphere only "
          "(`SPLIT_PHASE`); the 0.25 m spheres take look and Sun each half of it")
_NOT_REDUCED = ("the 0.5 m plates beside family II's blur and barred targets are rendered but not reduced: the harness "
                "measures the 20 m target only, and an unresolved streak is a few hits (BACKLOG \"Space-to-space: "
                "what round 30 leaves open\" (2))")
EMPTY = {
    ("Target motion", "resolved"):
        "family I's moving plates are 0.5 m at 200 km (0.08 px) and family II's target group the 20 m plate at "
        "25 km (24.5 px); a moving plate's size and speed are scene content, one per instance (`MOVING`, `BLUR`)",
    ("Relative motion combined", "resolved"):
        "family II's `both` group holds the 20 m plate (24.5 px) and a 0.5 m plate (0.61 px); nothing between",
    ("Relative motion combined", "unresolved"): _NOT_REDUCED,
    ("Shutter time, still", "resolved"): _ONE_AXIS,
    ("Shutter time, moving", "unresolved"):
        "family I's moving plates and its orbit point are at 5 ms only (`GRID` varies one axis at a time); "
        + _NOT_REDUCED[0].lower() + _NOT_REDUCED[1:],
    ("Look angle off nadir, plate", "resolved"): _ONE_AXIS,
    ("Sun angle, plate", "resolved"): _ONE_AXIS,
    ("Phase angle, look and Sun both off zero, plate", "resolved"): _ONE_AXIS,
    ("Look angle off nadir, sphere", "resolved"): _SPHERES,
    ("Look angle off nadir, sphere", "unresolved"): _SPLIT,
    ("Sun angle, sphere", "resolved"): _SPHERES,
    ("Sun angle, sphere", "unresolved"): _SPLIT,
    ("Phase angle, look and Sun both off zero, sphere", "resolved"): _SPHERES,
    ("Range and sub-pixel position, sphere", "resolved"): _SPHERES,
    ("Sphere", "resolved"): _SPHERES,
    ("Specular facet", "hyperresolved"): _FACET,
    ("Specular facet", "resolved"): _FACET,
    ("Specular facet", "unresolved"): _FACET,
    ("Barred plate", "resolved"): "the barred groups' targets are the 20 m plate and the 10 m sphere at 25 km "
                                  "(24.5 px)",
    ("Barred plate", "unresolved"): _NOT_REDUCED,
    ("Earth limb or albedo", "hyperresolved"): _EARTH,
    ("Earth limb or albedo", "resolved"): _EARTH,
    ("Earth limb or albedo", "unresolved"): _EARTH,
    ("Unlabelled (no `::IMPORTANT::`)", "hyperresolved"):
        "every unlabelled target is a 0.5 m plate or a 0.25 m sphere; the label matters only below about a pixel",
}


# --- the map ------------------------------------------------------------------------------------------------------

def classified():
    """[(record, attributes)] for every record of the results file."""
    idx = sm.index()
    return [(r, attributes(idx[r["spec"]])) for r in sm.load_results()]


def cells(records):
    """{(row, class): [record, ...]} in the results file's order."""
    out = {(row, c): [] for _, row, _, _ in RULES for c in CLASSES}
    for r, a in records:
        for _, row, _, pred in RULES:
            if pred(a):
                out[(row, a["size_class"])].append((r, a))
    return out


def _ratio(r):
    return "no ratio" if r["ratio"] is None else f"{r['method']} {r['ratio']:.4f}"


def document(records=None):
    records = classified() if records is None else records
    cs = cells(records)
    lines = ["# Space-to-space coverage map", "",
             "<!-- GENERATED by scripts/s2s_coverage.py from docs/data/s2s_results.jsonl - do not edit; "
             "python scripts/s2s_coverage.py --check compares -->", "",
             f"The realism axes of space-to-space imaging against the {len(records)} records of "
             "`docs/data/s2s_results.jsonl` (written by `scripts/s2s_measure.py`; the account of each family is "
             "[the characterization](Space_to_space_characterization.md)). A record's id is its `spec` name. Each "
             "record is classified by its index entry in `manifold_run_specs/s2s/index.json` and its committed spec "
             "by the rules below; a record counts in every row whose rule it meets. An empty cell states why it is "
             "empty. `python scripts/s2s_coverage.py` writes this document and `--check` refuses a stale one.", "",
             "## Classes", "",
             f"- **hyperresolved**: the target is more than {HYPER_PX:g} pixels across (plate side or sphere "
             "diameter over the pixel footprint at the stated range).",
             f"- **resolved**: {RESOLVED_PX:g} to {HYPER_PX:g} pixels across.",
             f"- **unresolved**: under {RESOLVED_PX:g} pixel across.", "",
             "## Rows", ""]
    lines += [f"- **{row}** ({group}): {text}." for group, row, text, _ in RULES]
    lines += ["", "## The map", "",
              "Each cell: the number of records, or the empty cell's reason number (below).", "",
              "| Group | Axis | " + " | ".join(CLASSES) + " |", "|---|---|" + "---|" * len(CLASSES)]
    reasons, empty = [], {}
    for group, row, _, _ in RULES:
        row_cells = []
        for c in CLASSES:
            n = len(cs[(row, c)])
            if n:
                row_cells.append(str(n))
            else:
                why = EMPTY.get((row, c))
                if why not in reasons:
                    reasons.append(why)
                empty[(row, c)] = reasons.index(why) + 1
                row_cells.append(f"empty ({empty[(row, c)]})")
        lines.append(f"| {group} | {row} | " + " | ".join(row_cells) + " |")
    lines += ["", "## Why the empty cells are empty", ""]
    lines += [f"{i}. {why or 'NO REASON STATED'}" for i, why in enumerate(reasons, 1)]
    lines += ["", "## Records per cell", "",
              "Each record with its primary measurement's ratio (measured over the closed form), its size in pixels "
              "and its window.", ""]
    for _, row, _, _ in RULES:
        for c in CLASSES:
            got = cs[(row, c)]
            if not got:
                continue
            lines += [f"### {row}, {c} ({len(got)})", ""]
            lines += [f"- `{r['spec']}`: {_ratio(r)}; {a['size_px']:.2f} px; {a['window']} x {a['window']}"
                      for r, a in got]
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def problems(records=None):
    records = classified() if records is None else records
    cs = cells(records)
    out = []
    for key, got in cs.items():
        if not got and not EMPTY.get(key):
            out.append(f"{key[0]} x {key[1]}: empty, and EMPTY states no reason")
        if got and EMPTY.get(key):
            out.append(f"{key[0]} x {key[1]}: has {len(got)} records, and EMPTY still states a reason")
    unknown = set(EMPTY) - set(cs)
    out += [f"{k[0]} x {k[1]}: a reason for a cell that is not in the map" for k in sorted(unknown)]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="compare with the committed document; exit 1 on a problem")
    ap.add_argument("--print", action="store_true", help="print the document instead of writing it")
    a = ap.parse_args(argv)
    records = classified()
    text = document(records)
    found = problems(records)
    if a.print:
        print(text, end="")
        return 0
    if a.check:
        if not DOC.is_file() or DOC.read_text() != text:
            where = DOC.relative_to(ROOT) if DOC.is_relative_to(ROOT) else DOC
            found.append(f"{where}: missing or stale (python scripts/s2s_coverage.py rewrites it)")
        print("\n".join(found) if found else f"{len(records)} records, {len(RULES)} rows x {len(CLASSES)} classes: "
                                             f"the coverage map is current")
        return 1 if found else 0
    if found:
        print("\n".join(found))
        return 1
    DOC.write_text(text)
    print(f"wrote {DOC.relative_to(ROOT)} ({len(records)} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
