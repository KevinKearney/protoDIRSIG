# Stage 1: drive the Auror job from a MANIFOLD run-spec YAML

A MANIFOLD run-spec YAML for this tree now exists: `eopticDocs/projects/MANIFOLD/04-guides/
auror_ref_run_spec.yaml`, documented by the guide at `04-guides/GD_DIRSIG_RunSpec_YAML_v01.md`
in the same repo. It centralizes, in one versioned file, exactly the values
`notebooks/tutorial_auror_scene.ipynb` currently hardcodes across several cells: the scene,
platform, atmosphere, weather and ephemeris references, and the run seed. This stage makes the
notebook read those values from the YAML instead of from literals written into it.

**New naming convention.** `tutorial_*.ipynb` stays reserved for the three existing
notebooks that teach dirfm usage itself (`tutorial_dirfm_basics`, `tutorial_orbit_to_ground`,
`tutorial_tacoma_scene`) — don't touch them. This work, and whatever follows it toward a
MANIFOLD-aligned generator, is staged implementation, not a tutorial someone reads to learn
dirfm. It gets its own sequence: `notebooks/stage_NN_<slug>.ipynb`, numbered independently of
the tutorial track, starting at `stage_01_auror_from_runspec.ipynb` for this step.

## What the YAML does and does not describe for this tree

`AUROR_ref` is a **received** run tree: `motion/AurorMotion.ppd` and `tasks/AurorTask.tasks`
already exist as files and are referenced, not generated. The run spec's `engine.motion` and
`engine.tasks` blocks describe what those files already encode (position, orientation, task
window) — they are not an instruction to regenerate the files from those parameters. Building
dirfm-native motion/tasks generation from a run spec is a later stage; this one does not attempt
it. Everything else in `engine` — `scenes`, `platform`, `atmosphere`, `weather`, `ephemeris`,
`run.seed` — does drive this stage, because the existing `src/protodirsig/` modules already
reference those as existing files or library entries rather than generating them, which is
exactly what the run spec's values are for here.

`engine.atmosphere.plugin: new_atmosphere` is a documented non-adopted schema extension (see the
guide, §6) — `dirsig-engine/1` currently defines only `four_curve` and `basic`. Treat it as a
fixed special case for this one tree's loader, not something to generalize.

## CAPABILITY CHECK

Before writing code:
- Confirm PyYAML is importable in the protodirsig environment; add it to the project's
  dependency file if it is not already declared.
- Re-read `src/protodirsig/atmosphere_patches.py`, `platform_ref.py` and `scene_ref.py` to
  confirm their current signatures — this stage wires existing functions together, it does not
  change them.
- `grep -rn "yaml" src/ notebooks/` to confirm there is no existing YAML-loading code this would
  duplicate.

## STEP 1 — Vendor the run spec

`eopticDocs` and `protoDIRSIG` are separate checkouts; don't have notebooks reach across
repositories. Create `run_specs/` at the protoDIRSIG root and copy the YAML in as
`run_specs/auror_ref.yaml`, with a one-line header comment recording that it is authored at
`eopticDocs/projects/MANIFOLD/04-guides/auror_ref_run_spec.yaml` and should be edited there, not
here, if its content needs to change. This is a small text file and is tracked normally — it is
not covered by the `AUROR_ref/` `.gitignore` entry and should not be added to it.

## STEP 2 — The run-spec loader: `src/protodirsig/run_spec.py`

- `load_run_spec(path)` — loads the YAML (a plain `yaml.safe_load` is adequate for this
  prototype; the strict loader, canonical-JSON hashing and duplicate-key rejection
  `AV_MANIFOLD_Metadata_v02.md` §6.15 specifies belong to the registry side MANIFOLD hasn't
  built, not to protoDIRSIG — note this gap in a comment rather than building it here).
- A function that takes the parsed run spec and the tree root (`AUROR_ref`'s path) and returns
  what Step 3 needs to assemble the job: the scene file path, the platform/motion/tasks file
  paths plus `output_prefix`, `split_channels` and `integration_samples` for
  `PlatformFilesPlugin`, a `PatchedNewAtmospherePlugin` built from
  `engine.atmosphere.database.ref.name`, the weather file path, the ephemeris plugin choice, and
  `engine.run.seed`. Use your judgment on the exact shape (a dataclass, a dict, several small
  functions) — the requirement is that the notebook stops hardcoding these values, not a
  particular interface.
- Raise a clear, specific error if `engine.atmosphere.plugin` is anything other than
  `new_atmosphere` — this loader is built for this one tree's schema extension, not as a general
  `dirsig-engine/1` interpreter. Resolve `engine.scenes[0].ref.name` and
  `engine.platform.ref.name` against the tree root; `scenes/tahoe` in the YAML names the
  config-repo's intended nested layout, which the received tree does not have (`tahoe.scene` is
  at tree root) — resolve this by tree-root-relative lookup of the actual file, not by taking the
  YAML path literally. Say in a comment that this is the same open config-repo-layout question
  the guide flags, worked around locally rather than resolved.
- Write `tests/test_run_spec.py`: load `run_specs/auror_ref.yaml` and assert the returned values
  are correct — scene path resolves under the tree root, platform ref name, `seed == 42`,
  atmosphere database ref name — following the existing test conventions.

## STEP 3 — `notebooks/stage_01_auror_from_runspec.ipynb`

`git mv notebooks/tutorial_auror_scene.ipynb notebooks/stage_01_auror_from_runspec.ipynb` as the
starting point. Replace the cells that currently hardcode the scene/platform/atmosphere/weather/
ephemeris/seed parameters with: load the run spec via `run_spec.py`, print a short summary of
what was loaded (`meta.name`, `origin`, one line noting the atmosphere plugin is the
`new_atmosphere` extension), then assemble and run the job exactly as before, driven by the
loaded values rather than literals. Leave the display cells (rendered image, truth/geolocation
output, the vehicle-not-appearing note) unchanged — this stage is about the input side, not the
output side.

Rewrite the top markdown cell: state that this notebook drives its run from a versioned run-spec
YAML (`run_specs/auror_ref.yaml`, authored in `eopticDocs/04-guides/`) rather than from values
written into the notebook, and that it is staged implementation toward a MANIFOLD-aligned
generator, not a tutorial — point to the three `tutorial_*.ipynb` notebooks for dirfm usage
itself.

## CONSTRAINTS

- Never write into the DIRSIG install directory, the dirfm checkout, or `AUROR_ref/`.
- Do not touch `tutorial_dirfm_basics.ipynb`, `tutorial_orbit_to_ground.ipynb`,
  `tutorial_tacoma_scene.ipynb`, or `notebooks/dev/auror_scene_buildup.ipynb`.
- Do not attempt to regenerate `motion`/`tasks` files from `engine.motion`/`engine.tasks` — see
  above. Record this as a stated scope boundary in `FINDINGS.md`, not as a silent omission.
- `run_spec.py` is narrow and tree-specific by design (including its `new_atmosphere` special
  case) — do not generalize it into a `dirsig-engine/1` interpreter in this stage.
- Reuse `scene_ref.py`, `platform_ref.py` and `atmosphere_patches.py` exactly as they stand.

Report git status and the actual `git add`/`git mv`/`git commit` commands when done. The rename
needs `git add` on both the old and new notebook paths (or `git add -A`) to record as a rename;
`run_specs/auror_ref.yaml` and `src/protodirsig/run_spec.py` are new tracked files.
