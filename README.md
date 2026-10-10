# protoDIRSIG

Prototype batch driver for generating synthetic EO/IR imagery with DIRSIG5, built on `dirfm` and developed notebook-first. Scope: MANIFOLD's DIRSIG automation workstream (see the MANIFOLD Drive project for the governing charter and requirements docs — not duplicated here).

`docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md` is the as-built description of the driver, the run-spec contract, and the interface to MANIFOLD; its Overview gives the workflow at block-diagram level. `BACKLOG.md` is the to-do list.

## What it does

A `run-spec/1` YAML names a collection, a sensor (a reference into `manifold_sensors/`) and engine assets (references into `manifold_config_repo/`). It is composed from layer files: a recipe naming a scenario, an engine profile and a library sensor, or several sensors for a sweep (one run per sensor; `scripts/compose.py`). The driver validates the spec, verifies content hashes, renders the `.platform` from the sensor description, generates motion and tasks files, runs a DIRSIG dry-run, and renders through `dirfm`. Output is imagery in electrons per m² of focal plane plus truth. Three sensors are in the library (AUROR NIR, a 1280-pixel NIR, a 1920-pixel VIS); the AUROR job reproduces the received platform file.

```python
from protodirsig.registry import LocalRegistry   # submit_recipe / submit_sweep, then Simulation.run / run_sweep
```

`notebooks/stage_01`–`stage_03` run the reference job, the conformance path and a three-sensor sweep.

## Environment setup

Prerequisites: a DIRSIG5 install (`~/DIRSIG/dirsig-2026.38.0.a020954-Linux-x86_64`, or anywhere via `DIRSIG_HOME`), git access to RIT's GitLab for `dirfm` (not on PyPI or conda-forge), and conda. `external/pins.json` fixes the exact `dirfm` and `agent-docs` commits and the DIRSIG version.

```bash
cd ~/dev/protoDIRSIG
python scripts/bootstrap.py install        # clone dirfm and agent-docs at the pins; link DIRSIG
python scripts/bootstrap.py status         # check each against its pin
conda env create -f environment.yml
conda activate protodirsig
pip install -e external/dirsig-file-maker
pip install -e ".[dev]"                 # adds pytest, jsonschema
python -m ipykernel install --user --name protodirsig --display-name "Python (protodirsig)"
```

To reuse existing checkouts instead of cloning, add `--link dirfm=~/dev/dirsig-file-maker --link agent-docs=~/dev/agent-docs` to the `install` command.

The last step registers a Jupyter kernel named `protodirsig` — select it when opening any notebook under `notebooks/`. DIRSIG's own `PATH`/`DIRSIG_HOME` setup is done **inside each notebook's first cell**, not at the shell level: a Jupyter kernel does not inherit an interactive shell's `PATH`, so every tutorial notebook sets `os.environ["DIRSIG_HOME"]` and prepends its `bin/` to `os.environ["PATH"]` explicitly and asserts `scene2hdf`/`dirsig5` resolve before doing anything else.

To update the environment after `environment.yml` changes:

```bash
conda env update -f environment.yml --prune
```

## Layout

- `prompt.md` — the current prompt handed to Claude Code. Overwritten per work package; gitignored, not versioned.
- `notebooks/` — Jupyter notebooks; the primary development and hand-off artifact for this project (see Architecture below — notebook-first is a deliberate convention, not a placeholder for "real" code). See `notebooks/README.md` for what each notebook does. `dirfm_tutorials/` holds the standalone `dirfm`-fundamentals tutorials; `dev/` holds discovery-log notebooks kept for their own sake, not maintained going forward; the stage notebooks live at the top level of `notebooks/` and are the active, accumulating work.
- `src/protodirsig/` — supplementary Python modules for gaps `dirfm` does not cover, installed editable via `pip install -e .`: the run-spec composer (`compose`) and loader (`run_spec`), `.platform` generation from the sensor description (`platform_gen`, `spectral`), motion/tasks generation (`motion_tasks`), the conformance checks and render (`simulation`), the local submission stand-in (`registry`), and the dirfm workarounds and helpers the notebooks use.
- `manifold_run_specs/` — MANIFOLD run specs: the layer files (`recipes/`, `scenarios/`, `engine_profiles/`) and the run specs composed from them (see its README). The only copy; protoDIRSIG is the source of truth.
- `manifold_sensors/` — the sensor library: `sensor-spec/1` files that run specs reference, and `spectral/` (QE, optics and filter curves, `spectral-curve/1` CSV).
- `manifold_contracts/` — schemas, vocabulary and validators (`sensor-spec-1.schema.json` and the composition vectors today; future `manifold-contracts`).
- `external/` — pinned dirfm and agent-docs checkouts and a link to the DIRSIG install, populated by `python scripts/bootstrap.py install`; gitignored except `pins.json`.
- `manifold_config_repo/` — the engine-asset library the run specs' `engine` refs resolve against (scenes, platforms, weather, atmosphere databases), in the layout of the CONOPS and Guide §5. Read-only at run time.
- `scripts/` — CLI entry points: `bootstrap.py` (pinned dependencies), `compose.py` (run specs from layers), `stamp_hashes.py` (content hashes), `import_curve.py` (measured curve intake), `crosscheck_sgp4.py`.
- `outputs/` — DIRSIG input/output roots written by notebooks and scripts. Gitignored except for a placeholder; nothing here is source, and nothing here is ever written into `dirfm`'s own checkout.
- `tests/` — pytest suite for `src/protodirsig`. `tests/fixtures/auror_ref/` holds the received AUROR_ref motion and tasks files, kept only to compare generated files against.
- `docs/` — the CONOPS and Guide, the DIRSIG platform decomposition notes, and `diagrams/`: the controlled drawings (Mermaid source, rendered SVG and PNG; `python scripts/render_diagrams.py`).

## Architecture

**`dirfm` is the only runtime dependency, used directly.** `dirfm` (RIT GitLab, developed in collaboration with Rendered.ai) is a plain, freely installable Python library that programmatically builds DIRSIG5 input files (materials, geometry, platform/sensor, motion, atmosphere, tasks) and invokes `scene2hdf`/`dirsig5`. It is checked out as an editable sibling dependency and never modified — this project reads its source as the API/behavior reference and treats its `demos/test_*.py` pytest suite as the canonical usage pattern to copy when adding anything new (per Rendered.ai's own internal convention for `dirfm`, confirmed via their `agent-docs` reference — see `external/agent-docs` for the full documentation set).

**Rendered.ai's channel/node layer (`dirsig_pkg`, `anatools`) is explicitly not a dependency.** That layer is Rendered.ai's commercial Agent Studio platform surface — gated behind an API key, a hosted workspace, and their own `ana`/`anadeploy`/`anamount` tooling — not open source code that can be vendored into this project. `external/agent-docs` is read as a *design-pattern* reference only (node `exec()` conventions, `ctx.seed`/`ctx.random` determinism discipline, truth-band-to-annotation conversion) to inform how `src/protodirsig` gets built, not as a library this project imports from or depends on. If actually adopting Rendered.ai's hosted platform becomes a live option, that's an organizational/contractual decision (the RIT CRADA relationship), not something this repo can architect around speculatively.

**Development is notebook-first by convention, not by default.** Each notebook is built from a versioned prompt in `prompt.md`, executed end to end (not just inspected) before being considered done, and kept additive — later stages extend earlier objects rather than rewriting them, so the notebook itself is a readable diff of the API surface as it's learned. `src/protodirsig` only gains code once a notebook has concretely demonstrated a gap `dirfm` doesn't cover; the notebook is the specification, the module is the extraction.

**Phased scope, in order:**

*Phase 1 — `dirfm` fundamentals (done).* `notebooks/dirfm_tutorials/tutorial_dirfm_basics.ipynb`, Stages 0–8: materials, primitives, sensor tree, motion, atmosphere, GLIST mesh geometry, multi-scene composition, and — closing the phase — empirical determinism verification (`set_seed()`, bitwise vs. statistical reproducibility) and the `convergence`/`max_nodes` render-quality knobs `DIRSIG.run()` forwards to `dirsig5`.

*Phase 2 — SDA/orbital reference demos (in progress).* Reconstructing DIRSIG's own bundled orbit-relevant demos with `dirfm` directly, starting with `StkImport1` (a real WorldView-2 LEO trajectory, imaging toward Earth — the only orbit-to-ground demo in DIRSIG's catalog; reconstructed from a TLE with skyfield/SGP4 rather than by STK-ephemeris import; `Ssa1`–`Ssa3` are satellite-to-satellite). This phase is also where `dirfm`'s actual orbital-motion coverage gets tested empirically (STK ephemeris ingestion, ECI/ECEF handling) rather than assumed, surfacing concrete candidates for `src/protodirsig` if `dirfm` falls short.

*Phase 3 — Provenance/lineage instrumentation (forward-looking).* A notebook demonstrating minimal MLflow/OpenLineage emission around a `dirfm`-driven run — resolving, in the process, the asset-versioning question for large binary DIRSIG scene assets (git-LFS vs. content-addressed store vs. hybrid) that the run's provenance record has to point at.

*Phase 4 — First Dagster asset (forward-looking).* Wrapping a Phase-2 scenario as a Dagster software-defined asset, then as a partitioned asset over a small parameter sweep. Dagster, not Prefect, per MANIFOLD's own orchestrator trade study: its partitioned-asset model is the direct structural match for DIRSIG's sweep/batch execution shape, and its first-party OpenLineage integration aligns with Phase 3 rather than requiring a bolted-on adapter.

*Phase 5 — Catalog/compute integration (out of notebook scope).* Requirements baselining, containerized production execution, and compute placement — sequenced per MANIFOLD's charter gates, not notebook-first work, and not started ahead of that baseline.
