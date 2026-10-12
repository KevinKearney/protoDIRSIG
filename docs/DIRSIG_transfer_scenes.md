# Scenes Kevin transferred: survey, layered comparison, hashes

Kevin uploaded a folder of DIRSIG scenes and parts to `/home/kevin-kearney/dev/DIRSIG_transfer` (2026-10-12): scenes, platforms, motion files, atmospheres, a Tahoe SWIR demo scene, AUROR material and training PDFs. This document records what the folder holds (paths and hashes, not bytes), what DIRSIG 2026.38 and the SDK can do with each part, and the layered-against-pass-through comparisons (round 32). The folder was read only. Nothing from it is copied into this repository.

## Survey

`python scripts/survey_transfer.py <root> --map-absolute` reads every `.sim` and `.jsim` under a Documents-style root (`scenes/<scene>/shots/<shot>/`, with `atmospheres/` and `platforms/` beside `scenes/`) with `survey_demos.py`'s own reader. A directory stands in for the demo zip, so each verdict and its causes are the demo survey's (`ready`, `near`, `far`, `refused`, `unparsed`; `docs/DIRSIG_demo_coverage.md` states the rules). With `--map-absolute`, a reference to the author's machine (`/Users/<name>/Documents/DIRSIG/<rest>`) resolves to `<root>/<rest>`.

**The transfer folder: 52 simulation files, all `unparsed`, one cause.** Every one names a `.scene` file that is not in the folder: no scene in the transfer holds a `.scene` file or a `.mat` material file. Without the scene description nothing can be compiled or rendered, as authored or layered, so no transfer scene is `ready`, `near` or `far`.

| Scene | Simulation files | Scene files they name (none present) | Other named files absent | Also in the install |
|---|---|---|---|---|
| foxbat | 15 | `foxbat_day.scene`, `foxbat_night.scene`, `foxbat_take_off.scene`, `foxbat.scene`, `inventory.scene` | `hsi_pushbroom.platform`, `simple.atm` (hsi_pushbroom), `640x480_cie.platform`, `classic.atm`, `night.options`, `04_jul_1300_2560ms.tasks`, `rgb.ppd` (stereo) | yes, complete: `Documents_Folder-07-Feb-2024/DIRSIG/scenes/foxbat` |
| MicroScene1 | 20 | `microscene1.scene` | `vehicles.json` (Chips) | no |
| MegaScene1 | 8 | `tile_1.scene`, `tile_1_2_3.scene`, `tile_1_cars.scene` | `t72.json` (chips) | no |
| refinery | 4 | `refinery.scene`, `refinery_terrain.scene` | `../../atm/uniform.atm`, `../../atm/classic_mls.atm`, `rgb.platform`, `modtran.atm`, `rgb-static.tasks` | yes, complete |
| urban | 2 | `summer_day.scene`, `winter_day.scene` | `uniform.atm`, `rgb.platform`, `simple.atm`, `gmapd.platform` | yes, complete |
| forest | 1 | `forest.scene` | `rgb.platform`, `rgb.ppd` | yes, complete |
| LidarJungle | 1 | `hilly.scene` | `rgb.tasks` | no |
| Trona | 1 | `trona_sar.scene` | `spotlight_200mps_20deg.ppd` | no |
| warehouse | 0 | (geometry only: 32 `.obj`, 20 `.gdb`) | — | yes, complete |
| RITBusLoop | 0 | (geometry only: `.obj`, `.glist`, 7 bundle `.mat`) | — | no |
| Tacoma | 0 | (bundles and one shot image) | — | yes: `Tacoma-08-Apr-2022/Tacoma`, byte-identical files |

Five of foxbat's simulation files also name files on the author's machine by absolute path (`/Users/scottbrown/Documents/DIRSIG/atmospheres/simple.atm`, `.../platforms/640x480_rgb.platform`, `.../platforms/640x480_cie.platform`), and MicroScene1's `Diurnal/slant.jsim` names a MODTRAN installation there (`/Users/scottbrown/pkg/Mod4v3r1/Mod4v3r1.exe` and its `DATA`). These are DIRSIG's own Documents-folder scenes, written to be installed at `~/Documents/DIRSIG`. The transfer's `atmospheres/` and `platforms/` are that folder's files: `simple.atm`, `classic_mls_rural_23km.atm`, the two `uniform_*.atm` and both `640x480_*.platform` are byte-identical to the install's copies.

**The transfer as a subset of the install.** Every file of the transfer's foxbat (117), forest (27), refinery (17), urban (33 of 34; the 34th is a README) and warehouse (52) is byte-identical to the same path under the install's `Documents_Folder-07-Feb-2024/DIRSIG/scenes/`. The install's copy also has the files the transfer lacks: 89 more for foxbat, among them its `.scene`, `.mat`, `.glist` and `.obj` files; 45 for forest; 156 for refinery; 79 for urban; 119 for warehouse. Tacoma's 14 files are byte-identical to the install's `Tacoma-08-Apr-2022`. The transfer adds nothing to these six scenes. Its own content is MicroScene1, MegaScene1, LidarJungle, Trona and RITBusLoop, and none of those has a scene file.

**The install's complete copies** (the same survey over `Documents_Folder-07-Feb-2024/DIRSIG`, 38 simulation files): `ready` 8 (forest `rgb`; foxbat `basic_rgb`, `ka27_single`, `ka27_take_off`; refinery `nadir`; urban `day/summer`, `day/winter`, `space`), `near` 13, `far` 13, `unparsed` 4 (foxbat `slant.sim` names `640x480_cie.platform`, which is not in the folder; foxbat `plane_chips.jsim` names `inventory.scene` and `stereo/rgb.sim` names `foxbat.scene`, neither present; refinery `rgb-slant.sim` names `refinery_terrain.scene`, not present). The `near` and `far` causes are the demo survey's: classic radiative transfer, `.ppd` waypoint motion, an options file, several focal planes, non-imaging sensors (lidar, radar), a ChipMaker or OrthoImage plugin instead of BasicPlatform.

## Layered against pass-through

At most four scenes, cheapest first, one render at a time (`docs/DIRSIG_layered_comparison.md`, round nine, holds the numbers and digests):

| Scene (simulation) | Source compared | Result |
|---|---|---|
| foxbat (`shots/basic_rgb/basic_rgb.sim`, 640 x 480 RGB, nadir from 5000 m) | the install's complete copy; the simulation file's two absolute references rewritten as the same files relative to the copy, in both forms alike | differs by two listed input differences: dirfm's six-decimal Euler angle (`4.71238898` written `4.712389`) and the scene compile. At the default thread count a repeat of either form changes every digest (0.09 to 0.10 % of pixels), and the demo's angle alone brings 3.70 % down to 0.16 %, within that noise. At one thread, the demo's angle plus the pass-through run's compiled scene gives the pass-through image and truth byte for byte. |
| urban (`shots/space/space.sim`, 512 x 512 RGB from 120 km) | the install's copy as shipped | byte-identical, image and truth |
| forest (`shots/rgb/rgb.sim`, 1024 x 1024 RGB) | the install's copy as shipped | stopped: the layered and the same-seed pass-through renders each passed the 150 s render timeout (cancelled) |
| MicroScene1 | the transfer (the only copy) | stopped at the survey: `microscene1.scene` and every material file are absent |

Unexplained differences: none.

The comparison script needed three changes to read these scenes, all in `scripts/compare_layered.py` and none in the SDK: a directory source (`--source`), and two older `.ppd` position forms in its pose reader (`<location type="scene">` in foxbat, `<scenelocation>` in urban; DIRSIG's demos write `<location frame="scene">`).

## The AUROR material and the other parts

Each file is judged current (DIRSIG 2026.38 reads it), stale (2026.38 reads it, but a newer or corrected version exists) or unusable. "Read" is DIRSIG's own dry run: a completed space-to-space job (`s2s-hyperresolved-r100km-...`, round 32) re-run with `dirsig5 --dry_run` and its platform replaced by the file. Every platform below exits 0, so 2026.38 rejects none of them.

| File | Judgment | Evidence | Catalog asset? |
|---|---|---|---|
| `platforms/AurorNIRDetector.platform` | current | byte-identical to the library's `platforms/AurorNIRDetector/AurorNIRDetector.platform`, rendered in every round; dry run clean | already one |
| `platforms/AurorPlatform.platform` | current, with a warning | dry run exits 0 with "Channel is truncated by the bandpass" for both channels (`NIR Detector`, `SWIR Detector`; bandpass 0.7 to 1.6 µm); no `aperturediameter` or `aperturethroughput`; byte-identical to the earlier received copy in `notebooks/dev/AURORA_ref_to_delete/` (not tracked) | no: a two-channel platform with no aperture, superseded by the generated AUROR platform |
| `platforms/AurorHSICamera.platform` | current | dry run clean; a 500 x 500 camera, 0.4 to 2.5 µm at 0.01 µm (211 samples), no aperture; byte-identical to the copy in `notebooks/dev/AURORA_ref_to_delete/` | candidate: a sensor-spec for an HSI AUROR camera would need its spectral response and optics, which the file does not state |
| `platforms/DeepScanSWIR_512.platform` | current, with a warning | dry run exits 0 with "Channel is truncated by the bandpass" (`SWIR-1`, 0.9 to 1.4 µm); a 256 x 256 array despite its name, focal length 360 mm, aperture stated | candidate: the library has a DeepScan NIR sensor-spec (`deepscan_850_306_nir_1280.yaml`) and no SWIR one |
| `platforms/640x480_rgb.platform`, `640x480_wv3.platform` | current | byte-identical to the install's Documents-folder copies; foxbat renders with the first | no: install files, referenced where they are |
| `motion/AurorMotion.ppd` | current | byte-identical to `tests/fixtures/auror_ref/motion/AurorMotion.ppd` (the received AUROR reference the tests use); writes `<location type="scene">` | no: the SDK generates motion |
| `motion/NoMotion.ppd` | current | a single static pose, the same form | no |
| `atmospheres/fourcurve_full_spectrum_10km.hdf`, `_100km.hdf` | stale | byte-identical to the install's `FourCurveAtm_Databases-25-Aug-2025`; the install's newer `FourCurveAtm_Databases-15-Feb-2026` has different bytes for both names (and adds 20 km) | no: install data; FourCurve is not built (`docs/DIRSIG_demo_coverage.md`) |
| `atmospheres/simple.atm`, `classic_mls_rural_23km.atm`, `uniform_diffuse.atm` (and its copy `uniform_diffuse (1).atm`), `uniform_direct.atm` | current | byte-identical to the install's Documents-folder copies; foxbat's `simple.atm` renders (its `<turbulence>` is the one input the layered form drops, and it was measured not to change foxbat's image) | no: install files |
| `_AUROR (RJ stuff)/jsims/result.img` | unusable | 422,000,000 bytes, no ENVI header, no simulation file beside it; the size matches a 500 x 500 x 211 cube of 8-byte values, the shape `AurorHSICamera.platform` would write, so it is an output, not an input | no |
| `_20260720_KevinSWIRDemo/scenes/tahoe` | current, partial | `geometry/lists/terrain.glist` and the ten `materials/emissivity/*.ems` are byte-identical to the library's `scenes/tahoe/`; `maps/material_map_small.pgm` and `maps/texture_map_small.pgm` (54 MB each) are the two files the library's `tahoe.scene` names in its class map and texture map, both `enabled="false"` because the library does not hold them; no `.scene` or simulation file | candidate: the two maps, as uncommitted library assets (`assets.json` names install archives as sources today; a user-supplied source would be a new source kind) |
| `DIRSIG_training/*.pdf` (8) | — | training slides and a schedule; reference material | no |

## Reference paths and hashes

Root `/home/kevin-kearney/dev/DIRSIG_transfer`. Directories are hashed by `dirhash/1` (`manifold_contracts/README.md`), files by sha256. Sizes in bytes.

| Path | Kind | Files | Bytes | Digest |
|---|---|---|---|---|
| `DIRSIG_training` | directory | 8 | 22,094,185 | `sha256:39c93f2830275582eeff4a432372c1a92f010820d7e5461a4becf92bd0c945d3` |
| `_20260720_KevinSWIRDemo/scenes/tahoe` | directory | 14 | 108,881,188 | `sha256:e30898648b9b55b6f0c5573827ad3ca520672df0a54037103e73546cb7db07ce` |
| `_AUROR (RJ stuff)` | directory | 1 | 422,000,000 | `sha256:00d94adb0667b42808dd2284de9decb9304dd18c1baf8b17a01eef438aedcc7a` |
| `atmospheres` | directory | 7 | 225,616,199 | `sha256:22cc20db377628ca607e3864e01f347e016f67a9f27336d748872fbf28ebf326` |
| `motion` | directory | 2 | 1,339 | `sha256:a7338c0c11628f3d9f71225aad5700e49d8199bd3257967f12c35f109dce41c9` |
| `platforms` | directory | 6 | 1,252,357 | `sha256:27cf7b13725c60e00c7d969f935a7c5220c3f3504dee8c86c54ac274e2cc03dc` |
| `scenes/LidarJungle` | directory | 42 | 244,745,952 | `sha256:f09a0cf2244c2a0c83c43144b4df66aae72d8bb0f0651b79eccc46d481556407` |
| `scenes/MegaScene1` | directory | 259 | 906,627,999 | `sha256:dc9b54baa86492be85ecb2e74bace853e888e725df71bf018e3f75d28af819c2` |
| `scenes/MicroScene1` | directory | 141 | 428,094,697 | `sha256:5e2618e62c30aec64d274311e49800c26ff214b3870923a3c815004772f4e395` |
| `scenes/RITBusLoop` | directory | 53 | 27,128,991 | `sha256:fdcb63243b090f8f0796cca07949fd41c9425dd65b537497f5f612c69426af14` |
| `scenes/Tacoma` | directory | 14 | 12,407,524 | `sha256:dc618ece8adf800d327c01c3dfbe50cf1ffb9085b1300624f87a43e136a03036` |
| `scenes/Trona` | directory | 157 | 48,658,139 | `sha256:de6ace9d5ad45d2be53913c6ab93a08225058a72ece0cbc9b4b70e529638b84d` |
| `scenes/forest` | directory | 27 | 1,971,418 | `sha256:2eb71a6a298556cad10b4d4daa9b708668d5bcfa435ef18c45fed3943956d6aa` |
| `scenes/foxbat` | directory | 117 | 59,025,405 | `sha256:2a3ebdc080326459b732e49830d53b674229d8386a3ddf4a6cf40b88eb744cd2` |
| `scenes/refinery` | directory | 17 | 6,156,792 | `sha256:b22dfc30d22c9e516becfdbca0f37b6b607c04b0eacfc60b9be9a02965c415f2` |
| `scenes/urban` | directory | 34 | 17,957,939 | `sha256:431511be7e8f2deee5be3c9f9f118e8c2719193c8edd0530272cbd6763f163d2` |
| `scenes/warehouse` | directory | 52 | 215,176,271 | `sha256:b642afdf0e64bbb6d09c821e79bcb6281ffcfe972057897153d103d8328dd1b5` |
| `platforms/640x480_rgb.platform` | file | 1 | 149,692 | `sha256:40a5af45927e00f556a471720deda0ec93507b145cb493316c69c93a83f7e64c` |
| `platforms/640x480_wv3.platform` | file | 1 | 1,083,822 | `sha256:d8c5be31b58843b4cf410522147929aaf0d052294ccabd7188f0ba6c010edee1` |
| `platforms/AurorHSICamera.platform` | file | 1 | 3,001 | `sha256:894bca5ac3fe631596440400aac315637d991a1ff3a6f4145a9db51dcd358915` |
| `platforms/AurorNIRDetector.platform` | file | 1 | 7,707 | `sha256:bed58062f31a1e21945ad357dc36ccfc9e88b5fd14ec4e365a42d2f4df4b2515` |
| `platforms/AurorPlatform.platform` | file | 1 | 4,166 | `sha256:e4dfb772b86bfb8315d35337023d89749d8a44a302d866f2a409de163970dd59` |
| `platforms/DeepScanSWIR_512.platform` | file | 1 | 3,969 | `sha256:167e9fef535d3e265de4dca87199362ac47bfc8582704ef80f9e7f6ff09b8a6d` |
| `motion/AurorMotion.ppd` | file | 1 | 677 | `sha256:b0e9bc824c1a26d1235375a84b27b06681c1dafb67634e0a3e35fd1d7a1023f7` |
| `motion/NoMotion.ppd` | file | 1 | 662 | `sha256:2572537e3e2fc5705f2b89da5bfea97700bf29b2ff56bf07116259ad0f2fe11a` |
| `atmospheres/classic_mls_rural_23km.atm` | file | 1 | 1,207 | `sha256:245d450e33bfd70a280de56bfb367ec7b82fa0acb0709d6b851ce9ed3daf1779` |
| `atmospheres/fourcurve_full_spectrum_100km.hdf` | file | 1 | 128,877,756 | `sha256:1bc67799dafb9c4e6721f5b07d89549675f0aaf8a44189a7553475be681eaba0` |
| `atmospheres/fourcurve_full_spectrum_10km.hdf` | file | 1 | 96,735,227 | `sha256:3b2bfc0440533e600e0cf018eb3d99c7355b5864f76adafe386ca5365498c827` |
| `atmospheres/simple.atm` | file | 1 | 479 | `sha256:9900868cf152eaabd4462a1325b22f7ebe1fe194d0e6dc0890f44ade1567f487` |
| `atmospheres/uniform_diffuse (1).atm` | file | 1 | 510 | `sha256:7b95fe214525d5bef199cfed7f5d5446670db708a6112fb0c2014197c3b22b84` |
| `atmospheres/uniform_diffuse.atm` | file | 1 | 510 | `sha256:7b95fe214525d5bef199cfed7f5d5446670db708a6112fb0c2014197c3b22b84` |
| `atmospheres/uniform_direct.atm` | file | 1 | 510 | `sha256:5bfd71096f77e6d45c1ec7fc6423bc9b7e1af1e3570398a824f0e3ebfaf75261` |
| `_AUROR (RJ stuff)/jsims/result.img` | file | 1 | 422,000,000 | `sha256:1e14b9a483c650b94992b68227fdae6c053be9a51d50bdc896a9676bbbf1db57` |
| `DIRSIG_training/03_Technical_Overview.pdf` | file | 1 | 4,050,283 | `sha256:b687c860dbd37a5bfceb6cc9a805eb0436d98092be6dd249b93f49a54b67a543` |
| `DIRSIG_training/04_Basic_Sensors.pdf` | file | 1 | 5,902,424 | `sha256:4d26580d01e95f04262712ac6fc23ca5ace6bec12429592f502a9e2f81ca248f` |
| `DIRSIG_training/05_Thermal.pdf` | file | 1 | 4,288,559 | `sha256:8ba36d39867388bdcf527d72a6270c3aacce50a2b5484cb9974c9ce94bd6a705` |
| `DIRSIG_training/08_Atmosphere.pdf` | file | 1 | 4,173,804 | `sha256:cb40b0051c3e2e01bbb3939ee7e71f06dc4f41849bc980b78af5d54137e1928c` |
| `DIRSIG_training/09_Installation.pdf` | file | 1 | 1,034,832 | `sha256:fa90086dff6be5c9b524e9f2549ee8ecc564dddda361613e0be06d8146c25c81` |
| `DIRSIG_training/3day_inperson_schedule.pdf` | file | 1 | 73,013 | `sha256:9b20419f335d4755cc0db3195bc9f86b93e759e946e756c5f1c904a0e52b054e` |
| `DIRSIG_training/BENNETT DAVID.pdf` | file | 1 | 1,102,627 | `sha256:9faebbe4081d4699dbfc1a4be778753690187e3a3ae56da69129dad6a77a9c90` |
| `DIRSIG_training/ChipMaker.pdf` | file | 1 | 1,468,643 | `sha256:df3479607e44deade9bae6e1d6f1cf4aecca60cfed889b39ff2da834d0772580` |
