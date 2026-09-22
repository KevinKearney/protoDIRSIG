# protoDIRSIG

Batch-driver prototype for generating synthetic EO imagery of Resident Space
Objects (RSOs) with DIRSIG5, orchestrated programmatically via `dirfm`. See
`docs/dirsig_batch_driver_plan.md` for the phased development plan and
`docs/dirsig_motion_temporal.md` for DIRSIG5's motion/temporal model.

## Layout

- `docs/` — planning and reference documents.
- `notebooks/` — Jupyter notebooks; primary development and hand-off artifact.
- `src/protodirsig/` — supplementary Python modules filling gaps `dirfm` does
  not cover (e.g. SSA-specific motion writers), installed editable via
  `pip install -e .`.
- `scripts/` — standalone CLI entry points, if/when notebook logic graduates
  out of prototyping.
- `outputs/` — DIRSIG input/output roots written by notebooks and scripts.
  Gitignored except for a placeholder; nothing here is source.
- `tests/` — pytest suite for `src/protodirsig`.
- `prompt.md` — standing Claude Code prompt for the tutorial notebook task.

## Environment

`dirfm` (https://github.com/KevinKearney/dirsig-file-maker, local checkout at
`~/dev/dirsig-file-maker`) and a working DIRSIG5 install
(`~/DIRSIG/dirsig-2026.38.0.a020954-Linux-x86_64`, with `bin/` on `PATH`) are
prerequisites. See `environment.yml` for the conda environment and the
install steps for `dirfm` as an editable dependency.
