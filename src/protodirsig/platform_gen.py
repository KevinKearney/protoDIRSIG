"""Render a job's `.platform` from a `sensor-spec/1` entry and the run spec's `settings`.

The library platform file (`engine.platform.ref`) is the template: it carries the structure the specs do
not model (metadata, mount, truth collections, spatial response, hypersampling, bandpass). The
sensor-spec and settings supply every value they model, so a different sensor entry gives a different
instrument with no other edit. Values substituted, with the units DIRSIG expects:

  instrument/properties   aperturediameter [m] = optics.aperture_diameter [mm] / 1000
                          focallength [mm]     = optics.focal_length [mm]
                          aperturethroughput   = optics.throughput_in_band, or 1 when
                                                 optics.throughput_reference folds the optics curve
                                                 into the channel (the factors multiply)
  detectorarray           xelementcount/yelementcount = settings.roi Width/Height (full frame if absent)
                          xelementspacing/yelementspacing = pitch [um]; element size = pitch x fill_factor
                          clock rate [Hz] = settings.frame_rate
  temporalintegration     time [s] = settings.exposure_time; samples = engine.platform.integration_samples
  channellist             one channel per sensor channel, named by its channel_id; gain/bias =
                          settings.gain/black_level. Written as a tabulated channel carrying the product
                          of the unit-peak shape (srf_model or srf_reference), qe_reference and the optics
                          curve on the template's bandpass grid; normalize="false", so DIRSIG treats it as
                          absolute (electrons per photon) under fluxunits="electronspersecond". With
                          engine.platform.channel_response native, an analytic channel is written as
                          DIRSIG's own shape instead (see render_platform).

Left as the template has them: names, truth collections, spatial response, hypersampling, bandpass,
image file base names (`engine.platform.output_prefix` is not applied; BACKLOG).
"""
import copy
from dataclasses import dataclass, field
from pathlib import Path

import lxml.etree as et

from protodirsig.spectral import FWHM_PER_SIGMA, SpectralError, band_grid, resolve_curve
from protodirsig.spectral import channel_response as compose_response

CLIP_LIMIT = 1e-3       # response fraction allowed outside the template bandpass


class PlatformGenError(ValueError):
    pass


@dataclass
class RenderedPlatform:
    path: Path
    channels: list = field(default_factory=list)    # [(channel_id, "native"|"tabulated")]


def _num(x):
    return f"{x:.10g}"


def _set(parent, tag, value):
    node = parent.find(tag)
    if node is None:
        raise PlatformGenError(f"template has no <{tag}> under <{parent.tag}>")
    node.text = value


def _single(root, path):
    nodes = root.findall(path)
    if len(nodes) != 1:
        raise PlatformGenError(f"template must have exactly one {path}, found {len(nodes)}")
    return nodes[0]


def _entry(sensor_doc, entry_id):
    for e in sensor_doc["sensor"]["entries"]:
        if e["entry_id"] == entry_id:
            return e
    raise PlatformGenError(f"sensor entry {entry_id!r} not in the sensor-spec")


def _setting(settings, entry_id):
    for s in settings:
        if s.get("entry_id") == entry_id:
            return s
    raise PlatformGenError(f"no settings member for entry {entry_id!r}")


def _q(x):
    """Value of a quantity object or bare number."""
    return x["value"] if isinstance(x, dict) else x


def check_template(template):
    """Structure problems in a template platform file; empty means it can be rendered."""
    try:
        root = et.parse(str(template)).getroot()
        for path in (".//instrument", ".//focalplane", ".//capturemethod/spectralresponse/channellist",
                     ".//detectorarray", ".//temporalintegration"):
            _single(root, path)
        if not root.findall(".//channellist/channel"):
            return ["template has no channel to use as a pattern"]
    except (PlatformGenError, et.XMLSyntaxError) as e:
        return [str(e)]
    return []


def render_platform(template, sensor_doc, entry_id, settings, integration_samples, sensor_library, out_path,
                    channel_response="tabulated"):
    """Write the generated `.platform` to `out_path`. Returns a `RenderedPlatform`.

    `channel_response` is `engine.platform.channel_response`: `tabulated` (default) writes every channel as the
    unit-peak shape times QE times optics. `native` writes an analytic-only channel as DIRSIG's own gaussian or
    rectangular shape, whose amplitude is DIRSIG's (a gaussian peaks at 1/sqrt(2 pi), not 1); it exists to
    reproduce the received AUROR_ref tree and refuses a channel that has a curve.
    """
    if channel_response not in ("tabulated", "native"):
        raise PlatformGenError(f"channel_response is {channel_response!r}, expected 'tabulated' or 'native'")
    tree = et.parse(str(template))
    root = tree.getroot()
    entry, st = _entry(sensor_doc, entry_id), _setting(settings, entry_id)
    if len(entry["focal_planes"]) != 1:
        raise PlatformGenError(f"entry {entry_id!r}: only one focal plane per entry is generated")
    fp = entry["focal_planes"][0]
    opt, det = entry["optics"], fp["detector"]

    props = _single(root, ".//instrument/properties")
    optics_curve = None
    if "throughput_reference" in opt:
        optics_curve = resolve_curve(sensor_library, opt["throughput_reference"])
    _set(props, "aperturediameter", _num(opt["aperture_diameter"] / 1000.0))
    _set(props, "focallength", _num(opt["focal_length"]))
    _set(props, "aperturethroughput", "1" if optics_curve is not None else _num(_q(opt["throughput_in_band"])))

    arr = _single(root, ".//detectorarray")
    roi = st.get("roi") or {}
    width, height = roi.get("Width") or det["SensorWidth"], roi.get("Height") or det["SensorHeight"]
    if width is None or height is None:
        raise PlatformGenError(f"entry {entry_id!r}: no roi in settings and no full frame in the detector block")
    px, py, fill = det["SensorPixelWidth"], det["SensorPixelHeight"], det["fill_factor"]
    for tag, val in (("xelementcount", str(int(width))), ("yelementcount", str(int(height))),
                     ("xelementspacing", f"{px:.6f}"), ("yelementspacing", f"{py:.6f}"),
                     ("xelementsize", f"{px * fill:.6f}"), ("yelementsize", f"{py * fill:.6f}")):
        _set(arr, tag, val)
    _set(arr.find("clock"), "rate", _num(_q(st["frame_rate"])))

    ti = _single(root, ".//temporalintegration")
    _set(ti, "time", _num(_q(st["exposure_time"])))
    _set(ti, "samples", str(int(integration_samples)))

    sr = _single(root, ".//capturemethod/spectralresponse")
    bp = sr.find("bandpass")
    band = band_grid(float(bp.findtext("minimum")), float(bp.findtext("maximum")), float(bp.findtext("delta")))
    clist = sr.find("channellist")
    pattern = copy.deepcopy(clist.find("channel"))
    for c in list(clist):
        clist.remove(c)

    rendered = []
    for ch in fp["channels"]:
        qe = resolve_curve(sensor_library, ch["qe_reference"]) if "qe_reference" in ch else None
        srf = resolve_curve(sensor_library, ch["srf_reference"]) if "srf_reference" in ch else None
        if srf is None and "srf_model" not in ch:
            raise PlatformGenError(f"channel {ch['channel_id']!r}: needs srf_model or srf_reference")
        node = copy.deepcopy(pattern)
        node.set("name", ch["channel_id"])
        node.set("gain", _num(_q(st["gain"])))
        node.set("bias", _num(_q(st["black_level"])))
        node.set("normalize", "false")
        for child in list(node):
            if child.tag not in ("polarizer", "dataoutput"):
                node.remove(child)
        anchor = node.find("polarizer")
        has_curve = optics_curve is not None or qe is not None or srf is not None
        if channel_response == "native" and has_curve:
            raise PlatformGenError(f"channel {ch['channel_id']!r}: channel_response native cannot carry a spectral curve")
        if channel_response == "native":
            m = ch["srf_model"]
            node.set("shape", m["kind"])
            if m["kind"] == "gaussian":
                items = [("center", f"{m['center']:.4f}"), ("width", f"{m['fwhm'] / FWHM_PER_SIGMA:.8f}")]
            else:
                items = [("center", f"{m['center']:.4f}"), ("width", f"{m['width']:.8f}")]
            for tag, text in items:
                el = et.Element(tag)
                el.text = text
                anchor.addprevious(el)
            mode = "native"
        else:
            try:
                resp, clipped = compose_response(band, ch, optics_curve, qe, sensor_library, srf)
            except SpectralError as e:
                raise PlatformGenError(f"channel {ch['channel_id']!r}: {e}") from e
            if clipped > CLIP_LIMIT:
                raise PlatformGenError(
                    f"channel {ch['channel_id']!r}: {clipped:.2%} of the response lies outside the template "
                    f"bandpass {band[0]:g}-{band[-1]:g} um, where the job's spectral data end")
            node.set("shape", "tabulated")
            for wl, v in zip(band, resp):
                e = et.Element("entry")
                et.SubElement(e, "spectralpoint").text = f"{wl:.3f}"
                et.SubElement(e, "value").text = f"{v:.9g}"
                anchor.addprevious(e)
            mode = "tabulated"
        clist.append(node)
        rendered.append((ch["channel_id"], mode))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(out_path), xml_declaration=False, encoding="utf-8", pretty_print=True)
    return RenderedPlatform(out_path, rendered)
