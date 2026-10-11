"""The engines this SDK can run: discovered from installed distributions and installed as `manifold.core.engine`'s
default registry.

An engine distribution registers its adapter in the entry-point group `manifold.engines`, the entry point's name being
the engine id and its object a zero-argument factory (a class or a function) returning the adapter. `build_registry()`
reads the group without importing any engine: each adapter loads on first use, and one that fails to load (its
distribution broken, a dependency missing, the factory raising) is listed as unavailable with the reason and leaves the
others unaffected. Two distributions registering one id make that id unavailable, naming both. `registry()` builds the
process's registry once and installs it as the default, so `compose`, `validate` and admission find the engines
without being passed a registry; importing `manifold.sim` calls it.
"""
from importlib.metadata import entry_points

from manifold.core.engine import Registry, set_default_registry

GROUP = "manifold.engines"
_REGISTRY = None


def _loader(ep):
    def load():
        factory = ep.load()
        return factory() if callable(factory) else factory
    return load


def _conflict(names):
    def load():
        raise RuntimeError(f"registered by more than one distribution: {', '.join(names)}")
    return load


def _source(ep):
    dist = getattr(ep, "dist", None)
    return f"{dist.name} {dist.version} ({ep.value})" if dist is not None else ep.value


def build_registry(group=GROUP):
    """A new registry of the engines registered in `group` in this environment (nothing is imported)."""
    reg = Registry()
    by_id = {}
    for ep in entry_points(group=group):
        by_id.setdefault(ep.name, []).append(ep)
    for engine_id, eps in sorted(by_id.items()):
        if len(eps) == 1:
            reg.register(engine_id, _loader(eps[0]), source=_source(eps[0]))
        else:
            reg.register(engine_id, _conflict([_source(e) for e in eps]), source="; ".join(_source(e) for e in eps))
    return reg


def registry():
    """The process's engine registry, built and installed as the default on first call."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = build_registry()
        set_default_registry(_REGISTRY)
    return _REGISTRY


def reset():
    """Forget the process's registry (tests that install or remove an engine distribution); the next `registry()`
    discovers again."""
    global _REGISTRY
    _REGISTRY = None
