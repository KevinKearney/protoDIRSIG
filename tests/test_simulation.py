"""protodirsig.simulation's three conformance checks must pass on the real AUROR_ref run spec and
report a broken spec as a failed check, not an exception (FINDINGS.md, 2026-10-08 — Stage 02).

Reads run_specs/auror_ref.yaml, config_repo and AUROR_ref READ-ONLY; the execution check runs a
DIRSIG dry run (no render, about a second) and writes only to pytest's tmp_path. Skipped without
AUROR_ref, config_repo, or dirsig5/scene2hdf on PATH.
"""
import os
import shutil
from pathlib import Path

import pytest
import yaml

from protodirsig.scene_ref import fingerprint
from protodirsig.simulation import Simulation, schema_errors

PROJECT = Path(__file__).resolve().parents[1]
SPEC = PROJECT / "run_specs" / "auror_ref.yaml"
AUROR = PROJECT / "AUROR_ref"
CONFIG_REPO = PROJECT / "config_repo"
DIRSIG_HOME = Path(os.environ.get("DIRSIG_HOME", Path.home() / "DIRSIG" / "dirsig-2026.38.0.a020954-Linux-x86_64"))


def _dirsig_on_path():
    os.environ.setdefault("DIRSIG_HOME", str(DIRSIG_HOME))
    if (DIRSIG_HOME / "bin").is_dir() and str(DIRSIG_HOME / "bin") not in os.environ["PATH"].split(os.pathsep):
        os.environ["PATH"] = f"{DIRSIG_HOME / 'bin'}{os.pathsep}{os.environ['PATH']}"
    return shutil.which("dirsig5") and shutil.which("scene2hdf")


needs_dirsig = pytest.mark.skipif(
    not ((AUROR / "motion").is_dir() and (CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene").is_file()
         and _dirsig_on_path()),
    reason="AUROR_ref, config_repo or DIRSIG not present")


def broken_spec(tmp_path, edit):
    """A copy of the real run spec with `edit` applied, written to tmp_path beside a symlink to
    run_specs/sensors/, since the sensor ref resolves against the run spec's own directory."""
    spec = yaml.safe_load(SPEC.read_text())
    edit(spec)
    path = tmp_path / "broken.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    if not (tmp_path / "sensors").exists():
        (tmp_path / "sensors").symlink_to(SPEC.parent / "sensors", target_is_directory=True)
    return path


@needs_dirsig
def test_real_spec_passes_all_three(tmp_path):
    before = fingerprint(AUROR), fingerprint(CONFIG_REPO)
    c = Simulation.from_run_spec(SPEC, AUROR, CONFIG_REPO, tmp_path).validate()
    assert (fingerprint(AUROR), fingerprint(CONFIG_REPO)) == before
    assert (c.schema_ok, c.resolution_ok, c.execution_ok) == (True, True, True), c
    assert c.passed and c.schema_error is None and c.resolution_mismatches == [] and c.execution_error is None
    caps = c.execution_log["capture_list"]
    assert len(caps) == 1 and caps[0]["task_index"] == 0
    assert not any((tmp_path / "validate" / "output").glob("*.img"))      # a dry run renders nothing


@needs_dirsig
def test_missing_scene_fails_resolution_only(tmp_path):
    path = broken_spec(tmp_path, lambda s: s["engine"]["scenes"][0]["ref"].update(name="scenes/no_such_scene"))
    c = Simulation.from_run_spec(path, AUROR, CONFIG_REPO, tmp_path / "work").validate()
    assert c.schema_ok and not c.resolution_ok and not c.passed
    assert "no_such_scene" in c.resolution_mismatches[0]
    assert not c.execution_ok and c.execution_error.startswith("not attempted")


@needs_dirsig
def test_bad_enum_fails_schema(tmp_path):
    path = broken_spec(tmp_path, lambda s: s["engine"]["motion"].update(kind="teleport"))
    c = Simulation.from_run_spec(path, AUROR, CONFIG_REPO, tmp_path / "work").validate()
    assert not c.schema_ok and "engine.motion.kind" in c.schema_error
    assert not c.resolution_ok                        # check_received_files: spec kind != the static .ppd
    assert c.execution_ok                             # the job itself (from the received files) is still fine


@needs_dirsig
def test_corrupt_atmosphere_fails_execution(tmp_path):
    lib = tmp_path / "config_repo"                   # symlinks into config_repo, except a corrupt database
    lib.mkdir()
    for p in CONFIG_REPO.iterdir():
        if p.name != "atmosphere":
            (lib / p.name).symlink_to(p)
    (lib / "atmosphere").mkdir()
    (lib / "atmosphere" / "AurorNewAtmosphere").write_bytes(b"not an hdf5 file")
    c = Simulation.from_run_spec(SPEC, AUROR, lib, tmp_path / "work").validate()
    assert c.schema_ok and c.resolution_ok and not c.execution_ok
    assert "NewAtmosphere" in c.execution_error


def test_unparseable_spec_is_a_result(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("spec_version: [unclosed\n")
    c = Simulation.from_run_spec(path, AUROR, CONFIG_REPO, tmp_path / "work").validate()
    assert not (c.schema_ok or c.resolution_ok or c.execution_ok) and "did not load" in c.schema_error


def test_schema_errors_collects_all():
    spec = yaml.safe_load(SPEC.read_text())
    assert schema_errors(spec) == []
    spec["engine"]["atmosphere"]["plugin"] = "four_curve"           # adopted value: schema-valid
    assert schema_errors(spec) == []
    spec["engine"]["ephemeris"]["plugin"] = "jpl"
    spec["engine"]["run"]["seed"] = "42"
    del spec["descriptor"]["fidelity"]
    errs = schema_errors(spec)
    assert len(errs) == 3 and any("ephemeris" in e for e in errs) and any("seed" in e for e in errs)


def test_sensor_ref_schema():
    spec = yaml.safe_load(SPEC.read_text())
    del spec["descriptor"]["sensor"]["ref"]["name"]
    errs = schema_errors(spec)
    assert len(errs) == 1 and "descriptor.sensor.ref.name" in errs[0]
    spec["descriptor"]["sensor"] = {"sensor_system": {"system_id": "x"}}   # the old inline shape
    assert any("descriptor.sensor.ref.name" in e for e in schema_errors(spec))


@needs_dirsig
def test_missing_sensor_file_fails_resolution_only(tmp_path):
    path = broken_spec(tmp_path, lambda s: s["descriptor"]["sensor"]["ref"].update(name="sensors/no_such_sensor.yaml"))
    c = Simulation.from_run_spec(path, AUROR, CONFIG_REPO, tmp_path / "work").validate()
    assert c.schema_ok and not c.resolution_ok
    assert "no_such_sensor.yaml" in c.resolution_mismatches[0]
