# Notebooks

Several kinds of notebook live here, and they're not interchangeable.

**Stage notebooks** (`stage_NN_<slug>.ipynb`, top level) are the active, accumulating work: each one builds toward a MANIFOLD-conformant template notebook, one stage at a time. A later stage extends what an earlier one does rather than rewriting it, so the stage notebooks are expected to keep changing as work continues — this file describes their current state, updated as they go, not a history of how they got there.

**`dirfm_tutorials/`** are standalone tutorials in `dirfm` usage: each is self-contained, driven directly through `dirfm` with no MANIFOLD run-spec or registry layer involved, and not part of the stage progression. They stay as worked examples.

**`dev/`** holds discovery-log notebooks — working notes from exploring a received tree or tool behavior before the pattern was understood well enough to write cleanly. Kept as executed, not maintained going forward.

**`sidebars/`** holds side investigations: exploratory like `dev/`, but tracked, because their results are cited in the CONOPS and Guide.

## Stage notebooks

- **`stage_01_auror_from_runspec.ipynb`** — Builds and renders the AUROR_ref DIRSIG job driven entirely from a MANIFOLD run-spec YAML (`manifold_run_specs/auror_ref.yaml`), via `src/protodirsig/run_spec.py`. Scene, platform, atmosphere, weather and seed all come from the run spec rather than being written into the notebook's cells; the assets resolve in `manifold_config_repo/`, and the motion and tasks files are generated from the spec.
- **`stage_02_conformance_template.ipynb`** — Submits the same job through `LocalRegistry` (schema, resolution and execution checks) and renders it with `Simulation.run()` only if accepted, capturing DIRSIG's JSON run/info logs alongside the render. This is the current conformance-template notebook. As received, the vehicle target never appears, so the notebook adds an oversized (8-pixel) Lambertian disk that flies with it. The disk goes into a mirror of `manifold_config_repo/` under `outputs/`; `manifold_config_repo/` itself is unchanged.
- **`stage_03_sensor_sweep.ipynb`** — The same scenario through different sensors. Shows the sensor library (`manifold_sensors/`), one entry's blocks, the three spectral curves, and the channel response the generator writes into each `.platform`. Then composes the sweep recipe `manifold_run_specs/recipes/sensor_sweep_tahoe.yaml` into one run per library sensor (`compose_sweep`), submits every run (`LocalRegistry.submit_sweep`) and renders all three in 32 × 32 windows (`run_sweep`, seconds each). Compares the ground sample distance measured from the geolocation truth with pitch ÷ focal length × range. Closes with what is synthetic and what is not. Finds DIRSIG and `dirfm` through `external/` (`scripts/bootstrap.py install`), with no home-directory paths.

## `dirfm_tutorials/`

- **`tutorial_dirfm_basics.ipynb`** — `dirfm`'s own building blocks: materials, primitives, sensor trees, motion, atmosphere, GLIST mesh geometry, multi-scene composition, and determinism/render-quality knobs.
- **`tutorial_orbit_to_ground.ipynb`** — An orbit-to-ground SDA/orbital scenario, reconstructed directly with `dirfm`.
- **`tutorial_tacoma_scene.ipynb`** — A WorldView-2 pass over DIRSIG's Tacoma scene, driven directly through `dirfm`.
- **`tutorial_auror_scene.ipynb`** — The AUROR_ref job (same scene and platform the stage notebooks use), driven directly through `dirfm` with no run-spec or registry layer. A plain usage example, not part of the staged work. Reads AUROR_ref's files from their copies in `manifold_config_repo/` and `tests/fixtures/auror_ref/`, since `AUROR_ref/` itself was retired.

## `sidebars/`

Side investigations that a stage or tutorial raised but that don't belong in one: exploratory, kept as executed, and tracked (unlike `dev/`, which `.gitignore` keeps local). Each notebook keeps any assets it adds in a folder of the same name beside it.

- **`vehicle_point_source.ipynb`** — Distils the real AUROR vehicle mesh, given a reflective material, into a radiant intensity from a close-range DIRSIG render at the task's exact sun and view angles. Writes it as a `.int` point source, and renders the 500 km scene with it. Also renders the received 1500 K emitter with thermal prediction forced. Results are summarised in the CONOPS and Guide, section 9.

## `dev/`

- **`auror_scene_buildup.ipynb`** — Discovery-log notebook for the AUROR_ref tree. Not a tutorial, not maintained going forward.
