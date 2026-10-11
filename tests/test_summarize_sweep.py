"""scripts/summarize_sweep.py on synthetic sweep results (no DIRSIG, no demo)."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("summarize_sweep", ROOT / "scripts" / "summarize_sweep.py")
summarize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summarize)
spec2 = importlib.util.spec_from_file_location("survey_demos", ROOT / "scripts" / "survey_demos.py")
survey = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(survey)


def _att(demo, sim, outcome, wall, outputs=(), det=None, differing=None, tail=None, first=None, temp=50.0,
         repeat=False, cache=None):
    a = {"type": "attempt", "demo": demo, "simulation": sim, "outcome": outcome, "wall_s": wall, "repeat": repeat,
         "outputs": [{"name": n, "size": s, "sha256": "0" * 64} for n, s in outputs], "max_cpu_temp_c": temp,
         "throttle_suspect": temp >= 90, "cache": cache or {"mode": "per-run home", "home": "home", "files": 0,
                                                            "bytes": 0}, "timeout_s": 1800.0}
    if det:
        a["deterministic"] = det
    if differing is not None:
        a["differing"] = differing
    if tail is not None:
        a["log_tail"], a["first_error_line"] = tail, first
    return a


def _demo(name, outcome, attempts, **kw):
    return {"type": "demo", "demo": name, "outcome": outcome, "attempts": attempts, **kw}


DB_TAIL = ["[error] Unable to load atmospheric database!", "[error] Filename = 'x.adb.hdf'",
           "[error] Error = 'Could not open NewAtmosphere HDF: \"x.adb.hdf\"!'", "[error] Error!",
           "  Unable to initialize atmosphere plugin!", "  Thrown by 'init' (AtmosphereManager.cpp:253)"]
SENSOR_TAIL = ["Unsupported 'spectralunits' in <bandpass>!", "[error] Error!", "  Sensor", "  Thrown by 'readSim'"]


@pytest.fixture
def records():
    rows = [
        _demo("Fast1", "rendered", [_att("Fast1", "demo.sim", "rendered", 4.0, [("a.img", 2_000_000)], det="yes",
                                         temp=95.0, cache={"mode": "per-run home", "home": "home", "files": 2,
                                                           "bytes": 3_000_000})]),
        _demo("Slow1", "rendered", [_att("Slow1", "demo.sim", "rendered", 400.0, [("a.img", 50_000_000)],
                                         det="not tested")]),
        _demo("Lidar1", "rendered", [_att("Lidar1", "demo.sim", "rendered", 10.0, [("demo.bin", 10)], det="no",
                                          differing=["demo.bin"])]),
        _demo("Truth1", "rendered", [_att("Truth1", "demo.jsim", "rendered", 20.0, [("t.img", 10)], det="no",
                                          differing=["demo_truth.img"])]),
        _demo("Atm1", "failed", [_att("Atm1", "demo.sim", "failed", 2.0, tail=DB_TAIL, first=DB_TAIL[0]),
                                 _att("Atm1", "demo.jsim", "failed", 2.0, tail=DB_TAIL, first=DB_TAIL[0])]),
        _demo("Atm2", "failed", [_att("Atm2", "demo.sim", "failed", 2.0, tail=DB_TAIL, first=DB_TAIL[0])]),
        _demo("Sens1", "failed", [_att("Sens1", "demo.sim", "failed", 2.0, tail=SENSOR_TAIL, first="[error] Error!")]),
        _demo("Long1", "timeout", [_att("Long1", "demo.sim", "timeout", 1800.5, tail=["Starting capture"], first=None)]),
        _demo("Ssa2", "skipped: dirsig4", [], note="flagged"),
        {"type": "attempt", "demo": "Fast1", "simulation": "demo.sim", "outcome": "rendered", "wall_s": 4.1,
         "repeat": True, "max_cpu_temp_c": 91.0, "throttle_suspect": True, "outputs": []},
        {"type": "stop", "reason": "candidates exhausted"},
    ]
    rows += [a for r in list(rows) if r["type"] == "demo" for a in r["attempts"]]      # each attempt has its own line
    return rows


VERDICTS = {"Fast1": ("near", "BasicAtmosphere .atm (uniformradiativetransfer, uniformweather)"),
            "Truth1": ("near", "FourCurveAtmosphere"), "Atm1": ("near", "weather without a ThermWeather file"),
            "Slow1": ("far", "a, b"), "Indoors1": ("near", "x")}


def test_shorten_reduces_absolute_paths_only():
    s = summarize.shorten
    assert s('loading "/home/u/work/runs/abc/input/D/demo.glist" now') == 'loading "demo.glist" now'
    assert s("while reading platform file './demo.platform':") == "while reading platform file './demo.platform':"
    assert s("Missing/Unknown environment variable") == "Missing/Unknown environment variable"


def test_cause_names_the_message_and_what_is_missing():
    assert summarize.cause(DB_TAIL, DB_TAIL[0]) == ("Unable to initialize atmosphere plugin!", "database x.adb.hdf")
    assert summarize.cause(SENSOR_TAIL)[0] == "Unsupported 'spectralunits' in <bandpass>!"   # not the bare "Sensor"
    tail = ["The current spectral state is 8-13um", "However, the scene covers 0.35-2.55um", "  Thrown by 'x'"]
    assert summarize.cause(tail)[0] == "However, the scene covers 0.35-2.55um"            # the generic line was cut
    for line, named in [("unable to open file 'mls.adb': No such file", "file mls.adb"),
                        ("[error] Missing/Unknown environment variable: 'MUSES_EXE'", "environment variable MUSES_EXE"),
                        ("    Variable = DIRSIG_ODB", "variable DIRSIG_ODB"),
                        ("cannot make canonical path: No such file or directory [city1.scene]", "file city1.scene"),
                        ('Path "/a/b/demo.scene.hdf" does not exist!', "file demo.scene.hdf")]:
        assert summarize.cause([line])[1] == named
    assert summarize.cause([], first_line="[error] Missing/Unknown environment variable: 'X'")[1] == "environment variable X"


def test_percentile_is_nearest_rank():
    assert summarize.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90) == 9
    assert summarize.percentile([5], 90) == 5


def test_failure_groups_are_largest_first_with_a_timeout_message(records):
    groups = summarize.failure_groups(summarize.demos_of(records))
    assert [k for k, _ in groups][0] == "[error] Unable to load atmospheric database!"
    assert [d for d, *_ in groups[0][1]] == ["Atm1", "Atm1", "Atm2"]
    timeout = dict(groups)["(no matching line; timeout)"]
    assert timeout[0][2].startswith("timed out after 1800.5 s")


def test_the_analysis(records):
    text = summarize.render(records, VERDICTS)
    assert text.startswith(summarize.BEGIN) and text.endswith(summarize.END)
    assert "9 demos, 10 attempts (1 of them repeats). The sweep ended: candidates exhausted." in text
    assert "| failed | 3 |" in text and "| rendered | 4 |" in text and "| skipped: dirsig4 | 1 |" in text
    assert "| [error] Unable to load atmospheric database! | 3 |" in text and "database x.adb.hdf" in text
    assert "median 15.0 s, 90th percentile 400.0 s, maximum 400.0 s" in text
    assert text.index("| Slow1 | demo.sim | 400.0 |") < text.index("| Fast1 | demo.sim | 4.0 |")
    assert "Identical outputs: 1 of 3 repeated demos (33 percent). Not repeated: Slow1 (not tested)." in text
    assert "| lidar .bin only | Lidar1 |" in text and "| truth images only | Truth1 |" in text
    assert "2 of 10 attempts reached 90 C" in text and "across 1 demos: Fast1." in text
    assert "1 first attempts wrote cache files into their per-run home (2 files, 3.00 MB): Fast1." in text
    assert "marks 4 demos `near`" in text and "2 of them now have a pass-through reference" in text
    assert text.index("| 1 | Fast1 | demo.sim | 4.0 | yes |") < text.index("| 2 | Truth1 | demo.jsim | 20.0 | no |")
    assert "`near` demos without a reference: Atm1 (failed), Indoors1 (not in the sweep)." in text


def test_the_tagged_table_marks_absent_demos(records):
    text = summarize.render_tags(records, VERDICTS, installed={"Fast1", "Ssa2"})
    assert "| SDA | Ssa2 | skipped: dirsig4 |" in text
    assert "| SDA | MoonSat1 | absent from the installation |" in text
    assert "| URSO | Indoors1 | not in the sweep | - | - | - | `near` | x |" in text


def test_main_rewrites_only_its_parts_and_the_tag_section_survives_survey_regeneration(tmp_path, records):
    results = tmp_path / "results.jsonl"
    results.write_text("".join(json.dumps(r) + "\n" for r in records) + '{"cut')
    report = tmp_path / "sweep.md"
    report.write_text("# Sweep\n\nBy hand.\n\n<!-- sweep_demos: x -->\ngenerated\n<!-- sweep_demos: end -->\n\n## Notes\n\nKept.\n")
    coverage = tmp_path / "coverage.md"
    coverage.write_text("# DIRSIG demo coverage\n\n| Fast1 | `near` | demo.sim | 1 | - | x |\n\n" + survey.KEPT
                        + "\n\nFindings by hand.\n")
    args = ["--results", str(results), "--report", str(report), "--coverage", str(coverage),
            "--dirsig-home", str(tmp_path / "none")]
    assert summarize.main(args) == 0
    text = report.read_text()
    assert text.startswith("# Sweep\n\nBy hand.\n\n<!-- sweep_demos: x -->\ngenerated\n") and "Kept.\n" in text
    assert summarize.BEGIN in text
    cov = coverage.read_text()
    assert cov.index(survey.KEPT) < cov.index("## Tagged demos") < cov.index(summarize.TAG_BEGIN)
    assert "Findings by hand." in cov and "| SDA | MoonSat1 | absent from the installation |" in cov
    assert summarize.main(args) == 0                                          # idempotent: one section, one analysis
    assert report.read_text() == text and coverage.read_text() == cov and cov.count("## Tagged demos") == 1
