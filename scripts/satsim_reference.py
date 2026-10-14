#!/usr/bin/env python3
"""The SatSim reference run: run it, measure it, and record or check its output digests.

    python scripts/satsim_reference.py [--work DIR]           run, then (re)write docs/data/satsim_reference_digests.jsonl
    python scripts/satsim_reference.py --check [--work DIR]   run, then exit 1 if a digest differs from the table

The reference is `manifold_run_specs/satsim/tahoe_worldview2.yaml` (the library sample, seed 1, cpu). It runs three
times through `LocalBackend`, each in its own work root under `--work` (default: a temporary folder, deleted after):
`default-a` and `default-b` (the reference twice, so its run directory is new each time) and `one-thread` (the same with
`resources.cpu_threads: 1`, another run id). Needs SatSim's interpreter and the pinned assets; without them it exits 2
naming what is missing.

The table has one JSON line per run: its label, run id, `cpu_threads`, and every artifact's name, role, size and sha256,
except the two that hold the run's own timing and paths (`worker.log`, `satsim_result.json`), which are listed by name
only. The script prints a summary: per run the wall time from submission to the final state, SatSim's own elapsed time
(the launcher's), and the peak resident memory of the largest process of the runs so far (`RUSAGE_CHILDREN`: the SatSim
process, reaped by its worker); whether `default-a` and `default-b` are byte-identical in every listed artifact, and
whether `one-thread` equals them in every artifact but `run_spec.json` (whose sha256 is the run id).
"""
import argparse
import json
import resource
import shutil
import sys
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "manifold_run_specs" / "satsim" / "tahoe_worldview2.yaml"
TABLE = ROOT / "docs" / "data" / "satsim_reference_digests.jsonl"
VARYING = ("worker.log", "satsim_result.json")
sys.path[:0] = [str(ROOT / "packages" / d / "src") for d in ("core", "sim")] + [str(ROOT / "tests")]

import manifold.sim  # noqa: E402,F401  (installs the discovered engine registry)
from manifold.sim import engines                       # noqa: E402
from manifold.sim.backend import LocalBackend          # noqa: E402


def _run(work, label, threads):
    from backend_conformance import wait_for
    spec = yaml.safe_load(SPEC.read_text())
    if threads is not None:
        spec["resources"] = {"cpu_threads": threads}
    path = work / f"{label}.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    backend = LocalBackend(work / label, ROOT / "manifold_config_repo")
    started = time.monotonic()
    final = wait_for(backend, backend.submit_run(str(path))["run_id"], ("rendered", "failed", "cancelled"), timeout=600)
    wall = time.monotonic() - started
    if final["state"] != "rendered":
        raise SystemExit(f"{label}: {final['state']}: {final['errors']}")
    record = backend.store.read_record(final["run_id"])
    out = backend.store.run_dir(final["run_id"]) / "output"
    line = {"label": label, "run_id": final["run_id"], "cpu_threads": threads,
            "artifacts": [{"name": a["name"], "role": a.get("role"), **({} if a["name"] in VARYING else
                          {"size": Path(a["uri"].removeprefix("file://")).stat().st_size, "sha256": a["sha256"]})}
                          for a in final["artifacts"]]}
    measured = {"label": label, "wall_s": round(wall, 2), "satsim_elapsed_s": record["engine_metadata"]["elapsed_s"],
                "peak_rss_mb_so_far": round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1),
                "network_attempts": (out / "network_attempts.log").is_file(), "fingerprint": record.get("satsim"),
                "engine_metadata": record["engine_metadata"]}
    return line, measured


def _digests(line, skip=()):
    return {a["name"]: a.get("sha256") for a in line["artifacts"] if a["name"] not in VARYING and a["name"] not in skip}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--work", type=Path, default=None)
    a = ap.parse_args(argv)
    adapter = engines.registry().find("satsim")
    reason = adapter.availability() if adapter is not None else "the satsim engine is not registered"
    if reason:
        print(f"SatSim is not available: {reason}", file=sys.stderr)
        return 2
    work = a.work or Path(tempfile.mkdtemp(prefix="satsim-reference-"))
    work.mkdir(parents=True, exist_ok=True)
    try:
        runs = [_run(work, label, threads) for label, threads in (("default-a", None), ("default-b", None),
                                                                    ("one-thread", 1))]
    finally:
        if a.work is None:
            shutil.rmtree(work, ignore_errors=True)
    lines = [r[0] for r in runs]
    da, db, one = lines
    summary = {"runs": [r[1] for r in runs],
               "repeat_identical": _digests(da) == _digests(db) and da["run_id"] == db["run_id"],
               "one_thread_equals_default": _digests(one, ("run_spec.json",)) == _digests(da, ("run_spec.json",)),
               "artifacts_compared": len(_digests(da))}
    print(json.dumps(summary, indent=1))
    text = "".join(json.dumps(line, sort_keys=True) + "\n" for line in lines)
    if a.check:
        ok = TABLE.is_file() and TABLE.read_text() == text
        print("the reference digests match docs/data/satsim_reference_digests.jsonl" if ok else
              "the reference digests DIFFER from docs/data/satsim_reference_digests.jsonl", file=sys.stderr)
        return 0 if ok and summary["repeat_identical"] and summary["one_thread_equals_default"] else 1
    TABLE.write_text(text)
    print(f"wrote {TABLE.relative_to(ROOT)}")
    return 0 if summary["repeat_identical"] and summary["one_thread_equals_default"] else 1


if __name__ == "__main__":
    sys.exit(main())
