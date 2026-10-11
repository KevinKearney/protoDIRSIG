#!/usr/bin/env python3
"""Run every DIRSIG 5 demo in the installation through the pass-through form once, unattended, and record each outcome.

    python scripts/sweep_demos.py [--budget-hours 14.5 | --deadline 2026-10-11T12:42:13-04:00] [--per-run-timeout 1800]
                                  [--work DIR] [--disk-floor-gb 20] [--resume] [--only A,B] [--skip C,D]
                                  [--report docs/DIRSIG_demo_sweep.md]

A standalone process (it does not need the session that started it). Candidates are every `<Name>.zip` in
`$DIRSIG_HOME/demos/zips` and every unpacked demo directory under `$DIRSIG_HOME/demos` or `$DIRSIG_HOME/demos/zips`
(one candidate per name; the zip is the source when both exist), ordered by total uncompressed size, smallest first. A
name holding a space or a parenthesis is recorded `skipped: duplicate name`; `MoonSat1`, `Ssa2` and `Ssa3` are recorded
`skipped: dirsig4` (flagged DIRSIG 4 only by the online demo page, which the user read). `--only` and `--skip` filter.

Per demo: the directory is extracted into `manifold_config_repo/demo_dirs/<Name>/` unless already placed (a demo is
skipped `skipped: disk` when the free space is below the floor plus three times its uncompressed size) and hashed with
`dirhash/1`; the simulation files are tried in turn (`simulation_plan`), each attempt an ad hoc pass-through run spec
submitted through `Workspace` in a fresh work root, with no engine check, waited for up to the smaller of
`--per-run-timeout` and the time left to the deadline minus 5 minutes (a timed-out run is cancelled), stopping at the
first that renders. An attempt that rendered in under 300 s is repeated once in a second fresh work root and its output
digests compared. Then the attempt work roots and, unless it is a committed asset or was placed before the sweep, the
extracted directory are deleted (`safe_delete` refuses any path outside the sweep work root and the demo directories the
sweep extracted). Each attempt records the demo, simulation file, outcome (`rendered`, `failed`, `timeout`,
`interrupted`), engine exit status, wall time, outputs (name, size, sha256), run-directory size, minimum free disk,
maximum CPU temperature (the worker's and the driver's own samples) and `throttle_suspect`, the per-run cache state,
the tool versions, and for a failure the first `worker.log` line matching `FIRST_ERROR` and the last 20 lines.

Budget: no attempt starts when the time left is less than the longest completed attempt or 10 minutes, whichever is
larger; a render is stopped only by its capped timeout. SIGTERM cancels the current render, records it `interrupted`,
writes the report and exits. State lives in `<work>/sweep/`: `results.jsonl` (one `attempt` line per attempt, one `demo`
line per finished demo; not committed), `heartbeat` (rewritten at least once a minute), `state.json` (the deadline;
`--resume` keeps it and skips finished demos). The report (`--report`) is rewritten between markers after every demo,
keeping hand-written text; it holds names, sizes, digests, measurements and DIRSIG error lines, no demo bytes.

`--dirsig-home`, `--config-repo`, `--library` and `--engine` override the installation, the engine-asset library, the
layer root and the engine (tests: synthetic zips and a stub engine).
"""
import argparse
import json
import os
import re
import shutil
import signal
import stat
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protodirsig.dirhash import directory_digest                  # noqa: E402
from protodirsig.passthrough import THROTTLE_SUSPECT_C, max_zone_temp_c   # noqa: E402

DIRSIG4 = ("MoonSat1", "Ssa2", "Ssa3")
DIRSIG4_NOTE = "flagged DIRSIG 4 only by the online demo page, which the user read"
FIRST_ERROR = re.compile(r"error|exception|does not exist|cannot|failed|missing", re.IGNORECASE)
REPEAT_UNDER_S = 300
MIN_LEFT_S = 600
DEADLINE_MARGIN_S = 300
MAX_FALLBACK_SIMS = 4
TAIL_LINES = 20
HEARTBEAT_S = 30
POLL_S = 2.0
BEGIN = "<!-- sweep_demos: generated between these markers by scripts/sweep_demos.py; edit outside them -->"
END = "<!-- sweep_demos: end -->"
REPORT = ROOT / "docs" / "DIRSIG_demo_sweep.md"


class DeleteScopeError(RuntimeError):
    """A delete outside the sweep's allowed prefixes, refused before anything is removed."""


def utc_now(clock=time.time):
    return datetime.fromtimestamp(clock(), timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# --- candidates and the simulation-file rule ------------------------------------------------------------------------

def _dir_size(path):
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file() and not p.is_symlink())


def _zip_members(zf, name):
    """The members of demo `name` in its zip: files under `<name>/`, without macOS resource forks."""
    return [i for i in zf.infolist() if i.filename.startswith(f"{name}/") and not i.is_dir()
            and "__MACOSX" not in i.filename.split("/") and not PurePosixPath(i.filename).name.startswith("._")]


def candidates(dirsig_home, only=None, skip=()):
    """`(runnable, skipped)`: runnable `{name, source, path, size}` sorted by size then name; skipped
    `{name, outcome, note}` records, sorted by name."""
    demos = Path(dirsig_home) / "demos"
    zips = demos / "zips"
    found = {}
    for z in sorted(zips.glob("*.zip")) if zips.is_dir() else []:
        found.setdefault(z.stem, {"name": z.stem, "source": "zip", "path": str(z)})
    for folder in (demos, zips):
        for d in sorted(p for p in folder.iterdir() if p.is_dir()) if folder.is_dir() else []:
            if folder == demos and d.name in ("zips", "thumbnails"):
                continue
            found.setdefault(d.name, {"name": d.name, "source": "directory", "path": str(d)})
    runnable, skipped = [], []
    for name, c in sorted(found.items()):
        if only and name not in only:
            continue
        if name in skip:
            skipped.append({"name": name, "outcome": "skipped: --skip", "note": "named in --skip"})
        elif " " in name or "(" in name or ")" in name:
            skipped.append({"name": name, "outcome": "skipped: duplicate name",
                            "note": "the name holds a space or a parenthesis (a copy of another demo)"})
        elif name in DIRSIG4:
            skipped.append({"name": name, "outcome": "skipped: dirsig4", "note": DIRSIG4_NOTE})
        else:
            if c["source"] == "zip":
                with zipfile.ZipFile(c["path"]) as zf:
                    c["size"] = sum(i.file_size for i in _zip_members(zf, name))
            else:
                c["size"] = _dir_size(c["path"])
            runnable.append(c)
    runnable.sort(key=lambda c: (c["size"], c["name"]))
    return runnable, skipped


def simulation_plan(directory):
    """The simulation files to try, in order, stopping at the first that renders: `demo.sim` if present, then
    `demo.jsim` if present; with neither, every top-level `.sim` and `.jsim` file in alphabetical order, at most 4."""
    d = Path(directory)
    named = [n for n in ("demo.sim", "demo.jsim") if (d / n).is_file()]
    if named:
        return named
    return sorted(p.name for p in d.iterdir() if p.is_file() and p.suffix in (".sim", ".jsim"))[:MAX_FALLBACK_SIMS]


# --- extraction and deletion ----------------------------------------------------------------------------------------

def extract(candidate, target):
    """Place a candidate's files at `target` (from its zip, or copied from its directory). Raises ValueError for a
    member that would escape the target or is a symbolic link."""
    target = Path(target)
    staging = target.with_name(f".{target.name}.extracting")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    if candidate["source"] == "zip":
        with zipfile.ZipFile(candidate["path"]) as zf:
            for info in _zip_members(zf, candidate["name"]):
                rel = PurePosixPath(info.filename[len(candidate["name"]) + 1:])
                if rel.is_absolute() or ".." in rel.parts:
                    raise ValueError(f"member {info.filename!r} escapes the demo directory")
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError(f"member {info.filename!r} is a symbolic link")
                dest = staging / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
    else:
        shutil.rmtree(staging)
        shutil.copytree(candidate["path"], staging, symlinks=True)
    os.replace(staging, target)
    return target


def safe_delete(path, allowed, protected=()):
    """Remove `path` (a file or a tree) only if it lies strictly inside one of `allowed` and inside none of
    `protected`; otherwise raise DeleteScopeError before removing anything."""
    p = Path(path).resolve()
    if not any(p != Path(a).resolve() and p.is_relative_to(Path(a).resolve()) for a in allowed):
        raise DeleteScopeError(f"refusing to delete {p}: not inside {[str(a) for a in allowed]}")
    if any(p == Path(q).resolve() or p.is_relative_to(Path(q).resolve()) for q in protected):
        raise DeleteScopeError(f"refusing to delete {p}: a protected path")
    if p.is_dir():
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()


# --- budget, errors, determinism ------------------------------------------------------------------------------------

def attempt_timeout(per_run_timeout, now, deadline):
    """The attempt's timeout: the smaller of the per-run timeout and the time left to the deadline minus 5 minutes."""
    return min(per_run_timeout, deadline - now - DEADLINE_MARGIN_S)


def may_start(now, deadline, longest_s):
    """Whether a new attempt may start: the time left is at least the longest completed attempt and 10 minutes."""
    return deadline - now >= max(longest_s or 0, MIN_LEFT_S)


def first_error_line(lines):
    """The first line matching FIRST_ERROR (stripped), or None."""
    return next((ln.strip() for ln in lines if FIRST_ERROR.search(ln)), None)


def compare_outputs(a, b):
    """`("yes" | "no", differing names)`: whether two attempts' outputs have the same names and digests."""
    da = {o["name"]: o["sha256"] for o in a}
    db = {o["name"]: o["sha256"] for o in b}
    differing = sorted(k for k in da.keys() | db.keys() if da.get(k) != db.get(k))
    return ("no" if differing else "yes"), differing


# --- one attempt ----------------------------------------------------------------------------------------------------

def passthrough_spec(name, directory_ref, digest, simulation, template):
    """An ad hoc pass-through run spec for a demo: the template's descriptor and generator, the demo's directory."""
    spec = json.loads(json.dumps(template))
    meta = spec["descriptor"]["meta"]
    meta["name"] = f"sweep-{name.lower()}-{Path(simulation).stem.lower()}"
    meta["tags"] = ["dirsig-demo", name.lower(), "passthrough", "sweep"]
    meta["description"] = f"DIRSIG demo {name} ({simulation}) run as authored by scripts/sweep_demos.py.\n"
    spec["engine"]["passthrough"] = {"directory": {"name": directory_ref, "content_hash": digest},
                                     "simulation": simulation}
    spec["engine"].pop("run", None)
    return spec


def _template():
    import yaml
    return yaml.safe_load((ROOT / "manifold_run_specs" / "demo_pointcollectors2_passthrough.yaml").read_text())


def _tail(path, n=TAIL_LINES):
    try:
        return Path(path).read_text(errors="replace").splitlines()[-n:]
    except OSError:
        return []


class Sweep:
    """The sweep's state and loop. `clock`, `free_bytes`, `temp` and `workspace_factory` are injectable for tests."""

    def __init__(self, work, deadline, per_run_timeout=1800, disk_floor_gb=20.0, dirsig_home=None, config_repo=None,
                 library=None, engine=None, report=REPORT, clock=time.time, sleep=time.sleep, free_bytes=None,
                 temp=max_zone_temp_c, out=print):
        self.work = Path(work).resolve()
        self.sweep_dir = self.work / "sweep"
        self.sweep_dir.mkdir(parents=True, exist_ok=True)
        self.deadline = float(deadline)
        self.per_run_timeout = float(per_run_timeout)
        self.floor = float(disk_floor_gb) * 1e9
        self.dirsig_home = Path(dirsig_home) if dirsig_home else _dirsig_home()
        self.config_repo = Path(config_repo).resolve() if config_repo else ROOT / "manifold_config_repo"
        self.demo_dirs = self.config_repo / "demo_dirs"
        self.library = library
        self.engine = engine
        self.report = Path(report) if report else None
        self.clock, self.sleep, self.temp, self.out = clock, sleep, temp, out
        self.free_bytes = free_bytes or (lambda: shutil.disk_usage(self.work).free)
        self.results = self.sweep_dir / "results.jsonl"
        self.protected = {self.demo_dirs / Path(e["path"]).name for e in _manifest_dirs(self.config_repo)}
        self.longest = 0.0
        self.stop = False
        self.current = {}
        self._beat = 0.0

    # state ---------------------------------------------------------------------------------------------------------
    def append(self, record):
        with open(self.results, "a") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    def records(self):
        return read_results(self.results)

    def finished(self):
        return {r["demo"] for r in self.records() if r.get("type") == "demo" and not r.get("interrupted")}

    def heartbeat(self, force=False):
        now = self.clock()
        if not force and now - self._beat < HEARTBEAT_S:
            return
        self._beat = now
        left = self.deadline - now
        text = (f"{utc_now(self.clock)} demo={self.current.get('demo', '-')} "
                f"attempt={self.current.get('simulation', '-')} index={self.current.get('index', '-')} "
                f"time_left_s={int(left)} stop={self.stop}\n")
        tmp = self.sweep_dir / "heartbeat.tmp"
        tmp.write_text(text)
        os.replace(tmp, self.sweep_dir / "heartbeat")

    def write_report(self):
        if self.report is not None:
            write_report(self.report, self.records(), self.state())

    def state(self):
        try:
            return json.loads((self.sweep_dir / "state.json").read_text())
        except (OSError, ValueError):
            return {}

    # the loop ------------------------------------------------------------------------------------------------------
    def run(self, only=None, skip=()):
        runnable, skipped = candidates(self.dirsig_home, only, skip)
        done = self.finished()
        for s in skipped:
            if s["name"] not in done:
                self.append({"type": "demo", "demo": s["name"], "outcome": s["outcome"], "note": s["note"],
                             "attempts": [], "recorded_at": utc_now(self.clock)})
        for r in self.records():
            if r.get("type") == "attempt" and isinstance(r.get("wall_s"), (int, float)):
                self.longest = max(self.longest, r["wall_s"])
        index = 0
        for c in runnable:
            index += 1
            if self.stop:
                break
            if c["name"] in done:
                continue
            self.current = {"demo": c["name"], "index": f"{index}/{len(runnable)}"}
            self.heartbeat(force=True)
            if not may_start(self.clock(), self.deadline, self.longest):
                self.out(f"budget: stopping before {c['name']} ({int(self.deadline - self.clock())} s left)")
                self.append({"type": "stop", "reason": "budget", "before": c["name"], "recorded_at": utc_now(self.clock),
                             "time_left_s": int(self.deadline - self.clock()), "longest_attempt_s": self.longest})
                break
            self.demo(c)
            self.write_report()
        else:
            if not self.stop:
                self.append({"type": "stop", "reason": "candidates exhausted", "recorded_at": utc_now(self.clock)})
        if self.stop:
            self.append({"type": "stop", "reason": "SIGTERM", "recorded_at": utc_now(self.clock)})
        self.current = {}
        self.heartbeat(force=True)
        self.write_report()

    def demo(self, c):
        name = c["name"]
        target = self.demo_dirs / name
        rec = {"type": "demo", "demo": name, "source": c["source"], "uncompressed_bytes": c["size"], "attempts": []}
        placed_before = target.is_dir()
        free = self.free_bytes()
        if not placed_before and free < self.floor + 3 * c["size"]:
            rec.update(outcome="skipped: disk", note=f"{free} bytes free, below the floor plus three times the size")
            self.append({**rec, "recorded_at": utc_now(self.clock)})
            return rec
        try:
            if not placed_before:
                extract(c, target)
            digest = directory_digest(target)
        except (ValueError, OSError, zipfile.BadZipFile) as e:
            rec.update(outcome="skipped: not placeable", note=f"{type(e).__name__}: {e}")
            if not placed_before and target.exists():
                self._delete(target)
            self.append({**rec, "recorded_at": utc_now(self.clock)})
            return rec
        rec["digest"] = digest
        rec["placed_before_sweep"] = placed_before
        plan = simulation_plan(target)
        if not plan:
            rec.update(outcome="skipped: no simulation file", note="no .sim or .jsim file at the top of the directory")
        for sim in plan:
            if self.stop or not may_start(self.clock(), self.deadline, self.longest):
                if not rec["attempts"]:
                    rec.update(outcome="skipped: budget")
                break
            self.current.update(simulation=sim)
            att = self.attempt(name, digest, sim)
            rec["attempts"].append(att)
            if att["outcome"] == "rendered":
                if att["wall_s"] < REPEAT_UNDER_S and not self.stop and \
                        may_start(self.clock(), self.deadline, self.longest):
                    rep = self.attempt(name, digest, sim, repeat=True)
                    att["repeat_run"] = {k: rep.get(k) for k in ("outcome", "wall_s", "outputs", "max_cpu_temp_c",
                                                              "throttle_suspect")}
                    if rep["outcome"] == "rendered":
                        att["deterministic"], att["differing"] = compare_outputs(att["outputs"], rep["outputs"])
                    else:
                        att["deterministic"] = f"repeat {rep['outcome']}"
                else:
                    att["deterministic"] = "not tested"
                break
            if att["outcome"] == "interrupted":
                break
        if rec["attempts"]:
            last = rec["attempts"][-1]
            rec["outcome"] = last["outcome"]
            rec["simulation"] = last["simulation"]
        rec["interrupted"] = any(a["outcome"] == "interrupted" for a in rec["attempts"])
        if not placed_before:
            self._delete(target)
        self.append({**rec, "recorded_at": utc_now(self.clock)})
        return rec

    def _delete(self, path):
        safe_delete(path, allowed=[self.work, self.demo_dirs], protected=self.protected)

    def _workspace(self, work):
        from protodirsig import Workspace
        from protodirsig.backend import LocalBackend
        kwargs = {"work": work, "config_repo": self.config_repo}
        if self.library is not None:
            kwargs["library"] = self.library
        ws = Workspace.local(**kwargs)
        if self.engine is not None:
            ws = Workspace(LocalBackend(Path(work), self.config_repo, library=ws.backend.library.root,
                                        sensor_library=ws.backend.library.sensor_library, engine=self.engine))
        return ws

    def attempt(self, name, digest, simulation, repeat=False):
        from protodirsig.errors import ProblemError
        tag = "repeat" if repeat else "first"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        work = self.work / "runs" / f"{name}-{Path(simulation).stem}-{tag}-{stamp}"
        work.mkdir(parents=True)
        timeout = attempt_timeout(self.per_run_timeout, self.clock(), self.deadline)
        att = {"type": "attempt", "demo": name, "simulation": simulation, "repeat": repeat,
               "started_at": utc_now(self.clock), "timeout_s": round(timeout, 1)}
        self.out(f"{att['started_at']} {name} {simulation} ({tag}, timeout {int(timeout)} s)")
        min_free = self.free_bytes()
        hot = self.temp()
        t0 = self.clock()
        ws = None
        try:
            ws = self._workspace(work)
            spec = passthrough_spec(name, f"demo_dirs/{name}", digest, simulation, _template())
            run_id = ws.submit_run(spec).run_id
            att["run_id"] = run_id
            state = None
            while True:
                status = ws.get_run(run_id)
                state = status.state
                if state in ("rendered", "failed", "cancelled"):
                    break
                if self.stop:
                    ws.cancel_run(run_id)
                    state = "interrupted"
                    break
                if self.clock() - t0 > timeout:
                    ws.cancel_run(run_id)
                    state = "timeout"
                    break
                min_free = min(min_free, self.free_bytes())
                t = self.temp()
                hot = t if hot is None else (max(hot, t) if t is not None else hot)
                self.heartbeat()
                self.sleep(POLL_S)
            att["outcome"] = {"cancelled": "interrupted" if self.stop else "failed"}.get(state, state)
        except ProblemError as e:
            att.update(outcome="failed", not_admitted=True, error=e.problem.get("detail"))
        att["wall_s"] = round(self.clock() - t0, 1)
        min_free = min(min_free, self.free_bytes())
        att["min_free_disk_bytes"] = min_free
        if ws is not None and att.get("run_id"):
            store = ws.backend.store
            run_dir = store.run_dir(att["run_id"])
            rec = store.read_record(att["run_id"])
            final = store.read_status(att["run_id"], reap=False)
            worker_hot = rec.get("max_cpu_temp_c")
            if worker_hot is not None:
                hot = worker_hot if hot is None else max(hot, worker_hot)
            att.update(engine_exit_status=rec.get("engine_exit_status"),
                       dirsig_version=(rec.get("engine") or {}).get("version"),
                       scene2hdf_version=(rec.get("scene2hdf") or {}).get("version"),
                       scene_compile=rec.get("scene_compile"), cache=rec.get("cache"),
                       run_dir_bytes=_dir_size(run_dir))
            att["outputs"] = [{"name": a["name"], "size": Path(a["uri"].removeprefix("file://")).stat().st_size,
                               "sha256": a["sha256"]} for a in final.get("artifacts", [])
                              if a["name"] != "run_spec.json"] if att["outcome"] == "rendered" else []
            if att["outcome"] != "rendered":
                lines = Path(run_dir / "worker.log").read_text(errors="replace").splitlines() \
                    if (run_dir / "worker.log").is_file() else []
                att["first_error_line"] = first_error_line(lines)
                att["log_tail"] = lines[-TAIL_LINES:]
                att["errors"] = [e.get("detail") for e in final.get("errors", []) if isinstance(e, dict)]
        else:
            att.setdefault("outputs", [])
        att["max_cpu_temp_c"] = hot
        att["throttle_suspect"] = hot is not None and hot >= THROTTLE_SUSPECT_C
        if att["outcome"] in ("rendered", "failed", "timeout"):
            self.longest = max(self.longest, att["wall_s"])
        self.append({**att, "recorded_at": utc_now(self.clock)})
        try:
            if ws is not None and att.get("run_id"):
                self._wait_worker_gone(ws, att["run_id"])
            self._delete(work)
        except DeleteScopeError:
            raise
        except OSError as e:
            self.out(f"could not delete {work}: {e}")
        return att

    def _wait_worker_gone(self, ws, run_id, limit=30.0):
        """Wait (bounded) until the run's worker process has exited, so its directory is not deleted under it."""
        pid = (ws.backend.store.read_record(run_id).get("worker") or {}).get("pid")
        end = self.clock() + limit
        while pid and self.clock() < end:
            ws.backend._poll_children()
            try:
                os.kill(pid, 0)
            except (ProcessLookupError, PermissionError):
                return
            try:
                if os.waitpid(pid, os.WNOHANG) != (0, 0):
                    return
            except ChildProcessError:
                pass
            self.sleep(0.5)


def _dirsig_home():
    env = os.environ.get("DIRSIG_HOME")
    if env:
        return Path(env)
    return (ROOT / "external" / "dirsig").resolve()


def _manifest_dirs(config_repo):
    try:
        entries = json.loads((Path(config_repo) / "assets.json").read_text()).get("assets", [])
    except (OSError, ValueError):
        return []
    return [e for e in entries if e.get("kind") == "directory" and str(e.get("path", "")).startswith("demo_dirs/")]


def read_results(path):
    out = []
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return out
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue                                   # a line cut by a crash
    return out


# --- the report -----------------------------------------------------------------------------------------------------

def _mb(n):
    return f"{n / 1e6:.2f}" if isinstance(n, (int, float)) else "-"


def _cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ") if text is not None else "-"


def demo_rows(records):
    """The last `demo` record of each demo, by name."""
    rows = {}
    for r in records:
        if r.get("type") == "demo":
            rows[r["demo"]] = r
    return rows


def render_generated(records, state):
    rows = demo_rows(records)
    attempts = [r for r in records if r.get("type") == "attempt"]
    stops = [r for r in records if r.get("type") == "stop"]
    counts = {}
    for r in rows.values():
        counts[r.get("outcome", "-")] = counts.get(r.get("outcome", "-"), 0) + 1
    lines = [BEGIN, "", "## Sweep", "",
             f"Deadline {state.get('deadline_iso', '-')}, per-run timeout {state.get('per_run_timeout', '-')} s, "
             f"disk floor {state.get('disk_floor_gb', '-')} GB, started {state.get('started_at', '-')}. "
             f"{len(rows)} demos recorded, {len(attempts)} attempts (repeats included). "
             + ("Ended: " + stops[-1]["reason"] + "." if stops else "Not ended yet."), "",
             "| Outcome | Demos |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(counts.items())]
    lines += ["", "## Demos", "",
              ("| Demo | Size (MB) | Outcome | Attempts | Wall time (s) | Outputs | Output (MB) | Run directory (MB) | "
               "Deterministic | Max CPU (C) | First error line |"),
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name in sorted(rows):
        r = rows[name]
        atts = r.get("attempts", [])
        last = atts[-1] if atts else {}
        folded = "; ".join(f"{a['simulation']}: {a['outcome']}" for a in atts) or _cell(r.get("note"))
        hot = max((a.get("max_cpu_temp_c") for a in atts if a.get("max_cpu_temp_c") is not None), default=None)
        flag = " (throttle suspect)" if any(a.get("throttle_suspect") for a in atts) else ""
        err = next((a.get("first_error_line") for a in reversed(atts) if a.get("first_error_line")), None)
        out_bytes = sum(o["size"] for o in last.get("outputs", [])) if last.get("outputs") else None
        lines.append(f"| {name} | {_mb(r.get('uncompressed_bytes'))} | {r.get('outcome', '-')} | {_cell(folded)} | "
                     f"{last.get('wall_s', '-')} | {len(last.get('outputs', []))} | {_mb(out_bytes)} | "
                     f"{_mb(last.get('run_dir_bytes'))} | {last.get('deterministic', '-')} | "
                     f"{hot if hot is not None else '-'}{flag} | {_cell(err)} |")
    rendered = [(n, r["attempts"][-1]) for n, r in sorted(rows.items())
                if r.get("outcome") == "rendered" and r.get("attempts")]
    if rendered:
        lines += ["", "## Outputs of rendered demos", ""]
        for n, a in rendered:
            lines += [f"### {n} ({a['simulation']})", "", "| File | Bytes | sha256 |", "|---|---|---|"]
            lines += [f"| {_cell(o['name'])} | {o['size']} | `{o['sha256']}` |" for o in a.get("outputs", [])]
            lines.append("")
    lines += ["", END]
    return "\n".join(lines)


def write_report(path, records, state):
    """Rewrite the generated part of the report from the results; text outside the markers is kept (a new file gets
    a title)."""
    path = Path(path)
    text = path.read_text() if path.is_file() else "# DIRSIG demo sweep\n\n" + BEGIN + "\n" + END + "\n"
    if BEGIN not in text or END not in text:
        text = text.rstrip("\n") + "\n\n" + BEGIN + "\n" + END + "\n"
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(head + render_generated(records, state) + tail)
    os.replace(tmp, path)
    return path


# --- the command line -----------------------------------------------------------------------------------------------

def parse_deadline(text):
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.timestamp()


def _names(text):
    return {n.strip() for n in text.split(",") if n.strip()} if text else set()


def main(argv=None, clock=time.time):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--budget-hours", type=float, default=14.5, help="hours from now (default 14.5)")
    ap.add_argument("--deadline", default=None, help="an absolute ISO 8601 timestamp; overrides --budget-hours")
    ap.add_argument("--per-run-timeout", type=float, default=1800.0, help="seconds per attempt (default 1800)")
    ap.add_argument("--work", default=None, help="the sweep work root, outside the repository")
    ap.add_argument("--disk-floor-gb", type=float, default=20.0, help="free space to keep (default 20)")
    ap.add_argument("--resume", action="store_true", help="skip finished demos and keep the original deadline")
    ap.add_argument("--only", default=None, help="NAME[,NAME...]: only these demos")
    ap.add_argument("--skip", default=None, help="NAME[,NAME...]: skip these demos")
    ap.add_argument("--report", default=str(REPORT), help="the markdown report to rewrite ('' for none)")
    ap.add_argument("--dirsig-home", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--config-repo", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--library", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--engine", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.per_run_timeout <= 0 or a.budget_hours <= 0:
        ap.error("--per-run-timeout and --budget-hours must be positive")
    if a.work is None:
        from protodirsig.workspace import default_work_root
        a.work = str(default_work_root().parent / "sweeps" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    work = Path(a.work).resolve()
    if work.is_relative_to(ROOT):
        ap.error("--work must be outside the repository")
    state_file = work / "sweep" / "state.json"
    state = {}
    if a.resume and state_file.is_file():
        state = json.loads(state_file.read_text())
        deadline = state["deadline"]
    else:
        deadline = parse_deadline(a.deadline) if a.deadline else clock() + a.budget_hours * 3600
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state.update(deadline=deadline, deadline_iso=datetime.fromtimestamp(deadline).astimezone().isoformat(timespec="seconds"),
                 per_run_timeout=a.per_run_timeout, disk_floor_gb=a.disk_floor_gb,
                 started_at=state.get("started_at") or utc_now(clock), pid=os.getpid(),
                 resumed=state.get("resumed", 0) + (1 if a.resume and state else 0))
    state_file.write_text(json.dumps(state, indent=1, sort_keys=True))
    sweep = Sweep(work, deadline, a.per_run_timeout, a.disk_floor_gb, a.dirsig_home, a.config_repo, a.library,
                  a.engine, a.report or None, clock=clock)

    def on_term(signum, frame):
        sweep.stop = True
    signal.signal(signal.SIGTERM, on_term)
    sweep.run(_names(a.only) or None, _names(a.skip))
    print(f"sweep finished: {len(demo_rows(sweep.records()))} demos recorded in {sweep.results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
