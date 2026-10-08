# Notebooks

Two kinds of notebook live here, and they're not interchangeable.

**Stage notebooks** (`stage_NN_<slug>.ipynb`, top level) are the active, accumulating work: each
one builds toward a MANIFOLD-conformant template notebook, one stage at a time. A later stage
extends what an earlier one does rather than rewriting it, so the stage notebooks are expected to
keep changing as work continues — this file describes their current state, updated as they go, not
a history of how they got there.

**`dirfm_tutorials/`** are standalone tutorials in `dirfm` usage: each is self-contained, driven
directly through `dirfm` with no MANIFOLD run-spec or registry layer involved, and not part of the
stage progression. They stay as worked examples.

**`dev/`** holds discovery-log notebooks — working notes from exploring a received tree or tool
behavior before the pattern was understood well enough to write cleanly. Kept as executed, not
maintained going forward.

## Stage notebooks

- **`stage_01_auror_from_runspec.ipynb`** — Builds and renders the AUROR_ref DIRSIG job driven
  entirely from a MANIFOLD run-spec YAML (`run_specs/auror_ref.yaml`), via
  `src/protodirsig/run_spec.py`. Scene, platform, atmosphere, weather and seed all come from the
  run spec rather than being written into the notebook's cells.
- **`stage_02_conformance_template.ipynb`** — Submits the same job through `LocalRegistry`
  (schema, resolution and execution checks) and renders it with `Simulation.run()` only if
  accepted, capturing DIRSIG's JSON run/info logs alongside the render. This is the current
  conformance-template notebook.

## `dirfm_tutorials/`

- **`tutorial_dirfm_basics.ipynb`** — `dirfm`'s own building blocks: materials, primitives,
  sensor trees, motion, atmosphere, GLIST mesh geometry, multi-scene composition, and
  determinism/render-quality knobs.
- **`tutorial_orbit_to_ground.ipynb`** — An orbit-to-ground SDA/orbital scenario, reconstructed
  directly with `dirfm`.
- **`tutorial_tacoma_scene.ipynb`** — A WorldView-2 pass over DIRSIG's Tacoma scene, driven
  directly through `dirfm`.
- **`tutorial_auror_scene.ipynb`** — The AUROR_ref job (same scene and platform the stage
  notebooks use), driven directly through `dirfm` with no run-spec or registry layer. A plain
  usage example, not part of the staged work.

## `dev/`

- **`auror_scene_buildup.ipynb`** — Discovery-log notebook for the AUROR_ref tree. Not a
  tutorial, not maintained going forward.
