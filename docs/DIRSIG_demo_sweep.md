# DIRSIG demo sweep

Every DIRSIG 5 demo shipped with the installation (`external/dirsig/demos/zips`), run once through the pass-through form by `scripts/sweep_demos.py`: which demos run in this installation, what they cost, what they output, and why the others fail. It is the evidence for choosing which demos drive layered loader work; `docs/DIRSIG_demo_coverage.md` is the static survey of the same demos and `docs/DIRSIG_demo_reference_runs.md` the measured reference runs of the two committed pass-through recipes.

The part between the markers is generated from the sweep's results file (outside the repository) and rewritten after every demo; text outside the markers is kept. Every attempt's complete list of output digests (this report shows at most 24 outputs per demo) is in `docs/data/demo_sweep_digests.jsonl.gz`, written by `scripts/export_sweep_digests.py`. Only names, sizes, digests, measurements and DIRSIG error lines appear here, no demo bytes. Each demo is extracted from its zip, its simulation files are tried in turn (`demo.sim`, then `demo.jsim`; with neither, up to four top-level `.sim` or `.jsim` files in alphabetical order), stopping at the first that renders; a render under 300 s is repeated in a fresh work root to test determinism. The engine is DIRSIG 2026.38 (a020954) with a per-run `HOME`, so DIRSIG's material caches start cold for every attempt and the user's cache is not involved. "Max CPU" is the maximum over the host's thermal zones during the attempt; 90 C or more is flagged as a throttle suspect.

<!-- sweep_demos: generated between these markers by scripts/sweep_demos.py; edit outside them -->

## Sweep

Deadline 2026-10-11T12:42:13-04:00, per-run timeout 1800.0 s, disk floor 20.0 GB, started 2026-10-11T02:40:36Z. 152 demos recorded, 282 attempts (repeats included). Ended: candidates exhausted.

| Outcome | Demos |
|---|---|
| failed | 16 |
| rendered | 131 |
| skipped: dirsig4 | 3 |
| skipped: duplicate name | 1 |
| timeout | 1 |

## Demos

| Demo | Size (MB) | Outcome | Attempts | Wall time (s) | Outputs | Output (MB) | Run directory (MB) | Deterministic | Max CPU (C) | First error line |
|---|---|---|---|---|---|---|---|---|---|---|
| AnimatedObject1 | 85.81 | rendered | nathan.jsim: rendered | 128.4 | 196 | 421.53 | 507.56 | yes | 95.0 (throttle suspect) | - |
| BackgroundSky1 | 1.04 | rendered | demo.jsim: rendered | 166.4 | 96 | 163.60 | 164.86 | yes | 94.05 (throttle suspect) | - |
| Balfour1 | 0.48 | rendered | demo.sim: rendered | 4.1 | 4 | 2.46 | 3.00 | yes | 94.05 (throttle suspect) | - |
| Balfour2 | 3.02 | rendered | single.sim: rendered | 6.1 | 4 | 20.48 | 24.91 | yes | 93.05 (throttle suspect) | - |
| BayerPattern1 | 4.36 | rendered | bayer_hdf.sim: rendered | 4.1 | 4 | 6.14 | 10.94 | yes | 94.05 (throttle suspect) | - |
| Blackadar1 | 3.08 | failed | demo.sim: failed | 2.0 | 0 | - | 3.14 | - | 84.05 | [error] while reading platform file './demo.platform': |
| Brdf1 | 2.31 | rendered | demo.sim: rendered | 204.3 | 4 | 3.69 | 10.12 | yes | 95.05 (throttle suspect) | - |
| Brdf2 | 8.86 | rendered | demo.sim: rendered | 20.1 | 2 | 7.37 | 19.31 | yes | 93.0 (throttle suspect) | - |
| Brdf3 | 0.47 | rendered | demo.jsim: rendered | 88.1 | 4 | 7.37 | 12.01 | no | 94.05 (throttle suspect) | - |
| BumpMap1 | 0.15 | rendered | demo.sim: rendered | 10.1 | 4 | 6.14 | 6.54 | yes | 86.05 | - |
| BumpMap2 | 0.11 | rendered | demo.sim: rendered | 4.1 | 4 | 7.99 | 9.73 | yes | 93.05 (throttle suspect) | - |
| BundledMaterials1 | 0.36 | rendered | w_bundles.jsim: rendered | 4.1 | 4 | 3.07 | 3.53 | yes | 94.05 (throttle suspect) | - |
| BundledObject1 | 8.55 | rendered | demo.sim: rendered | 48.2 | 4 | 10.45 | 39.61 | no | 94.05 (throttle suspect) | - |
| BundledObject2 | 23.64 | rendered | demo.sim: rendered | 66.1 | 4 | 11.06 | 59.52 | no | 93.05 (throttle suspect) | - |
| Caustics1 | 1.52 | rendered | clear_water.jsim: rendered | 100.3 | 4 | 134.22 | 135.87 | yes | 92.05 (throttle suspect) | - |
| ChipMaker1 | 1.18 | rendered | demo.sim: rendered | 212.3 | 4 | 14.75 | 20.04 | yes | 95.0 (throttle suspect) | - |
| ChipMaker2 | 36.70 | rendered | demo.sim: rendered | 66.2 | 4 | 63.90 | 240.75 | no | 95.05 (throttle suspect) | - |
| ChipMaker3 | 21.32 | rendered | demo.jsim: rendered | 424.8 | 60 | 36.90 | 195.10 | not tested | 97.05 (throttle suspect) | - |
| CloudOpenVdb1 | 12.65 | failed | demo_ppd.jsim: failed; demo_static.jsim: failed | 2.1 | 0 | - | 12.77 | - | 85.0 | [error] Unable to load atmospheric database! |
| Cloudview1 | 13.45 | failed | demo.jsim: failed | 2.1 | 0 | - | 13.58 | - | 75.05 | [error] Unable to load atmospheric database! |
| ColorFilterArray1 | 2.19 | rendered | bayer.sim: rendered | 4.0 | 4 | 6.14 | 20.86 | yes | 93.05 (throttle suspect) | - |
| CommandedMount1 | 4.72 | rendered | demo_absolute.sim: rendered | 24.1 | 20 | 30.72 | 36.03 | no | 95.05 (throttle suspect) | - |
| CommandedMount2 | 6.18 | rendered | demo_absolute.sim: rendered | 6.1 | 4 | 6.14 | 12.90 | no | 94.05 (throttle suspect) | - |
| CurveMap1 | 6.21 | rendered | demo.jsim: rendered | 4.1 | 4 | 7.37 | 14.76 | yes | 94.0 (throttle suspect) | - |
| DataDrivenArray2 | 3.62 | rendered | w_gain.sim: rendered | 4.1 | 4 | 6.14 | 9.82 | yes | 93.05 (throttle suspect) | - |
| DataDrivenTempSolver1 | 0.17 | rendered | demo.sim: rendered | 4.1 | 4 | 2.46 | 2.79 | yes | 95.05 (throttle suspect) | - |
| DecalMap1 | 3.05 | rendered | demo.sim: rendered | 4.1 | 4 | 7.99 | 13.11 | yes | 93.05 (throttle suspect) | - |
| DeltaMotion1 | 1.23 | rendered | demo.sim: rendered | 4.0 | 4 | 5.53 | 6.86 | yes | 94.0 (throttle suspect) | - |
| DensityMap1 | 0.69 | rendered | demo.sim: rendered | 4.1 | 4 | 6.14 | 7.36 | yes | 94.0 (throttle suspect) | - |
| EarthClouds1 | 99.23 | rendered | demo_advanced.jsim: failed; demo_basic.jsim: rendered | 82.3 | 2 | 21.12 | 207.63 | yes | 95.0 (throttle suspect) | [error] Unable to load atmospheric database! |
| EarthMap1 | 0.15 | rendered | demo.sim: rendered | 12.1 | 4 | 8.60 | 1875.07 | repeat failed | 94.05 (throttle suspect) | - |
| EarthShine1 | 1.43 | rendered | demo.jsim: rendered | 84.2 | 4 | 334.24 | 335.74 | yes | 99.05 (throttle suspect) | - |
| Eclipse1 | 7.53 | rendered | demo.jsim: rendered | 16.1 | 4 | 24.58 | 32.21 | yes | 94.05 (throttle suspect) | - |
| ExternalTriggers1 | 0.15 | rendered | constant.sim: rendered | 68.2 | 50 | 15.37 | 15.63 | yes | 94.05 (throttle suspect) | - |
| ExtinctionProp1 | 1.03 | rendered | demo.sim: rendered | 14.1 | 2 | 1.84 | 3.01 | yes | 93.05 (throttle suspect) | - |
| FastCloud1 | 8.41 | failed | demo.sim: failed | 2.1 | 0 | - | 8.41 | - | 88.05 | [error] Error! |
| FastCloud2 | 154.06 | rendered | demo_mat_map.sim: rendered | 52.3 | 4 | 36.87 | 228.69 | yes | 85.05 | - |
| Fireball1 | 0.66 | rendered | demo.sim: rendered | 6.1 | 6 | 7.37 | 8.14 | yes | 94.05 (throttle suspect) | - |
| FlexMotion1 | 1.17 | rendered | multi_frame.sim: rendered | 114.3 | 148 | 68.23 | 69.90 | no | 96.05 (throttle suspect) | - |
| FocusDistance1 | 0.70 | timeout | demo.jsim: timeout | 1800.8 | 0 | - | 1963.78 | - | 95.0 (throttle suspect) | - |
| FourCurveAtm1 | 9.01 | rendered | default_w_path.jsim: rendered | 160.3 | 92 | 169.60 | 200.20 | yes | 96.05 (throttle suspect) | - |
| GenericMotion1 | 1.17 | rendered | demo.sim: rendered | 4.1 | 4 | 3.07 | 4.35 | yes | 92.05 (throttle suspect) | - |
| GeoLocation1 | 8.40 | rendered | flex_ecef_ecef.jsim: rendered | 6.1 | 4 | 11.67 | 20.95 | no | 93.05 (throttle suspect) | - |
| GlistPopulations1 | 1.06 | rendered | demo_daily.sim: rendered | 88.2 | 4 | 7.37 | 12.00 | no | 94.05 (throttle suspect) | - |
| HdfWater1 | 9.09 | failed | demo.jsim: failed | 2.1 | 0 | - | 10.61 | - | 80.05 | [error] NewAtmosphere::updateState: |
| IESSources1 | 0.33 | rendered | demo.sim: rendered | 18.1 | 4 | 11.06 | 11.49 | yes | 96.05 (throttle suspect) | - |
| Indoors1 | 57.40 | rendered | demo.jsim: rendered | 8.1 | 4 | 7.37 | 96.58 | yes | 93.05 (throttle suspect) | - |
| InstanceOptions1 | 0.06 | rendered | binary_demo.sim: failed; glist_demo.sim: rendered | 6.1 | 4 | 8.60 | 8.72 | yes | 95.0 (throttle suspect) | [error] Error! |
| LeafStack1 | 0.39 | rendered | demo.sim: rendered | 10.1 | 4 | 8.60 | 9.06 | yes | 94.05 (throttle suspect) | - |
| LemniscateScanMount1 | 5.17 | rendered | demo.sim: rendered | 6.1 | 4 | 4.92 | 10.65 | yes | 93.05 (throttle suspect) | - |
| LensDistortion1 | 0.05 | rendered | demo.jsim: rendered | 4.1 | 4 | 4.92 | 5.03 | yes | 94.05 (throttle suspect) | - |
| LidarBiStatic1 | 18.05 | rendered | demo.sim: rendered | 6.1 | 1 | 4.90 | 25.54 | no | 88.05 | - |
| LidarBounces1 | 0.04 | rendered | demo.sim: rendered | 6.1 | 3 | 41.94 | 42.21 | no | 96.0 (throttle suspect) | - |
| LidarDynamicGate1 | 4.89 | rendered | dynamic_gate.jsim: rendered | 270.6 | 3 | 299.34 | 306.94 | no | 92.05 (throttle suspect) | - |
| LidarEdge1 | 1.39 | rendered | demo.sim: rendered | 2.0 | 3 | 0.00 | 1.52 | no | 90.05 (throttle suspect) | - |
| LidarMultiStatic1 | 17.40 | rendered | demo.jsim: rendered | 6.1 | 6 | 11.38 | 31.39 | no | 95.05 (throttle suspect) | - |
| LidarPointing1 | 1.29 | rendered | with_jitter.sim: rendered | 26.1 | 1 | 38.35 | 39.73 | no | 95.0 (throttle suspect) | - |
| LidarRetro1 | 0.01 | rendered | demo.sim: rendered | 4.9 | 3 | 0.39 | 0.53 | no | 72.05 | - |
| LidarSide1 | 17.25 | rendered | demo.sim: rendered | 8.1 | 3 | 6.26 | 26.11 | no | 78.05 | - |
| LidarSide2 | 0.23 | rendered | multiple.sim: rendered | 38.1 | 1 | 8.29 | 8.63 | no | 89.05 | - |
| LidarSlope1 | 0.36 | rendered | flat.sim: rendered | 2.1 | 3 | 0.00 | 0.43 | no | 81.05 | - |
| LidarStatic1 | 17.26 | rendered | demo.sim: rendered | 8.1 | 3 | 6.19 | 26.05 | no | 86.0 | - |
| LidarStatic2 | 17.32 | rendered | demo.sim: rendered | 6.1 | 1 | 1.32 | 21.23 | no | 93.05 (throttle suspect) | - |
| LidarUserBeam1 | 0.91 | rendered | demo.sim: rendered | 20.1 | 3 | 22.27 | 23.27 | no | 94.0 (throttle suspect) | - |
| LidarUserPulse1 | 0.63 | rendered | after_pulse.sim: rendered | 4.1 | 1 | 0.09 | 0.81 | no | 91.0 (throttle suspect) | - |
| LidarValidate1 | 3.72 | rendered | demo.sim: rendered | 2.0 | 1 | 0.00 | 3.78 | no | 84.05 | - |
| LidarWhisk1 | 17.25 | rendered | demo.sim: rendered | 60.2 | 3 | 49.91 | 69.76 | no | 88.05 | - |
| LidarWhisk2 | 17.32 | rendered | demo.sim: rendered | 178.6 | 1 | 49.65 | 69.59 | no | 97.05 (throttle suspect) | - |
| LightCurve1 | 2.11 | rendered | box_spin.jsim: rendered | 691.9 | 1681 | 13481.14 | 13485.84 | not tested | 94.05 (throttle suspect) | - |
| LineScanMount1 | 5.17 | rendered | demo.sim: rendered | 6.1 | 4 | 4.92 | 10.66 | yes | 94.0 (throttle suspect) | - |
| MacbethColorChecker1 | 0.85 | rendered | demo.sim: rendered | 10.1 | 4 | 12.29 | 13.45 | yes | 94.05 (throttle suspect) | - |
| MappedTherm1 | 0.19 | rendered | map_therm.sim: rendered | 10.1 | 2 | 3.67 | 3.92 | yes | 94.05 (throttle suspect) | - |
| MaterialMap1 | 0.26 | rendered | w_mixing.sim: rendered | 4.1 | 4 | 6.76 | 10.95 | yes | 93.05 (throttle suspect) | - |
| MaterialMap2 | 8.09 | rendered | demo.sim: rendered | 30.1 | 4 | 7.37 | 37.56 | yes | 94.05 (throttle suspect) | - |
| MaterialOverrides1 | 1.05 | rendered | demo.sim: rendered | 4.1 | 4 | 3.07 | 4.25 | no | 93.05 (throttle suspect) | - |
| MicroBolometer1 | 0.88 | rendered | long_decay.jsim: rendered | 6.1 | 4 | 6.30 | 10.20 | no | 94.05 (throttle suspect) | - |
| MixtureMap1 | 124.76 | rendered | demo.sim: rendered | 12.2 | 4 | 7.37 | 261.14 | yes | 94.0 (throttle suspect) | - |
| ModularCity1 | 26.73 | failed | demo.jsim: failed | 2.1 | 0 | - | 26.75 | - | 90.05 (throttle suspect) | [error] Error! |
| MoonSat1 | - | skipped: dirsig4 | flagged DIRSIG 4 only by the online demo page, which the user read | - | 0 | - | - | - | - | - |
| MoonSat2 | 2.18 | rendered | demo.jsim: rendered | 4.1 | 4 | 17.20 | 26.01 | no | 95.0 (throttle suspect) | - |
| MultiCamera1 | 0.15 | rendered | multi.sim: rendered | 12.1 | 16 | 24.58 | 24.81 | yes | 94.05 (throttle suspect) | - |
| Muses1 | 21.97 | rendered | demo.sim: rendered | 64.1 | 8 | 7.37 | 33.17 | yes | 96.0 (throttle suspect) | - |
| Muses2 | 42.78 | failed | demo.jsim: failed | 2.1 | 0 | - | 42.85 | - | 91.05 (throttle suspect) | [error] Missing/Unknown environment variable: 'MUSES_EXE' |
| NestedMotion1 | 0.96 | rendered | demo.sim: rendered | 4.1 | 4 | 6.14 | 10.01 | no | 95.05 (throttle suspect) | - |
| NormalMap1 | 0.50 | rendered | demo.sim: rendered | 4.1 | 4 | 7.99 | 10.14 | yes | 93.05 (throttle suspect) | - |
| NormalMap2 | 8.24 | rendered | demo.sim: rendered | 66.2 | 2 | 7.37 | 29.06 | yes | 94.05 (throttle suspect) | - |
| NormalMap3 | 27.24 | rendered | demo.jsim: rendered | 54.2 | 4 | 36.87 | 167.10 | yes | 96.0 (throttle suspect) | - |
| Parking1 | 42.41 | rendered | demo_assimp.sim: rendered | 132.2 | 4 | 11.06 | 102.81 | no | 95.05 (throttle suspect) | - |
| Pilings1 | 0.14 | rendered | demo.sim: rendered | 14.1 | 4 | 29.49 | 29.75 | yes | 94.05 (throttle suspect) | - |
| PlatformJitter1 | 0.10 | rendered | flex_single.sim: rendered | 6.1 | 5 | 6.15 | 6.31 | no | 94.0 (throttle suspect) | - |
| PlatformJitter2 | 0.10 | rendered | flex_single.sim: rendered | 4.1 | 5 | 6.15 | 6.34 | no | 94.05 (throttle suspect) | - |
| PlumeOpenVDB1 | 37.78 | rendered | lwir_sf6.jsim: rendered | 24.1 | 2 | 33.79 | 90.41 | yes | 95.05 (throttle suspect) | - |
| PointCollectors1 | 9.50 | rendered | framing.jsim: rendered | 36.1 | 4 | 16.78 | 32.17 | yes | 97.05 (throttle suspect) | - |
| PointCollectors2 | 0.28 | rendered | framing.jsim: rendered | 6.1 | 4 | 20.97 | 21.34 | yes | 94.05 (throttle suspect) | - |
| Polarization1 | 0.26 | rendered | nadir.sim: rendered | 310.6 | 4 | 6.14 | 19.27 | not tested | 96.05 (throttle suspect) | - |
| Polarization2 | 0.28 | failed | sphere.sim: failed | 22.1 | 0 | - | 1.58 | - | 90.0 (throttle suspect) | [error] Error! |
| Polarization3 | 4.23 | failed | texture.sim: failed | 2.1 | 0 | - | 4.23 | - | 83.05 | [error] Error! |
| Polarization4 | 0.11 | rendered | pi.sim: rendered | 244.3 | 8 | 0.81 | 13.79 | yes | 96.05 (throttle suspect) | - |
| Polarization5 | 1.21 | rendered | pi.sim: rendered | 230.4 | 4 | 2.03 | 16.10 | yes | 96.05 (throttle suspect) | - |
| PolyFill1 | 0.07 | rendered | demo.sim: rendered | 6.1 | 4 | 6.14 | 6.36 | yes | 94.05 (throttle suspect) | - |
| PrimitiveObjects1 | 0.06 | rendered | demo.sim: rendered | 6.1 | 4 | 4.92 | 5.15 | yes | 94.05 (throttle suspect) | - |
| PrimitiveObjects2 | 0.10 | rendered | demo.sim: rendered | 12.1 | 4 | 5.53 | 5.72 | yes | 94.05 (throttle suspect) | - |
| ReflectanceInversion1 | 3.03 | failed | grass.sim: failed; gray.sim: failed | 2.1 | 0 | - | 3.04 | - | 90.05 (throttle suspect) | [error] Error! |
| ReflectanceMap1 | 17.50 | rendered | demo.sim: rendered | 4.1 | 4 | 43.01 | 77.91 | yes | 95.0 (throttle suspect) | - |
| Refraction1 | 10.88 | failed | classic_atm.sim: failed; new_atm_merged.jsim: failed; new_atm_mod6_json.jsim: failed; new_atm_mod6_tape.jsim: failed | 2.1 | 0 | - | 24.30 | - | 86.05 | [error] Unable to load atmospheric database! |
| RegularGrid1 | 2.74 | rendered | demo.sim: rendered | 30.1 | 4 | 91.55 | 94.87 | no | 96.0 (throttle suspect) | - |
| RollingShutter1 | 0.84 | rendered | global.sim: rendered | 12.1 | 4 | 4.92 | 6.00 | yes | 94.05 (throttle suspect) | - |
| RossLi1 | 0.03 | rendered | demo.sim: rendered | 24.1 | 4 | 9.83 | 10.07 | yes | 94.05 (throttle suspect) | - |
| ScriptMount1 | 6.64 | failed | demo.sim: failed | 2.1 | 0 | - | 7.20 | - | 82.05 | [error] while reading platform file './demo.platform': |
| SensorPosition1 | 4.74 | rendered | downlook.sim: rendered | 8.1 | 4 | 7.37 | 12.49 | yes | 94.05 (throttle suspect) | - |
| Skyview1 | 0.99 | rendered | demo.sim: rendered | 6.1 | 4 | 135.17 | 136.30 | yes | 94.0 (throttle suspect) | - |
| Sources1 | 0.35 | rendered | demo.sim: rendered | 6.1 | 4 | 7.37 | 7.82 | yes | 93.05 (throttle suspect) | - |
| Sources3 | 8.91 | rendered | demo.sim: rendered | 6.1 | 2 | 0.61 | 13.79 | no | 94.05 (throttle suspect) | - |
| Sources4 | 0.90 | rendered | demo.sim: rendered | 4.1 | 2 | 0.61 | 1.59 | yes | 93.05 (throttle suspect) | - |
| Sources5 | 0.10 | rendered | demo.sim: rendered | 8.1 | 4 | 6.14 | 6.33 | yes | 92.05 (throttle suspect) | - |
| Sources6 | 23.85 | rendered | demo.sim: rendered | 44.1 | 4 | 7.37 | 53.98 | no | 95.0 (throttle suspect) | - |
| SpaceRendezVous1 | 30.75 | rendered | lidar_rpo.jsim: rendered | 705.5 | 3 | 359.46 | 407.48 | not tested | 92.05 (throttle suspect) | - |
| SpatialResponse1 | 0.07 | failed | checkers.sim: failed | 2.1 | 0 | - | 0.08 | - | 83.05 | [error] Error! |
| SphericalCollector1 | 3.59 | rendered | inbound_ortho.jsim: rendered | 80.2 | 2 | 20.74 | 25.83 | yes | 99.05 (throttle suspect) | - |
| SphericalCollector2 | 0.73 | rendered | overhead.jsim: rendered | 14.1 | 2 | 10.14 | 11.03 | yes | 94.0 (throttle suspect) | - |
| SpotlightSar1 | 0.87 | failed | demo.sim: failed | 2.0 | 0 | - | 0.87 | - | 77.05 | [error] Error! |
| Ssa1 | 0.63 | rendered | demo.sim: rendered | 629.4 | 4 | 12.29 | 21.36 | not tested | 97.05 (throttle suspect) | - |
| Ssa2 | - | skipped: dirsig4 | flagged DIRSIG 4 only by the online demo page, which the user read | - | 0 | - | - | - | - | - |
| Ssa3 | - | skipped: dirsig4 | flagged DIRSIG 4 only by the online demo page, which the user read | - | 0 | - | - | - | - | - |
| Starfield1 | 0.46 | rendered | demo.jsim: rendered | 154.2 | 4 | 9.83 | 18.73 | yes | 95.0 (throttle suspect) | - |
| Starfield1 (2) | - | skipped: duplicate name | the name holds a space or a parenthesis (a copy of another demo) | - | 0 | - | - | - | - | - |
| StkImport1 | 20.46 | rendered | demo.jsim: rendered | 24.1 | 5 | 44.24 | 64.71 | no | 94.05 (throttle suspect) | - |
| StripmapSar1 | 0.60 | failed | demo.sim: failed | 2.1 | 0 | - | 0.61 | - | 88.05 | [error] Error! |
| SubObjectMotion1 | 0.54 | rendered | demo.sim: rendered | 12.1 | 4 | 6.14 | 6.92 | yes | 94.05 (throttle suspect) | - |
| SubObjectMotion2 | 0.67 | rendered | demo.sim: rendered | 12.1 | 4 | 6.14 | 7.06 | yes | 95.0 (throttle suspect) | - |
| SubPixelObject1 | 0.27 | rendered | demo.sim: rendered | 44.1 | 4 | 0.32 | 0.68 | yes | 94.0 (throttle suspect) | - |
| SubPixelObject2 | 7.16 | rendered | demo.sim: rendered | 62.1 | 4 | 7.37 | 18.40 | no | 96.05 (throttle suspect) | - |
| SumoTraffic1 | 4.79 | rendered | multi_frame.sim: timeout; multi_scene.jsim: rendered | 28.1 | 4 | 10.76 | 18.30 | yes | 94.05 (throttle suspect) | - |
| TabulatedMount1 | 6.31 | rendered | demo.sim: rendered | 6.1 | 6 | 6.15 | 13.04 | no | 85.05 | - |
| TabulatedMount2 | 7.81 | rendered | demo.sim: rendered | 6.1 | 6 | 6.15 | 14.53 | no | 92.05 (throttle suspect) | - |
| Telecentricity1 | 0.19 | rendered | demo.jsim: rendered | 4.1 | 4 | 9.32 | 9.62 | yes | 94.05 (throttle suspect) | - |
| TemperatureMap1 | 0.10 | rendered | demo.sim: rendered | 18.1 | 4 | 6.76 | 6.96 | yes | 85.05 | - |
| TemporalIntegration1 | 0.96 | rendered | blur_off.sim: rendered | 4.1 | 2 | 1.84 | 2.95 | yes | 93.05 (throttle suspect) | - |
| TemporalIntegration2 | 0.98 | rendered | blur_off.sim: rendered | 4.1 | 2 | 1.84 | 2.95 | yes | 95.05 (throttle suspect) | - |
| Thermal1 | 0.06 | failed | demo.sim: failed | 2.1 | 0 | - | 0.16 | - | 79.05 | [error] BasicAtmosphere::init: ERROR! |
| Thermal2 | 0.08 | rendered | demo.sim: rendered | 116.3 | 20 | 33.80 | 34.00 | yes | 94.05 (throttle suspect) | - |
| Thermal3 | 8.59 | rendered | demo.sim: rendered | 22.1 | 8 | 6.76 | 20.17 | no | 94.05 (throttle suspect) | - |
| TimeDelayedIntegration1 | 46.76 | rendered | long_int.jsim: rendered | 8.1 | 4 | 10.27 | 64.29 | no | 96.05 (throttle suspect) | - |
| TrackingMount1 | 10.75 | rendered | demo.sim: rendered | 8.1 | 4 | 6.14 | 17.85 | no | 94.05 (throttle suspect) | - |
| TrafficLights1 | 0.06 | rendered | demo.jsim: rendered | 194.4 | 182 | 167.78 | 168.09 | yes | 94.05 (throttle suspect) | - |
| TriBar1 | 4.89 | rendered | demo.sim: rendered | 10.1 | 4 | 24.58 | 34.05 | yes | 94.05 (throttle suspect) | - |
| UvMapping1 | 1.01 | rendered | drape_map.sim: rendered | 12.1 | 4 | 6.14 | 7.36 | yes | 95.05 (throttle suspect) | - |
| UvMapping2 | 25.29 | rendered | demo.sim: rendered | 12.1 | 4 | 6.14 | 38.12 | yes | 95.05 (throttle suspect) | - |
| VertexNormals1 | 0.26 | rendered | demo.sim: rendered | 8.1 | 4 | 4.92 | 5.41 | yes | 94.0 (throttle suspect) | - |
| VertexNormals2 | 9.29 | rendered | demo.sim: rendered | 54.1 | 4 | 5.53 | 19.92 | yes | 95.0 (throttle suspect) | - |
| WeatherPlugins1 | 1.86 | rendered | nsrdb_weather.jsim: rendered | 4.1 | 4 | 1.23 | 3.18 | yes | 85.05 | - |
| WhiskScanMount1 | 5.17 | rendered | demo.sim: rendered | 6.1 | 4 | 4.92 | 10.65 | yes | 93.05 (throttle suspect) | - |

## Outputs of rendered demos

### AnimatedObject1 (nathan.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `cbd08f4c5852779ad78d120993e439fd1d19f5348b5d464f65f847908fd1a791` |
| demo-t0000-c0000.img.hdr | 524 | `d930386e5ed548914ae86216f88ca4c1860893e25a9b8aaaa3c92ba1ee17286e` |
| demo-t0000-c0001.img | 614400 | `98e0208edf9c774cf061596c4227e7be39f3376452ea8dcbd0afdc655584aea6` |
| demo-t0000-c0001.img.hdr | 523 | `583ccfb4b38a2684556a9150bf6d53072eedfbc0484026505ea7f9de2408b7fc` |
| demo-t0000-c0002.img | 614400 | `74f97f23a62e7cae5473cd7b93d9c1a8bb31923eb7b3aabaefd4cbc5383730f8` |
| demo-t0000-c0002.img.hdr | 525 | `058914f12537342f96be947847f1f40d9fe367799609fcc1b90387c4c5a554c9` |
| demo-t0000-c0003.img | 614400 | `b029848d4216597ed16bf84d98357c3172aec9dc29bd54f220f28c4683f8adfc` |
| demo-t0000-c0003.img.hdr | 524 | `d3691cd3908b26395da29c23995dd98cd0047d5d00f9672f35a597e769b9377d` |
| demo-t0000-c0004.img | 614400 | `53fdade9a7812040147215c989bdd324b59fdfb939c3b7ebccd2bed7ebadf200` |
| demo-t0000-c0004.img.hdr | 525 | `71ce145b0457dc71de1a376e0cf4242b2c10e019070055b360acc98c622b7e39` |
| demo-t0000-c0005.img | 614400 | `a01d2614239bc3933ea296f6dde17959df91cf97906bcd5c499e91e7ac86eb8a` |
| demo-t0000-c0005.img.hdr | 523 | `217cf5b34d904a46c151656ed6e37506fbfa10d6e5cc9b46ffd9d0a19b48d16c` |
| demo-t0000-c0006.img | 614400 | `415a07a5ac4953b14315619e1d5b4d00765cf3b3eb3e435cb517c369855e5773` |
| demo-t0000-c0006.img.hdr | 525 | `a1cb7c7d3cc1594444dd68c39655b09d9acb12cbf6dc72e20c9e318c0bb08b62` |
| demo-t0000-c0007.img | 614400 | `97b4155d67688d095f1f75bf83acffb165966bb839f4baf092d1dfdf812a9916` |
| demo-t0000-c0007.img.hdr | 525 | `ae7ad05f9447e3558610cc874f0eab0283521f828df68ba4f9d50559aa509882` |
| demo-t0000-c0008.img | 614400 | `d57edc2d5fbb7a3c992f0d5be0224c6d84d349524b6adc9217d0520fd45f5871` |
| demo-t0000-c0008.img.hdr | 524 | `f04de362d009178e73fadeabae5d331041aafeb27b3b3f467392e5a723a000d4` |
| demo-t0000-c0009.img | 614400 | `59f7603c38a0dac2516ee93cde9a06e8e2b5edd1a1ee3d6d86743e7c0bdc8ed2` |
| demo-t0000-c0009.img.hdr | 524 | `58ccba6749ee5acecb2df8a3d546121f620ff6ef169c316bf9a9f33d931a25c3` |
| demo-t0000-c0010.img | 614400 | `9990974b27c9ab92719859e02ca34911006a906874103e2a631cbe523bc842b8` |
| demo-t0000-c0010.img.hdr | 524 | `f4367f13617a09c72f72c681fed7ff3cba02593c7476d2cf6de6a27c614713b5` |
| demo-t0000-c0011.img | 614400 | `4fbd7be6782fc589031160c87329609967828b3af836f22160644284b00ab5db` |
| demo-t0000-c0011.img.hdr | 523 | `94873fadc25ea0440227923752b20b713e0e56bbdd972318a3d2c8ece6190fe4` |
| and 172 more files | 414148692 | listed in the results file |

### BackgroundSky1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000.img | 1572864 | `6a50f1ba54941f3dbfed1813ebb5955beeca279ba51e9d7377951711e70d6807` |
| demo-t0000.img.hdr | 559 | `d7851824f5c54d1dad37079a9b7d0ceabc14227f3d96e1c57e2f72dbebb2dc57` |
| demo-t0001.img | 1572864 | `2d15dc8d02c274d6b816d401bbf0f96a0cd379eb8924f0f5dc43998fa11a90ed` |
| demo-t0001.img.hdr | 557 | `7c70413b83be7c4cb401d96814c2ca2c6d3d9fd374f785193e187a92f99aa0ea` |
| demo-t0002.img | 1572864 | `681a3ccc4c28cf219c8dbb91c7b6d2ebb5d5d745d6a7d0c00bab5d72c8fbf9b2` |
| demo-t0002.img.hdr | 558 | `ef099dce3c33e5bfe3ac971181bed12afb78b6870379ba5c2d8bae5c97adb144` |
| demo-t0003.img | 1572864 | `15099a97d521a01ebb7b21e11f2545927f940414b824ff3a826350e5ea721048` |
| demo-t0003.img.hdr | 559 | `09728f1559dc323ccf984e6782fd94cc126670b188f048319a3406656d1ccc6f` |
| demo-t0004.img | 1572864 | `7e4f391ba670bf512d7a968269f27735079bcb015eaaa8e2e6acb6246eb626b1` |
| demo-t0004.img.hdr | 558 | `04b8d85d1bf99b95e60ebbdd8ebe6da4e8eb670368123b17e6b6831d1419376c` |
| demo-t0005.img | 1572864 | `f228a05c7886bb3eb6faa931703df164a9f14ad629959456e45eee6d597ef462` |
| demo-t0005.img.hdr | 558 | `f9902c3e4c271e794936c1bc94e8954d7b58047c06680b7ded9222de2d93b88f` |
| demo-t0006.img | 1572864 | `be5fa100f55747bef1ed5d7a6c0ea68545bdb5a4bd4e3661605d6aef33788a2c` |
| demo-t0006.img.hdr | 558 | `bb565ef0b4f3cb7cb32403db85cd075cdf91d729888fab75b03ac3e983e4142c` |
| demo-t0007.img | 1572864 | `644db373bcd048f5e62074d20f0ae78e78465b1a36d1036e7ba530c0685dde72` |
| demo-t0007.img.hdr | 558 | `9f61a6760d786b4537e05551f8e2cabfc373a23609a1347fda3e2427c0965956` |
| demo-t0008.img | 1572864 | `eccb568009e8c8a4a77de67479997cf7a282e20187e8e57b4ceb5153a0c3f715` |
| demo-t0008.img.hdr | 556 | `6050e013182ab2260c53e57b256f0bd2f9bff02e2bee32711bd74ddfc4e3aaca` |
| demo-t0009.img | 1572864 | `062dbb177d9499bc8f966c02ff38d1e94377736e74dcb90a4d72a2188f3b5a0f` |
| demo-t0009.img.hdr | 559 | `391a0ebda85134efa9732d0d741fbe3bd2194613853be3554918871f0b73aa3d` |
| demo-t0010.img | 1572864 | `7dc50ac86aeca85201ed536c491462e6b5668f32ef9cbf5a13267f94f0d99321` |
| demo-t0010.img.hdr | 558 | `67eb4faaa7b0b540167c73216d801c5b9214eae6a36dbd7b470fc20e160b2b56` |
| demo-t0011.img | 1572864 | `8fe47b023f41cf9d42b9409ca3432258977fabc3f47bf2b3d9f2f0311f6e5114` |
| demo-t0011.img.hdr | 559 | `925048eb9a6ee367c77812df77e62c9483400be3a7237b69b6e024e14b1316c6` |
| and 72 more files | 144720698 | listed in the results file |

### Balfour1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `1108130680b6791cb984c73c72f0abad7fdbcf087302c698f90b2ff81e9985f9` |
| demo.img.hdr | 525 | `abb874ebdb055daa2964736298bad23f93720364a34e0ef407d6f5c76cb70dc0` |
| demo_truth.img | 1843200 | `cae0e806689dbc3ed721f7abf79b75688e94990b4f178649ac30a1607cf95440` |
| demo_truth.img.hdr | 286 | `e37cb34631c0ab39cd0e4e34ca33db13b546b673e3434102845f855064e7275d` |

### Balfour2 (single.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1280000 | `59235e83fe26bd67270e659de37fa03b8655eded5dda9493f8074193f42dfbe7` |
| demo-t0000-c0000.img.hdr | 524 | `9472eb7708500c2d40ccd461f3999a3c254631168b91e3472dca5b8d5c0eabe3` |
| demo_truth-t0000-c0000.img | 19200000 | `a93d44fa94361e9007ec8a0ed975dac5e05ba6c6f402d47247ad89f5295c17e3` |
| demo_truth-t0000-c0000.img.hdr | 508 | `8bb8b5237fe2fbd3a4d7400bc4e74a21bb3eda91eb58627e0901af24f6ac3fc9` |

### BayerPattern1 (bayer_hdf.sim)

| File | Bytes | sha256 |
|---|---|---|
| bayer.img | 614400 | `7e23541d73cfeca1c17d95b20bf0cdd24298280182b5b95abe301a04089c3241` |
| bayer.img.hdr | 523 | `bc273c71759bd866ef20f48c812361b939dca61b56022dc44891ce7e4857159e` |
| bayer_truth.img | 5529600 | `84933fac4ac1c3a43141b50481662fc78a30e5940041c098d015bd1df9638bab` |
| bayer_truth.img.hdr | 424 | `1192db4f6743ff4c276c2ae2af2096c09869813b9465b29512487f6ea200356d` |

### Brdf1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1843200 | `033096bafc7590fece14373892f357a78c5476644cab542a07fbe285c9c42a35` |
| demo-t0000-c0000.img.hdr | 585 | `1e72a57b0ff1d2865abe5421e8810a125cbc0b2cb9cbd64f5d4b0d17709b8cef` |
| demo_truth.img | 1843200 | `0735459979d0cdb487d9dcbeef8c8fb163d7b2ebbc8108e3ff9c2e6cd709f5c1` |
| demo_truth.img.hdr | 283 | `8b27536622ffcd111c0918db27ad9cbf3f027eda6ba23219bdc5860e65516e03` |

### Brdf2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 7372800 | `f7e4e61d8c737dc58fc28227993f0e15d5d379d9e2b352a5c00bd97250107009` |
| demo-t0000-c0000.img.hdr | 559 | `329384a12a3c520949624bdc179d44269080325f194b2eb0eadf245507d53568` |

### Brdf3 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `0077ab39e99cf28a661fd533d1ecfa60e12c1a724a68c845031063516004ec1a` |
| demo.img.hdr | 555 | `c674b5dd434b98d6a4d57519215f92ed805fde07dc2fbaf5719856ff4b8d430d` |
| demo_truth.img | 5529600 | `06a6f1f2475e39eb7dcf2edcc1da9551d07292d118d5ff5fd18eb0c8e6e662fb` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### BumpMap1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `c41395c0b655108919cf58bb487d0ccb9008952ba5c270d9b5d6df5dd7999cf7` |
| demo.img.hdr | 564 | `faba4cda7d9479fe6bb0eadf6abef7a5a209ddc882d30b4fac5d72f971d75cc2` |
| demo_truth.img | 5529600 | `dac677bc6eccb543b15cac811be0b206bacfb8079bf0fb5f7a58b1aaae9895c4` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### BumpMap2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `70536849bf87ab7f000474b443d2a021870dc177c3672ed3e7b87f3615d492ad` |
| demo.img.hdr | 533 | `e548929f637b974c8ef3527d361c5cdb38edfc378cbf4211b896e769729fc18e` |
| demo_truth.img | 7372800 | `fadc38cb8a24221f06d62207c4ddaee8f458a2eb6f0317bfd52898a43835d4b8` |
| demo_truth.img.hdr | 506 | `bf809b2a42a8515450a3a31b188e972f5729c6f9bb1b2526b6e28ad46954a1e1` |

### BundledMaterials1 (w_bundles.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `162ef7ab100103c26c19365fedb0c5474c5bb7ec10061030a00660d8a3454167` |
| demo.img.hdr | 562 | `a6c39718022528b73ea8f6f60e873019dae480a56d1f2b02e5cd80b47da2d550` |
| demo_truth.img | 1228800 | `998e5d9cfda8658f56acc98115bfa1a2963da1c3327c22ca89ff78e7d2887f5c` |
| demo_truth.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |

### BundledObject1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `fd9f281d11a4ad978deca1c3c51d88bb56e756ec38524ab8704cfb388b5bda8c` |
| demo.img.hdr | 560 | `5a89e5e1ac374e4994998b4b2c4432410ae2bfb7936331e939c957a5a891f87a` |
| demo_truth.img | 8601600 | `cfb076cf0b84c0d918ffc927949974de71a5eb0cd0367a47f379d387474db0be` |
| demo_truth.img.hdr | 492 | `68f51138449fc9a05187083c9806e86e4e6701a8310e0e2bf300880e29deb46e` |

### BundledObject2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1843200 | `606c990c27193c71d37b7a771b1315c57d51abb29af4e500c0f6f9909439ccce` |
| demo-t0000-c0000.img.hdr | 588 | `d78513870fd71b3542e54ad5f48fa2ba4e750357e20149c7ef94a4a389c5432f` |
| demo_truth-t0000-c0000.img | 9216000 | `b44863c23053e887d6084fb2fd2df2cb93007a2984b96062c40c696184052677` |
| demo_truth-t0000-c0000.img.hdr | 505 | `95ae701308c0b99910ab92f00c5a94daa52594e9ac2a409a7d870a3aae741454` |

### Caustics1 (clear_water.jsim)

| File | Bytes | sha256 |
|---|---|---|
| clear_basic-truth.img | 127926272 | `081897005553affe136b849389052c25a06d1e15597e96e96d93e0f7a6622709` |
| clear_basic-truth.img.hdr | 1720 | `c3321013b93e66ab94ff102956a80bda68fe20556a00a61503b7462186151b19` |
| clear_pool-t0000-c0000.img | 6291456 | `707849a642aec4bdc7838dc52110fd6576bb27d401bf4627e744156ee5afb61b` |
| clear_pool-t0000-c0000.img.hdr | 586 | `0c9fceca1d0116b1aae7bf74fe0493cb43d7c5f997853419762b7a0e17d4310e` |

### ChipMaker1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 7372800 | `2e5f09ef58025499a7ffd8ab64b6c62e987ab76e60a79d9cc78d74924d94a13c` |
| demo.img.hdr | 552 | `e5eea2cf30e8a50594777b3d3ed96393d49ddb6c5e02e6739df3678b3e63c950` |
| demo_truth.img | 7372800 | `9b40efbfa92cb0d5744c606403e933a057d6bfaffc86df9e064e6ebccdba2b6a` |
| demo_truth.img.hdr | 283 | `b7d10b8b2a92f7f8926021cbf241268dd3494f10064469f762ca9eed5c9f0f60` |

### ChipMaker2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 19660800 | `ef739805b9ba7a92372b65168a387a2ce712fb14f21d42c4dda2aa95bdc53b97` |
| demo-t0000-c0000.img.hdr | 606 | `d1cba4f28063075ba860a2662508e27c102aff15f685518e7a3fe1711e096719` |
| demo_truth-t0000-c0000.img | 44236800 | `ca3afba13592fff1ac65c31f0927d01032b706f11b249f27148fd98081eada2a` |
| demo_truth-t0000-c0000.img.hdr | 424 | `8928d9e3ce85b29a858da7e375544f41a067d5afceb5b65f5a1c98c9f12de9d6` |

### ChipMaker3 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| chip00.img | 1843200 | `c754690cbd7e3bf971f25c8e3e7bdd5b8f5f3cb64dc9767426b4e53da381af3c` |
| chip00.img.hdr | 507 | `b619043e454c271f0fc4a93f9c647744526f13975908482c520f71ae8ae0f7f7` |
| chip00_meta.json | 1251 | `04e7dfe571fc76115e866eaecb00589aff3b13b684c0cf80ad9ec170fa437471` |
| chip01.img | 1843200 | `078ce052912c583400463914cbf9acb2aa0ccff11aa13c5e75f5453360e115b1` |
| chip01.img.hdr | 510 | `a079acfb6590000116e18d29d3b59693e1e2292305be01c600b575cc81e6ed09` |
| chip01_meta.json | 1250 | `83a8d8a609ef93ac4bb60c562f92b024ab98b1d91ff5befe7ddc1c29105afeaa` |
| chip02.img | 1843200 | `bdb0eca605ce5780e87398729716bb8bd856716bed7b1d0916223784817f7aa0` |
| chip02.img.hdr | 511 | `7e58b9bfb87e023f52cb29247d43fa23c6de77d7eda81b55696501eef884a927` |
| chip02_meta.json | 1253 | `0b91b7865880948b4bf19a25f100b6a06aecbcd0bb1fdfd78723309c985668ce` |
| chip03.img | 1843200 | `1ffc217298be6ef40644cd6e938e8881f9b08a5f1ec3854843fbc7204d8e458a` |
| chip03.img.hdr | 511 | `384c972d663b7cff515d55a4c9273bdd3cec41f2784cf561a09d0fd68a58e5dd` |
| chip03_meta.json | 1257 | `2f9f1608918c7dac4471f1c29c212ffd04baef326b5485d1dba7a97b318d8c05` |
| chip04.img | 1843200 | `fc8f3ac0f09bbaafe02170e20e5682464289537e71d4a28470a67e22d63af287` |
| chip04.img.hdr | 510 | `1f4d0ef432db49e29ba8ed3fa71954c4593a95ec35d494e3d99c908a163e71a4` |
| chip04_meta.json | 1252 | `a94474e790a590b4b54f2e5a7fe03e21acdb7d515fa74faa1014abb26c07cae2` |
| chip05.img | 1843200 | `489a76b1d8e68a74b74ad61188c4a56c6287f5c6da79dc8665dff99906b13390` |
| chip05.img.hdr | 511 | `8e06eca60b95231229fbba37ad762ff6353f3b5c2cd8743eec63f98f894ce270` |
| chip05_meta.json | 1250 | `e38c5ab2de4dd5d266fbfb032cb13d29db5982bcd9490464be3500f38875e86f` |
| chip06.img | 1843200 | `46cf961d566f0cfe61fafecd3fa6d36129bdafe6c285cf63528e9008a064fd8b` |
| chip06.img.hdr | 510 | `ebdb1b730205b9e7c4c1f73d9819993be8f8df52984584dc5fdbd5a29a4526f6` |
| chip06_meta.json | 1253 | `c7a8576cad90333da6515cfd6cd4b7f4492d4614ee03457ef44637b4c5973f2c` |
| chip07.img | 1843200 | `f1d731013c06f4de321ce824a08c8cc34d1af18be5f2ab70639ad2ca395184c2` |
| chip07.img.hdr | 510 | `bd834aeb5d0cdb7797a0691e0252b902332d81a064ea3474b11742afc95d405d` |
| chip07_meta.json | 1252 | `1a9eb9fdb5cc905cae4439bd02a38f4b1033f9eeee1eaa1059d0245d772c8ab4` |
| and 36 more files | 22139556 | listed in the results file |

### ColorFilterArray1 (bayer.sim)

| File | Bytes | sha256 |
|---|---|---|
| bayer.img | 614400 | `e5de7bc1fb2e864ce23e41024ea83a13999c86be8aa85bf04a10681a949cc779` |
| bayer.img.hdr | 518 | `fe09ce0e2a66d504dc16b00f70ac4355a88f779c2cd902d73ba365a8fabdbf55` |
| bayer_truth.img | 5529600 | `6513fba1d49733a1bf7954d2216b7434bedc84f4bb1af03e04077ea76770b040` |
| bayer_truth.img.hdr | 424 | `1192db4f6743ff4c276c2ae2af2096c09869813b9465b29512487f6ea200356d` |

### CommandedMount1 (demo_absolute.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `c88d8d7dcde947836d2be06940d6aff27322dad2ea7630ab79a1d6923fa21dee` |
| demo-t0000-c0000.img.hdr | 526 | `e4a06447f974b2160e471e3548481657e8d1c76600703fcd69ac16910b4ad52e` |
| demo-t0000-c0001.img | 614400 | `137760f809743a8bdeb0f33e0d5239fc80c44c1f3590223010e37cfdfbddeb5c` |
| demo-t0000-c0001.img.hdr | 524 | `b02a4212e14676ab3d2dc745ca3f243e90a7b19e916367bbbb4dcf0404e725e8` |
| demo-t0000-c0002.img | 614400 | `06dc9348bd7bb398c912f4c2831b85a13f402fcc348f22cc08e320ffe846e721` |
| demo-t0000-c0002.img.hdr | 524 | `5c7d71b18d098edba7d1ca96e982a3156d7a6a5d9d5fe47bef1e72c56d36c5eb` |
| demo-t0000-c0003.img | 614400 | `47dd6665f2984fb0306a8741c72fcde5f975b29a6c0c68dcc46bb95bf33c30ed` |
| demo-t0000-c0003.img.hdr | 525 | `7a0f1fcb6b6905d9706129ab246b4d482f457d37b159e8f2844005accb817fc5` |
| demo-t0000-c0004.img | 614400 | `6662eabe4859eb7b367dc34b8aa034a335565164fc7b099ff37aa1ddacbe057f` |
| demo-t0000-c0004.img.hdr | 526 | `de281fa78a501f909e3b3d7051b7a92f593e37987b4bc891ba2eb62eeb4a759a` |
| demo_truth-t0000-c0000.img | 5529600 | `92ff2c30a15fb591d2bb6f5a62a63dae47a6e983e1705435bbea1a211563a78c` |
| demo_truth-t0000-c0000.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |
| demo_truth-t0000-c0001.img | 5529600 | `1b0c87b91058d2fcd6e8575ba90549d9db60ccc17655c772212bacb51ab850e9` |
| demo_truth-t0000-c0001.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |
| demo_truth-t0000-c0002.img | 5529600 | `5e5ac539b1cc41b3aba21fffd5ea4c8cbbddd6bc2a76f11f6d102d5f7dd75925` |
| demo_truth-t0000-c0002.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |
| demo_truth-t0000-c0003.img | 5529600 | `c59ab51579acfe9e0a32f9ae4b20fb0e4b0b011eec55076a711a0cb826ba5271` |
| demo_truth-t0000-c0003.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |
| demo_truth-t0000-c0004.img | 5529600 | `a8885426c5767cad5806e182be83059ee2f56297a0baa0010e9b0d9e780753d5` |
| demo_truth-t0000-c0004.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### CommandedMount2 (demo_absolute.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `3c441819c5c9ea9d344d1ad557415bd8f8461f1db17053db9ac41a4b84b60be7` |
| demo-t0000-c0000.img.hdr | 526 | `49d1bb8f4be958906f8a85a9ba2b61c5451aea0a6a46812535067ea5e9fb9094` |
| demo_truth.img | 5529600 | `54066a6e7c460acf6699321b71db4ced19cd6eee5d0103e233f81d62073ece4b` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### CurveMap1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `c2d4d03aa6ddcf4474d82f82db388ca28a44f7827d8b0fa613472abfc41acaee` |
| demo.img.hdr | 559 | `7f201569d4b125291a22de0ec9704595a483f440eaa1aca2f83d1e698ca49e34` |
| demo_truth.img | 5529600 | `2d5aa73e17b5c13da81b52dcd56181f201c62298fa7cf66790683158495c07a3` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### DataDrivenArray2 (w_gain.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `771cbc3aff10533167c0b23293b9f72228cccf7a8c2f4ebcf45d93bd3447cbc0` |
| demo.img.hdr | 497 | `69c61f85af416e0ccb42509c647c3541a2488e2b077a0557102781d23321ec65` |
| demo_truth.img | 5529600 | `3ef61053faae40c027c5711c26cfe9e9bbb9e8635af5912db9cfa74e0fb865bb` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### DataDrivenTempSolver1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `5798dc81857532d96ddd528811d166bf8142af60f427bb79393f2ef29d211313` |
| demo-t0000-c0000.img.hdr | 534 | `6ffc07d59477056c5260df809d3a1a62f230352ced72238a5a599cf185a76109` |
| demo_truth.img | 1843200 | `441830ca711cbe8ca09bb26b3356076e998f5097a6ccb855cc620ec0984ae947` |
| demo_truth.img.hdr | 287 | `42cc6a2b6daa6ac863929a0d21bd8ecc877b60bde8483545fc9c0177f56fe493` |

### DecalMap1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `ffdf5851195b68c502711385b8a640387d7e26d89fd6b728129a13892794e415` |
| demo.img.hdr | 527 | `d0bcca3f9d3772a64c9b4f0bd3fe9c0d6a20a059ebabae71d173b5a43ba50418` |
| demo_truth.img | 7372800 | `dd70326ac68d0c9acccb3acdd6f9ef71cd5717c8315badbc914d69f8e90c6714` |
| demo_truth.img.hdr | 506 | `bf809b2a42a8515450a3a31b188e972f5729c6f9bb1b2526b6e28ad46954a1e1` |

### DeltaMotion1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1843200 | `f5c4744d455a4105d18093c52206e72de1da633eb34fec7a0f8b73fca6669bb4` |
| demo-t0000-c0000.img.hdr | 558 | `b23ee70bd5b5f23bd27b3d4461b23be14a1b9b84023bba3ffa41e1c5e9b89233` |
| demo_truth-t0000-c0000.img | 3686400 | `2156d3ec12cdc57619cbd5d69beebf30b91bcf3ceda575e7866e99967c215dd4` |
| demo_truth-t0000-c0000.img.hdr | 328 | `17b6e04b5ab4395b381c744520740c1cd657b4054389b7804835fca1891bc793` |

### DensityMap1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `d78868ccd749174ba6193a81a5c2b89c02ad86376d62d2df35a41047754817b9` |
| demo.img.hdr | 528 | `240588a0dd58de7591547733ecd5b41f06b135b34311aedc66ae081c9b5431d3` |
| demo_truth.img | 5529600 | `1e7990314cf49139a5a91874b389b7665c8383d236c35bd241e0cabcf0a91c05` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### EarthClouds1 (demo_basic.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo_basic.img | 21120000 | `671c23a5d9e38d92f212b61b13bf0c57beda2a2b1a0a4b6e716feb16fbe20c5e` |
| demo_basic.img.hdr | 474 | `6c4f104b8d7130ed9fdc740b9bb5bc9a1a980186a8a64209f2d92c34c44416a1` |

### EarthMap1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 2150400 | `a12dfa031a0f5458394e8cb07d7adf4e29e4f42f031f1e7b9dc0b7f7856a7e24` |
| demo.img.hdr | 581 | `2d1104a6c50d59935d1c04199758067137c2aec6a1c256ea0775889da8320b23` |
| demo_truth.img | 6451200 | `e80a1bcfdb06d296977996ad9cdb168b884ff2fb05e83120173ab4aa6680ea49` |
| demo_truth.img.hdr | 424 | `a0eae46b1fe9cd42d8d766bf0441b817e96230cf94f7c348c22ca9fbbd698dc8` |

### EarthShine1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 29491200 | `31f7fce45503bc71d1cb8dc97984f36adc56aa5e646b6df87c91f03ebf854b12` |
| demo.img.hdr | 593 | `167d8d53cf633df9e12548e7652921c8f73d12a87e282691001e97b68538edfb` |
| demo_truth.img | 304742400 | `2cf935d5edfdfa6a78d20c22287bb6698785bcd5acc447b47f97d5bf5a42c55e` |
| demo_truth.img.hdr | 847 | `517a8bea68a55f73b280e6892f325727da6a606865ed6a03423d5be595efc24e` |

### Eclipse1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 7372800 | `411b56e2ed114fc26174fa171961facb5ea8a6b5b386ef5e5ef404109e1a5ea1` |
| demo-t0000-c0000.img.hdr | 588 | `81857794474ff58cebea66e0d7908094f5c54217ad5a23e46bb042ee745d57cc` |
| demo_truth-t0000-c0000.img | 17203200 | `427111d74d7c0039a2f7b60aec360448a9105d384cf16659115ee3184f23e1da` |
| demo_truth-t0000-c0000.img.hdr | 337 | `21ae97218e9a2c1ffd6020e91a0d3be1ca17895be19c09d2b1e75146622e2ff5` |

### ExternalTriggers1 (constant.sim)

| File | Bytes | sha256 |
|---|---|---|
| constant-t0000-c0000.img | 614400 | `3f29899bddb197a63c93012b2d88086087a677f49c3839271164d3a9564678ca` |
| constant-t0000-c0000.img.hdr | 534 | `03cea553ac8aa03ae81c6d84fbad544495b9072e00ba11391926891541763ff1` |
| constant-t0000-c0001.img | 614400 | `ece37489f68123a7353b601ce2f8c0076bdae1e2e708d569a855a009353f0cc7` |
| constant-t0000-c0001.img.hdr | 531 | `d6d26555beff3681191870f32bce652cf8986072a7765e689943e4a93d3bc380` |
| constant-t0000-c0002.img | 614400 | `2b6eea3a759ed8b14232bb965404c7b30faac1b54afe4f93647d9b27d0da9023` |
| constant-t0000-c0002.img.hdr | 533 | `147e84964deb4883f5101e96f4682b9983948c17d04ec959dff613582afe7ebb` |
| constant-t0000-c0003.img | 614400 | `f235d9cd471bceb53295ce6620b1919f252695bd6d04e0e171cb8936d1464648` |
| constant-t0000-c0003.img.hdr | 534 | `f8c3b60cd6e0e89522fc1ba745ddc154f109a01efef17ad3d5367ce9ef260af8` |
| constant-t0000-c0004.img | 614400 | `6c4e30324eac43680bb6dab3ca03bfce83de06f446229dbb7143eaefd56307c8` |
| constant-t0000-c0004.img.hdr | 533 | `a552e9216c3e17e9e7764c4a18ae94ef04ce7926b11c6cf3717a7b1df5232d14` |
| constant-t0000-c0005.img | 614400 | `9f31fe28c56fe4aba439395d1d8627619aefca7042cc8648d21f709312f1ad0b` |
| constant-t0000-c0005.img.hdr | 534 | `3016d4eb0dd7e190c7ba2f767015637407e781f27362e8274ff573aea191c042` |
| constant-t0000-c0006.img | 614400 | `f6e1705aef8be5a205a1365fc2098afcb1dd3300775202190ea3ea7ff4d8fec7` |
| constant-t0000-c0006.img.hdr | 530 | `6111fda8b4ea450ce0181fde2ac931742a6e17d598b7cee2b0738568e3b95861` |
| constant-t0000-c0007.img | 614400 | `c1c0c654cb7c155e2a04448afb585028611724c53e5039117030d9a26d7b349c` |
| constant-t0000-c0007.img.hdr | 533 | `2880bd7a829c95c784938ee9755b78f935aabbd6ea4f66a87f646a447417a8dc` |
| constant-t0000-c0008.img | 614400 | `834bf791d4db7748c995c7ce5075c25ac107bbe33976034dfe98ba8076a8f29d` |
| constant-t0000-c0008.img.hdr | 534 | `782efae2fb8ed81660171cee2aaf7e14ee9779835b9e06c02af7239727160654` |
| constant-t0000-c0009.img | 614400 | `bb03559433b449e8fb350386adc7ae84d2e01d396f635cb12dce634cd09f545b` |
| constant-t0000-c0009.img.hdr | 534 | `b698cdbbeb2155da552120495dd3fe711d04a80c7d039b1f35a8fcfbb81541c8` |
| constant-t0000-c0010.img | 614400 | `33420c40babd9db85300ddb6778a55edacaab69086eedacde67315ee6bc54ed1` |
| constant-t0000-c0010.img.hdr | 533 | `2fbf4c4367121fde61aecddb713fbaa76fbfa4d7d6b21cdc6682335de44885c2` |
| constant-t0000-c0011.img | 614400 | `5941acebdddedb38c793c539d489b80a5906441ebf600ee9580e12bf76ab7c5c` |
| constant-t0000-c0011.img.hdr | 533 | `7dff536a6e69de651a1250760f9df6bbfb558fbb058dea59c5894bd5381f8746` |
| and 26 more files | 7994130 | listed in the results file |

### ExtinctionProp1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1843200 | `1ad4f19cdb44723c13ca7c57733d09e33bc7da9a0a2e9614e7fed0e23b537d18` |
| demo-t0000-c0000.img.hdr | 585 | `f1e12a9c7a47807b95c84c8bdf2f38947cdb35e7f77487b8a090b1efeaecedb6` |

### FastCloud2 (demo_mat_map.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 2457600 | `dc47baf3203be59992776f792d098781b276d6f32d592bbfb8bf32a4f9640384` |
| demo.img.hdr | 527 | `3ef12366e5a8855346a36fe24331ff154eca43fe092a101f8ee58bf7ce473b0c` |
| demo_truth.img | 34406400 | `fa8a8e73b430e3fd42f96b002b096010df90cbc43dac8779f5aad44ab6776afd` |
| demo_truth.img.hdr | 492 | `859361cd01d2a21eef7e83f9358010dc04ebb17654ebf40534596215d6bf52e8` |

### Fireball1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo_truth.img | 6144000 | `1a8546f1526392452381990b810eb74ac1c4b248bbb2098ab18341a425ae9cb1` |
| demo_truth.img.hdr | 441 | `44dfae38cfc25771b7c82b04c8e1981088f058026c933e6df572807f6a0d456f` |
| mwir-t0000-c0000.img | 614400 | `9c0829ebc538a2aef859cefa71480d8d47115b6835f4c12e0800ecfe20acdc26` |
| mwir-t0000-c0000.img.hdr | 529 | `0a3273ee5b9c1b62781067e83d41edf5e697cbeaf74fd76baf4538765764cc80` |
| vis-t0000-c0000.img | 614400 | `34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f` |
| vis-t0000-c0000.img.hdr | 541 | `5c5ee12b2692feefef502803fb237f1965a8acc8124f68d8c6956596de7a6909` |

### FlexMotion1 (multi_frame.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `6f73704604a58355652843f458fa99755750be0b9691a1a5208be2458befc3d1` |
| demo-t0000-c0000.img.hdr | 533 | `bbbb40dde6d7d2fc64e0c2b4eb71c865f1f9a084ecb6a6938ebb198b119ea4d6` |
| demo-t0000-c0001.img | 614400 | `00e78cbe2d3a111a6f7b0d585b668c68d6d15c8a2af34f170950b59d7d06f727` |
| demo-t0000-c0001.img.hdr | 533 | `3c83e99a18d9dbd63da7c9e65e3ff987a866c583866fe6a3aa44487ce4a7fe83` |
| demo-t0000-c0002.img | 614400 | `67dd9f8a0233555166f5e9fd2a632c4a4f6eb503423f785f7bdf671bffb4d158` |
| demo-t0000-c0002.img.hdr | 533 | `3f4061418c694cbedc6d10aa541d2d4f6f6d9eab0d556e5c2d446abda1d877f3` |
| demo-t0000-c0003.img | 614400 | `01dfaffa63d7fcd2cc579bb5ceefd5f17b460d2cd69793913fb9f75a00c5b788` |
| demo-t0000-c0003.img.hdr | 532 | `7c2596513acf5cb52613dbd6ef7436e743a8daf0a22213d12dfe749eac3b9184` |
| demo-t0000-c0004.img | 614400 | `9e57ce11926e46efe119cab2b901128a514bddf52482862d2f7a7220495719b2` |
| demo-t0000-c0004.img.hdr | 532 | `234dad685ced38446d530a257d07df02b4d217b2e8a3213018c45e61a268a02f` |
| demo-t0000-c0005.img | 614400 | `86e3f9bd0d5b78e2c4b776f1715e455c49259ad44634fbda3e425d7f24cdcdd0` |
| demo-t0000-c0005.img.hdr | 533 | `d2139a5c620cc1e31b5a3587d063376591215af6ec54ef22c72f1ff62f98e08e` |
| demo-t0000-c0006.img | 614400 | `d9a23cbdbcb446140aa2ac222db8639ce31faa8a17c6aa1650cbc2fd88f38980` |
| demo-t0000-c0006.img.hdr | 532 | `7584bbdbf973b608f102049460223573f3fcd843dfb68760dccb6fcf32565dab` |
| demo-t0000-c0007.img | 614400 | `08cb749e260103bc5794ae201465dc81d199c7a425853cfa1146ee5928fdea4f` |
| demo-t0000-c0007.img.hdr | 533 | `df9560719296dce49dbebd76a771256cefe11f51b5ff378bff2aa8dd30809667` |
| demo-t0000-c0008.img | 614400 | `5c93fa398974737fdffea8f8f11e530469c99cd77a232f405acc89a76be78d09` |
| demo-t0000-c0008.img.hdr | 533 | `af00bf59bfdf548acc1e84a0a1651759b90c568e1391d165eaaaad884622fd9a` |
| demo-t0000-c0009.img | 614400 | `ac18f4881fadc88dfa7e0324059eb9a88010f548c3369eb2f6630c6609982e89` |
| demo-t0000-c0009.img.hdr | 534 | `b3f615e14a6c8595d09245417e7ff0f8d296db54a8f2ff6c685591d797295d65` |
| demo-t0000-c0010.img | 614400 | `9d64d2cdee1e09c9a987e07205269e2b24ec8e0ee46f91871c495b245956909a` |
| demo-t0000-c0010.img.hdr | 531 | `4b3131be7fb47f6620241b07de023e507fb05639897515391fa29e971b66fcab` |
| demo-t0000-c0011.img | 614400 | `293f59b01e3100c3d0c08944e80c35bbde4ba528c8b659c9265c22f969e5d2d1` |
| demo-t0000-c0011.img.hdr | 533 | `1d2fa68996f352eb7e65182bb6cb725c08072037cc3c20d72c6d5a55cec0645b` |
| and 124 more files | 60848923 | listed in the results file |

### FourCurveAtm1 (default_w_path.jsim)

| File | Bytes | sha256 |
|---|---|---|
| default_w_path_demo-t0000-c0000.img | 1843200 | `4bbaffd070ba5904ef28cbb12fb99095ce3388eed3452ade21078c618819a2c0` |
| default_w_path_demo-t0000-c0000.img.hdr | 560 | `60d58039c42a00ee198fedb03bd7ee439fc740b3d2daf337f047daa837704b93` |
| default_w_path_demo-t0001-c0000.img | 1843200 | `2e35e577484e08b3509359eda10b5f0c02207d989f4690a315bbc41d8ac37c2c` |
| default_w_path_demo-t0001-c0000.img.hdr | 562 | `ed93830ebefc00b4f7212e5ee3b5e40468f4f5a2a3e5561e9b1c19c0e38dd409` |
| default_w_path_demo-t0002-c0000.img | 1843200 | `3b2128843e2fff114569c876449430bf388800f43ab22f5e621680af8920f859` |
| default_w_path_demo-t0002-c0000.img.hdr | 561 | `35811e92d50ad169bfbaa6cc3749a3538539d20959dd15db643481f06c9699ff` |
| default_w_path_demo-t0003-c0000.img | 1843200 | `b64102044da756b70bcdfbfee42c2fd38e375416fff51a1e40cd910ff2207dac` |
| default_w_path_demo-t0003-c0000.img.hdr | 561 | `caf4dbab404cabf9bc8b3e57454e063c0df98d1b488f89fa64d8a24b19d0ab55` |
| default_w_path_demo-t0004-c0000.img | 1843200 | `fcce1b2236192c2fc7d19c28b5c1910b66b098bcbcedf9794eccb3d6f186973e` |
| default_w_path_demo-t0004-c0000.img.hdr | 561 | `fc92160b9104f054daa1f2230372b8135412a165e09a8ca48ee8e52aea17d5bf` |
| default_w_path_demo-t0005-c0000.img | 1843200 | `2e1064a1559e1b4da198485224f794f7b1ffb92cec410d085bff8432444455c3` |
| default_w_path_demo-t0005-c0000.img.hdr | 561 | `720112d13fac6ca785ecb3d414dddf50d9c48b437d072666e93d105b2b1fdf44` |
| default_w_path_demo-t0006-c0000.img | 1843200 | `61e6761d63d79b2bd7ad050757774fc00ca7f74b49832bdcde1fbc505e8c210e` |
| default_w_path_demo-t0006-c0000.img.hdr | 561 | `5b8d1a6b00379bedd4357ca57795b0ab22528b7c5e1224933728220ac6900fc8` |
| default_w_path_demo-t0007-c0000.img | 1843200 | `6341913b3fd019c71c7eaa5407e8c0e6cf67aa07c52e1a9e8a3e4596d7e567ca` |
| default_w_path_demo-t0007-c0000.img.hdr | 562 | `5d76b6919bb392efcfa46b856102bdeb1bab40437ddd863c20904552519c2a79` |
| default_w_path_demo-t0008-c0000.img | 1843200 | `c3f7d4f3112e5eba0a1be16b636cef7190aad139a5c6dfff5d48ecd72c67f214` |
| default_w_path_demo-t0008-c0000.img.hdr | 561 | `10fb3acde08ae39ac1c901469d2aed5228dddd36ac2a16fa2462e414d3079c51` |
| default_w_path_demo-t0009-c0000.img | 1843200 | `8e30b30e143aecd33460a76efb5dbe17c0effbac2e6e8e1e069db299a4b65a9f` |
| default_w_path_demo-t0009-c0000.img.hdr | 562 | `75dd1cb2568184cc4f8225fa20d1b3d63cffb584dd7dec542c34b912c1ed2bcb` |
| default_w_path_demo-t0010-c0000.img | 1843200 | `b63197214caef11766f78802bf24fc9cc3f078b20b0dee54db2598ef099dc259` |
| default_w_path_demo-t0010-c0000.img.hdr | 561 | `5224b4563cf8593914a9946e20fe27a80fdd71b0c5d7eaaf754a6317fda016ee` |
| default_w_path_demo-t0011-c0000.img | 1843200 | `e86744515ded7ef0e6116c1f236564ab778cedc4b74701f1fe9de898992a4949` |
| default_w_path_demo-t0011-c0000.img.hdr | 562 | `9a4173ae5934a04482452a670f3abc2491fbe6e1c5e3c6c5a526ca5e36f5510b` |
| and 68 more files | 147470571 | listed in the results file |

### GenericMotion1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1843200 | `0eb70948edf27fe62ac7cf8516ca422fb97826dd4d1d7d84aada0ff32d598441` |
| demo-t0000-c0000.img.hdr | 556 | `7c151ea697c0561a4548dd282e6875849bbfc35e0bd296c148e16251af9ca8f3` |
| demo_truth-t0000-c0000.img | 1228800 | `0d4239ced33e8fb3b6bfc185c8770d55e7b35e1267c099bfff0f714893977736` |
| demo_truth-t0000-c0000.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |

### GeoLocation1 (flex_ecef_ecef.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `efb1eedcc2af61a9d9c0ff5dc85933e558d947db8ceb10c7de30627cd67d243e` |
| demo.img.hdr | 588 | `073f68193a7cc08a1cc1fa605d3eb26b924e1bf99b546716095aaf8ea32a43ad` |
| demo_truth.img | 9830400 | `0ec20c50d5b9a7feb51eacf7e74fd695d0fcf587134d3739638cf64c4e0684ba` |
| demo_truth.img.hdr | 588 | `0daa722054ba17168761a02390ce66183c28cf74d8c493a7bfcbeee52644c953` |

### GlistPopulations1 (demo_daily.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `dc1eaba246dae569d16f8d4ca449f0ab8572714041cb46d1fdbe81f95b284775` |
| demo.img.hdr | 558 | `342f3f68327ac4e2f9d28e90a7e126620d39e5480622cdc400ef77bdafc5197a` |
| demo_truth.img | 5529600 | `a7bdc4be2f1a58abfa10d865b9e36bc602aa809737a00f799408f2e50604d58d` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### IESSources1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 2764800 | `8bb798089646bee45c50a24a9cb22e9e1b76be1cc85b9349fec139d3d45285b0` |
| demo.img.hdr | 566 | `f5d0ef733b531ddb89bfb6283f214c6ae177fb610db527a23d7e89e686ceeb3b` |
| demo_truth.img | 8294400 | `be6faf33a4be4ed4878fdfbec73122cea84aea5cd4a8e947ee1fec54b414fde9` |
| demo_truth.img.hdr | 424 | `f605a1f26244c4956df890bb5be106c2f057b97227906d912e1a5a622079b508` |

### Indoors1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `8c5d23d284b77f5533102f4fa87e85cdf4849ede1a42f48635fa83d46b5d8239` |
| demo.img.hdr | 588 | `7565bfaf0f0f304182baed5fac70045b20d658834a5ec9d58be987bcc0754f1c` |
| demo_truth.img | 5529600 | `9223677b76ba2364ff18cdeec36c2eb52e1b857a912225008bd411031f384633` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### InstanceOptions1 (glist_demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `dbc5a9810aec76f2161c2b4d5d7f5dd45858764cbf604b06bb0e39dfc7f3f8ac` |
| demo.img.hdr | 534 | `b8fa78955759d15d64431b3faa682a763dc3a7f6eb958ed4037651e051b35e14` |
| demo_truth.img | 7987200 | `8192161bc673941bd554e1ceb0642a6a266a8b419e7e9f45a3f49d5c8cdc504b` |
| demo_truth.img.hdr | 483 | `a979d98bf92f77248be3c5f15407bae701b11a5433456fbb86d3abf556f13cff` |

### LeafStack1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 2457600 | `4684b1efbcb3f312cfd91290cd1b0cd4ed8dde735800448fdc3795e0b9a8cbbc` |
| demo.img.hdr | 579 | `bfcbe0410b9be694fab672868fc30bdde579dce94c68fb99b4082bf6f096b9aa` |
| demo_truth.img | 6144000 | `dcd04317de5b17e428bc63e79e39c1c83ea412b4d47b184303947d26fa045092` |
| demo_truth.img.hdr | 438 | `1b3039baf6841d65b81191901b954c37507289e1790c39fd2319d5c65401c5e8` |

### LemniscateScanMount1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `6a3a44c33ee1655d0c162f412569840a606217afb31a04be183813002d7fab00` |
| demo-t0000-c0000.img.hdr | 525 | `d5d1751a7446e4674af2c9e628b85abfd98b469c32f64221e1af24691207f24b` |
| demo_truth-t0000-c0000.img | 4300800 | `fa06537e580920a32378264800a3d24d367fa4d4eabfe82bc26652f784737757` |
| demo_truth-t0000-c0000.img.hdr | 368 | `e62d2f1056576a0b33f9fe7e250c4aa61ab60c8fbb06ef15ab637908ed8480a2` |

### LensDistortion1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `4d8d65ab9226980a4ee4d8efcd02de5ccc394c66f426a0409ee4ab887e1946f7` |
| demo.img.hdr | 530 | `c6ae07439c2c9111beb2ae57f9dd24a3905dcb0e95d2ebb06bbd28f245b664b7` |
| demo_truth.img | 4300800 | `17dfbb1b5a555128fa67a57a1de35e1bca6d36d1afc822ed70b1bc5e6c71d103` |
| demo_truth.img.hdr | 368 | `e62d2f1056576a0b33f9fe7e250c4aa61ab60c8fbb06ef15ab637908ed8480a2` |

### LidarBiStatic1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 4899972 | `dc4310de0927a6861e5d96d354241869c29b3b53e4a17b4075070d4451b5c982` |

### LidarBounces1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 39585237 | `fea7d9d1e3ef1960badffec18bda26d2f5feeea1fcc881b8dc2a3d9d4735a331` |
| lidar_truth.img | 2350080 | `a3bfb5ebe7e8de0c8585fb5b3177d9a001816d38674b94b077001750440d299f` |
| lidar_truth.img.hdr | 424 | `a8989798fe9ee8bb17fe2ebed278248aa152b27803af336b67a68b98141c773c` |

### LidarDynamicGate1 (dynamic_gate.jsim)

| File | Bytes | sha256 |
|---|---|---|
| dynamic_gate.bin | 285710729 | `f4ca50641908857ce2ab963cea67c4e49c1644410553802700a1cc100ecdfc17` |
| dynamic_gate_truth.img | 13629440 | `a12d2dd91d16e68884af75e1057e4dfb40c7fa34313f1d05ceef55be282534e3` |
| dynamic_gate_truth.img.hdr | 247 | `f006f90d1cd505302f64082b2e6ded4c3007378ae858cb7296f65910d3121899` |

### LidarEdge1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 2549 | `cf019236c56ee577e40b614348a2d969221d1cb8d24c155d1dda5ae0a0475f16` |
| demo_truth.img | 88 | `07cb9098e63c15c2225c570549005af22c2e367265db728cb103b6704354f47d` |
| demo_truth.img.hdr | 485 | `2b52eff291acf83da6b1f15c0e7b734666157f2bdd91ef9202895fc370e3264c` |

### LidarMultiStatic1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| rx1_demo.bin | 3339150 | `786692efc730b10acbf3046a3f70b5a75bc61112f4ff1098df735f5b62d88660` |
| rx1_truth.img | 2350080 | `684fead9b6ea1f49bb7fbf18a463df4dd242b0972f370c9262a0710584cc3a71` |
| rx1_truth.img.hdr | 424 | `a8989798fe9ee8bb17fe2ebed278248aa152b27803af336b67a68b98141c773c` |
| rx2_demo.bin | 3344766 | `a982190882b730149026281e286a60aaf3b46ee7b06a65c5bbaed44b336d0a75` |
| rx2_truth.img | 2350080 | `c41f6b0aa1428b08872aa0c0cf82043d428a0c05e20543ec054c3acbbe79047f` |
| rx2_truth.img.hdr | 424 | `a8989798fe9ee8bb17fe2ebed278248aa152b27803af336b67a68b98141c773c` |

### LidarPointing1 (with_jitter.sim)

| File | Bytes | sha256 |
|---|---|---|
| with_jitter.bin | 38351988 | `e7ae9924d00cd728f13f296532df8368b3dd8962d6cbb8c1191c3c25591fed46` |

### LidarRetro1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 215458 | `df956f2ebfca027f432e89b94d1ff41c391057f3871cd609caf0702610118054` |
| demo_truth.img | 171600 | `1d29ce572c67993208c42f6e515faefe3c6f01b3d19f84f786f89cccd5c9f979` |
| demo_truth.img.hdr | 436 | `9afde570779784d0f1463167b095d535339e871e1e7b4950ff09816cd26b19aa` |

### LidarSide1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 4432918 | `85ee24790f1faabd0cdc75066e5303ff6a75d90138308ab9a43a75b650297078` |
| demo_truth.img | 1827840 | `ec95ca05bcf606dc8b2936909988697bfa2cd7c98104ae8d23a932c0ea4d02ca` |
| demo_truth.img.hdr | 368 | `b23c8625ac618a771ab2a0bc72e1adc16d219c1ce769cf65018ede0bbae939cd` |

### LidarSide2 (multiple.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 8291014 | `3a21d1eec3cbfeeb6f81091def706de33ced18962a039f72423a9b6c000c5db7` |

### LidarSlope1 (flat.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 3580 | `e7475d5268cd539defb75a67c576d1e1d9b584cdf94add614d0a1fabe37758be` |
| demo_truth.img | 72 | `51d0e3c8817e166512e7071015156c3dade1a8d12a511e214c82b33ecf70f1b2` |
| demo_truth.img.hdr | 420 | `57ba9b8e25ce678badaccf9ac0f89c74cd00a59e398823e124da40ea0b8a3115` |

### LidarStatic1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 5662956 | `af6f4a409b93ff9ccdb23e678a9c45b592c4118f36bf11df252b670d308a9b21` |
| demo_truth.img | 522240 | `e7e4d1e1ace702a4f4e7079a8574e98ef2505ac237fa8c1b24b3000fcb7f071a` |
| demo_truth.img.hdr | 246 | `f9b45509180f61db6de3d291b48112b47cdadfb6b41ca2a0c2eb3c4b5644cbd5` |

### LidarStatic2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 1318612 | `99714f02246b57d48d06d911e684b3bafff6d0ec72e5d94ad1aa941d0aa225c4` |

### LidarUserBeam1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 12849587 | `b3844c16c321eec8ffd6d5be18aa0d16b635a8f33ad772020a64cefa8f0da196` |
| demo_truth.img | 9418752 | `26f07506e148d72c999c8e9d919a1f449074756a849f00b1e0619d8674c2c000` |
| demo_truth.img.hdr | 424 | `dae3db2d32ebc1398612dffb00f0cbef436d13424e119ac47ec0a4b885cb8b48` |

### LidarUserPulse1 (after_pulse.sim)

| File | Bytes | sha256 |
|---|---|---|
| after_pulse.bin | 92643 | `9700a5f364b5aa96925c4467367f2d027144d6b7d07e0e6ac8fecc6b7f7a6345` |

### LidarValidate1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 1651 | `0261a7bc7b2986b56ae23ce17e686df4cacbb120b4f0cc3e0e995f928b5288cb` |

### LidarWhisk1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 44800626 | `5c56a7f6977f020671c0c66bb1d56ffbf537d5a5e865ee43753d0942a0a54a87` |
| xyz_truth.img | 5108736 | `ee427b9e95a0cb3b3c07c343cbad884920ca64990606bc87ac93e139384fb24b` |
| xyz_truth.img.hdr | 296 | `1e0b3c0cb2fdac1e0ebdb4de0ff02f8e574a5040dfa2b0a81ddd69d8973e7b4f` |

### LidarWhisk2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 49653714 | `13357937cab8718cec57ba0fcd1418c5c73faa9d3f76762f085d0a103fdedd93` |

### LightCurve1 (box_spin.jsim)

| File | Bytes | sha256 |
|---|---|---|
| cube_000.img | 16040000 | `6c8e3e8d8565216f08ea016323c3540b2c3b9413b1e89f02fbe16353b56f002a` |
| cube_000.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| cube_001.img | 16040000 | `c1893cd73330ce88336225527d430442b7bc79cebcb754670a8ccd6e56c782bf` |
| cube_001.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| cube_002.img | 16040000 | `4eb9c8f8d8a2bdca79ca31732573890acf69529db25377e7a58c35773972f94b` |
| cube_002.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| cube_003.img | 16040000 | `114ba6b86c92a2b626e4d3824ce02dbc69cbd6bf4db23c149025a784a204bcfc` |
| cube_003.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| cube_004.img | 16040000 | `b86ae8ecabca075d9cd0d088e64fcfb9728502d997ada3593e20f63df46747fe` |
| cube_004.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| cube_005.img | 16040000 | `914883c39722427b3592ef5bea82b68c1047e11df33472c30d920059fa943e9c` |
| cube_005.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| cube_006.img | 16040000 | `914883c39722427b3592ef5bea82b68c1047e11df33472c30d920059fa943e9c` |
| cube_006.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| cube_007.img | 16040000 | `914883c39722427b3592ef5bea82b68c1047e11df33472c30d920059fa943e9c` |
| cube_007.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| cube_008.img | 16040000 | `914883c39722427b3592ef5bea82b68c1047e11df33472c30d920059fa943e9c` |
| cube_008.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| cube_009.img | 16040000 | `914883c39722427b3592ef5bea82b68c1047e11df33472c30d920059fa943e9c` |
| cube_009.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| cube_010.img | 16040000 | `914883c39722427b3592ef5bea82b68c1047e11df33472c30d920059fa943e9c` |
| cube_010.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| cube_011.img | 16040000 | `914883c39722427b3592ef5bea82b68c1047e11df33472c30d920059fa943e9c` |
| cube_011.img.hdr | 8911 | `f8f3c3cc49eb0e22828c6d412f5cd041dc758590505ef114ab5fc03394749664` |
| and 1657 more files | 13288551958 | listed in the results file |

### LineScanMount1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `cc7e835834e3522ce092d19cc4a0eaffc28838593b3b8a07c2b3e71bbc352c4a` |
| demo-t0000-c0000.img.hdr | 526 | `b78395511b03b80ddf20fc9afa3760f689bb41c7b3898963f80190b774c0bb75` |
| demo_truth-t0000-c0000.img | 4300800 | `ab9ae5e9fbabd2fd5f1dd2c2a78f9ceb42077fbe78bb163828f15ceb469c2b31` |
| demo_truth-t0000-c0000.img.hdr | 368 | `e62d2f1056576a0b33f9fe7e250c4aa61ab60c8fbb06ef15ab637908ed8480a2` |

### MacbethColorChecker1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| rgb.img | 7372800 | `ad555f185f1a6f3cb2de5f7f9a9ad3681d901e83130b236c291e5341c6d3c78c` |
| rgb.img.hdr | 583 | `52456575dc1b1e3b9dfd3a3b081a23862694a2582baf2caefe27963192f0f752` |
| rgb_truth.img | 4915200 | `271f4cf3bbf5c632e26337393a592350169fafa8d2f62e780365c5e097547700` |
| rgb_truth.img.hdr | 270 | `5a85053cd9f20ceb3123ae3a3709670e3664e5c27eae5d7bbc9b4d64e02ce362` |

### MappedTherm1 (map_therm.sim)

| File | Bytes | sha256 |
|---|---|---|
| map_therm.img | 3670016 | `bb968f3a318181158cff62d5f105752397a51437a4c205e42841f4afe09749ca` |
| map_therm.img.hdr | 599 | `ad561d90b2b63351af99b3c8081c1861d41d3d04436358b365a9da4c54ca3b35` |

### MaterialMap1 (w_mixing.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `e3af002344a905d52f37bc790f35b0583d73d682f6e18512955fedd60af29efc` |
| demo.img.hdr | 533 | `c2fa21cd69787999149cfe62411f05438c1460c21cc9f2c0e41b98ecd0e65741` |
| demo_truth.img | 6144000 | `44266bb5a144d70d21931075180c0e9fba18df1a787a28448f3f929fb74a5d38` |
| demo_truth.img.hdr | 441 | `44dfae38cfc25771b7c82b04c8e1981088f058026c933e6df572807f6a0d456f` |

### MaterialMap2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `f81c48c98d293d9b72c3f63504c5aeca5deb80c17ff181094213a8558c2b8223` |
| demo.img.hdr | 586 | `d38993eacee99c3ceb74731a9dae7d2d3d93ae5ba0155a21c8bf1885806a130d` |
| demo_truth.img | 5529600 | `5c28be9a96f012ca8893dd8ebf76b8ed09f5e8c9892774f660cf316c07fa60c5` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### MaterialOverrides1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1843200 | `9943fe5a674c91f786f900b4bfab99fb09601df817fa3b06797d3f79c54f95e7` |
| demo-t0000-c0000.img.hdr | 583 | `54bfae1535a2028ffb8a351e3f51d6a0e770ad1a90ce75106898bd1c28ee99e0` |
| demo_truth-t0000-c0000.img | 1228800 | `83d31f77f238cb7b75b4c1a2ff022039d43d6cf22a421973d4d47d4483e93e0c` |
| demo_truth-t0000-c0000.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |

### MicroBolometer1 (long_decay.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 153600 | `fed421cee237aec94577e4c7529aa1402a50bf00a61e8be6b76321fb9863fd1b` |
| demo-t0000-c0000.img.hdr | 514 | `bd447f577b611dfe1ac7629612ad7b9d48056835b35d88e0a13e2c7eb614beb9` |
| demo_truth-t0000-c0000.img | 6144000 | `502329a8067e7caadc4174b50a0b27194bcae3361f6c0c2d642010b0525b9c47` |
| demo_truth-t0000-c0000.img.hdr | 438 | `574d1916226a324a6e90e42db4ebf000ddac0023d69916c35ea30068e1b1b0f0` |

### MixtureMap1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `55932fb25994bb32ccaaeaf523dab7d289b57862a478bb01979a516bbfec3459` |
| demo.img.hdr | 556 | `b0a7bba00a7523c3625630485ff6941f10bbb0720ee3f10f9120146bd980de8e` |
| demo_truth.img | 5529600 | `ff5a66e168aa0f062d1ad59dca600d48ed417acbc8cbf7dab404c44c26dfb084` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### MoonSat2 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `b05154985b7829b704938c76a5922b4ff2663d9eb5a0e7496ad3afd1e0287e95` |
| demo-t0000-c0000.img.hdr | 538 | `5cb8ee37693569e94676f784c60ad52f3c23d5eb49fbecbc2a01be64e1cca177` |
| demo_truth-t0000-c0000.img | 16588800 | `d71c9095015a0fda48d4f0d21d85a0649b469fc5e22ae26ebe57d3687cfb3be1` |
| demo_truth-t0000-c0000.img.hdr | 779 | `97891094600c5cc4dea91ced8a37fa31eaed2e9d1d075cff6572b6bf00999692` |

### MultiCamera1 (multi.sim)

| File | Bytes | sha256 |
|---|---|---|
| camera1.img | 614400 | `5156bfdca6c530b3a576e94f94c406d48a755a693df8168bd582af0057bb6189` |
| camera1.img.hdr | 526 | `6f23819c50de6cda66f2e6d32217764dcb9ccf87f11dac41b5be1fdbb896f0c0` |
| camera1_truth.img | 5529600 | `0528765868d62015e9632fff0f44078b809aaa81e4d71842d8992ae7e1b958e1` |
| camera1_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |
| camera2.img | 614400 | `e45c9ed776c0fb40a05665926f8e0a800df1f77d89831d4871a1e8986979a8f4` |
| camera2.img.hdr | 526 | `21234bffa3d565ae26d9fc19ba9c38211eeae74a04c3ecd0b781ee385c3c461b` |
| camera2_truth.img | 5529600 | `6fe171af4907c480b9ed57e2615f160f975b27b343580d9223f0fa606296be5b` |
| camera2_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |
| camera3.img | 614400 | `78617893fb3898a4dfa08938efa0159e064183b4bed85f50577df582c666b9a4` |
| camera3.img.hdr | 526 | `13b03c467af4362599a081f32d42765caa181565d9b57c68528da33fa6abb59d` |
| camera3_truth.img | 5529600 | `14aaf2857aca0e60078666fc949efd262f429341907d7f6ef2e40b34d366dee9` |
| camera3_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |
| camera4.img | 614400 | `610d53143e84cb668a7576ac0cd7a387844644ff36f8ab4bb1ac2a96ae9fa59c` |
| camera4.img.hdr | 525 | `d6b6a3659dff73eb2b4ddd2d155263a0ecbcd35829fc0b5368151ab0d80d04d0` |
| camera4_truth.img | 5529600 | `014e2dba3a958434022deb67834aed5dd9d57a92c77d40197e4739dd5f2b432a` |
| camera4_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### Muses1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo_lwir.img | 614400 | `ec793d229e51664cd68e96dd057ad622e4f71143bd739d67f33b9c4690731ca6` |
| demo_lwir.img.hdr | 524 | `643b445a728af6644a15d8888f32a39ebbc1647e03cca946ef82d9d3b3ea90c4` |
| demo_lwir_truth.img | 614400 | `3f85f3f1e01efc21515ffbeceef389d5982d4f471b1957e46fc8af4d20cd4343` |
| demo_lwir_truth.img.hdr | 230 | `3f7a76edda6acca712d36b313e992c8732bea8cce077532b16bcb1d405abc89f` |
| demo_pan.img | 614400 | `522d6bddcd307afcbcfe8af39e5f37aa4a63f3bb144838e661e5599d73a5fccc` |
| demo_pan.img.hdr | 525 | `8d09a8695ec3568ef1baf0c6bf4fb7e8daf328615212105cb89dfe1ebe5b8924` |
| demo_pan_truth.img | 5529600 | `dea616ebadbb9eca9aabfc534021be564a1fa0724607c87ade4db464645d6d79` |
| demo_pan_truth.img.hdr | 424 | `1192db4f6743ff4c276c2ae2af2096c09869813b9465b29512487f6ea200356d` |

### NestedMotion1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `6064a6b902822384c43c5cb440d68b9db3132e6f2e8531b0d81c947f39557ec3` |
| demo-t0000-c0000.img.hdr | 523 | `d9ff04335cb5fe9b7efd4b77fe981a27959404f23c522cad4a161063c6d3ce8a` |
| demo_truth-t0000-c0000.img | 5529600 | `2705aa59ef9be8cc1e5c28a79d92690ef5329fa8ff1f4aeeba16e500acf1f4b8` |
| demo_truth-t0000-c0000.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### NormalMap1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `4cdd2ce50bf7d67c43cb14b5ca2dab6d446734518230c1404d35e88184e6a617` |
| demo-t0000-c0000.img.hdr | 533 | `5c311e10a4eb51df3c34d8eff7243ff2bcda13c519e9327f9af0242e38dfe41a` |
| demo_truth-t0000-c0000.img | 7372800 | `4f430c27e0ae4e2a136ed00d45709fcc0442d70c2efb09f8fc0b8e36f9fb5024` |
| demo_truth-t0000-c0000.img.hdr | 506 | `bf809b2a42a8515450a3a31b188e972f5729c6f9bb1b2526b6e28ad46954a1e1` |

### NormalMap2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 7372800 | `5aad23022db8fe7b8c08d0e610f809a53bb2f7c4175931ed957c011a6da440cd` |
| demo.img.hdr | 530 | `0ef810ddaf57d58b366e62818313c496baa24eb171cd3c69885b98a0883d660d` |

### NormalMap3 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 7372800 | `a52613ff4302d56f1263fe3a9e7436e6a273d4a9609738d5902b737975b89402` |
| demo.img.hdr | 615 | `5d815bef4da595cf1bf0ad2b84f2cc61a7404b34b2e02d535db4d8d66dea9c81` |
| demo_truth.img | 29491200 | `57b2bedce74ca91c03f37171c82f31e7a3c7005d070b7f739012fc0927a4e176` |
| demo_truth.img.hdr | 506 | `b23862f333df4758d78004fac2b0cfb21f7db28a71f6c7e2f940fef3d781965f` |

### Parking1 (demo_assimp.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `df772220fa4b684bd318f933bc5e4b3705d839473444f78087e3287bb305ef83` |
| demo.img.hdr | 586 | `35af87ac1f33a997d4750431b42bd6558193cf603c69eb47b7580d9467b62bc5` |
| demo_truth.img | 9216000 | `4260fe14abd4c6af8b874cbd9144aa557ba557cb4718b6ea314991198303a74a` |
| demo_truth.img.hdr | 515 | `be5a98737b33cb08992a1b4f201b46bdbf9d7e736a9fb7f6b0bad8a4fafd73b7` |

### Pilings1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 7372800 | `bcef2e7016a0cf6e31ab271304127834b77fd453831518d999e2ae9a8910d215` |
| demo.img.hdr | 559 | `56e1ceaf3840efbb8e5ccc1e82e1092eb3f3928943b0fa88f0c98a108bf537d5` |
| demo_truth.img | 22118400 | `08930894d74a112cfdc16c30435ba5a75415e9e8a126285a3dbcc546986e85c7` |
| demo_truth.img.hdr | 424 | `10f20bc8baa58650f3acdf5b79496ec8a7a97b63201b764fbe91b7e712a37bc2` |

### PlatformJitter1 (flex_single.sim)

| File | Bytes | sha256 |
|---|---|---|
| data_recorder.txt | 1054 | `ad256211152604eb0a62fffe5cfc41320969023b552a7e0f461664591da1599d` |
| demo-t0000-c0000.img | 614400 | `e160220291d304b25d8b8b14c11c0b99ec79f678a96e1cb869952b99399f0658` |
| demo-t0000-c0000.img.hdr | 525 | `c172d56fd54c98d98b1eb83e49a6af6d885d38c661babb54bcf55195da426418` |
| demo_truth.img | 5529600 | `453aed283be2d92a379f2f1c65273a776c219e19e9ae26a8812aac7ad7403916` |
| demo_truth.img.hdr | 424 | `1192db4f6743ff4c276c2ae2af2096c09869813b9465b29512487f6ea200356d` |

### PlatformJitter2 (flex_single.sim)

| File | Bytes | sha256 |
|---|---|---|
| data_recorder.txt | 1054 | `5601dd534b655b3ec8c1c743b0909b20d4d6329ebb8ac0d7314de1f2545a1474` |
| demo-t0000-c0000.img | 614400 | `a19a99bab952776d85f25ec305435273f77f89834614433e0f222140b7c9b310` |
| demo-t0000-c0000.img.hdr | 526 | `57b636a84704323fb6d82881900816f7837d43f68ed22e5f58f9a36b5a134c21` |
| demo_truth.img | 5529600 | `459e667dd09ce58b2b743571fcdfaa4a9317b8b234ef73728eb670fd84c429a3` |
| demo_truth.img.hdr | 424 | `1192db4f6743ff4c276c2ae2af2096c09869813b9465b29512487f6ea200356d` |

### PlumeOpenVDB1 (lwir_sf6.jsim)

| File | Bytes | sha256 |
|---|---|---|
| lwir_sf6.img | 33792000 | `3e28a05467f544cd67ea9c0a5d3c6d0b915380e06cb3aeaaf594913479dba37b` |
| lwir_sf6.img.hdr | 2521 | `d14d5ca7342073f4ab1d0d7dcc03ea51ce731c5047de0fd21b930cfe5b19b02f` |

### PointCollectors1 (framing.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 2097152 | `c4af584f04d6af468e066786f43b8143149b0f3db2cdada24a1aaa3f11a2fe3a` |
| demo.img.hdr | 529 | `b9b15f91426fa77923d4cf3d53f8a5b15051c113320adb696f05fd2281a9ad85` |
| demo_truth.img | 14680064 | `12699b4dea3dfbf62c2b27eb91f27dd9c80a07b3ddac40c4303e309376eefe95` |
| demo_truth.img.hdr | 368 | `f0b718e429191f9ac7b42eac720da31ae79f230270dff29aa03b1c41ea8609a1` |

### PointCollectors2 (framing.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 2097152 | `10699416f6d812b891534a71b630f534d8197d33c99fe0ef515e755e563d7962` |
| demo.img.hdr | 534 | `f16cb8680ab0d9cfd22f1c2e145960d1aece7b81102190cdb48c20f0e0a289f6` |
| demo_truth.img | 18874368 | `6dbf3513f653c648b225162f474a6c654637271c83446f5333cbe640b42cf096` |
| demo_truth.img.hdr | 420 | `eda4fa0fca4fd4228791aac5668e33b4ebb2a929c5f143a376ac4f515b8af0bd` |

### Polarization1 (nadir.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `c3f0f4410e4d1e276b1637357fc2adaf6b36ce56f3b34927de4e53b854d7d497` |
| demo.img.hdr | 534 | `6a825eb186b91f10e91809b308fb6cc0329c49d46655ff9dd4394dd5cb39b967` |
| demo_truth.img | 5529600 | `24b83c90122b35eeede28fd2f4e2d1a73731bafe03ce20c360039cd9e0065baf` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### Polarization4 (pi.sim)

| File | Bytes | sha256 |
|---|---|---|
| 000_degree.img | 202752 | `edf073194b1d18487b5a2e1dd612cd689d835043b69de4c80c9b91a850a7d4e2` |
| 000_degree.img.hdr | 533 | `6d8d3dc1204627878bb4fa0782a34135ed1a1752f371b6d108586afa056aa59c` |
| 045_degree.img | 202752 | `ec1b2b256bd8dff30e0bfa3edc6e3dc77c173062b11d1840034f8e8bc78bce73` |
| 045_degree.img.hdr | 534 | `80126a93115ebcb211374b2b4346cb67892f5af57292e82e6cbbf62d95129335` |
| 090_degree.img | 202752 | `74b82a4ebc59faccdd3c97d2b62c299cd89abfc00eeecf0c5d26bf1aaabeb2fb` |
| 090_degree.img.hdr | 533 | `95ed5fc9fb061d2a62830f43b19f460a9176427675f128ddc448a438b15c803d` |
| 135_degree.img | 202752 | `28f483644414db201b621afa59ae8274d7fe4ab6bc1d2789ae1b191c42b38a9d` |
| 135_degree.img.hdr | 533 | `bac13349e6f1b37615befb2f5cb6fe612706e99e02faa08531d76117815e11e8` |

### Polarization5 (pi.sim)

| File | Bytes | sha256 |
|---|---|---|
| pi.img | 202752 | `78519df81b0a9c5ca8e35803184946f5578a5283d28812ea951b7c223b8155e9` |
| pi.img.hdr | 493 | `f16ed2b8c91078b685017b73f3ff413db65d4c7f8ce6d61fb34aae7db4b6f284` |
| pi_truth.img | 1824768 | `13dd5244cdcf55b9b61e2565d564edeca347f9c937d671bf8ff3979406c04abe` |
| pi_truth.img.hdr | 424 | `71a2b631839769359c603df39ba0fe6ce993149db7c6285dd51adeb97e462305` |

### PolyFill1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `6d4364f346602a37456c6d815b5eafdbb4e9dad8d66ab808ad4c9a433cc443fd` |
| demo.img.hdr | 528 | `4efc8d0ad7d6f54a9a652431892418b476295828ae18ac8aae6510274459921f` |
| demo_truth.img | 5529600 | `fb4245918b4de9611be034d6b48c4a939923df25ccb21a5b97447c9f6e16060a` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### PrimitiveObjects1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `2325030b1617b13dd90021b9942d247377e56787da53e5b239aa44e2e3ef42bd` |
| demo.img.hdr | 526 | `5adce1f2176b759c0d5af5a1ff12137fb274583cf2ed687a20c8d8d6ad774174` |
| demo_truth.img | 4300800 | `55db6312e31279706ea01d4769face55348d3622a2120c52f19ecdaa53bb176f` |
| demo_truth.img.hdr | 368 | `e62d2f1056576a0b33f9fe7e250c4aa61ab60c8fbb06ef15ab637908ed8480a2` |

### PrimitiveObjects2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `4490b6f998d704f7948c3283a03e3026edcadc401776968fdbfdbe1ae596d624` |
| demo.img.hdr | 526 | `9f6d33ec44eb4911f9fd5e0c08ece1ae1c9a36fca5a2399ca894109054731f72` |
| demo_truth.img | 4915200 | `23c423926e41ac8507505e468ff2c88c0bb5b98ab3aa54deacacf2cc1e03d89a` |
| demo_truth.img.hdr | 381 | `735738cb5d63af7a75970cdfa0a220c48cc3178ee74683864d0280688939bee4` |

### ReflectanceMap1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 37478400 | `6ccf2e0333119b1c1f92bda5173869eeacdf59e55225f81784c8df512838c33e` |
| demo.img.hdr | 1654 | `da7e8f6277271a67c794c940dc956b2c88f6a7b39e8c9fb11504ac38ef44e0e3` |
| demo_truth.img | 5529600 | `bc96f673959ecce53f413e72e306a1b293b7f969a0dfd4e4f71abfec3b64a5e9` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### RegularGrid1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 84172800 | `2ec7c8e3d93cdf8194caf0c06352db2ec4c4098fec6b14e6c296f2ad3ae0e8b3` |
| demo.img.hdr | 2884 | `528ceddaad3af5283d9d7851b0e12b8852461b6c5910a2e1403a75cc942fc4f0` |
| demo_truth.img | 7372800 | `649551c9a315cdb74aca4c92cad3ba6f262927499134ec98bd61a08d587b932b` |
| demo_truth.img.hdr | 473 | `afcf356ffad4d14e9a7434ea7ed10869c8fcc2f443d04bea42781d7e502e87ab` |

### RollingShutter1 (global.sim)

| File | Bytes | sha256 |
|---|---|---|
| global_demo-t0000-c0000.img | 614400 | `168db4880f0c220fec606205f38e33d576967e6f146ac9c2ca8d0279ed18c2b6` |
| global_demo-t0000-c0000.img.hdr | 554 | `3bdc41bf47918519fcb2696ca21eedb5bd80a7b5b005d951cb346756b0bc067a` |
| global_demo_truth.img | 4300800 | `9672828356b0588f15ccda0b441a90f91e695c7537d7258eec5d4ea7f88f4273` |
| global_demo_truth.img.hdr | 368 | `e62d2f1056576a0b33f9fe7e250c4aa61ab60c8fbb06ef15ab637908ed8480a2` |

### RossLi1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 5529600 | `fb875b18cb631e511212c59153cecd986438819d8bc2f3b23e19a99f59324a8c` |
| demo.img.hdr | 699 | `28b4693520a9c28ff0c5e88c4e55f62464a0951cb47d42cdfa737a65b8df0cf5` |
| demo_truth.img | 4300800 | `2e9e7f58aa8545b604bd85329e0ae9fe7eed162e15283560678c88d1249c975a` |
| demo_truth.img.hdr | 368 | `e62d2f1056576a0b33f9fe7e250c4aa61ab60c8fbb06ef15ab637908ed8480a2` |

### SensorPosition1 (downlook.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `84cd65d33a08fd59a94b582b5c31cb276c987d14eea3732b168a094fc555f3c6` |
| demo.img.hdr | 528 | `dc67b110db2c83422cebdb6edf29e9268bb59b2c5b1b2570208509167ba28bf8` |
| truth.img | 6758400 | `0598d9d8fad9d8e7054b3e3c2806e7663c87cb772de7c2fbc08b5141b4306352` |
| truth.img.hdr | 457 | `8af917d61b11952e0e7bc9898152e7678534d1fa44cc3b04a51d817d6cf58d09` |

### Skyview1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 129638400 | `52bd71cf63526c22955f64ca09fd84e8700528dde589f68cf8485b50b56b19ff` |
| demo.img.hdr | 4599 | `96d3e9779104cc6c14f9dde79db2d22a080ad7d8f4950e85078d60ad863fbe17` |
| demo_truth.img | 5529600 | `030f66eee8fac7d999c5bdda9123bbc785f6d45765276257977ffb7804d8defb` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### Sources1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `852fab8124573ce59d4b513384f2e49755d98a99df0bf18695786bb1620e19c5` |
| demo.img.hdr | 586 | `2b840c73bea58b94cfce1d4464387028326ad53eebd3b9f4a6bceff16dbc4462` |
| demo_truth.img | 5529600 | `bb27a14a67a91cb430eb27a5d6b299bde29d0ca73da5685dfc41f2095193b95f` |
| demo_truth.img.hdr | 424 | `1192db4f6743ff4c276c2ae2af2096c09869813b9465b29512487f6ea200356d` |

### Sources3 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `29d622ae79422e77363acb4f76a46275734039d2b25584f238e5196f688e4f02` |
| demo-t0000-c0000.img.hdr | 529 | `d01e5ac3fe74af1cde72e8747cc9c3b444fc99d6fe368a4b51696f0303c49f7c` |

### Sources4 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f` |
| demo-t0000-c0000.img.hdr | 532 | `c26741b069fdd1d68d818892a06fc33945ec3bed7b99a99cd8bf43662603b48e` |

### Sources5 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `8d5886e6c81801f6972efdbfce7baac72dd3e63600b7d68355eef74e0aee8512` |
| demo.img.hdr | 527 | `aeaae7b736fa3203e567792121b88912e34a3475c82d2f60acd2642a8fd6a08b` |
| demo_truth.img | 5529600 | `da06dabf9e8aced162a435c7811682cd8ab6fbdf5e53d568d82a32e7dd4d22e4` |
| demo_truth.img.hdr | 424 | `1192db4f6743ff4c276c2ae2af2096c09869813b9465b29512487f6ea200356d` |

### Sources6 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1843200 | `e3b3fc9521386e98c14d443cc1ed1db07e44b17673eaf3645ab17e6bcc7c7a13` |
| demo-t0000-c0000.img.hdr | 554 | `72fe2445a5b29c5eddab3045a20587636e465778fa5d70739185d7d10d652748` |
| demo_truth.img | 5529600 | `5454643bd7aa8dd13d9e7f2bf05c98b374fafab25268157118278e3d9e4b6c22` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### SpaceRendezVous1 (lidar_rpo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 262998601 | `d3a6d885d98d0c52798461b04d90bd895761ed900bca68aa4d95e1e31e29c443` |
| lidar_truth.img | 96460800 | `abab018f2d6d959d32fdadc027a286dc4bbe2f547aef0371e768b3081e67dd42` |
| lidar_truth.img.hdr | 279 | `299a257eac963ee8e7af594c6d3e73866d932f755a544369d410a6c99fa8f1f3` |

### SphericalCollector1 (inbound_ortho.jsim)

| File | Bytes | sha256 |
|---|---|---|
| inbound_ortho.img | 20736000 | `6612b0a2364c1cacce0ca9e5a1b5762bb559d9938c69fbe9736b32da0d84ab11` |
| inbound_ortho.img.hdr | 369 | `c0fb8ceda026cc0897372f76595f8f3411cc0223f7a678dcb2e07092552fb255` |

### SphericalCollector2 (overhead.jsim)

| File | Bytes | sha256 |
|---|---|---|
| overhead.img | 10140000 | `e2259ce6384b5207d719a8964df8268a610151e8dcfb2feceab8dd4ea8eed25c` |
| overhead.img.hdr | 328 | `efac9973d1f78ae891a0f3b2cbd519b575bc469d1a9c37375d4b1c6f0aa3333c` |

### Ssa1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 2457600 | `2c8b616c6e6c408c28e5e8b6660d53cc359720e0d4f4a081b3d979cacc5bc7a8` |
| demo-t0000-c0000.img.hdr | 614 | `1112ed4e3c4d5f8f25034729e529dce93a85733ce33c66470f00f7c895d039b3` |
| demo_truth-t0000-c0000.img | 9830400 | `6f9bed32c94765443994f3160638dc0788668940e973c209df7530fefac2e83c` |
| demo_truth-t0000-c0000.img.hdr | 563 | `2038912b2cc9918a25a64d090a4467735ec4e9627b1a2b7a65eeda46e30ae96c` |

### Starfield1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 2457600 | `54f980b5b3be8ce80cb6490c527e38d681deade50f239f2cb7d23cf9d0108c37` |
| demo-t0000-c0000.img.hdr | 401 | `639a1304c432870e0da24926d4aeb7ad8af0e01616da8cdf34cb3104324cd1e1` |
| demo_truth-t0000-c0000.img | 7372800 | `0c0cf4338984e5cc9f7521c20ef1c3b3224a2a06bcee6d6edbb26ca2a6a96e92` |
| demo_truth-t0000-c0000.img.hdr | 650 | `e76bd019c7f4b23706da3f08faefc9bacff5a96d781791c2fad6fdd167b44a33` |

### StkImport1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| data_recorder.txt | 988 | `562c9dc0ec4890dabc2c05ed38011d96b38293eab678e6a9f7b01f10129374c7` |
| demo-t0000-c0000.img | 7372800 | `fc212e8ebf9210ce14a38f4196e6acfce484187398a3b5d803f37a4ab645b6c1` |
| demo-t0000-c0000.img.hdr | 583 | `e8a99a2f2148427c4aa003d0f94d3e4787fa2fa9006a6d0dff36d88dab0f3464` |
| demo_truth-t0000-c0000.img | 36864000 | `0001fcd368be20710079cdaf85ac0080a165f28b733f2a71c8ebb39240616f84` |
| demo_truth-t0000-c0000.img.hdr | 573 | `a3a352ec11cdb7f83ee1419bba1ab01af28529caf9014982e4319183fbb10e7f` |

### SubObjectMotion1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `df3295f196e6ac7c09c42414bc8606fb7470f355f27c9a76eee1ed94d26c7150` |
| demo-t0000-c0000.img.hdr | 529 | `2606958552e1e81875dd6aed11fb5c366bd8fd2c75ca22bc1545dccf01fd3512` |
| demo_truth-t0000-c0000.img | 5529600 | `bd5be1345b05a9a557d36aafe500125383cb04214f6b2b733c9f40939edf93ef` |
| demo_truth-t0000-c0000.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### SubObjectMotion2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `03852715230155f2a77a628ea77e256e62956d26ad4ba57a5874d332181a053c` |
| demo-t0000-c0000.img.hdr | 550 | `de3369c35409db395e8d59eb21165403cc512d44ac2445f1fb5dec113e442fd2` |
| demo_truth-t0000-c0000.img | 5529600 | `9da1b5c837d0ec74ab03bf4f5dcc742588b9463bd43c35201aac0b6237c642e3` |
| demo_truth-t0000-c0000.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### SubPixelObject1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 24576 | `0f955bb6462ac561fdfb1f6109959b100c526d82fd47997808fc3c955516d198` |
| demo.img.hdr | 526 | `63b6f3d45ecf59251c0244067ff31a0eee68c76372cd1a97905324cc3e7ceac4` |
| demo_truth.img | 294912 | `0df6bada566057510a3833e2a04b48638bcaad87ecff18078a9cc6e5c8200be9` |
| demo_truth.img.hdr | 500 | `07aa46832ef3d587d7b5642ca24681666fcdbd9f69c46e56e56758b9b29a0dc8` |

### SubPixelObject2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| hyper_demo-t0000-c0000.img | 614400 | `0e359b043904e29429bbd44686fd475048736201c6950a220501e8b45bbeaebf` |
| hyper_demo-t0000-c0000.img.hdr | 549 | `2410d6bb37cf6f297d77a0a80e5a71d6d1478072b62e775b04531c9df03a7da2` |
| hyper_demo_truth-t0000-c0000.img | 6758400 | `dc3d93edbc98f557577a520a7d3cedcfa92e73bfa2fffb79ae02145c3da03787` |
| hyper_demo_truth-t0000-c0000.img.hdr | 454 | `775477d4d282ed1669e5592a31590d4b69343f4e70cb211c1535c810dbfadd9c` |

### SumoTraffic1 (multi_scene.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 5379200 | `c73a9b9d938c8abd7ee63937cf464a82b46431ca102b5e0f6b1492749666c7d4` |
| demo-t0000-c0000.img.hdr | 526 | `cbcdfab74765df2a6444aadfd8485e9d68926492672893f11aa9551798ae36be` |
| demo_truth-t0000-c0000.img | 5379200 | `02068ae237a08ebc9ad802b48fe7afd051a817719f4a60846904b1c8fdf5e8e9` |
| demo_truth-t0000-c0000.img.hdr | 248 | `4e1c8755511dfaa74cbeb3fc92665725dc44a5a616147bb028872160d2d06eb5` |

### TabulatedMount1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| data_recorder_ext.txt | 1043 | `c9a1592f0f9c3099df37685a32f554f934e4e266c6f0939e081047a93afc8a8e` |
| data_recorder_int.txt | 1043 | `1e79e59cd8a69f6c10277289f07a4af135c512007cc7ffe84961418925b923d1` |
| demo-t0000-c0000.img | 614400 | `0263b9ec1b2689324be5386eac9ad219d2bcd57aea168fc941a6fe0b86bf1777` |
| demo-t0000-c0000.img.hdr | 527 | `1fbeaded47707b58677c0fbb5a680383061f6f2e49add6d6f90f7a760d549245` |
| demo_truth-t0000-c0000.img | 5529600 | `6e05949361ece9cbe6b8615a353620da507665ac00334fdd2f35fb63b91be496` |
| demo_truth-t0000-c0000.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### TabulatedMount2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| data_recorder_ext.txt | 1042 | `650e3be902cc75f48e9a5e796e7f199db11c8fb670fc718e75857a2f22d492f7` |
| data_recorder_int.txt | 1042 | `bdbd44a4a5c3e851b7413f8b909ba84c73458029a05457a8a90d40dff86133ed` |
| demo-t0000-c0000.img | 614400 | `bce71635c8a16c7ffcffbdd45cac99e644e0591977204589e6fc883d624ee55b` |
| demo-t0000-c0000.img.hdr | 526 | `60ef4974b6f22f036a11c64559d9cc79265b8facc659aba8489d4984c14c910b` |
| demo_truth-t0000-c0000.img | 5529600 | `c519b28b908b0a8c0642306d3fb623e01684a2a11bd04b2e7e462e506950ef29` |
| demo_truth-t0000-c0000.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### Telecentricity1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 2150400 | `8641eb5f0f440903db93a4be3566157ab6e0c65d3d841a12f287ea673e645fb6` |
| demo.img.hdr | 588 | `8d50fede070e3e7af8695d74e36fe142117f48ecb667c8bbfa3890ea1648ef5d` |
| demo_truth.img | 7168000 | `63074ce19994648b881ac42e92c8db3badac0b897cf92e55c1dfa1acb40d4e36` |
| demo_truth.img.hdr | 438 | `a68c7bc9faa9bd40c3a0f33cacd30d7d42a612f26cc8ed6e7e16edb01ed9c1be` |

### TemperatureMap1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `f5919f842210dcce6fbaec4e34b717c798118476bfa1c737d0a90980733f4d54` |
| demo-t0000-c0000.img.hdr | 530 | `231ba6c1f07532edce8ee3866d674ee5ecb61302f14ddc358d7b7daa6cab476e` |
| demo_truth.img | 6144000 | `1b1abe5c14ca29182646f75a030bf9161642f81b99fbcf64b23fa8e347a9a2cb` |
| demo_truth.img.hdr | 441 | `44dfae38cfc25771b7c82b04c8e1981088f058026c933e6df572807f6a0d456f` |

### TemporalIntegration1 (blur_off.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `d9d07f8cab256fe4f228b70e6393d6166a98394312e2a82a8e953cf65511a87c` |
| demo.img.hdr | 586 | `ab46b55175dc1d44a2578195f3f9785055fb17dd3c5deb156e0731b778ca1b79` |

### TemporalIntegration2 (blur_off.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 1843200 | `d9d07f8cab256fe4f228b70e6393d6166a98394312e2a82a8e953cf65511a87c` |
| demo.img.hdr | 586 | `ab46b55175dc1d44a2578195f3f9785055fb17dd3c5deb156e0731b778ca1b79` |

### Thermal2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `1ff844d16c536da8ff3f572c0da35b6372628aed8250c39b30b52cfab31d4c20` |
| demo-t0000-c0000.img.hdr | 530 | `231ba6c1f07532edce8ee3866d674ee5ecb61302f14ddc358d7b7daa6cab476e` |
| demo-t0000-c0001.img | 614400 | `4710037c5bab0d31c09e28a6847adee22ba432c2c5478cb0a10e7ecda3f4f670` |
| demo-t0000-c0001.img.hdr | 529 | `a39d3bf64950a8e2df32f0600b92e553b41be8fae1568eca23dab042a69e52ae` |
| demo-t0000-c0002.img | 614400 | `783195ab84c2b3629b4efd96513dfefe812a0d68c8dc2ec037c672856b69bfbd` |
| demo-t0000-c0002.img.hdr | 530 | `601765c2fa3ed66ae853cf9c753fe521f99e5a2e64adb71ac59c119883b3b8e3` |
| demo-t0000-c0003.img | 614400 | `544e8c160368fd5edf1dbffaaa61e1d7d559fddafb92d17695c10812887e7141` |
| demo-t0000-c0003.img.hdr | 529 | `7377b90d1427c8c39520fde7795fde919519686bf9796fab60c14898dc03fb0e` |
| demo-t0000-c0004.img | 614400 | `7d77ec5d1192a36304789d830cddbc7995b7989bd2739be46306fd744591278e` |
| demo-t0000-c0004.img.hdr | 530 | `2dea97a11623b79b38f6729844b860a98f4458e0b70770752d72c1c497139487` |
| demo_truth-t0000-c0000.img | 6144000 | `3b9b86512e8303aa9f65c8ba4ca05ace2fb8ea8877e7a41c5cf595c69d965e47` |
| demo_truth-t0000-c0000.img.hdr | 441 | `44dfae38cfc25771b7c82b04c8e1981088f058026c933e6df572807f6a0d456f` |
| demo_truth-t0000-c0001.img | 6144000 | `896b5b5aa94f41ea33b3d350c19422c1fd384843c76d91b8551b570eb3219b1b` |
| demo_truth-t0000-c0001.img.hdr | 441 | `44dfae38cfc25771b7c82b04c8e1981088f058026c933e6df572807f6a0d456f` |
| demo_truth-t0000-c0002.img | 6144000 | `77e66dad6f00ff70d9111163274ce015237710a5a273fc44d3c0c99307914a5d` |
| demo_truth-t0000-c0002.img.hdr | 441 | `44dfae38cfc25771b7c82b04c8e1981088f058026c933e6df572807f6a0d456f` |
| demo_truth-t0000-c0003.img | 6144000 | `470e5bac5c61ec94b236b08399be1d698dfec29b2a2c54b305ad5c545ec06a50` |
| demo_truth-t0000-c0003.img.hdr | 441 | `44dfae38cfc25771b7c82b04c8e1981088f058026c933e6df572807f6a0d456f` |
| demo_truth-t0000-c0004.img | 6144000 | `accde0dc14ab04b2ba058b1944dc6d49cd09ac14f2df5974d06e3211a9f2f1f0` |
| demo_truth-t0000-c0004.img.hdr | 441 | `44dfae38cfc25771b7c82b04c8e1981088f058026c933e6df572807f6a0d456f` |

### Thermal3 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `6c12b5f2e7db1ccb636671829d8d52e42ab16a5cd7afb87c38e094d24c859748` |
| demo-t0000-c0000.img.hdr | 540 | `e0ca8181914a7b75d9365b1b159ab1f46027aae75c6b014423ce52fef3f6f1d0` |
| hit_truth-t0000-c0000.img | 4300800 | `dcd855bce80f1f09194c21b86258bf7c4533fc2b554662252eb61d9299f1e724` |
| hit_truth-t0000-c0000.img.hdr | 368 | `e62d2f1056576a0b33f9fe7e250c4aa61ab60c8fbb06ef15ab637908ed8480a2` |
| mat_truth-t0000-c0000.img | 1228800 | `d18e7c5c0393a60e91312432d4a38c03c3e240a8360b7e3c1d09d75430da640b` |
| mat_truth-t0000-c0000.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| temp_truth-t0000-c0000.img | 614400 | `006b2b21eeefa997524700b48d1f53da104d5f09deacd16d8b5db77e269ddbc3` |
| temp_truth-t0000-c0000.img.hdr | 230 | `3f7a76edda6acca712d36b313e992c8732bea8cce077532b16bcb1d405abc89f` |

### TimeDelayedIntegration1 (long_int.jsim)

| File | Bytes | sha256 |
|---|---|---|
| long_int.img | 250500 | `63a4ee7a6bb1ae8566060474e8ac22a0ad449884fdc9c75bc6135a78215b5527` |
| long_int.img.hdr | 545 | `034e605520c55f86ab31fc351e0f9d20cb5636d1fa2dfc1aac99e1df62d5be1e` |
| long_int_truth.img | 10020000 | `3faebdaf5aee13195c666e774e2c705e96ceb5625fa0c7ea9ddc9b886a94d543` |
| long_int_truth.img.hdr | 438 | `191d36776fdf304e1b8e1059cf6a88fd9b152f8d516a242ff9da39a4320cdf37` |

### TrackingMount1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `a99466fc311c4c4450b50d93da35622f15c2d67937135d089d0739503dc9d031` |
| demo-t0000-c0000.img.hdr | 529 | `a58b9c3df6ded2c59beb3e5d12e1036c5b055b1ad9de318e45c5460eada8d6cb` |
| demo_truth-t0000-c0000.img | 5529600 | `dedd5e7d56be34a90ff2832abae9ff49e8a4f3dc28047235ce66718bf5322cdd` |
| demo_truth-t0000-c0000.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### TrafficLights1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1843200 | `f663c326d429b48a748052dddb4498d06f0f6a8c9a7a040ede5013c56b1d1857` |
| demo-t0000-c0000.img.hdr | 586 | `b8c1126a7dd7c85333c07df5b3d4229431e876fabd768efb6a15e64a27f63947` |
| demo-t0000-c0001.img | 1843200 | `5dc4c75dd8d9c41f1dfda4d1ccc1253d8e2892094d94ecbccfe0e59a94c587f2` |
| demo-t0000-c0001.img.hdr | 585 | `9d9532942d130d3669ff8f615aa30e693531b295a9426679993adfbb2bd91b34` |
| demo-t0000-c0002.img | 1843200 | `7bd59546d345273a0f9d5e607de4f48ce0b3adb364452fbc7440e44e9557f387` |
| demo-t0000-c0002.img.hdr | 586 | `5aa3660aa7f45dda6330e3ab5047f15678a1759ec7a42bc64e388c40e0746f7f` |
| demo-t0000-c0003.img | 1843200 | `aa634f20014958396fd1d6ed7701d65584d8e18e73867535b5c3953184e69012` |
| demo-t0000-c0003.img.hdr | 584 | `eba77ec18e9b5860211508eb5e39a3f5b490c5cf1de1cc27d8774a12e4a43616` |
| demo-t0000-c0004.img | 1843200 | `526948cdf0457245c9b10975c6cf3fceaac5dd8cd8e0296a1d73443b504e5b93` |
| demo-t0000-c0004.img.hdr | 585 | `b6fb70fc86be05a7854ae851769346f581eb32fa4026ce60e91242ebb87017ab` |
| demo-t0000-c0005.img | 1843200 | `fd7282909482f715065a667c5f964ccb0f24085dab712d8404d97f0a8a89a800` |
| demo-t0000-c0005.img.hdr | 584 | `b65f06c7fa49dacbcaa5b36d9ae812efa0380202ca9738c26f0f2861381a36ef` |
| demo-t0000-c0006.img | 1843200 | `712afc685ecc0c5aff2be98d20a6fee704e7cd429c11e400bb56537d460e5936` |
| demo-t0000-c0006.img.hdr | 585 | `2c5350cbd4ee9e7bff73cce0b4f1a31142ca3dc0038948662f7163020741ce29` |
| demo-t0000-c0007.img | 1843200 | `1ce9b3c8efd172bd1d717b5a605cbec3826c3f956c40846635868f6c19ebf043` |
| demo-t0000-c0007.img.hdr | 584 | `078d92ff7d6b639a2eec6ed1e24da909a4587103f65553317582b1f7b9458965` |
| demo-t0000-c0008.img | 1843200 | `f1b0f9dcbb9373d0d27547c7129f6d81671f0ba91933ca84ca5e4eaed0fea319` |
| demo-t0000-c0008.img.hdr | 586 | `d43bb55ffd5edf9a79dcee8c8eefbcb6483a472e55acf387814c1df9d93b81ca` |
| demo-t0000-c0009.img | 1843200 | `4fdf8509bf1b87215c13e224aaa3c328e82df675de7e3ef475a0b93bfb081409` |
| demo-t0000-c0009.img.hdr | 586 | `05e10cdb201e3caf0b66cbea2200f75298d2589fa93ea5593478ee5151440c44` |
| demo-t0000-c0010.img | 1843200 | `809a9613c3ddb31337f3617e793d6acffe0abe76a4e094b1f3d4f01b00594ed9` |
| demo-t0000-c0010.img.hdr | 586 | `026210ce98aaf2317d22eb5463a84963999fe82c3a811054bc396690197c6c89` |
| demo-t0000-c0011.img | 1843200 | `8ed290fa24769641ca2b6704469d5b0d353c56a8603a44630eff547a6fd26591` |
| demo-t0000-c0011.img.hdr | 586 | `2fd43ccac42c4110fe8c5a3bc26b7b40f7032bbae1275a8aa3dde5302d960b49` |
| and 158 more files | 145659019 | listed in the results file |

### TriBar1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 2457600 | `fcbcbbb53c15e824c65680224c16701bb1246f9e3c5fbb4b1de25d49e314ed2b` |
| demo.img.hdr | 534 | `a9c5c815177caa4f128c3b8289e256e2884951bb6442c97ce34d872295d886a3` |
| demo_truth.img | 22118400 | `7a5c7612852968e45a70be4b89c545470b5b443356b03137816c63409de4edfc` |
| demo_truth.img.hdr | 424 | `10f20bc8baa58650f3acdf5b79496ec8a7a97b63201b764fbe91b7e712a37bc2` |

### UvMapping1 (drape_map.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `e0de69dd81c57ffc6f1bb7705ba0f3d25090413af084c79dc95cf7e9cdf41521` |
| demo-t0000-c0000.img.hdr | 529 | `59671ad00a082f8b4342a07d7781925f1e88c5ce74b612e3bd5c79c71806672e` |
| demo_truth.img | 5529600 | `4e210c69ad155d82927616127266fdeb71cbf93a01d69a94b123f452dbcea309` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### UvMapping2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `c7fe93ee39e250507cdbbcac70a1dbb784f9de878cd8d35bf8956cf8434e62d3` |
| demo.img.hdr | 528 | `e6f6cdb4ec6e62a98d729f999e2af5aecd7da4e86f7ab2434ae1496db29c1c42` |
| demo_truth.img | 5529600 | `090bf55197bb0403316f176fe231c84f757445f9a68d85f7d56476185a9e2790` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### VertexNormals1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `4ac997322f4243987a5e08a4af5c6a1274eb6d65a70e1b2a63cd552b8895d307` |
| demo.img.hdr | 525 | `800311a475ddf1d7826d766b887bf3c4ed50b367c96c028975e80ad72507dd83` |
| demo_truth.img | 4300800 | `d45d428ab7e7da33f8cedf9ed90b3eed6a5e1acb7e81194bc59c000180ff722c` |
| demo_truth.img.hdr | 368 | `e62d2f1056576a0b33f9fe7e250c4aa61ab60c8fbb06ef15ab637908ed8480a2` |

### VertexNormals2 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `1282745316509d1c964259ab6943e97000a3e1cb2fe5494808b402cfc9846f82` |
| demo-t0000-c0000.img.hdr | 526 | `9f5c68212e019ae463ece9a6ef0b1d6bc9bf8eb379eda6c6824336231afbc53d` |
| demo_truth.img | 4915200 | `45b981f09a5af78d0d4e6c9c3ce03169403ecee691657b8ae86724b1dd1422d1` |
| demo_truth.img.hdr | 381 | `735738cb5d63af7a75970cdfa0a220c48cc3178ee74683864d0280688939bee4` |

### WeatherPlugins1 (nsrdb_weather.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `06aaf90300b3143cc52691c56f3d16ead490903905440ac3ecf9d8f9f8f3768d` |
| demo.img.hdr | 527 | `fa000c2f6f98314060bffb9f4535a61c0c9c157838952cfb761f6a20cbf02344` |
| demo_truth.img | 614400 | `ff6441e7cb8eabca4b09ddc41be99c38b4a4250fe23e36970474f7e68d9cfeed` |
| demo_truth.img.hdr | 230 | `3f7a76edda6acca712d36b313e992c8732bea8cce077532b16bcb1d405abc89f` |

### WhiskScanMount1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `0b3c7de0a755a68f9eef5d2ce32a3b3288733a41a22967b9978b2f5784329949` |
| demo-t0000-c0000.img.hdr | 526 | `07c6e29ded18373d1184f76c1c7a2d26c859f947be550be76f2357f623eaea26` |
| demo_truth-t0000-c0000.img | 4300800 | `bdcf2e69c5fa5ff936c678358935a270705103cc42c9523287e58022020a748f` |
| demo_truth-t0000-c0000.img.hdr | 368 | `e62d2f1056576a0b33f9fe7e250c4aa61ab60c8fbb06ef15ab637908ed8480a2` |


<!-- sweep_demos: end -->

<!-- summarize_sweep: analysis, generated between these markers by scripts/summarize_sweep.py; edit outside them -->

## Analysis

### Outcomes

152 demos, 282 attempts (126 of them repeats). The sweep ended: candidates exhausted.

| Outcome | Demos |
|---|---|
| rendered | 131 |
| failed | 16 |
| skipped: dirsig4 | 3 |
| skipped: duplicate name | 1 |
| timeout | 1 |

### Failures by first error line

Every failed or timed-out attempt, grouped by the first `worker.log` line matching the sweep's error pattern (7 groups; the 15 largest shown). DIRSIG usually prints a bare `[error] Error!` first, so each attempt also shows the message after it and the file, database, variable or tool the error names.

| First error line | Attempts | Demo (simulation): DIRSIG message | Names |
|---|---|---|---|
| [error] Error! | 10 | FastCloud1 (demo.sim): Line 5: unrecognized base geometry <atmospherics>; InstanceOptions1 (binary_demo.sim): [error]   ... while loading geometry list file "bin_instances.glist"; ModularCity1 (demo.jsim): Filesystem error: cannot make canonical path: No such file or directory [city1.scene]; Polarization2 (sphere.sim): However, the scene only has spectral coverage over 0.350-2.550um; Polarization3 (texture.sim): Texture maps are only supported on ClassicEmissivity materials; ReflectanceInversion1 (grass.sim): Path "test2.mat" is not a file!; ReflectanceInversion1 (gray.sim): Path "test1.mat" is not a file!; SpatialResponse1 (checkers.sim): EULAs are available in: 'eula.html'; SpotlightSar1 (demo.sim): Cannot load material ID '100': unsupported reflectance type: SarReflectivity; StripmapSar1 (demo.sim): Cannot load material ID '100': unsupported reflectance type: SarReflectivity | file city1.scene, variable DIRSIG_ODB |
| [error] Unable to load atmospheric database! | 7 | CloudOpenVdb1 (demo_ppd.jsim): Unable to initialize atmosphere plugin!; CloudOpenVdb1 (demo_static.jsim): Unable to initialize atmosphere plugin!; Cloudview1 (demo.jsim): Unable to initialize atmosphere plugin!; EarthClouds1 (demo_advanced.jsim): Unable to initialize atmosphere plugin!; Refraction1 (new_atm_merged.jsim): Unable to initialize atmosphere plugin!; Refraction1 (new_atm_mod6_json.jsim): Unable to initialize atmosphere plugin!; Refraction1 (new_atm_mod6_tape.jsim): Unable to initialize atmosphere plugin! | database dynamic_mls_rural_23km_isaac.adb.hdf, database mls_rural_23km.adb.hdf, database mls_rural_23km_merged.adb.hdf, database mls_rural_23km_mod6_json.adb.hdf, database mls_rural_23km_mod6_tape.adb.hdf, database static_mls_rural_23km_isaac.adb.hdf |
| (no matching line; timeout) | 2 | FocusDistance1 (demo.jsim): timed out after 1800.8 s (capped timeout 1800.0 s), cancelled; SumoTraffic1 (multi_frame.sim): timed out after 1800.3 s (capped timeout 1800.0 s), cancelled | - |
| [error] BasicAtmosphere::init: ERROR! | 2 | Refraction1 (classic_atm.sim): Unable to initialize atmosphere plugin!; Thermal1 (demo.sim): Unable to initialize atmosphere plugin! | file classic_mls_rural_23km.adb, file mls.adb |
| [error] while reading platform file './demo.platform': | 2 | Blackadar1 (demo.sim): Unsupported 'spectralunits' in <bandpass>!; ScriptMount1 (demo.sim): ModelImport::readMount: The 'scripted' mount is not supported (yet) | - |
| [error] Missing/Unknown environment variable: 'MUSES_EXE' | 1 | Muses2 (demo.jsim): Unable to setup 'Muses' plugin! | environment variable MUSES_EXE |
| [error] NewAtmosphere::updateState: | 1 | HdfWater1 (demo.jsim): Unable to update atmosphere plugin with current state! | - |

### Cost

Wall time of the 131 rendered demos (the rendering attempt, first run): median 12.1 s, 90th percentile 160.3 s, maximum 705.5 s; total 2.07 h. Wall time of every attempt, repeats included: 4.40 h.

The 10 most expensive rendered demos:

| Demo | Simulation | Wall time (s) | Outputs | Output (MB) |
|---|---|---|---|---|
| SpaceRendezVous1 | lidar_rpo.jsim | 705.5 | 3 | 359.46 |
| LightCurve1 | box_spin.jsim | 691.9 | 1681 | 13481.14 |
| Ssa1 | demo.sim | 629.4 | 4 | 12.29 |
| ChipMaker3 | demo.jsim | 424.8 | 60 | 36.90 |
| Polarization1 | nadir.sim | 310.6 | 4 | 6.14 |
| LidarDynamicGate1 | dynamic_gate.jsim | 270.6 | 3 | 299.34 |
| Polarization4 | pi.sim | 244.3 | 8 | 0.81 |
| Polarization5 | pi.sim | 230.4 | 4 | 2.03 |
| ChipMaker1 | demo.sim | 212.3 | 4 | 14.75 |
| Brdf1 | demo.sim | 204.3 | 4 | 3.69 |

Output size per rendered demo: median 7.37 MB, maximum 13481.14 MB.

| Output size | Demos |
|---|---|
| under 1 MB | 9 |
| 1 to 10 MB | 73 |
| 10 to 100 MB | 39 |
| 100 MB to 1 GB | 9 |
| 1 GB or more | 1 |

### Determinism

Every demo that rendered in under 300 s was rendered again in a fresh work root, with DIRSIG's default seed (no `--random_seed`). Identical outputs: 82 of 125 repeated demos (66 percent). Not repeated: ChipMaker3 (not tested), EarthMap1 (repeat failed), LightCurve1 (not tested), Polarization1 (not tested), SpaceRendezVous1 (not tested), Ssa1 (not tested).

| Outputs that differ | Demos |
|---|---|
| lidar .bin only | LidarBiStatic1, LidarBounces1, LidarDynamicGate1, LidarEdge1, LidarMultiStatic1, LidarPointing1, LidarRetro1, LidarSide1, LidarSide2, LidarSlope1, LidarStatic1, LidarStatic2, LidarUserBeam1, LidarUserPulse1, LidarValidate1, LidarWhisk1, LidarWhisk2 |
| radiance images (with or without others) | FlexMotion1, GlistPopulations1, MaterialOverrides1, MicroBolometer1, NestedMotion1, Parking1, RegularGrid1, Sources3, SubPixelObject2, TabulatedMount1, TabulatedMount2, Thermal3, TimeDelayedIntegration1, TrackingMount1 |
| truth images only | Brdf3, BundledObject1, BundledObject2, ChipMaker2, CommandedMount1, CommandedMount2, GeoLocation1, MoonSat2, Sources6 |
| data recorder text only | PlatformJitter1, PlatformJitter2, StkImport1 |

### Thermal and cache

Maximum CPU temperature per attempt (the maximum over the host's thermal zones): median 94.0 C, highest 99.0 C; 234 of 282 attempts reached 90 C and are flagged `throttle_suspect`, across 128 demos: AnimatedObject1, BackgroundSky1, Balfour1, Balfour2, BayerPattern1, Brdf1, Brdf2, Brdf3, BumpMap1, BumpMap2, BundledMaterials1, BundledObject1, BundledObject2, Caustics1, ChipMaker1, ChipMaker2, ChipMaker3, ColorFilterArray1, CommandedMount1, CommandedMount2, CurveMap1, DataDrivenArray2, DataDrivenTempSolver1, DecalMap1, DeltaMotion1, DensityMap1, EarthClouds1, EarthMap1, EarthShine1, Eclipse1, ExternalTriggers1, ExtinctionProp1, Fireball1, FlexMotion1, FocusDistance1, FourCurveAtm1, GenericMotion1, GeoLocation1, GlistPopulations1, IESSources1, Indoors1, InstanceOptions1, LeafStack1, LemniscateScanMount1, LensDistortion1, LidarBounces1, LidarDynamicGate1, LidarEdge1, LidarMultiStatic1, LidarPointing1, LidarSide2, LidarStatic2, LidarUserBeam1, LidarUserPulse1, LidarWhisk2, LightCurve1, LineScanMount1, MacbethColorChecker1, MappedTherm1, MaterialMap1, MaterialMap2, MaterialOverrides1, MicroBolometer1, MixtureMap1, ModularCity1, MoonSat2, MultiCamera1, Muses1, Muses2, NestedMotion1, NormalMap1, NormalMap2, NormalMap3, Parking1, Pilings1, PlatformJitter1, PlatformJitter2, PlumeOpenVDB1, PointCollectors1, PointCollectors2, Polarization1, Polarization2, Polarization4, Polarization5, PolyFill1, PrimitiveObjects1, PrimitiveObjects2, ReflectanceInversion1, ReflectanceMap1, RegularGrid1, RollingShutter1, RossLi1, SensorPosition1, Skyview1, Sources1, Sources3, Sources4, Sources5, Sources6, SpaceRendezVous1, SphericalCollector1, SphericalCollector2, Ssa1, Starfield1, StkImport1, SubObjectMotion1, SubObjectMotion2, SubPixelObject1, SubPixelObject2, SumoTraffic1, TabulatedMount1, TabulatedMount2, Telecentricity1, TemperatureMap1, TemporalIntegration1, TemporalIntegration2, Thermal2, Thermal3, TimeDelayedIntegration1, TrackingMount1, TrafficLights1, TriBar1, UvMapping1, UvMapping2, VertexNormals1, VertexNormals2, WeatherPlugins1, WhiskScanMount1.

Cache: every attempt ran with a per-run `HOME`, so DIRSIG's material caches started cold and the user's cache was not an input. 23 first attempts wrote cache files into their per-run home (73 files, 47.85 MB): Brdf1, Brdf3, BundledObject1, BundledObject2, ChipMaker1, ChipMaker2, ChipMaker3, FourCurveAtm1, GlistPopulations1, LightCurve1, MaterialMap2, Muses1, Parking1, Polarization1, Polarization2, Polarization4, Polarization5, RossLi1, Sources6, Ssa1, Starfield1, SubPixelObject2, VertexNormals2. A cold-versus-warm comparison does not apply.

### Layered-comparison candidates

The survey marks 42 demos `near` (one loader feature away) and 68 `ready` (none missing). 96 of them now have a pass-through reference; ranked by its cost, they are the candidates for a layered re-expression and comparison (a `ready` demo's missing feature is "none").

| Rank | Demo | Simulation | Reference wall time (s) | Deterministic | Missing feature (survey) |
|---|---|---|---|---|---|
| 1 | ColorFilterArray1 | bayer.sim | 4.0 | yes | none |
| 2 | DeltaMotion1 | demo.sim | 4.0 | yes | none |
| 3 | Balfour1 | demo.sim | 4.1 | yes | BasicAtmosphere .atm (classicradiativetransfer, uniformweather) |
| 4 | BayerPattern1 | bayer_hdf.sim | 4.1 | yes | none |
| 5 | BumpMap2 | demo.sim | 4.1 | yes | none |
| 6 | BundledMaterials1 | w_bundles.jsim | 4.1 | yes | none |
| 7 | CurveMap1 | demo.jsim | 4.1 | yes | FourCurveAtmosphere |
| 8 | DataDrivenArray2 | w_gain.sim | 4.1 | yes | none |
| 9 | DataDrivenTempSolver1 | demo.sim | 4.1 | yes | none |
| 10 | DecalMap1 | demo.sim | 4.1 | yes | none |
| 11 | DensityMap1 | demo.sim | 4.1 | yes | none |
| 12 | GenericMotion1 | demo.sim | 4.1 | yes | none |
| 13 | LensDistortion1 | demo.jsim | 4.1 | yes | none |
| 14 | MaterialMap1 | w_mixing.sim | 4.1 | yes | none |
| 15 | MaterialOverrides1 | demo.sim | 4.1 | no | none |
| 16 | MoonSat2 | demo.jsim | 4.1 | no | tracking mount |
| 17 | NestedMotion1 | demo.sim | 4.1 | no | none |
| 18 | NormalMap1 | demo.sim | 4.1 | yes | .ppd waypoint motion |
| 19 | ReflectanceMap1 | demo.sim | 4.1 | yes | none |
| 20 | Sources4 | demo.sim | 4.1 | yes | simulation options file |
| 21 | Telecentricity1 | demo.jsim | 4.1 | yes | none |
| 22 | TemporalIntegration1 | blur_off.sim | 4.1 | yes | none |
| 23 | TemporalIntegration2 | blur_off.sim | 4.1 | yes | .ppd waypoint motion |
| 24 | Balfour2 | single.sim | 6.1 | yes | none |
| 25 | CommandedMount2 | demo_absolute.sim | 6.1 | no | commanded mount |
| 26 | Fireball1 | demo.sim | 6.1 | yes | several instruments or focal planes |
| 27 | GeoLocation1 | flex_ecef_ecef.jsim | 6.1 | no | none |
| 28 | InstanceOptions1 | glist_demo.sim | 6.1 | yes | none |
| 29 | LemniscateScanMount1 | demo.sim | 6.1 | yes | lemniscate mount |
| 30 | LineScanMount1 | demo.sim | 6.1 | yes | line mount |
| 31 | MicroBolometer1 | long_decay.jsim | 6.1 | no | platform jitter |
| 32 | PointCollectors2 | framing.jsim | 6.1 | yes | none |
| 33 | PolyFill1 | demo.sim | 6.1 | yes | none |
| 34 | PrimitiveObjects1 | demo.sim | 6.1 | yes | none |
| 35 | Skyview1 | demo.sim | 6.1 | yes | BasicAtmosphere .atm (classicradiativetransfer, uniformweather) |
| 36 | Sources1 | demo.sim | 6.1 | yes | simulation options file |
| 37 | Sources3 | demo.sim | 6.1 | no | simulation options file |
| 38 | WhiskScanMount1 | demo.sim | 6.1 | yes | whisk mount |
| 39 | Indoors1 | demo.jsim | 8.1 | yes | none |
| 40 | SensorPosition1 | downlook.sim | 8.1 | yes | BasicAtmosphere .atm (classicradiativetransfer, uniformweather) |
| 41 | Sources5 | demo.sim | 8.1 | yes | simulation options file |
| 42 | TimeDelayedIntegration1 | long_int.jsim | 8.1 | no | .ppd waypoint motion |
| 43 | VertexNormals1 | demo.sim | 8.1 | yes | none |
| 44 | BumpMap1 | demo.sim | 10.1 | yes | none |
| 45 | LeafStack1 | demo.sim | 10.1 | yes | none |
| 46 | MacbethColorChecker1 | demo.sim | 10.1 | yes | none |
| 47 | MappedTherm1 | map_therm.sim | 10.1 | yes | none |
| 48 | TriBar1 | demo.sim | 10.1 | yes | none |
| 49 | EarthMap1 | demo.sim | 12.1 | repeat failed | none |
| 50 | MultiCamera1 | multi.sim | 12.1 | yes | several instruments or focal planes |
| 51 | PrimitiveObjects2 | demo.sim | 12.1 | yes | none |
| 52 | RollingShutter1 | global.sim | 12.1 | yes | none |
| 53 | SubObjectMotion1 | demo.sim | 12.1 | yes | none |
| 54 | SubObjectMotion2 | demo.sim | 12.1 | yes | none |
| 55 | UvMapping1 | drape_map.sim | 12.1 | yes | none |
| 56 | UvMapping2 | demo.sim | 12.1 | yes | none |
| 57 | MixtureMap1 | demo.sim | 12.2 | yes | none |
| 58 | ExtinctionProp1 | demo.sim | 14.1 | yes | none |
| 59 | Pilings1 | demo.sim | 14.1 | yes | none |
| 60 | IESSources1 | demo.sim | 18.1 | yes | none |
| 61 | TemperatureMap1 | demo.sim | 18.1 | yes | none |
| 62 | Brdf2 | demo.sim | 20.1 | yes | none |
| 63 | Thermal3 | demo.sim | 22.1 | no | none |
| 64 | CommandedMount1 | demo_absolute.sim | 24.1 | no | commanded mount |
| 65 | RossLi1 | demo.sim | 24.1 | yes | none |
| 66 | SumoTraffic1 | multi_scene.jsim | 28.1 | yes | platform jitter |
| 67 | MaterialMap2 | demo.sim | 30.1 | yes | none |
| 68 | RegularGrid1 | demo.sim | 30.1 | no | BasicAtmosphere .atm (classicradiativetransfer, uniformweather) |
| 69 | PointCollectors1 | framing.jsim | 36.1 | yes | none |
| 70 | Sources6 | demo.sim | 44.1 | no | none |
| 71 | SubPixelObject1 | demo.sim | 44.1 | yes | none |
| 72 | BundledObject1 | demo.sim | 48.2 | no | none |
| 73 | FastCloud2 | demo_mat_map.sim | 52.3 | yes | none |
| 74 | VertexNormals2 | demo.sim | 54.1 | yes | none |
| 75 | NormalMap3 | demo.jsim | 54.2 | yes | none |
| 76 | SubPixelObject2 | demo.sim | 62.1 | no | none |
| 77 | Muses1 | demo.sim | 64.1 | yes | several instruments or focal planes |
| 78 | BundledObject2 | demo.sim | 66.1 | no | none |
| 79 | ChipMaker2 | demo.sim | 66.2 | no | none |
| 80 | NormalMap2 | demo.sim | 66.2 | yes | none |
| 81 | ExternalTriggers1 | constant.sim | 68.2 | yes | none |
| 82 | Brdf3 | demo.jsim | 88.1 | no | FourCurveAtmosphere |
| 83 | GlistPopulations1 | demo_daily.sim | 88.2 | no | BasicAtmosphere .atm (classicradiativetransfer, uniformweather) |
| 84 | Caustics1 | clear_water.jsim | 100.3 | yes | none |
| 85 | FlexMotion1 | multi_frame.sim | 114.3 | no | none |
| 86 | Thermal2 | demo.sim | 116.3 | yes | none |
| 87 | Parking1 | demo_assimp.sim | 132.2 | no | none |
| 88 | Starfield1 | demo.jsim | 154.2 | yes | none |
| 89 | FourCurveAtm1 | default_w_path.jsim | 160.3 | yes | FourCurveAtmosphere |
| 90 | BackgroundSky1 | demo.jsim | 166.4 | yes | plugin PositionIndependentBackground |
| 91 | TrafficLights1 | demo.jsim | 194.4 | yes | plugin TrafficLight |
| 92 | Brdf1 | demo.sim | 204.3 | yes | weather without a ThermWeather file |
| 93 | ChipMaker1 | demo.sim | 212.3 | yes | none |
| 94 | Polarization5 | pi.sim | 230.4 | yes | none |
| 95 | Polarization4 | pi.sim | 244.3 | yes | several instruments or focal planes |
| 96 | Polarization1 | nadir.sim | 310.6 | not tested | BasicAtmosphere .atm (classicradiativetransfer, uniformweather) |

`ready` demos without a reference: FastCloud1 (failed), Polarization2 (failed), Polarization3 (failed).

`near` demos without a reference: Blackadar1 (failed), Cloudview1 (failed), FocusDistance1 (timeout), HdfWater1 (failed), Muses2 (failed), ReflectanceInversion1 (failed), Refraction1 (failed), SpatialResponse1 (failed), Ssa2 (skipped: dirsig4), Ssa3 (skipped: dirsig4), Thermal1 (failed).

<!-- summarize_sweep: end -->

## Notes on this sweep

- Wall times are measured by the driver's poll loop (every 2 s) from submission to the final state, so they have a resolution of about 2 s and include the worker start and the scene compile; the many 4.1 s and 6.1 s values are that floor, not the render.
- `Brdf1` renders here with `demo.sim` (204 s, deterministic). The round 14 reference run used `demo.jsim`, which names a NewAtmosphere database that is not in the archive; the recipe `demo_brdf1_passthrough` has since been switched to `demo.sim` (the same directory digest and simulation file as this sweep's attempt; the run ids differ only through the descriptor's name, tags and description).
- `EarthMap1`'s repeat is recorded `repeat failed` with a wall time of 0.0 s: the run store failed the repeat's run at once because it read the worker's command line in the instant between the process being forked and the worker starting, and took it for a dead worker. That is a defect of the SDK's run store, not of the demo; the run store has since been changed to know the worker by its start time. `EarthMap1`'s determinism is untested.
- No attempt states a seed, so every run uses DIRSIG's default. All 17 repeated lidar demos wrote different `.bin` files the second time, and 9 demos differ only in their truth images; whether a stated `--random_seed` makes them repeat is not tested here.
- The host's maximum thermal-zone temperature was 90 C or more during most attempts. CPU frequency was not recorded, so whether throttling lengthened the renders is unknown; the wall times are this host's under sustained load.
- Two simulation files hit the 1800 s cap: `FocusDistance1` `demo.jsim` and `SumoTraffic1` `multi_frame.sim` (whose second file, `multi_scene.jsim`, rendered in 28 s).
- `MoonSat1`, `Ssa2` and `Ssa3` were not attempted (DIRSIG 4 only, per the online demo page); `Starfield1 (2)` is a copy of `Starfield1`.
