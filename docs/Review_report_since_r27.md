# Review report: the repository since review-r27

For a reviewer who holds the tag `review-r27` (commit `9ded055`) and nothing later. Rounds 28 to 36 added measurements, documents, notebooks and scripts on top of that tag, additively: no member of `dirsig-engine/1` was added, `run-spec/1`, the existing entries of `tests/data/id_snapshot.json`, `packages/core` and the adapter protocol are as tagged. Round 37 wrote this report, ran a consistency pass over the documents (section 7) and reran one comparison (foxbat, section 2.3).

Every table between a `<!-- generated: ... -->` marker and its end marker is written by `scripts/review_report.py` from the committed records named under it (the results files, the spec index, the sensor library, git history, and cells of committed documents); `python scripts/review_report.py --check` exits 1 if any such table differs from what those files give now. Numbers in the prose are quoted from the documents each paragraph names.

## 1. What changed since review-r27

One row per round. A round's range runs from the previous round's last commit (exclusive) to its own last commit, which holds that round's log; "files added" are the paths present at the round's last commit and absent at the previous one.

<!-- generated: rounds -->
| Round | Commits (first..last) | Commits | Files added | Files added (more than 4 under one folder: the folder and a count) |
|---|---|---|---|---|
| 28 | `0d8f874`..`796ecd5` | 5 | 0 | none |
| 29 | `71e933a`..`91ebb4f` | 4 | 82 | `docs/Space_to_space_characterization.md`, `manifold_config_repo/scenes/s2s_targets/` (15 files), `manifold_run_specs/s2s/` (64 files), `scripts/s2s_scenarios.py`, `tests/test_s2s_scenarios.py` |
| 30 | `aeac0a7`..`142b06b` | 4 | 60 | `manifold_config_repo/scenes/s2s_blur/` (39 files), `manifold_run_specs/s2s/` (21 files) |
| 31 | `020b653`..`a2d992f` | 3 | 64 | `manifold_config_repo/satsim/s2s/` (11 files), `manifold_config_repo/scenes/s2s_sun/` (16 files), `manifold_run_specs/s2s/` (37 files) |
| 32 | `594d37d`..`b2e2c86` | 3 | 5 | `docs/DIRSIG_transfer_scenes.md`, `docs/data/s2s_results.jsonl`, `scripts/s2s_measure.py`, `scripts/survey_transfer.py`, `tests/test_s2s_results.py` |
| 33 | `5bcef1f`..`6180991` | 6 | 3 | `docs/data/risk_measurements.jsonl`, `scripts/risk_measure.py`, `tests/test_risk_measurements.py` |
| 34 | `7ffc2c4`..`df68496` | 5 | 6 | `docs/Authoring_layered_form.md`, `docs/Engine_author_guide.md`, `notebooks/stage_06_space_to_space.ipynb`, `tests/test_authoring_guide.py`, `tests/test_engine_author_guide.py`, `tests/test_stage06_notebook.py` |
| 35 | `dc7a13d`..`8a59ced` | 5 | 9 | `docs/Authoring_friction_audit.md`, `docs/User_glossary.md`, `docs/User_manual.md`, `notebooks/quickstart_sdk.ipynb`, `scripts/recipe_form.py`, `tests/test_friction_audit.py`, `tests/test_quickstart_notebook.py`, `tests/test_recipe_form.py`, `tests/test_user_manual.py` |
| 36 | `18d2bb8`..`3fa0a02` | 4 | 5 | `docs/Bigger_host_plan.md`, `docs/data/bigger_host_manifest.yaml`, `scripts/bigger_host_run.py`, `tests/test_bigger_host_run.py`, `tests/data/bigger_host_fake_manifest.yaml` |
<!-- end generated: rounds -->

What each round did, by its commit messages: 28, survey truth for files a `TEMP_SOLVER` or `SOURCE_SHAPE` names and eight more layered-against-pass-through comparisons; 29, the space-to-space coverage audit, scenario family I (63 specs) and its first measurements; 30, family II (shutter blur, look angle against a background) and round 29's three unexplained differences; 31, family III (Sun and phase angle on a sphere) and SatSim parity on one geometry; 32, the CONOPS decisions index (section 10.1), the measurement harness `scripts/s2s_measure.py` with `docs/data/s2s_results.jsonl`, and the survey of the scenes Kevin transferred; 33, risks A to E with `scripts/risk_measure.py` and `docs/data/risk_measurements.jsonl`; 34, the authoring guide, the engine author guide, notebook stage 06 and `compare_layered.py --threads`; 35, the authoring friction audit, the user manual, the quick-start notebook and the recipe form prototype; 36, the deferred-work inventory, its manifest and the runner `scripts/bigger_host_run.py`.

## 2. What was measured

### 2.1 Space-to-space imaging

Source: `docs/data/s2s_results.jsonl` (one record per DIRSIG spec measured; `python scripts/s2s_measure.py --check` recomputes each record's expectation) and `docs/Space_to_space_characterization.md`. Every DIRSIG point was rendered at the native 500 x 500 window, one thread, seed 1, through `Simulation.run`, except round 38's twelve `-w64` coverage points (64 x 64; `docs/s2s_coverage.md`, and the characterization's "Coverage points (round 38)"); a one-thread render repeats bit for bit, and round 32 re-rendered 62 of round 29's and 30's points to the digests those rounds recorded. Equivalent pixels are the image sum over `full_pixel`, the signal of a pixel wholly on a plate of reflectance 0.5 facing the Sun at the zenith.

**Aperture factor.** DIRSIG renders with the exact aperture cone, not the paraxial term: the rendered full pixel is the paraxial value times 1 / (1 + 1 / (4 N²)). SatSim's chain has no f-number; its zeropoint that carries the factor reproduces DIRSIG's scale.

<!-- generated: aperture -->
| Quantity | Value | Source |
|---|---|---|
| f-number N = focal length / aperture | 306 mm / 85 mm = 3.6 | `manifold_sensors/auror-nir.yaml` |
| exact-cone factor 1 / (1 + 1 / (4 N²)) | 0.981075 | computed from the two above |
| `full_pixel` at 1 ms (DIRSIG, e⁻ m⁻²) | 5.656931e+15 | `docs/data/s2s_results.jsonl` (family I, 25 km, nadir) |
| paraxial value at 1 ms (`full_pixel` / factor) | 5.76605e+15 | computed |
| `full_pixel` at 5 ms (DIRSIG, e⁻ m⁻²) | 2.828466e+16 | `docs/data/s2s_results.jsonl` (family I, 25 km, nadir) |
| paraxial value at 5 ms (`full_pixel` / factor) | 2.88303e+16 | computed |
| `full_pixel` at 20 ms (DIRSIG, e⁻ m⁻²) | 1.131386e+17 | `docs/data/s2s_results.jsonl` (family I, 25 km, nadir) |
| paraxial value at 20 ms (`full_pixel` / factor) | 1.15321e+17 | computed |
| SatSim truth plane / paraxial expectation with the cone zeropoint (`zpcone`) | 0.981075 | `docs/Space_to_space_characterization.md`, SatSim parity, Results |
<!-- end generated: aperture -->

**Flux closure, hyperresolved plate (family I).** A 20 m plate, nadir unless stated. The half-level count falls below the footprint where the edge pixels fall below half a full pixel; the peak is a full pixel.

<!-- generated: flux -->
| Spec | Range (km) | Exposure (ms) | Look (deg) | Solar zenith (deg) | Equivalent px | Expected px | Ratio | Half-level count / expected | Peak / full pixel |
|---|---|---|---|---|---|---|---|---|---|
| `s2s-hyperresolved-r12p5km-v0mps-e5ms-l0-z0-d0` | 12.5 | 5 | 0 | 0 | 2396.89 | 2397.08 | 0.99992 | 0.9941 | 1 |
| `s2s-hyperresolved-r25km-v0mps-e1ms-l0-z0-d0` | 25 | 1 | 0 | 0 | 599.84 | 599.27 | 1.00095 | 0.9612 | 1 |
| `s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0` | 25 | 5 | 0 | 0 | 599.84 | 599.27 | 1.00095 | 0.9612 | 1 |
| `s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0-w64` | 25 | 5 | 0 | 0 | 599.76 | 599.27 | 1.00082 | 0.9612 | 1 |
| `s2s-hyperresolved-r25km-v0mps-e5ms-l0-z30-d0` | 25 | 5 | 0 | 30 | 519.483 | 518.983 | 1.00096 | 0.9612 | 1.00001 |
| `s2s-hyperresolved-r25km-v0mps-e5ms-l0-z60-d0` | 25 | 5 | 0 | 60 | 299.934 | 299.635 | 1.00100 | 0.9612 | 1.00006 |
| `s2s-hyperresolved-r25km-v0mps-e5ms-l0-z75-d0-w64` | 25 | 5 | 0 | 75 | 155.245 | 155.103 | 1.00092 | 0.9612 | 1.00015 |
| `s2s-hyperresolved-r25km-v0mps-e5ms-l30-z0-d0` | 25 | 5 | 30 | 0 | 519.06 | 518.983 | 1.00015 | 1.015 | 1 |
| `s2s-hyperresolved-r25km-v0mps-e5ms-l30-z30-d0-w64` | 25 | 5 | 30 | 30 | 449.594 | 449.453 | 1.00031 | 1.017 | 1.00001 |
| `s2s-hyperresolved-r25km-v0mps-e5ms-l45-z45-d0-w64` | 25 | 5 | 45 | 45 | 299.681 | 299.635 | 1.00015 | 1.019 | 1.00003 |
| `s2s-hyperresolved-r25km-v0mps-e5ms-l60-z0-d0` | 25 | 5 | 60 | 0 | 300.05 | 299.635 | 1.00138 | 0.9612 | 1 |
| `s2s-hyperresolved-r25km-v0mps-e5ms-l60-z60-d0-w64` | 25 | 5 | 60 | 60 | 150.088 | 149.818 | 1.00180 | 0.9612 | 1.00006 |
| `s2s-hyperresolved-r25km-v0mps-e20ms-l0-z0-d0` | 25 | 20 | 0 | 0 | 599.84 | 599.27 | 1.00095 | 0.9612 | 1 |
| `s2s-hyperresolved-r50km-v0mps-e5ms-l0-z0-d0` | 50 | 5 | 0 | 0 | 150.62 | 149.818 | 1.00536 | 0.9612 | 1 |
| `s2s-hyperresolved-r100km-v0mps-e5ms-l0-z0-d0` | 100 | 5 | 0 | 0 | 37.76 | 37.4544 | 1.00816 | 0.9612 | 1 |
<!-- end generated: flux -->

**Unresolved objects (families I and III).** The labelled (`::IMPORTANT::`) objects stand in front of a black backstop. Without a surface behind it a sub-pixel object renders zero: DIRSIG's earth core ends a pixel's sampling at its first path to it (the characterization document, family II, C1). Where the plate fills more than about a third of a pixel the flux follows R⁻²; below that the estimate is a hit count.

<!-- generated: unresolved -->
| Spec | Target | `::IMPORTANT::` | Point | Equivalent px | Expected px | Ratio |
|---|---|---|---|---|---|---|
| `s2s-unresolved-r12p5km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | yes | 12.5 km, offset 0 px, 5 ms, look 0, zenith 0 | 1.49 | 1.4982 | 0.99446 |
| `s2s-unresolved-r12p5km-v0mps-e5ms-l0-z0-d0p25` | 0.5 m plate | yes | 12.5 km, offset 0.25 px, 5 ms, look 0, zenith 0 | 1.467 | 1.4982 | 0.97937 |
| `s2s-unresolved-r12p5km-v0mps-e5ms-l0-z0-d0p5` | 0.5 m plate | yes | 12.5 km, offset 0.5 px, 5 ms, look 0, zenith 0 | 1.502 | 1.4982 | 1.00285 |
| `s2s-unresolved-r12p5km-v0mps-e5ms-l0-z0-d0p75` | 0.5 m plate | yes | 12.5 km, offset 0.75 px, 5 ms, look 0, zenith 0 | 1.485 | 1.4982 | 0.99144 |
| `s2s-unresolved-r25km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | yes | 25 km, offset 0 px, 5 ms, look 0, zenith 0 | 0.3725 | 0.37454 | 0.99454 |
| `s2s-unresolved-r25km-v0mps-e5ms-l0-z0-d0-w64` | 0.5 m plate | yes | 25 km, offset 0 px, 5 ms, look 0, zenith 0 | 0.3675 | 0.37454 | 0.98119 |
| `s2s-unresolved-r25km-v0mps-e5ms-l0-z60-d0-w64` | 0.5 m plate | yes | 25 km, offset 0 px, 5 ms, look 0, zenith 60 | 0.1838 | 0.18727 | 0.98126 |
| `s2s-unresolved-r25km-v0mps-e5ms-l15-z0-d0-w64` | 0.5 m plate | yes | 25 km, offset 0 px, 5 ms, look 15, zenith 0 | 0.36 | 0.36178 | 0.99508 |
| `s2s-unresolved-r25km-v0mps-e5ms-l30-z30-d0-w64` | 0.5 m plate | yes | 25 km, offset 0 px, 5 ms, look 30, zenith 30 | 0.2754 | 0.28091 | 0.98039 |
| `s2s-unresolved-r25km-v0mps-e5ms-l45-z0-d0-w64` | 0.5 m plate | yes | 25 km, offset 0 px, 5 ms, look 45, zenith 0 | 0.245 | 0.26484 | 0.92508 |
| `s2s-unresolved-r25km-v0mps-e5ms-l50-z0-d0-w64` | 0.5 m plate | yes | 25 km, offset 0 px, 5 ms, look 50, zenith 0 | 0.22 | 0.24075 | 0.91380 |
| `s2s-unresolved-r25km-v0mps-e5ms-l55-z0-d0-w64` | 0.5 m plate | yes | 25 km, offset 0 px, 5 ms, look 55, zenith 0 | 0.1945 | 0.21483 | 0.90537 |
| `s2s-unresolved-r25km-v0mps-e5ms-l60-z0-d0-w64` | 0.5 m plate | yes | 25 km, offset 0 px, 5 ms, look 60, zenith 0 | 0.1695 | 0.18727 | 0.90510 |
| `s2s-unresolved-r25km-v0mps-e5ms-l65-z0-d0-w64` | 0.5 m plate | yes | 25 km, offset 0 px, 5 ms, look 65, zenith 0 | 0.1385 | 0.15829 | 0.87498 |
| `s2s-unresolved-r25km-v0mps-e5ms-l0-z0-d0p25` | 0.5 m plate | yes | 25 km, offset 0.25 px, 5 ms, look 0, zenith 0 | 0.3822 | 0.37454 | 1.02047 |
| `s2s-unresolved-r25km-v0mps-e5ms-l60-z0-d0p25-w64` | 0.5 m plate | yes | 25 km, offset 0.25 px, 5 ms, look 60, zenith 0 | 0.187 | 0.18727 | 0.99855 |
| `s2s-unresolved-r25km-v0mps-e5ms-l0-z0-d0p5` | 0.5 m plate | yes | 25 km, offset 0.5 px, 5 ms, look 0, zenith 0 | 0.3621 | 0.37454 | 0.96672 |
| `s2s-unresolved-r25km-v0mps-e5ms-l60-z0-d0p5-w64` | 0.5 m plate | yes | 25 km, offset 0.5 px, 5 ms, look 60, zenith 0 | 0.1908 | 0.18727 | 1.01875 |
| `s2s-unresolved-r25km-v0mps-e5ms-l0-z0-d0p75` | 0.5 m plate | yes | 25 km, offset 0.75 px, 5 ms, look 0, zenith 0 | 0.3626 | 0.37454 | 0.96820 |
| `s2s-unresolved-r50km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | yes | 50 km, offset 0 px, 5 ms, look 0, zenith 0 | 0.0765 | 0.093636 | 0.81699 |
| `s2s-unresolved-r50km-v0mps-e5ms-l0-z0-d0p25` | 0.5 m plate | yes | 50 km, offset 0.25 px, 5 ms, look 0, zenith 0 | 0.09 | 0.093636 | 0.96117 |
| `s2s-unresolved-r50km-v0mps-e5ms-l0-z0-d0p5` | 0.5 m plate | yes | 50 km, offset 0.5 px, 5 ms, look 0, zenith 0 | 0.09145 | 0.093636 | 0.97670 |
| `s2s-unresolved-r50km-v0mps-e5ms-l0-z0-d0p75` | 0.5 m plate | yes | 50 km, offset 0.75 px, 5 ms, look 0, zenith 0 | 0.068 | 0.093636 | 0.72622 |
| `s2s-unresolved-r100km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | yes | 100 km, offset 0 px, 5 ms, look 0, zenith 0 | 0.0165 | 0.023409 | 0.70486 |
| `s2s-unresolved-r200km-v0mps-e1ms-l0-z0-d0` | 0.5 m plate | yes | 200 km, offset 0 px, 1 ms, look 0, zenith 0 | 0.0045 | 0.0058523 | 0.76894 |
| `s2s-unresolved-r200km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | yes | 200 km, offset 0 px, 5 ms, look 0, zenith 0 | 0.0045 | 0.0058523 | 0.76894 |
| `s2s-unresolved-r200km-v1000mps-e5ms-l0-z0-d0` | 0.5 m plate | yes | 200 km, offset 0 px, 5 ms, look 0, zenith 0, 1000 m/s | 0.002 | 0.0058523 | 0.34175 |
| `s2s-unresolved-r200km-v7500mps-e5ms-l0-z0-d0` | 0.5 m plate | yes | 200 km, offset 0 px, 5 ms, look 0, zenith 0, 7500 m/s | 0.0015 | 0.0058523 | 0.25631 |
| `s2s-unresolved-r200km-v0mps-e5ms-l0-z30-d0` | 0.5 m plate | yes | 200 km, offset 0 px, 5 ms, look 0, zenith 30 | 0.003897 | 0.0050682 | 0.76894 |
| `s2s-unresolved-r200km-v0mps-e5ms-l0-z60-d0` | 0.5 m plate | yes | 200 km, offset 0 px, 5 ms, look 0, zenith 60 | 0.00225 | 0.0029261 | 0.76898 |
| `s2s-unresolved-r200km-v0mps-e5ms-l30-z0-d0` | 0.5 m plate | yes | 200 km, offset 0 px, 5 ms, look 30, zenith 0 | 0.0035 | 0.0050682 | 0.69058 |
| `s2s-unresolved-r200km-v0mps-e5ms-l60-z0-d0` | 0.5 m plate | yes | 200 km, offset 0 px, 5 ms, look 60, zenith 0 | 0.001 | 0.0029261 | 0.34175 |
| `s2s-unresolved-r200km-v0mps-e20ms-l0-z0-d0` | 0.5 m plate | yes | 200 km, offset 0 px, 20 ms, look 0, zenith 0 | 0.0045 | 0.0058523 | 0.76894 |
| `s2s-unresolved-r200km-v0mps-e5ms-l0-z0-d0p25` | 0.5 m plate | yes | 200 km, offset 0.25 px, 5 ms, look 0, zenith 0 | 0.0105 | 0.0058523 | 1.79418 |
| `s2s-unresolved-r200km-v0mps-e5ms-l0-z0-d0p5` | 0.5 m plate | yes | 200 km, offset 0.5 px, 5 ms, look 0, zenith 0 | 0.006 | 0.0058523 | 1.02525 |
| `s2s-unresolved-r200km-v0mps-e5ms-l0-z0-d0p75` | 0.5 m plate | yes | 200 km, offset 0.75 px, 5 ms, look 0, zenith 0 | 0.006 | 0.0058523 | 1.02525 |
| `s2s-unresolved-r400km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | yes | 400 km, offset 0 px, 5 ms, look 0, zenith 0 | 0.0005 | 0.0014631 | 0.34175 |
| `s2s-unresolved-r773p093km-vorbit-e5ms-l1p8-z0-d0` | 0.5 m plate | yes | 773.093 km, offset 0 px, 5 ms, look 1.8, zenith 0, the orbit form | 0.0005 | — | — |
| `s2s-unresolved-r800km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | yes | 800 km, offset 0 px, 5 ms, look 0, zenith 0 | 0.0005 | 0.00036577 | 1.36700 |
| `s2s-unresolvedplain-r12p5km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | no | 12.5 km, offset 0 px, 5 ms, look 0, zenith 0 | 1.6 | 1.4982 | 1.06797 |
| `s2s-unresolvedplain-r25km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | no | 25 km, offset 0 px, 5 ms, look 0, zenith 0 | 0.4 | 0.37454 | 1.06797 |
| `s2s-unresolvedplain-r25km-v0mps-e5ms-l60-z0-d0-w64` | 0.5 m plate | no | 25 km, offset 0 px, 5 ms, look 60, zenith 0 | 0.1 | 0.18727 | 0.53398 |
| `s2s-unresolvedplain-r50km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | no | 50 km, offset 0 px, 5 ms, look 0, zenith 0 | 0.03 | 0.093636 | 0.32039 |
| `s2s-unresolvedplain-r100km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | no | 100 km, offset 0 px, 5 ms, look 0, zenith 0 | 0 | 0.023409 | 0.00000 |
| `s2s-unresolvedplain-r200km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | no | 200 km, offset 0 px, 5 ms, look 0, zenith 0 | 0 | 0.0058523 | 0.00000 |
| `s2s-unresolvedplain-r400km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | no | 400 km, offset 0 px, 5 ms, look 0, zenith 0 | 0 | 0.0014631 | 0.00000 |
| `s2s-unresolvedplain-r800km-v0mps-e5ms-l0-z0-d0` | 0.5 m plate | no | 800 km, offset 0 px, 5 ms, look 0, zenith 0 | 0 | 0.00036577 | 0.00000 |
| `s2s3-phase-unresolved-a0-l0-z0` | 0.25 m sphere | yes | 25 km, phase 0 (look 0, zenith 0) | 0.1924 | 0.19611 | 0.98104 |
| `s2s3-phase-unresolved-a20-l10-z10` | 0.25 m sphere | yes | 25 km, phase 20 (look 10, zenith 10) | 0.181 | 0.18516 | 0.97774 |
| `s2s3-phase-unresolved-a40-l20-z20` | 0.25 m sphere | yes | 25 km, phase 40 (look 20, zenith 20) | 0.1539 | 0.15697 | 0.98067 |
| `s2s3-phase-unresolved-a60-l30-z30` | 0.25 m sphere | yes | 25 km, phase 60 (look 30, zenith 30) | 0.1178 | 0.11943 | 0.98629 |
| `s2s3-phase-unresolved-a80-l40-z40` | 0.25 m sphere | yes | 25 km, phase 80 (look 40, zenith 40) | 0.08061 | 0.080395 | 1.00268 |
| `s2s3-phase-unresolved-a100-l50-z50` | 0.25 m sphere | yes | 25 km, phase 100 (look 50, zenith 50) | 0.04831 | 0.04634 | 1.04246 |
| `s2s3-phase-unresolved-a120-l60-z60` | 0.25 m sphere | yes | 25 km, phase 120 (look 60, zenith 60) | 0.02247 | 0.021376 | 1.05110 |
| `s2s3-phase-unresolved-a135-l67p5-z67p5` | 0.25 m sphere | yes | 25 km, phase 135 (look 67.5, zenith 67.5) | 0.01099 | 0.0094726 | 1.16066 |
| `s2s3-phase-unresolved-a150-l75-z75` | 0.25 m sphere | yes | 25 km, phase 150 (look 75, zenith 75) | 0.00323 | 0.0029058 | 1.11165 |
| `s2s3-phase-unresolvedplain-a0-l0-z0` | 0.25 m sphere | no | 25 km, phase 0 (look 0, zenith 0) | 0.2026 | 0.19611 | 1.03334 |
| `s2s3-phase-unresolvedplain-a80-l40-z40` | 0.25 m sphere | no | 25 km, phase 80 (look 40, zenith 40) | 0.08294 | 0.080395 | 1.03169 |
| `s2s3-phase-unresolvedplain-a150-l75-z75` | 0.25 m sphere | no | 25 km, phase 150 (look 75, zenith 75) | 0.002717 | 0.0029058 | 0.93497 |
<!-- end generated: unresolved -->

**Shutter blur (family II).** The 20 m plate and a barred background under platform motion, target motion and both, 1000 m/s each, 25 km. The `both` group's native specs have no records (deferred: `docs/Bigger_host_plan.md`); round 38 measured it at 64 x 64 at 0.1, 1 and 5 ms (the `-w64` rows: flux to 1.6e-3, sweep 0.981 at 5 ms). The fitted streak is 1.7 to 3.1 % short of v·t / footprint at 5 and 20 ms, for the target and the background alike, and `integration_samples` 10 and 100 render byte-identical images (not explained; BACKLOG). The orbit pair holds a 100 m plate still over 20 ms.

<!-- generated: blur -->
| Spec | Group | Exposure (ms) | Flux ratio | Fitted streak (px) | v·t / footprint (px) | Fitted / expected |
|---|---|---|---|---|---|---|
| `s2s2-blur-static-e5ms` | static | 5 | 1.00095 | 0.6205 | 0 | — |
| `s2s2-blur-platform-e0p1ms` | platform | 0.1 | 1.00085 | 0.6031 | 0.1224 | 4.927 |
| `s2s2-blur-platform-e1ms` | platform | 1 | 0.99950 | 1.233 | 1.224 | 1.007 |
| `s2s2-blur-platform-e5ms` | platform | 5 | 1.00023 | 5.973 | 6.12 | 0.9759 |
| `s2s2-blur-platform-e20ms` | platform | 20 | 0.99801 | 23.85 | 24.48 | 0.9743 |
| `s2s2-blur-target-e0p1ms` | target | 0.1 | 1.00085 | 0.6031 | 0.1224 | 4.927 |
| `s2s2-blur-target-e1ms` | target | 1 | 0.99952 | 1.233 | 1.224 | 1.007 |
| `s2s2-blur-target-e5ms` | target | 5 | 1.00023 | 5.973 | 6.12 | 0.9759 |
| `s2s2-blur-target-e20ms` | target | 20 | 0.99800 | 23.85 | 24.48 | 0.9743 |
| `s2s2-blur-target-r100km-e20ms-w64` | target | 20 | 0.99107 | 5.97 | 6.12 | 0.9755 |
| `s2s2-blur-both-e0p1ms-w64` | both | 0.1 | 1.00162 | 0.6267 | 0.2448 | 2.56 |
| `s2s2-blur-both-e1ms-w64` | both | 1 | 1.00003 | 2.467 | 2.448 | 1.008 |
| `s2s2-blur-both-e5ms-n2-w64` | both | 5 | 1.00023 | 12.01 | 12.24 | 0.9809 |
| `s2s2-blur-both-e5ms-w64` | both | 5 | 1.00023 | 12.01 | 12.24 | 0.9809 |
| `s2s2-orbit-e0p1ms` | orbit | 0.1 | 1.00576 | — | — | — |
| `s2s2-orbit-e20ms` | orbit | 20 | 1.00576 | — | — | — |
<!-- end generated: blur -->

**Look angle against a background (family II).** At 75 degrees the line of sight past the plate leaves the background plate and meets the earth core, and the plate's flux falls to 0.957 of its projected area.

<!-- generated: look -->
| Spec | Look (deg) | Equivalent px | Expected px (projected area) | Ratio | Bar period, measured (px) | Bar period, expected (px) | Ratio |
|---|---|---|---|---|---|---|---|
| `s2s2-look-l0` | 0 | 599.84 | 599.27 | 1.00095 | 96 | 96 | 1 |
| `s2s2-look-l15` | 15 | 579.21 | 578.851 | 1.00062 | 93 | 92.66 | 1.004 |
| `s2s2-look-l30` | 30 | 519.05 | 518.983 | 1.00013 | 83 | 82.89 | 1.001 |
| `s2s2-look-l45` | 45 | 423.83 | 423.748 | 1.00019 | 67.5 | 67.34 | 1.002 |
| `s2s2-look-l60` | 60 | 300.04 | 299.635 | 1.00135 | 47 | 47.08 | 0.9984 |
| `s2s2-look-l75` | 75 | 148.442 | 155.103 | 0.95705 | — | 23.53 | — |
<!-- end generated: look -->

**Phase function (family III).** A 10 m Lambertian sphere (DIRSIG's analytic primitive) at 25 km, expected (2/3) π R² / g² × Φ(a), and the same sphere at nadir against a barred plate whose level follows cos θs. At 60 degrees the three splits of look and Sun give the same signal.

<!-- generated: phase -->
| Spec | Group | Phase (deg) | Look (deg) | Solar zenith (deg) | Equivalent px | Expected px | Ratio | Bar level / (0.5 cos θs) |
|---|---|---|---|---|---|---|---|---|
| `s2s3-background-z0` | background | 0 | 0 | 0 | 314.374 | 313.777 | 1.00190 | 1.00000 |
| `s2s3-background-z30` | background | 30 | 0 | 30 | 277.026 | 276.388 | 1.00231 | 1.00001 |
| `s2s3-background-z60` | background | 60 | 0 | 60 | 191.504 | 191.09 | 1.00217 | 1.00006 |
| `s2s3-background-z75` | background | 75 | 0 | 75 | 144.219 | 143.849 | 1.00258 | 1.00015 |
| `s2s3-phase-hyperresolved-a0-l0-z0` | hyperresolved | 0 | 0 | 0 | 314.14 | 313.777 | 1.00116 | — |
| `s2s3-phase-hyperresolved-a20-l10-z10` | hyperresolved | 20 | 10 | 10 | 296.611 | 296.253 | 1.00121 | — |
| `s2s3-phase-hyperresolved-a40-l20-z20` | hyperresolved | 40 | 20 | 20 | 251.618 | 251.153 | 1.00185 | — |
| `s2s3-phase-hyperresolved-a60-l0-z60` | hyperresolved | 60 | 0 | 60 | 191.427 | 191.09 | 1.00176 | — |
| `s2s3-phase-hyperresolved-a60-l30-z30` | hyperresolved | 60 | 30 | 30 | 191.4 | 191.09 | 1.00163 | — |
| `s2s3-phase-hyperresolved-a60-l60-z0` | hyperresolved | 60 | 60 | 0 | 191.382 | 191.09 | 1.00153 | — |
| `s2s3-phase-hyperresolved-a80-l40-z40` | hyperresolved | 80 | 40 | 40 | 128.841 | 128.631 | 1.00163 | — |
| `s2s3-phase-hyperresolved-a100-l50-z50` | hyperresolved | 100 | 50 | 50 | 74.3751 | 74.1446 | 1.00311 | — |
| `s2s3-phase-hyperresolved-a120-l60-z60` | hyperresolved | 120 | 60 | 60 | 34.2753 | 34.201 | 1.00217 | — |
| `s2s3-phase-hyperresolved-a135-l67p5-z67p5` | hyperresolved | 135 | 67.5 | 67.5 | 15.2874 | 15.1562 | 1.00866 | — |
| `s2s3-phase-hyperresolved-a150-l75-z75` | hyperresolved | 150 | 75 | 75 | 4.69498 | 4.64936 | 1.00981 | — |
<!-- end generated: phase -->

**SatSim parity (round 31).** Ten SatSim configurations of the same geometry run through `LocalBackend` with the SatSim adapter, seed 1. The cells are those of the characterization document's results table. Its seven listed differences each have a shown cause: the aperture cone (above), SatSim's apparent Sun (5.1e-4 at 150 degrees), the frame floored to whole counts, the narrow Gaussian's normalization (1.3 %), different PSF models, the sprite's footprint on the oversampled grid, and the sprite's placement (11.9 pixels off).

<!-- generated: satsim -->
| Spec | Phase (deg) | Exposure (ms) | PSF | Expected (pe) | SatSim truth plane (target_pe) / expected | SatSim frame / expected | DIRSIG, same geometry: equivalent px / expected |
|---|---|---|---|---|---|---|---|
| `s2s-satsim-sphere-a0-e5ms` | 0 | 5 | POPPY | 565,394 | 1.000000 | 0.99904 | 0.981 (σ over seeds 0.04) |
| `s2s-satsim-sphere-a60-e5ms` | 60 | 5 | POPPY | 344,323 | 1.000086 | 0.99843 | 0.986 |
| `s2s-satsim-sphere-a120-e5ms` | 120 | 5 | POPPY | 61,627 | 1.000240 | 0.99272 | 1.051 |
| `s2s-satsim-sphere-a150-e5ms` | 150 | 5 | POPPY | 8,378 | 1.000511 | 0.97748 | 1.112 (σ over seeds 0.24) |
| `s2s-satsim-sphere-a0-e1ms` | 0 | 1 | POPPY | 113,079 | 1.000000 | 0.99509 | (plates: × 0.2000, round 29) |
| `s2s-satsim-sphere-a0-e20ms` | 0 | 20 | POPPY | 2,261,574 | 1.000000 | 0.99976 | (plates: × 4.0000) |
| `s2s-satsim-sphere-a0-e5ms-psfgaussian` | 0 | 5 | Gaussian, eod 0.989 | 565,394 | 0.987384 | 0.98738 |  |
| `s2s-satsim-sphere-a0-e5ms-psfnone` | 0 | 5 | none | 565,394 | 1.000000 | 1.00000 |  |
| `s2s-satsim-sphere-a0-e5ms-zpcone` | 0 | 5 | POPPY, cone zeropoint | 565,394 | 0.981075 | 0.98013 |  |
| `s2s-satsim-plate-a0-e5ms` | 0 | 5 | POPPY | 1,727,715,461 | 1.000000 | 1.00000 | 1.00095 (`ec690ca81d5ec602`, round 29's image reproduced) |
<!-- end generated: satsim -->

**Both engines' exposure integration.** Both integrate over [t, t + exposure] from the task time (DIRSIG's `relative_time_window` [0.0, 0.005]; SatSim's frame 0), and SatSim stamps `DATE-OBS` at mid-exposure (the characterization document, "Time and frame conventions"). The signal scales with the exposure in both:

<!-- generated: exposure -->
| Engine | Spec | Exposure (ms) | Signal / signal at 5 ms | Exposure / 5 ms | Relative residual | Source |
|---|---|---|---|---|---|---|
| DIRSIG | `s2s-hyperresolved-r25km-v0mps-e1ms-l0-z0-d0` | 1 | 0.200000 | 0.2 | 1.3e-15 | `docs/data/s2s_results.jsonl` (image sum, e⁻ m⁻²) |
| DIRSIG | `s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0` | 5 | 1.000000 | 1 | 0 | `docs/data/s2s_results.jsonl` (image sum, e⁻ m⁻²) |
| DIRSIG | `s2s-hyperresolved-r25km-v0mps-e20ms-l0-z0-d0` | 20 | 4.000000 | 4 | 0 | `docs/data/s2s_results.jsonl` (image sum, e⁻ m⁻²) |
| SatSim | `s2s-satsim-sphere-a0-e1ms` | 1 | 0.200000 | 0.2 | 0 | `docs/Space_to_space_characterization.md`, SatSim parity, Results (truth plane / expected, the expectation proportional to the exposure) |
| SatSim | `s2s-satsim-sphere-a0-e5ms` | 5 | 1.000000 | 1 | 0 | `docs/Space_to_space_characterization.md`, SatSim parity, Results (truth plane / expected, the expectation proportional to the exposure) |
| SatSim | `s2s-satsim-sphere-a0-e20ms` | 20 | 4.000000 | 4 | 0 | `docs/Space_to_space_characterization.md`, SatSim parity, Results (truth plane / expected, the expectation proportional to the exposure) |
<!-- end generated: exposure -->

### 2.2 Risk measurements (round 33)

Source: `docs/data/risk_measurements.jsonl` (`python scripts/risk_measure.py --check` recomputes each record's derived numbers) and the CONOPS rows they inform (C-28, C-30, C-43, and the HOME and partial-collect decisions of section 10.1). One thread unless stated.

**A, HOME.** Each job rendered under a fresh HOME, the same HOME again and the user's HOME, traced with `strace`. `dirsig5` reads one HOME file, its Qt settings file.

<!-- generated: risk-a -->
| Id | Job | Size | Writes under any HOME | Digests equal across the three HOMEs | User's `Documents/DIRSIG` unchanged | Files in the fresh HOME afterwards |
|---|---|---|---|---|---|---|
| `s2s-hyperresolved-r25km-16px` | `s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0` | 16 x 16 | 0 | yes | yes | 0 |
| `s2s-hyperresolved-r25km-500px` | `s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0` | 500 x 500 | 0 | yes | yes | 0 |
| `tahoe-auror-ref-16px` | `auror_ref` | 16 x 16 | 0 | yes | yes | 0 |
<!-- end generated: risk-a -->

**B, concurrency and memory.** N concurrent copies of one layered job, one thread each, a HOME and work folder per job, on the 4-core, 11 GiB laptop.

<!-- generated: risk-b -->
| Id | Size | Jobs | Batch wall (s) | Mean job wall (s) | Peak RSS per job (KiB) | Summed dirsig5 RSS, max (KiB) | Jobs per hour | Digests equal the single job | Failed |
|---|---|---|---|---|---|---|---|---|---|
| `native-n1` | 500 x 500 | 1 | 70.7 | 70.69 | 159,296 to 159,296 | 159,540 | 50.919 | yes | 0 |
| `native-n2` | 500 x 500 | 2 | 78.1 | 78.06 | 159,128 to 159,132 | 318,980 | 92.19 | yes | 0 |
| `native-n4` | 500 x 500 | 4 | 113.21 | 112.37 | 158,764 to 159,248 | 637,288 | 127.2 | yes | 0 |
| `native-n8` | 500 x 500 | 8 | 198.05 | 195.49 | 157,896 to 159,216 | 1,272,824 | 145.42 | yes | 0 |
| `small-n1` | 16 x 16 | 1 | 1.61 | 1.6 | 129,016 to 129,016 | 0 | 2236 | yes | 0 |
| `small-n2` | 16 x 16 | 2 | 1.71 | 1.69 | 126,580 to 126,728 | 0 | 4210.5 | yes | 0 |
| `small-n4` | 16 x 16 | 4 | 2.05 | 1.93 | 128,108 to 129,180 | 438,376 | 7024.4 | yes | 0 |
| `small-n8` | 16 x 16 | 8 | 3.65 | 3.47 | 127,596 to 128,816 | 537,304 | 7890.4 | yes | 0 |

| Limit model | Cores | Hardware threads | RAM (GiB) | Peak RSS (GiB) | Limit | Throughput against one job (n = 1, 2, 4, 8) | Dual Xeon Gold 6230, 256 GB |
|---|---|---|---|---|---|---|---|
| `limit-model` | 4 | 8 | 10.978 | 0.1519 | 4 | 1, 1.81, 2.498, 2.856 | 40 |
<!-- end generated: risk-b -->

**C, cancel.** A 500 x 500 one-capture layered job submitted through `Workspace.local` and cancelled.

<!-- generated: risk-c -->
| Id | Cancelled at (fraction) | After (s) | Full run (s) | State | Verdict | Cancel returned (s) | Artifacts listed | Image rows on disk | Header line count | Rows equal the full run's |
|---|---|---|---|---|---|---|---|---|---|---|
| `s2s-500px-cancel-25` | 0.250 | 18.2 | 72.83 | cancelled | incomplete | 0.2 | `run_spec.json` | 114 of 500 | 105 | yes |
| `s2s-500px-cancel-50` | 0.500 | 36.4 | 72.83 | cancelled | incomplete | 0.2 | `run_spec.json` | 240 of 500 | 235 | yes |
| `s2s-500px-cancel-75` | 0.750 | 54.6 | 72.83 | cancelled | incomplete | 0.2 | `run_spec.json` | 368 of 500 | 365 | yes |
<!-- end generated: risk-c -->

**D, several captures per task window (C-43).** The SDK's one-capture check bypassed; the demos at reduced arrays.

<!-- generated: risk-d -->
| Id | Size | Captures logged | DIRSIG refused | Captures equal to their one-capture run | SDK check | Run state | Reversed trigger order |
|---|---|---|---|---|---|---|---|
| `fireball1-reduced` | 80 x 60 | 2 | no | 1 of 2 | expected 1 capture(s), one per task window, log lists 2 | — | rc 0, first output equals its single: yes |
| `polarization4-reduced` | 44 x 36 | 4 | no | 1 of 4 | expected 1 capture(s), one per task window, log lists 4 | — | rc 0, first output equals its single: yes |
| `s2s-500px-four-windows` | 500 x 500 | 4 | no | 1 of 4 | passes (one capture per task window) | failed | — |
| `thermal2-reduced` | 80 x 60 | 5 | no | 1 of 5 | expected 1 capture(s), one per task window, log lists 5 | — | rc 1 ([error] Error! Std::bad_alloc [error]   ... while generating a scheduled event queue); without a limit: killed by the kernel's OOM killer (exit 137 of the calling command), anon RSS 5,558,920 KiB |
<!-- end generated: risk-d -->

**E, default-thread determinism.** LightCurve1 cut to its first 151 samples; pairs of `cube_150.img` (and the light curve) across thread counts and repeats.

<!-- generated: risk-e -->
| Pair (t1, t2, t4: threads; td: default 8; a to c: repeats) | Class | Lit pixels differing | Max relative difference | Frame sum, relative | Light curve (last), relative | Outputs differing |
|---|---|---|---|---|---|---|
| `lightcurve1-cube150-t1-a-vs-t2-a` | float-order | 1 of 2,923 | 1.11e-07 | 8.08e-13 | 0 | `cube_150.img` |
| `lightcurve1-cube150-t1-a-vs-t4-a` | float-order | 2 of 2,923 | 2.17e-06 | 8.3e-10 | 0 | `cube_150.img` |
| `lightcurve1-cube150-t1-a-vs-t4-b` | float-order | 1 of 2,923 | 1.09e-07 | 2.06e-12 | 0 | `cube_150.img` |
| `lightcurve1-cube150-t1-a-vs-td-a` | sampling-noise | 4 of 2,923 | 0.0312 | 7.42e-06 | 1.12e-06 | `cube_150.img`, `lightcurve.dat` |
| `lightcurve1-cube150-t1-a-vs-td-b` | sampling-noise | 11 of 2,923 | 0.0335 | 6.7e-06 | 9.81e-07 | `cube_150.img`, `lightcurve.dat` |
| `lightcurve1-cube150-t1-a-vs-td-c` | sampling-noise | 9 of 2,923 | 0.0161 | 4.43e-06 | 7e-07 | `cube_150.img`, `lightcurve.dat` |
| `lightcurve1-cube150-t2-a-vs-t2-b` | identical | 0 of 2,923 | 0 | 0 | 0 | none |
| `lightcurve1-cube150-t2-a-vs-t4-a` | float-order | 3 of 2,923 | 2.17e-06 | 8.29e-10 | 0 | `cube_150.img` |
| `lightcurve1-cube150-t4-a-vs-t4-b` | float-order | 3 of 2,923 | 2.17e-06 | 8.32e-10 | 0 | `cube_150.img` |
| `lightcurve1-cube150-td-a-vs-td-b` | sampling-noise | 13 of 2,923 | 0.0335 | 1.41e-05 | 2.1e-06 | `cube_150.img`, `lightcurve.dat` |
| `lightcurve1-cube150-td-a-vs-td-c` | sampling-noise | 9 of 2,923 | 0.0312 | 2.99e-06 | 4.2e-07 | `cube_150.img`, `lightcurve.dat` |
| `lightcurve1-cube150-td-b-vs-td-c` | sampling-noise | 12 of 2,923 | 0.0335 | 1.11e-05 | 1.68e-06 | `cube_150.img`, `lightcurve.dat` |
<!-- end generated: risk-e -->

### 2.3 The transferred scenes

Source: `docs/DIRSIG_transfer_scenes.md` (survey by `scripts/survey_transfer.py`) and `docs/DIRSIG_layered_comparison.md` (comparisons by `scripts/compare_layered.py`). No transferred scene holds a `.scene` or `.mat` file; six are byte-identical subsets of the install's Documents-folder copies, which were compared instead.

<!-- generated: transfer -->
| Scene | Simulation files | Also in the install |
|---|---|---|
| foxbat | 15 | yes, complete: `Documents_Folder-07-Feb-2024/DIRSIG/scenes/foxbat` |
| MicroScene1 | 20 | no |
| MegaScene1 | 8 | no |
| refinery | 4 | yes, complete |
| urban | 2 | yes, complete |
| forest | 1 | yes, complete |
| LidarJungle | 1 | no |
| Trona | 1 | no |
| warehouse | 0 | yes, complete |
| RITBusLoop | 0 | no |
| Tacoma | 0 | yes: `Tacoma-08-Apr-2022/Tacoma`, byte-identical files |

| Scene (simulation) | Result |
|---|---|
| foxbat (`shots/basic_rgb/basic_rgb.sim`, 640 x 480 RGB, nadir from 5000 m) | differs by two listed input differences: dirfm's six-decimal Euler angle (`4.71238898` written `4.712389`) and the scene compile. At the default thread count a repeat of either form changes every digest (0.09 to 0.10 % of pixels), and the demo's angle alone brings 3.70 % down to 0.16 %, within that noise. At one thread, the demo's angle plus the pass-through run's compiled scene gives the pass-through image and truth byte for byte. Round 37 reran the comparison through `compare_layered.py --threads 1` and the noise-floor repeat: the same digests at one thread, the noise-floor note at the default count (`docs/DIRSIG_layered_comparison.md`, round ten). |
| urban (`shots/space/space.sim`, 512 x 512 RGB from 120 km) | byte-identical, image and truth |
| forest (`shots/rgb/rgb.sim`, 1024 x 1024 RGB) | stopped: the layered and the same-seed pass-through renders each passed the 150 s render timeout (cancelled) |
| MicroScene1 | stopped at the survey: `microscene1.scene` and every material file are absent |
<!-- end generated: transfer -->

**foxbat.** The rows of the comparison document for foxbat: round 32's at DIRSIG's default thread count, and round 37's through `compare_layered.py --threads 1` and, at the default count, with the noise-floor repeat (round 34's options, run on a real scene for the first time):

<!-- generated: foxbat -->
| Demo | Image | Against | Max abs difference | Pixels differing | Identical |
|---|---|---|---|---|---|
| foxbat | `rgb.img` | pass-through, seed 1 | 2.16182e-05 | 3.6956% | no |
| foxbat | `rgb_truth.img` | pass-through, seed 1 | 78 | 100.0000% | no |
| foxbat | `rgb.img` | pass-through, no seed | 0.000320223 | 96.2962% | no |
| foxbat (repeat) | `rgb.img` | pass-through, seed 1 | 2.16182e-05 | 3.7126% | no |
| foxbat (one thread, round 37) | `rgb.img` | pass-through, seed 1 | 2.16182e-05 | 3.6315% | no |
| foxbat (one thread, round 37) | `rgb_truth.img` | pass-through, seed 1 | 79 | 100.0000% | no |
| foxbat (one thread, round 37) | `rgb.img` | pass-through, no seed | 0.000320223 | 96.2962% | no |
| foxbat (one thread, round 37), layered with the demo's Euler angles alone | `rgb.img` | pass-through, seed 1 | 3.9992e-07 | 0.0697% | no |
| foxbat (one thread, round 37), layered with the demo's Euler angles alone | `rgb_truth.img` | pass-through, seed 1 | 79 | 5.1650% | no |
| foxbat (one thread, round 37), layered with the demo's motion file | `rgb.img` | pass-through, seed 1 | 3.9992e-07 | 0.0697% | no |
| foxbat (one thread, round 37), layered with the demo's motion file | `rgb_truth.img` | pass-through, seed 1 | 79 | 5.1650% | no |
| foxbat (round 37) | `rgb.img` | pass-through, seed 1 | 2.16182e-05 | 3.7031% | no |
| foxbat (round 37) | `rgb_truth.img` | pass-through, seed 1 | 40 | 100.0000% | no |
| foxbat (round 37) | `rgb.img` | pass-through, no seed | 0.000320223 | 96.2962% | no |
| foxbat (round 37), layered with the demo's Euler angles alone | `rgb.img` | pass-through, seed 1 | 1.24936e-06 | 0.1530% | no |
| foxbat (round 37), layered with the demo's Euler angles alone | `rgb_truth.img` | pass-through, seed 1 | 40 | 13.2161% | no |
| foxbat (round 37), layered with the demo's motion file | `rgb.img` | pass-through, seed 1 | 3.94273e-06 | 0.1585% | no |
| foxbat (round 37), layered with the demo's motion file | `rgb_truth.img` | pass-through, seed 1 | 40 | 13.2161% | no |
| foxbat (round 37), noise floor: pass-through, seed 1, repeated | `rgb.img` | pass-through, seed 1 | 3.94273e-06 | 0.0967% | no |
| foxbat (round 37), noise floor: pass-through, seed 1, repeated | `rgb_truth.img` | pass-through, seed 1 | 78 | 8.9440% | no |
<!-- end generated: foxbat -->

Round 37's result (`docs/DIRSIG_layered_comparison.md`, "Round ten"): at one thread the pass-through image is round 32's one-thread digest `c8125a16f266cb90…`, and the script's direct render with the demo's Euler angles alone gives round 32's by-hand digest `5e1c9dce19859001…`, 0.0697 % of pixels from the pass-through (maximum 4.0e-7; in the truth only the optical-property index band); the script reports it not identical, the remaining difference being the scene compile, which the script does not swap. At the default thread count the run ids are round 32's, the repeat differs in 0.0967 % of pixels and the script prints its noise-floor note. Peak resident size 576,292 kB (`scene2hdf`); `dirsig5` at most 196,564 kB. Three renders and two direct renders at one thread, four renders (the repeat among them) and two direct renders at the default count, one at a time.

### 2.4 Not measured on this host

Seven measurements were skipped, truncated or reduced for the laptop's time cap, memory or cores; `docs/Bigger_host_plan.md` lists them with their figures and `docs/data/bigger_host_manifest.yaml` holds them for `scripts/bigger_host_run.py`, which has run on this host at 16 x 16 only.

## 3. Defects found and not fixed

From `BACKLOG.md` (and, where a defect has no BACKLOG item, the document that records it). "Fixing touches" names what a fix would change: `core` (`packages/core`), `run id` (an existing run id or the bytes of committed specs or references), `snapshot` (`tests/data/id_snapshot.json`), `engine` (an engine package, dirfm, DIRSIG or SatSim), `document`. None is fixed, because each fix touches one of the first four, which the rounds since review-r27 leave as tagged, or is outside the repository.

**Found in rounds 28 to 36.**

| Defect | Recorded in | Status | Fixing touches |
|---|---|---|---|
| The family specs' `fidelity.absent` entry "optics blur (the template's spatial response is one uniform pixel)" is inaccurate: DIRSIG5 applies an aperture-dependent spread of about 0.18 pixel (σ) unless the platform file states a `<psf>` | `BACKLOG.md` "Space-to-space: what round 30 leaves open" | not regenerated | run id (every family spec; `scripts/s2s_scenarios.py` and `manifold_run_specs/s2s/index.json`); not the snapshot (the family specs have no entry) |
| The SatSim adapter's admission scan does not include a sprite model's `filename`, so the sprite is neither staged nor hashed and two sprites could run under one run id | `BACKLOG.md` "Space-to-space: what round 31 leaves open" | stated in `docs/Engine_author_guide.md`, asserted as stated by `tests/test_engine_author_guide.py` | engine (`packages/engine-satsim`), document |
| DIRSIG reads no `descriptor.collection.geometry.range` (a doubled range leaves the job byte-identical) and nothing checks it against `engine.motion` | `BACKLOG.md` "Space-to-space: what round 31 leaves open" | recorded | engine (a cross-check in `packages/engine-dirsig`); run id if the check refused an existing spec |
| The wrong-hash refusal shows 12 of 64 hex digits, which cannot be pasted back | `BACKLOG.md` "Authoring friction (round 35)" | recorded | core (`run_spec.py`, `resources.py`), engine (`passthrough_spec.py`) |
| A missing `settings` member is refused as `KeyError: '<member>'`, and the black-level refusal advises "omit it", which is then refused the same way | `BACKLOG.md` "Authoring friction (round 35)" | recorded | engine (`packages/engine-dirsig` `run_spec.py`) |
| `recipes/leo_pass_tahoe.yaml`'s `fidelity.approximated` parses as 4 items, not 3 (a comma inside a parenthesis) | `BACKLOG.md` "Authoring friction (round 35)" | recorded | run id, snapshot |
| A recipe outside `<library>/recipes/` does not compose; a run spec outside the layout needs `sensor_library=` | `BACKLOG.md` "Authoring friction (round 35)" | recorded | core (`compose.py`, `run_spec.py`, `admission.py`) |
| `manifold.core.engine.ROLES` lacks `preview`, which `manifold.core.artifacts.ROLES` has | `BACKLOG.md` "Artifact roles: the vocabulary" | not changed (core) | core |
| A cancelled DIRSIG run lists only `run_spec.json`, though its output folder holds usable rows (risk C) | `BACKLOG.md` "Partial artifacts of a cancelled DIRSIG run" | not built; a decision (section 5) | core (the adapter protocol's `collect`), engine |
| A layered job with four task windows passes the SDK's one-capture check and fails at collection ("artifact names used twice"; risk D) | CONOPS section 10.1, C-43 row | recorded with C-43 | engine (the DIRSIG collector or the check) |
| Thermal2's descending trigger times exhaust memory (OOM kill at about 5.3 GiB anonymous RSS) with no refusal from DIRSIG or the SDK (risk D) | `BACKLOG.md` "Several captures in one task window"; `docs/Bigger_host_plan.md` | deferred to a larger host | engine (DIRSIG) |
| The one-capture check refuses valid multi-capture jobs (Thermal2, Polarization4, Fireball1) | `BACKLOG.md` "Several captures in one task window" | C-43 asked; the check unchanged | engine (`packages/engine-dirsig` `simulation.py`) |
| dirfm compiles the scene with `--threads` and the seed, the pass-through runner with neither, and the truth's optical-property index renumbers between compiles | `BACKLOG.md` "The scene compile's flags" | fix stated, not done | engine (dirfm, `packages/engine-dirsig`) |
| `compare_layered.py`'s digest attribution says "not identical" on a scene that does not repeat at the default thread count; the comparison is not resumable per render | `BACKLOG.md` "Scenes Kevin transferred (round 32)" | `--threads` and the noise-floor repeat built (round 34); foxbat rerun in round 37 (section 2.3) | scripts only |
| The demo coverage report's prose and the BACKLOG item call Ssa1 a satellite imaging a satellite; round 29 found it a fixed site | `BACKLOG.md` "Ssa1 against the orbit form" | not edited (a generated report) | document (`scripts/survey_demos.py`'s template) |

**Found before review-r27 and still open** (unchanged since the tag; listed so that the list is complete): `BACKLOG.md` "Motion files lose precision in dirfm's `PlatformPosition`" (engine; the bytes of every static-pose layered job, not its run id), "dirfm writes an explicit zero scene offset" (engine; bytes, not run ids), "The epoch is written in UTC" (engine; thermal results), "Generator scope" (engine; fields neither written nor refused), "Strict loader and canonical hashing (MANIFOLD registry side)" (core; duplicate keys kept), "Throttle rule and idle cores" (engine), "Atmosphere database is for a different site" (run id; the database is a hashed asset), "`run_info.json` is not a complete plugin record" (DIRSIG), and the dirfm and DIRSIG items of BACKLOG's last two sections (engine).

## 4. Decisions asked of MANIFOLD

Every row of the CONOPS decisions index (section 10.1) whose owner is MANIFOLD, with its state there (which carries the numbers rounds 28 to 36 measured, where any) and the Evidence cell of its section 10 row. No row has an Outcome yet.

<!-- generated: manifold -->
| C-n | Ask | Blocks 0.1 | State and what is measured (section 10.1) | Evidence (section 10 row) |
|---|---|---|---|---|
| C-01 | `descriptor.sensor` refs resolve against the sensor library; `engine` refs resolve against `manifold_config_repo/` | yes | a position offered, not agreed | `tests/test_sensor_library.py` |
| C-02 | `atmosphere/<name>` flat library path | yes | a position offered, not agreed | `tests/test_run_spec.py` |
| C-03 | `new_atmosphere` plugin value in A.8.7 (database role `dirsig:atmosphere_db`) | yes | a position offered, not agreed | `tests/test_run_spec.py` |
| C-04 | Where motion and tasks are generated | yes | a question, no position taken | `tests/test_motion_tasks.py` |
| C-05 | Moving-platform motion generation | yes | a position offered, not agreed | `tests/test_orbit_motion.py` |
| C-06 | Authority of DIRSIG JSON logs | no | a position offered, not agreed | `tests/test_check_log.py` |
| C-07 | Compile-once | no | a position offered, not agreed | — |
| C-08 | A thread count for `dirsig5` (`--threads`) | yes | a question, no position taken | `tests/test_resources.py` |
| C-09 | `--force_temperature_prediction` as an `engine.run` option | no | a question, no position taken | — |
| C-10 | `engine.platform.output_prefix` | yes | a question, no position taken | — |
| C-11 | Illustrative instances in Metadata_v02 §6.11 and Configuration_v02 A.8.10 | no | a question, no position taken | — |
| C-12 | Strict loader and hashing | yes | a question, no position taken | `tests/test_run_spec_schema.py` |
| C-14 | Detector manufacturer and model | yes | a position offered, not agreed | `tests/test_sensor_library.py` |
| C-15 | Full frame versus modeled window | yes | a position offered, not agreed | `tests/test_sensor_render.py` |
| C-16 | Spectral references | yes | a position offered, not agreed | `tests/test_spectral_curves.py` |
| C-17 | `engine.platform.channel_response` (set by a recipe's `engine_overrides`, section 3.5) | yes | a position offered, not agreed | `tests/test_platform_render.py` |
| C-18 | One run per sensor | yes | a position offered, not agreed | `tests/test_compose.py` |
| C-29 | Engine registration and an open `origin.engine` | yes | a position offered, not agreed | `tests/test_engine_set.py` |
| C-30 | Resource slots and the run id | yes | a position offered, not agreed. Measured (round 33, risk B): 1 to 8 concurrent one-thread jobs gave byte-identical products at 156 MiB peak RSS each, supporting memory and concurrency out of the run id; limit min(cores, floor(RAM / peak RSS)) = 4 here, 40 on a dual Xeon Gold 6230 with 256 GB | `tests/test_resources.py` |
| C-31 | Assets and a network-free run | yes | a position offered, not agreed | `tests/test_satsim_adapter.py` |
| C-32 | Listing the engines of a backend | no | a position offered, not agreed | `tests/backend_conformance.py` |
| C-33 | An artifact role vocabulary | no | a position offered, not agreed | `tests/test_artifact_roles.py` |
| C-34 | Artifact roles and run verdicts in `sdk-api/1` | no | a position offered, not agreed | `tests/test_artifact_roles.py` |
| C-35 | SatSim's seed: a required input that enters the run id | yes | a position offered, not agreed | `tests/test_satsim_adapter.py` |
| C-36 | Asset snapshots and who owns the pins | no | a position offered, not agreed | `tests/test_bootstrap_assets.py` |
| C-37 | Opaque descriptors for a second engine | no | a position offered, not agreed | `tests/test_satsim_adapter.py` |
| C-38 | License position on bundling SatSim | no | a question, no position taken | — |
| C-39 | `atmosphere.uniform` with `plugin: basic` in `dirsig-engine/1` | yes | a position offered, not agreed | `tests/test_uniform_atmosphere.py` |
| C-40 | `platform.as_authored` in `dirsig-engine/1` | yes | a position offered, not agreed | `tests/test_authored_platform.py` |
| C-41 | `atmosphere.simple` with `plugin: basic` in `dirsig-engine/1` | yes | a position offered, not agreed | `tests/test_simple_atmosphere.py` |
| C-42 | `working_folder` in `dirsig-engine/1` | yes | a position offered, not agreed | `tests/test_working_folder.py` |
| C-43 | One capture per task window, checked by the SDK | no | a question, no position taken. Measured (round 33, risk D): DIRSIG refuses no multi-capture job; only a run's first capture equals its one-capture run; descending Thermal2 trigger times exhaust memory (5.3 GiB, OOM); a four-window layered job fails at collection ("artifact names used twice") | `tests/test_check_log.py`; `docs/DIRSIG_layered_comparison.md` |
| C-44 | Governed vocabulary values for space-to-space runs (`space_to_space`, `space`, `none`, `space_object`) | yes | a question, no position taken | `tests/test_s2s_scenarios.py` |
<!-- end generated: manifold -->

## 5. Decisions that are the SDK maintainer's

Three were measured in rounds 33 and 35 and are not put to MANIFOLD:

- **Product direction for authoring.** A form or GUI that writes recipes and layers, a CLI, or neither (`docs/Authoring_friction_audit.md`, `scripts/recipe_form.py`, `BACKLOG.md` "Authoring friction (round 35)"). A recipe-only form adds nothing to the SDK; a form that writes layers, or a CLI, needs a hashing or stamping operation in the SDK.
- **HOME.** Layered jobs run with the user's HOME, pass-through runs with a per-run HOME (`BACKLOG.md` "Layered jobs and the user's HOME"). Risk A measured no write under any HOME and equal products under all three.
- **Partial collect.** A collection mode for a cancelled DIRSIG run that reports the outputs it finds, with roles (`BACKLOG.md` "Partial artifacts of a cancelled DIRSIG run"). It changes the adapter protocol in `manifold.core`; risk C measured the rows on disk equal to the full run's first rows.

All the maintainer's rows of section 10.1, the held-back C-n first:

<!-- generated: maintainer -->
| C-n | Ask | Blocks 0.1 | State |
|---|---|---|---|
| C-19 | Entries per DIRSIG run | yes | deferred by the author; not put to MANIFOLD yet |
| C-20 | Product radiometric quantity; is `radiometric_reference` optional? | yes | deferred by the author; not put to MANIFOLD yet |
| C-21 | Layered submission and a MANIFOLD input constructor | yes | deferred by the author; not put to MANIFOLD yet |
| C-22 | Recording a sweep at registration | yes | deferred by the author; not put to MANIFOLD yet |
| C-23 | What a run id covers | yes | deferred by the author; not put to MANIFOLD yet |
| C-24 | A status member in library listings | no | deferred by the author; not put to MANIFOLD yet |
| C-25 | An opaque descriptor for pass-through runs | yes | deferred by the author; not put to MANIFOLD yet |
| C-26 | A pass-through mode in `dirsig-engine/1` | yes | deferred by the author; not put to MANIFOLD yet |
| C-27 | Paging artifact listings | no | deferred by the author; not put to MANIFOLD yet |
| C-28 | A thread count in the run id | yes | deferred by the author; not put to MANIFOLD yet. Measured (round 33, risk E): LightCurve1's `cube_150.img` at the default 8 threads resamples 4 to 13 of 2,923 lit pixels (up to 3.4 % of a value; frame sum 1.4e-5, light curve 2.1e-6 relative); 2 and 4 threads differ by summation order only (2.2e-6); one and two threads repeated bit for bit |

| Decision | Where it is recorded | Owner | Blocks 0.1 | What it changes, and what is measured |
|---|---|---|---|---|
| A collection mode for a cancelled DIRSIG run that reports the outputs it finds, with roles | `BACKLOG.md` "Partial artifacts of a cancelled DIRSIG run" | Kevin | yes | the adapter protocol in `manifold.core`, which engine packages implement. Round 33 (`docs/data/risk_measurements.jsonl`, risk C): a 500 x 500 one-capture layered job cancelled through the Workspace at 25, 50 and 75 % of its 72.8 s run was `cancelled` with verdict `incomplete` within 0.2 s and listed only `run_spec.json`, while its output folder held both images and their headers with 114, 240 and 368 of 500 rows, each byte-identical to the full run's first rows; DIRSIG had rewritten each header to a row count a few rows behind the data (105 to 365 lines) without geo points or acquisition time |
| Layered jobs run with the user's `HOME`; pass-through runs with a per-run `HOME` | `scripts/compare_layered.py` (its list of known input differences), `docs/DIRSIG_layered_comparison.md`, section 5, `BACKLOG.md` "Layered jobs and the user's HOME" | Kevin | no | where DIRSIG's material caches go; measured not to change outputs (section 5). Round 33 (`docs/data/risk_measurements.jsonl`, risk A): three layered jobs (the 25 km space-to-space plate at 16 x 16 and 500 x 500, the Tahoe `auror_ref` job at 16 x 16; one thread) traced with `strace` under a fresh HOME, the same HOME again and the user's HOME wrote nothing under any HOME (0 write calls; the user's `Documents/DIRSIG` tree unchanged; the fresh HOME still empty afterwards), and gave the same product digests in all three; `dirsig5` reads one HOME file, its Qt settings `~/.config/Rochester Institute of Technology/DIRSIG.conf` (editor window and recent files), and looks for `~/Documents/DIRSIG/plugins` (absent here). For parallel jobs sharing a HOME, these jobs share nothing through it; a material that writes a cache (`mat_<hash>.sqt`, as the pass-through Brdf1 run in section 5 does) or a user plugin folder would be shared, and neither occurred in these three jobs |
| A requested `cpu_threads` enters a SatSim run id although SatSim's seeded output was the same at one thread and at the default | section 7.4 ("Resources"), section 3.3, C-30 | Kevin, then MANIFOLD through C-30 | yes | the run id of a SatSim spec that requests threads |
| dirfm writes a static `.ppd`'s Euler angles to six decimals and its position to three | `BACKLOG.md` "Motion files lose precision in dirfm's `PlatformPosition`" | Kevin | yes | the bytes of every static-pose layered job and so its references (not its run id). Round 37 (foxbat through `compare_layered.py --threads 1`, `docs/DIRSIG_layered_comparison.md` round ten): at one thread the demo's angle alone brings the layered render from 3.63 % to 0.0697 % of pixels differing from the same-seed pass-through (maximum 4.0e-7), the remainder being the scene compile; at the default thread count a repeat of the pass-through differs in 0.097 % |
| dirfm writes an explicit zero scene offset | `BACKLOG.md` "dirfm writes an explicit zero scene offset" | Kevin | yes | the bytes of every layered job (not its run id) |
| The epoch's written form (UTC against the scene's local offset) | `BACKLOG.md` "The epoch is written in UTC" | Kevin, then a C-n question | yes | thermal results; the item asks for a stated rule |
| How users author recipes and layers: a form or GUI that writes them, a CLI, or neither | `docs/Authoring_friction_audit.md` (the measurement), `BACKLOG.md` "Authoring friction (round 35)", `scripts/recipe_form.py` (a prototype of the recipe step) | Kevin | no | the SDK's public surface. Measured (round 35): the shortest path writes 0 files, 2 fields and 0 hashes; a new recipe 20 required fields, 4 copied; a new scene and sensor in a checkout 4 YAML files and 115 fields, 14 copied, 4 hashes written by `scripts/stamp_hashes.py`, and with the installed packages alone the same 4 hashes computed and typed by the user. A recipe-only form adds nothing to the SDK (it reads `list_*`); a form or GUI that writes layers, or a CLI, needs a hashing or stamping operation in the SDK (today a repository script without a path argument), and a CLI a console entry point |
| The descriptor audit with two engines, before any layered SatSim form | `BACKLOG.md` "Descriptor audit with two engines (first)", C-37 | Kevin | yes | the descriptor's members, and the questions put to MANIFOLD |
<!-- end generated: maintainer -->

## 6. What a reviewer can run

From a checkout with the environment of the README's "Environment setup" (DIRSIG for the suite's renders, which are 16 x 16), at the repository root, with the environment's `python`:

<!-- block: command -->
```bash
python -m pytest -q -p no:cacheprovider
python scripts/review_report.py --check
python scripts/compose.py --check
python scripts/stamp_hashes.py --check
python scripts/render_diagrams.py --check
python scripts/api_examples.py --check
python scripts/gen_models.py --check
python scripts/survey_demos.py --check
python scripts/id_snapshot.py --check
python scripts/engine_contracts.py --check
python scripts/status_markers.py --check
python scripts/cold_start_check.py --check
python scripts/s2s_scenarios.py --check
python scripts/s2s_measure.py --check
python scripts/s2s_coverage.py --check
python scripts/risk_measure.py --check
python scripts/bigger_host_run.py --check
```

Expected at HEAD (each exits 0; what it prints last):

| Command | Expected |
|---|---|
| `python -m pytest -q -p no:cacheprovider` | 2090 passed, 2 skipped (about 9 to 10 minutes on the 4-core laptop) |
| `python scripts/review_report.py --check` | `review_report: 18 generated blocks, 0 problem(s)` |
| `compose.py`, `stamp_hashes.py`, `render_diagrams.py`, `api_examples.py`, `gen_models.py`, `survey_demos.py`, `engine_contracts.py` `--check` | exit 0, nothing printed |
| `python scripts/id_snapshot.py --check` | `id snapshot: unchanged` |
| `python scripts/status_markers.py --check` | `status_markers: 182 markers, 0 problems` |
| `python scripts/cold_start_check.py --check` | a line per step, the last beginning `ok   imported from the new environment` |
| `python scripts/s2s_scenarios.py --check` | `133 run specs: generated, valid, ids as indexed` |
| `python scripts/s2s_measure.py --check` | `101 records: well formed, specs indexed, expected values recompute` |
| `python scripts/s2s_coverage.py --check` | `101 records, 20 rows x 3 classes: the coverage map is current` |
| `python scripts/risk_measure.py --check` | `31 records: well formed, derived numbers recompute` |
| `python scripts/bigger_host_run.py --check` | `7 entries: well formed, drivers and items known, named in docs/Bigger_host_plan.md` |

The notebooks: `notebooks/quickstart_sdk.ipynb` (the manual's quick start, seven code cells), `notebooks/stage_05_sdk_auror_demo.ipynb` and `notebooks/stage_06_space_to_space.ipynb` are executed by the suite (`tests/test_quickstart_notebook.py`, `tests/test_stage05_notebook.py`, `tests/test_stage06_notebook.py`); stage 06 renders nothing and reads `docs/data/s2s_results.jsonl`. The manual's quick start is `docs/User_manual.md` sections 2 and 3, whose code blocks `tests/test_user_manual.py` executes.

## 7. Consistency pass (round 37)

`tests/test_docs_consistency.py` checks every committed Markdown file under `docs/`, `README.md` and every committed Markdown file and notebook under `notebooks/` (34 documents at the pass): every relative link resolves (19 links); every `scripts/` and `tests/` path named exists (514 mentions); every backticked repository path with a file extension exists; every C-number named has a row in the CONOPS decisions index, section 10.1 (204 mentions; id 13 is retired and is cited nowhere); every fenced `python scripts/<name>.py` command, in a Markdown fence or a notebook's `!` line, uses only options its script defines (32 commands; the rule of `tests/test_authoring_guide.py`); no document cites the relay's working notes.

Defects found, with the file and what was done:

| File | Defect | Found by | Done |
|---|---|---|---|
| `notebooks/stage_01_auror_from_runspec.ipynb` (first markdown cell, and a comment in the second cell) | It said the run spec is authored in eopticDocs (`GD_DIRSIG_RunSpec_YAML_v01.md`, a document not in this repository) and vendored here, and that `protodirsig.run_spec` reads it; `manifold_run_specs/auror_ref.yaml` is generated by `scripts/compose.py` from `manifold_run_specs/recipes/auror_ref.yaml`, the vendored copy is retired, and the notebook imports `manifold.core.run_spec` and `manifold.engines.dirsig.run_spec` | a probe while building the pass: Markdown file names in backticks that are not in the repository (not one of the test's rules: the other names it listed are the README's names relative to `docs/` and files of other projects) | fixed in the notebook's text; no code changed |
| `notebooks/dev/auror_scene_buildup.ipynb` | It names the AUROR scene tutorial at its old path directly under `notebooks/` (now `notebooks/dirfm_tutorials/tutorial_auror_scene.ipynb`) and `FINDINGS.md` (removed when the journals were consolidated) | the backticked-path rule | not changed: `notebooks/dev/` is gitignored, so the notebook is no committed document and the test's scope is the committed files |
| this report, while it was written | its rounds table listed the relay's state files among the files added | the no-citation rule | `scripts/review_report.py` leaves them out of the table |

Every other rule passed on the documents as they stood at the start of round 37: no relative link, script or test path, C-number or fenced command option was wrong.
