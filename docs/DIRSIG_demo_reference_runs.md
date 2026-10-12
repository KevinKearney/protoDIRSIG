# DIRSIG demo reference runs

Reference runs of DIRSIG's shipped demos through the SDK's pass-through form (`demo_<name>_passthrough` recipes): each demo directory is run by DIRSIG as authored, under the run store, admission, worker and `Workspace`, by `python scripts/run_demo.py <Name> --timeout 1200 --repeat --report docs/DIRSIG_demo_reference_runs.md`, in a fresh work root outside the repository. The measurements between the markers are written by the script; the sections outside them are written by hand and kept. Output digests are hashes only: no output byte is in the repository. A pass-through run is the reference that a layered re-expression of the same demo is compared against.

<!-- run_demo: generated between these markers by scripts/run_demo.py; edit outside them -->

## Measurements

| Demo | Recipe | State | Wall time (s) | Outputs | Run directory (MB) | Deterministic | Engine exit | DIRSIG version |
|---|---|---|---|---|---|---|---|---|
| Brdf1 | `demo_brdf1_passthrough` | rendered | 217.3 | 4 | 10.12 | yes | 0 | 2026.38 (a020954) |
| PointCollectors2 | `demo_pointcollectors2_passthrough` | rendered | 5.2 | 4 | 21.34 | yes | 0 | 2026.38 (a020954) |

### Brdf1: outputs

Run id `909394b77e554607304836697fa45e82f8adda057296e9d5b6d1b9d195f2e2be`, started 2026-10-11T19:27:09Z, work root outside the repository. Second run in a fresh work root: rendered, 209.2 s; deterministic: yes.

| File | Bytes | sha256 |
|---|---|---|
| demo-t0000-c0000.img | 1843200 | `033096bafc7590fece14373892f357a78c5476644cab542a07fbe285c9c42a35` |
| demo-t0000-c0000.img.hdr | 585 | `1e72a57b0ff1d2865abe5421e8810a125cbc0b2cb9cbd64f5d4b0d17709b8cef` |
| demo_truth.img | 1843200 | `0735459979d0cdb487d9dcbeef8c8fb163d7b2ebbc8108e3ff9c2e6cd709f5c1` |
| demo_truth.img.hdr | 283 | `8b27536622ffcd111c0918db27ad9cbf3f027eda6ba23219bdc5860e65516e03` |

### PointCollectors2: outputs

Run id `0ee025143676ad443fa41ff7c511bb5260b96bff8284c117aca05be85a670944`, started 2026-10-11T19:26:46Z, work root outside the repository. Second run in a fresh work root: rendered, 6.1 s; deterministic: yes.

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 2097152 | `10699416f6d812b891534a71b630f534d8197d33c99fe0ef515e755e563d7962` |
| demo.img.hdr | 534 | `f16cb8680ab0d9cfd22f1c2e145960d1aece7b81102190cdb48c20f0e0a289f6` |
| demo_truth.img | 18874368 | `6dbf3513f653c648b225162f474a6c654637271c83446f5333cbe640b42cf096` |
| demo_truth.img.hdr | 420 | `eda4fa0fca4fd4228791aac5668e33b4ebb2a929c5f143a376ac4f515b8af0bd` |

<!-- run_demo data: {"Brdf1":{"demo":"Brdf1","deterministic":"yes","differing":[],"first":{"demo":"Brdf1","engine_exit_status":0,"engine_version":"2026.38 (a020954)","outputs":[{"name":"demo-t0000-c0000.img","sha256":"033096bafc7590fece14373892f357a78c5476644cab542a07fbe285c9c42a35","size":1843200},{"name":"demo-t0000-c0000.img.hdr","sha256":"1e72a57b0ff1d2865abe5421e8810a125cbc0b2cb9cbd64f5d4b0d17709b8cef","size":585},{"name":"demo_truth.img","sha256":"0735459979d0cdb487d9dcbeef8c8fb163d7b2ebbc8108e3ff9c2e6cd709f5c1","size":1843200},{"name":"demo_truth.img.hdr","sha256":"8b27536622ffcd111c0918db27ad9cbf3f027eda6ba23219bdc5860e65516e03","size":283}],"recipe":"demo_brdf1_passthrough","run_dir_bytes":10115526,"run_id":"909394b77e554607304836697fa45e82f8adda057296e9d5b6d1b9d195f2e2be","started_at":"2026-10-11T19:27:09Z","state":"rendered","wall_s":217.3,"work_root":"/home/kevin-kearney/.local/state/manifold/reference-runs/Brdf1-20261011T192709Z-1"},"second":{"demo":"Brdf1","engine_exit_status":0,"engine_version":"2026.38 (a020954)","outputs":[{"name":"demo-t0000-c0000.img","sha256":"033096bafc7590fece14373892f357a78c5476644cab542a07fbe285c9c42a35","size":1843200},{"name":"demo-t0000-c0000.img.hdr","sha256":"1e72a57b0ff1d2865abe5421e8810a125cbc0b2cb9cbd64f5d4b0d17709b8cef","size":585},{"name":"demo_truth.img","sha256":"0735459979d0cdb487d9dcbeef8c8fb163d7b2ebbc8108e3ff9c2e6cd709f5c1","size":1843200},{"name":"demo_truth.img.hdr","sha256":"8b27536622ffcd111c0918db27ad9cbf3f027eda6ba23219bdc5860e65516e03","size":283}],"recipe":"demo_brdf1_passthrough","run_dir_bytes":10115526,"run_id":"909394b77e554607304836697fa45e82f8adda057296e9d5b6d1b9d195f2e2be","started_at":"2026-10-11T19:30:47Z","state":"rendered","wall_s":209.2,"work_root":"/home/kevin-kearney/.local/state/manifold/reference-runs/Brdf1-20261011T193047Z-2"}},"PointCollectors2":{"demo":"PointCollectors2","deterministic":"yes","differing":[],"first":{"demo":"PointCollectors2","engine_exit_status":0,"engine_version":"2026.38 (a020954)","outputs":[{"name":"demo.img","sha256":"10699416f6d812b891534a71b630f534d8197d33c99fe0ef515e755e563d7962","size":2097152},{"name":"demo.img.hdr","sha256":"f16cb8680ab0d9cfd22f1c2e145960d1aece7b81102190cdb48c20f0e0a289f6","size":534},{"name":"demo_truth.img","sha256":"6dbf3513f653c648b225162f474a6c654637271c83446f5333cbe640b42cf096","size":18874368},{"name":"demo_truth.img.hdr","sha256":"eda4fa0fca4fd4228791aac5668e33b4ebb2a929c5f143a376ac4f515b8af0bd","size":420}],"recipe":"demo_pointcollectors2_passthrough","run_dir_bytes":21340184,"run_id":"0ee025143676ad443fa41ff7c511bb5260b96bff8284c117aca05be85a670944","started_at":"2026-10-11T19:26:46Z","state":"rendered","wall_s":5.2,"work_root":"/home/kevin-kearney/.local/state/manifold/reference-runs/PointCollectors2-20261011T192646Z-1"},"second":{"demo":"PointCollectors2","engine_exit_status":0,"engine_version":"2026.38 (a020954)","outputs":[{"name":"demo.img","sha256":"10699416f6d812b891534a71b630f534d8197d33c99fe0ef515e755e563d7962","size":2097152},{"name":"demo.img.hdr","sha256":"f16cb8680ab0d9cfd22f1c2e145960d1aece7b81102190cdb48c20f0e0a289f6","size":534},{"name":"demo_truth.img","sha256":"6dbf3513f653c648b225162f474a6c654637271c83446f5333cbe640b42cf096","size":18874368},{"name":"demo_truth.img.hdr","sha256":"eda4fa0fca4fd4228791aac5668e33b4ebb2a929c5f143a376ac4f515b8af0bd","size":420}],"recipe":"demo_pointcollectors2_passthrough","run_dir_bytes":21340185,"run_id":"0ee025143676ad443fa41ff7c511bb5260b96bff8284c117aca05be85a670944","started_at":"2026-10-11T19:26:51Z","state":"rendered","wall_s":6.1,"work_root":"/home/kevin-kearney/.local/state/manifold/reference-runs/PointCollectors2-20261011T192651Z-2"}}} -->

<!-- run_demo: end -->

## Notes on these runs

1. Brdf1, first attempt (the recipe's earlier form, `demo.jsim`, run id `5bd1d5684b7f...`) (2.1 s, engine exit 1): DIRSIG5 reported that `demo.scene.hdf` does not exist. DIRSIG5 reads a scene's compiled HDF and does not compile it; the pass-through runner did not run `scene2hdf`. The runner now compiles every scene the simulation file names with the `scene2hdf` beside the engine, in the run's copy of the directory, before it runs `dirsig5` (the demo itself is unchanged). The second attempt is the one in the table.
2. Brdf1, second attempt (the same earlier form) (210 s, engine exit 1): the scene compiled (exit 0); DIRSIG then could not open the NewAtmosphere database the demo's `demo.jsim` names (`mls_urban_38km.adb.hdf`), which is not in the demo archive; the simulation file's NewAtmosphere inputs name a backend to build it, which this installation did not do. Recorded as the result; the demo was not modified and no workaround was attempted. Most of the 210 s was the scene compile and material-cache building before the atmosphere was initialized.
3. PointCollectors2 (`framing.jsim`) rendered in about 6 s, and a second run in a second fresh work root gave identical digests for every output: deterministic at DIRSIG's default seed on this machine. DIRSIG writes its material caches under `$HOME/Documents/DIRSIG/cache`; the pass-through runner sets `HOME` to a per-run folder inside the run directory (`passthrough.py`, recorded as the run's cache state), so the user's cache is not an input and every run starts cold.
4. Native sizes and the cost of comparison: PointCollectors2's image is 2 097 152 bytes (one 512 x 512 band of 8-byte values, by its header) with an 18.9 MB truth image, in about 6 s and a 21 MB run directory, so a layered render at the same native size is cheap and a pixel comparison is feasible. Brdf1's `demo.jsim` has no reference output (its atmosphere database is missing); its `demo.sim` form, the recipe's current one, is the reference in the table (note 5).
5. The Brdf1 row and outputs above are of the recipe's current form, which names `demo.sim` (run id `909394b77e55...`), run on 2026-10-11 after the package rename (the `manifold` packages): it rendered in 217.3 s and again in 209.2 s in a second fresh work root, with identical digests, and all four output digests equal those the demo sweep recorded for `demo.sim` (`docs/data/demo_sweep_digests.jsonl.gz`). PointCollectors2 was rerun on the renamed stack the same day: the same run id as before the rename, 5.2 s and 6.1 s, and its four digests equal the sweep's for `framing.jsim`. Neither run id nor any output changed with the rename.
