#!/usr/bin/env python3
"""Space-to-space sampling-effect envelope: how far DIRSIG's records fall from their closed forms, by target size in
pixels and motion, written to `docs/s2s_envelope.md`.

    python scripts/s2s_envelope.py            (re)write docs/s2s_envelope.md from the records
    python scripts/s2s_envelope.py --check    regenerate in memory and compare with the committed document; also refuse
                                              a row whose deficit exceeds `QUIET` without a stated `REMOVED_BY` text,
                                              and a text for a row that has no records; exit 1 on a problem
    python scripts/s2s_envelope.py --print    print the document instead of writing it

The records are `docs/data/s2s_results.jsonl` (`scripts/s2s_measure.py`). Each DIRSIG record's size (pixels across),
motion, look, Sun and label are `scripts/s2s_coverage.py`'s `attributes`; its placement is family I's `offset_px`
(families II and III place the target on the frame's centre and do not vary it). A record is in the envelope when its
target is at least `MIN_PX` across and its geometry is valid (`excluded` names the others and why). Its measurements
are the primary flux closure and, for a streak at least `MIN_SWEEP_PX` long, the fitted sweep length; the deficit of a
measurement is 1 - measured / closed form (negative: an excess). The rows group the records by size (`BINS`), motion and
label; a SatSim control (round 40) is listed beside the DIRSIG record it images (its `s2s.engine_counterpart`). The
`REMOVED_BY` texts state what the records show removes a row's deficit; nothing here is tuned.
"""
import argparse
import math
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import s2s_coverage as cov                                                     # noqa: E402
import s2s_measure as sm                                                       # noqa: E402
import s2s_scenarios as s2s                                                    # noqa: E402

DOC = ROOT / "docs" / "s2s_envelope.md"
MIN_PX = 0.3                       # below this a plate is a few hits per frame (round 29): not a sampling envelope
MIN_SWEEP_PX = 1.0                 # a shorter sweep reads long by DIRSIG's own spread (round 30), not by sampling
QUIET = 0.01                       # a row whose every deficit is within 1 % needs no REMOVED_BY text
BINS = ((0.3, 0.5, "0.3 to 0.5"), (0.5, 1.0, "0.5 to 1"), (1.0, 2.0, "1 to 2"), (2.0, 6.0, "2 to 6"), (6.0, 13.0, "6 to 13"),
        (13.0, math.inf, "over 13"))
MOTIONS = ("fixed", "tracked", "platform", "target", "both")
_MOTION = {None: "fixed", "platform": "platform", "target": "target", "combined": "both"}


def motion(entry, a):
    """fixed, tracked (the orbit form: the platform moves and the line of sight follows the target, no streak),
    platform, target or both."""
    p = sm.point(entry)
    if sm.family(entry) == 2 and p["kind"] == "orbit":
        return "tracked"
    return _MOTION[a["motion"]]


def size_bin(px):
    return next((name for lo, hi, name in BINS if lo <= px < hi), None)


# --- one record ---------------------------------------------------------------------------------------------------

def excluded(entry, a):
    """Why a DIRSIG record is outside the envelope, or None."""
    if a["size_px"] < MIN_PX:
        return f"under {MIN_PX:g} px across: a few hits per frame (round 29)"
    p = sm.point(entry)
    if sm.family(entry) == 2 and p["kind"] == "look" and p["look_deg"] >= 75:
        return "the background ends behind the target at 75 degrees (round 30 B): a geometry limit"
    if sm.family(entry) == 1 and p["relative_speed"] == s2s.ORBIT:
        return "the orbit point's range and speed are the TLE's (no closed form recorded)"
    return None


def _ratio(r, method):
    ms = [{k: r[k] for k in sm.MEASUREMENT_KEYS}] + list(r["also"])
    m = next((m for m in ms if m["method"] == method), None)
    return None if m is None else m["ratio"]


def measurements(r):
    """{method: ratio} of a record's envelope measurements: flux closure, and a long enough streak's sweep."""
    out = {"flux_closure": _ratio(r, "flux_closure")}
    ms = [{k: r[k] for k in sm.MEASUREMENT_KEYS}] + list(r["also"])
    streak = next((m for m in ms if m["method"] == "streak_length"), None)
    if streak is not None and streak["expected"] and streak["expected"] >= MIN_SWEEP_PX:
        out["streak_length"] = streak["ratio"]
    return {k: v for k, v in out.items() if v is not None}


def placement(entry):
    return sm.point(entry).get("offset_px", 0.0) if sm.family(entry) == 1 else 0.0


def controls():
    """{DIRSIG spec name: [SatSim control record, ...]} from each control's `s2s.engine_counterpart`."""
    out = {}
    for r in sm.load_results():
        if r["family"] != "satsim":
            continue
        spec = yaml.safe_load((s2s.OUT / f"{r['spec']}.yaml").read_text())
        out.setdefault(spec["descriptor"]["extras"]["s2s.engine_counterpart"], []).append(r)
    return out


def rows_of_records():
    """[(record, attributes, row key or None, exclusion reason or None)] for every DIRSIG record."""
    idx = sm.index()
    out = []
    for r in sm.load_results():
        if r["family"] == "satsim":
            continue
        entry = idx[r["spec"]]
        a = cov.attributes(entry)
        a["motion"] = motion(entry, a)
        a["offset_px"] = placement(entry)
        why = excluded(entry, a)
        key = None if why else (size_bin(a["size_px"]), a["motion"], a["labelled"])
        out.append((r, a, key, why))
    return out


# --- the envelope -------------------------------------------------------------------------------------------------

# (size bin, motion, labelled) -> what the records show removes the row's deficit (the evidence named)
_STREAK = ("the streak shortfall is DIRSIG's adaptive per-pixel sampling: at a fixed 1000 paths per pixel the sweep reads "
           "0.9988 (25 km, 5 ms) and 0.9983 (100 km, 20 ms) (round 39 A, scratch renders, not records); SatSim's controls "
           "of the same streaks read 0.9983, 0.9965 and 0.9942 (round 40)")
_LABEL = ("the label: an unlabelled pixel takes 100 paths, a labelled one 2000 (round 39 B), so the unlabelled plate's "
          "few hits scatter; ")
REMOVED_BY = {
    ("0.3 to 0.5", "fixed", True):
        "nothing in the records: the 0.31 px plate at 50 km reads 0.726 to 0.977 over its four offsets (a few lit "
        "pixels, round 29); no SatSim control at this size",
    ("0.3 to 0.5", "fixed", False): _LABEL + "the labelled plate at 50 km reads 0.817 where this one reads 0.320",
    ("0.5 to 1", "fixed", True):
        "moving off the pixel corner: on the corner the plate reads 0.875 to 0.925 at 45 to 65 degrees off nadir, off it "
        "0.9985 and 1.0188 at 60 (round 39 B); SatSim holds the corner, its offsets and the 60 degree sprite to 6.3e-6 "
        "(round 40), so it is DIRSIG's sampling. The labelled spheres' excess (to 16 % at phase 135) is the hit count on "
        "a lit fraction that shrinks with the phase (round 31); no record removes it",
    ("0.5 to 1", "fixed", False): _LABEL + "the unlabelled plate reads 1.068 at nadir and 0.534 at 60 degrees",
    ("0.5 to 1", "target", True):
        "nothing in the records: one record (round 41), 8 lit pixels over a 6.12 px streak; no SatSim control at this "
        "size; the per-pixel path count that would test it is not a run-spec member (BACKLOG candidate ask, round 40)",
    ("1 to 2", "fixed", True):
        "within 1 % but for offset 0.25 (0.979) at 12.5 km; placement, not isolated",
    ("1 to 2", "fixed", False): _LABEL + "the labelled plate at 12.5 km reads 0.9945 where this one reads 1.068",
    ("1 to 2", "target", True):
        "absent in SatSim (the moving sprite 0.999995 and sphere 0.999994 of the flux, round 40), so DIRSIG's sampling: "
        "the streak's 20 lit pixels take 20 to 100 paths, with gaps (round 39 C); no DIRSIG record removes it",
    ("2 to 6", "fixed", True):
        "one record (round 41) at 1.1 %, beside the platform and target groups' 0.8 % excess at the same size; the "
        "seed-to-seed scatter of the 20 m plate at 100 km is 0.8 % (round 30); not isolated",
    ("2 to 6", "both", True):
        "nothing in the records: the platform and target groups at the same size and exposure hold the flux to 0.8 %; "
        "the both group's flux deficit grows as the plate shrinks (0.0 % at 24.5 px, 1.3 % at 6.12 px, 3.7 % at "
        "3.06 px; rounds 38, 40 and 41); not isolated",
    ("6 to 13", "fixed", True):
        "nothing in the records for the two points beyond 1 %: the 6.12 px plate seen 60 degrees off nadir alone reads "
        "0.9735 on the pixel corner and 0.9767 off it (round 40 B: not placement), the 6.12 px sphere at phase 120 reads "
        "1.0233 (round 39 C); the rest are within 1 %",
    ("6 to 13", "platform", True): _STREAK + "; the platform group reads the target group's ratios at 100 km (round 41)",
    ("6 to 13", "target", True): _STREAK,
    ("6 to 13", "both", True):
        "nothing in the records: the flux 0.987 and the sweep 0.966 (round 40 B), not isolated; " + _STREAK,
    ("over 13", "platform", True): _STREAK,
    ("over 13", "target", True): _STREAK,
    ("over 13", "both", True): _STREAK,
}


def deficits(records):
    """[1 - ratio, ...] over the envelope measurements of `records`."""
    return [1 - v for r, *_ in records for v in measurements(r).values()]


def envelope(rows=None):
    """[{size, motion, labelled, records, flux (min, max deficit), streak (min, max deficit) or None, controls,
    removed_by}] in BINS x MOTIONS x (labelled, unlabelled) order, rows with records only."""
    rows = rows_of_records() if rows is None else rows
    ctl = controls()
    out = []
    for _, _, name in BINS:
        for motion in MOTIONS:
            for labelled in (True, False):
                got = [(r, a) for r, a, key, _ in rows if key == (name, motion, labelled)]
                if not got:
                    continue
                fl = [1 - measurements(r)["flux_closure"] for r, _ in got]
                st = [1 - measurements(r)["streak_length"] for r, _ in got if "streak_length" in measurements(r)]
                cs = [c for r, _ in got for c in ctl.get(r["spec"], [])]
                out.append({"size": name, "motion": motion, "labelled": labelled, "records": len(got),
                            "flux": (min(fl), max(fl)), "streak": (min(st), max(st)) if st else None,
                            "controls": cs, "removed_by": REMOVED_BY.get((name, motion, labelled)),
                            "quiet": max(abs(d) for d in fl + st) <= QUIET})
    return out


def _pct(d):
    return f"{100 * d:+.1f} %"


def _range(pair):
    lo, hi = pair
    return _pct(lo) if abs(hi - lo) < 5e-4 else f"{_pct(lo)} to {_pct(hi)}"


def _control_text(cs):
    if not cs:
        return "none"
    lo = min(1 - c["ratio"] for c in cs)
    hi = max(1 - c["ratio"] for c in cs)
    sts = [1 - _ratio(c, "streak_length") for c in cs if _ratio(c, "streak_length") is not None]
    return (f"{len(cs)}: flux {_range((lo, hi))}" + (f", streak {_range((min(sts), max(sts)))}" if sts else ""))


def document(rows=None):
    rows = rows_of_records() if rows is None else rows
    env = envelope(rows)
    inside = [x for x in rows if x[2] is not None]
    lines = ["# Space-to-space sampling-effect envelope", "",
             "<!-- GENERATED by scripts/s2s_envelope.py from docs/data/s2s_results.jsonl - do not edit; "
             "python scripts/s2s_envelope.py --check compares -->", "",
             f"How far DIRSIG's {len(inside)} space-to-space records of at least {MIN_PX:g} px fall from their closed "
             "forms, by target size in pixels and motion (`docs/data/s2s_results.jsonl`, written by "
             "`scripts/s2s_measure.py`; [the characterization](Space_to_space_characterization.md) is the account, "
             "[the coverage map](s2s_coverage.md) the axes). The deficit of a measurement is 1 - measured / closed "
             "form, in percent; a negative deficit is an excess. Measurements: the flux closure of every record and, "
             f"for a streak at least {MIN_SWEEP_PX:g} px long, the fitted sweep length. A SatSim control (round 40) "
             "images the same geometry without DIRSIG's adaptive per-pixel sampling. Nothing here is tuned. "
             "`python scripts/s2s_envelope.py` writes this document and `--check` refuses a stale one.", "",
             "## The envelope", "",
             f"One row per size, motion and label with records. A row whose every deficit is within {100 * QUIET:g} % "
             "states none to remove.", "",
             "| Size (px) | Motion | Label | Records | Flux deficit | Streak deficit | SatSim controls | What removes it |",
             "|---|---|---|---|---|---|---|---|"]
    for e in env:
        removed = e["removed_by"] or (f"nothing to remove: within {100 * QUIET:g} %" if e["quiet"] else
                                      "NOT STATED")
        lines.append(f"| {e['size']} | {e['motion']} | {'labelled' if e['labelled'] else 'unlabelled'} | "
                     f"{e['records']} | {_range(e['flux'])} | {_range(e['streak']) if e['streak'] else '-'} | "
                     f"{_control_text(e['controls'])} | {removed} |")
    lines += ["", "## Bins and motions", "",
              "- Size: the plate's side or the sphere's diameter over the pixel footprint at the stated range; bins "
              + ", ".join(f"{name} px" for _, _, name in BINS) + " (lower edge included).",
              "- Motion: fixed (no motion), tracked (family II's orbit pair: the platform on its TLE with the line of "
              "sight on the plate, so no streak), platform (family II's `platform` group, the scene moving the other way), "
              "target (family I's moving plates, family II's `target` group), both (family II's `both` group).",
              "- Label: labelled is a target named `::IMPORTANT::` (DIRSIG hypersamples it) or a resolved one; "
              "unlabelled the same 0.5 m plate or 0.25 m sphere without the name.", "",
              "## Outside the envelope", ""]
    out = [(r, a, why) for r, a, key, why in rows if key is None]
    lines += [f"- `{r['spec']}`: {a['size_px']:.3g} px; {why}." for r, a, why in out]
    lines += ["", "## Records", "",
              "Each DIRSIG record in the envelope: size, motion, look and solar zenith (degrees), placement (family I's "
              "offset in pixels; 0 is the pixel corner), label, the flux and streak ratios (measured over the closed "
              "form), and the SatSim control of the same geometry where one exists.", "",
              "| Spec | Size (px) | Motion | Look | Sun | Placement | Label | Flux ratio | Streak ratio | SatSim control |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    ctl = controls()
    for r, a, key, _ in sorted(inside, key=lambda x: (x[1]["size_px"], MOTIONS.index(x[1]["motion"]), x[0]["spec"])):
        ms = measurements(r)
        cs = ctl.get(r["spec"], [])
        ctext = "; ".join(f"`{c['spec']}` flux {c['ratio']:.4f}" + (
            f", streak {_ratio(c, 'streak_length'):.4f}" if _ratio(c, "streak_length") is not None else "")
            for c in cs) or "-"
        streak = f"{ms['streak_length']:.4f}" if "streak_length" in ms else "-"
        lines.append(f"| `{r['spec']}` | {a['size_px']:.2f} | {a['motion']} | {a['look_deg']:g} | "
                     f"{a['solar_zenith_deg']:g} | {a['offset_px']:g} | {'yes' if a['labelled'] else 'no'} | "
                     f"{ms['flux_closure']:.4f} | {streak} | {ctext} |")
    return "\n".join(lines).rstrip("\n") + "\n"


def problems(rows=None):
    env = envelope(rows)
    out = [f"{e['size']} px, {e['motion']}, {'labelled' if e['labelled'] else 'unlabelled'}: a deficit beyond "
           f"{100 * QUIET:g} % and REMOVED_BY states nothing" for e in env if not e["quiet"] and not e["removed_by"]]
    keys = {(e["size"], e["motion"], e["labelled"]) for e in env}
    out += [f"{k}: a REMOVED_BY text for a row with no records" for k in REMOVED_BY if k not in keys]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="compare with the committed document; exit 1 on a problem")
    ap.add_argument("--print", action="store_true", help="print the document instead of writing it")
    a = ap.parse_args(argv)
    rows = rows_of_records()
    text = document(rows)
    found = problems(rows)
    if a.print:
        print(text, end="")
        return 0
    if a.check:
        if not DOC.is_file() or DOC.read_text() != text:
            found.append(f"{DOC.relative_to(ROOT)}: missing or stale (python scripts/s2s_envelope.py rewrites it)")
        print("\n".join(found) if found else f"{len(envelope(rows))} rows over {sum(k is not None for _, _, k, _ in rows)} "
                                             "records: the envelope is current")
        return 1 if found else 0
    if found:
        print("\n".join(found))
        return 1
    DOC.write_text(text)
    print(f"wrote {DOC.relative_to(ROOT)} ({len(envelope(rows))} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
