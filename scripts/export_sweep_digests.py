#!/usr/bin/env python3
"""Export a demo sweep's output digests as a compressed table: one JSON line per attempt.

    python scripts/export_sweep_digests.py --results <work>/sweep/results.jsonl [--out docs/data/demo_sweep_digests.jsonl.gz]
    python scripts/export_sweep_digests.py --check [--results <work>/sweep/results.jsonl]

Reads the results file `scripts/sweep_demos.py` writes (outside the repository) and writes, for every `attempt` line in
file order, `{"demo", "simulation", "outcome", "repeat", "output_count", "outputs": [{"name", "size", "sha256"}]}`,
with outputs sorted by name. Digests, names and sizes only: no output bytes. The gzip stream carries no file name and
a zero time stamp, so the same results give the same bytes. If the compressed table would exceed `LIMIT_BYTES`, each
attempt keeps its first `KEEP_OUTPUTS` outputs (by name), `output_count` still gives the total, and a line
`{"truncated": KEEP_OUTPUTS}` comes first.

`--check` with `--results`: the committed table equals the one the results give (exit 1 otherwise). Without
`--results` (the results file is not in the repository): the committed table parses and every line has the members
above (exit 1 otherwise).
"""
import argparse
import gzip
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data" / "demo_sweep_digests.jsonl.gz"
LIMIT_BYTES = 10 * 1024 * 1024
KEEP_OUTPUTS = 200
MEMBERS = ("demo", "simulation", "outcome", "repeat", "output_count", "outputs")


def read_results(path):
    out = []
    for ln in Path(path).read_text().splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:                                      # a line cut by a crash
            continue
    return out


def rows(records, keep=None):
    """The table's rows: one per attempt line, outputs sorted by name, the first `keep` of them when given."""
    out = []
    for r in records:
        if r.get("type") != "attempt":
            continue
        outputs = sorted(({"name": o["name"], "size": o["size"], "sha256": o["sha256"]} for o in r.get("outputs") or []),
                         key=lambda o: o["name"])
        out.append({"demo": r["demo"], "simulation": r.get("simulation"), "outcome": r.get("outcome"),
                    "repeat": bool(r.get("repeat")), "output_count": len(outputs),
                    "outputs": outputs[:keep] if keep is not None else outputs})
    return out


def compress(lines):
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as gz:
        for line in lines:
            gz.write((json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n").encode())
    return buf.getvalue()


def table(records, limit=LIMIT_BYTES, keep=KEEP_OUTPUTS):
    """`(bytes, truncated)`: the compressed table, cut to `keep` outputs per attempt if it would exceed `limit`."""
    data = compress(rows(records))
    if len(data) <= limit:
        return data, False
    return compress([{"truncated": keep}] + rows(records, keep)), True


def parse(data):
    return [json.loads(ln) for ln in gzip.decompress(data).decode().splitlines()]


def check_structure(data):
    """Problems with a committed table read on its own; empty when it is well formed."""
    try:
        lines = parse(data)
    except (OSError, ValueError, EOFError) as e:
        return [f"not a gzip JSON lines file: {e}"]
    problems = []
    for i, line in enumerate(lines):
        if i == 0 and set(line) == {"truncated"}:
            continue
        missing = [m for m in MEMBERS if m not in line]
        if missing:
            problems.append(f"line {i + 1}: missing {missing}")
        elif any(set(o) != {"name", "size", "sha256"} for o in line["outputs"]):
            problems.append(f"line {i + 1}: an output is not {{name, size, sha256}}")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", type=Path, help="the sweep's results.jsonl")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--check", action="store_true", help="verify the committed table instead of writing it")
    args = ap.parse_args(argv)
    if args.check:
        if not args.out.is_file():
            print(f"{args.out} is missing", file=sys.stderr)
            return 1
        committed = args.out.read_bytes()
        if args.results is None:
            problems = check_structure(committed)
            for p in problems:
                print(p, file=sys.stderr)
            return 1 if problems else 0
        expected, _ = table(read_results(args.results))
        if committed != expected:
            print(f"{args.out} differs from the table {args.results} gives; rerun without --check", file=sys.stderr)
            return 1
        return 0
    if args.results is None:
        ap.error("--results is required to write the table")
    data, truncated = table(read_results(args.results))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)
    n = sum(1 for line in parse(data) if "demo" in line)
    print(f"wrote {args.out} ({len(data)} bytes, {n} attempts{f', {KEEP_OUTPUTS} outputs kept per attempt' if truncated else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
