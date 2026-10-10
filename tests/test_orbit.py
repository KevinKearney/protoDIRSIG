"""protodirsig.orbit must reproduce tutorial_orbit_to_ground.ipynb's verified Stage 1 results.

Uses the TLE and ephemeris cached in outputs/_orbit_data/ (skipped if absent), so the pass is
the same one the notebook chose: Rochester, 2026-09-25 16:07 UTC.
"""
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from protodirsig import orbit

DATA = Path(__file__).resolve().parents[1] / "outputs" / "_orbit_data"
pytestmark = pytest.mark.skipif(not (DATA / "tle_35946.txt").exists() or not (DATA / "de421.bsp").exists(),
                                reason="cached TLE / de421.bsp not present")


def test_matches_phase2_rochester_pass():
    _, name, l1, l2 = orbit.fetch_tle(35946, DATA, expect_name="WORLDVIEW-2", expect_intl="09055A")
    best = orbit.choose_pass(orbit.find_passes(l1, l2, 43.1566, -77.6088, DATA / "de421.bsp"))
    minute = datetime.fromtimestamp(round(best.culmination_s / 60) * 60, tz=timezone.utc)   # utc_strftime rounds
    assert minute.strftime("%Y-%m-%d %H:%M") == "2026-09-25 16:07" and round(best.max_el_deg, 1) == 89.4
    assert best.culmination_utc.startswith("2026-09-25T16:06:")
    assert isinstance(best.culmination_s, float) and isinstance(best.sun_el_deg, float)

    epoch = orbit.pass_epoch(best.culmination_s, 120.0)
    t = np.arange(12001) * 0.01
    traj = orbit.propagate(l1, l2, epoch, t)
    pos = traj.pos_itrs
    orbit.check_teme_to_itrs(pos, traj.pos_teme, traj.ut1_jd, t)

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
