"""TLE -> SGP4 -> ITRS (ECEF) trajectory helpers, factored out of tutorial_orbit_to_ground.ipynb.

Every function here is the code that notebook's Stage 1 built and verified inline (the
notebook keeps its inline copies because they *are* the explanation). The derivations and the
reasons for each check live there and in FINDINGS.md; this module only makes them reusable.
"""
import urllib.request
from datetime import datetime, timezone

import numpy as np

MU_EARTH = 3.986004418e14            # m^3/s^2
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

    comment, name, line1, line2 = [ln.rstrip() for ln in path.read_text().splitlines()]
    assert line1.startswith("1 ") and line2.startswith("2 ") and len(line1) == len(line2) == 69
    assert tle_checksum_ok(line1) and tle_checksum_ok(line2), "TLE checksum failure"
    assert int(line1[2:7]) == int(line2[2:7]) == norad_id
    if expect_name:
        assert expect_name.upper() in name.upper(), f"catalog {norad_id} is {name!r}, not {expect_name}"
    if expect_intl:
        assert line1[9:17].strip() == expect_intl, f"international designator {line1[9:17]!r} != {expect_intl}"
    return comment, name, line1, line2


def mean_altitude_km(sat):
    """Kepler's-third-law mean altitude from the TLE mean motion (independent of propagation)."""
    n_rad_s = sat.model.no_kozai / 60.0
    return ((MU_EARTH / n_rad_s**2) ** (1 / 3) - WGS84_A) / 1e3


# --- pass selection --------------------------------------------------------------------------

def find_passes(sat, target, earth, sun, days=7, min_el_deg=30.0):
    """All culminations above `min_el_deg` within `days` of the TLE epoch, seen from `target`.

    Returns a list of (skyfield Time, max elevation deg, sun elevation deg at the target).
    """
    t_ev, kind = sat.find_events(target, sat.epoch, sat.epoch + days, altitude_degrees=min_el_deg)
    out = []
    for tc in t_ev[kind == 1]:                               # 1 = culmination
        el = (sat - target).at(tc).altaz()[0].degrees
        sun_el = (earth + target).at(tc).observe(sun).apparent().altaz()[0].degrees
        out.append((tc, el, sun_el))
    return out


def choose_pass(candidates, min_sun_deg=20.0):
    """The stated rule: highest culmination among daylight (sun >= min_sun_deg) candidates."""
    daylight = [c for c in candidates if c[2] >= min_sun_deg]
    assert daylight, "no daylight pass in the search window"
    return max(daylight, key=lambda c: c[1])


def pass_epoch(t_culm, duration):
    """Window start: `duration` s centred on culmination, rounded to a whole UTC second."""
    c = t_culm.utc_datetime()
    return datetime.fromtimestamp(round(c.timestamp()) - duration / 2, tz=timezone.utc)


# --- propagation and the TEME -> ITRS check ------------------------------------------------------

def propagate(sat, ts, epoch, t):
    """SGP4 at `epoch + t` seconds. Returns (skyfield Time, geocentric, pos ITRS (N,3), pos TEME (N,3))."""
    from skyfield.framelib import itrs
    from skyfield.sgp4lib import TEME
    times = ts.utc(epoch.year, epoch.month, epoch.day, epoch.hour, epoch.minute, epoch.second + t)
    geo = sat.at(times)
    return times, geo, geo.frame_xyz(itrs).m.T, geo.frame_xyz(TEME).m.T


def gmst82(ut1_jd):
    """IAU-1982 Greenwich mean sidereal time (rad) from a UT1 Julian date. Check only."""
    tu = (ut1_jd - 2451545.0) / 36525.0
    sec = 67310.54841 + (876600 * 3600 + 8640184.812866) * tu + 0.093104 * tu**2 - 6.2e-6 * tu**3
    return np.radians((sec % 86400.0) / 240.0)


def check_teme_to_itrs(pos, pos_teme, times, t):
    """The three independent checks on skyfield's TEME -> ITRS rotation; asserts, returns the numbers."""
    rot = np.unwrap(np.arctan2(pos_teme[:, 1], pos_teme[:, 0]) - np.arctan2(pos[:, 1], pos[:, 0]))
    rot_err = np.angle(np.exp(1j * (rot - gmst82(times.ut1))))
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
