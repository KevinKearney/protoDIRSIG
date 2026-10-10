"""Exceptions that carry a problem details object (RFC 9457), the SDK's one error model for Python callers.

`ProblemError.problem` is a dict that conforms to `api/schemas/problem.schema.json`; the exception's message is its
`detail` (else its `title`). The subclasses fix the kind: `AdmissionError` (status 422: a submission or validation
that failed, or a recipe that does not compose), `NotFoundError` (404: an unknown run, sweep or artifact) and
`InvalidRequestError` (422, `urn:protodirsig:problem:invalid-request`: a request the SDK cannot act on as given). The
REST form serves the same dict as `application/problem+json`.

`LocalBackend` raises these. `compose.ComposeError` and `run_spec.RunSpecError` remain what the composer and the loader
raise; `problems.from_compose_error` and `problems.from_resolution_error` turn them into problems.

Imports: the standard library and `protodirsig.problems` only; no engine package.
"""
from protodirsig import problems


class ProblemError(Exception):
    """An error with its problem details: `.problem` (a dict), `.status`, `.type`."""

    def __init__(self, problem):
        if not isinstance(problem, dict) or not {"type", "title", "status"} <= problem.keys():
            raise TypeError(f"a problem details dict with type, title and status is required, got {problem!r:.120}")
        self.problem = problem
        super().__init__(problem.get("detail") or problem["title"])

    @property
    def status(self):
        return self.problem["status"]

    @property
    def type(self):
        return self.problem["type"]


class AdmissionError(ProblemError):
    """A submission, validation or composition that failed (422). Built from a problem: `problems.from_submission`,
    `from_schema_violations`, `from_resolution_error` or `from_compose_error`."""


class NotFoundError(ProblemError):
    """An unknown id or name (404). `NotFoundError("run", run_id)`, or from a ready problem."""

    def __init__(self, kind_or_problem, identifier=None, instance=None):
        if isinstance(kind_or_problem, dict):
            super().__init__(kind_or_problem)
        else:
            super().__init__(problems.not_found(kind_or_problem, identifier, instance))


class InvalidRequestError(ProblemError):
    """A request the SDK cannot act on as given (422, invalid-request). `InvalidRequestError(detail)`, or from a ready
    problem (a compose problem for a recipe that does not compose)."""

    def __init__(self, detail_or_problem, instance=None, layer=None, field=None):
        if isinstance(detail_or_problem, dict):
            super().__init__(detail_or_problem)
        else:
            super().__init__(problems.invalid_request(detail_or_problem, instance, layer, field))
