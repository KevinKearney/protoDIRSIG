# Backlog

The single to-do list for protoDIRSIG. Add an item any time; remove it when done or dropped (git history is the record). Each item is a `###` title and a short body, so the file imports into GitHub issues one to one; the group heading becomes the label.

Group **TBR** holds items whose resolution may require a change on the MANIFOLD side (run-spec schema, guides, registry, sensor-spec). protoDIRSIG records them and does not edit MANIFOLD documents itself.

## TBR (MANIFOLD-impacting)

### `--force_temperature_prediction` as a run-spec engine option
Default off; global. The reference render has the same black vehicle, and three notebooks and one test pin byte-identical renders. Enable only for scenarios with an intended hot emitter. Needs a decision, then an `engine.run` field or a `Simulation` option.

### Modeled window and per-sensor run specs: placement (TBR)
`roi` is a run-spec `settings` member and the generator writes it into the `.platform` (Detector_v02 treats it as commanded). Confirm with MANIFOLD, with C-18 (one run per sensor, no run-time override).

### Confirm the DeepScan values carried from auror-nir
`manifold_sensors/deepscan_850_306_nir_1280.yaml` copies optics (85 mm, 306 mm, f/3.6), throughput 0.875, shutter, ADC depth 14, fill factor 1.0, band width, reference frame, and mount from `auror-nir`. Confirm against the DeepScan design and the SCION datasheet. Remaining null: Teledyne part number. Its QE is `synthetic_visgaas`.

### `engine.platform.output_prefix: auror_nir_` is not applied
Applying it renames the outputs and breaks reproduction of the tree. It appears in no file in the tree, so it looks like an authoring choice in the YAML. Settle with MANIFOLD.

### Three resolution roots, one rule
Engine assets resolve against `manifold_config_repo/`, the sensor ref against `manifold_sensors/`, motion and tasks are generated. A run spec may carry the sensor as a ref or inline; which form the registered descriptor carries is C-21.

### Strict loader and canonical hashing (MANIFOLD registry side)
Unknown keys are rejected at admission (the run-spec schema) and canonical-JSON hashing (RFC 8785) gives run ids, both SDK-side; duplicate-key rejection is not built (the loader is plain `yaml.safe_load`, which keeps the last value), and whether the registry's hash equals the run id is MANIFOLD's (C-12). `content_hash` is the sha256 of file bytes (`scripts/stamp_hashes.py`), verified when stamped; a `.scene` ref is not stamped, since geometry and materials sit beside it. Replace the stamp with the registry's hash.

### Compile-once
`submit` then `run()` runs `scene2hdf` twice. Irrelevant for one job, material for sweeps.

### `run_info.json` is not a complete plugin record
`plugin_list` lists only `NewAtmosphere` and `BasicPlatform`; `SpiceEphemeris` and `ThermWeather` are missing. Do not use it as the provenance record of plugins.

### `--threads` in `engine.run`
Not exposed. Add before MANIFOLD schedules concurrent DIRSIG jobs on shared hardware.

### Generalize `resolve_run`
It accepts only `new_atmosphere`, ephemeris `spice`, weather `library`, one scene, and `static` or `orbit` motion. `four_curve` and others fail with a specific `RunSpecError`. The NewAtmosphere backend recipe (MODTRAN tape, `Isaac`) has no run-spec field and is fixed in `AUROR_ATMOSPHERE_BACKEND`.

### Moving-platform pass: what remains (C-05)
The ground-imaging pass is built (`engine.motion` kind `orbit`, CONOPS §3.2; `recipes/leo_pass_tahoe.yaml`, three 16 x 16 frames with an independent ground-track check). Remaining: a form for DIRSIG's native `sgp4` location engine, if one is wanted, with its recorded 33 m difference from the UT1-corrected track (it applies no UT1 - UTC; see the item below); an authored `waypoints` form; frame count, ROI and runtime beyond 16 x 16 (a 500 x 500 frame takes about 7 minutes), where compile-once (C-07), threads (C-08) and parallel sweeps become the cost drivers; deciding whether polar motion is applied (the tables' refresh is its own item); per-frame truth products beyond the GeoLocation and Intersection collectors of the pass template. MANIFOLD's answers on the descriptor form and on indexing derived time-varying geometry (C-05) may add descriptor work.

### Space-object imaging against space (after the pass)
An observer imaging a space object against space: star field (no streamlined support in DIRSIG; a flux-matched finite emitter, or compositing from the truth cube), space background, relative target motion, probably a different scene. A separate design problem; C-05 scopes it out until this item is taken.

## Sensor model

### Real QE and optics data
Import the Teledyne SCION curve with `scripts/import_curve.py` (`--provenance vendor_typical` or `measured`, `--pad-zero-to 0.150,14.000`; its ~0.3-1.7 um range does not cover the job's 0.41-2.0 um bandpass), point `deepscan_850_306_nir_1280.yaml`'s `qe_reference` at it, update `qe_peak`, and restamp. State in `--source` whether the quoted QE includes the die window or microlens. Likewise `synthetic_silicon` and `synthetic_vis_lens` if a real VIS sensor replaces the invented one.

### Received AUROR_ref radiometry carries a 0.399 factor
Its native gaussian channel peaks at 1/√(2π) (CONOPS section 9). Decide whether `auror_ref.yaml` stays `native` (reproduces the tree) or moves to `tabulated` (unit peak) and its reference renders are regenerated.

### Generator scope
One sensor entry, one focal plane, one `settings` member per job (refused otherwise at resolution); several channels per focal plane are generated. Not generated, and refused when a sensor-spec asks for them: a non-identity mount (needs the quaternion-to-`<mount>` convention, and `axis_convention` is unconfirmed), lens distortion, a mosaic `channel_layout` (DIRSIG `<channelpattern>`), a rolling shutter (DIRSIG `detectorarray@rollingreadout`, seconds per line, which the sensor-spec does not carry), a `timestamp_reference` other than `exposure_start`. Not written and not refused: `AdcBitDepth` (DIRSIG quantizes only in `<detectormodel>`, which also needs full well, read noise and dark current, none of them modeled), image flips (`x/yflipaxis`; no sensor-spec field), and `DeviceVendorName`/`DeviceModelName` (no DIRSIG element; platform metadata is free text). Instrument and focal plane names, truth collections, spatial response (PSF) and hypersampling stay as the template has them. `throughput_in_band` is checked against the optics curve only in the tests. Beam-split optical paths and `.platform` noise models are not generated.

### `split_channels: true` with `new_atmosphere`
Refused at resolution: the AUROR database has no per-channel spectral states, and the render fails after the dry run passes. A database built for the per-channel states would lift it; `tests/test_sensor_render.py` flags when the render succeeds.

### Spectral grid
Synthetic curves are 1 nm over 0.150-14.000 µm; imported curves keep their source grid. Channels are tabulated on the template's 0.41-2.0 µm bandpass; a sensor needing the UV or LWIR needs a template with that bandpass and scene and atmosphere data to match.

## SDK and run-spec engine

### Sweeps and layers: what remains after the sensor axis
Sweeps exist over the sensor axis only (CONOPS §3.5). Remaining: a grid over other axes (exposure, epoch, geometry), with grid versus zip decided per axis and the run cap applied to the product; a compiled-scene cache keyed by scene hash, so the runs of a sweep that share a scene compile it once (with compile-once); and splitting scene-specific from engine-general engine-profile content, now that the AUROR and VIS profiles are one file with a recipe override.

### SDK API: after phase 2b-3 (`api/`)
`api/` states the SDK API (`sdk-api/1`, proposed); `Workspace` over `LocalBackend` implements every operation for the local case, and what departs from the contract is listed in `api/operations.md`. `LocalRegistry` is deprecated (a DeprecationWarning points to `Workspace`) and is removed in phase 3, once the notebooks use the facade. The run-spec schemas leave some members open (`collection.platform`, `field`, `settings[].binning`; engine `motion` kind `waypoints`, the `four_curve` and `basic` atmospheres, `weather.source: install`) until the MANIFOLD vocabulary or a run defines them. Re-execution of an identical spec stays out of `sdk-api/1`.

### SDK API: the REST server and `RemoteBackend` (phase 3)
A REST server over `LocalBackend` (each call returns the wire form already) and `RemoteBackend`, a client generated from `api/openapi.yaml`, run against `tests/backend_conformance.py`; download URLs for artifact references.

### `LocalBackend` on Windows and other non-POSIX hosts
The run store and the worker use `fcntl` locks, `/proc` and process groups (`start_new_session`, `killpg`), so `LocalBackend` runs on POSIX hosts only. A port needs another lock, a process-liveness check and a way to terminate a worker's children.

### Streaming large artifacts
`get_artifact` reads the whole file into memory. Large images or truth cubes need a streamed read (and a range read over REST).

### Work-root clean-up
Run records are identity-keyed results, not a cache, so the default work root is in the state directory (`$XDG_STATE_HOME/protodirsig/work`, else `~/.local/state/protodirsig/work`); a former default under `~/.cache/protodirsig/work` is left in place and `Workspace.local` warns once when it exists and the new root is empty. Runs stay in `<work_root>/runs/` for ever (about 34 MB per Tahoe run: the job's atmosphere copy and compiled scene HDF beside the outputs). Decide a retention policy (by age, by state, or keep outputs and drop `input/`) and whether a deleted run's id may be resubmitted.

### Documentation site
A readthedocs-style site generated from `api/` (the operation table, schemas, OpenAPI document) and the SDK's docstrings (R-11 in `api/requirements.md`). The generator is chosen in phase 2, with the facade class whose docstrings it renders.

### Earth-orientation tables expire 2027-01 (refresh dated 2027-01)
`manifold_config_repo/orbit/iers.npz` is a copy of skyfield 1.54's bundled UT1 - UTC tables, covering January 2027; a skyfield upgrade that changes its bundled file fails `test_library_eop_copy_is_the_bundled_tables`. Refresh before 2027-01: recopy, restamp, recompose. The refresh changes the file's hash and therefore the run id of the pass, by design. Add the refresh as a `scripts/bootstrap.py` step.

### `AurorNIRDetectorPass` forks `AurorNIRDetector`
The pass template is the AUROR NIR template with per-capture image and truth schedules and an Intersection collector. Fold the per-capture output option into one template (or into `platform_gen`), so the two copies cannot drift. Risk: the AUROR reference job reproduces the received platform file byte for byte (`channel_response: native`), and a merged template must keep that output identical; test the merge against the received file before replacing either template.

### Multi-focal-plane generation
`platform_gen` renders one focal plane per run (C-19). A rig whose entries image the same instant needs one `.platform` with several focal planes and one run with several `settings` members. Build it when a run needs a co-boresight rig, and after MANIFOLD answers C-19.

### Release repo plan
Cut the validated SDK, tests, and notebooks into a new repository under formal change control. Strip `.claude_mem/`, `notebooks/dev/`, and `prompt.md`; carry `docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md`.

## Vehicle (URSO) and radiometry

### A/B validation of the distilled intensity
Render the real mesh with `Gidder_mat_reflective` (thermal off) against the same seed without it, and compare the added signal with the +0.0115 prediction. A match validates I = 67.0 W/(sr µm). A flux-matched `::IMPORTANT::` emitter (radiance × area = I) is the DIRSIG5 route to a rendered unresolved object.

### Decide what the sandbox target demonstrates
The true-size reflective vehicle is a ~1 % excess, below terrain pixel-to-pixel variation. The 1500 K emitter is detectable (~6σ over the block). A reflective unresolved object needs a dark background or a much larger or brighter object.

### Emitter residual
Rendered +0.56 against predicted +0.51 (10 %), with no stated uncertainty. Quantify against the block noise before quoting either number.

### Two unexplained DIRSIG5 source behaviours
A source scaled 10⁹ times changed nothing at 50 km. The same source on a static instance zeroed the whole close-pass image. Low priority; neither affects a current result.

### LightCurve cross-check (optional)
Independent magnitude-vs-time check of the distilled intensity. Incompatible with `new_atmosphere`; needs its own BasicAtmosphere/SimpleAtm job.

### Atmosphere database is for a different site
The AUROR database was built for western NY (43.12 N, −78.45, 250 m; stored sun zenith 36.24°, azimuth 238.56°), not Tahoe (21.50 / 155.52). The tasks reference time (2009-07-27 11:29:32-08:00) is stale and labels a July date PST. Rebuild the database for the site if absolute radiometry is ever needed.

## Notebooks and tools

### Image viewer for DIRSIG ENVI output
DS9 cannot read the ENVI `.img` + `.hdr` (float64, BIP). Build a pyqtgraph viewer (ImageView, ROI, mouse-move truth readout) as an optional `[viewer]` extra behind `protodirsig-view`. Stage A: ENVI loader plus a tested shared ROI-excess function. Stage B: the viewer. Run-vs-run difference is kept while validation continues.

### `tutorial_orbit_to_ground` Stage 3
Final render and comparison. The notebook status still reads "in progress".

### `tutorial_tacoma_scene` calls the old `orbit` API
Its Stage 1 calls `orbit.find_passes`, `choose_pass`, `pass_epoch`, `propagate` and `check_teme_to_itrs` with skyfield objects; those now take and return plain values (`orbit.Pass`, `orbit.Trajectory`). Its stored outputs stand; re-executing it needs that cell moved to the new calls, as `scripts/crosscheck_sgp4.py` was.

### New-user notebooks
A short path for a new user of `dirfm` and then the SDK, built from the existing tutorials and stage notebooks. Define the path before writing anything new.

### Motion notes in `docs/dirsig_motion_temporal.md`
Kevin's DIRSIG motion notes. Contains errors (direct point-source viewing; targeted oversampling). Correct the errors or delete the file once its content is absorbed into the CONOPS.

## Tests and environment

### Notebooks and tests still assume sibling checkouts and `~/DIRSIG`
Notebook first cells set `DIRSIG_HOME` and locate `dirfm` by home-relative paths. Switch them to `external/` (the `dirsig` link and `dirsig-file-maker`) so the bootstrap is the only setup step, as `stage_03_sensor_sweep` does. Tests still fall back to `~/DIRSIG/<version>`.

### Placed demo layers marked "does not validate yet"
A layer file whose header comment (its text before the first blank line) contains "does not validate yet" is placed in the library but does not resolve yet (today the PointCollectors2 demo's recipe, scenario and engine profile). `library.file_status` reads the marker and the library listings surface it as `status: does-not-validate-yet`. Two test conventions depend on it: `tests/test_compose.py` skips such a recipe (`_resolvable`) in the test that resolves every one-run recipe, and `tests/test_import_boundary.py` filters out generated specs composed from such a recipe in the engine-free validation test. Remove the marker from a demo's layers when they validate, and the skip and filter then cover it again.

### Library assets: what remains after the manifest
`manifold_config_repo/assets.json` and `scripts/bootstrap.py assets` place and verify assets from zip members of the linked DIRSIG install (the demos). Remaining: decide LFS versus a content-addressed store for assets that are not demos (acquired scenes and databases over about 50 MB); source kinds beyond `zip` (a directory in the install, such as the Tacoma and HarvardForest scenes, and an artifact store URL for acquired assets); a gitignored layer overlay for demo values that cannot be committed (sensor, pose, epoch: see the coverage document's first-demo findings). Each new scene also needs a matched atmosphere database, weather file and platform.

### Pass-through follow-ups (proposed form)
The pass-through form runs a demo directory as authored (CONOPS section 3.2). Follow-ups: the `dry_run` level runs `dirsig5 --dry_run` on a copy of the directory, which still compiles the scene and builds caches, so it is not cheap (Brdf1's attempt spent most of 210 s there); decide whether validation should stop after the scene compile. The opaque descriptor (C-25) carries nothing indexable; decide with MANIFOLD whether a pass-through run is registrable, or whether a descriptor can be extracted from the demo's files at bootstrap (licensing permitting). Artifact media types come from extensions only (ENVI `.img` is `application/octet-stream`); a header-aware type would help viewers. Frames are absent: a pass-through output is not split per capture; extracting frames would need the DIRSIG log (`--log_info_filename`), which the runner does not request yet. DIRSIG writes material caches to the user's DIRSIG cache directory, outside the run directory; set `DIRSIG_CACHE_DIR` per run if a run must not share state. A demo whose inputs are not all in its archive (Brdf1's NewAtmosphere database) fails as authored; record such demos rather than patching them.

### Licensed-value overlay (not built)
Expressing a demo in layers needs its camera, epoch and pose, which live only in its licensed files: the planned overlay (`scripts/derive_demo_layers.py` writing a gitignored `demo-<name>.licensed.yaml` scenario at bootstrap) was not built this round, because its first user, Brdf1, has no reference run. Limits known in advance: only values stated mechanically in the demo's XML can be derived; a committed recipe that names a gitignored scenario does not compose in a fresh clone until bootstrap runs, so it stays marked "does not validate yet" there; and the overlay's digests change if DIRSIG ships a different demo.

### Loader features for demos, ranked by what the reference runs showed
1. BasicAtmosphere `.atm` with uniform radiative transfer: unlocks 31 `near` demos (50 need it), and PointCollectors2, which needs it, now has a cheap deterministic reference run (about 6 s, identical digests twice), so a layered PointCollectors2 can be compared pixel for pixel as soon as this and a platform form exist.
2. A platform form for demo platforms: a demo's own `.platform` is not a platform_gen template (PointCollectors2's lacks `temporalintegration`); either a template-compatible variant or a pass-through-platform mode in the layered form.
3. BasicAtmosphere `.atm` with simple radiative transfer: 26 `near` demos, 78 need it.
4. BasicAtmosphere `.atm` with classic radiative transfer: 5 `near`, 11 in all. Items 1, 3 and 4 are one loader feature with three forms.
5. FourCurveAtmosphere: 3 `near`, 5 in all.
6. Uniform weather without a ThermWeather file: 2 `near`, 5 in all. Dropped from second place: its leading demo, Brdf1, has no reference (its NewAtmosphere database is missing from the archive), so a layered Brdf1 could not be compared.

### Compare layered demos with their pass-through references
For each demo with a pass-through reference (`docs/DIRSIG_demo_reference_runs.md`; today PointCollectors2), render the layered recipe at the demo's native size and compare with the reference: shape, per-band mean, maximum absolute difference and the fraction of pixels differing, listing every known input difference (platform template, sensor stand-ins, atmosphere, seed). The pass criterion stays byte equality at the same seed, region of interest and DIRSIG version, or a stated tolerance; the reference is the pass-through run, kept outside git.

### CI job
Run `scripts/bootstrap.py status`, then the test suite, on a clean clone. Needs a runner with a DIRSIG install or a container image that has one.

### Dangling citations in the MANIFOLD documents
`AD_MANIFOLD_Architecture_Description_v02` and `AV_MANIFOLD_Configuration_v02` cite deleted documents (`review/TRIAL_2026-10-06_dirsig-container.md`, `ROLE_PROPOSAL_2026-10-05.md`, `MANIFOLD_Gap_Analysis_and_Project_Plan`, and the folded A&T analyses). Recoverable from eopticDocs git history; the MANIFOLD team decides whether to reword the citations.

### pytest is not installed in the `protodirsig` env
Every stage ran it from a scratch `--target` install. Declare the `dev` extra in `environment.yml`.

## Tacoma scene (only if Tacoma is used radiometrically)

### Radiometric seam at the mesh edge
Water from the 20 km BOX is ~1.6 times brighter than in-mesh water. Suspected: the matid 3005 texture map sampled with the BOX's own UVs. Not verified. Use in-mesh pixels or characterise it first.

### NIR coverage
`lt_blue_panel.ems` ends at 0.78 µm, `orange_panel` and `dark_orange_panel` at 0.80 µm, and the ground maps cover 0.4–0.7 µm only. DIRSIG's behaviour past a curve's end is unexercised.

### Hard shadows are exactly zero radiance
Under `SimpleRadiativeTransfer` (0.77 % of Tacoma pixels). Not checked against the DIRSIG docs.

## dirfm upstream (out of scope here; candidates for issues or patches)

### NewAtmosphere is unusable as shipped
Six attributes are never initialised under `_FrozenAttrs`, and `"Isacc"`/`"Distort"` are typos for `"Isaac"`/`"Disort"`. Worked around in `atmosphere_patches.py`; `tests/test_atmosphere_patches.py` flags an upstream fix.

### Plugin plumbing
`SPICEPlugin` requires three kernel paths. `PlatformSensorPlugin.prepare()` always regenerates platform, motion and tasks. `write_files()` assumes a `PlatformSensorPlugin` (`UnboundLocalError: platform_plugin_idx` otherwise). Worked around in `platform_ref.py`.

### Missing wrappers
`EarthGrid`; STK-report import (`source="stk_report"`); a quaternion orientation engine; `LookAt` with a velocity-tracking `up`; a native SGP4 location engine.

### Numeric formatting
`PlatformPosition.add_entry` writes angles with `{:0.6f}` (π becomes 3.141593) and positions to 3 decimals. This changed every pixel by ~1e-7. Suggested fix: `repr` or `{:.17g}`.

### Dead and silent paths
`DIRSIG.set_output_prefix` stores `_prefix` and nothing reads it. `SCENE._check_coverage` passes vacuously on a `_fname` scene and looks like a pass.

## DIRSIG, to report to RIT

### `GROUND_PLANE` is documented as infinite and renders as a ~2 km square
The only trace is the `scene2hdf` warning "emulating with a limited, facetized representation".

### Native `sgp4` location engine does not apply UT1−UTC
33 m today (1.411 arcsec of Earth rotation), up to ~470 m at the 0.9 s IERS bound. Inferred from the fit; the docs do not say.

### Direct viewing of point sources is DIRSIG4-only
`sources.html` lists it only under "Relevant Options (DIRSIG4 only)". DIRSIG5 point sources illuminate surfaces and are not drawn.

## Housekeeping

### `vehicle_point_source` stored output still prints "FINDINGS"
Cell sources no longer cite `FINDINGS.md`. Two printed lines in the sidebar's saved output still end with "FINDINGS … expected +0.49"; they go away when the notebook is next re-executed.
