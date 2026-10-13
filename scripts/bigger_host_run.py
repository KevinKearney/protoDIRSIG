#!/usr/bin/env python3
"""Run the measurements deferred to a larger host: one manifest, one command, resumable.

    python scripts/bigger_host_run.py [--only NAME[,NAME ...]] [--work DIR] [--max-jobs N] [--max-mem-gb G]
    python scripts/bigger_host_run.py --dry-run [--assume-cores N --assume-mem-gb M] [--only ...]
    python scripts/bigger_host_run.py --check

The manifest (`docs/data/bigger_host_manifest.yaml`, or `--manifest FILE`) lists one entry per deferred measurement
(`docs/Bigger_host_plan.md`): its driver, its items (the jobs), the results file it writes and the figures the plan
uses (`est_s`, the one-thread wall time of an item on the 4-core laptop; `peak_mib`, a job's peak memory where an
earlier round measured it). Entries run one after another, in manifest order; the items of one entry run concurrently.

1. The host: physical cores (unique core ids of /proc/cpuinfo, at most the CPUs this process may use), MemTotal and
   MemAvailable (/proc/meminfo).
2. A job's peak memory, per entry: the figure cached in `<work>/peaks.json`, else the manifest's `peak_mib`, else
   measured by running the entry's smallest instance (`probe`) alone and reading its peak resident set size from
   `wait4` (the job's process tree: the interpreter and the DIRSIG it waits for), then cached.
3. The concurrency of an entry: the minimum of the cores over the threads of one job and the memory budget over the
   memory of one job, where the budget is `MEMORY_FRACTION` (0.75) of MemAvailable and a job counts as
   `JOB_FACTOR` (1.25) times its peak (the safety margin); at least 1, at most `--max-jobs`, and capped by the entry's
   `max_concurrency`. A job that does not fit the budget alone, or needs more threads than the host has, is not run
   (listed as "exceeds host").
4. Each job runs as its own process (`_job`), one thread unless the item states more, with `HOME` set to a folder of
   its own under `<work>/<entry>/` (DIRSIG's caches stay in the job) and `DIRSIG_HOME` set from this process, so the
   installation is found after `HOME` moves.
5. Resume: an item whose result is already in the entry's results file is skipped, and so is an entry whose results are
   all there. Results are written by this process alone, one item at a time as each job ends, with the record schema
   and into the file the earlier rounds use (`docs/data/s2s_results.jsonl` through `scripts/s2s_measure.py`'s
   functions, `docs/data/risk_measurements.jsonl` through `scripts/risk_measure.py`'s); a killed invocation loses only
   the jobs in flight. Events go to `<work>/runner.log` (one JSON object per line).

`--dry-run` prints the plan (items pending and done, threads, memory and its source, concurrency, an estimated wall
time from `est_s`) for this host and, with `--assume-cores N --assume-mem-gb M`, for a host of N physical cores and M GB
of memory (MemAvailable taken as `ASSUMED_AVAILABLE` (0.9) of it); nothing is run or probed. `--check` verifies the
manifest (form, drivers, items, results files, checks named) and that `docs/Bigger_host_plan.md` names every entry.

Drivers: `s2s` (a space-to-space family spec rendered through `Simulation.run(threads=1)` and reduced by
`s2s_measure`), `concurrency` (risk B: N concurrent one-thread copies of one s2s spec), `capture_order` (risk D: a
demo with several captures, as authored, each capture alone and in reverse order, dirsig5 directly), `lightcurve`
(risk E: LightCurve1 rendered at several thread counts, the cube images compared pair by pair), `command` (a
repository script that keeps its own results file in the job folder) and `sleep` (a stub for tests: an item sleeps and
is recorded).
"""
import argparse
import hashlib
import itertools
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "packages" / d / "src") for d in ("core", "sim")]
sys.path.insert(0, str(ROOT / "scripts"))

MANIFEST = ROOT / "docs" / "data" / "bigger_host_manifest.yaml"
PLAN_DOC = ROOT / "docs" / "Bigger_host_plan.md"
SCHEMA = "bigger-host-manifest/1"
MEMORY_FRACTION = 0.75      # of MemAvailable: the memory budget for concurrent jobs
JOB_FACTOR = 1.25           # a job counts as this times its measured peak
ASSUMED_AVAILABLE = 0.9     # an assumed host's MemAvailable, as a fraction of its memory
ENTRY_KEYS = {"name", "driver", "source", "results", "check", "items", "est_s"}


# --- the host -----------------------------------------------------------------------------------------------------

def host_facts():
    """{cores, hardware_threads, mem_total_kib, mem_available_kib, cpu} of this host."""
    usable = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    cores, model = set(), None
    try:
        phys = core = None
        for line in Path("/proc/cpuinfo").read_text().splitlines() + [""]:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k == "physical id":
                phys = v
            elif k == "core id":
                core = v
            elif k == "model name" and model is None:
                model = v
            elif not line.strip():
                if core is not None:
                    cores.add((phys, core))
                phys = core = None
    except OSError:
        pass
    mem = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k, _, v = line.partition(":")
        mem[k] = int(v.split()[0])
    n = min(len(cores), usable) if cores else usable
    return {"cores": n, "hardware_threads": usable, "mem_total_kib": mem["MemTotal"],
            "mem_available_kib": mem["MemAvailable"], "cpu": model or "unknown", "assumed": False}


def assumed_host(cores, mem_gb):
    kib = int(mem_gb * 1e9 / 1024)
    return {"cores": cores, "hardware_threads": cores, "mem_total_kib": kib,
            "mem_available_kib": int(kib * ASSUMED_AVAILABLE), "cpu": "assumed", "assumed": True}


def host_tag(host):
    return f"{host['cores']}c{round(host['mem_total_kib'] * 1024 / 1e9)}g"


# --- manifest -----------------------------------------------------------------------------------------------------

def load_manifest(path=MANIFEST, work=None):
    """The manifest, each entry's results file resolved (`{work}` in it is the work root)."""
    m = yaml.safe_load(Path(path).read_text())
    for e in m.get("entries", []):
        e["_results"] = _path(str(e["results"]).replace("{work}", str(work or default_work())))
    return m


def _path(p):
    p = Path(str(p)).expanduser()
    return p if p.is_absolute() else ROOT / p


def manifest_problems(m, path=MANIFEST):
    p = []
    if not isinstance(m, dict) or m.get("schema") != SCHEMA:
        return [f"schema is not {SCHEMA}"]
    names = [e.get("name") for e in m.get("entries", [])]
    if not names:
        p.append("no entries")
    if len(set(names)) != len(names):
        p.append("entry names repeat")
    for e in m.get("entries", []):
        n = e.get("name")
        missing = ENTRY_KEYS - set(e)
        if missing:
            p.append(f"{n}: missing {sorted(missing)}")
            continue
        if e["driver"] not in DRIVERS:
            p.append(f"{n}: unknown driver {e['driver']!r}")
            continue
        if not (isinstance(e["items"], list) and e["items"]):
            p.append(f"{n}: items is not a non-empty list")
            continue
        est = e["est_s"]
        if not (isinstance(est, (int, float)) or (isinstance(est, dict) and
                                                  all(isinstance(v, (int, float)) for v in est.values()))):
            p.append(f"{n}: est_s is not a number or a mapping of numbers")
        p += [f"{n}: {x}" for x in DRIVERS[e["driver"]].problems(e)]
        if path == MANIFEST:
            script = re.search(r"scripts/(\w+)\.py", e["check"])
            if script and not (ROOT / "scripts" / f"{script.group(1)}.py").is_file():
                p.append(f"{n}: check names a missing script")
            if e["driver"] != "command" and not (ROOT / e["results"]).is_file():
                p.append(f"{n}: results file {e['results']} is not a file of the repository")
    return p


def est_of(entry, item):
    e = entry["est_s"]
    return float(e if isinstance(e, (int, float)) else e.get(str(item), e.get("default", 0.0)))


# --- drivers ------------------------------------------------------------------------------------------------------

class Driver:
    """Items, their state, a job and its record. `job` runs in the job process; the others in the runner."""
    max_concurrency = None

    def problems(self, entry):
        return []

    def items(self, entry, host):
        return [str(i) for i in entry["items"]]

    def threads(self, entry, item, host):
        return int(entry.get("threads", 1))

    def memory_jobs(self, entry, item):
        """How many job peaks one item holds at once."""
        return 1

    def whole_host(self, entry, item):
        """True for an item that runs at DIRSIG's default thread count (it takes every core, so it runs alone)."""
        return False

    def done(self, entry, host):
        return set()

    def complete(self, entry, host):
        return set(self.items(entry, host)) <= self.done(entry, host)

    def probe(self, entry):
        """(item, job arguments) of the entry's smallest instance, or None (no probe: one job at a time)."""
        return None

    def job(self, entry, item, folder, args):
        raise NotImplementedError

    def record(self, entry, item, folder, host):
        """Write the item's result into the results file (the runner calls this after the job ends with 0)."""

    def finish(self, entry, host):
        """Write what follows from all the items (after the last one), if anything."""


def _s2s():
    import s2s_measure
    return s2s_measure


def render_s2s(name, folder, roi=None):
    """Render the committed family spec `name` (its window cut to roi x roi when given) into `folder`, one thread."""
    m = _s2s()
    from manifold.engines.dirsig.simulation import Simulation
    import manifold.sim  # noqa: F401  (registers the engines)
    spec = yaml.safe_load((m.s2s.OUT / f"{name}.yaml").read_text())
    if roi:
        spec["descriptor"]["settings"][0]["roi"] = {"Width": roi, "Height": roi, "OffsetX": None, "OffsetY": None}
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    (folder / "spec.yaml").write_text(yaml.safe_dump(spec, sort_keys=False) if roi else
                                      (m.s2s.OUT / f"{name}.yaml").read_text())
    sim = Simulation(folder / "spec.yaml", m.s2s.LIBRARY, work_dir=folder, sensor_library=m.s2s.SENSORS)
    if sim.resolved is None:
        raise SystemExit(f"{name}: does not resolve: {sim.resolve_error}")
    sim.run(threads=1)


def s2s_product(folder):
    """(image, [truth images], platform) of a rendered s2s job folder."""
    out = folder / "output"
    truth = sorted(i for i in out.glob("*.img") if "truth" in i.name)
    images = [i for i in sorted(out.glob("*.img")) if i not in truth]
    platforms = sorted((folder / "input" / "platforms").rglob("*.platform"))
    if len(images) != 1 or len(platforms) != 1:
        raise SystemExit(f"{folder}: {len(images)} images, {len(platforms)} platforms")
    return images[0], truth, platforms[0]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class S2S(Driver):
    """Family specs of `manifold_run_specs/s2s/`; a record per spec in `s2s_results.jsonl` (`s2s_measure`'s schema).
    `roi: N` cuts the window (tests and this host's check; the record's source says so)."""

    def problems(self, entry):
        idx = _s2s().index()
        return [f"{i} is not a DIRSIG spec of the s2s index" for i in entry["items"] if i not in idx]

    def done(self, entry, host):
        return {r["spec"] for r in _s2s().load_results(entry["_results"])} & set(self.items(entry, host))

    def probe(self, entry):
        return entry.get("probe", entry["items"][0])

    def job(self, entry, item, folder, args):
        render_s2s(item, folder / "run", entry.get("roi"))

    def record(self, entry, item, folder, host):
        m = _s2s()
        run = folder / "run"
        roi = entry.get("roi")
        image, truth, platform = s2s_product(run)
        img = m.read_envi(image, m.header_for(image))[0]
        spec = yaml.safe_load((run / "spec.yaml").read_text())
        s_full = m.full_pixel_signal(platform, spec["descriptor"]["settings"][0]["exposure_time"]["value"])
        idx = m.index()
        ms = m.reduce(idx[item], img, s_full)
        source = m._home_relative(run) + (f" (window cut to {roi} x {roi})" if roi else "")
        rec = {"spec": item, "run_id": idx[item]["run_id"], "family": m.family(idx[item]), "source": source,
               "product": {"image": sha256(image), **{t.name: sha256(t) for t in truth}}, "full_pixel": s_full}
        rec.update(ms[0])
        rec["also"] = ms[1:]
        path = entry["_results"]
        m.write_results([r for r in m.load_results(path) if r["spec"] != item] + [rec], path)


def _risk():
    import risk_measure
    return risk_measure


def _risk_add(entry, records):
    rm = _risk()
    bad = [f"{r['id']}: {x}" for r in records for x in rm.record_problems(r)]
    if bad:
        raise SystemExit("records not written:\n" + "\n".join(bad))
    keep = {(r["risk"], r["id"]): r for r in rm.load_results(entry["_results"])}
    keep.update({(r["risk"], r["id"]): r for r in records})
    rm.write_results(list(keep.values()), entry["_results"])


def _risk_ids(entry):
    return {r["id"] for r in _risk().load_results(entry["_results"]) if r["risk"] == entry["risk"]}


_LOCATED = {}


def located():
    """`locate_dirsig()` once per process (it runs `dirsig5 --version`)."""
    if not _LOCATED:
        from manifold.engines.dirsig.adapter import locate_dirsig
        _LOCATED.update(locate_dirsig())
    return _LOCATED


def _tools():
    from manifold.engines.dirsig.adapter import dirfm_revision
    return {"dirsig": located().get("version") or "unknown", "dirfm": dirfm_revision().get("revision"),
            "runner": "scripts/bigger_host_run.py"}


def _machine(host):
    return {k: host[k] for k in ("cpu", "cores", "hardware_threads", "mem_total_kib")}


class Concurrency(Driver):
    """Risk B: an item `n` is a batch of n concurrent one-thread copies of `spec` (own HOME and folder each); the
    item `cores` is the host's physical core count. A record per batch, then the limit model."""
    max_concurrency = 1

    def items(self, entry, host):
        out = []
        for i in entry["items"]:
            n = host["cores"] if i == "cores" else int(i)
            if f"n{n}" not in out:
                out.append(f"n{n}")
        return sorted(out, key=lambda s: int(s[1:]))

    def problems(self, entry):
        bad = [i for i in entry["items"] if not (i == "cores" or (isinstance(i, int) and i > 0))]
        return ([f"items {bad} are not positive integers or 'cores'"] if bad else []) + \
            ([] if "spec" in entry and "risk" in entry else ["spec and risk are required"])

    def threads(self, entry, item, host):
        return int(item[1:])

    def memory_jobs(self, entry, item):
        return int(item[1:])

    def _id(self, entry, item, host):
        return f"{entry['id_prefix']}-{host_tag(host)}-{item}"

    def done(self, entry, host):
        have = _risk_ids(entry)
        return {i for i in self.items(entry, host) if self._id(entry, i, host) in have}

    def complete(self, entry, host):
        return super().complete(entry, host) and f"{entry['id_prefix']}-{host_tag(host)}-limit-model" in \
            _risk_ids(entry)

    def probe(self, entry):
        return "n1"

    def job(self, entry, item, folder, args):
        n = int(item[1:])
        shutil.rmtree(folder / "batch", ignore_errors=True)
        procs, t0 = {}, time.time()
        for k in range(1, n + 1):
            jf = folder / "batch" / f"job{k}"
            (jf / "home").mkdir(parents=True)
            log = open(jf / "job.log", "w")
            p = subprocess.Popen([sys.executable, __file__, "_render_s2s", entry["spec"], str(jf / "run"),
                                  str(entry.get("roi") or 0)], stdout=log, stderr=subprocess.STDOUT,
                                 env={**os.environ, "HOME": str(jf / "home")})
            procs[p.pid] = (k, jf, time.time())
        jobs = []
        while procs:
            pid, status, ru = os.wait4(-1, 0)
            if pid not in procs:
                continue
            k, jf, start = procs.pop(pid)
            rc = os.waitstatus_to_exitcode(status)
            image = None
            if rc == 0:
                image = sha256(s2s_product(jf / "run")[0])
            jobs.append({"job": k, "rc": rc, "wall_s": round(time.time() - start, 2), "peak_rss_kib": ru.ru_maxrss,
                         "image_sha256": image})
        wall = round(time.time() - t0, 2)
        (folder / "batch.json").write_text(json.dumps({"n": n, "batch_wall_s": wall,
                                                       "jobs": sorted(jobs, key=lambda j: j["job"])}, indent=1))
        if any(j["rc"] for j in jobs):
            raise SystemExit(f"{sum(1 for j in jobs if j['rc'])} of {n} jobs failed")

    def record(self, entry, item, folder, host):
        b = json.loads((folder / "batch.json").read_text())
        ref = None
        for r in _risk().load_results(entry["_results"]):
            if r["risk"] == "B" and r["id"] == self._id(entry, "n1", host):
                ref = r["measured"]["jobs"][0].get("image_sha256")
        if item == "n1":
            ref = b["jobs"][0]["image_sha256"]
        jobs = [{**j, "sha256_equal_single": j["image_sha256"] == ref} for j in b["jobs"]]
        n, wall = b["n"], b["batch_wall_s"]
        roi = entry.get("roi") or 500
        rec = {"risk": "B", "id": self._id(entry, item, host),
               "configuration": {"job": entry["spec"], "form": "layered (Simulation.run, dirfm)", "roi": [roi, roi],
                                 "threads": 1, "seed": 1, "concurrent_copies": n, "home": "one per job",
                                 "work_dir": "one per job", "machine": _machine(host)},
               "method": "scripts/bigger_host_run.py, driver concurrency: N copies started at once, each its own "
                         "process (Simulation.run(threads=1)) with its own HOME and folder; the batch wall time from "
                         "the first start to the last exit; peak RSS from wait4 of each job's process tree; image "
                         "digests against the N = 1 batch.",
               "measured": {"n": n, "jobs": jobs, "batch_wall_s": wall, "throughput_jobs_per_hour": n * 3600.0 / wall,
                            "digests_equal_single": all(j["sha256_equal_single"] for j in jobs),
                            "mean_job_wall_s": round(sum(j["wall_s"] for j in jobs) / n, 2),
                            "failed_jobs": sum(j["rc"] != 0 for j in jobs)},
               "tools": _tools(), "date": date.today().isoformat(), "source": _home_relative(folder)}
        _risk_add(entry, [rec])

    def finish(self, entry, host):
        if self.complete(entry, host) or not super().complete(entry, host):
            return
        recs = [r for r in _risk().load_results(entry["_results"])
                if r["risk"] == "B" and r["id"] in {self._id(entry, i, host) for i in self.items(entry, host)}]
        peak = max(j["peak_rss_kib"] for r in recs for j in r["measured"]["jobs"]) / 2 ** 20
        ram = host["mem_total_kib"] / 2 ** 20
        n1 = next(r for r in recs if r["measured"]["n"] == 1)["measured"]["throughput_jobs_per_hour"]
        rec = {"risk": "B", "id": f"{entry['id_prefix']}-{host_tag(host)}-limit-model",
               "configuration": {"job": entry["spec"], "threads": 1, "machine": _machine(host),
                                 "model": "limit = min(cores, floor(RAM / peak RSS per job))"},
               "method": "From this host's batch records: cores are physical cores (/proc/cpuinfo), RAM is MemTotal, "
                         "the peak RSS the largest of any job in any batch.",
               "measured": {"cores": host["cores"], "hardware_threads": host["hardware_threads"],
                            "ram_gib": round(ram, 3), "peak_rss_gib": round(peak, 4),
                            "limit": min(host["cores"], math.floor(round(ram, 3) / round(peak, 4))),
                            "throughput_ratio_vs_n1": {r["id"]: round(r["measured"]["throughput_jobs_per_hour"] / n1, 3)
                                                       for r in recs}},
               "tools": _tools(), "date": date.today().isoformat(), "source": "(the batch records)"}
        _risk_add(entry, [rec])


def extract_demo(name, target):
    """The install's `demos/zips/<name>.zip` extracted into `target` (replaced)."""
    z = Path(located()["home"]) / "demos" / "zips" / f"{name}.zip"
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    with zipfile.ZipFile(z) as zf:
        for mem in zf.infolist():
            if mem.is_dir() or not mem.filename.startswith(f"{name}/"):
                continue
            rel = Path(mem.filename[len(name) + 1:])
            if rel.is_absolute() or ".." in rel.parts:
                raise SystemExit(f"{z}: unsafe member {mem.filename}")
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            (target / rel).write_bytes(zf.read(mem))
    return target


def compile_scenes(demo, env):
    s2h = Path(located()["home"]) / "bin" / "scene2hdf"
    for scene in sorted(demo.rglob("*.scene")):
        subprocess.run([str(s2h), scene.name], cwd=scene.parent, env=env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_dirsig(cwd, simulation, out, threads, env, seed=None, as_limit_gib=None, timeout_s=None, log_info=None):
    """dirsig5 on `simulation` in `cwd`; peak VM and RSS polled every 0.2 s. Returns a dict."""
    out.mkdir(parents=True, exist_ok=True)
    cmd = [str(Path(located()["home"]) / "bin" / "dirsig5"), f"--output_folder={out}"]
    if threads != "default":
        cmd.append(f"--threads={threads}")
    if seed is not None:
        cmd.append(f"--random_seed={seed}")
    if log_info is not None:
        cmd.append(f"--log_info_filename={log_info}")
    cmd.append(simulation)
    if as_limit_gib:
        cmd = ["prlimit", f"--as={int(float(as_limit_gib) * 2 ** 30)}", "--"] + cmd
    t0, vm, hwm, timed_out = time.time(), 0, 0, False
    with open(out.parent / f"{out.name}.dirsig5.log", "w") as log:
        p = subprocess.Popen(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, env=env)
        while p.poll() is None:
            try:
                st = Path(f"/proc/{p.pid}/status").read_text()
                vm = max(vm, int(st.split("VmPeak:")[1].split()[0]))
                hwm = max(hwm, int(st.split("VmHWM:")[1].split()[0]))
            except (OSError, IndexError):
                pass
            if timeout_s and time.time() - t0 > timeout_s:
                p.kill()
                timed_out = True
            time.sleep(0.2)
    text = (out.parent / f"{out.name}.dirsig5.log").read_text(errors="replace").splitlines()
    return {"rc": p.returncode, "timed_out": timed_out, "wall_s": round(time.time() - t0, 1), "vm_peak_kib": vm,
            "rss_peak_kib": hwm, "errors": [x for x in text if "error" in x.lower() or "bad_alloc" in x][:8]}


def _captures(log_info):
    if not Path(log_info).is_file():
        return []
    li = json.loads(Path(log_info).read_text())
    return [{"t": c["relative_time_window"][0], "image": Path(c["plugin_data"]["filename"]).name,
             "truth": [Path(t).name for t in c["plugin_data"].get("truth_filenames", []) if t]}
            for c in li.get("capture_list", [])]


def capture_variant(demo, label, simulation):
    """Edit an extracted demo in place for `label`: `control` (as authored), `single-K` (capture K alone: one trigger
    time with the task window ended 1 s after it, or one focal plane) or `reversed` (trigger times or focal planes in
    reverse order)."""
    import lxml.etree as et
    trig = demo / "triggers.txt"
    if label == "control":
        return
    if trig.is_file():
        times = trig.read_text().split()
        if label == "reversed":
            trig.write_text("\n".join(reversed(times)) + "\n")
        else:
            k = int(label.split("-")[1])
            trig.write_text(times[k] + "\n")
            tasks = next(demo.glob("*.tasks"))
            tt = et.parse(str(tasks))
            tt.find(".//stop/datetime").text = str(float(times[k]) + 1.0)
            tt.write(str(tasks), xml_declaration=True, encoding="UTF-8")
        return
    plat = next(demo.glob("*.platform"))
    t = et.parse(str(plat))
    fps = list(t.iter("focalplane"))
    order = list(reversed(range(len(fps)))) if label == "reversed" else [int(label.split("-")[1])]
    parent, pos = fps[0].getparent(), fps[0].getparent().index(fps[0])
    for f in fps:
        f.getparent().remove(f)
    for k, j in enumerate(order):
        parent.insert(pos + k, fps[j])
    t.write(str(plat), xml_declaration=True, encoding="UTF-8")


def _compare_files(a, b):
    import numpy as np
    from compare_outputs import header_for, read_envi
    if Path(a).read_bytes() == Path(b).read_bytes():
        return {"equal": True}
    x = read_envi(a, header_for(a))[0].astype(float)
    y = read_envi(b, header_for(b))[0].astype(float)
    if x.shape != y.shape:
        return {"equal": False, "shapes": [list(x.shape), list(y.shape)]}
    d, mx = np.abs(x - y), np.maximum(np.abs(x), np.abs(y))
    return {"equal": False, "fraction_differing": float((d > 0).mean()), "max_abs": float(d.max()),
            "max_rel": float((d / np.where(mx > 0, mx, 1)).max())}


class CaptureOrder(Driver):
    """Risk D at the demo's native size: an item is a demo; its job renders the demo as authored (`control`), each
    capture alone and the captures reversed, dirsig5 directly (one thread, seed 1, the job's HOME, an address-space
    limit `as_limit_gib` and a timeout `timeout_s` per render). The memory a job counts for is that limit."""

    def problems(self, entry):
        return [] if {"risk", "simulation", "as_limit_gib", "timeout_s"} <= set(entry) else \
            ["risk, simulation, as_limit_gib and timeout_s are required"]

    def _id(self, item):
        return f"{item.lower()}-native"

    def done(self, entry, host):
        have = _risk_ids(entry)
        return {i for i in self.items(entry, host) if self._id(i) in have}

    def job(self, entry, item, folder, args):
        sim = entry["simulation"][item]
        env = {**os.environ}
        recs = {}

        def variant(label):
            d = folder / label
            if (d / "rec.json").is_file():
                return json.loads((d / "rec.json").read_text())
            demo = extract_demo(item, d / "demo")
            capture_variant(demo, label, sim)
            compile_scenes(demo, env)
            r = run_dirsig(demo, sim, d / "output", 1, env, seed=1, as_limit_gib=entry["as_limit_gib"],
                           timeout_s=entry["timeout_s"], log_info=d / "log_info.json")
            r["captures"] = _captures(d / "log_info.json")
            (d / "rec.json").write_text(json.dumps(r, indent=1))
            return r

        recs["control"] = variant("control")
        for k in range(len(recs["control"]["captures"])):
            recs[f"single-{k}"] = variant(f"single-{k}")
        recs["reversed"] = variant("reversed")
        (folder / "variants.json").write_text(json.dumps(recs, indent=1))

    def record(self, entry, item, folder, host):
        recs = json.loads((folder / "variants.json").read_text())
        ctrl = recs["control"]
        co = folder / "control" / "output"
        single, differences = {}, {}
        for k, c in enumerate(ctrl["captures"]):
            s = recs[f"single-{k}"]
            if s["rc"] != 0 or not s["captures"]:
                single[c["image"]] = False
                differences[c["image"]] = {"rc": s["rc"], "timed_out": s["timed_out"]}
                continue
            sc = s["captures"][0]
            cmp = _compare_files(folder / f"single-{k}" / "output" / sc["image"], co / c["image"])
            eq = cmp["equal"]
            for tc, ts in zip(c["truth"], sc["truth"]):
                eq = eq and _compare_files(folder / f"single-{k}" / "output" / ts, co / tc)["equal"]
            single[c["image"]] = eq
            if not cmp["equal"]:
                differences[c["image"]] = cmp
        rv = recs["reversed"]
        rev = {}
        if rv["rc"] == 0:
            for c in rv["captures"]:
                if any(x["image"] == c["image"] for x in ctrl["captures"]):
                    rev[c["image"]] = _compare_files(folder / "reversed" / "output" / c["image"],
                                                     co / c["image"])["equal"]
        products = sorted({c["image"] for c in ctrl["captures"]} | {t for c in ctrl["captures"] for t in c["truth"]})
        rec = {"risk": "D", "id": self._id(item),
               "configuration": {"demo": item, "simulation": entry["simulation"][item],
                                 "form": "pass-through (the demo's own files, dirsig5 directly)", "roi": "native",
                                 "threads": 1, "seed": 1, "as_limit_gib": entry["as_limit_gib"],
                                 "timeout_s": entry["timeout_s"], "machine": _machine(host)},
               "method": "scripts/bigger_host_run.py, driver capture_order: the demo's archive extracted per "
                         "variant, scene2hdf, dirsig5 --threads=1 --random_seed=1 under prlimit --as: as authored "
                         "('control'), one capture alone per capture ('single-K': one trigger time with the task window "
                         "ended 1 s after it, or one focal plane), and the captures in reverse order; images and truth "
                         "compared byte for byte, a difference as the fraction of values differing and the largest "
                         "absolute and relative difference; peak VM and RSS polled every 0.2 s from /proc.",
               "measured": {"captures_logged": len(ctrl["captures"]), "products": products, "equal_single": single,
                            "dirsig_refused": False, "single_differences": differences,
                            "control_wall_s": ctrl["wall_s"], "control_rss_peak_kib": ctrl["rss_peak_kib"],
                            "control_vm_peak_kib": ctrl["vm_peak_kib"],
                            "reversed": {"rc": rv["rc"], "timed_out": rv["timed_out"], "wall_s": rv["wall_s"],
                                         "rss_peak_kib": rv["rss_peak_kib"], "vm_peak_kib": rv["vm_peak_kib"],
                                         "errors": rv["errors"][:3], "equal_control_by_name": rev,
                                         "order_written": [c["image"] for c in rv["captures"]]}},
               "tools": _tools(), "date": date.today().isoformat(), "source": _home_relative(folder)}
        _risk_add(entry, [rec])


class LightCurve(Driver):
    """Risk E: an item is a render label `t<N>-<x>` (N threads) or `td-<x>` (DIRSIG's default: the host's hardware
    threads) of LightCurve1's `box_spin.jsim` (`samples` cuts it to the first samples); after the last render each
    pair of `pairs` is compared over every cube image both wrote, one record per pair."""

    def problems(self, entry):
        bad = [i for i in entry["items"] if not re.fullmatch(r"(t\d+|td)-[a-z]", str(i))]
        p = [f"items {bad} are not t<N>-<x> or td-<x>"] if bad else []
        unknown = [x for pr in entry.get("pairs", []) for x in pr if x not in entry["items"]]
        return p + ([f"pairs name {unknown}, not items"] if unknown else []) + \
            ([] if entry.get("pairs") and "risk" in entry else ["pairs and risk are required"])

    def threads(self, entry, item, host):
        return host["hardware_threads"] if item.startswith("td") else int(item[1:].split("-")[0])

    def whole_host(self, entry, item):
        return item.startswith("td")

    def _pair_id(self, entry, a, b, host):
        return f"{entry['id_prefix']}-{host_tag(host)}-{a}-vs-{b}"

    def done(self, entry, host):
        base = Path(entry.get("_work", "/nonexistent"))
        out = set()
        for i in self.items(entry, host):
            rec = base / i / "rec.json"
            if rec.is_file() and json.loads(rec.read_text()).get("rc") == 0:
                out.add(i)
        if self.complete(entry, host):
            out |= set(self.items(entry, host))
        return out

    def complete(self, entry, host):
        have = _risk_ids(entry)
        return all(self._pair_id(entry, a, b, host) in have for a, b in entry["pairs"])

    def probe(self, entry):
        return {"item": "t1-probe", "samples": 1}

    def job(self, entry, item, folder, args):
        samples = args.get("samples", entry.get("samples"))
        shutil.rmtree(folder, ignore_errors=True)
        demo = extract_demo("LightCurve1", folder / "demo")
        jsim = demo / "box_spin.jsim"
        j = json.loads(jsim.read_text())
        if samples:
            lc = next(p for p in j[0]["plugin_list"] if p["name"] == "LightCurve")["inputs"]
            lc["duration"] = samples
            lc["sample_count"] = samples
            jsim.write_text(json.dumps(j, indent=4))
        env = {**os.environ}
        compile_scenes(demo, env)
        threads = "default" if item.startswith("td") else int(item[1:].split("-")[0])
        r = run_dirsig(demo, "box_spin.jsim", folder / "output", threads, env)
        r["outputs"] = {p.name: sha256(p) for p in sorted((folder / "output").iterdir()) if p.is_file()}
        r["threads"] = threads
        r["samples"] = samples
        (folder / "rec.json").write_text(json.dumps(r, indent=1))
        if r["rc"] != 0:
            raise SystemExit(f"dirsig5 exited {r['rc']}")

    def finish(self, entry, host):
        import numpy as np
        if self.complete(entry, host) or not set(self.items(entry, host)) <= self.done(entry, host):
            return
        base = Path(entry["_work"])
        recs = {i: json.loads((base / i / "rec.json").read_text()) for i in self.items(entry, host)}
        out = []
        for a, b in entry["pairs"]:
            cubes = sorted(n for n in recs[a]["outputs"] if n.startswith("cube_") and n.endswith(".img")
                           and n in recs[b]["outputs"])
            samples = differing = 0
            max_abs = max_rel = 0.0
            frames_differing = []
            for n in cubes:
                if recs[a]["outputs"][n] == recs[b]["outputs"][n]:
                    samples += (base / a / "output" / n).stat().st_size // 4
                    continue
                x = np.fromfile(base / a / "output" / n, np.float32).astype(float)
                y = np.fromfile(base / b / "output" / n, np.float32).astype(float)
                d, mx = np.abs(x - y), np.maximum(np.abs(x), np.abs(y))
                samples += x.size
                differing += int((d > 0).sum())
                max_abs = max(max_abs, float(d.max()))
                max_rel = max(max_rel, float((d / np.where(mx > 0, mx, 1)).max()))
                frames_differing.append(n)
            other = sorted(k for k in recs[a]["outputs"] if recs[a]["outputs"][k] != recs[b]["outputs"].get(k)
                           and not k.startswith("cube_"))
            out.append({"risk": "E", "id": self._pair_id(entry, a, b, host),
                        "configuration": {"demo": "LightCurve1",
                                          "simulation": "box_spin.jsim" + (f" (samples 0 to {entry['samples'] - 1})"
                                                                           if entry.get("samples") else ""),
                                          "threads": [recs[a]["threads"], recs[b]["threads"]],
                                          "seed": "DIRSIG's default", "renders": [a, b], "machine": _machine(host)},
                        "method": "scripts/bigger_host_run.py, driver lightcurve: the demo's archive extracted, "
                                  "scene2hdf, dirsig5 with --threads=N or none (DIRSIG's default), the default seed, "
                                  "the job's HOME; every cube image both renders wrote compared value by value "
                                  "(float32): values differing, the largest absolute and relative difference "
                                  "|a-b|/max(|a|,|b|); frames with equal digests count as equal.",
                        "measured": {"pair": f"{a} vs {b}", "samples": samples, "differing": differing,
                                     "fraction_differing": differing / samples if samples else 0.0,
                                     "max_abs": max_abs, "max_rel": max_rel, "frames_compared": len(cubes),
                                     "frames_differing": frames_differing[:50],
                                     "frames_differing_count": len(frames_differing),
                                     "class": "identical" if not differing else "float-order" if max_rel <= 1e-5
                                     else "sampling-noise", "outputs_differing": other,
                                     "wall_s": [recs[a]["wall_s"], recs[b]["wall_s"]]},
                        "tools": _tools(), "date": date.today().isoformat(), "source": _home_relative(base)})
        _risk_add(entry, out)


class Command(Driver):
    """A repository script run as one job (`argv`, with `{python}`, `{repo}`, `{folder}` and `{dirsig_home}`
    substituted); it keeps its own results file, `done` (relative to the job folder). The item is done when that file
    exists and, with `done_lines` (a list of mappings), each mapping matches a JSON line of it."""

    def problems(self, entry):
        return [] if {"argv", "done"} <= set(entry) and len(entry["items"]) == 1 else \
            ["argv, done and exactly one item are required"]

    def threads(self, entry, item, host):
        t = entry.get("threads", 1)
        return host["hardware_threads"] if t == "default" else int(t)

    def whole_host(self, entry, item):
        return entry.get("threads", 1) == "default"

    def done(self, entry, host):
        base = Path(entry.get("_work", "/nonexistent"))
        out = set()
        for i in self.items(entry, host):
            f = base / i / entry["done"]
            if not f.is_file():
                continue
            lines = [json.loads(x) for x in f.read_text().splitlines() if x.strip().startswith("{")] \
                if entry.get("done_lines") else []
            if all(any(all(r.get(k) == v for k, v in want.items()) for r in lines) for want in
                   entry.get("done_lines", [])):
                out.add(i)
        return out

    def job(self, entry, item, folder, args):
        subs = {"python": sys.executable, "repo": str(ROOT), "folder": str(folder),
                "dirsig_home": located()["home"] or ""}
        argv = [a.format(**subs) for a in entry["argv"]]
        rc = subprocess.run(argv, cwd=ROOT).returncode
        if rc:
            raise SystemExit(f"{argv[1] if len(argv) > 1 else argv[0]} exited {rc}")


class Sleep(Driver):
    """A stub for tests: an item `NAME:SECONDS` sleeps, then is recorded as one JSON line in the results file."""

    def done(self, entry, host):
        p = entry["_results"]
        have = {json.loads(x)["item"] for x in p.read_text().splitlines() if x.strip()} if p.is_file() else set()
        return have & set(self.items(entry, host))

    def probe(self, entry):
        return entry.get("probe")

    def job(self, entry, item, folder, args):
        folder.mkdir(parents=True, exist_ok=True)
        time.sleep(float(item.split(":")[1]) if ":" in item else 0.0)
        if entry.get("hold_mib"):
            block = bytearray(int(entry["hold_mib"]) * 2 ** 20)
            block[::4096] = b"x" * len(block[::4096])
        (folder / "done").write_text(item)

    def record(self, entry, item, folder, host):
        with open(entry["_results"], "a") as f:
            f.write(json.dumps({"entry": entry["name"], "item": item, "pid": os.getpid()}) + "\n")


DRIVERS = {"s2s": S2S(), "concurrency": Concurrency(), "capture_order": CaptureOrder(), "lightcurve": LightCurve(),
           "command": Command(), "sleep": Sleep()}


def _home_relative(path):
    try:
        return "~/" + str(Path(path).resolve().relative_to(Path.home().resolve()))
    except ValueError:
        return str(path)


# --- planning -----------------------------------------------------------------------------------------------------

def read_peaks(work):
    p = Path(work) / "peaks.json"
    return json.loads(p.read_text()) if p.is_file() else {}


def peak_of(entry, work):
    """(peak KiB of one job or None, its source)."""
    if entry["driver"] == "capture_order":
        return int(entry["as_limit_gib"] * 2 ** 20), "the address-space limit of a job"
    cached = read_peaks(work).get(entry["name"])
    if cached:
        return cached["kib"], f"measured on {cached['host']} ({cached['date']}), cached"
    if entry.get("peak_mib"):
        return int(entry["peak_mib"] * 1024), "manifest: " + entry.get("peak_source", "an earlier round")
    return None, "unmeasured"


def plan_entry(entry, host, work, max_jobs=None, max_mem_kib=None, with_done=True):
    d = DRIVERS[entry["driver"]]
    items = d.items(entry, host)
    done = d.done(entry, host) if with_done else set()
    complete = with_done and d.complete(entry, host)
    peak, source = peak_of(entry, work)
    budget = host["mem_available_kib"] * MEMORY_FRACTION
    if max_mem_kib:
        budget = min(budget, max_mem_kib)
    rows = []
    for i in items:
        t = d.threads(entry, i, host)
        mem = None if peak is None else d.memory_jobs(entry, i) * peak * JOB_FACTOR
        fits = (t <= host["cores"] or d.whole_host(entry, i)) and (mem is None or mem <= budget)
        rows.append({"item": i, "threads": t, "memory_kib": mem, "fits": fits, "done": i in done or complete,
                     "est_s": est_of(entry, i)})
    t1 = max([r["threads"] for r in rows] or [1])
    conc = max(1, host["cores"] // max(1, min(r["threads"] for r in rows)))
    probe_pending = peak is None and d.probe(entry) is not None
    if peak is not None:
        conc = min(conc, max(1, math.floor(budget / (peak * JOB_FACTOR * max(d.memory_jobs(entry, i) for i in items)))))
    elif not probe_pending:
        conc = 1            # no figure and no probe (a command entry): one job at a time
    for cap in (d.max_concurrency, entry.get("max_concurrency"), max_jobs):
        if cap:
            conc = min(conc, cap)
    pending = [r for r in rows if not r["done"] and r["fits"]]
    return {"name": entry["name"], "driver": entry["driver"], "items": rows, "pending": len(pending),
            "done": sum(r["done"] for r in rows), "exceeds_host": [r["item"] for r in rows if not r["fits"]],
            "peak_kib": peak, "peak_source": source, "concurrency": conc, "max_threads": t1,
            "est_wall_s": makespan([r for r in pending], conc, host["cores"]), "complete": complete,
            "probe_pending": probe_pending, "disk_gb": entry.get("disk_gb_per_item", 0) * len(pending)}


def makespan(rows, conc, cores):
    """Wall time of `rows` (each `est_s`, `threads`) run longest first on `conc` slots and `cores` cores."""
    running, t = [], 0.0
    queue = sorted(rows, key=lambda r: -r["est_s"])
    while queue or running:
        used = sum(r["threads"] for _, r in running)
        started = False
        for r in list(queue):
            if len(running) < conc and (not running or used + min(r["threads"], cores) <= cores):
                running.append((t + r["est_s"], r))
                used += min(r["threads"], cores)
                queue.remove(r)
                started = True
        if not started or not queue:
            if not running:
                break
            running.sort(key=lambda x: x[0])
            t = running.pop(0)[0]
    return t


def format_plan(plans, host, label):
    gib = 2 ** 20
    lines = [f"Host ({label}): {host['cores']} cores, {host['hardware_threads']} hardware threads, "
             f"MemTotal {host['mem_total_kib'] / gib:.1f} GiB, MemAvailable {host['mem_available_kib'] / gib:.1f} GiB; "
             f"memory budget {MEMORY_FRACTION:.0%} of MemAvailable, a job counts {JOB_FACTOR} x its peak",
             "",
             "| Entry | Driver | Items (pending / done / exceeds host) | Threads per job | Peak per job (source) | "
             "Concurrency | Estimated wall (s) | Disk (GB) |",
             "|---|---|---|---|---|---|---|---|"]
    total = 0.0
    for p in plans:
        peak = "-" if p["peak_kib"] is None else f"{p['peak_kib'] / 1024:.0f} MiB"
        threads = sorted({r["threads"] for r in p["items"]})
        conc = f"{p['concurrency']}{'*' if p['probe_pending'] else ''}"
        lines.append(f"| {p['name']} | {p['driver']} | {len(p['items'])} ({p['pending']} / {p['done']} / "
                     f"{len(p['exceeds_host'])}) | {', '.join(map(str, threads))} | {peak} ({p['peak_source']}) | "
                     f"{conc} | {p['est_wall_s']:.0f} | {p['disk_gb']:g} |")
        total += p["est_wall_s"]
    lines.append("")
    lines.append(f"Total estimated wall time: {total:.0f} s ({total / 3600:.2f} h), entries one after another; "
                 f"estimates are one-thread wall times on the 4-core laptop (est_s). * the cores' bound: the job's "
                 f"memory is unmeasured, and the entry's probe (run alone first) sets the memory bound.")
    return "\n".join(lines)


# --- running ------------------------------------------------------------------------------------------------------

class Runner:
    def __init__(self, manifest, work, host, max_jobs=None, max_mem_kib=None, out=print):
        self.m, self.work, self.host = manifest, Path(work), host
        self.max_jobs, self.max_mem_kib, self.out = max_jobs, max_mem_kib, out
        self.running = {}
        self.work.mkdir(parents=True, exist_ok=True)
        for e in self.m["entries"]:
            e["_work"] = str(self.work / e["name"])

    def log(self, **event):
        event = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), **event}
        with open(self.work / "runner.log", "a") as f:
            f.write(json.dumps(event) + "\n")
        self.out(json.dumps(event))

    def env(self, entry, label):
        home = self.work / entry["name"] / f"{label}.home"
        home.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "HOME": str(home)}
        found = located()["home"]
        if found:
            env["DIRSIG_HOME"] = found
        return env

    def launch(self, entry, item, args=None, label=None):
        folder = self.work / entry["name"] / (label or item)
        folder.parent.mkdir(parents=True, exist_ok=True)
        log = open(self.work / entry["name"] / f"{label or item}.log", "w")
        payload = json.dumps({"manifest": self.m["_path"], "entry": entry["name"], "item": item,
                              "folder": str(folder), "work": str(self.work), "args": args or {}})
        p = subprocess.Popen([sys.executable, __file__, "_job", payload], stdout=log, stderr=subprocess.STDOUT,
                             env=self.env(entry, label or item), start_new_session=False)
        log.close()
        return p, folder

    def probe(self, entry):
        d = DRIVERS[entry["driver"]]
        pr = d.probe(entry)
        if pr is None:
            return None
        item, args = (pr["item"], pr) if isinstance(pr, dict) else (pr, {})
        self.log(event="probe", entry=entry["name"], item=item)
        p, folder = self.launch(entry, item, args, label=item if not args else f"probe-{item}")
        _, status, ru = os.wait4(p.pid, 0)
        p.returncode = os.waitstatus_to_exitcode(status)
        if p.returncode != 0:
            self.log(event="probe-failed", entry=entry["name"], item=item, rc=p.returncode)
            return None
        peaks = read_peaks(self.work)
        peaks[entry["name"]] = {"kib": ru.ru_maxrss, "host": host_tag(self.host), "item": item,
                                "date": date.today().isoformat()}
        (self.work / "peaks.json").write_text(json.dumps(peaks, indent=1, sort_keys=True))
        self.log(event="peak", entry=entry["name"], item=item, peak_kib=ru.ru_maxrss)
        if not args and item in d.items(entry, self.host):
            self.finish_item(entry, item, folder)
        return ru.ru_maxrss

    def finish_item(self, entry, item, folder):
        try:
            DRIVERS[entry["driver"]].record(entry, item, folder, self.host)
            self.log(event="recorded", entry=entry["name"], item=item)
        except Exception as e:   # a reduction that fails is logged; the item stays pending
            self.log(event="record-failed", entry=entry["name"], item=item, error=f"{type(e).__name__}: {e}")

    def run_entry(self, entry):
        d = DRIVERS[entry["driver"]]
        if d.complete(entry, self.host):
            self.log(event="skip", entry=entry["name"], reason="results present")
            return
        if peak_of(entry, self.work)[0] is None and d.probe(entry) is not None:
            self.probe(entry)
        plan = plan_entry(entry, self.host, self.work, self.max_jobs, self.max_mem_kib)
        if plan["peak_kib"] is None:
            plan["concurrency"] = 1                       # no figure (a command entry, or a failed probe)
        for i in plan["exceeds_host"]:
            self.log(event="exceeds-host", entry=entry["name"], item=i)
        queue = [r for r in plan["items"] if not r["done"] and r["fits"]]
        if not queue:
            d.finish(entry, self.host)
            self.log(event="skip", entry=entry["name"], reason="every item done")
            return
        self.log(event="start", entry=entry["name"], pending=len(queue), concurrency=plan["concurrency"],
                 peak_kib=plan["peak_kib"])
        running = self.running
        budget_threads = self.host["cores"]
        while queue or running:
            used = sum(r["threads"] for r, _, _ in running.values())
            for r in list(queue):
                if len(running) >= plan["concurrency"]:
                    break
                if running and used + min(r["threads"], budget_threads) > budget_threads:
                    continue
                need = entry.get("disk_gb_per_item", 0) * 1e9
                if need and shutil.disk_usage(self.work).free < need:
                    queue.remove(r)
                    self.log(event="exceeds-host", entry=entry["name"], item=r["item"],
                             note=f"less than {need / 1e9:g} GB free under the work root")
                    continue
                p, folder = self.launch(entry, r["item"])
                running[p.pid] = (r, p, folder)
                used += min(r["threads"], budget_threads)
                queue.remove(r)
                self.log(event="job-start", entry=entry["name"], item=r["item"], pid=p.pid)
            pid, status, ru = os.wait4(-1, 0)
            if pid not in running:
                continue
            r, p, folder = running.pop(pid)
            p.returncode = rc = os.waitstatus_to_exitcode(status)
            self.log(event="job-end", entry=entry["name"], item=r["item"], rc=rc, peak_kib=ru.ru_maxrss)
            if rc == 0:
                self.finish_item(entry, r["item"], folder)
            elif rc in (-9, 137):
                self.log(event="killed", entry=entry["name"], item=r["item"],
                         note="exit 137 or SIGKILL: an out-of-memory kill is a finding, not retried in this invocation")
        d.finish(entry, self.host)

    def run(self, only=None):
        def stop(signum, frame):
            self.log(event="interrupted", signal=signum, note="jobs in flight stopped; they rerun on the next "
                                                              "invocation")
            for pid in list(self.running):
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
            raise SystemExit(130)
        signal.signal(signal.SIGTERM, stop)
        for e in self.m["entries"]:
            if only and e["name"] not in only:
                continue
            self.run_entry(e)
        self.log(event="end")


def job_main(payload):
    a = json.loads(payload)
    m = load_manifest(a["manifest"], a["work"])
    entry = next(e for e in m["entries"] if e["name"] == a["entry"])
    entry["_work"] = str(Path(a["work"]) / entry["name"])
    if entry["driver"] != "sleep":
        located()
    DRIVERS[entry["driver"]].job(entry, a["item"], Path(a["folder"]), a["args"])
    return 0


def default_work():
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return base / "manifold" / "bigger-host"


def check(path=MANIFEST):
    if not Path(path).is_file():
        return [f"{path}: missing"]
    m = load_manifest(path)
    problems = manifest_problems(m, Path(path).resolve())
    if Path(path).resolve() == MANIFEST:
        text = PLAN_DOC.read_text() if PLAN_DOC.is_file() else ""
        problems += [f"{PLAN_DOC.relative_to(ROOT)}: entry {e['name']} not named"
                     for e in m.get("entries", []) if f"`{e['name']}`" not in text]
    return problems


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv[:1] == ["_job"]:
        return job_main(argv[1])
    if argv[:1] == ["_render_s2s"]:
        located()
        render_s2s(argv[1], Path(argv[2]), int(argv[3]) or None)
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--work", type=Path, default=None, help="outside the repository (default: the state directory's "
                                                             "manifold/bigger-host/)")
    ap.add_argument("--only", default=None, help="NAME[,NAME ...]: only these entries")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; run and probe nothing")
    ap.add_argument("--assume-cores", type=int, default=None)
    ap.add_argument("--assume-mem-gb", type=float, default=None)
    ap.add_argument("--max-jobs", type=int, default=None, help="at most this many jobs at once")
    ap.add_argument("--max-mem-gb", type=float, default=None, help="the memory budget at most this (GB)")
    ap.add_argument("--check", action="store_true", help="verify the manifest; exit 1 on a problem")
    a = ap.parse_args(argv)
    if a.check:
        problems = check(a.manifest)
        n = len(load_manifest(a.manifest)["entries"]) if not problems else 0
        print("\n".join(problems) if problems else f"{n} entries: well formed, drivers and items known, "
                                                   f"named in {PLAN_DOC.relative_to(ROOT)}")
        return 1 if problems else 0
    if (a.assume_cores is None) != (a.assume_mem_gb is None):
        ap.error("--assume-cores and --assume-mem-gb go together")
    work = (a.work or default_work()).expanduser().resolve()
    if work.is_relative_to(ROOT.resolve()):
        ap.error(f"--work {work} is inside the repository")
    m = load_manifest(a.manifest, work)
    m["_path"] = str(a.manifest.resolve())
    problems = manifest_problems(m, a.manifest.resolve())
    if problems:
        print("\n".join(problems))
        return 1
    only = set(a.only.split(",")) if a.only else None
    if only and only - {e["name"] for e in m["entries"]}:
        ap.error(f"--only names unknown entries: {sorted(only - {e['name'] for e in m['entries']})}")
    entries = [e for e in m["entries"] if not only or e["name"] in only]
    max_mem = int(a.max_mem_gb * 1e9 / 1024) if a.max_mem_gb else None
    if a.dry_run:
        for e in m["entries"]:
            e["_work"] = str(work / e["name"])
        host = host_facts()
        print(format_plan([plan_entry(e, host, work, a.max_jobs, max_mem) for e in entries], host, "this host"))
        if a.assume_cores is not None:
            ah = assumed_host(a.assume_cores, a.assume_mem_gb)
            print()
            print(format_plan([plan_entry(e, ah, work, a.max_jobs, max_mem) for e in entries], ah,
                              f"assumed, {a.assume_cores} cores, {a.assume_mem_gb:g} GB"))
        return 0
    Runner(m, work, host_facts(), a.max_jobs, max_mem).run(only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
