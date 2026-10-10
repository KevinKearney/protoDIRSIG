"""Run ids and sweep ids: content-addressed, as the SDK API contract defines them (api/operations.md, R-09).

A run id is the sha256, 64 lowercase hex digits, of the RFC 8785 canonical JSON serialization (UTF-8) of the
resolved run spec: the parsed `run-spec/1` document with its sensor reference replaced by the referenced
sensor-spec's `sensor` block, after the reference's `content_hash` is verified. The generated file's header (which
names the recipe) and composition provenance are not part of the parsed document, so they are not hashed; the
`provenance` label of each settings value is part of it, so it is. The same run spec with its sensor inline or by
reference has the same id. A sweep id is the sha256 of the canonical JSON of the sorted list of its run ids, so a
sweep is identified by the runs it contains, whatever the order of the recipe's sensor list.

`canonical_json` implements RFC 8785 (JSON Canonicalization Scheme) here, without a library: object members sorted
by the UTF-16 code units of their keys, no whitespace, strings with only the mandatory escapes, numbers in the
ECMAScript `Number::toString` form of the IEEE-754 double. Conformance vectors: manifold_contracts/vectors/identity/.

Imports: the standard library and `protodirsig.run_spec` (which loads no engine package).
"""
import copy
import hashlib
import math
from datetime import date, datetime, timezone
from decimal import Decimal

from pathlib import Path

from protodirsig.run_spec import RunSpecError, _verify_hash, is_inline_sensor, load_sensor_spec

_SHORT = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def _string(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch in _SHORT:
            out.append(_SHORT[ch])
        elif o < 0x20 or 0xD800 <= o <= 0xDFFF:           # control characters; a lone surrogate cannot be UTF-8
            out.append(f"\\u{o:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _number(x):
    """ECMAScript Number::toString for a finite double, from Python's shortest round-trip digits."""
    if math.isnan(x) or math.isinf(x):
        raise ValueError(f"{x!r} has no JSON form (RFC 8785 forbids NaN and infinities)")
    if x == 0:
        return "0"                                          # also -0
    if x < 0:
        return "-" + _number(-x)
    sign, digits, exp = Decimal(repr(x)).as_tuple()
    s = "".join(map(str, digits)).rstrip("0")
    exp += len(digits) - len(s)                             # value = s x 10^exp
    k = len(s)
    n = exp + k                                             # value = 0.s x 10^n
    if k <= n <= 21:
        return s + "0" * (n - k)
    if 0 < n <= 21:
        return s[:n] + "." + s[n:]
    if -6 < n <= 0:
        return "0." + "0" * (-n) + s
    e = n - 1
    mantissa = s if k == 1 else s[0] + "." + s[1:]
    return f"{mantissa}e{'+' if e >= 0 else '-'}{abs(e)}"


def _utf16_key(key):
    return key.encode("utf-16-be", "surrogatepass")


def _serialize(obj, out):
    if obj is None:
        out.append("null")
    elif obj is True:
        out.append("true")
    elif obj is False:
        out.append("false")
    elif isinstance(obj, int):
        f = float(obj)
        if int(f) != obj:
            raise ValueError(f"integer {obj} is not exactly representable as an IEEE-754 double (RFC 8785)")
        out.append(_number(f))
    elif isinstance(obj, float):
        out.append(_number(obj))
    elif isinstance(obj, str):
        out.append(_string(obj))
    elif isinstance(obj, datetime):
        out.append(_string(_iso(obj)))
    elif isinstance(obj, date):
        out.append(_string(obj.isoformat()))
    elif isinstance(obj, (list, tuple)):
        out.append("[")
        for i, v in enumerate(obj):
            if i:
                out.append(",")
            _serialize(v, out)
        out.append("]")
    elif isinstance(obj, dict):
        for k in obj:
            if not isinstance(k, str):
                raise TypeError(f"object key {k!r} is not a string (RFC 8785)")
        out.append("{")
        for i, k in enumerate(sorted(obj, key=_utf16_key)):
            if i:
                out.append(",")
            out.append(_string(k))
            out.append(":")
            _serialize(obj[k], out)
        out.append("}")
    else:
        raise TypeError(f"{type(obj).__name__} {obj!r:.60} has no JSON form")


def _iso(dt):
    if dt.tzinfo is None:
        return dt.isoformat()
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(obj):
    """The RFC 8785 canonical JSON serialization of `obj`, as UTF-8 bytes. A `datetime` (YAML's unquoted
    timestamp) is written as its ISO 8601 string (UTC with Z when aware), a `date` likewise."""
    out = []
    _serialize(obj, out)
    return "".join(out).encode("utf-8", "surrogatepass")


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def materialize_sensor(spec, sensor_library):
    """A deep copy of `spec` with `descriptor.sensor` in place: a reference `{ref: {name, content_hash}}` is
    replaced by the referenced sensor-spec's `sensor` block after its stamped hash is verified (a mismatch raises
    RunSpecError; the `sha256:<hash>` placeholder is not checked, but the id then covers the file's content anyway,
    since the block is in the hashed document). An inline sensor is returned unchanged (as a copy)."""
    out = copy.deepcopy(spec)
    desc = out.get("descriptor") if isinstance(out, dict) else None
    sensor = desc.get("sensor") if isinstance(desc, dict) else None
    if is_inline_sensor(sensor):
        return out
    ref = sensor.get("ref") if isinstance(sensor, dict) else None
    if not isinstance(ref, dict) or not isinstance(ref.get("name"), str):
        raise RunSpecError(f"descriptor.sensor is neither a sensor-spec/1 reference nor an inline block: {sensor!r:.80}")
    path = Path(sensor_library) / ref["name"]
    if path.is_file():
        _verify_hash(path, ref, "sensor-spec", "/descriptor/sensor/ref")   # stamped: must match; placeholder: not checked
    doc = load_sensor_spec(sensor_library, ref["name"])
    desc["sensor"] = copy.deepcopy(doc["sensor"])
    return out


def resolved_run_spec(spec, sensor_library):
    """The document a run id is computed over: `spec` with its sensor materialized."""
    return materialize_sensor(spec, sensor_library)


def run_id(spec, sensor_library):
    """The run id of a parsed run spec: sha256 of the canonical JSON of the resolved run spec, 64 hex digits."""
    return sha256_hex(canonical_json(resolved_run_spec(spec, sensor_library)))


def sweep_id_from_runs(run_ids):
    """The sweep id: sha256 of the canonical JSON of the sorted list of its run ids, 64 hex digits."""
    ids = list(run_ids)
    if not ids or not all(isinstance(i, str) and len(i) == 64 for i in ids):
        raise ValueError(f"a sweep id needs one or more 64-digit run ids, got {ids!r:.120}")
    return sha256_hex(canonical_json(sorted(ids)))


def short_id(identifier, n=12):
    """The first `n` hex digits of an id, for display only; the stored value is always the full id."""
    return identifier[:n]
