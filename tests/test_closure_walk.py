"""The DIRSIG closure walker (round 46 B) on small synthetic trees: roles from the referencing element, Cfg 2.3's path
rules reported rather than normalized (absolute, `..`, non-NFC, symbolic link, outside the root, form), unresolved
references, installation references, disabled elements, orphans, and the role conflict and unroled cases."""
import json
import os
import unicodedata

from manifold.engines.dirsig.closure import VIOLATION_KINDS, walk


def _write(root, rel, text=""):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _jsim(root, scene="scenes/s/s.scene", extra=None, name="run.jsim"):
    plugins = [{"name": "BasicPlatform", "inputs": {"platform_filename": "platforms/p.platform",
                                                    "motion_filename": "motion/m.ppd",
                                                    "tasks_filename": "tasks/t.tasks"}},
               {"name": "ThermWeather", "inputs": {"filename": "weather/w.wth"}}] + (extra or [])
    _write(root, name, json.dumps([{"scene_list": [{"inputs": scene}], "plugin_list": plugins}]))
    for rel in ("platforms/p.platform", "motion/m.ppd", "tasks/t.tasks", "weather/w.wth"):
        _write(root, rel, "<platform/>" if rel.endswith(".platform") else "x")


SCENE = """<classicscene>
  <metadata><entry><value>/Users/someone/notes.txt</value></entry></metadata>
  <gdbdirectory>$SCENE_DIR/geometry</gdbdirectory>
  <geometrylist enabled="true">
    <geometrylistinclude enabled="true">lists/a.glist</geometrylistinclude>
    {extra_list}
  </geometrylist>
  <matfilename>$SCENE_DIR/materials/s.mat</matfilename>
  <emsdirectory>$SCENE_DIR/materials</emsdirectory>
  <mapdirectory>$SCENE_DIR/maps</mapdirectory>
  <maplist>
    <materialmap enabled="false"><image><filename>{map}</filename></image></materialmap>
  </maplist>
</classicscene>"""

GLIST = """<geometrylist>
  <object><basegeometry><obj><filename>objects/o.obj</filename></obj></basegeometry>
    <dynamicinstance><motion type="generic"><filename>motion/track.ppd</filename></motion></dynamicinstance>
  </object>
</geometrylist>"""

MAT = """MATERIAL_ENTRY {
    ID = 1
    SURFACE_PROPERTIES {
        REFLECTANCE_PROP {
            TXT_FILENAME = curves/r.txt
        }
    }
    EMISSIVITY_PROP {
        FILENAME = e.ems
    }
}"""


def _tree(root, map_text="material_map.pgm", extra_list="", mat=MAT, scene_ref="scenes/s/s.scene"):
    _jsim(root, scene=scene_ref)
    _write(root, "scenes/s/s.scene", SCENE.format(map=map_text, extra_list=extra_list))
    _write(root, "scenes/s/geometry/lists/a.glist", GLIST)
    _write(root, "scenes/s/geometry/objects/o.obj", "o")
    _write(root, "scenes/s/geometry/motion/track.ppd", "x")
    _write(root, "scenes/s/materials/s.mat", mat)
    _write(root, "scenes/s/materials/curves/r.txt", "1 2")
    _write(root, "scenes/s/materials/e.ems", "1 2")


def _roles(w):
    return {f.path: f.role for f in w.files}


def test_a_clean_tree_reaches_every_file_with_its_role(tmp_path):
    _tree(tmp_path)
    w = walk(tmp_path, "run.jsim")
    assert _roles(w) == {
        "run.jsim": "dirsig:sim", "platforms/p.platform": "dirsig:platform", "motion/m.ppd": "dirsig:motion",
        "tasks/t.tasks": "dirsig:tasks", "weather/w.wth": "dirsig:weather", "scenes/s/s.scene": "dirsig:scene",
        "scenes/s/geometry/lists/a.glist": "dirsig:geometry_list",
        "scenes/s/geometry/objects/o.obj": "dirsig:geometry_object",
        "scenes/s/geometry/motion/track.ppd": "dirsig:instance_motion",
        "scenes/s/materials/s.mat": "dirsig:material_db", "scenes/s/materials/curves/r.txt": "dirsig:other_input",
        "scenes/s/materials/e.ems": "dirsig:emissivity"}
    assert w.passes and w.clean and not w.violations and not w.orphans
    assert [f.path for f in w.files] == sorted((f.path for f in w.files), key=lambda p: p.encode())


def test_two_ppd_files_take_two_roles_from_their_elements(tmp_path):
    _tree(tmp_path)
    roles = _roles(walk(tmp_path, "run.jsim"))
    assert roles["motion/m.ppd"] == "dirsig:motion"
    assert roles["scenes/s/geometry/motion/track.ppd"] == "dirsig:instance_motion"


def test_an_absolute_reference_is_reported_and_not_followed(tmp_path):
    _tree(tmp_path)
    doc = json.loads((tmp_path / "run.jsim").read_text())
    doc[0]["plugin_list"][1]["inputs"]["filename"] = "C:/DIRSIG/weather/w.wth"
    (tmp_path / "run.jsim").write_text(json.dumps(doc))
    w = walk(tmp_path, "run.jsim")
    assert [(v.kind, v.text, v.field) for v in w.violations] == [
        ("absolute", "C:/DIRSIG/weather/w.wth", "ThermWeather.filename")]
    assert "weather/w.wth" in w.orphans and "weather/w.wth" not in _roles(w)
    assert not w.passes


def test_a_dotdot_segment_is_reported_and_one_leaving_the_root_also_as_outside(tmp_path):
    _tree(tmp_path, scene_ref="scenes/../scenes/s/s.scene")
    w = walk(tmp_path, "run.jsim")
    assert {v.kind for v in w.violations} == {"dotdot"}
    assert "scenes/s/s.scene" in _roles(w)                         # reported, the walk goes on
    _tree(tmp_path / "t2", scene_ref="../outside.scene")
    w = walk(tmp_path / "t2", "run.jsim")
    assert {v.kind for v in w.violations} == {"dotdot", "outside_root"}


def test_a_non_nfc_name_is_reported_not_normalized(tmp_path):
    name = unicodedata.normalize("NFD", "caf\u00e9.ems")
    assert not unicodedata.is_normalized("NFC", name)
    _tree(tmp_path, mat=MAT.replace("e.ems", name))
    _write(tmp_path, f"scenes/s/materials/{name}", "1 2")
    w = walk(tmp_path, "run.jsim")
    assert [v.kind for v in w.violations] == ["non_nfc"]
    assert f"scenes/s/materials/{name}" in _roles(w)               # the path as written, not its NFC form


def test_a_symbolic_link_is_reported_with_the_files_behind_it(tmp_path):
    lib = tmp_path / "library"
    _write(lib, "lists/a.glist", GLIST)
    _write(lib, "objects/o.obj", "o")
    _write(lib, "motion/track.ppd", "x")
    _write(lib, "unused.obj", "u")
    root = tmp_path / "job"
    _tree(root)
    import shutil
    shutil.rmtree(root / "scenes/s/geometry")
    os.symlink(lib, root / "scenes/s/geometry", target_is_directory=True)
    w = walk(root, "run.jsim")
    assert w.links == ["scenes/s/geometry"] and w.kinds() == ["symlink"]
    assert _roles(w)["scenes/s/geometry/objects/o.obj"] == "dirsig:geometry_object"     # the link's path, not its target
    assert w.behind_links == ["scenes/s/geometry/unused.obj"] and not w.orphans


def test_a_disabled_element_is_not_followed_but_its_text_is_checked(tmp_path):
    _tree(tmp_path, map_text="/Users/eoptic/maps/material_map.pgm")
    w = walk(tmp_path, "run.jsim")
    assert [(v.kind, v.enabled, v.field) for v in w.violations] == [("absolute", False, "materialmap.filename")]
    _tree(tmp_path / "t2")                                         # relative but missing: disabled, so not unresolved
    assert not walk(tmp_path / "t2", "run.jsim").unresolved


def test_descriptive_subtrees_are_not_read(tmp_path):
    _tree(tmp_path)
    assert not [v for v in walk(tmp_path, "run.jsim").violations if "notes" in v.text]


def test_an_orphan_is_listed_and_an_orphan_atm_is_scanned(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "atmospheres/test.atm", "<atmosphericconditions><uniformweather><classicdata>"
           "<filename>/home/someone/weather/saw.wth</filename></classicdata></uniformweather></atmosphericconditions>")
    w = walk(tmp_path, "run.jsim")
    assert w.orphans == ["atmospheres/test.atm"]
    assert [(v.kind, v.referrer, v.orphan) for v in w.violations] == [("absolute", "atmospheres/test.atm", True)]
    assert "atmospheres/test.atm" not in _roles(w)


def test_an_installation_reference_is_recorded_not_a_violation(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "u.atm", "<atmosphericconditions><uniformweather><classicdata>"
           "<filename>$DIRSIG_HOME/lib/data/weather/mls.wth</filename></classicdata></uniformweather>"
           "</atmosphericconditions>")
    doc = json.loads((tmp_path / "run.jsim").read_text())
    doc[0]["plugin_list"].append({"name": "BasicAtmosphere", "inputs": {"atmosphere_filename": "./u.atm"}})
    (tmp_path / "run.jsim").write_text(json.dumps(doc))
    w = walk(tmp_path, "run.jsim")
    assert w.install == [("$DIRSIG_HOME/lib/data/weather/mls.wth", "u.atm", "classicdata.filename")]
    assert _roles(w)["u.atm"] == "dirsig:atmosphere"               # a leading ./ is stripped
    assert w.passes


def test_an_unresolved_reference_is_reported(tmp_path):
    _tree(tmp_path)
    (tmp_path / "scenes/s/materials/e.ems").unlink()
    w = walk(tmp_path, "run.jsim")
    assert w.unresolved == [("e.ems", "scenes/s/materials/s.mat", "EMISSIVITY_PROP.FILENAME")] and not w.passes


def test_a_file_no_role_covers_is_reached_unroled(tmp_path):
    _tree(tmp_path, mat=MAT.replace("TXT_FILENAME = curves/r.txt", "BRDF_FIT_FILE = curves/r.txt"))
    w = walk(tmp_path, "run.jsim")
    assert [(f.path, f.field) for f in w.unroled] == [("scenes/s/materials/curves/r.txt",
                                                       "REFLECTANCE_PROP.BRDF_FIT_FILE")]
    assert not w.passes


def test_a_compiled_scene_reference_stands_for_the_scene(tmp_path):
    _tree(tmp_path, scene_ref="scenes/s/s.scene.hdf")
    assert _roles(walk(tmp_path, "run.jsim"))["scenes/s/s.scene"] == "dirsig:scene"


def test_a_file_reached_under_two_roles_is_a_conflict(tmp_path):
    _tree(tmp_path)
    (tmp_path / "scenes/s/geometry/lists/a.glist").write_text(GLIST.replace("motion/track.ppd", "../../../../motion/m.ppd"))
    w = walk(tmp_path, "run.jsim")
    assert [(c[0], c[1], c[2]) for c in w.role_conflicts] == [("motion/m.ppd", "dirsig:motion",
                                                               "dirsig:instance_motion")]


def test_a_legacy_sim_entry(tmp_path):
    _tree(tmp_path)
    _write(tmp_path, "demo.sim", '<simulation><scene externalfile="./scenes/s/s.scene"/>'
           '<platform externalfile="platforms/p.platform"/><platformmotion externalfile="motion/m.ppd"/>'
           '<tasklist externalfile="tasks/t.tasks"/></simulation>')
    w = walk(tmp_path, "demo.sim")
    roles = _roles(w)
    assert roles["demo.sim"] == "dirsig:sim" and roles["motion/m.ppd"] == "dirsig:motion"
    assert "run.jsim" in w.orphans and "weather/w.wth" in w.orphans


def test_the_violation_kinds_are_the_path_rules():
    assert set(VIOLATION_KINDS) >= {"absolute", "dotdot", "non_nfc", "symlink", "outside_root"}
