"""`platform_gen.render_platform`: the generated `.platform` for `auror-nir` equals the received library
file (the reproduction gate), and other sensor entries render the values their specs give."""
import copy
import math
from pathlib import Path

import lxml.etree as et
import numpy as np
import pytest
import yaml

from protodirsig.platform_gen import PlatformGenError, check_template, render_platform
from protodirsig.run_spec import load_run_spec, load_sensor_spec
from protodirsig.spectral import read_curve, srf_model_values

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "config_repo" / "platforms" / "AurorNIRDetector" / "AurorNIRDetector.platform"
LIB = ROOT / "sensors"
SETTINGS = load_run_spec(ROOT / "run_specs" / "auror_ref.yaml")["descriptor"]["settings"]


def render(tmp_path, sensor, entry, settings=None, samples=10, mode="tabulated"):
    doc = load_sensor_spec(LIB, sensor)
    settings = settings or [{**SETTINGS[0], "entry_id": entry}]
    return render_platform(TEMPLATE, doc, entry, settings, samples, LIB, tmp_path / "out.platform", mode)


def same(a, b, path=""):
    """Element-wise equality: tags, attributes and text, with numeric text compared to 1e-12."""
    assert a.tag == b.tag, path
    assert dict(a.attrib).keys() == dict(b.attrib).keys(), f"{path}/{a.tag} attributes"
    for k, v in a.attrib.items():
        if (a.tag, k) == ("channel", "name"):
            continue                            # DIRSIG channel name = the spec's channel_id (names the ENVI band)
        assert same_text(v, b.attrib[k]), f"{path}/{a.tag}@{k}: {v} != {b.attrib[k]}"
    assert same_text((a.text or "").strip(), (b.text or "").strip()), f"{path}/{a.tag}: {a.text!r} != {b.text!r}"
    assert len(a) == len(b), f"{path}/{a.tag}: {len(a)} children vs {len(b)}"
    for x, y in zip(a, b):
        same(x, y, f"{path}/{a.tag}")


def same_text(x, y):
    try:
        return math.isclose(float(x), float(y), rel_tol=1e-12, abs_tol=1e-15)
    except ValueError:
        return x == y


def test_reproduction_gate_auror_nir(tmp_path):
    out = render(tmp_path, "auror-nir.yaml", "auror-nir", mode="native")
    assert out.channels == [("nir-b1", "native")]
    same(et.parse(str(out.path)).getroot(), et.parse(str(TEMPLATE)).getroot())


def test_run_spec_asks_for_the_native_gate():
    assert load_run_spec(ROOT / "run_specs" / "auror_ref.yaml")["engine"]["platform"]["channel_response"] == "native"


def test_native_refuses_a_curve(tmp_path):
    with pytest.raises(PlatformGenError, match="native cannot carry"):
        render(tmp_path, "deepscan_850_306_nir_1280.yaml", "deepscan-850-306-nir-1280", mode="native")


def test_tabulated_default_for_auror_is_unit_peak(tmp_path):
    out = render(tmp_path, "auror-nir.yaml", "auror-nir")
    assert out.channels == [("nir-b1", "tabulated")]
    ch = et.parse(str(out.path)).getroot().find(".//channellist/channel")
    assert max(float(e.findtext("value")) for e in ch.findall("entry")) == pytest.approx(1.0)


def test_template_is_renderable():
    assert check_template(TEMPLATE) == []


def test_units_and_array(tmp_path):
    out = render(tmp_path, "auror-nir.yaml", "auror-nir", mode="native")
    r = et.parse(str(out.path)).getroot()
    assert r.findtext(".//properties/aperturediameter") == "0.085"     # mm in the spec, m in DIRSIG
    assert r.findtext(".//properties/focallength") == "306"
    assert r.findtext(".//xelementcount") == "500"                     # settings.roi


def test_deepscan_tabulates_qe(tmp_path):
    out = render(tmp_path, "deepscan_850_306_nir_1280.yaml", "deepscan-850-306-nir-1280")
    assert out.channels == [("nir-b1", "tabulated")]
    ch = et.parse(str(out.path)).getroot().find(".//channellist/channel")
    assert ch.get("shape") == "tabulated" and ch.get("normalize") == "false"
    wl = np.array([float(e.findtext("spectralpoint")) for e in ch.findall("entry")])
    v = np.array([float(e.findtext("value")) for e in ch.findall("entry")])
    assert (wl[0], wl[-1], len(wl)) == (0.41, 2.0, 1591)
    qe = read_curve(LIB / "spectral/qe/synthetic_visgaas.csv")
    expect = srf_model_values({"kind": "gaussian", "center": 0.85, "fwhm": 0.15}, wl) * qe.at(wl)
    assert v == pytest.approx(expect, abs=1e-8)                          # the product, as written (9 significant digits)
    assert v[np.argmin(abs(wl - 0.85))] == pytest.approx(qe.at(0.85), rel=1e-6)
    assert v[wl > 1.75].max() == 0.0                                    # QE support ends at 1.72 um


def test_vis_entry(tmp_path):
    settings = [{**SETTINGS[0], "entry_id": "synthetic-600-200-vis-1920", "roi": {"Width": 64, "Height": 48}}]
    out = render(tmp_path, "synthetic_600_200_vis_1920.yaml", "synthetic-600-200-vis-1920", settings)
    r = et.parse(str(out.path)).getroot()
    assert out.channels == [("vis-pan", "tabulated")]
    assert r.findtext(".//properties/aperturediameter") == "0.05"
    assert r.findtext(".//properties/focallength") == "200"
    assert r.findtext(".//properties/aperturethroughput") == "1"       # optics curve folded into the channel
    assert (r.findtext(".//xelementcount"), r.findtext(".//yelementcount")) == ("64", "48")
    assert r.findtext(".//xelementspacing") == "5.500000"
    ch = r.find(".//channellist/channel")
    wl = np.array([float(e.findtext("spectralpoint")) for e in ch.findall("entry")])
    v = np.array([float(e.findtext("value")) for e in ch.findall("entry")])
    assert v[(wl < 0.449) | (wl > 0.751)].max() == 0.0                  # rectangular band 0.45-0.75
    assert 0.80 < v[np.argmin(abs(wl - 0.6))] < 0.88                    # lens ~0.94 x silicon ~0.90


def test_no_roi_uses_full_frame(tmp_path):
    settings = [{k: v for k, v in {**SETTINGS[0], "entry_id": "deepscan-850-306-nir-1280"}.items() if k != "roi"}]
    out = render(tmp_path, "deepscan_850_306_nir_1280.yaml", "deepscan-850-306-nir-1280", settings)
    r = et.parse(str(out.path)).getroot()
    assert (r.findtext(".//xelementcount"), r.findtext(".//yelementcount")) == ("1280", "1024")


def test_unknown_full_frame_without_roi_is_refused(tmp_path):
    settings = [{k: v for k, v in SETTINGS[0].items() if k != "roi"}]
    with pytest.raises(PlatformGenError, match="no full frame"):
        render(tmp_path, "auror-nir.yaml", "auror-nir", settings)


def test_response_outside_bandpass_is_refused(tmp_path):
    doc = load_sensor_spec(LIB, "deepscan_850_306_nir_1280.yaml")
    doc = copy.deepcopy(doc)
    ch = doc["sensor"]["entries"][0]["focal_planes"][0]["channels"][0]
    ch["srf_model"] = {"kind": "gaussian", "center": 0.30, "fwhm": 0.05}   # QE responds there; the job's data do not
    with pytest.raises(PlatformGenError, match="outside the template bandpass"):
        render_platform(TEMPLATE, doc, "deepscan-850-306-nir-1280",
                        [{**SETTINGS[0], "entry_id": "deepscan-850-306-nir-1280"}], 10, LIB, tmp_path / "x.platform")


def test_missing_curve_is_specific(tmp_path):
    doc = copy.deepcopy(load_sensor_spec(LIB, "deepscan_850_306_nir_1280.yaml"))
    doc["sensor"]["entries"][0]["focal_planes"][0]["channels"][0]["qe_reference"] = {"name": "spectral/qe/nope.csv"}
    from protodirsig.spectral import SpectralError
    with pytest.raises(SpectralError, match="not found"):
        render_platform(TEMPLATE, doc, "deepscan-850-306-nir-1280",
                        [{**SETTINGS[0], "entry_id": "deepscan-850-306-nir-1280"}], 10, LIB, tmp_path / "x.platform")
