# Handover: the space-to-space thread and the relay

For whoever takes over the relay and the space-to-space work from round 44 on. It states what the repository holds at the end of round 43, how the relay runs a round and the rules each round keeps, how to run the suite on the 4-core laptop, which commit holds which round, where each finding is recorded, and what is open: for the owner, for MANIFOLD, and for a larger host. It adds no finding of its own; each statement points to the document or record that holds it.

## 1. What the repository contains

| Part | Where | What it is |
|---|---|---|
| The SDK | `packages/core`, `packages/sim`, `packages/engine-dirsig`, `packages/engine-satsim` | the `manifold` distributions: run-spec layer and adapter protocol (`core`), `Workspace` and `LocalBackend` (`sim`), the DIRSIG and SatSim engines; the README's "Layout" names their modules |
| Contracts | `manifold_contracts/`, `api/` | `run-spec/1`, `sensor-spec/1`, `dirsig-engine/1` schemas and vectors; the SDK API contract `sdk-api/1` |
| Libraries | `manifold_run_specs/`, `manifold_sensors/`, `manifold_config_repo/` | layers, run specs (172 space-to-space specs under `manifold_run_specs/s2s/`), sensors, engine assets and scenes |
| As-built description | `docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md` | the driver, the contract and the interface to MANIFOLD; section 10.1 is the decisions index |
| Review report | `docs/Review_report_since_r27.md` | what changed since the tag `review-r27`, the defects not fixed, section 3.1 the behaviour changed outside `packages/core`, the decisions asked, the commands a reviewer runs |
| Space-to-space account | `docs/Space_to_space_characterization.md`, `docs/s2s_coverage.md`, `docs/s2s_envelope.md`, `docs/User_manual.md` section 11 | the measurements by round, the coverage map, the sampling-effect envelope, the reader's guide |
| Records | `docs/data/s2s_results.jsonl` (140), `docs/data/risk_measurements.jsonl` (31) | every space-to-space measurement (DIRSIG and SatSim) and every known-risk measurement, written by `scripts/s2s_measure.py` and `scripts/risk_measure.py` |
| The study | `docs/study/` | the journal-style manuscript, its PDF and DOCX, the data appendix, the claims map; `scripts/study_build.py` generates every number in it |
| Deferred work | `docs/Bigger_host_plan.md`, `docs/data/bigger_host_manifest.yaml`, `scripts/bigger_host_run.py` | the measurements this laptop cannot make, and the runner that makes them on a larger host |
| Backlog | `BACKLOG.md` | every open item, one `###` per item |

## 2. The relay

**What it is.** A shell loop on the laptop (`outputs/relay.sh`, under the gitignored `outputs/`, so not in a clone) that runs one prompt at a time through `claude -p`, unattended. Start it once from the repository root, in a terminal with the `protodirsig` environment active:

```
systemd-inhibit --what=sleep:idle:handle-lid-switch --who=relay --why="manifold rounds" bash outputs/relay.sh
```

**Queue protocol** (all under `outputs/relay/`): write the prompt to `next_prompt.md`, then create `READY` whose first line is the round id (for example `r44`); create `STOP` to halt after the current round. The loop waits while the working tree is not clean or another `claude` process runs (`RELAY_IGNORE_CLAUDE_AFTER` sets a cutoff), copies the prompt to `prompt.md` at the root (gitignored), runs the round with a 5-hour timeout (`RELAY_ROUND_TIMEOUT`), and stops after `RELAY_MAX_ROUNDS` rounds (default 6). It writes `status.json`, `finished.json` (exit, tip, dirty file count), `heartbeat` and `logs/<round>.*`, and after each round a bundle of all refs to `~/protoDIRSIG-backup.bundle`. A pre-push hook under `outputs/relay/hooks/` refuses every push from a round.

**Completion signal.** A round writes `prompt_report.md` at the root (gitignored), then `outputs/relay/DONE` last: one line, `<round id> <tip hash> <ISO time> <outcome>`, the outcome `complete`, `stopped` or `partial`. The report's sections, in order: commits (hash, step, suite count); gates; what was proved and not proved; judgment calls; OPEN; tests edited (assertion changes against import-only edits); time used; the push instruction.

**Standing rules** each round's prompt has carried since round 41, to keep:

- The relay host is a 12 GB, 4-core laptop. Nothing heavy beside the test suite (the suite runs alone); the summed peak memory of concurrent jobs under 4 GB; at most 4 jobs; exactly one render at a time (a SatSim run counts as a render), one case per background command. An exit 137 or an out-of-memory kill is a finding to record, not a call to repeat unchanged.
- A background command is limited to 10 minutes: native renders through a script outside the repository, one per command, resuming from completed results. The suite renders at 16 x 16 only.
- No network, no GPU, never `git push`. One commit per step, gated with only that step's changes in the tree.
- Additive against `review-r27`: no change to `run-spec/1`, an existing id-snapshot entry, `packages/core`, the adapter protocol or a run id. Behaviour changed elsewhere goes into the review report's section 3.1 for MANIFOLD.
- A failed gate gets at most two fix attempts, then the step is restored and logged. A test edit may not loosen an assertion; adapting one to a corrected statement is allowed and is reported as "assertion changed" with the reason.
- Every commit leaves the CONOPS true at HEAD. Human documents do not cite the relay's working notes.

## 3. Running the suite in parts

The whole suite (2282 passed, 2 skipped at round 43) takes about 10 minutes here, the background cap, so a gate runs it in thirds by test file, each third its own background command, one after another, with nothing else running:

```
(cd tests && ls test_*.py | sort | awk 'NR % 3 == 1') > ~/third.txt    # third 1; 'NR % 3 == 2' and 'NR % 3 == 0' the others
python -m pytest -q -p no:cacheprovider $(sed 's|^|tests/|' ~/third.txt)
```

The thirds take about 3, 4 to 5 and 3 minutes. Then the checks, each exiting 0, as the review report's section 6 lists them with their expected last lines:

```
python scripts/compose.py --check
python scripts/stamp_hashes.py --check
python scripts/render_diagrams.py --check
python scripts/api_examples.py --check
python scripts/gen_models.py --check
python scripts/survey_demos.py --check
python scripts/id_snapshot.py --check
python scripts/engine_contracts.py --check
python scripts/status_markers.py --check
python scripts/cold_start_check.py --check
python scripts/s2s_scenarios.py --check
python scripts/s2s_measure.py --check
python scripts/risk_measure.py --check
python scripts/bigger_host_run.py --check
python scripts/review_report.py --check
python scripts/s2s_coverage.py --check
python scripts/s2s_envelope.py --check
python scripts/study_build.py --check
```

and `git diff review-r27 -- packages/core tests/data/id_snapshot.json`, which must stay empty. `/tmp` is a 5.5 GB tmpfs; a suite beside scratch renders there fails with "Disk quota exceeded".

## 4. Commits and rounds from round 28

A round's range runs from the previous round's last commit (exclusive) to its own last commit, which holds its log. The review report's section 1 generates the same table for rounds 28 to 36 with the files each added.

| Round | Commits (first..last) | What it did |
|---|---|---|
| 28 | `0d8f874`..`796ecd5` | survey truth for scenes naming `TEMP_SOLVER` or `SOURCE_SHAPE`; eight more layered-against-pass-through comparisons; `origin/main` stops at `0d8f874` |
| 29 | `71e933a`..`91ebb4f` | the space-to-space coverage audit; family I (63 specs) and its first measurements |
| 30 | `aeac0a7`..`142b06b` | family II (shutter blur, look angle against a background); round 29's three differences explained |
| 31 | `020b653`..`a2d992f` | family III (Sun and phase on a sphere); SatSim parity on one geometry |
| 32 | `594d37d`..`b2e2c86` | the CONOPS decisions index; `scripts/s2s_measure.py` and the results file; the transferred scenes |
| 33 | `5bcef1f`..`6180991` | risks A to E (`scripts/risk_measure.py`, the risk records) |
| 34 | `7ffc2c4`..`df68496` | the authoring and engine-author guides; notebook stage 06; `compare_layered.py --threads` |
| 35 | `dc7a13d`..`8a59ced` | the friction audit, the user manual, the quick-start notebook, the recipe form prototype |
| 36 | `18d2bb8`..`3fa0a02` | the deferred-work inventory, its manifest and `scripts/bigger_host_run.py` |
| 37 | `d18ad55`..`655fc6c` | the review report; the documents' consistency test; foxbat at one thread |
| 38 | `5c96674`..`e93c508` | the coverage map; twelve coverage points at 64 x 64 |
| 39 | `fdc0cff`..`3a580de` | the streak shortfall, the sub-pixel look and the resolved class isolated |
| 40 | `ae4bcba`..`f8ce601` | SatSim controls of round 39's deficits; the resolved cells; the path-count ask |
| 41 | `aed73b6`..`41405dc` | the sampling-effect envelope; three authoring defects fixed outside the core; the manual's section 11 |
| 42 | `0f9d172`..`5f06951` | the study: manuscript, data appendix, reproduction package |
| 43 | `b981374`.. | A `b981374` the study refreshed against HEAD; B `1c2fe64` the review report's section 3.1 and the black-level revert; C `f6d7c83` this document and the bigger-host update; D the close-out (the round's last commit) |

## 5. Where each finding lives

| Finding | Records (`spec` or `id` in the record file) | Document and section |
|---|---|---|
| Flux closure of a hyperresolved plate within 1 % | `s2s_results.jsonl`: `s2s-hyperresolved-*` | characterization "First measurements (round 29)" E1; study "Hyperresolved targets" |
| A sub-pixel target needs a backstop and the `::IMPORTANT::` label (the earth core ends a pixel's sampling) | `s2s-unresolved-*`, `s2s-unresolvedplain-*` | characterization "Scenario family II (round 30)" C; study "Unresolved targets" |
| Shutter blur: flux kept, the fitted streak 2.0 to 3.4 % short at default sampling | `s2s2-blur-*` | characterization family II A and "Three differences isolated (round 39)" A; envelope rows 6 to 13 px and over 13 px |
| The streak shortfall is DIRSIG's adaptive per-pixel sampling | `s2s2-blur-*`, `s2s-satsim-ctl-plate-*` (and scratch fixed-path renders, `docs/study/data/document_figures.csv`) | characterization round 39 A and "SatSim as a control (round 40)"; study "The SatSim control and the attribution of the deficits" |
| The pixel-corner deficit of a sub-pixel plate at 45 to 65 degrees | `s2s-unresolved-r25km-*-l45..65-*-w64` and the off-corner records | characterization round 39 B; envelope row 0.5 to 1 px fixed labelled |
| The resolved class (6.12 px): look alone 2.3 to 2.7 % low, sphere at phase 120 2.3 % high | `s2s-hyperresolved-r100km-*-w64`, `s2s3-phase-hyperresolved-*-r100km-*` | characterization round 39 C and "The resolved cells round 39 left empty (round 40)"; envelope row 6 to 13 px fixed |
| Combined motion: the flux deficit grows as the plate shrinks (0.0, 1.3, 3.7 %) | `s2s2-blur-both-*` | characterization "The sampling-effect envelope (round 41)"; envelope rows "both" |
| A moving sub-pixel plate loses 12.7 % (1.22 px) and 22.2 % (0.61 px) | `s2s-unresolved-r12p5km-v1000mps-*`, `s2s-unresolved-r25km-v1000mps-*` | characterization rounds 39 C and 41; envelope rows "target" under 2 px |
| Sun and phase angle follow the closed forms | `s2s3-*` | characterization "Scenario family III (round 31)"; study "Hyperresolved targets" |
| SatSim parity (one geometry) and SatSim controls | `s2s-satsim-*` | characterization "SatSim parity on one geometry (round 31)" and round 40 |
| One thread repeats bit for bit; the default thread count resamples a few pixels | risk records E | `docs/DIRSIG_determinism.md`; study "Determinism and reproducibility" |
| Layered jobs and HOME, concurrency, cancel, captures per task window | risk records A, B, C, D | review report sections 2.2 and 5; CONOPS section 10.1 rows C-28, C-30, C-43 |
| Window against native size (0.9999, 0.9963, 0.9866) | the `-w64` records and their native records | characterization "Coverage points (round 38)"; manual section 11 |

The envelope (`docs/s2s_envelope.md`) is the one-table summary: each record's deficit by size, motion and label, with what the records show removes it.

## 6. DIRSIG against SatSim: the attribution and its limits

SatSim draws a target without per-pixel ray sampling. Where a DIRSIG deficit is absent from SatSim's render of the same geometry, at the same window, range, exposure and placement, the rounds attribute it to DIRSIG's adaptive per-pixel sampling: the pixel-corner deficit (SatSim holds the corner, its offsets and the 60 degree sprite to 6.3e-6), the moving 1.22 px plate's lost flux (SatSim 0.999995 and 0.999994) and the resolved streak shortfall (SatSim 0.9942 to 0.9983 against DIRSIG's 0.9743 to 0.9759). For the streak, scratch renders at a fixed 1000 paths per pixel remove most of it (0.9988 and 0.9983).

The limits:

- The attribution is by absence in another renderer, not by a DIRSIG control: the run spec cannot state a per-pixel path count, so the fixed-path renders edited an assembled job and are scratch figures, not records.
- No SatSim control exists for the moving 0.61 px plate, combined motion at a resolved size, or the resolved plate's look alone; these and three single records (the resolved sphere at phase 120, the still 3.06 px plate, the 1.22 px plate a quarter pixel off the corner) have no attribution (study, "The SatSim control and the attribution of the deficits").
- SatSim models a target as a point or a sprite, so a flat plate's look and Sun dependence, a resolved sphere, the `::IMPORTANT::` label and the `both` group's background have no SatSim counterpart (BACKLOG "Space-to-space: what SatSim cannot express as a control (round 40)").
- Both are renderers. There is no real-sensor comparison and no hardware validation (BACKLOG "Space-to-space study: what it lacks (round 42)").

## 7. Open items

**For MANIFOLD** (CONOPS section 10.1; the review report's section 4 lists all MANIFOLD rows with their evidence):

| C-n | Ask | Blocks 0.1 | State |
|---|---|---|---|
| C-34 | Artifact roles and run verdicts in `sdk-api/1` | no | a position offered, not agreed |
| C-35 | SatSim's seed: a required input that enters the run id | yes | a position offered, not agreed |
| C-36 | Asset snapshots and who owns the pins | no | a position offered, not agreed |
| C-37 | Opaque descriptors for a second engine | no | a position offered, not agreed |
| C-38 | License position on bundling SatSim | no | a question, no position taken |
| C-39 | `atmosphere.uniform` with `plugin: basic` in `dirsig-engine/1` | yes | a position offered, not agreed |
| C-40 | `platform.as_authored` in `dirsig-engine/1` | yes | a position offered, not agreed |
| C-41 | `atmosphere.simple` with `plugin: basic` in `dirsig-engine/1` | yes | a position offered, not agreed |
| C-42 | `working_folder` in `dirsig-engine/1` | yes | a position offered, not agreed |
| C-43 | One capture per task window, checked by the SDK | no | a question, no position taken (risk D measured) |
| C-44 | Governed vocabulary values for space-to-space runs | yes | a question, no position taken |

Also for MANIFOLD: the five behaviour changes outside `packages/core` since `review-r27` (review report section 3.1), and the fixed per-pixel path count, which is a candidate ask, not a C-n row: an optional member that would carry the focal plane's convergence settings and change a run id only for specs that state it (BACKLOG "Candidate ask: a per-pixel path count in `dirsig-engine` (round 40)"). Every unattributed space-to-space deficit waits on it.

**For the owner (Kevin):**

- The product direction for authoring: a form or GUI that writes recipes and layers, a CLI, or neither (CONOPS section 10.1, the maintainer's decisions; `docs/Authoring_friction_audit.md`; `scripts/recipe_form.py` prototypes the recipe step).
- The repository host. `origin` is `github.com/KevinKearney/protoDIRSIG`, and `origin/main` is at `0d8f874`: every later commit, from round 28's second to round 43's, is local only, and the relay's bundle (`~/protoDIRSIG-backup.bundle`) is their one copy off the working tree. Where the repository lives, and when it is pushed, is the owner's action (BACKLOG "Release repo plan" and "Publishing and the internal index policy"); no round pushes.
- The black-level advice. The refusal of a non-zero `black_level` says "use 0 or omit it", and omitting it is refused: round 41's default was reverted in round 43 because it gave one job two run ids (review report section 3.1). A fix that holds changes the composer (core) or the message (id snapshot).
- The study's references and author list (`docs/study/README.md` "References to supply"), and its unverified LaTeX and LibreOffice routes.
- The partial-collect mode for a cancelled DIRSIG run and the HOME of layered jobs (review report section 5).

## 8. The bigger host

The measurements this laptop cannot make are seven entries of `docs/data/bigger_host_manifest.yaml`, run by `python scripts/bigger_host_run.py` on a larger host (resumable, `--dry-run` for the plan, `--only NAME` for one entry). `docs/Bigger_host_plan.md` gives the inventory, the concurrency rule, the run instructions and the checks after a run, and its section "Still deferred at round 43" the memory and time estimates the records support for each entry, including the capture-order case and the full-size combined-motion specs.
