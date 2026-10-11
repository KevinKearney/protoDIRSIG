"""The engines this SDK can run: the registry `manifold.sim` builds and installs as `manifold.core.engine`'s default.

`registry()` is built once per process and installed with `engine.set_default_registry`, so `compose`, `validate` and
admission find the engines without being passed a registry. Adapters load on first use; one that fails to load is
listed as unavailable with the reason and does not affect the others.
"""
from manifold.core.engine import Registry, set_default_registry

_REGISTRY = None


def _dirsig():
    from manifold.sim._dirsig.adapter import DirsigAdapter      # transitional: the DIRSIG engine still lives in sim
    return DirsigAdapter()


def build_registry():
    """A new registry of the engines installed in this environment."""
    reg = Registry()
    reg.register("dirsig", _dirsig, source="manifold.sim._dirsig (transitional)")
    return reg


def registry():
    """The process's engine registry, built and installed as the default on first call."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = build_registry()
        set_default_registry(_REGISTRY)
    return _REGISTRY
