#!/usr/bin/env python3
"""The numeric tables of `docs/Review_report_since_r27.md`, generated from the committed records.

    python scripts/review_report.py            rewrite the report's generated blocks from the records
    python scripts/review_report.py --check    exit 1 if a generated block differs from what the records give,
                                               or a BACKLOG heading the report names is not in BACKLOG.md
    python scripts/review_report.py --print NAME   print one block (NAME as in its marker)

The report is prose with generated blocks. Each block sits between `<!-- generated: NAME -->` and
`<!-- end generated: NAME -->`; this script writes only what is between the two markers, and `--check` compares
those blocks with a fresh generation, so a number in a block cannot drift from the file it came from. The sources:

- `git` history: the rounds 28 to 36 (commit ranges in `ROUNDS`, the files each added);
- `docs/data/s2s_results.jsonl` with `manifold_run_specs/s2s/index.json` (each spec's range, exposure, look, phase)
  and `manifold_sensors/auror-nir.yaml` (the aperture and focal length behind the cone factor);
- `docs/data/risk_measurements.jsonl` (risks A to E);
- tables of committed documents, taken cell for cell: the SatSim parity results and the integration statement of
  `docs/Space_to_space_characterization.md`, the transfer survey and its comparisons in
  `docs/DIRSIG_transfer_scenes.md`, the foxbat rows of `docs/DIRSIG_layered_comparison.md`;
- the CONOPS: section 10's convergence table (each row's Evidence) and section 10.1's decisions index.

Engine-free and network-free; reads only committed files and `git log`.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "Review_report_since_r27.md"
S2S = ROOT / "docs" / "data" / "s2s_results.jsonl"
S2S_INDEX = ROOT / "manifold_run_specs" / "s2s" / "index.json"
RISK = ROOT / "docs" / "data" / "risk_measurements.jsonl"
SENSOR = ROOT / "manifold_sensors" / "auror-nir.yaml"
S2S_DOC = ROOT / "docs" / "Space_to_space_characterization.md"
TRANSFER_DOC = ROOT / "docs" / "DIRSIG_transfer_scenes.md"
LAYERED_DOC = ROOT / "docs" / "DIRSIG_layered_comparison.md"
CONOPS = ROOT / "docs" / "MANIFOLD_DIRSIG_CONOPS_and_Guide.md"
BACKLOG = ROOT / "BACKLOG.md"

TAG = "review-r27"
TAG_COMMIT = "9ded055"          # the tag's commit, used when the tag is absent locally
# Each round's last commit (its log is in it); a round's range is the previous round's last commit to its own.
ROUNDS = [(28, "796ecd5"), (29, "91ebb4f"), (30, "142b06b"), (31, "a2d992f"), (32, "b2e2c86"),
          (33, "6180991"), (34, "df68496"), (35, "8a59ced"), (36, "3fa0a02")]
NOTES = ".claude_mem/"          # the relay's working notes: not listed (a document does not cite them)
COLLAPSE = 4                    # more files than this added in one folder are listed as the folder and a count

BEGIN = re.compile(r"^<!-- generated: (?P<name>[\w-]+) -->$", re.M)


# ---------------------------------------------------------------- helpers

def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def cells(line):
    """The cells of a markdown table row (a `|` inside backticks is kept)."""
    out, cur, code = [], "", False
    for ch in line.strip()[1:-1]:
        if ch == "`":
            code = not code
        if ch == "|" and not code:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return out


def doc_table(path, after, first_header=None):
    """(header, rows) of the first table after the line starting with `after` (and with that first header cell)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(after))
    for i in range(start, len(lines)):
        if lines[i].startswith("|") and (first_header is None or cells(lines[i])[0] == first_header):
            header = cells(lines[i])
            rows = []
            for l in lines[i + 2:]:
                if not l.startswith("|"):
                    break
                rows.append(cells(l))
            return header, rows
    raise LookupError(f"{path.name}: no table after {after!r}")


def pick(header, rows, columns):
    idx = [header.index(c) for c in columns]
    return [[r[i] for i in idx] for r in rows]


def f(x, digits=5):
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return f"{x:,}" if abs(x) >= 10000 else str(x)
    return f"{x:.{digits}g}"


def rt(x):
    return "—" if x is None else f"{x:.5f}"


def ms(seconds):
    return f"{seconds * 1000:g}"


def km(metres):
    return f"{metres / 1000:g}"


def also(record, method):
    return next((a for a in record["also"] if a["method"] == method), None)


# ---------------------------------------------------------------- section 1: rounds

def rounds_block():
    try:
        git("rev-parse", "--verify", "-q", TAG)
        base = TAG_COMMIT
    except subprocess.CalledProcessError:
        base = TAG_COMMIT
    rows, prev = [], base
    for n, last in ROUNDS:
        commits = git("rev-list", "--reverse", f"{prev}..{last}").split()
        added = [p for p in git("diff", "--diff-filter=A", "--name-only", prev, last).split()
                 if not p.startswith(NOTES)]
        by_dir = defaultdict(list)
        for p in added:
            parts = Path(p).parts
            by_dir["/".join(parts[:3]) if len(parts) > 4 else str(Path(p).parent)].append(p)
        listed = []
        for d in sorted(by_dir):
            files = by_dir[d]
            if len(files) > COLLAPSE:
                listed.append(f"`{d}/` ({len(files)} files)")
            else:
                listed += [f"`{p}`" for p in sorted(files)]
        rows.append([str(n), f"`{commits[0][:7]}`..`{last}`", str(len(commits)), str(len(added)), ", ".join(listed) or "none"])
        prev = last
    return table(["Round", "Commits (first..last)", "Commits", "Files added", "Files added (more than "
                  f"{COLLAPSE} under one folder: the folder and a count)"], rows)


# ---------------------------------------------------------------- section 2: space-to-space

def s2s_records():
    index = {e["name"]: e for e in json.loads(S2S_INDEX.read_text())}
    return [(r, index[r["spec"]]) for r in jsonl(S2S)]


def optics():
    doc = yaml.safe_load(SENSOR.read_text())
    entry = doc["sensor"]["entries"][0] if "sensor" in doc else doc["entries"][0]
    return entry["optics"]["aperture_diameter"], entry["optics"]["focal_length"]


def aperture_block():
    d, fl = optics()
    n = fl / d
    cone = 1 / (1 + 1 / (4 * n * n))
    full = sorted({(e["exposure_s"], r["full_pixel"]) for r, e in s2s_records() if e.get("object_class") == "hyperresolved"
                   and e["range_m"] == 25000.0 and e["look_deg"] == 0 and e["solar_zenith_deg"] == 0})
    header, rows = doc_table(S2S_DOC, "### Results", "Spec")
    zp = next(r for r in rows if r[0] == "`s2s-satsim-sphere-a0-e5ms-zpcone`")
    zcol = header.index("SatSim truth plane (target_pe) / expected")
    out = [["f-number N = focal length / aperture", f"{fl:g} mm / {d:g} mm = {n:.4g}", "`manifold_sensors/auror-nir.yaml`"],
           ["exact-cone factor 1 / (1 + 1 / (4 N²))", f"{cone:.6f}", "computed from the two above"]]
    for exp, value in full:
        out.append([f"`full_pixel` at {ms(exp)} ms (DIRSIG, e⁻ m⁻²)", f"{value:.6e}",
                    "`docs/data/s2s_results.jsonl` (family I, 25 km, nadir)"])
        out.append([f"paraxial value at {ms(exp)} ms (`full_pixel` / factor)", f"{value / cone:.5e}", "computed"])
    out.append(["SatSim truth plane / paraxial expectation with the cone zeropoint (`zpcone`)", zp[zcol],
                "`docs/Space_to_space_characterization.md`, SatSim parity, Results"])
    return table(["Quantity", "Value", "Source"], out)


def flux_block():
    rows = []
    for r, e in s2s_records():
        if r["family"] == 1 and e.get("object_class") == "hyperresolved":
            h, p = also(r, "half_level_count"), also(r, "peak")
            rows.append((e["range_m"], e["exposure_s"], e["look_deg"], e["solar_zenith_deg"], [
                f"`{r['spec']}`", km(e["range_m"]), ms(e["exposure_s"]), f"{e['look_deg']:g}", f"{e['solar_zenith_deg']:g}",
                f(r["measured"], 6), f(r["expected"], 6), rt(r["ratio"]), f(h and h["ratio"], 4), f(p and p["measured"], 6)]))
    rows.sort(key=lambda t: t[:4])
    return table(["Spec", "Range (km)", "Exposure (ms)", "Look (deg)", "Solar zenith (deg)", "Equivalent px",
                  "Expected px", "Ratio", "Half-level count / expected", "Peak / full pixel"], [t[4] for t in rows])


def unresolved_block():
    rows = []
    for r, e in s2s_records():
        cls = e.get("object_class") if r["family"] == 1 else e.get("group")
        if cls not in ("unresolved", "unresolved_plain") or r["family"] == 2:
            continue
        label = "yes" if cls == "unresolved" else "no"
        if r["family"] == 1:
            v = e["relative_speed"]
            motion = "" if not v else (", the orbit form" if isinstance(v, str) else f", {v:g} m/s")
            target, where = "0.5 m plate", (f"{km(e['range_m'])} km, offset {e['offset_px']:g} px, {ms(e['exposure_s'])} ms, "
                                            f"look {e['look_deg']:g}, zenith {e['solar_zenith_deg']:g}{motion}")
            key = (1, cls, e["range_m"], e["offset_px"], e["exposure_s"], e["look_deg"], e["solar_zenith_deg"],
                   v if isinstance(v, float) else 1e9)
        else:
            phase = e["look_deg"] + e["solar_zenith_deg"]
            target, where = "0.25 m sphere", f"25 km, phase {phase:g} (look {e['look_deg']:g}, zenith {e['solar_zenith_deg']:g})"
            key = (3, cls, phase, e["look_deg"], 0, 0, 0, 0)
        rows.append((key, [f"`{r['spec']}`", target, label, where, f(r["measured"], 4), f(r["expected"], 5), rt(r["ratio"])]))
    rows.sort(key=lambda t: t[0])
    return table(["Spec", "Target", "`::IMPORTANT::`", "Point", "Equivalent px", "Expected px", "Ratio"], [t[1] for t in rows])


def blur_block():
    order = {"static": 0, "platform": 1, "target": 2, "both": 3, "orbit": 4}
    rows = []
    for r, e in s2s_records():
        if r["family"] == 2 and e["kind"] in ("blur", "orbit"):
            s = also(r, "streak_length")
            rows.append(((order[e["group"]], e["exposure_s"]), [
                f"`{r['spec']}`", e["group"], ms(e["exposure_s"]), rt(r["ratio"]),
                f(s and s["measured"], 4), f(s and s["expected"], 4), f(s and s["ratio"], 4)]))
    rows.sort(key=lambda t: t[0])
    return table(["Spec", "Group", "Exposure (ms)", "Flux ratio", "Fitted streak (px)", "v·t / footprint (px)",
                  "Fitted / expected"], [t[1] for t in rows])


def look_block():
    rows = []
    for r, e in s2s_records():
        if r["family"] == 2 and e["kind"] == "look":
            b = also(r, "background_period")
            rows.append((e["look_deg"], [f"`{r['spec']}`", f"{e['look_deg']:g}", f(r["measured"], 6), f(r["expected"], 6),
                                         rt(r["ratio"]), f(b and b["measured"], 4), f(b and b["expected"], 4),
                                         f(b and b["ratio"], 4)]))
    rows.sort(key=lambda t: t[0])
    return table(["Spec", "Look (deg)", "Equivalent px", "Expected px (projected area)", "Ratio",
                  "Bar period, measured (px)", "Bar period, expected (px)", "Ratio"], [t[1] for t in rows])


def phase_block():
    rows = []
    for r, e in s2s_records():
        if r["family"] == 3 and e["group"] in ("hyperresolved", "background"):
            bar = also(r, "bar_level")
            phase = e["look_deg"] + e["solar_zenith_deg"]
            rows.append(((e["group"], phase, e["look_deg"]), [
                f"`{r['spec']}`", e["group"], f"{phase:g}", f"{e['look_deg']:g}", f"{e['solar_zenith_deg']:g}",
                f(r["measured"], 6), f(r["expected"], 6), rt(r["ratio"]), rt(bar and bar["ratio"])]))
    rows.sort(key=lambda t: t[0])
    return table(["Spec", "Group", "Phase (deg)", "Look (deg)", "Solar zenith (deg)", "Equivalent px", "Expected px",
                  "Ratio", "Bar level / (0.5 cos θs)"], [t[1] for t in rows])


def satsim_block():
    header, rows = doc_table(S2S_DOC, "### Results", "Spec")
    cols = ["Spec", "Phase (deg)", "Exposure (ms)", "PSF", "Expected (pe)", "SatSim truth plane (target_pe) / expected",
            "SatSim frame / expected", "DIRSIG, same geometry: equivalent px / expected"]
    return table(cols, pick(header, rows, cols))


def exposure_block():
    out = []
    by = {}
    for r, e in s2s_records():
        if r["family"] == 1 and e.get("object_class") == "hyperresolved" and e["range_m"] == 25000.0 \
                and e["look_deg"] == 0 and e["solar_zenith_deg"] == 0 and "window" not in e:
            by[e["exposure_s"]] = r                 # the native exposure axis (round 38's 64 x 64 control is not on it)
    ref = by[0.005]
    for exp in sorted(by):
        r = by[exp]
        scale = (r["measured"] * r["full_pixel"]) / (ref["measured"] * ref["full_pixel"])
        out.append(["DIRSIG", f"`{r['spec']}`", ms(exp), f"{scale:.6f}", f"{exp / 0.005:g}",
                    f"{abs(scale / (exp / 0.005) - 1):.2g}", "`docs/data/s2s_results.jsonl` (image sum, e⁻ m⁻²)"])
    header, rows = doc_table(S2S_DOC, "### Results", "Spec")
    truth = header.index("SatSim truth plane (target_pe) / expected")
    exp_col, pe = header.index("Exposure (ms)"), header.index("Expected (pe)")
    sat = {r[exp_col]: r for r in rows if r[0].startswith("`s2s-satsim-sphere-a0-e") and r[header.index("PSF")] == "POPPY"}
    for exp in sorted(sat, key=float):
        r = sat[exp]
        rel = float(r[truth]) / float(sat["5"][truth])      # the truth plane over the analytic pe, which scales with t
        out.append(["SatSim", r[0], exp, f"{rel * float(exp) / 5:.6f}", f"{float(exp) / 5:g}", f"{abs(rel - 1):.2g}",
                    "`docs/Space_to_space_characterization.md`, SatSim parity, Results (truth plane / expected, "
                    "the expectation proportional to the exposure)"])
    return table(["Engine", "Spec", "Exposure (ms)", "Signal / signal at 5 ms", "Exposure / 5 ms", "Relative residual", "Source"], out)


# ---------------------------------------------------------------- section 2: risks

def risks(letter):
    return [r for r in jsonl(RISK) if r["risk"] == letter]


def risk_a_block():
    rows = [[f"`{r['id']}`", f"`{r['configuration']['job']}`", " x ".join(map(str, r["configuration"]["roi"])),
             f(r["measured"]["home_writes"]), f(r["measured"]["digests_equal"]),
             f(r["measured"]["user_home_documents_dirsig_unchanged"]), f(r["measured"]["fresh_home_files_after"])]
            for r in risks("A")]
    return table(["Id", "Job", "Size", "Writes under any HOME", "Digests equal across the three HOMEs",
                  "User's `Documents/DIRSIG` unchanged", "Files in the fresh HOME afterwards"], rows)


def risk_b_block():
    rows, model = [], None
    for r in risks("B"):
        m = r["measured"]
        if r["id"].endswith("limit-model"):
            model = r
            continue
        peaks = [j["peak_rss_kib"] for j in m["jobs"]]
        rows.append([f"`{r['id']}`", " x ".join(map(str, r["configuration"]["roi"])), str(m["n"]), f(m["batch_wall_s"]),
                     f(m["mean_job_wall_s"]), f"{min(peaks):,} to {max(peaks):,}", f(m["max_sum_dirsig5_rss_kib"]),
                     f(m["throughput_jobs_per_hour"], 5), f(m["digests_equal_single"]), str(m["failed_jobs"])])
    out = table(["Id", "Size", "Jobs", "Batch wall (s)", "Mean job wall (s)", "Peak RSS per job (KiB)",
                 "Summed dirsig5 RSS, max (KiB)", "Jobs per hour", "Digests equal the single job", "Failed"], rows)
    if model:
        m = model["measured"]
        out += "\n\n" + table(["Limit model", "Cores", "Hardware threads", "RAM (GiB)", "Peak RSS (GiB)", "Limit",
                               "Throughput against one job (n = 1, 2, 4, 8)", "Dual Xeon Gold 6230, 256 GB"],
                              [[f"`{model['id']}`", str(m["cores"]), str(m["hardware_threads"]), f(m["ram_gib"]),
                                f(m["peak_rss_gib"], 4), str(m["limit"]),
                                ", ".join(f(v, 4) for v in m["throughput_ratio_vs_n1"].values()),
                                str(m["dual_6230_256gb_limit"])]])
    return out


def risk_c_block():
    rows = []
    for r in risks("C"):
        m = r["measured"]
        disk = m["on_disk"]
        img = next(k for k in disk if k.endswith(".img") and not k.startswith("truth"))
        rows.append([f"`{r['id']}`", f"{m['fraction']:.3f}", f(m["cancel_after_s"]), f(m["reference_s"]), m["state"],
                     m["verdict"], f(m["cancel_return_s"]), ", ".join(f"`{x}`" for x in m["listed"]),
                     f"{disk[img]['rows_on_disk']} of {disk[img]['rows_total']}", str(disk[img]["header_lines"]),
                     f(disk[img]["prefix_equal_full"])])
    return table(["Id", "Cancelled at (fraction)", "After (s)", "Full run (s)", "State", "Verdict", "Cancel returned (s)",
                  "Artifacts listed", "Image rows on disk", "Header line count", "Rows equal the full run's"], rows)


def risk_d_block():
    rows = []
    for r in risks("D"):
        m = r["measured"]
        eq = m["equal_single"]
        rev = m.get("reversed")
        if rev is None:
            reversed_cell = "—"
        elif rev.get("rc") == 0:
            reversed_cell = f"rc 0, first output equals its single: {f(rev['first_equals_its_single'])}"
        else:
            first = rev.get("first_session", {})
            reversed_cell = f"rc {rev['rc']} ({' '.join(e.strip() for e in rev['errors'])})"
            if first:
                reversed_cell += f"; without a limit: {first['outcome']}, anon RSS {first['anon_rss_kib']:,} KiB"
        rows.append([f"`{r['id']}`", " x ".join(map(str, r["configuration"]["roi"])), str(m["captures_logged"]),
                     f(m["dirsig_refused"]), f"{sum(eq.values())} of {len(eq)}", m["sdk_check"],
                     m.get("state", "—"), reversed_cell])
    return table(["Id", "Size", "Captures logged", "DIRSIG refused", "Captures equal to their one-capture run",
                  "SDK check", "Run state", "Reversed trigger order"], rows)


def risk_e_block():
    rows = [[f"`{r['id']}`", r["measured"]["class"], f"{r['measured']['pixels_differing']} of {r['measured']['pixels_lit']:,}",
             f(r["measured"]["max_rel"], 3), f(r["measured"]["image_sum_rel_diff"], 3),
             f(r["measured"]["lightcurve_last_rel_diff"], 3),
             ", ".join(f"`{o}`" for o in r["measured"]["outputs_differing"]) or "none"]
            for r in risks("E")]
    return table(["Pair (t1, t2, t4: threads; td: default 8; a to c: repeats)", "Class", "Lit pixels differing",
                  "Max relative difference", "Frame sum, relative", "Light curve (last), relative", "Outputs differing"],
                 rows)


# ---------------------------------------------------------------- section 2: transfer scenes and foxbat

def transfer_block():
    header, rows = doc_table(TRANSFER_DOC, "**The transfer folder", "Scene")
    survey = table(["Scene", "Simulation files", "Also in the install"],
                   pick(header, rows, ["Scene", "Simulation files", "Also in the install"]))
    header, rows = doc_table(TRANSFER_DOC, "## Layered against pass-through", "Scene (simulation)")
    return survey + "\n\n" + table(["Scene (simulation)", "Result"], pick(header, rows, ["Scene (simulation)", "Result"]))


def foxbat_block():
    header, rows = doc_table(LAYERED_DOC, "## Results", "Demo")
    keep = [r for r in rows if r[0].startswith("foxbat")]
    cols = ["Demo", "Image", "Against", "Max abs difference", "Pixels differing", "Identical"]
    return table(cols, pick(header, keep, cols))


# ---------------------------------------------------------------- sections 4 and 5: decisions

def conops_tables():
    text = CONOPS.read_text(encoding="utf-8")
    lines = text.splitlines()
    evidence, index, outside = {}, [], []
    for i, l in enumerate(lines):
        if l.startswith("| C-"):
            c = cells(l)
            if len(c) == 7:                           # the convergence table: ID, Item, position, Build, Agreement, Evidence, Outcome
                evidence[c[0]] = c[5]
    h, rows = doc_table(CONOPS, "### 10.1 Decisions needed", "Ask")
    index = [dict(zip(h, r)) for r in rows]
    h, rows = doc_table(CONOPS, "Decisions recorded outside the table", "Decision")
    outside = [dict(zip(h, r)) for r in rows]
    return evidence, index, outside


def manifold_block():
    evidence, index, _ = conops_tables()
    rows = [[r["Ask"], r["Item"], r["Blocks 0.1"], r["State"], evidence.get(r["Ask"], "—")]
            for r in index if r["Owner"] == "MANIFOLD"]
    return table(["C-n", "Ask", "Blocks 0.1", "State and what is measured (section 10.1)", "Evidence (section 10 row)"], rows)


def maintainer_block():
    _, index, outside = conops_tables()
    held = table(["C-n", "Ask", "Blocks 0.1", "State"],
                 [[r["Ask"], r["Item"], r["Blocks 0.1"], r["State"]] for r in index if r["Owner"].startswith("Kevin")])
    rest = table(["Decision", "Where it is recorded", "Owner", "Blocks 0.1", "What it changes, and what is measured"],
                 [[r["Decision"], r["Where it is recorded"], r["Owner"], r["Blocks 0.1"], r["What it changes"]] for r in outside])
    return held + "\n\n" + rest


BLOCKS = {
    "rounds": rounds_block,
    "aperture": aperture_block,
    "flux": flux_block,
    "unresolved": unresolved_block,
    "blur": blur_block,
    "look": look_block,
    "phase": phase_block,
    "satsim": satsim_block,
    "exposure": exposure_block,
    "risk-a": risk_a_block,
    "risk-b": risk_b_block,
    "risk-c": risk_c_block,
    "risk-d": risk_d_block,
    "risk-e": risk_e_block,
    "transfer": transfer_block,
    "foxbat": foxbat_block,
    "manifold": manifold_block,
    "maintainer": maintainer_block,
}


# ---------------------------------------------------------------- the report

def blocks_in(text):
    """{name: (start, end)} of each generated block's body (between the two marker lines)."""
    out = {}
    for m in BEGIN.finditer(text):
        name = m["name"]
        end = text.index(f"<!-- end generated: {name} -->", m.end())
        out[name] = (m.end() + 1, end)
    return out


def regenerate(text):
    spans = blocks_in(text)
    for name, (a, b) in sorted(spans.items(), key=lambda kv: -kv[1][0]):
        if name not in BLOCKS:
            raise KeyError(f"unknown generated block {name!r}")
        text = text[:a] + BLOCKS[name]() + "\n" + text[b:]
    return text


def backlog_headings_named(text):
    """BACKLOG items the report names as `BACKLOG.md` "Heading"."""
    return re.findall(r'`BACKLOG\.md` "([^"]+)"', text)


def check(path=REPORT):
    problems = []
    text = path.read_text(encoding="utf-8")
    spans = blocks_in(text)
    missing = sorted(set(BLOCKS) - set(spans))
    problems += [f"{path.name}: no generated block {n!r}" for n in missing]
    fresh = regenerate(text)
    if fresh != text:
        new = blocks_in(fresh)
        for name in spans:
            if text[slice(*spans[name])] != fresh[slice(*new[name])]:
                problems.append(f"{path.name}: block {name!r} differs from what the records give "
                                f"(run `python scripts/review_report.py`)")
    backlog = BACKLOG.read_text(encoding="utf-8")
    heads = {l.lstrip("#").strip() for l in backlog.splitlines() if l.startswith("#")}
    for h in backlog_headings_named(text):
        if not any(x == h or x.startswith(h) for x in heads):
            problems.append(f"{path.name}: names BACKLOG item {h!r}, which BACKLOG.md has no heading for")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if the report's generated blocks are stale")
    ap.add_argument("--print", dest="name", choices=sorted(BLOCKS), help="print one generated block")
    a = ap.parse_args(argv)
    if a.name:
        print(BLOCKS[a.name]())
        return 0
    if a.check:
        problems = check()
        for p in problems:
            print(p)
        n = len(blocks_in(REPORT.read_text(encoding="utf-8")))
        print(f"review_report: {n} generated blocks, {len(problems)} problem(s)")
        return 1 if problems else 0
    REPORT.write_text(regenerate(REPORT.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"review_report: wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
