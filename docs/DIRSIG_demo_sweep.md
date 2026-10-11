# DIRSIG demo sweep

Every DIRSIG 5 demo shipped with the installation (`external/dirsig/demos/zips`), run once through the pass-through form by `scripts/sweep_demos.py`: which demos run in this installation, what they cost, what they output, and why the others fail. It is the evidence for choosing which demos drive layered loader work; `docs/DIRSIG_demo_coverage.md` is the static survey of the same demos and `docs/DIRSIG_demo_reference_runs.md` the measured reference runs of the two committed pass-through recipes.

The part between the markers is generated from the sweep's results file (outside the repository) and rewritten after every demo; text outside the markers is kept. Only names, sizes, digests, measurements and DIRSIG error lines appear here, no demo bytes. Each demo is extracted from its zip, its simulation files are tried in turn (`demo.sim`, then `demo.jsim`; with neither, up to four top-level `.sim` or `.jsim` files in alphabetical order), stopping at the first that renders; a render under 300 s is repeated in a fresh work root to test determinism. The engine is DIRSIG 2026.38 (a020954) with a per-run `HOME`, so DIRSIG's material caches start cold for every attempt and the user's cache is not involved. "Max CPU" is the maximum over the host's thermal zones during the attempt; 90 C or more is flagged as a throttle suspect.

<!-- sweep_demos: generated between these markers by scripts/sweep_demos.py; edit outside them -->
The sweep has not run at this commit.
<!-- sweep_demos: end -->
