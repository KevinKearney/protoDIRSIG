"""Build hook: copy the contract schemas into the package as `protodirsig/_contracts/` at build time.

`manifold_contracts/` stays the one tracked copy of each schema; the packaged copies are build products, written into
the build directory only (never into `src/`), so a checkout always validates against `manifold_contracts/` and an
installed wheel against its own copy (`protodirsig.contract.contracts_dir`). An editable install keeps reading the
repository folder. Everything else is configured in pyproject.toml.
"""
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

ROOT = Path(__file__).resolve().parent
SCHEMAS = ("run-spec-1.schema.json", "dirsig-engine-1.schema.json", "sensor-spec-1.schema.json")


class build_py_with_contracts(build_py):
    def run(self):
        super().run()
        if getattr(self, "editable_mode", False):
            return                                       # an editable install reads manifold_contracts/ in place
        target = Path(self.build_lib) / "protodirsig" / "_contracts"
        self.mkpath(str(target))
        for name in SCHEMAS:
            self.copy_file(str(ROOT / "manifold_contracts" / name), str(target / name))

    def get_outputs(self, include_bytecode=True):
        outputs = super().get_outputs(include_bytecode)
        if getattr(self, "editable_mode", False):
            return outputs
        return outputs + [str(Path(self.build_lib) / "protodirsig" / "_contracts" / n) for n in SCHEMAS]


setup(cmdclass={"build_py": build_py_with_contracts})
