"""Every sensors/*.yaml validates against contracts/sensor-spec-1.schema.json, and the fields that restate one
another agree: the name matches the file, the channel's band_center and bandwidth match its srf_model, qe_peak
matches the maximum of the QE curve, and every referenced curve exists with its stamped hash."""
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from protodirsig.spectral import read_curve, resolve_curve

ROOT = Path(__file__).resolve().parents[1]
SENSORS = ROOT / "sensors"
FILES = sorted(SENSORS.glob("*.yaml"))
SCHEMA = json.loads((ROOT / "contracts" / "sensor-spec-1.schema.json").read_text())


def test_library_is_not_empty():
    assert {f.stem for f in FILES} >= {"auror-nir", "deepscan_850_306_nir_1280", "synthetic_600_200_vis_1920"}


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_entry_validates_against_the_schema(path):
    doc = yaml.safe_load(path.read_text())
    errors = sorted(Draft202012Validator(SCHEMA).iter_errors(doc), key=lambda e: list(e.path))
    assert not errors, "; ".join(f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors)
    assert doc["meta"]["name"] == path.stem


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_restated_fields_agree(path):
    doc = yaml.safe_load(path.read_text())
    for entry in doc["sensor"]["entries"]:
        opt = entry["optics"]
        assert opt["f_number"] == pytest.approx(opt["focal_length"] / opt["aperture_diameter"], abs=0.05)
        if "throughput_reference" in opt:
            curve = resolve_curve(SENSORS, opt["throughput_reference"])
            band = (curve.wavelength > 0.45) & (curve.wavelength < 0.75)
            assert curve.value[band].mean() == pytest.approx(opt["throughput_in_band"]["value"], abs=0.02)
        for fp in entry["focal_planes"]:
            det = fp["detector"]
            if det["SensorWidth"] is not None:
                assert det["SensorWidth"] >= 1 and det["SensorHeight"] >= 1
            for ch in fp["channels"]:
                m = ch.get("srf_model")
                if m:
                    assert ch["band_center"] == m["center"]
                    assert ch["bandwidth"] == (m["fwhm"] if m["kind"] == "gaussian" else m["width"])
                if "qe_reference" in ch:
                    curve = resolve_curve(SENSORS, ch["qe_reference"])
                    assert curve.meta["quantity"] == "qe_absolute"
                    assert ch["qe_peak"]["value"] == pytest.approx(curve.value.max(), abs=0.005)


def test_curves_validate_as_spectral_curve_files():
    for path in (SENSORS / "spectral").glob("*/*.csv"):
        curve = read_curve(path)
        assert curve.meta["name"] == path.stem
