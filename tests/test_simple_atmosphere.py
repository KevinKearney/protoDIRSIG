"""`engine.atmosphere` of plugin `basic` with `simple` (proposed): a BasicAtmosphere `.atm` with DIRSIG's SimpleAtm,
written from stated values.

The written file parsed back (`basic_atmosphere.read_simple_atm`), a demo's simple `.atm` read and written again (from
the installation's archive, into tmp_path; no demo value enters the repository), the refusals (no weather values, a
fixed ephemeris beside an ephemeris plugin, a library weather file, `simple` beside `uniform` or a file), the run id, a
dry run through the adapter and one 16 x 16 render. Specs are edits of `manifold_run_specs/synthetic_vis.yaml` written
to tmp_path (as in tests/test_uniform_atmosphere.py); the library is read only.
"""
import copy
import zipfile

import lxml.etree as et
import pytest
import yaml

from backend_conformance import wait_for
from manifold.core.identity import run_id
from manifold.core.run_spec import RunSpecError
from manifold.engines.dirsig.basic_atmosphere import WEATHER_DIR, read_atm, read_simple_atm, write_simple_atm
from manifold.engines.dirsig.run_spec import resolve_run
from manifold.engines.dirsig.simulation import schema_errors
from test_simulation import CONFIG_REPO, needs_dirsig
from test_uniform_atmosphere import BASE, ROOT, SENSORS, UNIFORM

SIMPLE = {"radiative_transfer": {"apparent_sky_temperature": 250},
          "weather": {"install_file": "mls.wth"},
          "fixed_ephemeris": {"units": "radians", "solar_zenith": 0.6, "solar_azimuth": 3.0}}
ZIPS = ROOT / "external" / "dirsig" / "demos" / "zips"


def simple_spec(simple=SIMPLE, roi=16, keep=()):
    """synthetic_vis.yaml with a simple atmosphere: no library weather and, with a fixed ephemeris, no ephemeris
    plugin (members named in `keep` stay as they were)."""
    spec = yaml.safe_load(BASE.read_text())
    eng = spec["engine"]
    eng["atmosphere"] = {"plugin": "basic", "simple": copy.deepcopy(simple)}
    for member in ("weather", "ephemeris"):
        if member not in keep:
            eng.pop(member, None)
    if "fixed_ephemeris" not in simple and "ephemeris" not in keep:
        eng["ephemeris"] = {"plugin": "spice"}
    spec["descriptor"]["settings"][0]["roi"] = {"Width": roi, "Height": roi, "OffsetX": None, "OffsetY": None}
    return spec


def _write(tmp_path, spec, name="simple.yaml"):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    return path


def _resolve(tmp_path, spec):
    return resolve_run(spec, _write(tmp_path, spec), CONFIG_REPO, SENSORS)


# --- the written file -------------------------------------------------------------------------------------------------

def test_the_written_atm_parses_back_to_the_stated_values(tmp_path):
    path = write_simple_atm(SIMPLE, tmp_path / "s.atm")
    assert read_simple_atm(path) == SIMPLE
    root = et.parse(str(path)).getroot()
    assert [c.tag for c in root] == ["uniformweather", "ephemeris", "simpleradiativetransfer"]
    assert root.findtext("uniformweather/classicdata/filename") == f"{WEATHER_DIR}/mls.wth"
    assert root.findtext("simpleradiativetransfer/apparentskytemperature") == "250"     # an int stays an int
    with pytest.raises(ValueError, match="uniformradiativetransfer"):
        read_atm(path)                                                                  # the forms do not mix


def test_without_a_fixed_ephemeris_no_ephemeris_element_is_written(tmp_path):
    values = {k: v for k, v in SIMPLE.items() if k != "fixed_ephemeris"}
    path = write_simple_atm(values, tmp_path / "s.atm")
    assert et.parse(str(path)).getroot().find("ephemeris") is None and read_simple_atm(path) == values


def test_a_simple_atm_with_values_simple_does_not_carry_is_refused(tmp_path):
    path = tmp_path / "x.atm"
    path.write_text(f"<atmosphericconditions><uniformweather><classicdata><filename>{WEATHER_DIR}/mls.wth</filename>"
                    "</classicdata></uniformweather><simpleradiativetransfer><apparentskytemperature>250"
                    "</apparentskytemperature><other>1</other></simpleradiativetransfer></atmosphericconditions>")
    with pytest.raises(ValueError, match="other"):
        read_simple_atm(path)


@pytest.mark.skipif(not (ZIPS / "BumpMap2.zip").is_file(), reason="DIRSIG demo archives not linked (external/dirsig)")
def test_a_demo_atm_read_and_written_again_states_the_same_values(tmp_path):
    with zipfile.ZipFile(ZIPS / "BumpMap2.zip") as z:                 # a simple-radiative-transfer demo .atm
        name = next(n for n in z.namelist() if n.endswith(".atm"))
        (tmp_path / "demo.atm").write_bytes(z.read(name))              # tmp_path only; no demo value is committed
    values = read_simple_atm(tmp_path / "demo.atm")
    assert read_simple_atm(write_simple_atm(values, tmp_path / "again.atm")) == values


# --- schema and resolution --------------------------------------------------------------------------------------------

def test_a_simple_spec_is_schema_valid_and_resolves(tmp_path):
    spec = simple_spec()
    assert schema_errors(spec) == []
    r = _resolve(tmp_path, spec)
    assert r.simple_atmosphere == SIMPLE and r.uniform_atmosphere is None
    assert r.atmosphere_db is None and r.weather is None
    assert r.ephemeris is None and r.ephemeris_plugin() is None
    no_sun = simple_spec({k: v for k, v in SIMPLE.items() if k != "fixed_ephemeris"})
    assert schema_errors(no_sun) == [] and _resolve(tmp_path, no_sun).ephemeris == "spice"


def test_a_simple_atmosphere_without_weather_values_is_refused_with_a_reason(tmp_path):
    spec = simple_spec({k: v for k, v in SIMPLE.items() if k != "weather"})
    assert schema_errors(spec) == []                 # the rule is the loader's, with its reason
    with pytest.raises(RunSpecError) as e:
        _resolve(tmp_path, spec)
    assert e.value.pointer == "/engine/atmosphere/simple"
    assert "no weather values" in str(e.value) and "Expected a <filename> in uniform weather" in str(e.value)


@pytest.mark.parametrize("edit, pointer, words", [
    (lambda s: s["engine"].update(ephemeris={"plugin": "spice"}), "/engine/ephemeris", "simple.fixed_ephemeris"),
    (lambda s: s["engine"].update(weather=yaml.safe_load(BASE.read_text())["engine"]["weather"]),
     "/engine/weather/source", "a simple atmosphere carries its weather in the .atm"),
    (lambda s: s["engine"]["atmosphere"].update(uniform=copy.deepcopy(UNIFORM)), "/engine/atmosphere/simple",
     "both `uniform` and `simple`"),
])
def test_conflicting_members_are_refused(tmp_path, edit, pointer, words):
    spec = simple_spec()
    edit(spec)
    with pytest.raises(RunSpecError) as e:
        _resolve(tmp_path, spec)
    assert e.value.pointer == pointer and words in str(e.value)


def test_the_schema_refuses_simple_beside_uniform_or_a_file_and_bad_values():
    spec = simple_spec()
    spec["engine"]["atmosphere"]["uniform"] = copy.deepcopy(UNIFORM)
    assert schema_errors(spec)
    spec = simple_spec()
    spec["engine"]["atmosphere"]["file"] = {"name": "x.atm", "content_hash": "sha256:<hash>"}
    assert schema_errors(spec)
    for bad in ({"apparent_sky_temperature": 0}, {"apparent_sky_temperature": -5}, {"sky_fraction": 0.2}):
        values = copy.deepcopy(SIMPLE)
        values["radiative_transfer"].update(bad)
        assert schema_errors(simple_spec(values))
    values = copy.deepcopy(SIMPLE)
    values["radiative_transfer"] = {"hemisphere_irradiance": 1, "sky_fraction": 0.2}     # the uniform form's members
    assert schema_errors(simple_spec(values))


def test_the_run_id_covers_the_stated_values_and_the_form():
    a, b = simple_spec(), simple_spec()
    b["engine"]["atmosphere"]["simple"]["radiative_transfer"]["apparent_sky_temperature"] = 260
    base = yaml.safe_load(BASE.read_text())
    ids = {run_id(s, SENSORS) for s in (a, b, base)}
    assert len(ids) == 3


# --- through the adapter and DIRSIG -----------------------------------------------------------------------------------

def _backend(tmp_path):
    from manifold.sim.backend import LocalBackend
    return LocalBackend(tmp_path / "work", CONFIG_REPO, sensor_library=SENSORS)


@needs_dirsig
def test_dry_run_through_the_adapter(tmp_path):
    run = _backend(tmp_path).validate(str(_write(tmp_path, simple_spec())), "dry_run")["runs"][0]
    assert run["valid"] and run["engine_checked"], run["checks"]
    assert run["checks"][-1] == {"check": "dry_run", "passed": True, "errors": []}


@needs_dirsig
def test_a_16_by_16_render_through_the_adapter(tmp_path):
    backend = _backend(tmp_path)
    status = wait_for(backend, backend.submit_run(str(_write(tmp_path, simple_spec())))["run_id"],
                      ("rendered", "failed", "cancelled"), timeout=300)
    assert status["state"] == "rendered", status
    names = [a["name"] for a in backend.list_artifacts(status["run_id"])["artifacts"]]
    assert any(n.endswith(".img") for n in names)
    atm = next((tmp_path / "work").rglob("input/simple.atm"))         # the job's written .atm, as stated
    assert read_simple_atm(atm) == SIMPLE
    jsim = next(atm.parent.glob("*.jsim")).read_text()
    assert "BasicAtmosphere" in jsim and "simple.atm" in jsim
    assert "SpiceEphemeris" not in jsim and "ThermWeather" not in jsim
