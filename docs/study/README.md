# Space-to-space study: manuscript, data appendix and reproduction package

The study writes up the DIRSIG5 space-to-space characterization (`docs/Space_to_space_characterization.md`) as a journal manuscript. Every number in its text is generated from the records by `scripts/study_build.py`; nothing here is typed by hand except the template's prose and the two figure lists in `data/`.

| Path | What it is | Written by |
|---|---|---|
| [`manuscript.template.md`](manuscript.template.md) | the manuscript's prose with named fields (`{{KIND:KEY}}`, with an optional format after a bar) | hand |
| [`manuscript.md`](manuscript.md) | the manuscript (pandoc markdown, LaTeX math), fields filled and tables inlined | `scripts/study_build.py` |
| `manuscript.pdf`, `manuscript.docx` | the manuscript built with pandoc (below) | pandoc |
| [`tables/`](tables) | every table, one markdown file each | `scripts/study_build.py` |
| [`figures/`](figures) | every figure, PNG and PDF | `scripts/study_build.py` |
| [`build/`](build) | the LaTeX route (`template.latex`, pandoc's default with the study's patch) and the Typst route's `typst-header.typ` | hand |
| [`manuscript.latex.md`](manuscript.latex.md) | the manuscript with its Unicode math as LaTeX, for the LaTeX route | `scripts/study_build.py` |
| [`claims.md`](claims.md) | each section's numbers mapped to their record ids and commits | `scripts/study_build.py` |
| [`data/study_records.jsonl`](data/study_records.jsonl), [`data/study_records.csv`](data/study_records.csv) | every s2s and known-risk record in one stable column set, with its commit and how to regenerate it | `scripts/study_build.py` |
| [`data/document_figures.csv`](data/document_figures.csv) | figures the committed characterization and determinism documents state and no record holds (scratch controls, truth renders, counts), each with its document and commit | hand |
| [`data/log_figures.csv`](data/log_figures.csv) | figures of rounds 29 to 41 that no committed document states, each with the commit whose working notes hold it (not cited by the manuscript) | hand |

## Dependencies

- The repository's environment (`environment.yml`: Python 3.11, numpy, PyYAML, matplotlib). `scripts/study_build.py` needs nothing else, renders nothing and reads only committed files and `git log`.
- To regenerate the records: the pinned DIRSIG installation and dirfm (`external/pins.json`, `python scripts/bootstrap.py status`), and for the SatSim controls the SatSim 0.26.1 environment the SatSim adapter names.
- To build the documents: pandoc 3 (built here with 3.8). The PDF through LaTeX needs a TeX distribution with `xelatex`; the PDF committed here was built through Typst (below). For the DOCX check, LibreOffice and `pdftoppm` (poppler) if available.

## Regenerating the data from DIRSIG5

Every record's `reproduce` entry in `data/study_records.jsonl` names the spec, the scene, the configuration and the command. For an s2s record (DIRSIG or SatSim) the command is the measurement harness, one spec per command, one render at a time, outside the repository:

```
python scripts/s2s_measure.py run s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0 --work ~/s2s-work
python scripts/s2s_measure.py --check
python scripts/study_build.py
python scripts/study_build.py --check
python scripts/study_build.py --check
```

The harness renders the committed spec through `Simulation.run` at one thread and seed 1 and replaces the record in `docs/data/s2s_results.jsonl`; a one-thread render repeats bit for bit, so a regenerated record carries the same image digest. A record whose source is a `--workspace` folder was rendered through the SDK API; its command adds `--via workspace`.

## Records that cannot be regenerated on a 12 GB host

The relay host is a 4-core, 8-thread laptop with 11 GiB of memory, at most 4 concurrent jobs, a 4 GB budget for their summed memory and 10 minutes per command. Every s2s record can be regenerated there (one render at a time; the native renders take up to about four minutes). Among the known-risk records (`relay_host` column):

| Records | Relay host | Why |
|---|---|---|
| risk A, three records (the job and the user's HOME) | manual | no script in the repository regenerates them: the tracing script was scratch; the record's `method` states it, and the jobs themselves are one-thread renders of seconds to a minute |
| risk B `native-n8`, `small-n8` | no | a batch of 8 concurrent jobs exceeds the relay's 4; the runner's `concurrency-native` entry runs the batches of 1, 2 and 4 here |
| risk B, the other seven | yes | `python scripts/bigger_host_run.py --only concurrency-native --max-jobs 4` (the runner's records carry a host suffix; the 16 x 16 batches were a scratch cut) |
| risk C, three records (cancels) | manual | no script in the repository regenerates them: the cancel-timing script was scratch; the record's `method` states it |
| risk D, four records (captures in one window) | no | the runner's `capture-order-native` entry renders the demos at their own size under a 24 GiB address-space limit; Thermal2 with its captures reversed reached 13 GB virtual memory and was killed by the out-of-memory killer; the reduced-size records were a scratch cut |
| risk E, twelve records (LightCurve1 by thread count) | no | the runner's `lightcurve1-full` entry renders the full demo: about 40 minutes per one-thread render, past the 10-minute command limit, and 13.5 GB of outputs per render; the records' cut to 151 samples was a scratch script (the record's `method`) |
| risk F, one record (Balfour2, the `.tasks` reference time's UTC offset; round 44) | manual | no script in the repository regenerates it: the scripts that rewrote the reference time and compared the images were scratch; the record's `method` states them, and each pass-through render takes about 5 s on this host |
| risk G, one record (Balfour2, the `.tasks` reference time: written digits or instant; round 45) | manual | no script in the repository regenerates it: the scripts that rewrote the reference time and compared the images were scratch; the record's `method` states them, and each pass-through render takes about 9 s at two threads on this host |

The measurements deferred to a larger host, which are not records yet, are the entries of `docs/data/bigger_host_manifest.yaml` (`docs/Bigger_host_plan.md`):

| Entry | Why not on this host |
|---|---|
| `s2s-unlabelled-points` | runs here (18 renders, 538 s summed); deferred for the rounds' render budgets |
| `s2s-blur-both` | runs here (4 native renders, about 590 s summed); deferred for the rounds' render budgets |
| `concurrency-native` | batches of 8 and more concurrent jobs exceed the 4-job limit; 16 to 64 exceed the cores |
| `lightcurve1-full` | 13.5 GB of outputs per render (108 GB for 8) and about 40 minutes per one-thread render, past the 10-minute command limit |
| `capture-order-native` | each render runs under a 24 GiB address-space limit; Thermal2 with its captures reversed reached 13 GB virtual and was killed |
| `forest-layered-comparison` | each render takes more than the 150 s the comparison allows (estimated 525 s, 5 renders) |
| `sweep-capped-demos` | demos that exceeded the sweep's 1800 s cap, at the host's default thread count |

## Rebuilding the manuscript

From `docs/study/`, after `python scripts/study_build.py` (from the repository root).

PDF through LaTeX, with the patched template (`build/template.latex`: pandoc 3.8's default LaTeX template with the study's patch, marked `% study patch`) and the manuscript's Unicode math converted to LaTeX (`python scripts/study_build.py` also writes `manuscript.latex.md`, the manuscript with µ, σ, θ, Φ, ×, ± and the like as LaTeX math):

```
pandoc manuscript.latex.md -o manuscript.pdf --pdf-engine=xelatex --template=build/template.latex
```

No TeX distribution is installed on the relay host, so that command was not run. The committed `manuscript.pdf` was built through Typst (pandoc's `typst` writer and the Typst 0.15 binary that Quarto bundles):

```
pandoc manuscript.md -s -t typst -V mainfont="DejaVu Serif" -V fontsize=10pt --include-in-header=build/typst-header.typ -o _build.typ
typst compile --root . _build.typ manuscript.pdf
rm _build.typ
```

(`pandoc --pdf-engine=typst` in one step fails here: pandoc extracts the figures to a temporary folder outside Typst's root. `build/typst-header.typ` lets long tables break across pages.)

DOCX:

```
pandoc manuscript.md -o manuscript.docx
```

Verification: with LibreOffice, `soffice --headless --convert-to pdf manuscript.docx` and `pdftoppm -png -r 60 manuscript.pdf page` to look at the pages. LibreOffice is not installed on the relay host; the DOCX was checked by converting it back with `pandoc manuscript.docx -t plain` and comparing its text with the manuscript's.

## References to supply

The manuscript cites only the DIRSIG5 documentation, SatSim and standard radiometry, without bibliographic detail; none can be verified offline. To be supplied:

- the DIRSIG5 reference (the tool's documentation or a journal description of DIRSIG5), with the release used, 2026.38.0;
- the SatSim reference (software citation or paper), version 0.26.1;
- a radiometry text for the Lambertian sphere's phase function and the radiance of a Lambertian surface;
- the SGP4 reference used by the platform's orbit propagation;
- the author list and affiliations.

## Claims map

[`claims.md`](claims.md) lists, for each section of the manuscript, the record ids its numbers read, the committed figures it cites from `data/document_figures.csv`, and the commits that added them. `python scripts/study_build.py --claims` prints the same.
