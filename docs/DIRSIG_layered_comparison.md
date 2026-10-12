# DIRSIG demos: layered form against pass-through

The first comparisons of a DIRSIG demo expressed in the layered form (CONOPS section 3.2: `engine.atmosphere.uniform`, C-39, and `engine.platform.as_authored`, C-40) with the same demo run as authored through the pass-through form. Numbers and digests only; no output byte and no demo value is in this repository.

**How.** `python scripts/compare_layered.py DensityMap1 MaterialMap1 PointCollectors2 --work <outside the repository>` (2026-10-12, DIRSIG 2026.38 (a020954), dirfm 93195ce, 36 s for all renders). Per demo the script extracts the demo's archive into a private library under `--work`, derives the layers from the demo's own files (the scene and platform by reference and hash, the `.atm` read with `basic_atmosphere.read_atm`, the one-entry `.ppd` as a static pose, the `.tasks` as epoch and windows), renders the layered recipe, the pass-through form at the same seed and the pass-through form without a seed, one at a time at the demo's native size, and compares every image both forms wrote. The derived layers hold the demo's licensed values, so they are written only under `--work` and are not committed as recipes (section 5.1); the script is the recipe's source. Seed: 1 for the layered run and the same-seed pass-through run.

## Results

| Demo | Image | Against | Shape (bands x lines x samples) | Per-band mean, layered | Per-band mean, pass-through | Max abs difference | Pixels differing | Identical |
|---|---|---|---|---|---|---|---|---|
| DensityMap1 | `demo.img` | pass-through, seed 1 | 1 x 240 x 320 | 0.045067 | 0.0450775 | 0.0336805 | 99.8724% | no |
| DensityMap1 | `demo_truth.img` | pass-through, seed 1 | 9 x 240 x 320 | 1.03333, 0.0334635, -0.00426604, -0.0060606, 0.00469933, nan, 0.507347, 0.476342, 0.468925 | 1.03331, 0.0333854, -0.00436159, -0.00704023, 0.00469719, nan, 0.507268, 0.4762, 0.467182 | 1 | 100.0000% | no |
| DensityMap1 | `demo.img` | pass-through, no seed (the sweep's reference) | 1 x 240 x 320 | 0.045067 | 0.0450778 | 0.0340224 | 99.9479% | no |
| DensityMap1 | `demo_truth.img` | pass-through, no seed | 9 x 240 x 320 | as above | 1.03331, 0.0334115, -0.00436165, -0.00704044, 0.00469717, nan, 0.507277, 0.476213, 0.467189 | 1 | 100.0000% | no |
| MaterialMap1 | `demo.img` | pass-through, seed 1 | 1 x 240 x 320 | 0.0714416 | 0.0714416 | 0 | 0% | yes |
| MaterialMap1 | `demo_truth.img` | pass-through, seed 1 | 10 x 240 x 320 | 3.38076, 2.38232, 1.81199e-05, 3.22681e-05, 0.000845158, 750.287, 0.999616, 0.43403, 0.434028, 323.892 | identical | 0 | 0% | yes |
| MaterialMap1 | `demo.img` | pass-through, no seed (the sweep's reference) | 1 x 240 x 320 | 0.0714416 | 0.0714375 | 0.019471 | 44.0299% | no |
| MaterialMap1 | `demo_truth.img` | pass-through, no seed | 10 x 240 x 320 | as above | 3.3812, 2.3824, 3.89154e-05, -7.01243e-06, 0.000845117, 750.287, 0.999616, 0.434047, 0.434031, 323.893 | 6.93077 | 100.0000% | no |
| PointCollectors2 | none | — | — | — | — | — | — | stopped: the layered run failed |

The `nan` band of DensityMap1's truth image is NaN in some pixels of both forms; pixels NaN in both are not counted as differing. "Pixels differing" counts a pixel when any band differs.

**MaterialMap1.** The layered render is byte-identical to the pass-through render at the same seed, image and truth. Only the image headers differ: the acquisition time is written in UTC (`2000-08-01T18:00:00.0000+00:00`) by the layered form and with the demo's offset (`13:00:00.0000-05:00`) by the pass-through form, the same instant; and the geolocation corners in the last digits.

**DensityMap1.** The layered render differs from the same-seed pass-through render in almost every pixel, by Monte Carlo noise around equal means (0.045067 against 0.0450775). Attribution (the script's step 5, a diagnostic outside the recipe): the layered job's own input folder rendered again with the demo's `.ppd` in place of the generated one gives the pass-through digests exactly (`demo.img` db5d5511..., `demo_truth.img` 23429245...). Two further diagnostic renders narrowed it to the Euler angles: dirfm's `PlatformPosition` writes them to six decimals (1.047198 for the demo's 1.04719755, 5.759587 for 5.75958653), and restoring the two values alone gives the pass-through digests, while writing the location's `frame` attribute in place of dirfm's `type` changes nothing. The tasks file, the jsim's plugin order, the scene compile's seed and thread count, and the cache (user HOME against a per-run HOME) made no difference here. MaterialMap1's angles are 0, which six decimals hold exactly.

**PointCollectors2.** The layered run failed in DIRSIG's dry run: `demo.mat` "is not a file" in the job's scene copy. The demo's `.scene` names `demo.glist` and `$SCENE_DIR/demo.mat`, files beside it, and the scene reference (`scene_ref.reference_scene`) links only the `geometry/`, `materials/` and `maps/` folders beside a `.scene` (BACKLOG "Tagged demos: loader gaps", item 11). That feature is not built this round; no pass-through render was made for the comparison.

## Known input differences

Listed for every comparison, whether or not it changed a number:

- simulation file: the layered job's jsim is written by dirfm (BasicPlatform, BasicAtmosphere, and SpiceEphemeris unless the `.atm` fixes the Sun), not the demo's own `.sim` or `.jsim`; MaterialMap1's `.atm` fixes no Sun, so its layered job names SpiceEphemeris where the `.sim` relies on DIRSIG's implicit ephemeris;
- motion and tasks: regenerated by dirfm from the derived values (the `.ppd` with positions to three and Euler angles to six decimals, the `.tasks` with the epoch in UTC);
- `.atm`: written from the derived uniform values; the demo's `<metadata>`, `<turbulence>` and lunar values are not carried;
- seed: the layered run states 1; the sweep's references state none (DIRSIG's default seed), so the same-seed pass-through run is the like-for-like reference;
- scene compile: dirfm runs `scene2hdf` with `--threads <cpu count>` and the seed; the pass-through runner runs it with neither;
- cache: the layered job runs with the user's HOME; the pass-through run with a per-run HOME;
- descriptor: the layered run's sensor-spec is a library stand-in, checked but not applied (the platform is used as authored), and its collection states the scene origin and the pose's height.

## Digests

| Demo | Run | Run id | `demo.img` sha256 | `demo_truth.img` sha256 | Wall time (s) |
|---|---|---|---|---|---|
| DensityMap1 | layered | `90080847337966e7` | `8ad130d916a7d2755e18ea021a521f91b9ed25c41694bdde9a5fac8727564fba` | `c56444b4ea9b67a82a1ac693afa8543895994dec8e51bce6a218946e2aad4b45` | 5.1 |
| DensityMap1 | pass-through, seed 1 | `d8c328daa25fcd55` | `db5d55114d39239e46572335d993e9d4de9880b56b2719a3fed26925d4f36ab6` | `2342924589335267bbc74a9f4936db8ad3264aa7f281f9d9c3a2efbf48fcbe12` | 5.0 |
| DensityMap1 | pass-through, no seed | `6c5103d2321169d1` | `d78868ccd749174ba6193a81a5c2b89c02ad86376d62d2df35a41047754817b9` | `1e7990314cf49139a5a91874b389b7665c8383d236c35bd241e0cabcf0a91c05` | 5.0 |
| MaterialMap1 | layered | `c0446776c46ddb75` | `57ad35d39f3d8929f2371cf2384953c7c42cb05b14802035a0989afdc8a4293c` | `f0ead2e81524b19c0ef8b19b99cebbaec8625fe7f3768c7aa3c4cf991f97cbc8` | 5.0 |
| MaterialMap1 | pass-through, seed 1 | `fd22cf1938d86011` | `57ad35d39f3d8929f2371cf2384953c7c42cb05b14802035a0989afdc8a4293c` | `f0ead2e81524b19c0ef8b19b99cebbaec8625fe7f3768c7aa3c4cf991f97cbc8` | 5.0 |
| MaterialMap1 | pass-through, no seed | `0b6395d7f4647bc9` | `e3af002344a905d52f37bc790f35b0583d73d682f6e18512955fedd60af29efc` | `44266bb5a144d70d21931075180c0e9fba18df1a787a28448f3f929fb74a5d38` | 5.0 |
| PointCollectors2 | layered | `7cbfc2ff7e841437` | failed (scene files beside the `.scene`) | — | 3.0 |

The two no-seed pass-through runs reproduce the demo sweep's recorded digests (`docs/DIRSIG_demo_sweep.md`, `docs/data/demo_sweep_digests.jsonl.gz`). The run ids are those of the specs the script derived; they are not in `tests/data/id_snapshot.json`, which holds committed specs only.
