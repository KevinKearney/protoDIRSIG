"""The orbit golden vector (manifold_contracts/vectors/orbit/): the propagator reproduces it within its tolerance.

Needs no network and no cached file: the pinned TLE is in the vector and the Earth-orientation tables ship with
skyfield. A replacement propagator passes the same test.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from protodirsig import orbit

VECTOR = Path(__file__).resolve().parents[1] / "manifold_contracts" / "vectors" / "orbit"
WANT = json.loads((VECTOR / "expected.json").read_text())


def _tle():
    _, _, l1, l2 = orbit.read_tle(VECTOR / WANT["tle_file"], 35946)
    assert [l1, l2] == WANT["tle"]
    return l1, l2


def test_propagator_reproduces_the_vector():
    traj = orbit.propagate(*_tle(), WANT["epoch_utc"], WANT["t_s"])
    tol = WANT["tolerance_m"]
    assert np.linalg.norm(traj.pos_itrs - np.array(WANT["itrs_m"]), axis=1).max() < tol
    assert np.linalg.norm(traj.pos_teme - np.array(WANT["teme_m"]), axis=1).max() < tol
    assert traj.epoch_utc == WANT["epoch_utc"] and np.array_equal(traj.t, WANT["t_s"])


def test_independent_path_reproduces_the_vector():
    """The sgp4 package and the hand-written GMST-1982 rotation, sharing no code with `propagate`."""
    teme, itrs, _ = orbit.itrs_by_sgp4_gmst82(*_tle(), WANT["epoch_utc"], WANT["t_s"])
    tol = WANT["tolerance_m"]
    assert np.linalg.norm(itrs - np.array(WANT["itrs_m"]), axis=1).max() < tol
    assert np.linalg.norm(teme - np.array(WANT["teme_m"]), axis=1).max() < tol


def test_vector_states_its_basis():
    assert len(WANT["t_s"]) == len(WANT["itrs_m"]) == len(WANT["teme_m"]) == 121
    assert np.allclose(np.diff(WANT["t_s"]), 1.0) and WANT["tolerance_m"] <= 10.0
    assert WANT["tolerance_m"] > 2 * WANT["tolerance_basis"]["measured_max_itrs_difference_m"]
    assert {"skyfield", "sgp4"} <= set(WANT["produced_with"])
    eop = orbit.bundled_eop_path()
    assert hashlib.sha256(eop.read_bytes()).hexdigest() == WANT["earth_orientation"]["file_sha256"], \
        "skyfield's bundled Earth-orientation tables changed; re-measure the vector's tolerance"


def test_trajectory_carries_no_skyfield_objects():
    traj = orbit.propagate(*_tle(), WANT["epoch_utc"], [0.0, 1.0])
    for name in ("t", "ut1_jd", "pos_itrs", "vel_itrs", "pos_teme", "vel_teme"):
        assert type(getattr(traj, name)) is np.ndarray, name
    assert isinstance(traj.epoch_utc, str) and traj.propagator == orbit.propagator_provenance()
    assert set(traj.propagator) >= {"name", "version", "sgp4_version"}
    speed = np.linalg.norm(traj.vel_itrs, axis=1)
    assert np.all((6500 < speed) & (speed < 8000))
