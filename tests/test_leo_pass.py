"""The LEO pass recipe (recipes/leo_pass_tahoe.yaml): composition, and the three-frame render checked independently.

Composition: the composed spec passes the run-spec checks, composes to the same bytes twice, and names no path
outside the libraries (its run-id inputs are the document alone).

Render (16 x 16, three frames 10 s apart, about 3 s on the development machine, so it runs in the normal suite where
DIRSIG is installed): each check uses something the generator did not produce. (a) The platform position recovered
from each frame's truth (Gauss-Newton on hit points and distances, orbit.recover_position) is the generated
waypoint track at the frame time. (b) The track's sub-satellite points equal those of a track computed by the sgp4
package and the GMST-1982 rotation (orbit.itrs_by_sgp4_gmst82). (c) The frame-centre intercept is the LookAt target
within a pixel footprint. (d) The three positions are distinct and about speed x 10 s apart.
"""
from pathlib import Path

import numpy as np
import yaml

from protodirsig import orbit
from protodirsig.compose import HEADER, compose, dump
from protodirsig.motion_tasks import orbit_waypoints
from protodirsig.simulation import schema_errors
from test_simulation import needs_dirsig

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "manifold_run_specs" / "recipes" / "leo_pass_tahoe.yaml"
GENERATED = ROOT / "manifold_run_specs" / "leo_pass_tahoe.yaml"
CONFIG_REPO = ROOT / "manifold_config_repo"
SENSORS = ROOT / "manifold_sensors"


def test_pass_spec_passes_the_run_spec_checks():
    spec = compose(RECIPE)
    assert schema_errors(spec) == []
    assert spec["engine"]["motion"]["kind"] == "orbit" and len(spec["engine"]["tasks"]["windows"]) == 3


def test_pass_spec_composes_to_the_same_bytes_twice():
    a, b = (dump(compose(RECIPE), "recipes/leo_pass_tahoe.yaml") for _ in range(2))
    assert a == b == GENERATED.read_text()
    assert a.startswith(HEADER.format(recipe="recipes/leo_pass_tahoe.yaml"))


def _strings(node, where=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _strings(v, f"{where}.{k}" if where else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _strings(v, f"{where}[{i}]")
    elif isinstance(node, str):
        yield where, node


def _refs(node, where=""):
    if isinstance(node, dict):
        if set(node) >= {"name", "content_hash"}:
            yield where, node["name"]
        for k, v in node.items():
            yield from _refs(v, f"{where}.{k}" if where else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _refs(v, f"{where}[{i}]")


def test_pass_spec_names_no_path_outside_the_libraries():
    spec = yaml.safe_load(GENERATED.read_text())
    for where, s in _strings(spec):
        assert not s.startswith(("/", "~")) and ".." not in Path(s).parts and "outputs/" not in s, (where, s)
    refs = dict(_refs(spec))
    assert {"engine.motion.orbit.tle", "engine.motion.orbit.earth_orientation"} <= set(refs)
    for where, name in refs.items():
        root = SENSORS if where.startswith("descriptor.sensor") else CONFIG_REPO
        assert (root / name).resolve().is_relative_to(root.resolve()), (where, name)
        assert (root / name).is_file(), (where, name)


def _truth(path):
    from spectral import open_image
    img = open_image(str(path) + ".hdr")
    return {n.split(" [")[0]: np.asarray(img.read_band(i), dtype=float) for i, n in enumerate(img.metadata["band names"])}


def ground_track_check(work_dir):
    """Render the pass and return the independent checks' numbers (also used by the stage notebook)."""
    from protodirsig.registry import LocalRegistry
    sub = LocalRegistry().submit(GENERATED, CONFIG_REPO, work_dir)
    assert sub.accepted, sub.reasons
    res = sub.simulation.run()
    run = sub.simulation.auror_run
    t_wp, pos_wp, _, _ = orbit_waypoints(run)
    interp = lambda t: np.array([np.interp(t, t_wp, pos_wp[:, k]) for k in range(3)])
    out = {"frames": [], "propagator": res.propagator}
    target = np.array(run.orbit["lookat_target"])
    recovered = []
    for f in res.frames:
        tr = _truth(f.truth[0])
        hits = np.column_stack([tr[f"ECEF {c} Coordinate"].ravel() for c in "XYZ"])
        t0 = f.time_window[0]
        s, rms, cov, n = orbit.recover_position(hits, tr["Distance"].ravel(), interp(t0) + 500.0)
        recovered.append(s)
        enu = np.dstack([tr[f"Scene ENU {c} Coordinate"] for c in "XYZ"])
        c = enu.shape[0] // 2
        centre = enu[c - 1:c + 1, c - 1:c + 1].reshape(-1, 3).mean(axis=0)
        footprint = float(np.median(np.hypot(*np.diff(enu[:, :, :2], axis=1).reshape(-1, 2).T)))
        out["frames"].append({"t_s": t0, "image": f.image.name, "truth": f.truth[0].name,
                              "recovered_minus_track_m": float(np.linalg.norm(s - interp(t0))),
                              "fit_sigma_m": np.sqrt(np.diag(cov)).tolist(), "fit_rms_m": rms, "pixels": n,
                              "centre_enu_m": centre.tolist(),
                              "boresight_miss_m": float(np.hypot(*(centre[:2] - target[:2]))),
                              "pixel_footprint_m": footprint})
    _, _, l1, l2 = orbit.read_tle(run.orbit["tle"])
    _, itrs2, _ = orbit.itrs_by_sgp4_gmst82(l1, l2, run.epoch, t_wp, eop=run.orbit["earth_orientation"])

    def subsat(pos):
        lat, lon, _ = orbit.ecef_to_geodetic(pos)
        la, lo = np.radians(lat), np.radians(lon)
        n_ = orbit.WGS84_A / np.sqrt(1 - orbit.WGS84_E2 * np.sin(la) ** 2)
        return np.column_stack([n_ * np.cos(la) * np.cos(lo), n_ * np.cos(la) * np.sin(lo),
                                n_ * (1 - orbit.WGS84_E2) * np.sin(la)])
    out["ground_track_diff_m"] = float(np.linalg.norm(subsat(pos_wp) - subsat(itrs2), axis=1).max())
    speed = np.linalg.norm(orbit.propagate(l1, l2, run.epoch, [f.time_window[0] for f in res.frames],
                                           eop=run.orbit["earth_orientation"]).vel_itrs, axis=1)
    out["separations_m"] = [float(np.linalg.norm(b - a)) for a, b in zip(recovered, recovered[1:])]
    out["speed_x_10s_m"] = [float(10 * v) for v in (speed[:-1] + speed[1:]) / 2]
    return out


@needs_dirsig
def test_three_frame_render_and_independent_ground_track(tmp_path):
    import json
    out = ground_track_check(tmp_path / "work")
    tol = json.loads((ROOT / "manifold_contracts" / "vectors" / "orbit" / "expected.json").read_text())["tolerance_m"]
    assert [f["t_s"] for f in out["frames"]] == [50.0, 60.0, 70.0]
    assert len({f["image"] for f in out["frames"]}) == 3 and len({f["truth"] for f in out["frames"]}) == 3
    for f in out["frames"]:
        assert f["recovered_minus_track_m"] < 1.0, f                                   # (a)
        assert f["boresight_miss_m"] < f["pixel_footprint_m"], f                         # (c)
    assert out["ground_track_diff_m"] < tol, out["ground_track_diff_m"]                  # (b)
    for sep, want in zip(out["separations_m"], out["speed_x_10s_m"]):                    # (d)
        assert abs(sep - want) / want < 0.01, (sep, want)
    assert out["propagator"]["tag"] == "skyfield_sgp4"
