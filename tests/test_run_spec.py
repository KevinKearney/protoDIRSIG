"""protodirsig.run_spec must resolve run_specs/auror_ref.yaml, engine assets against config_repo and
motion/tasks against the received AUROR_ref tree, to the files the stage-01 notebook used to
hardcode, and refuse what it is not built for (FINDINGS.md, Stage 01; Stage 04 for config_repo).

Reads the run spec, config_repo and AUROR_ref READ-ONLY (tests needing them skipped if absent);
writes only to pytest's tmp_path.
"""
from pathlib import Path

import pytest
import yaml

from protodirsig.run_spec import (RunSpecError, check_received_files, load_run_spec, load_sensor_spec,
                                  resolve_auror_run)

PROJECT = Path(__file__).resolve().parents[1]
SPEC = PROJECT / "run_specs" / "auror_ref.yaml"
AUROR = PROJECT / "AUROR_ref"
CONFIG_REPO = PROJECT / "config_repo"
needs_tree = pytest.mark.skipif(not ((AUROR / "motion").is_dir() and (AUROR / "tasks").is_dir()),
                                reason="AUROR_ref not present")
needs_config_repo = pytest.mark.skipif(not (CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene").is_file(),
                                       reason="config_repo not present")


def test_spec_values():
    spec = load_run_spec(SPEC)
    assert spec["descriptor"]["sensor"]["ref"]["name"] == "sensors/auror-nir.yaml"
    eng = spec["engine"]
    assert eng["run"]["seed"] == 42
    assert eng["scenes"][0]["ref"]["name"] == "scenes/tahoe/tahoe.scene"
    assert eng["platform"]["ref"]["name"] == "platforms/AurorNIRDetector/AurorNIRDetector.platform"
    assert eng["atmosphere"]["plugin"] == "new_atmosphere"
    assert eng["atmosphere"]["database"]["ref"]["name"] == "atmosphere/AurorNewAtmosphere"
    assert eng["weather"]["file"]["name"] == "weather/saw.wth"


@needs_tree
@needs_config_repo
def test_resolves_against_tree():
    spec = load_run_spec(SPEC)
    run = resolve_auror_run(spec, AUROR, SPEC, CONFIG_REPO)
    assert run.name == "auror-ref-static-pose" and run.origin == {"kind": "synthetic", "engine": "dirsig"}
    # Engine assets come from config_repo's library layout; motion/tasks from the received tree.
    assert run.scene == CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene"
    assert run.platform == CONFIG_REPO / "platforms" / "AurorNIRDetector" / "AurorNIRDetector.platform"
    assert run.atmosphere_db == CONFIG_REPO / "atmosphere" / "AurorNewAtmosphere"
    assert run.weather == CONFIG_REPO / "weather" / "saw.wth"
    assert run.motion == AUROR / "motion" / "AurorMotion.ppd"
    assert run.tasks == AUROR / "tasks" / "AurorTask.tasks"
    assert (run.seed, run.ephemeris, run.split_channels, run.integration_samples) == (42, "spice", False, 10)
    assert run.output_prefix == "auror_nir_"
    assert check_received_files(spec, run) == []
    # The sensor ref resolves beside the run spec (run_specs/sensors/), not under the tree.
    assert run.sensor["meta"]["name"] == "auror-nir"
    assert run.sensor["sensor"]["sensor_system"]["system_id"] == "auror.nir-staring-01"


@needs_tree
@needs_config_repo
def test_plugins_match_received_jsim(tmp_path):
    run = resolve_auror_run(load_run_spec(SPEC), AUROR, SPEC, CONFIG_REPO)
    assert run.ephemeris_plugin().get_plugin_name() == "SpiceEphemeris"
    db = tmp_path / "AurorNewAtmosphere"
    db.write_bytes(b"")
    inputs = run.atmosphere_plugin(db).get_plugin_inputs({"root": tmp_path})
    assert inputs["hdf_filename"] == "AurorNewAtmosphere"
    t5 = inputs["backend"]["tape5_parameters"]
    assert (inputs["backend"]["modtran_profile"], t5["atmospheric_model"], t5["multiple_scattering"]["type"],
            t5["boundary_aerosol_model"]["type"]) == ("New Profile", "MidLatitudeSummer", "Isaac", "RuralVis23Km")


@needs_tree
@needs_config_repo
def test_mismatch_is_reported():
    spec = load_run_spec(SPEC)
    spec["engine"]["motion"]["position"]["xyz"] = [0.0, 0.0, 550000.0]
    spec["engine"]["platform"]["integration_samples"] = 4
    bad = check_received_files(spec, resolve_auror_run(spec, AUROR, SPEC, CONFIG_REPO))
    assert len(bad) == 2 and bad[0].startswith("motion.position") and bad[1].startswith("integration_samples")


@needs_tree
@needs_config_repo
@pytest.mark.parametrize("plugin", ["four_curve", "basic", None])
def test_rejects_other_atmosphere_plugins(plugin):
    spec = load_run_spec(SPEC)
    spec["engine"]["atmosphere"]["plugin"] = plugin
    with pytest.raises(RunSpecError, match="new_atmosphere"):
        resolve_auror_run(spec, AUROR, SPEC, CONFIG_REPO)


def test_missing_scene_is_specific(tmp_path):
    with pytest.raises(RunSpecError, match="scenes/tahoe/tahoe.scene"):
        resolve_auror_run(load_run_spec(SPEC), tmp_path, SPEC, tmp_path)


@needs_tree
@needs_config_repo
def test_no_flat_scene_fallback():
    """The Stage 01-03 nested-then-flat guess is gone: a ref resolves under config_repo exactly."""
    spec = load_run_spec(SPEC)
    spec["engine"]["scenes"][0]["ref"]["name"] = "scenes/tahoe"          # the old ref value
    with pytest.raises(RunSpecError, match="scenes/tahoe"):
        resolve_auror_run(spec, AUROR, SPEC, AUROR)                       # would once find AUROR_ref/tahoe.scene
    spec["engine"]["scenes"][0]["ref"]["name"] = "tahoe.scene"            # flat at the library root
    with pytest.raises(RunSpecError, match="tahoe.scene"):
        resolve_auror_run(spec, AUROR, SPEC, CONFIG_REPO)
    with pytest.raises(RunSpecError, match="scenes/tahoe/tahoe.scene"):   # the received tree is not a library
        resolve_auror_run(load_run_spec(SPEC), AUROR, SPEC, AUROR)


def test_rejects_non_run_spec(tmp_path):
    p = tmp_path / "x.yaml"
    p.write_text(yaml.safe_dump({"spec_version": "run-spec/2"}))
    with pytest.raises(RunSpecError, match="run-spec/1"):
        load_run_spec(p)


def test_load_sensor_spec():
    doc = load_sensor_spec(SPEC, "sensors/auror-nir.yaml")
    assert doc["spec_version"] == "sensor-spec/1" and set(doc) == {"spec_version", "meta", "sensor"}
    entry = doc["sensor"]["entries"][0]
    assert entry["entry_id"] == "auror-nir" and entry["focal_planes"][0]["array"]["SensorWidth"] == 500


@pytest.mark.parametrize("text, match", [
    ("spec_version: run-spec/1\nsensor: {}\n", "sensor-spec/1"),       # wrong document kind
    ("spec_version: sensor-spec/1\nmeta: {name: x}\n", "no `sensor`"),  # right kind, no sensor block
    ("spec_version: [unclosed\n", "does not parse"),
])
def test_load_sensor_spec_rejects(tmp_path, text, match):
    (tmp_path / "sensors").mkdir()
    (tmp_path / "sensors" / "bad.yaml").write_text(text)
    with pytest.raises(RunSpecError, match=match):
        load_sensor_spec(tmp_path / "run.yaml", "sensors/bad.yaml")


@needs_tree
@needs_config_repo
def test_missing_sensor_ref_is_specific(tmp_path):
    spec = load_run_spec(SPEC)
    with pytest.raises(RunSpecError, match="not found beside the run spec"):
        resolve_auror_run(spec, AUROR, tmp_path / "run.yaml", CONFIG_REPO)              # no sensors/ beside this path
    spec["descriptor"]["sensor"] = {"sensor_system": {}}                     # the old inline shape
    with pytest.raises(RunSpecError, match="sensor-spec/1 ref"):
        resolve_auror_run(spec, AUROR, SPEC, CONFIG_REPO)
