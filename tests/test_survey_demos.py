"""scripts/survey_demos.py on synthetic demo archives built here (no DIRSIG demo bytes), and on the real install when
it is linked."""
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("survey_demos", ROOT / "scripts" / "survey_demos.py")
survey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(survey)
REAL = ROOT / "external" / "dirsig" / "demos" / "zips"
SECRET = "CONTENT-THAT-MUST-NOT-LEAK"

SCENE = f"""<classicscene><metadata><entry><name>Description</name><value>{SECRET}</value></entry></metadata>
<geometrylist><geometrylistinclude>geometry/demo.glist</geometrylistinclude></geometrylist>
<matfilename>$SCENE_DIR/materials/demo.mat</matfilename><odbdirectory>.</odbdirectory></classicscene>"""
GLIST = "<geometrylist><object><basegeometry><obj><filename>box.obj</filename></obj></basegeometry></object></geometrylist>"
ATM = "<atmosphericconditions><metadata/><uniformweather/><simpleradiativetransfer/></atmosphericconditions>"
PPD = "<platformmotion><method type='raw'/><locationjitter/><orientationjitter/><data><entry/></data></platformmotion>"
TASKS = "<tasklist><task/><task/></tasklist>"


def platform(instrument="generic", extra=""):
    return (f"<platform><attachment><mount type='static'><attachment><instrument type='{instrument}'>{extra}"
            "<focalplane><capturemethod type='simple'><channellist><channel/><channel/></channellist></capturemethod>"
            "<detectorarray><xelementcount>16</xelementcount><yelementcount>12</yelementcount></detectorarray>"
            "</focalplane></instrument></attachment></mount></attachment></platform>")


def make(tmp_path, name, sim=None, jsim=None, plat=None, extra_files=None, drop=()):
    files = {"demo.scene": SCENE, "geometry/demo.glist": GLIST, "geometry/box.obj": "v 0 0 0\n" * 100,
             "materials/demo.mat": "mat", "demo.atm": ATM, "demo.platform": plat or platform(), "demo.ppd": PPD,
             "demo.tasks": TASKS, "README.txt": SECRET}
    if sim is not None:
        files["demo.sim"] = sim
    if jsim is not None:
        files["demo.jsim"] = json.dumps(jsim)
    files.update(extra_files or {})
    path = tmp_path / f"{name}.zip"
    with zipfile.ZipFile(path, "w") as z:
        for rel, text in files.items():
            if rel not in drop:
                z.writestr(f"{name}/{rel}", text)
    return path


SIM = ("<simulation><scene externalfile='./demo.scene'/><atmosphericconditions externalfile='./demo.atm'/>"
       "<platform externalfile='./demo.platform'/><platformmotion externalfile='./demo.ppd'/>"
       "<tasklist externalfile='./demo.tasks'/></simulation>")


def jsim(atmosphere="NewAtmosphere", weather="ThermWeather", ephemeris="SpiceEphemeris"):
    plugins = [{"name": atmosphere, "inputs": {}}, {"name": ephemeris, "inputs": {}},
               {"name": "BasicPlatform", "inputs": {"platform_filename": "./demo.platform",
                                                    "motion_filename": "./demo.ppd", "tasks_filename": "./demo.tasks"}}]
    if weather:
        plugins.append({"name": weather, "inputs": {}})
    return [{"scene_list": [{"inputs": "./demo.scene"}], "plugin_list": plugins}]


def test_a_legacy_sim_demo_is_read_and_is_near(tmp_path):
    r = survey.survey(make(tmp_path, "Legacy1", sim=SIM))
    assert r["verdict"] == "near" and r["format"] == "sim" and r["ephemeris"] == "implicit (.sim)"
    # Simple radiative transfer is covered (engine.atmosphere.simple); this .atm's uniform weather names no file.
    assert r["missing"] == ["BasicAtmosphere .atm (uniform weather not from the installation)"]
    assert (r["array"], r["channels"], r["tasks"], r["motion"]) == ("16x12", 2, 2, "static (.ppd)")
    members = {m.split("/", 1)[1] for m in r["scene_members"]}
    assert members == {"demo.scene", "geometry/demo.glist", "geometry/box.obj", "materials/demo.mat"}
    assert r["scene_bytes"] == sum(len(t) for t in (SCENE, GLIST, "v 0 0 0\n" * 100, "mat"))


def test_a_jsim_demo_with_new_atmosphere_is_ready(tmp_path):
    r = survey.survey(make(tmp_path, "Ready1", jsim=jsim()))
    assert (r["verdict"], r["missing"], r["atmosphere"], r["weather"]) == ("ready", [], "NewAtmosphere", "ThermWeather")


@pytest.mark.parametrize("kwargs, verdict, feature", [
    (dict(jsim=jsim(atmosphere="FourCurveAtmosphere")), "near", "FourCurveAtmosphere"),
    (dict(jsim=jsim(weather=None)), "near", "weather without a ThermWeather file"),
    (dict(jsim=jsim(ephemeris="FixedEphemeris")), "near", "FixedEphemeris"),
    (dict(jsim=jsim(), plat=platform("lidar")), "far", "non-imaging sensor: lidar"),
    (dict(jsim=jsim(atmosphere="FourCurveAtmosphere", weather="NsrdbWeather")), "far", "NsrdbWeather"),
], ids=["four_curve", "no_weather", "fixed_ephemeris", "lidar", "two_features"])
def test_features_and_verdicts(tmp_path, kwargs, verdict, feature):
    r = survey.survey(make(tmp_path, "Case1", **kwargs))
    assert r["verdict"] == verdict and feature in r["missing"]


def test_a_platform_feature_is_the_camera_as_authored_not_missing(tmp_path):
    r = survey.survey(make(tmp_path, "Case1", jsim=jsim(), plat=platform(extra="<distortion/>")))
    assert r["verdict"] == "ready" and r["missing"] == [] and r["camera"] == ["lens distortion"]


UNIFORM_ATM = ("<atmosphericconditions><uniformweather><classicdata><filename>{weather}</filename></classicdata>"
               "</uniformweather><{rt}radiativetransfer/></atmosphericconditions>")


@pytest.mark.parametrize("rt", ["uniform", "simple"])
@pytest.mark.parametrize("weather, missing", [
    ("$DIRSIG_HOME/lib/data/weather/mls.wth", []),
    ("./my.wth", ["BasicAtmosphere .atm (uniform weather not from the installation)"]),
], ids=["installation_weather", "own_weather"])
def test_a_uniform_atm_is_covered_only_with_an_installation_weather_file(tmp_path, weather, missing, rt):
    atm = UNIFORM_ATM.format(weather=weather, rt=rt)
    r = survey.survey(make(tmp_path, "Uniform1", sim=SIM, extra_files={"demo.atm": atm}))
    assert r["missing"] == missing and r["verdict"] == ("ready" if not missing else "near")


def test_classic_radiative_transfer_is_still_missing(tmp_path):
    atm = UNIFORM_ATM.format(weather="$DIRSIG_HOME/lib/data/weather/mls.wth", rt="classic")
    r = survey.survey(make(tmp_path, "Classic1", sim=SIM, extra_files={"demo.atm": atm}))
    assert r["missing"] == ["BasicAtmosphere .atm (classicradiativetransfer, uniformweather)"] and r["verdict"] == "near"


THUMB = ("<classicscene><thumbnaillist><thumbnail><filename>$SCENE_DIR/images/t.png</filename></thumbnail>"
         "</thumbnaillist>")


def test_files_named_beside_the_scene_are_placed_and_thumbnails_are_not_needed(tmp_path):
    scene = SCENE.replace("geometry/demo.glist", "demo.glist").replace("<classicscene>", THUMB)
    r = survey.survey(make(tmp_path, "Sibling1", jsim=jsim(), extra_files={"demo.scene": scene, "demo.glist": GLIST,
                                                                           "images/t.png": "png"}))
    assert r["missing"] == [] and r["verdict"] == "ready"


def test_scene_files_the_job_does_not_place_are_missing(tmp_path):
    # A folder the scene reaches only through a file it names that is not there: the job places nothing from it.
    scene = SCENE.replace("<classicscene>", "<classicscene><image><filename>$SCENE_DIR/textures/gone.png</filename></image>")
    r = survey.survey(make(tmp_path, "Unplaced1", jsim=jsim(), extra_files={"demo.scene": scene, "textures/t.png": "png"}))
    assert r["missing"] == ["scene files the job does not place"] and r["verdict"] == "near"


def test_a_geometry_list_found_only_from_the_working_folder_is_placed(tmp_path):
    # Named by a bare name, beside the scene and not in its gdbdirectory: DIRSIG searches the working folder, where the
    # job copies it (engine.working_folder, Telecentricity1 measured byte-identical), so it is listed, not missing.
    scene = SCENE.replace("geometry/demo.glist", "demo.glist").replace(
        "<odbdirectory>.</odbdirectory>", "<gdbdirectory>$SCENE_DIR/geometry</gdbdirectory>")
    r = survey.survey(make(tmp_path, "Beside1", jsim=jsim(), extra_files={"demo.scene": scene, "demo.glist": GLIST},
                           drop=("geometry/demo.glist",)))
    assert r["missing"] == [] and r["verdict"] == "ready" and r["working_folder"] == ["demo.glist"]
    found = scene.replace("$SCENE_DIR/geometry</gdbdirectory>", "$SCENE_DIR</gdbdirectory>")
    r = survey.survey(make(tmp_path, "Beside2", jsim=jsim(), extra_files={"demo.scene": found, "demo.glist": GLIST},
                           drop=("geometry/demo.glist",)))
    assert r["missing"] == [] and r["verdict"] == "ready" and r["working_folder"] == []


def test_files_the_platform_names_are_placed(tmp_path):
    # DIRSIG reads them from the working folder, where the job copies them (BayerPattern1 measured byte-identical).
    plat = platform(extra="<pixelmap><filename format='hdf'>pixels.hdf</filename></pixelmap><x><filename/></x>")
    r = survey.survey(make(tmp_path, "PlatFile1", jsim=jsim(), plat=plat, extra_files={"pixels.hdf": "hdf"}))
    assert r["missing"] == [] and r["verdict"] == "ready" and r["working_folder"] == ["pixels.hdf"]
    r = survey.survey(make(tmp_path, "PlatFile2", jsim=jsim(), plat=plat))          # named but not shipped: not counted
    assert r["missing"] == [] and r["verdict"] == "ready" and r["working_folder"] == []


def test_material_files_found_only_from_the_working_folder_are_placed(tmp_path):
    # A PARAMETER_FILE, BRDF_FIT_FILE or EMISSIVITY_FILE relative to the scene's folder and not to its emsdirectory
    # (Polarization5, measured): DIRSIG looks for it in the working folder, where the job copies it (engine.working_folder),
    # so it is listed, not missing. A TEMP_SOLVER FILENAME is not counted (DataDrivenTempSolver1 renders without it in the
    # working folder), nor an unmeasured key.
    mat = ("MATERIAL_ENTRY {\n  REFLECTANCE_PROP {\n    PARAMETER_FILE = ./materials/a.brdf\n"
           "    TXT_FILENAME = ./materials/u.txt\n  }\n  TEMP_SOLVER {\n    FILENAME = materials/t.txt\n  }\n}\n")
    scene = SCENE.replace("<odbdirectory>", "<emsdirectory>$SCENE_DIR/materials</emsdirectory><odbdirectory>")
    files = {"demo.scene": scene, "materials/demo.mat": mat, "materials/a.brdf": "brdf", "materials/t.txt": "0 300",
             "materials/u.txt": "txt"}
    r = survey.survey(make(tmp_path, "MatFile1", jsim=jsim(), extra_files=files))
    assert r["missing"] == [] and r["verdict"] == "ready" and r["working_folder"] == ["materials/a.brdf"]
    files["materials/demo.mat"] = mat.replace("./materials/a.brdf", "a.brdf")                  # in the emsdirectory
    r = survey.survey(make(tmp_path, "MatFile2", jsim=jsim(), extra_files=files))
    assert r["missing"] == [] and r["verdict"] == "ready" and r["working_folder"] == []
    for key in ("BRDF_FIT_FILE", "EMISSIVITY_FILE"):
        files["materials/demo.mat"] = mat.replace("PARAMETER_FILE", key)
        r = survey.survey(make(tmp_path, f"MatFile3{key}", jsim=jsim(), extra_files=files))
        assert r["missing"] == [] and r["working_folder"] == ["materials/a.brdf"]
    # A material bundle with an empty emsdirectory: DIRSIG searches the working folder only (BundledMaterials1).
    bundle = SCENE.replace("<odbdirectory>", "<emsdirectory></emsdirectory><odbdirectory>")
    files = {"demo.scene": bundle, "materials/demo.mat": "MATERIAL_ENTRY {\n  BUNDLE_FILENAME = bundles/a.mat.hdf\n}\n",
             "bundles/a.mat.hdf": "hdf"}
    r = survey.survey(make(tmp_path, "MatFile4", jsim=jsim(), extra_files=files))
    assert r["missing"] == [] and r["verdict"] == "ready" and r["working_folder"] == ["bundles/a.mat.hdf"]


def test_material_files_the_job_does_not_place_are_missing(tmp_path):
    # A file the material file names (any key) that lies beside the .scene, outside the linked folders and not named by
    # the .scene, is held neither by the job's scene copy nor by its working folder (MappedTherm1's values.img and
    # roof_metal_gray.ems, measured); in materials/ it is linked, and named by the .scene it is copied.
    scene = SCENE.replace("<odbdirectory>", "<emsdirectory>$SCENE_DIR</emsdirectory><mapdirectory>$SCENE_DIR/maps"
                          "</mapdirectory><odbdirectory>")
    mat = "MATERIAL_ENTRY {\n  FILENAME = gray.ems\n  TEMP_SOLVER {\n    IMAGE_FILENAME = values.img\n  }\n}\n"
    files = {"demo.scene": scene, "materials/demo.mat": mat, "gray.ems": "ems", "values.img": "img"}
    r = survey.survey(make(tmp_path, "Unplaced2", jsim=jsim(), extra_files=files))
    assert r["missing"] == ["material files the job does not place"] and r["verdict"] == "near"
    assert r["working_folder"] == ["values.img"]          # round 27: a TEMP_SOLVER IMAGE_FILENAME is placed; gray.ems,
                                                          # a FILENAME outside an EMISSIVITY_PROP block, is not
    files = {"demo.scene": scene, "materials/demo.mat": mat.replace("values.img", "materials/values.img"),
             "gray.ems": "ems", "materials/values.img": "img"}
    files["demo.scene"] = scene.replace("<odbdirectory>", "<notes>gray.ems</notes><odbdirectory>")
    r = survey.survey(make(tmp_path, "Unplaced3", jsim=jsim(), extra_files=files))
    assert r["missing"] == [] and r["verdict"] == "ready"


def test_material_files_the_scene_copy_does_not_hold_are_placed(tmp_path):
    # Round 27, measured on MappedTherm1 and ChipMaker2: an EMISSIVITY_PROP FILENAME, a TEMP_SOLVER IMAGE_FILENAME (with
    # its ENVI header), a texture IMAGE FILENAME or a MATERIAL_MAP IMAGE_FILENAME relative to the scene's folder, where
    # the scene copy does not hold it in the emsdirectory or mapdirectory, is looked for in the working folder, where
    # the job copies it: listed, not missing.
    scene = SCENE.replace("<odbdirectory>", "<emsdirectory>$SCENE_DIR</emsdirectory><mapdirectory>$SCENE_DIR/maps"
                          "</mapdirectory><odbdirectory>")
    mat = ("MATERIAL_ENTRY {\n  SURFACE_PROPERTIES {\n    EMISSIVITY_PROP {\n      FILENAME = gray.ems\n    }\n  }\n"
           "  TEMP_SOLVER {\n    IMAGE_FILENAME = values.img\n  }\n  MATERIAL_MAP {\n    IMAGE_FILENAME = maps/m.png\n"
           "    IMAGE_FILENAME = n.png\n  }\n}\n")
    files = {"demo.scene": scene, "materials/demo.mat": mat, "gray.ems": "ems", "values.img": "img",
             "values.img.hdr": "hdr", "maps/m.png": "png", "maps/n.png": "png"}
    r = survey.survey(make(tmp_path, "Unheld1", jsim=jsim(), extra_files=files))
    assert r["missing"] == [] and r["verdict"] == "ready"
    assert sorted(r["working_folder"]) == ["gray.ems", "maps/m.png", "values.img", "values.img.hdr"]   # n.png: held
    # An unmeasured block (a REFLECTANCE_PROP IMAGE_FILENAME, EarthClouds1's form) beside the .scene stays missing.
    files["materials/demo.mat"] = mat.replace("TEMP_SOLVER", "REFLECTANCE_PROP")
    r = survey.survey(make(tmp_path, "Unheld2", jsim=jsim(), extra_files=files))
    assert r["missing"] == ["material files the job does not place"] and "values.img" not in r["working_folder"]


def test_an_external_clock_is_missing(tmp_path):
    # It captures at its trigger times, several in one task window; the SDK's dry-run check expects one capture per
    # window (Thermal2, measured), so it is not a camera feature carried as authored.
    plat = platform(extra="<clock type='external'><filename>triggers.txt</filename></clock>")
    r = survey.survey(make(tmp_path, "Clock1", jsim=jsim(), plat=plat, extra_files={"triggers.txt": "0\n900\n"}))
    assert r["missing"] == ["external clock (several captures in a task window)"] and r["verdict"] == "near"
    assert "external clock (triggers)" not in r["camera"]

def test_motion_kinds(tmp_path):
    moving = PPD.replace("<data><entry/></data>", "<data><entry/><entry/><entry/></data>")
    r = survey.survey(make(tmp_path, "Moving1", jsim=jsim(), extra_files={"demo.ppd": moving}))
    assert r["moving"] and ".ppd waypoint motion" in r["missing"] and r["verdict"] == "near"
    flex = ("<motion type='flexible'><locationengine type='waypoints'><data source='stk_report'/></locationengine>"
            "<orientationengine type='quaternions'/></motion>")
    doc = jsim()
    doc[0]["plugin_list"][2]["inputs"]["motion_filename"] = "./demo.motion"
    r = survey.survey(make(tmp_path, "Stk1", jsim=doc, extra_files={"demo.motion": flex}))
    assert {"STK report import", "quaternion orientation"} <= set(r["missing"]) and r["verdict"] == "far"


@pytest.mark.parametrize("make_kwargs, reason", [
    (dict(), "no .sim or .jsim"),
    (dict(sim="<simulation><scene"), "not XML"),
    (dict(jsim=None, extra_files={"demo.jsim": "[{not json"}), "not JSON"),
    (dict(sim=SIM, drop=("demo.scene",)), "not in the archive"),
], ids=["no_sim", "bad_xml", "bad_json", "missing_scene"])
def test_an_unparseable_demo_is_unparsed_with_a_reason(tmp_path, make_kwargs, reason):
    r = survey.survey(make(tmp_path, "Broken1", **make_kwargs))
    assert r["verdict"] == "unparsed" and reason in r["reason"]


def test_a_file_that_is_not_a_zip_is_unparsed(tmp_path):
    (tmp_path / "Junk1.zip").write_bytes(b"not a zip")
    r = survey.survey(tmp_path / "Junk1.zip")
    assert r["verdict"] == "unparsed" and "not a zip" in r["reason"]


def test_temp_solver_filenames_and_source_shapes_the_scene_copy_does_not_hold_are_placed(tmp_path):
    # Round 28, measured on Fireball1 (a TEMP_SOLVER FILENAME beside the .scene: searched in the working folder and the
    # scene's seven directory elements) and IESSources1 (SOURCE_SHAPE files beside the .scene: the working folder and
    # the srcdirectory): the job copies them into the working folder, so they are listed, not missing. A file the copy
    # holds under a directory element (DataDrivenTempSolver1's materials/temps/, odbdirectory $SCENE_DIR) needs nothing.
    scene = SCENE.replace("<odbdirectory>.</odbdirectory>", "<odbdirectory>$SCENE_DIR</odbdirectory><srcdirectory>"
                          "$SCENE_DIR/materials/sources</srcdirectory>")
    mat = ("MATERIAL_ENTRY {\n  SOURCE_SHAPE = a.ies\n  SOURCE_SHAPE = 10\n  TEMP_SOLVER {\n    FILENAME = t.txt\n"
           "    FILENAME = materials/temps/held.txt\n  }\n}\n")
    files = {"demo.scene": scene, "materials/demo.mat": mat, "a.ies": "ies", "t.txt": "txt",
             "materials/temps/held.txt": "txt"}
    r = survey.survey(make(tmp_path, "Searched1", jsim=jsim(), extra_files=files))
    assert r["missing"] == [] and r["verdict"] == "ready"
    assert sorted(r["working_folder"]) == ["a.ies", "t.txt"]


def test_a_demo_dirsig_refuses_as_authored_is_refused(tmp_path):
    # Measured by running it (the survey's reading cannot see it): Polarization2's own run and its layered and
    # pass-through runs fail in DIRSIG on the scene's spectral coverage. Its class says so, with what DIRSIG said.
    r = survey.survey(make(tmp_path, "Polarization2", jsim=jsim()))
    assert r["verdict"] == "refused" and r["missing"] == [] and "spectral coverage" in r["refused"]
    text = survey.render([r, survey.survey(make(tmp_path, "Ready1", jsim=jsim()))], "demos")
    assert "| `refused` | 1 |" in text and "| `ready` | 1 |" in text
    row = next(ln for ln in text.splitlines() if ln.startswith("| Polarization2 |"))
    assert "`refused`" in row and "spectral coverage" in row


def test_the_table_is_deterministic_and_carries_no_content(tmp_path):
    for name, kw in (("Legacy1", dict(sim=SIM)), ("Ready1", dict(jsim=jsim())), ("Far1", dict(jsim=jsim(), plat=platform("radar")))):
        make(tmp_path, name, **kw)
    (tmp_path / "Junk1.zip").write_bytes(b"x")
    text = survey.render(survey.survey_all(tmp_path), "demos")
    assert text == survey.render(survey.survey_all(tmp_path), "demos")
    assert SECRET not in text
    assert "| `ready` | 1 |" in text and "| `near` | 1 |" in text and "| `far` | 1 |" in text and "| `unparsed` | 1 |" in text
    rows = [ln for ln in text.splitlines() if ln.startswith("| ") and "`" in ln.split("|")[2]]
    assert [ln.split("|")[1].strip() for ln in rows if ln.split("|")[1].strip() in ("Ready1", "Legacy1", "Far1", "Junk1")] == \
        ["Ready1", "Legacy1", "Far1", "Junk1"]                             # sorted by verdict, then name


def test_a_findings_section_is_kept_when_regenerating(tmp_path):
    demos = tmp_path / "demos"
    demos.mkdir()
    make(demos, "Ready1", jsim=jsim())
    out = tmp_path / "coverage.md"
    out.write_text("old table\n\n" + survey.KEPT + "\n\n1. a finding\n")
    assert survey.main(["--demos", str(demos), "--out", str(out)]) == 0
    text = out.read_text()
    assert "old table" not in text and text.endswith(survey.KEPT + "\n\n1. a finding\n") and "Ready1" in text


@pytest.mark.skipif(not REAL.is_dir(), reason="the DIRSIG install's demo archives (external/dirsig/demos/zips) are not linked")
def test_the_real_install_survey_matches_the_committed_table():
    records = survey.survey_all(REAL)
    assert len(records) == len(list(REAL.glob("*.zip"))) and records
    committed = (ROOT / "docs" / "DIRSIG_demo_coverage.md").read_text()
    fresh = survey.render(records, "external/dirsig/demos/zips")
    kept = committed[committed.index(survey.KEPT):] if survey.KEPT in committed else ""
    assert committed == fresh + ("\n" + kept if kept else ""), "run python scripts/survey_demos.py --out docs/DIRSIG_demo_coverage.md"


def test_check_reports_a_stale_table(tmp_path):
    demos = tmp_path / "demos"
    demos.mkdir()
    make(demos, "Ready1", jsim=jsim())
    out = tmp_path / "coverage.md"
    assert survey.main(["--demos", str(demos), "--out", str(out)]) == 0
    assert survey.main(["--demos", str(demos), "--out", str(out), "--check"]) == 0
    out.write_text(out.read_text() + "\n" + survey.KEPT + "\n\n1. kept\n")
    assert survey.main(["--demos", str(demos), "--out", str(out), "--check"]) == 0      # the kept section is not stale
    make(demos, "Near1", jsim=jsim(weather=None))
    assert survey.main(["--demos", str(demos), "--out", str(out), "--check"]) == 1
