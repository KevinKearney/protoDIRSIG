#!/usr/bin/env python3
"""Summarize a demo sweep's results into the sweep report and tag demos in the coverage table.

    python scripts/summarize_sweep.py --results <work>/sweep/results.jsonl [--report docs/DIRSIG_demo_sweep.md]
                                      [--coverage docs/DIRSIG_demo_coverage.md]

Reads the results file `scripts/sweep_demos.py` writes and the verdicts of the coverage table, and rewrites two
generated parts, each between its own markers, keeping every other line: the analysis in the sweep report (outcome
counts; failures grouped by first error line with the file, database, variable or tool each names; cost; determinism;
thermal and cache; the layered-comparison candidates, the survey's `ready` and `near` demos that now have a pass-through reference,
ranked by its cost), and the table of the "Tagged demos" section of the coverage table (the section is hand-written and
kept when `scripts/survey_demos.py` regenerates the table; the tags are `TAGS`). Only names, sizes, measurements and
DIRSIG error lines are written, with paths reduced to file names.
"""
import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "DIRSIG_demo_sweep.md"
COVERAGE = ROOT / "docs" / "DIRSIG_demo_coverage.md"
BEGIN = "<!-- summarize_sweep: analysis, generated between these markers by scripts/summarize_sweep.py; edit outside them -->"
END = "<!-- summarize_sweep: end -->"
TAG_BEGIN = "<!-- summarize_sweep: tagged demos, generated between these markers by scripts/summarize_sweep.py -->"
TAG_END = "<!-- summarize_sweep: tagged demos end -->"
TAGS = {
    "SDA": ["MoonSat1", "MoonSat2", "Ssa1", "Ssa2", "Ssa3", "EarthShine1", "SpaceRendezVous1", "LightCurve1",
            "StkImport1"],
    "URSO": ["Sources1", "Indoors1", "Sources3", "Sources4", "Sources5", "IESSources1", "Sources6", "SubPixelObject1",
             "SubPixelObject2"],
}
TOP_GROUPS = 15
TOP_COST = 10
GENERIC = re.compile(r"^\[error\]\s*Error!\s*$", re.I)
# what a DIRSIG error line names: (kind, pattern with one group)
NAMED = [
    ("database", re.compile(r"Could not open NewAtmosphere HDF: \"([^\"]+)\"")),
    ("file", re.compile(r"unable to open file '([^']+)'")),
    ("file", re.compile(r"Path \"([^\"]+)\" does not exist")),
    ("file", re.compile(r"cannot make canonical path: [^\[]*\[([^\]]+)\]")),
    ("environment variable", re.compile(r"environment variable: '([^']+)'")),
    ("variable", re.compile(r"Variable = (\S+)")),
]
PATH = re.compile(r"(?<![\w.])/(?:[^\s\"'/]+/)+[^\s\"']+")      # an absolute path of two or more parts


def read_results(path):
    out = []
    for ln in Path(path).read_text().splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def demos_of(records):
    rows = {}
    for r in records:
        if r.get("type") == "demo":
            rows[r["demo"]] = r
    return rows


def shorten(line):
    """A log line with every absolute path reduced to its file name."""
    return PATH.sub(lambda m: PurePosixPath(m.group(0)).name, line).strip() if line else line


def cause(log_tail, first_line=None):
    """`(message, named)` from an attempt's log tail: the DIRSIG message (the first non-empty line after a generic
    "[error] Error!"; when the tail does not reach back to it, the line before the first "Thrown by"; else the first
    `[error]` line), and the `kind name` the error names (searched in the first error line and the tail), if any."""
    lines = [ln.rstrip() for ln in log_tail or []]
    message = None
    for i, ln in enumerate(lines):  # noqa: B007
        if GENERIC.match(ln.strip()):
            message = next((x.strip() for x in lines[i + 1:] if x.strip()), None)
            if message and " " not in message:              # a bare context word ("Sensor"): the cause precedes it
                message = next((x.strip() for x in reversed(lines[:i]) if x.strip()), message)
            break
    if message is None:
        thrown = next((i for i, x in enumerate(lines) if x.strip().startswith("Thrown by")), None)
        if thrown:
            message = next((x.strip() for x in reversed(lines[:thrown]) if x.strip()), None)
            if message and " " not in shorten(message):     # a path list: the cause is outside the tail
                message = None
    if message is None:
        message = next((x.strip() for x in lines if x.strip().startswith("[error]") and not GENERIC.match(x.strip())),
                       None)
    named = None
    for ln in ([first_line] if first_line else []) + lines:
        for kind, rx in NAMED:
            m = rx.search(ln)
            if m:
                named = f"{kind} {PurePosixPath(m.group(1)).name}"
                break
        if named:
            break
    return shorten(message), named


def percentile(values, q):
    """Nearest-rank percentile of a non-empty list."""
    s = sorted(values)
    return s[max(0, math.ceil(q / 100 * len(s)) - 1)]


def coverage_verdicts(path):
    """`{demo: (verdict, missing)}` from the coverage table's "All demos" rows."""
    out = {}
    if not Path(path).is_file():
        return out
    for ln in Path(path).read_text().splitlines():
        m = re.match(r"^\| (\S+) \| `(ready|near|far|unparsed)` \|(.*)\|$", ln)
        if m:
            cells = [c.strip() for c in m.group(3).split("|")]
            out[m.group(1)] = (m.group(2), cells[-1] if cells else "-")
    return out


def _mb(n):
    return f"{n / 1e6:.2f}" if isinstance(n, (int, float)) else "-"


def _cell(text):
    return str(text).replace("|", "\\|") if text not in (None, "") else "-"


def final_attempt(row):
    atts = row.get("attempts") or []
    return atts[-1] if atts else {}


def out_bytes(att):
    return sum(o["size"] for o in att.get("outputs", []))


def nondeterminism_kind(differing):
    names = differing or []
    if names and all("truth" in n for n in names):
        return "truth images only"
    if names and all(n.endswith(".bin") for n in names):
        return "lidar .bin only"
    if names and all(n.endswith(".txt") for n in names):
        return "data recorder text only"
    return "radiance images (with or without others)"


def failure_groups(rows):
    """[(first error line, [(demo, simulation, message, named)])], largest first, over every failed or timed-out
    first attempt."""
    groups = {}
    for name, row in sorted(rows.items()):
        for a in row.get("attempts", []):
            if a.get("outcome") in ("failed", "timeout"):
                key = shorten(a.get("first_error_line")) or f"(no matching line; {a['outcome']})"
                message, named = cause(a.get("log_tail"), a.get("first_error_line"))
                if a["outcome"] == "timeout":
                    message = f"timed out after {a.get('wall_s')} s (capped timeout {a.get('timeout_s')} s), cancelled"
                groups.setdefault(key, []).append((name, a["simulation"], message, named))
    return sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))


def render(records, verdicts):
    rows = demos_of(records)
    attempts = [r for r in records if r.get("type") == "attempt"]
    stop = [r for r in records if r.get("type") == "stop"]
    counts = {}
    for r in rows.values():
        counts[r.get("outcome", "-")] = counts.get(r.get("outcome", "-"), 0) + 1
    rendered = {n: final_attempt(r) for n, r in rows.items() if r.get("outcome") == "rendered"}
    lines = [BEGIN, "", "## Analysis", "", "### Outcomes", "",
             f"{len(rows)} demos, {len(attempts)} attempts ({sum(1 for a in attempts if a.get('repeat'))} of them "
             f"repeats). The sweep ended: {stop[-1]['reason'] if stop else 'not recorded'}.", "",
             "| Outcome | Demos |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    groups = failure_groups(rows)
    lines += ["", "### Failures by first error line", "",
              f"Every failed or timed-out attempt, grouped by the first `worker.log` line matching the sweep's error "
              f"pattern ({len(groups)} groups; the {TOP_GROUPS} largest shown). DIRSIG usually prints a bare "
              "`[error] Error!` first, so each attempt also shows the message after it and the file, database, variable "
              "or tool the error names.", "",
              "| First error line | Attempts | Demo (simulation): DIRSIG message | Names |", "|---|---|---|---|"]
    for key, members in groups[:TOP_GROUPS]:
        detail = "; ".join(f"{d} ({s}): {_cell(m)}" for d, s, m, _ in members)
        named = ", ".join(sorted({n for *_, n in members if n})) or "-"
        lines.append(f"| {_cell(key)} | {len(members)} | {detail} | {_cell(named)} |")

    walls = [a["wall_s"] for a in rendered.values()]
    sizes = [out_bytes(a) for a in rendered.values()]
    lines += ["", "### Cost", ""]
    if walls:
        lines += [f"Wall time of the {len(walls)} rendered demos (the rendering attempt, first run): median "
                  f"{statistics.median(walls):.1f} s, 90th percentile {percentile(walls, 90):.1f} s, maximum "
                  f"{max(walls):.1f} s; total {sum(walls) / 3600:.2f} h. Wall time of every attempt, repeats included: "
                  f"{sum(a.get('wall_s', 0) for a in attempts) / 3600:.2f} h.", "",
                  f"The {TOP_COST} most expensive rendered demos:", "",
                  "| Demo | Simulation | Wall time (s) | Outputs | Output (MB) |", "|---|---|---|---|---|"]
        for n, a in sorted(rendered.items(), key=lambda kv: -kv[1]["wall_s"])[:TOP_COST]:
            lines.append(f"| {n} | {a['simulation']} | {a['wall_s']} | {len(a.get('outputs', []))} | "
                         f"{_mb(out_bytes(a))} |")
        bins = [("under 1 MB", 0, 1e6), ("1 to 10 MB", 1e6, 1e7), ("10 to 100 MB", 1e7, 1e8),
                ("100 MB to 1 GB", 1e8, 1e9), ("1 GB or more", 1e9, float("inf"))]
        lines += ["", f"Output size per rendered demo: median {_mb(statistics.median(sizes))} MB, maximum "
                  f"{_mb(max(sizes))} MB.", "", "| Output size | Demos |", "|---|---|"]
        lines += [f"| {label} | {sum(1 for s in sizes if lo <= s < hi)} |" for label, lo, hi in bins]

    det = {n: a.get("deterministic") for n, a in rendered.items()}
    yes = sorted(n for n, d in det.items() if d == "yes")
    no = sorted(n for n, d in det.items() if d == "no")
    other = sorted(f"{n} ({d})" for n, d in det.items() if d not in ("yes", "no"))
    lines += ["", "### Determinism", "",
              f"Every demo that rendered in under 300 s was rendered again in a fresh work root, with DIRSIG's default "
              f"seed (no `--random_seed`). Identical outputs: {len(yes)} of {len(yes) + len(no)} repeated demos"
              + (f" ({100 * len(yes) / (len(yes) + len(no)):.0f} percent)" if yes or no else "") + "."
              + (f" Not repeated: {', '.join(other)}." if other else ""), ""]
    if no:
        kinds = {}
        for n in no:
            kinds.setdefault(nondeterminism_kind(rendered[n].get("differing")), []).append(n)
        lines += ["| Outputs that differ | Demos |", "|---|---|"]
        lines += [f"| {k} | {', '.join(v)} |" for k, v in sorted(kinds.items(), key=lambda kv: (-len(kv[1]), kv[0]))]

    first = [a for a in attempts if not a.get("repeat")]
    temps = [a["max_cpu_temp_c"] for a in attempts if a.get("max_cpu_temp_c") is not None]
    hot = sorted({a["demo"] for a in attempts if a.get("throttle_suspect")})
    cached = [a for a in first if (a.get("cache") or {}).get("files")]
    lines += ["", "### Thermal and cache", ""]
    if temps:
        lines += [f"Maximum CPU temperature per attempt (the maximum over the host's thermal zones): median "
                  f"{statistics.median(temps):.1f} C, highest {max(temps):.1f} C; {sum(1 for t in temps if t >= 90)} of "
                  f"{len(temps)} attempts reached 90 C and are flagged `throttle_suspect`, across {len(hot)} demos: "
                  f"{', '.join(hot) or 'none'}.", ""]
    else:
        lines += ["No thermal sensor could be read during the sweep (`max_cpu_temp_c` is null).", ""]
    lines += [f"Cache: every attempt ran with a per-run `HOME`, so DIRSIG's material caches started cold and the user's "
              f"cache was not an input. {len(cached)} first attempts wrote cache files into their per-run home "
              f"({sum(a['cache']['files'] for a in cached)} files, {_mb(sum(a['cache']['bytes'] for a in cached))} MB): "
              f"{', '.join(sorted({a['demo'] for a in cached})) or 'none'}. A cold-versus-warm comparison does not "
              "apply."]

    near = sorted((n for n, (v, _) in verdicts.items() if v == "near"))
    ready = sorted((n for n, (v, _) in verdicts.items() if v == "ready"))
    cands = sorted(((rendered[n]["wall_s"], n) for n in ready + near if n in rendered))
    missing_ref = sorted(n for n in near if n not in rendered)
    ready_no_ref = sorted(n for n in ready if n not in rendered)
    lines += ["", "### Layered-comparison candidates", "",
              f"The survey marks {len(near)} demos `near` (one loader feature away) and {len(ready)} `ready` (none "
              f"missing). {len(cands)} of them now have a pass-through reference; ranked by its cost, they are the "
              "candidates for a layered re-expression and comparison (a `ready` demo's missing feature is \"none\").", "",
              "| Rank | Demo | Simulation | Reference wall time (s) | Deterministic | Missing feature (survey) |",
              "|---|---|---|---|---|---|"]
    for i, (w, n) in enumerate(cands, 1):
        a = rendered[n]
        lines.append(f"| {i} | {n} | {a['simulation']} | {w} | {a.get('deterministic', '-')} | "
                     f"{'none' if verdicts[n][0] == 'ready' else _cell(verdicts[n][1])} |")
    if ready_no_ref:
        lines += ["", "`ready` demos without a reference: "
                  + ", ".join(f"{n} ({rows[n].get('outcome', 'not in the sweep') if n in rows else 'not in the sweep'})"
                              for n in ready_no_ref) + "."]
    if missing_ref:
        lines += ["", "`near` demos without a reference: "
                  + ", ".join(f"{n} ({rows[n].get('outcome', 'not in the sweep') if n in rows else 'not in the sweep'})"
                              for n in missing_ref) + "."]
    lines += ["", END]
    return "\n".join(lines)


def render_tags(records, verdicts, installed):
    rows = demos_of(records)
    lines = [TAG_BEGIN, "", "| Tag | Demo | Sweep outcome | Simulation | Wall time (s) | Deterministic | Survey verdict | "
             "Missing features (survey) |", "|---|---|---|---|---|---|---|---|"]
    for tag, names in TAGS.items():
        for n in names:
            if n not in installed and n not in rows and n not in verdicts:
                lines.append(f"| {tag} | {n} | absent from the installation | - | - | - | - | - |")
                continue
            r = rows.get(n, {})
            a = final_attempt(r)
            v, missing = verdicts.get(n, ("-", "-"))
            lines.append(f"| {tag} | {n} | {r.get('outcome', 'not in the sweep')} | {a.get('simulation', '-')} | "
                         f"{a.get('wall_s', '-')} | {a.get('deterministic', '-') if a else '-'} | "
                         f"{'`' + v + '`' if v != '-' else '-'} | {_cell(missing)} |")
    lines += ["", TAG_END]
    return "\n".join(lines)


def replace_between(text, begin, end, body, append_heading=None):
    """`text` with the part from `begin` to `end` replaced by `body` (which carries both markers); when the markers
    are absent, `body` is appended (after `append_heading` if given)."""
    if begin in text and end in text:
        head, rest = text.split(begin, 1)
        _, tail = rest.split(end, 1)
        return head + body + tail
    return text.rstrip("\n") + "\n\n" + (append_heading + "\n\n" if append_heading else "") + body + "\n"


TAG_SECTION = ("## Tagged demos\n\nHand-maintained and kept when the table is regenerated: the demos the user named as "
               "of interest, by tag (SDA: space domain awareness; URSO: relevance to the URSO work), with each one's "
               "pass-through sweep outcome and cost (`docs/DIRSIG_demo_sweep.md`) and its survey verdict. The table "
               "between the markers is rewritten by `scripts/summarize_sweep.py`.")


def installed_names(dirsig_home):
    zips = Path(dirsig_home) / "demos" / "zips"
    names = {p.stem for p in zips.glob("*.zip")} if zips.is_dir() else set()
    return names | ({p.name for p in zips.iterdir() if p.is_dir()} if zips.is_dir() else set())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", required=True, help="the sweep's results.jsonl")
    ap.add_argument("--report", default=str(REPORT))
    ap.add_argument("--coverage", default=str(COVERAGE))
    ap.add_argument("--dirsig-home", default=str(ROOT / "external" / "dirsig"))
    a = ap.parse_args(argv)
    records = read_results(a.results)
    verdicts = coverage_verdicts(a.coverage)
    report = Path(a.report)
    text = report.read_text() if report.is_file() else "# DIRSIG demo sweep\n"
    report.write_text(replace_between(text, BEGIN, END, render(records, verdicts)))
    cov = Path(a.coverage)
    if cov.is_file():
        ctext = cov.read_text()
        cov.write_text(replace_between(ctext, TAG_BEGIN, TAG_END, render_tags(records, verdicts,
                                                                           installed_names(a.dirsig_home)),
                                       append_heading=None if TAG_BEGIN in ctext else TAG_SECTION))
    print(f"updated {report} and {cov}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
