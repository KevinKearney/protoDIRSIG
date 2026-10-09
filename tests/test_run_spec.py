"""protodirsig.run_spec must resolve manifold_run_specs/auror_ref.yaml (engine assets against manifold_config_repo,
the sensor ref in the sensor library), carry the motion/tasks values the generator needs, and refuse
what it is not built for.

Reads the run spec and manifold_config_repo READ-ONLY (tests needing manifold_config_repo skipped if absent);
writes only to pytest's tmp_path.
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from protodirsig.run_spec import (RunSpecError, _check_settings_roi, derive_run_spec, check_library_files, load_run_spec, load_sensor_spec,
                                  resolve_auror_run)

PROJECT = Path(__file__).resolve().parents[1]
SPEC = PROJECT / "manifold_run_specs" / "auror_ref.yaml"
CONFIG_REPO = PROJECT / "manifold_config_repo"
FIXTURE = PROJECT / "tests" / "fixtures" / "auror_ref"     # the received motion/tasks; never resolved against
needs_config_repo = pytest.mark.skipif(not (CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene").is_file(),
                                       reason="manifold_config_repo not present")


def test_spec_values():
    spec = load_run_spec(SPEC)
    assert spec["descriptor"]["sensor"]["ref"]["name"] == "auror-nir.yaml"
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
    # Engine assets come from manifold_config_repo's library layout; motion/tasks are values to generate from.
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
    # The sensor ref resolves in the sensor library (manifold_sensors/), not in manifold_config_repo.
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
def test_library_files_render_cleanly():
    spec = load_run_spec(SPEC)
    assert check_library_files(spec, resolve_auror_run(spec, SPEC, CONFIG_REPO)) == []


@needs_config_repo
def test_unrenderable_sensor_is_reported(tmp_path):
    import shutil
    lib = tmp_path / "manifold_sensors"
    shutil.copytree(SPEC.parent.parent / "manifold_sensors", lib)
    shutil.rmtree(lib / "spectral")                                  # the QE curve the DeepScan entry references
    spec = derive_run_spec(load_run_spec(SPEC), "deepscan_850_306_nir_1280.yaml", "deepscan-850-306-nir-1280")
    bad = check_library_files(spec, resolve_auror_run(spec, SPEC, CONFIG_REPO, lib))
    assert len(bad) == 1 and "could not be rendered" in bad[0] and "not found" in bad[0]


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


def _drop(d, key):
    del d[key]


def _ref(path, name):
    def edit(eng):
        d = eng
        for k in path:
            d = d[k]
        d["name"] = name
    return edit


@needs_config_repo
@pytest.mark.parametrize("edit, match", [
    # ephemeris is optional and has one schema value ('spice'); this loader requires it present.
    (lambda e: e["ephemeris"].update(plugin="jpl"), "only 'spice'"),
    (lambda e: _drop(e, "ephemeris"), "only 'spice'"),
    # scenes is "list, at least 1" in the schema; this loader handles exactly one.
    (lambda e: e.update(scenes=[]), "expected one engine.scenes entry, got 0"),
    (lambda e: e.update(scenes=e["scenes"] * 2), "expected one engine.scenes entry, got 2"),
    # weather is optional and may be 'install'; this loader needs a library file.
    (lambda e: e["weather"].update(source="install"), "must be a library file"),
    (lambda e: _drop(e, "weather"), "must be a library file"),
    # one spectral state per channel: the NewAtmosphere database has none (tests/test_sensor_render.py)
    (lambda e: e["platform"].update(split_channels=True), "split_channels true is not handled"),
    # each library ref that is not the scene must also resolve to a file in manifold_config_repo
    (_ref(("platform", "ref"), "platforms/nope/nope.platform"), "platform 'platforms/nope/nope.platform' not found"),
    (_ref(("atmosphere", "database", "ref"), "atmosphere/nope"), "atmosphere database 'atmosphere/nope' not found"),
    (_ref(("weather", "file"), "weather/nope.wth"), "weather file 'weather/nope.wth' not found"),
], ids=["ephemeris-jpl", "ephemeris-absent", "scenes-0", "scenes-2", "weather-install", "weather-absent",
        "split-channels", "platform-missing", "atmosphere-db-missing", "weather-file-missing"])
def test_rejects_engine_values_it_does_not_handle(edit, match):
    """The remaining RunSpecError branches of resolve_auror_run."""
    spec = load_run_spec(SPEC)
    edit(spec["engine"])
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
    """The Stage 01-03 nested-then-flat guess is gone: a ref resolves under manifold_config_repo exactly."""
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
    doc = load_sensor_spec(SPEC.parent.parent / "manifold_sensors", "auror-nir.yaml")
    assert doc["spec_version"] == "sensor-spec/1" and set(doc) == {"spec_version", "meta", "sensor"}
    entry = doc["sensor"]["entries"][0]
    assert entry["entry_id"] == "auror-nir" and "roi" not in entry["focal_planes"][0]


@pytest.mark.parametrize("text, match", [
    ("spec_version: run-spec/1\nsensor: {}\n", "sensor-spec/1"),       # wrong document kind
    ("spec_version: sensor-spec/1\nmeta: {name: x}\n", "no `sensor`"),  # right kind, no sensor block
    ("spec_version: [unclosed\n", "does not parse"),
])
def test_load_sensor_spec_rejects(tmp_path, text, match):
    (tmp_path / "bad.yaml").write_text(text)
    with pytest.raises(RunSpecError, match=match):
        load_sensor_spec(tmp_path, "bad.yaml")


@needs_config_repo
def test_missing_sensor_ref_is_specific(tmp_path):
    spec = load_run_spec(SPEC)
    with pytest.raises(RunSpecError, match="not found in the sensor library"):
        resolve_auror_run(spec, tmp_path / "run.yaml", CONFIG_REPO, tmp_path)    # empty sensor library
    spec["descriptor"]["sensor"] = {"sensor_system": {}}                     # the old inline shape
    with pytest.raises(RunSpecError, match="sensor-spec/1 ref"):
        resolve_auror_run(spec, SPEC, CONFIG_REPO)


def test_settings_roi_checked_against_detector():
    spec = load_run_spec(SPEC)
    assert spec["descriptor"]["settings"][0]["roi"]["Width"] == 500
    lib = SPEC.parent.parent / "manifold_sensors"
    doc = load_sensor_spec(lib, "deepscan_850_306_nir_1280.yaml")
    _check_settings_roi([{"entry_id": "deepscan-850-306-nir-1280", "roi": {"Width": 500, "Height": 500}}], doc)
    with pytest.raises(RunSpecError, match="exceeds detector SensorWidth"):
        _check_settings_roi([{"entry_id": "deepscan-850-306-nir-1280",
                              "roi": {"Width": 500, "Height": 500, "OffsetX": 800}}], doc)
    with pytest.raises(RunSpecError, match="matches no sensor entry"):
        _check_settings_roi([{"entry_id": "nope"}], doc)


def test_derive_run_spec_swaps_sensor_only():
    base = load_run_spec(SPEC)
    new = derive_run_spec(base, "deepscan_850_306_nir_1280.yaml", "deepscan-850-306-nir-1280", roi={"Width": 64, "Height": 32})
    assert new["descriptor"]["sensor"]["ref"]["name"] == "deepscan_850_306_nir_1280.yaml"
    st = new["descriptor"]["settings"][0]
    assert st["entry_id"] == "deepscan-850-306-nir-1280" and st["roi"] == {"Width": 64, "Height": 32}
    assert st["exposure_time"] == base["descriptor"]["settings"][0]["exposure_time"]
    assert "channel_response" not in new["engine"]["platform"]               # a derived sensor is tabulated
    assert {k: v for k, v in new["engine"].items() if k != "platform"} == {k: v for k, v in base["engine"].items() if k != "platform"}
    assert base["descriptor"]["settings"][0]["roi"]["Width"] == 500          # the base is not modified
    assert "roi" not in derive_run_spec(base, "a.yaml", "a", roi={})["descriptor"]["settings"][0]


def _two_of(lib, what):
    """A copy of auror-nir in `lib` with its entry, or its entry's focal plane, doubled."""
    import copy
    import shutil
    shutil.copytree(PROJECT / "manifold_sensors", lib)
    doc = yaml.safe_load((lib / "auror-nir.yaml").read_text())
    entry = doc["sensor"]["entries"][0]
    if what == "entries":
        second = copy.deepcopy(entry)
        second["entry_id"] = "auror-nir-2"
        doc["sensor"]["entries"].append(second)
    else:
        entry["focal_planes"].append(copy.deepcopy(entry["focal_planes"][0]))
    (lib / "auror-nir.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))


@needs_config_repo
@pytest.mark.parametrize("what, settings, match", [
    ("entries", None, "has 2 entries; one sensor entry per job"),
    ("focal_planes", None, "has 2 focal planes; one focal plane per entry"),
    (None, 0, "settings must have one member.*got 0 members"),
    (None, 2, "settings must have one member.*got 2 members"),
    (None, "absent", "settings must have one member.*got None"),
], ids=["two-entries", "two-focal-planes", "settings-0", "settings-2", "settings-absent"])
def test_rejects_sensor_shapes_it_does_not_generate(tmp_path, what, settings, match):
    """One sensor entry, one focal plane and one settings member per job; anything else fails at resolution,
    so `Simulation` never assembles or renders it."""
    from protodirsig.simulation import Simulation
    lib = tmp_path / "manifold_sensors"
    if what:
        _two_of(lib, what)
    else:
        import shutil
        shutil.copytree(PROJECT / "manifold_sensors", lib)
    spec = load_run_spec(SPEC)
    spec["descriptor"]["sensor"]["ref"]["content_hash"] = "sha256:<hash>"
    st = spec["descriptor"]["settings"]
    if settings == "absent":
        del spec["descriptor"]["settings"]
    elif settings is not None:
        spec["descriptor"]["settings"] = (st * 2)[:settings]
    with pytest.raises(RunSpecError, match=match):
        resolve_auror_run(spec, SPEC, CONFIG_REPO, lib)
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    sim = Simulation.from_run_spec(path, CONFIG_REPO, tmp_path / "work", lib)
    c = sim.validate()
    assert not c.resolution_ok and not c.execution_ok and "not attempted" in c.execution_error
    with pytest.raises(RunSpecError, match="cannot run"):
        sim.run()
