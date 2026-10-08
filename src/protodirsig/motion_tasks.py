"""Generate a job's platform motion (`.ppd`) and tasks (`.tasks`) files from a resolved run spec.

`engine.motion` (`kind: static`) and `engine.tasks` used to describe received files; since
Stage 05 they are the input that builds them, as MANIFOLD's executor materializes a run tree from
its run spec (AV_MANIFOLD_Configuration_v02 §2). These two functions are the only users of
dirfm's `PlatformPosition` and `TASKS`.

dirfm behaviour the output depends on (FINDINGS.md, "2026-10-08 — Stage 05"):
- `PlatformPosition` always writes `rotationframe="sceneenu"` and `location type="scene"`, and
  formats positions to 3 decimals and angles to 6 (`3.141592654` becomes `3.141593`).
- `TASKS.write` returns None, so the path is built here. It formats the reference offset as
  `strftime("%z")[:-2] + ":00"`, which needs a timezone-aware datetime and drops the minutes of
  a non-whole-hour offset; `run.epoch` is UTC, so neither applies.
"""
from dirfm.platform_motion import PlatformPosition
from dirfm.tasks import TASKS


def generate_motion(run, motion_dir, name="motion.ppd"):
    """Write a single-entry static `.ppd` at relative time 0 from `run`'s position and Euler
    orientation. Returns its path."""
    motion_dir.mkdir(parents=True, exist_ok=True)
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
