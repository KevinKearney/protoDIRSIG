"""protodirsig.run_spec must resolve run_specs/auror_ref.yaml against the received AUROR_ref tree
to the files the stage-01 notebook used to hardcode, and refuse what it is not built for
(FINDINGS.md, 2026-10-07 — Stage 01).

Reads the run spec and AUROR_ref READ-ONLY (tree tests skipped if it is absent); writes only to
pytest's tmp_path.
"""
from pathlib import Path

import pytest
import yaml

from protodirsig.run_spec import (RunSpecError, check_received_files, load_run_spec, load_sensor_spec,
                                  resolve_auror_run)

PROJECT = Path(__file__).resolve().parents[1]
SPEC = PROJECT / "run_specs" / "auror_ref.yaml"
AUROR = PROJECT / "AUROR_ref"
needs_tree = pytest.mark.skipif(not (AUROR / "tahoe.scene").is_file(), reason="AUROR_ref not present")


def test_spec_values():
    spec = load_run_spec(SPEC)
    assert spec["descriptor"]["sensor"]["ref"]["name"] == "sensors/auror-nir.yaml"
    eng = spec["engine"]
    assert eng["run"]["seed"] == 42
    assert eng["platform"]["ref"]["name"] == "platforms/AurorNIRDetector.platform"
    assert eng["atmosphere"]["plugin"] == "new_atmosphere"
    assert eng["atmosphere"]["database"]["ref"]["name"] == "jsims/AurorNewAtmosphere"


@needs_tree
def test_resolves_against_tree():
    spec = load_run_spec(SPEC)
    run = resolve_auror_run(spec, AUROR, SPEC)
    assert run.name == "auror-ref-static-pose" and run.origin == {"kind": "synthetic", "engine": "dirsig"}
    # `scenes/tahoe` resolves to the tree-root scene, not a literal scenes/tahoe/ path.
    assert run.scene == AUROR / "tahoe.scene" and run.scene.parent == AUROR
    assert run.platform == AUROR / "platforms" / "AurorNIRDetector.platform"
    assert run.motion == AUROR / "motion" / "AurorMotion.ppd"
    assert run.tasks == AUROR / "tasks" / "AurorTask.tasks"
    assert run.atmosphere_db == AUROR / "jsims" / "AurorNewAtmosphere"
    assert run.weather == AUROR / "weather" / "saw.wth"
    assert (run.seed, run.ephemeris, run.split_channels, run.integration_samples) == (42, "spice", False, 10)
    assert run.output_prefix == "auror_nir_"
    assert check_received_files(spec, run) == []
    # The sensor ref resolves beside the run spec (run_specs/sensors/), not under the tree.
    assert run.sensor["meta"]["name"] == "auror-nir"
    assert run.sensor["sensor"]["sensor_system"]["system_id"] == "auror.nir-staring-01"


@needs_tree
def test_plugins_match_received_jsim(tmp_path):
    run = resolve_auror_run(load_run_spec(SPEC), AUROR, SPEC)
    assert run.ephemeris_plugin().get_plugin_name() == "SpiceEphemeris"
    db = tmp_path / "AurorNewAtmosphere"
    db.write_bytes(b"")
    inputs = run.atmosphere_plugin(db).get_plugin_inputs({"root": tmp_path})
    assert inputs["hdf_filename"] == "AurorNewAtmosphere"
    t5 = inputs["backend"]["tape5_parameters"]
    assert (inputs["backend"]["modtran_profile"], t5["atmospheric_model"], t5["multiple_scattering"]["type"],
            t5["boundary_aerosol_model"]["type"]) == ("New Profile", "MidLatitudeSummer", "Isaac", "RuralVis23Km")


@needs_tree
def test_mismatch_is_reported():
    spec = load_run_spec(SPEC)
    spec["engine"]["motion"]["position"]["xyz"] = [0.0, 0.0, 550000.0]
    spec["engine"]["platform"]["integration_samples"] = 4
    bad = check_received_files(spec, resolve_auror_run(spec, AUROR, SPEC))
    assert len(bad) == 2 and bad[0].startswith("motion.position") and bad[1].startswith("integration_samples")


@needs_tree
@pytest.mark.parametrize("plugin", ["four_curve", "basic", None])
def test_rejects_other_atmosphere_plugins(plugin):
    spec = load_run_spec(SPEC)
    spec["engine"]["atmosphere"]["plugin"] = plugin
    with pytest.raises(RunSpecError, match="new_atmosphere"):
        resolve_auror_run(spec, AUROR, SPEC)


def test_missing_scene_is_specific(tmp_path):
    with pytest.raises(RunSpecError, match="scenes/tahoe"):
        resolve_auror_run(load_run_spec(SPEC), tmp_path, SPEC)


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
def test_missing_sensor_ref_is_specific(tmp_path):
    spec = load_run_spec(SPEC)
    with pytest.raises(RunSpecError, match="not found beside the run spec"):
        resolve_auror_run(spec, AUROR, tmp_path / "run.yaml")              # no sensors/ beside this path
    spec["descriptor"]["sensor"] = {"sensor_system": {}}                     # the old inline shape
    with pytest.raises(RunSpecError, match="sensor-spec/1 ref"):
        resolve_auror_run(spec, AUROR, SPEC)
