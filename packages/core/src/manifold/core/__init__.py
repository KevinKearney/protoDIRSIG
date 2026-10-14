"""manifold.core: the engine-neutral MANIFOLD run-spec layer: composition (`compose`), loading and resolution
(`run_spec`), the contract schemas (`contract`), run and sweep identity (`identity`, `dirhash`), admission, problem
details and errors, and the generated API models.

No engine package and none of numpy, skyfield or sgp4 loads when a module of this package is imported.
"""
from importlib.metadata import PackageNotFoundError, version

from manifold.core._names import DISTRIBUTION_CORE

try:
    __version__ = version(DISTRIBUTION_CORE)
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = ["__version__"]
