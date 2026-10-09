"""Stamped `content_hash` values: current in the repo, verified by the loaders, restamped by the script."""
import importlib.util
import shutil
from pathlib import Path

import pytest

from protodirsig.run_spec import RunSpecError, load_run_spec, resolve_auror_run
from protodirsig.spectral import SpectralError, read_curve, resolve_curve

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "run_specs" / "auror_ref.yaml"
spec = importlib.util.spec_from_file_location("stamp_hashes", ROOT / "scripts" / "stamp_hashes.py")
stamp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stamp)


def test_repo_hashes_are_current():
    assert stamp.main(["--check"]) == 0, "run scripts/stamp_hashes.py"


def test_edited_sensor_spec_fails_resolution(tmp_path):
    lib = tmp_path / "sensors"
    shutil.copytree(ROOT / "sensors", lib)
    (lib / "auror-nir.yaml").write_text((lib / "auror-nir.yaml").read_text() + "\n# edited\n")
    run = load_run_spec(SPEC)
    with pytest.raises(RunSpecError, match="stamp_hashes"):
        resolve_auror_run(run, SPEC, ROOT / "config_repo", lib)


def test_placeholder_hash_is_not_verified(tmp_path):
    lib = tmp_path / "sensors"
    shutil.copytree(ROOT / "sensors", lib)
    (lib / "auror-nir.yaml").write_text((lib / "auror-nir.yaml").read_text() + "\n# edited\n")
    run = load_run_spec(SPEC)
    run["descriptor"]["sensor"]["ref"]["content_hash"] = "sha256:<hash>"
    assert resolve_auror_run(run, SPEC, ROOT / "config_repo", lib).sensor["meta"]["name"] == "auror-nir"


def test_edited_curve_fails(tmp_path):
    lib = tmp_path / "sensors"
    shutil.copytree(ROOT / "sensors", lib)
    path = lib / "spectral" / "qe" / "synthetic_visgaas.csv"
    path.write_text(path.read_text().replace("0.900,0.800000", "0.900,0.700000"))
    ref = {"name": "spectral/qe/synthetic_visgaas.csv", "content_hash": stamp.digest(ROOT / "sensors/spectral/qe/synthetic_visgaas.csv")}
    with pytest.raises(SpectralError, match="content_hash"):
        resolve_curve(lib, ref)
    assert read_curve(path).value.max() == pytest.approx(0.8, abs=0.11)      # the file itself still parses
