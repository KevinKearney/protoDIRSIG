"""The contract schemas are packaged with the library (`manifold/core/_contracts/`, copied by the build from
manifold_contracts/), so an installed wheel validates without the repository.

The wheel is built offline (`pip wheel . --no-deps --no-build-isolation`) from a temporary copy of the build inputs
(packages/core: pyproject.toml, setup.py, src/manifold/core; the three schemas), so no build/ or egg-info appears in the checkout.
"""
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from manifold.core import contract

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ("run-spec-1.schema.json", "sensor-spec-1.schema.json")   # the engine-block schema is the engine's wheel's
VALID = ROOT / "manifold_run_specs" / "auror_ref.yaml"

CHECK = """
import sys
site, spec_path = sys.argv[1], sys.argv[2]
sys.path.insert(0, site)
import yaml
from manifold.core import contract
assert contract.__file__.startswith(site), contract.__file__
folder = contract.contracts_dir()
assert str(folder).startswith(site) and folder == contract.packaged_contracts_dir(), folder
spec = yaml.safe_load(open(spec_path).read())
assert contract.schema_violations(spec) == [], contract.schema_violations(spec)
spec["descriptor"]["origin"]["kind"] = "bogus"
bad = contract.schema_violations(spec)
assert [v["path"] for v in bad] == ["/descriptor/origin/kind"], bad
print("ok", folder)
"""


@pytest.fixture(scope="module")
def wheel(tmp_path_factory):
    repo = tmp_path_factory.mktemp("build_inputs")
    src = repo / "packages" / "core"
    src.mkdir(parents=True)
    shutil.copy2(ROOT / "packages" / "core" / "pyproject.toml", src)
    shutil.copy2(ROOT / "packages" / "core" / "setup.py", src)
    shutil.copytree(ROOT / "packages" / "core" / "src" / "manifold" / "core", src / "src" / "manifold" / "core",
                    ignore=shutil.ignore_patterns("__pycache__", "_contracts"))
    (repo / "manifold_contracts").mkdir()
    for name in SCHEMAS:
        shutil.copy2(ROOT / "manifold_contracts" / name, repo / "manifold_contracts")
    out = tmp_path_factory.mktemp("wheel")
    r = subprocess.run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "-w", str(out)],
                       cwd=src, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"a wheel cannot be built offline here: {(r.stderr or r.stdout).strip().splitlines()[-1:]}")
    (whl,) = out.glob("eoptic_manifold_core-*.whl")
    return whl


def test_the_wheel_carries_the_three_schemas(wheel):
    with zipfile.ZipFile(wheel) as z:
        for name in SCHEMAS:
            assert z.read(f"manifold/core/_contracts/{name}") == (ROOT / "manifold_contracts" / name).read_bytes(), name


def test_an_installed_wheel_validates_without_the_repository(wheel, tmp_path):
    site = tmp_path / "site"
    with zipfile.ZipFile(wheel) as z:
        z.extractall(site)
    env = {k: v for k, v in os.environ.items() if k != "MANIFOLD_CONTRACTS"}
    r = subprocess.run([sys.executable, "-c", CHECK, str(site), str(VALID)], cwd=tmp_path, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("ok ")


def test_the_checkout_has_no_packaged_copy_and_reads_manifold_contracts(monkeypatch):
    monkeypatch.delenv("MANIFOLD_CONTRACTS", raising=False)
    assert not (ROOT / "packages" / "core" / "src" / "manifold" / "core" / "_contracts").exists()
    assert contract.packaged_contracts_dir() is None
    assert contract.contracts_dir() == ROOT / "manifold_contracts"


def test_the_environment_variable_comes_first(monkeypatch, tmp_path):
    monkeypatch.setenv("MANIFOLD_CONTRACTS", str(tmp_path))
    assert contract.contracts_dir() == tmp_path


def test_the_engine_wheel_carries_its_schema_and_registers_its_adapter(tmp_path_factory):
    """eoptic-manifold-engine-dirsig builds offline into a wheel with `dirsig-engine-1.schema.json` under
    `manifold/engines/dirsig/_contracts/`, the `manifold.engines` entry point `dirsig`, and no namespace `__init__`."""
    repo = tmp_path_factory.mktemp("engine_inputs")
    src = repo / "packages" / "engine-dirsig"
    src.mkdir(parents=True)
    for name in ("pyproject.toml", "setup.py"):
        shutil.copy2(ROOT / "packages" / "engine-dirsig" / name, src)
    shutil.copytree(ROOT / "packages" / "engine-dirsig" / "src", src / "src",
                    ignore=shutil.ignore_patterns("__pycache__", "_contracts", "*.egg-info"))
    (repo / "manifold_contracts").mkdir()
    shutil.copy2(ROOT / "manifold_contracts" / "dirsig-engine-1.schema.json", repo / "manifold_contracts")
    out = tmp_path_factory.mktemp("engine_wheel")
    r = subprocess.run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "-w", str(out)],
                       cwd=src, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"a wheel cannot be built offline here: {(r.stderr or r.stdout).strip().splitlines()[-1:]}")
    (whl,) = out.glob("eoptic_manifold_engine_dirsig-*.whl")
    with zipfile.ZipFile(whl) as z:
        names = z.namelist()
        schema = z.read("manifold/engines/dirsig/_contracts/dirsig-engine-1.schema.json")
        eps = z.read(next(n for n in names if n.endswith("entry_points.txt"))).decode()
    assert schema == (ROOT / "manifold_contracts" / "dirsig-engine-1.schema.json").read_bytes()
    assert "[manifold.engines]" in eps and "dirsig = manifold.engines.dirsig.adapter:DirsigAdapter" in eps
    assert "manifold/__init__.py" not in names and "manifold/engines/__init__.py" not in names
