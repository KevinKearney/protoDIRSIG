# DIRSIG determinism probe

The demo sweep (`docs/DIRSIG_demo_sweep.md`) repeated every demo that rendered in under 300 s and found 43 of 125 whose two runs gave different output digests under DIRSIG's default seed: 17 lidar demos, 14 in radiance images, 9 in truth images only and 3 in data-recorder text only. A digest difference can come from a changed path or timestamp, from floating-point accumulation order under threads, from a different random seed, or from something else. This probe separates these for six non-lidar demos, and repeats the three long SDA demos the sweep could not repeat. It records names, measurements and DIRSIG band and element names only; no demo bytes.

Lidar demos were run (by the sweep) and are not analyzed here: their `.bin` outputs are out of scope.

## Method

`scripts/probe_determinism.py` renders each chosen demo twice under each condition, each render in its own fresh directory outside the repository with a per-run `HOME`, through the SDK's pass-through runner (`protodirsig.passthrough.run_engine`: the demo copied, its scenes compiled with `scene2hdf`, then `dirsig5` on the simulation file the sweep rendered). `scripts/compare_outputs.py` compares two output directories file by file. Both scripts are in the repository; the outputs were deleted after the analysis.

Conditions, from `dirsig5 --help` (DIRSIG 2026.38), which lists `-j/--threads` and `-s/--random_seed`:

| Condition | What changes | How |
|---|---|---|
| C0 | nothing: DIRSIG's defaults, as the sweep ran | `dirsig5 --output_folder=<run>/output <sim>` |
| C1 | one thread | the same, with `--threads=1` (the engine contract has no thread count, so the probe runs a wrapper that adds the option) |
| C2 | an explicit seed | the same, with `--random_seed=1` (the option the runner passes for `engine.run.seed`) |

The two renders of one condition give that condition's noise floor; the first render of C1 and of C2 is also compared with the first of C0.

Classes of a differing file (`compare_outputs.py`):

| Class | Meaning | Threshold and why |
|---|---|---|
| `metadata` | nothing differs after masking paths, home directories, work-root names, run ids, dates, times and process ids (text), or the pixel values are identical (an image whose bytes differ) | exact after the mask |
| `float-order` | every differing value is within 1e-5 relative of its counterpart | the ray tracer is single precision (epsilon 1.2e-7); adding the same samples in another order moves a sum by a few epsilon per addition, which stays below 1e-5 for these sample counts, while a different random path does not |
| `index-relabel` | the only differing bands hold integer labels and at least 99.9 percent of pixels agree with one renumbering of the labels | added for this probe: the truth images' "Dominant Optical Property Index" differs in this way, which none of the three classes above describes |
| `sampling-noise` | any larger difference | a Monte Carlo estimate drawn from other random numbers, or another object hit by a pixel's sample in a truth image |

Image measures are relative to the RMS of the first image's values ("RMS / signal"); "max value rel" is the largest `|a - b| / max(|a|, |b|)` of one value; "pixels" is the fraction of pixels with any band different.

## Selection

| Demo | Simulation file | Sweep group | Why |
|---|---|---|---|
| MaterialOverrides1 | `demo.sim` | radiance | named by the plan; 4 s |
| NestedMotion1 | `demo.sim` | radiance | named by the plan; 4 s |
| MoonSat2 | `demo.jsim` | truth only | named by the plan; an SDA demo |
| StkImport1 | `demo.jsim` | data recorder only | named by the plan; an SDA demo |
| CommandedMount2 | `demo_absolute.sim` | truth only | the cheapest other truth-only demo (6.1 s; tied with GeoLocation1, taken by name) |
| PlatformJitter2 | `flex_single.sim` | data recorder only | the cheapest other recorder-only demo (4.1 s) |

## Results

Each cell gives the class of each differing file; "identical" means every output file is byte-identical. Numbers are for the radiance image unless a truth band is named.

| Demo | C0 pair (noise floor) | C1 pair | C2 pair | C0 vs C1 | C0 vs C2 |
|---|---|---|---|---|---|
| MaterialOverrides1 | radiance `float-order`: RMS / signal 4.0e-8, max value rel 9.5e-6, 2.1 % of pixels | identical | radiance `float-order`: 1.6e-8, 8.8e-6, 2.0 % | radiance `sampling-noise` by the threshold: 3.9e-8, 2.8e-5, 2.9 % | radiance `sampling-noise`: 2.2e-2, 1, 76 %; truth `sampling-noise` |
| NestedMotion1 | radiance `sampling-noise`: 1.4e-5, 8.0e-3, 2.2 %; truth `sampling-noise` (7 geometry bands, 0.1 % of pixels) | identical | radiance `sampling-noise`: 3.0e-5, 2.6e-2, 2.3 %; truth `sampling-noise` | radiance `sampling-noise`: 8.1e-5, 4.5e-2, 3.3 %; truth `sampling-noise` | radiance `sampling-noise`: 8.6e-3, 1, 53 %; truth `sampling-noise` |
| MoonSat2 | truth `index-relabel` (Dominant Optical Property Index, 16 % of pixels) | truth `index-relabel` (27 %) | truth `index-relabel` (30 %) | truth `index-relabel` | radiance `sampling-noise`: 8.5e-2, 1, 11 %; truth `sampling-noise`; header tie points differ |
| CommandedMount2 | truth `index-relabel` (2 % of pixels) | truth `index-relabel` (93 %) | truth `index-relabel` (70 %) | truth `index-relabel` | radiance `sampling-noise`: 1.6e-2, 1, 82 %; truth `sampling-noise` |
| StkImport1 | recorder `metadata` | recorder `metadata` | recorder `metadata` | recorder `metadata` | recorder `metadata`; radiance `sampling-noise`: 1.7e-2, 1, 100 %; truth `sampling-noise` |
| PlatformJitter2 | recorder `metadata` | recorder `metadata` | recorder `metadata` | recorder `metadata` | recorder `metadata`; radiance `sampling-noise`: 1.2e-2, 1, 63 %; truth `sampling-noise` |

Wall time per render (two renders each), C0 / C1 / C2 in seconds: MaterialOverrides1 2.0 / 7.2 / 2.0; NestedMotion1 1.9 / 6.4 / 1.9; MoonSat2 2.5 / 7.7 / 2.5; StkImport1 23 to 29 / 76 / 22 to 28; CommandedMount2 5.0 / 16.1 / 4.3; PlatformJitter2 3.2 / 11.7 / 3.2. One thread costs about 3.1 to 3.7 times the default. Every render reached 74 C or more (most 88 to 96 C).

## Findings

1. **Threads explain the radiance differences.** With one thread, both radiance demos repeated bit for bit, radiance and truth alike. With the default thread count, they differed whether or not a seed was given. The difference is either accumulation order alone (MaterialOverrides1: at most 9.5e-6 of a value, RMS 4e-8 of the signal) or a different random draw for some pixels (NestedMotion1: up to 0.8 percent of a value in 2 percent of pixels, RMS 1.4e-5 of the signal); which one depends on the demo, presumably on how the work of a pixel is split between threads.
2. **The default seed is fixed.** C1 repeated without a seed, so DIRSIG does not draw a new seed per run. An explicit seed changes the result (C0 against C2: 1 to 9 percent of the signal RMS, most pixels) but does not make repeats identical. A layered run and its reference must therefore use the same seed, default or explicit; a seed alone gives no exactness.
3. **The truth-only differences are a renumbering.** In MoonSat2 and CommandedMount2 the only differing band is "Dominant Optical Property Index", in every condition, including one thread with a fixed seed. The material index band and the radiance are identical; the index takes the same set of values (17 in MoonSat2's Moon material, 55 in CommandedMount2's mapped material); and 99.96 percent or more of the pixels agree with one permutation of the numbers. DIRSIG numbers the optical properties of a mapped material in an order that changes between runs. This is not a radiometric difference, and neither threads nor the seed control it.
4. **The data-recorder differences are a time stamp.** StkImport1 and PlatformJitter2's recorder text differs only in a generation-time line; masked, it is identical in every condition and even between seeds (PlatformJitter2's recorded jitter does not depend on the seed).
5. **Headers.** A radiance header differs only when the image does (its geolocation tie points come from the render); masked, no header differed within a condition.

## Long SDA demos

The sweep rendered Ssa1, SpaceRendezVous1 and LightCurve1 once (629 s, 706 s and 692 s), too long for its repeat rule. `scripts/sweep_demos.py --only Ssa1,SpaceRendezVous1,LightCurve1 --repeat Ssa1,SpaceRendezVous1,LightCurve1` rendered each twice more at the default thread count and seed (C0), each render in a fresh work root, and compared output digests only; the outputs were deleted after hashing. The first of the two new renders was also compared with the sweep's render, from `docs/data/demo_sweep_digests.jsonl.gz`.

| Demo | Simulation file | Wall time of the two renders (s) | Outputs | New pair | Against the sweep's render |
|---|---|---|---|---|---|
| Ssa1 | `demo.sim` | 672.7, 655.4 | 4 | identical | identical |
| LightCurve1 | `box_spin.jsim` | 748.7, 749.9 | 1,681 | 2 differ: `cube_150.img`, `lightcurve.dat` | the same 2 differ |
| SpaceRendezVous1 | `lidar_rpo.jsim` (a lidar) | 718.2, 701.4 | 3 | 2 differ: `demo.bin`, `lidar_truth.img` | the same 2 differ |

Ssa1 is deterministic: three renders, the sweep's and two about 12 hours later, gave one set of digests. LightCurve1 repeats 1,679 of its 1,681 outputs exactly; one frame and the light-curve table differ, which digests alone cannot classify (the table summarizes the frames, so a difference in one frame would appear in it too). SpaceRendezVous1's file is a lidar simulation: run, not analyzed. Every one of these renders peaked at 93 to 99 C.

## Recommendation for a layered-versus-reference test

- **Exact, where the reference is deterministic.** Render the reference and the layered run with the same seed (default or stated) and, for an exact test, with one thread (`--threads=1`): the probe's C1 pairs were bit-identical for every radiance image. At the default thread count, 82 of 125 sweep demos repeated identically as well, and those can be compared exactly at default threads.
- **Truth images.** Compare every band exactly except label bands whose numbering is not stable ("Dominant Optical Property Index"); compare those after mapping labels through the most common partner, or compare the material index instead.
- **Data-recorder text and headers.** Compare after masking times, dates, paths and process ids.
- **Statistical, otherwise.** When a run must use the default thread count and the reference is not deterministic, compare against the noise floor of the C0 pair, the condition the reference itself ran in: pass if the RMS difference relative to the signal is within a small multiple (3 is proposed) of the C0 pair's, and the fraction of differing pixels within the same multiple. A single-thread floor is zero and cannot serve; a seed-changed comparison (C0 against C2) measures a different seed, not the noise of one configuration.
- **Thread count in the run spec.** The engine contract has no thread count (BACKLOG "`--threads` in `engine.run`"; MANIFOLD question C-28). An exact comparison of a non-deterministic demo needs it.
