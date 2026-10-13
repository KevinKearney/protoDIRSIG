"""The bigger-host runner (`scripts/bigger_host_run.py`) and its manifest (`docs/data/bigger_host_manifest.yaml`).

No heavy run: the plan is computed with `--dry-run` and assumed hosts, the scheduler and resume are exercised with the
`sleep` stub driver (an item sleeps and is recorded), the drivers' reductions on synthetic files, and the fake two-entry
manifest of 16 x 16 jobs (`tests/data/bigger_host_fake_manifest.yaml`) runs only when DIRSIG is installed.
"""
import importlib.util
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bigger_host_run.py"
FAKE = ROOT / "tests" / "data" / "bigger_host_fake_manifest.yaml"
spec = importlib.util.spec_from_file_location("bigger_host_run", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def _manifest(tmp_path, entries):
    p = tmp_path / "manifest.yaml"
    p.write_text(yaml.safe_dump({"schema": m.SCHEMA, "entries": entries}, sort_keys=False))
    return p


def _sleep_entry(name="stub", items=("a:0.2", "b:0.2", "c:0.2"), **kw):
    return {"name": name, "driver": "sleep", "source": "test", "results": "{work}/stub.jsonl", "check": "test",
            "est_s": 1, "items": list(items), "peak_mib": 10, **kw}


def _run(args, **kw):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT, **kw)


def _lines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()] if Path(path).is_file() else []


# --- the manifest and the plan document ---------------------------------------------------------------------------

def test_the_manifest_checks_and_the_check_exits_zero():
    assert m.check() == []
    r = _run(["--check"])
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_plan_document_lists_exactly_the_manifest_entries():
    names = [e["name"] for e in m.load_manifest()["entries"]]
    rows = [line.split("|")[2].strip().strip("`") for line in m.PLAN_DOC.read_text().split("## Inventory")[1]
            .split("\n## ")[0].splitlines() if line.startswith("| ") and line.split("|")[1].strip().isdigit()]
    assert rows == names


def test_the_check_catches_an_unknown_item_and_driver(tmp_path):
    entries = [dict(e) for e in yaml.safe_load(m.MANIFEST.read_text())["entries"][:1]]
    entries[0]["items"] = entries[0]["items"] + ["s2s-no-such-spec"]
    entries.append({**_sleep_entry(), "driver": "nonesuch"})
    problems = m.manifest_problems(m.load_manifest(_manifest(tmp_path, entries)), tmp_path / "manifest.yaml")
    assert any("s2s-no-such-spec" in p for p in problems) and any("unknown driver" in p for p in problems)


def test_every_results_file_of_the_repository_entries_is_one_the_earlier_rounds_use():
    for e in m.load_manifest()["entries"]:
        if e["driver"] in ("s2s",):
            assert e["results"] == "docs/data/s2s_results.jsonl"
        elif e["driver"] in ("concurrency", "lightcurve", "capture_order"):
            assert e["results"] == "docs/data/risk_measurements.jsonl"


# --- concurrency and the dry run ----------------------------------------------------------------------------------

@pytest.mark.parametrize("cores,mem_gb", [(16, 64), (32, 128), (64, 256)])
def test_concurrency_is_the_minimum_of_cores_and_memory_over_the_peak(tmp_path, cores, mem_gb):
    host = m.assumed_host(cores, mem_gb)
    budget = host["mem_available_kib"] * m.MEMORY_FRACTION
    for e in m.load_manifest()["entries"]:
        e["_work"] = str(tmp_path / e["name"])
        p = m.plan_entry(e, host, tmp_path, with_done=False)
        if e["driver"] == "s2s" and e.get("peak_mib"):
            want = min(cores, math.floor(budget / (e["peak_mib"] * 1024 * m.JOB_FACTOR)))
            assert p["concurrency"] == want == cores           # these jobs are core-bound
        if e["driver"] == "capture_order":
            want = min(cores, math.floor(budget / (e["as_limit_gib"] * 2 ** 20 * m.JOB_FACTOR)))
            assert p["concurrency"] == max(1, want)
            assert p["exceeds_host"] == ([] if want >= 1 else e["items"])
        if e["driver"] == "concurrency":
            assert p["concurrency"] == 1
            assert p["exceeds_host"] == [f"n{n}" for n in (16, 32, 64) if n > cores]
            assert f"n{cores}" in [r["item"] for r in p["items"]]
        if e["driver"] == "command" or (e["driver"] == "s2s" and not e.get("peak_mib")):
            assert p["peak_source"] == "unmeasured"
            assert p["concurrency"] == (1 if e["driver"] == "command" else cores) and p["probe_pending"] == \
                (e["driver"] != "command")


def test_a_memory_bound_entry_and_the_caps(tmp_path):
    e = _sleep_entry(items=[f"i{k}:0" for k in range(10)], peak_mib=4096)
    e["_results"] = tmp_path / "stub.jsonl"
    host = m.assumed_host(64, 64)
    p = m.plan_entry(e, host, tmp_path)
    assert p["concurrency"] == math.floor(host["mem_available_kib"] * 0.75 / (4096 * 1024 * 1.25)) == 8
    assert m.plan_entry(e, host, tmp_path, max_jobs=3)["concurrency"] == 3
    assert m.plan_entry(e, host, tmp_path, max_mem_kib=4 * 2 ** 20)["exceeds_host"] == [f"i{k}:0" for k in range(10)]


def test_a_cached_peak_wins_over_the_manifest(tmp_path):
    e = _sleep_entry()
    e["_results"] = tmp_path / "stub.jsonl"
    (tmp_path / "peaks.json").write_text(json.dumps({"stub": {"kib": 2048, "host": "x", "date": "2026-10-13"}}))
    assert m.peak_of(e, tmp_path) == (2048, "measured on x (2026-10-13), cached")


def test_dry_run_prints_this_host_and_an_assumed_host_and_runs_nothing(tmp_path):
    r = _run(["--dry-run", "--assume-cores", "32", "--assume-mem-gb", "128", "--work", str(tmp_path)])
    assert r.returncode == 0, r.stderr
    assert "Host (this host)" in r.stdout and "Host (assumed, 32 cores, 128 GB)" in r.stdout
    for e in m.load_manifest()["entries"]:
        assert r.stdout.count(f"| {e['name']} |") == 2
    assert not any(tmp_path.iterdir())
    assert _run(["--dry-run", "--assume-cores", "32"]).returncode == 2


def test_the_work_root_may_not_be_inside_the_repository():
    assert _run(["--dry-run", "--work", str(ROOT / "outputs" / "x")]).returncode == 2


def test_the_makespan_runs_whole_host_items_alone():
    rows = [{"est_s": 10, "threads": 1}] * 4 + [{"est_s": 5, "threads": 8}]
    assert m.makespan(rows, conc=4, cores=4) == 15          # four one-thread items together, then the 8-thread one
    assert m.makespan(rows[:4], conc=2, cores=4) == 20


# --- running and resume, with the stub driver ---------------------------------------------------------------------

def test_a_second_invocation_skips_everything(tmp_path):
    man = _manifest(tmp_path, [_sleep_entry()])
    work = tmp_path / "work"
    r1 = _run(["--manifest", str(man), "--work", str(work), "--max-jobs", "2"])
    assert r1.returncode == 0, r1.stderr
    recs = _lines(work / "stub.jsonl")
    assert sorted(x["item"] for x in recs) == ["a:0.2", "b:0.2", "c:0.2"]
    r2 = _run(["--manifest", str(man), "--work", str(work)])
    assert r2.returncode == 0 and len(_lines(work / "stub.jsonl")) == 3
    events = [json.loads(x) for x in r2.stdout.splitlines()]
    assert {"skip"} <= {e["event"] for e in events} and "job-start" not in {e["event"] for e in events}


def test_jobs_run_concurrently_up_to_the_concurrency(tmp_path):
    man = _manifest(tmp_path, [_sleep_entry(items=[f"i{k}:1.0" for k in range(4)])])
    work = tmp_path / "work"
    t0 = time.time()
    assert _run(["--manifest", str(man), "--work", str(work), "--max-jobs", "4"]).returncode == 0
    assert time.time() - t0 < 4.0                         # four 1 s jobs at once, not one after another
    starts = [e for e in _lines(work / "runner.log") if e["event"] == "job-start"]
    assert len(starts) == 4


@pytest.mark.parametrize("sig", [signal.SIGKILL, signal.SIGTERM])
def test_an_interrupted_invocation_resumes(tmp_path, sig):
    man = _manifest(tmp_path, [_sleep_entry(items=[f"i{k}:0.6" for k in range(5)])])
    work = tmp_path / "work"
    p = subprocess.Popen([sys.executable, str(SCRIPT), "--manifest", str(man), "--work", str(work), "--max-jobs", "1"],
                         cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 30
    while len(_lines(work / "stub.jsonl")) < 2 and time.time() < deadline:
        time.sleep(0.05)
    p.send_signal(sig)
    p.wait(timeout=30)
    first = [x["item"] for x in _lines(work / "stub.jsonl")]
    assert 2 <= len(first) < 5                            # killed mid-way
    time.sleep(1.0)                                       # a SIGKILLed runner's job in flight ends on its own
    r = _run(["--manifest", str(man), "--work", str(work), "--max-jobs", "1"])
    assert r.returncode == 0, r.stderr
    items = [x["item"] for x in _lines(work / "stub.jsonl")]
    assert sorted(items) == [f"i{k}:0.6" for k in range(5)] and items[:len(first)] == first   # each exactly once
    log = _lines(work / "runner.log")
    second = max(k for k, e in enumerate(log) if e["event"] == "start")
    again = [e["item"] for e in log[second:] if e["event"] == "job-start"]
    assert sorted(again) == sorted(set(items) - set(first))                    # only the rest ran again
    if sig == signal.SIGTERM:
        assert any(e["event"] == "interrupted" for e in _lines(work / "runner.log"))


def test_the_probe_measures_a_jobs_peak_and_caches_it(tmp_path):
    e = _sleep_entry(items=["a:0", "b:0"], probe="a:0", hold_mib=64)
    del e["peak_mib"]
    man = _manifest(tmp_path, [e])
    work = tmp_path / "work"
    assert _run(["--manifest", str(man), "--work", str(work)]).returncode == 0
    peaks = json.loads((work / "peaks.json").read_text())
    assert peaks["stub"]["kib"] > 64 * 1024 and peaks["stub"]["item"] == "a:0"
    assert sorted(x["item"] for x in _lines(work / "stub.jsonl")) == ["a:0", "b:0"]      # the probe item counts


def test_a_failed_job_stays_pending(tmp_path):
    man = _manifest(tmp_path, [_sleep_entry(items=["a:0", "b:x"])])     # "x" is not a number: the job fails
    work = tmp_path / "work"
    assert _run(["--manifest", str(man), "--work", str(work)]).returncode == 0
    assert [x["item"] for x in _lines(work / "stub.jsonl")] == ["a:0"]
    ends = {e["item"]: e["rc"] for e in _lines(work / "runner.log") if e["event"] == "job-end"}
    assert ends["a:0"] == 0 and ends["b:x"] != 0


# --- the drivers on synthetic inputs ------------------------------------------------------------------------------

def test_capture_variants_edit_triggers_tasks_and_focal_planes(tmp_path):
    t = tmp_path / "t"
    t.mkdir()
    (t / "triggers.txt").write_text("0.0\n900.0\n1800.0\n")
    (t / "demo.tasks").write_text("<tasklist><task><start><datetime>0</datetime></start>"
                                  "<stop><datetime>3600</datetime></stop></task></tasklist>")
    single = tmp_path / "s"
    shutil.copytree(t, single)
    m.capture_variant(single, "single-1", "demo.sim")
    assert (single / "triggers.txt").read_text().split() == ["900.0"]
    assert "<stop><datetime>901.0</datetime>" in (single / "demo.tasks").read_text()
    m.capture_variant(t, "reversed", "demo.sim")
    assert (t / "triggers.txt").read_text().split() == ["1800.0", "900.0", "0.0"]
    p = tmp_path / "p"
    p.mkdir()
    (p / "pi.platform").write_text("<platform><instrument>" + "".join(f"<focalplane><name>f{k}</name></focalplane>"
                                                                      for k in range(4)) + "</instrument></platform>")
    q = tmp_path / "q"
    shutil.copytree(p, q)
    m.capture_variant(p, "reversed", "pi.sim")
    assert [x.split("<")[0] for x in (p / "pi.platform").read_text().split("<name>")[1:]] == ["f3", "f2", "f1", "f0"]
    m.capture_variant(q, "single-2", "pi.sim")
    assert [x.split("<")[0] for x in (q / "pi.platform").read_text().split("<name>")[1:]] == ["f2"]


def test_the_lightcurve_pairs_are_risk_e_records(tmp_path):
    import numpy as np
    import risk_measure as rm                                                   # scripts/ is on sys.path
    e = {"name": "lc", "driver": "lightcurve", "risk": "E", "id_prefix": "lc", "items": ["t1-a", "t2-a", "td-a"],
         "pairs": [["t1-a", "t2-a"], ["t1-a", "td-a"]], "_work": str(tmp_path / "lc"),
         "_results": tmp_path / "risk.jsonl"}
    host = m.assumed_host(8, 16)
    base = np.arange(1, 101, dtype=np.float32)
    for label, bump in (("t1-a", 0.0), ("t2-a", 0.0), ("td-a", 1e-3)):
        out = tmp_path / "lc" / label / "output"
        out.mkdir(parents=True)
        for k in range(3):
            x = base.copy()
            if k == 2:
                x[5] += bump
            x.tofile(out / f"cube_{k}.img")
        rec = {"rc": 0, "wall_s": 1.0, "threads": label, "outputs": {f.name: m.sha256(f) for f in out.iterdir()}}
        (tmp_path / "lc" / label / "rec.json").write_text(json.dumps(rec))
    assert m.DRIVERS["lightcurve"].done(e, host) == {"t1-a", "t2-a", "td-a"}
    m.DRIVERS["lightcurve"].finish(e, host)
    recs = rm.load_results(e["_results"])
    assert [r["id"] for r in recs] == [f"lc-{m.host_tag(host)}-t1-a-vs-t2-a", f"lc-{m.host_tag(host)}-t1-a-vs-td-a"]
    assert rm.check(e["_results"]) == []
    same, diff = (r["measured"] for r in recs)
    assert same["differing"] == 0 and same["class"] == "identical" and same["samples"] == 300
    assert diff["differing"] == 1 and diff["frames_differing"] == ["cube_2.img"] and diff["class"] == "sampling-noise"
    assert m.DRIVERS["lightcurve"].complete(e, host)


def test_a_command_entry_is_done_when_its_results_hold_the_lines(tmp_path):
    e = {"name": "c", "driver": "command", "items": ["demos"], "done": "sweep/results.jsonl", "_work": str(tmp_path),
         "done_lines": [{"type": "demo", "demo": "A"}, {"type": "demo", "demo": "B"}]}
    f = tmp_path / "demos" / "sweep" / "results.jsonl"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"type": "attempt", "demo": "A"}) + "\n" + json.dumps({"type": "demo", "demo": "A"}) + "\n")
    host = m.assumed_host(4, 8)
    assert m.DRIVERS["command"].done(e, host) == set()
    with open(f, "a") as fh:
        fh.write(json.dumps({"type": "demo", "demo": "B", "outcome": "rendered"}) + "\n")
    assert m.DRIVERS["command"].done(e, host) == {"demos"}


# --- the fake manifest of 16 x 16 jobs (DIRSIG) -------------------------------------------------------------------

def _dirsig():
    from manifold.engines.dirsig.adapter import locate_dirsig
    return locate_dirsig()["home"] is not None


@pytest.mark.skipif(not _dirsig(), reason="no DIRSIG installation")
def test_the_fake_manifest_runs_at_16_px_and_resumes(tmp_path):
    work = tmp_path / "work"
    r = _run(["--manifest", str(FAKE), "--work", str(work), "--max-jobs", "4", "--max-mem-gb", "4"])
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    s2s = _lines(work / "fake_s2s_results.jsonl")
    import s2s_measure                                                          # noqa: E402  (scripts/ on sys.path)
    idx = s2s_measure.index()
    assert [x["spec"] for x in s2s] == sorted(yaml.safe_load(FAKE.read_text())["entries"][0]["items"])
    for x in s2s:
        assert tuple(x) == s2s_measure.RECORD_KEYS and x["run_id"] == idx[x["spec"]]["run_id"]
        assert "window cut to 16 x 16" in x["source"]
    assert s2s_measure.check(work / "fake_s2s_results.jsonl") == []
    import risk_measure                                                         # noqa: E402
    risk = risk_measure.load_results(work / "fake_risk_measurements.jsonl")
    assert risk_measure.check(work / "fake_risk_measurements.jsonl") == []
    assert sorted(x["id"].rsplit("-", 1)[1] for x in risk) == ["model", "n1", "n2"]
    assert all(x["measured"]["digests_equal_single"] for x in risk if x["id"].endswith(("n1", "n2")))
    assert json.loads((work / "peaks.json").read_text())["fake-s2s-16px"]["kib"] > 0
    again = _run(["--manifest", str(FAKE), "--work", str(work)])
    assert again.returncode == 0 and "job-start" not in again.stdout
    assert _lines(work / "fake_s2s_results.jsonl") == s2s
