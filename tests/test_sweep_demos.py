"""scripts/sweep_demos.py: candidates, the simulation-file rule, budgets, disk floor, delete scope, resume, error lines,
determinism and the report, with synthetic zips in a temporary folder and the stub engine (no DIRSIG, no demo)."""
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

from test_passthrough import VECTOR, stub_engine

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sweep_demos", ROOT / "scripts" / "sweep_demos.py")
sweep_demos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweep_demos)

TREE = {p.relative_to(VECTOR / "tree").as_posix(): p.read_bytes() for p in (VECTOR / "tree").rglob("*") if p.is_file()}


def make_zip(zips, name, files=None, pad=0):
    """`<zips>/<name>.zip` holding `files` (relative path -> bytes; default the vector's tree) under `<name>/`, plus a
    macOS resource fork that must be ignored, and `pad` bytes of filler to set its size."""
    files = dict(TREE if files is None else files)
    if pad:
        files["filler.bin"] = b"\0" * pad
    zips.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zips / f"{name}.zip", "w") as zf:
        for rel, data in files.items():
            zf.writestr(f"{name}/{rel}", data)
        zf.writestr(f"__MACOSX/{name}/._demo.jsim", b"fork")
    return zips / f"{name}.zip"


@pytest.fixture
def home(tmp_path):
    """A synthetic DIRSIG home: demos/zips with zips and one unpacked directory."""
    zips = tmp_path / "dirsig" / "demos" / "zips"
    make_zip(zips, "Big1", pad=5000)
    make_zip(zips, "Small1")
    make_zip(zips, "Mid1", pad=100)
    make_zip(zips, "Ssa2")
    make_zip(zips, "Dup1 (2)")
    (zips / "Unpacked1").mkdir()
    for rel, data in TREE.items():
        (zips / "Unpacked1" / rel).parent.mkdir(parents=True, exist_ok=True)
        (zips / "Unpacked1" / rel).write_bytes(data)
    (zips / "Mid1").mkdir()                                   # both a zip and a directory: the zip is the source
    (zips / "Mid1" / "demo.jsim").write_text("{}")
    return tmp_path / "dirsig"


# --- candidates and the simulation-file rule ------------------------------------------------------------------------

def test_candidates_are_ordered_by_size_and_named_skips_are_recorded(home):
    runnable, skipped = sweep_demos.candidates(home)
    assert [c["name"] for c in runnable] == ["Small1", "Unpacked1", "Mid1", "Big1"]
    small = runnable[0]
    assert small["source"] == "zip" and small["size"] == sum(len(v) for v in TREE.values())   # no resource fork
    assert next(c for c in runnable if c["name"] == "Mid1")["source"] == "zip"
    assert next(c for c in runnable if c["name"] == "Unpacked1")["source"] == "directory"
    reasons = {s["name"]: s["outcome"] for s in skipped}
    assert reasons == {"Ssa2": "skipped: dirsig4", "Dup1 (2)": "skipped: duplicate name"}
    assert next(s for s in skipped if s["name"] == "Ssa2")["note"] == sweep_demos.DIRSIG4_NOTE


def test_only_and_skip_filter_candidates(home):
    runnable, skipped = sweep_demos.candidates(home, only={"Small1", "Big1"}, skip={"Big1"})
    assert [c["name"] for c in runnable] == ["Small1"] and [s["outcome"] for s in skipped] == ["skipped: --skip"]


def test_the_seeded_dirsig4_names():
    assert sweep_demos.DIRSIG4 == ("MoonSat1", "Ssa2", "Ssa3")


@pytest.mark.parametrize("files, plan", [
    (["demo.sim", "demo.jsim", "other.sim"], ["demo.sim", "demo.jsim"]),
    (["demo.jsim", "a.sim"], ["demo.jsim"]),
    (["demo.sim"], ["demo.sim"]),
    (["e.jsim", "b.sim", "a.jsim", "d.sim", "c.sim", "notes.txt"], ["a.jsim", "b.sim", "c.sim", "d.sim"]),
    (["readme.txt"], []),
])
def test_the_simulation_file_rule(tmp_path, files, plan):
    for f in files:
        (tmp_path / f).write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "aa.sim").write_text("x")            # not top level
    assert sweep_demos.simulation_plan(tmp_path) == plan


# --- budget, timeout cap, errors, determinism -----------------------------------------------------------------------

def test_the_timeout_cap_and_the_budget_stop():
    assert sweep_demos.attempt_timeout(1800, now=0, deadline=10_000) == 1800
    assert sweep_demos.attempt_timeout(1800, now=0, deadline=1000) == 700           # deadline minus 5 minutes
    assert sweep_demos.may_start(now=0, deadline=601, longest_s=0)
    assert not sweep_demos.may_start(now=0, deadline=599, longest_s=0)               # 10 minutes at least
    assert not sweep_demos.may_start(now=0, deadline=1000, longest_s=1200)           # the longest attempt
    assert sweep_demos.may_start(now=0, deadline=1300, longest_s=1200)


def test_first_error_line():
    lines = ["DIRSIG5 banner", "loading scene", "[error] Unable to load atmospheric database!", "Missing x"]
    assert sweep_demos.first_error_line(lines) == "[error] Unable to load atmospheric database!"
    assert sweep_demos.first_error_line(["Path demo.scene.hdf DOES NOT EXIST"]) == "Path demo.scene.hdf DOES NOT EXIST"
    assert sweep_demos.first_error_line(["all good"]) is None


def test_determinism_comparison():
    a = [{"name": "x.img", "sha256": "1"}, {"name": "x.hdr", "sha256": "2"}]
    assert sweep_demos.compare_outputs(a, list(reversed(a))) == ("yes", [])
    assert sweep_demos.compare_outputs(a, [{"name": "x.img", "sha256": "9"}]) == ("no", ["x.hdr", "x.img"])


# --- delete scope ---------------------------------------------------------------------------------------------------

def test_a_delete_outside_the_allowed_prefixes_raises_before_removing(tmp_path):
    allowed, other = tmp_path / "work", tmp_path / "elsewhere"
    (allowed / "runs" / "a").mkdir(parents=True)
    other.mkdir()
    (other / "keep.txt").write_text("keep")
    protected = allowed / "demo_dirs" / "Keep"
    protected.mkdir(parents=True)
    for bad in (other, other / "keep.txt", allowed, tmp_path, allowed / "runs" / ".." / ".." / "elsewhere", protected,
                protected / "x"):
        with pytest.raises(sweep_demos.DeleteScopeError):
            sweep_demos.safe_delete(bad, allowed=[allowed], protected=[protected])
    assert (other / "keep.txt").read_text() == "keep" and protected.is_dir() and allowed.is_dir()
    sweep_demos.safe_delete(allowed / "runs" / "a", allowed=[allowed], protected=[protected])
    assert not (allowed / "runs" / "a").exists()


# --- the sweep with a stub engine -----------------------------------------------------------------------------------

class Clock:
    """An injected clock that also advances on sleep."""

    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def _sweep(tmp_path, home, deadline=None, clock=None, **kw):
    config_repo = tmp_path / "config_repo"
    config_repo.mkdir(exist_ok=True)
    layers = tmp_path / "layers" / "manifold_run_specs"
    (tmp_path / "layers" / "manifold_sensors").mkdir(parents=True, exist_ok=True)
    layers.mkdir(parents=True, exist_ok=True)
    clock = clock or __import__("time").time
    kw.setdefault("disk_floor_gb", 0.0)                    # pytest's temporary folder may sit on a small tmpfs
    return sweep_demos.Sweep(tmp_path / "work", deadline if deadline is not None else clock() + 3600,
                             dirsig_home=home, config_repo=config_repo, library=layers,
                             engine=stub_engine(tmp_path), report=tmp_path / "sweep.md", clock=clock,
                             out=lambda *a: None, temp=lambda: 50.0, **kw)


def test_a_sweep_renders_repeats_records_and_cleans_up(tmp_path, home, monkeypatch):
    monkeypatch.setenv("PROTODIRSIG_THERMAL_ZONES", str(tmp_path / "no-sensors"))   # the worker reads none
    s = _sweep(tmp_path, home)
    s.run(only={"Small1", "Ssa2", "Dup1 (2)"})
    rows = sweep_demos.demo_rows(s.records())
    small = rows["Small1"]
    assert small["outcome"] == "rendered" and small["simulation"] == "demo.jsim"
    att = small["attempts"][0]
    assert att["engine_exit_status"] == 0 and att["dirsig_version"].startswith("stub-engine")
    assert {o["name"] for o in att["outputs"]} >= {"demo-t0000-c0000.img", "demo-t0000-c0000.img.hdr"}
    assert att["repeat_run"]["outcome"] == "rendered"
    assert att["deterministic"] == "no" and att["differing"] == ["stub_engine_args.json"]   # the stub writes its paths
    assert att["max_cpu_temp_c"] == 50.0 and att["throttle_suspect"] is False
    assert att["cache"]["mode"] == "per-run home" and att["min_free_disk_bytes"] > 0
    assert rows["Ssa2"]["outcome"] == "skipped: dirsig4" and rows["Dup1 (2)"]["outcome"] == "skipped: duplicate name"
    assert not (s.demo_dirs / "Small1").exists()                              # the extracted directory is deleted
    assert not list((s.work / "runs").iterdir())                              # and every attempt's work root
    assert [r["reason"] for r in s.records() if r["type"] == "stop"] == ["candidates exhausted"]
    beat = (s.sweep_dir / "heartbeat").read_text()
    assert "time_left_s=" in beat
    text = (tmp_path / "sweep.md").read_text()
    assert "| Small1 |" in text and "demo.jsim: rendered" in text and "skipped: dirsig4" in text


def test_a_failing_demo_tries_each_simulation_file_and_records_the_error(tmp_path, home, monkeypatch):
    make_zip(home / "demos" / "zips", "Two1", files={**TREE, "demo.sim": TREE["demo.jsim"]})
    monkeypatch.setenv("STUB_ENGINE_EXIT", "4")
    s = _sweep(tmp_path, home)
    s.run(only={"Two1"})
    row = sweep_demos.demo_rows(s.records())["Two1"]
    assert row["outcome"] == "failed" and [a["simulation"] for a in row["attempts"]] == ["demo.sim", "demo.jsim"]
    att = row["attempts"][0]
    assert att["engine_exit_status"] == 4 and att["first_error_line"] and att["log_tail"]
    assert "status 4" in att["first_error_line"] or "status 4" in " ".join(att["errors"])


def test_a_committed_asset_is_used_in_place_and_never_deleted(tmp_path, home):
    s = _sweep(tmp_path, home)
    keep = s.demo_dirs / "Small1"
    for rel, data in TREE.items():
        (keep / rel).parent.mkdir(parents=True, exist_ok=True)
        (keep / rel).write_bytes(data)
    (s.config_repo / "assets.json").write_text(json.dumps({"version": "assets/1", "assets": [
        {"path": "demo_dirs/Small1", "kind": "directory"}]}))
    s = _sweep(tmp_path, home)
    assert keep in s.protected
    s.run(only={"Small1"})
    assert keep.is_dir() and sweep_demos.demo_rows(s.records())["Small1"]["placed_before_sweep"] is True
    with pytest.raises(sweep_demos.DeleteScopeError):
        s._delete(keep)


def test_the_disk_floor_skips_a_demo(tmp_path, home):
    s = _sweep(tmp_path, home, disk_floor_gb=1.0, free_bytes=lambda: 10**9 + 10)
    s.run(only={"Small1"})
    row = sweep_demos.demo_rows(s.records())["Small1"]
    assert row["outcome"] == "skipped: disk" and not (s.demo_dirs / "Small1").exists()


def test_the_budget_stops_new_attempts(tmp_path, home):
    clock = Clock()
    s = _sweep(tmp_path, home, deadline=clock() + 500, clock=clock, sleep=clock.sleep)
    s.run(only={"Small1", "Big1"})
    assert not [r for r in s.records() if r["type"] == "attempt"]
    stop = [r for r in s.records() if r["type"] == "stop"]
    assert stop[0]["reason"] == "budget" and stop[0]["before"] == "Small1"


def test_the_attempt_timeout_is_capped_by_the_deadline_and_cancels(tmp_path, home, monkeypatch):
    """With 300 s + 2 s left to the deadline... the cap is 2 s, well under the per-run timeout; the stub sleeps longer."""
    monkeypatch.setenv("STUB_ENGINE_SLEEP", "60")
    import time
    s = _sweep(tmp_path, home, per_run_timeout=1800)
    s.deadline = time.time() + sweep_demos.DEADLINE_MARGIN_S + 3
    att = s.attempt("Small1", *_placed(s, "Small1"))
    assert att["timeout_s"] <= 3 and att["outcome"] == "timeout" and att["wall_s"] < 60


def _placed(s, name):
    target = s.demo_dirs / name
    for rel, data in TREE.items():
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        (target / rel).write_bytes(data)
    return sweep_demos.directory_digest(target), "demo.jsim"


def test_resume_skips_finished_demos_and_keeps_the_deadline(tmp_path, home):
    config_repo = tmp_path / "config_repo"
    config_repo.mkdir()
    (tmp_path / "layers" / "manifold_sensors").mkdir(parents=True)
    (tmp_path / "layers" / "manifold_run_specs").mkdir()
    common = ["--work", str(tmp_path / "work"), "--dirsig-home", str(home), "--config-repo", str(config_repo),
              "--library", str(tmp_path / "layers" / "manifold_run_specs"), "--engine", str(stub_engine(tmp_path)),
              "--report", str(tmp_path / "r.md"), "--only", "Small1", "--disk-floor-gb", "0"]
    assert sweep_demos.main([*common, "--deadline", "2099-01-01T00:00:00+00:00"]) == 0
    state = json.loads((tmp_path / "work" / "sweep" / "state.json").read_text())
    assert state["deadline"] == sweep_demos.parse_deadline("2099-01-01T00:00:00+00:00")
    n = len([r for r in sweep_demos.read_results(tmp_path / "work" / "sweep" / "results.jsonl") if r["type"] == "attempt"])
    assert n == 2                                                               # first and repeat
    assert sweep_demos.main([*common, "--resume", "--deadline", "2098-01-01T00:00:00+00:00"]) == 0
    state2 = json.loads((tmp_path / "work" / "sweep" / "state.json").read_text())
    assert state2["deadline"] == state["deadline"] and state2["resumed"] == 1
    records = sweep_demos.read_results(tmp_path / "work" / "sweep" / "results.jsonl")
    assert len([r for r in records if r["type"] == "attempt"]) == n            # Small1 was not run again


def test_results_survive_a_cut_line(tmp_path):
    f = tmp_path / "results.jsonl"
    f.write_text('{"type": "demo", "demo": "A", "outcome": "rendered", "attempts": []}\n{"type": "dem')
    assert [r["demo"] for r in sweep_demos.read_results(f)] == ["A"]


def test_the_report_keeps_hand_written_sections(tmp_path):
    report = tmp_path / "sweep.md"
    report.write_text("# DIRSIG demo sweep\n\nIntro by hand.\n\n" + sweep_demos.BEGIN + "\nold\n" + sweep_demos.END
                      + "\n\n## Analysis\n\nKept.\n")
    records = [{"type": "demo", "demo": "A1", "outcome": "failed", "uncompressed_bytes": 2_000_000, "attempts": [
        {"simulation": "demo.sim", "outcome": "failed", "wall_s": 3.0, "outputs": [], "first_error_line": "[error] x | y",
         "max_cpu_temp_c": 91.0, "throttle_suspect": True}]},
        {"type": "demo", "demo": "B1", "outcome": "skipped: dirsig4", "note": sweep_demos.DIRSIG4_NOTE, "attempts": []},
        {"type": "stop", "reason": "candidates exhausted"}]
    sweep_demos.write_report(report, records, {"deadline_iso": "2026-10-11T12:42:13-04:00"})
    text = report.read_text()
    assert text.startswith("# DIRSIG demo sweep\n\nIntro by hand.\n\n") and text.endswith("\n\n## Analysis\n\nKept.\n")
    assert "\nold\n" not in text and "Ended: candidates exhausted." in text
    assert "| A1 | 2.00 | failed | demo.sim: failed | 3.0 |" in text and "91.0 (throttle suspect)" in text
    assert "[error] x \\| y" in text and "| skipped: dirsig4 | 1 |" in text


def test_argument_errors(capsys):
    with pytest.raises(SystemExit) as e:
        sweep_demos.main(["--work", str(ROOT / "outputs" / "x")])
    assert e.value.code == 2 and "outside the repository" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        sweep_demos.main(["--per-run-timeout", "0", "--work", "/nonexistent-sweep"])


def test_a_stop_request_cancels_the_render_records_it_and_writes_the_report(tmp_path, home, monkeypatch):
    """What the SIGTERM handler does (it sets `stop`): the current render is cancelled and recorded `interrupted`, the
    demo is left for `--resume`, and the report is written."""
    import threading
    monkeypatch.setenv("STUB_ENGINE_SLEEP", "60")
    s = _sweep(tmp_path, home)
    threading.Timer(3.0, lambda: setattr(s, "stop", True)).start()
    s.run(only={"Small1", "Big1"})
    records = s.records()
    row = sweep_demos.demo_rows(records)["Small1"]
    assert row["outcome"] == "interrupted" and row["interrupted"] is True and row["attempts"][0]["wall_s"] < 60
    assert "Big1" not in sweep_demos.demo_rows(records) and "Small1" not in s.finished()
    assert [r["reason"] for r in records if r["type"] == "stop"] == ["SIGTERM"]
    assert "| Small1 |" in (tmp_path / "sweep.md").read_text() and not (s.demo_dirs / "Small1").exists()


def test_the_report_caps_a_demo_s_output_rows():
    outs = [{"name": f"f{i:04d}.img", "size": 10, "sha256": "0" * 64} for i in range(30)]
    records = [{"type": "demo", "demo": "Many1", "outcome": "rendered", "uncompressed_bytes": 1,
                "attempts": [{"simulation": "demo.sim", "outcome": "rendered", "wall_s": 1.0, "outputs": outs}]}]
    text = sweep_demos.render_generated(records, {})
    assert "| f0023.img |" in text and "| f0024.img |" not in text
    assert "| and 6 more files | 60 | listed in the results file |" in text


@pytest.mark.parametrize("repeat, expected", [((), "not tested"), (("Small1",), "no")])
def test_repeat_names_a_demo_to_repeat_whatever_its_duration(tmp_path, home, monkeypatch, repeat, expected):
    monkeypatch.setenv("PROTODIRSIG_THERMAL_ZONES", str(tmp_path / "no-sensors"))
    monkeypatch.setattr(sweep_demos, "REPEAT_UNDER_S", 0)                     # every render counts as long
    s = _sweep(tmp_path, home, repeat=repeat)
    s.run(only={"Small1"})
    att = sweep_demos.demo_rows(s.records())["Small1"]["attempts"][0]
    assert att["deterministic"] == expected and ("repeat_run" in att) is bool(repeat)
