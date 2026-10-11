# Tagged DIRSIG demos: features and loader gaps

The demos tagged in `docs/DIRSIG_demo_coverage.md` ("Tagged demos": URSO relevance and SDA) read feature by feature: what each models, which DIRSIG features it uses, how far the SDK's layered form (`run-spec/1` engine block, `run_spec.resolve_run`, `platform_gen`, `motion_tasks`, the generated job) covers each, its pass-through reference run, and what stands between it and a layered run. Hand-written; not regenerated. The control files were read in place from the demo archives of DIRSIG 2026.38 (no extraction); the simulation file read is the one the demo sweep ran, or for the three DIRSIG 4 demos the one the coverage survey names. Only names of plugins, elements and files, counts and measurements appear here, and every description is a paraphrase. No feature was built.

## Evidence for the SDK status

Each feature below cites one of these. "Supported" means the layered form expresses it today; "partial" that it does with a stated limit; "unsupported" that the loader refuses it or has no member for it; "unsure" that the code does not settle it and it was not tested.

| Id | What the SDK does | Where |
|---|---|---|
| E-ATM | Only `engine.atmosphere.plugin: new_atmosphere` (a prebuilt NewAtmosphere HDF database) is loaded; any other plugin is refused | `run_spec.resolve_run`, refusal at `/engine/atmosphere/plugin`; BACKLOG "Loader features for demos" items 1 to 3 |
| E-WTH | Weather must be a library ThermWeather file (`engine.weather.source: library`); a `.atm` file's uniform weather from a `.wth` in the installation (`source: install`) is open in the schema and not loaded | `run_spec.resolve_run`, refusal at `/engine/weather/source` |
| E-EPH | The job always carries `SpiceEphemeris` with DIRSIG's bundled kernels; no other ephemeris, and no run without one | `run_spec.resolve_run` (`engine.ephemeris.plugin` must be `spice`); `platform_ref.SpiceEphemerisPlugin` |
| E-SCN | One scene per run; the scene file is copied beside symbolic links to its `geometry/`, `materials/` and `maps/` folders and compiled as authored, so its geometry lists, static and dynamic instances (with their own motion files or engines), materials, sources, texture and BRDF files are used unchanged | `run_spec.resolve_run` (one `engine.scenes` entry); `scene_ref.reference_scene` (`ASSET_DIRS`) |
| E-PLT | The `.platform` is rendered from a library template plus a sensor-spec: the sensor-spec supplies optics, detector size and pitch, channels, gain, frame rate and exposure; the template keeps the mount, truth collection, spatial response, sampling and image file. A template needs exactly one instrument, focal plane, channel list, detector array and temporal integration. A demo's own `.platform` is not a template (most lack temporal integration), so a demo camera needs a sensor-spec holding its values | `platform_gen.render_platform`, `platform_gen.check_template`; BACKLOG item 4 "A platform form for demo platforms"; BACKLOG "Licensed-value overlay" |
| E-UNITS | A generated platform writes channels as absolute responses (electrons per photon) for an image in electrons per square metre (`platform_gen.IMAGE_QUANTITY`); the demos image radiance (`fluxunits="watts"`, `areaunits="cm2"`) with unit-gain channels | `platform_gen` module docstring and `IMAGE_QUANTITY` |
| E-MNT | A sensor-spec mount other than a fixed identity mount is refused; whether a template's own non-static mount passes through unchanged is not tested | `platform_gen._check_unwritten`; survey rule "`<type>` mount" |
| E-MOT | Platform motion is `static` (dirfm `PlatformPosition`: one scene-frame location, Euler angles in `sceneenu`) or `orbit` (a TLE propagated to ECEF waypoints by the SDK's propagator, dirfm `FlexMotion`, pointed by LookAt at a fixed scene point along track); `waypoints` is refused | `run_spec.resolve_run` (motion kinds), `run_spec._resolve_orbit`, `motion_tasks.generate_motion`, `orbit` |
| E-TSK | One `.tasks` file from the collection epoch and `engine.tasks` windows | `motion_tasks.generate_tasks` |
| E-OPT | No engine member carries a simulation options file (`<options>` in a `.sim`); some of its entries have `dirsig5` command-line counterparts, which the engine block does not carry either | `dirsig-engine/1` schema (`engine.run` holds `seed` only); BACKLOG "`--threads` in `engine.run`" |
| E-PLG | No engine member adds a plugin beyond atmosphere, ephemeris and `BasicPlatform` (for example `EarthGrid`, `LightCurve`); a run without a scene file is refused | `run_spec.resolve_run` (one scene); the job's plugin list in `simulation.Simulation` |
| E-NI | One imaging sensor entry with one focal plane per job; non-imaging instruments (data recorder, lidar) and sensor plugins are not generated | `run_spec.resolve_run` (one entry, one focal plane); `platform_gen.check_template` |
| E-OUT | The image, its header and the truth images of every capture become artifacts, each with its frame | `store.artifacts_for` |

The legacy `.sim` form names no ephemeris; DIRSIG supplies one implicitly. Whether that equals the `SpiceEphemeris` the layered job always carries is unsure (not tested); it applies to every `.sim` demo below.

## URSO relevance

### Sources1 (`demo.sim`)

1. A flat plate at night lit by three point sources with different lamp spectra, seen by a nadir colour camera.
2. Features: `BasicAtmosphere` from `simple.atm` (`simpleradiativetransfer`, `uniformweather` from an installation `.wth`); implicit ephemeris; one scene (`classicscene`) whose geometry list holds `gdb` objects with static instances and three `pointsource` objects, with source materials naming intensity files and source shapes; `BasicPlatform` with a static mount, a `generic` instrument, `simple` capture, `central` sampling, a tabulated three-channel response over 0.4 to 0.7 um, a 320 x 240 array, truth (Material, Intersection); a one-entry `.ppd` (`raw` method); one task; an options file (`secondarysources.viewdirect`, `secondarysources.threshold`).
3. SDK status: atmosphere and weather unsupported (E-ATM, E-WTH); ephemeris unsure (implicit); scene and point sources supported as authored (E-SCN); platform partial (E-PLT, E-UNITS); static mount and one-entry motion supported (E-MOT); task supported (E-TSK); options file unsupported (E-OPT); outputs supported (E-OUT).
4. Reference run: rendered, 6.1 s, deterministic (sweep).
5. Gaps: BasicAtmosphere `.atm` with uniform weather; the demo platform form; the options file. Comparison: exact is plausible (the reference repeats bit for bit), if the regenerated platform, motion and tasks reproduce the demo's values exactly.

### Indoors1 (`demo.jsim`)

1. A handful of metal and painted objects (OBJ models and boxes) indoors, lit by one point source and seen by a colour camera with sub-pixel sampling.
2. Features: `BasicAtmosphere` from `uniform.atm` (`uniformradiativetransfer`, `uniformweather`, `turbulence`); `SpiceEphemeris`; one scene with `obj` geometry (material assignments), `box` primitives, static instances, a point source material and measured `.sqt` materials; `BasicPlatform`: static mount, `generic` instrument, `simple` capture, `central` sampling with detector sub-samples, rectangular channels over 0.4 to 0.7 um, 320 x 240, truth (Material, Intersection); one-entry `.ppd`; one task.
3. SDK status: atmosphere unsupported (E-ATM, E-WTH); ephemeris supported (E-EPH); scene supported (E-SCN); platform partial (E-PLT, E-UNITS; the sub-sampling stays in a template); motion and task supported (E-MOT, E-TSK); outputs supported.
4. Reference run: rendered, 8.1 s, deterministic (sweep). The coverage survey marks it `near` (one missing feature).
5. Gaps: BasicAtmosphere `.atm` (uniform radiative transfer) and the demo platform form. Comparison: exact plausible.

### Sources3 (`demo.sim`)

1. Two vehicles moving over a ground plane, one carrying a lamp source, seen in one frame (the archive's `video.sim` is the sequence).
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); implicit ephemeris; one scene with a `groundplane`, nested geometry lists and two `dynamicinstance`s moved by `delta` motion files in `geometry/`, one source material with a tabulated spectrum; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, rectangular channels over 0.4 to 0.7 um, 320 x 240; one-entry `.ppd`; one task; options file (secondary sources).
3. SDK status: as Sources1; the dynamic instances are scene content (E-SCN, supported).
4. Reference run: rendered, 6.1 s; repeats differed in the radiance image (sweep; not classified by the probe, whose two radiance demos differed through threads).
5. Gaps: BasicAtmosphere `.atm`; demo platform form; options file. Comparison: statistical at the default thread count, exact at one thread (determinism probe).

### Sources4 (`demo.sim`)

1. Lamps on alternating-current power whose output flickers, seen by a camera clocked at 1800 Hz: sources modulated in time.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`); implicit ephemeris; one scene with `gdb` objects and seven `pointsource` objects whose materials name intensity files, source shapes, power-spectral-density files (`PSD_FILENAME`) and blink settings; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, tabulated channels over 0.4 to 0.7 um, 320 x 240, an independent clock at 1800 Hz; one-entry `.ppd`; one task; options file.
3. SDK status: as Sources1; the temporal modulation is source material content (E-SCN, supported as authored); the frame rate comes from a sensor-spec setting (E-PLT, partial).
4. Reference run: rendered, 4.1 s, deterministic (sweep).
5. Gaps: BasicAtmosphere `.atm`; demo platform form; options file. Comparison: exact plausible.

### Sources5 (`demo.sim`)

1. A plate lit by three point sources, imaged from 0.4 to 0.9 um.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`); implicit ephemeris; one scene with a `gdb` plate and three `pointsource` objects with intensity files and shapes; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, rectangular channels, 320 x 240; one-entry `.ppd`; one task; options file.
3. SDK status: as Sources1.
4. Reference run: rendered, 8.1 s, deterministic (sweep).
5. Gaps: BasicAtmosphere `.atm`; demo platform form; options file. Comparison: exact plausible.

### IESSources1 (`demo.sim`)

1. Three point sources whose angular light distributions come from IES photometric files, lighting two boxes.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`); implicit ephemeris; one scene with `box` primitives and three `pointsource` objects whose source materials name an intensity spectrum and an IES file as the source shape; the IES files sit at the top of the demo folder, not under `geometry/`, `materials/` or `maps/`; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, tabulated channels, 480 x 240; one-entry `.ppd`; one task.
3. SDK status: atmosphere unsupported; scene partial or unsure: the scene copy links only `geometry/`, `materials/` and `maps/` (E-SCN), so IES files elsewhere may not resolve, depending on how DIRSIG resolves the source-shape path (not tested); platform partial; motion and task supported.
4. Reference run: rendered, 18.1 s, deterministic (sweep). Survey `near`.
5. Gaps: BasicAtmosphere `.atm`; demo platform form; possibly scene files outside the linked folders. Comparison: exact plausible.

### Sources6 (`demo.sim`)

1. A car with working head and tail lights driving through a parking lot.
2. Features: `BasicAtmosphere` (`uniformradiativetransfer`, `uniformweather`, `turbulence`); implicit ephemeris; one scene with nested geometry lists (bundled car and parking-lot geometry, each with its own material file and source intensity files) and one `dynamicinstance` moved by a `generic` motion file under `geometry/`; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, rectangular channels, 320 x 240, frame clock 8 Hz; one-entry `.ppd`; one task.
3. SDK status: atmosphere unsupported; scene supported (E-SCN); platform partial; motion and task supported.
4. Reference run: rendered, 44.1 s; repeats differed in the truth image only (sweep; not probed, likely the optical-property renumbering the probe found in two other truth-only demos).
5. Gaps: BasicAtmosphere `.atm`; demo platform form. Comparison: radiance exact plausible; truth with the label band mapped (determinism probe).

### SubPixelObject1 (`demo.sim`)

1. A small box moving across a grass plate, smaller than a pixel of a 64 x 48 camera, with abundance and sample-count truth: sub-pixel target detection.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); implicit ephemeris; one scene with a `gdb` plate, a texture map, static instances and one `dynamicinstance` on `flexible` motion (`waypoints` location, `velocity` orientation) inside the scene; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, rectangular channels, 64 x 48, truth (Intersection, Material, Sample Count, Abundance); one-entry `.ppd`; one task.
3. SDK status: atmosphere unsupported; scene supported, including the object's waypoint motion (E-SCN, scene content); platform partial (the truth collectors stay in a template); motion and task supported.
4. Reference run: rendered, 44.1 s, deterministic (sweep). Survey `near`.
5. Gaps: BasicAtmosphere `.atm`; demo platform form. Comparison: exact plausible.

### SubPixelObject2 (`demo.sim`)

1. Two cars moving over grass, seen in the 8 to 12 um thermal infrared with an exposure integrated over ten time samples, with temperature truth.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`), with the weather driving temperatures; implicit ephemeris; one scene with a `groundplane` and two `dynamicinstance`s on `delta` motion files, BRDF-fitted paint and glass; `BasicPlatform` (`hyper.platform`): static mount, `generic`, `simple` capture, `central` sampling, `temporalintegration` (25 ms, 10 samples), rectangular channels over 8 to 12 um, 320 x 240, truth (Intersection, Material, SampleCount, Temperature); one-entry `.ppd`; one task.
3. SDK status: atmosphere and weather unsupported (E-ATM, E-WTH); scene supported; platform partial, and the closest of these demos to a template, since it has temporal integration (E-PLT; the generator writes exposure time and sample count); motion and task supported.
4. Reference run: rendered, 62.1 s; repeats differed in the radiance and truth images (sweep).
5. Gaps: BasicAtmosphere `.atm` with uniform weather (thermal); demo platform form. Comparison: statistical at the default thread count; exact at one thread is plausible.

## SDA

### MoonSat2 (`demo.jsim`)

1. A textured Moon moving along waypoints, followed by a long-focal-length camera on a tracking mount.
2. Features: `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); no ephemeris plugin named; an empty `medium_list`; one scene with a `sphere`, a texture-mapped material and a `dynamicinstance` on `flexible` motion (`waypoints` location, `euler` orientation); `BasicPlatform`: `tracking` mount, `generic`, `simple` capture, `central` sampling, rectangular channels over 0.4 to 0.8 um, 320 x 240, truth (Material, Intersection, Normal, GeoIds, Geolocation, Shadow); one-entry `.ppd`; one task.
3. SDK status: atmosphere unsupported (E-ATM, E-WTH); ephemeris: the layered job would add `SpiceEphemeris` that the demo does not name (E-EPH; effect unsure); scene supported, including the Moon's motion (E-SCN); tracking mount unsupported or unsure (E-MNT); platform partial (E-PLT, E-UNITS); motion and task supported.
4. Reference run: rendered, 4.1 s. Determinism probe: radiance identical in every condition; the truth image differs only by the renumbering of the Moon material's optical-property index (`index-relabel`).
5. Gaps: BasicAtmosphere `.atm`; tracking mount; demo platform form; a run without an ephemeris plugin (or evidence that adding one changes nothing). Comparison: radiance exact; truth exact except the label band.

### Ssa1 (`demo.sim`)

1. A ground telescope at a fixed site tracking a communications satellite whose position comes from a two-line element set, with path right ascension and declination truth.
2. Features: `BasicAtmosphere` (`uniformradiativetransfer`, `uniformweather`, `turbulence`); implicit ephemeris; one scene (`demo_sgp4.scene`) with an `obj` satellite model with BRDF-fitted materials on a `dynamicinstance` with `flexible` motion (`sgp4` location engine, `lookat` orientation); platform motion: `flexible`, `fixed` geodetic location, `lookat` orientation whose target is an `sgp4` location engine with the same element set; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, focal length 400 m, rectangular channels over 0.4 to 0.9 um, 320 x 240, truth (Material, Shadow, GeoLocation, PathRightAscension, PathDeclination, ConvergenceStatus); one task; options file (`atm.sourceupdatedelta`, `atm.verbose`).
3. SDK status: atmosphere unsupported; scene supported, including the satellite's sgp4 motion (E-SCN); platform motion unsupported: a fixed site pointed by LookAt at a moving target is neither `static` nor `orbit` (E-MOT); platform partial; options file unsupported (E-OPT).
4. Reference run: rendered, 629.4 s in the sweep; two more renders (673 s, 655 s) gave the same digests as the sweep's (`docs/DIRSIG_determinism.md`): deterministic.
5. Gaps: BasicAtmosphere `.atm`; fixed-site LookAt motion with an sgp4 target; options file; demo platform form. Comparison: exact plausible, at the default thread count; each render takes about 11 minutes.

### EarthShine1 (`demo.jsim`)

1. A sphere lit both by the Sun and by sunlight reflected from the Earth, seen from a fixed site with a large 1280 x 960 camera.
2. Features: `EarthGrid` (a background image and grid lines for the Earth); `BasicAtmosphere` (`uniformradiativetransfer`, `uniformweather`, `turbulence`, an `ephemeris` element); `SpiceEphemeris`; one scene with a `sphere` on `flexible` motion at a `fixed` location; platform motion: `flexible`, `fixed` location, `lookat` at a `fixed` location with an up vector; `BasicPlatform`: static mount, `generic`, `simple` capture, `central` sampling, rectangular channels, 1280 x 960, truth (eight collectors including HitFractions and SampleCount); one task.
3. SDK status: `EarthGrid` unsupported (E-PLG); atmosphere unsupported; ephemeris supported (E-EPH); scene supported; platform motion unsupported (E-MOT, fixed-site LookAt); platform partial.
4. Reference run: rendered, 84.2 s, deterministic (sweep).
5. Gaps: `EarthGrid`; BasicAtmosphere `.atm`; fixed-site LookAt motion; demo platform form. Comparison: exact plausible.

### SpaceRendezVous1 (`lidar_rpo.jsim`)

1. A chaser closing on the Hubble telescope, both moved by trajectory and attitude files in an STK export format, imaged by a lidar (the file the sweep ran) or by a panchromatic camera (`pan_rpo.jsim`, not run by the sweep).
2. Features: `EarthGrid`; `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); `SpiceEphemeris`; one scene with an `obj` Hubble model on `flexible` motion (`waypoints` location and `quaternions` orientation from data files); platform motion: `flexible`, `waypoints` and `quaternions` from data files; `BasicPlatform` with a `tracking` mount and a `lidar` instrument (`protolidar` capture); one task list over 15 minutes.
3. SDK status: the lidar sensor was run, not analyzed (out of scope); `EarthGrid` unsupported (E-PLG); atmosphere unsupported; scene supported (E-SCN); platform motion unsupported (E-MOT, `waypoints`); tracking mount unsupported or unsure (E-MNT).
4. Reference run: rendered, 705.5 s (lidar); two more renders differed from each other and from the sweep's in `demo.bin` and `lidar_truth.img` (digests only; lidar, not analyzed).
5. Gaps for the imaging variant (`pan_rpo.jsim`): `EarthGrid`; BasicAtmosphere `.atm`; waypoint and quaternion motion from STK-format files; tracking mount; demo platform form; a reference run of that file. Comparison: not estimated (no imaging reference).

### LightCurve1 (`box_spin.jsim`)

1. A spinning box-shaped satellite on an orbit from a two-line element set, whose brightness over time as seen from a ground site is computed frame by frame.
2. Features: `LightCurve` (a sensor plugin with a location, bandpass, sample count, start time, duration and a target tag, writing one image per time step: 1,681 files, 13.5 GB); `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); no ephemeris named; one scene with an `obj` box with BRDF-fitted materials on `flexible` motion (`sgp4` location, `spin` orientation); no `BasicPlatform`.
3. SDK status: the sensor plugin is unsupported (E-NI, E-PLG); atmosphere unsupported; scene supported (E-SCN); artifact listing of 1,681 outputs measured (BACKLOG "Artifact listings at scale").
4. Reference run: rendered, 691.9 s; two more renders (749 s, 750 s) repeated 1,679 of the 1,681 outputs exactly; one frame (`cube_150.img`) and the light-curve table differ, in the new pair and against the sweep's render (digests only, `docs/DIRSIG_determinism.md`).
5. Gaps: the `LightCurve` sensor plugin as an engine member (or a BasicPlatform re-expression); BasicAtmosphere `.atm`. Comparison: not estimated.

### StkImport1 (`demo.jsim`)

1. A satellite imaging pass rebuilt from STK position and attitude reports, with the Earth drawn by `EarthGrid` instead of a scene, a colour camera and a data recorder.
2. Features: `EarthGrid`; no scene file; `BasicAtmosphere` (`simpleradiativetransfer`, `uniformweather`, `turbulence`); `SpiceEphemeris`; platform motion: `flexible`, `waypoints` and `quaternions` from report files; `BasicPlatform`: static mount, a `generic` instrument (`simple` capture, `central` sampling, rectangular channels, 640 x 480, truth with GeoLocation) and a `datarecorder` instrument with its own clock; one task.
3. SDK status: no-scene runs and `EarthGrid` unsupported (E-PLG); atmosphere unsupported; ephemeris supported; motion unsupported (E-MOT, `waypoints`); data recorder unsupported (E-NI); platform partial. The coverage survey notes the pass was rebuilt from a TLE in `notebooks/dirfm_tutorials/tutorial_orbit_to_ground.ipynb`, which is the orbit form, not this demo's motion.
4. Reference run: rendered, 24.1 s. Determinism probe: radiance and truth identical in every condition; the recorder text differs only in a generation time stamp (`metadata`).
5. Gaps: `EarthGrid` and runs without a scene; STK-report waypoints with quaternions; the data recorder; BasicAtmosphere `.atm`; demo platform form. Comparison: exact (recorder after masking the time stamp).

### MoonSat1 (`classic_atm.sim`, DIRSIG 4 only, not run)

1. The Moon seen from a static platform with a long focal length, under the classic radiative transfer.
2. Features: `BasicAtmosphere` (`classicradiativetransfer`, `uniformweather`, `turbulence`); implicit ephemeris; one scene with the Moon's materials; `BasicPlatform`: static mount, `generic`, `simple` capture with a `convergence` element, `central` sampling, 320 x 240, truth; one-entry `.ppd`; one task; options file (`atm.verbose`, `atm.minsolarmu`).
3. SDK status: atmosphere unsupported (classic radiative transfer); platform partial (the convergence settings stay in a template); options file unsupported.
4. Reference run: none; the sweep skipped it as DIRSIG 4 only.
5. Gaps: a DIRSIG 5 reference first; then the classic `.atm`, options file, demo platform form.

### Ssa2 (`demo.sim`, DIRSIG 4 only, not run)

1. The Hubble telescope and an Earth sphere at fixed Earth-centred positions, seen from a fixed Earth-centred site, with Earth-reflected light.
2. Features: `BasicAtmosphere` (`uniformradiativetransfer`, `uniformweather`, `turbulence`, `ephemeris`); implicit ephemeris; one scene with an Earth `sphere` and an `obj` Hubble model, both static; platform motion: `flexible`, `fixed` ECEF location, `lookat` at a `fixed` ECEF location; `BasicPlatform`: static mount, `generic`, `simple` capture, `adaptive` sampling, 320 x 240; one task.
3. SDK status: atmosphere unsupported; motion unsupported (fixed-site LookAt, ECEF); platform partial (the adaptive sampling stays in a template).
4. Reference run: none (DIRSIG 4 only).
5. Gaps: a DIRSIG 5 reference; BasicAtmosphere `.atm`; fixed-site LookAt; demo platform form.

### Ssa3 (`demo.sim`, DIRSIG 4 only, not run)

1. An Earth-observing satellite on an orbit from an element set, seen by a platform that is itself on an element-set orbit and points at it.
2. Features: `BasicAtmosphere` (`uniformradiativetransfer`, `uniformweather`, `turbulence`, `ephemeris`); implicit ephemeris; one scene with an Earth `sphere` and an `obj` model on `flexible` motion (`sgp4` location, `velocity` orientation); platform motion: `flexible`, `sgp4` location, `lookat` at an `sgp4` target with an up vector; `BasicPlatform`: static mount, `generic`, `simple` capture, `adaptive` sampling, focal length 3 km, 320 x 240; one task.
3. SDK status: atmosphere unsupported; platform motion partial: the `orbit` kind propagates an element set itself and points by LookAt at a fixed scene point along track, not at another orbiting object, and it does not use DIRSIG's `sgp4` engine (E-MOT; BACKLOG "Ssa1 against the orbit form"); platform partial.
4. Reference run: none (DIRSIG 4 only).
5. Gaps: a DIRSIG 5 reference; BasicAtmosphere `.atm`; LookAt at a moving target from an orbit; demo platform form.

## Loader gaps across the tagged demos

Counts are the tagged demos whose simulation file needs the feature (URSO / SDA); the three DIRSIG 4 demos are included in the counts but have no reference. "Unblocks" lists the demos that would have no remaining gap once this feature and the features ranked above it exist.

| Rank | Candidate loader feature | URSO | SDA | Unblocks |
|---|---|---|---|---|
| 1 | BasicAtmosphere `.atm` (simple, uniform and classic radiative transfer, `turbulence`) with uniform weather from an installation `.wth` (E-ATM, E-WTH) | 9 | 9 | none alone |
| 2 | Demo platform form: a demo's `.platform` used as authored, or a sensor-spec holding a demo camera's values with its radiance units (E-PLT, E-UNITS) | 9 | 7 | URSO: Indoors1, Sources6, SubPixelObject1, SubPixelObject2, and IESSources1 if its IES files resolve |
| 3 | Simulation options file, or the engine-run options it sets (E-OPT) | 4 | 2 | URSO: Sources1, Sources3, Sources4, Sources5 |
| 4 | Fixed-site LookAt platform motion, with a fixed or an `sgp4` target (E-MOT) | 0 | 3 | SDA: Ssa2 (no DIRSIG 5 reference); with 3, Ssa1 |
| 5 | `EarthGrid`, and runs without a scene file (E-PLG) | 0 | 3 | SDA: EarthShine1 (with 4) |
| 6 | Tracking mount (E-MNT) | 0 | 2 | SDA: MoonSat2 (with item 10) |
| 7 | Waypoint and quaternion motion from STK-format files (E-MOT) | 0 | 2 | none alone (StkImport1 also needs 5 and 8; SpaceRendezVous1's imaging variant needs 5 and 6) |
| 8 | Non-imaging instruments: the data recorder; the `LightCurve` sensor plugin (E-NI) | 0 | 2 | SDA: StkImport1 (with 5 and 7); LightCurve1 |
| 9 | LookAt at a moving target from an orbit (E-MOT, the `orbit` kind) | 0 | 1 | SDA: Ssa3 (no DIRSIG 5 reference) |
| 10 | Ephemeris as authored: a run without an ephemeris plugin, and evidence that a legacy `.sim`'s implicit ephemeris equals `SpiceEphemeris` (E-EPH) | 7 | 5 | SDA: MoonSat2 (with 6); for the `.sim` demos, a check rather than a feature |
| 11 | Scene files outside `geometry/`, `materials/` and `maps/` (E-SCN; unsure) | 1 | 0 | URSO: IESSources1, if needed |

Ranking: by the number of tagged demos that need the feature, then by how cheap their references are. Items 1 and 2 are needed by nearly every tagged demo and by the 62 survey `near` demos with references (BACKLOG "Loader features for demos"); everything else is SDA-specific.

**First layered target, URSO: Indoors1.** It needs only items 1 (uniform radiative transfer) and 2; it names `SpiceEphemeris`, so the implicit-ephemeris question does not arise; its reference renders in 8 s and repeats bit for bit; and the coverage survey already marks it `near`. SubPixelObject1 (44 s, deterministic, the same two items, but a legacy `.sim`) is the second.

**First layered target, SDA: MoonSat2.** It needs items 1, 2, 6 and 10, the fewest of the SDA demos that have a DIRSIG 5 reference; its reference renders in 4 s; and the determinism probe showed its radiance is identical in every condition, so a layered radiance image can be compared exactly. EarthShine1 (84 s, deterministic) needs 1, 2, 4 and 5 and is the second.
