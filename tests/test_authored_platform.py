"""`engine.platform.as_authored` (proposed): a platform file used as authored, copied into the job byte for byte.

The platform here is written by the test (a DIRSIG `.platform` of the shape a demo's has: radiance in watts/cm2, a
rectangular channel, a 16 x 16 array), placed in a temporary copy of the library beside the Tahoe scene, with a uniform
atmosphere, so the render is 16 x 16 and no demo file is needed. Checked: resolution (the file is not rendered from the sensor-spec, and the
template-only members are refused), the library-file check, the run id (the platform's content hash is in it, and a
spec without the member keeps its id: tests/test_id_snapshot.py), the dry run through the adapter, and a render whose
job platform is byte-identical to the library file and whose image is in the authored units.
"""
import shutil
from pathlib import Path

import pytest
import yaml

from backend_conformance import wait_for
from manifold.core.identity import run_id
from manifold.core.run_spec import RunSpecError
from manifold.core.spectral import sha256_file
from manifold.engines.dirsig.run_spec import authored_platform_problems, check_library_files, resolve_run
from manifold.engines.dirsig.simulation import schema_errors
from test_simulation import CONFIG_REPO, needs_dirsig
from test_uniform_atmosphere import UNIFORM

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "manifold_run_specs" / "synthetic_vis.yaml"
SENSORS = ROOT / "manifold_sensors"
PLATFORM = """<platform>
  <clocktable/>
  <attachment>
    <affinetransform/>
    <mount type="static" name="Static">
      <data rotationorder="xyz" angularunits="radians"><xrotation>0</xrotation><yrotation>0</yrotation><zrotation>0</zrotation></data>
      <attachment>
        <affinetransform/>
        <instrument type="generic" name="Authored">
          <properties><focallength>5000</focallength></properties>
          <focalplane enabled="true" name="FPA">
            <capturemethod type="simple" name="Simple">
              <samplestrategy type="central"/>
              <imagefile areaunits="cm2" fluxunits="watts">
                <basename>authored</basename><extension>img</extension><schedule>simulation</schedule>
              </imagefile>
              <spectralresponse>
                <bandpass spectralunits="microns"><minimum>0.4</minimum><maximum>0.8</maximum><delta>0.05</delta></bandpass>
                <channellist>
                  <channel normalize="true" bias="0" shape="rectangular" name="Pan" gain="1">
                    <center>0.600</center><width>0.400</width><polarizer type="none"/><dataoutput type="total"/>
                  </channel>
                </channellist>
              </spectralresponse>
            </capturemethod>
            <detectorarray spatialunits="microns">
              <clock type="independent" temporalunits="hertz"><rate>20</rate><offset>0</offset></clock>
              <xelementcount>16</xelementcount><yelementcount>16</yelementcount>
              <xelementsize>20</xelementsize><yelementsize>20</yelementsize>
              <xelementspacing>20</xelementspacing><yelementspacing>20</yelementspacing>
              <xarrayoffset>0</xarrayoffset><yarrayoffset>0</yarrayoffset>
              <xflipaxis>0</xflipaxis><yflipaxis>1</yflipaxis>
            </detectorarray>
          </focalplane>
        </instrument>
      </attachment>
      <rotationdeviates/>
    </mount>
  </attachment>
</platform>
"""
REL = "platforms/Authored/authored.platform"


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    """A copy of the library's scenes plus the authored platform (once per module)."""
    lib = tmp_path_factory.mktemp("authored") / "config_repo"
    shutil.copytree(CONFIG_REPO / "scenes", lib / "scenes", symlinks=True)
    (lib / REL).parent.mkdir(parents=True)
    (lib / REL).write_text(PLATFORM)
    return lib


def authored_spec(lib, **extra):
    spec = yaml.safe_load(BASE.read_text())
    plat = spec["engine"]["platform"]
    for member in ("integration_samples", "channel_response"):
        plat.pop(member, None)
    plat["ref"] = {"name": REL, "content_hash": sha256_file(lib / REL)}
    plat["as_authored"] = True
    plat.update(extra)
    # A uniform atmosphere (test_uniform_atmosphere.py), as a demo's: the authored bandpass is not in the library's
    # NewAtmosphere database, which holds only the states of the templates' bandpass.
    spec["engine"]["atmosphere"] = {"plugin": "basic", "uniform": UNIFORM}
    for member in ("weather", "ephemeris"):
        spec["engine"].pop(member)
    return spec


def _write(tmp_path, spec):
    path = tmp_path / "authored.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    return path


def test_an_authored_platform_resolves_and_passes_the_library_check(tmp_path, library):
    spec = authored_spec(library)
    assert schema_errors(spec) == []
    r = resolve_run(spec, _write(tmp_path, spec), library, SENSORS)
    assert r.platform_as_authored and r.integration_samples is None and r.platform == library / REL
    assert check_library_files(spec, r) == []


@pytest.mark.parametrize("member, value", [("integration_samples", 10), ("channel_response", "native")])
def test_template_only_members_are_refused(tmp_path, library, member, value):
    spec = authored_spec(library, **{member: value})
    with pytest.raises(RunSpecError) as e:
        resolve_run(spec, _write(tmp_path, spec), library, SENSORS)
    assert e.value.pointer == f"/engine/platform/{member}" and "as authored" in str(e.value)


def test_a_file_that_is_not_a_platform_is_a_library_problem(tmp_path, library):
    assert authored_platform_problems(library / REL) == []
    for text, words in (("<tasklist/>\n", "expected <platform>"), ("<platform><nope/></platform>\n", "no <focalplane>"),
                        ("<platform>\n", "does not parse")):
        (tmp_path / "x.platform").write_text(text)
        assert words in authored_platform_problems(tmp_path / "x.platform")[0]


def test_the_platform_hash_is_in_the_run_id(library):
    a = authored_spec(library)
    b = authored_spec(library)
    b["engine"]["platform"]["ref"]["content_hash"] = "sha256:" + "0" * 64
    assert run_id(a, SENSORS) != run_id(b, SENSORS) != run_id(yaml.safe_load(BASE.read_text()), SENSORS)


def _backend(tmp_path, library):
    from manifold.sim.backend import LocalBackend
    return LocalBackend(tmp_path / "work", library, sensor_library=SENSORS)


@needs_dirsig
def test_dry_run_through_the_adapter(tmp_path, library):
    run = _backend(tmp_path, library).validate(str(_write(tmp_path, authored_spec(library))), "dry_run")["runs"][0]
    assert run["valid"] and run["engine_checked"], run["checks"]


@needs_dirsig
def test_a_16_by_16_render_uses_the_platform_as_authored(tmp_path, library):
    backend = _backend(tmp_path, library)
    status = wait_for(backend, backend.submit_run(str(_write(tmp_path, authored_spec(library))))["run_id"],
                      ("rendered", "failed", "cancelled"), timeout=300)
    assert status["state"] == "rendered", status
    job_platform = next((tmp_path / "work").rglob("input/" + REL))
    assert job_platform.read_bytes() == (library / REL).read_bytes()
    names = [a["name"] for a in backend.list_artifacts(status["run_id"])["artifacts"]]
    header = next((tmp_path / "work").rglob("authored*.hdr")).read_text()
    assert any(n.startswith("authored") and n.endswith(".img") for n in names)
    assert "samples = 16" in header and "lines = 16" in header
