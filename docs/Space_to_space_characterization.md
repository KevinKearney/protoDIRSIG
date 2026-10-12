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
