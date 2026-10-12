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


def test_a_geometry_list_found_only_from_the_working_folder_is_missing(tmp_path):
    # Named by a bare name, beside the scene and not in its gdbdirectory: DIRSIG searches the working folder.
    scene = SCENE.replace("geometry/demo.glist", "demo.glist").replace(
        "<odbdirectory>.</odbdirectory>", "<gdbdirectory>$SCENE_DIR/geometry</gdbdirectory>")
    r = survey.survey(make(tmp_path, "Beside1", jsim=jsim(), extra_files={"demo.scene": scene, "demo.glist": GLIST},
                           drop=("geometry/demo.glist",)))
    assert r["missing"] == ["geometry lists DIRSIG finds only from the working folder"] and r["verdict"] == "near"
    found = scene.replace("$SCENE_DIR/geometry</gdbdirectory>", "$SCENE_DIR</gdbdirectory>")
    r = survey.survey(make(tmp_path, "Beside2", jsim=jsim(), extra_files={"demo.scene": found, "demo.glist": GLIST},
                           drop=("geometry/demo.glist",)))
    assert r["missing"] == [] and r["verdict"] == "ready"


def test_files_the_platform_names_are_missing(tmp_path):
    plat = platform(extra="<pixelmap><filename format='hdf'>pixels.hdf</filename></pixelmap><x><filename/></x>")
    r = survey.survey(make(tmp_path, "PlatFile1", jsim=jsim(), plat=plat, extra_files={"pixels.hdf": "hdf"}))
    assert r["missing"] == ["files the platform names"] and r["verdict"] == "near"
    r = survey.survey(make(tmp_path, "PlatFile2", jsim=jsim(), plat=plat))          # named but not shipped: not counted
    assert r["missing"] == [] and r["verdict"] == "ready"


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
