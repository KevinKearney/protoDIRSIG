"""`engine.atmosphere` of plugin `basic` with `uniform` (proposed): a BasicAtmosphere `.atm` written from stated values.

The written file parsed back (`basic_atmosphere.read_atm`), the refusals (no weather values, a fixed ephemeris beside an
ephemeris plugin, a library weather file, `uniform` beside `file`), the run id (changed for a run that states it,
unchanged for every committed one: tests/test_id_snapshot.py), a dry run through the adapter, and one 16 x 16 render.
The renders use the library's Tahoe scene: no demo scene the library places renders through the layered form yet (the
placed PointCollectors2 scene names files beside its `.scene`, which the scene reference does not link). Specs are
edits of `manifold_run_specs/synthetic_vis.yaml` written to tmp_path; the library is read only.
"""
import copy
from pathlib import Path

import lxml.etree as et
import pytest
import yaml

from backend_conformance import wait_for
from manifold.core.identity import run_id
from manifold.core.run_spec import RunSpecError
from manifold.engines.dirsig.basic_atmosphere import WEATHER_DIR, read_atm, write_atm
from manifold.engines.dirsig.run_spec import resolve_run
from manifold.engines.dirsig.simulation import schema_errors
from test_simulation import CONFIG_REPO, needs_dirsig

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "manifold_run_specs" / "synthetic_vis.yaml"
SENSORS = ROOT / "manifold_sensors"
UNIFORM = {"radiative_transfer": {"hemisphere_irradiance": 1, "sky_fraction": 0.2},
           "weather": {"install_file": "mls.wth"},
           "fixed_ephemeris": {"units": "radians", "solar_zenith": 0.6, "solar_azimuth": 3.0}}
PLACED_ATM = CONFIG_REPO / "demos" / "PointCollectors2" / "uniform.atm"


def uniform_spec(uniform=UNIFORM, roi=16, keep=()):
    """synthetic_vis.yaml with a uniform atmosphere: no library weather and, with a fixed ephemeris, no ephemeris
    plugin (members named in `keep` stay as they were)."""
    spec = yaml.safe_load(BASE.read_text())
    eng = spec["engine"]
    eng["atmosphere"] = {"plugin": "basic", "uniform": copy.deepcopy(uniform)}
    for member in ("weather", "ephemeris"):
        if member not in keep:
            eng.pop(member, None)
    if "fixed_ephemeris" not in uniform and "ephemeris" not in keep:
        eng["ephemeris"] = {"plugin": "spice"}
    spec["descriptor"]["settings"][0]["roi"] = {"Width": roi, "Height": roi, "OffsetX": None, "OffsetY": None}
    return spec


def _write(tmp_path, spec, name="uniform.yaml"):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    return path


def _resolve(tmp_path, spec):
    return resolve_run(spec, _write(tmp_path, spec), CONFIG_REPO, SENSORS)


# --- the written file -------------------------------------------------------------------------------------------------

def test_the_written_atm_parses_back_to_the_stated_values(tmp_path):
    path = write_atm(UNIFORM, tmp_path / "u.atm")
    assert read_atm(path) == UNIFORM
    root = et.parse(str(path)).getroot()
    assert [c.tag for c in root] == ["uniformweather", "ephemeris", "uniformradiativetransfer"]
    assert root.findtext("uniformweather/classicdata/filename") == f"{WEATHER_DIR}/mls.wth"
    assert root.find("ephemeris/fixed").get("units") == "radians"
    assert root.findtext("uniformradiativetransfer/hemisphereirradiance") == "1"        # an int stays an int
    assert root.findtext("uniformradiativetransfer/skyfraction") == "0.2"


def test_without_a_fixed_ephemeris_no_ephemeris_element_is_written(tmp_path):
    values = {k: v for k, v in UNIFORM.items() if k != "fixed_ephemeris"}
    path = write_atm(values, tmp_path / "u.atm")
    assert et.parse(str(path)).getroot().find("ephemeris") is None and read_atm(path) == values


@pytest.mark.skipif(not PLACED_ATM.is_file(), reason="demo assets not placed (scripts/bootstrap.py assets)")
def test_a_demo_atm_read_and_written_again_states_the_same_values(tmp_path):
    values = read_atm(PLACED_ATM)                    # the placed demo's file; its values are not written into the repo
    assert read_atm(write_atm(values, tmp_path / "again.atm")) == values


# --- schema and resolution --------------------------------------------------------------------------------------------

def test_a_uniform_spec_is_schema_valid_and_resolves(tmp_path):
    spec = uniform_spec()
    assert schema_errors(spec) == []
    r = _resolve(tmp_path, spec)
    assert r.uniform_atmosphere == UNIFORM and r.atmosphere_db is None and r.weather is None
    assert r.ephemeris is None and r.ephemeris_plugin() is None
    no_sun = uniform_spec({k: v for k, v in UNIFORM.items() if k != "fixed_ephemeris"})
    assert schema_errors(no_sun) == [] and _resolve(tmp_path, no_sun).ephemeris == "spice"


def test_a_uniform_atmosphere_without_weather_values_is_refused_with_a_reason(tmp_path):
    spec = uniform_spec({k: v for k, v in UNIFORM.items() if k != "weather"})
    assert schema_errors(spec) == []                 # the rule is the loader's, with its reason
    with pytest.raises(RunSpecError) as e:
        _resolve(tmp_path, spec)
    assert e.value.pointer == "/engine/atmosphere/uniform"
    assert "no weather values" in str(e.value) and "Expected a <filename> in uniform weather" in str(e.value)


@pytest.mark.parametrize("edit, pointer, words", [
    (lambda s: s["engine"].update(ephemeris={"plugin": "spice"}), "/engine/ephemeris", "fixed ephemeris"),
    (lambda s: s["engine"].update(weather=yaml.safe_load(BASE.read_text())["engine"]["weather"]),
     "/engine/weather/source", "carries its weather in the .atm"),
])
def test_conflicting_members_are_refused(tmp_path, edit, pointer, words):
    spec = uniform_spec()
    edit(spec)
    with pytest.raises(RunSpecError) as e:
        _resolve(tmp_path, spec)
    assert e.value.pointer == pointer and words in str(e.value)


def test_the_schema_refuses_uniform_beside_a_file_and_out_of_range_values():
    spec = uniform_spec()
    spec["engine"]["atmosphere"]["file"] = {"name": "x.atm", "content_hash": "sha256:<hash>"}
    assert schema_errors(spec)
    for bad in ({"sky_fraction": 1.5}, {"hemisphere_irradiance": -1}):
        values = copy.deepcopy(UNIFORM)
        values["radiative_transfer"].update(bad)
        assert schema_errors(uniform_spec(values))
    values = copy.deepcopy(UNIFORM)
    values["weather"]["install_file"] = "../escape.wth"
    assert schema_errors(uniform_spec(values))


def test_basic_without_uniform_is_still_refused(tmp_path):
    spec = uniform_spec()
    spec["engine"]["atmosphere"] = {"plugin": "basic", "file": {"name": "x.atm", "content_hash": "sha256:<hash>"}}
    spec["engine"]["ephemeris"] = {"plugin": "spice"}
    with pytest.raises(RunSpecError, match="'basic' with a file"):
        _resolve(tmp_path, spec)


def test_the_run_id_covers_the_stated_values():
    a, b = uniform_spec(), uniform_spec()
    b["engine"]["atmosphere"]["uniform"]["radiative_transfer"]["sky_fraction"] = 0.3
    base = yaml.safe_load(BASE.read_text())
    ids = {run_id(s, SENSORS) for s in (a, b, base)}
    assert len(ids) == 3


# --- through the adapter and DIRSIG -----------------------------------------------------------------------------------

def _backend(tmp_path):
    from manifold.sim.backend import LocalBackend
    return LocalBackend(tmp_path / "work", CONFIG_REPO, sensor_library=SENSORS)


@needs_dirsig
def test_dry_run_through_the_adapter(tmp_path):
    run = _backend(tmp_path).validate(str(_write(tmp_path, uniform_spec())), "dry_run")["runs"][0]
    assert run["valid"] and run["engine_checked"], run["checks"]
    assert run["checks"][-1] == {"check": "dry_run", "passed": True, "errors": []}


@needs_dirsig
def test_a_16_by_16_render_through_the_adapter(tmp_path):
    backend = _backend(tmp_path)
    status = wait_for(backend, backend.submit_run(str(_write(tmp_path, uniform_spec())))["run_id"],
                      ("rendered", "failed", "cancelled"), timeout=300)
    assert status["state"] == "rendered", status
    names = [a["name"] for a in backend.list_artifacts(status["run_id"])["artifacts"]]
    assert any(n.endswith(".img") for n in names)
    run_dir = next((tmp_path / "work").rglob("input/uniform.atm"))     # the job's written .atm, as stated
    assert read_atm(run_dir) == UNIFORM
    jsim = next(run_dir.parent.glob("*.jsim")).read_text()
    assert "BasicAtmosphere" in jsim and "SpiceEphemeris" not in jsim and "ThermWeather" not in jsim
