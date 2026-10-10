"""The contract schemas are packaged with the library (`protodirsig/_contracts/`, copied by the build from
manifold_contracts/), so an installed wheel validates without the repository.

The wheel is built offline (`pip wheel . --no-deps --no-build-isolation`) from a temporary copy of the build inputs
(pyproject.toml, setup.py, src/protodirsig, the three schemas), so no build/ or egg-info appears in the checkout.
"""
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from protodirsig import contract

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ("run-spec-1.schema.json", "dirsig-engine-1.schema.json", "sensor-spec-1.schema.json")
VALID = ROOT / "manifold_run_specs" / "auror_ref.yaml"

CHECK = """
import sys
site, spec_path = sys.argv[1], sys.argv[2]
sys.path.insert(0, site)
import yaml
from protodirsig import contract
assert contract.__file__.startswith(site), contract.__file__
folder = contract.contracts_dir()
assert str(folder).startswith(site) and folder == contract.packaged_contracts_dir(), folder
spec = yaml.safe_load(open(spec_path).read())
assert contract.schema_violations(spec) == [], contract.schema_violations(spec)
spec["engine"]["motion"]["kind"] = "bogus"
bad = contract.schema_violations(spec)
assert [v["path"] for v in bad] == ["/engine/motion/kind"], bad
print("ok", folder)
"""


@pytest.fixture(scope="module")
def wheel(tmp_path_factory):
    src = tmp_path_factory.mktemp("build_inputs")
    shutil.copy2(ROOT / "pyproject.toml", src)
    shutil.copy2(ROOT / "setup.py", src)
    shutil.copytree(ROOT / "src" / "protodirsig", src / "src" / "protodirsig",
                    ignore=shutil.ignore_patterns("__pycache__", "_contracts"))
    (src / "manifold_contracts").mkdir()
    for name in SCHEMAS:
        shutil.copy2(ROOT / "manifold_contracts" / name, src / "manifold_contracts")
    out = tmp_path_factory.mktemp("wheel")
    r = subprocess.run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "-w", str(out)],
                       cwd=src, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"a wheel cannot be built offline here: {(r.stderr or r.stdout).strip().splitlines()[-1:]}")
    (whl,) = out.glob("protodirsig-*.whl")
    return whl


def test_the_wheel_carries_the_three_schemas(wheel):
    with zipfile.ZipFile(wheel) as z:
        for name in SCHEMAS:
            assert z.read(f"protodirsig/_contracts/{name}") == (ROOT / "manifold_contracts" / name).read_bytes(), name


def test_an_installed_wheel_validates_without_the_repository(wheel, tmp_path):
    site = tmp_path / "site"
    with zipfile.ZipFile(wheel) as z:
        z.extractall(site)
    env = {k: v for k, v in os.environ.items() if k != "PROTODIRSIG_CONTRACTS"}
    r = subprocess.run([sys.executable, "-c", CHECK, str(site), str(VALID)], cwd=tmp_path, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("ok ")


def test_the_checkout_has_no_packaged_copy_and_reads_manifold_contracts(monkeypatch):
    monkeypatch.delenv("PROTODIRSIG_CONTRACTS", raising=False)
    assert not (ROOT / "src" / "protodirsig" / "_contracts").exists()
    assert contract.packaged_contracts_dir() is None
    assert contract.contracts_dir() == ROOT / "manifold_contracts"


def test_the_environment_variable_comes_first(monkeypatch, tmp_path):
    monkeypatch.setenv("PROTODIRSIG_CONTRACTS", str(tmp_path))
    assert contract.contracts_dir() == tmp_path
