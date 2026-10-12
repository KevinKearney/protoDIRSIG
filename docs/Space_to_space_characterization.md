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

**Gaps at 796ecd5.** No library scene holds a space object or a space background; no run-spec member moves a target (target motion lives in the scene asset); the `orbit` form's range and speed are the TLE's, so neither is a parameter; the descriptor has no target radiometry, phase angle or look angle (only `collection.geometry.range` and governed terms); the sensor-spec has no PSF, and DIRSIG keeps the template's one-pixel uniform spatial response (CONOPS section 4; corrected in round 30, C3: DIRSIG5 applies an aperture-dependent spread of its own); nothing measured the handling of a sub-pixel object against an empty background. The SDK cannot set DIRSIG's per-pixel sample count (`--convergence`); `::IMPORTANT::` hypersampling is a scene-asset label and a template value, not a member.

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

**What the family does not state.** A speed other than the moving plates' and the TLE's (the `waypoints` motion form is refused by the loader); a target that moves relative to a moving platform (only one of the two moves in any spec); an Earth background (the scene has none; a finite `GROUND_PLANE` or a terrain scene would be one); stars; a PSF (the sensor-spec has none; DIRSIG5 ignores the template's spatial response and applies an aperture-dependent spread of about 0.18 pixel σ, round 30 C3); a phase angle for anything but a flat plate (for a Lambertian plate only the solar zenith changes the signal).

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
- **A PSF.** The sensor-spec has none; DIRSIG keeps the template's one-pixel uniform response. (Corrected in round 30, C3: DIRSIG5 applies an aperture-dependent spread, which a `<psf>` in the platform file replaces.)
- **SatSim.** Nothing run (C-38). The table's SatSim cells are unchanged.

## Scenario family II (round 30)

`scripts/s2s_scenarios.py` also writes family II: 21 specs (`s2s2-*` in `manifold_run_specs/s2s/`, indexed after family I's 63 with `family: 2`) and a second generated scene, `manifold_config_repo/scenes/s2s_blur/`, so that family I's scene and specs are byte-identical to round 29's. Every spec keeps family I's template: `auror-nir`, one thread, seed 1, the 500 x 500 window, the Sun at the zenith from `atmosphere.uniform`, a static platform at nadir unless stated.

| Group | Scene content (scene ENU) | What moves (DIRSIG `straight`, heading 90, fixed orientation) | Specs |
|---|---|---|---|
| `static` | a 20 m plate (reflectance 0.5) at (0, 0, 10 km); a 0.5 m `::IMPORTANT::` plate 120 m to its +y side; a 4 m marker plate 100 m to its +x side; 10 km below, a 1200 m black plate with white bars (reflectance 0.25, 40 m wide every 80 m, running along y) on its −y side from −60 to −600 m, black elsewhere | nothing | `s2s2-blur-static-e5ms` |
| `platform` | the same, without the marker, at x = 2 km | everything at 1000 m/s: the platform moving at 1000 m/s on heading 270, expressed in the scene | 0.1, 1, 5, 20 ms |
| `target` | the same at x = 4 km | the two plates at 1000 m/s; the background still | 0.1, 1, 5, 20 ms |
| `both` | the same at x = 6 km | the background at 1000 m/s, the plates at 2000 m/s (the platform at 1000 m/s on heading 270, the target at 1000 m/s on heading 90) | 0.1, 1, 5, 20 ms |
| `look` | the 20 m plate at (0, 5 km, 10 km); 500 m below it a 2400 m black plate with the same bars on both sides of a black band 80 m wide along x | nothing | look 0, 15, 30, 45, 60, 75 degrees at a slant range of 25 km |
| `orbit` | a 100 m plate at (0, −20 km, 0) with a 2 km black backstop 10 m behind | the platform, by the `orbit` form (library TLE, LookAt at the plate, task at culmination): 773.266 km, 2.2 degrees off nadir, 7558 m/s | 0.1, 20 ms |

The platform stands 25 km above each blur group's plates, so the background is 35 km away: the target's pixel footprint is 0.8170 m and the background's 1.1438 m. A plate is 24.48 pixels across, a bar period 69.94 pixels. Blur is expected to be speed × exposure / footprint, a boxcar of that length convolved with the plate's or the bars' profile and the pixel.

**Why the background is 10 km behind and the plates are at the top of the scene (measured while building).** The first layout put the background 25 km behind the plates. No pixel of it rendered. With 16 x 16 probes and DIRSIG's truth collectors (`samplecount`, `convergencestatus`, `earthcorefraction`, `voidfraction`; scratch, not committed), the background at z = 0 rendered from a platform 20 km above it and not from 21 km. From 21 km each pixel took one path that hit DIRSIG's default earth core (fraction 1, status 4, radiance 0). With `--disable_earth_core` the same pixels took 20 paths that hit nothing (void fraction 1). Moving the background and the plates 10 km higher moved the threshold with them (rendered from 30 km above the background, not from 31 km). A surface more than about 20 km along the ray inside this scene was therefore not intersected. The mechanism is not isolated (OPEN). The family keeps every path inside the scene shorter than 10 km: the plates are the highest geometry, so a platform above them enters the scene at their height. Round 29's single-plane scene never met this.

### A: shutter blur (native 500 x 500, one thread)

**Image directions.** In the static frame the marker (scene +x) lies at decreasing column and the bars (scene −y) at increasing row. The streaks below are measured along the columns.

**Direction and timing of the streak (round 29's `straight` heading, now verified).** Every moving plate and background sweeps toward scene +x (heading 90 is +x, east), and the sweep starts at the task time. The swept interval, fitted relative to the static position, runs from about 0 to +b (for example [−0.06, +5.92] pixels at 5 ms and [+0.13, +48.26] at 20 ms for the `both` target). The streak's centroid moves by about half the blur (2.94 against 3.06 pixels, 24.22 against 24.48), not zero: the exposure window is [t, t + exposure], not centred on the task time. The orbit form's platform is the only other motion. It does not streak the plate it looks at: at 0.1 ms and 20 ms the same 25 pixels are lit, and the sums differ by 200.000 (images `9eac82dead43210a`, `cb617b12fb7e8292`). An untracked platform at the same speed would have streaked it by 5.98 pixels in 20 ms.

| Group, exposure | Target blur, expected / fitted (px) | Target flux ratio | Background blur, expected / fitted (px) | Profile rms, fitted / analytic (target) | Unresolved: ratio, pixels lit | Wall (s) | Image sha256 (16) |
|---|---|---|---|---|---|---|---|
| static, 5 ms | 0 / — | 1.0009 | 0 / — | — | 1.040, 4 | 83.7 | `2313fb4264480b38` |
| platform, 0.1 ms | 0.122 / 0.122 | 1.0008 | 0.087 / 0.089 | 0.0007 / 0.0098 | 1.031, 4 | 122.9 | `45b32999db892a54` |
| platform, 1 ms | 1.224 / 1.233 | 0.9995 | 0.874 / 0.955 | 0.0008 / 0.0092 | 0.895, 4 | 126.4 | `1b957de3de6889dd` |
| platform, 5 ms | 6.12 / 5.97 | 1.0002 | 4.37 / 4.25 | 0.0027 / 0.0060 | 0.790, 12 | 139.7 | `a54757f48e7f0c2d` |
| platform, 20 ms | 24.48 / 23.85 | 0.9980 | 17.49 / 17.11 | 0.0045 / 0.0059 | 0.364, 9 | 200.3 | `09a3764bca2cfdb9` |
| target, 0.1 ms | 0.122 / 0.122 | 1.0008 | 0 / 0.001 | 0.0007 / 0.0098 | 1.031, 4 | 88.5 | `1bd70400b514705b` |
| target, 1 ms | 1.224 / 1.233 | 0.9995 | 0 / 0.001 | 0.0008 / 0.0092 | 0.895, 4 | 88.8 | `f6e6d760ef9d9e2b` |
| target, 5 ms | 6.12 / 5.97 | 1.0002 | 0 / 0.001 | 0.0027 / 0.0060 | 0.790, 12 | 89.0 | `a35a397f1e1e6686` |
| target, 20 ms | 24.48 / 23.85 | 0.9980 | 0 / 0.001 | 0.0045 / 0.0059 | 0.364, 9 | 90.3 | `b03b658b62c92b7e` |
| both, 0.1 ms | 0.245 / 0.249 | 1.0012 | 0.087 / 0.088 | 0.0016 / 0.0195 | 1.071, 4 | 123.3 | `e1497e09ac81550f` |
| both, 1 ms | 2.448 / 2.363 | 0.9988 | 0.874 / 0.955 | 0.0014 / 0.0140 | 0.754, 5 | 126.8 | `26b211543a99beb2` |
| both, 5 ms | 12.24 / 11.87 | 1.0003 | 4.37 / 4.25 | 0.0023 / 0.0075 | 0.619, 12 | 140.8 | `68ec8789c9e710d3` |
| both, 20 ms | 48.96 / 48.13 | 0.9907 | 17.49 / 17.11 | 0.0064 / 0.0079 | 0.254, 9 | 204.1 | `3327da933d03225e` |

How each number is made. The target profile is the mean of the plate's interior rows. It is fitted with the exact model: a plate 24.48 pixels wide swept uniformly over a signed length, integrated over each pixel; the start and the length are free. The background profile is the mean of the bar rows away from the plates, fitted the same way with the static frame's bar phase as the reference. The flux ratio is the sum over a box about the streak, divided by the full-pixel signal at that exposure (the 5 ms value 2.82847e16 scaled by the exposure) and by the plate's 599.27-pixel area. The analytic-profile rms is the same model with the start at the static position and the length v·t/footprint. Profile values are fractions of a full pixel.

What this shows, for the hyperresolved plate and the textured background:
- Target and background blur are separately observable. With the target moving alone the background does not blur (fitted 0.001 pixel); with the platform moving both blur, the background less (its footprint is larger); with both, the target's blur is the sum (twice) and the background's is the platform's alone.
- The blur length follows exposure over 2.3 decades, and the edge is a boxcar: the fitted model leaves an rms of 0.0007 to 0.0064 of a full pixel. At 5 and 20 ms the fitted length is short of v·t/footprint by 1.7 to 3.1 percent (target 5.97/6.12, 23.85/24.48, 11.87/12.24, 48.13/48.96; background 4.25/4.37, 17.11/17.49). The shortfall is the same for the target and the background, at both ranges, and does not depend on `integration_samples`: 10 and 100 render byte-identical images, as the manual says DIRSIG5 ignores the count. Not explained (OPEN). At 1 ms the background fit is long (0.955/0.874): a 0.9-pixel blur on a 70-pixel bar period is near what the fit can resolve.
- Integrated flux is conserved over the exposure: 0.9907 to 1.0012 of the expectation scaled by the exposure.

**The unresolved plate's streak.** The 0.5 m plate (0.61 pixels across, labelled) keeps its flux only while its streak stays within about a pixel. The ratio is 1.03 to 1.07 at 0.1 ms, falls to 0.75 to 0.90 at 1 ms, 0.62 to 0.79 at 5 ms and 0.25 to 0.36 at 20 ms, with 9 pixels lit along a 24- or 49-pixel streak. A 64 x 64 truth render of the `both` 20 ms streak (scratch; platform recentred on the streak) shows why. Only two pixels on the streak are hypersampled (2000 paths): the pixel holding the plate at the task time, and one more. Every other streak pixel starts with the minimum 20 paths. If none hits the plate, the pixel stops there with status 4 and radiance 0. If one does, it runs to the maximum of 100 paths (status 2) and takes 0.01 of a full pixel per hit. At about 0.008 of a pixel of plate per streak pixel, about 15 percent of the pixels are hit at all. So the hit-count noise of round 29 becomes, along a streak, a lost-or-one-hit sampling. Its integrated flux is not conserved, and it falls as the streak lengthens. The `::IMPORTANT::` multiplier evidently follows the object at one time, not over the exposure.

### B: look angle against a background (native 500 x 500, one thread)

The `look` group: the 20 m plate seen from a slant range of 25 km, 0 to 75 degrees off nadir, in the plane of scene x (the platform on the −x side). The barred black plate is 500 m behind it, with a black band 80 m wide behind the plate (so the plate's own pixels are measured against zero). The expectations come from the spec's numbers. Projected area: 400 cos θ m². Footprint: that area over the pixel footprint squared (0.8170 m at 25 km). The background's pixel footprint is taken at its slant range, 25 km + 500 m / cos θ; its bar period along x is 80 cos θ m over that footprint. Equivalent pixels are the band rows' sum over a full pixel. The bar columns are predicted by casting each column's ray onto the background plane, using the image direction measured in step A.

| Look | Projected area (m²) | Expected (px) | Equivalent px | Ratio | Plate extent x, y (px; expected) | Background footprint (m) | Bar period, expected / measured (px) | Bar columns agreeing with the prediction | Background x seen (m) | Wall (s) | Image sha256 (16) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 400.0 | 599.27 | 599.84 | 1.0009 | 24, 24 (24.48, 24.48) | 0.8333 | 96.00 / 96.0 | 1.000 | −208 to 208 | 86.1 | `efee7da6b67b0276` |
| 15 | 386.4 | 578.85 | 579.21 | 1.0006 | 24, 24 (23.65, 24.48) | 0.8339 | 92.66 / 93.0 | 0.994 | −81 to 350 | 84.9 | `b8bf797e9787021b` |
| 30 | 346.4 | 518.98 | 519.05 | 1.0001 | 22, 24 (21.20, 24.48) | 0.8359 | 82.89 / 83.0 | 0.986 | 49 to 531 | 84.6 | `758467b5b12e03e4` |
| 45 | 282.8 | 423.75 | 423.87 | 1.0003 | 18, 24 (17.31, 24.48) | 0.8401 | 67.34 / 67.5 | 0.974 | 206 to 799 | 86.5 | `fac1cd96c0c775ee` |
| 60 | 200.0 | 299.64 | 300.04 | 1.0013 | 12, 24 (12.24, 24.48) | 0.8497 | 47.08 / 47.0 | 0.958 | 448 to 1296 | 91.5 | `66c384f828774ec0` |
| 75 | 103.5 | 155.10 | 148.44 | **0.9571** | 6, 25 (6.34, 24.48) | 0.8801 | 23.53 / — | 0.978 | 1043 to 2741 (plate ends at 1550) | 34.1 | `06620aebe0ec2cbf` |

(Plate extents count pixels at least half full; the measured period is the mean spacing of the bars' rising edges in the central 200 columns.)

From 0 to 60 degrees the integrated flux follows the projected area to 0.13 percent. The plate shortens along the look plane as cos θ, and the background's apparent footprint grows with its slant range: its period in pixels follows 80 cos θ over the footprint to within half a pixel.

**Where the geometry stops being valid: 75 degrees.** The line of sight through the plate meets the background plane at x = 1866 m, beyond the plate's edge at 1550 m. 344 of the 500 columns look past the background (343 measured: a truth render of the same frame, byte-identical image, has earth-core fraction 1 across them). Behind the plate there is nothing but the earth core, and the plate's flux falls to 0.957 of the expectation. The truth shows why. A pixel half on the plate took 2 paths and reads 1/2; pixels mostly on it took 17 and 13 paths and read 16/17 and 12/13. Their earth-core fractions are 1/2, 0.06 and 0.08. This is consistent with each pixel stopping at its first path that reaches the earth core. This is round 29's no-backstop failure, met here by the scene's extent. The family's geometry is valid while the line of sight through the target lands on the background plate. It also needs every path inside the scene to be shorter than about 20 km (the layout note above).

**An Earth-like or planar background with existing members.** A planar background is expressible only as scene content: the family's barred plate is one. An Earth surface is not, alongside a target. The DIRSIG run spec takes exactly one `engine.scenes` entry (the resolver refuses two), so the library's Tahoe terrain cannot stand behind a generated target. No member adds an Earth model plugin. Recorded as a gap.

### C: round 29's three unexplained differences

Controlled variations at 16 x 16 unless stated, one thread, through the job the SDK assembles. Each variation edits the assembled job's platform file, the dirsig5 options or the spec's seed; scratch, not committed. Render time used: about 6 minutes of the 60 allowed. Truth bands: `samplecount`, `convergencestatus`, `earthcorefraction`, `voidfraction`, `userscenefraction`.

**1. Empty-background pixels untouched by the convergence options: explained (observed cause).** The cause is the earth core, DIRSIG's absorbing ellipsoid about 430 m below sea level that catches paths leaving the scene. Test case: round 29's no-backstop scene (scratch library copy with the five backstop instances removed) and the labelled 0.5 m plate at 25 km.

| Variation | Paths per pixel | Status | Earth core / void fraction | Ratio to expectation | Image sha256 (16) |
|---|---|---|---|---|---|
| as round 29 | 1 everywhere | 4 (radiance 0) | 1 / 0 | 0 | `e5a00aa9991ac8a5` |
| focal-plane `<convergence>` 100, 1000, 1e-6 | 1 everywhere | 4 | 1 / 0 | 0 | `e5a00aa9991ac8a5` (identical) |
| `--disable_earth_core` | 20; 2000 on the plate | 0, 4 | 0 / 0.999 | 1.0039 | `60da15fb538acae1` |
| `--disable_earth_core` and the convergence above | 100; 10000 on the plate | 0, 4 | 0 / 0.999 | 0.9919 | `a3baa2f6bd9c57ba` |
| with the backstop (the committed scene) | 20; 2000 on the plate | 0, 4 | 0 / 0 | 1.0039 | `60da15fb538acae1` (identical to the core disabled) |

A pixel's sampling ends at its first path that reaches the earth core. When that is the first path the pixel takes one path, whatever the convergence settings. A pixel whose earlier paths hit the plate reads (n − 1)/n of a full pixel, the small-integer fractions round 29 saw (4/5, 3/4, 2/3, 6/7, 1/2). The look sweep's 75-degree frame shows the same: 16/17, 12/13 and 1/2, with earth-core fractions of one path in n. With the core disabled, the plate's pixels are sampled as with a backstop, and the image is byte-identical to the backstop render. A black backstop is therefore exactly equivalent here to removing the core. `--disable_earth_core` is a dirsig5 option, not a run-spec member.

**2. The E1 residual rising with range: explained as sampling scatter (observed).** The 20 m plate's integrated signal moves with the seed alone (`engine.run.seed`; native 500 x 500, default convergence):

| Range | Seed 1 (round 29) | Seed 2 | Seed 3 |
|---|---|---|---|
| 50 km | 1.00536 (`3b6459fea3d5b16a`) | 0.99694 (`73dcfc57f93ce5a8`) | 1.00495 (`543309ac395cdf2a`) |
| 100 km | 1.00816 (`09e3c59874d67ef0`, round 29's image reproduced) | 0.99641 (`5e8ab6ebab8546b1`) | 1.01350 (`3b6db6ae2695e104`) |

The edge pixels take 20 to 100 paths (`samplecount`), and their Monte Carlo scatter, summed over the plate's perimeter, is a larger share of the signal the fewer pixels the plate covers. At 16 x 16 the 100 km sum is 0.99801 to 1.00255 over seeds 1 to 5, 1.0009 at a fixed 1000 paths per pixel, and 1.01857 at a fixed 20. Round 29's monotone rise is one seed's realization; it brackets 1 across seeds.

**3. The pixel-centred 1.224-pixel plate peaking at 0.9025: explained (observed cause).** The cause is a spread applied by the BasicPlatform plugin, set by the aperture. The 20 m plate's edge, at a fixed 1000 paths per pixel, reads 0.0704 in the pixel outside the edge and 0.9283 in the pixel inside, where the geometry gives 0 and 1. The profile is identical at 12.5 and 25 km, so the spread is not defocus. It is unchanged, to the sum, by the template's spatial response (`xwidth`, `ywidth` 0.5; 3 x 3 sub-elements) and by removing the sample strategy. The manual says this plugin ignores the spatial response. The variations that change it:

| Variation (focal plane) | Pixel outside / inside the edge |
|---|---|
| none (the template as used) | 0.0704 / 0.9283 |
| `<psf><width>0.01</width></psf>` | 0.0024 / 0.9982 |
| `<psf>` width 0.15, 0.2, 0.25, 0.3, 0.35, 0.4 | 0.030, 0.039, 0.049, 0.058, 0.067, 0.078 outside |
| aperture diameter 42.5 mm (twice the f-number) | 0.145 / 0.856 |
| aperture diameter 170 mm (half the f-number) | 0.036 / 0.963 |

The spread scales with the f-number, as a diffraction spread would. 1.22 λ N at 0.85 µm and N 3.6 is 3.7 µm, 0.37 pixel, inside the 0.35 to 0.40 bracket of explicit Gaussian widths. The plugin's model is not documented; that is an interpretation, not a measurement. Fitted as the pixel convolved with a Gaussian, the spread has σ = 0.18 pixel (100 km plate, 1000 paths: residual rms 0.0034). That model predicts the 12.5 km unresolved plate's peaks at offsets 0, 0.25, 0.5 and 0.75 as 0.373, 0.698, 0.882 and 0.698. Round 29 rendered 0.381, 0.699, 0.903 and 0.707; at 4000 paths per pixel (×100 hypersampled) the pixel-centred peak is 0.8876. Hypersampling multiplier 1 and the unlabelled plate give 0.90 at 100 paths: the label and multiplier do not cause it. A symmetric spread keeps the sum, so it does not cause item 2.

Consequences for the documents: the sensor-spec has no PSF member, and DIRSIG5 does not keep the template's one-pixel uniform response. It applies an aperture-dependent spread of about 0.18 pixel (σ) for `auror-nir`, unless the platform file states a `<psf>`. The family specs' `fidelity.absent` entry "optics blur (the template's spatial response is one uniform pixel)" is therefore inaccurate. The specs are not regenerated: that would change every family spec's run id, and the text is a fidelity statement, not an input. It is recorded here and in BACKLOG.

### The audit's DIRSIG cells after round 30

| Axis | Unresolved | Hyperresolved |
|---|---|---|
| Platform motion | measured as scene motion (the `platform` group): the 0.5 m plate's streak is sampled at a few hits, flux 1.03 to 0.36 of the expectation from 0.1 to 20 ms (A). The `orbit` form tracks its LookAt point (round 29's orbit point: one hit) | measured as scene motion: blur v·t/footprint to 2 to 3 percent, flux to 0.2 percent, along scene +x from the task time (A). The `orbit` form holds a 100 m plate still over 20 ms (A); its range and speed are the TLE's |
| Target motion | measured (the `target` group, scene content): as for platform motion; the background unblurred | measured (the `target` group): the plate's blur as above, the background's 0.001 pixel |
| Shutter blur | measured: an unresolved streak loses flux as it lengthens, because hypersampling covers only the pixels at about the task time and the rest stop at 20 paths with no hit (A) | measured: boxcar edge profile (rms ≤ 0.0064 of a full pixel), four exposures over 2.3 decades, target and background blur separately (A); the blur length 1.7 to 3.1 percent short at 5 and 20 ms, unexplained |
| Off-nadir look angle | measured at 200 km in round 29 (3 hits and 1 hit) | measured 0 to 75 degrees against a barred background: projected area to 0.13 percent and background period to half a pixel up to 60 degrees; at 75 degrees the background ends behind the target and the flux drops to 0.957 (B) |
| Sun angle | measured at 200 km (round 29) | measured (round 29) |

### Axes the SDK cannot express (round 30)

- **Platform motion at a stated speed.** The `static` form has no velocity. The `orbit` form's speed (7558 m/s here) and range are the TLE's, and its LookAt holds the target still (A). Family II therefore moves the scene: platform motion is the whole group moving the other way (DIRSIG `straight`, heading 90, a fixed orientation), target motion is the plates alone, both is both. This is exact for a non-rotating platform and a fixed Sun. Every such speed is a scene-asset value, one per instance, not a member.
- **Target motion.** As in round 29: scene content only.
- **Hypersampling of a moving unresolved object.** `::IMPORTANT::` follows the object at about the task time only (A). Neither the multiplier nor the per-pixel sample count is a member.
- **The earth core.** A pixel's sampling ends at its first path to the earth core (C1). Its removal (`--disable_earth_core`) is a dirsig5 option, not a member, so the family needs a surface behind every target and background.
- **Path length inside the scene.** A surface about 20 km along the ray inside the generated scene was not hit (family II's layout note). The mechanism is not isolated, and no member or documented option states it.
- **An Earth background beside a target.** The run spec takes one `engine.scenes` entry; no member adds an Earth model. A planar background is scene content (B).
- **A PSF.** The sensor-spec has none. DIRSIG5 applies an aperture-dependent spread of its own (C3), and only a `<psf>` in the platform file, not a member, changes it.
- **Look angle and phase angle in the descriptor.** As in round 29: recorded under `descriptor.extras`.

## Scenario family III (round 31): Sun and phase angle on a Lambertian sphere

`scripts/s2s_scenarios.py` also writes family III: 27 specs (`s2s3-*`, indexed after family II with `family: 3`) and a third generated scene, `manifold_config_repo/scenes/s2s_sun/`, so that families I and II stay byte-identical. The targets are DIRSIG's analytic sphere primitive (`<sphere>` in the geometry list, with a scene material by `matid`, as the install's MERL and Brdf1 scenes use it), not facets, so the shape carries no facet error. Reflectance 0.5 (`SimpleReflectance`). Every spec keeps family I's template: `auror-nir`, one thread, seed 1, the 500 x 500 window, 5 ms, the uniform atmosphere with a `fixed_ephemeris` Sun, a static platform at a slant range of 25 km.

| Group | Scene content (scene ENU) | Role |
|---|---|---|
| `hyperresolved` | a 10 m radius sphere at (0, 0, 1000 m); a black 400 m backstop 30 m below its centre | 24.48 pixels across |
| `unresolved` | a 0.25 m radius sphere named `::IMPORTANT::` at (5 km, 0, 1000 m); a backstop 10 m below | 0.61 pixel across, hypersampled |
| `unresolved_plain` | the same sphere without the label at (−5 km, 0, 1000 m) | the label's effect |
| `background` | a 10 m sphere at (0, 5 km, 1000 m); family II's barred black plate (bars of reflectance 0.25 on its −y side) 500 m below it | the Sun's zenith changes the background and the sphere differently |

**The phase angle and the expectation.** The platform is placed toward −x from the sphere at the look angle off nadir (`pose`), and the Sun stands toward +x at the solar zenith, solar azimuth 90. The phase angle is look + solar zenith. In the phase sweep each is half the angle, from 0 to 150 degrees in nine steps, so both stay above the horizon and the backstop below the sphere catches every line of sight past its limb (up to 75 degrees off nadir). A Lambertian sphere of radius R and reflectance ρ under irradiance E has the radiant intensity (2/3) ρ E R² Φ(a), with Φ(a) = (sin a + (π − a) cos a) / π. In the family's units, full pixels of a plate facing the Sun and the sensor (round 29's S_full = 2.82847e16 e⁻ m⁻² at 5 ms), the expectation is (2/3) π R² / g² × Φ(a), with g the pixel footprint (0.8170 m at 25 km): 313.777 pixels at full phase for the 10 m sphere and 0.19611 for the 0.25 m sphere. A 64 x 64 probe confirmed the direction first: with the Sun 60 degrees toward +x, the lit side is at decreasing column (scene +x, round 30's image direction) and the terminator 5 m toward −x, where R cos 60° puts it.

**Measured while building: the earth core hides geometry below the origin.** The first layout put the spheres at the origin's altitude and the barred plate 500 m below them. The bars did not render. The three renders from that layout are all-zero outside the sphere, and the sphere's integrated signal is unchanged (1.0011 of the expectation at 0 degrees). Raising every group by 1 km rendered the bars at 0.5 of a full pixel, as their reflectance gives. This fits round 30's account of the earth core as an absorbing ellipsoid about 430 m below the origin's altitude: a surface below it is inside it. The family keeps every surface above the origin's altitude.

### A: the phase sweep (native 500 x 500, one thread)

| Phase (deg) | Look, solar zenith (deg) | Φ(a) | 10 m sphere: expected (px) | Equivalent px | Ratio | Pixels lit | Peak / S_full | Image sha256 (16) | 0.25 m sphere `::IMPORTANT::`: expected (px) | Equivalent px | Ratio | Pixels lit | Image sha256 (16) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0, 0 | 1.0000 | 313.78 | 314.14 | 1.0012 | 527 | 0.998 | `5e3e1d1d5864333a` | 0.19611 | 0.19239 | 0.981 | 4 | `bfc3d34b2f5dac00` |
| 20 | 10, 10 | 0.9442 | 296.25 | 296.61 | 1.0012 | 508 | 0.998 | `48cb9ee78409a4fa` | 0.18516 | 0.18104 | 0.978 | 4 | `fff1ed0698302a0b` |
| 40 | 20, 20 | 0.8004 | 251.15 | 251.62 | 1.0019 | 469 | 0.998 | `85a431dccdebeb8a` | 0.15697 | 0.15394 | 0.981 | 4 | `fb8557cd35d02ae7` |
| 60 | 30, 30 | 0.6090 | 191.09 | 191.40 | 1.0016 | 402 | 0.998 | `8cdce3ec6973c90b` | 0.11943 | 0.11779 | 0.986 | 4 | `cb15c76db7f9e894` |
| 80 | 40, 40 | 0.4099 | 128.63 | 128.84 | 1.0016 | 323 | 0.984 | `0b3c363dd57244d8` | 0.08039 | 0.08061 | 1.003 | 4 | `b71fc03fd494036a` |
| 100 | 50, 50 | 0.2363 | 74.14 | 74.37 | 1.0031 | 241 | 0.876 | `c47bcdacd9295284` | 0.04634 | 0.04831 | 1.042 | 4 | `902faf309c63e641` |
| 120 | 60, 60 | 0.1090 | 34.20 | 34.28 | 1.0022 | 163 | 0.679 | `530b0ecdb8e6b5a0` | 0.02138 | 0.02247 | 1.051 | 4 | `6e976cd235cf1cad` |
| 135 | 67.5, 67.5 | 0.0483 | 15.16 | 15.29 | 1.0087 | 113 | 0.448 | `2dd8bc9bc6a474e5` | 0.00947 | 0.01099 | 1.161 | 4 | `75f508d29d81170d` |
| 150 | 75, 75 | 0.0148 | 4.65 | 4.69 | 1.0098 | 77 | 0.225 | `b5205cf6f9cd9395` | 0.00291 | 0.00323 | 1.112 | 3 | `afbf4e7cabb6e88e` |

(Equivalent pixels: the frame's sum over S_full; the backstops are black, so the sum is the sphere's. Render wall time 22 to 77 s each, about 25 minutes for the family's 27 renders.)

**Hyperresolved.** The 10 m sphere follows the phase function to between 1.0012 and 1.0098 from 0 to 150 degrees. The angle alone sets the signal, not how it is split between the look and the Sun: at 60 degrees, all of it in the Sun (look 0, zenith 60), half and half, and all of it in the look (look 60, zenith 0) give 191.43, 191.40 and 191.38 equivalent pixels (images `2eb733fcb35290c6`, `8cdce3ec6973c90b`, `75835e349378d4f8`). The residual is sampling scatter, which grows as the lit crescent narrows to a few edge pixels. 64 x 64 controlled variations of the same specs: at 0 degrees seeds 1 to 3 give 0.9999, 1.0005 and 1.0004, and a fixed 1000 paths per pixel (a focal-plane `<convergence>`) gives 1.0005. At 150 degrees seeds 1 to 3 give 0.9994, 0.9739 and 1.0024, and 1000 paths give 0.9998.

**Unresolved, and what the label does where little is lit.** The labelled 0.25 m sphere's ratio scatters about 1: 0.98 at small angles, then 1.04 to 1.16 from 100 degrees. The scatter is the hit count of round 29, now applied to a lit fraction that shrinks with the angle. A 16 x 16 truth render (`samplecount`) shows that the label hypersamples the sphere's 3 x 3 pixels at 2000 paths at every phase angle, the same at 0 and 150 degrees. The other pixels take 20 paths and stop. The paths that find the lit part fall with the angle: about 0.29 of a pixel of disc × 2000 ≈ 590 at 0 degrees, and about 40 at 150 degrees, where the lit part is about 7 % of the disc. Five seeds at 16 x 16 give 0.970, 0.990, 1.054, 1.007, 0.956 at 0 degrees (σ 0.04) and 1.116, 1.263, 1.093, 0.681, 1.256 at 150 degrees (σ 0.24). With a focal-plane `<convergence>` of 2000 paths, multiplied by the template's 100 to 200,000 on the sphere's pixels, 150 degrees gives 0.996. The integrated signal of an unresolved sphere therefore follows the phase function to within the hit-count scatter. At the template's sampling that scatter is a few percent near full phase and about a quarter at 150 degrees. No pass or fail threshold is set here.

**Without the label.** The unlabelled sphere takes 20 paths in every pixel (truth). It reads 1.033 and 1.032 of the expectation at 0 and 80 degrees (3 and 2 pixels lit, `fcbe3884480e7d52`, `48c400d0ff30e53f`). At 150 degrees it is one pixel at 0.935 (`cc386bd70172654c`), a single hit; the 16 x 16 render of the same spec is all zero. A sphere that is mostly dark is therefore lost without the label, or rests on one hit, at a size the label still resolves. Both requirements stand from round 29: a surface behind the object, and the label.

**The Sun against the background.** The `background` group, at nadir, under a solar zenith of 0, 30, 60 and 75 degrees. The barred plate is Lambertian and flat, so its bars follow cos θs. The sphere follows Φ(θs), since at nadir the phase angle is the solar zenith. The two illumination geometries are measured in one frame:

| Solar zenith | Bar level / S_full, measured (cos θs × 0.5) | Ratio | Sphere: expected (px) | Equivalent px | Ratio | Image sha256 (16) |
|---|---|---|---|---|---|---|
| 0 | 0.50000 (0.50000) | 1.00000 | 313.78 | 314.37 | 1.0019 | `3d88d4c5e99bc25d` |
| 30 | 0.43302 (0.43301) | 1.00001 | 276.39 | 277.03 | 1.0023 | `94b06d5fdb11549a` |
| 60 | 0.25002 (0.25000) | 1.00006 | 191.09 | 191.50 | 1.0022 | `9d896cbd0bedeb21` |
| 75 | 0.12943 (0.12941) | 1.00015 | 143.85 | 144.22 | 1.0026 | `fcfa4fb762d48484` |

(The bar level is the median of the bar pixels at full level, rows 340 to 480. The sphere is summed over a 100-pixel box about it; behind it is the plate's black band.) At 75 degrees the background has fallen to 0.26 of its zenith value and the sphere to 0.46 of its own. The ratio between the two changes by a factor of 1.8, as the two functions predict.

**Tests.** `tests/test_s2s_scenarios.py` adds family III's engine-free checks and one 16 x 16 render pair: with the Sun at the zenith the sphere's image is symmetric, and with the Sun 60 degrees toward +x the −x columns are dark.

## SatSim parity on one geometry (round 31)

**The baseline and how each engine states it.** The family's baseline is the hyperresolved 20 m plate at 25 km (`s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0`) and, as the sub-pixel point object, family III's 0.25 m Lambertian sphere at the same range (`s2s3-phase-unresolved-*`). Both have no relative motion, a 5 ms exposure and the `auror-nir` sensor (85 mm aperture, 306 mm focal length, 10 µm pitch, 500 x 500). `scripts/s2s_scenarios.py` writes the same geometry for SatSim: ten SatSim configurations in `manifold_config_repo/satsim/s2s/` and ten SatSim run specs (`s2s-satsim-*` in `manifold_run_specs/s2s/`, indexed with `engine: satsim`). The SatSim specs are generated beside the DIRSIG families, not composed: the composer's pass-through form is DIRSIG's. They have no id-snapshot entry. Each was run through `LocalBackend` with the SatSim adapter (`docs/SatSim_reference_run.md`), seed 1, CPU, one thread, one run at a time: 12 to 15 s each.

| Shared number | DIRSIG run spec | SatSim configuration (the run spec is pass-through) |
|---|---|---|
| Range 25 km | `engine.motion` static position 25 km from the target | observer and target as GCRS states 25 km apart (two-body, `geometry.site` and `geometry.obs.list[]`) |
| Relative speed 0 | static platform and target | both on the same circular velocity (7.546 km/s); the observer rate-tracks the target |
| Exposure 5 ms (and 1, 20) | `descriptor.settings[0].exposure_time` | `fpa.time.exposure` |
| Look angle | the static pose off the scene's nadir | no Earth in SatSim: the observer–target line is placed freely; not a parameter of the signal |
| Sun angle (phase) | `engine.atmosphere.uniform.fixed_ephemeris` (zenith and azimuth in the scene frame; the epoch does not move it) | the Sun from de421 at `geometry.time`: the target is put 7000 km from the geocentre toward the Sun, the observer at the phase angle from the Sun's direction |
| Aperture, focal length, pitch | the sensor-spec, rendered into the platform file | pitch / focal length as the field of view (0.936206 degrees for 500 pixels); the aperture, the channel, throughput and QE only through `fpa.zeropoint` and the POPPY PSF. SatSim writes `FOCALLEN` and `APTDIA` as 0 |
| Target radiometry | the scene's reflectance and the uniform atmosphere's irradiance (0.1 W cm⁻² µm⁻¹) | the Lambertian sphere model (albedo 0.5, diameter 0.5 m) against a −26.74 mag Sun; `fpa.zeropoint` 19.586255 makes −26.74 mag equal to what the aperture collects from that irradiance (paraxial) |
| The plate | a Lambertian plate in the scene | not expressible: a sprite (a uniform square of 73 oversampled pixels, 24.33 pixels, for 24.48) carrying the plate's expected flux as `pe`, so its flux matches by construction |
| PSF | none stated; DIRSIG5 applies its own spread (round 30, C3) | POPPY: an 85 mm circular aperture at 0.786, 0.85 and 0.914 µm weighted by the channel's Gaussian; variants: a Gaussian with energy-on-detector 0.989 (σ 0.18 pixel, DIRSIG's fitted spread) and none |
| Clean frame | no noise model | no shot, read or dark noise, no stars, galactic background 99 mag per square arcsecond; float32 output; the ground-truth planes saved |

The expectation is family III's. The sphere's flux is (2/3) π R² / g² × Φ(a) full pixels. A full pixel is S_full in DIRSIG's units. In SatSim it is the paraxial rate F = 5.76606e8 pe/s, which is S_full without DIRSIG's exact-cone factor 0.981075.

### Results

| Spec | Phase (deg) | Exposure (ms) | PSF | Expected (pe) | SatSim truth plane (target_pe) / expected | SatSim frame / expected | Peak / sum | 3 x 3 / sum | Frame sha256 (16) | DIRSIG, same geometry: equivalent px / expected |
|---|---|---|---|---|---|---|---|---|---|---|
| `s2s-satsim-sphere-a0-e5ms` | 0 | 5 | POPPY | 565,394 | 1.000000 | 0.99904 | 0.484 | 0.949 | `5b1f2869202c6f15` | 0.981 (σ over seeds 0.04) |
| `s2s-satsim-sphere-a60-e5ms` | 60 | 5 | POPPY | 344,323 | 1.000086 | 0.99843 | 0.485 | 0.950 | `6d7abbb412e18441` | 0.986 |
| `s2s-satsim-sphere-a120-e5ms` | 120 | 5 | POPPY | 61,627 | 1.000240 | 0.99272 | 0.488 | 0.956 | `4ed11aac3e80f7cc` | 1.051 |
| `s2s-satsim-sphere-a150-e5ms` | 150 | 5 | POPPY | 8,378 | 1.000511 | 0.97748 | 0.495 | 0.970 | `ade9beb610098441` | 1.112 (σ over seeds 0.24) |
| `s2s-satsim-sphere-a0-e1ms` | 0 | 1 | POPPY | 113,079 | 1.000000 | 0.99509 | 0.486 | 0.953 | `237d22580fd15591` | (plates: × 0.2000, round 29) |
| `s2s-satsim-sphere-a0-e20ms` | 0 | 20 | POPPY | 2,261,574 | 1.000000 | 0.99976 | 0.484 | 0.949 | `34e9cf509d5d15ba` | (plates: × 4.0000) |
| `s2s-satsim-sphere-a0-e5ms-psfgaussian` | 0 | 5 | Gaussian, eod 0.989 | 565,394 | 0.987384 | 0.98738 | 0.551 | 1.000 | `bdc4398d8f5ea33d` | |
| `s2s-satsim-sphere-a0-e5ms-psfnone` | 0 | 5 | none | 565,394 | 1.000000 | 1.00000 | 1.000 | 1.000 | `2ba51dcc8a96f6cb` | |
| `s2s-satsim-sphere-a0-e5ms-zpcone` | 0 | 5 | POPPY, cone zeropoint | 565,394 | 0.981075 | 0.98013 | 0.484 | 0.949 | `152bde3216819bb7` | |
| `s2s-satsim-plate-a0-e5ms` | 0 | 5 | POPPY | 1,727,715,461 | 1.000000 | 1.00000 | 0.002 | 0.015 | `0f74aeb511c15925` | 1.00095 (`ec690ca81d5ec602`, round 29's image reproduced) |

**What agrees.**
- The sphere's phase scaling: SatSim's Lambertian model is the same function. With the real Sun at four phase angles its truth plane is within 5.1e-4 of the analytic value. DIRSIG's labelled sphere follows the same function within its hit-count scatter (A).
- Exposure scaling is exact in both: SatSim's truth plane × 0.2000 and × 4.0000; DIRSIG's plates the same (round 29).
- The integrated signal agrees in each engine's own units. In absolute photo-electrons the two differ by the cone factor alone (below).
- Neither engine streaks a target at zero relative speed: SatSim's start, mid and end positions are identical.

**Every difference, with its cause where a controlled variation shows it.**
1. **Absolute scale: DIRSIG's exact aperture cone (cause shown).** In photo-electrons SatSim's sphere is 1/0.981075 = 1.0193 of DIRSIG's expectation. DIRSIG renders every surface, a sub-pixel sphere included, with the exact-cone factor 1/(1 + 1/(4N²)) (round 29). SatSim's chain is a point source on the aperture area, with no f-number. Variation: the zeropoint that carries the factor (`zpcone`) gives 0.981075 of the paraxial expectation, DIRSIG's own to 1e-6.
2. **The small excess at large phase angles: the apparent Sun (cause shown).** The truth plane's 0.9e-4, 2.4e-4 and 5.1e-4 at 60, 120 and 150 degrees are what a 20.4″ shift of the Sun gives through Φ′(a)/Φ(a). SatSim takes the Sun's apparent direction (light time and annual aberration), the configurations the geometric one. Variations: with light transit and stellar aberration off the excess is unchanged (`range` becomes exactly 25.000 km); with the configurations built on the apparent direction, the truth plane is 1.000000 at 120 and 150 degrees.
3. **The frame below the truth plane: SatSim floors every pixel to a whole count (cause shown).** It does so even with float32 output. The POPPY PSF's tails, under one count per pixel, are lost: 0.1 % at 0 degrees and 5 ms, 2.3 % at 150 degrees, 0.5 % at 1 ms, 0.02 % at 20 ms. The loss falls as the counts rise. With no PSF the frame equals the truth plane.
4. **The Gaussian PSF loses 1.3 % of the flux (cause shown).** At energy-on-detector 0.989 (σ 0.18 pixel, 0.55 oversampled pixel) the truth plane holds 0.987384 of the expectation. Variation: at 0.8 (a wider kernel) it holds 1.000000. The narrow kernel's sampled normalization loses the flux.
5. **PSF and encircled energy: different models (as measured).** SatSim's POPPY PSF from the 85 mm aperture puts 0.484 of the point's flux in the brightest pixel, 0.949 in 3 x 3 and 0.969 in 5 x 5, with the point 0.27 pixel from a pixel centre. DIRSIG states no PSF and applies its own spread (σ about 0.18 pixel). For an unresolved object it also ends sampling outside the hypersampled 3 x 3 pixels (A: 20 paths, no hit), so all its flux lies inside them. The plate's edge shows the same contrast. DIRSIG at the default sampling: 0.18 and 0.21 in the partial pixels and 0 outside. Round 30 measured 0.070 outside at 1000 paths. SatSim with POPPY: 0.043, 0.013 and 0.008 one, two and three pixels outside. A like-for-like comparison would put both points at the same sub-pixel position (OPEN).
6. **The plate's footprint: a sprite on the oversampled grid (cause shown).** 616 pixels at least half full, against DIRSIG's 576 and the plate's 599.27 pixel area. The sprite's side is a whole number of oversampled pixels (73, 24.33 pixels), and its edges land at a third of a pixel (edge pixels 0.80 and 0.50).
7. **Where the sprite lands (cause shown).** Its centroid is 11.9 pixels from the tracked target's position along both axes. Variation: a sprite 26 oversampled pixels larger moves it to 16.2 pixels. The shift grows with half the sprite's size (4.33 pixels predicted, 4.36 measured), so a sprite is not centred on its object's position. SatSim's own code carries a "TODO need to investigate +1 shift" there.

**Time and frame conventions.**

| | DIRSIG (through the SDK) | SatSim |
|---|---|---|
| Epoch | `descriptor.collection.epoch` (UTC, `Z`), DIRSIG's reference date-time `2026-09-26T18:50:25.0000+00:00` | `geometry.time`, a UTC list `[2026, 9, 26, 18, 50, 25.0]`; Skyfield's TT internally |
| Exposure window | [task time, task time + exposure]: `relative_time_window` [0.0, 0.005] (and round 30's streaks start at the task time) | [t, t + exposure] for frame 0 (`docs/SatSim_probe.md`, code) |
| Frame time stamped | none in the image; the log's window | `DATE-OBS`, `TIME-OBS`, `SH-UT001` and the annotation's `time` are mid-exposure (18:50:25.0025); `SH-UT002` is mid + exposure (18:50:25.0075), half an exposure past the end |
| Spatial frame | scene ENU at a geodetic origin (39 N, 120 W); the platform pose in `sceneenu` | GCRS (km); the WCS `RADESYS` `GAPPT` |
| Sun | a fixed direction in the scene frame from `fixed_ephemeris`; the epoch does not move it | de421 at the epoch, apparent (2 above) |
| Light time, aberration | none | on by default (light transit and stellar aberration); they change the annotated range by up to 2 m at 25 km and not the target's flux |

`docs/SatSim_probe.md` described `DATE-OBS` as the observation start; it is mid-exposure (corrected there).

### The adapter seam: what the shared `run-spec/1` carries

- **DIRSIG reads the engine block and part of the descriptor.** Assembling the job for the plate's spec and for variants with one member changed (scratch, no render): `collection.epoch` changes the tasks file, `settings[0].exposure_time` and `gain` change the platform file. `collection.geometry.range` doubled, `collection.illumination.regime`, `extras`, `meta.description` and `fidelity.valid_for` leave every job file byte-identical. The geometry DIRSIG renders comes from `engine.motion`, and nothing checks the descriptor's range against it.
- **SatSim reads only its engine block.** Its descriptor must be opaque: a SatSim spec with `collection`, `sensor` or `settings` beside `opaque` is refused by the schema, and without `opaque` by the pass-through rule. The shared numbers can therefore live only in `descriptor.extras`, where neither engine reads them. Everything SatSim renders is in the configuration, whose content hash is in the engine block.
- **The run id.** It is the hash of the whole resolved spec, so every field either engine ignores still changes it. The direction is safe: two runs that render the same can differ in id, but two that render differently cannot share one. There is one exception, found here. The SatSim adapter's admission scan for files a configuration names (`$import`, `$cache`, `path`, `file`) does not include the sprite model's `filename`. A single-file configuration naming a sprite, even at an absolute path outside the library, is admitted (`config_problems` returns no problem). The sprite is then neither staged nor hashed, so two different sprites could run under one id. The family's plate uses a directory reference, so its sprite is hashed with it, and names it `input/plate.fits`, the path where the launcher stages the directory (BACKLOG).

### The audit's SatSim cells after round 31

| Axis | Unresolved | Hyperresolved |
|---|---|---|
| Platform motion | measured at zero relative speed: a space observer on a two-body GCRS state rate-tracking a co-moving target; no streak | measured as above with the plate as a sprite |
| Target motion | expressible, unmeasured (no relative speed run) | expressible, unmeasured |
| Shutter blur | exposure scaling measured (exact in the truth plane, 1 to 20 ms); blur unmeasured | unmeasured |
| Off-nadir look angle | no Earth in SatSim: not a parameter of a target's signal against space | as unresolved |
| Sun angle | measured: 0, 60, 120, 150 degrees from the real Sun, the Lambertian phase function to 5.1e-4 (the apparent Sun, 2 above) | not expressible: a sprite has no shading or phase |
