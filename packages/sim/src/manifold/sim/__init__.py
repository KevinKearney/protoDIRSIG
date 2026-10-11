"""manifold.sim: running MANIFOLD run specs: the `Workspace` facade, the `Backend` protocol and `LocalBackend`, the run
store, the worker, `LibraryReader`, and engine discovery (`engines`).

Engines are separate distributions (for DIRSIG, `eoptic-manifold-engine-dirsig`, `manifold.engines.dirsig`) reached
only through the registry `engines.registry()` builds from the installed distributions' entry points. Importing the
package loads nothing heavy: each public name is imported on first use (PEP 562), and no engine package loads until a
run is submitted.
"""
from importlib.metadata import PackageNotFoundError, version

from manifold.core._names import DISTRIBUTION_SIM

try:
    __version__ = version(DISTRIBUTION_SIM)
except PackageNotFoundError:
    __version__ = "0+unknown"

_LAZY = {"Workspace": "manifold.sim.workspace", "Backend": "manifold.sim.backend",
         "LocalBackend": "manifold.sim.backend", "RunStore": "manifold.sim.store",
         "LibraryReader": "manifold.sim.library"}
__all__ = [*_LAZY, "__version__"]

from manifold.sim import engines as _engines     # noqa: E402

_engines.registry()                                # install the engine registry as manifold.core's default (no engine loads)


def __getattr__(name):
    if name in _LAZY:
        import importlib
        return getattr(importlib.import_module(_LAZY[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
