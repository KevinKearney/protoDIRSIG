"""scripts/run_demo.py: argument handling and report-section preservation, with the stub engine (no DIRSIG, no demo)."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from test_passthrough import EXPECTED, PROFILE, RECIPE, VECTOR, stub_engine

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_demo", ROOT / "scripts" / "run_demo.py")
run_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_demo)


@pytest.fixture
def setup(tmp_path):
    root = tmp_path / "manifold_run_specs"
    for d in ("recipes", "engine_profiles", "scenarios"):
        (root / d).mkdir(parents=True)
    (tmp_path / "manifold_sensors").mkdir()
    (root / "recipes" / "demo_synthetic1_passthrough.yaml").write_text(RECIPE.replace("DIGEST", EXPECTED["digest"]))
    (root / "engine_profiles" / "passthrough_runtime.yaml").write_text(PROFILE)
    assets = tmp_path / "assets"
    shutil.copytree(VECTOR / "tree", assets / "demo_dirs" / "PassthroughVector")
    args = ["--library", str(root), "--config-repo", str(assets), "--engine", str(stub_engine(tmp_path)),
            "--work", str(tmp_path / "work")]
    return tmp_path, args


def test_a_run_is_measured_and_the_report_keeps_hand_written_sections(setup, capsys):
    tmp_path, args = setup
    report = tmp_path / "report.md"
    report.write_text("# DIRSIG demo reference runs\n\nIntro written by hand.\n\n" + run_demo.BEGIN + "\nold\n"
                      + run_demo.END + "\n\n## Notes\n\nKept as written.\n")
    assert run_demo.main(["Synthetic1", *args, "--repeat", "--report", str(report)]) == 0
    text = report.read_text()
    assert text.startswith("# DIRSIG demo reference runs\n\nIntro written by hand.\n\n")
    assert text.endswith("\n\n## Notes\n\nKept as written.\n") and "\nold\n" not in text
    assert "| Synthetic1 | `demo_synthetic1_passthrough` | rendered |" in text
    data = json.loads(run_demo.DATA.search(text).group(1))
    first = data["Synthetic1"]["first"]
    assert {o["name"] for o in first["outputs"]} >= {"demo-t0000-c0000.img", "demo-t0000-c0000.img.hdr"}
    assert first["engine_exit_status"] == 0 and first["engine_version"].startswith("stub-engine")
    assert data["Synthetic1"]["deterministic"] in ("yes", "no") and "second" in data["Synthetic1"]
    assert run_demo.main(["demo_synthetic1_passthrough", *args, "--report", str(report)]) == 0  # a second demo row
    data = json.loads(run_demo.DATA.search(report.read_text()).group(1))
    assert set(data) == {"Synthetic1", "demo_synthetic1_passthrough"} and report.read_text().endswith("Kept as written.\n")


def test_a_failed_run_is_a_result(setup, monkeypatch):
    tmp_path, args = setup
    monkeypatch.setenv("STUB_ENGINE_EXIT", "5")
    report = tmp_path / "r.md"
    assert run_demo.main(["Synthetic1", *args, "--report", str(report)]) == 1
    data = json.loads(run_demo.DATA.search(report.read_text()).group(1))
    first = data["Synthetic1"]["first"]
    assert first["state"] == "failed" and first["engine_exit_status"] == 5 and first["worker_log_tail"]
    assert "status 5" in " ".join(first["errors"]) and "Worker log tail" in report.read_text()


def test_a_timeout_cancels_the_run_and_is_recorded(setup, monkeypatch):
    tmp_path, args = setup
    monkeypatch.setenv("STUB_ENGINE_SLEEP", "30")
    result = run_demo.measure("Synthetic1", timeout=3, work=tmp_path / "work", library=args[1], config_repo=args[3],
                              engine=args[5])
    assert result["first"]["state"].startswith("timed out") and result["deterministic"] == "not tested"


@pytest.mark.parametrize("argv, message", [
    (["Brdf1", "--timeout", "0"], "--timeout must be positive"),
    (["Brdf1", "--timeout", "soon"], "invalid float"),
    (["Brdf1", "--work", str(ROOT / "outputs")], "outside the repository"),
    ([], "required"),
])
def test_argument_errors(argv, message, capsys):
    with pytest.raises(SystemExit) as e:
        run_demo.main(argv)
    assert e.value.code == 2 and message in capsys.readouterr().err


def test_an_unknown_demo_is_not_admitted(setup):
    tmp_path, args = setup
    result = run_demo.run_once("NoSuchDemo", tmp_path / "w", 10, args[1], args[3], args[5])
    assert result["state"] == "not admitted" and result["recipe"] == "demo_nosuchdemo_passthrough"
    assert "nosuchdemo" in result["error"].lower()
