# Glossary: your words and the SDK's

The left column is what you would call it; the middle column is the name the SDK, its messages and its documents use. [The user manual](User_manual.md) uses both.

| Your word | The SDK's word | What it is |
|---|---|---|
| simulation | run | One run spec rendered once by an engine; it has a run id, a state and a result. |
| a set of simulations | sweep | The runs one recipe gives when it lists several sensors (`sensors:`), one per sensor; it has a sweep id. |
| the file I edit | recipe | A `compose/1` YAML file or dict naming a sensor, a scenario and an engine profile, with the settings and the fidelity statement. |
| what actually runs | run spec | The `run-spec/1` document the SDK composes from a recipe and its layers; not edited by hand. |
| merging the files | compose | Making the run spec from a recipe and the layers it names (`Workspace.compose`). |
| the parts a recipe names | layers | The scenario, the engine profile and the sensor, each a file in a library. |
| sensor | sensor | A `sensor-spec/1` file in the sensor library (`manifold_sensors/`): optics, focal planes, channels; one or more cameras, each an *entry* with an `entry_id`. |
| scene | scenario, engine profile, scene | The scenario says when and from where (epoch, platform position, geometry, atmosphere and target kinds); the engine profile names the DIRSIG scene and the rest of DIRSIG's inputs; the DIRSIG scene itself sits in the engine-asset library (`manifold_config_repo/scenes/`). |
| DIRSIG settings | engine profile, engine block | The `engine` member of a run spec, written in the engine profile: scene, platform template, motion, capture times, atmosphere, weather, seed. |
| camera settings | settings | The `settings` members of a recipe, one per camera (`entry_id`): exposure time, frame rate, gain, black level, window. |
| window, image size | roi | The region of interest, `settings[...].roi`: `Width`, `Height`, and an optional offset. |
| what the simulation is good for | fidelity | The recipe's statement of what is modeled, approximated and absent, and what the run is valid for. |
| check before running | validate, admission | `Workspace.validate` runs the checks without starting anything; admission is the same checks when `submit_run` or `submit_sweep` accepts a run. |
| DIRSIG's own check | dry run | `validate(..., engine_check="dry_run")`: DIRSIG reads the generated input files without rendering. |
| the checks | schema, resolution, content_hash, library_files | The documents' structure; every named file found in the libraries; every file unchanged since its hash was recorded; the sensor and settings against the platform template. |
| error, refusal | problem | What a refusal carries: `title`, `detail`, and the `layer` and `field` that caused it (`ProblemError.problem`). |
| simulation ID, fingerprint | run id | The sha256 of the run spec's canonical JSON: 64 hex digits; the same run spec always has the same id. |
| file fingerprint | content hash | `content_hash: "sha256:..."`: the sha256 of a library file (or the `dirhash/1` digest of a scene folder), recorded where the file is named. |
| where a value came from | provenance | Per member of the run spec, the layer file it came from and that file's hash (`Workspace.compose`). |
| result | run status, artifacts | The status has the `state` (`accepted`, `running`, `rendered`, `failed`, `cancelled`) and the `verdict`; the artifacts are the files the run kept. |
| did it work | verdict | `complete` (every expected output there), `incomplete` or `failed`. |
| the image | artifact with role `product` | An ENVI image (`.img` with its `.hdr`, role `metadata`); `truth`, `log` and `config` are the other common roles. |
| the folder with my runs | work root | The folder `Workspace.local(work=...)` keeps every run in, one folder per run id under `runs/`. |
| the simulator | engine | DIRSIG5 (or SatSim); an engine package connects it to the SDK. |
| the shared files | library | The read-only folders of recipes, scenarios, engine profiles (`manifold_run_specs/`), sensors (`manifold_sensors/`) and DIRSIG files (`manifold_config_repo/`). |
| the demo as DIRSIG ships it | pass-through form | A run spec that names a DIRSIG demo folder and its simulation file, run as authored. |
| the demo rewritten as layers | layered form | A run spec whose engine block states the demo's inputs member by member. |
| what the answer should be | closed form, ratio | The value a space-to-space geometry predicts (a target's projected area over the pixel footprint squared, times the Sun's cosine; a sphere's phase function; speed times exposure for a streak); a record's `ratio` is measured over it. |
| full frame, small window | native size, `-w64` | A space-to-space spec renders the sensor's 500 x 500 frame, or with `-w64` in its name a 64 x 64 window about the target; compare like with like. |
| rays per pixel | path count, adaptive sampling | How many paths DIRSIG traces for a pixel; it chooses per pixel, more for a target named `::IMPORTANT::`; no run-spec member fixes it. |
| how far off it can be | sampling-effect envelope | `docs/s2s_envelope.md`: each space-to-space record's deficit against its closed form, by target size in pixels, motion and label, with what removes it. |
| a second simulator as a check | SatSim control | The same space-to-space geometry imaged by SatSim, which has no adaptive per-pixel sampling, beside the DIRSIG record. |
