# Engine author guide

An engine reaches the SDK through one adapter object: `manifold.core` defines the protocol and names no engine, `manifold.sim` discovers adapters from installed distributions, and admission, execution and collection go through the adapter alone. This guide states the protocol as it is in `packages/core/src/manifold/core/engine.py`, how an adapter is registered and admitted, what the boundary tests forbid, and the two adapters in the repository (DIRSIG and SatSim) as worked examples. Section 7.3 of the [CONOPS and Guide](MANIFOLD_DIRSIG_CONOPS_and_Guide.md) is the contract-level summary; `tests/fixtures/engine_dummy/` is the smallest working adapter, exercised by `tests/test_engine_dummy.py`. `tests/test_engine_author_guide.py` checks each name and signature this guide gives against the code.

## The protocol

`manifold.core.engine.EngineAdapter` is a `typing.Protocol` (runtime-checkable). Its members, with the signatures the protocol declares:

| Member | Returns | Called |
|---|---|---|
| `info(self)` | `EngineInfo` | at registration (the registry checks that `info().engine_id` is the registered id), by `list_engines` |
| `engine_schema(self, engine_block)` | the engine block's JSON Schema (a mapping) or None | at admission (schema check) |
| `compose_problems(self, settings)` | a list of `(field, message)` | at composition, on the recipe's settings |
| `semantic_rules(self, spec)` | a list of messages | at admission, after the schema |
| `resolve(self, descriptor, engine_block, context: ResolveContext)` | the engine's resolved run (any object), or raises `RunSpecError` | at admission |
| `library_problems(self, spec, resolved)` | a list of messages | at admission, after resolution |
| `plan(self, context: RunContext)` | `LaunchPlan` | by the worker, before the engine process starts |
| `collect(self, output_dir, run_dir)` | `Collection` | by the worker, after the process ends or is stopped |
| `fingerprint(self, spec=None)` | a mapping written into the execution record | by the worker |
| `resources(self, spec=None)` | a `manifold.core.resources.ResourceDeclaration` | at admission and by the worker |

Optional members, looked up with `getattr`: `availability(self)` (None, or why the engine's runtime cannot run here; `Registry.status`), `dry_run(self, spec, resolved, scratch_root, options=None)` (the engine's own dry run, for `validate` at level `dry_run`), and `schemas(self)` (the engine-block schemas the adapter publishes; without it `manifold.core.contract.adapter_schemas` uses `engine_schema(None)`).

The data types, all frozen dataclasses in `manifold.core.engine`:

| Type | Fields (defaults) |
|---|---|
| `EngineInfo` | `engine_id`, `adapter_version`, `contracts=()`, `modes=("layered",)`, `description=""` |
| `ResolveContext` | `config_repo`, `sensor_library=None`, `run_spec_path=None` |
| `RunContext` | `run_dir`, `spec`, `config_repo`, `sensor_library=None`, `output_dir=None`, `options={}` |
| `EnvironmentPolicy` | `set={}`, `unset=()`, `isolate_home=False`, `thread_variables=()`, `gpu_variable=None` |
| `LaunchPlan` | `argv`, `cwd=None`, `env=EnvironmentPolicy()`, `interpreter=None`, `python_module=None`, `stage={}`, `expected_outputs=()` |
| `CollectedArtifact` | `path`, `role`, `frame=None`, `name=None` |
| `Collection` | `artifacts`, `verdict`, `message=None`, `record={}` |

`MODES` is `("layered", "passthrough")`, an initial vocabulary. The verdicts are `complete`, `incomplete` and `failed` (`VERDICTS`). The artifact roles' initial set is `product`, `truth`, `preview`, `log`, `config`, `metadata` (`manifold.core.artifacts.ROLES`; `manifold.core.engine.ROLES` lists the same set without `preview`). A `LaunchPlan` runs `argv[0]` as given when `interpreter` and `python_module` are None; with `python_module` the command is `<python> -m <python_module> <argv...>`, `<python>` being the SDK's interpreter (`interpreter` None), an interpreter path, or the `python` of a named conda environment.

The engine side of execution is the adapter's own business: what the launched process runs is not part of the protocol. The DIRSIG adapter's process calls its private `_execute`; the SatSim adapter's runs its shipped `launcher.py`.

## Registration

A distribution registers its adapter in the entry-point group `manifold.engines` (`manifold.sim.engines.GROUP`): the entry point's name is the engine id, the value of `descriptor.origin.engine`, and its object a zero-argument factory (a class or a function) returning the adapter.

```toml
[project.entry-points."manifold.engines"]
dirsig = "manifold.engines.dirsig.adapter:DirsigAdapter"
```

`manifold.sim.engines.build_registry()` reads the group without importing any engine; each adapter loads on first use. One that fails to load is listed unavailable with the reason and leaves the others unaffected; two distributions registering one id make that id unavailable, naming both. Importing `manifold.sim` calls `registry()`, which builds the registry once and installs it as `manifold.core.engine`'s default (`set_default_registry`). A process that uses `manifold.core` alone passes `registry=` to `compose`, `validate_spec` and the schema checks; with none passed and none configured they raise `RegistryNotConfigured`.

`Registry.describe()` gives the engine set as data (per engine its id, import target `module:attribute`, source, whether the adapter loaded and its version). `LocalBackend` writes it into the run's `job.json`, and the worker rebuilds exactly that set with `Registry.from_description(description, manifold.sim.engines.load_target)`. A registration therefore needs an importable target: an adapter class defined inside a function cannot be run by the worker.

## Admission and hashing

`manifold.core.admission.validate_spec(spec, run_spec_path=None, config_repo=None, sensor_library=None, *, resolved=None, registry=None)` runs the engine-free checks on a parsed run spec and returns a `ValidationReport`; it never raises for a bad spec. In order:

1. **Schema** (`manifold.core.contract.schema_errors`): the published `run-spec/1` schema, then the engine block against the schema the adapter for `descriptor.origin.engine` returns from `engine_schema`, then `semantic_errors`: an engine id no registered adapter serves (naming the registered engines), `descriptor.opaque` without `engine.mode: passthrough` or the reverse, the adapter's `semantic_rules(spec)`, and a `resources` request its `resources(spec)` declaration does not cover.
2. **Resolution**: `adapter.resolve(spec["descriptor"], spec.get("engine"), ResolveContext(config_repo, sensor_library, path))`. A `RunSpecError` (with `pointer=`, the JSON Pointer of the member) is a refusal; so is a `KeyError`, `TypeError` or `AttributeError` raised there.
3. **Library files**: `adapter.library_problems(spec, resolved)`, then the asset rule for the assets the adapter declares and the run requests (unstamped, missing or mismatched digests are refused).
4. **Unstamped references**: listed (`run_spec.unstamped_refs`); validation reports them, submission refuses them.
5. **Run id**: `manifold.core.identity.run_id(spec, sensor_library)`.

The adapter takes no part in hashing. The run id is the sha256 of the RFC 8785 canonical JSON of the resolved run spec (the sensor reference replaced by its block; `resources` reduced to `cpu_threads`, `gpu`, `assets` and `interpreter`). It therefore covers exactly what the spec states by value and, through each stamped `content_hash` the adapter verifies, the bytes of each referenced file. A file the engine reads that the spec neither states nor references by a verified hash is outside the id: two runs could differ in it under one id. An adapter's `resolve` and `library_problems` are where such a file must be refused or covered.

`scripts/engine_contracts.py --check` fails when a registered engine's engine-block schema is not published under `manifold_contracts/` with its `$id`, or differs from the one its adapter applies; `manifold_contracts/vectors/admission/` holds the schema-stage verdicts (`tests/test_admission_vectors.py`).

## What the boundary tests forbid

- `tests/test_core_boundary.py` parses every `.py` under `packages/core` at every depth. Core may not import `manifold.sim`, `manifold.engines`, `dirfm`, `protodirsig` or a module named like an engine id (by `import`, `from ... import`, `importlib.import_module` or `__import__`, a non-literal argument included); may not hold a string literal that is such a module path; may not hold a string literal equal to an engine id except as a member name; and may not hold dirfm's generator strings or any literal naming `dirsig-engine`. `packages/sim` may not import `manifold.engines.*` or `dirfm`. An engine package (`packages/engine-*`) may import `manifold.core` and may not import `manifold.sim`. The engine ids checked are the known ones (`dirsig`, `satsim`, `usd`, `field`) and every id registered in the environment. The published run-spec schema names no engine.
- `tests/test_import_boundary.py` runs each check in a fresh interpreter: the modules it lists as pure load neither `dirfm` nor the propagator (`skyfield`, `sgp4`); importing any `manifold.core` module loads no `manifold.sim` module, no engine package and no numpy; compose and engine-free validation run with the engine packages unimportable; importing `manifold.sim` loads no engine package; no distribution ships the `manifold/` or `manifold/engines/` namespace `__init__.py`; without `dirfm` the SDK imports and lists `dirsig` unavailable.
- `tests/test_distribution_graph.py` reads each `pyproject.toml`: an engine distribution depends on `eoptic-manifold-core` only among the manifold distributions (pinned to the shared version) plus its own third-party packages, registers a `manifold.engines` entry point, and ships no namespace `__init__.py`.

## Worked example 1: DIRSIG (`manifold.engines.dirsig.adapter.DirsigAdapter`)

Distribution `eoptic-manifold-engine-dirsig`; entry point `dirsig = manifold.engines.dirsig.adapter:DirsigAdapter`; dependencies `eoptic-manifold-core==0.0.1`, `dirfm`, `pyyaml`, `lxml`, `numpy`.

- `info()`: `EngineInfo("dirsig", <distribution version>, ("dirsig-engine/1",), ("layered", "passthrough"), ...)`.
- `engine_schema(block)`: `dirsig-engine-1.schema.json`, the copy packaged under `_contracts/` (written by the build), else the one in the contract folder (`schema_path()`).
- `availability()`: `dirfm` must be importable, checked with `importlib.util.find_spec` without importing it.
- `compose_problems(settings)`: a non-zero `black_level` (DIRSIG applies it as a channel bias), as `(field, message)`.
- `semantic_rules(spec)`: `engine.run.seed` or `engine.platform.integration_samples` read from YAML as a float.
- `resolve`: `resolve_passthrough` for `mode: passthrough`, else `run_spec.resolve_run` (the layered form).
- `library_problems`: `run_spec.check_library_files` (the platform template renders from the sensor-spec and the settings, the orbit files load); nothing for the pass-through form.
- `plan(context)`: `python -m manifold.engines.dirsig.runner <run_dir>` in the SDK's interpreter, a default environment policy, no expected outputs. The runner reads `job.json`, `run_spec.yaml` and `grant.json` and calls `DirsigAdapter._execute`, which builds the job with dirfm and runs the dry run and the render (layered), or runs `scene2hdf` and `dirsig5` on a copy of the demo directory with a per-run `HOME` (pass-through), and writes `engine_result.json`.
- `collect(output_dir, run_dir)`: no `engine_result.json` is `incomplete`; a failed outcome is `failed` with the run-level logs; a pass-through run lists every file in `output/`, with a role by suffix (`passthrough_role`); a layered run lists the run-level logs and, per capture from the engine's `log_info.json`, the image (`product`), the truth images (`truth`) and their headers (`metadata`), each with its `frame`. A file the log names that was not written makes the run `failed`.
- `fingerprint(spec)`: the `dirfm` revision in use against `engine.generator.revision`, and the DIRSIG installation and version.
- `resources(spec)`: any thread count (no variables: the runner passes the grant as `--threads`), no GPU, network `none`, no declared asset.
- `dry_run(spec, resolved, scratch_root, options=None)`: DIRSIG's own dry run in a scratch directory; `(passed, engine_checked, messages)`.

The module also exposes `registry()`, a registry that serves `dirsig` whether or not `manifold.sim` was imported, so the engine's own modules (`Simulation`, `LocalRegistry`) validate without it.

## Worked example 2: SatSim (`manifold.engines.satsim.adapter.SatsimAdapter`)

Distribution `eoptic-manifold-engine-satsim`; entry point `satsim = manifold.engines.satsim.adapter:SatsimAdapter`; dependencies `eoptic-manifold-core==0.0.1` and `pyyaml`. SatSim runs in its own interpreter and the adapter imports neither `satsim`, `tensorflow` nor `numpy`.

- `info()`: `EngineInfo("satsim", <version>, ("satsim-engine/1",), ("passthrough",), ...)`: pass-through only.
- **The opaque descriptor.** A SatSim run spec's descriptor is `meta`, `origin`, `fidelity` and `opaque: {source: passthrough}`, with no `collection`, `sensor` or `settings`, and the engine block states `mode: passthrough`. The core's semantic rule ties the two together; SatSim fills no descriptor field from its configuration. The engine block is `mode`, `config` (a library ref, a file or a directory holding exactly one `config.yaml`, `config.yml` or `config.json`), a required integer `seed` and `device: cpu`.
- `engine_schema(block)` and `schemas()`: `satsim-engine-1.schema.json`, shipped in the package.
- `availability()`: the interpreter is found (`MANIFOLD_SATSIM_PYTHON`, then `satsim.python` in `$XDG_CONFIG_HOME/manifold/engines.yaml`, then a conda environment named `satsim`) and imports `satsim`, probed once per process in a subprocess.
- `semantic_rules(spec)`: a `device` other than `cpu` or a GPU request is refused ("SatSim GPU behavior is unverified").
- `resolve`: `resolve_config` finds the configuration, verifies its stamped digest (a file's sha256 or a directory's `dirhash/1`) and parses it; a failure is a `RunSpecError` at `/engine/config`.
- `library_problems`: `config_problems`: exactly one of SatSim's roots (`fpa`, `radar`, `passive_rf`), `sim.samples` 1, and no file named outside what the reference hashes.
- `plan(context)`: verifies the digest again, stages the configuration read-only in `<run_dir>/input/`, writes `input/launch.json`, and returns `launcher.py <run_dir>` with `interpreter` set to SatSim's Python, `isolate_home=True`, the four thread variables, the SDK's Python variables (`PYTHONPATH`, `PYTHONHOME`, `PYTHONSTARTUP`) and SatSim's own path variables unset, and `expected_outputs=("satsim_result.json",)`.
- `collect`: the set folder's files by role (`ImageFiles/*.fits` `product`, `Annotations/*.json` `truth`, and so on); `complete` only when the launcher reported success, every frame was written and SatSim's end-of-run files exist.
- `fingerprint`: the interpreter, its probe, the launcher's sha256 and the asset digests.
- `resources`: any thread count carried in `TF_NUM_INTRAOP_THREADS`, `TF_NUM_INTEROP_THREADS`, `OMP_NUM_THREADS` and `NUMBA_NUM_THREADS`; 1 GiB of memory; 256 MiB of scratch; no GPU; network `none`; two assets (`de421.bsp` in `MANIFOLD_SATSIM_EPHEMERIS`, `finals2000A.all` in `MANIFOLD_SATSIM_IERS`); the interpreter.

**Stated limitation: the sprite filename.** `config_problems` scans a configuration for the members that name files, `$import`, `$cache`, `path` and `file` (`_references`). A sprite model names its file in `filename`, which the scan does not include. A single-file configuration naming a sprite, even at an absolute path outside the library, is therefore admitted with no problem: `config_problems` returns `[]` for a model `{mode: sprite, filename: /abs/plate.fits}` and a refusal for the same model with `file:`. The sprite is then neither staged nor hashed, so two different sprites could run under one run id. Not fixed in this repository (BACKLOG, "Space-to-space: what round 31 leaves open"). The space-to-space plate configuration avoids it by being a directory reference whose sprite lies inside the directory (`input/plate.fits`, the path where the plan stages the directory).

## Checklist for a third engine

1. A distribution `eoptic-manifold-engine-<id>` shipping the package `manifold.engines.<id>`, with no `__init__.py` at `manifold/` or `manifold/engines/`; dependencies `eoptic-manifold-core==<shared version>` and its own third-party packages, never `eoptic-manifold-sim` (`tests/test_distribution_graph.py`).
2. An entry point `<id> = manifold.engines.<id>.adapter:<Adapter>` in `manifold.engines`; the class is importable at module level, and the adapter module imports nothing heavy at import time (validation loads it).
3. `info()` with `engine_id` equal to the entry point's name and `descriptor.origin.engine`, its version, its contract `<id>-engine/<major>` and its modes.
4. The engine-block schema shipped in the distribution, with a `$id` under the contract base, and published under `manifold_contracts/` (`scripts/engine_contracts.py`, then `--check`).
5. `semantic_rules` and `compose_problems` for what the schema cannot say; `resolve` that finds every file the block names and verifies its stamped hash, raising `RunSpecError` with a pointer; `library_problems` for checks on the resolved files. Every file the engine will read is either stated by value or covered by a verified hash (see the SatSim limitation above).
6. For a pass-through engine, an opaque descriptor and `mode: passthrough`; descriptor members the engine does not read are still in the run id.
7. `resources()`: the thread range and the variables that carry the count, memory, GPU, scratch, network, named assets with the variables their staged paths arrive in, and the interpreter.
8. `plan()`: a `LaunchPlan` with a per-run `HOME` where the engine writes caches, and expected outputs; `collect()`: roles from the initial set and a verdict that does not rest on the exit status alone (`incomplete` when an end-of-run file is missing).
9. `fingerprint()`: tool and data versions for the execution record; optionally `availability()` and `dry_run()`.
10. Tests in the pattern of `tests/test_engine_dummy.py` (install, compose, validate, admit, run through `LocalBackend`, list, cancel, uninstall) and `tests/test_satsim_adapter.py` (each refusal, the plan and its environment, the collector's verdicts on synthetic outputs, the import rule); `tests/test_core_boundary.py` and `tests/test_distribution_graph.py` cover every `packages/engine-*` without change.
