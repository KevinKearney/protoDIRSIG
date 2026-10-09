# protoDIRSIG CONOPS: run-spec-driven DIRSIG jobs, current state and open questions

**Date:** 8 October 2026
**For:** the MANIFOLD team, for early feedback
**Status:** Draft. Stage 04 (engine-asset library) is committed; Stage 05 (motion/tasks
generation, below) is in progress.

## 1. What protoDIRSIG is

protoDIRSIG is a local driver that takes a `run-spec/1` YAML (`GD_DIRSIG_RunSpec_YAML_v01.md`)
and runs the DIRSIG job it describes, through `dirfm`, without a MANIFOLD executor, registry, or
orchestration layer. It exists to find out, ahead of those components existing, which parts of a
`dirsig-engine/1` run spec a real job can be driven from and which parts still have to be supplied
some other way. Everything here is driven from a single reference job, `AUROR_ref`'s static NIR
pass over DIRSIG's Tahoe scene, run-spec `run_specs/auror_ref.yaml`.

Three things resolve a run spec into a job: a conformance check (`Simulation.validate()`, schema
→ resolution → execution, mirroring the checks a MANIFOLD executor would run before materializing
a job), a resolver (`protodirsig.run_spec.resolve_auror_run`) that turns the spec's `engine.*`
block into dirfm objects and file paths, and a generator for the two inputs that aren't static
assets (below). None of this validates the full `dirsig-engine/1` schema — `resolve_auror_run` is
narrow by design, accepting only the values the Auror job actually uses and raising on everything
else, so what it accepts is a lower bound on what the schema permits, not a claim about it.

## 2. The distinction this document exists to surface: resolved vs. generated

Every `engine.*` block falls into one of two categories against a run spec.

**Resolved**: the block names an asset that already exists as a file, and the run spec picks it by
reference. `engine.scenes`, `engine.platform`, `engine.atmosphere.database`, `engine.weather.file`
are all resolved this way, against `config_repo/` (section 3). Nothing in these four blocks is
built from spec values; the spec just says which library file to use.

**Generated**: the block states values from which a file must be built, because no file exists
until the run spec is evaluated. `engine.motion` (a platform pose or trajectory) and `engine.tasks`
(collection windows) are the only two in `dirsig-engine/1` that work this way. Through Stage 04,
protoDIRSIG treated both as resolved — it read `AUROR_ref/motion/*.ppd` and `AUROR_ref/tasks/
*.tasks` as received files and checked the run spec's `engine.motion`/`engine.tasks` values against
them, rather than building them. That was workable only because `AUROR_ref` came with the motion
and tasks files already written by hand. It does not generalize: a run spec for a pose or window
combination nobody has hand-authored a `.ppd`/`.tasks` file for has nothing to check against.

Stage 05 (in progress) replaces that check with generation: `engine.motion`/`engine.tasks` are read
and used to build the `.ppd`/`.tasks` files directly, via `dirfm.platform_motion.PlatformPosition`
and `dirfm.tasks.TASKS`. This is restricted, for now, to `motion.kind: static` with euler
orientation in the `scene`/`sceneenu` frames dirfm's static-pose writer hardcodes; `waypoints` and
`orbit` motion need `dirfm.FlexMotion`, a different generator, and stay unbuilt until that work
(already underway, `tutorial_orbit_to_ground.ipynb`) is further along. Once this lands, a run spec
with no corresponding received tree runs end to end: nothing is read back from `AUROR_ref` at
runtime, and `AUROR_ref` becomes a fixture the test suite checks the generator against, not an
input to anything.

## 3. Current layout, by MANIFOLD role

- **`config_repo/`** — the engine-asset library: `scenes/<scene>/<scene>.scene` (with its
  geometry/materials/maps as descendants), `platforms/<platform>/<platform>.platform`,
  `atmosphere/<name>` (proposed, non-adopted path for the `new_atmosphere` extension; see
  `GD_DIRSIG_RunSpec_YAML_v01.md` §9), `weather/<name>.wth`. Nested-library paths follow
  `AV_MANIFOLD_Configuration_v02.md` A.8's own layout (not the flat layout `AUROR_ref` happened to
  use), confirmed independently as DIRSIG-native via the engine's own scene documentation, not a
  MANIFOLD invention. This is a resolution root only — nothing writes into it.
- **`run_specs/`** — vendored `run-spec/1` and `sensor-spec/1` documents, plus the sensor refs
  they point at beside themselves (`run_specs/sensors/`). `descriptor.sensor` resolves here, not
  against `config_repo/`, per `GD_DIRSIG_RunSpec_YAML_v01.md` §7's by-schema-side resolution rule.
- **A generated job working directory** (`outputs/<job>/`, ephemeral) — everything `Simulation.
  _assemble()` writes for one job: a scene reference copy, byte-identical copies of the resolved
  library files, and, after Stage 05, the motion/tasks files this run spec generates. This is the
  one piece of the layout with a direct MANIFOLD analog: `AV_MANIFOLD_Configuration_v02.md` line
  309's `materialize` into `<work>/<run_id>/inputs`.
- **`tests/fixtures/`** (after Stage 05) — `AUROR_ref`'s motion and tasks files only, kept as
  ground truth for the generator's acceptance test. Not a resolution root; nothing in
  `src/protodirsig/` reads it.

The guiding rule for this layout, applied incrementally rather than all at once: a top-level folder
exists here only if it has a MANIFOLD-side analog. `AUROR_ref` as a whole did not — there is no
persistent received-tree concept in MANIFOLD's architecture at all, only `materialize` into a
per-run ephemeral directory — which is why it is being narrowed to a test fixture rather than kept
as a project-root folder.

## 4. Open questions, for feedback

1. **`sensors/` location.** `descriptor.sensor` resolves beside the run spec
   (`run_specs/sensors/`), physically separate from `config_repo/`'s engine-asset library, because
   `GD_DIRSIG_RunSpec_YAML_v01.md` §7 resolves by schema side (descriptor vs. engine) rather than
   by a single tree. Does MANIFOLD's own manifest/registry model keep sensor specs and engine
   assets apart the same way, or does a `sensor-spec/1` document belong in the asset library?
2. **`atmosphere/<name>`, flat.** Proposed here because `new_atmosphere` is not an adopted A.8.7
   plugin value and so has no library path of its own; modeled on `weather/<name>.wth`'s shape.
   Worth ratifying alongside `new_atmosphere` itself, if and when that happens, rather than left as
   a local convention.
3. **Generated motion/tasks and MANIFOLD's `materialize` step.** Section 2's design places file
   generation at the same point `_assemble()` already copies resolved assets into a job's `inputs`
   directory — does this match where MANIFOLD's own `materialize` would generate these, or does
   MANIFOLD expect motion/tasks to always arrive pre-built (e.g. from an upstream mission-planning
   tool) rather than being synthesized from `engine.motion`/`engine.tasks` values at run time?
4. **Static-only generation, for now.** `waypoints`/`orbit` motion are schema-valid under A.8 but
   rejected here at resolution. Confirming this is an acceptable interim gap rather than a
   conformance requirement MANIFOLD is already relying on.
