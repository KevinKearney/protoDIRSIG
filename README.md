# protoDIRSIG

Prototype batch driver for generating synthetic EO/IR imagery with DIRSIG5,
built on `dirfm` and developed notebook-first. Scope: MANIFOLD's DIRSIG
automation workstream (see the MANIFOLD Drive project for the governing
charter and requirements docs — not duplicated here).

`docs/dirsig_batch_driver_plan.md` and `docs/dirsig_motion_temporal.md`
are retained for history but are **not** the current plan — superseded by
`prompt.md` (the standing spec driving notebook development) and the
architecture below. Don't scope new work against them.

## Environment setup

Prerequisites: a working DIRSIG5 install with `bin/` locatable (this
project assumes `~/DIRSIG/dirsig-2026.38.0.a020954-Linux-x86_64`, overridable
via `DIRSIG_HOME`), and a `dirfm` checkout as a sibling directory
(`~/dev/dirsig-file-maker`) — `dirfm` is not on PyPI or conda-forge.

```bash
cd ~/dev/protoDIRSIG
conda env create -f environment.yml
conda activate protodirsig
pip install -e ~/dev/dirsig-file-maker
pip install -e .
python -m ipykernel install --user --name protodirsig --display-name "Python (protodirsig)"
```

The last step registers a Jupyter kernel named `protodirsig` — select it when
opening any notebook under `notebooks/`. DIRSIG's own `PATH`/`DIRSIG_HOME`
setup is done **inside each notebook's first cell**, not at the shell level:
a Jupyter kernel does not inherit an interactive shell's `PATH`, so every
tutorial notebook sets `os.environ["DIRSIG_HOME"]` and prepends its `bin/` to
`os.environ["PATH"]` explicitly and asserts `scene2hdf`/`dirsig5` resolve
before doing anything else.

To update the environment after `environment.yml` changes:

```bash
conda env update -f environment.yml --prune
```

## Layout

- `prompt.md` — the standing, versioned prompt handed to Claude Code for
  notebook development. This is the actual spec; update it in place as the
  approach evolves rather than treating it as a one-shot instruction.
- `notebooks/` — Jupyter notebooks; the primary development and hand-off
  artifact for this project (see Architecture below — notebook-first is a
  deliberate convention, not a placeholder for "real" code).
- `src/protodirsig/` — supplementary Python modules for gaps `dirfm` does
  not cover, installed editable via `pip install -e .`. Empty scaffold for
  now; populated as Phase 2+ work identifies concrete gaps (see below).
- `scripts/` — standalone CLI entry points, if/when notebook logic
  graduates out of prototyping.
- `outputs/` — DIRSIG input/output roots written by notebooks and scripts.
  Gitignored except for a placeholder; nothing here is source, and nothing
  here is ever written into `dirfm`'s own checkout.
- `tests/` — pytest suite for `src/protodirsig`.
- `docs/` — historical planning documents; not current (see above).

## Architecture

**`dirfm` is the only runtime dependency, used directly.** `dirfm` (RIT
GitLab, developed in collaboration with Rendered.ai) is a plain, freely
installable Python library that programmatically builds DIRSIG5 input files
(materials, geometry, platform/sensor, motion, atmosphere, tasks) and
invokes `scene2hdf`/`dirsig5`. It is checked out as an editable sibling
dependency and never modified — this project reads its source as the
API/behavior reference and treats its `demos/test_*.py` pytest suite as the
canonical usage pattern to copy when adding anything new (per Rendered.ai's
own internal convention for `dirfm`, confirmed via their `agent-docs`
reference — see `~/dev/agent-docs` for the full documentation set).

**Rendered.ai's channel/node layer (`dirsig_pkg`, `anatools`) is explicitly
not a dependency.** That layer is Rendered.ai's commercial Agent Studio
platform surface — gated behind an API key, a hosted workspace, and their
own `ana`/`anadeploy`/`anamount` tooling — not open source code that can be
vendored into this project. `~/dev/agent-docs` is read as a *design-pattern*
reference only (node `exec()` conventions, `ctx.seed`/`ctx.random`
determinism discipline, truth-band-to-annotation conversion) to inform how
`src/protodirsig` gets built, not as a library this project imports from or
depends on. If actually adopting Rendered.ai's hosted platform becomes a
live option, that's an organizational/contractual decision (the RIT CRADA
relationship), not something this repo can architect around speculatively.

**Development is notebook-first by convention, not by default.** Each
notebook is built from a versioned prompt in `prompt.md`, executed end to
end (not just inspected) before being considered done, and kept additive —
later stages extend earlier objects rather than rewriting them, so the
notebook itself is a readable diff of the API surface as it's learned.
`src/protodirsig` only gains code once a notebook has concretely
demonstrated a gap `dirfm` doesn't cover; the notebook is the specification,
the module is the extraction.

**Phased scope, in order:**

*Phase 1 — `dirfm` fundamentals (done).* `notebooks/tutorial_dirfm_basics.ipynb`,
Stages 0–8: materials, primitives, sensor tree, motion, atmosphere, GLIST
mesh geometry, multi-scene composition, and — closing the phase — empirical
determinism verification (`set_seed()`, bitwise vs. statistical
reproducibility) and the `convergence`/`max_nodes` render-quality knobs
`DIRSIG.run()` forwards to `dirsig5`.

*Phase 2 — SDA/orbital reference demos (in progress).* Reconstructing
DIRSIG's own bundled orbit-relevant demos with `dirfm` directly, starting
with `StkImport1` (a real WorldView-2 LEO trajectory, STK-ephemeris-driven,
imaging toward Earth — the only orbit-to-ground demo in DIRSIG's catalog;
`Ssa1`–`Ssa3` are satellite-to-satellite). This phase is also where `dirfm`'s
actual orbital-motion coverage gets tested empirically (STK ephemeris
ingestion, ECI/ECEF handling) rather than assumed, surfacing concrete
candidates for `src/protodirsig` if `dirfm` falls short.

*Phase 3 — Provenance/lineage instrumentation (forward-looking).* A notebook
demonstrating minimal MLflow/OpenLineage emission around a `dirfm`-driven
run — resolving, in the process, the asset-versioning question for large
binary DIRSIG scene assets (git-LFS vs. content-addressed store vs. hybrid)
that the run's provenance record has to point at.

*Phase 4 — First Dagster asset (forward-looking).* Wrapping a Phase-2
scenario as a Dagster software-defined asset, then as a partitioned asset
over a small parameter sweep. Dagster, not Prefect, per MANIFOLD's own
orchestrator trade study: its partitioned-asset model is the direct
structural match for DIRSIG's sweep/batch execution shape, and its
first-party OpenLineage integration aligns with Phase 3 rather than
requiring a bolted-on adapter.

*Phase 5 — Catalog/compute integration (out of notebook scope).* Requirements
baselining, containerized production execution, and compute placement —
sequenced per MANIFOLD's charter gates, not notebook-first work, and not
started ahead of that baseline.
