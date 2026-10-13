# Authoring friction audit: what a user writes, copies and computes to get one run through `Workspace`

Starting point: a DIRSIG5 user with a demo or scene and a sensor in mind, and the `manifold` packages with this repository's libraries. This document lists the files, the fields and the values a run needs, and who produces each. Every count in it is recomputed by `tests/test_friction_audit.py` from the committed files; every refusal quoted is produced by that test.

**Counting rule.** A *field* is a leaf member of a YAML document: a scalar, or a list of scalars (a `tags` list is one field). Comments are not fields. A *hash* is a `content_hash` field. A *copied value* is one the user does not choose: a hash, a library name or path, an `entry_id`, a generator revision.

## 1. The files a run touches

`Workspace` (`manifold.sim`) composes a recipe against three libraries: the layer library (`library=`, default `manifold_run_specs/`), the sensor library (`sensor_library=`, default `manifold_sensors/` beside it) and the engine-asset library (`config_repo=`, default `manifold_config_repo/`).

| File | Library and path | Format | Who produces it |
|---|---|---|---|
| recipe | `manifold_run_specs/recipes/<name>.yaml`, or a Python dict | `compose/1` | the user authors it |
| scenario | `manifold_run_specs/scenarios/<name>.yaml` | `descriptor.collection` | the user authors it |
| engine profile | `manifold_run_specs/engine_profiles/<name>.yaml` | `descriptor.origin`, `descriptor.extras`, `engine` (`dirsig-engine/1`) | the user authors it; `scripts/stamp_hashes.py` writes its hashes and its generator revision |
| sensor | `manifold_sensors/<file>.yaml` | `sensor-spec/1` | the user authors it; `scripts/stamp_hashes.py` writes the hashes of its spectral-curve references |
| spectral curves | `manifold_sensors/spectral/...` | CSV | the user supplies them (only a sensor with a tabulated QE or throughput) |
| scene | `manifold_config_repo/scenes/<scene>/<scene>.scene` with `geometry/` and `materials/` | DIRSIG | the user copies the DIRSIG scene into this layout |
| platform template | `manifold_config_repo/platforms/<P>/<P>.platform` | DIRSIG | the user copies a DIRSIG `.platform`; its entry is named by `library_entry` |
| atmosphere, weather, orbit files | `manifold_config_repo/atmosphere/`, `weather/`, `orbit/` | DIRSIG, TLE | the user copies them |
| composed run spec | in memory (`Workspace.compose`); on disk only for a library recipe, `manifold_run_specs/<name>.yaml` | `run-spec/1` | `Workspace.compose` in memory; `scripts/compose.py` writes the library's copies |
| run id | the run's status and folder name | 64 hex digits | `Workspace` computes it (`manifold.core.identity`) |

## 2. AUROR_ref, file by file

The library's `auror_ref` recipe and the layers it names. Fields as committed:

| File | Fields | Hashes | Other copied values | Who writes the hashes |
|---|---|---|---|---|
| `recipes/auror_ref.yaml` | 25 | 0 | 4: `sensor` (a file name), `scenario`, `engine_profile` (library names), `settings[0].entry_id` (from the sensor file) | none needed |
| `scenarios/tahoe_static_pose.yaml` | 18 | 0 | 0 | none needed |
| `engine_profiles/tahoe_static_pose.yaml` | 34 | 4 (scene, platform, atmosphere database, weather) | 6: the four reference names (library paths), `platform.library_entry` (from the `.platform`), `generator.revision` (the `dirfm` pin) | `scripts/stamp_hashes.py` |
| `manifold_sensors/auror-nir.yaml` | 43 | 0 | 0 | none needed |
| composed run spec (`manifold_run_specs/auror_ref.yaml`) | 76 | 5 (the four above and the sensor's) | | `Workspace.compose` and `scripts/compose.py` write the sensor's; the other four are carried from the engine profile |

The other two library sensors carry hashes of their spectral curves: `deepscan_850_306_nir_1280.yaml` 47 fields, 1 hash; `synthetic_600_200_vis_1920.yaml` 49 fields, 2 hashes. The pass recipe's engine profile, `engine_profiles/tahoe_leo_pass.yaml`, has 43 fields and 6 hashes (scene, platform, TLE, Earth-orientation table, atmosphere database, weather).

**The fields a recipe must carry.** Removing each member of `auror_ref` in turn and validating (engine-free) leaves 20 required fields: `compose`; `meta.name`; `sensor`, `scenario`, `engine_profile`; in the settings member, `entry_id`, `exposure_time`, `frame_rate`, `gain` and `black_level` (each a `value` and a `provenance`, 8 fields) and `roi.Width`, `roi.Height`; and the four `fidelity` members `modeled`, `approximated`, `absent`, `valid_for`. Optional: `meta.tags`, `meta.description`, `roi.OffsetX`, `roi.OffsetY`, `engine_overrides`. Of the 20, 4 are copied (the scenario and engine-profile names, the sensor file name, the `entry_id`) and 16 are chosen. A missing settings member is reported by the `library_files` check as a Python error (`platform could not be rendered from the sensor-spec: KeyError: 'gain'`); a missing `fidelity` member by the `schema` check.

**Changing one thing in `auror_ref`.**

| Change | Fields edited | Notes |
|---|---|---|
| the window | 2 (`settings[0].roi.Width`, `Height`) | |
| the sensor, to `synthetic_600_200_vis_1920.yaml` | 3 (`sensor`, `settings[0].entry_id`, and `engine_overrides` removed) | with `sensor` alone, compose refuses: `settings[0].entry_id: 'auror-nir' names no entry of the listed sensors`; with the `entry_id` too, `library_files` refuses: `channel_response native cannot carry a spectral curve` (the override `auror_ref` sets) |
| the sensor, from `synthetic_vis` to `auror-nir.yaml` | 2 (`sensor`, `settings[0].entry_id`) | `synthetic_vis` sets no override |

## 3. A space-to-space spec, file by file

`manifold_run_specs/s2s/s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0.yaml` is a whole run spec, not a recipe: `scripts/s2s_scenarios.py` writes it with every value, hash and revision in place, and `s2s/index.json` records its run id. 72 fields, 3 hashes (sensor, scene, platform), 1 generator revision, 4 other copied values (the three reference names and `library_entry`). The scene it images, `manifold_config_repo/scenes/s2s_targets/`, is written by the same script.

| Route | Files the user writes | Fields | Hashes the user produces |
|---|---|---|---|
| submit a committed spec | none | 0 | 0 |
| a new grid point | none: an edit of the grid in `scripts/s2s_scenarios.py`, then the script | | 0 (the script writes them) |
| a new spec by hand | one run spec | 72 | 3, and the revision |

Submitting a committed s2s spec as a file needs one argument more than a recipe: `Workspace.local(sensor_library=<the repository's manifold_sensors/>)`. A run-spec file finds its sensor library beside the folder that holds it (`manifold_run_specs/manifold_sensors/` here, which does not exist), and validation refuses with `sensor 'auror-nir.yaml' not found in the sensor library`. The same spec passed as a dict (`yaml.safe_load`) uses the workspace's sensor library and validates.

## 4. Where a content hash is typed, and where a script writes it

| Step | Hash | Typed by the user | Written by |
|---|---|---|---|
| a recipe names a sensor | the sensor's | no | `Workspace.compose` (`manifold.core.compose`), at every compose |
| a recipe of the pass-through form | `passthrough.directory.content_hash` (`recipes/demo_*_passthrough.yaml`, 1 each) | yes, unless the recipe is in the repository's library | `scripts/stamp_hashes.py` in a checkout |
| an engine profile references a scene, platform, atmosphere, weather or orbit file | one per reference (3 to 6 in the library's profiles) | yes, unless the profile is in the repository's library | `scripts/stamp_hashes.py` in a checkout |
| a sensor references a spectral curve | one per curve (0 to 2 in the library's sensors) | yes, unless the sensor is in the repository's sensor library | `scripts/stamp_hashes.py` in a checkout |
| a run spec | the run id | no | `Workspace` |
| an artifact | its `sha256` | no | the run store |

The stamping flow in a checkout: the user writes `content_hash: "sha256:<hash>"` (a placeholder) and runs `python scripts/stamp_hashes.py`, which replaces it with the sha256 of the file or the `dirhash/1` digest of a scene directory. A reference with no `content_hash` is refused by the `schema` check (`'content_hash' is a required property`). A placeholder passes `validate` (the `content_hash` check lists it, `passed` true) and is refused by `submit_run` (`Stamp check failed: /engine/platform/ref carry a placeholder instead of a stamped value; run scripts/stamp_hashes.py`). A wrong hash is refused by the `content_hash` check with the first 12 hex digits of the right one (`does not match the file (sha256:bed58062f31a...)`), so the message cannot be pasted back.

`scripts/stamp_hashes.py` reads and writes only the repository's own `manifold_sensors/` and `manifold_run_specs/{recipes,scenarios,engine_profiles}/`, and resolves names against the repository's `manifold_config_repo/`; it takes no path argument. A layer, sensor or asset library outside the checkout is not stamped by any script: the user computes each hash (`hashlib.sha256` of the file bytes, or `manifold.core.dirhash.directory_digest` for a scene directory) and types or pastes it.

What the user sees without typing: the run id (64 hex digits) in every status and as the run's folder name; each provenance entry's `content_hash` in a compose response; each artifact's `sha256`.

On the shortest path (section 6) no step requires typing a hash.

## 5. Checkout only, or installed packages

| Item | In a checkout | With the installed packages alone |
|---|---|---|
| `Workspace`, `compose`, `validate`, `submit_run`, `submit_sweep`, `wait`, `list_engines` | yes | yes |
| `manifold.core.dirhash`, `manifold.core.identity`, the schemas `admission` checks against | yes | yes |
| the layer library `manifold_run_specs/` (recipes, scenarios, engine profiles, s2s specs) | yes | no |
| the sensor library `manifold_sensors/` | yes | no |
| the engine-asset library `manifold_config_repo/` (the Tahoe scene, the AUROR platforms, atmosphere, weather, orbit) | yes | no |
| `Workspace.local()` defaults for `library`, `config_repo`, `sensor_library` | point into the checkout | point beside the installed package (`REPOSITORY` is five folders above `workspace.py`); every one must be passed |
| `scripts/bootstrap.py` (links DIRSIG as `external/dirsig`, materializes demo assets) | yes | no |
| `scripts/stamp_hashes.py`, `scripts/compose.py`, `scripts/s2s_scenarios.py`, `scripts/compare_layered.py`, `scripts/compare_outputs.py` (`read_envi`) | yes | no |
| an ENVI reader | `scripts/compare_outputs.py`'s `read_envi`, or `spectral` | `spectral` (a dependency of `eoptic-manifold-sim`) |

## 6. Notebook 5 against the shortest path

`notebooks/stage_05_sdk_auror_demo.ipynb` has 23 cells, 11 of them code. What each part does and whether a first rendered run needs it:

| Notebook 5 part | Cells | Needed for a first rendered run |
|---|---|---|
| setup: DIRSIG on `PATH`, work folders | 2 | the `PATH` part only when DIRSIG is not linked by `scripts/bootstrap.py` |
| library copy (the three layer folders under `outputs/`) and a new engine profile with `resources.cpu_threads: 1` | 4 | no: the copy exists to add the engine profile; one thread is for byte-identical repeats, not for a render |
| the recipe from `auror_ref` with a 16 x 16 window | 4 | yes |
| `compose`, run id, provenance | 6 | no |
| run-spec loader round trip, engine-block schema from `list_engines` | 8 | no |
| `validate`, engine-free and dry run | 10 | the engine-free check is optional; `submit_run` runs the same checks |
| the deliberate refusal (a uniform atmosphere with no weather) | 12 | no |
| `submit_run`, `wait`, artifacts by role, resubmission | 14 | `submit_run` and `wait` |
| the image through `read_envi` | 16 | reading the image: yes, with any ENVI reader |
| a second work root, byte-identical repeat | 18 | no |
| MaterialMap1, layered against pass-through, and its plot | 20, 21 | no |

The shortest path to a rendered run: `Workspace.local()`, the `auror_ref` recipe as `get_recipe` returns it with `settings[0].roi` set to 16 x 16 (2 fields edited), `submit_run`, `wait`; then `list_artifacts` and `get_artifact` (or `save_artifact`) for the image. 0 files written, 0 hashes, 4 SDK calls to a final state. `notebooks/quickstart_sdk.ipynb` follows it.

## 7. Totals

| Route | Files the user writes | Fields the user writes | Of which copied | Hashes the user types |
|---|---|---|---|---|
| a shipped recipe with a changed window | 0 | 2 | 0 | 0 |
| a shipped recipe with another library sensor (`auror_ref` to the VIS sensor) | 0 | 3 | 2 (`sensor`, `entry_id`) | 0 |
| a new recipe over the library's layers | 1 | 20 required | 4 | 0 |
| a new scene and sensor, in a checkout: recipe, scenario, engine profile (as `tahoe_static_pose`), sensor (as `auror-nir`) and the DIRSIG files copied into the library layout | 4 YAML files, and the copied DIRSIG files | 20 + 18 + 34 + 43 = 115 | 4 + 0 + 10 + 0 = 14 | 0 (4 placeholders, written by `scripts/stamp_hashes.py`) |
| the same with the installed packages alone | the same | 115 | 14 | 4 (computed by the user) |
| a committed space-to-space spec | 0 | 0 | 0 | 0 |
| a space-to-space spec by hand | 1 | 72 | 8 (3 hashes, the revision, 4 names) | 3 |
