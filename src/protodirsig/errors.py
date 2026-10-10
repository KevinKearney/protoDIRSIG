"""The SDK's one exception family, and the problem details (RFC 9457) each exception carries.

Every SDK error is a `ProblemError`: `except ProblemError` catches all of them. `.problem` is a dict that conforms to
`api/schemas/problem.schema.json`: the one given at construction, or one built on demand from the class (its `type`,
`title` and `status`), the message (`detail`) and the `layer` and `field` when known. The family:

    ProblemError                      admission, 422 (the base)
        AdmissionError                admission, 422: a submission or validation that failed
        NotFoundError                 not-found, 404: an unknown run, sweep, artifact or library resource
        InvalidRequestError           invalid-request, 422: a request the SDK cannot act on as given
        run_spec.RunSpecError         admission, 422 (also a ValueError): the loader refuses a spec or a reference
            compose.ComposeError      compose, 422: a recipe that does not compose (`layer`, `field`)

`RunSpecError` subclasses `ProblemError` and `ValueError`, so `except ValueError` and `except RunSpecError` keep working.
Every exception pickles with its members (the worker and a future server move them across processes).

This module also holds the plain problem constructors (`make_problem`, `admission`, `not_found`, `invalid_request`,
`execution_failed`, `from_compose_error`) and the problem type URNs, because `run_spec` imports this module and
`problems` imports `run_spec`: the constructors live here, `problems` re-exports them and adds the ones that locate a
pointer in a composed spec. Imports: the standard library only.
"""

COMPOSE = "urn:protodirsig:problem:compose"
ADMISSION = "urn:protodirsig:problem:admission"
NOT_FOUND = "urn:protodirsig:problem:not-found"
INVALID_REQUEST = "urn:protodirsig:problem:invalid-request"
EXECUTION = "urn:protodirsig:problem:execution"
TITLES = {COMPOSE: "The recipe does not compose", ADMISSION: "The submission failed admission",
          NOT_FOUND: "Not found", INVALID_REQUEST: "The request is not valid",
          EXECUTION: "The run failed while executing"}
NO_LAYER = (NOT_FOUND, EXECUTION)                   # kinds of problem no authored file causes


def make_problem(type_, status, detail, instance=None, layer=None, field=None, errors=None):
    """A problem details dict: `type`, its `title`, `status`, `detail`; `instance` and `errors` when given; `layer`
    and `field` (possibly null) unless the type is one no authored file causes (not-found, execution)."""
    out = {"type": type_, "title": TITLES[type_], "status": status, "detail": detail}
    if instance is not None:
        out["instance"] = instance
    if type_ not in NO_LAYER:
        out["layer"], out["field"] = layer, field
    if errors is not None:
        out["errors"] = errors
    return out


def admission(detail, instance=None, layer=None, field=None):
    """A plain admission problem (422) for a failed check with no richer constructor."""
    return make_problem(ADMISSION, 422, detail, instance, layer, field)


def execution_failed(run_id, name, message, instance=None):
    """The problem for an accepted run that failed while executing (the engine, the worker or the host): status 500,
    no authored file."""
    return make_problem(EXECUTION, 500, f"Run {name} ({run_id}) failed while executing: {message}", instance)


def invalid_request(detail, instance=None, layer=None, field=None):
    """The problem for a request the SDK cannot act on as given (for example a sweep recipe sent to `submit_run`)."""
    return make_problem(INVALID_REQUEST, 422, detail, instance, layer, field)


def not_found(kind, identifier, instance=None):
    """The problem for an unknown id or name: `kind` is what was looked up (`run`, `sweep`, `recipe`, ...)."""
    return make_problem(NOT_FOUND, 404, f"No {kind} {identifier!r}.", instance)


def from_compose_error(exc, instance=None):
    """The problem for a `compose.ComposeError`: the layer file and field it names, its message as `detail`."""
    return make_problem(COMPOSE, 422, str(exc), instance, getattr(exc, "layer", None), getattr(exc, "field", None))


def _restore(cls, args, state):
    obj = cls.__new__(cls, *args)
    obj.args = args
    obj.__dict__.update(state)
    return obj


class ProblemError(Exception):
    """An SDK error with its problem details.

    Construct with a message and optional members, `ProblemError(message, layer=..., field=..., instance=...)`, or
    with a ready problem dict, `ProblemError(problem)` or `ProblemError(message, problem=problem)`. `.problem` is the
    given dict, or one built from the class (`TYPE`, `STATUS`), the message and the members. `.status` and `.type`
    read it."""
    TYPE, STATUS = ADMISSION, 422

    def __init__(self, message=None, *, problem=None, layer=None, field=None, instance=None):
        if isinstance(message, dict) and problem is None:
            message, problem = None, message
        if problem is not None and (not isinstance(problem, dict) or not {"type", "title", "status"} <= problem.keys()):
            raise TypeError(f"a problem details dict with type, title and status is required, got {problem!r:.120}")
        if message is None:
            message = (problem or {}).get("detail") or (problem or {}).get("title") or TITLES[self.TYPE]
        super().__init__(message)
        self._problem = problem
        self._members = {"layer": layer, "field": field, "instance": instance}

    @property
    def problem(self):
        if self._problem is not None:
            return self._problem
        return make_problem(self.TYPE, self.STATUS, str(self), self._members.get("instance"),
                            self._members.get("layer"), self._members.get("field"))

    @property
    def status(self):
        return self.problem["status"]

    @property
    def type(self):
        return self.problem["type"]

    def __reduce__(self):
        return _restore, (self.__class__, self.args, self.__dict__)


class AdmissionError(ProblemError):
    """A submission, validation or composition that failed (422). Usually built from a problem:
    `problems.from_validation`, `from_schema_violations`, `from_resolution_error` or `from_compose_error`."""


class NotFoundError(ProblemError):
    """An unknown id or name (404). `NotFoundError("run", run_id)`, or from a ready problem."""
    TYPE, STATUS = NOT_FOUND, 404

    def __init__(self, kind_or_problem, identifier=None, instance=None, *, problem=None):
        if isinstance(kind_or_problem, dict) or problem is not None:
            super().__init__(problem=problem if problem is not None else kind_or_problem)
        else:
            super().__init__(problem=not_found(kind_or_problem, identifier, instance))


class InvalidRequestError(ProblemError):
    """A request the SDK cannot act on as given (422, invalid-request). `InvalidRequestError(detail)`, or from a ready
    problem (a compose problem for a recipe that does not compose)."""
    TYPE, STATUS = INVALID_REQUEST, 422

    def __init__(self, detail_or_problem=None, instance=None, layer=None, field=None, *, problem=None):
        if isinstance(detail_or_problem, dict) or problem is not None:
            super().__init__(problem=problem if problem is not None else detail_or_problem)
        else:
            super().__init__(detail_or_problem, layer=layer, field=field, instance=instance)
