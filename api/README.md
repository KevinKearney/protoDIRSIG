# protoDIRSIG SDK API contract

Status: proposed. Contract version `sdk-api/1`.

This folder is the contract of the protoDIRSIG SDK: the operations it offers, their inputs, outputs and errors, and the payload schemas they exchange. The SDK's Python class and its REST wrapper are to be written and tested against it. The SDK class is a hand-written facade over a `Backend` protocol with two implementations: `LocalBackend`, over the SDK's existing composer, registry and simulation code, which needs no server; and `RemoteBackend`, a REST client generated from `openapi.yaml`. Nothing here is implemented yet beyond what `operations.md` marks `built` or `partial`.

## Contents and reading order

1. `requirements.md`: what the SDK must do (R-01 onward), why, the test that verifies each requirement today, and its status.
2. `operations.md`: the operation set (library reads, compose, validate, submit, status, cancel, artifacts), with inputs, outputs, errors, mode, idempotency, the requirements each serves and the existing code it would be built on; the run states; the rules for run and sweep ids; and the list of places where today's code departs from the contract.
3. `schemas/`: JSON Schema (2020-12) for every request and response body: `artifact_ref`, `artifact_list`, `run_status`, `sweep_status`, `compose_request`, `compose_response`, `validate_request`, `validate_response`, `submit_run_request`, `submit_sweep_request`, `library_list`, `library_document`, `sensor_document`, `run_spec_document` and `problem`. A sensor document is referenced from `manifold_contracts/sensor-spec-1.schema.json`, and a run spec (`run_spec_document`, used by `compose_response`, `validate_request`, `submit_run_request` and `get_artifact`) from `manifold_contracts/run-spec-1.schema.json`, which in turn references `dirsig-engine-1.schema.json`; none is copied.
4. `openapi.yaml`: the REST form of the operations (OpenAPI 3.1, `info.version: sdk-api/1`). Every request and response body is a `$ref` to a file in `schemas/`; the document defines no body inline.
5. `examples/`: one request and one response per operation, plus `compose.problem.json`, the problem a recipe that does not compose produces. They are generated from the real library; each description says what is real, what is a placeholder and what is abbreviated.

Two controlled drawings illustrate the contract: `docs/diagrams/sdk_api.png` (the layers, from the user to the engine tools) and `docs/diagrams/sdk_api_sequence.png` (submit, poll status, list and fetch artifacts).

## Contract version

`sdk-api/1` is the version of the whole folder: the operations, the schemas and the OpenAPI document change together. A change that removes or renames an operation, a field or a state, or changes the meaning of one, needs a new version.

## Out of scope

Authentication, tenancy and quotas are not part of this contract. A server that needs them adds them around the operations without changing their inputs, outputs or errors. Re-executing a run spec that has already been submitted is also not part of `sdk-api/1`: resubmission returns the existing run.

## Keeping the contract consistent

`tests/test_api_contract.py` checks the contract against itself and the code. Every schema must be valid JSON Schema with every property described; the OpenAPI document must validate (with `openapi-spec-validator`, in the `dev` extra) and must name exactly the operations of `operations.md`; every example must validate against its schema and its operation; every operation must name existing code or be marked `gap`; every requirement must be cited; and no file in this folder may cite internal records. Run it with the rest of the suite:

    pytest tests/test_api_contract.py

The examples are written by `scripts/api_examples.py` from the library files. After a library file changes, regenerate them, then check:

    python scripts/api_examples.py
    python scripts/api_examples.py --check

The drawings' Mermaid sources are `docs/diagrams/sdk_api.mmd` and `docs/diagrams/sdk_api_sequence.mmd`. After editing one, re-render it and commit the source and the rendered files together; `--check` fails if a source changed without a re-render:

    python scripts/render_diagrams.py
    python scripts/render_diagrams.py --check

Rendering needs the Mermaid CLI (`mmdc`, or `npx`); set `PUPPETEER_EXECUTABLE_PATH` to a system Chromium or Chrome if it cannot download its own.
