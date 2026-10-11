"""The engine adapter protocol (proposed) and the engine registry: how the SDK reaches an engine without knowing it.

An engine is added by installing a distribution that registers an adapter; nothing in `manifold.core` or
`manifold.sim` names it. The adapter is a `typing.Protocol` (`EngineAdapter`); its inputs and outputs are frozen
dataclasses:

- identity: `EngineInfo` (`engine_id`, `adapter_version`, the engine-block `contracts` it reads, the `modes` it serves);
- schema: `engine_schema(engine_block)`, the JSON Schema the engine block is validated against at admission (the
  published `run-spec/1` schema leaves the engine block an open object);
- interpretation: `compose_problems(settings)` (composition-time rules on the recipe's settings), `semantic_rules(spec)`
  (admission rules the schema cannot express), `resolve(descriptor, engine_block, context)` (every reference found and
  verified; returns the engine's resolved run or raises `run_spec.RunSpecError`), `library_problems(spec, resolved)`
  (checks that need the resolved files);
- execution: `plan(context)` returns a `LaunchPlan` (argv, working folder, environment policy, interpreter, files to
  stage, expected outputs) that `manifold.sim` runs as a subprocess; `execute(context, hook)` is what that subprocess
  runs (engine side); `collect(output_dir, run_dir)` returns a `Collection` (artifacts with roles and a completeness
  verdict that does not rely on the exit status alone);
- provenance: `fingerprint(spec)`, the external dependencies recorded in the execution record (tool versions, hashed
  assets, interpreter identity);
- resources: `resources(spec)`, the typed slots the run needs (`resources.ResourceRequest`);
- optional: `availability()` (None, or why the engine's runtime cannot run here; listed by `Registry.status`) and
  `dry_run(spec, resolved, scratch_root, options)` (the engine's own dry run).

`Registry` holds adapters by engine id, loads them lazily (a loader that raises leaves the engine listed as unavailable
with the reason; the others are unaffected) and lists them deterministically. `default_registry()` is the registry
`compose`, `validate` and admission use when none is passed; it is empty until a caller installs one with
`set_default_registry` (`manifold.sim` installs the registry it discovers from installed distributions), so a process
that uses `manifold.core` alone passes a registry explicitly.

Imports: the standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

MODES = ("layered", "passthrough")                 # initial vocabulary; an adapter may serve others
ROLES = ("product", "truth", "log", "config", "metadata")   # initial artifact-role vocabulary (free, proposed)
VERDICTS = ("complete", "incomplete", "failed")


@dataclass(frozen=True)
class EngineInfo:
    """Who an adapter is and what it serves."""
    engine_id: str
    adapter_version: str
    contracts: tuple = ()                          # engine-block contracts read, e.g. "<engine>-engine/1"
    modes: tuple = ("layered",)
    description: str = ""


@dataclass(frozen=True)
class ResolveContext:
    """What resolution may read: the engine-asset library, the sensor library and the run spec's own path."""
    config_repo: Any
    sensor_library: Any = None
    run_spec_path: Any = None


@dataclass(frozen=True)
class EnvironmentPolicy:
    """How the launched process's environment is built from the worker's: `set` overrides, `unset` removes,
    `isolate_home` gives it a per-run `HOME` (`<run_dir>/home`), `thread_variables` are set to the granted thread count,
    `gpu_variable` (for example `CUDA_VISIBLE_DEVICES`) to the granted GPU ids."""
    set: Mapping[str, str] = field(default_factory=dict)
    unset: tuple = ()
    isolate_home: bool = False
    thread_variables: tuple = ()
    gpu_variable: str | None = None                # set to the granted device ids, comma-separated


@dataclass(frozen=True)
class LaunchPlan:
    """One engine process. `argv[0]` is run as given when `interpreter` is None and `python_module` is None; with
    `python_module`, the command is `<python> -m <python_module> <argv...>`, where `<python>` is the SDK's own
    interpreter (`interpreter` None), an interpreter path, or the `python` of a named conda environment. `stage` maps
    names under the run directory to files the engine needs (assets, read-only); `expected_outputs` are names under the
    output folder whose absence makes the run incomplete."""
    argv: tuple
    cwd: Any = None
    env: EnvironmentPolicy = field(default_factory=EnvironmentPolicy)
    interpreter: str | None = None
    python_module: str | None = None
    stage: Mapping[str, Any] = field(default_factory=dict)
    expected_outputs: tuple = ()


@dataclass(frozen=True)
class RunContext:
    """What execution needs: the run folder, its run spec, the libraries, the output folder and the options the
    backend passes through (for example an engine executable override)."""
    run_dir: Any
    spec: Mapping
    config_repo: Any
    sensor_library: Any = None
    output_dir: Any = None
    options: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CollectedArtifact:
    """One output the adapter reports: a path (under the run folder), its role, for a product of one capture its
    zero-based frame index, and the artifact name when it is not the file's base name."""
    path: Any
    role: str
    frame: int | None = None
    name: str | None = None


@dataclass(frozen=True)
class Collection:
    """What a finished (or stopped) engine process left: the artifacts in reporting order, the verdict, a message for
    a verdict other than complete, and members the adapter adds to the execution record."""
    artifacts: tuple
    verdict: str
    message: str | None = None
    record: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class EngineAdapter(Protocol):
    """The protocol an engine distribution implements (see the module docstring)."""

    def info(self) -> EngineInfo: ...

    def engine_schema(self, engine_block) -> Mapping | None: ...

    def compose_problems(self, settings) -> list: ...

    def semantic_rules(self, spec) -> list: ...

    def resolve(self, descriptor, engine_block, context: ResolveContext) -> Any: ...

    def library_problems(self, spec, resolved) -> list: ...

    def plan(self, context: RunContext) -> LaunchPlan: ...

    def execute(self, context: RunContext, hook=None) -> Mapping: ...

    def collect(self, output_dir, run_dir) -> Collection: ...

    def fingerprint(self, spec=None) -> Mapping: ...

    def resources(self, spec=None) -> Any: ...


@dataclass(frozen=True)
class EngineStatus:
    """One registry entry as listed: the info when the adapter loaded, else why it is unavailable."""
    engine_id: str
    available: bool
    info: EngineInfo | None = None
    reason: str | None = None
    source: str | None = None


class EngineUnavailable(LookupError):
    """An engine id that is not registered, or whose adapter failed to load."""

    def __init__(self, engine_id, reason, registered):
        super().__init__(f"engine {engine_id!r} {reason}; registered engines: "
                         f"{', '.join(registered) if registered else 'none'}")
        self.engine_id, self.reason, self.registered = engine_id, reason, tuple(registered)


class Registry:
    """Adapters by engine id. `register(engine_id, loader_or_adapter, source=...)`: a loader (a callable returning an
    adapter) is called on first use; if it raises, the engine stays listed as unavailable with the reason and every
    other engine is unaffected. Pure: no discovery here."""

    def __init__(self):
        self._entries = {}

    def register(self, engine_id, adapter_or_loader, *, source=None, replace=False):
        if not isinstance(engine_id, str) or not engine_id:
            raise ValueError("an engine id is a non-empty string")
        if engine_id in self._entries and not replace:
            raise ValueError(f"engine {engine_id!r} is already registered ({self._entries[engine_id]['source']})")
        is_factory = isinstance(adapter_or_loader, type) or (callable(adapter_or_loader)
                                                              and not isinstance(adapter_or_loader, EngineAdapter))
        loader = adapter_or_loader if is_factory else (lambda a=adapter_or_loader: a)
        self._entries[engine_id] = {"loader": loader, "adapter": None, "error": None, "loaded": False,
                                    "source": source}

    def unregister(self, engine_id):
        self._entries.pop(engine_id, None)

    def ids(self):
        """Registered engine ids, sorted (available or not)."""
        return sorted(self._entries)

    def _load(self, engine_id):
        e = self._entries[engine_id]
        if not e["loaded"]:
            e["loaded"] = True
            try:
                adapter = e["loader"]()
                info = adapter.info()
                if info.engine_id != engine_id:
                    raise ValueError(f"the adapter reports engine id {info.engine_id!r}")
                e["adapter"] = adapter
            except Exception as exc:  # noqa: BLE001 -- a broken engine must not break the registry
                e["error"] = f"{type(exc).__name__}: {exc}"
        return e

    def get(self, engine_id):
        """The adapter for `engine_id`; `EngineUnavailable` if it is not registered or failed to load."""
        if engine_id not in self._entries:
            raise EngineUnavailable(engine_id, "is not registered", self.ids())
        e = self._load(engine_id)
        if e["adapter"] is None:
            raise EngineUnavailable(engine_id, f"is unavailable ({e['error']})", self.ids())
        return e["adapter"]

    def find(self, engine_id):
        """The adapter, or None (not registered or unavailable)."""
        try:
            return self.get(engine_id)
        except EngineUnavailable:
            return None

    def status(self, engine_id):
        """The engine's `EngineStatus`: available when its adapter loaded and its optional `availability()` (the
        engine's runtime: its packages, tools) reports nothing missing; otherwise the reason. An adapter that loaded
        still serves validation (`get`, `find`) even when its runtime is unavailable."""
        e = self._load(engine_id)
        adapter = e["adapter"]
        if adapter is None:
            return EngineStatus(engine_id, False, None, e["error"], e["source"])
        reason = None
        check = getattr(adapter, "availability", None)
        if callable(check):
            try:
                reason = check()
            except Exception as exc:  # noqa: BLE001
                reason = f"{type(exc).__name__}: {exc}"
        return EngineStatus(engine_id, reason is None, adapter.info(), reason, e["source"])

    def listing(self):
        """Every registered engine's `EngineStatus`, sorted by engine id (loads each adapter once)."""
        return [self.status(i) for i in self.ids()]


_DEFAULT = Registry()


def default_registry():
    """The registry used when a caller passes none (empty until `set_default_registry`)."""
    return _DEFAULT


def set_default_registry(registry):
    """Install `registry` as the default; returns the previous one."""
    global _DEFAULT
    previous, _DEFAULT = _DEFAULT, registry
    return previous


def resolve_registry(registry=None):
    return registry if registry is not None else default_registry()


def engine_id_of(spec):
    """`descriptor.origin.engine` of a parsed run spec, or None."""
    try:
        value = spec["descriptor"]["origin"]["engine"]
    except (KeyError, TypeError):
        return None
    return value if isinstance(value, str) else None


def mode_of(spec):
    """`engine.mode` of a parsed run spec (absent means the engine's layered form), or None without an engine block."""
    eng = spec.get("engine") if isinstance(spec, dict) else None
    if not isinstance(eng, dict):
        return None
    return eng.get("mode", "layered")


Loader = Callable[[], EngineAdapter]
