"""Resolution failures named by layer file and field (`RunSpecError.pointer`, `problems.from_resolution_error`), and the
`ProblemError` exceptions (protodirsig.errors).

The temporary engine-asset library links `scenes/` and `atmosphere/` back to the real `manifold_config_repo` (read
only; nothing large is copied) and copies the small `platforms/`, `weather/` and `orbit/` folders, so a referenced file
can be deleted or edited. Resolution fails before any engine runs, so no DIRSIG is needed.
"""
import json
import shutil
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from protodirsig import problems
from protodirsig.compose import compose_sweep, dump
from protodirsig.errors import AdmissionError, InvalidRequestError, NotFoundError, ProblemError
from protodirsig.registry import LocalRegistry
from protodirsig.run_spec import RunSpecError, load_run_spec, resolve_run

ROOT = Path(__file__).resolve().parents[1]
CONFIG_REPO = ROOT / "manifold_config_repo"
RUN_SPECS = ROOT / "manifold_run_specs"
PROBLEM = Draft202012Validator(json.loads((ROOT / "api" / "schemas" / "problem.schema.json").read_text()))
PROFILE = "engine_profiles/tahoe_static_pose.yaml"

needs_config_repo = pytest.mark.skipif(not (CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene").is_file(),
                                       reason="manifold_config_repo not present")


def conforms(problem):
    errors = [e.message for e in PROBLEM.iter_errors(problem)]
    assert errors == [], errors
    return problem


@pytest.fixture
def library(tmp_path):
    """(layer root, engine-asset library): small copies plus links to the real scene and atmosphere folders."""
    root = tmp_path / "manifold_run_specs"
    for d in ("recipes", "scenarios", "engine_profiles"):
        shutil.copytree(RUN_SPECS / d, root / d)
    shutil.copytree(ROOT / "manifold_sensors", tmp_path / "manifold_sensors")
    lib = tmp_path / "manifold_config_repo"
    lib.mkdir()
    for p in CONFIG_REPO.iterdir():
        if p.name in ("scenes", "atmosphere"):
            (lib / p.name).symlink_to(p, target_is_directory=True)
        elif p.is_dir():
            shutil.copytree(p, lib / p.name)
    return root, lib


def _ref(root, rel, key):
    """The ref `{name, content_hash}` at dotted `key` under `engine` in a layer file (parsed)."""
    node = yaml.safe_load((root / rel).read_text())["engine"]
    for k in key.split("."):
        node = node[k]
    return node


def _submit(root, lib, tmp_path, recipe="auror_ref"):
    r = LocalRegistry().submit_recipe(root / "recipes" / f"{recipe}.yaml", lib, tmp_path / "work")
    assert not r.accepted and r.checks["schema"] and not r.checks["resolution"], r.reasons
    return conforms(r.problem)


def _delete_weather(root, lib):
    (lib / _ref(root, PROFILE, "weather.file")["name"]).unlink()
    return "engine.weather.file.name"


def _edit_platform_byte(root, lib):
    path = lib / _ref(root, PROFILE, "platform.ref")["name"]
    data = bytearray(path.read_bytes())
    data[-2] ^= 1
    path.write_bytes(bytes(data))
    return "engine.platform.ref.content_hash"


def _edit_layer_hash(root, lib):
    path = root / PROFILE
    want = _ref(root, PROFILE, "atmosphere.database.ref")["content_hash"]
    path.write_text(path.read_text().replace(want, "sha256:" + "1" * 64))
    return "engine.atmosphere.database.ref.content_hash"


@needs_config_repo
@pytest.mark.parametrize("edit", [_delete_weather, _edit_platform_byte, _edit_layer_hash],
                         ids=["deleted_file", "changed_byte", "changed_content_hash"])
def test_a_resolution_failure_names_the_layer_file_and_field(library, tmp_path, edit):
    root, lib = library
    field = edit(root, lib)
    p = _submit(root, lib, tmp_path)
    assert (p["type"], p["status"], p["layer"], p["field"]) == ("urn:protodirsig:problem:admission", 422, PROFILE, field)
    assert "Resolution check failed" in p["detail"]


@needs_config_repo
def test_an_orbit_file_failure_names_the_pass_profile(library, tmp_path):
    root, lib = library
    (lib / _ref(root, "engine_profiles/tahoe_leo_pass.yaml", "motion.orbit.tle")["name"]).unlink()
    p = _submit(root, lib, tmp_path, "leo_pass_tahoe")
    assert (p["layer"], p["field"]) == ("engine_profiles/tahoe_leo_pass.yaml", "engine.motion.orbit.tle.name")


@needs_config_repo
def test_from_resolution_error_locates_the_pointer(library):
    root, lib = library
    _delete_weather(root, lib)
    recipe = root / "recipes" / "auror_ref.yaml"
    sweep = compose_sweep(recipe)
    (name,) = sweep.runs
    spec = sweep.runs[name]
    with pytest.raises(RunSpecError) as e:
        resolve_run(spec, recipe, lib, root.parent / "manifold_sensors")
    assert e.value.pointer == "/engine/weather/file/name"
    p = conforms(problems.from_resolution_error(e.value, spec, sweep.sources[name], recipe, "/runs"))
    assert (p["layer"], p["field"], p["instance"]) == (PROFILE, "engine.weather.file.name", "/runs")
    unattributed = conforms(problems.from_resolution_error(e.value, spec, None))
    assert (unattributed["layer"], unattributed["field"]) == (None, None)


@needs_config_repo
def test_a_spec_submitted_directly_has_no_layer(library, tmp_path):
    """No composition record: the failure is reported, but no layer file is named."""
    root, lib = library
    _delete_weather(root, lib)
    sweep = compose_sweep(root / "recipes" / "auror_ref.yaml")
    (name,) = sweep.runs
    path = tmp_path / "spec.yaml"
    path.write_text(dump(sweep.runs[name], "recipes/auror_ref.yaml"))
    r = LocalRegistry().submit(path, lib, tmp_path / "work", root.parent / "manifold_sensors")
    assert not r.accepted and not r.checks["resolution"]
    p = conforms(r.problem)
    assert (p["layer"], p["field"]) == (None, None) and "weather" in p["detail"]


@needs_config_repo
@pytest.mark.parametrize("key, pointer", [("scenes", "/engine/scenes/0/ref/name"),
                                          ("platform", "/engine/platform/ref/name"),
                                          ("database", "/engine/atmosphere/database/ref/name"),
                                          ("weather", "/engine/weather/file/name")])
def test_each_library_ref_sets_its_pointer(key, pointer):
    spec = load_run_spec(RUN_SPECS / "auror_ref.yaml")
    eng = spec["engine"]
    ref = {"scenes": eng["scenes"][0]["ref"], "platform": eng["platform"]["ref"],
           "database": eng["atmosphere"]["database"]["ref"], "weather": eng["weather"]["file"]}[key]
    ref["name"] = ref["name"].rsplit("/", 1)[0] + "/no_such_file"
    with pytest.raises(RunSpecError) as e:
        resolve_run(spec, RUN_SPECS / "auror_ref.yaml", CONFIG_REPO)
    assert e.value.pointer == pointer


def test_a_missing_sensor_sets_the_sensor_ref_pointer(tmp_path):
    spec = load_run_spec(RUN_SPECS / "auror_ref.yaml")
    spec["descriptor"]["sensor"]["ref"]["name"] = "no_such_sensor.yaml"
    with pytest.raises(RunSpecError) as e:
        resolve_run(spec, RUN_SPECS / "auror_ref.yaml", CONFIG_REPO)
    assert e.value.pointer == "/descriptor/sensor/ref/name"


def test_run_spec_error_without_a_pointer_still_works():
    e = RunSpecError("plain message")
    assert str(e) == "plain message" and e.pointer is None and isinstance(e, ValueError)
    assert RunSpecError("m", pointer="/engine/x").pointer == "/engine/x"


def test_problem_errors_carry_conforming_problems():
    compose_problem = problems.from_compose_error(type("E", (Exception,), {"layer": "recipes/r.yaml", "field": "x"})("bad"))
    cases = [AdmissionError(compose_problem), NotFoundError("run", "0" * 64, "/runs/" + "0" * 64),
             InvalidRequestError("a sweep recipe; use submit_sweep"), InvalidRequestError(compose_problem),
             ProblemError(problems.execution_failed("0" * 64, "r", "dirsig5 exited 1"))]
    for err in cases:
        conforms(err.problem)
        assert str(err) == err.problem["detail"] and err.status == err.problem["status"]
    assert (cases[1].status, cases[1].type) == (404, "urn:protodirsig:problem:not-found")
    assert cases[2].type == "urn:protodirsig:problem:invalid-request" and cases[2].status == 422
    assert cases[4].status == 500 and cases[4].type == "urn:protodirsig:problem:execution"
    assert all(isinstance(e, ProblemError) for e in cases)
    with pytest.raises(TypeError):
        ProblemError({"detail": "no type"})


# --- one exception family -------------------------------------------------------------------------------------------

def _family():
    from protodirsig.compose import ComposeError
    return [ComposeError("recipes/r.yaml", "fidelity", "missing"), RunSpecError("scene not found", pointer="/engine/x"),
            AdmissionError("the submission failed", layer="recipes/r.yaml", field="settings[0]"),
            AdmissionError(problems.admission("from a problem")), NotFoundError("run", "0" * 64),
            InvalidRequestError("not a recipe"), ProblemError("plain")]


@pytest.mark.parametrize("err", _family(), ids=lambda e: type(e).__name__)
def test_except_problem_error_catches_every_sdk_error(err):
    with pytest.raises(ProblemError):
        raise err
    conforms(err.problem)
    assert err.problem["detail"] == str(err)


def test_the_built_problems_carry_class_type_and_members():
    from protodirsig.compose import ComposeError
    c = ComposeError("recipes/r.yaml", "fidelity", "missing").problem
    assert (c["type"], c["status"], c["layer"], c["field"]) == ("urn:protodirsig:problem:compose", 422, "recipes/r.yaml",
                                                                "fidelity")
    r = RunSpecError("m").problem
    assert (r["type"], r["status"], r["layer"]) == ("urn:protodirsig:problem:admission", 422, None)
    a = AdmissionError("x", layer="l.yaml", field="f").problem
    assert (a["layer"], a["field"]) == ("l.yaml", "f")
    assert isinstance(RunSpecError("m"), ValueError) and issubclass(ComposeError, RunSpecError)


@pytest.mark.parametrize("err", _family(), ids=lambda e: type(e).__name__)
def test_every_exception_pickles_with_its_members(err):
    import pickle
    back = pickle.loads(pickle.dumps(err))
    assert type(back) is type(err) and str(back) == str(err) and back.problem == err.problem
    for attr in ("layer", "field", "pointer"):
        assert getattr(back, attr, None) == getattr(err, attr, None)


# --- the loader's refusals name the layer file and field (the committed PointCollectors2 demo recipe) ----------------

DEMO_PROFILE = "engine_profiles/pointcollectors2_demo.yaml"
DEMO_ASSETS = CONFIG_REPO / "demos" / "PointCollectors2"


@pytest.fixture
def demo_library(tmp_path):
    root = tmp_path / "manifold_run_specs"
    for d in ("recipes", "scenarios", "engine_profiles"):
        shutil.copytree(RUN_SPECS / d, root / d)
    shutil.copytree(ROOT / "manifold_sensors", tmp_path / "manifold_sensors")
    return root


def _demo_problem(library, tmp_path, check):
    from protodirsig.workspace import Workspace
    ws = Workspace.local(library=library, config_repo=CONFIG_REPO, work=tmp_path / "work")
    run = ws.validate("pointcollectors2_demo").runs[0]
    assert not run.valid
    (failed,) = [c for c in run.checks if c.check == check]
    assert not failed.passed
    with pytest.raises(AdmissionError) as e:
        ws.submit_run("pointcollectors2_demo")
    return failed.errors[0].to_dict(), conforms(e.value.problem)


def _set_tahoe_atmosphere(library, weather=False):
    path = library / DEMO_PROFILE
    tahoe = yaml.safe_load((library / "engine_profiles" / "tahoe_static_pose.yaml").read_text())["engine"]
    text = path.read_text()
    atm = text[text.index("  atmosphere:\n"):text.index("  weather:\n")]
    text = text.replace(atm, "  atmosphere:\n    plugin: new_atmosphere\n    database:\n      ref: "
                        + json.dumps(tahoe["atmosphere"]["database"]["ref"]) + "\n\n")
    if weather:
        w = text[text.index("  weather:\n"):text.index("  ephemeris:\n")]
        text = text.replace(w, "  weather:\n    source: library\n    file: " + json.dumps(tahoe["weather"]["file"]) + "\n\n")
    path.write_text(text)


@needs_config_repo
def test_the_atmosphere_refusal_names_the_engine_profile_field(demo_library, tmp_path):
    check, problem = _demo_problem(demo_library, tmp_path, "resolution")
    for p in (check, problem):
        assert (p["layer"], p["field"]) == (DEMO_PROFILE, "engine.atmosphere.plugin"), p


@needs_config_repo
def test_the_weather_refusal_names_the_engine_profile_field(demo_library, tmp_path):
    _set_tahoe_atmosphere(demo_library)
    check, problem = _demo_problem(demo_library, tmp_path, "resolution")
    for p in (check, problem):
        assert (p["layer"], p["field"]) == (DEMO_PROFILE, "engine.weather.source"), p


@pytest.mark.skipif(not (DEMO_ASSETS / "demo.platform").is_file(),
                    reason="the PointCollectors2 demo assets are not placed (run scripts/bootstrap.py assets)")
def test_the_platform_template_refusal_names_the_engine_profile_field(demo_library, tmp_path):
    _set_tahoe_atmosphere(demo_library, weather=True)
    check, problem = _demo_problem(demo_library, tmp_path, "library_files")
    for p in (check, problem):
        assert (p["layer"], p["field"]) == (DEMO_PROFILE, "engine.platform.ref"), p
    assert "temporalintegration" in check["detail"]
