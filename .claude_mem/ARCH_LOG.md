# MANIFOLD architecture considerations log

A running log of architecture-level assessments, decisions, and open
questions that arise from protoDIRSIG implementation work but belong at the
MANIFOLD program level rather than in protoDIRSIG's own `FINDINGS.md`.
Append dated entries; don't rewrite earlier ones except to record that a
later entry supersedes them. Entries here are candidates for eventual
promotion into `02-design/` or a `ROLE_PROPOSAL_` when a question is
actually settled — this log is where they live while open.

---

## 2026-10-08 — JSON logging and DIRSIG5 command-line best practices

Prompted by: phased-plan work on the AUROR_ref conformance template
(`review/PLAN_2026-10-08_conformance-template-roadmap.md`), implemented in
`protoDIRSIG/prompt.md` (Stage 2).

**Decision: adopt, narrowly.** DIRSIG5's two JSON logs — the run log
(`--run_info_filename`: compiled scene hash, bounding box, loaded-plugin
inputs) and the info log (`--log_info_filename`: per-capture time, platform
pose, source geometry, output filenames) — are adopted as (a) a free,
pre-execution conformance check via `--dry_run --log_info_filename`, and
(b) corroborating provenance captured alongside real runs. They are **not**
adopted as a registry-level data source or as the schema's source of truth.

**Open question, not yet decided:** descriptor vs. engine-log authority.
The DIRSIG-emitted log states what the engine actually resolved (compiled
hash, resolved geometry); the descriptor states what the author declared.
These can diverge (stale hash, pose typo), and only the engine-side log
catches it. Whether the registry eventually treats the DIRSIG log as
authoritative over the descriptor for overlapping fields, or only as a
disagreement flag that doesn't resolve itself, is unsettled. Leaning:
disagreement flag only — making the descriptor schema hostage to one
engine's log format defeats the point of the descriptor/engine split in
`run-spec/1`. Revisit once a second engine (non-DIRSIG) is in scope and this
can be tested against a real case, not just argued.

**Caution:** the command-line guide describes these logs by field meaning,
not a published, versioned schema. Treat parsing them as parsing an
unspecified, reverse-engineered contract — defensible for a narrow sanity
check (does the dry-run log describe the expected single capture), not
defensible as an automated-decision data source until DIRSIG documents or
RIT confirms schema stability.

**Other best practices from the same page, with architectural consequence:**

- *Compile once.* `scene2hdf` output should be a first-class, content-hashed
  artifact in whatever asset repository eventually replaces the `AUROR_ref/`
  one-off tree (roadmap Phase 5), invalidated only when the source scene
  changes — not regenerated per run. Cheap to get right now, expensive to
  retrofit once multiple scenes exist.
- *No documented exit codes.* An automation-first architecture can't branch
  on structured failure categories from the process boundary alone. Design
  around this: treat artifact presence (did the expected log/output file
  get written) as the success signal, not the process exit code.
- *No documented determinism/seed flag.* `engine.run.seed` in the run-spec
  schema has no confirmed DIRSIG-side effect (see protoDIRSIG `FINDINGS.md`,
  2026-10-08 entry, for the specific unresolved mechanism). Run-to-run
  reproducibility currently rests on upstream input determinism; the
  compiled scene hash in the run log is evidence of that, not a guarantee.
- *`--threads` is an unexposed resource knob.* Not in `engine.run` today.
  Add it to the schema before, not after, MANIFOLD schedules concurrent
  DIRSIG jobs on shared hardware.

No support found on the page for restructuring MANIFOLD's general
provenance model around DIRSIG's JSON logs — the adopted scope above is
the full extent of what the evidence supports.

---

## 2026-10-08 — Stage 02 verification: seed confirmed, run-log completeness gap

Prompted by: independent verification of Claude Code's Stage 02 report
(`protoDIRSIG` commit `5bb1468`).

**Supersedes the open item above.** `engine.run.seed` is confirmed, not
merely suspected: `dirfm.DIRSIG.set_seed` passes `--random_seed` to both
`scene2hdf` and `dirsig5`. Stage 02's render is byte-identical to Stage 01's
(`cmp` on the primary and truth images) despite different assembly code on
different days. Reproducibility rests on an actual DIRSIG/dirfm mechanism,
not only on upstream input determinism as the prior entry assumed.

**New consideration, bearing on the descriptor-vs-engine-log-authority
question above.** `run_info.json`'s `plugin_list` is incomplete: it records
`NewAtmosphere` and `BasicPlatform` but omits `SpiceEphemeris` and
`ThermWeather`, which the job demonstrably used. This weakens the case for
ever treating the DIRSIG-emitted run log as authoritative over the
descriptor for overlapping fields — an incomplete log can't out-rank a
complete, author-declared descriptor. Strengthens the "disagreement flag
only" leaning already recorded; does not yet settle it.

**Evidence for Phase 6 (sweep efficiency), not yet acted on.** `Simulation.run()`
calls `DIRSIG.run()`, which always invokes `scene2hdf` regardless of whether
the scene was already compiled; a `submit()` followed by `run()` compiles
the same scene twice (~1 s each on AUROR_ref's scene). Immaterial for a
single job; the first measured cost supporting the "compile once, reuse
across a sweep" recommendation already made in the roadmap and in the first
entry above.

## 2026-10-08 (cont'd) — sensor-spec/1 split

Wrote the `sensor-spec/1` extraction (`descriptor.sensor` pulled into its own
document, `GD_DIRSIG_RunSpec_YAML_v01.md` §7) and vendored a Stage 03 prompt
for protoDIRSIG to consume it. Two scope decisions made in writing the spec,
recorded here because both narrow or resolve questions the roadmap had left
open rather than merely implementing it as sketched.

**`settings` stays with the run spec, not the sensor file.** The roadmap's
original framing grouped "sensor and settings" as one reusable unit. The
metadata schema (§2) defines `settings` as the commanded, per-collection
value — exposure time, frame rate, gain — not a hardware property. Two runs
against the same sensor profile can legitimately command different exposure
times; folding `settings` into the sensor file would turn it into a template
for one operating point, which is a narrower kind of reuse than "pick a
sensor." This only became visible once the schema was actually drafted, not
from the roadmap text alone — a general case for being suspicious of
grouping decisions made before the schema exists.

**Sensor refs get the same by-name trust as every other ref, not a stricter
one.** `content_hash` is carried but unverified, consistent with
`engine.scenes[].ref` and `engine.platform.ref` elsewhere in this codebase.
Closes the open question from the original roadmap (PLAN_2026-10-08) about
whether sensor refs warranted hash-pinning given their cross-run reuse.
Holding one ref class to a stricter standard than the others without a
schema-level reason to would be inconsistent; the hash becomes load-bearing
only once the deferred registry-side strict loader exists, for all refs at
once, not sensor refs specifically.

Separately: `simulation.schema_errors`'s `refs` check (added Stage 02) only
ever covered engine-side refs (`platform`, `atmosphere.database.ref`,
`weather.file`) — it has no path for `descriptor.sensor.ref` at all, inline
or ref-shaped, because `descriptor.sensor` wasn't a ref when that check was
written. This is now the specific gap the Stage 03 prompt directs closing.
Noted as a pattern, not just a one-off bug: any future descriptor-side field
that gains a `ref` shape will need the same check extended by hand — the
`refs` list is not currently derived from the schema in any way that would
catch a new ref automatically.

---

## 2026-10-08 (cont'd) — Phase 5 scoping: library vs. tree layout, and sweep-efficiency abandoned

Prompted by: selecting the next roadmap phase to build. Two decisions made
before any protoDIRSIG code changed.

**Phase 6 (sweep efficiency) is not buildable against the current tree and
was dropped in favor of Phase 5.** `AUROR_ref/` has exactly one of every
sweepable asset (one `.wth`, one atmosphere database, one `.platform`, one
motion file, one tasks file); `run_spec.py` never regenerates motion/tasks
from spec values, only resolves existing files. There is no parameter
surface to sweep over without first building Phase 5's asset repository.
Separately, `dirfm.DIRSIG.run()` is monolithic — it always calls
`write_files()` then unconditionally recompiles every scene via
`scene2hdf`, with no skip-if-already-compiled branch — so "compile once,
reuse across a sweep" (recommended in the first entry above) cannot be
implemented without modifying `dirfm` itself, which is out of scope by
standing constraint. Recorded so a future attempt at Phase 6 doesn't
re-discover this from scratch: it needs either a second sweepable asset
set or a `dirfm` change, neither of which exists yet.

**Phase 5 targets the Configuration doc's library layout, not the tree
layout `AUROR_ref/` happens to use.** `AV_MANIFOLD_Configuration_v02.md`
§lines 256–268 draws a layout the doc itself holds apart from any one
received or generated tree: `scenes/<scene>/<scene>.scene` (geometry/,
materials/, maps/ nested beneath it), `platforms/<platform>/<platform>.platform`,
`weather/<name>.wth` — explicitly not aligned with run-tree paths, because
aligning them would change manifest paths. `AUROR_ref/` itself uses a flat
layout (`tahoe.scene` at its root, siblings not descendants) that matches
neither. Chose library layout for `config_repo/` over matching `AUROR_ref/`
as-is: confirmed independently via DIRSIG's own scene documentation
(dirsig.cis.rit.edu/docs/new/scene.html) that `$SCENE_DIR` defaults to the
`.scene` file's own folder and RIT's reference layout nests geometry/
materials/maps as direct children of that same folder — the library
nesting is DIRSIG-native, not a MANIFOLD invention, so the migration should
not require rewriting references inside `tahoe.scene` itself (to be
confirmed by grep for absolute paths / `<scenebasedirectory>` overrides
before the copy, and a byte-identical re-render after).

**New convention, proposed and marked non-adopted: `atmosphere/<name>`,
flat.** A.8 defines no library path for a `new_atmosphere` database, because
`new_atmosphere` is itself not an adopted A.8.7 plugin value (see the first
`new_atmosphere` note, 2026-10-08 entry above). Modeled on `weather/<name>.wth`'s
flat, single-file shape rather than invented from nothing. Revisit if and
when `new_atmosphere` (or its database) is formally adopted into the
schema — the library path should be ratified alongside the plugin, not
independently.

**Left open, deliberately:** whether `sensors/auror-nir.yaml` eventually
joins `config_repo/` or stays in `run_specs/sensors/` as a physically
separate folder from the engine-asset repository. `GD_DIRSIG_RunSpec_YAML_v01.md`
§7 resolves refs by schema side (descriptor vs. engine), not by a single
tree, so the two folders being distinct is a deliberate reading of that
rule, not an oversight — but which folder is "correct" long-term was not
decided under the asset-migration's own time pressure.


## 2026-10-08 (cont'd) — AUROR_ref has no MANIFOLD analog; motion/tasks generation scoped to `kind: static`

**MANIFOLD has no persistent "received tree" folder at all.** `AV_MANIFOLD_Configuration_v02.md`
line 309: "the executor calls `materialize` into `<work>/<run_id>/inputs` and runs the engine with
a separate writable output directory." A run tree is generated fresh into an ephemeral work
directory per run, every run, from the run spec. `AUROR_ref/` was never a template for that kind
of tree; it predates `protodirsig.run_spec` and was kept only because nothing yet generated what
it holds. Under the standing principle that this project's folder structure should incrementally
mirror MANIFOLD's real one, `AUROR_ref` is the one top-level folder with no MANIFOLD-side analog —
decided to relocate it to a test fixture (`tests/fixtures/auror_ref/`, trimmed to `motion/`+
`tasks/` only) rather than give it a `config_repo`-style name or keep it at the project root.

**Motion/tasks generation scoped to `kind: static` only, for this stage.** `dirfm.platform_motion.
PlatformPosition` and `dirfm.tasks.TASKS` write exactly `AUROR_ref/motion/AurorMotion.ppd`'s and
`AUROR_ref/tasks/AurorTask.tasks`'s schemas respectively (confirmed by direct comparison of both
dirfm source and the received XML, not assumption). `waypoints`/`orbit` motion kinds need
`dirfm.FlexMotion`, a structurally different generator (`<motion type="flexible">` vs.
`<platformmotion type="generic">`) already in partial use (`src/protodirsig/orbit.py`, backing
`tutorial_orbit_to_ground.ipynb`'s still-unfinished scenario) — deferred until that notebook's own
work is further along, rather than built speculatively alongside the static case.

**`AUROR_ref` kept as a fixture, not deleted or renamed to a `_repo` suffix.** Considered and
rejected: deleting it outright (loses the one piece of ground truth the generator's acceptance
test checks against) and renaming it in place to something like `motion_repo` (implies it is a
resolution root parallel to `config_repo`, which it no longer is once motion/tasks are generated
rather than resolved). A `tests/fixtures/` location makes its role — comparison data for the test
suite, read by nothing in `src/protodirsig/` — unambiguous from the path alone.
