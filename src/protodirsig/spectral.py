"""Spectral curves (`spectral-curve/1`, sensors/spectral/README.md) and the per-channel response the
platform generator composes from them.

A channel's effective response is the product of three factors that Detector_v02 keeps apart
(`optics.throughput_reference`, the channel's `srf_reference`/`srf_model`, `qe_reference`). DIRSIG
holds one response per channel; with `fluxunits="electronspersecond"` it takes that response as
quantum efficiency (basicplatform_plugin docs), so the product is the right single input.
"""
import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FWHM_PER_SIGMA = 2.0 * math.sqrt(2.0 * math.log(2.0))
KINDS = {"qe": "qe_absolute", "optics": "transmission", "filter": "transmission"}
REQUIRED = {"name", "quantity", "x", "range_um", "interpolation", "extrapolation", "provenance"}
PLACEHOLDER = "<"          # `sha256:<hash>`: a hash not yet stamped


class SpectralError(ValueError):
    pass


@dataclass
class Curve:
    meta: dict
    wavelength: np.ndarray
    value: np.ndarray

    def at(self, wl):
        """Linear interpolation; a wavelength outside `range_um` is an error (`extrapolation: none`)."""
        wl = np.asarray(wl, dtype=float)
        lo, hi = self.wavelength[0], self.wavelength[-1]
        if wl.min() < lo - 1e-12 or wl.max() > hi + 1e-12:
            raise SpectralError(f"curve {self.meta['name']!r} spans {lo}-{hi} um; asked for {wl.min()}-{wl.max()} um "
                                "(extrapolation: none)")
        return np.interp(wl, self.wavelength, self.value)


def sha256_file(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_curve(path):
    """Parse a `spectral-curve/1` CSV. Raises `SpectralError` for a malformed file."""
    path = Path(path)
    meta, key, lines = {}, None, path.read_text(encoding="utf-8").splitlines()
    body = None
    for i, line in enumerate(lines):
        if not line.startswith("#"):
            body = lines[i:]
            break
        text = line[1:]
        if i == 0:
            meta["spec"] = text.strip()
        elif text.startswith("   ") and key:
            meta[key] += " " + text.strip()
        else:
            key, _, value = text.partition(":")
            key = key.strip()
            meta[key] = value.strip()
    if meta.get("spec") != "spectral-curve/1" or body is None:
        raise SpectralError(f"{path.name}: not a spectral-curve/1 file")
    missing = REQUIRED - set(meta)
    if missing:
        raise SpectralError(f"{path.name}: metadata missing {sorted(missing)}")
    rows = list(csv.reader(body))
    data = np.array([[float(a), float(b)] for a, b in rows[1:]])
    return Curve(meta, data[:, 0], data[:, 1])


def resolve_curve(sensor_library, ref):
    """Load the curve a `{name, content_hash}` ref names under the sensor library, verifying a stamped hash."""
    path = Path(sensor_library) / ref["name"]
    if not path.is_file():
        raise SpectralError(f"spectral curve {ref['name']!r} not found under {sensor_library}")
    want = ref.get("content_hash")
    if isinstance(want, str) and PLACEHOLDER not in want and sha256_file(path) != want:
        raise SpectralError(f"spectral curve {ref['name']!r}: content_hash {want} != file {sha256_file(path)}")
    return read_curve(path)


def srf_model_values(model, wl):
    """Analytic channel shape on `wl` (peak 1): `gaussian` {center, fwhm} or `rectangular` {center, width}.

    A rectangle on an ascending grid is the fraction of each sample's bin (midpoint to midpoint) inside
    [center - width/2, center + width/2]: its sum times the step is `width`, and an edge on a grid point weighs
    1/2, as in DIRSIG's native rectangular channel (CONOPS section 9). A single wavelength gets the inclusive
    indicator.
    """
    wl = np.asarray(wl, dtype=float)
    kind = model["kind"]
    if kind == "gaussian":
        sigma = model["fwhm"] / FWHM_PER_SIGMA
        return np.exp(-0.5 * ((wl - model["center"]) / sigma) ** 2)
    if kind == "rectangular":
        lo, hi = model["center"] - model["width"] / 2.0, model["center"] + model["width"] / 2.0
        if wl.size < 2:
            return ((wl >= lo - 1e-9) & (wl <= hi + 1e-9)).astype(float)
        mid = (wl[1:] + wl[:-1]) / 2.0
        left = np.concatenate([[wl[0] - (wl[1] - wl[0]) / 2.0], mid])
        right = np.concatenate([mid, [wl[-1] + (wl[-1] - wl[-2]) / 2.0]])
        frac = (np.minimum(right, hi) - np.maximum(left, lo)) / (right - left)
        return np.round(np.clip(frac, 0.0, 1.0), 9)           # an edge on a grid point weighs exactly 1/2
    raise SpectralError(f"srf_model.kind {kind!r} is not gaussian or rectangular")


def band_grid(minimum, maximum, delta):
    """The DIRSIG `<bandpass>` grid, on integer multiples of `delta` so values do not drift."""
    n0, n1 = round(minimum / delta), round(maximum / delta)
    return np.arange(n0, n1 + 1) * delta


def channel_response(band, channel, optics_curve=None, qe_curve=None, sensor_library=None, srf_curve=None):
    """Product of the optics, shape and QE factors on `band` (a wavelength grid).

    Returns (response, clipped): `clipped` is the fraction of the response integral that lies outside
    `band` (evaluated on a 1 nm grid over the widest curve range). The generator refuses a channel
    that responds where the job's spectral data end.
    """
    def total(wl):
        r = np.ones_like(wl)
        if optics_curve is not None:
            r = r * optics_curve.at(wl)
        if srf_curve is not None:
            r = r * srf_curve.at(wl)
        elif "srf_model" in channel:
            r = r * srf_model_values(channel["srf_model"], wl)
        if qe_curve is not None:
            r = r * qe_curve.at(wl)
        return r

    resp = total(band)
    curves = [c for c in (optics_curve, srf_curve, qe_curve) if c is not None]
    lo = max([0.15] + [c.wavelength[0] for c in curves])
    hi = min([14.0] + [c.wavelength[-1] for c in curves])
    wide = band_grid(min(lo, band[0]), max(hi, band[-1]), 0.001)
    inside = (wide >= band[0] - 1e-9) & (wide <= band[-1] + 1e-9)
    w = total(wide)
    whole = w.sum()
    return resp, (float(w[~inside].sum() / whole) if whole > 0 else 0.0)
