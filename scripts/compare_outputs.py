#!/usr/bin/env python3
"""Compare two DIRSIG output directories file by file and classify every difference.

    python scripts/compare_outputs.py DIR_A DIR_B [--mask TEXT ...] [--json]

For each file name in either directory: byte-identical, or present on one side only, or different. A different ENVI
image (a `.img` or headerless data file with a `<name>.hdr` or `<data>.hdr` header beside it) is read with numpy by its
header (`samples`, `lines`, `bands`, `data type`, `interleave`, `byte order`, `header offset`) and measured: maximum,
mean and RMS absolute difference, the same divided by the RMS of the first image's values (the signal), the largest
relative difference of one value (`|a - b| / max(|a|, |b|)`), and the fraction of values and of pixels (any band)
that differ. A different text file (a header, a data recorder, a log) is compared after masking what changes between
runs without changing the result: absolute paths, home directories, work-root names (`--mask`, and 64-hex run ids),
ISO and `ctime` dates and times, and process ids. Other files are reported as different and not classified.

Classes of a differing file (`CLASSES`):
- `metadata`: nothing survives the mask (text), or the pixel data are identical (an image whose header differs).
- `float-order`: every differing value is within `FLOAT_ORDER_REL` (1e-5) relative of its counterpart. The ray tracer
  is single precision (machine epsilon 1.2e-7); summing the same samples in another order, as threads finishing in a
  different order do, moves a value by a few epsilon per addition, which stays below 1e-5 for the sample counts of
  these demos. A different random path is not bounded this way.
- `sampling-noise`: a larger difference, the spread of Monte Carlo estimates drawn with different random numbers (or,
  in a truth image, a different object hit by a pixel's sample). For text, numbers that differ by more than
  `FLOAT_ORDER_REL`, or a non-numeric difference that survives the mask.
- `index-relabel`: every differing band of an image holds integer labels (for example a truth image's "Dominant
  Optical Property Index") and at least `RELABEL_CONSISTENT` (99.9 percent) of its pixels agree with one renumbering
  of the labels: the same labels, numbered in another order (the rest are pixels whose dominant label is a tie). Not
  a radiometric difference. The three classes above did not fit this case, which the determinism probe found.
- `unclassified`: a different file that is neither an ENVI image nor text (for example lidar `.bin`).

A different image also lists its differing bands (`bands`, by the header's `band names`), each with its own measures
and class.

Exit status 0 when every file is identical, 1 otherwise. Imports: the standard library and numpy.
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

import numpy as np

FLOAT_ORDER_REL = 1e-5
RELABEL_CONSISTENT = 0.999
CLASSES = ("identical", "metadata", "float-order", "index-relabel", "sampling-noise", "unclassified", "only in A",
           "only in B")
ENVI_TYPES = {1: "u1", 2: "i2", 3: "i4", 4: "f4", 5: "f8", 6: "c8", 9: "c16", 12: "u2", 13: "u4", 14: "i8", 15: "u8"}
MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
DAYS = "Mon|Tue|Wed|Thu|Fri|Sat|Sun"
MASKS = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?"), "<datetime>"),
    (re.compile(rf"\b({DAYS}) ({MONTHS}) +\d{{1,2}} \d{{2}}:\d{{2}}:\d{{2}} \d{{4}}\b"), "<datetime>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "<date>"),
    (re.compile(r"\b\d{2}:\d{2}:\d{2}(\.\d+)?\b"), "<time>"),
    (re.compile(r"(?<![\w.])(~|/)(?:[^\s\"',;{}()\[\]]+/)*[^\s\"',;{}()\[\]]*"), "<path>"),
    (re.compile(r"\b[0-9a-f]{64}\b"), "<id>"),
    (re.compile(r"\b(pid|process id|process)\b([ =:#]*)\d+", re.I), r"\1\2<pid>"),
]
NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def mask(text, extra=()):
    """`text` with run-specific strings replaced: the `extra` strings first, then `MASKS`."""
    for s in sorted((e for e in extra if e), key=len, reverse=True):
        text = text.replace(s, "<mask>")
    for pattern, repl in MASKS:
        text = pattern.sub(repl, text)
    return text


def read_header(path):
    """An ENVI header as a dict of lower-case keys to string values (braces kept off)."""
    text = Path(path).read_text(errors="replace")
    if not text.lstrip().startswith("ENVI"):
        raise ValueError(f"{path} is not an ENVI header")
    out, key, buf = {}, None, []
    for line in text.splitlines()[1:]:
        if key is not None:
            buf.append(line)
            if "}" in line:
                out[key] = " ".join(buf).strip().strip("{}").strip()
                key, buf = None, []
            continue
        if "=" not in line:
            continue
        k, v = (x.strip() for x in line.split("=", 1))
        if v.startswith("{") and "}" not in v:
            key, buf = k.lower(), [v]
        else:
            out[k.lower()] = v.strip("{}").strip()
    return out


def header_for(data):
    """The ENVI header that describes `data` (`<data>.hdr`, else `<stem>.hdr`), or None."""
    data = Path(data)
    for h in (data.with_name(data.name + ".hdr"), data.with_suffix(".hdr")):
        if h != data and h.is_file():
            return h
    return None


def read_envi(data, header=None):
    """The image as a float64 array of shape (bands, lines, samples)."""
    h = read_header(header or header_for(data))
    samples, lines, bands = int(h["samples"]), int(h["lines"]), int(h.get("bands", 1))
    dtype = np.dtype(ENVI_TYPES[int(h["data type"])]).newbyteorder(">" if int(h.get("byte order", 0)) else "<")
    count = samples * lines * bands
    raw = np.fromfile(data, dtype=dtype, count=count, offset=int(h.get("header offset", 0)))
    if raw.size != count:
        raise ValueError(f"{data}: {raw.size} values, the header gives {count}")
    il = h.get("interleave", "bsq").lower()
    shape = {"bsq": (bands, lines, samples), "bil": (lines, bands, samples), "bip": (lines, samples, bands)}[il]
    arr = raw.reshape(shape)
    arr = {"bsq": arr, "bil": arr.transpose(1, 0, 2), "bip": arr.transpose(2, 0, 1)}[il]
    return np.real(arr).astype(np.float64)


def image_metrics(a, b):
    """Difference measures of two images of one shape (see the module docstring)."""
    if a.shape != b.shape:
        return {"shape_a": list(a.shape), "shape_b": list(b.shape)}
    with np.errstate(invalid="ignore"):
        d = np.abs(a - b)
    finite = np.isfinite(a) & np.isfinite(b)
    nan_mismatch = int(np.sum(np.isnan(a) != np.isnan(b)))
    d = np.where(finite, d, 0.0)
    signal = float(np.sqrt(np.mean(np.where(np.isfinite(a), a, 0.0) ** 2)))
    scale = np.maximum(np.abs(np.where(finite, a, 0.0)), np.abs(np.where(finite, b, 0.0)))
    rel = np.divide(d, scale, out=np.zeros_like(d), where=scale > 0)
    diff = (d > 0) | (np.isnan(a) != np.isnan(b))
    m = {"max_abs": float(d.max()), "mean_abs": float(d.mean()), "rms": float(np.sqrt(np.mean(d ** 2))),
         "signal_rms": signal, "max_value_rel": float(rel.max()),
         "fraction_values_differ": float(diff.mean()), "fraction_pixels_differ": float(diff.any(axis=0).mean()),
         "nan_mismatch": nan_mismatch}
    for k in ("max_abs", "mean_abs", "rms"):
        m[k + "_rel"] = m[k] / signal if signal > 0 else (0.0 if m[k] == 0 else float("inf"))
    return m


def relabel_consistency(a, b):
    """The fraction of pixels of two integer label bands that agree with one renumbering (the most common partner of
    each label, which must be a permutation), or None when the bands are not integer labels."""
    ok = np.isfinite(a) & np.isfinite(b)
    x, y = a[ok], b[ok]
    if x.size == 0 or np.any(x % 1) or np.any(y % 1) or np.array_equal(np.isfinite(a), np.isfinite(b)) is False:
        return None
    pairs, counts = np.unique(np.stack([x, y]), axis=1, return_counts=True)
    best = {}
    for (u, v), n in sorted(zip(map(tuple, pairs.T), counts), key=lambda t: -t[1]):
        best.setdefault(u, v)
    if len(set(best.values())) != len(best):
        return 0.0
    agree = sum(n for (u, v), n in zip(map(tuple, pairs.T), counts) if best[u] == v)
    return float(agree / x.size)


def band_records(a, b, names):
    """Measures and a class for every band that differs."""
    out = []
    for i in range(a.shape[0]):
        if np.array_equal(a[i], b[i], equal_nan=True):
            continue
        m = image_metrics(a[i:i + 1], b[i:i + 1])
        consistent = relabel_consistency(a[i], b[i])
        if m["max_abs"] == 0 and m["nan_mismatch"] == 0:
            cls = "metadata"
        elif m["nan_mismatch"] == 0 and m["max_value_rel"] <= FLOAT_ORDER_REL:
            cls = "float-order"
        elif consistent is not None and consistent >= RELABEL_CONSISTENT and m["fraction_values_differ"] > 0.001:
            cls = "index-relabel"
        else:
            cls = "sampling-noise"
        out.append({"band": names[i] if i < len(names) else str(i), "class": cls, "relabel_consistent": consistent,
                    **{k: m[k] for k in ("max_abs", "rms", "rms_rel", "max_value_rel", "fraction_values_differ")}})
    return out


def text_diff(a, b, extra=()):
    """`(surviving diff lines, numeric max relative difference or None)` of two texts after masking."""
    ma, mb = mask(a, extra).splitlines(), mask(b, extra).splitlines()
    lines = [ln for ln in difflib.unified_diff(ma, mb, lineterm="", n=0) if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]
    if not lines:
        return [], None
    worst, non_numeric = 0.0, False
    for la, lb in zip(ma, mb):
        if la == lb:
            continue
        na, nb = NUMBER.findall(la), NUMBER.findall(lb)
        if NUMBER.sub("#", la) != NUMBER.sub("#", lb) or len(na) != len(nb):
            non_numeric = True
            continue
        for x, y in zip(na, nb):
            fx, fy = float(x), float(y)
            s = max(abs(fx), abs(fy))
            worst = max(worst, abs(fx - fy) / s if s > 0 else 0.0)
    if len(ma) != len(mb):
        non_numeric = True
    return lines, (None if non_numeric else worst)


def _is_text(data):
    if b"\0" in data[:4096]:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def compare_file(pa, pb, extra=()):
    """One file's comparison record: `{name, class, kind, ...measures}`."""
    a, b = pa.read_bytes(), pb.read_bytes()
    rec = {"name": pa.name, "bytes_a": len(a), "bytes_b": len(b)}
    if a == b:
        return {**rec, "class": "identical", "kind": "bytes"}
    ha, hb = header_for(pa), header_for(pb)
    if ha is not None and hb is not None and not pa.name.endswith(".hdr"):
        try:
            ia, ib = read_envi(pa, ha), read_envi(pb, hb)
        except (ValueError, KeyError, OSError) as e:
            return {**rec, "class": "unclassified", "kind": "image", "error": str(e)}
        m = image_metrics(ia, ib)
        if "shape_a" in m:
            return {**rec, "class": "sampling-noise", "kind": "image", **m}
        names = [n.strip() for n in read_header(ha).get("band names", "").split(",") if n.strip()]
        bands = band_records(ia, ib, names)
        if m["max_abs"] == 0 and m["nan_mismatch"] == 0:
            cls = "metadata"                                    # the bytes differ but no value does (padding)
        elif m["nan_mismatch"] == 0 and m["max_value_rel"] <= FLOAT_ORDER_REL:
            cls = "float-order"
        elif bands and all(b["class"] in ("index-relabel", "float-order", "metadata") for b in bands) and \
                any(b["class"] == "index-relabel" for b in bands):
            cls = "index-relabel"
        else:
            cls = "sampling-noise"
        return {**rec, "class": cls, "kind": "image", **m, "bands": bands}
    if _is_text(a) and _is_text(b):
        lines, worst = text_diff(a.decode(), b.decode(), extra)
        if not lines:
            cls = "metadata"
        elif worst is not None and worst <= FLOAT_ORDER_REL:
            cls = "float-order"
        else:
            cls = "sampling-noise"
        return {**rec, "class": cls, "kind": "text", "surviving_lines": len(lines), "numeric_max_rel": worst,
                "first_surviving": lines[:4]}
    return {**rec, "class": "unclassified", "kind": "binary"}


def compare_dirs(da, db, extra=()):
    """Comparison records for every file name in either directory (recursively, by relative path), sorted."""
    da, db = Path(da), Path(db)
    fa = {p.relative_to(da).as_posix(): p for p in da.rglob("*") if p.is_file()}
    fb = {p.relative_to(db).as_posix(): p for p in db.rglob("*") if p.is_file()}
    out = []
    for rel in sorted(fa.keys() | fb.keys()):
        if rel not in fb:
            out.append({"name": rel, "class": "only in A"})
        elif rel not in fa:
            out.append({"name": rel, "class": "only in B"})
        else:
            out.append({**compare_file(fa[rel], fb[rel], extra), "name": rel})
    return out


def headers_only(records):
    """A header whose image's data are identical differs in metadata only, whatever its masked text shows."""
    by = {r["name"]: r for r in records}
    for r in records:
        if r["name"].endswith(".hdr") and r["class"] not in ("identical", "metadata", "only in A", "only in B"):
            data = by.get(r["name"][:-4]) or by.get(r["name"][:-4] + ".img")
            if data is not None and data["class"] == "identical":
                r["class"], r["note"] = "metadata", "the image data are identical"
    return records


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--mask", action="append", default=[], help="a run-specific string to mask (repeatable)")
    ap.add_argument("--json", action="store_true", help="print the records as JSON")
    args = ap.parse_args(argv)
    records = headers_only(compare_dirs(args.a, args.b, args.mask))
    if args.json:
        print(json.dumps(records, indent=1))
    else:
        for r in records:
            extra = ""
            if r.get("kind") == "image" and "rms_rel" in r:
                extra = (f" max {r['max_abs']:.3g} rms {r['rms']:.3g} rms/signal {r['rms_rel']:.3g} "
                         f"value rel {r['max_value_rel']:.3g} pixels {100 * r['fraction_pixels_differ']:.2f}%")
            elif r.get("kind") == "text":
                extra = f" surviving lines {r['surviving_lines']} numeric rel {r['numeric_max_rel']}"
            print(f"{r['class']:15s} {r['name']}{extra}")
    return 0 if all(r["class"] == "identical" for r in records) else 1


if __name__ == "__main__":
    sys.exit(main())
