# SatSim probe

The adapter this probe informed now exists: `eoptic-manifold-engine-satsim` (pass-through form, `proposed`; CONOPS and Guide section 7.4), with its first run recorded in `docs/SatSim_reference_run.md`. The findings below are the probe's, unchanged.

SatSim is the planned second engine. This probe installed it into its own environment on the development machine and measured what an engine adapter and the descriptor audit need: how it installs and runs, what it costs on CPU, what it writes, whether its outputs repeat, what it touches outside its output folder, and how its configuration maps onto the run-spec descriptor. Nothing in the repository's code, contracts or schemas changed. All runs were on CPU (the machine has no GPU); the GPU items are listed at the end. The probe ran on 2026-10-11.

## Machine and setup

| Item | Value |
|---|---|
| CPU | 11th Gen Intel Core i5-1135G7 @ 2.40 GHz, 4 cores, 8 threads |
| Memory | 10 GB |
| Free disk | 355 GB |
| Operating system | Ubuntu 26.04.1 LTS, kernel 7.0.0-38-generic |
| GPU | none (`nvidia-smi` not installed); TensorFlow reports no CUDA driver |
| conda | 26.7.2 (base Python 3.14.6) |
| Environment | `satsim`, Python 3.11.17, created for this probe; the SDK's `protodirsig` environment was not modified |

## Install recipe

Published metadata of `satsim` 0.26.1, the latest of 34 versions on PyPI (0.12.0 to 0.26.1): no `Requires-Python` field; classifiers name Python 3.8 to 3.12; dependencies with lower bounds only, apart from `astropy>=5.2.1,<6` and `asdf>=2.14.3,<3`; `tensorflow>=2.4` with no upper bound; others include `skyfield`, `sgp4`, `poppy`, `numba`, `pooch`, `diskcache`, `scikit-image`, `czmlpy`, `tifffile`, `imagecodecs`. Python 3.11 was chosen as inside the classifier range and supported by current TensorFlow wheels.

```bash
conda create -y -n satsim -c conda-forge --override-channels python=3.11 pip   # 14 s
~/anaconda3/envs/satsim/bin/pip install satsim==0.26.1                          # 145 s, CPU TensorFlow from PyPI
```

| Package | Version |
|---|---|
| satsim | 0.26.1 |
| tensorflow | 2.21.0 (CPU; keras 3.15.1) |
| numpy | 1.26.4 |
| astropy (FITS writer and reader) | 5.3.4 |
| skyfield | 1.55 |
| poppy | 1.1.2 |
| numba | 0.68.0 |
| scipy | 1.17.1 |

The environment is 3.0 GB on disk. Install and run commands use the environment's own executables; nothing is activated in the SDK's environment.

## License

The installed distribution states `License: UNKNOWN` in its metadata and has no license classifier. The only file declared as a license file is `AUTHORS.md`, which names the development lead and no copyright holder; the distribution contains no LICENSE or COPYING file. The project description says the source was developed under contract with AFRL/RDSM and was approved for public release (an AFRL public-affairs release number is cited); that is a release approval, not a license. One bundled module carries a third-party notice: the Hosek–Wilkie sky model reference code is stated to be under the 3-clause BSD license (copyright 2012–2013, Lukas Hosek and Alexander Wilkie). No license for SatSim itself is stated in the installed distribution.

## CLI surface

`satsim [--version] [-d/--debug LEVEL] COMMAND`, with two commands: `run` and `version`. There is no template, init or example command, and the wheel ships no example configuration; the configuration structure was learned from the package's code.

`satsim run [OPTIONS] CONFIG_FILE` reads `.yml`, `.yaml` or `.json` and dispatches on the root: exactly one of `fpa` (EO imaging), `radar` or `passive_rf` (analytical observations). Its options:

| Option | Bears on | Behavior |
|---|---|---|
| `-d/--device` | device selection | GPU device ids, default `0`; on a machine without a GPU it is accepted and the run uses the CPU |
| `-r/--memory` | memory | GPU memory limit per process, MB |
| `-j/--jobs` | processes | jobs per GPU device; more than one job starts a multiprocessing pool and divides `sim.samples` between the jobs |
| `-m/--mode` | run mode | TensorFlow mode; only `eager` is supported |
| `-o/--output_dir` | output location | default `./`; each set is written into a new subfolder named by the local wall-clock time |
| `-i/--output_intermediate` | debug output | intermediate images as pickles |

No option sets CPU thread counts or a random seed. The Python API (`gen_multi`, `load_yaml`) is documented in the package description and is what the CLI calls.

## Sample configuration

`docs/data/satsim_probe_config.yaml` is the probe's sample, written for this probe: a ground site near Lake Tahoe (39.1 N, 120.03 W, 1.9 km) tracks WorldView-2 (NORAD 35946, from the repository's pinned TLE) in rate-track mode through three 0.1 s frames, 0.5 s apart, around the 2026-09-26 18:51:25 UTC culmination (87.5 degrees elevation, 771 km range by SatSim's own computation); a 64 x 64 focal plane over 0.4 degrees; a Gaussian PSF; a uniform sky of 19.5 mag/arcsec²; stars drawn from a magnitude-density table, which needs no catalog; no clouds; target brightness magnitude 8. The target is annotated at the frame centre with an SNR of about 36. The first draft placed the collect 25 hours earlier, when the satellite was 5 degrees below the horizon; SatSim rendered and annotated it without complaint.

A 40-frame, 256 x 256 variant (the same file with a larger focal plane and frame count, not committed) was used for the interruption and thread tests.

## Cost

| Run | Wall time | CPU time (user + system) | Peak RSS | Threads (max) | Processes |
|---|---|---|---|---|---|
| `satsim --help` (startup: TensorFlow import) | 3.16 s | | 737 MB | | 1 |
| A failing configuration (exit at load) | 3.0 to 3.1 s | | | | 1 |
| Sample, first run (downloads `de421.bsp`) | 15.6 s | 10.4 s | 858 MB | | 1 |
| Sample, ephemeris present | 4.4 s | 9.6 s | 856 MB | 37 | 1 |
| 40 frames at 256 x 256, defaults | 11.6 to 12.7 s | 52 to 56 s | 904 to 908 MB | 37 | 1 |
| 40 frames, TensorFlow pools set to 1 thread (Python API) | 13.0 to 13.1 s | 54 s | 905 MB | 23 | 1 |
| 40 frames, `TF_NUM_INTRAOP_THREADS`, `TF_NUM_INTEROP_THREADS`, `OMP_NUM_THREADS`, `NUMBA_NUM_THREADS` = 1 (CLI) | 10.2 s | 10.1 s | 901 MB | 9 | 1 |

About 3 s of every run is the TensorFlow import. At default settings most CPU time is system time (34 s of 54 s on the 40-frame case), which the four environment variables remove: the same work then takes 10.1 s of CPU instead of about 55 s and finishes sooner, so the default thread pools spin rather than work on this 8-thread machine. Limiting only TensorFlow's own pools through its documented API reduced the thread count to 23 but not the CPU time.

## Outputs

One set (a `sim.samples` of 1) writes into `<output_dir>/<YYYY-MM-DDTHH-MM-SS.ffffff>/`, the folder named by local wall-clock time; the sample's 19 files:

| Path in the set folder | Format | Role | Notes |
|---|---|---|---|
| `ImageFiles/sat_00000.NNNN.fits` | FITS, one 2-D uint16 HDU (`BZERO` 32768) | frame | header: observation time (`DATE-OBS`, `TIME-OBS`, `SH-UT001`: the middle of the exposure, and `SH-UT002`: the middle plus the exposure, measured in round 31 (`docs/Space_to_space_characterization.md`); simulated time, not wall-clock), exposure (`EXPTIME`, `EXPOSURE`), site (`SITELAT`, `SITELONG`, `SITEALT`), pointing (`CENTAZ`, `CENTALT`, `OBJCTRA`, `OBJCTDEC`, `RA-OBJ`, `DEC-OBJ`, `RA-APP`, `DEC-APP`, `TELTKRA`, `TELTKDEC`, `TRKMODE`), a TAN WCS (`CTYPE*`, `CRVAL*`, `CRPIX*`, `CDELT*`, `CD*_*`, `CROTA*`, `RADESYS GAPPT`), `BIAS`, display stretch `CBLACK`/`CWHITE` (computed from the pixels), binning keys, `SWCREATE 'SATSIM 0.26.1'`, and empty or zero instrument keys (`OBSERVER`, `OBJECT`, `INSTRUME`, `FILTER`, `FOCALLEN`, `APTDIA`); no path, host name, user name or wall-clock timestamp |
| `Annotations/sat_00000.NNNN.json` | JSON | annotation (SatNet layout) | `data.file` (`dirname`: the set folder's name, so the run's wall-clock time; `filename`, `sequence`, `sequence_id`), `data.sensor` (size, IFOV), `data.objects[]` (class, bounding box and centre in normalized coordinates, start/mid/end positions, magnitude, pe/s, per-frame SNR, pixels, segmentation id, observed and catalog RA/Dec), `data.stats`, `data.metadata` (site, track mode, pointing, range, rates, az/el, time, FOV, frame number, background model) |
| `AnnotatedImages/sat_00000.NNNN.jpg` | JPEG | preview | the frame stretched to 8 bits with annotation boxes drawn |
| `AnnotatedImages/movie.png` | animated PNG | movie | the previews in sequence; written at the end |
| `satsim.czml` | CZML (JSON) | visualization | site and object trajectories; written at the end |
| `config.json` | JSON | provenance config | the input configuration with every random draw resolved, plus `_input_dir`, the absolute folder of the configuration file (machine-specific) |
| `config_pass_1.json` to `config_pass_7.json` | JSON | intermediate configs | the configuration after each pass of SatSim's transform (imports, references, samples, generators, functions); identical to each other for this configuration and to `config.json` apart from `_input_dir`; written at the end |

Optional products not produced by the sample (flags under `sim`): segmentation masks and ground-truth planes (TIFF), cloud-transmission planes, pickles, analytical observations under `AnalyticalObservations/`, and the radar and passive-RF outputs.

## Side effects and network

| Where | What | When |
|---|---|---|
| Current working directory | `de421.bsp` (JPL planetary ephemeris, 16.8 MB, sha256 `a20a7139da04…`), downloaded by skyfield's default loader | every run in a working directory that lacks it, unless `SATSIM_SKYFIELD_LOAD_DIR` names a folder that holds it |
| `$HOME/.astropy/cache/download/url/` | `finals2000A.all` (IERS Earth orientation, 3.8 MB) and `Leap_Second.dat` (1.4 kB), downloaded by astropy | the first run under a given home |
| `$HOME/.keras/keras.json` | Keras backend settings | first import of TensorFlow |
| `$HOME/.cache/matplotlib`, `$HOME/.config/matplotlib` | font cache, config folder | first run under a given home |
| `$TMPDIR` | nothing | |

Hosts contacted by SatSim runs: `ssd.jpl.nasa.gov` (`/ftp/eph/planets/bsp/de421.bsp`), `datacenter.iers.org` (`/data/9/finals2000A.all`) and `hpiers.obspm.fr` (`/iers/bul/bulc/Leap_Second.dat`). The install contacted `conda.anaconda.org` (conda-forge) and `pypi.org` with `files.pythonhosted.org`. With `HOME` set to an empty folder, a clean `TMPDIR` and an empty working directory, the run succeeded, recreated the files above in those folders and downloaded all three files again (19.6 s instead of 4.4 s). A run with the ephemeris and the astropy cache in place used no network. Star catalogs are not downloaded: the `sstr7` catalog is read from `geometry.stars.path` or `SATSIM_SSTR7_PATH`, the variable-star catalog from `SATSIM_GCVS5_PATH`; the `$cache` directive of a configuration writes a `diskcache` folder, `.satsim_cache`, inside the folder it names.

## Failure and interruption

| Case | Exit code | Message | Output left |
|---|---|---|---|
| Malformed YAML | 1 | YAML parser traceback with line and column | none |
| No `fpa`, `radar` or `passive_rf` at the root | 1 | one-line error naming the three roots | none |
| A required member missing (`fpa.time`) | 1 | Python `KeyError` traceback | none |
| A missing file named by `$import` | 1 | `FileNotFoundError` traceback naming the path | none |
| A missing star catalog (`stars.mode: sstr7` without `path`; with a path that does not exist) | 1 | `KeyError: 'path'`; `FileNotFoundError` naming the catalog index file | none; an empty set folder |
| SIGTERM at 8 s of a 12 s run | killed by the signal (no handler; exit status -15 as a subprocess) | none | `config.json` and the frames completed so far (30 of 40 FITS, annotations and previews, all readable, contiguous from frame 0); no `config_pass_*`, `movie.png` or `satsim.czml` |
| SIGKILL at 8 s | killed (-9) | none | as SIGTERM (27 of 40 frames) |

Each failing configuration costs the 3 s TensorFlow import before it fails. A partial run is distinguishable from a complete one only by what is written at the end: the seven `config_pass_*.json`, and `movie.png` and `satsim.czml` when enabled. No completion marker or status file is written, and the frames already written are complete files, so a reader that does not check the frame count or the end-of-run files cannot tell.

## Repeatability

Comparisons used a scratch script in the `satsim` environment: byte equality, then for FITS frames the maximum, mean and RMS absolute difference and the fraction of differing pixels, for previews the decoded 8-bit pixels, and for JSON a structural walk with absolute paths, home and temporary folders, ISO timestamps and process ids masked. Classes: `identical` (bytes); `metadata` (equal after masking, or pixels equal with only a header key different); `float-order` (integer frames: every differing pixel within 1 count and at most 1 percent of pixels; numbers: within 1e-6 relative), the size of a rounding-boundary flip of an accumulated float, since frames are integer counts and a different summation order can move a value across a rounding boundary but not further; `sampling-noise` (anything larger).

| Comparison | Frames (FITS) | Previews and movie | Annotations | `config.json`, passes, CZML |
|---|---|---|---|---|
| CLI, defaults, two runs | sampling-noise: RMS 13.4 counts, 97 % of pixels, max 74; headers differ in `CBLACK`/`CWHITE` | sampling-noise | metadata (the set-folder name) | identical |
| CLI, read noise, dark current and shot noise off, two runs | sampling-noise: 5 % of pixels, max 20 counts, the difference is whole stars present in one run and absent in the other | identical (below the 8-bit stretch) | metadata | identical |
| CLI, target magnitude drawn by `$sample` with `seed: 42`, two runs | sampling-noise | sampling-noise | metadata | identical: the draw resolves to the same value |
| `seed: 42` against `seed: 7` | sampling-noise | sampling-noise | sampling-noise (the magnitude) | differ in the resolved magnitude |
| Python API, numpy and TensorFlow global seeds set (`np.random.seed`, `tf.random.set_seed`), seed 1, two runs | identical | identical | metadata | identical |
| Same, seed 1 against seed 2 | sampling-noise | sampling-noise | metadata | identical |
| Python API, seed 1, TensorFlow pools at 1 thread, two runs; and against default threads | identical | identical | metadata | identical |
| 40 frames at 256 x 256, seed 1, default threads twice, 1 thread twice, and default against 1 thread | identical (40 of 40) | identical | metadata | identical |

Three sources of randomness, found in the code and confirmed by the runs: the `bins` star field is drawn from numpy's global random state; shot, read and dark noise are drawn with TensorFlow random operations without an operation seed; and `$sample` draws in the configuration are resolved when the configuration is transformed. The configuration has no global seed. A `seed` member on a `$sample` node (`{"$sample": "random.uniform", "low": 7, "high": 9, "seed": 42}`) makes that draw and its nested draws reproducible, and the resolved values are recorded in `config.json`; it does not reach the star field or the noise. The CLI has no seed option, so CLI runs never repeat. Through the Python API, setting numpy's and TensorFlow's global seeds before `gen_multi` made every image byte-identical on CPU, at the default thread count and at one thread, and the one-thread results equal the default-thread results: no summation-order effect appeared, unlike DIRSIG's multi-threaded renders. Restricting TensorFlow's pools to one thread cost about 12 percent wall time on the 40-frame case (13.0 s against 11.6 s); the four thread environment variables instead saved time. Annotations always differ in `data.file.dirname`, the wall-clock folder name.

## Mapping onto the descriptor

One row per SatSim configuration concept, against `run-spec/1`'s descriptor (`collection`, `sensor`, `settings`, `fidelity`) and `sensor-spec/1`; "engine block" means the member belongs in a SatSim engine section, as the DIRSIG engine's motion, tasks and scenes do in `dirsig-engine/1`. Verdicts: **clean** (maps cleanly), **convert** (maps with a unit or frame conversion), **none** (no home in the descriptor).

| # | SatSim concept and key path | Physical meaning | Nearest descriptor member | Verdict | Note |
|---|---|---|---|---|---|
| 1 | `geometry.time`, `[Y, M, D, h, m, s]` | UTC start of the first exposure | `collection.epoch` | convert | list to ISO 8601; both mark the collect's start |
| 2 | `fpa.time.exposure` (s) | integration time of each frame | `settings[].exposure_time` | clean | seconds on both sides |
| 3 | `fpa.time.exposure` + `fpa.time.gap` (s) | frame period | `settings[].frame_rate` | convert | frame rate = 1 / (exposure + gap) |
| 4 | `fpa.num_frames` | frames in the collect, hence its duration | none | none | the descriptor states no frame count or collect duration (DIRSIG keeps them in `engine.tasks`) |
| 5 | `geometry.site.lat`, `lon` (deg), `alt` (km) | ground observer | `collection.platform.position` | convert | km to m; SatSim does not state the altitude reference |
| 6 | `geometry.site.tle`, `tle1`/`tle2`, `position`/`velocity`/`epoch` (km, km/s), `positions`/`velocities` | space observer and its orbit | `collection.platform.class` and the position at the epoch | none | the trajectory has no descriptor home; an engine block, as DIRSIG's orbit motion |
| 7 | `geometry.site.track.mode` (`rate`, `sidereal`, `fixed`, `radec`, `rate-sidereal`) with a track target (TLE, state vector, az/el, RA/Dec) | how the boresight moves during the collect | `collection.geometry.regime` | none | a governed term such as `orbital_nadir` cannot carry the mode or its target |
| 8 | `geometry.site.gimbal.rotation` (deg) | field rotation of the focal plane | none (`sensor` entry `mount` is an unconstrained object) | none | |
| 9 | slant range, computed by SatSim (`metadata.range`, km, an output) | sensor-to-target range | `collection.geometry.range` | convert | km to m; computed from the geometry, not input |
| 10 | `geometry.obs.list[].mode` (`tle`, `twobody`, `gc`, `ephemeris`, `observation`, `line`, `line-polar`) with its parameters | target trajectories, in orbit or on the image plane | `collection.targets[]` | none | targets carry only a class; SatSim has no input class (annotations say `Satellite`) |
| 11 | `geometry.obs.list[].mv`, or `model` (Lambertian sphere: size, albedo; a sprite file) | target brightness | none | none | the descriptor has no target radiometry |
| 12 | `geometry.stars.mode`: `bins` (`mv.bins`, `mv.density`) or `sstr7`/`csv` (`path`) | star field: random by magnitude density, or a catalog | `collection.background.regime` | none | a catalog is an asset needing a library ref and hash; `bins` is unseeded |
| 13 | `geometry.stars.motion` | apparent star motion | none | none | |
| 14 | `background.galactic` (mag/arcsec²), `skyglow`, `stray` | diffuse sky brightness | `collection.background.regime` | none | a number cannot be recovered from a governed term |
| 15 | `background.moon`, `twilight`, `daytime` (`mode`) | Sun, Moon and twilight sky models | `collection.illumination.regime` | convert | a mode maps to a governed term; any parameters do not |
| 16 | `clouds` (procedural layers, motion, seed) | cloud attenuation and glow | `collection.atmosphere.regime` | none | parameters and their seed are engine input |
| 17 | `fpa.height`, `fpa.width` (px) | focal-plane array size | sensor `detector.SensorHeight`, `SensorWidth` | clean | |
| 18 | `fpa.crop` | readout window | `settings[].roi` | clean | the same window under GenICam names |
| 19 | `fpa.y_fov`, `fpa.x_fov` (deg) | field of view, hence pixel scale | sensor `optics.focal_length` with `detector.SensorPixelHeight`, `SensorPixelWidth` | convert | IFOV = pixel pitch / focal length; SatSim takes the angle |
| 20 | `fpa.psf.mode: gaussian`, `eod` | blur by energy on detector | none | none | `sensor-spec/1` has no PSF member |
| 21 | `fpa.psf.mode: poppy` (aperture, obscuration, wavelengths and weights) | diffraction-limited PSF | sensor `optics.aperture_diameter`, channel band and SRF | convert | mm to m; wavelength weights from the band |
| 22 | `fpa.zeropoint` (magnitude giving 1 pe/s) | the whole radiometric chain: band, optics throughput, QE, aperture | sensor channel `band`, `srf_*`, `qe_reference`, optics `throughput_*`, `aperture_diameter` | convert | one way only: computable from the sensor-spec and a source spectrum; SatSim has no band or QE |
| 23 | `fpa.dark_current` (pe/px/s) | dark signal | none | none | `sensor-spec/1` has no noise member |
| 24 | `fpa.noise.read`, `fpa.noise.electronic` (pe) | read and electronic noise | none | none | as 23 |
| 25 | `fpa.a2d.gain` (pe/ADU), `fpa.a2d.bias` (ADU), `fpa.gain`, `fpa.bias` | analog-to-digital conversion | `settings[].gain`, `settings[].black_level` | convert | `settings.gain` is dimensionless; a system gain in pe/ADU needs a stated definition |
| 26 | `fpa.a2d.fwc` (pe), `fpa.a2d.dtype` | full well, output type | `readout.AdcBitDepth` (library-asserted) | convert | dtype to bit depth; the full well has no home |
| 27 | `sim.enable_shot_noise`, `num_shot_noise_samples` | which noise is modelled | `fidelity.modeled` | convert | as fidelity text |
| 28 | `sim.mode`, `spatial_osf`, `temporal_osf`, `padding`, `point_rendering`, `enable_light_transit`, `enable_stellar_aberration`, `enable_deflection` | numerical model choices | `fidelity` (as text) | none | values belong in an engine block |
| 29 | `sim.save_*`, `fits_compression`, `show_obs_boxes`, `show_star_boxes` | which products are written | none | none | the API's artifact roles describe products, not requests |
| 30 | `seed` on a `$sample` node; no global seed | reproducibility of configuration draws | none | none | `dirsig-engine/1` has `run.seed`, engine-side |
| 31 | `sim.samples` with `$sample`/`$generator`/`$function`/`$pipeline` | several randomized sets from one configuration | none | none | the SDK expresses variation as a sweep of run specs |
| 32 | `radar`, `passive_rf` roots; `sim.analytical_obs` | non-imaging analytical observations | none | none | |

Count: 3 clean, 11 convert, 18 none (32 concepts). Gaps (no proposals):

1. **Targets.** `collection.targets` holds only a class; a SatSim target is a trajectory (TLE, state vector, ephemeris, image-plane line) and a brightness (magnitude or a reflectance model), and neither has a descriptor home (rows 10 and 11).
2. **Observer motion and pointing.** The descriptor holds a geodetic position at the epoch and a governed geometry term; a space observer's orbit, the track mode and its track target, and the field rotation have no home (rows 6 to 8).
3. **Detector noise and radiometric scale.** `sensor-spec/1` describes band, QE and optics but no dark current, read noise, full well or PSF, while SatSim needs those and takes its radiometry as a single photometric zeropoint; one direction of conversion exists (sensor-spec to zeropoint) and the noise has no home (rows 20 and 22 to 26).

Also without a home: the frame count and collect duration, the star field and its catalog, the sky brightness and clouds as numbers, product requests, Monte Carlo sets, and a seed.

## Engine-adapter requirements

Facts the probe establishes for an adapter that runs SatSim behind the engine adapter protocol:

1. **Interpreter.** Python 3.8 to 3.12 by the package's classifiers (no `Requires-Python`); probed with Python 3.11.17, TensorFlow 2.21.0 (CPU), numpy 1.26.4, astropy 5.3.4.
2. **Separate environment.** Required in practice: the environment is 3.0 GB, pins `astropy<6` and `asdf<3`, and carries TensorFlow; the SDK's environment must not take these. The adapter launches the environment's own `satsim` executable or a Python launcher in that environment as a subprocess.
3. **Launch.** `satsim run --device 0 -o <out> <config>` (YAML or JSON), or the Python API `gen_multi(ssp, True, out, input_dir, 0, None, 0, False)`, which the CLI calls; a launcher is needed for global seeds (item 10).
4. **Cancel.** SIGTERM or SIGKILL; there is no handler and no cleanup. Frames written before the signal are complete files; the end-of-run files are missing.
5. **Startup cost.** About 3.0 to 3.2 s and 740 MB for the TensorFlow import, paid by every run, including one whose configuration fails to load.
6. **Resources it consumes and could declare.** CPU: 37 threads in one process by default on 8 logical CPUs, with most CPU time spent in system time; `TF_NUM_INTRAOP_THREADS`, `TF_NUM_INTEROP_THREADS`, `OMP_NUM_THREADS` and `NUMBA_NUM_THREADS` set to 1 reduce it to 9 threads and about a fifth of the CPU time, with a shorter wall time. Memory: 0.85 to 0.91 GB peak for 64 x 64 to 256 x 256 frames. Devices: GPU ids (`--device`), GPU memory per process (`--memory`), jobs per GPU (`--jobs`, multiprocessing) — unverified.
7. **Isolation controls.** `-o` for products (the adapter must find the timestamped set folder inside it); `SATSIM_SKYFIELD_LOAD_DIR` for the ephemeris (otherwise the working directory); `HOME` for the astropy, Keras and matplotlib caches (a per-run home works but downloads again); `SATSIM_SSTR7_PATH` and `SATSIM_GCVS5_PATH` or `geometry.stars.path` for catalogs; `TMPDIR` is not used.
8. **Network.** First runs download `de421.bsp` from `ssd.jpl.nasa.gov` and the IERS tables from `datacenter.iers.org` and `hpiers.obspm.fr`; with those files in place a run uses no network. A network-free run needs them provided as assets.
9. **Inputs to hash.** The configuration file; every file it references (`$import` targets, sprite files, catalogs, ephemeris files of targets or observers); `de421.bsp`; the IERS tables the run used, since they move apparent positions; the SatSim and TensorFlow versions.
10. **Seeds and determinism.** The CLI cannot repeat a run: the `bins` star field (numpy global state) and the detector noise (TensorFlow, no operation seed) are unseeded, and the configuration has no global seed. Through the Python API, global seeds made every product byte-identical on CPU, at default threads and at one thread. Configuration draws are reproducible with a per-node `seed` and are recorded resolved in `config.json`.
11. **Artifacts and roles.** Frames: `ImageFiles/*.fits`. Annotations: `Annotations/*.json`. Previews: `AnnotatedImages/*.jpg`. Movie: `AnnotatedImages/movie.png`. Visualization: `satsim.czml`. Provenance: `config.json` (resolved configuration). Intermediate: `config_pass_*.json`. Optional: segmentation and ground-truth TIFFs, cloud-transmission planes, pickles, analytical observations.
12. **Failures.** Exit status 1 with a Python traceback on stderr for most configuration errors (only the missing-root error is a one-line message); no structured error output; sometimes an empty set folder. A signal leaves no status.
13. **Its own provenance.** `SWCREATE 'SATSIM 0.26.1'` in each FITS header; the resolved configuration in `config.json`, with one absolute path (`_input_dir`); the simulated observation time in FITS headers and annotations; the wall-clock time only in the set folder's name. It records no TensorFlow version, seed, host or user.
14. **Unverified without a GPU.** GPU selection (`--device`), memory limits (`--memory`), multi-job execution (`--jobs`), GPU wall time and memory, and whether GPU results repeat with global seeds or equal CPU results.

## GPU follow-up checklist

On a machine with an NVIDIA GPU and a CUDA-enabled TensorFlow:

```bash
conda create -y -n satsim -c conda-forge --override-channels python=3.11 pip
~/anaconda3/envs/satsim/bin/pip install satsim==0.26.1 "tensorflow[and-cuda]"
nvidia-smi -L
~/anaconda3/envs/satsim/bin/python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
mkdir -p ephem && cp <de421.bsp from this probe or a first run> ephem/
SATSIM_SKYFIELD_LOAD_DIR=$PWD/ephem /usr/bin/time -v ~/anaconda3/envs/satsim/bin/satsim run --device 0 -o out_gpu docs/data/satsim_probe_config.yaml
SATSIM_SKYFIELD_LOAD_DIR=$PWD/ephem /usr/bin/time -v ~/anaconda3/envs/satsim/bin/satsim run --device 0 --memory 2048 -o out_gpu_mem docs/data/satsim_probe_config.yaml
SATSIM_SKYFIELD_LOAD_DIR=$PWD/ephem /usr/bin/time -v ~/anaconda3/envs/satsim/bin/satsim run --device 0 --jobs 2 -o out_gpu_jobs <the config with sim.samples: 2>
CUDA_VISIBLE_DEVICES= SATSIM_SKYFIELD_LOAD_DIR=$PWD/ephem /usr/bin/time -v ~/anaconda3/envs/satsim/bin/satsim run -o out_cpu docs/data/satsim_probe_config.yaml
```

Measure and compare with the CPU results above: wall time, peak host memory and GPU memory (`nvidia-smi --query-gpu=memory.used --format=csv -l 1` during the run), the startup cost, whether `--device` with an absent id fails or falls back, what `--memory` and `--jobs` change, and, with a launcher that sets numpy's and TensorFlow's global seeds, whether two GPU runs are byte-identical, whether GPU and CPU frames are identical or differ by float order (a 1-count flip at most) or more, and whether `TF_DETERMINISTIC_OPS=1` changes the GPU result.
