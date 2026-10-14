"""scripts/compare_layered.py: what it derives from a demo's files, on synthetic files (no demo, no DIRSIG).

The native-size comparison itself runs only through the script, outside the repository
(docs/DIRSIG_layered_comparison.md); here: the files a `.sim` and a `.jsim` name, the static pose of a one-entry `.ppd`
and its refusals, the epoch and task windows of a `.tasks`, the image comparison, the refusal of a work folder inside
the repository, and the `engine.working_folder` that `write_layers` states (the files the loader requires).
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("compare_layered", ROOT / "scripts" / "compare_layered.py")
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)

PPD = """<platformmotion type="generic">
  <method type="raw" />
  <locationjitter>{jitter}</locationjitter>
  <orientationjitter></orientationjitter>
  <data rotationframe="sceneenu" rotationorder="xyz" angletype="absolute" angularunits="radians" spatialunits="meters">
    {entries}
  </data>
</platformmotion>
"""
ENTRY = """<entry><datetime type="relative">0</datetime>
      <position><location frame="scene"><point><x>-1.5</x><y>2</y><z>300</z></point></location></position>
      <orientation><eulerangles><cartesiantriple><x>0.1</x><y>0</y><z>3.14159265</z></cartesiantriple></eulerangles></orientation>
    </entry>"""
TASKS = """<tasklist>
  <reference><datetime type="absolute">2000-08-01T12:00:00.0000-05:00</datetime></reference>
  <task><start><datetime type="relative">0</datetime></start><stop><datetime type="relative">0.5</datetime></stop></task>
  <task><start><datetime type="relative">2</datetime></start><stop><datetime type="relative">2</datetime></stop></task>
</tasklist>
"""


def test_the_files_a_sim_and_a_jsim_name(tmp_path):
    (tmp_path / "a.sim").write_text('<simulation><scene externalfile="./s/x.scene"/><atmosphericconditions '
                                    'externalfile="./u.atm"/><platform externalfile="./p.platform"/><platformmotion '
                                    'externalfile="./m.ppd"/><tasklist externalfile="./t.tasks"/></simulation>')
    assert cl.simulation_inputs(tmp_path, "a.sim") == {"scene": "s/x.scene", "atmosphere": "u.atm",
                                                      "platform": "p.platform", "motion": "m.ppd", "tasks": "t.tasks"}
    plugins = [{"name": "BasicAtmosphere", "inputs": {"atmosphere_filename": "u.atm"}},
               {"name": "BasicPlatform", "inputs": {"platform_filename": "./p.platform", "motion_filename": "m.ppd",
                                                    "tasks_filename": "t.tasks"}}]
    (tmp_path / "b.jsim").write_text(json.dumps([{"scene_list": [{"inputs": "./x.scene"}], "plugin_list": plugins}]))
    assert cl.simulation_inputs(tmp_path, "b.jsim")["scene"] == "x.scene"
    # SpiceEphemeris without inputs is the plugin the layered job adds itself (Indoors1); with inputs, or any other
    # plugin, it is refused.
    plugins.append({"name": "SpiceEphemeris", "inputs": {}})
    (tmp_path / "c.jsim").write_text(json.dumps([{"scene_list": [{"inputs": "./x.scene"}], "plugin_list": plugins}]))
    assert cl.simulation_inputs(tmp_path, "c.jsim")["platform"] == "p.platform"
    plugins[-1]["inputs"] = {"kernel": "x.bsp"}
    (tmp_path / "d.jsim").write_text(json.dumps([{"scene_list": [{"inputs": "./x.scene"}], "plugin_list": plugins}]))
    with pytest.raises(ValueError, match="SpiceEphemeris"):
        cl.simulation_inputs(tmp_path, "d.jsim")
    plugins[-1] = {"name": "FixedEphemeris", "inputs": {}}
    (tmp_path / "e.jsim").write_text(json.dumps([{"scene_list": [{"inputs": "./x.scene"}], "plugin_list": plugins}]))
    with pytest.raises(ValueError, match="FixedEphemeris"):
        cl.simulation_inputs(tmp_path, "e.jsim")


@pytest.mark.parametrize("origin", [
    '<location frame="geodetic"><latitude>44.4</latitude><longitude>-73.2</longitude></location>',
    "<geodeticlocation><latitude>44.4</latitude><longitude>-73.2</longitude><altitude>0</altitude></geodeticlocation>",
], ids=["location", "geodeticlocation"])
def test_the_scene_origin_in_either_form(tmp_path, origin):
    (tmp_path / "x.scene").write_text(f"<classicscene><sceneorigin>{origin}</sceneorigin></classicscene>")
    assert cl.scene_origin(tmp_path / "x.scene") == (44.4, -73.2)


def test_a_one_entry_ppd_is_a_static_pose_and_others_are_refused(tmp_path):
    p = tmp_path / "m.ppd"
    p.write_text(PPD.format(jitter="", entries=ENTRY))
    assert cl.static_pose(p) == {"kind": "static", "position": {"frame": "scene", "xyz": [-1.5, 2.0, 300.0]},
                                 "orientation": {"kind": "euler", "euler": {"order": "xyz", "units": "radians",
                                                                            "frame": "sceneenu",
                                                                            "angles": [0.1, 0.0, 3.14159265]}}}
    for jitter, entries, words in (("", ENTRY + ENTRY, "2 entries"), ("<x/>", ENTRY, "locationjitter")):
        p.write_text(PPD.format(jitter=jitter, entries=entries))
        with pytest.raises(ValueError, match=words):
            cl.static_pose(p)


def test_the_epoch_is_utc_and_the_windows_relative(tmp_path):
    (tmp_path / "t.tasks").write_text(TASKS)
    assert cl.epoch_and_windows(tmp_path / "t.tasks") == (
        "2000-08-01T17:00:00Z", [{"start": 0.0, "stop": 0.5}, {"start": 2.0, "stop": 2.0}])


def _envi(path, values):
    values = np.asarray(values, dtype="<f8")
    path.write_bytes(values.tobytes())
    Path(str(path) + ".hdr").write_text(f"ENVI\nsamples = {values.shape[2]}\nlines = {values.shape[1]}\n"
                                        f"bands = {values.shape[0]}\ndata type = 5\ninterleave = bsq\nbyte order = 0\n")
    return path


def test_the_image_comparison(tmp_path):
    a = _envi(tmp_path / "a.img", [[[1, 2], [3, 4]]])
    b = _envi(tmp_path / "b.img", [[[1, 2], [3, 4.5]]])
    c = cl.compare(a, b)
    assert c["shape_a"] == c["shape_b"] == [1, 2, 2] and c["mean_a"] == [2.5] and c["mean_b"] == [2.625]
    assert c["max_abs_diff"] == 0.5 and c["fraction_pixels_differ"] == 0.25 and c["sha256_a"] != c["sha256_b"]
    assert cl.compare(a, a)["max_abs_diff"] == 0 and cl.compare(a, a)["fraction_pixels_differ"] == 0


def test_a_work_folder_inside_the_repository_is_refused():
    with pytest.raises(SystemExit, match="inside the repository"):
        cl.main(["DensityMap1", "--work", str(ROOT / "outputs" / "layered")])


def test_the_demo_angles_replace_only_the_generated_angles(tmp_path):
    demo = tmp_path / "demo.ppd"
    demo.write_text(PPD.format(jitter="", entries=ENTRY))
    generated = ("<platformmotion><data><entry><position><location type=\"scene\"><point><x>-1.500</x><y>2.000</y>"
                 "<z>300.000</z></point></location></position><orientation><eulerangles><cartesiantriple><x>0.100000</x>"
                 "<y>0.000000</y><z>3.141593</z></cartesiantriple></eulerangles></orientation></entry></data></platformmotion>")
    out = cl._demo_angles(generated, demo)
    assert "<x>0.1</x><y>0</y><z>3.14159265</z>" in out                     # the demo's text, as written there
    assert out.replace("<x>0.1</x><y>0</y><z>3.14159265</z>", "") == generated.replace(
        "<x>0.100000</x><y>0.000000</y><z>3.141593</z>", "")                 # nothing else changed


@pytest.mark.parametrize("rt, form, values", [
    ("<uniformradiativetransfer><hemisphereirradiance>1</hemisphereirradiance><skyfraction>0.2</skyfraction>"
     "</uniformradiativetransfer>", "uniform", {"hemisphere_irradiance": 1, "sky_fraction": 0.2}),
    ("<simpleradiativetransfer><apparentskytemperature>260</apparentskytemperature></simpleradiativetransfer>", "simple",
     {"apparent_sky_temperature": 260}),
], ids=["uniform", "simple"])
def test_a_demo_atm_is_read_by_its_radiative_transfer_form(tmp_path, rt, form, values):
    atm = tmp_path / "x.atm"
    atm.write_text("<atmosphericconditions><metadata/><uniformweather><classicdata><filename>"
                   f"$DIRSIG_HOME/lib/data/weather/mls.wth</filename></classicdata></uniformweather>{rt}"
                   "</atmosphericconditions>")
    got_form, block = cl.read_basic_atm(atm)
    assert got_form == form and block == {"radiative_transfer": values, "weather": {"install_file": "mls.wth"}}


def _synthetic_demo(config_repo, name, working=True):
    """A demo folder under `config_repo/demo_dirs/` (`demo.sim` and the files it names). With `working`, it names a file
    of each kind DIRSIG looks for in the working folder: a platform `<filename>`, a geometry list beside the `.scene`
    outside its `gdbdirectory` and the file that list names, and a material-file `PARAMETER_FILE` relative to the
    scene's folder; its `EMISSIVITY_FILE` lies in the `emsdirectory` and is not one."""
    demo = config_repo / "demo_dirs" / name
    (demo / "geometry").mkdir(parents=True)
    (demo / "materials").mkdir()
    (demo / "demo.sim").write_text('<simulation><scene externalfile="./demo.scene"/><atmosphericconditions '
                                   'externalfile="./demo.atm"/><platform externalfile="./demo.platform"/><platformmotion '
                                   'externalfile="./demo.ppd"/><tasklist externalfile="./demo.tasks"/></simulation>')
    glist = "demo.glist" if working else "geometry/demo.glist"                   # named "demo.glist" either way
    (demo / "demo.scene").write_text(
        '<classicscene><sceneorigin><location frame="geodetic"><latitude>44.4</latitude><longitude>-73.2</longitude>'
        "</location></sceneorigin><gdbdirectory>$SCENE_DIR/geometry</gdbdirectory><geometrylist>"
        "<geometrylistinclude>demo.glist</geometrylistinclude></geometrylist><matfilename>$SCENE_DIR/materials/demo.mat"
        "</matfilename><emsdirectory>$SCENE_DIR/materials</emsdirectory></classicscene>")
    (demo / glist).write_text("<geometrylist><object><basegeometry><obj><filename>shape.obj</filename></obj>"
                              "</basegeometry></object></geometrylist>")
    (demo / glist).with_name("shape.obj").write_text("v 0 0 0\n")
    entries = "PARAMETER_FILE = ./materials/a.brdf\n" if working else ""
    (demo / "materials" / "demo.mat").write_text(f"MATERIAL_ENTRY {{\n{entries}EMISSIVITY_FILE = b.ems\n}}\n")
    (demo / "materials" / "a.brdf").write_text("brdf")
    (demo / "materials" / "b.ems").write_text("ems")
    named = "<notes><filename>pixels.txt</filename></notes>" if working else ""
    (demo / "demo.platform").write_text(f"<platform>{named}</platform>")
    (demo / "pixels.txt").write_text("pixels")
    (demo / "demo.atm").write_text(
        "<atmosphericconditions><metadata/><uniformweather><classicdata><filename>$DIRSIG_HOME/lib/data/weather/mls.wth"
        "</filename></classicdata></uniformweather><uniformradiativetransfer><hemisphereirradiance>1"
        "</hemisphereirradiance><skyfraction>0.2</skyfraction></uniformradiativetransfer></atmosphericconditions>")
    (demo / "demo.ppd").write_text(PPD.format(jitter="", entries=ENTRY))
    (demo / "demo.tasks").write_text(TASKS)
    return demo


def _engine(layers, name):
    import yaml
    return yaml.safe_load((layers / "engine_profiles" / f"layered_{name.lower()}.yaml").read_text())["engine"]


def test_write_layers_states_the_working_folder_files_the_loader_requires(tmp_path, monkeypatch):
    from manifold.core.spectral import sha256_file
    from manifold.engines.dirsig.run_spec import _working_folder
    monkeypatch.setitem(cl.SIMULATION, "Synth1", "demo.sim")
    config_repo = tmp_path / "config_repo"
    demo = _synthetic_demo(config_repo, "Synth1")
    key, notes = cl.write_layers("Synth1", tmp_path / "layers", config_repo, 1)
    assert key == "layered_synth1"
    engine = _engine(tmp_path / "layers", "Synth1")
    names = [("demo.glist", "demo.glist"), ("materials/a.brdf", "materials/a.brdf"), ("pixels.txt", "pixels.txt"),
             ("shape.obj", "shape.obj")]
    assert engine["working_folder"] == [{"name": n, "ref": {"name": f"demo_dirs/Synth1/{rel}",
                                                            "content_hash": sha256_file(demo / rel)}}
                                        for n, rel in names]
    assert ("engine.working_folder: [('demo.glist', 'demo.scene'), ('materials/a.brdf', 'demo.mat'), "
            "('pixels.txt', 'demo.platform'), ('shape.obj', 'demo.glist')]") in notes
    # The loader accepts exactly what the script states (no missing, mismatched or unneeded entry).
    assert _working_folder(engine, config_repo, demo / "demo.scene", demo / "demo.platform") == tuple(
        (n, config_repo / "demo_dirs" / "Synth1" / rel) for n, rel in names)


def test_write_layers_states_no_working_folder_when_none_is_needed(tmp_path, monkeypatch):
    monkeypatch.setitem(cl.SIMULATION, "Synth2", "demo.sim")
    config_repo = tmp_path / "config_repo"
    _synthetic_demo(config_repo, "Synth2", working=False)
    _, notes = cl.write_layers("Synth2", tmp_path / "layers", config_repo, 1)
    assert "working_folder" not in _engine(tmp_path / "layers", "Synth2")
    assert not any(n.startswith("engine.working_folder") for n in notes)


@pytest.mark.parametrize("position", ['<location type="scene"><point><x>-1.5</x><y>2</y><z>300</z></point></location>',
                                      '<scenelocation><point><x>-1.5</x><y>2</y><z>300</z></point></scenelocation>'])
def test_the_older_ppd_position_forms_give_the_same_pose(tmp_path, position):
    """DIRSIG's Documents-folder scenes write `<location type="scene">` (foxbat) or `<scenelocation>` (urban) where its
    demos write `<location frame="scene">`; all three are the same scene-frame position (round 32)."""
    p, q = tmp_path / "a.ppd", tmp_path / "b.ppd"
    p.write_text(PPD.format(jitter="", entries=ENTRY))
    old = '<location frame="scene"><point><x>-1.5</x><y>2</y><z>300</z></point></location>'
    q.write_text(PPD.format(jitter="", entries=ENTRY.replace(old, position)))
    assert cl.static_pose(q) == cl.static_pose(p)
    q.write_text(PPD.format(jitter="", entries=ENTRY.replace(old, old.replace('frame="scene"', 'frame="ecef"'))))
    with pytest.raises(ValueError, match="location frame 'ecef'"):
        cl.static_pose(q)


def test_a_directory_source_needs_its_simulation_file_and_a_demo_name_must_be_known(tmp_path):
    with pytest.raises(SystemExit, match="NAME=DIR:SIMULATION"):
        cl.main(["--source", f"scene={tmp_path}:shots/none.sim", "--work", str(tmp_path / "work")])
    with pytest.raises(SystemExit):
        cl.main(["NotADemo", "--work", str(tmp_path / "work")])
    with pytest.raises(SystemExit):
        cl.main(["--work", str(tmp_path / "work")])


def test_threads_is_parsed_and_must_be_at_least_one(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(cl, "run_demo", lambda name, work, seed, timeout, threads=None: seen.append(threads) or
                        {"demo": name, "runs": {}})
    assert cl.main(["DensityMap1", "--work", str(tmp_path / "work"), "--threads", "1"]) == 0
    assert cl.main(["DensityMap1", "--work", str(tmp_path / "work")]) == 0
    assert seen == [1, None]                                         # the default requests no count, as before
    with pytest.raises(SystemExit):
        cl.main(["DensityMap1", "--work", str(tmp_path / "work"), "--threads", "0"])


def test_threads_reach_the_layered_profile_the_pass_through_specs_and_the_direct_renders(tmp_path, monkeypatch):
    import yaml
    monkeypatch.setitem(cl.SIMULATION, "Synth3", "demo.sim")
    config_repo = tmp_path / "config_repo"
    _synthetic_demo(config_repo, "Synth3", working=False)
    cl.write_layers("Synth3", tmp_path / "a", config_repo, 1)
    cl.write_layers("Synth3", tmp_path / "b", config_repo, 1, threads=1)
    profile = lambda d: yaml.safe_load((d / "engine_profiles" / "layered_synth3.yaml").read_text())  # noqa: E731
    assert "resources" not in profile(tmp_path / "a")
    assert profile(tmp_path / "b")["resources"] == {"cpu_threads": 1}
    assert profile(tmp_path / "b")["engine"] == profile(tmp_path / "a")["engine"]
    assert "resources" not in cl.passthrough_spec("Synth3", config_repo, 1)
    assert cl.passthrough_spec("Synth3", config_repo, None, threads=2)["resources"] == {"cpu_threads": 2}
    assert cl.dirsig5_command("dirsig5", "out", 1) == ["dirsig5", "--output_folder=out", "--random_seed", "1",
                                                       "example.jsim"]
    assert cl.dirsig5_command("dirsig5", "out", 1, 1)[-2:] == ["--threads=1", "example.jsim"]


def test_the_noise_floor_note_appears_only_when_the_two_pass_through_renders_differ(tmp_path, capsys, monkeypatch):
    a = _envi(tmp_path / "a.img", [[[1, 2], [3, 4]]])
    b = _envi(tmp_path / "b.img", [[[1, 2], [3, 4.5]]])
    same = {"demo": "Synth4", "noise_floor": {"demo.img": cl.compare(a, a)}}
    differ = {"demo": "Synth4", "noise_floor": {"demo.img": cl.compare(a, b)}}
    assert cl.noise_floor_note(same) is None and cl.noise_floor_note({"demo": "Synth4"}) is None
    note = cl.noise_floor_note(differ)
    assert note == ("Synth4: noise floor: two same-seed pass-through renders at DIRSIG's default thread count differ "
                    "from one another (demo.img; up to 25.0000% of pixels, max abs difference 0.5), so a digest "
                    "difference above is no evidence of an input difference; rerun with --threads 1")
    monkeypatch.setattr(cl, "run_demo", lambda *args, **kw: differ)
    cl.main(["DensityMap1", "--work", str(tmp_path / "work")])
    assert note in capsys.readouterr().out
