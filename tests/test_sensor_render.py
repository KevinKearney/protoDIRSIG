"""The generated `.platform` as DIRSIG uses it: dry-run validation of each library sensor, and small renders
(16 x 16 window, a few seconds each) that test the generator's conventions against DIRSIG itself.

- A tabulated unit-peak gaussian (width = FWHM / 2.3548, sigma) differs from DIRSIG's native gaussian channel
  only by the factor sqrt(2 pi) at every pixel: the native shape has the same width, and its amplitude
  is a standard-normal density (peak 1/sqrt(2 pi)). A tabulated response with normalize="false" is absolute.
- Folding the optics throughput into the channel (aperturethroughput 1) equals the scalar aperturethroughput:
  the factors multiply, so a scalar and a curve are not both applied.
- QE scales the image linearly.
- DIRSIG's native rectangular channel has unit amplitude, and an edge on a bandpass grid point weighs 1/2,
  as `srf_model_values` writes it.
- A two-channel entry renders a two-band image whose bands equal the single-channel renders; the window's
  offset in the full frame places it where it sits in a larger window.
"""
import os
import shutil
from pathlib import Path

import numpy as np
import pytest
import yaml

from protodirsig.run_spec import derive_run_spec, load_run_spec
from protodirsig.simulation import Simulation

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "run_specs" / "auror_ref.yaml"
CONFIG_REPO = ROOT / "config_repo"
LIB = ROOT / "sensors"
DIRSIG_HOME = Path(os.environ.get("DIRSIG_HOME", Path.home() / "DIRSIG" / "dirsig-2026.38.0.a020954-Linux-x86_64"))


def _dirsig_on_path():
    os.environ.setdefault("DIRSIG_HOME", str(DIRSIG_HOME))
    if (DIRSIG_HOME / "bin").is_dir() and str(DIRSIG_HOME / "bin") not in os.environ["PATH"].split(os.pathsep):
        os.environ["PATH"] = f"{DIRSIG_HOME / 'bin'}{os.pathsep}{os.environ['PATH']}"
    return shutil.which("dirsig5") and shutil.which("scene2hdf")


needs_dirsig = pytest.mark.skipif(
    not ((CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene").is_file() and _dirsig_on_path()),
    reason="config_repo or DIRSIG not present")

HDR = """# spectral-curve/1
# name: {name}
# quantity: {quantity}
# x: wavelength_um
# range_um: 0.150 14.000
# interpolation: linear
# extrapolation: none
# provenance: synthetic
wavelength_um,{col}
"""


def constant_curve(lib, kind, value):
    name = f"const_{str(value).replace('.', 'p')}"
    path = lib / "spectral" / kind / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    quantity, col = ("qe_absolute", "qe") if kind == "qe" else ("transmission", "transmission")
    path.write_text(HDR.format(name=name, quantity=quantity, col=col)
                    + "".join(f"{n / 1000:.3f},{value}\n" for n in range(150, 14001)))
    return {"name": f"spectral/{kind}/{name}.csv"}


def step_curve(lib, name, lo, hi):
    """QE 1 for lo <= wavelength < hi, else 0, on the 1 nm grid."""
    path = lib / "spectral" / "qe" / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HDR.format(name=name, quantity="qe_absolute", col="qe")
                    + "".join(f"{n / 1000:.3f},{1 if lo <= n / 1000 < hi else 0}\n" for n in range(150, 14001)))
    return {"name": f"spectral/qe/{name}.csv"}


def variant(tmp_path, edit):
    """A copy of the sensor library whose `variant.yaml` is auror-nir with `edit(entry)` applied."""
    lib = tmp_path / "sensors"
    shutil.copytree(LIB, lib)
    doc = yaml.safe_load((LIB / "auror-nir.yaml").read_text())
    entry = doc["sensor"]["entries"][0]
    edit(lib, entry, entry["focal_planes"][0]["channels"][0])
    doc["meta"]["name"] = "variant"
    (lib / "variant.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    return lib


def simulation(tmp_path, lib, ref="variant.yaml", entry_id="auror-nir", roi=None, tag="r", native=False, edit=None):
    spec = derive_run_spec(load_run_spec(SPEC), ref, entry_id, roi=roi or {"Width": 16, "Height": 16}, name=tag)
    if native:
        spec["engine"]["platform"]["channel_response"] = "native"
    if edit:
        edit(spec)
    work = tmp_path / tag
    work.mkdir()
    (work / "spec.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))
    return Simulation.from_run_spec(work / "spec.yaml", CONFIG_REPO, work_dir=work / "w", sensor_library=lib)


def render(tmp_path, lib, ref="variant.yaml", entry_id="auror-nir", roi=None, tag="r", native=False, truth=False):
    roi = roi or {"Width": 16, "Height": 16}
    out = simulation(tmp_path, lib, ref, entry_id, roi, tag, native).run()
    if truth:     # geodetic lat, lon, alt; ECEF x, y, z
        return np.fromfile(out.truth[0], dtype="<f8").reshape(roi["Height"], roi["Width"], 6)
    return np.fromfile(out.image, dtype="<f8")


@pytest.fixture(scope="module")
def baseline(tmp_path_factory):
    # pytest's own temp root (kept for the last three sessions), not a mkdtemp that nothing removes
    return render(tmp_path_factory.mktemp("base"), LIB, "auror-nir.yaml", tag="base")


@needs_dirsig
@pytest.mark.parametrize("spec_name, ref, entry_id", [
    ("auror_ref.yaml", None, None),
    ("synthetic_vis.yaml", None, None),
    ("auror_ref.yaml", "deepscan_850_306_nir_1280.yaml", "deepscan-850-306-nir-1280"),
], ids=["auror-nir", "synthetic-vis", "deepscan"])
def test_each_library_sensor_validates(tmp_path, spec_name, ref, entry_id):
    spec = load_run_spec(ROOT / "run_specs" / spec_name)
    if ref:
        spec = derive_run_spec(spec, ref, entry_id)
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    c = Simulation.from_run_spec(path, CONFIG_REPO, tmp_path / "work", LIB).validate()
    assert (c.schema_ok, c.resolution_ok, c.execution_ok) == (True, True, True), c


@needs_dirsig
def test_native_gaussian_is_unit_peak_over_sqrt_two_pi(tmp_path, baseline):
    native = render(tmp_path, LIB, "auror-nir.yaml", tag="native", native=True)
    ratio = baseline / native
    np.testing.assert_allclose(ratio, np.sqrt(2.0 * np.pi), rtol=1e-4)      # constant over pixels: same shape and width


@needs_dirsig
def test_unity_qe_equals_no_qe(tmp_path, baseline):
    lib = variant(tmp_path, lambda lib, e, ch: ch.update(qe_reference=constant_curve(lib, "qe", 1.0)))
    np.testing.assert_allclose(render(tmp_path, lib, tag="unity"), baseline, rtol=1e-6)


@needs_dirsig
def test_folded_optics_equals_scalar_throughput(tmp_path, baseline):
    def edit(lib, e, ch):
        e["optics"]["throughput_reference"] = constant_curve(lib, "optics", 0.875)   # scalar is 0.875
    img = render(tmp_path, variant(tmp_path, edit), tag="fold")
    np.testing.assert_allclose(img, baseline, rtol=1e-4)


@needs_dirsig
def test_qe_scales_linearly(tmp_path, baseline):
    lib = variant(tmp_path, lambda lib, e, ch: ch.update(qe_reference=constant_curve(lib, "qe", 0.5)))
    np.testing.assert_allclose(render(tmp_path, lib, tag="half"), 0.5 * baseline, rtol=1e-4)


@needs_dirsig
@pytest.mark.parametrize("ref, entry_id, pitch_um, focal_mm", [
    ("auror-nir.yaml", "auror-nir", 10.0, 306.0),
    ("synthetic_600_200_vis_1920.yaml", "synthetic-600-200-vis-1920", 5.5, 200.0),
    ("deepscan_850_306_nir_1280.yaml", "deepscan-850-306-nir-1280", 10.0, 306.0),
], ids=["auror-nir", "synthetic-vis", "deepscan"])
def test_ground_sample_distance_is_pitch_over_focal_length_times_range(tmp_path, ref, entry_id, pitch_um, focal_mm):
    """Adjacent-pixel horizontal spacing of the GeoLocation truth equals (pitch / focal length) x range, nadir
    view. Horizontal: the vertical component of the ECEF difference (terrain relief) is projected out."""
    ecef = render(tmp_path, LIB, ref, entry_id, tag="gsd", truth=True)
    alt, xyz = ecef[..., 2], ecef[..., 3:6]
    up = xyz / np.linalg.norm(xyz, axis=-1, keepdims=True)

    def horizontal(d, u):
        return np.linalg.norm(d - (d * u).sum(-1, keepdims=True) * u, axis=-1).ravel()
    d = np.concatenate([horizontal(np.diff(xyz, axis=0), up[:-1]), horizontal(np.diff(xyz, axis=1), up[:, :-1])])
    rng = 550000.0 - np.median(alt)                         # platform altitude from the run spec; scene origin at 0 m
    assert np.median(d) == pytest.approx(pitch_um * 1e-6 / (focal_mm * 1e-3) * rng, rel=0.01)


@needs_dirsig
def test_complementary_qe_windows_sum_to_the_full_band(tmp_path, baseline):
    """The response is integrated linearly over wavelength: two QE windows that partition the band give images
    that sum to the unit-QE image."""
    def window(lo, hi, tag):
        lib = variant(tmp_path / tag, lambda lib, e, ch: ch.update(qe_reference=step_curve(lib, tag, lo, hi)))
        return render(tmp_path / tag, lib, tag=tag)
    for tag in ("lo", "hi"):
        (tmp_path / tag).mkdir()
    lo, hi = window(0.0, 0.85, "lo"), window(0.85, 99.0, "hi")
    assert (lo > 0).all() and (hi > 0).all()
    np.testing.assert_allclose(lo + hi, baseline, rtol=1e-4)


@needs_dirsig
def test_native_rectangular_is_unit_peak_with_half_weight_edges(tmp_path):
    """Grid-aligned edges (0.775, 0.925 um on the 1 nm bandpass): native equals the tabulated rectangle whose
    edge samples are 1/2. Inclusive edges would be 0.6 % brighter, exclusive 0.6 % darker."""
    lib = variant(tmp_path, lambda lib, e, ch: ch.update(srf_model={"kind": "rectangular", "center": 0.85, "width": 0.15}))
    native = render(tmp_path, lib, tag="native", native=True)
    np.testing.assert_allclose(render(tmp_path, lib, tag="tab"), native, rtol=2e-5)


B2 = {"channel_id": "nir-b2", "band": "SWIR", "band_center": 1.25, "bandwidth": 0.1,
      "srf_model": {"kind": "gaussian", "center": 1.25, "fwhm": 0.1},
      "radiometric_reference": {"quantity": "electron_exposure", "unit": "e-/m2"}}


@needs_dirsig
def test_two_channel_entry_renders_two_bands(tmp_path, baseline):
    """Each band of a two-channel render equals the single-channel render of that channel, value for value
    (one spectral state for the focal plane: `split_channels` false)."""
    (tmp_path / "lib2").mkdir()
    (tmp_path / "lib_b2").mkdir()
    two = variant(tmp_path / "lib2", lambda lib, e, ch: e["focal_planes"][0]["channels"].append(dict(B2)))
    only_b2 = variant(tmp_path / "lib_b2", lambda lib, e, ch: e["focal_planes"][0].update(channels=[dict(B2)]))
    out = simulation(tmp_path, two, tag="two").run()
    hdr = Path(f"{out.image}.hdr").read_text()
    assert "bands = 2" in hdr and "nir-b1,nir-b2" in hdr
    img = np.fromfile(out.image, dtype="<f8").reshape(16, 16, 2)             # BIP
    np.testing.assert_array_equal(img[..., 0].ravel(), baseline)
    np.testing.assert_array_equal(img[..., 1].ravel(), render(tmp_path, only_b2, tag="b2only"))


@needs_dirsig
def test_split_channels_render_fails_with_this_atmosphere_database(tmp_path):
    """Why `resolve_auror_run` refuses `split_channels: true`: one spectral state per channel, which the AUROR
    NewAtmosphere database does not hold. The dry run passes; the render fails. If this test starts failing
    because the render succeeds, the refusal can go."""
    import dataclasses
    sim = simulation(tmp_path, LIB, "auror-nir.yaml", tag="split")
    sim.auror_run = dataclasses.replace(sim.auror_run, split_channels=True)      # past the resolution refusal
    c = sim.validate()
    assert (c.schema_ok, c.resolution_ok, c.execution_ok) == (True, True, True), c
    with pytest.raises(RuntimeError, match="Missing spectral/temporal state in atmosphere database"):
        sim.run()


@needs_dirsig
def test_roi_offset_places_the_window_in_the_full_frame(tmp_path):
    """A 16 x 16 window at OffsetX 640, OffsetY 496 of DeepScan's 1280 x 1024 frame images the top-right
    quadrant of the centred 32 x 32 window (OffsetX 624, OffsetY 496). Per-pixel geolocation differs by the
    sampling (~2 m at 16 m GSD); a wrong sign or axis would shift it by 16 pixels."""
    ref, eid = "deepscan_850_306_nir_1280.yaml", "deepscan-850-306-nir-1280"
    big = render(tmp_path, LIB, ref, eid, {"Width": 32, "Height": 32, "OffsetX": 624, "OffsetY": 496}, "big", truth=True)
    quad = render(tmp_path, LIB, ref, eid, {"Width": 16, "Height": 16, "OffsetX": 640, "OffsetY": 496}, "q", truth=True)
    d = np.linalg.norm(quad[..., 3:6] - big[:16, 16:, 3:6], axis=-1)
    gsd = 10e-6 / 0.306 * 500000.0
    assert np.median(d) < 0.25 * gsd and np.linalg.norm((quad[..., 3:6] - big[:16, 16:, 3:6]).mean((0, 1))) < 0.05 * gsd
