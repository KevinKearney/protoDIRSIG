#!/usr/bin/env python3
"""The DIRSIG closure test (round 47): run a job end to end with `scene2hdf` and `dirsig5` under `strace`, and compare
the walker's list, the job tree's contents and the files the engine opened (`manifold.engines.dirsig.closure_trace`).

    python scripts/closure_trace.py one SPEC --work DIR [--threads 2]     one tree; prints its record (JSON)
    python scripts/closure_trace.py corpus --work DIR --stop-at EPOCH     every DIRSIG spec not yet recorded, breadth
                                                                          first, appended to docs/data/closure_trace.jsonl
    python scripts/closure_trace.py --table                                the summary table from the committed records
    python scripts/closure_trace.py --write-doc                            write that table into docs/Closure_walk.md

How a tree is run. `DIR/bin/` holds two wrappers named `scene2hdf` and `dirsig5`, first on `PATH`, so dirfm's
`DIRSIG.run` (layered) and `passthrough.run_engine` (pass-through) start them exactly as they start the real tools. The
first wrapper to start walks the tree (`closure.walk`) and lists its files (`closure_trace.job_files`) before any tool
has run (`pre.json`), so the walk sees the tree the engine starts on. Each wrapper then sets `HOME` to an empty
`DIR/home` (Cfg A.6: the executor runs DIRSIG with an empty home, so no user plugin or material cache is read) and
`exec`s `strace -ff -y -s 4096 --seccomp-bpf -e trace=open,openat,openat2` on the real tool from the located DIRSIG
installation. Layered: `Simulation.run(threads=...)` (dirfm passes `--threads` to `dirsig5`; it starts `scene2hdf` with
`--threads <cpu count>`, unchanged). Pass-through: `run_engine(..., threads=...)`. The seed is the spec's.

A record: `spec`, `mode`, `threads`, `ran` (both tools exited 0), `error`, `seconds`, `entry`, `walked`, `job` (counts),
the sets of `closure_sets` as lists (`listed_not_in_job`, `in_job_not_listed`, `read_in_neither`, `generated`,
`listed_not_read`, `library_written`), `roles` (walked path -> role, for the sets' paths), `read` (count) and
`read_by` (path -> tools), `written`, `probed`, `install_read` (installation files opened, shared libraries left out),
`install_libraries` (their count), `install_listed` (the walker's `$DIRSIG_HOME` references) and
`install_listed_not_read`, `home_read`, `output_read` (counts). The tree is removed afterwards.
"""
import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "manifold_config_repo"
SENSORS = ROOT / "manifold_sensors"
RECORDS = ROOT / "docs" / "data" / "closure_trace.jsonl"
DOC = ROOT / "docs" / "Closure_walk.md"
BEGIN, END = "<!-- closure-trace-table -->", "<!-- /closure-trace-table -->"
TOOLS = ("scene2hdf", "dirsig5")
_SHARED = re.compile(r"\.so(\.\d+)*$")

sys.path.insert(0, str(ROOT / "scripts"))
import closure_walk as cw  # noqa: E402  (specs(), the corpus of round 46)

WRAPPER = """#!/bin/bash
if [ ! -e "$CLOSURE_OUT/pre.json" ]; then
  "{python}" "{script}" pre || exit 97
fi
export HOME="$CLOSURE_HOME"
exec strace -ff -y -s 4096 -qq --seccomp-bpf -e trace=open,openat,openat2 \\
  -o "$CLOSURE_OUT/trace.{tool}.$$" "{real}" "$@"
"""


def _install():
    from manifold.engines.dirsig.adapter import locate_dirsig
    home = locate_dirsig()["home"]
    if home is None:
        raise SystemExit("no DIRSIG installation found")
    return Path(home)


def pre():
    """Run by the first wrapper: walk the tree and list its files before any tool runs."""
    from manifold.engines.dirsig.closure import walk
    from manifold.engines.dirsig.closure_trace import job_files
    root, entry, out = os.environ["CLOSURE_ROOT"], os.environ["CLOSURE_ENTRY"], Path(os.environ["CLOSURE_OUT"])
    w = walk(root, entry)
    doc = {"cwd": os.getcwd(), "walked": {f.path: f.role for f in w.files},
           "install": [t for t, _, _ in w.install], "job": job_files(root)}
    (out / "pre.json").write_text(json.dumps(doc))
    return 0


def _tool_cwds(out):
    """The folder each traced process started in, from its first open (`AT_FDCWD</cwd>`)."""
    cwds = {}
    for f in out.glob("trace.*"):
        m = re.search(r"AT_FDCWD<((?:[^>\\]|\\.)*)>", f.read_text(errors="surrogateescape")[:20000])
        cwds[f.name] = m.group(1) if m else None
    return cwds


def run_one(spec, work, threads):
    """Build and run one spec under trace; returns its record."""
    from manifold.core.run_spec import load_run_spec
    from manifold.engines.dirsig.closure_trace import closure_sets, parse_trace
    from manifold.engines.dirsig.passthrough_spec import is_passthrough, resolve_passthrough
    install = _install()
    work = Path(work).resolve()
    if work.exists():
        shutil.rmtree(work)
    out, bindir, home = work / "trace", work / "bin", work / "home"
    for d in (out, bindir, home):
        d.mkdir(parents=True)
    for tool in TOOLS:
        w = bindir / tool
        w.write_text(WRAPPER.format(python=sys.executable, script=Path(__file__).resolve(), tool=tool,
                                    real=install / "bin" / tool))
        w.chmod(0o755)
    doc = load_run_spec(ROOT / spec)
    mode = "passthrough" if is_passthrough(doc) else "layered"
    rec = {"spec": spec, "mode": mode, "threads": threads}
    env = {"CLOSURE_OUT": str(out), "CLOSURE_HOME": str(home), "DIRSIG_HOME": str(install),
           "PATH": f"{bindir}{os.pathsep}{install / 'bin'}{os.pathsep}{os.environ['PATH']}"}
    t0 = time.time()
    error = None
    if mode == "passthrough":
        from manifold.engines.dirsig.passthrough import run_engine
        run = resolve_passthrough(doc, LIBRARY)
        root, entry = work / "input" / run.directory.name, run.simulation_rel
        os.environ.update(env, CLOSURE_ROOT=str(root), CLOSURE_ENTRY=entry)
        res = run_engine(run, work, bindir / "dirsig5", log=work / "engine.log", threads=threads)
        if res["returncode"] != 0:
            error = f"{res['command'][0]} exited {res['returncode']}"
        output = work / "output"
    else:
        from manifold.engines.dirsig.simulation import Simulation
        root, entry = work / "input", "example.jsim"
        os.environ.update(env, CLOSURE_ROOT=str(root), CLOSURE_ENTRY=entry)
        sim = Simulation.from_run_spec(ROOT / spec, LIBRARY, work, SENSORS)
        output = work / "output"
        if sim.resolved is None:
            rec.update(ran=False, error=f"not built: {sim.resolve_error or sim.load_error}", seconds=0)
            shutil.rmtree(work, ignore_errors=True)
            return rec
        try:
            sim.run(out_dir=output, threads=threads)
        except Exception as e:  # noqa: BLE001  -- recorded, not raised
            error = f"{type(e).__name__}: {str(e).strip()[:2000]}"
    rec["seconds"] = round(time.time() - t0, 1)
    if not (out / "pre.json").is_file():
        rec.update(ran=False, error=error or "no tool started")
        shutil.rmtree(work, ignore_errors=True)
        return rec
    pre_doc = json.loads((out / "pre.json").read_text())
    cwds = _tool_cwds(out)
    opens, calls = [], 0
    for f in sorted(out.glob("trace.*")):
        tool, text = f.name.split(".")[1], f.read_text(errors="surrogateescape")
        calls += sum(1 for ln in text.splitlines() if re.match(r"(open|openat|openat2)\(", ln))
        opens += parse_trace(text, tool, cwds.get(f.name) or pre_doc["cwd"])
    places = {"root": str(root), "library": str(LIBRARY), "install": str(install), "home": str(home),
              "output": str(output)}
    s = closure_sets(pre_doc["walked"], pre_doc["job"], opens, places)
    walked = pre_doc["walked"]
    listed_install = sorted({t.replace("$DIRSIG_HOME", "", 1).lstrip("/") for t in pre_doc["install"]})
    install_read = [p for p in s["install"] if not _SHARED.search(p)]
    named = set(s["listed_not_in_job"]) | set(s["listed_not_read"]) | set(s["in_job_not_listed"])
    rec.update({
        "ran": error is None, "error": error, "entry": entry, "walked": len(walked), "job": len(pre_doc["job"]),
        "listed_not_in_job": s["listed_not_in_job"], "in_job_not_listed": s["in_job_not_listed"],
        "read_in_neither": s["read_in_neither"], "generated": s["generated"],
        "listed_not_read": s["listed_not_read"], "library_written": s["library_written"],
        "roles": {p: walked[p] for p in sorted(named) if p in walked},
        "read": len(s["read"]), "read_by": s["read"], "written": s["written"], "probed": s["probed"],
        "install_read": install_read, "install_libraries": len(s["install"]) - len(install_read),
        "install_listed": listed_install, "install_listed_not_read": [p for p in listed_install
                                                                      if p not in s["install"]],
        "home_read": len(s["home"]), "output_read": len(s["output"]),
        "trace_files": len(list(out.glob("trace.*"))), "opens": len(opens), "unparsed": calls - len(opens),
    })
    if not os.environ.get("CLOSURE_KEEP"):
        shutil.rmtree(work, ignore_errors=True)
    return rec


# --- the corpus -------------------------------------------------------------------------------------------------------
def _signature(spec):
    """What makes a tree different from its siblings: mode, scenes, platform, sensor, atmosphere, motion kind, window."""
    from manifold.core.run_spec import load_run_spec
    doc = load_run_spec(ROOT / spec)
    eng = doc.get("engine") or {}
    if (eng.get("mode") or "") == "passthrough":
        return ("passthrough", spec)
    atm = eng.get("atmosphere") or {}
    sensor = (((doc.get("descriptor") or {}).get("sensor") or {}).get("ref") or {}).get("name")
    return ("layered", tuple(s["ref"]["name"] for s in eng.get("scenes") or []),
            ((eng.get("platform") or {}).get("ref") or {}).get("name"), sensor,
            atm.get("plugin"), tuple(sorted(k for k in atm if k != "plugin")),
            (eng.get("motion") or {}).get("kind"), "w64" if spec.endswith("-w64.yaml") else "full")


def order(specs):
    """Breadth first: one spec per signature (the shortest name first), then the rest round by round over the
    signatures, a round taking the 64 x 64 windows' specs before the full-size ones (a full-size s2s render takes
    minutes, a 64 x 64 one seconds)."""
    groups = {}
    for spec in specs:
        groups.setdefault(_signature(spec), []).append(spec)
    for g in groups.values():
        g.sort(key=lambda s: (len(s), s))
    out = [g[0] for g in groups.values()]
    rest = [g[1:] for g in groups.values()]
    cheap = [g for sig, g in zip(groups, rest) if sig[-1] == "w64"]
    dear = [g for sig, g in zip(groups, rest) if sig[-1] != "w64"]
    for gs in (cheap, dear):
        depth = 0
        while any(len(g) > depth for g in gs):
            out += [g[depth] for g in gs if len(g) > depth]
            depth += 1
    return out


def load():
    return [json.loads(line) for line in RECORDS.read_text().splitlines() if line.strip()] if RECORDS.is_file() else []


def corpus(work, threads, stop_at, timeout, only=None):
    done = {r["spec"] for r in load()}
    todo = [s for s in order(cw.specs()) if s not in done]
    if only:
        todo = todo[:only]
    for spec in todo:
        if time.time() >= stop_at:
            print("stop time reached", flush=True)
            break
        t0 = time.time()
        proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "one", spec, "--work", str(work),
                                 "--threads", str(threads)], stdout=subprocess.PIPE, text=True,
                                start_new_session=True)
        try:
            text, _ = proc.communicate(timeout=min(timeout, max(1, stop_at - time.time() + 60)))
            rec = json.loads(text.strip().splitlines()[-1]) if proc.returncode == 0 and text.strip() else \
                {"spec": spec, "ran": False, "error": f"closure_trace one exited {proc.returncode}"}
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            shutil.rmtree(work, ignore_errors=True)
            rec = {"spec": spec, "ran": False, "error": f"timed out after {round(time.time() - t0)} s",
                   "seconds": round(time.time() - t0, 1)}
        with RECORDS.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"{spec} ran={rec.get('ran')} {rec.get('seconds')}s set1={len(rec.get('listed_not_in_job', []))} "
              f"set2={len(rec.get('in_job_not_listed', []))} set3={len(rec.get('read_in_neither', []))} "
              f"unread={len(rec.get('listed_not_read', []))}", flush=True)


# --- the table --------------------------------------------------------------------------------------------------------
def _short(spec):
    return spec.rsplit("/", 1)[-1].removesuffix(".yaml")


def table(records):
    traced = [r for r in records if "walked" in r]
    lines = ["| Tree | Mode | Ran | Walked | Job | Listed, not in job | In job, not listed | Read, in neither "
             "(generated) | Listed, never opened |", "|---|---|---|---|---|---|---|---|---|"]
    for r in traced:
        lines.append(f"| `{_short(r['spec'])}` | {r['mode']} | {'yes' if r['ran'] else 'no'} | {r['walked']} | "
                     f"{r['job']} | {len(r['listed_not_in_job'])} | {len(r['in_job_not_listed'])} | "
                     f"{len(r['read_in_neither'])} ({len(r['generated'])}) | {len(r['listed_not_read'])} |")
    for r in records:
        if "walked" not in r:
            lines.append(f"| `{_short(r['spec'])}` | {r.get('mode', '')} | no: {r.get('error')} | | | | | | |")
    specs = cw.specs()
    lines += ["", f"Trees traced: {len(traced)} of {len(specs)} DIRSIG specs ({sum(1 for r in traced if r['ran'])} "
              f"ran to completion); not traced: {len(specs) - len(records)} (time) and "
              f"{len(records) - len(traced)} (failed before a tool started)."]
    return "\n".join(lines)


def summary(records):
    """Counts over the traced trees, for the verdict."""
    traced = [r for r in records if "walked" in r and r["ran"]]
    c = Counter()
    for key in ("listed_not_in_job", "in_job_not_listed", "read_in_neither", "generated", "listed_not_read",
                "library_written", "install_listed_not_read"):
        c[key] = sum(len(r[key]) for r in traced)
    return {"trees": len(traced), **c}


def write_doc(records):
    text = DOC.read_text()
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    DOC.write_text(f"{head}{BEGIN}\n{table(records)}\n{END}{tail}")


def main(argv=None):
    if argv is None and sys.argv[1:2] == ["pre"]:
        return pre()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", choices=["one", "corpus"])
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--work", type=Path)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--stop-at", type=float, help="epoch seconds after which no tree is started")
    ap.add_argument("--timeout", type=float, default=1800, help="seconds per tree")
    ap.add_argument("--only", type=int, help="at most this many trees")
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--write-doc", action="store_true")
    args = ap.parse_args(argv)
    if args.table:
        print(table(load()))
        return 0
    if args.write_doc:
        write_doc(load())
        return 0
    if args.work is None:
        ap.error("--work is required")
    work = args.work.resolve()
    if work == ROOT or ROOT in work.parents:
        ap.error("--work must be outside the repository")
    if args.command == "one":
        print(json.dumps(run_one(args.spec, work / "tree", args.threads)))
        return 0
    if args.command == "corpus":
        corpus(work / "tree", args.threads, args.stop_at or float("inf"), args.timeout, args.only)
        return 0
    ap.error("one, corpus, --table or --write-doc")


if __name__ == "__main__":
    sys.exit(main())
