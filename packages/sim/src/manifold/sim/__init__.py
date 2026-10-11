"""manifold.sim: running MANIFOLD run specs: the `Workspace` facade, the `Backend` protocol and `LocalBackend`, the run
store, the worker, `LibraryReader`, the orbit propagation, and the deprecated `LocalRegistry`.

`manifold.sim._dirsig` holds the DIRSIG-bound modules; it is private and transitional (a separate engine distribution
behind an engine adapter protocol replaces it). Importing the package loads nothing heavy: each public name is imported
on first use (PEP 562), and no engine package loads until a run is submitted.
"""
from importlib.metadata import PackageNotFoundError, version

from manifold.core._names import DISTRIBUTION_SIM

try:
    __version__ = version(DISTRIBUTION_SIM)
except PackageNotFoundError:
    __version__ = "0+unknown"

_LAZY = {"Workspace": "manifold.sim.workspace", "Backend": "manifold.sim.backend",
         "LocalBackend": "manifold.sim.backend", "RunStore": "manifold.sim.store",
         "LibraryReader": "manifold.sim.library", "LocalRegistry": "manifold.sim._dirsig.registry"}
__all__ = [*_LAZY, "__version__"]


def __getattr__(name):
    if name in _LAZY:
        import importlib
        return getattr(importlib.import_module(_LAZY[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
