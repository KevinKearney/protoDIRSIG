"""engine.motion kind `orbit` (proposed): resolution, refusals, schema checks, generated waypoints, hash checks.

The composed pass spec (manifold_run_specs/leo_pass_tahoe.yaml) is the valid case; each refusal edits one field.
The waypoint test generates the pinned TLE's track over the golden vector's window and compares it to the vector.
"""
import copy
import json
import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from protodirsig import orbit
from protodirsig.motion_tasks import generate_motion, orbit_waypoints
from protodirsig.run_spec import RunSpecError, _check_orbit_files, check_library_files, load_run_spec, resolve_auror_run
from protodirsig.simulation import schema_errors

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "manifold_run_specs" / "leo_pass_tahoe.yaml"
STATIC = ROOT / "manifold_run_specs" / "auror_ref.yaml"
CONFIG_REPO = ROOT / "manifold_config_repo"
VECTOR = ROOT / "manifold_contracts" / "vectors" / "orbit"
needs_config_repo = pytest.mark.skipif(not (CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene").is_file(),
                                       reason="manifold_config_repo not present")


def _spec():
    return load_run_spec(SPEC)


@needs_config_repo
def test_orbit_spec_resolves():
    run = resolve_auror_run(_spec(), SPEC, CONFIG_REPO)
    o = run.orbit
    assert run.motion_kind == "orbit" and run.motion_position is None and run.motion_orientation is None
    assert o["tle"] == CONFIG_REPO / "orbit" / "worldview2_35946.tle" and o["propagator"] == "skyfield_sgp4"
    assert o["earth_orientation"] == CONFIG_REPO / "orbit" / "iers.npz"
    assert (o["window_start"], o["window_duration"], o["waypoint_spacing"]) == (0.0, 120.0, 1.0)
    assert o["lookat_target"] == [-400.0, 400.0, 132.0] and o["up"] == "along_track"
    assert o["scene_origin"] == (39.0, -120.0)
    assert run.tasks_windows == [(50.0, 50.0), (60.0, 60.0), (70.0, 70.0)]
    assert check_library_files(_spec(), run) == []


@needs_config_repo
def test_static_spec_still_resolves_as_before():
    run = resolve_auror_run(load_run_spec(STATIC), STATIC, CONFIG_REPO)
    assert run.motion_kind == "static" and run.orbit is None and run.motion_position == [-400.0, 400.0, 550000.0]


def _edit(path, value):
    spec = _spec()
    d = spec["engine"]
    for k in path[:-1]:
        d = d[k]
    if value is KeyError:
        del d[path[-1]]
    else:
        d[path[-1]] = value
    return spec


@needs_config_repo
@pytest.mark.parametrize("path, value, match", [
    (("motion", "orbit"), KeyError, "engine.motion.orbit is missing"),
    (("motion", "orbit", "propagator"), "dirsig_sgp4", "propagator is 'dirsig_sgp4'"),
    (("motion", "orbit", "tle"), {"name": "orbit/absent.tle"}, "orbit TLE 'orbit/absent.tle' not found"),
    (("motion", "orbit", "earth_orientation"), "iers.npz", "earth_orientation must be a library ref"),
    (("motion", "orbit", "window"), {"start": 0.0, "duration": 0.0}, "duration > 0"),
    (("motion", "orbit", "window"), {"start": 55.0, "duration": 120.0}, r"windows\[0\] \[50.0, 50.0\] is outside"),
    (("motion", "orbit", "window"), {"start": 0.0, "duration": 120.5}, "not a whole number"),
    (("motion", "orbit", "waypoint_spacing"), -1.0, "positive number of seconds"),
    (("motion", "orientation", "kind"), "euler", "pointed by 'lookat'"),
    (("motion", "orientation", "lookat", "up"), [0, 0, 1], "only 'along_track'"),
    (("motion", "orientation", "lookat", "frame"), "ecef", "frame: sceneenu"),
    (("motion", "orientation", "lookat", "target"), [0.0, 0.0], "frame: sceneenu, target"),
    (("motion", "kind"), "waypoints", "'waypoints' .* is not built"),
])
def test_orbit_refusals(path, value, match):
    with pytest.raises(RunSpecError, match=match):
        resolve_auror_run(_edit(path, value), SPEC, CONFIG_REPO)


def test_composed_orbit_spec_passes_the_schema_checks():
    assert schema_errors(_spec()) == []


@pytest.mark.parametrize("path, value, match", [
    (("motion", "orbit", "tle"), KeyError, r"^/engine/motion/orbit: 'tle' is a required property"),
    (("motion", "orbit", "propagator"), "other", r"^/engine/motion/orbit/propagator: 'other' is not one of"),
    (("motion", "orbit", "window"), {"start": 0}, r"^/engine/motion/orbit/window: 'duration' is a required property"),
    (("motion", "orbit", "waypoint_spacing"), 0, r"^/engine/motion/orbit/waypoint_spacing: 0 is less than or equal to"),
    (("motion", "orientation", "kind"), "euler", r"^/engine/motion/orientation/kind: 'lookat' was expected"),
    (("motion", "orientation", "lookat", "up"), "velocity", r"^/engine/motion/orientation/lookat/up: 'velocity' is not one of"),
    (("motion", "orientation", "lookat", "target"), "origin", r"^/engine/motion/orientation/lookat/target: 'origin' is not of type 'array'"),
])
def test_orbit_schema_errors(path, value, match):
    errs = schema_errors(_edit(path, value))
    assert any(re.search(match, e) for e in errs), errs


def _vector_run(tmp_path):
    want = json.loads((VECTOR / "expected.json").read_text())
    epoch = datetime.fromisoformat(want["epoch_utc"].replace("Z", "+00:00"))
    run = SimpleNamespace(motion_kind="orbit", epoch=epoch, orbit={
        "tle": VECTOR / "tle_35946.txt", "earth_orientation": orbit.bundled_eop_path(), "propagator": "skyfield_sgp4",
        "window_start": 0.0, "window_duration": 120.0, "waypoint_spacing": 1.0,
        "lookat_target": [0.0, 0.0, 0.0], "up": "along_track", "scene_origin": (39.0, -120.0)})
    return run, want


def test_generated_waypoints_match_the_golden_vector(tmp_path):
    run, want = _vector_run(tmp_path)
    t_wp, pos_wp, up, err = orbit_waypoints(run)
    assert np.array_equal(t_wp, want["t_s"])
    assert np.linalg.norm(pos_wp - np.array(want["itrs_m"]), axis=1).max() < want["tolerance_m"]
    assert err < 1.5 and abs(np.linalg.norm(up) - 1) < 1e-5 and up[2] == 0.0
    # and the written FlexMotion file carries the same waypoints
    path = generate_motion(run, tmp_path / "motion")
    text = path.read_text()
    assert path.name == "motion.motion" and 'type="waypoints"' in text and 'frame="ecef"' in text
    assert 'type="lookat"' in text
    rows = re.search(r"<!\[CDATA\[(.*?)\]\]>", text, re.S).group(1).split()
    table = np.array([[float(v) for v in r.split(",")] for r in rows])
    assert np.array_equal(table[:, 0], want["t_s"])
    assert np.linalg.norm(table[:, 1:] - np.array(want["itrs_m"]), axis=1).max() < want["tolerance_m"]


def test_library_eop_copy_is_the_bundled_tables():
    lib = CONFIG_REPO / "orbit" / "iers.npz"
    if not lib.is_file():
        pytest.skip("manifold_config_repo not present")
    assert lib.read_bytes() == orbit.bundled_eop_path().read_bytes(), \
        "skyfield's bundled tables changed; recopy them and restamp, or pin skyfield"


def _repo_with_orbit_copy(tmp_path):
    """A config repo of symlinks to the real one, except orbit/, which is a copy that a test may edit."""
    repo = tmp_path / "config_repo"
    repo.mkdir()
    for p in CONFIG_REPO.iterdir():
        if p.name != "orbit":
            (repo / p.name).symlink_to(p)
    (repo / "orbit").mkdir()
    for f in (CONFIG_REPO / "orbit").iterdir():
        (repo / "orbit" / f.name).write_bytes(f.read_bytes())
    return repo


@needs_config_repo
def test_a_changed_tle_byte_fails_hash_verification(tmp_path):
    repo = _repo_with_orbit_copy(tmp_path)
    resolve_auror_run(_spec(), SPEC, repo)                                  # unchanged copy resolves
    tle = repo / "orbit" / "worldview2_35946.tle"
    data = bytearray(tle.read_bytes())
    i = data.index(b"98.4713")
    data[i + 6] = ord("4")                                                    # 98.4713 -> 98.4714
    tle.write_bytes(bytes(data))
    with pytest.raises(RunSpecError, match="orbit TLE worldview2_35946.tle: content_hash .* does not match"):
        resolve_auror_run(_spec(), SPEC, repo)


def test_an_unparseable_tle_is_a_library_problem(tmp_path):
    bad = tmp_path / "bad.tle"
    lines = (VECTOR / "tle_35946.txt").read_text().splitlines()
    lines[3] = lines[3][:-1] + str((int(lines[3][-1]) + 1) % 10)             # break line 2's checksum
    bad.write_text("\n".join(lines) + "\n")
    o = {"tle": bad, "earth_orientation": orbit.bundled_eop_path()}
    assert len(_check_orbit_files(o)) == 1 and "not a valid two-line element set" in _check_orbit_files(o)[0]
    o = {"tle": VECTOR / "tle_35946.txt", "earth_orientation": bad}
    assert "do not load" in _check_orbit_files(o)[0]
    assert _check_orbit_files(copy.deepcopy({"tle": VECTOR / "tle_35946.txt",
                                             "earth_orientation": orbit.bundled_eop_path()})) == []
