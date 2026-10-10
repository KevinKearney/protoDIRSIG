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
    assert r["missing"] == ["BasicAtmosphere .atm (simpleradiativetransfer, uniformweather)"]
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
    (dict(jsim=jsim(), plat=platform(extra="<distortion/>")), "near", "lens distortion"),
    (dict(jsim=jsim(atmosphere="FourCurveAtmosphere", weather="NsrdbWeather")), "far", "NsrdbWeather"),
], ids=["four_curve", "no_weather", "fixed_ephemeris", "lidar", "distortion", "two_features"])
def test_features_and_verdicts(tmp_path, kwargs, verdict, feature):
    r = survey.survey(make(tmp_path, "Case1", **kwargs))
    assert r["verdict"] == verdict and feature in r["missing"]


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
