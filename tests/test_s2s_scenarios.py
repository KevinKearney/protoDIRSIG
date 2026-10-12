"""The space-to-space scenario family (`scripts/s2s_scenarios.py`): deterministic grid, stable ids, valid specs, renders.

The grid and the specs are generated twice and compared; the committed specs, `index.json` and the generated target scene
(`manifold_config_repo/scenes/s2s_targets/`) must equal what the script writes; every spec passes the engine-free
checks with its run id as indexed. Two 16 x 16 renders (one thread): the hyperresolved plate at 25 km fills the window
with one value, and the Sun at 60 degrees zenith halves it; the plate seen 60 degrees off nadir stays centred. The
library and the committed files are read only; renders write to tmp_path.

Family II (round 30): its grid, its own scene (`scenes/s2s_blur/`) and its expectations; 16 x 16 renders show heading 90
moving a plate toward +x from the start of the exposure, and the orbit form holding its LookAt plate over 20 ms.

Family III (round 31): its grid spans the phase angle, its scene (`scenes/s2s_sun/`) and the sphere's expectation; a
16 x 16 render pair shows the Sun at solar azimuth 90 lighting the sphere from +x.

SatSim parity (round 31): the SatSim specs (pass-through, indexed with `engine: satsim`) and their generated
configurations state the shared geometry; a 16 x 16 SatSim run of the sphere at full phase holds the expected
photo-electrons (skipped where SatSim's interpreter or its assets are absent).
"""
import hashlib
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


# --- family II (round 30): blur groups, look group, orbit pair ---------------------------------------------------------

def test_family_two_is_deterministic_and_named_apart_from_family_one():
    a, b = s2s.grid2(), s2s.grid2()
    assert a == b
    names = [s2s.point2_name(p) for p in a]
    assert len(names) == len(set(names)) == len(a)
    assert not set(names) & {s2s.point_name(p) for p in s2s.grid()}
    exposures = {p["exposure_s"] for p in a if p["kind"] == "blur" and p["group"] != "static"}
    assert len(exposures) >= 4 and max(exposures) / min(exposures) >= 100          # four values over two decades
    assert {p["group"] for p in a if p["kind"] == "blur"} == set(s2s.BLUR_GROUPS)
    assert max(p["look_deg"] for p in a if p["kind"] == "look") >= 45 and \
        len({p["look_deg"] for p in a if p["kind"] == "look"}) >= 4


def test_family_two_specs_name_their_own_scene_and_family_one_is_unchanged():
    index = json.loads((s2s.OUT / "index.json").read_text())
    one = [e for e in index if "family" not in e]
    assert len(one) == len(s2s.grid())                   # family I's 63 entries, first, without a family key
    for p in s2s.grid2():
        spec = yaml.safe_load((s2s.OUT / f"{s2s.point2_name(p)}.yaml").read_text())
        assert spec["engine"]["scenes"][0]["ref"]["name"] == s2s.SCENE2_REF
        assert spec["descriptor"]["settings"][0]["exposure_time"]["value"] == p["exposure_s"]
        assert spec["resources"]["cpu_threads"] == 1
    on_disk = {str(q.relative_to(s2s.SCENE2_DIR)): q.read_text() for q in s2s.SCENE2_DIR.rglob("*") if q.is_file()}
    assert on_disk == s2s.scene2_files()


def test_family_two_expectations_follow_the_spec_numbers():
    g = s2s.footprint(s2s.BLUR["range_m"])
    gb = s2s.footprint(s2s.BLUR["range_m"] + s2s.BLUR["depth"])
    ex = s2s.expected2({"kind": "blur", "group": "both", "exposure_s": 0.02, "look_deg": 0.0})
    assert ex["target_blur_px"] == pytest.approx(2 * s2s.BLUR["speed"] * 0.02 / g)
    assert ex["background_blur_px"] == pytest.approx(s2s.BLUR["speed"] * 0.02 / gb)
    ex = s2s.expected2({"kind": "blur", "group": "target", "exposure_s": 0.02, "look_deg": 0.0})
    assert ex["background_blur_px"] == 0.0 and ex["target_blur_px"] == pytest.approx(24.48, rel=1e-4)
    ex = s2s.expected2({"kind": "look", "group": "look", "exposure_s": 0.005, "look_deg": 60.0})
    assert ex["projected_area_m2"] == pytest.approx(200.0)
    assert ex["background_footprint_m"] == pytest.approx(
        s2s.footprint(s2s.LOOK["range_m"] + s2s.LOOK["depth"] / math.cos(math.radians(60))))


def _render2(tmp_path, point, roi=16, position=None):
    from manifold.engines.dirsig.simulation import Simulation
    spec = s2s.run_spec2(point)
    spec["descriptor"]["settings"][0]["roi"] = {"Width": roi, "Height": roi, "OffsetX": None, "OffsetY": None}
    if position is not None:
        spec["engine"]["motion"]["position"]["xyz"] = position
    path = tmp_path / f"{s2s.point2_name(point)}.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    result = Simulation(path, CONFIG_REPO, work_dir=tmp_path / path.stem, sensor_library=s2s.SENSORS).run(threads=1)
    return compare_outputs.read_envi(result.image)[0]


@needs_dirsig
def test_heading_90_moves_the_plate_toward_plus_x_from_the_start_of_the_exposure(tmp_path):
    """The window is centred on the 20 m plate's -x edge. Static: half the window is plate. The target group at 20 ms
    (1000 m/s, heading 90): if the plate moves toward +x from the task time it leaves the window (mean about 0.08 of a
    full pixel); toward -x, or over a window centred on the task time, the mean would be about 0.84 or 0.5."""
    z = s2s.BLUR["base_z"] + s2s.BLUR["depth"] + s2s.BLUR["range_m"]
    half = s2s.PLATES["hyperresolved"]["side"] / 2
    still = _render2(tmp_path, {"kind": "blur", "group": "static", "exposure_s": 0.005, "look_deg": 0.0},
                     position=[s2s.BLUR_GROUPS["static"][0] - half, 0.0, z])
    full = still.max()
    assert still.mean() / full == pytest.approx(0.5, abs=0.07)
    moved = _render2(tmp_path, {"kind": "blur", "group": "target", "exposure_s": 0.02, "look_deg": 0.0},
                     position=[s2s.BLUR_GROUPS["target"][0] - half, 0.0, z])
    assert 0.02 < moved.mean() / (4 * full) < 0.25


@needs_dirsig
def test_the_orbit_form_holds_its_lookat_point_through_the_exposure(tmp_path):
    short = _render2(tmp_path, {"kind": "orbit", "group": "orbit", "exposure_s": 0.0001, "look_deg": None})
    long = _render2(tmp_path, {"kind": "orbit", "group": "orbit", "exposure_s": 0.02, "look_deg": None})
    assert short.sum() > 0
    assert np.array_equal(short > 0, long > 0)                       # the same pixels: no streak over 20 ms
    assert long.sum() / short.sum() == pytest.approx(200.0, rel=1e-6)


@needs_dirsig
def test_sixty_degrees_off_nadir_the_plate_is_foreshortened_by_the_cosine(tmp_path):
    """The 20 m plate 60 degrees off nadir at 25 km: 24.48 pixels along y fill the 16-row window, and 12.24 pixels
    along x lie inside it, so the window sums to 16 x 12.24 full pixels (the background behind is black)."""
    img = _render2(tmp_path, {"kind": "look", "group": "look", "exposure_s": 0.005, "look_deg": 60.0})
    full = img.max()
    ex = s2s.expected2({"kind": "look", "group": "look", "exposure_s": 0.005, "look_deg": 60.0})
    assert img.sum() / full == pytest.approx(16 * ex["side_px"] * 0.5, rel=0.01)


# --- family III (round 31): Lambertian spheres, Sun and phase angle --------------------------------------------------

def test_family_three_spans_the_phase_angles_and_names_its_own_scene():
    a, b = s2s.grid3(), s2s.grid3()
    assert a == b
    names = [s2s.point3_name(p) for p in a]
    assert len(names) == len(set(names)) == len(a)
    assert not set(names) & ({s2s.point_name(p) for p in s2s.grid()} | {s2s.point2_name(p) for p in s2s.grid2()})
    for group in ("hyperresolved", "unresolved"):
        phases = sorted({p["look_deg"] + p["solar_zenith_deg"] for p in a if p["group"] == group})
        assert len(phases) >= 8 and phases[0] <= 5 and phases[-1] >= 145, (group, phases)
    assert {p["solar_zenith_deg"] for p in a if p["kind"] == "background"} >= {0.0, 60.0}
    index = {e["name"]: e for e in json.loads((s2s.OUT / "index.json").read_text())}
    for p in a:
        spec = yaml.safe_load((s2s.OUT / f"{s2s.point3_name(p)}.yaml").read_text())
        assert spec["engine"]["scenes"][0]["ref"]["name"] == s2s.SCENE3_REF
        assert index[s2s.point3_name(p)]["family"] == 3
        sun = spec["engine"]["atmosphere"]["uniform"]["fixed_ephemeris"]
        assert sun["solar_zenith"] == p["solar_zenith_deg"] and sun["solar_azimuth"] == 90.0
    on_disk = {str(q.relative_to(s2s.SCENE3_DIR)): q.read_text() for q in s2s.SCENE3_DIR.rglob("*") if q.is_file()}
    assert on_disk == s2s.scene3_files()
    assert "<sphere>" in on_disk["geometry/lists/targets.glist"]


def test_the_lambertian_sphere_expectation():
    assert s2s.phase_function(0.0) == pytest.approx(1.0)
    assert s2s.phase_function(90.0) == pytest.approx(1 / math.pi)
    assert s2s.phase_function(180.0) == pytest.approx(0.0, abs=1e-12)
    ex = s2s.expected3({"kind": "phase", "group": "hyperresolved", "look_deg": 30.0, "solar_zenith_deg": 30.0})
    g = s2s.footprint(s2s.SUN3["range_m"])
    assert ex["phase_deg"] == 60.0
    assert ex["full_phase_px"] == pytest.approx(2 / 3 * math.pi * 10.0 ** 2 / g ** 2)
    assert ex["expected_px"] == pytest.approx(ex["full_phase_px"] * s2s.phase_function(60.0))


def _render3(tmp_path, point, roi=16):
    from manifold.engines.dirsig.simulation import Simulation
    spec = s2s.run_spec3(point)
    spec["descriptor"]["settings"][0]["roi"] = {"Width": roi, "Height": roi, "OffsetX": None, "OffsetY": None}
    path = tmp_path / f"{s2s.point3_name(point)}.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    result = Simulation(path, CONFIG_REPO, work_dir=tmp_path / path.stem, sensor_library=s2s.SENSORS).run(threads=1)
    return compare_outputs.read_envi(result.image)[0]


@needs_dirsig
def test_the_sun_lights_the_sphere_from_plus_x(tmp_path):
    """The 10 m sphere at nadir, 16 x 16 pixels (about 13 m) about its centre. With the Sun at the zenith the image is
    symmetric; with the Sun 60 degrees from the zenith toward +x (solar azimuth 90) the terminator lies 5 m toward -x
    from the centre, so the columns toward -x (increasing column) are dark and those toward +x lit."""
    point = {"kind": "phase", "group": "hyperresolved", "look_deg": 0.0, "solar_zenith_deg": 0.0}
    full = _render3(tmp_path, point)
    assert full.min() > 0 and full[:, :8].sum() == pytest.approx(full[:, 8:].sum(), rel=0.02)
    side = _render3(tmp_path, {**point, "solar_zenith_deg": 60.0})
    assert side[:, :4].mean() > 0.5 * full.max()
    assert side[:, 15].mean() < 0.01 * side[:, :4].mean()


# --- SatSim parity (round 31): the same geometry as SatSim configurations ---------------------------------------------

def test_the_satsim_specs_state_the_shared_geometry_in_their_configurations():
    """Each SatSim spec is pass-through (an opaque descriptor: the shared numbers can only be extras) and indexed apart
    from the DIRSIG families; its configuration puts the observer 25 km from the target at the phase angle from the Sun's
    direction, both on the same velocity, and states the sensor's field of view, exposure and zeropoint."""
    index = {e["name"]: e for e in json.loads((s2s.OUT / "index.json").read_text())}
    nums = s2s.satsim_numbers()
    assert nums["ifov_rad"] == pytest.approx(1e-5 / 0.306)
    assert nums["cone_factor"] == pytest.approx(1 / (1 + 1 / (4 * (306 / 85) ** 2)))
    phases = set()
    for p in s2s.satsim_grid():
        name = s2s.satsim_name(p)
        spec = yaml.safe_load((s2s.OUT / f"{name}.yaml").read_text())
        assert index[name]["engine"] == "satsim" and index[name]["family"] == "satsim"
        assert spec["engine"]["mode"] == "passthrough" and spec["descriptor"]["origin"]["engine"] == "satsim"
        assert set(spec["descriptor"]) == {"meta", "origin", "fidelity", "opaque", "extras"}
        cfg = s2s.satsim_config(p)
        assert cfg["fpa"]["time"]["exposure"] == p["exposure_s"] == spec["descriptor"]["extras"]["s2s.exposure_s"]
        assert cfg["fpa"]["y_fov"] == pytest.approx(math.degrees(500 * nums["ifov_rad"]), rel=1e-8)
        t = np.array(cfg["geometry"]["obs"]["list"][0]["position"])
        o = np.array(cfg["geometry"]["site"]["position"])
        assert np.linalg.norm(o - t) == pytest.approx(25.0, rel=1e-9)
        cos_a = np.dot(o - t, s2s.SUN_GCRS) / np.linalg.norm(o - t)
        assert math.degrees(math.acos(min(1.0, cos_a))) == pytest.approx(p["phase_deg"], abs=1e-4)
        assert cfg["geometry"]["obs"]["list"][0]["velocity"] == cfg["geometry"]["site"]["velocity"]
        phases.add(p["phase_deg"])
    assert len(phases) >= 3
    on_disk = {str(q.relative_to(s2s.SATSIM_DIR)): q.read_bytes() for q in s2s.SATSIM_DIR.rglob("*") if q.is_file()}
    assert on_disk == s2s.satsim_files()


def _fits_image(path):
    """The primary image of a FITS file (BITPIX -32, 16 or 32, with BZERO and BSCALE), read without astropy."""
    raw = path.read_bytes()
    cards, at = {}, 0
    while True:
        block = raw[at:at + 2880].decode("ascii")
        at += 2880
        for i in range(0, 2880, 80):
            card = block[i:i + 80]
            if card[:8].strip() == "END":
                break
            if card[8:10] == "= ":
                cards[card[:8].strip()] = card[10:].split("/")[0].strip()
        else:
            continue
        break
    dtype = {"-32": ">f4", "16": ">i2", "32": ">i4"}[cards["BITPIX"]]
    shape = (int(cards["NAXIS2"]), int(cards["NAXIS1"]))
    data = np.frombuffer(raw, dtype=dtype, count=shape[0] * shape[1], offset=at).reshape(shape).astype(float)
    return data * float(cards.get("BSCALE", 1)) + float(cards.get("BZERO", 0))


def _satsim_why_not():
    from test_satsim_integration import WHY_NOT
    return WHY_NOT


@pytest.mark.satsim
def test_a_16_by_16_satsim_run_of_the_sphere_at_full_phase(tmp_path):
    """The sphere at full phase on a 16 x 16 focal plane (the same IFOV, no PSF), through LocalBackend: the frame holds
    the expected photo-electrons, (2/3) pi R^2 / footprint^2 full pixels at the paraxial rate, to one count, in one pixel
    near the centre."""
    why = _satsim_why_not()
    if why:
        pytest.skip(why)
    from backend_conformance import wait_for
    from manifold.sim.backend import LocalBackend
    p = s2s.satsim_grid()[0]
    assert p["phase_deg"] == 0.0 and p["target"] == "sphere"
    cfg = s2s.satsim_config(p)
    nums = s2s.satsim_numbers()
    cfg["fpa"]["height"] = cfg["fpa"]["width"] = 16
    cfg["fpa"]["y_fov"] = cfg["fpa"]["x_fov"] = math.degrees(16 * nums["ifov_rad"])
    cfg["fpa"]["psf"] = {"mode": "none"}         # every photo-electron in one pixel: the frame keeps them all
    lib = tmp_path / "library"
    (lib / "satsim" / "assets").mkdir(parents=True)
    for name in ("de421.bsp", "finals2000A.all"):
        (lib / "satsim" / "assets" / name).symlink_to((CONFIG_REPO / "satsim" / "assets" / name).resolve())
    path = lib / "satsim" / "sphere.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    spec = s2s.satsim_spec(p)
    spec["engine"]["config"] = {"name": "satsim/sphere.yaml",
                                "content_hash": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()}
    (tmp_path / "spec.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))
    backend = LocalBackend(tmp_path / "work", lib)
    final = wait_for(backend, backend.submit_run(str(tmp_path / "spec.yaml"))["run_id"], ("rendered", "failed"),
                     timeout=300)
    assert final["state"] == "rendered", final["errors"]
    frame = next(a for a in final["artifacts"] if a["name"].startswith("ImageFiles_") and a["name"].endswith(".fits"))
    img = _fits_image(Path(frame["uri"].removeprefix("file://")))
    g = s2s.footprint(s2s.SATSIM["range_m"])
    expected = 2 / 3 * math.pi * s2s.SATSIM["sphere_radius_m"] ** 2 / g ** 2 * nums["full_pixel_pe_per_s"] * p["exposure_s"]
    assert abs(img.sum() - expected) <= 1.0 and (img > 0).sum() == 1
    r, c = np.unravel_index(img.argmax(), img.shape)
    assert 6 <= r <= 9 and 6 <= c <= 9
