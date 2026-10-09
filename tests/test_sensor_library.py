"""Every manifold_sensors/*.yaml validates against manifold_contracts/sensor-spec-1.schema.json, and the fields that restate one
another agree: the name matches the file, the channel's band_center and bandwidth match its srf_model, qe_peak
matches the maximum of the QE curve, and every referenced curve exists with its stamped hash."""
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from protodirsig.spectral import read_curve, resolve_curve

ROOT = Path(__file__).resolve().parents[1]
SENSORS = ROOT / "manifold_sensors"
FILES = sorted(SENSORS.glob("*.yaml"))
SCHEMA = json.loads((ROOT / "manifold_contracts" / "sensor-spec-1.schema.json").read_text())


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


def _with_reference(ref):
    doc = yaml.safe_load((SENSORS / "auror-nir.yaml").read_text())
    doc["sensor"]["entries"][0]["focal_planes"][0]["channels"][0]["radiometric_reference"] = ref
    return [e.message for e in Draft202012Validator(SCHEMA).iter_errors(doc)]


@pytest.mark.parametrize("ref, match", [
    ({"quantity": "electron_flux", "unit": "e-/s"}, "is not one of"),             # outside the enum
    ({"quantity": "electron_exposure"}, "'unit' is a required property"),
    ({"quantity": "spectral_radiance", "unit": "W/(m2.sr.um)", "gain": 2}, "Additional properties"),
], ids=["quantity-outside-enum", "unit-missing", "unknown-member"])
def test_schema_rejects_a_bad_radiometric_reference(ref, match):
    errors = _with_reference(ref)
    assert any(match in e for e in errors), errors


def test_schema_accepts_detector_v02_members_and_the_electron_member():
    for q in ("radiance", "spectral_radiance", "irradiance", "brightness_temperature", "digital_number",
              "electron_exposure"):
        assert _with_reference({"quantity": q, "unit": "x", "scale": None, "offset": 0.0}) == []


def _rendered_quantity(root):
    """(quantity, unit) of the image a generated platform makes DIRSIG write (basicplatform_plugin.html units
    table). Only the combinations the generator produces are mapped; anything else fails here, by design."""
    imagefile = root.find(".//capturemethod/imagefile")
    flux, area = imagefile.get("fluxunits", "watts"), imagefile.get("areaunits", "cm2")
    integrated = float(root.findtext(".//temporalintegration/time") or 0) > 0
    aperture = root.findtext(".//instrument/properties/aperturediameter") is not None
    if flux == "electronspersecond" and integrated and aperture:      # focal-plane electrons over the exposure
        return "electron_exposure", f"e-/{area}"
    raise AssertionError(f"no radiometric_reference mapping for fluxunits={flux} areaunits={area} "
                         f"integrated={integrated} aperture={aperture}")


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_radiometric_reference_matches_the_generated_image(tmp_path, path):
    """Every channel's radiometric_reference states what the generated .platform makes DIRSIG write, so the field
    cannot drift from the generator again (it said spectral radiance while the image was electrons)."""
    import lxml.etree as et

    from protodirsig.platform_gen import render_platform
    from protodirsig.run_spec import load_run_spec, load_sensor_spec
    template = ROOT / "manifold_config_repo" / "platforms" / "AurorNIRDetector" / "AurorNIRDetector.platform"
    settings = load_run_spec(ROOT / "manifold_run_specs" / "auror_ref.yaml")["descriptor"]["settings"][0]
    doc = load_sensor_spec(SENSORS, path.name)
    for entry in doc["sensor"]["entries"]:
        out = render_platform(template, doc, entry["entry_id"], [{**settings, "entry_id": entry["entry_id"]}], 10,
                              SENSORS, tmp_path / f"{entry['entry_id']}.platform")
        quantity, unit = _rendered_quantity(et.parse(str(out.path)).getroot())
        for fp in entry["focal_planes"]:
            for ch in fp["channels"]:
                assert (ch["radiometric_reference"]["quantity"], ch["radiometric_reference"]["unit"]) == (quantity, unit)
