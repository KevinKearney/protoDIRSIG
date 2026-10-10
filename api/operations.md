# protoDIRSIG SDK API: operations

Status: proposed. Contract version `sdk-api/1`.

The operation set of the SDK. The Python facade and the REST API expose the same operations with the same inputs, outputs and errors. `Mode` is `pure` (no state is created or changed; the same inputs give the same output), `sync` (changes state and completes before returning) or `async` (returns an id at once; the work continues, and its state is read with `get_run` or `get_sweep`). Every error is a problem details object (RFC 9457); an error caused by an authored file carries `layer` (the file, relative to the library root) and `field` (the field in that file). `Today` names the existing code the operation would be built on, or `none`. `Status` is `built`, `partial` or `gap`. Requirement ids refer to `requirements.md`.

| Operation | Inputs | Output | Errors | Mode | Idempotency | Requirements | Today | Status |
|---|---|---|---|---|---|---|---|---|
| `list_sensors`, `list_scenarios`, `list_engine_profiles`, `list_recipes` (the library family, one per resource kind) | none | the resources of that kind: for each, its `name` and the `sha256` of its file | none | pure | safe: reads only | R-12, R-01, R-06 | none (callers glob `manifold_sensors/` and `manifold_run_specs/`) | gap |
| `get_sensor`, `get_scenario`, `get_engine_profile`, `get_recipe` | the resource `name` | the document as authored (for a sensor, a `sensor-spec/1` document), with its `name` and `sha256` | not found (404); a file that does not parse or is not of its kind (problem, with `layer`) | pure | safe: reads only | R-12, R-04, R-16, R-06 | `run_spec.load_sensor_spec` for sensors; none for the other kinds (`compose._load_layer` is private) | partial |
| `compose` | a recipe (a library recipe name, or a recipe document), and optionally `inline_sensor` and `max_runs` | the sweep id, and for each run: its name, its composed `run-spec/1` document, and its provenance (the layer file and `sha256` of each member). A one-sensor recipe gives one run | a recipe that does not compose (422, with `layer` and `field`) | pure | same inputs give the same bytes | R-02, R-03, R-04, R-05, R-08, R-15, R-06 | `compose.compose_sweep` (`compose.compose`, `compose.explain` for one run) | partial |
| `validate` | a run spec, or a recipe (composed first) | for each run: `accepted` or `rejected`, the outcome of each check (compose, schema, resolution, execution as a DIRSIG dry run) and the reasons for each failed check | a recipe that does not compose (422, with `layer` and `field`) | pure | same inputs give the same verdict | R-02, R-08, R-15, R-16, R-01, R-06 | `LocalRegistry.submit`, `LocalRegistry.submit_recipe`, `Simulation.validate` | partial |
| `submit_run` | a run spec, or a one-sensor recipe | the run id and the run's state after admission (`accepted` or `rejected`); execution continues in the background | a recipe that does not compose (422, with `layer` and `field`); a run id already submitted with different content (409) | async | resubmitting the same run spec returns the existing run id | R-13, R-09, R-10, R-01, R-07, R-06 | `LocalRegistry.submit_recipe` then `Simulation.run`, both synchronous | partial |
| `submit_sweep` | a recipe naming several sensors (or one) | the sweep id and the id and admission state of each run | a recipe that does not compose (422, with `layer` and `field`) | async | resubmitting the same recipe returns the existing sweep id and run ids | R-05, R-13, R-14, R-09, R-01, R-06 | `LocalRegistry.submit_sweep` then `LocalRegistry.run_sweep`, both synchronous | partial |
| `get_run` | a run id | the run's status: id, name, state, errors, and the artifact references once it has `rendered` | unknown run id (404) | pure | safe: reads only | R-13, R-07, R-08, R-06 | none (`registry.RunStatus` and `registry.SubmissionResult` exist only in memory, not by id) | partial |
| `get_sweep` | a sweep id | the sweep's status: id, recipe, and the status of each run in sensor-list order | unknown sweep id (404) | pure | safe: reads only | R-13, R-14, R-06 | none (`registry.SweepResult` exists only in memory, not by id) | partial |
| `cancel_run` | a run id | the run's status, `cancelled` | unknown run id (404); a run already in a final state (409) | sync | cancelling a `cancelled` run returns it unchanged | R-13, R-06 | none | gap |
| `list_artifacts` | a run id | the run's artifact references `{name, sha256, media_type, uri}`: the composed run spec, the image and its header, the truth images, the DIRSIG run and info logs | unknown run id (404); a run that has not rendered (409) | pure | safe: reads only | R-07, R-10, R-03, R-06 | `simulation.RunResult` (`image`, `truth`, `output_dir`, `run_log`, `info_log`) as paths and parsed logs | partial |
| `get_artifact` | a run id and an artifact name | the artifact's bytes, with its `media_type`; the bytes match the reference's `sha256` | unknown run id or artifact name (404) | pure | safe: reads only | R-07, R-10, R-06 | none (callers open the paths in `RunResult`) | gap |

## Run states

A run has one of six states. `accepted` and `rejected` are decided by admission (the checks of `validate`) before `submit_run` or `submit_sweep` returns; execution after that is asynchronous.

| State | Meaning | Final |
|---|---|---|
| `accepted` | admitted: the run spec composes, is valid, its references resolve, and DIRSIG accepts it in a dry run; waiting to execute | no |
| `rejected` | not admitted; `errors` gives the reasons | yes |
| `running` | DIRSIG is executing the run | no |
| `rendered` | execution finished; the artifacts are available | yes |
| `failed` | execution stopped with an error; `errors` gives it | yes |
| `cancelled` | cancelled before it finished | yes |

Transitions: `accepted` to `running`; `running` to `rendered` or `failed`; `accepted` or `running` to `cancelled`. A sweep has no state of its own: `get_sweep` reports the state of each of its runs.

## Where the code departs from the contract today

- No operation returns artifact references. `RunResult` holds file paths (`image`, `truth`, `output_dir`) and the parsed logs, and no file is hashed or typed.
- Execution is synchronous. `Simulation.run` and `LocalRegistry.run_sweep` block until DIRSIG finishes; nothing runs in the background, so `running` is never observable.
- There are no run ids. Runs are identified by `meta.name` inside a `SweepResult`, and results exist only in the memory of the process that made them. The sweep id exists (`compose.sweep_id`), but it is computed from the recipe's bytes, and no run id is computed from a composed spec's bytes.
- Nothing can be looked up later: there is no store of runs or sweeps, so `get_run` and `get_sweep` have nothing to read.
- There is no cancel.
- There are no library reads except `load_sensor_spec`: no `list` operation for any kind, and no public reader for scenarios, engine profiles or recipes.
- Errors are exceptions. `ComposeError` carries `layer` and `field`; `RunSpecError` (resolution) carries only a message, and the admission checks report reasons as plain strings in `SubmissionResult.reasons`. Nothing produces a problem details object.
- Validation and submission are one call. `LocalRegistry.submit` both validates and returns the object that `run` executes; there is no `validate` that is only a check.
- `validate` is pure in the contract's sense (it changes no library file and gives the same verdict for the same inputs), but its execution check runs `dirsig5 --dry_run` in a scratch directory, so it needs a local DIRSIG installation.
- A recipe is accepted only as a file path in a library folder; the contract also accepts a recipe document.
- Resubmission is not idempotent: each `submit_sweep` call writes and validates its runs again in a new directory.
