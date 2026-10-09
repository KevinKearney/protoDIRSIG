# Fix PROJECT root detection in the three remaining dirfm tutorials

## CONTEXT

`notebooks/README.md`'s doc-update commit (`7219275`) moved the four dirfm tutorials from
`notebooks/` into `notebooks/dirfm_tutorials/`, one level deeper. Each tutorial's setup cell
derives its project root as:

```python
PROJECT = Path.cwd()
if PROJECT.name == "notebooks":       # notebook lives in protoDIRSIG/notebooks/
    PROJECT = PROJECT.parent
```

or, in `tutorial_tacoma_scene.ipynb`'s case, the equivalent one-liner
`Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()`. Run from
`notebooks/dirfm_tutorials/`, `Path.cwd().name` is `"dirfm_tutorials"`, not `"notebooks"`, so the
check never fires and `PROJECT` resolves one directory too shallow -- `notebooks/` itself, not the
repo root. Everything downstream (`OUTPUTS = PROJECT / "outputs"`, and in
`tutorial_dirfm_basics.ipynb`'s case the printed `PROJECT =` sanity check) is wrong as a result.

This was already fixed once, in `tutorial_auror_scene.ipynb` (re-run during Stage 05 since its
inputs moved), with:

```python
PROJECT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())   # repo root, from any depth
```

This walks up from wherever the notebook is actually run from and stops at the first ancestor
holding `pyproject.toml` (the repo root marker) -- correct regardless of nesting depth, so it
doesn't break again if a tutorial moves another level deeper later.

The other three tutorials still have the stale depth-one check: `tutorial_dirfm_basics.ipynb`
(`PROJECT = Path.cwd()` / `if PROJECT.name == "notebooks": PROJECT = PROJECT.parent`),
`tutorial_orbit_to_ground.ipynb` (identical pattern), and `tutorial_tacoma_scene.ipynb`
(`PROJECT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()`).

## STEP 1

In each of the three notebooks, replace the broken `PROJECT = ...` logic with the same
ancestor-walk `tutorial_auror_scene.ipynb` already uses:

```python
PROJECT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())   # repo root, from any depth
```

Keep each notebook's own comment style and surrounding lines (e.g. `tutorial_dirfm_basics.ipynb`'s
`OUTPUTS.mkdir(...)` line and printed sanity check, `tutorial_orbit_to_ground.ipynb`'s `IN_DIR`/
`OUT_DIR`/`DATA_DIR` lines) unchanged -- only the `PROJECT` assignment itself changes. Don't
introduce the helper as a shared function or module; each tutorial is self-contained by design
(`notebooks/README.md`), so a copy-pasted one-liner in each is consistent with how
`tutorial_auror_scene.ipynb` already did it, not a regression.

## STEP 2

Re-execute all three notebooks top to bottom from their actual location
(`notebooks/dirfm_tutorials/`) and confirm each one's printed `PROJECT`/`OUTPUTS` (or equivalent)
now resolves to the repo root, not `notebooks/`, and that each still runs and renders as before.
Report what each notebook's corrected output paths resolve to.

## CONSTRAINTS

- Don't touch anything else in these notebooks -- this is a one-line fix per notebook, re-executed
  to confirm, nothing more.
- Don't touch `tutorial_auror_scene.ipynb` -- already fixed and re-run during Stage 05.

Report git status and the actual `git add`/`git commit` commands, as a separate commit from Stage
05's.
