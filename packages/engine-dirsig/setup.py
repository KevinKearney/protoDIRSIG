"""Build hook: copy the DIRSIG engine-block schema into the package as `manifold/engines/dirsig/_contracts/`.

`manifold_contracts/` stays the one tracked copy; the packaged copy is a build product written into the build directory
only, so a checkout or an editable install reads `manifold_contracts/` and an installed wheel its own copy
(`manifold.engines.dirsig.adapter.schema_path`). Everything else is configured in pyproject.toml.
"""
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

ROOT = Path(__file__).resolve().parent
CONTRACTS = ROOT.parents[1] / "manifold_contracts"     # packages/engine-dirsig/ -> the repository's canonical folder
SCHEMAS = ("dirsig-engine-1.schema.json",)


class build_py_with_contracts(build_py):
    def run(self):
        super().run()
        if getattr(self, "editable_mode", False):
            return
        target = Path(self.build_lib) / "manifold" / "engines" / "dirsig" / "_contracts"
        self.mkpath(str(target))
        for name in SCHEMAS:
            self.copy_file(str(CONTRACTS / name), str(target / name))

    def get_outputs(self, include_bytecode=True):
        outputs = super().get_outputs(include_bytecode)
        if getattr(self, "editable_mode", False):
            return outputs
        return outputs + [str(Path(self.build_lib) / "manifold" / "engines" / "dirsig" / "_contracts" / n) for n in SCHEMAS]


setup(cmdclass={"build_py": build_py_with_contracts})
