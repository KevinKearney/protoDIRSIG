# DIRSIG demo reference runs

Reference runs of DIRSIG's shipped demos through the SDK's pass-through form (`demo_<name>_passthrough` recipes): each demo directory is run by DIRSIG as authored, under the run store, admission, worker and `Workspace`, by `python scripts/run_demo.py <Name> --timeout 1200 --repeat --report docs/DIRSIG_demo_reference_runs.md`, in a fresh work root outside the repository. The measurements between the markers are written by the script; the sections outside them are written by hand and kept. Output digests are hashes only: no output byte is in the repository. A pass-through run is the reference that a layered re-expression of the same demo is compared against.

<!-- run_demo: generated between these markers by scripts/run_demo.py; edit outside them -->

## Measurements

| Demo | Recipe | State | Wall time (s) | Outputs | Run directory (MB) | Deterministic | Engine exit | DIRSIG version |
|---|---|---|---|---|---|---|---|---|
| Brdf1 | `demo_brdf1_passthrough` | failed | 210.2 | 0 | 4.41 | not tested | 1 | 2026.38 (a020954) |
| PointCollectors2 | `demo_pointcollectors2_passthrough` | rendered | 6.1 | 4 | 21.34 | yes | 0 | 2026.38 (a020954) |

### Brdf1: outputs

Run id `5bd1d5684b7feb62cd83207c6cf904bc7e8804bf0ff6fa285d73004649061a91`, started 2026-10-11T00:20:52Z, work root outside the repository. Determinism: not tested.


Failure: Run demo-brdf1-passthrough (5bd1d5684b7feb62cd83207c6cf904bc7e8804bf0ff6fa285d73004649061a91) failed while executing: the engine exited with status 1 (see worker.log)

Worker log tail:

```
[error] Filename = 'mls_urban_38km.adb.hdf'
[error] Error = 'Could not open NewAtmosphere HDF: "mls_urban_38km.adb.hdf"!'
[error] Error!
  Unable to initialize atmosphere plugin!

  Thrown by 'init' (AtmosphereManager.cpp:253)

[error] 
[error]   Debug Log:
[error]     - Error condition satisfied: !globalAtmosphere->init(atmInitIn, atmCallbacks)
[error] 
Troubleshooting
---------------
Something went wrong running the simulation!
This is most often a problem with the given scene or
simulation files. Make sure these files are properly configured.

Refer to the DIRSIG Troubleshooting Guide for possible solutions:
https://dirsig.cis.rit.edu/docs/new/trouble_shooting.html
2026-10-11T00:24:21Z failed: the engine exited with status 1 (see worker.log)
```

### PointCollectors2: outputs

Run id `0ee025143676ad443fa41ff7c511bb5260b96bff8284c117aca05be85a670944`, started 2026-10-11T00:24:45Z, work root outside the repository. Second run in a fresh work root: rendered, 5.1 s; deterministic: yes.

| File | Bytes | sha256 |
|---|---|---|
| demo.img | 2097152 | `10699416f6d812b891534a71b630f534d8197d33c99fe0ef515e755e563d7962` |
| demo.img.hdr | 534 | `f16cb8680ab0d9cfd22f1c2e145960d1aece7b81102190cdb48c20f0e0a289f6` |
| demo_truth.img | 18874368 | `6dbf3513f653c648b225162f474a6c654637271c83446f5333cbe640b42cf096` |
| demo_truth.img.hdr | 420 | `eda4fa0fca4fd4228791aac5668e33b4ebb2a929c5f143a376ac4f515b8af0bd` |

<!-- run_demo data: {"Brdf1":{"demo":"Brdf1","deterministic":"not tested","first":{"demo":"Brdf1","engine_exit_status":1,"engine_version":"2026.38 (a020954)","errors":["Run demo-brdf1-passthrough (5bd1d5684b7feb62cd83207c6cf904bc7e8804bf0ff6fa285d73004649061a91) failed while executing: the engine exited with status 1 (see worker.log)"],"outputs":[],"recipe":"demo_brdf1_passthrough","run_dir_bytes":4405648,"run_id":"5bd1d5684b7feb62cd83207c6cf904bc7e8804bf0ff6fa285d73004649061a91","started_at":"2026-10-11T00:20:52Z","state":"failed","wall_s":210.2,"work_root":"/home/kevin-kearney/.local/state/protodirsig/reference-runs/Brdf1-20261011T002052Z-1","worker_log_tail":["[error] Filename = 'mls_urban_38km.adb.hdf'","[error] Error = 'Could not open NewAtmosphere HDF: \"mls_urban_38km.adb.hdf\"!'","[error] Error!","  Unable to initialize atmosphere plugin!","","  Thrown by 'init' (AtmosphereManager.cpp:253)","","[error] ","[error]   Debug Log:","[error]     - Error condition satisfied: !globalAtmosphere->init(atmInitIn, atmCallbacks)","[error] ","Troubleshooting","---------------","Something went wrong running the simulation!","This is most often a problem with the given scene or","simulation files. Make sure these files are properly configured.","","Refer to the DIRSIG Troubleshooting Guide for possible solutions:","https://dirsig.cis.rit.edu/docs/new/trouble_shooting.html","2026-10-11T00:24:21Z failed: the engine exited with status 1 (see worker.log)"]}},"PointCollectors2":{"demo":"PointCollectors2","deterministic":"yes","differing":[],"first":{"demo":"PointCollectors2","engine_exit_status":0,"engine_version":"2026.38 (a020954)","outputs":[{"name":"demo.img","sha256":"10699416f6d812b891534a71b630f534d8197d33c99fe0ef515e755e563d7962","size":2097152},{"name":"demo.img.hdr","sha256":"f16cb8680ab0d9cfd22f1c2e145960d1aece7b81102190cdb48c20f0e0a289f6","size":534},{"name":"demo_truth.img","sha256":"6dbf3513f653c648b225162f474a6c654637271c83446f5333cbe640b42cf096","size":18874368},{"name":"demo_truth.img.hdr","sha256":"eda4fa0fca4fd4228791aac5668e33b4ebb2a929c5f143a376ac4f515b8af0bd","size":420}],"recipe":"demo_pointcollectors2_passthrough","run_dir_bytes":21339804,"run_id":"0ee025143676ad443fa41ff7c511bb5260b96bff8284c117aca05be85a670944","started_at":"2026-10-11T00:24:45Z","state":"rendered","wall_s":6.1,"work_root":"/home/kevin-kearney/.local/state/protodirsig/reference-runs/PointCollectors2-20261011T002445Z-1"},"second":{"demo":"PointCollectors2","engine_exit_status":0,"engine_version":"2026.38 (a020954)","outputs":[{"name":"demo.img","sha256":"10699416f6d812b891534a71b630f534d8197d33c99fe0ef515e755e563d7962","size":2097152},{"name":"demo.img.hdr","sha256":"f16cb8680ab0d9cfd22f1c2e145960d1aece7b81102190cdb48c20f0e0a289f6","size":534},{"name":"demo_truth.img","sha256":"6dbf3513f653c648b225162f474a6c654637271c83446f5333cbe640b42cf096","size":18874368},{"name":"demo_truth.img.hdr","sha256":"eda4fa0fca4fd4228791aac5668e33b4ebb2a929c5f143a376ac4f515b8af0bd","size":420}],"recipe":"demo_pointcollectors2_passthrough","run_dir_bytes":21339804,"run_id":"0ee025143676ad443fa41ff7c511bb5260b96bff8284c117aca05be85a670944","started_at":"2026-10-11T00:24:51Z","state":"rendered","wall_s":5.1,"work_root":"/home/kevin-kearney/.local/state/protodirsig/reference-runs/PointCollectors2-20261011T002451Z-2"}}} -->

<!-- run_demo: end -->

## Notes on these runs

1. Brdf1, first attempt (2.1 s, engine exit 1): DIRSIG5 reported that `demo.scene.hdf` does not exist. DIRSIG5 reads a scene's compiled HDF and does not compile it; the pass-through runner did not run `scene2hdf`. The runner now compiles every scene the simulation file names with the `scene2hdf` beside the engine, in the run's copy of the directory, before it runs `dirsig5` (the demo itself is unchanged). The second attempt is the one in the table.
2. Brdf1, second attempt (210 s, engine exit 1): the scene compiled (exit 0); DIRSIG then could not open the NewAtmosphere database the demo's `demo.jsim` names (`mls_urban_38km.adb.hdf`), which is not in the demo archive; the simulation file's NewAtmosphere inputs name a backend to build it, which this installation did not do. Recorded as the result; the demo was not modified and no workaround was attempted. Most of the 210 s was the scene compile and material-cache building before the atmosphere was initialized.
3. PointCollectors2 (`framing.jsim`) rendered in about 6 s, and a second run in a second fresh work root gave identical digests for every output: deterministic at DIRSIG's default seed on this machine. DIRSIG also writes material caches under the user's DIRSIG cache directory (`~/Documents/DIRSIG/cache` unless `DIRSIG_CACHE_DIR` is set), outside the run directory; whether that cache can change an output was not isolated.
4. Native sizes and the cost of comparison: PointCollectors2's image is 2 097 152 bytes (one 512 x 512 band of 8-byte values, by its header) with an 18.9 MB truth image, in about 6 s and a 21 MB run directory, so a layered render at the same native size is cheap and a pixel comparison is feasible. Brdf1 has no reference output (its atmosphere database is missing), so it cannot be compared until that database is available; the layered comparison planned for Brdf1 is not possible this round.
