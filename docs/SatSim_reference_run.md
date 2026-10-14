# SatSim reference run

The first SatSim run through the SDK: the probe's sample configuration, run as authored by the SatSim adapter (`satsim-engine/1`, pass-through form, `proposed`; CONOPS and Guide section 7.4) through `LocalBackend`, three times. Sizes and digests only: the outputs are not committed. `scripts/satsim_reference.py` runs it and writes the digest table `docs/data/satsim_reference_digests.jsonl`; `--check` runs it again and compares. Measured on 2026-10-11 on the probe's machine (`docs/SatSim_probe.md`: 4 cores, 8 threads, 10 GB, no GPU).

## Inputs

| Input | Identity |
|---|---|
| Run spec | `manifold_run_specs/satsim/tahoe_worldview2.yaml` (seed 1, device `cpu`), run id `81fe69a103a32acdc8a1015e36724faa9d3ed8152488806dbd8a93f24adc5a3d` |
| Configuration | `manifold_config_repo/satsim/tahoe_worldview2.yaml`, sha256 `481365c096d0512f7d118ee2f68a0c3bd6478f0859022486dc0306b6b385f7c0` (the probe's `docs/data/satsim_probe_config.yaml` with a new header comment; the configuration itself unchanged) |
| Ephemeris asset | `de421.bsp`, sha256 `a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc`, 16,788,480 bytes |
| Earth-orientation asset | `finals2000A.all`, snapshot of 2026-10-11, sha256 `0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a`, 3,769,212 bytes |
| Launcher | `packages/engine-satsim/src/manifold/engines/satsim/launcher.py`, sha256 `10fed7a37d0907484eae094a06e87555c59a9f8146eed96901915fa9168df1b4` |

## Interpreter

The conda environment `satsim` (found by the adapter's third rule; no `MANIFOLD_SATSIM_PYTHON`, no `engines.yaml`), probed by `availability()` in 3.5 s:

| Package | Version |
|---|---|
| Python | 3.11.17 |
| satsim | 0.26.1 |
| tensorflow | 2.21.0 (CPU) |
| numpy | 1.26.4 |
| astropy | 5.3.4 |
| skyfield | 1.55 |

## Runs

| Label | Run id | `cpu_threads` | Wall time, submission to `rendered` | SatSim's own time (launcher) | Frames | Image size |
|---|---|---|---|---|---|---|
| `default-a` | `81fe69a103a3…` | not requested (TensorFlow's defaults) | 9.1 s | 3.98 s | 3 of 3 | 64 x 64 |
| `default-b` | `81fe69a103a3…` | not requested | 9.1 s | 3.98 s | 3 of 3 | 64 x 64 |
| `one-thread` | `3c17707f9d82…` | 1 | 8.8 s | 3.77 s | 3 of 3 | 64 x 64 |

Each run is in its own work root, so `default-b` is a new run directory, not the resubmission of `default-a`. The wall time includes the worker's start, the TensorFlow import (about 3 s, `docs/SatSim_probe.md`) and the hashing of the artifacts. The peak resident memory of the largest process the runs started, read as `RUSAGE_CHILDREN` by the script after each run (it also covers the availability probe's import of SatSim), was 706 MB, under the 1 GiB the adapter declares; the probe measured 856 MB for the same configuration through the `satsim` command. Every run: verdict `complete`, 22 artifacts, no connection attempted (the launcher's guard wrote no `network_attempts.log`), nothing written into the `satsim` environment or the user's caches.

## Repeatability and thread invariance

| Comparison | Result |
|---|---|
| `default-a` against `default-b`: every artifact but the two that carry the run's own timing and paths (`worker.log`, `satsim_result.json`) | byte-identical: 20 artifacts (3 FITS frames, 3 annotations, 3 annotated previews, the movie, the CZML, `config.json`, the 7 `config_pass_*.json`, `run_spec.json`) |
| `one-thread` against `default-a`: the same 20 less `run_spec.json` (whose sha256 is the run id, which differs because a requested thread count enters it) | byte-identical: 19 artifacts |
| `config.json` | byte-identical across the repeats without any normalization: the launcher passes the input folder relative (`_input_dir` is `input`) |
| Annotations | byte-identical: the launcher fixes SatSim's set folder name (`set`), which SatSim otherwise names by the local wall-clock time and writes into every annotation |

| Artifact | Role | Size (bytes) | sha256 (first 16) |
|---|---|---|---|
| `ImageFiles_set.0000.fits` | product | 17,280 | `cc1348b219aadc92` |
| `ImageFiles_set.0001.fits` | product | 17,280 | `089d85e196f8587c` |
| `ImageFiles_set.0002.fits` | product | 17,280 | `d24359d13aa1f712` |
| `Annotations_set.0000.json` | truth | 1,601 | `f6d5cdedf4576c98` |
| `Annotations_set.0001.json` | truth | 1,608 | `3af8efb10ed77f4e` |
| `Annotations_set.0002.json` | truth | 1,608 | `3b526eee5646a17e` |
| `AnnotatedImages_movie.png` | preview | 26,050 | `0932e9cad3a7e783` |
| `satsim.czml` | metadata | 4,062 | `bb8bde5e1613c19a` |
| `config.json` | config | 2,292 | `eb9bed6900f13dfb` |

The full digests of every artifact of the three runs are in `docs/data/satsim_reference_digests.jsonl` (one JSON line per run: label, run id, `cpu_threads`, and each artifact's name, role, size and sha256; `worker.log` and `satsim_result.json` by name and role only).

## What this shows and what it does not

It shows that, on this machine's CPU, with SatSim 0.26.1 and TensorFlow 2.21.0, the seeded launcher makes the SDK's SatSim run repeat byte for byte in every product, truth, preview, metadata and configuration file, in a fresh run directory, and that one thread gives the same bytes as TensorFlow's default thread count; and that the run needs no network and leaves the user's caches and SatSim's environment untouched. It does not show repeatability on another machine, CPU model or instruction set (TensorFlow's oneDNN kernels may order sums differently), with other SatSim, TensorFlow or numpy versions, on a GPU (unverified; `docs/SatSim_probe.md` lists the checklist), for configurations that use features the sample does not (clouds, POPPY PSFs, star catalogs, `$sample` draws, radar and passive RF), or at sizes and frame counts beyond the 64 x 64 three-frame sample (the integration tests add a 40-frame, 256 x 256 run only to be interrupted).
