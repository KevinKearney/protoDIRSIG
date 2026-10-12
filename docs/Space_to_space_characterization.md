# Space-to-space characterization

Space-to-space imaging is a sensor in orbit imaging an orbital target, with the Earth or space as the background. This document records what the SDK covers for it. Everything here is additive to the tag the MANIFOLD team is assessing (review-r27, 9ded055): no new member of `dirsig-engine-1`, no change to `run-spec/1`, `packages/core` or the adapter protocol. Where the SDK cannot express an axis, the gap is recorded with minimal evidence and listed in `BACKLOG.md`; the spec is not extended to close it. The run-spec contract, the motion forms and the SatSim adapter are described in the [CONOPS and Guide](MANIFOLD_DIRSIG_CONOPS_and_Guide.md) (sections 3.2, 7.4 and 9); this document cites them rather than restating them.

## Coverage audit (round 29, at 796ecd5)

**Sources read.** `notebooks/stage_04_leo_pass.ipynb`; `packages/core/src/manifold/core/orbit.py` and `tle.py`; `packages/engine-dirsig/src/manifold/engines/dirsig/motion_tasks.py` and `run_spec.py` (the motion, settings and atmosphere members it resolves); `tests/test_leo_pass.py`, `tests/test_orbit.py`, `tests/test_orbit_motion.py`, `tests/test_orbit_vector.py`, `tests/test_motion_tasks.py`; the demo survey and sweep (`docs/DIRSIG_demo_coverage.md`, `docs/DIRSIG_demo_sweep.md`), the tagged-demo notes (`docs/DIRSIG_tagged_demo_features.md`), the layered comparison (`docs/DIRSIG_layered_comparison.md`), the determinism probe (`docs/DIRSIG_determinism.md`), `docs/SatSim_probe.md` and `docs/SatSim_reference_run.md`.

**What exists, DIRSIG.** Platform motion has two generated forms (CONOPS section 3.2): `static` (a scene-frame position and an `xyz` Euler orientation in `sceneenu`) and `orbit` (a library TLE propagated by SGP4 with UT1–UTC over a window, ECEF waypoints, a LookAt at a scene ENU point with a fixed along-track up). The orbit form was built and checked for a ground-imaging pass: `tests/test_leo_pass.py` recovers the platform position from each 16 x 16 frame's truth to under a metre and lands the frame centre on the LookAt target; the golden vector (`tests/test_orbit_vector.py`) pins the propagator to 0.1 m. Exposure time is `settings[].exposure_time`, written as the platform's `temporalintegration` time with `engine.platform.integration_samples`; DIRSIG5 spreads ray times uniformly over the window. The Sun is set by the epoch with `SpiceEphemeris`, or directly by `engine.atmosphere.uniform` or `simple` with a `fixed_ephemeris` (solar zenith and azimuth). A scene object moves only as its scene file authors it: the Tahoe scene's vehicle flies a `straight` line at 100 m/s and 50 km altitude, fixed in the library asset. Sub-pixel objects: an instance named `::IMPORTANT::` is hypersampled; point sources are not drawn when viewed directly; an unresolved object is real geometry at true scale or a flux-matched emitter (CONOPS section 9, "Rendering and sampling").

**What exists, SatSim.** The adapter runs SatSim's own configuration as authored (pass-through, `satsim-engine/1`; CONOPS section 7.4). Its one run (`docs/SatSim_reference_run.md`) is a ground site rate-tracking WORLDVIEW-2 from the library TLE: a target moving on its orbit, unresolved, seen from a fixed site. SatSim's configuration can state a space observer on a TLE (`geometry.site.tle`), track modes, target brightness as a magnitude or a Lambertian sphere or a sprite, a PSF and an exposure (`docs/SatSim_probe.md`, "Mapping onto the descriptor", rows 2, 6, 7, 10, 11, 20); none of these has a descriptor home, so each is SatSim configuration, not run-spec members. The SatSim licence question (C-38) is open; this round runs nothing in SatSim.

**Install demos with orbital geometry** (from the survey and sweep; referenced by name only, no demo bytes). None gives a usable space-to-space geometry for the layered form at this tag:

| Demo | Geometry | Survey verdict | Rendered here |
|---|---|---|---|
| Ssa3 | space to space: a platform on a TLE with LookAt at another `sgp4` satellite | near | no: DIRSIG 4 only (skipped by the sweep) |
| SpaceRendezVous1 | space to space: a chaser closing on Hubble, STK waypoints and quaternions | far | `lidar_rpo.jsim` only (a lidar); the imaging `pan_rpo.jsim` never run |
| Ssa1 | ground to space: a fixed site tracking a TLE satellite | far | yes, deterministic over three renders |
| LightCurve1 | ground to space: a spinning box on a TLE | far | yes; one thread bit-identical |
| Ssa2 | a fixed Earth-centred site looking at Hubble | near | no: DIRSIG 4 only |
| MoonSat2 | a tracking mount following a Moon sphere on waypoints | near | yes; radiance identical in every condition |
| StkImport1 | space to ground (EarthGrid, STK reports) | far | yes |

The nearest renderable space-to-space geometry is therefore not a demo: it is a layered scene with an object in it and a static or orbit platform pointed at the object. (The survey's text calls Ssa1 to Ssa3 "a satellite from a satellite"; the tagged-demo notes and the survey's own Ssa1 row describe Ssa1 as a fixed site, which is what the archive's motion shows. Only Ssa3 is space to space.)

### The axes

Cells: **measured** (with the report), **expressible, unmeasured** (existing members state it; no measurement), **not expressible** (what is missing), **unknown**. Object classes: *unresolved*, smaller than a pixel footprint; *hyperresolved*, many pixels across.

| Axis | Class | DIRSIG | SatSim |
|---|---|---|---|
| Platform motion | unresolved | expressible, unmeasured: `orbit` motion with LookAt at the object's scene point; range and speed are the TLE's, not stated; measured only for a ground scene (`tests/test_leo_pass.py`) | expressible, unmeasured: `geometry.site.tle` in the pass-through configuration; the reference run's observer is a fixed ground site |
| Platform motion | hyperresolved | expressible, unmeasured: as above; at the TLE's ranges (773 km and more for the library TLE over its scene) a hyperresolved object must be hundreds of metres across, and no library scene holds a space object | unknown: a sprite target is the only extended form named in the probe; not run |
| Target motion | unresolved | not expressible with run-spec members: no member moves a scene object; only a scene asset's authored motion (the Tahoe vehicle's `straight` line, fixed at 100 m/s) | expressible, unmeasured as an axis: the target's TLE in the configuration; the reference run renders one such target (`docs/SatSim_reference_run.md`), not characterized |
| Target motion | hyperresolved | not expressible with run-spec members (as above) | unknown |
| Shutter blur | unresolved | expressible, unmeasured: `exposure_time` with `integration_samples`, blur from platform motion (`orbit`) or a scene-authored target motion; Stage 04 chose 10 µs to keep blur under a pixel; TemporalIntegration1's layered render is byte-identical to its demo (`docs/DIRSIG_layered_comparison.md`), a ground scene | expressible, unmeasured: `fpa.time.exposure` |
| Shutter blur | hyperresolved | expressible, unmeasured (as above) | unknown |
| Off-nadir look angle | unresolved | expressible, unmeasured: a `static` pose (position and Euler angles) or the `orbit` LookAt target away from the sub-satellite point | expressible, unmeasured: the observer's track mode and target |
| Off-nadir look angle | hyperresolved | expressible, unmeasured (as above) | unknown |
| Sun angle (phase angle) | unresolved | expressible, unmeasured: the epoch with `SpiceEphemeris`, or `atmosphere.uniform`/`simple` with `fixed_ephemeris`; the phase angle is derived, not a member; DensityMap1's fixed Sun measured on a ground scene (CONOPS section 9) | expressible, unmeasured: `geometry.time` and a Lambertian-sphere model (phase follows); no descriptor home |
| Sun angle (phase angle) | hyperresolved | expressible, unmeasured (as above) | unknown |

**Gaps at 796ecd5.** No library scene holds a space object or a space background; no run-spec member moves a target (target motion lives in the scene asset); the `orbit` form's range and speed are the TLE's, so neither is a parameter; the descriptor has no target radiometry, phase angle or look angle (only `collection.geometry.range` and governed terms); the sensor-spec has no PSF, and DIRSIG keeps the template's one-pixel uniform spatial response (CONOPS section 4); nothing measured the handling of a sub-pixel object against an empty background. The SDK cannot set DIRSIG's per-pixel sample count (`--convergence`); `::IMPORTANT::` hypersampling is a scene-asset label and a template value, not a member.

## Scenario family I (round 29)

`scripts/s2s_scenarios.py` writes the family: `run-spec/1` documents for a parameter grid built from existing members only, the library scene they image, and an index of run ids. `--check` regenerates both in memory, compares them with the committed files, and runs the engine-free checks on every spec (schema, resolution against the library with hashes verified, no placeholder, run id as indexed); `--list` prints each point with its derived geometry. `tests/test_s2s_scenarios.py` checks the same and renders two points at 16 x 16.

**The geometry, and why it is not a demo.** No install demo gives a renderable space-to-space geometry (the audit above); the nearest is Ssa3, which this DIRSIG does not run. The family therefore images a generated library scene, `manifold_config_repo/scenes/s2s_targets/` (written by the script from stated numbers; no demo bytes): square Lambertian plates of reflectance 0.5 (DIRSIG `SimpleReflectance`, normal +z), each with a black backstop behind it, and nothing else. Its origin is the Tahoe scene's (39 N, 120 W), so the library TLE's pass applies. The plates stand 50 km apart so that one frame holds one plate:

| Plate | Side | Centre (scene ENU) | Role |
|---|---|---|---|
| `hyperresolved` | 20 m | (0, 0, 0) | hyperresolved class: 6 to 49 pixels across at 100 to 12.5 km |
| `::IMPORTANT::unresolved` | 0.5 m | (50 km, 0, 0) | unresolved class, hypersampled (the template's multiplier, 100) |
| `unresolved_plain` | 0.5 m | (-50 km, 0, 0) | the same plate without the label |
| `::IMPORTANT::moving_1000`, `_7500` | 0.5 m | (0, 50 km, 0), (0, -50 km, 0) at time 0 | a target moving on a DIRSIG `straight` line (heading 90) at 1000 and 7500 m/s |
| `backstop_0` to `_4` | 400 m | 10 m behind each plate's centre | reflectance 0; see "The handling of an unresolved object" below |

**How each axis is stated.**

| Axis | Values | Member |
|---|---|---|
| Range | hyperresolved 12.5, 25, 50, 100 km; unresolved 12.5 to 800 km in factors of two | `engine.motion` kind `static`: the platform `range` from the plate along the look direction |
| Look angle off nadir | 0, 30, 60 degrees | the same position, turned to face the plate (`xyz` Euler angles: a rotation about y by the look angle, after the nadir pose's pi about z; the sign was measured with 64 x 64 renders) |
| Sub-pixel offset | 0, 0.25, 0.5, 0.75 of a pixel footprint, along both scene axes | the platform moved; crossed with 12.5, 25 and 50 km for the unresolved plates |
| Exposure time | 1, 5, 20 ms (frame rate 10 Hz) | `settings[].exposure_time`; `integration_samples` 10 |
| Sun angle | solar zenith 0, 30, 60 degrees | `engine.atmosphere` plugin `basic`, `uniform` (hemisphere irradiance 0.1, sky fraction 0: all direct, no extinction, no path radiance) with `fixed_ephemeris`; the phase angle (look angle plus solar zenith, the Sun opposite the sensor in the look plane) is recorded in `descriptor.extras` |
| Relative speed | 0; 1000 and 7500 m/s (the moving plates); `orbit` | 0 is a static platform and plate; the moving plates are scene-authored motion; `orbit` is `engine.motion` kind `orbit` with the library WORLDVIEW-2 TLE and a LookAt at the unresolved plate, task at 60 s (culmination): range 773.093 km and look angle 1.8 degrees, the TLE's, not set |
| Object class | hyperresolved, unresolved, unresolved without the label | which plate the platform faces |

Every spec states `resources.cpu_threads: 1` (one thread repeats bit for bit, `docs/DIRSIG_determinism.md`), seed 1, the `auror-nir` sensor and the `AurorNIRDetector` template, and a 500 x 500 window: the template's array, since `auror-nir` records no full frame (its `SensorWidth` and `SensorHeight` are null). The grid is one axis at a time about one baseline per class (hyperresolved: 25 km; unresolved: 200 km; nadir, Sun at the zenith, 5 ms, static), plus the sub-pixel block: 63 specs, listed with their run ids in `manifold_run_specs/s2s/index.json`. The full product is available as `grid(full=True)` and is not committed.

**What the family does not state.** A speed other than the moving plates' and the TLE's (the `waypoints` motion form is refused by the loader); a target that moves relative to a moving platform (only one of the two moves in any spec); an Earth background (the scene has none; a finite `GROUND_PLANE` or a terrain scene would be one); stars; a PSF (the sensor-spec has none, and the template's spatial response is one uniform pixel); a phase angle for anything but a flat plate (for a Lambertian plate only the solar zenith changes the signal).

## First measurements (round 29, DIRSIG only)

**How.** Each grid point was rendered at the native 500 x 500 window, one thread, seed 1, through `Simulation.run` (the layered job the SDK assembles from the committed spec, the library read in place), by a scratch script outside the repository, one render at a time, each its own process, with a per-run `HOME`. Numbers and digests only; the images were deleted. DIRSIG 2026.38.0.a020954, dirfm at the pinned revision. 45 of the 63 points were rendered: every hyperresolved and labelled-unresolved point, and the unlabelled plate's range sweep. The unlabelled plate's other points (look, Sun, exposure, offsets) were not.

**The expectation, from the run spec's own numbers.** A pixel wholly on a plate: the plate's radiance L = ρ E cos θs / π (ρ 0.5 from the scene; E 0.1 W cm⁻² µm⁻¹, spectrally constant, all direct, from `atmosphere.uniform`; θs the stated solar zenith), times the aperture's view of it, times the exposure, integrated over the channel the generator wrote from the sensor-spec (unit-peak shape × QE × optics, tabulated on 0.41–2.0 µm), in photo-electrons per m² of focal plane. With the paraxial aperture term τ A_ap / f² (τ 0.875, D 85 mm, f 306 mm, 5 ms) this is S_full = 2.8830e16 e⁻ m⁻². The rendered value is 2.82847e16 (ratio 0.98108), which is the exact-cone factor 1/(1 + 1/(4N²)) for N = 3.6. With that factor the expectation is 2.82847e16, ratio 1.0000001, and every ratio below uses it. A plate's expected footprint in pixels is its projected area over the pixel footprint squared, A cos θv / (R p / f)², from the plate side and the spec's range, look angle, pitch (10 µm) and focal length. The integrated signal is the sum of all pixels over S_full ("equivalent pixels"). Flux closure means equivalent pixels equal the expected footprint; for an unresolved plate this is the R⁻² law at fixed plate area.

### E1: hyperresolved range sweep (20 m plate, nadir, Sun at the zenith, 5 ms)

| Range | Pixel footprint | Expected footprint (px) | Equivalent pixels | Ratio | Pixels ≥ half level | Σ × footprint² (m², plate 400) | Wall (s) | Image sha256 (16) |
|---|---|---|---|---|---|---|---|---|
| 12.5 km | 0.408 m | 2397.08 | 2396.89 | 0.99992 | 2383 | 399.97 | 79.1 | `85ca8c68feece0ec` |
| 25 km | 0.817 m | 599.27 | 599.84 | 1.00095 | 576 | 400.38 | 70.2 | `ec690ca81d5ec602` |
| 50 km | 1.634 m | 149.82 | 150.62 | 1.00536 | 144 | 402.14 | 20.6 | `3b6459fea3d5b16a` |
| 100 km | 3.268 m | 37.45 | 37.76 | 1.00816 | 36 | 403.26 | 8.9 | `09e3c59874d67ef0` |

The footprint scales as R⁻²: 2383, 576, 144 and 36 pixels at or above half a full pixel, against the plate's 2397, 599, 150 and 37 pixel areas (48.96, 24.48, 12.24 and 6.12 pixels across). The integrated signal over the footprint is constant to within 0.8 percent. The interior pixels equal S_full exactly, and the background is exactly zero. The excess grows as the edge pixels become a larger share (0.01 % at 12.5 km, 0.8 % at 100 km) and is not explained (OPEN). The other hyperresolved points close as well: exposure 1 and 20 ms scale the sum by 0.2000 and 4.0000; 30 and 60 degrees off nadir give 519.06 and 300.05 equivalent pixels against 518.98 and 299.64 (ratios 1.0002, 1.0014); solar zenith 30 and 60 degrees scale an interior pixel by cos θs to 1.00001 and 1.00006.

Without a backstop (the first scene; the same plate and pose, every other byte of the scene the same less the backstop instances), the 25 km render gave 605 nonzero pixels and 589.8 equivalent pixels (ratio 0.984, image `edd16f7e6ba2602a`). The edge pixels, part plate and part nothing, were undersampled.

### E2: unresolved plate (0.5 m, nadir, Sun at the zenith, 5 ms)

| Range | Plate across (px) | Expected (equivalent px) | Labelled: equivalent px | Ratio | Peak / S_full | Unlabelled: equivalent px | Ratio | Labelled image sha256 (16) |
|---|---|---|---|---|---|---|---|---|
| 12.5 km | 1.224 | 1.4982 | 1.4899 | 0.994 | 0.381 | 1.6 | 1.068 | `cc34415da1f3472f` |
| 25 km | 0.612 | 0.37454 | 0.3725 | 0.995 | 0.099 | 0.4 | 1.068 | `702fe770dccdf416` |
| 50 km | 0.306 | 0.093636 | 0.0765 | 0.817 | 0.026 | 0.03 | 0.320 | `66f14931a86248e9` |
| 100 km | 0.153 | 0.023409 | 0.0165 | 0.705 | 0.007 | 0 | 0 | `af0a9d058a5ba16e` |
| 200 km | 0.0765 | 0.0058523 | 0.0045 | 0.769 | 0.002 | 0 | 0 | `6927ed2953a1321c` |
| 400 km | 0.0383 | 0.0014631 | 0.0005 | 0.342 | 0.0005 | 0 | 0 | `e3d2e3d6e4f46026` |
| 800 km | 0.0191 | 0.00036577 | 0.0005 | 1.367 | 0.0005 | 0 | 0 | `f96e413c4b4e6ef1` |

(The unlabelled plate's zero images are all `13aea96040f21330`, the all-zero 500 x 500 image.)

**Sub-pixel position.** The platform moved by 0, 0.25, 0.5 and 0.75 of a pixel footprint along both axes (at 0 the plate is centred on a pixel corner, at 0.5 on a pixel centre). The sum over the pixels near the plate (a 13 x 13 box about the peak) over the expectation, and the peak pixel over S_full:

| Range | Sum ratio at 0, 0.25, 0.5, 0.75 | Peak at 0, 0.25, 0.5, 0.75 | Geometric peak at 0, 0.25, 0.5, 0.75 |
|---|---|---|---|
| 12.5 km | 0.994, 0.979, 1.003, 0.991 | 0.381, 0.699, 0.903, 0.707 | 0.375, 0.743, 1.000, 0.743 |
| 25 km | 0.995, 1.020, 0.967, 0.968 | 0.099, 0.262, 0.350, 0.261 | 0.094, 0.262, 0.375, 0.262 |
| 50 km | 0.817, 0.961, 0.977, 0.726 | 0.026, 0.072, 0.091, 0.068 | 0.023, 0.070, 0.094, 0.070 |
| 200 km | 0.769, 1.794, 1.025, 1.025 | 0.002, 0.010, 0.006, 0.006 | 0.0015, 0.0059, 0.0059, 0.0059 |

Where the plate covers at least a third of a pixel (12.5 and 25 km), the sum near it is independent of its sub-pixel position to within 3 percent and the peak is not: it moves by a factor of 2.4 to 3.5, as the geometry says. At 12.5 km with the plate on a pixel centre the peak is 0.903 where the geometry gives 1.000; not explained (OPEN). At 50 km the sum varies by 25 percent with position, and at 200 km by a factor of 2.3.

**How the SDK's output handles a sub-pixel object, and where it fails.**
1. **Nothing behind it: the object is lost.** A pixel whose rays all leave the scene gets no samples that can find a small object in it. In the first scene (no backstops) a plate under about 0.8 of a pixel across rendered exactly zero at every range and position: the 0.5 m plate from 20 km on, the 20 m plate at 800 km. The loss followed the plate's size in pixels only, not its size in metres: the 0.5 m plate at 5 and 10 km and the 20 m plate at 200 and 400 km gave identical sums. The `::IMPORTANT::` label changed nothing. Neither did `--convergence 10 10 0` or `100 1000 1e-6` (DIRSIG logged the setting), nor the template's sample strategy (`central`, `adaptive`, or removed), nor centring the plate on a pixel: the image was byte-identical each time. Partly covered pixels took small-integer fractions of a full pixel (4/5, 3/4, 2/3, 6/7, 1/2). Why the convergence settings do not reach these pixels is not isolated (OPEN). A space background as empty geometry is therefore not a usable model for an unresolved target in DIRSIG.
2. **A surface behind it and the `::IMPORTANT::` label: flux is conserved where the hit count is large.** With a black backstop (reflectance 0; this band evaluates no emission, so it renders exactly zero, as space would) and the label, the hypersampled pixel's value is a count of hits in steps of 1/2000 of a full pixel. Down to about 0.37 pixel area of plate the integrated signal is within 0.6 percent of the expectation and follows R⁻²; from 50 km out the estimate rests on tens of hits or fewer and scatters (0.70 to 0.82); at 400 and 800 km it is a single hit (0.34, 1.37). The R⁻² law therefore holds only where the plate fills more than about a third of a pixel at this template's multiplier (100).
3. **A surface behind it but no label: the object is lost from about a third of a pixel down.** The unlabelled plate's pixels converge on few samples (steps of 1/25 to 1/33 of a full pixel): 1.07 of the expectation at 12.5 and 25 km, a single hit at 50 km, zero from 100 km out.
4. **The SDK cannot state any of this in a run spec.** The per-pixel sample count (`--convergence`) and the hypersampling multiplier are not members (the multiplier is the platform template's), and the label and the backstop are scene-asset content. The family states them only through the library scene and template it names.

**Other points, unresolved (with backstop and label).** Exposure 1 and 20 ms scale the 200 km sum by 0.2000 and 4.0000 (the same three hits). 30 and 60 degrees off nadir: 0.69 and 0.34 of the expectation (3 hits and 1 hit). Solar zenith 30 and 60 degrees: the same hits, scaled by cos θs. Moving plates at 200 km: 1000 m/s (5 m over 5 ms, 0.77 pixel) gives 0.34 (1 pixel lit), and 7500 m/s (37.5 m, 5.7 pixels) gives 0.26 (2 pixels lit). The streak of an unresolved mover is undersampled, so the shutter-blur axis cannot be measured on an unresolved object at this sampling. The orbit point (773.093 km, 1.8 degrees, LookAt at the plate) lights one pixel with one hit (0.0005 equivalent pixels against 0.00039). The platform-motion form tracks the plate, but its flux is not measurable at this range.

### The audit's DIRSIG cells after these measurements

| Axis | Unresolved | Hyperresolved |
|---|---|---|
| Platform motion | measured, inconclusive: the orbit point renders one hit (E2, "Other points") | expressible, unmeasured (the family's TLE ranges make every plate unresolved) |
| Target motion | not expressible as a member; scene-authored movers measured, undersampled ("Other points") | not expressible; no moving hyperresolved plate in the family |
| Shutter blur | not measurable at this sampling (an unresolved streak is a few hits) | expressible, unmeasured as blur; the exposure scales the signal exactly (E1) |
| Off-nadir look angle | measured at 200 km: 3 hits and 1 hit (0.69, 0.34) | measured: projected area to 0.14 % at 30 and 60 degrees (E1) |
| Sun angle | measured at 200 km: the hits scale by cos θs | measured: cos θs to 6e-5 at 30 and 60 degrees (E1) |

### Axes the SDK cannot express (round 29)

- **Target motion as a parameter.** No run-spec member moves a target. The family's moving plates are scene content, one fixed speed per instance.
- **Arbitrary relative speed or range under platform motion.** The `orbit` form takes its speed and range from the TLE. The `waypoints` form, which would state them, is refused by the loader.
- **Sampling of an unresolved object.** The per-pixel sample count and the hypersampling multiplier are not members. The `::IMPORTANT::` label and a surface behind the object, both needed (E2), are scene content.
- **Look angle, phase angle and target radiometry in the descriptor.** Only the range and governed terms have homes. The family records the rest under `descriptor.extras`.
- **A PSF.** The sensor-spec has none; DIRSIG keeps the template's one-pixel uniform response.
- **SatSim.** Nothing run (C-38). The table's SatSim cells are unchanged.
