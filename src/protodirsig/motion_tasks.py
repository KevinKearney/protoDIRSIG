"""Generate a job's platform motion (`.ppd`) and tasks (`.tasks`) files from a resolved run spec.

`engine.motion` and `engine.tasks` used to describe received files; since Stage 05 they are the input that
builds them, as MANIFOLD's executor materializes a run tree from its run spec (AV_MANIFOLD_Configuration_v02 §2).
`generate_motion` dispatches on the motion kind: `static` writes a `.ppd` with dirfm's `PlatformPosition`; `orbit`
(proposed) propagates the TLE over the window (`orbit.propagate`), thins the track to the waypoint spacing
(`orbit.thin`) and writes a FlexMotion `.motion`: ECEF waypoints and a LookAt at a scene ENU point with the fixed
along-track up (`orbit.lookat_motion`). These functions are the only users of `PlatformPosition` and `TASKS`.

dirfm behaviour the output depends on:
- `PlatformPosition` always writes `rotationframe="sceneenu"` and `location type="scene"`, and
  formats positions to 3 decimals and angles to 6 (`3.141592654` becomes `3.141593`).
- `TASKS.write` returns None, so the path is built here. It formats the reference offset as
  `strftime("%z")[:-2] + ":00"`, which needs a timezone-aware datetime and drops the minutes of
  a non-whole-hour offset; `run.epoch` is UTC, so neither applies.
"""
from dirfm.platform_motion import PlatformPosition
from dirfm.tasks import TASKS


DENSE_PER_WAYPOINT = 10          # orbit: propagation samples per waypoint interval, thinned to the waypoints


def orbit_waypoints(run):
    """An orbit run's waypoints: (t_wp relative to the epoch, ECEF positions (N, 3) m, the fixed along-track up in
    scene ENU, the largest linear-interpolation error of the thinned track against the dense one, in metres)."""
    import numpy as np

    from protodirsig import orbit
    o = run.orbit
    _, _, line1, line2 = orbit.read_tle(o["tle"])
    dt = o["waypoint_spacing"] / DENSE_PER_WAYPOINT
    n = int(round(o["window_duration"] / dt))
    t = o["window_start"] + np.arange(n + 1) * dt
    traj = orbit.propagate(line1, line2, run.epoch, t, eop=o["earth_orientation"])
    t_wp, pos_wp, err = orbit.thin(t, traj.pos_itrs, dt, o["waypoint_spacing"])
    to_enu = orbit.ecef_to_enu_matrix(*o["scene_origin"])
    up = orbit.along_track_up(traj.vel_itrs @ to_enu.T, n // 2)
    return t_wp, pos_wp, up, err


def generate_motion(run, motion_dir, name=None):
    """Write the platform motion file for `run` and return its path: for `static`, a single-entry `.ppd` at
    relative time 0 from the position and Euler orientation (default name `motion.ppd`); for `orbit`, a
    FlexMotion `.motion` of ECEF waypoints with a LookAt (default name `motion.motion`)."""
    motion_dir.mkdir(parents=True, exist_ok=True)
    if run.motion_kind == "orbit":
        from dirfm import frames

        from protodirsig import orbit
        t_wp, pos_wp, up, _ = orbit_waypoints(run)
        motion = orbit.lookat_motion(t_wp, pos_wp, frames.ENUFrame(*run.orbit["lookat_target"]), up)
        motion.write({"root": motion_dir}, name=name or "motion.motion")
        return motion_dir / (name or "motion.motion")
    name = name or "motion.ppd"
    o = run.motion_orientation
    pos = PlatformPosition(rotationorder=o["order"], angularunits=o["units"])
    pos.add_entry(0.0, run.motion_position, o["angles"])
    return pos.write({"root": motion_dir}, name=name)


def generate_tasks(run, tasks_dir, name="tasks.tasks"):
    """Write a `.tasks` file: reference datetime `run.epoch`, one task per window. Returns its path."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    t = TASKS(run.epoch)
    for start, stop in run.tasks_windows:
        t.add_start_stop(start, stop)
    t.write({"root": tasks_dir}, name=name)                  # returns None
    return tasks_dir / name
