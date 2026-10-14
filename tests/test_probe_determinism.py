"""scripts/probe_determinism.py helpers and its --compare step on synthetic run directories (no DIRSIG, no demo)."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("probe_determinism", ROOT / "scripts" / "probe_determinism.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_swept_simulation_is_the_first_rendered_attempt(tmp_path):
    results = tmp_path / "results.jsonl"
    results.write_text("\n".join(json.dumps(r) for r in [
        {"type": "demo", "demo": "A1", "attempts": [{"simulation": "demo.sim", "outcome": "failed"},
                                                   {"simulation": "demo.jsim", "outcome": "rendered"}]},
        {"type": "demo", "demo": "F1", "attempts": [{"simulation": "demo.sim", "outcome": "failed"}]}]) + "\n{cut")
    assert probe.swept_simulation(results, "A1") == "demo.jsim"
    assert probe.swept_simulation(results, "F1") is None and probe.swept_simulation(results, "Z9") is None


def test_the_thread_wrapper_adds_the_option_and_links_scene2hdf(tmp_path):
    engine = tmp_path / "dirsig" / "bin" / "dirsig5"
    engine.parent.mkdir(parents=True)
    engine.write_text("#!/bin/sh\n")
    (engine.parent / "scene2hdf").write_text("#!/bin/sh\n")
    wrapper = probe.thread_wrapper(tmp_path / "work", engine)
    assert f'exec "{engine}" --threads=1 "$@"' in wrapper.read_text()
    assert (wrapper.parent / "scene2hdf").resolve() == (engine.parent / "scene2hdf").resolve()
    assert probe.thread_wrapper(tmp_path / "work", engine) == wrapper                     # idempotent


def test_compare_writes_pairs_and_cross_condition_records(tmp_path, capsys):
    work = tmp_path / "work"
    for cond, rep, text in [("C0", 1, "a\n"), ("C0", 2, "a\n"), ("C1", 1, "b\n"), ("C1", 2, "b\n")]:
        out = work / "runs" / "D1" / f"{cond}-{rep}" / "output"
        out.mkdir(parents=True)
        (out / "data_recorder.txt").write_text(f"# Generated: 2026-10-11T15:19:{rep:02d}Z\n{text}")
    (work / "probe.jsonl").write_text(json.dumps({"demo": "D1", "condition": "C0", "rep": 1}) + "\n")
    assert probe.main(["--work", str(work), "--compare"]) == 0
    got = json.loads((work / "compare.json").read_text())["D1"]
    assert set(got) == {"C0 pair", "C1 pair", "C0 vs C1"}
    assert got["C0 pair"][0]["class"] == "metadata" and got["C0 vs C1"][0]["class"] == "sampling-noise"
    assert "D1" in capsys.readouterr().out
