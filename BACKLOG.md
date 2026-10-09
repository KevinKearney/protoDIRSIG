# Backlog

The single to-do list for protoDIRSIG. Add an item any time; remove it when done or dropped (git history is
the record). Each item is a `###` title and a short body, so the file imports into GitHub issues one to one;
the group heading becomes the label.

Group **TBR** holds items whose resolution may require a change on the MANIFOLD side (run-spec schema,
guides, registry, sensor-spec). protoDIRSIG records them and does not edit MANIFOLD documents itself.

## TBR (MANIFOLD-impacting)

### `--force_temperature_prediction` as a run-spec engine option
Default off; global. The reference render has the same black vehicle, and three notebooks and one test pin
byte-identical renders. Enable only for scenarios with an intended hot emitter. Needs a decision, then an
`engine.run` field or a `Simulation` option.

### Modeled window written into the `.platform`
`roi` is a run-spec `settings` member (Detector_v02 treats it as commanded). DIRSIG's `.platform` fixes the array
size (`detectorarray.xelementcount`, `yelementcount`), so the generator still uses the `.platform` from
`config_repo/`. Writing the window from `settings.roi` into a generated `.platform` is not built; until then the
`roi` in `run_specs/auror_ref.yaml` records the window and is not applied. Confirm the placement with MANIFOLD (TBR).

### Confirm the DeepScan values carried from auror-nir
`sensors/deepscan_850_306_nir_1280.yaml` copies optics (85 mm, 306 mm, f/3.6), throughput 0.875, shutter, ADC
depth 14, fill factor 1.0, band width, reference frame, and mount from
`auror-nir`. Confirm against the DeepScan design and the SCION datasheet. Remaining null: Teledyne part
number.

### `engine.platform.output_prefix: auror_nir_` is not applied
Applying it renames the outputs and breaks reproduction of the tree. It appears in no file in the tree, so it
looks like an authoring choice in the YAML. Settle with MANIFOLD.

### Three resolution roots, one rule
Engine assets resolve against `config_repo/`, the sensor ref against `sensors/`, motion and
tasks are generated. Still open: whether inline `descriptor.sensor` stays disallowed (the code rejects it).

### Strict loader and content hashing (MANIFOLD registry side)
Duplicate-key and unknown-key rejection, canonical-JSON hashing, and `content_hash` verification are not
built. The loader is plain `yaml.safe_load`; the hashes are placeholders.

### Compile-once
`submit` then `run()` runs `scene2hdf` twice. Irrelevant for one job, material for sweeps.

### `run_info.json` is not a complete plugin record
`plugin_list` lists only `NewAtmosphere` and `BasicPlatform`; `SpiceEphemeris` and `ThermWeather` are missing.
Do not use it as the provenance record of plugins.

### `--threads` in `engine.run`
Not exposed. Add before MANIFOLD schedules concurrent DIRSIG jobs on shared hardware.

### Generalize `resolve_auror_run`
It accepts only `new_atmosphere`, ephemeris `spice`, weather `library`, one scene, and `static` motion.
`four_curve` and others fail with a specific `RunSpecError`. The NewAtmosphere backend recipe (MODTRAN tape,
`Isaac`) has no run-spec field and is fixed in `AUROR_ATMOSPHERE_BACKEND`.

### Waypoint and orbit motion generation
Motion generation covers `kind: static` only. Waypoints and orbits need `dirfm.FlexMotion` and a design
decision.

## SDK and run-spec engine

### Doc-code drift check
A test asserting that every `run_specs/*.yaml` passes `schema_errors` and every module in `src/protodirsig`
appears in the CONOPS module table.

### Release repo plan
Cut the validated SDK, tests, and notebooks into a new repository under formal change control. Strip
`.claude_mem/`, `notebooks/dev/`, and `prompt.md`; carry `docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md`.

## Vehicle (URSO) and radiometry

### A/B validation of the distilled intensity
Render the real mesh with `Gidder_mat_reflective` (thermal off) against the same seed without it, and compare
the added signal with the +0.0115 prediction. A match validates I = 67.0 W/(sr µm). A flux-matched
`::IMPORTANT::` emitter (radiance × area = I) is the DIRSIG5 route to a rendered unresolved object.

### Decide what the sandbox target demonstrates
The true-size reflective vehicle is a ~1 % excess, below terrain pixel-to-pixel variation. The 1500 K emitter
is detectable (~6σ over the block). A reflective unresolved object needs a dark background or a much larger
or brighter object.

### Emitter residual
Rendered +0.56 against predicted +0.51 (10 %), with no stated uncertainty. Quantify against the block noise
before quoting either number.

### Two unexplained DIRSIG5 source behaviours
A source scaled 10⁹ times changed nothing at 50 km. The same source on a static instance zeroed the whole
close-pass image. Low priority; neither affects a current result.

### LightCurve cross-check (optional)
Independent magnitude-vs-time check of the distilled intensity. Incompatible with `new_atmosphere`; needs its
own BasicAtmosphere/SimpleAtm job.

### Atmosphere database is for a different site
The AUROR database was built for western NY (43.12 N, −78.45, 250 m; stored sun zenith 36.24°, azimuth
238.56°), not Tahoe (21.50 / 155.52). The tasks reference time (2009-07-27 11:29:32-08:00) is stale and
labels a July date PST. Rebuild the database for the site if absolute radiometry is ever needed.

## Notebooks and tools

### Image viewer for DIRSIG ENVI output
DS9 cannot read the ENVI `.img` + `.hdr` (float64, BIP). Build a pyqtgraph viewer (ImageView, ROI, mouse-move
truth readout) as an optional `[viewer]` extra behind `protodirsig-view`. Stage A: ENVI loader plus a tested
shared ROI-excess function. Stage B: the viewer. Run-vs-run difference is kept while validation continues.

### `tutorial_orbit_to_ground` Stage 3
Final render and comparison. The notebook status still reads "in progress".

### New-user notebooks
A short path for a new user of `dirfm` and then the SDK, built from the existing tutorials and stage
notebooks. Define the path before writing anything new.

### Motion notes in `docs/dirsig_motion_temporal.md`
Kevin's DIRSIG motion notes. Contains errors (direct point-source viewing; targeted oversampling). Correct
the errors or delete the file once its content is absorbed into the CONOPS.

## Tests and environment

### Notebooks and tests still assume sibling checkouts and `~/DIRSIG`
Notebook first cells set `DIRSIG_HOME` and locate `dirfm` by home-relative paths. Switch them to
`external/` (the `dirsig` link and `dirsig-file-maker`) so the bootstrap is the only setup step.

### Asset manifest for large scenes and databases
`config_repo/` holds real files, so scenes and databases over about 50 MB cannot go in git. Add a manifest
(name, sha256, size, source) and a `bootstrap.py assets` step that copies each asset from its source (the
DIRSIG install for shipped demo scenes such as Tacoma and HarvardForest, an artifact store for acquired ones)
into a gitignored `config_repo/` path and verifies the hash. Decide LFS versus a content-addressed store
first. Each new scene also needs a matched atmosphere database, weather file, and platform.

### CI job
Run `scripts/bootstrap.py status`, then the test suite, on a clean clone. Needs a runner with a DIRSIG
install or a container image that has one.

### Dangling citations in the MANIFOLD documents
`AD_MANIFOLD_Architecture_Description_v02` and `AV_MANIFOLD_Configuration_v02` cite deleted documents
(`review/TRIAL_2026-10-06_dirsig-container.md`, `ROLE_PROPOSAL_2026-10-05.md`,
`MANIFOLD_Gap_Analysis_and_Project_Plan`, and the folded A&T analyses). Recoverable from eopticDocs git history;
the MANIFOLD team decides whether to reword the citations.

### pytest is not installed in the `protodirsig` env
Every stage ran it from a scratch `--target` install. Declare the `dev` extra in `environment.yml`.

### `test_orbit` skips on a fresh clone
It needs `outputs/_orbit_data/tle_35946.txt` and `de421.bsp`, which are gitignored. Add a fixture or a
documented bootstrap.

## Tacoma scene (only if Tacoma is used radiometrically)

### Radiometric seam at the mesh edge
Water from the 20 km BOX is ~1.6 times brighter than in-mesh water. Suspected: the matid 3005 texture map
sampled with the BOX's own UVs. Not verified. Use in-mesh pixels or characterise it first.

### NIR coverage
`lt_blue_panel.ems` ends at 0.78 µm, `orange_panel` and `dark_orange_panel` at 0.80 µm, and the ground maps
cover 0.4–0.7 µm only. DIRSIG's behaviour past a curve's end is unexercised.

### Hard shadows are exactly zero radiance
Under `SimpleRadiativeTransfer` (0.77 % of Tacoma pixels). Not checked against the DIRSIG docs.

## dirfm upstream (out of scope here; candidates for issues or patches)

### NewAtmosphere is unusable as shipped
Six attributes are never initialised under `_FrozenAttrs`, and `"Isacc"`/`"Distort"` are typos for
`"Isaac"`/`"Disort"`. Worked around in `atmosphere_patches.py`; `tests/test_atmosphere_patches.py` flags an
upstream fix.

### Plugin plumbing
`SPICEPlugin` requires three kernel paths. `PlatformSensorPlugin.prepare()` always regenerates platform,
motion and tasks. `write_files()` assumes a `PlatformSensorPlugin` (`UnboundLocalError: platform_plugin_idx`
otherwise). Worked around in `platform_ref.py`.

### Missing wrappers
`EarthGrid`; STK-report import (`source="stk_report"`); a quaternion orientation engine; `LookAt` with a
velocity-tracking `up`; a native SGP4 location engine.

### Numeric formatting
`PlatformPosition.add_entry` writes angles with `{:0.6f}` (π becomes 3.141593) and positions to 3 decimals.
This changed every pixel by ~1e-7. Suggested fix: `repr` or `{:.17g}`.

### Dead and silent paths
`DIRSIG.set_output_prefix` stores `_prefix` and nothing reads it. `SCENE._check_coverage` passes vacuously on
a `_fname` scene and looks like a pass.

## DIRSIG, to report to RIT

### `GROUND_PLANE` is documented as infinite and renders as a ~2 km square
The only trace is the `scene2hdf` warning "emulating with a limited, facetized representation".

### Native `sgp4` location engine does not apply UT1−UTC
33 m today (1.411 arcsec of Earth rotation), up to ~470 m at the 0.9 s IERS bound. Inferred from the fit; the
docs do not say.

### Direct viewing of point sources is DIRSIG4-only
`sources.html` lists it only under "Relevant Options (DIRSIG4 only)". DIRSIG5 point sources illuminate
surfaces and are not drawn.

## Housekeeping

### Notebook text cites FINDINGS.md
Markdown cells and printed output in the stage 01/02 (stage 01 also cites the retired run-spec guide), `tutorial_auror_scene`, `tutorial_tacoma_scene`, and
`vehicle_point_source` notebooks cite `FINDINGS.md`, which no longer exists at the repo root. Reword the cells
on each notebook's next re-execution; the code strings in the sidebar also print "FINDINGS".
