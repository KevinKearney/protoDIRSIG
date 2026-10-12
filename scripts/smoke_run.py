#!/usr/bin/env python3
"""Smoke run of a fresh setup: the DIRSIG layered and pass-through forms at their expected run ids.

    python scripts/smoke_run.py                  # compose both runs offline and compare their run ids with EXPECTED
    python scripts/smoke_run.py --render [--work DIR]
                                                 # also render both through Workspace (needs DIRSIG and the demo assets)

The layered run is the library recipe `auror_ref` with a 16 x 16 window on every settings member (the recipe document
is edited in memory; no library file changes). The pass-through run is the library recipe
`demo_pointcollectors2_passthrough` as authored (PointCollectors2's own image size; about 6 s). Composition is offline
and needs neither DIRSIG nor `dirfm`; the pass-through recipe needs its demo directory materialized
(`scripts/bootstrap.py assets`) only to render. `--render` submits both to a `Workspace.local` whose work root is
`--work` (default a new temporary directory, deleted afterwards), waits, and prints each run's state and verdict.
Exit status 1 if a run id differs from EXPECTED or a render does not end `rendered` with verdict `complete`.
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RECIPES = ROOT / "manifold_run_specs" / "recipes"

EXPECTED = {
    "auror_ref (16 x 16)": "b1b01f1f01f157c96cf8f6b98f39d24a12781ce94101f9ab201b48f03c465ec0",
    "demo_pointcollectors2_passthrough": "0ee025143676ad443fa41ff7c511bb5260b96bff8284c117aca05be85a670944",
}


def recipes():
    """{label: recipe document}."""
    layered = yaml.safe_load((RECIPES / "auror_ref.yaml").read_text())
    for member in layered["settings"]:
        member["roi"] = {"Width": 16, "Height": 16, "OffsetX": None, "OffsetY": None}
    passthrough = yaml.safe_load((RECIPES / "demo_pointcollectors2_passthrough.yaml").read_text())
    return {"auror_ref (16 x 16)": layered, "demo_pointcollectors2_passthrough": passthrough}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--render", action="store_true", help="render both runs (needs DIRSIG and the demo assets)")
    ap.add_argument("--work", type=Path, help="the work root for --render (default: a temporary directory)")
    ap.add_argument("--timeout", type=float, default=600.0)
    args = ap.parse_args(argv)
    from manifold.sim import Workspace

    work = args.work or Path(tempfile.mkdtemp(prefix="manifold-smoke-"))
    ws = Workspace.local(work=work)
    bad = 0
    try:
        for label, doc in recipes().items():
            run_id = ws.compose(doc).runs[0].run_id
            ok = run_id == EXPECTED[label]
            bad += not ok
            print(f"{label}: run id {run_id} {'(expected)' if ok else 'DIFFERS from ' + EXPECTED[label]}")
            if args.render:
                status = ws.submit_run(doc)
                final = ws.wait(status.run_id, timeout=args.timeout)
                good = final.state == "rendered" and final.verdict == "complete"
                bad += not good
                print(f"{label}: {final.state}, verdict {final.verdict}, {len(ws.list_artifacts(status.run_id).artifacts)} artifacts")
    finally:
        if args.work is None:
            shutil.rmtree(work, ignore_errors=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
