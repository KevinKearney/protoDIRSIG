# DIRSIG Motion and Temporal Sampling

## Architecture Overview

DIRSIG5 models motion as a continuous 4D (spatial + temporal) construct sampled stochastically via Monte Carlo path tracing. There is no discrete motion step loop and no per-step full radiometry solve. Instead, each ray carries a timestamp drawn from a distribution over the integration time window; the motion model is evaluated at that timestamp to determine instantaneous pose for all moving bodies before geometry intersection proceeds.

This is physically correct motion blur by construction — the detector pixel accumulates the time-integral of at-aperture radiance over the dwell window, naturally captured as the stochastic ray population samples the RSO's trajectory through that window.

---

## Motion Model Framework

Platform, object, and mount motion share a common `FlexMotion` architecture that decouples location from orientation via composable engines.

**Location engines:**

| Engine | Input | Notes |
|--------|-------|-------|
| `Fixed` | Position + optional jitter | Static with perturbation |
| `Waypoints` | Time-tagged position table | Scene ENU, Geodetic, UTM, or ECEF; ingests STK `.e` ephemeris directly |
| `Straight` | Origin + velocity vector | Constant-velocity linear |
| `Circling` | Center + radius + rate | Constant angular rate |
| `SGP4` | TLE | Two-body propagator, native DIRSIG5 |

**Orientation engines:** Euler angle time-series, Spin (constant rate), Quaternion time-series, Velocity-derived, LookAt (stare-point tracking).

**Coordinate system:** All motion is ECEF-referenced at simulation time. There is no native ECI frame — TLE-derived SGP4 output in ECI must be converted to ECEF externally before ingestion. Earth rotation is implicit: a geodetically fixed object is carried with the rotating Earth frame.

**Jitter model:** Configurable independently in all six DoF. Two models: temporally uncorrelated (Gaussian, mean + σ) and temporally correlated (PSD-specified as frequency/magnitude/phase triplets).

---

## Time-Tagged Ray Trace: DIRSIG4 vs. DIRSIG5

| Dimension | DIRSIG4 | DIRSIG5 |
|-----------|---------|---------|
| Temporal sampling | Separate pass; entire detector re-rendered N times | Unified: ray timestamp drawn simultaneously with spatial sample |
| Cost scaling | O(N × pixels) — brute force | Amortized into per-pixel path budget |
| Sub-pixel sampling | Fixed N×M spatial grid | Adaptive, convergence-driven |
| Motion blur | Correct but expensive | Correct and efficient |

In DIRSIG5, ray timestamps are drawn uniformly across the integration time window as part of the same adaptive sampling loop that handles spatial anti-aliasing. A moving RSO produces physically correct streak or blur as a natural consequence — no special handling required.

---

## Implications for RSO Simulation

**Streak geometry:** A fast-moving RSO will produce a correctly integrated streak across the detector. Streak length and orientation are determined by the RSO's projected angular velocity and the integration time — no post-processing approximation involved.

**Tumbling targets:** Rapidly varying specular glints from a tumbling RSO demand higher path counts per pixel (high radiance variance → slow Monte Carlo convergence). The cost is not additional motion steps but additional rays. `--min_paths` and `--max_paths` are the tuning parameters; convergence is driven by a radiance threshold criterion.

**Temporal resolution bottleneck:** DIRSIG outputs are already the temporally-integrated result over the full integration window. Interpolating between DIRSIG output frames is interpolating integrated images. For smooth motion this is acceptable; for tumbling targets with sharp specular features it is not — the integrand (instantaneous radiance) has structure that aliases across the temporal integration boundary. Any surrogate model must operate at the scene/radiance layer prior to temporal integration, not on output frames.

**ECI gap:** The absence of a native ECI frame is the principal operational friction for SSA workflows. SGP4 propagators output in ECI; conversion to ECEF must be handled externally (e.g., `astropy.coordinates`, `skyfield`) before ephemeris data is ingested by DIRSIG.

---

## Batch Execution Relevance

The per-ray motion model evaluation is computationally cheap relative to the radiometric path trace — motion complexity does not significantly affect wall time. Run time is dominated by scene complexity (number of geometric primitives, material scattering models) and convergence criteria (path counts). For the background canvas and RSO chip generation use cases, the exo-atmospheric scene geometry is minimal and per-path evaluation is fast; convergence to acceptable noise floors at 4K-equivalent resolution is the binding constraint, not motion evaluation cost.
