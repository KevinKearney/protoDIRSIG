"""Deprecated: the `protodirsig` import paths, kept so code written before the rename keeps working. Use
`manifold.core` and `manifold.sim`.

`MODULES` is the one table: each former submodule and the module that replaced it. A meta path finder makes
`import protodirsig.<name>` return the replacing module itself (the same module object, so its names, the AUROR-era
aliases among them, and any monkeypatching are shared), and `__getattr__` serves `protodirsig.<name>` and the former
package-level names. Importing this package emits one `DeprecationWarning` naming the replacement; the submodule
aliases do not warn again. Removal: one release after MANIFOLD adopts the manifold packages.
"""
import importlib
import importlib.abc
import importlib.util
import sys
import warnings

REPLACEMENT = "manifold.core and manifold.sim"

MODULES = {                                     # former protodirsig submodule -> its replacement
    "admission": "protodirsig._split.admission",                # names split between core and the DIRSIG engine
    "compose": "protodirsig._split.compose",                # names split between core and the DIRSIG engine
    "contract": "protodirsig._split.contract",                # names split between core and the DIRSIG engine
    "dirhash": "manifold.core.dirhash",
    "errors": "manifold.core.errors",
    "identity": "manifold.core.identity",
    "models": "manifold.core.models",
    "platform_gen": "manifold.core.platform_gen",
    "problems": "manifold.core.problems",
    "run_spec": "manifold.core.run_spec",
    "spectral": "manifold.core.spectral",
    "backend": "manifold.sim.backend",
    "library": "manifold.sim.library",
    "orbit": "manifold.sim.orbit",
    "store": "manifold.sim.store",
    "worker": "manifold.sim.worker",
    "workspace": "manifold.sim.workspace",
    "atmosphere_patches": "manifold.sim._dirsig.atmosphere_patches",
    "motion_tasks": "manifold.sim._dirsig.motion_tasks",
    "passthrough": "manifold.sim._dirsig.passthrough",
    "platform_ref": "manifold.sim._dirsig.platform_ref",
    "registry": "manifold.sim._dirsig.registry",
    "scene_coverage": "manifold.sim._dirsig.scene_coverage",
    "scene_ref": "manifold.sim._dirsig.scene_ref",
    "sensors": "manifold.sim._dirsig.sensors",
    "simulation": "manifold.sim._dirsig.simulation",
}
NAMES = {                                       # former package-level names -> the module that holds them
    "Workspace": "manifold.sim.workspace",
    "LocalRegistry": "manifold.sim._dirsig.registry",
}

warnings.warn(f"the protodirsig package is deprecated; import from {REPLACEMENT} instead", DeprecationWarning,
              stacklevel=2)


class _Aliases(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """`protodirsig.<name>` is the module `MODULES[name]` itself, not a copy."""

    def find_spec(self, fullname, path=None, target=None):
        prefix, _, name = fullname.partition(".")
        if prefix == __name__ and name in MODULES:
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        module = importlib.import_module(MODULES[spec.name.partition(".")[2]])
        self._specs = getattr(self, "_specs", {})
        self._specs[spec.name] = module.__spec__          # the import system overwrites __spec__; restored below
        return module

    def exec_module(self, module):
        module.__spec__ = self._specs.pop(module.__spec__.name)


if not any(isinstance(f, _Aliases) for f in sys.meta_path):
    sys.meta_path.insert(0, _Aliases())


def __getattr__(name):                          # PEP 562
    if name in MODULES:
        return importlib.import_module(f"{__name__}.{name}")
    if name in NAMES:
        return getattr(importlib.import_module(NAMES[name]), name)
    if name == "__version__":
        return importlib.import_module("manifold.sim").__version__
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["Workspace", "LocalRegistry", "__version__"]
