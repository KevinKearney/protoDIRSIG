"""Phase 4a: cross-check protodirsig.orbit (skyfield SGP4 -> ITRS waypoints) against DIRSIG's
own `<locationengine type="sgp4">`, on tutorial_tacoma_scene.ipynb's WorldView-2-over-Tacoma pass.

Two renders that differ ONLY in the location engine:
  A  "skyfield": ECEF waypoints from protodirsig.orbit (exactly what the Tacoma notebook uses)
  B  "native"  : the same TLE lines handed to DIRSIG's built-in SGP4 engine
Same scene reference, sensor, atmosphere, TASKS (PASS_EPOCH, one frame at t = 60 s), same LookAt
orientation. The sensor adds the Geolocation truth collector (ECEF hit points) to the notebook's
Intersection truth; truth collectors do not change the radiance.

Why not just compare boresight intercepts: the camera stares at a fixed scene point, so the
frame centre hits that point whatever the platform position is. So in addition to the pixel-wise
truth comparison, the platform's ECEF position is RECOVERED from each truth image: every pixel
gives an ECEF hit point P_i and a sensor-to-hit distance d_i, and the sensor position S is the
least-squares solution of |S - P_i| = d_i over all pixels (Gauss-Newton). Run A calibrates the
method (its true position is known exactly: it is a waypoint); run B is the independent answer.

Run from the project root:  python scripts/crosscheck_sgp4.py   (writes under outputs/sgp4_check/)
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
DIRSIG_HOME = Path(os.environ.get("DIRSIG_HOME", Path.home() / "DIRSIG" / "dirsig-2026.38.0.a020954-Linux-x86_64"))
os.environ["DIRSIG_HOME"] = str(DIRSIG_HOME)
os.environ["PATH"] = f"{DIRSIG_HOME / 'bin'}{os.pathsep}" + os.environ.get("PATH", "")

import lxml.etree as et                                   # noqa: E402
from dirfm import DIRSIG, SCENE, TASKS, frames            # noqa: E402
from dirfm import flexible_motion as fm                   # noqa: E402
from skyfield.api import EarthSatellite, Loader, wgs84    # noqa: E402
from spectral import open_image                           # noqa: E402

from protodirsig import orbit, sensors                    # noqa: E402
from protodirsig.scene_ref import fingerprint, reference_scene  # noqa: E402

TACOMA = DIRSIG_HOME / "Tacoma-08-Apr-2022" / "Tacoma"
WORK = PROJECT / "outputs" / "sgp4_check"
DATA_DIR = PROJECT / "outputs" / "_orbit_data"
FOCAL_MM, NPIX, PITCH_UM = 3000, 512, 8                   # tutorial_tacoma_scene.ipynb Stage 2
PASS_DURATION, DENSE_DT, FRAME_T = 120.0, 0.01, 60.0
C_LIGHT = 299792458.0


class Sgp4LocationEngine(fm.LocationEngine):
    """DIRSIG's native `<locationengine type="sgp4">` (flex_motion.html#SGP4); dirfm has no wrapper."""

    def __init__(self, tle1, tle2):
        self._tle = (tle1, tle2)

    def write(self, root):
        data = et.SubElement(et.SubElement(root, "locationengine", type="sgp4"), "data", source="internal")
        et.SubElement(data, "tle1").text = self._tle[0]
        et.SubElement(data, "tle2").text = self._tle[1]


def tacoma_pass():
    """The Tacoma notebook's Stage 1, via the same protodirsig.orbit calls and parameters."""
    scene_xml = et.parse(str(TACOMA / "tacoma.scene")).getroot()
    loc = scene_xml.find("sceneorigin/location")
    lat0, lon0 = float(loc.findtext("latitude")), float(loc.findtext("longitude"))
    inst = re.search(r"OBJ_FILENAME\s*=\s*ground_large\.obj.*?INFO\s*=\s*([^\n]+)",
                     (TACOMA / "geometry" / "terrain.odb").read_text(), flags=re.S).group(1)
    aim = [round(float(v), 3) for v in inst.split(",")[:3]]

    _, name, l1, l2 = orbit.fetch_tle(35946, DATA_DIR, expect_name="WORLDVIEW-2", expect_intl="09055A")
    load = Loader(DATA_DIR, verbose=False)
    ts = load.timescale()
    sat = EarthSatellite(l1, l2, name, ts)
    planets = load("de421.bsp")
    target = wgs84.latlon(lat0, lon0)
    t_culm, _, _ = orbit.choose_pass(orbit.find_passes(sat, target, planets["earth"], planets["sun"]))
    epoch = orbit.pass_epoch(t_culm, PASS_DURATION)
    t = np.arange(round(PASS_DURATION / DENSE_DT) + 1) * DENSE_DT
    times, _, pos, pos_teme = orbit.propagate(sat, ts, epoch, t)
    orbit.check_teme_to_itrs(pos, pos_teme, times, t)
    m = orbit.ecef_to_enu_matrix(lat0, lon0)
    k = int(round(FRAME_T / DENSE_DT))
    up = orbit.along_track_up(np.gradient(pos, t, axis=0) @ m.T, k)
    return dict(l1=l1, l2=l2, epoch=epoch, t=t, pos=pos, k=k, aim=aim, up=up, sat=sat, ts=ts,
                vel=np.gradient(pos, t, axis=0))


def render(tag, motion, p, ref_file):
    in_dir, out_dir = WORK / f"{tag}_input", WORK / f"{tag}_output"
    scene = SCENE("tacoma")
    scene._fname = ref_file
    camera = sensors.make_rgb_camera(focal=FOCAL_MM, nx=NPIX, ny=NPIX, pitch=PITCH_UM,
                                     truth=("Intersection", "Geolocation"))
    job = DIRSIG(in_dir, out_dir)
    job.add_plugin(sensors.simple_atmosphere())
    job.add_plugin(camera.set_motion(motion).set_tasks(TASKS(p["epoch"]).add_start_stop(FRAME_T, FRAME_T)))
    job.add_scene(scene, [0, 0, 0])
    before = fingerprint(TACOMA.parent)
    t0 = time.perf_counter()
    job.run()
    elapsed = time.perf_counter() - t0
    assert fingerprint(TACOMA.parent) == before, "the Tacoma bundle changed during the run"
    tr = open_image(str(out_dir / "truth.img.hdr"))
    truth = {n: np.asarray(tr.read_band(i), dtype=float) for i, n in enumerate(tr.metadata["band names"])}
    rgb = np.asarray(open_image(str(out_dir / "demo.img.hdr")).load(), dtype=float)
    motion_xml = (in_dir / "example.motion").read_text()
    return dict(truth=truth, rgb=rgb, elapsed=elapsed, motion_xml=motion_xml)


def band(truth, pattern):
    hits = [n for n in truth if re.search(pattern, n, re.IGNORECASE)]
    assert len(hits) == 1, f"{pattern!r} matched {hits} in {list(truth)}"
    return truth[hits[0]]


def recover_sensor(truth, s0, iters=8):
    """Least-squares S with |S - P_i| = d_i over all pixels; returns S, rms residual, covariance."""
    P = np.column_stack([band(truth, r"ecef\s*x").ravel(), band(truth, r"ecef\s*y").ravel(),
                         band(truth, r"ecef\s*z").ravel()])
    d = band(truth, r"^distance").ravel()
    ok = np.all(np.isfinite(P), axis=1) & np.isfinite(d)
    P, d = P[ok], d[ok]
    s = np.array(s0, float)
    for _ in range(iters):
        diff = s - P
        rng = np.linalg.norm(diff, axis=1)
        J = diff / rng[:, None]
        r = rng - d
        step, *_ = np.linalg.lstsq(J, -r, rcond=None)
        s = s + step
        if np.linalg.norm(step) < 1e-4:
            break
    r = np.linalg.norm(s - P, axis=1) - d
    cov = np.linalg.inv(J.T @ J) * np.var(r)
    return s, float(np.sqrt(np.mean(r**2))), cov, int(ok.sum())


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    p = tacoma_pass()
    ref_file = reference_scene(TACOMA / "tacoma.scene", WORK / "tacoma_ref")
    t_wp, pos_wp, _ = orbit.thin(p["t"], p["pos"], DENSE_DT, 1.0)

    runs = {
        "skyfield": render("skyfield", orbit.lookat_motion(t_wp, pos_wp, frames.ENUFrame(*p["aim"]), p["up"]), p, ref_file),
        "native": render("native", fm.FlexMotion(Sgp4LocationEngine(p["l1"], p["l2"]),
                                                 fm.LookAtOrientationEngine(fm.FixedLocationEngine(frames.ENUFrame(*p["aim"])), up=p["up"])),
                         p, ref_file),
    }
    assert 'type="sgp4"' in runs["native"]["motion_xml"] and p["l1"] in runs["native"]["motion_xml"]
    assert 'type="waypoints"' in runs["skyfield"]["motion_xml"]

    truth_pos = p["pos"][p["k"]]                     # skyfield ITRS at t = 60 s (= a waypoint row)
    vel = p["vel"][p["k"]]
    along = vel / np.linalg.norm(vel)
    radial = truth_pos / np.linalg.norm(truth_pos)
    cross = np.cross(radial, along)
    basis = np.vstack([along, cross / np.linalg.norm(cross), radial])   # rows: along, cross, radial

    out = {"pass_epoch": p["epoch"].isoformat(), "frame_t": FRAME_T, "tle": [p["l1"], p["l2"]],
           "speed_m_s": float(np.linalg.norm(vel))}
    rec = {}
    for tag, r in runs.items():
        s, rms, cov, n = recover_sensor(r["truth"], truth_pos)
        rec[tag] = s
        d = s - truth_pos
        out[tag] = {"render_s": round(r["elapsed"], 1), "pixels_used": n, "recovered_ecef_m": s.tolist(),
                    "fit_rms_m": rms, "fit_sigma_m": np.sqrt(np.diag(cov)).tolist(),
                    "minus_skyfield_m": d.tolist(), "minus_skyfield_acr_m": (basis @ d).tolist(),
                    "minus_skyfield_norm_m": float(np.linalg.norm(d))}

    diff = rec["native"] - rec["skyfield"]
    out["native_minus_skyfield_recovered_m"] = diff.tolist()
    out["native_minus_skyfield_recovered_acr_m"] = (basis @ diff).tolist()
    out["native_minus_skyfield_recovered_norm_m"] = float(np.linalg.norm(diff))
    out["equivalent_time_offset_s"] = float(np.dot(diff, along) / np.linalg.norm(vel))

    # Pixel-wise truth comparison.
    A, B = runs["skyfield"]["truth"], runs["native"]["truth"]
    xa, ya = band(A, r"scene enu x"), band(A, r"scene enu y")
    xb, yb = band(B, r"scene enu x"), band(B, r"scene enu y")
    dxy = np.hypot(xb - xa, yb - ya)
    c0 = NPIX // 2
    cen = lambda x: float(x[c0 - 1:c0 + 1, c0 - 1:c0 + 1].mean())
    out["pixelwise"] = {
        "centre_skyfield_xy": [cen(xa), cen(ya)], "centre_native_xy": [cen(xb), cen(yb)],
        "centre_shift_m": float(np.hypot(cen(xb) - cen(xa), cen(yb) - cen(ya))),
        "xy_shift_median_m": float(np.nanmedian(dxy)), "xy_shift_p99_m": float(np.nanpercentile(dxy, 99)),
        "xy_shift_max_m": float(np.nanmax(dxy)),
        "distance_diff_median_m": float(np.nanmedian(band(B, r"^distance") - band(A, r"^distance"))),
        "rgb_identical": bool(np.array_equal(runs["skyfield"]["rgb"], runs["native"]["rgb"])),
        "rgb_max_abs_diff": float(np.abs(runs["native"]["rgb"] - runs["skyfield"]["rgb"]).max()),
    }
    out["light_time_s"] = float(np.linalg.norm(truth_pos - wgs84.latlon(47.27, -122.41).itrs_xyz.m) / C_LIGHT)
    out["truth_bands"] = list(A)

    (WORK / "result.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
