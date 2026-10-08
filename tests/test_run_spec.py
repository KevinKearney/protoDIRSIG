"""protodirsig.run_spec must resolve run_specs/auror_ref.yaml (engine assets against config_repo,
the sensor ref beside the run spec), carry the motion/tasks values the generator needs, and refuse
what it is not built for (FINDINGS.md, Stage 01; Stage 04 config_repo; Stage 05 generation).

Reads the run spec and config_repo READ-ONLY (tests needing config_repo skipped if absent);
writes only to pytest's tmp_path.
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from protodirsig.run_spec import (RunSpecError, check_library_files, load_run_spec, load_sensor_spec,
                                  resolve_auror_run)

PROJECT = Path(__file__).resolve().parents[1]
SPEC = PROJECT / "run_specs" / "auror_ref.yaml"
CONFIG_REPO = PROJECT / "config_repo"
FIXTURE = PROJECT / "tests" / "fixtures" / "auror_ref"     # the received motion/tasks; never resolved against
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


@needs_config_repo
def test_resolves_against_config_repo():
    spec = load_run_spec(SPEC)
    run = resolve_auror_run(spec, SPEC, CONFIG_REPO)
    assert run.name == "auror-ref-static-pose" and run.origin == {"kind": "synthetic", "engine": "dirsig"}
    # Engine assets come from config_repo's library layout; motion/tasks are values to generate from.
    assert run.scene == CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene"
    assert run.platform == CONFIG_REPO / "platforms" / "AurorNIRDetector" / "AurorNIRDetector.platform"
    assert run.atmosphere_db == CONFIG_REPO / "atmosphere" / "AurorNewAtmosphere"
    assert run.weather == CONFIG_REPO / "weather" / "saw.wth"
    assert run.motion_position == [-400.0, 400.0, 550000.0]
    assert run.motion_orientation == {"order": "xyz", "units": "radians", "angles": [0.0, 0.0, 3.141592654]}
    assert run.tasks_windows == [(0.0, 0.0)]
    assert run.epoch == datetime(2009, 7, 27, 19, 29, 32, tzinfo=timezone.utc)
    assert run.epoch.utcoffset().total_seconds() == 0
    assert (run.seed, run.ephemeris, run.split_channels, run.integration_samples) == (42, "spice", False, 10)
    assert run.output_prefix == "auror_nir_"
    assert check_library_files(spec, run) == []
    # The sensor ref resolves beside the run spec (run_specs/sensors/), not in config_repo.
    assert run.sensor["meta"]["name"] == "auror-nir"
    assert run.sensor["sensor"]["sensor_system"]["system_id"] == "auror.nir-staring-01"


@needs_config_repo
def test_plugins_match_received_jsim(tmp_path):
    run = resolve_auror_run(load_run_spec(SPEC), SPEC, CONFIG_REPO)
    assert run.ephemeris_plugin().get_plugin_name() == "SpiceEphemeris"
    db = tmp_path / "AurorNewAtmosphere"
    db.write_bytes(b"")
    inputs = run.atmosphere_plugin(db).get_plugin_inputs({"root": tmp_path})
    assert inputs["hdf_filename"] == "AurorNewAtmosphere"
    t5 = inputs["backend"]["tape5_parameters"]
    assert (inputs["backend"]["modtran_profile"], t5["atmospheric_model"], t5["multiple_scattering"]["type"],
            t5["boundary_aerosol_model"]["type"]) == ("New Profile", "MidLatitudeSummer", "Isaac", "RuralVis23Km")


@needs_config_repo
def test_mismatch_is_reported():
    spec = load_run_spec(SPEC)
    spec["engine"]["platform"]["integration_samples"] = 4
    bad = check_library_files(spec, resolve_auror_run(spec, SPEC, CONFIG_REPO))
    assert len(bad) == 1 and bad[0].startswith("integration_samples")


@needs_config_repo
@pytest.mark.parametrize("path, value, match", [
    (("motion", "kind"), "waypoints", "FlexMotion"),
    (("motion", "kind"), "orbit", "FlexMotion"),
    (("motion", "orientation", "kind"), "lookat", "FlexMotion"),
    (("motion", "position", "frame"), "ecef", "scene-frame"),
    (("motion", "orientation", "euler", "frame"), "ecef", "sceneenu"),
])
def test_rejects_motion_it_cannot_generate(path, value, match):
    """Schema-valid values (ENGINE_ENUMS for the kinds) that dirfm PlatformPosition cannot write."""
    spec = load_run_spec(SPEC)
    d = spec["engine"]
    for k in path[:-1]:
        d = d[k]
    d[path[-1]] = value
    with pytest.raises(RunSpecError, match=match):
        resolve_auror_run(spec, SPEC, CONFIG_REPO)


@needs_config_repo
def test_rejects_naive_epoch():
    spec = load_run_spec(SPEC)
    spec["descriptor"]["collection"]["epoch"] = "2009-07-27T19:29:32"     # no offset
    with pytest.raises(RunSpecError, match="no UTC offset"):
        resolve_auror_run(spec, SPEC, CONFIG_REPO)


@needs_config_repo
@pytest.mark.parametrize("plugin", ["four_curve", "basic", None])
def test_rejects_other_atmosphere_plugins(plugin):
    spec = load_run_spec(SPEC)
    spec["engine"]["atmosphere"]["plugin"] = plugin
    with pytest.raises(RunSpecError, match="new_atmosphere"):
        resolve_auror_run(spec, SPEC, CONFIG_REPO)


def test_missing_scene_is_specific(tmp_path):
    with pytest.raises(RunSpecError, match="scenes/tahoe/tahoe.scene"):
        resolve_auror_run(load_run_spec(SPEC), SPEC, tmp_path)


@needs_config_repo
def test_no_flat_scene_fallback():
    """The Stage 01-03 nested-then-flat guess is gone: a ref resolves under config_repo exactly."""
    spec = load_run_spec(SPEC)
    spec["engine"]["scenes"][0]["ref"]["name"] = "scenes/tahoe"          # the old ref value: a directory here,
    with pytest.raises(RunSpecError, match="scenes/tahoe"):              # which the removed nested guess would
        resolve_auror_run(spec, SPEC, CONFIG_REPO)                        # have completed to scenes/tahoe/tahoe.scene
    spec["engine"]["scenes"][0]["ref"]["name"] = "tahoe.scene"            # flat at the library root
    with pytest.raises(RunSpecError, match="tahoe.scene"):
        resolve_auror_run(spec, SPEC, CONFIG_REPO)
    with pytest.raises(RunSpecError, match="scenes/tahoe/tahoe.scene"):   # the received-tree fixture is not a library
        resolve_auror_run(load_run_spec(SPEC), SPEC, FIXTURE)


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


@needs_config_repo
def test_missing_sensor_ref_is_specific(tmp_path):
    spec = load_run_spec(SPEC)
    with pytest.raises(RunSpecError, match="not found beside the run spec"):
        resolve_auror_run(spec, tmp_path / "run.yaml", CONFIG_REPO)              # no sensors/ beside this path
    spec["descriptor"]["sensor"] = {"sensor_system": {}}                     # the old inline shape
    with pytest.raises(RunSpecError, match="sensor-spec/1 ref"):
        resolve_auror_run(spec, SPEC, CONFIG_REPO)
