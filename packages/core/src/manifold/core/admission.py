"""Engine-free validation: the `none` level of `validate`, the checks admission runs before a run exists.

`validate_spec(spec, ..., registry=None)` runs, on a parsed run spec, the schema check (`contract.schema_errors`: the
published schemas, the engine block against its adapter's schema, and the semantic rules), resolution (the adapter
registered for `descriptor.origin.engine` resolves the engine block: every reference found in its library and its
stamped hash verified), the adapter's library-file check (for DIRSIG, the platform template renders from the
sensor-spec and `settings`, the orbit files load) and the unstamped listing (`run_spec.unstamped_refs`), and computes
the run id (`identity.run_id`). It returns a `ValidationReport` and never raises for a bad spec. An engine id no
registered adapter serves fails resolution and the schema check names the registered engines. No engine process runs
(`engine_checked` is always False here); the backend's `dry_run` level adds that.

Imports: the standard library and pure `manifold.core` modules (`contract`, `engine`, `identity`, `run_spec`); no engine
package (tests/test_import_boundary.py runs it with dirfm, skyfield and sgp4 blocked).
"""
from dataclasses import dataclass, field
from pathlib import Path

from manifold.core import identity
from manifold.core.contract import schema_errors
from manifold.core.engine import ResolveContext, engine_id_of, resolve_registry
from manifold.core.run_spec import RunSpecError, unstamped_refs

REPOSITORY = Path(__file__).resolve().parents[5]   # packages/<dist>/src/manifold/<pkg>/


@dataclass
class ValidationReport:
    """The outcome of the engine-free checks for one run spec. `valid` is schema and resolution (including the library
    files); an unstamped member is listed, not a failure (submission refuses it). `run` is the resolved run object
    (the adapter's resolved run, for DIRSIG a `ResolvedRun`) when resolution succeeded, else None, and `resolve_exception` the exception when it did
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


def validate_spec(spec, run_spec_path=None, config_repo=None, sensor_library=None, *, resolved=None, registry=None):
    """The engine-free checks of one parsed run spec; never raises for a bad spec.

    `config_repo` defaults to the repository's `manifold_config_repo/`; `sensor_library` to the sibling of the run
    spec's folder (`run_spec.default_sensor_library`), or the repository's `manifold_sensors/` without a path.
    `resolved`, a `(run, exception)` pair the caller already computed with `resolve_run` for the same spec and
    libraries, is used instead of resolving again (`Simulation` resolves at construction). `registry` is the engine
    registry (default `engine.default_registry()`)."""
    registry = resolve_registry(registry)
    config_repo = Path(config_repo) if config_repo is not None else REPOSITORY / "manifold_config_repo"
    if sensor_library is None and run_spec_path is None:
        sensor_library = REPOSITORY / "manifold_sensors"
    path = Path(run_spec_path) if run_spec_path is not None else REPOSITORY / "manifold_run_specs" / "spec.yaml"
    try:
        schema = schema_errors(spec, registry)
    except Exception as e:  # noqa: BLE001 -- a spec too malformed to walk is a schema failure, not a crash
        schema = [f"/: the spec could not be checked: {type(e).__name__}: {e}"]
    engine_id = engine_id_of(spec)
    adapter = registry.find(engine_id) if engine_id is not None else None
    if resolved is not None:
        run, exc = resolved
    elif adapter is None:
        run, exc = None, RunSpecError(f"no registered engine adapter serves descriptor.origin.engine {engine_id!r} "
                                      f"(registered: {', '.join(registry.ids()) or 'none'})",
                                      pointer="/descriptor/origin/engine")
    else:
        run = exc = None
        try:
            run = adapter.resolve(spec["descriptor"], spec.get("engine"),
                                  ResolveContext(config_repo, sensor_library, path))
        except (RunSpecError, KeyError, TypeError, AttributeError) as e:
            exc = e
    if run is None:
        mismatches = [f"references did not resolve: {type(exc).__name__}: {exc}"]
    else:
        try:
            mismatches = list(adapter.library_problems(spec, run)) if adapter is not None else []
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
