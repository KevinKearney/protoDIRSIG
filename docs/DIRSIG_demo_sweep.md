# DIRSIG demo sweep

Every DIRSIG 5 demo shipped with the installation (`external/dirsig/demos/zips`), run once through the pass-through form by `scripts/sweep_demos.py`: which demos run in this installation, what they cost, what they output, and why the others fail. It is the evidence for choosing which demos drive layered loader work; `docs/DIRSIG_demo_coverage.md` is the static survey of the same demos and `docs/DIRSIG_demo_reference_runs.md` the measured reference runs of the two committed pass-through recipes.

The part between the markers is generated from the sweep's results file (outside the repository) and rewritten after every demo; text outside the markers is kept. Only names, sizes, digests, measurements and DIRSIG error lines appear here, no demo bytes. Each demo is extracted from its zip, its simulation files are tried in turn (`demo.sim`, then `demo.jsim`; with neither, up to four top-level `.sim` or `.jsim` files in alphabetical order), stopping at the first that renders; a render under 300 s is repeated in a fresh work root to test determinism. The engine is DIRSIG 2026.38 (a020954) with a per-run `HOME`, so DIRSIG's material caches start cold for every attempt and the user's cache is not involved. "Max CPU" is the maximum over the host's thermal zones during the attempt; 90 C or more is flagged as a throttle suspect.

<!-- sweep_demos: generated between these markers by scripts/sweep_demos.py; edit outside them -->

## Sweep

Deadline 2026-10-11T12:42:13-04:00, per-run timeout 1800.0 s, disk floor 20.0 GB, started 2026-10-11T02:40:36Z. 72 demos recorded, 129 attempts (repeats included). Not ended yet.

| Outcome | Demos |
|---|---|
| failed | 5 |
| rendered | 62 |
| skipped: dirsig4 | 3 |
| skipped: duplicate name | 1 |
| timeout | 1 |

## Demos

| Demo | Size (MB) | Outcome | Attempts | Wall time (s) | Outputs | Output (MB) | Run directory (MB) | Deterministic | Max CPU (C) | First error line |
|---|---|---|---|---|---|---|---|---|---|---|
| BackgroundSky1 | 1.04 | rendered | demo.jsim: rendered | 166.4 | 96 | 163.60 | 164.86 | yes | 94.05 (throttle suspect) | - |
| Balfour1 | 0.48 | rendered | demo.sim: rendered | 4.1 | 4 | 2.46 | 3.00 | yes | 94.05 (throttle suspect) | - |
| Brdf3 | 0.47 | rendered | demo.jsim: rendered | 88.1 | 4 | 7.37 | 12.01 | no | 94.05 (throttle suspect) | - |
| BumpMap1 | 0.15 | rendered | demo.sim: rendered | 10.1 | 4 | 6.14 | 6.54 | yes | 86.05 | - |
| BumpMap2 | 0.11 | rendered | demo.sim: rendered | 4.1 | 4 | 7.99 | 9.73 | yes | 93.05 (throttle suspect) | - |
| BundledMaterials1 | 0.36 | rendered | w_bundles.jsim: rendered | 4.1 | 4 | 3.07 | 3.53 | yes | 94.05 (throttle suspect) | - |
| DataDrivenTempSolver1 | 0.17 | rendered | demo.sim: rendered | 4.1 | 4 | 2.46 | 2.79 | yes | 95.05 (throttle suspect) | - |
| DensityMap1 | 0.69 | rendered | demo.sim: rendered | 4.1 | 4 | 6.14 | 7.36 | yes | 94.0 (throttle suspect) | - |
| EarthMap1 | 0.15 | rendered | demo.sim: rendered | 12.1 | 4 | 8.60 | 1875.07 | repeat failed | 94.05 (throttle suspect) | - |
| ExternalTriggers1 | 0.15 | rendered | constant.sim: rendered | 68.2 | 50 | 15.37 | 15.63 | yes | 94.05 (throttle suspect) | - |
| ExtinctionProp1 | 1.03 | rendered | demo.sim: rendered | 14.1 | 2 | 1.84 | 3.01 | yes | 93.05 (throttle suspect) | - |
| Fireball1 | 0.66 | rendered | demo.sim: rendered | 6.1 | 6 | 7.37 | 8.14 | yes | 94.05 (throttle suspect) | - |
| FlexMotion1 | 1.17 | rendered | multi_frame.sim: rendered | 114.3 | 148 | 68.23 | 69.90 | no | 96.05 (throttle suspect) | - |
| FocusDistance1 | 0.70 | timeout | demo.jsim: timeout | 1800.8 | 0 | - | 1963.78 | - | 95.0 (throttle suspect) | - |
| GenericMotion1 | 1.17 | rendered | demo.sim: rendered | 4.1 | 4 | 3.07 | 4.35 | yes | 92.05 (throttle suspect) | - |
| GlistPopulations1 | 1.06 | rendered | demo_daily.sim: rendered | 88.2 | 4 | 7.37 | 12.00 | no | 94.05 (throttle suspect) | - |
| IESSources1 | 0.33 | rendered | demo.sim: rendered | 18.1 | 4 | 11.06 | 11.49 | yes | 96.05 (throttle suspect) | - |
| InstanceOptions1 | 0.06 | rendered | binary_demo.sim: failed; glist_demo.sim: rendered | 6.1 | 4 | 8.60 | 8.72 | yes | 95.0 (throttle suspect) | [error] Error! |
| LeafStack1 | 0.39 | rendered | demo.sim: rendered | 10.1 | 4 | 8.60 | 9.06 | yes | 94.05 (throttle suspect) | - |
| LensDistortion1 | 0.05 | rendered | demo.jsim: rendered | 4.1 | 4 | 4.92 | 5.03 | yes | 94.05 (throttle suspect) | - |
| LidarBounces1 | 0.04 | rendered | demo.sim: rendered | 6.1 | 3 | 41.94 | 42.21 | no | 96.0 (throttle suspect) | - |
| LidarRetro1 | 0.01 | rendered | demo.sim: rendered | 4.9 | 3 | 0.39 | 0.53 | no | 72.05 | - |
| LidarSide2 | 0.23 | rendered | multiple.sim: rendered | 38.1 | 1 | 8.29 | 8.63 | no | 89.05 | - |
| LidarSlope1 | 0.36 | rendered | flat.sim: rendered | 2.1 | 3 | 0.00 | 0.43 | no | 81.05 | - |
| LidarUserBeam1 | 0.91 | rendered | demo.sim: rendered | 20.1 | 3 | 22.27 | 23.27 | no | 94.0 (throttle suspect) | - |
| LidarUserPulse1 | 0.63 | rendered | after_pulse.sim: rendered | 4.1 | 1 | 0.09 | 0.81 | no | 91.0 (throttle suspect) | - |
| MacbethColorChecker1 | 0.85 | rendered | demo.sim: rendered | 10.1 | 4 | 12.29 | 13.45 | yes | 94.05 (throttle suspect) | - |
| MappedTherm1 | 0.19 | rendered | map_therm.sim: rendered | 10.1 | 2 | 3.67 | 3.92 | yes | 94.05 (throttle suspect) | - |
| MaterialMap1 | 0.26 | rendered | w_mixing.sim: rendered | 4.1 | 4 | 6.76 | 10.95 | yes | 93.05 (throttle suspect) | - |
| MaterialOverrides1 | 1.05 | rendered | demo.sim: rendered | 4.1 | 4 | 3.07 | 4.25 | no | 93.05 (throttle suspect) | - |
| MicroBolometer1 | 0.88 | rendered | long_decay.jsim: rendered | 6.1 | 4 | 6.30 | 10.20 | no | 94.05 (throttle suspect) | - |
| MoonSat1 | - | skipped: dirsig4 | flagged DIRSIG 4 only by the online demo page, which the user read | - | 0 | - | - | - | - | - |
| MultiCamera1 | 0.15 | rendered | multi.sim: rendered | 12.1 | 16 | 24.58 | 24.81 | yes | 94.05 (throttle suspect) | - |
| NestedMotion1 | 0.96 | rendered | demo.sim: rendered | 4.1 | 4 | 6.14 | 10.01 | no | 95.05 (throttle suspect) | - |
| NormalMap1 | 0.50 | rendered | demo.sim: rendered | 4.1 | 4 | 7.99 | 10.14 | yes | 93.05 (throttle suspect) | - |
| Pilings1 | 0.14 | rendered | demo.sim: rendered | 14.1 | 4 | 29.49 | 29.75 | yes | 94.05 (throttle suspect) | - |
| PlatformJitter1 | 0.10 | rendered | flex_single.sim: rendered | 6.1 | 5 | 6.15 | 6.31 | no | 94.0 (throttle suspect) | - |
| PlatformJitter2 | 0.10 | rendered | flex_single.sim: rendered | 4.1 | 5 | 6.15 | 6.34 | no | 94.05 (throttle suspect) | - |
| PointCollectors2 | 0.28 | rendered | framing.jsim: rendered | 6.1 | 4 | 20.97 | 21.34 | yes | 94.05 (throttle suspect) | - |
| Polarization1 | 0.26 | rendered | nadir.sim: rendered | 310.6 | 4 | 6.14 | 19.27 | not tested | 96.05 (throttle suspect) | - |
| Polarization2 | 0.28 | failed | sphere.sim: failed | 22.1 | 0 | - | 1.58 | - | 90.0 (throttle suspect) | [error] Error! |
| Polarization4 | 0.11 | rendered | pi.sim: rendered | 244.3 | 8 | 0.81 | 13.79 | yes | 96.05 (throttle suspect) | - |
| PolyFill1 | 0.07 | rendered | demo.sim: rendered | 6.1 | 4 | 6.14 | 6.36 | yes | 94.05 (throttle suspect) | - |
| PrimitiveObjects1 | 0.06 | rendered | demo.sim: rendered | 6.1 | 4 | 4.92 | 5.15 | yes | 94.05 (throttle suspect) | - |
| PrimitiveObjects2 | 0.10 | rendered | demo.sim: rendered | 12.1 | 4 | 5.53 | 5.72 | yes | 94.05 (throttle suspect) | - |
| RollingShutter1 | 0.84 | rendered | global.sim: rendered | 12.1 | 4 | 4.92 | 6.00 | yes | 94.05 (throttle suspect) | - |
| RossLi1 | 0.03 | rendered | demo.sim: rendered | 24.1 | 4 | 9.83 | 10.07 | yes | 94.05 (throttle suspect) | - |
| Skyview1 | 0.99 | rendered | demo.sim: rendered | 6.1 | 4 | 135.17 | 136.30 | yes | 94.0 (throttle suspect) | - |
| Sources1 | 0.35 | rendered | demo.sim: rendered | 6.1 | 4 | 7.37 | 7.82 | yes | 93.05 (throttle suspect) | - |
| Sources4 | 0.90 | rendered | demo.sim: rendered | 4.1 | 2 | 0.61 | 1.59 | yes | 93.05 (throttle suspect) | - |
| Sources5 | 0.10 | rendered | demo.sim: rendered | 8.1 | 4 | 6.14 | 6.33 | yes | 92.05 (throttle suspect) | - |
| SpatialResponse1 | 0.07 | failed | checkers.sim: failed | 2.1 | 0 | - | 0.08 | - | 83.05 | [error] Error! |
| SphericalCollector2 | 0.73 | rendered | overhead.jsim: rendered | 14.1 | 2 | 10.14 | 11.03 | yes | 94.0 (throttle suspect) | - |
| SpotlightSar1 | 0.87 | failed | demo.sim: failed | 2.0 | 0 | - | 0.87 | - | 77.05 | [error] Error! |
| Ssa1 | 0.63 | rendered | demo.sim: rendered | 629.4 | 4 | 12.29 | 21.36 | not tested | 97.05 (throttle suspect) | - |
| Ssa2 | - | skipped: dirsig4 | flagged DIRSIG 4 only by the online demo page, which the user read | - | 0 | - | - | - | - | - |
| Ssa3 | - | skipped: dirsig4 | flagged DIRSIG 4 only by the online demo page, which the user read | - | 0 | - | - | - | - | - |
| Starfield1 | 0.46 | rendered | demo.jsim: rendered | 154.2 | 4 | 9.83 | 18.73 | yes | 95.0 (throttle suspect) | - |
| Starfield1 (2) | - | skipped: duplicate name | the name holds a space or a parenthesis (a copy of another demo) | - | 0 | - | - | - | - | - |
| StripmapSar1 | 0.60 | failed | demo.sim: failed | 2.1 | 0 | - | 0.61 | - | 88.05 | [error] Error! |
| SubObjectMotion1 | 0.54 | rendered | demo.sim: rendered | 12.1 | 4 | 6.14 | 6.92 | yes | 94.05 (throttle suspect) | - |
| SubObjectMotion2 | 0.67 | rendered | demo.sim: rendered | 12.1 | 4 | 6.14 | 7.06 | yes | 95.0 (throttle suspect) | - |
| SubPixelObject1 | 0.27 | rendered | demo.sim: rendered | 44.1 | 4 | 0.32 | 0.68 | yes | 94.0 (throttle suspect) | - |
| Telecentricity1 | 0.19 | rendered | demo.jsim: rendered | 4.1 | 4 | 9.32 | 9.62 | yes | 94.05 (throttle suspect) | - |
| TemperatureMap1 | 0.10 | rendered | demo.sim: rendered | 18.1 | 4 | 6.76 | 6.96 | yes | 85.05 | - |
| TemporalIntegration1 | 0.96 | rendered | blur_off.sim: rendered | 4.1 | 2 | 1.84 | 2.95 | yes | 93.05 (throttle suspect) | - |
| TemporalIntegration2 | 0.98 | rendered | blur_off.sim: rendered | 4.1 | 2 | 1.84 | 2.95 | yes | 95.05 (throttle suspect) | - |
| Thermal1 | 0.06 | failed | demo.sim: failed | 2.1 | 0 | - | 0.16 | - | 79.05 | [error] BasicAtmosphere::init: ERROR! |
| Thermal2 | 0.08 | rendered | demo.sim: rendered | 116.3 | 20 | 33.80 | 34.00 | yes | 94.05 (throttle suspect) | - |
| TrafficLights1 | 0.06 | rendered | demo.jsim: rendered | 194.4 | 182 | 167.78 | 168.09 | yes | 94.05 (throttle suspect) | - |
| UvMapping1 | 1.01 | rendered | drape_map.sim: rendered | 12.1 | 4 | 6.14 | 7.36 | yes | 95.05 (throttle suspect) | - |
| VertexNormals1 | 0.26 | rendered | demo.sim: rendered | 8.1 | 4 | 4.92 | 5.41 | yes | 94.0 (throttle suspect) | - |

## Outputs of rendered demos

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
| demo-t0012.img | 1572864 | `c2ef208711edb1cd9a6281bc43a6f08d7b89c542bc9feb3aa5711053fb388370` |
| demo-t0012.img.hdr | 558 | `9d857537d4ae1c4885e7fbe2bddd733114c5398ceb1a9ddefb9111455e6f5a97` |
| demo-t0013.img | 1572864 | `b7104e090d4abbc40d599dbfb6a569f54beda3af966840b6d6406114b6d60c33` |
| demo-t0013.img.hdr | 559 | `ba60b8fb00827211618b545c42b69b306cd36252af37d389a19ed31cb0014af8` |
| demo-t0014.img | 1572864 | `26c383ef8f06d916cf0fe2d0a4d0a4adb0c2495661900a19f612564fff11750c` |
| demo-t0014.img.hdr | 558 | `f944b3c8c1ea8bf345b85cce6edd0d682bd67c63d6c071fd6abb222aac12bf4a` |
| demo-t0015.img | 1572864 | `0bdf97c70543176d3e8b49703c3e4be2fa40e66f28c2268eac286e25a3264faf` |
| demo-t0015.img.hdr | 556 | `009feadd9b57d8e4be4db6595d9e5b37ba89fd798c3bfce1e98ae69cf69bbd20` |
| demo-t0016.img | 1572864 | `03f294c8d9a311ff8d5e27e6cbbc2601dcac87c272367152c298a6c1faeaaa65` |
| demo-t0016.img.hdr | 559 | `372dcfb0432c8a1b8ed7dd6d8918b50f92606e4bfcc11814521916a0b7b7f8d7` |
| demo-t0017.img | 1572864 | `9f827ecfa52953adc4c6a2e6019dae27cfc0a9e1cb92c414707e0cff9e3ac6ee` |
| demo-t0017.img.hdr | 559 | `d940d4e3e979c173a5837c3e4810c6ad20d3a14d3a3e81c604fc34db7cca39c6` |
| demo-t0018.img | 1572864 | `7a2795852e1f05eaaab3f9dbe762e639fdf4c6bfeca7ef65cd1da80f865c36ab` |
| demo-t0018.img.hdr | 558 | `4d7927a1fd100cf347720fa5a93abf59b93fb0f147e043dba0eec0a1a535ac1c` |
| demo-t0019.img | 1572864 | `ea1c50bdfee237de2bec3d16c52d0895934810fc910ca5bdaff7199a4b35d7dc` |
| demo-t0019.img.hdr | 559 | `842472515accd456e9c90b12cadd5c35714db0c41b1096870daca57d9c2eda83` |
| demo-t0020.img | 1572864 | `5611be50685171e7f4594188f815295c3e771879d75ea4f137a9116c2bf1010b` |
| demo-t0020.img.hdr | 558 | `4914ca784606d17c2743155e99cf4070219dd5578d7e128a251e67dd17fe08b2` |
| demo-t0021.img | 1572864 | `ea056b64f6a64daf7312eef32a431acee3a5e28724e0df9dcd1c24bdc59c18b2` |
| demo-t0021.img.hdr | 559 | `f0b6d6a233301cb76770b9b566e86995805b67545b700e9a8a1a04636db821b8` |
| demo-t0022.img | 1572864 | `fb1e6090a503c508ce82b6e91b9c3c14e67204581a60f97772ea3a16b2c47e58` |
| demo-t0022.img.hdr | 558 | `b478565291a4c53b0f9b6cc4462250df98fab9b7ccd8e9d9c2ddc936fc1a0327` |
| demo-t0023.img | 1572864 | `2babea7c0e65eda22420c9fbadc626255f0408e6de3f5cc33ea2c2aeeb1ddc19` |
| demo-t0023.img.hdr | 557 | `46396c4b317c92dd7ba2addf8f2e60bc1468ac7566798647c8cffa5fb5dcda68` |
| demo_truth-t0000.img | 5242880 | `b4c4a938de86c4697522ffdb89d2870110c54496ce88ef8013285bd8663a2ec3` |
| demo_truth-t0000.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0001.img | 5242880 | `23d9fb4c20f6ede9c7523778449f4798bab9b799b32dad1398e8735e2e4d39c7` |
| demo_truth-t0001.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0002.img | 5242880 | `a3fc691ded27416c17f31fae75b7cd0fa38c7a80c0d0c1679615e9f374cb8573` |
| demo_truth-t0002.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0003.img | 5242880 | `e211bb342d998d20e2d94e7e684551635ab96f09b0e9e3a76bcd7258c5c17ede` |
| demo_truth-t0003.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0004.img | 5242880 | `4d29c2797189cf68e6bd62eead69b576fe6580183036b363122a7ef3a8a6f896` |
| demo_truth-t0004.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0005.img | 5242880 | `ec6f6042197edca864ad9115e43339b19b0a0532967ebd46015312106fac9d8e` |
| demo_truth-t0005.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0006.img | 5242880 | `8d7979ad2a4ecfaf00c204880d3497b28e6340def1dc15ae8a3b7f8051c67a25` |
| demo_truth-t0006.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0007.img | 5242880 | `3f00d0160208d7093ca6caf1e20a325426eaa5077a91aa1c49c2daa437186081` |
| demo_truth-t0007.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0008.img | 5242880 | `f053d1acb3899ba9d9d84aca7ac4d7a1306127b8462354da704be40527d48f41` |
| demo_truth-t0008.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0009.img | 5242880 | `a248f1aa35d6752d0d4807735bdcac54627255ee919c62a60677b844b417e7c7` |
| demo_truth-t0009.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0010.img | 5242880 | `0a69bbf171db2356982c1ece0b2c9231fb1a3ce83805353d97c00593d919dac1` |
| demo_truth-t0010.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0011.img | 5242880 | `59dd29f7e220646ea9ee8a02a2d766b5d1969cbc199d458382cfaa09ef6e4685` |
| demo_truth-t0011.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0012.img | 5242880 | `5f2f79aacffb024af4479741547fe0b0d20d6d0ed935f19b39e5ece225e2971e` |
| demo_truth-t0012.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0013.img | 5242880 | `e56f6b28fa15633f6602a801fc0d688ff189f787557455250be310ed779697fa` |
| demo_truth-t0013.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0014.img | 5242880 | `d5537d27e424c70099b23997ce692729b7de716d61b1e7bed472ead881a57cf7` |
| demo_truth-t0014.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0015.img | 5242880 | `705c5b0133f4595883cb07eb6652ba106c6b05ab0faa3b2e60fc2f5d31edeace` |
| demo_truth-t0015.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0016.img | 5242880 | `54340b01d4a3fa6258889b5cdf82231c25cbe041a398c30026a25f08d59df9f5` |
| demo_truth-t0016.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0017.img | 5242880 | `1cb3d838313de8de0d8615df2f7bd7db16640423dc350ebc8b75dcc31e387ba1` |
| demo_truth-t0017.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0018.img | 5242880 | `1ebdcddfec15d73e061c9ef8eab8431fd75209e22cd84e23ac29c0492897ad96` |
| demo_truth-t0018.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0019.img | 5242880 | `5bf4f6c1a8a31a526e1156519bc7a5ef5a0232c201a2973f543d52eebc059a43` |
| demo_truth-t0019.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0020.img | 5242880 | `1b19e834d694491ba069cbf1f48e429e27d74c4ad2535a2243de5c43a3daf829` |
| demo_truth-t0020.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0021.img | 5242880 | `9c95373e2490a5e500670b9488f60ffbcf503e4f6f2410f3f4316a8571d29354` |
| demo_truth-t0021.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0022.img | 5242880 | `409922401230572c4aa7cd53a6e02ab825b666311418257b23daf87a8cf3371e` |
| demo_truth-t0022.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |
| demo_truth-t0023.img | 5242880 | `a48607975a2c1a31b133a79f228ab983cded6f7f5c7913d055725eceef5d63e1` |
| demo_truth-t0023.img.hdr | 438 | `e87cc598dfa8e8e88361321f776d52b412c7148990a5a13dafa27a77dc6e1190` |

### Balfour1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `1108130680b6791cb984c73c72f0abad7fdbcf087302c698f90b2ff81e9985f9` |
| demo.img.hdr | 525 | `abb874ebdb055daa2964736298bad23f93720364a34e0ef407d6f5c76cb70dc0` |
| demo_truth.img | 1843200 | `cae0e806689dbc3ed721f7abf79b75688e94990b4f178649ac30a1607cf95440` |
| demo_truth.img.hdr | 286 | `e37cb34631c0ab39cd0e4e34ca33db13b546b673e3434102845f855064e7275d` |

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

### DataDrivenTempSolver1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `5798dc81857532d96ddd528811d166bf8142af60f427bb79393f2ef29d211313` |
| demo-t0000-c0000.img.hdr | 534 | `6ffc07d59477056c5260df809d3a1a62f230352ced72238a5a599cf185a76109` |
| demo_truth.img | 1843200 | `441830ca711cbe8ca09bb26b3356076e998f5097a6ccb855cc620ec0984ae947` |
| demo_truth.img.hdr | 287 | `42cc6a2b6daa6ac863929a0d21bd8ecc877b60bde8483545fc9c0177f56fe493` |

### DensityMap1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `d78868ccd749174ba6193a81a5c2b89c02ad86376d62d2df35a41047754817b9` |
| demo.img.hdr | 528 | `240588a0dd58de7591547733ecd5b41f06b135b34311aedc66ae081c9b5431d3` |
| demo_truth.img | 5529600 | `1e7990314cf49139a5a91874b389b7665c8383d236c35bd241e0cabcf0a91c05` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### EarthMap1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 2150400 | `a12dfa031a0f5458394e8cb07d7adf4e29e4f42f031f1e7b9dc0b7f7856a7e24` |
| demo.img.hdr | 581 | `2d1104a6c50d59935d1c04199758067137c2aec6a1c256ea0775889da8320b23` |
| demo_truth.img | 6451200 | `e80a1bcfdb06d296977996ad9cdb168b884ff2fb05e83120173ab4aa6680ea49` |
| demo_truth.img.hdr | 424 | `a0eae46b1fe9cd42d8d766bf0441b817e96230cf94f7c348c22ca9fbbd698dc8` |

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
| constant-t0000-c0012.img | 614400 | `8735efdf3b08e84d68d412d1fb25e20727cf93e72dfe8091d9488a781776a598` |
| constant-t0000-c0012.img.hdr | 534 | `624a24fa4ea47fdf8ac6068b0522fd9f81195201d79a532923a3904321ed2bef` |
| constant-t0000-c0013.img | 614400 | `82601297b315924c059f2f8028acc853c77f47a372e74074a903db1dd4447645` |
| constant-t0000-c0013.img.hdr | 533 | `55243959a6ae56f2e437efbae0093f609e8ddcd35e5dfd74d135bca57a32ab4b` |
| constant-t0000-c0014.img | 614400 | `954b49268fc3fcb648d8c172b6a2617293f5b7282182a88e766695bdacdd8c3b` |
| constant-t0000-c0014.img.hdr | 534 | `c01a9e2dee3afb52f0dc4c3d75d5313d0068a5ed2ca648f16fa60625e60395d6` |
| constant-t0000-c0015.img | 614400 | `3cda6addc872511261cd070b041b78ba18239b30f036f94486926194dbbc2d89` |
| constant-t0000-c0015.img.hdr | 533 | `88e9c91fc62ddcb0ab98f6000686f42c4424b6044b63bbf8abb04ec74fbc6187` |
| constant-t0000-c0016.img | 614400 | `9106fb743719340b7d63267f836a80e30b286595f7c9fcafba01c1c653a34271` |
| constant-t0000-c0016.img.hdr | 531 | `20a4d9091d16a7d87b752a6960a1221d3638ecae2c04122fd76ed06ff7cd92e7` |
| constant-t0000-c0017.img | 614400 | `c840a57281eccd24ba5999c793d5e0b07ee82d1455686caadcad4ad000d6356c` |
| constant-t0000-c0017.img.hdr | 533 | `31059c80f45bf9f1d1d02e00bdc0529113bf92171b1f143737f5f5e6cb1cfa50` |
| constant-t0000-c0018.img | 614400 | `e3dbdb4f51539b1e414c74d54f2be7cab17b26a3862e5133f5cfc2fbc3bf6c98` |
| constant-t0000-c0018.img.hdr | 534 | `ac86c2cae7b7b6de25ba1f044df0470b751125d709b05750818264292ebd70fe` |
| constant-t0000-c0019.img | 614400 | `7c1f1ca13e607001077fd809069239942a2e30acb00715868cb3ff32eca0e715` |
| constant-t0000-c0019.img.hdr | 534 | `599aebca7a4026f997148a9f2e92a9f9cf41a9570af727643851aeceb677abc9` |
| constant-t0000-c0020.img | 614400 | `8ccefdb6676642b0d4d617d71c9a50416fbf33d685f7c5c218afd6c846477581` |
| constant-t0000-c0020.img.hdr | 533 | `e4780bb2067c496d0c442d78fe3bf5a38d42abdce7cd21655fdc1d1c0d42a2a6` |
| constant-t0000-c0021.img | 614400 | `dc48a5ec8dc87e36c6bc8d6beb6c5fec15d0eb1983193a5756ee0c720d5a05f2` |
| constant-t0000-c0021.img.hdr | 534 | `eabecd3745968da762ed8231e341c84e7f416558fbb4180ab295ff2d42598567` |
| constant-t0000-c0022.img | 614400 | `1a4dd0be548e51df95ca70cb6e1878207fa8bc95f0746adac36e5c837fd08f7d` |
| constant-t0000-c0022.img.hdr | 533 | `07a82d62fc79e09042682897e10d096f5aa5db5c7b04f3cacb0e3bbf5d26b0fa` |
| constant-t0000-c0023.img | 614400 | `a7e4768dba37f40dda1ab25a5983e363385e1c99f30441364e3ae1df2249fa3b` |
| constant-t0000-c0023.img.hdr | 533 | `375d7c9f7fbcee3bdd23cfaa61a0d024198f0e496de99e27fdcf6c8df98ad251` |
| constant-t0000-c0024.img | 614400 | `672ad1fbb91406f653e74b88c87ccd84ba1586f9d4c5875042831c0137db0413` |
| constant-t0000-c0024.img.hdr | 531 | `81eb9ac646e86f038acb452a819cb6d1dfe98ee7644d8f7f105cf180fb55bc35` |

### ExtinctionProp1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1843200 | `1ad4f19cdb44723c13ca7c57733d09e33bc7da9a0a2e9614e7fed0e23b537d18` |
| demo-t0000-c0000.img.hdr | 585 | `f1e12a9c7a47807b95c84c8bdf2f38947cdb35e7f77487b8a090b1efeaecedb6` |

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
| demo-t0000-c0012.img | 614400 | `73cd2cb9235362ec970d5b2b2c154b107f8ad172ea9c481c6b8ad7ef6f29b493` |
| demo-t0000-c0012.img.hdr | 534 | `c82795acc77d4ea7f98f8729cace109666fcddd4a08273435a2e72aab28ab738` |
| demo-t0000-c0013.img | 614400 | `e341c295dcbba736a454db6c03e3f4738c7b3f7a24f7f3279d0de93f306673e6` |
| demo-t0000-c0013.img.hdr | 532 | `0a0d75a5693b85d3a81deaea7cb1f005d4ec59d82a4f72048aa28fe4dcbd6f5b` |
| demo-t0000-c0014.img | 614400 | `7a4a9a4edb2eb2a748d83a0ca874ece5546df1020c25ba438ea6e0d2482cff8d` |
| demo-t0000-c0014.img.hdr | 533 | `6d7565bb2e622e8e0f647356dbc8c263bce28840707c9316af89a1a3fd335108` |
| demo-t0000-c0015.img | 614400 | `6522cc7252bf2b19849e1fc996201648d2a1f1c45d3df139cb1bca9cbb74083d` |
| demo-t0000-c0015.img.hdr | 532 | `5840e444893560ebd29118c2452c1f0fed147776b60472fad406504d0afb071c` |
| demo-t0000-c0016.img | 614400 | `3c61ff5ecee08faacaa11a85ac5cb575832e346ca319c20746b7aacf59724cd6` |
| demo-t0000-c0016.img.hdr | 534 | `a93f76b9ba9fdb97d66c97ba04d6dac7e101254e4cf7df00a415903c5163403b` |
| demo-t0000-c0017.img | 614400 | `702d1dc3cb5d005b280b622cfe8a09ded0452079828247aa02b20479df0ec1f7` |
| demo-t0000-c0017.img.hdr | 533 | `bef49eec607080c3b8eda5c44c019ebd340bfffb0ddceec3e482386073137f82` |
| demo-t0000-c0018.img | 614400 | `a5980f080180e5a2949f53c1394ce9cc81826cc21d05ec501735a646b24a11fd` |
| demo-t0000-c0018.img.hdr | 534 | `57c9efe559253634059749fa0ae36a410af8c127ba14125de137f3105f48162d` |
| demo-t0000-c0019.img | 614400 | `b7ed1d2b67afe8666bf42d8231d0bd192ca85a25c83341e63bcfd72d4e4d884a` |
| demo-t0000-c0019.img.hdr | 532 | `4d661d87fab223f493421ed86c0d02479740fa6a4be513212620a00ac66e6c43` |
| demo-t0000-c0020.img | 614400 | `3088a98c0f3749aef42e8a55cf36ca5a5a0332ebb2a3933e2e5c448058246a88` |
| demo-t0000-c0020.img.hdr | 534 | `760bdc2000e51683cbd0f394e2ecdbfd5f7440a542bc66eb92dd9976ae8f4de6` |
| demo-t0000-c0021.img | 614400 | `4885de8918146181317f4c1f3f7826ddd007cf5bd4ec1e684f946b850f3f12d4` |
| demo-t0000-c0021.img.hdr | 534 | `c53f8033c961d56b0ac30ac041428a4d130471883611ce8ea224f469a7ce5262` |
| demo-t0000-c0022.img | 614400 | `cf6379d99389e4afb2286e7cd998b126030168d87c0989cdfcf2c9a06c902808` |
| demo-t0000-c0022.img.hdr | 534 | `cda0e6317ae232d9b537d108cb2cb9b968b441300c205649fcd0873c05cb9024` |
| demo-t0000-c0023.img | 614400 | `cb8bd842be43c98f9d5fb72558118d9d89c44bdcd20d5694e4c24168d40e7ab7` |
| demo-t0000-c0023.img.hdr | 534 | `93c1a3d509505b4eb02b1a61348e9ecb45507b34d347035023c12df8c05d5bf0` |
| demo-t0000-c0024.img | 614400 | `cd25abeb58b2fb1e8d55708b563a55e5b10e47bf4eb2da33790cfb4ed06141ec` |
| demo-t0000-c0024.img.hdr | 533 | `957348dcf96daa2a80265674064bfb3ebdefd175db43feb85062b748b83b95f6` |
| demo-t0000-c0025.img | 614400 | `1c893f916ce2b5fd6abcf8c29bcf30fdb064a34f5ace99d371c3f7f67d81b3c4` |
| demo-t0000-c0025.img.hdr | 534 | `70aaf2db7f6bcc6733f05f29bc32b713432695770ccf1730f594ed38a518c462` |
| demo-t0000-c0026.img | 614400 | `2e826c28be17dfc67ece849af3158d8a36cabb454e25ead9d74c976009a0e994` |
| demo-t0000-c0026.img.hdr | 532 | `99f8d3c5e4ec5c0c7418ff661d094e32f08537d2879f4c6503e243aed2c93aa6` |
| demo-t0000-c0027.img | 614400 | `c5bb87d01a45ac6c84f05b9aa437464f5bbe1e50e66e3c05dda03aaece40cf1d` |
| demo-t0000-c0027.img.hdr | 534 | `22e2ebfbf9203537d699ebc740a03fcd65c25d1eaf7e295d23376996aa791c99` |
| demo-t0000-c0028.img | 614400 | `4dc513e566e52124524a02475b4ace744ebde2e43bef5e7d465c924cc70393b0` |
| demo-t0000-c0028.img.hdr | 534 | `11696f75eec0d3e32d11c2ac974048930ca01a7deef05f1fae02b85321ee4587` |
| demo-t0000-c0029.img | 614400 | `25f0ccca5982965862198ccc5acf882e30dbeedbbd87b52999a9a4f1392062b9` |
| demo-t0000-c0029.img.hdr | 533 | `7fcb403c532725e7ced73034d5cf8f5143525616eb914158314f2c7a9253dde3` |
| demo-t0000-c0030.img | 614400 | `95ec7329c5965fe90c1df24dbb424afc3856eedf8c5776294673dc31099a1225` |
| demo-t0000-c0030.img.hdr | 533 | `72db4465cf26de7975319243fa5f3fedefd32b6c4a209bca0e4ba0e7977777f5` |
| demo-t0000-c0031.img | 614400 | `27774c91ec9c53a1bf5fe875d740530b54b230394f1fe388e0d5d7529a940a41` |
| demo-t0000-c0031.img.hdr | 534 | `2d74ca16c3c118c669418efb507cf3d70fbc7adaf148131ec016e41e09fdf231` |
| demo-t0000-c0032.img | 614400 | `e173b3d06403ee109cbeba980a95dfb7ccd43e48cbf9b134623f7dedf3213509` |
| demo-t0000-c0032.img.hdr | 534 | `014f582c68296ecebc0eb16f166b69d61d63bc620a108c2cda1b104779c6ecda` |
| demo-t0000-c0033.img | 614400 | `f09f639f1064e333843fd72a0d02f242ec1ee774ee3c77a272f8b60a21e1ae48` |
| demo-t0000-c0033.img.hdr | 532 | `899eb1236552458b1e6e23431ae660d062904af64fc4e9a6b5b6862b2509edb9` |
| demo-t0000-c0034.img | 614400 | `9b7517fa2ba3b4c0e6522bad02bdd88b42ba0aa76dd81770c311560ebeb73077` |
| demo-t0000-c0034.img.hdr | 533 | `fed84dd9827d4233d51842f237db6dfe44fd230508079fb2adb17237674e6099` |
| demo-t0000-c0035.img | 614400 | `b1924fbaaef2e3204d2a2620dc22db40cac387cc89672c3318352056e8a662a7` |
| demo-t0000-c0035.img.hdr | 533 | `6ecb6b586d09b8a7da7191fe9a52909d90589b0fa89c469697091fd0b1852eb4` |
| demo-t0000-c0036.img | 614400 | `b38d890843a579e0c802bce8be57283e2de2b7558056947b0b60f28cd1833de9` |
| demo-t0000-c0036.img.hdr | 534 | `d1c7f655deb33cb51ad9e054bcb32c2b20a0468b78d1cc17628f436e0f061239` |
| demo_truth-t0000-c0000.img | 1228800 | `e1d86532f55d629608a8db36a25b4fd7057003668a8b728e92a246129a1ffa81` |
| demo_truth-t0000-c0000.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0001.img | 1228800 | `d2ac78ccea6741bae3cbb51e033390c1001aafceee605a41f7f1591340f6e7e9` |
| demo_truth-t0000-c0001.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0002.img | 1228800 | `ca90d04146a6f7a85a7263892dc4ec83ff4b836ea694b2a9d8ed788477e8572c` |
| demo_truth-t0000-c0002.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0003.img | 1228800 | `d4d0acc9825496b40c7157310bdf21fcd75808cf0ccf6f803b9418e3085f7aff` |
| demo_truth-t0000-c0003.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0004.img | 1228800 | `f95e52a5df1977a351a041b9e92866e91a7ba73d6ed43ca6a81954b23e3709c9` |
| demo_truth-t0000-c0004.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0005.img | 1228800 | `4288b5baeecdee0a4cab31119ad965c99be3734c62bd4ae435cab00c7dff1265` |
| demo_truth-t0000-c0005.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0006.img | 1228800 | `f818103f74bfb3ec195c337e01e831fa78dafbb3c10814bfc3c46adaffaf49b1` |
| demo_truth-t0000-c0006.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0007.img | 1228800 | `27ccc047f9b9f9c440053493ed33c0dc6c489d8084fe03468347a4fea93c5ad9` |
| demo_truth-t0000-c0007.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0008.img | 1228800 | `8d8ee54afb4eee62a253a428c2d63835ac1b65abaf399dc481035d43f59d3f1a` |
| demo_truth-t0000-c0008.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0009.img | 1228800 | `8c1763bab7a3aa7e8d5e94259f81771cf8ae398876a36fb8f4c83e0b8dc414a6` |
| demo_truth-t0000-c0009.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0010.img | 1228800 | `d1a93580c0c2663cea8222577f9f8e9b889415ff237094b6e9c8d298adbb63c7` |
| demo_truth-t0000-c0010.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0011.img | 1228800 | `6a7b7f29739f12d93611d181427e9f472a9a9d7ed2fde51b8112df0d18ffd206` |
| demo_truth-t0000-c0011.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0012.img | 1228800 | `2b73ce2200ff19e3eac20d12e586888a5054a26f7d709f89f3326b9d41eedca8` |
| demo_truth-t0000-c0012.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0013.img | 1228800 | `03f964422eddba9abac59f794b8104a93383dd776e69a58678a7b4e649dd189d` |
| demo_truth-t0000-c0013.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0014.img | 1228800 | `46f46b4fb5aeab4f122bf90017610162e64940f80e8ce0e9487777f597281075` |
| demo_truth-t0000-c0014.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0015.img | 1228800 | `48dcefa0386fc9d4295cff96d6722896bdf629d368dc520e6b22619e3e4b8aa0` |
| demo_truth-t0000-c0015.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0016.img | 1228800 | `39312b36a46f2cec0c61f1a47d6987e7a990e1ee8689f923f04731c177640b98` |
| demo_truth-t0000-c0016.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0017.img | 1228800 | `6c0b623779e5431bfaa761bd6c5409d1de561b65fba377377795ee7101ddbc98` |
| demo_truth-t0000-c0017.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0018.img | 1228800 | `3b60d3a4bc5f8ba9648c043a3084b7dbe5dee7fb687af1fdb6450b26a2b63ae8` |
| demo_truth-t0000-c0018.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0019.img | 1228800 | `bf0493a21caafcce4eef887af8907a9a80adc1cd35d887326fd55da62259fd1e` |
| demo_truth-t0000-c0019.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0020.img | 1228800 | `130b437944f7d0d57714e19461413747d39e09da431a2a9f5ef85e6cced53d57` |
| demo_truth-t0000-c0020.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0021.img | 1228800 | `7ed121a25ad2654fd2ddde655810a4ea07c084e42b6e0207ecee354182c414d4` |
| demo_truth-t0000-c0021.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0022.img | 1228800 | `995e5b7997471af34073ac07ba6bb5389dfac33223758f933003462acbd91246` |
| demo_truth-t0000-c0022.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0023.img | 1228800 | `59d23d5102f94ab9c8dbd4e60b75db48f155d752b840465cb3b6a8eb45985ed1` |
| demo_truth-t0000-c0023.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0024.img | 1228800 | `8ff059d4b2ccd90d2aff4c17a360a4179db314340a7fd96e0e041828aae717ad` |
| demo_truth-t0000-c0024.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0025.img | 1228800 | `6a8283d0fda0a8d08ee0405c76efb47dd884a82880b8184d4c8c6db02c33e52f` |
| demo_truth-t0000-c0025.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0026.img | 1228800 | `9b9d1a109641faa6d8509995e50d6755b6b400ac964ed7674a50371312a88e11` |
| demo_truth-t0000-c0026.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0027.img | 1228800 | `0c3df4e553d9803f77ac281bc745a6fa4a36c56f34b701e0521236ce0705b727` |
| demo_truth-t0000-c0027.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0028.img | 1228800 | `309ef97ebaa23a4d4b87716d1b93165efe12c2c8cb8773267471c6c387b4258a` |
| demo_truth-t0000-c0028.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0029.img | 1228800 | `562354561b3b436dd5e18bfd2ef14f5955454c7fc62aa99e47e44877107add03` |
| demo_truth-t0000-c0029.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0030.img | 1228800 | `28c39d2933d810c459db8d5a80f815883b255f84c5974f02f01137a8ea3015a8` |
| demo_truth-t0000-c0030.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0031.img | 1228800 | `8988e1b7eff2ca61b4f4b0d89b9ebd48ea213f55b8fde072d873a4c2527c3790` |
| demo_truth-t0000-c0031.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0032.img | 1228800 | `3692bfa58531995432b58bd5cd0b61b8a056e1e3641afe033a44b7e103eb0e7f` |
| demo_truth-t0000-c0032.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0033.img | 1228800 | `49f2330d56f51ef18b10254dd170472bd747d4405468d4784f8f1fad106f0599` |
| demo_truth-t0000-c0033.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0034.img | 1228800 | `7d355172d8a2dd401b5f23442d9371b12083b5c0e8b065ad2620bc348238c1a2` |
| demo_truth-t0000-c0034.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0035.img | 1228800 | `6612c372dfb02f3d1d516e579bc356408fadf9612f4572c4721c173e638b1b76` |
| demo_truth-t0000-c0035.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |
| demo_truth-t0000-c0036.img | 1228800 | `367261e5375c3c1003279fb98bbd7b6ca1ece2e836e7c999b6c24460ad979e4e` |
| demo_truth-t0000-c0036.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |

### GenericMotion1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1843200 | `0eb70948edf27fe62ac7cf8516ca422fb97826dd4d1d7d84aada0ff32d598441` |
| demo-t0000-c0000.img.hdr | 556 | `7c151ea697c0561a4548dd282e6875849bbfc35e0bd296c148e16251af9ca8f3` |
| demo_truth-t0000-c0000.img | 1228800 | `0d4239ced33e8fb3b6bfc185c8770d55e7b35e1267c099bfff0f714893977736` |
| demo_truth-t0000-c0000.img.hdr | 270 | `efc1487469060d490405af8143d5fb6dd15e5db8162881c47cb438036ca31bec` |

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

### LensDistortion1 (demo.jsim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `4d8d65ab9226980a4ee4d8efcd02de5ccc394c66f426a0409ee4ab887e1946f7` |
| demo.img.hdr | 530 | `c6ae07439c2c9111beb2ae57f9dd24a3905dcb0e95d2ebb06bbd28f245b664b7` |
| demo_truth.img | 4300800 | `17dfbb1b5a555128fa67a57a1de35e1bca6d36d1afc822ed70b1bc5e6c71d103` |
| demo_truth.img.hdr | 368 | `e62d2f1056576a0b33f9fe7e250c4aa61ab60c8fbb06ef15ab637908ed8480a2` |

### LidarBounces1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 39585237 | `fea7d9d1e3ef1960badffec18bda26d2f5feeea1fcc881b8dc2a3d9d4735a331` |
| lidar_truth.img | 2350080 | `a3bfb5ebe7e8de0c8585fb5b3177d9a001816d38674b94b077001750440d299f` |
| lidar_truth.img.hdr | 424 | `a8989798fe9ee8bb17fe2ebed278248aa152b27803af336b67a68b98141c773c` |

### LidarRetro1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.bin | 215458 | `df956f2ebfca027f432e89b94d1ff41c391057f3871cd609caf0702610118054` |
| demo_truth.img | 171600 | `1d29ce572c67993208c42f6e515faefe3c6f01b3d19f84f786f89cccd5c9f979` |
| demo_truth.img.hdr | 436 | `9afde570779784d0f1463167b095d535339e871e1e7b4950ff09816cd26b19aa` |

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
| demo-t0000-c0012.img | 1843200 | `3d66d30885f1852778193fbe0816b6a42ab34a71fd82a4cc58155446dd185c25` |
| demo-t0000-c0012.img.hdr | 586 | `5925c40d098e4ab90aa679dbcf6e87af9f14e391f64b78d3e013fbc93d1256c7` |
| demo-t0000-c0013.img | 1843200 | `51bd9ab880e97d444345a7a1674fb752f9dbffbecb8af741409e469d0fe0c2d0` |
| demo-t0000-c0013.img.hdr | 586 | `fcb876258833d5b1ee1b693a9989fef8756a8472a75774bff182445e962b26d2` |
| demo-t0000-c0014.img | 1843200 | `e56242a0e6db3547ec2f3e9fb24bbe3fb41060be73968ceed20e1472f580ff55` |
| demo-t0000-c0014.img.hdr | 586 | `3ac9bdd42eedc305da4fbd7d4793554d22c3de31c22bf1b3fc21b100173f7f23` |
| demo-t0000-c0015.img | 1843200 | `f34762864215bf4ad4084e682b5e5c8d2628ba550b8e06a3a439ce89e78650e3` |
| demo-t0000-c0015.img.hdr | 585 | `8ac6cbd76941d0e9832f8cd16978ffa52f0b7232cb879fafefa3be290c7003c6` |
| demo-t0000-c0016.img | 1843200 | `73d8fb7c8c61db1cc24da44ab0525da8111b0170e86dad7939363ca850e76b05` |
| demo-t0000-c0016.img.hdr | 584 | `87edbccc7bdbae51ecb509fdfcdc38f43bea1154ec7e8f09d7c94e2fe0981285` |
| demo-t0000-c0017.img | 1843200 | `a82d4382a4667197f3a82c73a388d1519a47b83104808f8f4ffc0ef2457e7961` |
| demo-t0000-c0017.img.hdr | 585 | `d5246dfc9a3673a9bbf2bdcd7253f811a12f1bf14505110245eefebaff89d63a` |
| demo-t0000-c0018.img | 1843200 | `54b5a30e3d81530e243500940bcc1750c5b2b71bb9f41d3028b154415845753d` |
| demo-t0000-c0018.img.hdr | 584 | `20182a9d3bf37485818c6646695b5870b242fe76b3a1b8779273bfa9a1cb6e52` |
| demo-t0000-c0019.img | 1843200 | `34ef66df9cbd1325ebef0d84b269d9518ae5eebdf3323686307047e4ae5cd81d` |
| demo-t0000-c0019.img.hdr | 584 | `4a2bc51b5f6076ef2a72a64790c8b8a306bb108fceb6958f121e16c791ecbc04` |
| demo-t0000-c0020.img | 1843200 | `b552c6a8d745e503dd6e5476698af60a701c0080ee84a942dd1200755d172f89` |
| demo-t0000-c0020.img.hdr | 585 | `9b8c509bd4ff2b78a5c9aa00e28b99c812cfd6d21e6a82a3d2397e7d9db77a0f` |
| demo-t0000-c0021.img | 1843200 | `d3667ff2701f76978a7c9f6cc20258fb35697037761ea6903bde168e3756038b` |
| demo-t0000-c0021.img.hdr | 583 | `8c2003ea395ec11d6eb2af00b0e6da99915d3595ba228b58d08b5495a4bec16b` |
| demo-t0000-c0022.img | 1843200 | `c0646a3a13b795a112b5e783b5da7ef19aed255c8deb82d648316d781344fc53` |
| demo-t0000-c0022.img.hdr | 585 | `f9849333581b77cf396350cd13bb48206d1864e827e565c64574d8fc6b218211` |
| demo-t0000-c0023.img | 1843200 | `eaaa073a20f840ad45bd73424f4d8a7410143fbf75bc5b1a416068cb38ea4249` |
| demo-t0000-c0023.img.hdr | 586 | `53922ea86632b63fe702fb55b76ce1ba74d8f607a01f5b6c7e7c54a2331c64eb` |
| demo-t0000-c0024.img | 1843200 | `e6d96367d96350e41377082721a94c91f7ccfd2994bae70846cd7d439b82a2fb` |
| demo-t0000-c0024.img.hdr | 586 | `a06d047300752a7a666ddaaf0cb345dec06a715394c833e69ea0654c4ada4a28` |
| demo-t0000-c0025.img | 1843200 | `c0768304a42461484f19d05af44e4e2aa2510313d5e7c6fba54d4c87eaa6dbb7` |
| demo-t0000-c0025.img.hdr | 586 | `4a77dac10e8ea7bc573e6cd6791bc66548e327bfc3d98ffbeea209a8bbd6f322` |
| demo-t0000-c0026.img | 1843200 | `3e12150f8bbcfcebe6d97efcfb25d4c926b62cb11478a1ca7b4833bf109fa8f3` |
| demo-t0000-c0026.img.hdr | 586 | `3b62bfa3a629bc84006410f5f399f7aac864d08ca087671c2d4139f36046a4e1` |
| demo-t0000-c0027.img | 1843200 | `57e80cc47230c568021e8c8d318fcb30225a0e609b01806fb296fb4c8a29d5af` |
| demo-t0000-c0027.img.hdr | 585 | `719c2f9dbce6ea277c25e22c7b352822ff8e6a371a6cc663af1ca618390987d5` |
| demo-t0000-c0028.img | 1843200 | `fbf9b1cfe7dbf5cba1ce835522eb963ab07f2d0b4aab79e287dd73f813084333` |
| demo-t0000-c0028.img.hdr | 586 | `91a184b12f9659afbcf84f00185f40d5a868610007b1b057ae99f17603dff23e` |
| demo-t0000-c0029.img | 1843200 | `1b68118cd09d1f3847652cffb5153f58d89879569d684c84f4296fb4b14492c9` |
| demo-t0000-c0029.img.hdr | 585 | `81c26ccb4185b261fcb1d6b6b10f0e9979657437b3a9fc0fb7d3cf5a2ff527b1` |
| demo-t0000-c0030.img | 1843200 | `6b5c1361ea1cd57045675ec38a47f0f4e94cd36efce1df537ad365578866b164` |
| demo-t0000-c0030.img.hdr | 585 | `89ce8c154a0020916374b99d13ba6a565d6d83e2c0a539931bfc0e67f19fc8ab` |
| demo-t0000-c0031.img | 1843200 | `835ac58721a9200d46fc84e335111af7775f3854a49ed3bc9c4e68e8e8a88f85` |
| demo-t0000-c0031.img.hdr | 585 | `89e8a98a6f098b35982c06bad0deb35b12785d37d0cbf65e14d81e3b9976a214` |
| demo-t0000-c0032.img | 1843200 | `2346f2d992457099f6525557619145e2745d0b02aa7019360ff3754acc7c9427` |
| demo-t0000-c0032.img.hdr | 585 | `d1eb878382fec18f9c657a668d8c53171581d44e0ac0033ad2e93c28b79b58ae` |
| demo-t0000-c0033.img | 1843200 | `71a8b1d967dd36405f9a4052cd7961d5e13ceaacbcff087e967e160caec7ab9b` |
| demo-t0000-c0033.img.hdr | 586 | `4bfaded1f9748fa480ab3db812c6a65999001d973ec3290b58a0c986ba878901` |
| demo-t0000-c0034.img | 1843200 | `b48f70f79028f938a3a19b65aa0b1202f3e8d28a60d102fb95a81aa42ec39f0a` |
| demo-t0000-c0034.img.hdr | 582 | `1b026f07734a2dd189c7c7dea465308ae9339a7e1fa7e6e5094a5745549e9191` |
| demo-t0000-c0035.img | 1843200 | `46f181b1de7b67b115c3d94e535bb738b9b5493aa1fa84f248a1afc699d05a2e` |
| demo-t0000-c0035.img.hdr | 584 | `58aefbe4e499588d346b72eab4c371d76a8d903675647f4bf5695dd49ff9a52a` |
| demo-t0000-c0036.img | 1843200 | `d99d415b02cad23bf9d40520ba3a86dd69f7d5f6f6013de4042ed3fa93790b28` |
| demo-t0000-c0036.img.hdr | 584 | `23b55518a1ade8874f81baaa6e6290a559db396f85a388089cefb73ea8acad10` |
| demo-t0000-c0037.img | 1843200 | `0d2fcfa0427f94a3100f026b5b71e188ab9444185b015e312f145f8f1b3b2c37` |
| demo-t0000-c0037.img.hdr | 586 | `df50b9595e355df286f2cf72e86dfa6631cd7d5c65f4c8dd944740346bf26ec4` |
| demo-t0000-c0038.img | 1843200 | `65e5586dc6c645b75c7b4cc7d2c1e333094339e4aa34b3a296799b146a24aaba` |
| demo-t0000-c0038.img.hdr | 585 | `c45a4b3334faef63b93b952bf66dca8c5d34bd1b81af7621fad6522ec4a06dc9` |
| demo-t0000-c0039.img | 1843200 | `0a0449376edef4efe14bf4a80ac5726e93c6e9c88cf1b6080c802c3cfb5ed9a6` |
| demo-t0000-c0039.img.hdr | 586 | `3d75a03e4f9fe8b82983d21a363ae07f0e36abced1770b3f8df4913984bf93b6` |
| demo-t0000-c0040.img | 1843200 | `2bdda729d927f45dfe82219664fc13d997b24706d0b74cb60b35946999447e5a` |
| demo-t0000-c0040.img.hdr | 586 | `9c93c8148d8b6a00caaec31baec2b2473833a223cb437395b232f7350eade6ec` |
| demo-t0000-c0041.img | 1843200 | `5d19f89f5c147c6c15631facf5b7299bb4940fb93462d5ebf8289c3d40734804` |
| demo-t0000-c0041.img.hdr | 584 | `33f8c0a23d63d79f68378a68ecec07bc343b716fb12998b4d83c666a6dde0bdd` |
| demo-t0000-c0042.img | 1843200 | `a27f6ed6db5856e0c0142b934399245e823d6728d14bdf43a8f89ac15a2412d2` |
| demo-t0000-c0042.img.hdr | 586 | `6df390ccb3840c006748dd12b7fc414fd5c20be75b63c6e5d2a3192b044887cb` |
| demo-t0000-c0043.img | 1843200 | `8406c3d417085cd31ffad194717e30b8621befabdcbffb982572fafc6884ef17` |
| demo-t0000-c0043.img.hdr | 585 | `e1157c9e10c1ed993917772c006c015e8519c1167047df60d9f13202c7170887` |
| demo-t0000-c0044.img | 1843200 | `0eb077c3295bcea104372a152e1c305d0a3627b21c2bec1159c98b6654d537c9` |
| demo-t0000-c0044.img.hdr | 584 | `7d17ac1b1c4be166e9ba8e53051d6de00a4264f4e33a2242ca47241bfa555133` |
| demo-t0000-c0045.img | 1843200 | `8915fb320ad36e7a92a3c13f9a262886248e4fbfabf5dfb8ac505118c03bb908` |
| demo-t0000-c0045.img.hdr | 586 | `ea2f189f8835bb840b286e65dfb89832d44c35200412cfdf5a33f495abb6e491` |
| demo-t0000-c0046.img | 1843200 | `767fd0ed7ac06713314caee1bdfb6ec15069520ed4815c9e03987a01f9042346` |
| demo-t0000-c0046.img.hdr | 585 | `d97a8b3718663e73d005a8bdf7f61612dee0599fa9a839dcac69ae65b0f27c20` |
| demo-t0000-c0047.img | 1843200 | `80280f2852dc088ee1551b4e07b44997f464bbada1bec089f87d0625e6609d89` |
| demo-t0000-c0047.img.hdr | 585 | `812aceae5b9868d3b4452a01389db64139605d8d59496ba3095a315cd381e5ae` |
| demo-t0000-c0048.img | 1843200 | `135b4e31a32fa1fb0ea48ff99acebaf888183c5ec62150ce4d22c282a8f56679` |
| demo-t0000-c0048.img.hdr | 586 | `fd972ebf99072a0b5b60465388faf39ed612296de7e9ca9f89957e62defe9380` |
| demo-t0000-c0049.img | 1843200 | `500015d8d84808dbafae29523574e5a3b3fc541a21393ffcebaad44b4c1e4800` |
| demo-t0000-c0049.img.hdr | 584 | `6899468623f23ac8eb0ec2168220f225db7c302fca40c486e391c6616b92471a` |
| demo-t0000-c0050.img | 1843200 | `3278ed566d62a4112bcb9b956c81fdc57bfe38b4f27441e5cd2292078a45efdb` |
| demo-t0000-c0050.img.hdr | 585 | `0b15ca50f98f5d71b3a9072d724c9fc03bb8cc6e74417cb0a65c72739f48a1fa` |
| demo-t0000-c0051.img | 1843200 | `f15157e5985ce86c8ea191a736838ae1f7585198fc974a703847bf0bb57f0392` |
| demo-t0000-c0051.img.hdr | 586 | `33672cb0a58c6e02bee25ba825262754965d9aefc3d9fe7eeb052399be7aa27b` |
| demo-t0000-c0052.img | 1843200 | `b008ea2a7ef4f8a3dc62b4edcbc0ce8f900c8439608d21e9979214c776abcd98` |
| demo-t0000-c0052.img.hdr | 584 | `12d05c23649c389208c2181002e37cebdaf42051590c95f7583d2a62752b8642` |
| demo-t0000-c0053.img | 1843200 | `9281fba9cdb01170158e57a8bf23dbde6da1b788df6329ec7d27f54e208c03bb` |
| demo-t0000-c0053.img.hdr | 584 | `d07bfc083c71f44d9772eae29247e6709ce7c1c8f6b0bb1a65e6f231891812fd` |
| demo-t0000-c0054.img | 1843200 | `5f0469500bce078e9d25511341af0889adfb0a71ee2832307642466eacb7e6c2` |
| demo-t0000-c0054.img.hdr | 586 | `11f895ce04e6ac9f620a82115b8ee49e7531e8b99d18050cd2345d9b6018aa3c` |
| demo-t0000-c0055.img | 1843200 | `8408208bf1eb57fa7a24eac9540755bf89166f1e89c4bd6d3ae03351bbf770e5` |
| demo-t0000-c0055.img.hdr | 584 | `a78ddcf4b4504d18f96fddc3e51f99fc3ea3a1261f430886837ce8af9c5b28f7` |
| demo-t0000-c0056.img | 1843200 | `6e9ce572b3ab44ef2447561a2cd353be14d5da5dc9ef0454532448456495d0e3` |
| demo-t0000-c0056.img.hdr | 586 | `4cae745fa0429590d9bae3e2b76629a018c37786e68b8e622d054b838bfd1487` |
| demo-t0000-c0057.img | 1843200 | `0c15a62d8083b0a358eba1d645f9bab1663f749cf0696f48b04cbd4e0e800554` |
| demo-t0000-c0057.img.hdr | 586 | `5c907aa9fb0c3eb57f335e40ccc2c4af2b291b5803f7390caafe0e0e8231a57d` |
| demo-t0000-c0058.img | 1843200 | `5c1283760df8703c1a76aef057a493dc63d5d36cf2e7c69d69b704352a29651d` |
| demo-t0000-c0058.img.hdr | 585 | `0570cadb3604e653970699fc6612bf7008e306effcdfe9ca61711255c943de0f` |
| demo-t0000-c0059.img | 1843200 | `74816d9093a727736b3c42336d57f31921c8de53ecba13bf4bce68a21dafca70` |
| demo-t0000-c0059.img.hdr | 585 | `36647ed658ddc7e2c3d78402bede7a42014d0c7e6a890f0d2ce41defa3ec9440` |
| demo-t0000-c0060.img | 1843200 | `285d6f6f078ef4a5633dec6eda531fd7f67b149c1ca9ea18cd66e7a2aee0733b` |
| demo-t0000-c0060.img.hdr | 583 | `577d0ebbea386ef49a3158da74d86fe21a2aa06fcb07f5826017c0738d79dada` |
| demo-t0000-c0061.img | 1843200 | `cec9bad51c0f98ce2832877858fff21e6c9083cbb732907f0aa4ad9086a57acd` |
| demo-t0000-c0061.img.hdr | 586 | `72be1226e19207246b872becb5817035741ec70355d127996ee412345cfeff5d` |
| demo-t0000-c0062.img | 1843200 | `f63afa26e562b3c79ae54225a38e8f59a9f5674167994a687adc757809c3d125` |
| demo-t0000-c0062.img.hdr | 584 | `e6c04cc653809120ba80d93107f94c28bbc42b43d0dc2b4816edb4058cb9fb09` |
| demo-t0000-c0063.img | 1843200 | `8b4b1e08a1ff2f319fd2251912d2453178cebc941f99dadfe8fcaf5fb4898d60` |
| demo-t0000-c0063.img.hdr | 586 | `eea1cd55ea91bc3f4e1c1a7ee9efb32d584616eae7f8edec48d79fe89fc5f292` |
| demo-t0000-c0064.img | 1843200 | `7791b877e789c687d979bf9ce763e76aa0d3f90dd71ed920af6db935253ccbcb` |
| demo-t0000-c0064.img.hdr | 586 | `418e5da7cf7bf7f69433e1eb72f41ea2e92dc5252106559611853cf1e6984c61` |
| demo-t0000-c0065.img | 1843200 | `56c168301076ff076ec9015bbefc6e172f0c83965aed6416535192d63e36c962` |
| demo-t0000-c0065.img.hdr | 585 | `215d8751aab287e7ee5b2344e2eb5165529446b7ec0095fe1c3d3fd7b0b37c9f` |
| demo-t0000-c0066.img | 1843200 | `5cb701caece2d69a1948103e45601d5d923b9963c1e8319ee38d934de863e280` |
| demo-t0000-c0066.img.hdr | 586 | `564c446a98c68f32f81ca2770a7f88636822758f072e6b42927d96186bedfc6c` |
| demo-t0000-c0067.img | 1843200 | `0b0b82d4b9dac0b95d77dc797d990e430b1d62e2961065a1767c10071a3c0d2a` |
| demo-t0000-c0067.img.hdr | 585 | `dca9216816654f5593443d63200d60f66903f9d3efd085bf490f1401dd2bd8bf` |
| demo-t0000-c0068.img | 1843200 | `607786cb10467dd18bcedb8b8d7170885ebf5f916a6f06e8a628898b0f712e2d` |
| demo-t0000-c0068.img.hdr | 583 | `b0244c46bf25f87d2025d1162f15ccd55fdbf5fad36175f5abb581a5991fbb39` |
| demo-t0000-c0069.img | 1843200 | `857d6920ab0bc9f4287093f805e0024ca62e38993af264b8239cb8edbb678fb8` |
| demo-t0000-c0069.img.hdr | 585 | `33f5375ba2f4e5e9ad89d3169745f738e8154108d84276a5d466fddecdbfc563` |
| demo-t0000-c0070.img | 1843200 | `281729cf70babf5c12388ee557aa9c2db305e30744c31bd84b7df38770d1c33f` |
| demo-t0000-c0070.img.hdr | 585 | `2aecea1499d5812eadef2a7dac0060e0c8c9c04db5aef39f54178fe2439086ea` |
| demo-t0000-c0071.img | 1843200 | `40fa4e7f39daa750161afc1214dd7908daeb40c3388ec38324fb26c0a896584b` |
| demo-t0000-c0071.img.hdr | 586 | `0ab8a341618010121df913eb54c03c154f52e18f432adde6ca213f4f445580b7` |
| demo-t0000-c0072.img | 1843200 | `164f24d8ed57e55f238d1ccc72007e63aaeff15427c95600bbbb47758761a713` |
| demo-t0000-c0072.img.hdr | 586 | `942c2cf9bfbed8926cba5384d21fb928e3dd848dc516fa0a1eef96a94c958fd0` |
| demo-t0000-c0073.img | 1843200 | `4a8980c9e01928cce1bdcad7061d66edea1afb8159bde2e441ce03265ea3feff` |
| demo-t0000-c0073.img.hdr | 583 | `6e4ce0a129e9d32fac800ab4e521ded4ef241ff02fb831008d197a3ae431fb56` |
| demo-t0000-c0074.img | 1843200 | `5f6ca4f0c8795b4a9b870ff065c78e8e7d5b9db49eecff6a1cba7c206cb66da2` |
| demo-t0000-c0074.img.hdr | 586 | `ba1fd5b56ddceea2a7ff4340905eedfe1acadd8a0ca852ac2d891c43279150a6` |
| demo-t0000-c0075.img | 1843200 | `86ee12476618cd36b9eea5a20a8cb4441aede80c17b343642a8894d14a981c7d` |
| demo-t0000-c0075.img.hdr | 584 | `2e67db9718ce85e7c1679c4896676c85d2f68d3e6ba63a4e5f368ae1c189a2b9` |
| demo-t0000-c0076.img | 1843200 | `404507c3382f19e4918f42703e163783144ef5e2c516eab2764df7760404012b` |
| demo-t0000-c0076.img.hdr | 586 | `eb3bcaa2cdc27b243d613b456f0ba9454b81ce05bf6caf6813098cc0ba886688` |
| demo-t0000-c0077.img | 1843200 | `b625dbd70da978ee8d7334626e707283bd0c22154f541ffb482fe1c8b204394a` |
| demo-t0000-c0077.img.hdr | 584 | `f647a802d31bcc105d815d217d58f47a218a65acfabb7ed0ef26be6190ef92ea` |
| demo-t0000-c0078.img | 1843200 | `e5d892b3f6d86876c2c053b756212d58abd2886416ea08f522f626dc9d585e89` |
| demo-t0000-c0078.img.hdr | 584 | `8b3bd2a5afe6e24f4cf10e3308bb87e848490bf74cde92613d19a7b2cffad688` |
| demo-t0000-c0079.img | 1843200 | `6055b9b72393a0c2f6650b47fc6945e124d0caddfb4b988e85c8e58e4c9c591d` |
| demo-t0000-c0079.img.hdr | 586 | `4753f8186e307a838dd021ae17e9bdbbcc2128230514a6854fdb39ced767af23` |
| demo-t0000-c0080.img | 1843200 | `2933131e105a9913dfd1dfbcd05dd72b1dd02a1959aed901d2df54ae117eb2ef` |
| demo-t0000-c0080.img.hdr | 586 | `eb82e4994d764b28c8da1f8330c5c761e5be5f4a8c26a016b30351456d578900` |
| demo-t0000-c0081.img | 1843200 | `3548c829ac4cd20cc2140840f54472835a02eee07b0994f22d6af4709ba57d7e` |
| demo-t0000-c0081.img.hdr | 586 | `ff843127a484b414a7ca1dc0e80fc070908e4573e08ff50e89a4354c98acfb89` |
| demo-t0000-c0082.img | 1843200 | `ec4ef0d7a19fb6ba3de6d2ed4e07ff19c3f244a46810ac634dce6663ad7c808c` |
| demo-t0000-c0082.img.hdr | 585 | `80d00d7ce0fcfb74a24b223146b01dab7f84985b0ea14b83ae2cf9b7e227091c` |
| demo-t0000-c0083.img | 1843200 | `e1d8fe650d69a9c7f54dae754ca959053bf7c64f59a6dea8b8c16b8b4b108243` |
| demo-t0000-c0083.img.hdr | 585 | `5de8aae819575d7bbdbf158d51abdfb0f1a71744300c57df9fd56ecbb8397f2c` |
| demo-t0000-c0084.img | 1843200 | `201a244837917918152970b450f6d03b53476c7ab74c8c7ca91daef5bf1ab1fb` |
| demo-t0000-c0084.img.hdr | 585 | `8c20ccbbfe9b893dc79a60499cf122b7e61fae6caadb07ad416d0b8464f2fa04` |
| demo-t0000-c0085.img | 1843200 | `58c6963706fad578b2ec8de564557b95a60a4c06769db21a62ecb4a53754d126` |
| demo-t0000-c0085.img.hdr | 585 | `cd0bd78195ce0a487fa16fa59629ffb09164bb9a997ab376e511e45b7de6c606` |
| demo-t0000-c0086.img | 1843200 | `6dca39f9293484984ba2d2e53fff99d1e4585410bcf41967126e26a52c13633c` |
| demo-t0000-c0086.img.hdr | 584 | `293d9b7ab6fafac22f8868d53f0553fa86d91510913c3eab5ae3f97a4c88ff08` |
| demo-t0000-c0087.img | 1843200 | `e1d1fd9db5c9dc483bebc0d07226a9f8a18f110d9b12d690f79d92f5cdfea66d` |
| demo-t0000-c0087.img.hdr | 585 | `3585b014d2d943b14e520cef4a9f908caf0113ab6ac126cf3e02dff392e67781` |
| demo-t0000-c0088.img | 1843200 | `8bd64b1d788a31ab4549666bf8831dbe77925347ff5d9424b3c8bd0654590865` |
| demo-t0000-c0088.img.hdr | 586 | `4a99b651a91084fa446688495048053c5e91e210e05619a3ae1482c10532786a` |
| demo-t0000-c0089.img | 1843200 | `bfc618e4993261dfdb39b8465433e3d3c3a6aebe097213024831b09fc07f289b` |
| demo-t0000-c0089.img.hdr | 584 | `9da1aef0a31b14055e027c1e7750416acba03826690dd85ce5b8a9cbc62ac622` |
| demo-t0000-c0090.img | 1843200 | `7100d8254c336e49ea0243400bd8da9981c4a7e18303215367f98c58fd3a7372` |
| demo-t0000-c0090.img.hdr | 586 | `fca7ed9fad3dd22745490ea688113fb619ee9144fa03f7f2719262003193dfbe` |

### UvMapping1 (drape_map.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 614400 | `e0de69dd81c57ffc6f1bb7705ba0f3d25090413af084c79dc95cf7e9cdf41521` |
| demo-t0000-c0000.img.hdr | 529 | `59671ad00a082f8b4342a07d7781925f1e88c5ce74b612e3bd5c79c71806672e` |
| demo_truth.img | 5529600 | `4e210c69ad155d82927616127266fdeb71cbf93a01d69a94b123f452dbcea309` |
| demo_truth.img.hdr | 424 | `4b745f0ee57c6b55010b1fe86420cb4b7540df464c3e2b8694942ab2a0ae7597` |

### VertexNormals1 (demo.sim)

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 614400 | `4ac997322f4243987a5e08a4af5c6a1274eb6d65a70e1b2a63cd552b8895d307` |
| demo.img.hdr | 525 | `800311a475ddf1d7826d766b887bf3c4ed50b367c96c028975e80ad72507dd83` |
| demo_truth.img | 4300800 | `d45d428ab7e7da33f8cedf9ed90b3eed6a5e1acb7e81194bc59c000180ff722c` |
| demo_truth.img.hdr | 368 | `e62d2f1056576a0b33f9fe7e250c4aa61ab60c8fbb06ef15ab637908ed8480a2` |


<!-- sweep_demos: end -->
