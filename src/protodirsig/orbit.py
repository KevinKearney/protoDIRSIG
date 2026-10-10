"""TLE -> SGP4 -> ITRS (ECEF) trajectory helpers, factored out of tutorial_orbit_to_ground.ipynb.

Every function here is the code that notebook's Stage 1 built and verified inline (the
notebook keeps its inline copies because they *are* the explanation). The derivations and the
reasons for each check live there; this module only makes them reusable.

The propagator is a seam. Only `propagate`, `find_passes`, `propagator_provenance` and the timescale helper touch
skyfield, and they import it inside the function; every public function takes and returns numpy arrays and plain
Python values, so no skyfield type crosses the module boundary and the propagator can be replaced behind
`propagate`. A replacement must reproduce `manifold_contracts/vectors/orbit/` within its tolerance.
"""
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import NamedTuple

import numpy as np

OMEGA_EARTH = 7.2921150e-5           # rad/s, Earth sidereal rotation rate
WGS84_A = 6378137.0                  # semi-major axis, m
WGS84_F = 1 / 298.257223563
WGS84_E2 = WGS84_F * (2 - WGS84_F)   # first eccentricity squared


# --- TLE -----------------------------------------------------------------------------------

def tle_checksum_ok(line):
    """TLE mod-10 checksum: digits count face value, '-' counts 1, everything else 0."""
    s = sum(int(c) if c.isdigit() else (1 if c == "-" else 0) for c in line[:68])
    return s % 10 == int(line[68])


def fetch_tle(norad_id, cache_dir, refresh=False, expect_name=None, expect_intl=None):
    """Celestrak GP TLE for `norad_id`, cached in `cache_dir`; validated before it is returned.

    Returns (comment, name, line1, line2). `expect_name` / `expect_intl` (e.g. "WORLDVIEW-2",
    "09055A") guard against trusting a catalog number blindly.
    """
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=tle"
    path = cache_dir / f"tle_{norad_id}.txt"
    if refresh or not path.exists():
        with urllib.request.urlopen(url, timeout=30) as r:
            text = r.read().decode()
        fetched = datetime.now(timezone.utc).isoformat(timespec="seconds")
        path.write_text(f"# fetched {fetched} from {url}\n{text.strip()}\n")
    return read_tle(path, norad_id, expect_name, expect_intl)


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


# --- propagator seam --------------------------------------------------------------------------

PROPAGATOR = "skyfield_sgp4"          # the propagator tag a run spec's `engine.motion` names


def propagator_provenance():
    """Name and versions of the propagator behind `propagate`, for the execution record (never a run spec)."""
    return {"name": "skyfield", "version": version("skyfield"), "sgp4_version": version("sgp4"), "tag": PROPAGATOR}


def _timescale(eop=None):
    """A skyfield timescale. `eop` None: skyfield's bundled Earth-orientation tables (no network). `eop` a path
    to a copy of those tables (`iers.npz`, the same arrays) so they can be a hashed library file."""
    from skyfield.api import Loader
    if eop is None:
        return Loader(".", verbose=False).timescale(builtin=True)
    from skyfield.timelib import Timescale
    arrays = np.load(eop)
    daily_tt = arrays["tt_jd_minus_arange"] + np.arange(len(arrays["tt_jd_minus_arange"]))
    daily_delta_t = (arrays["delta_t_1e7"] / 1e7).round(7)
    return Timescale((daily_tt, daily_delta_t), arrays["leap_dates"], arrays["leap_offsets"])


def _utc_iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, eq=False)
class Trajectory:
    """An SGP4 trajectory sampled at `epoch_utc + t`. Arrays are numpy; nothing here is a skyfield object."""
    epoch_utc: str           # ISO-8601 UTC of t = 0, e.g. "2026-09-25T16:06:00Z"
    t: np.ndarray            # (N,) offsets from epoch_utc, s
    ut1_jd: np.ndarray       # (N,) UT1 Julian dates of the samples
    pos_itrs: np.ndarray     # (N, 3) ITRS (ECEF) position, m
    vel_itrs: np.ndarray     # (N, 3) ITRS velocity, m/s
    pos_teme: np.ndarray     # (N, 3) TEME position, m
    vel_teme: np.ndarray     # (N, 3) TEME velocity, m/s
    propagator: dict         # propagator_provenance()


def propagate(line1, line2, epoch, t, eop=None):
    """SGP4 for the TLE (`line1`, `line2`) at `epoch + t` seconds; `epoch` a UTC datetime or ISO-8601 string.

    The propagation entry point: the one function that turns a TLE into positions. `eop` as in `_timescale`."""
    from skyfield.api import EarthSatellite
    from skyfield.framelib import itrs
    from skyfield.sgp4lib import TEME
    if isinstance(epoch, str):
        epoch = datetime.fromisoformat(epoch.replace("Z", "+00:00"))
    epoch = epoch.astimezone(timezone.utc)
    t = np.asarray(t, dtype=float)
    ts = _timescale(eop)
    times = ts.utc(epoch.year, epoch.month, epoch.day, epoch.hour, epoch.minute,
                   epoch.second + epoch.microsecond / 1e6 + t)
    geo = EarthSatellite(line1, line2, None, ts).at(times)
    r_itrs, v_itrs = geo.frame_xyz_and_velocity(itrs)
    r_teme, v_teme = geo.frame_xyz_and_velocity(TEME)
    return Trajectory(epoch_utc=_utc_iso(epoch), t=t, ut1_jd=np.asarray(times.ut1, dtype=float),
                      pos_itrs=r_itrs.m.T, vel_itrs=v_itrs.m_per_s.T, pos_teme=r_teme.m.T, vel_teme=v_teme.m_per_s.T,
                      propagator=propagator_provenance())


# --- pass selection --------------------------------------------------------------------------

class Pass(NamedTuple):
    """One culmination: when (ISO-8601 UTC and POSIX seconds), how high, and the sun elevation at the target."""
    culmination_utc: str
    culmination_s: float
    max_el_deg: float
    sun_el_deg: float


def find_passes(line1, line2, lat_deg, lon_deg, ephemeris, days=7, min_el_deg=30.0, eop=None):
    """All culminations above `min_el_deg` within `days` of the TLE epoch, seen from (`lat_deg`, `lon_deg`).

    `ephemeris` is the path of a JPL ephemeris (`de421.bsp`), used for the sun only; it chooses a pass at
    authoring time and is never a run input. Returns a list of `Pass`.
    """
    from skyfield.api import EarthSatellite, load_file, wgs84
    ts = _timescale(eop)
    sat = EarthSatellite(line1, line2, None, ts)
    planets = load_file(str(ephemeris))
    target = wgs84.latlon(lat_deg, lon_deg)
    t_ev, kind = sat.find_events(target, sat.epoch, sat.epoch + days, altitude_degrees=min_el_deg)
    out = []
    for tc in t_ev[kind == 1]:                               # 1 = culmination
        el = (sat - target).at(tc).altaz()[0].degrees
        sun_el = (planets["earth"] + target).at(tc).observe(planets["sun"]).apparent().altaz()[0].degrees
        c = tc.utc_datetime()
        out.append(Pass(_utc_iso(c), c.timestamp(), float(el), float(sun_el)))
    return out


def choose_pass(candidates, min_sun_deg=20.0):
    """The stated rule: highest culmination among daylight (sun >= min_sun_deg) candidates."""
    daylight = [c for c in candidates if c.sun_el_deg >= min_sun_deg]
    assert daylight, "no daylight pass in the search window"
    return max(daylight, key=lambda c: c.max_el_deg)


def pass_epoch(culmination_s, duration):
    """Window start: `duration` s centred on culmination (POSIX seconds), rounded to a whole UTC second."""
    return datetime.fromtimestamp(round(culmination_s) - duration / 2, tz=timezone.utc)


# --- the TEME -> ITRS check ------------------------------------------------------------------------

def gmst82(ut1_jd):
    """IAU-1982 Greenwich mean sidereal time (rad) from a UT1 Julian date. Check only."""
    tu = (ut1_jd - 2451545.0) / 36525.0
    sec = 67310.54841 + (876600 * 3600 + 8640184.812866) * tu + 0.093104 * tu**2 - 6.2e-6 * tu**3
    return np.radians((sec % 86400.0) / 240.0)


def check_teme_to_itrs(pos, pos_teme, ut1_jd, t):
    """The three independent checks on the propagator's TEME -> ITRS rotation; asserts, returns the numbers."""
    rot = np.unwrap(np.arctan2(pos_teme[:, 1], pos_teme[:, 0]) - np.arctan2(pos[:, 1], pos[:, 0]))
    rot_err = np.angle(np.exp(1j * (rot - gmst82(ut1_jd))))
    res = {
        "max_dz_m": float(np.abs(pos_teme[:, 2] - pos[:, 2]).max()),
        "max_gmst_err_arcsec": float(np.degrees(np.abs(rot_err)).max() * 3600),
        "rate_rad_s": float(np.polyfit(t, rot, 1)[0]),
        "teme_as_ecef_err_km": (float(np.linalg.norm(pos_teme - pos, axis=1).min() / 1e3),
                                float(np.linalg.norm(pos_teme - pos, axis=1).max() / 1e3)),
    }
    assert res["max_dz_m"] < 1.0
    assert res["max_gmst_err_arcsec"] < 1.0
    assert abs(res["rate_rad_s"] / OMEGA_EARTH - 1) < 1e-4
    return res


def teme_to_itrs_gmst82(pos_teme, ut1_jd):
    """TEME -> ITRS by the GMST-1982 rotation about z alone (no polar motion): the second, hand-written path."""
    g = gmst82(np.asarray(ut1_jd, dtype=float))
    c, s = np.cos(g), np.sin(g)
    x, y, z = np.asarray(pos_teme, dtype=float).T
    return np.column_stack([c * x + s * y, -s * x + c * y, z])



def bundled_eop_path():
    """The path of skyfield's bundled Earth-orientation tables (`iers.npz`), found without importing skyfield."""
    from importlib.util import find_spec
    return Path(find_spec("skyfield").submodule_search_locations[0]) / "data" / "iers.npz"


def itrs_by_sgp4_gmst82(line1, line2, epoch, t, eop=None):
    """The second, independent path to the trajectory: the `sgp4` package directly, then `teme_to_itrs_gmst82`
    with UT1 interpolated linearly from the Earth-orientation arrays (`eop`, default the bundled `iers.npz`).
    Shares no code with `propagate` beyond the SGP4 theory and the data. Returns (pos_teme, pos_itrs, ut1_jd)."""
    from sgp4.api import Satrec, jday
    if isinstance(epoch, str):
        epoch = datetime.fromisoformat(epoch.replace("Z", "+00:00"))
    epoch = epoch.astimezone(timezone.utc)
    arrays = np.load(eop or bundled_eop_path())
    daily_tt = arrays["tt_jd_minus_arange"] + np.arange(len(arrays["tt_jd_minus_arange"]))
    daily_delta_t = arrays["delta_t_1e7"] / 1e7
    jd0, fr0 = jday(epoch.year, epoch.month, epoch.day, epoch.hour, epoch.minute,
                    epoch.second + epoch.microsecond / 1e6)
    fr = fr0 + np.asarray(t, dtype=float) / 86400.0
    err, r, _ = Satrec.twoline2rv(line1, line2).sgp4_array(np.full(fr.shape, jd0), fr)
    assert not err.any(), f"sgp4 error codes {set(err.tolist())}"
    tai_utc = arrays["leap_offsets"][np.searchsorted(arrays["leap_dates"], jd0 + fr, side="right") - 1]
    tt = jd0 + fr + (tai_utc + 32.184) / 86400.0
    ut1 = tt - np.interp(tt, daily_tt, daily_delta_t) / 86400.0
    pos_teme = r * 1e3
    return pos_teme, teme_to_itrs_gmst82(pos_teme, ut1), ut1

# --- geodesy ---------------------------------------------------------------------------------

def ecef_to_geodetic(xyz, iters=6):
    """ECEF (m) -> (lat deg, lon deg, height m) on WGS-84, by fixed-point iteration on latitude."""
    x, y, z = np.asarray(xyz, dtype=float).T
    lon = np.arctan2(y, x)
    p = np.hypot(x, y)
    lat = np.arctan2(z, p * (1 - WGS84_E2))
    for _ in range(iters):
        n = WGS84_A / np.sqrt(1 - WGS84_E2 * np.sin(lat) ** 2)
        h = p / np.cos(lat) - n
        lat = np.arctan2(z, p * (1 - WGS84_E2 * n / (n + h)))
    n = WGS84_A / np.sqrt(1 - WGS84_E2 * np.sin(lat) ** 2)
    h = p / np.cos(lat) - n
    return np.degrees(lat), np.degrees(lon), h


def ground_km(lat1, lon1, lat2, lon2):
    """Great-circle distance (km, spherical Earth) — adequate for a sanity check."""
    p1, p2, dl = np.radians(lat1), np.radians(lat2), np.radians(lon2 - lon1)
    return 6371.0 * np.arccos(np.clip(np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(dl), -1, 1))


def ecef_to_enu_matrix(lat_deg, lon_deg):
    """Rows are the local East, North, Up unit vectors in ECEF at (lat, lon): v_enu = M @ v_ecef."""
    phi, lam = np.radians(lat_deg), np.radians(lon_deg)
    e = np.array([-np.sin(lam), np.cos(lam), 0.0])
    n = np.array([-np.sin(phi) * np.cos(lam), -np.sin(phi) * np.sin(lam), np.cos(phi)])
    return np.vstack([e, n, np.cross(e, n)])



def recover_position(hits, distances, s0, iters=8):
    """The sensor position S that best satisfies |S - P_i| = d_i (Gauss-Newton, least squares), from truth hit
    points `hits` (N, 3, ECEF m) and sensor-to-hit distances `distances` (N,), started at `s0`. Non-finite rows
    are dropped. Returns (S, rms residual m, covariance (3, 3) m^2, pixels used). Independent of the propagator:
    it reads only what the engine rendered."""
    P, d = np.asarray(hits, dtype=float), np.asarray(distances, dtype=float)
    ok = np.all(np.isfinite(P), axis=1) & np.isfinite(d)
    P, d = P[ok], d[ok]
    s = np.array(s0, dtype=float)
    for _ in range(iters):
        diff = s - P
        rng = np.linalg.norm(diff, axis=1)
        J = diff / rng[:, None]
        step, *_ = np.linalg.lstsq(J, -(rng - d), rcond=None)
        s = s + step
        if np.linalg.norm(step) < 1e-4:
            break
    r = np.linalg.norm(s - P, axis=1) - d
    cov = np.linalg.inv(J.T @ J) * np.var(r)
    return s, float(np.sqrt(np.mean(r**2))), cov, int(ok.sum())

# --- LookAt up vector --------------------------------------------------------------------------

def perp_unit(u, b):
    """Component of u perpendicular to unit vector(s) b, normalised."""
    p = u - np.sum(u * b, axis=-1, keepdims=True) * b
    return p / np.linalg.norm(p, axis=-1, keepdims=True)


def along_track_up(vel_enu, i):
    """The fixed along-track up: horizontal (E, N) direction of the velocity at sample i, rounded."""
    along = np.array(vel_enu[i], dtype=float)
    along[2] = 0.0
    along /= np.linalg.norm(along)
    return [round(float(v), 6) for v in along]


def up_vector_check(up, bore_enu, vel_enu):
    """Per-sample (angle between up and boresight, roll of the fixed up vs velocity-up), degrees.

    `bore_enu` are unit line-of-sight vectors in the scene ENU frame, `vel_enu` the platform
    velocity in the same frame. Roll is measured after projecting both references onto the
    plane perpendicular to the boresight, which is what actually fixes the image roll.
    """
    up = np.array(up, float) / np.linalg.norm(up)
    ang = np.degrees(np.arccos(np.clip(bore_enu @ up, -1, 1)))
    vel_up = perp_unit(vel_enu / np.linalg.norm(vel_enu, axis=1, keepdims=True), bore_enu)
    roll = np.degrees(np.arccos(np.clip(
        np.sum(perp_unit(np.broadcast_to(up, bore_enu.shape), bore_enu) * vel_up, axis=1), -1, 1)))
    return ang, roll


# --- dirfm motion --------------------------------------------------------------------------------

def thin(t, pos, dense_dt, waypoint_dt):
    """Thin a dense track to `waypoint_dt` spacing; returns (t_wp, pos_wp, max linear-interp error m)."""
    step = int(round(waypoint_dt / dense_dt))
    idx = np.arange(0, len(t), step)
    assert idx[-1] == len(t) - 1, "thinning must keep the final sample"
    t_wp, pos_wp = t[idx], pos[idx]
    interp = np.column_stack([np.interp(t, t_wp, pos_wp[:, k]) for k in range(3)])
    return t_wp, pos_wp, float(np.linalg.norm(interp - pos, axis=1).max())


def lookat_motion(t_wp, pos_wp, look_at, up):
    """dirfm FlexMotion: ECEF waypoints (relative seconds) + LookAt at `look_at` with a fixed `up`.

    `look_at` is a dirfm Frame: ECEFFrame(0, 0, 0) for nadir, or ENUFrame(x, y, z) to stare at a
    scene point.
    """
    from dirfm import flexible_motion as fm
    location = fm.WaypointsLocationEngine(frame="ecef")
    for ti, p in zip(t_wp, pos_wp):
        location.add_point(round(float(ti), 6), [float(v) for v in p])
    orientation = fm.LookAtOrientationEngine(fm.FixedLocationEngine(look_at), up=up)
    return fm.FlexMotion(location, orientation)
