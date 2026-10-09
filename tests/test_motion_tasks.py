"""protodirsig.motion_tasks must generate, from manifold_run_specs/auror_ref.yaml, motion and tasks files that
mean what the received AUROR_ref files meant.

The comparison is semantic, not textual: dirfm formats numbers differently from the received
files (`3.141593` vs `3.141592654`, `0.0` vs `0`), and the tasks reference is written in UTC
(`+00:00`) where the received file used `-08:00`, the same instant. Reads the run spec, manifold_config_repo
and tests/fixtures/auror_ref READ-ONLY; writes only to pytest's tmp_path.
"""
from datetime import datetime, timezone
from pathlib import Path

import lxml.etree as et
import pytest

from protodirsig.motion_tasks import generate_motion, generate_tasks
from protodirsig.run_spec import load_run_spec, resolve_auror_run

PROJECT = Path(__file__).resolve().parents[1]
SPEC = PROJECT / "manifold_run_specs" / "auror_ref.yaml"
CONFIG_REPO = PROJECT / "manifold_config_repo"
FIXTURE = PROJECT / "tests" / "fixtures" / "auror_ref"
pytestmark = pytest.mark.skipif(
    not ((CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene").is_file() and (FIXTURE / "motion").is_dir()),
    reason="manifold_config_repo or tests/fixtures/auror_ref not present")


def _motion(path):
    root = et.parse(str(path)).getroot()
    data = root.find("data")
    entries = data.findall("entry")
    return {
        "type": root.get("type"),
        "frame": data.get("rotationframe"), "order": data.get("rotationorder"),
        "units": data.get("angularunits"), "angletype": data.get("angletype"),
        "location_types": [e.find("position/location").get("type") for e in entries],
        "times": [float(e.findtext("datetime")) for e in entries],
        "positions": [[float(e.findtext(f"position/location/point/{k}")) for k in "xyz"] for e in entries],
        "angles": [[float(e.findtext(f"orientation/eulerangles/cartesiantriple/{k}")) for k in "xyz"] for e in entries],
    }


def _tasks(path):
    root = et.parse(str(path)).getroot()
    return {
        "epoch": datetime.fromisoformat(root.findtext("reference/datetime")).astimezone(timezone.utc),
        "windows": [(float(t.findtext("start/datetime")), float(t.findtext("stop/datetime")))
                    for t in root.findall("task")],
    }


@pytest.fixture
def generated(tmp_path):
    run = resolve_auror_run(load_run_spec(SPEC), SPEC, CONFIG_REPO)
    return generate_motion(run, tmp_path / "motion"), generate_tasks(run, tmp_path / "tasks")


def test_motion_matches_received(generated):
    gen, rec = _motion(generated[0]), _motion(FIXTURE / "motion" / "AurorMotion.ppd")
    for key in ("type", "frame", "order", "units", "angletype", "location_types", "times", "positions"):
        assert gen[key] == rec[key], key
    # dirfm writes angles to 6 decimals: 3.141592654 -> 3.141593 (a 3.5e-7 rad difference).
    assert len(gen["angles"]) == 1 and gen["angles"][0] == pytest.approx(rec["angles"][0], abs=5e-7)


def test_tasks_match_received(generated):
    gen, rec = _tasks(generated[1]), _tasks(FIXTURE / "tasks" / "AurorTask.tasks")
    assert gen["epoch"] == rec["epoch"] == datetime(2009, 7, 27, 19, 29, 32, tzinfo=timezone.utc)
    assert gen["windows"] == rec["windows"] == [(0.0, 0.0)]
    text = et.parse(str(generated[1])).getroot().findtext("reference/datetime")
    assert text.endswith("+00:00")                                  # same instant, printed in UTC


def test_generate_returns_written_paths(generated):
    motion, tasks = generated
    assert motion.is_file() and motion.suffix == ".ppd"
    assert tasks.is_file() and tasks.suffix == ".tasks"            # dirfm TASKS.write itself returns None
