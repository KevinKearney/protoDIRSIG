"""`LocalRegistry`: a local stand-in for MANIFOLD's submission endpoint, which does not exist yet.

Stage 02. A
notebook calls `LocalRegistry().submit(...)` instead of `Simulation.validate()` directly, so the
real submission path, when it exists, replaces this one call. `SubmissionResult` is
deliberately not `ConformanceResult`: MANIFOLD's admission response is not defined, and only the
verdict, the reasons and the per-check outcomes are likely to carry over.

`submit_recipe` composes a layered recipe (`protodirsig.compose`) and submits the result: the layered submission
a MANIFOLD input constructor would accept (CONOPS and Guide, C-21).
"""
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from protodirsig.compose import ComposeError, compose, default_sensor_library, dump
from protodirsig.simulation import Simulation


@dataclass
class SubmissionResult:
    verdict: str                                   # "accepted" or "rejected"
    reasons: list[str]                             # plain-language, one per failed check
    checks: dict[str, bool] = field(default_factory=dict)   # {"schema": ..., "resolution": ..., "execution": ...}
    simulation: Simulation | None = None           # the validated job; call .run() on it if accepted

    @property
    def accepted(self):
        return self.verdict == "accepted"


class LocalRegistry:
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
                                simulation=sim)
