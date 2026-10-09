# MANIFOLD–DIRSIG CONOPS and Guide (as built)

**Scope:** the driver for DIRSIG5 jobs from MANIFOLD run specs (`dirfm`, `protodirsig`, notebooks) and the
interface it presents to MANIFOLD.
**Status of the document:** a theory of the interface, tested against the code in this repository and
periodically against the MANIFOLD implementation team. Section 10 records each disagreement and its outcome.
**Authority:** this document is the single description of what is built. When code and document disagree,
the code is right until the document is corrected in the same commit.

Status markers used in section headings and tables:

| Marker | Meaning |
|---|---|
| `built` | Implemented and covered by a test or an executed notebook. |
| `built, partial` | Implemented for the AUROR job only; the limits are stated. |
| `proposed` | Offered to MANIFOLD. Not adopted in their schema or architecture documents. |
| `open` | Question for MANIFOLD; no position taken. |

## 1. Purpose

protoDIRSIG takes a `run-spec/1` YAML and executes the DIRSIG job it describes through `dirfm`, with no
MANIFOLD executor, registry, or orchestrator. Its purposes are: (a) establish which parts of a
`dirsig-engine/1` run spec a real job can be driven from; (b) validate and integrate `dirfm`; (c) grow an
abstraction layer (`src/protodirsig`) into the SDK; (d) provide notebooks for new `dirfm` and SDK users;
(e) test the MANIFOLD requirements by conforming to them. The reference job is the AUROR static NIR pass over
DIRSIG's Tahoe scene, `run_specs/auror_ref.yaml`.

## 2. System overview

Layers, bottom to top:

- **DIRSIG5** (`dirsig-2026.38.0.a020954`): `scene2hdf` and `dirsig5` binaries. Inputs are files; the scene is
  consumed by path.
- **`dirfm`** (RIT, read-only dependency): Python builders for DIRSIG input files, and `DIRSIG.run()`, the only
  code that constructs a `dirsig5` command line.
- **`src/protodirsig`**: gap-fillers and the run-spec driver (section 7).
- **Notebooks**: stage notebooks (the conformance template), `dirfm` tutorials, sidebars (section 8).

A run spec becomes a job in three steps, each independently testable:

1. **Schema check** (`simulation.schema_errors`): required members and enumerated values of `run-spec/1` and
   `dirsig-engine/1`.
2. **Resolution** (`run_spec.resolve_auror_run`): `engine.*` becomes `dirfm` objects and file paths.
3. **Execution check** (`Simulation.validate`): the job is assembled in a scratch directory and run with
   `dirsig5 --dry_run --log_info_filename`.

`LocalRegistry.submit` runs the three and accepts or rejects. `Simulation.run` renders only an accepted job.

**Resolved versus generated** `built`. Each `engine.*` block is one or the other.

- *Resolved*: the block names an existing file and the spec selects it by reference. `scenes`, `platform`,
  `atmosphere.database`, `weather.file`. Nothing is built from spec values.
- *Generated*: the block states values from which a file is built at job-assembly time. `motion` (`.ppd`) and
  `tasks` (`.tasks`) only. Generation uses `dirfm.platform_motion.PlatformPosition` and `dirfm.tasks.TASKS`,
  and is `built, partial`: `motion.kind: static` with Euler orientation in the `scene`/`sceneenu` frames.
  `waypoints` and `orbit` need `dirfm.FlexMotion` and are rejected at resolution.

Generation happens where `Simulation._assemble()` copies resolved assets into the job's `inputs/` directory.
The closest MANIFOLD analog is `materialize` into `<work>/<run_id>/inputs` (Configuration_v02, line 309).

`resolve_auror_run` is narrow by design (`built, partial`): `new_atmosphere`, ephemeris `spice`, weather
`library`, one scene, static motion. It raises `RunSpecError` on anything else, so what it accepts is a lower
bound on what the schema permits.

## 3. Run-spec contract `built, partial`

A run spec is one YAML document with three keys (Metadata_v02 §6.3).

| Key | Required | Content |
|---|---|---|
| `spec_version` | yes | `run-spec/<major>`; currently `run-spec/1`. |
| `descriptor` | yes | Engine-independent. Governed vocabulary, units, frames, provenance. Authority for catalog search. |
| `engine` | no | Origin-specific generator input; one schema per origin (`dirsig-engine/1`). Absent for field data. Not indexed. |

`descriptor` is registered, searched, and hashed into the provenance record. `engine` is what the generator
and executor consume.

### 3.1 `descriptor`

Required blocks for `run-spec/1`: `meta`, `origin`, `collection`, `sensor`, `settings`, `fidelity`. `field`
is required iff `origin.kind: field`. `extras` is optional. Unknown keys are rejected everywhere except
`extras`.

- **`meta` / `origin`.** `meta.name` is an immutable alias to one `parameter_set_id`. `origin` has two axes,
  `kind` (`synthetic`, `field`) and `engine` (`dirsig`, `satsim`, `usd`, `field`); `engine: field` iff
  `kind: field`. DIRSIG: `origin: {kind: synthetic, engine: dirsig}`.
- **`collection`.** Observation conditions as governed terms and derived quantities, not engine parameters.
  `atmosphere.regime` is a vocabulary term, not a DIRSIG preset. `epoch` is phenomenon time (read from
  `.tasks`). `geometry.range` is required when `targets` is non-empty.
- **`sensor`.** A `sensor-spec/1` reference; structure per `AV_MANIFOLD_Detector_v02` (section 4).
- **`settings`.** Commanded per-entry values: exposure, frame rate, gain, black level, ROI, binning. One
  member per `sensor.entries[]`; `entry_id` must resolve. Stays in the run spec, not the sensor file.
- **`fidelity`.** `modeled`, `approximated`, `absent` lists and free-text `valid_for`. Authored, not
  derived, not queryable.
- **`extras`.** Namespaced `<origin>.<name>`; stored as `jsonb`; no query guarantees.
- **Quantities.** A `quantity` is `{value, provenance, uncertainty?, uncertainty_kind?, conditions?}`.
  `provenance` is `measured`, `specified`, `modeled`, or `inherited_from_type`; `conditions` is required
  when `measured`. Fields fixed by design are plain scalars.

### 3.2 `engine` (`dirsig-engine/1`)

The `engine` section is origin-specific: one schema per engine, selected by `descriptor.origin.engine`.
DIRSIG (`dirsig-engine/1`) is the first engine implemented. Others (`satsim`, `usd`) will follow with their own
`<engine>-engine/<major>` schemas; none of what follows constrains them. The `descriptor` is the
engine-independent part of the contract and is shared across all engines. This document describes the DIRSIG
engine only.

Members (Configuration_v02 A.8.1): `generator`, `scenes`, `platform`, `motion`, `tasks`, `atmosphere`
(required); `weather`, `ephemeris`, `run` (optional).

- **Division with `descriptor`.** Epoch, exposure, frame rate, gain, and black level are stated once, in
  `descriptor`; the generator writes them into `.tasks` and `.platform`. Platform position at epoch is
  emitted by the generator and may be omitted from an authored spec.
- **`scenes[]`.** Library scene references with optional `[x,y,z]` offsets. `scene2hdf` compiles the HDF at
  run time beside the `.scene` file; the HDF is derived, outside the manifest, never pre-compiled in the
  library.
- **`platform`.** References a library `.platform` by name and hash, with a `library_entry` whose `sensor`
  instance is checked for equality. `output_prefix`, `split_channels`, `integration_samples`. The
  `.platform` is not regenerated from `descriptor.sensor`.
- **`motion`.** `static | waypoints | orbit`. Orbit propagation (skyfield + SGP4 with UT1–UTC) runs outside
  DIRSIG; only ECEF waypoint samples cross into the engine body.
- **`tasks`.** `{start, stop}` windows relative to `descriptor.collection.epoch`; `start == stop` is one
  static sample.
- **`atmosphere`, `weather`, `ephemeris`.** `atmosphere.plugin` is `four_curve` or `basic` in A.8.7.
  AUROR uses `new_atmosphere` (`proposed`, section 10). `ephemeris.plugin: spice` takes no inputs and reads
  kernels from the DIRSIG installation.
- **`run`.** Seed, convergence, thread count. Recorded on the execution record, not in identity.
  `engine.run.seed` is confirmed to work: `dirfm.DIRSIG.set_seed` passes `--random_seed` to both
  `scene2hdf` and `dirsig5`, and seeded renders are byte-identical across assemblies. `--threads` is not in
  `engine.run`.
- **Not in the body** (A.7): quaternion orientation, STK report import, velocity-tracking `up`, `EarthGrid`,
  jitter, uniform or classic radiative transfer, turbulence, uniform weather. A tree needing these is
  registered with a hand-written descriptor.

### 3.3 Outside both sections

Installation-resident data (`FourCurveAtmosphere` presets, SPICE kernels, `ThermWeather` files read with
`weather.source: install`) is covered by a Merkle hash per DIRSIG installation (`engine_data_sha256`) on the
execution record. Execution parameters are on the execution record, not the registered spec.

### 3.4 Admission `open` (MANIFOLD-side)

The generator emits files and descriptor from one run spec; admission validates and hashes the emitted
descriptor, not the authored one. `contract_version`, `_schemaURL`, `system_configuration_id`, and
`noise_class` are set after the gate and are never authored. The extractor reads values back from the
registered files and compares them with the descriptor (MD-13); a column with no extractor path is
`unvalidated`. protoDIRSIG implements none of admission, extraction, or hashing. The loader is
`yaml.safe_load`; `content_hash` values are placeholders; duplicate-key rejection is absent.

## 4. `sensor-spec/1` `built`

A sensor system is reusable across runs. `sensor-spec/1` is the `descriptor.sensor` block as its own
document: `spec_version: sensor-spec/1`, `meta` (`name`, `tags`, `description`), and `sensor` as in 3.1.
A run spec carries `descriptor.sensor: {ref: {name: "<name>.yaml", content_hash: "sha256:<hash>"}}`; the name resolves against the
sensor library, `sensors/`.
An inline `descriptor.sensor` is rejected by the schema and resolution checks. The first entry is
`sensors/auror-nir.yaml`.

`content_hash` is authored and carried through; nothing computes or verifies it.

Each focal plane carries a `detector` block: the physical device, whose properties are fixed.
`DeviceVendorName`, `DeviceModelName`, `SensorWidth` and `SensorHeight` (the full frame), `SensorPixelWidth`,
`SensorPixelHeight`, `fill_factor`, `channel_layout`. A value not known is `null`, never a guess.
The window DIRSIG models, usually a subset of the full frame, is the commanded `roi` setting
(`Width`, `Height`, `OffsetX`, `OffsetY`, SFNC names) in the run spec's `settings` member for the entry. The loader
rejects a `settings` member whose `entry_id` matches no sensor entry, and a known `roi` that exceeds the
detector's full frame.
Library entries: `auror-nir` (AUROR_ref; vendor, model, and full frame not recorded) and
`deepscan_850_306_nir_1280` (Eoptic DeepScan with a Teledyne SCION 1280 x 1024 VisGaAs sensor; optics and
readout values pending).

Several required `sensor` fields have no DIRSIG source (`SensorShutterMode`, `AdcBitDepth`,
`timestamp_reference`, `optical_path`, `system_id`, `reference_frame`). They are assigned in the library entry
with `provenance: specified` or `modeled`, not read from any DIRSIG file. `entry_id` joins each sensor entry
to its `settings` member in the run spec.

## 5. Repository layout and resolution roots `built`

```
config_repo/
  scenes/<scene>/<scene>.scene     # geometry/, materials/, maps/ as descendants
  platforms/<platform>/<platform>.platform
  weather/<name>.wth
  atmosphere/<name>                # proposed path; see section 10
run_specs/                         # run-spec/1 documents
sensors/                           # sensor library: sensor-spec/1 documents
contracts/                         # schemas, vocabulary, validators (empty today)
external/                          # pinned dirfm, agent-docs, DIRSIG link; gitignored (pins.json tracked)
src/protodirsig/  tests/  notebooks/  scripts/
tests/fixtures/auror_ref/          # motion and tasks files; compared with generated files only
outputs/<job>/                     # ephemeral job directories; gitignored
```

Refs resolve by which side of the schema they sit on.

| Ref | Resolves against |
|---|---|
| `engine.*` (`scenes[].ref`, `platform.ref`, `atmosphere.database.ref`, `weather.file`) | `config_repo/` |
| `descriptor.*` (`sensor.ref`) | `sensors/` (the sensor library) |
| `engine.motion`, `engine.tasks` | not resolved; generated into the job directory |

Each library folder is a resolution root and maps to a future MANIFOLD repository. Any `descriptor` ref
added later resolves against its own library, regardless of where the engine-asset library lives. `config_repo/` is read-only at run time. A job directory holds a scene reference
copy, byte-identical copies of resolved library files (geometry and materials symlinked back to the library),
and the generated motion and tasks files.

`config_repo/` follows Configuration_v02 A.8.3 for `scenes/` and `platforms/`. The nesting is also DIRSIG's
own convention: `$SCENE_DIR` defaults to the `.scene` file's folder, and the reference layout nests
`geometry/`, `materials/`, `maps/` there.

Library assets are real files. The MANIFOLD hashing procedure rejects symlinks (Configuration_v02 §2.3), and
symlinks appear only in the per-run view the executor builds (AD A-42). `config_repo/` therefore holds no
symlinks. Data that ships with the DIRSIG installation (`FourCurveAtmosphere` presets, SPICE kernels, demo
scenes) is not copied into it: presets are referenced by name and covered by the installation's data hash.

A top-level folder exists here only if it has a MANIFOLD analog. `AUROR_ref/` had none and is retired to the
test fixture.

## 6. Using `dirfm`

- **Read-only.** `dirfm` is never modified. Its `demos/test_*.py` suite is the usage reference. Install
  editable from a sibling checkout; do not run `pip install -e` from inside the checkout (it writes
  `egg-info`); use `sys.path.insert` if needed outside the conda workflow.
- **Environment.** Each notebook sets `DIRSIG_HOME` and prepends `bin/` to `PATH` in its first cell and
  asserts `scene2hdf` and `dirsig5` resolve.
- **Existing scenes.** `dirfm` builds scenes; it does not read them. A pre-existing `.scene` is referenced by
  setting `SCENE._fname` to its path, which makes `write()` a no-op returning that path. The coverage check
  then runs against a dummy material database and carries no information; use
  `protodirsig.scene_coverage` against the real `.mat`.
- **Command line.** All `dirsig5` flags go through `DIRSIG.run(**options)` (`None` becomes `--flag`, a value
  becomes `--flag=value`). `run()` always runs `scene2hdf` first.
- **Gaps and workarounds in `src/`.**

| Gap in `dirfm` | Handling |
|---|---|
| `NewAtmosphere`: six attributes never initialised under `_FrozenAttrs`; `"Isacc"`/`"Distort"` typos | `atmosphere_patches.py`; test flags an upstream fix |
| `PlatformSensorPlugin.prepare()` always regenerates platform, motion, tasks; `write_files()` assumes that plugin | `platform_ref.py` |
| `SPICEPlugin` requires three kernel paths | supplied by `platform_ref.py` |
| `PlatformPosition.add_entry` formats angles `{:0.6f}`, positions to 3 decimals (~1e-7 per pixel) | accepted; suggest `{:.17g}` upstream |
| `DIRSIG.set_output_prefix` stores `_prefix`; nothing reads it | not used |
| `SCENE._check_coverage` passes vacuously on a `_fname` scene | `scene_coverage.py` |
| No `EarthGrid`, STK-report import, quaternion orientation, velocity-tracking `up`, SGP4 engine | skyfield for propagation; fixed `up` vector verified per pass; tiled `GROUND_PLANE` |

## 7. SDK as built (`src/protodirsig`)

| Module | Role | Status |
|---|---|---|
| `run_spec` | run-spec loader and AUROR resolver | `built, partial` |
| `motion_tasks` | `.ppd` and `.tasks` generation from `engine.motion`, `engine.tasks` | `built, partial` (static) |
| `simulation` | schema, resolution, execution checks; render | `built` |
| `registry` | `LocalRegistry`: local stand-in for submission | `built` |
| `scene_ref`, `platform_ref`, `scene_coverage`, `atmosphere_patches` | `dirfm` gap-fillers | `built` |
| `orbit`, `sensors` | skyfield TEME→ECEF and trajectory; sensor helpers | `built` |

Pending work is in `BACKLOG.md`.

## 8. Notebooks

| Notebook | Role |
|---|---|
| `stage_01_auror_from_runspec` | AUROR job from `auror_ref.yaml`, seeded, motion and tasks generated |
| `stage_02_conformance_template` | same job through `LocalRegistry`, then `Simulation.run`; adds an 8-pixel Lambertian visibility disk (albedo 0.8) in a library mirror under `outputs/` |
| `dirfm_tutorials/` | `dirfm` basics; orbit-to-ground (Stage 3 unwritten); Tacoma; AUROR direct |
| `sidebars/vehicle_point_source` | distils the vehicle mesh to a radiant intensity; renders the emitter with thermal prediction forced |
| `dev/` | local discovery logs; gitignored |

`notebooks/README.md` describes each in detail.

## 9. DIRSIG behaviors that matter

Measured on `dirsig-2026.38.0.a020954` unless stated. Each was confirmed by test, render, or the DIRSIG
documentation.

**Rendering and sampling**

- **Targeted oversampling exists.** An instance named with `::IMPORTANT::` is hypersampled: central sample
  strategy with `<hypersamplingmultiplier>` (set to 100 in `AurorNIRDetector.platform`; five pixels around
  the vehicle received 2000 samples against a frame median of 22). Adaptive sampling does not target
  sub-pixel geometry.
- **Emission is not evaluated by default in a 0.41–2.0 µm job.** Temperature prediction, including
  `DataDriven` temperatures, is off unless the simulation covers the thermal spectrum.
  `dirsig5 --force_temperature_prediction` enables it. A material with zero reflectance and `TEMPERATURE`
  set renders exactly zero without the flag. The flag is global.
- **Point sources only illuminate.** DIRSIG5 does not draw a directly viewed `<basesource><pointsource>`;
  `sources.html` lists direct viewing under "Relevant Options (DIRSIG4 only)". An unresolved emitter or
  reflector is rendered as real geometry at true scale, hypersampled, with ε(λ)·B(λ,T) or a reflectance
  model. A flux-matched small emitter (radiance × area = I) is the equivalent for a distilled intensity.
- **Distilled intensity.** I(λ) = L̄·A_proj from a close-range, no-atmosphere render at the task's sun and
  view angles (`vehicle_point_source` sidebar): A_proj = 0.826 m², I = 67.0 W sr⁻¹ µm⁻¹ for ρ = 0.30 in the
  AUROR channel. Background-subtraction uncertainty is ~3 %.
- **Stars.** No streamlined star-field support. Options are a flux-matched finite emitter, or compositing
  from the truth cube (`pathrightascension`, `pathdeclination`, `pathtransmission`).
- **Precision and seeds.** The ray tracer is single precision. `--random_seed` is honored by both
  binaries. `--convergence MIN MAX THRESH` is the convergence control; there is no `--min_paths`.
- **`GROUND_PLANE` is finite.** Documented as infinite; renders as a ~2 km square about its anchor
  (`scene2hdf` warns "emulating with a limited, facetized representation"). Tile it, with the checkerboard
  phase aligned across seams.

**Geometry and time**

- **TEME is not ECEF.** Treating raw SGP4 output as ECEF places the sub-satellite point 8–9 000 km off with
  no error. Use skyfield and check the rotation independently.
- **Native `sgp4` location engine omits UT1–UTC.** 33 m LEO position error today (1.411 arcsec of Earth
  rotation), up to ~470 m at the 0.9 s IERS bound. Propagate outside DIRSIG.
- **Nadir `LookAt` is singular** against the default `up = [0,0,1]`. Choose a near-perpendicular fixed `up`
  and verify per pass.
- **`straight` instance `<start>`** is the location at simulation start; the AUROR vehicle is on boresight
  at task time 0.

**Outputs and logs**

- Image and truth outputs are ENVI `.img` + `.img.hdr`, float64, BIP. DS9 does not read them directly
  (convert to FITS or use a viewer).
- `--run_info_filename` and `--log_info_filename` JSON logs have no published, versioned schema. The run
  log's `plugin_list` is incomplete (omits `SpiceEphemeris`, `ThermWeather`).
- No documented exit codes. Treat expected-file presence as the success signal alongside a nonzero-exit and
  `[error]`-line check.
- `LightCurve` plugin: magnitude-vs-time diagnostic, not an imager, incompatible with `new_atmosphere`.

**Scene data**

- The AUROR atmosphere database was built for western NY (43.12 N, −78.45, 250 m), not Tahoe; the tasks
  reference time (2009-07-27 11:29:32 −08:00) is stale. Comparisons against the reference are like for
  like; absolute radiometry is not Tahoe's.
- Tacoma: water from the 20 km BOX is ~1.6× brighter than in-mesh water (suspected UV sampling of the
  matid 3005 map); NIR coverage of the panel emissivity curves ends at 0.78–0.80 µm and the ground maps
  cover 0.4–0.7 µm only; hard shadows are exactly zero radiance under `SimpleRadiativeTransfer`.
- AUROR vehicle: true-size reflective vehicle at ρ = 0.30 is a ~1 % excess, below terrain pixel-to-pixel
  variation; the 1500 K emitter with thermal prediction forced is +0.56 of a pixel's signal (~6σ over the
  4×4 block). The 8-pixel disk in stage 02 is a visibility device, not a radiometric model.

## 10. Convergence with MANIFOLD

One row per interface item. `Outcome` is filled after review with the MANIFOLD team: **accepted**
(MANIFOLD adopts), **MANIFOLD changes**, **we change**, or **withdrawn**. Blank means not yet reviewed.

| ID | Item | Our position | Status | Outcome |
|---|---|---|---|---|
| C-01 | `descriptor.sensor` refs resolve against the sensor library; `engine` refs resolve against `config_repo/` | resolve by schema side, not one tree; `sensors/` is its own library, not part of the asset library | `open` | |
| C-02 | `atmosphere/<name>` flat library path | modeled on `weather/<name>.wth`; ratify with C-03 | `proposed` | |
| C-03 | `new_atmosphere` plugin value in A.8.7 (database role `dirsig:atmosphere_db`) | AUROR's atmosphere is `NewAtmosphere` reading a prebuilt HDF5 database; `four_curve` in the architecture-view instances is wrong for this tree. The recipe (MODTRAN tape, `Isaac`) has no run-spec field | `proposed` | |
| C-04 | Where motion and tasks are generated | at `materialize`, from `engine.motion` and `engine.tasks`; or does MANIFOLD expect them pre-built upstream? | `open` | |
| C-05 | Static-only motion generation | acceptable interim; `waypoints` and `orbit` rejected at resolution | `open` | |
| C-06 | Authority of DIRSIG JSON logs | disagreement flag only, never authoritative over the descriptor (the run log is incomplete and unversioned) | `proposed` | |
| C-07 | Compile-once | `scene2hdf` output as a content-hashed artifact, invalidated by scene change; `submit` then `run()` currently compiles twice | `proposed` | |
| C-08 | `--threads` in `engine.run` | add before concurrent jobs share hardware | `open` | |
| C-09 | `--force_temperature_prediction` as an `engine.run` option | default off; global; enable only for scenarios with an intended hot emitter | `open` | |
| C-10 | `engine.platform.output_prefix` | applying it renames outputs and breaks tree reproduction; it appears in no file of the tree | `open` | |
| C-11 | Illustrative instances in Metadata_v02 §6.11 and Configuration_v02 A.8.10 | `meta.name: tacoma-nir-baseline` is stale (values are AUROR); `scenes/tahoe` path matches the nested layout, not the flat received tree; `four_curve` should be `new_atmosphere` | `open` | |
| C-12 | Strict loader and hashing | duplicate and unknown key rejection, canonical-JSON hashing, `content_hash` verification belong on the registry side; not built here | `open` | |
| C-14 | Detector manufacturer and model | `focal_planes[].detector.DeviceVendorName` and `DeviceModelName` (SFNC names, Detector_v02 §6.3); placement in the focal plane rather than `identity` | `proposed` | |
| C-15 | Full frame versus modeled window | `detector` is the Detector_v02 `array` block (SFNC `SensorWidth`, `SensorHeight`, pitch, `fill_factor`, `channel_layout`, all the full sensor) plus vendor and model, under a different block name. The window DIRSIG models is the commanded `roi` (SFNC `Width`, `Height`, `OffsetX`, `OffsetY`) in run-spec `settings`, as Detector_v02 treats a region of interest | `proposed` | |
