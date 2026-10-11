"""protoDIRSIG: an SDK for composing, validating and running DIRSIG simulations from MANIFOLD run specs.

`Workspace` is the user-facing class (see `protodirsig.workspace`); `__version__` the installed version. Importing the
package loads nothing heavy: `Workspace` is imported on first use.
"""
from importlib.metadata import PackageNotFoundError, version

from protodirsig._names import DISTRIBUTION

try:
    __version__ = version(DISTRIBUTION)
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = ["Workspace", "__version__"]


def __getattr__(name):                          # PEP 562: `protodirsig.Workspace` imports the facade on first use
    if name == "Workspace":
        from protodirsig.workspace import Workspace
        return Workspace
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
