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
Partly addressed: a run can now request a thread count through the run spec's `resources.cpu_threads` (`built / proposed`, `tests/test_resources.py`; DIRSIG honors it with `--threads`; it enters the run id when stated, C-30), and the engine block itself still has no thread member (C-08). The determinism probe's reason stands: at the default thread count a demo's radiance can differ between runs of one spec, and one thread made every probed repeat bit-identical (3.1 to 3.7 times slower; `docs/DIRSIG_determinism.md`). Decide with MANIFOLD whether the request belongs in `resources` or `engine.run` (C-08, C-28, C-30).

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
`api/` states the SDK API (`sdk-api/1`, `built, partial / internal`: no REST server or `RemoteBackend` yet, `tests/test_local_backend.py`); `Workspace` over `LocalBackend` implements every operation for the local case, and what departs from the contract is listed in `api/operations.md`. `LocalRegistry` is deprecated (a DeprecationWarning points to `Workspace`) and is removed in phase 3, once the notebooks use the facade. The run-spec schemas leave some members open (`collection.platform`, `field`, `settings[].binning`; engine `motion` kind `waypoints`, the `four_curve` and `basic` atmospheres, `weather.source: install`) until the MANIFOLD vocabulary or a run defines them. Re-execution of an identical spec stays out of `sdk-api/1`.

### SDK API: the REST server and `RemoteBackend` (phase 3)
A REST server over `LocalBackend` (each call returns the wire form already) and `RemoteBackend`, a client generated from `api/openapi.yaml`, run against `tests/backend_conformance.py`; download URLs for artifact references.

### `LocalBackend` on Windows and other non-POSIX hosts
The run store and the worker use `fcntl` locks, `/proc` and process groups (`start_new_session`, `killpg`), so `LocalBackend` runs on POSIX hosts only. A port needs another lock, a process-liveness check and a way to terminate a worker's children.

### Streaming large artifacts
`get_artifact` reads the whole file into memory. Large images or truth cubes need a streamed read (and a range read over REST).

### Work-root clean-up
Run records are identity-keyed results, not a cache, so the default work root is in the state directory (`$XDG_STATE_HOME/manifold/work`, else `~/.local/state/manifold/work`); the pre-rename default `~/.local/state/protodirsig/work` and a former default under `~/.cache/protodirsig/work` are left in place, and `Workspace.local` warns once about each when it exists and the new root holds no run (the first warning gives the `mv` command). Runs stay in `<work_root>/runs/` for ever (about 34 MB per Tahoe run: the job's atmosphere copy and compiled scene HDF beside the outputs). Decide a retention policy (by age, by state, or keep outputs and drop `input/`) and whether a deleted run's id may be resubmitted.

### Documentation site
A readthedocs-style site generated from `api/` (the operation table, schemas, OpenAPI document) and the SDK's docstrings (R-11 in `api/requirements.md`). The generator is chosen in phase 2, with the facade class whose docstrings it renders.

### Earth-orientation tables expire 2027-01 (refresh dated 2027-01)
`manifold_config_repo/orbit/iers.npz` is a copy of skyfield 1.54's bundled UT1 - UTC tables, covering January 2027; a skyfield upgrade that changes its bundled file fails `test_library_eop_copy_is_the_bundled_tables`. Refresh before 2027-01: recopy, restamp, recompose. The refresh changes the file's hash and therefore the run id of the pass, by design. Add the refresh as a `scripts/bootstrap.py` step.

### `AurorNIRDetectorPass` forks `AurorNIRDetector`
The pass template is the AUROR NIR template with per-capture image and truth schedules and an Intersection collector. Fold the per-capture output option into one template (or into `platform_gen`), so the two copies cannot drift. Risk: the AUROR reference job reproduces the received platform file byte for byte (`channel_response: native`), and a merged template must keep that output identical; test the merge against the received file before replacing either template.

### Multi-focal-plane generation
`platform_gen` renders one focal plane per run (C-19). A rig whose entries image the same instant needs one `.platform` with several focal planes and one run with several `settings` members. Build it when a run needs a co-boresight rig, and after MANIFOLD answers C-19.

### Remove the `protodirsig` compatibility shim
`packages/compat-protodirsig` maps the pre-rename import paths to `manifold.core`, `manifold.sim` and `manifold.engines.dirsig` (facade modules `protodirsig._split.*` for the former modules whose names now live in more than one place) and warns on import. Keep it for one release after MANIFOLD adopts the `manifold` packages, then delete the distribution, `tests/test_compat_shim.py` and `tests/data/protodirsig_public_names.json`, and the legacy fallbacks in `manifold.core._names` (the `PROTODIRSIG_*` environment variables, the pre-rename state directory warning, the `protodirsig.worker` command line the store still recognizes in old run records).

### Publishing and the internal index policy
The distributions (`eoptic-manifold-core`, `eoptic-manifold-sim`, `eoptic-manifold-engine-dirsig`, and while it lasts `protodirsig`) are installed editable only. Decide the internal package index, who may publish, the version policy (lockstep today, 0.0.1), how wheels carry the contract schemas (`packages/core/setup.py` for run-spec and sensor-spec, `packages/engine-dirsig/setup.py` for `dirsig-engine/1`), how `dirfm` (not on any index) reaches an engine wheel's installation, and that a resolver never consults the public index for a `manifold` name (a public PyPI project named Manifold exists; the `eoptic-` prefix avoids the collision for installs by name, not for a misconfigured index).

### Rename the repository directory (user's action)
The repository directory is still `protoDIRSIG`, and so are the conda environment and Jupyter kernel names (`protodirsig`, `environment.yml`, README). Renaming them is outside the code: no path in the code or tests depends on the directory name. YAML comments in the layer, sensor and vector files still cite the "protoDIRSIG CONOPS and Guide"; editing them changes the stamped `content_hash` of sensor files (not any run id), so do it with `scripts/stamp_hashes.py` and `scripts/compose.py` in one change.

### Execution record member `protodirsig_version`
`execution.json` records the SDK version under the pre-rename key (`manifold.core._names.RECORD_VERSION_KEY`); the value is now the `eoptic-manifold-sim` version. Rename it to a neutral key with the next change of the record's schema; it is not hashed and no id depends on it. No other name-derived string reaches hashed content (round 17 audit; `tests/test_id_snapshot.py`).

### Descriptor audit with two engines (first)
DIRSIG and SatSim are both registered now (SatSim in the pass-through form, `docs/SatSim_reference_run.md`). Audit the descriptor against both engines' needs (the SatSim mapping in `docs/SatSim_probe.md`, the gaps item below, and DIRSIG's engine block), and write the MANIFOLD questions that follow (C-37 asks about opaque descriptors meanwhile), before any layered SatSim form is designed.

### `descriptor_id` (second)
An id for the descriptor alone, the engine-independent part of a run spec, beside the run id: two runs that describe the same observation (two engines, or one engine with another seed or engine profile) would share it, so results can be related and searched by observation. Define what it hashes (the descriptor with or without `meta`, `fidelity`, `extras`; an opaque descriptor has none to give) after the audit, as a MANIFOLD question.

### Layered SatSim (third)
A layered form of `satsim-engine/1`, composed from the descriptor and a SatSim engine profile as DIRSIG's layered form is, after the audit decides what the descriptor holds. The composer's pass-through form is DIRSIG-shaped today (a demo directory and a simulation file), which is why the SatSim run spec is written whole (`manifold_run_specs/satsim/`); generalize compose's pass-through form per engine with it.

### SatSim GPU follow-up (fourth)
Repeat the probe on a GPU machine with the checklist at the end of `docs/SatSim_probe.md`: device selection (`--device`, `--memory`, `--jobs`), wall time and host and GPU memory against the CPU numbers, and repeatability with global seeds on GPU and against CPU (with and without `TF_DETERMINISTIC_OPS=1`). Until then the adapter refuses any `device` other than `cpu` and any GPU request ("SatSim GPU behavior is unverified").

### SatSim: what remains of seeds, assets and catalogs
The launcher always seeds Python, numpy and TensorFlow from the run spec's required `seed` (byte-identical repeats on CPU); ask upstream for a seed option so the `satsim` command can repeat too. The ephemeris and a dated IERS snapshot are pinned assets (`external/pins.json`); decide how a snapshot is refreshed and archived (it cannot be fetched again from its URL; C-36; today's snapshot is committed at `external/snapshots/finals2000A.all` and restored offline by `bootstrap.py assets`), and make star catalogs (`SATSIM_SSTR7_PATH`, `SATSIM_GCVS5_PATH`, `geometry.stars.path`) directory assets, which today a single-file configuration may not name at all.

### Descriptor gaps found by the SatSim mapping
Of 32 SatSim configuration concepts, 3 map cleanly onto the descriptor, 11 with a conversion and 18 have no home (`docs/SatSim_probe.md`). The consequential gaps: targets (only a class; no trajectory or brightness), observer motion and pointing (a geodetic position and a governed term; no orbit, track mode or field rotation), detector noise and the radiometric scale (`sensor-spec/1` has no dark current, read noise, full well or PSF; SatSim takes a photometric zeropoint). Also without a home: frame count and collect duration, the star field and catalog, sky brightness and clouds as numbers, product requests, Monte Carlo sets, a seed. Decide which belong in the descriptor (MANIFOLD questions) and which in a `satsim-engine/1` block.

### Resource slots: what remains
Built in round 18 (`built / proposed`, `tests/test_resources.py`): typed slots in `manifold.core.resources`, the `resources` member of a run spec, admission against the declaration and the backend's capacity, a flock'd reservation ledger in `LocalBackend` for threads, memory and GPU devices, and GPU allocation tested against stub capacities. What remains: a backend that advertises real GPUs (device discovery, `CUDA_VISIBLE_DEVICES` through the plan's `gpu_variable`), and SatSim's GPU options measured (see the GPU follow-up); memory is reserved, not enforced (no cgroup limit); a run waits for its reservation in state `running`, after its `max_parallel` slot; MANIFOLD's answer on slots and the run id (C-30).

### Artifact roles: the vocabulary
`artifact_ref` carries a role and a run status its verdict (round 19, `built / proposed`, `tests/test_artifact_roles.py`; initial roles `product`, `truth`, `preview`, `log`, `config`, `metadata`, a free vocabulary). Settle the vocabulary and its owner with MANIFOLD (C-34); a layered DIRSIG run's generated input files are not listed as `config` artifacts yet.

### Partial artifacts of a cancelled DIRSIG run
Since round 21 the worker handles the SIGTERM of a cancel: it stops the engine's process group, runs the adapter's collector and lists what it reports (SatSim's frames, the dummy engine's), with the verdict `incomplete`. Left: DIRSIG's collector reports nothing without the runner's `engine_result.json`, so a cancelled DIRSIG run still lists only `run_spec.json`, although a pass-through run's outputs are in its folder; a collection mode that reports whatever exists, with roles, is a change to the adapter protocol in `manifold.core` and to the DIRSIG adapter. Also: the backend waits 10 s for the worker, so a cancelled run whose collection hashes many large files is cut off and lists only `run_spec.json`; a size-aware bound would fix it.

### A network sandbox for runs
`LocalBackend` refuses network requests at admission and, for an engine that declares network use, points the proxy variables at a closed port; it does not isolate the process (unprivileged user namespaces are restricted on the development host). Decide on a real sandbox (a network namespace, a container) before an engine that downloads at run time is admitted.

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
DS9 cannot read the ENVI `.img` + `.hdr` (float64, BIP). Build a pyqtgraph viewer (ImageView, ROI, mouse-move truth readout) as an optional `[viewer]` extra behind a `manifold-view` entry point. Stage A: ENVI loader plus a tested shared ROI-excess function. Stage B: the viewer. Run-vs-run difference is kept while validation continues.

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

### Pass-through follow-ups (`built / proposed` form, `tests/test_passthrough.py`)
The pass-through form runs a demo directory as authored (CONOPS section 3.2). Follow-ups: the `dry_run` level runs `dirsig5 --dry_run` on a copy of the directory, which still compiles the scene and builds caches, so it is not cheap (Brdf1's attempt spent most of 210 s there); decide whether validation should stop after the scene compile. The opaque descriptor (C-25) carries nothing indexable; decide with MANIFOLD whether a pass-through run is registrable, or whether a descriptor can be extracted from the demo's files at bootstrap (licensing permitting). Artifact media types come from extensions only (ENVI `.img` is `application/octet-stream`); a header-aware type would help viewers. Frames are absent: a pass-through output is not split per capture; extracting frames would need the DIRSIG log (`--log_info_filename`), which the runner does not request yet. DIRSIG's material caches now land in a per-run `HOME` (round 15), so a pass-through run shares no cache state; layered runs (`dirfm`) still use the user's cache. A demo whose inputs are not all in its archive (Brdf1's `demo.jsim` and its NewAtmosphere database) fails as authored; record such demos rather than patching them. The recipe `demo_brdf1_passthrough` now names `demo.sim` (run id `909394b77e55...`, was `5bd1d5684b7f...` with `demo.jsim`); rerun `scripts/run_demo.py Brdf1 --repeat` to replace the reference-runs row, which still records the `demo.jsim` failure.

### Licensed-value overlay (not built)
Expressing a demo in layers needs its camera, epoch and pose, which live only in its licensed files: the planned overlay (`scripts/derive_demo_layers.py` writing a gitignored `demo-<name>.licensed.yaml` scenario at bootstrap) was not built in round 14, because its first user, Brdf1, then had no reference run (the demo sweep has since rendered Brdf1's `demo.sim`, so it has one now). Limits known in advance: only values stated mechanically in the demo's XML can be derived; a committed recipe that names a gitignored scenario does not compose in a fresh clone until bootstrap runs, so it stays marked "does not validate yet" there; and the overlay's digests change if DIRSIG ships a different demo.

### Loader features for demos, ranked by the demo sweep
Ranked by how many of the coverage survey's `near` demos each feature would make expressible in layers and that now have a deterministic pass-through reference to compare against (`docs/DIRSIG_demo_sweep.md`, "Layered-comparison candidates"; counts are near / with a reference / with an identical repeat). The counts below are from the survey before items 1 and 4 were built. Regenerated in round 23 with them and with the files a `.scene` names beside it placed in the job ("Tagged demos" item 11; `docs/DIRSIG_demo_coverage.md`): 38 demos `ready`, 52 `near`; the features that alone would make the most `near` demos expressible are now simple radiative transfer (30), classic radiative transfer (10), FourCurveAtmosphere (4) and uniform weather without a ThermWeather file (3). Regenerated in round 24 with two files DIRSIG looks for in the working folder counted as missing ("Files DIRSIG looks for in the working folder" below): 35 `ready`, 53 `near`; simple radiative transfer (28), classic (10), FourCurveAtmosphere (4), uniform weather without a ThermWeather file (3). Item 2 built in round 24: 63 `ready`, 47 `near`, 40 `far`; next by the same count, classic radiative transfer (10), several instruments or focal planes (5), then a simulation options file, files the platform names and FourCurveAtmosphere (4 each). Regenerated in round 25 with the working-folder files the job now places counted as covered and material files DIRSIG finds only from the working folder counted as missing: 65 `ready`, 44 `near`, 41 `far`.
1. BasicAtmosphere `.atm` with uniform radiative transfer: 31 / 31 / 27; the cheapest references take about 4 s (DensityMap1, MaterialMap1) and PointCollectors2 6 s. Built in round 22 as `engine.atmosphere.uniform` (uniform radiative transfer, uniform weather from an installation weather file, an optional fixed Sun; CONOPS section 3.2); what remains is items 2 and 3, turbulence and lunar values.
2. BasicAtmosphere `.atm` with simple radiative transfer: 26 / 23 / 15 (DeltaMotion1, BumpMap2 and BundledMaterials1 at about 4 s). Built in round 24 as `engine.atmosphere.simple` (DIRSIG's SimpleAtm: the apparent sky temperature, with the uniform form's weather and optional fixed Sun; CONOPS section 3.2, C-41); DeltaMotion1's layered render is byte-identical to its same-seed pass-through render. Round 25, a thermal band: DataDrivenTempSolver1 (8 to 12 um) is byte-identical once the epoch's written form and the Euler angles are restored, and its sky pixels hold the Planck radiance at the stated value in kelvin (`docs/DIRSIG_layered_comparison.md`). Turbulence and lunar values remain (as for item 1).
3. BasicAtmosphere `.atm` with classic radiative transfer: 5 / 4 / 2 (Balfour1 at about 4 s).
4. A platform form for demo platforms: a demo's own `.platform` is not a platform_gen template (PointCollectors2's lacks `temporalintegration`); every layered comparison above needs it, so it ranks with item 1 in practice. Built in round 22 as `engine.platform.as_authored` (the file by ref and hash, copied as it is). The other form is "A demo camera as a sensor-spec" below.
5. FourCurveAtmosphere: 3 / 3 / 2 (CurveMap1 at about 4 s).
6. Uniform weather without a ThermWeather file: 2 / 1 / 1 (Brdf1 through `demo.sim`, 204 s; Brdf1's `demo.jsim` needs a missing database).

### A demo camera as a sensor-spec
The form of a demo platform not chosen in round 22 (`engine.platform.as_authored` was): `platform_gen` writes an electron image from a template plus a sensor-spec; a demo camera states radiance (`fluxunits="watts"`, `areaunits="cm2"`), a rectangular or gaussian `normalize="true"` channel, sub-element spatial sampling and flips. Needs an image-units member (or a template per unit) and values that, for a licensed demo, can only be derived at bootstrap into a gitignored layer (the licensed-value overlay). It would make the descriptor's sensor the rendered one, which `as_authored` does not.

### Tagged demos: loader gaps, ranked
From `docs/DIRSIG_tagged_demo_features.md`, which reads the 18 tagged demos (URSO relevance and SDA) feature by feature. Ranked by the number of tagged demos that need each feature. First layered targets: Indoors1 for URSO (items 1 and 2 only; 8 s, deterministic, names `SpiceEphemeris`) and MoonSat2 for SDA (items 1, 2, 6 and 10; 4 s; radiance identical in every probe condition). Not built.

#### 1. BasicAtmosphere `.atm` with uniform weather
Needed by all 18 tagged demos (URSO 9, SDA 9): simple, uniform and classic radiative transfer with `turbulence` and uniform weather from an installation `.wth`. The uniform form with installation weather and a fixed Sun is built (`engine.atmosphere.uniform`, round 22); simple and classic radiative transfer, turbulence and lunar values remain. The same feature as items 1 to 3 and 6 of "Loader features for demos".

#### 2. Demo platform form
Needed by 16 (URSO 9, SDA 7): a demo's `.platform` as authored (built in round 22, `engine.platform.as_authored`), or a sensor-spec holding a demo camera's values with its radiance image units (`platform_gen` writes an electron image from a template plus a sensor-spec; "A demo camera as a sensor-spec"). Same as item 4 of "Loader features for demos" and the licensed-value overlay. With item 1 it makes Indoors1, Sources6, SubPixelObject1, SubPixelObject2 (and IESSources1, see 11) layered.

#### 3. Simulation options file
Needed by 6 (URSO 4: Sources1, Sources3, Sources4, Sources5; SDA 2: Ssa1, MoonSat1): the `<options>` file of a legacy `.sim` (secondary-source and atmosphere entries). No engine member carries it; decide between carrying the file and mapping its entries to `engine.run` options (some have `dirsig5` command-line counterparts). With 1 and 2 it completes the URSO set.

#### 4. Fixed-site LookAt platform motion
Needed by 3 SDA (Ssa1, EarthShine1, Ssa2): a platform at a fixed geodetic or ECEF location pointed by LookAt at a fixed location or at an `sgp4` target. `resolve_run` motion kinds are `static` (Euler) and `orbit` only.

#### 5. `EarthGrid` and runs without a scene
Needed by 3 SDA (EarthShine1, SpaceRendezVous1, StkImport1): the `EarthGrid` plugin (background image and grid lines), and StkImport1 has no scene file at all. No engine member adds a plugin, and one scene is required.

#### 6. Tracking mount
Needed by 2 SDA (MoonSat2, SpaceRendezVous1). `platform_gen._check_unwritten` generates only a fixed identity mount from a sensor-spec; whether a template's tracking mount passes through unchanged is untested and is the first thing to try for MoonSat2.

#### 7. STK-format waypoint and quaternion motion
Needed by 2 SDA (StkImport1, SpaceRendezVous1): platform `flexible` motion with `waypoints` location and `quaternions` orientation read from STK report files. Engine motion kind `waypoints` is open in the schema and refused by the loader.

#### 8. Non-imaging instruments
Needed by 2 SDA: StkImport1's `datarecorder` instrument and LightCurve1's `LightCurve` sensor plugin (SpaceRendezVous1's lidar is out of scope). One imaging sensor entry and one focal plane per job today.

#### 9. LookAt at a moving target from an orbit
Needed by 1 SDA (Ssa3, DIRSIG 4 only): a platform on an element-set orbit pointed at another orbiting object. The `orbit` kind points along track at a fixed scene point and propagates the element set itself rather than with DIRSIG's `sgp4` engine ("Ssa1 against the orbit form").

#### 10. Ephemeris as authored
MoonSat2 names no ephemeris plugin, and every legacy `.sim` (URSO 7, SDA 4) relies on DIRSIG's implicit one, while the layered job always adds `SpiceEphemeris`. Check whether that changes any output; if it does, allow a run without an ephemeris plugin. A check before it is a feature.

#### 11. Scene files outside the linked folders
IESSources1's IES files sit at the top of the demo folder; the scene reference copy links only `geometry/`, `materials/` and `maps/` (`scene_ref.ASSET_DIRS`). Test whether DIRSIG resolves the source-shape path from the copy; if not, link the files the scene names. PointCollectors2 has the same gap and it is confirmed: its `.scene` names `demo.glist` and `$SCENE_DIR/demo.mat` beside it, and its layered run fails in the dry run ("demo.mat is not a file", round 22, `docs/DIRSIG_layered_comparison.md`). Built in round 23 (`scene_ref.scene_named_paths`, `reference_scene(..., named=...)`): the job copies (not links: `scene2hdf` writes beside the `.scene`) the files the `.scene` names inside its folder, one level into a named `.glist` or `.odb`, and links the folders it names there; PointCollectors2's layered render is now byte-identical to its same-seed pass-through render. Remaining: files named only from a material file (IESSources1's IES files, if the source material names them) are not followed; test IESSources1 when its atmosphere form is built.

### Compare layered demos with their pass-through references
For each demo with a pass-through reference (`docs/DIRSIG_demo_reference_runs.md` and the 131 demos the sweep rendered, `docs/DIRSIG_demo_sweep.md`; 69 of them are survey `ready` or `near` demos since the survey was regenerated in round 23), render the layered recipe at the demo's native size and compare with the reference: shape, per-band mean, maximum absolute difference and the fraction of pixels differing, listing every known input difference (platform template, sensor stand-ins, atmosphere, seed). The pass criterion stays byte equality at the same seed, region of interest and DIRSIG version, or a stated tolerance; the reference is the pass-through run, kept outside git. Round 22 did the first three with `scripts/compare_layered.py` (`docs/DIRSIG_layered_comparison.md`): MaterialMap1 byte-identical at the same seed, DensityMap1 different only through the pose's rounding (next item), PointCollectors2 stopped by item 11 of "Tagged demos: loader gaps"; with item 11 built in round 23, PointCollectors2 byte-identical at the same seed. Round 24, the next eight `ready` demos by reference cost: ColorFilterArray1, LensDistortion1, ReflectanceMap1 byte-identical; PolyFill1, PrimitiveObjects1, Indoors1 different only through the pose's rounding (next item); BayerPattern1 and Telecentricity1 stopped by files DIRSIG looks for in the working folder (below). With the simple form built (item 2 of the ranking), DeltaMotion1 byte-identical. Round 25: with the working-folder files placed (below), BayerPattern1 and Telecentricity1 byte-identical; Polarization5 stopped by files its material file names (below). Then the next ten by cost: GenericMotion1, TemporalIntegration1, InstanceOptions1 byte-identical; DecalMap1, VertexNormals1 different only through the pose's rounding (next item); BumpMap2, DataDrivenArray2 only through the explicit zero scene offset (and, round 26, Polarization5's truth coordinates with the pose's rounding), and Balfour2, DataDrivenTempSolver1 (thermal) only through the epoch's written form (items below); BundledMaterials1 stopped by material bundles (below). Round 26, with the material-file entries placed (below): BundledMaterials1 byte-identical; Polarization5 different only through the pose's rounding and the explicit zero scene offset (items below). Then the next ten by cost: LeafStack1, MacbethColorChecker1 byte-identical; BumpMap1, PrimitiveObjects2, RollingShutter1, SubObjectMotion1, SubObjectMotion2 only through the pose's rounding; TriBar1 only through the zero offset; MappedTherm1 stopped by material files the job holds nowhere and Thermal2 by the one-capture-per-window check (items below; past them, both differ only by listed differences). Round 27: MappedTherm1 with its files placed (below), different only through the epoch's written form and the pose's rounding; the demos the survey moved without a render: Polarization4 stopped by the one-capture-per-window check (four focal planes; past it, only the pose's rounding), Fireball1 by a `TEMP_SOLVER` `FILENAME` beside its `.scene`, Polarization2 failing in DIRSIG in both forms (no reference), EarthClouds1 not derivable (plugins); then the next five by cost: MixtureMap1 byte-identical; UvMapping1, UvMapping2, ExtinctionProp1, Pilings1 only through the pose's rounding. Next: the remaining `ready` demos with a deterministic reference (the sweep report's candidates; ChipMaker2, whose layered dry run passes with round 27's working-folder files, not yet rendered). Next: the remaining `ready` demos with a reference (the sweep report's "Layered-comparison candidates", now including the simple-atmosphere demos, BumpMap2 and BundledMaterials1 next), then the classic form once built.

### Motion files lose precision in dirfm's `PlatformPosition`
dirfm writes a static `.ppd`'s Euler angles to six decimals and its position to three (`%f`-style formatting), and its location element carries `type` where DIRSIG's own files say `frame`. The angle rounding alone makes DensityMap1's layered render differ from its pass-through render in almost every pixel (round 22; restoring the two angles gives byte equality), and PolyFill1's, PrimitiveObjects1's and Indoors1's (round 24; restoring the angles alone gives byte equality for each). Since then DecalMap1, VertexNormals1 (round 25), BumpMap1, PrimitiveObjects2, RollingShutter1, SubObjectMotion1, SubObjectMotion2 (round 26), UvMapping1, UvMapping2, ExtinctionProp1, Pilings1 and Polarization4 past its capture check (round 27) the same way, and with other differences DataDrivenTempSolver1, Polarization5 and MappedTherm1. Fix in `motion_tasks` (write the `.ppd` without dirfm, or with full precision) or upstream in dirfm; either changes the bytes of every static-pose layered job (not its run id), so re-render the layered references after it.

### Files DIRSIG looks for in the working folder
DIRSIG runs a pass-through job in the demo's folder and a layered job in the job's input folder, and resolves some relative names from the working folder. Two cases are measured (round 24, `docs/DIRSIG_layered_comparison.md`): a file a `.platform` names in a `<filename>` (BayerPattern1's `pixels.hdf`; `engine.platform.as_authored` copies the `.platform` alone, and a copy beside it is not found) and a geometry list a `.scene` names by a bare name that lies beside it and not in its `gdbdirectory` (Telecentricity1's `demo.glist`, and then the `Sphere.obj` the list names). With the files in the job's working folder both layered renders are byte-identical to their same-seed pass-through renders. Built in round 25 (`engine.working_folder`, `scene_ref.working_folder_files`, `tests/test_working_folder.py`): the loader finds both kinds from the scene and platform files, requires the engine block to list them with their library refs (so the run id covers them), and the job copies them into its input folder; BayerPattern1's and Telecentricity1's layered renders are byte-identical to their same-seed pass-through renders, and the survey counts both kinds as covered (66 `ready`). Remaining: files a material file names. Polarization5 (covered by the platform rule) stops next on its `.mat`'s `PARAMETER_FILE = ./materials/*.brdf` and `BRDF_FIT_FILE = ./materials/grass.fit`, which DIRSIG looks for in the working folder and the `emsdirectory` only; with the six files its material file names in the working folder its dry run passes (round 25, controlled variation). A `TEMP_SOLVER` `FILENAME` (DataDrivenTempSolver1's `materials/temps/*.txt`) is found without them (placing them changed nothing). BundledMaterials1's material file names four material bundles in `BUNDLE_FILENAME` entries (`bundles/*.mat.hdf`), which DIRSIG looks for in the working folder only (its `emsdirectory` is empty); with them there the layered render is byte-identical to the same-seed pass-through render (round 25). Built in round 26: `working_folder_files` also follows the scene's material file, for `PARAMETER_FILE`, `BRDF_FIT_FILE`, `EMISSIVITY_FILE` (measured: with the other five of Polarization5's files placed, its dry run fails on `./materials/grass.ems`) and `BUNDLE_FILENAME` entries relative to the scene's folder and not to its `emsdirectory` (or with an empty one); BundledMaterials1's layered render is byte-identical to its same-seed pass-through render, Polarization5's differs only by the pose's rounding and the explicit zero offset (items below). The survey counts the four keys as covered (68 `ready`; Polarization2 `ready` and Polarization4 `near` by the rule without a render). Built in round 27: a fourth rule for `EMISSIVITY_PROP` `FILENAME`, `TEMP_SOLVER` `IMAGE_FILENAME`, texture `IMAGE` `FILENAME` and `MATERIAL_MAP` `IMAGE_FILENAME` entries the scene copy does not hold where DIRSIG looks (MappedTherm1, ChipMaker2; "Material files the job holds nowhere" below). Remaining: other material-file keys DIRSIG may resolve from the working folder (`TXT_FILENAME`, `DATA_FILENAME`, `SLI_FILENAME`, a `REFLECTANCE_PROP` `IMAGE_FILENAME` and the rest are unmeasured; CurveMap1's `SLI_FILENAME` and Fireball1's `TEMP_SOLVER` `FILENAME` are the demo cases; DataDrivenTempSolver1's `TEMP_SOLVER` `FILENAME` is measured not to need it).

### dirfm writes an explicit zero scene offset
dirfm's jsim states every scene as `{"inputs": ..., "offset": "0,0,0"}`; a demo's own simulation file states none. For BumpMap2 (image, at most 4.75e-10), DataDrivenArray2 (truth scene-ENU coordinates, at most 4.1e-9 m) and, with the pose's rounding, Polarization5 (truth scene-ENU coordinates, at most 4.6e-9 m; round 26), TriBar1 (image, at most 3.5e-18; round 26) and Thermal2 (truth coordinates, with the epoch's form; round 26) that alone makes the layered render differ from the same-seed pass-through render: the layered job's input folder re-rendered without the key gives the pass-through digests (round 25, `docs/DIRSIG_layered_comparison.md`). Fix: omit the key when `engine.scenes[].offset` is zero (or absent) in the job's jsim; it changes the bytes of every layered job (not its run id), so re-render the layered references after it.

### The epoch is written in UTC
dirfm's `.tasks` writes the reference time in UTC (`...T17:00:00.000000+00:00`); a demo writes the same instant with its local offset (`...T12:00:00.0000-05:00`). Visible-band renders are unaffected; thermal ones are not: Balfour2's layered render equals the same-seed pass-through render with only that string restored, DataDrivenTempSolver1's with it and the Euler angles (round 25). Mechanism not isolated (a hypothesis: the temperature prediction reads the time of day in the written offset). Decide whether the run spec's epoch keeps its offset (`descriptor.collection.epoch` is stated with an offset; the loader converts it to UTC) or the scene's local offset is derived from its origin; either changes thermal results, so it needs a stated rule and C-n question. Round 26: MappedTherm1 (with the demo's `.tasks` and angles) and Thermal2 (with the demo's `.tasks` and without the zero offset) the same way, both thermal.

### Material files the job holds nowhere
MappedTherm1's material file names `values.img` (a `TEMP_SOLVER` `IMAGE_FILENAME` of a `MappedTherm` solver; DIRSIG searches the working folder and the scene's `mapdirectory`) and `roof_metal_gray.ems` (a `FILENAME`; the working folder and the `emsdirectory`, here `$SCENE_DIR`), both lying beside the `.scene`. The job's scene copy holds the linked folders and the files the `.scene` names, and `engine.working_folder` follows only the four measured keys, so neither file is in the job and the layered dry run stops (round 26). With `values.img`, its `.hdr` and the `.ems` in the working folder the render differs only by the epoch's written form and the angles. The survey counts such files (any key, a file beside the `.scene` the job holds nowhere) as missing: MappedTherm1 `near`, Fireball1 `far` and EarthClouds1 (already `far`) by the rule without a render. Built in round 27, measured first: by dry runs of the layered job with the files placed in turn, `values.img` is found in the working folder or the scene copy's `mapdirectory`, not in the scene copy's own folder, and needs its ENVI header beside it; `roof_metal_gray.ems` in the working folder or the scene copy's folder. `working_folder_files` gained a fourth rule (working folder, one mechanism for both): an `EMISSIVITY_PROP` `FILENAME`, a `TEMP_SOLVER` `IMAGE_FILENAME` (with its header), a texture `IMAGE` `FILENAME` or a `MATERIAL_MAP` `IMAGE_FILENAME` relative to the scene's folder where the scene copy does not hold it in the `emsdirectory` or `mapdirectory` (the last two measured on ChipMaker2, whose layered dry run then passes). MappedTherm1's layered render differs only by the epoch's written form and the angles; the survey counts it `ready`. Remaining: Fireball1's `fireball_temp.txt` (a `TEMP_SOLVER` `FILENAME` beside its `.scene`; round 27, measured: its layered dry run stops on it, DIRSIG searching the working folder and the scene's seven directory elements but not the scene's own folder, so the working folder would serve; not placed, because DataDrivenTempSolver1's `TEMP_SOLVER` `FILENAME`s, held in a linked folder, need nothing and a rule must tell the two apart) and EarthClouds1's `denmark.png` (a `REFLECTANCE_PROP` `IMAGE_FILENAME`; unmeasured: its simulation file names plugins the layered form does not write).

### Several captures in one task window
Thermal2's camera has an external clock (`<clock type="external">` naming a trigger file, placed by `engine.working_folder`) with five trigger times in its one task window; DIRSIG captures five frames, and the SDK's check of the dry-run log (`Simulation._check_log`, one capture per task window) refuses the run (round 26). Past the check (a diagnostic with it bypassed), the five images and truth images equal the pass-through ones with the demo's `.tasks` and without the zero offset. The survey counts an external clock as missing (Thermal2 `near`). Fix: let the check expect the captures the platform's clock states (trigger times inside each window) when the platform is used as authored, or state the expected capture count in the spec; either is a change to the check's semantics, so it needs a decision. Round 27: Polarization4 is refused by the same check for a different reason, four focal planes each capturing once in its one window ("log lists 4"); past the check its layered render differs only by the pose's angles. The survey already counts several focal planes as missing.

### NewAtmosphere databases the demo archives do not ship
Seven attempts in the demo sweep failed with "Could not open NewAtmosphere HDF" for a database the demo's simulation file names but its archive does not contain: CloudOpenVdb1 (`dynamic_mls_rural_23km_isaac.adb.hdf`, `static_mls_rural_23km_isaac.adb.hdf`), Cloudview1 and EarthClouds1 `demo_advanced.jsim` (`mls_rural_23km.adb.hdf`), Refraction1 (`mls_rural_23km_merged.adb.hdf`, `mls_rural_23km_mod6_json.adb.hdf`, `mls_rural_23km_mod6_tape.adb.hdf`), and earlier Brdf1 `demo.jsim` (`mls_urban_38km.adb.hdf`). The demos expect the user to build them with DIRSIG's atmosphere tools (MODTRAN-backed), which the sweep did not run. Decide whether to build them once and keep them as hashed library assets outside the demos (a database is an engine asset like AUROR's), or leave these demos as recorded failures.

### ClassicAtm `.adb` files the demo archives do not ship
Two attempts failed with "unable to open file" for a ClassicAtm database: Refraction1 `classic_atm.sim` (`classic_mls_rural_23km.adb`) and Thermal1 (`mls.adb`). Same decision as the NewAtmosphere item; the files come from the same database tools.

### Single-demo external dependencies
Muses2 needs the external MUSES tool (`MUSES_EXE` is unset); SpatialResponse1 needs the DIRSIG 4 variable `DIRSIG_ODB`; ReflectanceInversion1's `grass.sim` and `gray.sim` read `test1.mat` and `test2.mat`, which the demo presumably makes in an earlier step; ModularCity1's `demo.jsim` names `city1.scene`, which is not where it looks. Each is a demo-level prerequisite, recorded and not worked around.

### DIRSIG 4 engine path (maybe)
`MoonSat1`, `Ssa2` and `Ssa3` are DIRSIG 4 demos (flagged by the online demo page) and were not attempted; several DIRSIG 5 failures are DIRSIG 4 features DIRSIG 5 refuses (SAR reflectivity in SpotlightSar1 and StripmapSar1, a scripted mount in ScriptMount1, an `<atmospherics>` geometry in FastCloud1, the `DIRSIG_ODB` variable). Maybe: a second engine path for DIRSIG 4, if an installation is available and the SDA demos need it. Not planned.

### Artifact listings at scale
References are hashed once when a run completes and cached in `artifacts.json` and the status, so `list_artifacts` on 2,000 files takes about 3 ms (`tests/test_artifact_scale.py`). The contract has no pagination: the listing and every `get_run` status carry all references, about 630 KB for 2,000 files (LightCurve1 wrote 1,681). `LocalBackend.get_artifact` reads the whole file into memory (a 1 GB file: 0.35 s and a 1 GB peak). No contract change this round; MANIFOLD question C-27. Options: a status that carries a count and a listing with a cursor; a streamed or ranged artifact read.

### Default-seed nondeterminism in demos
With no `--random_seed`, 43 of 125 repeated demos gave different outputs (every lidar demo's `.bin`, 9 demos in truth images only, 3 in data-recorder text, 14 in radiance images; `docs/DIRSIG_demo_sweep.md`). The determinism probe (`docs/DIRSIG_determinism.md`) repeated six of the non-lidar ones under three conditions: a stated seed does not make them repeat; one thread does (radiance); truth-only differences are a renumbering of the optical-property index band, which neither controls; recorder differences are a time stamp. DIRSIG's default seed is fixed. Not carried into the run spec: a seed member exists (`engine.run.seed`), and a thread count is item "`--threads` in `engine.run`". Lidar demos were run and not analyzed. Remaining: the other 20 non-lidar demos that differed were not probed; truth images need a label-aware comparison (`scripts/compare_outputs.py`, class `index-relabel`).

### Lidar demos: run, not analyzed
The sweep rendered 17 lidar demos (and SpaceRendezVous1's `lidar_rpo.jsim`); every repeated one differed in its `.bin` output, and SpaceRendezVous1's lidar output and truth differed again on two more renders. Lidar outputs are out of scope for the determinism probe and the tagged-demo reading: run, not analyzed. Analyzing them needs a reader for DIRSIG's binary lidar format.

### Determinism follow-ups
The seed: `engine.run.seed` exists and reaches `--random_seed`, but a stated seed did not make any probed repeat identical, so no seed question is put to MANIFOLD; the open question is the thread count (C-08, and C-28 for the run id). LightCurve1's two further renders repeated 1,679 of 1,681 outputs; one frame (`cube_150.img`) and the light-curve table differ (digests only). Two one-thread renders were bit-identical in all 1,681 outputs (`docs/DIRSIG_determinism.md`, addendum); classifying the default-thread difference in `cube_150.img` needs a default-thread render kept beside a one-thread one. The 20 other non-lidar demos whose sweep repeats differed were not probed; the classes from the probe predict threads for radiance and the index renumbering for truth images, untested. A layered-versus-reference test needs the label-aware truth comparison of `scripts/compare_outputs.py` (`index-relabel`).

### Throttle rule and idle cores
`throttle_suspect` now needs a core below 90 percent of `cpuinfo_max_freq`, but the minimum over cores includes cores idle during single-threaded phases (scene compile, scene loading): 27 of 28 probe renders at 90 C and above, and all six long SDA renders, were flagged, with minimum frequencies near 400 MHz. Use a busy-core statistic (the mean, or the minimum over cores above an idle threshold) to separate throttling from idling.

### Demo sweep follow-ups
`scripts/sweep_demos.py` measures wall time by its 2 s poll, so short renders read as 4.1 s or 6.1 s; record the worker's start and finish times instead. Its stdout to `driver.log` is block-buffered, so the log showed nothing during the run (the heartbeat was the progress signal); flush per line. The pass-through record now carries the CPU frequency (`cpu_freq_khz`); the round 15 sweep predates it, so whether its 90 C-plus temperatures throttled the renders is unknown. Rerun the sweep after a DIRSIG upgrade and diff the outcomes.

### Ssa1 against the orbit form
Ssa1 (satellite imaging a satellite) rendered as authored in 629 s with four outputs. Compare it with the SDK's orbit form once space-object imaging against space exists (the C-05 scope note): propagate the same objects, express the observer in layers, and compare the images and truth with the pass-through reference.

### PointCollectors2 scan variants
PointCollectors2's `xy_scan.jsim`, `xz_scan.jsim` and `yz_scan.jsim` use the PointCollectors plugin and write point samples, not images; the sweep ran only `framing.jsim` (no `demo.sim` or `demo.jsim`, alphabetical first). Run the three scans through the pass-through form and decide how a non-image output is listed and compared.

### Notebook policy
Executable truth lives in scripts and tests, not notebooks: a demo's reference run is `scripts/run_demo.py` (and the sweep `scripts/sweep_demos.py`). Notebooks only where analysis is the point; they hold no logic of their own (they call the SDK and the scripts' functions), and each has a validate-only smoke test that runs without rendering.

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
