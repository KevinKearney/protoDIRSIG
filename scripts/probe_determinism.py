#!/usr/bin/env python3
"""Determinism probe: render chosen demos twice under each of several conditions and keep the outputs for comparison.

    python scripts/probe_determinism.py --work DIR --results <sweep>/results.jsonl --demos A,B,...
                                        [--conditions C0,C1,C2] [--seed N] [--timeout S] [--disk-floor-gb G]
    python scripts/probe_determinism.py --work DIR --compare

Conditions: `C0` DIRSIG's defaults (as the sweep ran); `C1` one thread (`dirsig5 --threads=1`, through a wrapper in
`<work>/bin` that adds the option, since the engine contract has no thread count); `C2` an explicit seed (`--seed`,
default 1, passed as the run's seed, `--random_seed`). Each demo is extracted from its zip once into
`<work>/demos/<Name>` (the demo is not modified), and each render runs the SDK's pass-through runner
(`manifold.sim._dirsig.passthrough.run_engine`: scene compile, the engine, a per-run `HOME`) on the simulation file the sweep
rendered, in its own fresh directory `<work>/runs/<Name>/<condition>-<rep>`; the copy of the demo is deleted after the
render and `output/` is kept. One render at a time. A line per render is appended to `<work>/probe.jsonl` (demo,
simulation, condition, rep, return code, wall time, outputs with size and sha256, maximum CPU temperature, CPU
frequency); a render already recorded is skipped, so a rerun resumes.

`--compare` compares, for each demo, the two renders of each condition (the noise floor of that condition) and the
first render of each condition against the first of `C0`, with `scripts/compare_outputs.py`, masking the work root
and run directory names, and writes `<work>/compare.json`.

Nothing is written into the repository. Deletion is limited to `<work>` (`sweep_demos.safe_delete`).
"""
import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "packages" / d / "src") for d in ("core", "sim")]   # the manifold namespace, uninstalled
sys.path.insert(0, str(ROOT / "scripts"))

import compare_outputs  # noqa: E402
import sweep_demos  # noqa: E402
from manifold.sim._dirsig.passthrough import PassthroughRun, run_engine  # noqa: E402
from manifold.sim._dirsig.adapter import locate_dirsig  # noqa: E402

CONDITIONS = {"C0": "default", "C1": "one thread", "C2": "explicit seed"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_lines(path):
    out = []
    if Path(path).is_file():
        for ln in Path(path).read_text().splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
    return out


def swept_simulation(results, name):
    """The simulation file the sweep rendered for `name` (its first rendered attempt), or None."""
    for r in read_lines(results):
        if r.get("type") == "demo" and r.get("demo") == name:
            for a in r.get("attempts", []):
                if a.get("outcome") == "rendered":
                    return a["simulation"]
    return None


def thread_wrapper(work, engine):
    """`<work>/bin/dirsig5`, which runs `engine` with `--threads=1`, and `scene2hdf` beside it (the runner compiles
    scenes with the `scene2hdf` beside the engine)."""
    bin_dir = Path(work) / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "dirsig5"
    wrapper.write_text(f'#!/bin/sh\nexec "{engine}" --threads=1 "$@"\n')
    wrapper.chmod(0o755)
    link = bin_dir / "scene2hdf"
    if not link.exists():
        link.symlink_to(Path(engine).parent / "scene2hdf")
    return wrapper


def render(work, name, directory, simulation, condition, rep, engine, seed, timeout):
    run_dir = Path(work) / "runs" / name / f"{condition}-{rep}"
    if run_dir.exists():
        sweep_demos.safe_delete(run_dir, [work])
    run_dir.mkdir(parents=True)
    run = PassthroughRun(name, Path(directory), Path(directory) / simulation, simulation,
                         seed if condition == "C2" else None)
    t0 = time.monotonic()
    try:
        result = run_engine(run, run_dir, engine, timeout=timeout, log=run_dir / "engine.log", home=run_dir / "home")
        rc, timed_out = result["returncode"], False
    except Exception as e:  # noqa: BLE001 -- a timeout or a runner failure is a result
        result, rc, timed_out = {"command": [], "max_cpu_temp_c": None, "cpu_freq_khz": None}, None, True
        (run_dir / "engine.log").open("a").write(f"\nprobe: {type(e).__name__}: {e}\n")
    wall = round(time.monotonic() - t0, 1)
    out = run_dir / "output"
    outputs = [{"name": p.relative_to(out).as_posix(), "size": p.stat().st_size, "sha256": sha256(p)}
               for p in sorted(out.rglob("*")) if p.is_file()] if out.is_dir() else []
    if (run_dir / "input").exists():
        sweep_demos.safe_delete(run_dir / "input", [work])
    return {"demo": name, "simulation": simulation, "condition": condition, "rep": rep, "returncode": rc,
            "timed_out": timed_out, "wall_s": wall, "outputs": outputs,
            "command": [Path(c).name if i == 0 else c for i, c in enumerate(result.get("command") or [])],
            "max_cpu_temp_c": result.get("max_cpu_temp_c"), "cpu_freq_khz": result.get("cpu_freq_khz")}


def probe(args):
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    dirsig = locate_dirsig()
    if not dirsig["home"]:
        sys.exit("no DIRSIG installation found")
    engine = Path(dirsig["home"]) / "bin" / "dirsig5"
    engines = {"C0": engine, "C1": thread_wrapper(work, engine), "C2": engine}
    found, _ = sweep_demos.candidates(dirsig["home"])
    by_name = {c["name"]: c for c in found}
    log = work / "probe.jsonl"
    done = {(r["demo"], r["condition"], r["rep"]) for r in read_lines(log)}
    for name in args.demos:
        sim = swept_simulation(args.results, name)
        if sim is None or name not in by_name:
            print(f"{name}: not rendered by the sweep or not in the installation; skipped", flush=True)
            continue
        directory = work / "demos" / name
        if not directory.is_dir():
            sweep_demos.extract(by_name[name], directory)
        for condition in args.conditions:
            for rep in (1, 2):
                if (name, condition, rep) in done:
                    continue
                free = shutil.disk_usage(work).free
                if free < args.disk_floor_gb * 1e9:
                    sys.exit(f"free disk {free / 1e9:.1f} GB is below the floor {args.disk_floor_gb} GB; stopped")
                print(f"{time.strftime('%H:%M:%S')} {name} {sim} {condition} rep {rep}", flush=True)
                rec = render(work, name, directory, sim, condition, rep, engines[condition], args.seed, args.timeout)
                with open(log, "a") as f:
                    f.write(json.dumps(rec) + "\n")
                print(f"  rc {rec['returncode']} {rec['wall_s']} s, {len(rec['outputs'])} outputs, "
                      f"{rec['max_cpu_temp_c']} C", flush=True)
    return 0


def compare(args):
    work = args.work.resolve()
    recs = read_lines(work / "probe.jsonl")
    demos = sorted({r["demo"] for r in recs})
    out = {}
    for name in demos:
        base = work / "runs" / name
        pairs = {}
        for condition in CONDITIONS:
            a, b = base / f"{condition}-1" / "output", base / f"{condition}-2" / "output"
            if a.is_dir() and b.is_dir():
                pairs[f"{condition} pair"] = (a, b)
            if condition != "C0" and a.is_dir() and (base / "C0-1" / "output").is_dir():
                pairs[f"C0 vs {condition}"] = (base / "C0-1" / "output", a)
        out[name] = {}
        for label, (a, b) in pairs.items():
            masks = [str(work), str(a.parent), str(b.parent), a.parent.name, b.parent.name]
            out[name][label] = compare_outputs.headers_only(compare_outputs.compare_dirs(a, b, masks))
    (work / "compare.json").write_text(json.dumps(out, indent=1) + "\n")
    for name, labels in out.items():
        for label, records in labels.items():
            differing = [f"{r['name']}: {r['class']}" for r in records if r["class"] != "identical"]
            print(f"{name:20s} {label:10s} {'identical' if not differing else '; '.join(differing)}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--results", type=Path, help="the sweep's results.jsonl (which simulation file rendered)")
    ap.add_argument("--demos", type=lambda s: [x for x in s.split(",") if x], default=[])
    ap.add_argument("--conditions", type=lambda s: [x for x in s.split(",") if x], default=list(CONDITIONS))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--disk-floor-gb", type=float, default=20.0)
    ap.add_argument("--compare", action="store_true")
    args = ap.parse_args(argv)
    if args.compare:
        return compare(args)
    if args.results is None or not args.demos:
        ap.error("--results and --demos are required to probe")
    bad = [c for c in args.conditions if c not in CONDITIONS]
    if bad:
        ap.error(f"unknown conditions {bad}; known: {list(CONDITIONS)}")
    return probe(args)


if __name__ == "__main__":
    sys.exit(main())
