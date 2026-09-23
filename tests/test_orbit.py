"""protodirsig.orbit must reproduce tutorial_orbit_to_ground.ipynb's verified Stage 1 results.

Uses the TLE and ephemeris cached in outputs/_orbit_data/ (skipped if absent), so the pass is
the same one the notebook chose: Rochester, 2026-09-25 16:07 UTC.
"""
from pathlib import Path

import numpy as np
import pytest

from protodirsig import orbit

DATA = Path(__file__).resolve().parents[1] / "outputs" / "_orbit_data"
pytestmark = pytest.mark.skipif(not (DATA / "tle_35946.txt").exists() or not (DATA / "de421.bsp").exists(),
                                reason="cached TLE / de421.bsp not present")


def test_matches_phase2_rochester_pass():
    from skyfield.api import EarthSatellite, Loader, wgs84
    _, name, l1, l2 = orbit.fetch_tle(35946, DATA, expect_name="WORLDVIEW-2", expect_intl="09055A")
    load = Loader(DATA, verbose=False)
    ts = load.timescale()
    sat = EarthSatellite(l1, l2, name, ts)
    planets = load("de421.bsp")
    target = wgs84.latlon(43.1566, -77.6088)

    t_culm, el, sun_el = orbit.choose_pass(orbit.find_passes(sat, target, planets["earth"], planets["sun"]))
    assert t_culm.utc_strftime("%Y-%m-%d %H:%M") == "2026-09-25 16:07" and round(el, 1) == 89.4

    epoch = orbit.pass_epoch(t_culm, 120.0)
    t = np.arange(12001) * 0.01
    times, geo, pos, pos_teme = orbit.propagate(sat, ts, epoch, t)
    orbit.check_teme_to_itrs(pos, pos_teme, times, t)

    lat, lon, alt = orbit.ecef_to_geodetic(pos)
    miss = orbit.ground_km(lat, lon, 43.1566, -77.6088)
    assert round(miss.min(), 2) == 7.14 and round(t[miss.argmin()], 2) == 59.54

    m = orbit.ecef_to_enu_matrix(43.1566, -77.6088)
    vel_enu = np.gradient(pos, t, axis=0) @ m.T
    up = orbit.along_track_up(vel_enu, len(t) // 2)
    assert up == [-0.248526, -0.968625, 0.0]                       # Phase 2's UP_VECTOR
    bore = (-pos / np.linalg.norm(pos, axis=1, keepdims=True)) @ m.T
    ang, roll = orbit.up_vector_check(up, bore, vel_enu)
    assert np.all(np.abs(ang - 90) < 10) and roll.max() < 2.0

    t_wp, pos_wp, err = orbit.thin(t, pos, 0.01, 1.0)
    assert len(t_wp) == 121 and round(err, 2) == 1.00
