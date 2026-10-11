#!/usr/bin/env python3
"""Run a DIRSIG demo's committed pass-through recipe through `Workspace` and measure it (a reference run).

    python scripts/run_demo.py Brdf1 [--timeout SECONDS] [--work DIR] [--repeat] [--report docs/DIRSIG_demo_reference_runs.md]

`<name>` is a demo name (`Brdf1` runs the recipe `demo_brdf1_passthrough`) or a recipe name. The run is submitted to a
`Workspace.local` over the work root `--work` (default: a fresh folder under the state directory's
`protodirsig/reference-runs/`), waited for up to `--timeout` seconds (default 1200), and measured: wall time, every output
file's name, size and sha256, the run directory's size, the engine's exit status and version. A run that fails or times
out is a result: the failure, the worker log's tail and the cost so far are recorded, and a timed-out run is cancelled.
`--repeat` runs the demo a second time in a second fresh work root when the first run took under 5 minutes, and records
whether every output digest is identical (resubmitting in the same work root returns the same run and tests nothing).

The repository is never written, except `--report`: a markdown report whose generated part (between the
`run_demo` markers, with the recorded runs kept as a JSON comment so running another demo keeps the earlier rows) is
rewritten and whose hand-written sections are kept verbatim. Only names, sizes and digests are written; no output byte.

`--library`, `--config-repo` and `--engine` override the repository's layer root, engine-asset library and the located
`dirsig5` (the tests use a stub engine).
"""
import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protodirsig import Workspace                                 # noqa: E402
from protodirsig.backend import LocalBackend                       # noqa: E402
from protodirsig.errors import ProblemError                        # noqa: E402
from protodirsig.workspace import default_work_root               # noqa: E402

BEGIN = "<!-- run_demo: generated between these markers by scripts/run_demo.py; edit outside them -->"
END = "<!-- run_demo: end -->"
DATA = re.compile(r"<!-- run_demo data: (.*?) -->", re.S)
REPEAT_UNDER_S = 300
TAIL_LINES = 20


def recipe_for(name, library):
    """The recipe a demo name or recipe name means."""
    if (Path(library) / "recipes" / f"{name}.yaml").is_file():
        return name
    return f"demo_{name.lower()}_passthrough"


def _dir_size(path):
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file() and not p.is_symlink())


def _tail(path, n=TAIL_LINES):
    try:
        return Path(path).read_text(errors="replace").splitlines()[-n:]
    except OSError:
        return []


def run_once(name, work, timeout, library=None, config_repo=None, engine=None):
    """Submit, wait, measure. Returns a record (never raises for a failed or timed-out run)."""
    kwargs = {"work": work}
    if library is not None:
        kwargs["library"] = library
    if config_repo is not None:
        kwargs["config_repo"] = config_repo
    ws = Workspace.local(**kwargs)
    if engine is not None:
        ws = Workspace(LocalBackend(Path(work), ws.backend.config_repo, library=ws.backend.library.root,
                                    sensor_library=ws.backend.library.sensor_library, engine=engine))
    recipe = recipe_for(name, ws.backend.library.root)
    rec = {"demo": name, "recipe": recipe, "work_root": str(work), "started_at":
           datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}
    t0 = time.monotonic()
    try:
        status = ws.submit_run(recipe)
    except ProblemError as e:
        rec.update(state="not admitted", error=e.problem.get("detail"), wall_s=round(time.monotonic() - t0, 1))
        return rec
    rec["run_id"] = status.run_id
    try:
        final = ws.wait(status.run_id, timeout=timeout, poll=1.0)
        rec["state"] = final.state
    except TimeoutError:
        ws.cancel_run(status.run_id)
        final = ws.get_run(status.run_id)
        rec["state"] = f"timed out after {timeout} s (cancelled)"
    rec["wall_s"] = round(time.monotonic() - t0, 1)
    store = ws.backend.store
    run_dir = store.run_dir(status.run_id)
    record = store.read_record(status.run_id)
    rec["engine_exit_status"] = record.get("engine_exit_status")
    rec["engine_version"] = (record.get("engine") or {}).get("version")
    rec["run_dir_bytes"] = _dir_size(run_dir)
    rec["outputs"] = [{"name": a.name, "size": Path(a.uri.removeprefix("file://")).stat().st_size, "sha256": a.sha256}
                      for a in final.artifacts if a.name != "run_spec.json"]
    if final.state != "rendered":
        rec["errors"] = [e.get("detail") if isinstance(e, dict) else getattr(e, "detail", str(e)) for e in final.errors]
        rec["worker_log_tail"] = _tail(run_dir / "worker.log")
    return rec


def fresh_work(base, name, tag):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = Path(base) / f"{name}-{stamp}-{tag}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def measure(name, timeout=1200, work=None, repeat=False, library=None, config_repo=None, engine=None):
    """The reference-run record of one demo: the first run, and the repeat when asked and the first took < 5 min."""
    base = Path(work) if work is not None else default_work_root().parent / "reference-runs"
    first = run_once(name, fresh_work(base, name, "1"), timeout, library, config_repo, engine)
    result = {"demo": name, "first": first, "deterministic": "not tested"}
    if repeat and first.get("state") == "rendered" and first["wall_s"] < REPEAT_UNDER_S:
        second = run_once(name, fresh_work(base, name, "2"), timeout, library, config_repo, engine)
        result["second"] = second
        if second.get("state") == "rendered":
            a = {o["name"]: o["sha256"] for o in first["outputs"]}
            b = {o["name"]: o["sha256"] for o in second["outputs"]}
            result["deterministic"] = "yes" if a == b else "no"
            result["differing"] = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
    return result


# --- the report -----------------------------------------------------------------------------------------------------

def _mb(n):
    return f"{n / 1e6:.2f}" if isinstance(n, (int, float)) else "-"


def render_generated(results):
    lines = [BEGIN, "", "## Measurements", "",
             "| Demo | Recipe | State | Wall time (s) | Outputs | Run directory (MB) | Deterministic | Engine exit | DIRSIG version |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name in sorted(results):
        r = results[name]
        f = r["first"]
        lines.append(f"| {name} | `{f.get('recipe')}` | {f.get('state')} | {f.get('wall_s', '-')} | "
                     f"{len(f.get('outputs', []))} | {_mb(f.get('run_dir_bytes'))} | {r.get('deterministic')} | "
                     f"{f.get('engine_exit_status', '-')} | {f.get('engine_version') or '-'} |")
    for name in sorted(results):
        r = results[name]
        f = r["first"]
        lines += ["", f"### {name}: outputs", "",
                  f"Run id `{f.get('run_id', '-')}`, started {f.get('started_at')}, work root outside the repository. "
                  + (f"Second run in a fresh work root: {r['second'].get('state')}, {r['second'].get('wall_s')} s; "
                     f"deterministic: {r['deterministic']}" + (f" (differing: {', '.join(r['differing'])})"
                                                                 if r.get("differing") else "") + "."
                     if "second" in r else f"Determinism: {r['deterministic']}."), ""]
        if f.get("outputs"):
            lines += ["| File | Bytes | sha256 |", "|---|---|---|"]
            lines += [f"| {o['name']} | {o['size']} | `{o['sha256']}` |" for o in f["outputs"]]
        if f.get("errors") or f.get("error"):
            lines += ["", "Failure: " + "; ".join(x for x in (f.get("errors") or [f.get("error")]) if x)]
        if f.get("worker_log_tail"):
            lines += ["", "Worker log tail:", "", "```", *f["worker_log_tail"], "```"]
    data = json.dumps(results, sort_keys=True, separators=(",", ":"))
    lines += ["", f"<!-- run_demo data: {data} -->", "", END]
    return "\n".join(lines)


def write_report(path, result):
    """Merge one demo's result into the report: the generated part is rewritten from every recorded result, the rest
    of the file is kept verbatim (a new file gets a title)."""
    path = Path(path)
    text = path.read_text() if path.is_file() else "# DIRSIG demo reference runs\n\n" + BEGIN + "\n" + END + "\n"
    if BEGIN not in text or END not in text:
        text = text.rstrip("\n") + "\n\n" + BEGIN + "\n" + END + "\n"
    head, rest = text.split(BEGIN, 1)
    middle, tail = rest.split(END, 1)
    m = DATA.search(middle)
    results = json.loads(m.group(1)) if m else {}
    results[result["demo"]] = result
    path.write_text(head + render_generated(results) + tail)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("name", help="a demo name (Brdf1) or a pass-through recipe name")
    ap.add_argument("--timeout", type=float, default=1200.0, help="seconds to wait for the run (default 1200)")
    ap.add_argument("--work", default=None, help="the folder fresh work roots are made in (outside the repository)")
    ap.add_argument("--repeat", action="store_true", help="run again in a fresh work root if the first took < 5 min")
    ap.add_argument("--report", default=None, help="the markdown report to update")
    ap.add_argument("--library", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--config-repo", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--engine", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.timeout <= 0:
        ap.error("--timeout must be positive")
    if a.work is not None and Path(a.work).resolve().is_relative_to(ROOT):
        ap.error("--work must be outside the repository")
    result = measure(a.name, a.timeout, a.work, a.repeat, a.library, a.config_repo, a.engine)
    print(json.dumps(result, indent=1))
    if a.report:
        print(f"updated {write_report(a.report, result)}")
    return 0 if result["first"].get("state") == "rendered" else 1


if __name__ == "__main__":
    sys.exit(main())
