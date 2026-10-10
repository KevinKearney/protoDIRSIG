"""`LocalRegistry`: a local stand-in for MANIFOLD's submission endpoint, which does not exist yet.

Stage 02. A
notebook calls `LocalRegistry().submit(...)` instead of `Simulation.validate()` directly, so the
real submission path, when it exists, replaces this one call. `SubmissionResult` is
deliberately not `ConformanceResult`: MANIFOLD's admission response is not defined, and only the
verdict, the reasons and the per-check outcomes are likely to carry over.

`submit_recipe` composes a layered recipe (`protodirsig.compose`) and submits the result: the layered submission
a MANIFOLD input constructor would accept (CONOPS and Guide, C-21). `submit_sweep` does the same for every run of a
sweep recipe and `run_sweep` renders the accepted ones. Each run has its own state; a rejected or failed run never
stops the others.
"""
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from protodirsig import identity
from protodirsig.compose import MAX_RUNS, ComposeError, compose, compose_sweep, default_sensor_library, dump, sweep_id  # noqa: F401
from protodirsig.run_spec import RunSpecError
from protodirsig.run_spec import default_sensor_library as run_spec_default_library
from protodirsig.simulation import Simulation


@dataclass
class SubmissionResult:
    verdict: str                                   # "accepted" or "rejected"
    reasons: list[str]                             # plain-language, one per failed check
    checks: dict[str, bool] = field(default_factory=dict)   # {"schema": ..., "resolution": ..., "execution": ...}
    simulation: Simulation | None = None           # the validated job; call .run() on it if accepted
    run_id: str | None = None                      # identity.run_id of the submitted spec; None if it cannot be computed

    @property
    def accepted(self):
        return self.verdict == "accepted"


@dataclass
class RunStatus:
    """One run of a sweep. `state`: `accepted` or `rejected` after `submit_sweep`; `rendered` or `failed` after
    `run_sweep` for a run that was accepted."""
    name: str
    state: str
    errors: list[str] = field(default_factory=list)
    spec_path: Path | None = None                  # the composed run spec written into the sweep's work directory
    submission: SubmissionResult | None = None
    result: object | None = None                   # simulation.RunResult once rendered
    run_id: str | None = None                      # the run's id (identity.run_id), 64 hex digits


@dataclass
class SweepResult:
    sweep_id: str                                  # identity.sweep_id_from_runs; "" when the recipe did not compose
    recipe: Path
    runs: dict[str, RunStatus] = field(default_factory=dict)   # by run name, in sensor-list order
    errors: list[str] = field(default_factory=list)           # recipe-level: the recipe did not compose

    @property
    def states(self):
        return {name: r.state for name, r in self.runs.items()}


class LocalRegistry:
    def submit_sweep(self, recipe_path, config_repo, work_dir=None, max_runs=MAX_RUNS):
        """Compose every run of the recipe and `submit` each. The specs and each run's work directory go under
        `work_dir` (default: a fresh temporary directory). A recipe that does not compose gives no runs and one
        recipe-level error; otherwise each run is `accepted` or `rejected` with its reasons, independently."""
        recipe_path = Path(recipe_path).resolve()
        library = default_sensor_library(recipe_path)
        result = SweepResult("", recipe_path)
        try:
            sweep = compose_sweep(recipe_path, sensor_library=library, max_runs=max_runs)
        except ComposeError as e:
            result.errors.append(f"Composition failed: {e}")
            return result
        result.sweep_id = sweep.sweep_id
        work_dir = Path(work_dir) if work_dir is not None else Path(tempfile.mkdtemp(prefix="protodirsig_sweep_"))
        work_dir.mkdir(parents=True, exist_ok=True)
        for name, spec in sweep.runs.items():
            path = work_dir / f"{sweep.files[name]}.yaml"
            path.write_text(dump(spec, sweep.recipe))
            try:
                sub = self.submit(path, config_repo, work_dir / sweep.files[name], library)
            except Exception as e:  # noqa: BLE001 -- one run's failure must not stop the others
                result.runs[name] = RunStatus(name, "rejected", [f"{type(e).__name__}: {e}"], path,
                                              run_id=sweep.run_ids[name])
                continue
            result.runs[name] = RunStatus(name, sub.verdict, list(sub.reasons), path, sub, run_id=sweep.run_ids[name])
        return result

    def run_sweep(self, sweep, config_repo=None, work_dir=None):
        """Render every accepted run of `sweep` (a `SweepResult`, or a recipe path, which is submitted first with
        `config_repo` and `work_dir`). Each accepted run becomes `rendered` (with its `RunResult`) or `failed` (with
        the error text); rejected runs stay as they are. Returns the same `SweepResult`."""
        if not isinstance(sweep, SweepResult):
            sweep = self.submit_sweep(sweep, config_repo, work_dir)
        for run in sweep.runs.values():
            if run.state != "accepted":
                continue
            try:
                run.result = run.submission.simulation.run()
                run.state = "rendered"
            except Exception as e:  # noqa: BLE001 -- one run's failure must not stop the others
                run.state, run.errors = "failed", [f"{type(e).__name__}: {e}"]
        return sweep


    def submit_recipe(self, recipe_path, config_repo, work_dir=None):
        """Compose the recipe, write the run spec into `work_dir` and `submit` it against the recipe's sensor
        library. A recipe that does not compose is rejected with `checks["compose"]` False."""
        recipe_path = Path(recipe_path).resolve()
        library = default_sensor_library(recipe_path)
        try:
            spec = compose(recipe_path, sensor_library=library)
        except ComposeError as e:
            return SubmissionResult(verdict="rejected", reasons=[f"Composition failed: {e}"],
                                    checks={"compose": False, "schema": False, "resolution": False, "execution": False})
        work_dir = Path(work_dir) if work_dir is not None else Path(tempfile.mkdtemp(prefix="protodirsig_"))
        work_dir.mkdir(parents=True, exist_ok=True)
        path = work_dir / f"{recipe_path.stem}.yaml"
        path.write_text(dump(spec, recipe_path.relative_to(recipe_path.parent.parent).as_posix()))
        result = self.submit(path, config_repo, work_dir, library)
        result.checks = {"compose": True, **result.checks}
        return result

    def submit(self, run_spec_path, config_repo, work_dir=None, sensor_library=None):
        sim = Simulation.from_run_spec(run_spec_path, config_repo, work_dir, sensor_library)
        c = sim.validate()
        reasons = []
        if not c.schema_ok:
            reasons.append(f"Schema check failed: the run spec is not valid run-spec/1 / dirsig-engine/1. "
                           f"{c.schema_error}")
        if not c.resolution_ok:
            reasons.append("Resolution check failed: the run spec's references do not resolve, or do not "
                           "match the library files. " + "; ".join(c.resolution_mismatches))
        if not c.execution_ok:
            reasons.append(f"Execution check failed: DIRSIG did not accept the assembled job in a dry run. "
                           f"{c.execution_error}")
        return SubmissionResult(verdict="accepted" if c.passed else "rejected", reasons=reasons,
                                checks={"schema": c.schema_ok, "resolution": c.resolution_ok,
                                        "execution": c.execution_ok},
                                simulation=sim, run_id=_run_id(sim, run_spec_path))


def _run_id(sim, run_spec_path):
    """The submitted spec's run id, or None when its sensor cannot be materialized (the reasons say why)."""
    if sim.spec is None:
        return None
    library = sim.sensor_library if sim.sensor_library is not None else run_spec_default_library(run_spec_path)
    try:
        return identity.run_id(sim.spec, library)
    except (RunSpecError, TypeError, ValueError):
        return None
