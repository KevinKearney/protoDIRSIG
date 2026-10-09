"""`scripts/import_curve.py`: vendor-style input (nm, percent, non-uniform, about 0.3-1.7 um) becomes a
`spectral-curve/1` file that the library reads and the platform generator composes. The inputs are fabricated
in a temporary directory; nothing is written to `sensors/`."""
import copy
import importlib.util
import shutil
from pathlib import Path

import numpy as np
import pytest
import test_spectral_curves

from protodirsig.platform_gen import PlatformGenError, render_platform
from protodirsig.run_spec import load_run_spec, load_sensor_spec
from protodirsig.spectral import read_curve

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "config_repo" / "platforms" / "AurorNIRDetector" / "AurorNIRDetector.platform"
SETTINGS = load_run_spec(ROOT / "run_specs" / "auror_ref.yaml")["descriptor"]["settings"]
_spec = importlib.util.spec_from_file_location("import_curve", ROOT / "scripts" / "import_curve.py")
ic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ic)

# Vendor-style: header row, nm, percent, coarse and non-uniform, 300-1700 nm.
NM = [300, 325, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1650, 1700]
PCT = [5.0, 18.5, 30.0, 45.2, 55.0, 60.1, 66.0, 71.4, 76.0, 79.8, 80.0, 79.0, 78.2, 77.5, 76.0, 72.3, 55.0, 30.0, 8.5]


def vendor_file(tmp_path, nm=NM, pct=PCT, sep=", ", name="vendor.csv"):
    p = tmp_path / name
    p.write_text("Wavelength (nm)" + sep + "QE (%)\n" + "".join(f"{a}{sep}{b}\n" for a, b in zip(nm, pct)))
    return p


def run(tmp_path, src, **kw):
    args = {"kind": "qe", "name": "vendor_qe", "wavelength_unit": "nm", "percent": True,
            "provenance": "vendor_typical", "source": "fabricated test input", "acquired": "2026-10-09",
            "library": tmp_path / "lib"}
    args.update(kw)
    return ic.import_curve(src, **args)


def test_nm_percent_round_trip(tmp_path):
    out = run(tmp_path, vendor_file(tmp_path))
    c = read_curve(out)
    np.testing.assert_allclose(c.wavelength, np.array(NM) / 1000.0)
    np.testing.assert_allclose(c.value, np.array(PCT) / 100.0)
    assert c.meta["range_um"] == "0.300 1.700" and c.meta["provenance"] == "vendor_typical"
    assert (c.meta["source"], c.meta["acquired"]) == ("fabricated test input", "2026-10-09")
    assert "padding" not in c.meta                                     # no padding unless asked
    test_spectral_curves.test_curve_shape(out)


def test_um_fraction_whitespace_input(tmp_path):
    src = vendor_file(tmp_path, [w / 1000 for w in NM], [p / 100 for p in PCT], sep="  ")
    a = read_curve(run(tmp_path, src, wavelength_unit="um", percent=False))
    b = read_curve(run(tmp_path, vendor_file(tmp_path), name="other"))
    np.testing.assert_allclose(a.value, b.value)
    np.testing.assert_allclose(a.wavelength, b.wavelength)


def test_descending_input_is_sorted(tmp_path):
    c = read_curve(run(tmp_path, vendor_file(tmp_path, NM[::-1], PCT[::-1])))
    np.testing.assert_allclose(c.wavelength, np.array(NM) / 1000.0)
    np.testing.assert_allclose(c.value, np.array(PCT) / 100.0)


def test_exact_duplicate_is_dropped_conflicting_duplicate_refused(tmp_path):
    c = read_curve(run(tmp_path, vendor_file(tmp_path, NM + [800], PCT + [76.0])))
    assert len(c.wavelength) == len(NM)
    with pytest.raises(ic.CurveImportError, match="appears twice"):
        run(tmp_path, vendor_file(tmp_path, NM + [800], PCT + [70.0], name="dup.csv"), name="dup")


@pytest.mark.parametrize("bad, match", [(101.0, "outside"), (-0.5, "outside")])
def test_out_of_range_value_is_refused(tmp_path, bad, match):
    with pytest.raises(ic.CurveImportError, match=match):
        run(tmp_path, vendor_file(tmp_path, NM, PCT[:-1] + [bad]))


def test_rounding_excursion_is_set_to_the_bound(tmp_path):
    c = read_curve(run(tmp_path, vendor_file(tmp_path, NM, PCT[:-1] + [100.05])))
    assert c.value[-1] == 1.0


def test_percent_forgotten_is_refused(tmp_path):
    with pytest.raises(ic.CurveImportError, match="--percent"):
        run(tmp_path, vendor_file(tmp_path), percent=False)


def test_existing_file_is_not_overwritten(tmp_path):
    run(tmp_path, vendor_file(tmp_path))
    with pytest.raises(ic.CurveImportError, match="new name"):
        run(tmp_path, vendor_file(tmp_path))


def test_synthetic_provenance_is_not_importable(tmp_path):
    with pytest.raises(ic.CurveImportError, match="provenance"):
        run(tmp_path, vendor_file(tmp_path), provenance="synthetic")


def test_padding_is_recorded_and_only_where_asked(tmp_path):
    out = run(tmp_path, vendor_file(tmp_path), pad_zero_to=(0.150, 14.000))
    c = read_curve(out)
    assert c.meta["range_um"] == "0.150 14.000"
    assert c.meta["measured_range_um"] == "0.300 1.700"
    assert c.meta["padding"] == "zero below 0.300 um and above 1.700 um; not measured"
    assert c.at(0.2) == 0 and c.at(1.701) == 0 and c.at(5.0) == 0     # zero outside, with a 1 nm step
    inside = (c.wavelength >= 0.3) & (c.wavelength <= 1.7)
    np.testing.assert_allclose(c.value[inside], np.array(PCT) / 100.0)   # measured rows untouched
    assert len(c.wavelength) == len(NM) + 4                            # LO, 1 nm below, 1 nm above, HI
    test_spectral_curves.test_curve_shape(out)


def test_padding_inside_measured_range_is_refused(tmp_path):
    with pytest.raises(ic.CurveImportError, match="outside the measured range"):
        run(tmp_path, vendor_file(tmp_path), pad_zero_to=(0.41, 2.0))      # the job bandpass edge lies inside
    with pytest.raises(ic.CurveImportError, match="outside the measured range"):
        run(tmp_path, vendor_file(tmp_path), pad_zero_to=(0.150, 1.6))


def test_cli(tmp_path):
    src = vendor_file(tmp_path)
    rc = ic.main([str(src), "--kind", "qe", "--name", "cli_qe", "--wavelength-unit", "nm", "--percent",
                  "--provenance", "measured", "--source", "bench", "--pad-zero-to", "0.150,14.000",
                  "--library", str(tmp_path / "lib")])
    assert rc == 0
    assert read_curve(tmp_path / "lib/spectral/qe/cli_qe.csv").meta["provenance"] == "measured"


def _deepscan_with(lib, qe_name):
    doc = copy.deepcopy(load_sensor_spec(lib, "deepscan_850_306_nir_1280.yaml"))
    doc["sensor"]["entries"][0]["focal_planes"][0]["channels"][0]["qe_reference"] = {"name": f"spectral/qe/{qe_name}.csv"}
    return doc


def test_padded_curve_composes_through_platform_gen(tmp_path):
    lib = tmp_path / "lib"
    shutil.copytree(ROOT / "sensors", lib)
    run(tmp_path, vendor_file(tmp_path), name="padded_qe", pad_zero_to=(0.150, 14.000))
    run(tmp_path, vendor_file(tmp_path), name="bare_qe")
    settings = [{**SETTINGS[0], "entry_id": "deepscan-850-306-nir-1280"}]
    out = render_platform(TEMPLATE, _deepscan_with(lib, "padded_qe"), "deepscan-850-306-nir-1280", settings, 10, lib,
                          tmp_path / "p.platform")
    assert out.channels == [("nir-b1", "tabulated")]
    with pytest.raises(PlatformGenError, match="extrapolation: none"):     # as measured, 0.3-1.7 um < job's 0.41-2.0 um
        render_platform(TEMPLATE, _deepscan_with(lib, "bare_qe"), "deepscan-850-306-nir-1280", settings, 10, lib,
                        tmp_path / "q.platform")
