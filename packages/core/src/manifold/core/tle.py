"""Two-line element sets read from a file and validated: the TLE checks admission runs on an orbit run's library
file, without the propagator. `manifold.core.orbit` re-exports both functions and adds `fetch_tle` and the propagator.

Imports: the standard library only.
"""
from pathlib import Path


def tle_checksum_ok(line):
    """TLE mod-10 checksum: digits count face value, '-' counts 1, everything else 0."""
    s = sum(int(c) if c.isdigit() else (1 if c == "-" else 0) for c in line[:68])
    return s % 10 == int(line[68])


def read_tle(path, norad_id=None, expect_name=None, expect_intl=None):
    """A TLE file as `fetch_tle` writes it (comment line, name line, line 1, line 2), validated; no network.

    Returns (comment, name, line1, line2). `norad_id`, if given, must match both lines' catalog number.
    """
    comment, name, line1, line2 = [ln.rstrip() for ln in Path(path).read_text().splitlines()]
    assert line1.startswith("1 ") and line2.startswith("2 ") and len(line1) == len(line2) == 69
    assert tle_checksum_ok(line1) and tle_checksum_ok(line2), "TLE checksum failure"
    assert int(line1[2:7]) == int(line2[2:7])
    if norad_id is not None:
        assert int(line1[2:7]) == norad_id, f"{path}: catalog {int(line1[2:7])} != {norad_id}"
    if expect_name:
        assert expect_name.upper() in name.upper(), f"catalog {norad_id} is {name!r}, not {expect_name}"
    if expect_intl:
        assert line1[9:17].strip() == expect_intl, f"international designator {line1[9:17]!r} != {expect_intl}"
    return comment, name, line1, line2
