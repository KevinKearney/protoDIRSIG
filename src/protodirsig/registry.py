"""`LocalRegistry`: a local stand-in for MANIFOLD's submission endpoint, which does not exist yet.

Stage 02 (eopticDocs `review/PLAN_2026-10-08_conformance-template-roadmap.md`, Phase 4). A
notebook calls `LocalRegistry().submit(...)` instead of `Simulation.validate()` directly, so the
real submission path, when it exists, replaces this one call. `SubmissionResult` is
deliberately not `ConformanceResult`: MANIFOLD's admission response is not defined, and only the
verdict, the reasons and the per-check outcomes are likely to carry over.
"""
from dataclasses import dataclass, field

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
    def submit(self, run_spec_path, tree_root, config_repo, work_dir=None):
        sim = Simulation.from_run_spec(run_spec_path, tree_root, config_repo, work_dir)
        c = sim.validate()
        reasons = []
        if not c.schema_ok:
            reasons.append(f"Schema check failed: the run spec is not valid run-spec/1 / dirsig-engine/1. "
                           f"{c.schema_error}")
        if not c.resolution_ok:
            reasons.append("Resolution check failed: the run spec's references do not resolve, or do not "
                           "match the received files. " + "; ".join(c.resolution_mismatches))
        if not c.execution_ok:
            reasons.append(f"Execution check failed: DIRSIG did not accept the assembled job in a dry run. "
                           f"{c.execution_error}")
        return SubmissionResult(verdict="accepted" if c.passed else "rejected", reasons=reasons,
                                checks={"schema": c.schema_ok, "resolution": c.resolution_ok,
                                        "execution": c.execution_ok},
                                simulation=sim)
