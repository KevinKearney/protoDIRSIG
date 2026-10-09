# Stage 05: generate motion and tasks from the run spec; demote AUROR_ref to a test fixture

## CONTEXT

Stage 04 (`e8bdec9`) made `config_repo/` the resolution root for every engine *asset*: scene,
platform, atmosphere database, weather. `AUROR_ref/` remained the resolution root for exactly two
things `resolve_auror_run` still treats as "received" rather than generated: the platform motion
file (`motion/*.ppd`) and the tasks file (`tasks/*.tasks`). `check_received_files` then compares
those two files' content back against `engine.motion`/`engine.tasks` in the run spec, on the
premise (`run_spec.py`'s module docstring, `FINDINGS.md` "2026-10-07 — Stage 01") that a received
tree's motion/tasks describe a pose MANIFOLD already committed to, so the run spec is checked
against them rather than used to build them.

That premise doesn't survive contact with MANIFOLD's real model. `AV_MANIFOLD_Configuration_v02.md`
line 309: "the executor calls `materialize` into `<work>/<run_id>/inputs` and runs the engine with a
separate writable output directory." There is no persistent received-tree folder in MANIFOLD's
architecture at all — a run tree is generated fresh into an ephemeral work directory per run, from
the run spec, every time. `AUROR_ref` was never a template for that; it was a fixture left over
from before `protodirsig.run_spec` existed, kept because nothing yet generated what it holds.

Something does now, for the static case. `dirfm.platform_motion.PlatformPosition` writes exactly
`AUROR_ref/motion/AurorMotion.ppd`'s schema (`<platformmotion type="generic">`, hardcoded
`rotationframe="sceneenu"`, one `<entry>` per pose), and `dirfm.tasks.TASKS` writes exactly
`AUROR_ref/tasks/AurorTask.tasks`'s schema (`<tasklist><reference>` + one `<task>` per window) --
confirmed by direct comparison, not assumption. Both are already dirfm primitives; `FlexMotion`
(the `waypoints`/`orbit` mechanism, a different XML schema entirely, `<motion type="flexible">`)
is already used elsewhere in this codebase (`src/protodirsig/orbit.py`, backing
`tutorial_orbit_to_ground.ipynb`'s still-unfinished scenario) to prove the pattern of
run-spec-drives-dirfm-writes is not speculative here.

This stage makes `engine.motion`/`engine.tasks` generate the platform's motion and tasks files for
`kind: static` only, the same way Stage 03/04 already made other `engine.*` blocks generate
(`platform_ref.py`, `atmosphere_patches.py`, `sensors.py` are all "spec block in, dirfm object or
file out"). `waypoints`/`orbit` stay unbuilt until `tutorial_orbit_to_ground.ipynb`'s Phase 2 work
is further along -- they need `FlexMotion`, a materially different generator, not an extension of
this one.

Once motion/tasks are generated instead of resolved, `AUROR_ref` stops being a runtime dependency
of anything. Running the stage notebooks end to end needs nothing from it. Per Kevin's standing
principle for this project -- the folder structure should incrementally mirror MANIFOLD's real
one, stage by stage, and `AUROR_ref` is the one top-level folder with no MANIFOLD analog (no
`config_repo`-equivalent "received tree" concept exists there at all) -- `AUROR_ref` is relocated
out of the project root into a test fixture and trimmed to only the two subdirectories still read
by anything: `motion/` and `tasks/`. Everything else under it (`tahoe.scene`, `geometry/`,
`materials/`, `platforms/`, `weather/`, `jsims/`, `_to_delete/`) is redundant with `config_repo/`
-- Stage 04's `diff -r`/`cmp` already proved byte-identical copies of all of it live there -- and
is deleted, not archived.

Read before starting: `run_spec.py` in full (module docstring, `AurorRun`, `resolve_auror_run`,
`check_received_files`, `_single`), `simulation.py`'s `ENGINE_ENUMS`, `Simulation.__init__`,
`Simulation._assemble`, `Simulation.validate`; `platform_ref.py`'s `PlatformFilesPlugin` (confirm
it only asserts the three file paths it's given are files -- it has no opinion on where they came
from, which is why nothing about the plugin changes here); `scene_ref.py`'s `copy_input`; both
stage notebooks' setup cells; `tests/test_run_spec.py` and `tests/test_simulation.py` in full.

## CAPABILITY CHECK

- Confirm `dirfm.platform_motion.PlatformPosition` and `dirfm.tasks.TASKS`'s constructors,
  `add_entry`/`add_start_stop`, and `write(dirs, key="root", name=...)` signatures by reading
  `dirsig-file-maker/dirfm/platform_motion.py` and `dirfm/tasks.py` directly -- don't take this
  prompt's description of them as gospel. Note `write()` requires `dirs[key]` to already exist as
  a directory; the generator must create it first.
- Grep `src/protodirsig/*.py` and `tests/*.py` for every use of `_single`, `.motion`, `.tasks`,
  `run.motion`, `run.tasks`, `tree_root`, `tree=`, `AUROR` to get a complete call-site inventory
  before changing `resolve_auror_run`'s signature. Don't assume this prompt's inventory below is
  exhaustive.
- Confirm nothing else in the codebase treats `AUROR_ref/tahoe.scene`, `AUROR_ref/geometry`,
  `AUROR_ref/materials`, `AUROR_ref/platforms`, `AUROR_ref/weather`, or `AUROR_ref/jsims` as a
  live input before deleting them -- Stage 04's commit message and `FINDINGS.md` entry are the
  record of that already being proven redundant; re-verify with a `diff -r`/`cmp` pass of your own
  against `config_repo/` rather than trusting the record blindly.

## STEP 1 -- generate motion and tasks instead of resolving them

Add a new module, `src/protodirsig/motion_tasks.py`, following the one-concern-per-module
convention of `scene_ref.py`/`platform_ref.py`/`atmosphere_patches.py`. It wraps
`dirfm.platform_motion.PlatformPosition` and `dirfm.tasks.TASKS` and writes one `.ppd` and one
`.tasks` file from an `AurorRun`'s resolved values into a given directory. Something like:

```python
def generate_motion(run, motion_dir):
    """Write a single-entry, static .ppd file from run's resolved position/orientation."""
    motion_dir.mkdir(parents=True, exist_ok=True)
    o = run.motion_orientation
    pos = PlatformPosition(rotationorder=o["order"], angularunits=o["units"])
    pos.add_entry(0.0, run.motion_position, o["angles"])
    return pos.write({"root": motion_dir}, name="motion.ppd")

def generate_tasks(run, tasks_dir):
    """Write a .tasks file from run's resolved epoch and windows."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    t = TASKS(run.epoch)
    for w in run.tasks_windows:
        t.add_start_stop(w["start"], w["stop"])
    return t.write({"root": tasks_dir}, name="tasks.tasks")
```

Pick whatever names/signatures read best in context; the point is these two functions are the only
place `PlatformPosition`/`TASKS` get used, mirroring how `atmosphere_plugin()`/`ephemeris_plugin()`
on `AurorRun` are the only place their dirfm classes get used.

## STEP 2 -- change what `resolve_auror_run` resolves, not just where

In `run_spec.py`:

- Drop `resolve_auror_run`'s `tree` parameter entirely: `resolve_auror_run(spec, run_spec_path,
  config_repo)`. There are now two resolution roots, not three -- update the module docstring's
  "Three resolution roots" section accordingly (`config_repo` for engine assets, the run spec's
  own directory for the sensor ref; nothing resolves against a received tree anymore).
- Add explicit restrictions, each raising `RunSpecError` with a message that says what this loader
  generates and what it doesn't (matching the existing style of the `atmosphere.plugin`/
  `ephemeris.plugin` checks already in this function):
  - `engine.motion.kind` must be `"static"` -- `"waypoints"`/`"orbit"` need `dirfm.FlexMotion`, a
    different generator not built here (point at `orbit.py`/`tutorial_orbit_to_ground.ipynb` as
    where that work already lives, unfinished).
  - `engine.motion.position.frame` must be `"scene"` -- `dirfm.PlatformPosition` hardcodes
    `location type="scene"` per entry; it cannot emit anything else.
  - `engine.motion.orientation.kind` must be `"euler"` -- `"lookat"` also needs `FlexMotion`.
  - `engine.motion.orientation.euler.frame` must be `"sceneenu"` -- `PlatformPosition` hardcodes
    `rotationframe="sceneenu"` on the `<data>` element; it cannot be parameterized without
    modifying dirfm, which stays out of scope here as everywhere else in this project.
  These are schema-valid-but-unsupported values exactly like `four_curve`/`basic` atmosphere or a
  non-`spice` ephemeris already are -- same pattern, same place in the function.
- Replace `AurorRun`'s `motion: Path` and `tasks: Path` fields with the raw values the generator
  needs: something like `motion_position: list`, `motion_orientation: dict` (order/units/angles,
  already validated as euler/sceneenu by the checks above), `tasks_windows: list`, and `epoch:
  datetime` (parsed once here from `descriptor.collection.epoch`, replacing the ad hoc
  `datetime.fromisoformat(...replace("Z","+00:00"))` that used to live only in
  `check_received_files`). Update the `AurorRun` docstring: it no longer resolves "engine assets in
  config_repo, motion/tasks in the tree" -- motion/tasks are generated, not resolved.
- Remove `_single()` and its two call sites (`motion=_single(...)`, `tasks=_single(...)`) -- dead
  code once nothing globs a received tree for these files.
- Trim `check_received_files` to only the comparison that's still meaningful: `integration_samples`
  against the platform file (platform remains a resolved `config_repo` library file, independent
  of motion/tasks generation). The motion-position/orientation comparison, the tasks-windows
  comparison, and the epoch-vs-tasks-reference comparison all become tautological once the file
  being compared *is* the spec's own values rendered to XML -- remove them along with the function's
  now-dead branching, and rewrite its docstring to describe only what's left. Consider whether the
  function still deserves the name `check_received_files` once nothing is "received" except the
  platform file it's checking against -- your call, but leave a clear docstring either way.

## STEP 3 -- wire generation into `_assemble`, drop `tree_root` everywhere

In `simulation.py`:

- `Simulation.__init__`/`from_run_spec` and `LocalRegistry.submit` (`registry.py`) drop the
  `tree_root` parameter: `Simulation(run_spec_path, config_repo, work_dir=None)`. Update both
  classes' docstrings (`Simulation`'s currently says "`tree_root` is the received run tree...";
  that sentence goes away, `config_repo` is now the only resolution root described).
- `Simulation._assemble`: generate motion and tasks into `in_dir` the same way everything else
  lands there -- `motion_file = generate_motion(r, in_dir / "motion")`,
  `tasks_file = generate_tasks(r, in_dir / "tasks")` -- and pass those paths to
  `PlatformFilesPlugin` exactly where `inputs["motion"]`/`inputs["tasks"]` used to go. Drop
  `motion`/`tasks` from the `copy_input` comprehension (there's no received file left to copy);
  `platform` and `weather` keep copying from `config_repo` as Stage 04 left them.
- Update `simulation.py`'s module docstring (currently: "the motion/tasks files in the received
  tree" under the Resolution check, and "motion/tasks ... received tree" elsewhere) to describe
  generation instead of resolution.

## STEP 4 -- relocate AUROR_ref to a test fixture

- Create `tests/fixtures/auror_ref/` holding only `motion/AurorMotion.ppd` and
  `tasks/AurorTask.tasks`, moved (via `git mv`, preserving history) from `AUROR_ref/`.
- Delete everything else under `AUROR_ref/`: `tahoe.scene`, `geometry/`, `materials/`,
  `platforms/`, `weather/`, `jsims/`, `_to_delete/`. Report exactly what you deleted and the
  `diff -r`/`cmp` evidence that each piece is redundant with `config_repo/` before deleting it --
  don't silently remove anything you haven't individually confirmed.
- Remove the `AUROR_ref/`-specific lines from `.gitignore` (`tahoe.scene.hdf`, `asset_report.txt`,
  `material_report.json`, `jsims/*.img`, `jsims/*.img.hdr`, `jsims/material_report.json`,
  `_to_delete/`) -- all stale once those paths no longer exist.

## STEP 5 -- update tests

- `tests/test_run_spec.py`: `AUROR = PROJECT / "AUROR_ref"` becomes
  `AUROR = PROJECT / "tests" / "fixtures" / "auror_ref"` (used now only as a comparison fixture,
  never passed to `resolve_auror_run`). Every `resolve_auror_run(spec, AUROR, SPEC, CONFIG_REPO)`
  call site drops the `AUROR` argument. `test_resolves_against_tree`'s
  `assert run.motion == AUROR / "motion" / "AurorMotion.ppd"` and the `tasks` line next to it
  become assertions against the new fields instead (`run.motion_position`, `run.motion_orientation`,
  `run.tasks_windows`, `run.epoch` -- whatever values the spec actually has, which you can read
  straight out of `run_specs/auror_ref.yaml`). `test_mismatch_is_reported` and
  `check_received_files(spec, run) == []` in `test_resolves_against_tree` need rethinking now that
  the function only checks `integration_samples` -- keep the `integration_samples`-mismatch half of
  `test_mismatch_is_reported`, drop the motion-mismatch half (there's nothing left to compare it
  against). `test_no_flat_scene_fallback` passes `AUROR` as a stand-in bad `config_repo` to test
  the "received tree is not a library" rejection path -- re-examine that test now that `AUROR` is
  trimmed to just `motion/`+`tasks/`; it should still fail to resolve a scene ref against it (it
  has no `scenes/` at all now, which is a stronger failure, not a weaker one), but confirm the
  `match=` regex still fits and update the comment that currently calls it "the received tree" if
  that no longer reads correctly.
- `tests/test_simulation.py`: every `Simulation.from_run_spec(path_or_SPEC, AUROR, CONFIG_REPO,
  ...)` call drops the `AUROR` argument. The `needs_tree`/`needs` skip-guard at the top of the file
  (checking `(AUROR / "motion").is_dir()`) should check the new fixture path instead. Update the
  module docstring's "Reads ... AUROR_ref READ-ONLY" line.
- Add new test coverage: (a) a semantic (not byte-identical) comparison of a freshly generated
  motion/tasks pair against `tests/fixtures/auror_ref/`'s parsed values -- compare position,
  orientation angles, task windows, and epoch-as-a-UTC-instant, not raw XML text. The received
  tasks reference datetime is `...-08:00`; a UTC-parsed epoch generates `...+00:00` -- same instant,
  different printed offset, so compare parsed `datetime` objects, not strings. (b) a test that
  `motion.kind: waypoints` and `motion.orientation.kind: lookat` each raise `RunSpecError` at
  resolution (schema-valid per `ENGINE_ENUMS`, rejected here) -- parametrize similarly to the
  existing `test_rejects_other_atmosphere_plugins`.
- `tests/test_simulation.py`'s comment `# check_received_files: spec kind != the static .ppd` (near
  `test_bad_enum_fails_schema`) is stale once `check_received_files` no longer looks at motion --
  find and fix it.

## STEP 6 -- update the notebooks and docs

- `notebooks/stage_01_auror_from_runspec.ipynb` and `stage_02_conformance_template.ipynb`: remove
  the `AUROR = PROJECT / "AUROR_ref"` cell and the `AUROR` argument from every
  `resolve_auror_run(...)`/`LocalRegistry().submit(...)` call. Re-execute both end to end and
  confirm the render is still byte-identical to what Stage 01/02 produced -- this is the concrete
  proof that the YAML now generates the run tree rather than requiring one to already exist. Report
  the comparison you ran, not just that it looked fine.
- `FINDINGS.md`: append a Stage 05 entry in the existing journal style, covering the
  resolve-vs-generate distinction this stage draws, the restriction to `kind: static`, and the
  `AUROR_ref` relocation/trim.
- `notebooks/README.md`: the `stage_01`/`tutorial_auror_scene`/`auror_scene_buildup` entries
  mention "the AUROR_ref job" and "the AUROR_ref tree" descriptively -- reread them after this
  stage and adjust only if they now describe something inaccurate (e.g. `tutorial_auror_scene.ipynb`
  still drives dirfm directly against the old received files and is unaffected; say so if asked to
  touch it, but don't rewrite it needlessly).
- `README.md`: grep it for `AUROR_ref` and fix anything that describes it as a resolution root
  rather than a test fixture.

## CONSTRAINTS

- Do not implement `waypoints`/`orbit` motion generation. That is `FlexMotion`, a different code
  path, scoped to when `tutorial_orbit_to_ground.ipynb`'s own work is further along.
- Do not modify `dirsig-file-maker`/`dirfm` itself -- standing constraint, unchanged.
- Do not touch `config_repo/`'s contents -- Stage 04 is done; this stage only changes what resolves
  against it and what no longer needs to.
- Do not build Phase 6 / ChipMaker / any sweep mechanism -- out of scope, already logged as
  abandoned in `MANIFOLD_Architecture_Considerations_Log.md`.
- `tests/fixtures/auror_ref/` is a test-only comparison fixture from this point on. Nothing in
  `src/protodirsig/` should import or reference `tests/` -- the generator must stand on its own,
  verified only by the test suite reading the fixture, never the reverse.

Report git status and the actual `git mv`/`git add`/`git rm`/`git commit` commands.
