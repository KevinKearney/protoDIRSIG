"""Engine-free validation: the `none` level of `validate`, the checks admission runs before a run exists.

`validate_spec(spec, ...)` runs, on a parsed run spec, the schema check (`contract.schema_errors`: the published
schemas plus the semantic rules), resolution (`run_spec.resolve_run`: every reference found in its library and
its stamped hash verified), the library-file comparison (`run_spec.check_library_files`: the platform template renders
from the sensor-spec and `settings`, the orbit files load) and the unstamped listing (`run_spec.unstamped_refs`), and
computes the run id (`identity.run_id`). It returns a `ValidationReport` and never raises for a bad spec. No DIRSIG
dry run is performed (`engine_checked` is always False here); `Simulation.validate("dry_run")` adds it, and implements
its own schema, resolution and unstamped parts through this function, so the two cannot diverge.

Imports: the standard library and pure `protodirsig` modules (`contract`, `identity`, `run_spec`, and, inside
`check_library_files`, `platform_gen`, `spectral`, `orbit`); nothing from `dirfm`, skyfield, sgp4, `simulation` or
`registry` (tests/test_import_boundary.py runs it with those imports blocked).
"""
from dataclasses import dataclass, field
from pathlib import Path

from protodirsig import identity
from protodirsig.contract import schema_errors
from protodirsig.run_spec import RunSpecError, check_library_files, resolve_run, unstamped_refs

REPOSITORY = Path(__file__).resolve().parents[2]


@dataclass
class ValidationReport:
    """The outcome of the engine-free checks for one run spec. `valid` is schema and resolution (including the library
    files); an unstamped member is listed, not a failure (submission refuses it). `run` is the resolved run object
    (`run_spec.ResolvedRun`) when resolution succeeded, else None, and `resolve_exception` the exception when it did
    not (`RunSpecError.pointer` names the member)."""
    schema_errors: list
    resolution_mismatches: list
    unstamped: list
    run_id: str | None
    run: object = None
    resolve_exception: Exception | None = None
    engine_checked: bool = False
    spec: dict | None = field(default=None, repr=False)

    @property
    def schema_ok(self):
        return not self.schema_errors

    @property
    def resolution_ok(self):
        return not self.resolution_mismatches

    @property
    def valid(self):
        return self.schema_ok and self.resolution_ok


def validate_spec(spec, run_spec_path=None, config_repo=None, sensor_library=None, *, resolved=None):
    """The engine-free checks of one parsed run spec; never raises for a bad spec.

    `config_repo` defaults to the repository's `manifold_config_repo/`; `sensor_library` to the sibling of the run
    spec's folder (`run_spec.default_sensor_library`), or the repository's `manifold_sensors/` without a path.
    `resolved`, a `(run, exception)` pair the caller already computed with `resolve_run` for the same spec and
    libraries, is used instead of resolving again (`Simulation` resolves at construction)."""
    config_repo = Path(config_repo) if config_repo is not None else REPOSITORY / "manifold_config_repo"
    if sensor_library is None and run_spec_path is None:
        sensor_library = REPOSITORY / "manifold_sensors"
    path = Path(run_spec_path) if run_spec_path is not None else REPOSITORY / "manifold_run_specs" / "spec.yaml"
    try:
        schema = schema_errors(spec)
    except Exception as e:  # noqa: BLE001 -- a spec too malformed to walk is a schema failure, not a crash
        schema = [f"/: the spec could not be checked: {type(e).__name__}: {e}"]
    if resolved is not None:
        run, exc = resolved
    else:
        run = exc = None
        try:
            run = resolve_run(spec, path, config_repo, sensor_library)
        except (RunSpecError, KeyError, TypeError, AttributeError) as e:
            exc = e
    if run is None:
        mismatches = [f"references did not resolve: {type(exc).__name__}: {exc}"]
    else:
        try:
            mismatches = check_library_files(spec, run)
        except Exception as e:  # noqa: BLE001
            mismatches = [f"library files could not be compared: {type(e).__name__}: {e}"]
    library = Path(sensor_library) if sensor_library is not None else path.resolve().parent.parent / "manifold_sensors"
    try:
        run_id = identity.run_id(spec, library)
    except (RunSpecError, TypeError, ValueError, KeyError, AttributeError, OSError):
        run_id = None
    try:
        unstamped = unstamped_refs(spec)
    except Exception:  # noqa: BLE001
        unstamped = []
    return ValidationReport(schema_errors=schema, resolution_mismatches=mismatches, unstamped=unstamped, run_id=run_id,
                            run=run, resolve_exception=exc, spec=spec)
