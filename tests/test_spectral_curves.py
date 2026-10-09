"""Every sensors/spectral/<kind>/*.csv is a spectral-curve/1 file: required metadata, ascending wavelength,
values in [0, 1], and the first and last rows match the declared range. Also `spectral.py` itself."""
from pathlib import Path

import numpy as np
import pytest

from protodirsig.spectral import (FWHM_PER_SIGMA, KINDS, SpectralError, band_grid, channel_response, read_curve,
                                  srf_model_values)

SPECTRAL = Path(__file__).resolve().parents[1] / "sensors" / "spectral"
FILES = sorted(SPECTRAL.glob("*/*.csv"))


def test_curves_exist():
    assert {p.stem for p in FILES} >= {"synthetic_visgaas", "synthetic_silicon", "synthetic_vis_lens"}


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_curve_shape(path):
    curve = read_curve(path)
    meta = curve.meta
    assert meta["name"] == path.stem
    assert meta["quantity"] == KINDS[path.parent.name]
    assert meta["x"] == "wavelength_um" and meta["provenance"] in {"synthetic", "vendor_typical", "measured"}
    assert (np.diff(curve.wavelength) > 0).all()
    assert ((curve.value >= 0) & (curve.value <= 1)).all()
    lo, hi = (float(x) for x in meta["range_um"].split())
    assert (curve.wavelength[0], curve.wavelength[-1]) == (lo, hi)


def test_curve_refuses_extrapolation():
    curve = read_curve(SPECTRAL / "qe" / "synthetic_visgaas.csv")
    assert curve.at(0.9) == pytest.approx(0.8)
    with pytest.raises(SpectralError, match="extrapolation: none"):
        curve.at(np.array([0.1, 0.5]))


def test_malformed_file_is_refused(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("wavelength_um,qe\n0.4,1\n")
    with pytest.raises(SpectralError, match="not a spectral-curve/1"):
        read_curve(p)


def test_gaussian_fwhm_and_rectangle():
    wl = band_grid(0.41, 2.0, 0.001)
    g = srf_model_values({"kind": "gaussian", "center": 0.85, "fwhm": 0.15}, wl)
    assert g.max() == 1.0 and g[np.argmin(abs(wl - 0.775))] == pytest.approx(0.5, abs=1e-6)     # half max at +-fwhm/2
    assert FWHM_PER_SIGMA == pytest.approx(2.3548200450309493)
    r = srf_model_values({"kind": "rectangular", "center": 0.6, "width": 0.3}, wl)
    assert wl[r > 0][0] == pytest.approx(0.45) and wl[r > 0][-1] == pytest.approx(0.75)


def test_channel_response_reports_clipped_fraction():
    band = band_grid(0.41, 2.0, 0.001)
    ch = {"srf_model": {"kind": "gaussian", "center": 0.85, "fwhm": 0.15}}
    _, clipped = channel_response(band, ch)
    assert clipped < 1e-9
    _, clipped = channel_response(band, {"srf_model": {"kind": "gaussian", "center": 0.41, "fwhm": 0.1}})
    assert 0.45 < clipped < 0.55                                    # half the response lies below the bandpass
