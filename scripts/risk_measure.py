#!/usr/bin/env python3
"""Known-risk measurements: one results file, `docs/data/risk_measurements.jsonl`, and its check.

    python scripts/risk_measure.py --check            the results file is well formed and every derived number
                                                      recomputes from the record's own values; exit 1 if not
    python scripts/risk_measure.py add FILE [...]     merge records (JSON lines) into the results file: a record
                                                      replaces the one with the same risk and id; each is checked first
    python scripts/risk_measure.py list               one line per record

The measurements themselves are made by scratch scripts outside the repository (renders, cancels and HOME experiments
must not change how the SDK launches a job); this script only keeps and checks what they found. The risks (round 33):

- A: what a layered DIRSIG job reads from and writes to the user's HOME, and whether a HOME changes the product.
- B: concurrent one-thread jobs: peak memory, wall time and throughput against the number of jobs, and the
  concurrency limit min(cores, RAM / peak RSS per job).
- C: cancelling a DIRSIG job through the adapter at about 25, 50 and 75 percent of its run.
- D: more than one capture in one task window (C-43), with the SDK's check bypassed.
- E: differences between repeat renders, and between thread counts, at DIRSIG's default thread count.
- F (round 44, D-2): whether a thermal render depends on the instant only or also on the UTC offset in which the
  `.tasks` reference time is written: one instant written at several offsets, the first offset rendered twice.
- G (round 45, D-2): whether the render follows the written clock digits or the instant: at a pinned thread count, a
  repeat pair, pairs with the same digits at different offsets and pairs with the same instant at different offsets.

A record (one JSON object per line, sorted by risk, then id), in this key order:
`risk` (A to G), `id` (unique within the risk), `configuration` (what was run: job, size, threads, seed, HOME and so
on), `method` (how it was measured, one sentence or more), `measured` (the quantities; the members each risk requires are
in `REQUIRED`), `tools` (`dirsig`, the DIRSIG version, and whatever else the method used, for example `dirfm` or
`strace`), `date` (YYYY-MM-DD) and `source` (where the raw data was, home-relative, outside the repository).

A risk B record whose id is `limit-model` or ends in `-limit-model` (one per host, `scripts/bigger_host_run.py`) is the limit model.

Derived numbers are checked against the record's own values, the way `scripts/s2s_measure.py --check` recomputes its
expected values: A's `digests_equal` against its `products`, B's job count, throughput and limit, C's cancel fraction,
D's per-capture equality list, E's differing fraction, F's repeatability and result (every written time
the stated instant; `repeatable` from the repeat pair's digests; `result` from the compared products' digests), G's
pairs and result (each digits-held pair the same clock digits at two offsets, each instant-held pair the same instant at
two offsets; `repeatable` from the repeat pair's digests; `result` from the pairs' digests: `written digits` when every
digits-held pair is equal and every instant-held pair differs, `instant` for the reverse, otherwise `not isolated`).
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "docs" / "data" / "risk_measurements.jsonl"
RECORD_KEYS = ("risk", "id", "configuration", "method", "measured", "tools", "date", "source")
RISKS = {"A": "layered jobs and the user's HOME", "B": "concurrency and memory", "C": "DIRSIG cancel",
         "D": "one capture per task window (C-43)", "E": "default-thread determinism",
         "F": "the .tasks reference time's UTC offset (D-2)",
         "G": "the .tasks reference time: written digits or instant (D-2)"}
NUMBER = (int, float)
# The members each risk's `measured` must hold, with their types; a record may hold more.
REQUIRED = {
    "A": {"home_paths": list, "home_writes": int, "products": dict, "digests_equal": bool},
    "B": {"n": int, "jobs": list, "batch_wall_s": NUMBER, "throughput_jobs_per_hour": NUMBER,
          "digests_equal_single": bool},
    "B-model": {"cores": int, "hardware_threads": int, "ram_gib": NUMBER, "peak_rss_gib": NUMBER, "limit": int},
    "C": {"cancel_after_s": NUMBER, "reference_s": NUMBER, "fraction": NUMBER, "verdict": str, "listed": list,
          "on_disk": dict, "usable": bool},
    "D": {"captures_logged": int, "products": list, "equal_single": dict, "dirsig_refused": bool},
    "E": {"pair": str, "samples": int, "differing": int, "fraction_differing": NUMBER, "max_abs": NUMBER,
          "max_rel": NUMBER},
    "F": {"instant": str, "written": dict, "repeat": list, "compared": list, "products": dict, "repeatable": bool,
          "result": str},
    "G": {"written": dict, "threads": int, "repeat": list, "digits_held": list, "instant_held": list, "compared": list,
          "products": dict, "repeatable": bool, "result": str},
}
F_RESULTS = ("instant only", "offset dependent", "not decidable")
G_RESULTS = ("written digits", "instant", "not isolated", "not decidable")


def load_results(path=RESULTS):
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_results(records, path=RESULTS):
    path.parent.mkdir(parents=True, exist_ok=True)
    records = sorted(records, key=lambda r: (r["risk"], r["id"]))
    path.write_text("".join(json.dumps(r, sort_keys=False) + "\n" for r in records))


def _kind(r):
    return "B-model" if r["risk"] == "B" and (r["id"] == "limit-model" or r["id"].endswith("-limit-model")) \
        else r["risk"]


def _close(a, b):
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


def record_problems(r):
    """Problems of one record (no file context)."""
    if not isinstance(r, dict) or tuple(r) != RECORD_KEYS:
        return [f"keys are not {RECORD_KEYS}"]
    p = []
    if r["risk"] not in RISKS:
        return [f"risk {r['risk']!r} is not one of {sorted(RISKS)}"]
    if not (isinstance(r["id"], str) and re.fullmatch(r"[a-z0-9][a-z0-9._-]*", r["id"])):
        p.append(f"id {r['id']!r} is not a lower-case slug")
    for key in ("configuration", "measured", "tools"):
        if not (isinstance(r[key], dict) and r[key]):
            p.append(f"{key} is not a non-empty object")
    if not (isinstance(r["method"], str) and r["method"].strip()):
        p.append("method is empty")
    if not (isinstance(r["source"], str) and r["source"].strip()):
        p.append("source is empty")
    if not (isinstance(r["date"], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date"])):
        p.append(f"date {r['date']!r} is not YYYY-MM-DD")
    if p:
        return p
    if not (isinstance(r["tools"].get("dirsig"), str) and r["tools"]["dirsig"]):
        p.append("tools.dirsig (the DIRSIG version) is missing")
    m = r["measured"]
    for key, typ in REQUIRED[_kind(r)].items():
        if key not in m:
            p.append(f"measured.{key} is missing")
        elif isinstance(m[key], bool) and typ is not bool or not isinstance(m[key], typ):
            p.append(f"measured.{key} is not {typ}")
    if p:
        return p
    return p + derived_problems(_kind(r), m)


def derived_problems(kind, m):
    """Derived numbers that do not recompute from the record's own values."""
    p = []
    if kind == "A":
        digests = [json.dumps(v, sort_keys=True) for v in m["products"].values()]
        if len(digests) < 2:
            p.append("products: fewer than two HOME variants")
        elif m["digests_equal"] != (len(set(digests)) == 1):
            p.append("digests_equal does not follow from products")
        if m["home_writes"] < 0:
            p.append("home_writes is negative")
    elif kind == "B":
        if len(m["jobs"]) != m["n"]:
            p.append(f"jobs lists {len(m['jobs'])} jobs, n is {m['n']}")
        walls = [j.get("wall_s") for j in m["jobs"]]
        if not all(isinstance(w, NUMBER) and w > 0 for w in walls) or \
                not all(isinstance(j.get("peak_rss_kib"), int) and j["peak_rss_kib"] > 0 for j in m["jobs"]):
            p.append("a job lacks a positive wall_s or peak_rss_kib")
        elif m["batch_wall_s"] + 1e-9 < max(walls):
            p.append("batch_wall_s is shorter than a job's wall time")
        elif not _close(m["throughput_jobs_per_hour"], m["n"] * 3600.0 / m["batch_wall_s"]):
            p.append("throughput_jobs_per_hour is not n x 3600 / batch_wall_s")
        if all(isinstance(j.get("sha256_equal_single"), bool) for j in m["jobs"]):
            if m["digests_equal_single"] != all(j["sha256_equal_single"] for j in m["jobs"]):
                p.append("digests_equal_single does not follow from the jobs")
        else:
            p.append("a job lacks sha256_equal_single")
    elif kind == "B-model":
        if m["peak_rss_gib"] <= 0:
            p.append("peak_rss_gib is not positive")
        elif m["limit"] != min(m["cores"], math.floor(m["ram_gib"] / m["peak_rss_gib"])):
            p.append("limit is not min(cores, floor(ram_gib / peak_rss_gib))")
    elif kind == "C":
        if not (m["reference_s"] > 0 and _close(m["fraction"], m["cancel_after_s"] / m["reference_s"])):
            p.append("fraction is not cancel_after_s / reference_s")
    elif kind == "D":
        if not all(isinstance(v, bool) for v in m["equal_single"].values()):
            p.append("equal_single holds a value that is not true or false")
    elif kind == "E":
        if not (0 <= m["differing"] <= m["samples"] and m["samples"] > 0):
            p.append("differing is not between 0 and samples")
        elif not _close(m["fraction_differing"], m["differing"] / m["samples"]):
            p.append("fraction_differing is not differing / samples")
        if (m["differing"] == 0) != (m["max_abs"] == 0):
            p.append("max_abs is zero exactly when nothing differs")
    elif kind == "F":
        p += _offset_problems(m)
    elif kind == "G":
        p += _digits_or_instant_problems(m)
    return p


def _split_time(s):
    """(clock digits, offset, instant) of an ISO 8601 time with a `+hh:mm` or `-hh:mm` offset."""
    from datetime import datetime
    if not (isinstance(s, str) and re.fullmatch(r".+[+-]\d\d:\d\d", s)):
        raise ValueError(s)
    return s[:-6], s[-6:], datetime.fromisoformat(re.sub(r"(\.\d+)(?=[+-]\d\d:\d\d$)", "", s)).timestamp()


def _digits_or_instant_problems(m):
    """Risk G: the pairs are what they are named, and `repeatable` and `result` follow from the digests."""
    labels = list(m["written"])
    try:
        parts = {x: _split_time(s) for x, s in m["written"].items()}
    except ValueError:
        return ["a written time is not an ISO 8601 time with an offset"]
    pairs = [m["repeat"]] + m["digits_held"] + m["instant_held"]
    if set(m["products"]) != set(labels) or not m["digits_held"] or not m["instant_held"] or \
            any(not (isinstance(q, list) and len(q) == 2 and set(q) <= set(labels)) for q in pairs):
        return ["products, written and the pairs do not name the same renders"]
    if not m["compared"] or any(f not in m["products"][x] for f in m["compared"] for x in labels):
        return ["a compared product is missing from a render"]
    p = []
    if m["written"][m["repeat"][0]] != m["written"][m["repeat"][1]]:
        p.append("the repeat pair's written times differ")
    for a, b in m["digits_held"]:
        if parts[a][0] != parts[b][0] or parts[a][1] == parts[b][1]:
            p.append(f"digits-held pair {a}, {b}: not the same digits at two offsets")
    for a, b in m["instant_held"]:
        if parts[a][2] != parts[b][2] or parts[a][1] == parts[b][1]:
            p.append(f"instant-held pair {a}, {b}: not the same instant at two offsets")

    def same(a, b):
        return all(m["products"][a][f] == m["products"][b][f] for f in m["compared"])
    if m["repeatable"] != same(*m["repeat"]):
        p.append("repeatable does not follow from the repeat pair's digests")
    digits = [same(a, b) for a, b in m["digits_held"]]
    instant = [same(a, b) for a, b in m["instant_held"]]
    result = "not decidable" if not m["repeatable"] else \
        "written digits" if all(digits) and not any(instant) else \
        "instant" if all(instant) and not any(digits) else "not isolated"
    if m["result"] not in G_RESULTS or m["result"] != result:
        p.append(f"result does not follow from the digests (they give {result!r})")
    return p


def _offset_problems(m):
    """Risk F: every written time is the stated instant, and `repeatable` and `result` follow from the digests."""
    from datetime import datetime
    p = []

    def instant(s):
        return datetime.fromisoformat(re.sub(r"(\.\d+)(?=[+-]\d\d:\d\d$)", "", s)).timestamp()
    try:
        ref = instant(m["instant"])
        if any(instant(s) != ref for s in m["written"].values()):
            p.append("a written time is not the stated instant")
        if len({s[-6:] for s in m["written"].values()}) < 2:
            p.append("written: fewer than two offsets")
    except (TypeError, ValueError):
        return ["instant or a written time is not an ISO 8601 time with an offset"]
    labels = list(m["written"])
    if set(m["products"]) != set(labels) or len(m["repeat"]) != 2 or not set(m["repeat"]) <= set(labels) \
            or m["written"][m["repeat"][0]] != m["written"][m["repeat"][1]]:
        return p + ["products, written and the repeat pair do not name the same renders"]
    if not m["compared"] or any(f not in m["products"][x] for f in m["compared"] for x in labels):
        return p + ["a compared product is missing from a render"]

    def same(a, b):
        return all(m["products"][a][f] == m["products"][b][f] for f in m["compared"])
    if m["repeatable"] != same(*m["repeat"]):
        p.append("repeatable does not follow from the repeat pair's digests")
    first = m["repeat"][0]
    result = "not decidable" if not m["repeatable"] else \
        "instant only" if all(same(first, x) for x in labels) else "offset dependent"
    if m["result"] not in F_RESULTS or m["result"] != result:
        p.append(f"result does not follow from the digests (they give {result!r})")
    return p


def check(path=RESULTS):
    """Problems of the results file: form, duplicates, order, and per-record problems."""
    try:
        where0 = path.relative_to(ROOT)
    except ValueError:
        where0 = path
    if not path.is_file():
        return [f"{where0}: missing"]
    problems, seen, keys = [], set(), []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        where = f"{where0}:{i}"
        try:
            r = json.loads(line)
        except ValueError as e:
            problems.append(f"{where}: not JSON ({e})")
            continue
        problems += [f"{where}: {x}" for x in record_problems(r)]
        if isinstance(r, dict) and "risk" in r and "id" in r:
            key = (str(r["risk"]), str(r["id"]))
            if key in seen:
                problems.append(f"{where}: {key[0]}/{key[1]} recorded twice")
            seen.add(key)
            keys.append(key)
    if keys != sorted(keys):
        problems.append(f"{where0}: records are not sorted by risk, then id")
    return problems


def add(files, path=RESULTS):
    new = [json.loads(line) for f in files for line in Path(f).read_text().splitlines() if line.strip()]
    bad = [f"{r.get('risk')}/{r.get('id')}: {x}" for r in new for x in record_problems(r)]
    if bad:
        raise SystemExit("not added:\n" + "\n".join(bad))
    keep = {(r["risk"], r["id"]): r for r in load_results(path)}
    keep.update({(r["risk"], r["id"]): r for r in new})
    write_results(list(keep.values()), path)
    return len(new)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="verify the results file; exit 1 on a problem")
    sub = ap.add_subparsers(dest="cmd")
    a_ = sub.add_parser("add", help="merge records (JSON lines) into the results file")
    a_.add_argument("files", nargs="+", type=Path)
    sub.add_parser("list", help="one line per record")
    a = ap.parse_args(argv)
    if a.check:
        problems = check()
        n = len(load_results()) if RESULTS.is_file() else 0
        print("\n".join(problems) if problems else f"{n} records: well formed, derived numbers recompute")
        return 1 if problems else 0
    if a.cmd == "add":
        print(f"{add(a.files)} records merged into {RESULTS.relative_to(ROOT)}")
        return 0
    if a.cmd == "list":
        for r in load_results():
            print(f"{r['risk']} {r['id']}: {json.dumps(r['configuration'])[:100]}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
