# Tagged DIRSIG demos: features and loader gaps

The demos tagged in `docs/DIRSIG_demo_coverage.md` ("Tagged demos": URSO relevance and SDA) read feature by feature: what each models, which DIRSIG features it uses, how far the SDK's layered form (`run-spec/1` engine block, `run_spec.resolve_run`, `platform_gen`, `motion_tasks`, the generated job) covers each, its pass-through reference run, and what stands between it and a layered run. Hand-written; not regenerated. First written before `engine.atmosphere.uniform` and `engine.platform.as_authored` were built; brought up to date in round 27 with them, `engine.atmosphere.simple`, `engine.working_folder`, the copies of the files a `.scene` names and the `fixed_ephemeris` rule (CONOPS and Guide section 3.2). The verdicts quoted are those of `docs/DIRSIG_demo_coverage.md` at that date; the comparisons are in `docs/DIRSIG_layered_comparison.md`. The control files were read in place from the demo archives of DIRSIG 2026.38 (no extraction); the simulation file read is the one the demo sweep ran, or for the three DIRSIG 4 demos the one the coverage survey names. Only names of plugins, elements and files, counts and measurements appear here, and every description is a paraphrase. No feature was built.

## Evidence for the SDK status

Each feature below cites one of these. "Supported" means the layered form expresses it today; "partial" that it does with a stated limit; "unsupported" that the loader refuses it or has no member for it; "unsure" that the code does not settle it and it was not tested.

| Id | What the SDK does | Where |
|---|---|---|
| E-ATM | `engine.atmosphere.plugin: new_atmosphere` (a prebuilt NewAtmosphere HDF database), or `basic` with `uniform` or `simple` (a BasicAtmosphere `.atm` the job writes from stated values: UniformAtm or SimpleAtm radiative transfer, uniform weather from an installation file, an optional fixed Sun); classic radiative transfer, `turbulence` and lunar values are not written; `four_curve` and `basic` with a file are refused | `run_spec.resolve_run`, refusal at `/engine/atmosphere/plugin`; `basic_atmosphere`; BACKLOG "Loader features for demos" items 1 to 3 |
| E-WTH | With `new_atmosphere`, weather must be a library ThermWeather file (`engine.weather.source: library`); with `atmosphere.uniform` or `atmosphere.simple`, the uniform weather is an installation `.wth` named in the written `.atm` (`weather.install_file`), and a library weather file beside it is refused | `run_spec.resolve_run`, refusal at `/engine/weather/source`; `basic_atmosphere` |
| E-EPH | The job carries `SpiceEphemeris` with DIRSIG's bundled kernels (`engine.ephemeris.plugin: spice`), except when `atmosphere.uniform` or `atmosphere.simple` states `fixed_ephemeris`: then it has no ephemeris plugin and DIRSIG takes the Sun from the `.atm` (an `engine.ephemeris` beside it is refused) | `run_spec.resolve_run`; `platform_ref.SpiceEphemerisPlugin` |
| E-SCN | One scene per run; the scene file is copied beside symbolic links to its `geometry/`, `materials/` and `maps/` folders, with copies of the files (and links to the folders) the `.scene` names inside its own folder (one level into a named `.glist` or `.odb`), and compiled as authored, so its geometry lists, static and dynamic instances (with their own motion files or engines), materials, sources, texture and BRDF files are used unchanged; the files DIRSIG looks for in the working folder (a platform `<filename>`, a geometry list beside the `.scene` outside its `gdbdirectory`, and material-file entries by the measured keys) are copied there when `engine.working_folder` lists them; other files only a material file names (for example a `SOURCE_SHAPE`) are not placed | `run_spec.resolve_run` (one `engine.scenes` entry); `scene_ref.reference_scene` (`ASSET_DIRS`), `scene_ref.scene_named_paths`, `scene_ref.working_folder_files` |
| E-PLT | The `.platform` is rendered from a library template plus a sensor-spec (the sensor-spec supplies optics, detector size and pitch, channels, gain, frame rate and exposure; the template keeps the mount, truth collection, spatial response, sampling and image file; a template needs exactly one instrument, focal plane, channel list, detector array and temporal integration), or, with `engine.platform.as_authored: true`, a demo's own `.platform` is copied into the job byte for byte (the sensor-spec and settings are checked, not applied; `integration_samples` and `channel_response` are refused) | `platform_gen.render_platform`, `platform_gen.check_template`; `run_spec.resolve_run` (`as_authored`); BACKLOG "Licensed-value overlay" |
| E-UNITS | A generated platform writes channels as absolute responses (electrons per photon) for an image in electrons per square metre (`platform_gen.IMAGE_QUANTITY`); the demos image radiance (`fluxunits="watts"`, `areaunits="cm2"`) with unit-gain channels | `platform_gen` module docstring and `IMAGE_QUANTITY` |
| E-MNT | A sensor-spec mount other than a fixed identity mount is refused; whether a template's own non-static mount passes through unchanged is not tested | `platform_gen._check_unwritten`; survey rule "`<type>` mount" |
| E-MOT | Platform motion is `static` (dirfm `PlatformPosition`: one scene-frame location, Euler angles in `sceneenu`) or `orbit` (a TLE propagated to ECEF waypoints by the SDK's propagator, dirfm `FlexMotion`, pointed by LookAt at a fixed scene point along track); `waypoints` is refused | `run_spec.resolve_run` (motion kinds), `run_spec._resolve_orbit`, `motion_tasks.generate_motion`, `orbit` |
| E-TSK | One `.tasks` file from the collection epoch and `engine.tasks` windows | `motion_tasks.generate_tasks` |
| E-OPT | No engine member carries a simulation options file (`<options>` in a `.sim`); some of its entries have `dirsig5` command-line counterparts, which the engine block does not carry either | `dirsig-engine/1` schema (`engine.run` holds `seed` only); BACKLOG "`--threads` in `engine.run`" |
| E-PLG | No engine member adds a plugin beyond atmosphere, ephemeris and `BasicPlatform` (for example `EarthGrid`, `LightCurve`); a run without a scene file is refused | `run_spec.resolve_run` (one scene); the job's plugin list in `simulation.Simulation` |
| E-NI | One imaging sensor entry with one focal plane per job; non-imaging instruments (data recorder, lidar) and sensor plugins are not generated | `run_spec.resolve_run` (one entry, one focal plane); `platform_gen.check_template` |
| E-OUT | The image, its header and the truth images of every capture become artifacts, each with its frame | `artifacts.artifacts_for` |

The legacy `.sim` form names no ephemeris; DIRSIG supplies one implicitly. Where the `.atm` fixes no Sun the layered job adds `SpiceEphemeris`; MaterialMap1 (a `.sim`) and LensDistortion1 (a `.jsim` that names none) rendered byte-identical to their same-seed pass-through runs with it (`docs/DIRSIG_layered_comparison.md`). Where the `.atm` fixes the Sun, `fixed_ephemeris` gives a job with no ephemeris plugin.

## URSO relevance

### Sources1 (`demo.sim`)

1. A flat plate at night lit by three point sources with different lamp spectra, seen by a nadir colour camera.
2. Features: `BasicAtmosphere` from `simple.atm` (`simpleradiativetransfer`, `uniformweather` from an installation `.wth`); implicit ephemeris; one scene (`classicscene`) whose geometry list holds `gdb` objects with static instances and three `pointsource` objects, with source materials naming intensity files and source shapes; `BasicPlatform` with a static mount, a `generic` instrument, `simple` capture, `central` sampling, a tabulated three-channel response over 0.4 to 0.7 um, a 320 x 240 array, truth (Material, Intersection); a one-entry `.ppd` (`raw` method); one task; an options file (`secondarysources.viewdirect`, `secondarysources.threshold`).
3. SDK status: atmosphere and weather supported (`atmosphere.simple`, installation weather; E-ATM, E-WTH); ephemeris: the job adds `SpiceEphemeris`, measured unchanged on other `.sim` demos (paragraph above); scene and point sources supported as authored (E-SCN); platform supported as authored (E-PLT); static mount and one-entry motion supported (E-MOT); task supported (E-TSK); options file unsupported (E-OPT); outputs supported (E-OUT).
4. Reference run: rendered, 6.1 s, deterministic (sweep).
5. Gaps: the options file (survey `near`). Comparison: exact is plausible (the reference repeats bit for bit), if the regenerated motion and tasks reproduce the demo's values exactly.

### Indoors1 (`demo.jsim`)

1. A handful of metal and painted objects (OBJ models and boxes) indoors, lit by one point source and seen by a colour camera with sub-pixel sampling.
2. Features: `BasicAtmosphere` from `uniform.atm` (`uniformradiativetransfer`, `uniformweather`, `turbulence`); `SpiceEphemeris`; one scene with `obj` geometry (material assignments), `box` primitives, static instances, a point source material and measured `.sqt` materials; `BasicPlatform`: static mount, `generic` instrument, `simple` capture, `central` sampling with detector sub-samples, rectangular channels over 0.4 to 0.7 um, 320 x 240, truth (Material, Intersection); one-entry `.ppd`; one task.
3. SDK status: atmosphere supported (`atmosphere.uniform`, installation weather; turbulence not carried; E-ATM, E-WTH); ephemeris supported (E-EPH); scene supported (E-SCN); platform supported as authored, sub-sampling included (E-PLT); motion and task supported (E-MOT, E-TSK); outputs supported.
4. Reference run: rendered, 8.1 s, deterministic (sweep). The coverage survey marks it `ready`.
5. Gaps: none. Comparison (round 24): the layered render differs from the same-seed pass-through render only through the pose's Euler angle, which dirfm's `PlatformPosition` writes to six decimals; with it restored, byte-identical (`docs/DIRSIG_layered_comparison.md`).

### Sources3 (`demo.sim`)

1. Two vehicles moving over a ground plane, one carrying a lamp source, seen in one frame (the archive's `video.sim` is the sequence).
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); implicit ephemeris; one scene with a `groundplane`, nested geometry lists and two `dynamicinstance`s moved by `delta` motion files in `geometry/`, one source material with a tabulated spectrum; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, rectangular channels over 0.4 to 0.7 um, 320 x 240; one-entry `.ppd`; one task; options file (secondary sources).
3. SDK status: as Sources1; the dynamic instances are scene content (E-SCN, supported).
4. Reference run: rendered, 6.1 s; repeats differed in the radiance image (sweep; not classified by the probe, whose two radiance demos differed through threads).
5. Gaps: options file (survey `near`). Comparison: statistical at the default thread count, exact at one thread (determinism probe).

### Sources4 (`demo.sim`)

1. Lamps on alternating-current power whose output flickers, seen by a camera clocked at 1800 Hz: sources modulated in time.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`); implicit ephemeris; one scene with `gdb` objects and seven `pointsource` objects whose materials name intensity files, source shapes, power-spectral-density files (`PSD_FILENAME`) and blink settings; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, tabulated channels over 0.4 to 0.7 um, 320 x 240, an independent clock at 1800 Hz; one-entry `.ppd`; one task; options file.
3. SDK status: as Sources1; the temporal modulation is source material content (E-SCN, supported as authored); the 1800 Hz clock is in the platform used as authored (E-PLT).
4. Reference run: rendered, 4.1 s, deterministic (sweep).
5. Gaps: options file (survey `near`). Comparison: exact plausible.

### Sources5 (`demo.sim`)

1. A plate lit by three point sources, imaged from 0.4 to 0.9 um.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`); implicit ephemeris; one scene with a `gdb` plate and three `pointsource` objects with intensity files and shapes; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, rectangular channels, 320 x 240; one-entry `.ppd`; one task; options file.
3. SDK status: as Sources1.
4. Reference run: rendered, 8.1 s, deterministic (sweep).
5. Gaps: options file (survey `near`). Comparison: exact plausible.

### IESSources1 (`demo.sim`)

1. Three point sources whose angular light distributions come from IES photometric files, lighting two boxes.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`); implicit ephemeris; one scene with `box` primitives and three `pointsource` objects whose source materials name an intensity spectrum and an IES file as the source shape; the IES files sit at the top of the demo folder, not under `geometry/`, `materials/` or `maps/`; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, tabulated channels, 480 x 240; one-entry `.ppd`; one task.
3. SDK status: atmosphere supported (`atmosphere.simple`); scene partial: the IES files are named only by the material file (`SOURCE_SHAPE`, bare names, beside the `.scene`), which neither the scene copy nor `engine.working_folder` places (E-SCN), and the layered dry run stops on them (round 27, measured: `Unable to locate file "example1.ies"`, searched in the working folder and the scene's `srcdirectory`; the working folder would serve); platform supported as authored; motion and task supported.
4. Reference run: rendered, 18.1 s, deterministic (sweep). Survey `ready`, an overstatement: the survey does not follow `SOURCE_SHAPE` entries, so it does not see the IES files.
5. Gaps: the IES files the material file names (`SOURCE_SHAPE`), which the job does not place (measured). Comparison: exact plausible once they are placed.

### Sources6 (`demo.sim`)

1. A car with working head and tail lights driving through a parking lot.
2. Features: `BasicAtmosphere` (`uniformradiativetransfer`, `uniformweather`, `turbulence`); implicit ephemeris; one scene with nested geometry lists (bundled car and parking-lot geometry, each with its own material file and source intensity files) and one `dynamicinstance` moved by a `generic` motion file under `geometry/`; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, rectangular channels, 320 x 240, frame clock 8 Hz; one-entry `.ppd`; one task.
3. SDK status: atmosphere supported (`atmosphere.uniform`; turbulence not carried); scene supported (E-SCN); platform supported as authored; motion and task supported.
4. Reference run: rendered, 44.1 s; repeats differed in the truth image only (sweep; not probed, likely the optical-property renumbering the probe found in two other truth-only demos).
5. Gaps: none (survey `ready`). Comparison: radiance exact plausible; truth with the label band mapped (determinism probe).

### SubPixelObject1 (`demo.sim`)

1. A small box moving across a grass plate, smaller than a pixel of a 64 x 48 camera, with abundance and sample-count truth: sub-pixel target detection.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); implicit ephemeris; one scene with a `gdb` plate, a texture map, static instances and one `dynamicinstance` on `flexible` motion (`waypoints` location, `velocity` orientation) inside the scene; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, rectangular channels, 64 x 48, truth (Intersection, Material, Sample Count, Abundance); one-entry `.ppd`; one task.
3. SDK status: atmosphere supported (`atmosphere.simple`; turbulence not carried); scene supported, including the object's waypoint motion (E-SCN, scene content); platform supported as authored, truth collectors included; motion and task supported.
4. Reference run: rendered, 44.1 s, deterministic (sweep). Survey `ready`.
5. Gaps: none. Comparison: exact plausible.

### SubPixelObject2 (`demo.sim`)

1. Two cars moving over grass, seen in the 8 to 12 um thermal infrared with an exposure integrated over ten time samples, with temperature truth.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`), with the weather driving temperatures; implicit ephemeris; one scene with a `groundplane` and two `dynamicinstance`s on `delta` motion files, BRDF-fitted paint and glass; `BasicPlatform` (`hyper.platform`): static mount, `generic`, `simple` capture, `central` sampling, `temporalintegration` (25 ms, 10 samples), rectangular channels over 8 to 12 um, 320 x 240, truth (Intersection, Material, SampleCount, Temperature); one-entry `.ppd`; one task.
3. SDK status: atmosphere and weather supported (`atmosphere.simple`, installation weather; turbulence not carried); scene supported; platform supported as authored, temporal integration included (E-PLT); motion and task supported.
4. Reference run: rendered, 62.1 s; repeats differed in the radiance and truth images (sweep).
5. Gaps: none (survey `ready`); in a thermal band the layered `.tasks` epoch, written in UTC, changed the renders of Balfour2, DataDrivenTempSolver1, MappedTherm1 and Thermal2 (`docs/DIRSIG_layered_comparison.md`). Comparison: statistical at the default thread count; exact at one thread is plausible.

## SDA

### MoonSat2 (`demo.jsim`)

1. A textured Moon moving along waypoints, followed by a long-focal-length camera on a tracking mount.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); no ephemeris plugin named; an empty `medium_list`; one scene with a `sphere`, a texture-mapped material and a `dynamicinstance` on `flexible` motion (`waypoints` location, `euler` orientation); `BasicPlatform`: `tracking` mount, `generic`, `simple` capture, `central` sampling, rectangular channels over 0.4 to 0.8 um, 320 x 240, truth (Material, Intersection, Normal, GeoIds, Geolocation, Shadow); one-entry `.ppd`; one task.
3. SDK status: atmosphere supported (`atmosphere.simple`; turbulence not carried); ephemeris: the layered job adds `SpiceEphemeris`, which the demo does not name (E-EPH; unchanged for LensDistortion1, a `.jsim` naming none; untested here); scene supported, including the Moon's motion (E-SCN); tracking mount carried in the platform used as authored, untested (the survey counts it missing; E-MNT); motion and task supported.
4. Reference run: rendered, 4.1 s. Determinism probe: radiance identical in every condition; the truth image differs only by the renumbering of the Moon material's optical-property index (`index-relabel`).
5. Gaps: the tracking mount (survey `near`; untested as authored); the added `SpiceEphemeris` (or evidence that it changes nothing here). Comparison: radiance exact; truth exact except the label band.

### Ssa1 (`demo.sim`)

1. A ground telescope at a fixed site tracking a communications satellite whose position comes from a two-line element set, with path right ascension and declination truth.
2. Features: `BasicAtmosphere` (`uniformradiativetransfer`, `uniformweather`, `turbulence`); implicit ephemeris; one scene (`demo_sgp4.scene`) with an `obj` satellite model with BRDF-fitted materials on a `dynamicinstance` with `flexible` motion (`sgp4` location engine, `lookat` orientation); platform motion: `flexible`, `fixed` geodetic location, `lookat` orientation whose target is an `sgp4` location engine with the same element set; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, focal length 400 m, rectangular channels over 0.4 to 0.9 um, 320 x 240, truth (Material, Shadow, GeoLocation, PathRightAscension, PathDeclination, ConvergenceStatus); one task; options file (`atm.sourceupdatedelta`, `atm.verbose`).
3. SDK status: atmosphere supported (`atmosphere.uniform`; turbulence not carried); scene supported, including the satellite's sgp4 motion (E-SCN); platform motion unsupported: a fixed site pointed by LookAt at a moving target is neither `static` nor `orbit` (E-MOT); platform supported as authored; options file unsupported (E-OPT).
4. Reference run: rendered, 629.4 s in the sweep; two more renders (673 s, 655 s) gave the same digests as the sweep's (`docs/DIRSIG_determinism.md`): deterministic.
5. Gaps: fixed-site LookAt motion with an sgp4 target; options file. Comparison: exact plausible, at the default thread count; each render takes about 11 minutes.

### EarthShine1 (`demo.jsim`)

1. A sphere lit both by the Sun and by sunlight reflected from the Earth, seen from a fixed site with a large 1280 x 960 camera.
2. Features: `EarthGrid` (a background image and grid lines for the Earth); `BasicAtmosphere` (`uniformradiativetransfer`, `uniformweather`, `turbulence`, an `ephemeris` element); `SpiceEphemeris`; one scene with a `sphere` on `flexible` motion at a `fixed` location; platform motion: `flexible`, `fixed` location, `lookat` at a `fixed` location with an up vector; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, rectangular channels, 1280 x 960, truth (eight collectors including HitFractions and SampleCount); one task.
3. SDK status: `EarthGrid` unsupported (E-PLG); atmosphere supported (`atmosphere.uniform` without `fixed_ephemeris`, since the demo's `SpiceEphemeris` replaces the `.atm`'s fixed Sun); ephemeris supported (E-EPH); scene supported; platform motion unsupported (E-MOT, fixed-site LookAt); platform supported as authored.
4. Reference run: rendered, 84.2 s, deterministic (sweep).
5. Gaps: `EarthGrid`; fixed-site LookAt motion. Comparison: exact plausible.

### SpaceRendezVous1 (`lidar_rpo.jsim`)

1. A chaser closing on the Hubble telescope, both moved by trajectory and attitude files in an STK export format, imaged by a lidar (the file the sweep ran) or by a panchromatic camera (`pan_rpo.jsim`, not run by the sweep).
2. Features: `EarthGrid`; `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); `SpiceEphemeris`; one scene with an `obj` Hubble model on `flexible` motion (`waypoints` location and `quaternions` orientation from data files); platform motion: `flexible`, `waypoints` and `quaternions` from data files; `BasicPlatform` with a `tracking` mount and a `lidar` instrument (`protolidar` capture); one task list over 15 minutes.
3. SDK status: the lidar sensor was run, not analyzed (out of scope); `EarthGrid` unsupported (E-PLG); atmosphere supported (`atmosphere.simple`); scene supported (E-SCN); platform motion unsupported (E-MOT, `waypoints`); tracking mount carried in the platform used as authored, untested (E-MNT).
4. Reference run: rendered, 705.5 s (lidar); two more renders differed from each other and from the sweep's in `demo.bin` and `lidar_truth.img` (digests only; lidar, not analyzed).
5. Gaps for the imaging variant (`pan_rpo.jsim`): `EarthGrid`; waypoint and quaternion motion from STK-format files; tracking mount (untested as authored); a reference run of that file. Comparison: not estimated (no imaging reference).

### LightCurve1 (`box_spin.jsim`)

1. A spinning box-shaped satellite on an orbit from a two-line element set, whose brightness over time as seen from a ground site is computed frame by frame.
2. Features: `LightCurve` (a sensor plugin with a location, bandpass, sample count, start time, duration and a target tag, writing one image per time step: 1,681 files, 13.5 GB); `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); no ephemeris named; one scene with an `obj` box with BRDF-fitted materials on `flexible` motion (`sgp4` location, `spin` orientation); no `BasicPlatform`.
3. SDK status: the sensor plugin is unsupported (E-NI, E-PLG); atmosphere supported (`atmosphere.simple`); scene supported (E-SCN); artifact listing of 1,681 outputs measured (BACKLOG "Artifact listings at scale").
4. Reference run: rendered, 691.9 s; two more renders (749 s, 750 s) repeated 1,679 of the 1,681 outputs exactly; one frame (`cube_150.img`) and the light-curve table differ, in the new pair and against the sweep's render (digests only, `docs/DIRSIG_determinism.md`).
5. Gaps: the `LightCurve` sensor plugin as an engine member (or a BasicPlatform re-expression). Comparison: not estimated.

### StkImport1 (`demo.jsim`)

1. A satellite imaging pass rebuilt from STK position and attitude reports, with the Earth drawn by `EarthGrid` instead of a scene, a colour camera and a data recorder.
2. Features: `EarthGrid`; no scene file; `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); `SpiceEphemeris`; platform motion: `flexible`, `waypoints` and `quaternions` from report files; `BasicPlatform`: static mount, a `generic` instrument (`simple` capture, `central` sampling, rectangular channels, 640 x 480, truth with GeoLocation) and a `datarecorder` instrument with its own clock; one task.
3. SDK status: no-scene runs and `EarthGrid` unsupported (E-PLG); atmosphere supported (`atmosphere.simple`); ephemeris supported; motion unsupported (E-MOT, `waypoints`); data recorder unsupported (E-NI); platform supported as authored. The coverage survey notes the pass was rebuilt from a TLE in `notebooks/dirfm_tutorials/tutorial_orbit_to_ground.ipynb`, which is the orbit form, not this demo's motion.
4. Reference run: rendered, 24.1 s. Determinism probe: radiance and truth identical in every condition; the recorder text differs only in a generation time stamp (`metadata`).
5. Gaps: `EarthGrid` and runs without a scene; STK-report waypoints with quaternions; the data recorder. Comparison: exact (recorder after masking the time stamp).

### MoonSat1 (`classic_atm.sim`, DIRSIG 4 only, not run)

1. The Moon seen from a static platform with a long focal length, under the classic radiative transfer.
2. Features: `BasicAtmosphere` (`classicradiativetransfer`, `uniformweather`, `turbulence`); implicit ephemeris; one scene with the Moon's materials; `BasicPlatform`: static mount, `generic`, `simple` capture with a `convergence` element, `central` sampling, 320 x 240, truth; one-entry `.ppd`; one task; options file (`atm.verbose`, `atm.minsolarmu`).
3. SDK status: atmosphere unsupported (classic radiative transfer); platform supported as authored, convergence settings included; options file unsupported.
4. Reference run: none; the sweep skipped it as DIRSIG 4 only.
5. Gaps: a DIRSIG 5 reference first; then the classic `.atm` and the options file.

### Ssa2 (`demo.sim`, DIRSIG 4 only, not run)

1. The Hubble telescope and an Earth sphere at fixed Earth-centred positions, seen from a fixed Earth-centred site, with Earth-reflected light.
2. Features: `BasicAtmosphere` (`uniformradiativetransfer`, `uniformweather`, `turbulence`, `ephemeris`); implicit ephemeris; one scene with an Earth `sphere` and an `obj` Hubble model, both static; platform motion: `flexible`, `fixed` ECEF location, `lookat` at a `fixed` ECEF location; `BasicPlatform`: static mount, `generic`, `simple` capture, `adaptive` sampling, 320 x 240; one task.
3. SDK status: atmosphere supported (`atmosphere.uniform` with `fixed_ephemeris`, a job with no ephemeris plugin); motion unsupported (fixed-site LookAt, ECEF); platform supported as authored, adaptive sampling included.
4. Reference run: none (DIRSIG 4 only).
5. Gaps: a DIRSIG 5 reference; fixed-site LookAt.

### Ssa3 (`demo.sim`, DIRSIG 4 only, not run)

1. An Earth-observing satellite on an orbit from an element set, seen by a platform that is itself on an element-set orbit and points at it.
2. Features: `BasicAtmosphere` (`uniformradiativetransfer`, `uniformweather`, `turbulence`, `ephemeris`); implicit ephemeris; one scene with an Earth `sphere` and an `obj` model on `flexible` motion (`sgp4` location, `velocity` orientation); platform motion: `flexible`, `sgp4` location, `lookat` at an `sgp4` target with an up vector; `BasicPlatform`: static mount, `generic`, `simple` capture, `adaptive` sampling, focal length 3 km, 320 x 240; one task.
3. SDK status: atmosphere supported (`atmosphere.uniform` with `fixed_ephemeris`); platform motion partial: the `orbit` kind propagates an element set itself and points by LookAt at a fixed scene point along track, not at another orbiting object, and it does not use DIRSIG's `sgp4` engine (E-MOT; BACKLOG "Ssa1 against the orbit form"); platform supported as authored.
4. Reference run: none (DIRSIG 4 only).
5. Gaps: a DIRSIG 5 reference; LookAt at a moving target from an orbit.

## Loader gaps across the tagged demos

Counts are the tagged demos whose simulation file needs the feature (URSO / SDA); the three DIRSIG 4 demos are included in the counts but have no reference. "Unblocks" lists the demos that would have no remaining gap once this feature and the features ranked above it exist.

| Rank | Candidate loader feature | URSO | SDA | Unblocks |
|---|---|---|---|---|
| 1 | BasicAtmosphere `.atm` with uniform weather from an installation `.wth` (E-ATM, E-WTH): uniform and simple radiative transfer built (`atmosphere.uniform`, `atmosphere.simple`); classic radiative transfer, `turbulence` and lunar values not | 9 | 9 | none alone (classic: MoonSat1 only) |
| 2 | Demo platform form: built as `engine.platform.as_authored`; a sensor-spec holding a demo camera's values with its radiance units is not (E-PLT, E-UNITS) | 9 | 7 | URSO: Indoors1, Sources6, SubPixelObject1, SubPixelObject2; IESSources1 also needs item 11 (measured) |
| 3 | Simulation options file, or the engine-run options it sets (E-OPT) | 4 | 2 | URSO: Sources1, Sources3, Sources4, Sources5 |
| 4 | Fixed-site LookAt platform motion, with a fixed or an `sgp4` target (E-MOT) | 0 | 3 | SDA: Ssa2 (no DIRSIG 5 reference); with 3, Ssa1 |
| 5 | `EarthGrid`, and runs without a scene file (E-PLG) | 0 | 3 | SDA: EarthShine1 (with 4) |
| 6 | Tracking mount (E-MNT) | 0 | 2 | SDA: MoonSat2 (with item 10) |
| 7 | Waypoint and quaternion motion from STK-format files (E-MOT) | 0 | 2 | none alone (StkImport1 also needs 5 and 8; SpaceRendezVous1's imaging variant needs 5 and 6) |
| 8 | Non-imaging instruments: the data recorder; the `LightCurve` sensor plugin (E-NI) | 0 | 2 | SDA: StkImport1 (with 5 and 7); LightCurve1 |
| 9 | LookAt at a moving target from an orbit (E-MOT, the `orbit` kind) | 0 | 1 | SDA: Ssa3 (no DIRSIG 5 reference) |
| 10 | Ephemeris as authored: a run without an ephemeris plugin when the `.atm` fixes no Sun (built when it does: `fixed_ephemeris`), and evidence that DIRSIG's implicit ephemeris equals `SpiceEphemeris` (equal on MaterialMap1 and LensDistortion1) (E-EPH) | 8 | 5 | SDA: MoonSat2 (with 6); for the `.sim` demos, a check rather than a feature |
| 11 | Files only a material file names, outside the placed files (IESSources1's `SOURCE_SHAPE` IES files, on which its layered dry run stops; DIRSIG searches the working folder and the `srcdirectory`); files the `.scene` names are copied since round 23 (E-SCN) | 1 | 0 | URSO: IESSources1 |

Ranking: by the number of tagged demos that need the feature, then by how cheap their references are. Items 1 and 2 were needed by nearly every tagged demo and are built (classic radiative transfer and turbulence aside); items 3, 10 and 11 also concern URSO demos, the rest are SDA-specific.

**First layered target, URSO: Indoors1.** Items 1 (uniform radiative transfer) and 2 are built and the survey marks it `ready`; its layered render (round 24) differs from the same-seed pass-through render only through the pose's Euler angle, which dirfm writes to six decimals (byte-identical with it restored). SubPixelObject1 (44 s, deterministic, `ready`, a legacy `.sim`) is the second.

**First layered target, SDA: MoonSat2.** It needed items 1, 2, 6 and 10, the fewest of the SDA demos that have a DIRSIG 5 reference; with items 1 and 2 built, 6 (its tracking mount, carried as authored but untested; the survey's one missing feature) and 10 remain; its reference renders in 4 s; and the determinism probe showed its radiance is identical in every condition, so a layered radiance image can be compared exactly. EarthShine1 (84 s, deterministic) needs 4 and 5 and is the second.
