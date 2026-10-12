"""scripts/compare_layered.py: what it derives from a demo's files, on synthetic files (no demo, no DIRSIG).

The native-size comparison itself runs only through the script, outside the repository
(docs/DIRSIG_layered_comparison.md); here: the files a `.sim` and a `.jsim` name, the static pose of a one-entry `.ppd`
and its refusals, the epoch and task windows of a `.tasks`, the image comparison, and the refusal of a work folder
inside the repository.
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
