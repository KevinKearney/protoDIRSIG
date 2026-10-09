#!/usr/bin/env python3
"""Import a vendor or measured spectral curve into the sensor library as `spectral-curve/1`. stdlib + numpy.

    python scripts/import_curve.py SCION_QE.csv --kind qe --name teledyne_scion_visgaas_typ \\
        --wavelength-unit nm --percent --provenance vendor_typical \\
        --source "Teledyne SCION datasheet rev C, fig. 3" --pad-zero-to 0.150,14.000

Input: two numeric columns (wavelength, value), comma- or whitespace-separated. Lines starting with `#` and
lines whose first two fields are not numbers (column headers) are skipped. Output:
`sensors/spectral/<kind>/<name>.csv` (sensors/spectral/README.md), at the input's own wavelength grid:

- wavelength converted to um and sorted ascending; a repeated wavelength with the same value is kept once, a
  repeated wavelength with two different values is refused (the file does not say which is right);
- values divided by 100 with `--percent`; a value outside [0, 1] by no more than `ROUNDING` is set to the bound,
  one further out is refused, not clipped;
- outside the measured range nothing is written unless `--pad-zero-to LO,HI` asks: then a zero row 1 nm beyond
  each measured end and a zero row at LO and HI, recorded in the header as `padding`. The 1 nm step keeps
  linear interpolation from inventing response between the last measured point and the pad.

An existing file is never overwritten: a new curve gets a new name.
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"qe": ("qe_absolute", "electrons/photon", "qe"),
         "optics": ("transmission", "dimensionless", "transmission"),
         "filter": ("transmission", "dimensionless", "transmission")}
PROVENANCE = ("vendor_typical", "measured")
ROUNDING = 1e-3          # tolerated excursion outside [0, 1], in output units (0.1 percentage point)
PAD_STEP_UM = 0.001      # the zero row written just beyond each measured end
NAME = re.compile(r"^[a-z0-9][a-z0-9_]*$")


class CurveImportError(ValueError):
    pass


def _um(x):
    """Wavelength text: at least 3 decimals, at most 6, so 1 nm grids read like the synthetic files."""
    s = f"{x:.6f}".rstrip("0")
    head, _, frac = s.partition(".")
    return f"{head}.{frac.ljust(3, '0')}"


def parse_rows(text):
    """(wavelength, value) pairs from CSV or whitespace text; comments and non-numeric header lines skipped."""
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = [f for f in re.split(r"[,\s;]+", line) if f]
        try:
            wl, v = float(fields[0]), float(fields[1])
        except (ValueError, IndexError):
            if rows:
                raise CurveImportError(f"line {n}: {line!r} is not two numbers") from None
            continue                                   # header line before the data
        rows.append((wl, v))
    if len(rows) < 2:
        raise CurveImportError(f"found {len(rows)} data rows; need at least 2")
    return np.array(rows, dtype=float)


def clean(rows, wavelength_unit, percent):
    """Convert, sort, de-duplicate and range-check. Returns (wavelength_um, value)."""
    wl = rows[:, 0] / 1000.0 if wavelength_unit == "nm" else rows[:, 0].copy()
    v = rows[:, 1] / 100.0 if percent else rows[:, 1].copy()
    if not np.isfinite(wl).all() or not np.isfinite(v).all():
        raise CurveImportError("non-finite wavelength or value")
    if (wl <= 0).any():
        raise CurveImportError(f"non-positive wavelength {wl.min()} um")
    order = np.argsort(wl, kind="stable")
    wl, v = wl[order], v[order]
    same = np.isclose(np.diff(wl), 0.0, atol=1e-9)
    if same.any():
        clash = same & ~np.isclose(v[1:], v[:-1], atol=1e-12)
        if clash.any():
            i = int(np.argmax(clash))
            raise CurveImportError(f"wavelength {wl[i]:g} um appears twice with values {v[i]:g} and {v[i + 1]:g}")
        keep = np.concatenate([[True], ~same])
        wl, v = wl[keep], v[keep]
    bad = (v < -ROUNDING) | (v > 1 + ROUNDING)
    if bad.any():
        i = int(np.argmax(bad))
        raise CurveImportError(f"value {v[i]:g} at {wl[i]:g} um is outside [0, 1] by more than rounding ({ROUNDING:g}); "
                           "check --percent, or fix the source")
    return wl, np.clip(v, 0.0, 1.0)


def pad(wl, v, lo, hi):
    """Zero rows PAD_STEP_UM beyond each measured end (skipped where the end is already 0) and at lo, hi."""
    if not (lo < wl[0] and hi > wl[-1]):
        raise CurveImportError(f"--pad-zero-to {lo:g},{hi:g} must lie outside the measured range {wl[0]:g}-{wl[-1]:g} um")
    pre, post = [lo], [hi]
    if v[0] != 0 and wl[0] - PAD_STEP_UM > lo:
        pre.append(wl[0] - PAD_STEP_UM)
    if v[-1] != 0 and wl[-1] + PAD_STEP_UM < hi:
        post.insert(0, wl[-1] + PAD_STEP_UM)
    return (np.concatenate([pre, wl, post]),
            np.concatenate([np.zeros(len(pre)), v, np.zeros(len(post))]))


def render(name, kind, provenance, source, acquired, wl, v, measured, padded, description=None):
    """The `spectral-curve/1` text."""
    quantity, units, col = KINDS[kind]
    lines = ["# spectral-curve/1", f"# name: {name}", f"# quantity: {quantity}", f"# units: {units}",
             "# x: wavelength_um", f"# range_um: {_um(wl[0])} {_um(wl[-1])}", "# interpolation: linear",
             "# extrapolation: none", f"# provenance: {provenance}", f"# source: {source}",
             f"# acquired: {acquired}", f"# measured_range_um: {_um(measured[0])} {_um(measured[-1])}"]
    if padded:
        lines.append(f"# padding: zero below {_um(measured[0])} um and above {_um(measured[-1])} um; not measured")
    if description:
        lines.append(f"# description: {description}")
    lines.append(f"wavelength_um,{col}")
    lines += [f"{_um(a)},{b:.6f}" for a, b in zip(wl, v)]
    return "\n".join(lines) + "\n"


def import_curve(src, kind, name, wavelength_unit, percent, provenance, source, pad_zero_to=None,
                 acquired=None, description=None, library=ROOT / "sensors"):
    """Write `<library>/spectral/<kind>/<name>.csv` from `src`. Returns its path."""
    if kind not in KINDS:
        raise CurveImportError(f"--kind {kind!r}: expected one of {sorted(KINDS)}")
    if provenance not in PROVENANCE:
        raise CurveImportError(f"--provenance {provenance!r}: expected one of {PROVENANCE} (synthetic curves are "
                           "authored, not imported)")
    if not NAME.match(name):
        raise CurveImportError(f"--name {name!r}: lower case, digits and underscores (it is the file stem)")
    if not source.strip():
        raise CurveImportError("--source is empty: say where the data came from")
    out = Path(library) / "spectral" / kind / f"{name}.csv"
    if out.exists():
        raise CurveImportError(f"{out} exists; a new curve gets a new name (sensors/spectral/README.md)")
    wl, v = clean(parse_rows(Path(src).read_text(encoding="utf-8-sig")), wavelength_unit, percent)
    measured = (wl[0], wl[-1])
    if pad_zero_to is not None:
        wl, v = pad(wl, v, *pad_zero_to)
    acquired = acquired or dt.datetime.now(dt.timezone.utc).date().isoformat()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(name, kind, provenance, source.strip(), acquired, wl, v, measured,
                          pad_zero_to is not None, description), encoding="utf-8", newline="\n")
    return out


def _pair(text):
    try:
        lo, hi = (float(x) for x in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r}: expected LO,HI in um") from None
    return lo, hi


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("input")
    p.add_argument("--kind", required=True, choices=sorted(KINDS))
    p.add_argument("--name", required=True)
    p.add_argument("--wavelength-unit", required=True, choices=("nm", "um"))
    p.add_argument("--percent", action="store_true", help="values are percent (divided by 100)")
    p.add_argument("--provenance", required=True, choices=PROVENANCE)
    p.add_argument("--source", required=True, help="where the data came from (document, revision, figure)")
    p.add_argument("--acquired", help="date the data were obtained, YYYY-MM-DD (default: today, UTC)")
    p.add_argument("--pad-zero-to", type=_pair, metavar="LO,HI",
                   help="write zero response out to LO and HI um (recorded in the header); none by default")
    p.add_argument("--description")
    p.add_argument("--library", type=Path, default=ROOT / "sensors", help="sensor library root (default sensors/)")
    a = p.parse_args(argv)
    if a.acquired:
        dt.date.fromisoformat(a.acquired)
    try:
        out = import_curve(a.input, a.kind, a.name, a.wavelength_unit, a.percent, a.provenance, a.source,
                           a.pad_zero_to, a.acquired, a.description, a.library)
    except (CurveImportError, OSError) as e:
        print(f"import_curve: {e}", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
