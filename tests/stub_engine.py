#!/usr/bin/env python3
"""A stub for `dirsig5` in the pass-through tests: no DIRSIG. It records its arguments, and unless `--dry_run` is given
writes a few files into `--output_folder` (an image, its header, a log) and one file beside the simulation file (as a
scene compile would). Exit status: 0, or the integer in the environment variable STUB_ENGINE_EXIT."""
import json
import os
import sys
import time
from pathlib import Path

args = sys.argv[1:]
if "--version" in args or "-v" in args:
    print("stub-engine 0.0 (not DIRSIG)")
    sys.exit(0)
out = next((a.split("=", 1)[1] for a in args if a.startswith("--output_folder=")), ".")
sim = args[-1]
Path("stub_engine_args.json").write_text(json.dumps({"args": args, "cwd": os.getcwd(), "sim_exists": Path(sim).is_file()}))
delay = float(os.environ.get("STUB_ENGINE_SLEEP", "0"))
time.sleep(delay)
if "--dry_run" not in args:
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "demo-t0000-c0000.img").write_bytes(bytes(range(64)))
    (Path(out) / "demo-t0000-c0000.img.hdr").write_text("ENVI\nsamples = 4\nlines = 2\nbands = 1\n")
    (Path(out) / "demo.weird").write_text("an unknown extension\n")
    Path("demo.scene.hdf").write_bytes(b"compiled")
sys.exit(int(os.environ.get("STUB_ENGINE_EXIT", "0")))
