"""The space-to-space scenario family (`scripts/s2s_scenarios.py`): deterministic grid, stable ids, valid specs, renders.

The grid and the specs are generated twice and compared; the committed specs, `index.json` and the generated target scene
(`manifold_config_repo/scenes/s2s_targets/`) must equal what the script writes; every spec passes the engine-free
checks with its run id as indexed. Two 16 x 16 renders (one thread): the hyperresolved plate at 25 km fills the window
with one value, and the Sun at 60 degrees zenith halves it; the plate seen 60 degrees off nadir stays centred. The
library and the committed files are read only; renders write to tmp_path.
"""
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from test_simulation import CONFIG_REPO, needs_dirsig

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("s2s_scenarios", ROOT / "scripts" / "s2s_scenarios.py")
s2s = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s2s)
_CO = importlib.util.spec_from_file_location("compare_outputs", ROOT / "scripts" / "compare_outputs.py")
compare_outputs = importlib.util.module_from_spec(_CO)
_CO.loader.exec_module(compare_outputs)


def test_the_grid_is_deterministic_and_names_are_unique():
    a, b = s2s.grid(), s2s.grid()
    assert a == b
    names = [s2s.point_name(p) for p in a]
    assert len(names) == len(set(names)) == len(a)
    assert s2s.family() == s2s.family()


def test_every_axis_value_appears_for_each_class_it_applies_to():
    points = s2s.grid()
    for axis, by_class in s2s.GRID.items():
        for cls, values in by_class.items():
            seen = {p[axis] for p in points if p["object_class"] == cls}
            if axis == "range_m" and cls == "unresolved":
                seen |= {s2s.ORBIT}               # the orbit point records the TLE's range instead
            assert set(values) <= seen | ({s2s.ORBIT} if axis == "relative_speed" else set()), (axis, cls)


def test_the_committed_family_and_scene_are_what_the_script_writes():
    scene = s2s.scene_files()
    on_disk = {str(p.relative_to(s2s.SCENE_DIR)): p.read_text() for p in s2s.SCENE_DIR.rglob("*") if p.is_file()}
    assert on_disk == scene
    files = s2s.family()
    committed = {p.name: p.read_text() for p in s2s.OUT.glob("*")}
    assert committed == files


def test_ids_are_stable_and_every_spec_validates():
    index = json.loads((s2s.OUT / "index.json").read_text())
    from manifold.core.identity import run_id
    for entry in index:
        spec = yaml.safe_load((s2s.OUT / f"{entry['name']}.yaml").read_text())
        assert run_id(spec, s2s.SENSORS) == entry["run_id"]
    assert s2s.validate(s2s.family()) == []


def test_the_geometry_follows_the_run_spec_numbers():
    f, p = s2s.sensor_numbers()
    assert f == 0.306 and p == pytest.approx(1e-5)
    assert s2s.footprint(25000.0) == pytest.approx(25000.0 * 1e-5 / 0.306)
    base = {"object_class": "hyperresolved", **s2s.BASELINE["hyperresolved"]}
    pos, angles = s2s.pose(base)
    assert pos == [0.0, 0.0, 25000.0] and angles == [0.0, 0.0, round(math.pi, 9)]
    pos, angles = s2s.pose({**base, "look_deg": 60.0})
    assert pos[0] == pytest.approx(-25000.0 * math.sin(math.radians(60))) and angles[1] == pytest.approx(math.radians(60))
    pos, _ = s2s.pose({**base, "offset_px": 0.5})
    assert pos[:2] == [pytest.approx(0.5 * s2s.footprint(25000.0))] * 2
    ex = s2s.expected({**base, "look_deg": 60.0, "solar_zenith_deg": 30.0})
    assert ex["projected_area_m2"] == pytest.approx(200.0) and ex["phase_deg"] == 90.0
    assert ex["cos_sun"] == pytest.approx(math.cos(math.radians(30)))


def _render(tmp_path, point, roi=16):
    from manifold.engines.dirsig.simulation import Simulation
    spec = s2s.run_spec(point)
    spec["descriptor"]["settings"][0]["roi"] = {"Width": roi, "Height": roi, "OffsetX": None, "OffsetY": None}
    path = tmp_path / f"{s2s.point_name(point)}.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    result = Simulation(path, CONFIG_REPO, work_dir=tmp_path / path.stem, sensor_library=s2s.SENSORS).run(threads=1)
    return compare_outputs.read_envi(result.image)[0]


@needs_dirsig
def test_a_16_by_16_render_of_the_hyperresolved_plate(tmp_path):
    base = {"object_class": "hyperresolved", **s2s.BASELINE["hyperresolved"]}
    full = _render(tmp_path, base)
    assert full.shape == (16, 16) and full.min() > 0                  # the 20 m plate fills the 13 m window
    assert full.max() == pytest.approx(full.min(), rel=1e-12)
    half = _render(tmp_path, {**base, "solar_zenith_deg": 60.0})
    assert half.max() == pytest.approx(half.min(), rel=1e-12)
    assert half[0, 0] / full[0, 0] == pytest.approx(0.5, rel=1e-3)


@needs_dirsig
def test_off_nadir_the_plate_stays_centred(tmp_path):
    base = {"object_class": "hyperresolved", **s2s.BASELINE["hyperresolved"], "range_m": 50000.0, "look_deg": 60.0}
    img = _render(tmp_path, base, roi=32)
    ys, xs = np.nonzero(img)
    assert len(ys) > 0
    assert abs(ys.mean() - 15.5) < 1.0 and abs(xs.mean() - 15.5) < 1.0
