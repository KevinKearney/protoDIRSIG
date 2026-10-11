# Rename inventory (round 17 preflight)

Every tracked-file occurrence of `protodirsig`, `PROTODIRSIG` and `protoDIRSIG` (case-insensitive `git grep`, `.claude_mem/` excluded), grouped by class; counts are matching lines per file. Classification is by the first matching rule, so a line with an import and a path counts once.

## imports (255 lines, 59 files)

- `README.md`: 1
- `scripts/api_examples.py`: 7
- `scripts/compose.py`: 1
- `scripts/crosscheck_sgp4.py`: 2
- `scripts/probe_determinism.py`: 2
- `scripts/run_demo.py`: 4
- `scripts/sweep_demos.py`: 6
- `src/protodirsig/__init__.py`: 1
- `src/protodirsig/admission.py`: 4
- `src/protodirsig/backend.py`: 14
- `src/protodirsig/compose.py`: 4
- `src/protodirsig/identity.py`: 1
- `src/protodirsig/library.py`: 4
- `src/protodirsig/motion_tasks.py`: 2
- `src/protodirsig/passthrough.py`: 2
- `src/protodirsig/platform_gen.py`: 2
- `src/protodirsig/problems.py`: 4
- `src/protodirsig/registry.py`: 5
- `src/protodirsig/run_spec.py`: 12
- `src/protodirsig/simulation.py`: 9
- `src/protodirsig/store.py`: 3
- `src/protodirsig/worker.py`: 4
- `src/protodirsig/workspace.py`: 3
- `tests/backend_conformance.py`: 4
- `tests/test_absolute_radiometry.py`: 4
- `tests/test_admission.py`: 4
- `tests/test_api_contract.py`: 7
- `tests/test_artifact_scale.py`: 4
- `tests/test_atmosphere_patches.py`: 2
- `tests/test_compose.py`: 12
- `tests/test_dirhash.py`: 2
- `tests/test_errors.py`: 8
- `tests/test_hashes.py`: 2
- `tests/test_identity.py`: 3
- `tests/test_import_boundary.py`: 11
- `tests/test_import_curve.py`: 3
- `tests/test_leo_pass.py`: 5
- `tests/test_library.py`: 5
- `tests/test_local_backend.py`: 1
- `tests/test_models.py`: 1
- `tests/test_motion_tasks.py`: 3
- `tests/test_orbit.py`: 2
- `tests/test_orbit_motion.py`: 4
- `tests/test_orbit_vector.py`: 1
- `tests/test_packaging.py`: 2
- `tests/test_passthrough.py`: 17
- `tests/test_platform_render.py`: 4
- `tests/test_problems.py`: 7
- `tests/test_registry.py`: 6
- `tests/test_renames.py`: 5
- `tests/test_run_spec.py`: 3
- `tests/test_run_spec_schema.py`: 3
- `tests/test_scene_coverage.py`: 2
- `tests/test_sensor_library.py`: 3
- `tests/test_sensor_render.py`: 2
- `tests/test_simulation.py`: 3
- `tests/test_spectral_curves.py`: 1
- `tests/test_store.py`: 6
- `tests/test_workspace.py`: 6

## environment variables (16 lines, 6 files)

- `docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md`: 1
- `src/protodirsig/contract.py`: 3
- `src/protodirsig/passthrough.py`: 4
- `tests/test_packaging.py`: 3
- `tests/test_passthrough.py`: 3
- `tests/test_sweep_demos.py`: 2

## URNs and problem types (29 lines, 12 files)

- `api/examples/compose.problem.json`: 1
- `api/examples/submit_run.problem.json`: 1
- `api/schemas/problem.schema.json`: 1
- `scripts/api_examples.py`: 1
- `src/protodirsig/errors.py`: 5
- `src/protodirsig/models.py`: 4
- `tests/backend_conformance.py`: 1
- `tests/test_api_contract.py`: 1
- `tests/test_errors.py`: 6
- `tests/test_passthrough.py`: 1
- `tests/test_problems.py`: 5
- `tests/test_store.py`: 2

## schema $ids and $refs (0 lines, 0 files)


## state and cache paths (35 lines, 13 files)

- `BACKLOG.md`: 1
- `README.md`: 1
- `api/examples/cancel_run.json`: 1
- `api/examples/get_run.json`: 1
- `api/examples/get_sweep.json`: 3
- `api/examples/list_artifacts.json`: 1
- `api/examples/list_artifacts.pass.json`: 15
- `api/examples/submit_run.json`: 1
- `api/examples/submit_sweep.json`: 3
- `docs/DIRSIG_demo_reference_runs.md`: 1
- `docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md`: 1
- `scripts/api_examples.py`: 1
- `src/protodirsig/workspace.py`: 5

## log and warning text (6 lines, 4 files)

- `src/protodirsig/__init__.py`: 1
- `src/protodirsig/registry.py`: 1
- `src/protodirsig/workspace.py`: 1
- `tests/test_workspace.py`: 3

## provenance or record fields written into outputs (4 lines, 3 files)

- `src/protodirsig/worker.py`: 2
- `tests/test_local_backend.py`: 1
- `tests/test_store.py`: 1

## entry points and packaging (11 lines, 4 files)

- `.gitignore`: 1
- `environment.yml`: 4
- `pyproject.toml`: 2
- `setup.py`: 4

## notebooks (114 lines, 9 files)

- `notebooks/dirfm_tutorials/tutorial_auror_scene.ipynb`: 18
- `notebooks/dirfm_tutorials/tutorial_dirfm_basics.ipynb`: 5
- `notebooks/dirfm_tutorials/tutorial_orbit_to_ground.ipynb`: 5
- `notebooks/dirfm_tutorials/tutorial_tacoma_scene.ipynb`: 22
- `notebooks/sidebars/vehicle_point_source.ipynb`: 6
- `notebooks/stage_01_auror_from_runspec.ipynb`: 22
- `notebooks/stage_02_conformance_template.ipynb`: 16
- `notebooks/stage_03_sensor_sweep.ipynb`: 12
- `notebooks/stage_04_leo_pass.ipynb`: 8

## docs prose (71 lines, 18 files)

- `BACKLOG.md`: 4
- `README.md`: 12
- `api/README.md`: 3
- `api/openapi.yaml`: 2
- `api/operations.md`: 2
- `api/requirements.md`: 1
- `docs/DIRSIG_determinism.md`: 1
- `docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md`: 25
- `docs/diagrams/run_workflow.mmd`: 2
- `docs/diagrams/run_workflow.svg`: 1
- `docs/diagrams/sdk_api.mmd`: 1
- `docs/diagrams/sdk_api_sequence.mmd`: 1
- `manifold_contracts/README.md`: 5
- `manifold_contracts/dirsig-engine-1.schema.json`: 1
- `manifold_contracts/run-spec-1.schema.json`: 7
- `manifold_contracts/vectors/identity/README.md`: 1
- `manifold_contracts/vectors/orbit/README.md`: 1
- `notebooks/README.md`: 1

## comments in hash-stamped or vector data files (88 lines, 49 files)

- `manifold_contracts/vectors/compose/auror_ref/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/auror_ref/recipes/auror_ref.yaml`: 1
- `manifold_contracts/vectors/compose/auror_ref/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/black_level_nonzero/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/black_level_nonzero/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/engine_override/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/engine_override/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/engine_override_missing_path/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/engine_override_missing_path/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/engine_override_off_list/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/engine_override_off_list/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/inline_sensor/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/inline_sensor/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/manifold_sensors/auror-nir.yaml`: 1
- `manifold_contracts/vectors/compose/manifold_sensors/deepscan_850_306_nir_1280.yaml`: 1
- `manifold_contracts/vectors/compose/manifold_sensors/synthetic_600_200_vis_1920.yaml`: 1
- `manifold_contracts/vectors/compose/member_in_two_layers/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/member_in_two_layers/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/missing_sensor/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/missing_sensor/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/settings_by_entry_id/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/settings_by_entry_id/recipes/auror_ref.yaml`: 1
- `manifold_contracts/vectors/compose/settings_by_entry_id/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_duplicate_entry_id/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_duplicate_entry_id/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_fidelity_for_absent_sensor/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_fidelity_for_absent_sensor/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_member_for_no_sensor/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_member_for_no_sensor/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_over_cap/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_over_cap/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_sensor_and_sensors/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_sensor_and_sensors/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_sensor_without_settings/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_sensor_without_settings/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_three_sensors/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/sweep_three_sensors/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/synthetic_vis/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/synthetic_vis/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/unresolved_entry_id/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_contracts/vectors/compose/unresolved_entry_id/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_run_specs/engine_profiles/tahoe_leo_pass.yaml`: 1
- `manifold_run_specs/engine_profiles/tahoe_static_pose.yaml`: 2
- `manifold_run_specs/recipes/auror_ref.yaml`: 1
- `manifold_run_specs/scenarios/tahoe_leo_pass.yaml`: 2
- `manifold_run_specs/scenarios/tahoe_static_pose.yaml`: 2
- `manifold_sensors/auror-nir.yaml`: 1
- `manifold_sensors/deepscan_850_306_nir_1280.yaml`: 1
- `manifold_sensors/synthetic_600_200_vis_1920.yaml`: 1

## other code strings (91 lines, 23 files)

- `scripts/api_examples.py`: 2
- `scripts/bootstrap.py`: 2
- `scripts/compose.py`: 1
- `scripts/crosscheck_sgp4.py`: 3
- `scripts/gen_models.py`: 4
- `scripts/probe_determinism.py`: 1
- `scripts/run_demo.py`: 1
- `scripts/stamp_hashes.py`: 2
- `src/protodirsig/__init__.py`: 4
- `src/protodirsig/admission.py`: 1
- `src/protodirsig/backend.py`: 1
- `src/protodirsig/compose.py`: 2
- `src/protodirsig/contract.py`: 3
- `src/protodirsig/identity.py`: 1
- `src/protodirsig/library.py`: 1
- `src/protodirsig/passthrough.py`: 1
- `src/protodirsig/problems.py`: 1
- `src/protodirsig/registry.py`: 4
- `src/protodirsig/run_spec.py`: 5
- `src/protodirsig/simulation.py`: 2
- `src/protodirsig/store.py`: 2
- `src/protodirsig/worker.py`: 5
- `src/protodirsig/workspace.py`: 42

## tests (other) (28 lines, 14 files)

- `tests/backend_conformance.py`: 1
- `tests/test_admission.py`: 1
- `tests/test_api_contract.py`: 2
- `tests/test_compose.py`: 1
- `tests/test_dirhash.py`: 1
- `tests/test_errors.py`: 1
- `tests/test_identity.py`: 1
- `tests/test_import_boundary.py`: 2
- `tests/test_library.py`: 1
- `tests/test_models.py`: 1
- `tests/test_module_table.py`: 2
- `tests/test_packaging.py`: 6
- `tests/test_store.py`: 2
- `tests/test_workspace.py`: 6

Total: 748 lines.

## Distinct values

- Environment variables: `PROTODIRSIG_CONTRACTS`, `PROTODIRSIG_CPUFREQ`, `PROTODIRSIG_THERMAL_ZONES`
- Problem URNs: `urn:protodirsig:problem:admission`, `urn:protodirsig:problem:compose`, `urn:protodirsig:problem:execution`, `urn:protodirsig:problem:invalid-request`, `urn:protodirsig:problem:not-found`
- Schema `$id`s: none contains the old name (all four are `https://schemas.manifold.example/contracts/<name>.schema.json`; the API schemas checked in step 3).
- State and cache paths: `$XDG_STATE_HOME/protodirsig/work` (else `~/.local/state/protodirsig/work`), `~/.cache/protodirsig/work` (legacy mention), `/tmp/protodirsig/runs/...` in API examples (the example generator's work root).
- Record fields: `protodirsig_version` in `execution.json`.
