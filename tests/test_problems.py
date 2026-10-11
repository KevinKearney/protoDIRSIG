"""protodirsig.problems: errors caused by an authored file name the layer file and the field in it (R-08).

`locate` must agree with the composer's own provenance for every top-level member of every repository recipe, and a
mutated copy of the library must give problems naming the edited file and field. Every constructor's output must
conform to api/schemas/problem.schema.json. Mutations are made in a temporary copy; the library is read only.
"""
import copy
import json
import shutil
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from protodirsig import identity, problems
from protodirsig.compose import ComposeError, compose, compose_sweep
from protodirsig.contract import schema_violations
from test_simulation import CONFIG_REPO, needs_dirsig

ROOT = Path(__file__).resolve().parents[1]
RUN_SPECS = ROOT / "manifold_run_specs"
RECIPES = sorted((RUN_SPECS / "recipes").glob("*.yaml"))
LAYERED = [r for r in RECIPES if "passthrough" not in yaml.safe_load(r.read_text())]   # pass-through: no collection, motion
PROBLEM = Draft202012Validator(json.loads((ROOT / "api" / "schemas" / "problem.schema.json").read_text()))


def conforms(problem):
    errors = [e.message for e in PROBLEM.iter_errors(problem)]
    assert errors == [], errors
    return problem


def _pointer(member):
    return "/" + member.replace(".", "/")


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda p: p.stem)
def test_locate_agrees_with_the_composers_provenance_for_every_member(recipe):
    sweep = compose_sweep(recipe)
    for name, spec in sweep.runs.items():
        for member, src in sweep.sources[name].items():
            layer, field = problems.locate(_pointer(member), sweep.sources[name], spec=spec, recipe=recipe)
            if src["layer"].startswith("rules "):              # set by the rules (spec_version, an opaque descriptor)
                assert (layer, field) == (None, None)
                continue
            assert layer == src["layer"], (name, member)
            assert field, (name, member)


@pytest.mark.parametrize("recipe", LAYERED, ids=lambda p: p.stem)
def test_locate_names_the_field_in_the_layers_own_layout(recipe):
    sweep = compose_sweep(recipe)
    doc = yaml.safe_load(recipe.read_text())
    for name, spec in sweep.runs.items():
        src = sweep.sources[name]
        loc = lambda p: problems.locate(p, src, spec=spec, recipe=doc)            # noqa: E731
        assert loc("/descriptor/collection/geometry/range") == (src["descriptor.collection"]["layer"],
                                                                "collection.geometry.range")
        assert loc("/engine/motion/kind") == (src["engine"]["layer"], "engine.motion.kind")
        assert loc("/engine/scenes/0/ref") == (src["engine"]["layer"], "engine.scenes[0].ref")
        assert loc("/descriptor/meta/name") == (src["descriptor.meta"]["layer"], "meta.name")
        (member,) = spec["descriptor"]["settings"]
        j = [m["entry_id"] for m in doc["settings"]].index(member["entry_id"])
        assert loc("/descriptor/settings/0/gain/value") == (src["descriptor.settings"]["layer"], f"settings[{j}].gain.value")
        sensor = sweep.sensors[name]
        fid = f"fidelity_by_sensor.{sensor}" if sensor in (doc.get("fidelity_by_sensor") or {}) else "fidelity"
        assert loc("/descriptor/fidelity/modeled") == (src["descriptor.fidelity"]["layer"], f"{fid}.modeled")
        want = f"sensors[{doc['sensors'].index(sensor)}]" if "sensors" in doc else "sensor"
        assert loc("/descriptor/sensor/ref/name") == (src["descriptor.meta"]["layer"], want)
        for path in (m for m in src if m.startswith("engine.")):                # engine_overrides
            assert loc(_pointer(path)) == (src[path]["layer"], f"engine_overrides.{path[len('engine.'):]}")


def test_recipe_layout_fields_are_not_guessed_without_the_recipe():
    sweep = compose_sweep(RUN_SPECS / "recipes" / "sensor_sweep_tahoe.yaml")
    name = list(sweep.runs)[2]
    src, spec = sweep.sources[name], sweep.runs[name]
    layer = src["descriptor.settings"]["layer"]
    assert problems.locate("/descriptor/settings/0/gain", src, spec=spec) == (layer, None)
    assert problems.locate("/descriptor/fidelity", src, spec=spec) == (layer, None)
    assert problems.locate("/descriptor/sensor/ref/name", src, spec=spec) == (layer, None)
    assert problems.locate("/descriptor/settings/0/gain", src, spec=spec, recipe=RUN_SPECS / "recipes" /
                           "sensor_sweep_tahoe.yaml") == (layer, "settings[2].gain")


@pytest.mark.parametrize("pointer", ["", "/", "/spec_version", "/descriptor", "/descriptor/bogus", "/bogus/x"])
def test_a_pointer_with_no_owner_is_not_attributed(pointer):
    sweep = compose_sweep(RUN_SPECS / "recipes" / "auror_ref.yaml")
    (name,) = sweep.runs
    assert problems.locate(pointer, sweep.sources[name], spec=sweep.runs[name]) == (None, None)


def test_a_member_missing_from_the_sources_is_not_attributed():
    sweep = compose_sweep(RUN_SPECS / "recipes" / "synthetic_vis.yaml")
    (name,) = sweep.runs
    src = {k: v for k, v in sweep.sources[name].items() if k != "engine"}
    assert problems.locate("/engine/motion/kind", src) == (None, None)
    assert problems.locate("/engine/motion/kind", None) == (None, None)


# --- a mutated copy of the library --------------------------------------------------------------------------------

@pytest.fixture
def library(tmp_path):
    """A temporary copy of the repository's layers and sensor library: `<tmp>/manifold_run_specs/{recipes,scenarios,
    engine_profiles}` and `<tmp>/manifold_sensors`."""
    root = tmp_path / "manifold_run_specs"
    for d in ("recipes", "scenarios", "engine_profiles"):
        shutil.copytree(RUN_SPECS / d, root / d)
    shutil.copytree(ROOT / "manifold_sensors", tmp_path / "manifold_sensors")
    return root


def _edit(path, old, new):
    text = path.read_text()
    assert text.count(old) == 1, (path, old)
    path.write_text(text.replace(old, new))


MUTATIONS = {                       # name: (file under the layer root, old text, new text, layer, field)
    "engine_profile_motion_kind": ("engine_profiles/tahoe_static_pose.yaml", "    kind: static\n", "    kind: bogus\n",
                                   "engine_profiles/tahoe_static_pose.yaml", "engine.motion.kind"),
    "scenario_bad_enum": ("scenarios/tahoe_static_pose.yaml", "range: {value: 500000, provenance: modeled}",
                          "range: {value: 500000, provenance: guessed}", "scenarios/tahoe_static_pose.yaml",
                          "collection.geometry.range.provenance"),
    "recipe_missing_settings_value": ("recipes/auror_ref.yaml", "exposure_time: {value: 0.005, provenance: specified}",
                                      "exposure_time: {provenance: specified}", "recipes/auror_ref.yaml",
                                      "settings[0].exposure_time"),
}


@pytest.mark.parametrize("case", sorted(MUTATIONS))
def test_a_mutated_layer_is_named_by_file_and_field(library, case):
    rel, old, new, layer, field = MUTATIONS[case]
    _edit(library / rel, old, new)
    recipe = library / "recipes" / "auror_ref.yaml"
    sweep = compose_sweep(recipe)
    (name,) = sweep.runs
    spec = sweep.runs[name]
    violations = schema_violations(spec)
    assert violations, case
    p = conforms(problems.from_schema_violations(spec, sweep.sources[name], violations, "/runs", recipe=recipe))
    assert (p["type"], p["status"], p["layer"], p["field"]) == ("urn:protodirsig:problem:admission", 422, layer, field)
    assert p["detail"].startswith(f"Run {name} is not valid run-spec/1: {layer}: {field}: ")
    assert [e["run"] for e in p["errors"]] == [name] * len(violations)
    assert (p["errors"][0]["layer"], p["errors"][0]["field"]) == (layer, field)


def test_a_reordered_sweep_member_is_named_at_its_recipe_index(library):
    recipe = library / "recipes" / "sensor_sweep_tahoe.yaml"
    doc = yaml.safe_load(recipe.read_text())
    j = [m["entry_id"] for m in doc["settings"]].index("synthetic-600-200-vis-1920")
    del doc["settings"][j]["gain"]["value"]
    recipe.write_text(yaml.safe_dump(doc, sort_keys=False))
    sweep = compose_sweep(recipe)
    bad = {n: schema_violations(s) for n, s in sweep.runs.items()}
    assert [n for n, v in bad.items() if v] == ["sensor-sweep-tahoe--synthetic_600_200_vis_1920"]
    name = "sensor-sweep-tahoe--synthetic_600_200_vis_1920"
    p = conforms(problems.from_schema_violations(sweep.runs[name], sweep.sources[name], bad[name], recipe=recipe))
    assert (p["layer"], p["field"]) == ("recipes/sensor_sweep_tahoe.yaml", f"settings[{j}].gain")


@pytest.mark.parametrize("inline", [True, False], ids=["inline", "by_reference"])
def test_a_sensor_violation_is_named_in_the_sensor_library_file(library, inline):
    sensors = library.parent / "manifold_sensors"
    doc = yaml.safe_load((sensors / "auror-nir.yaml").read_text())
    doc["sensor"]["entries"][0]["focal_planes"][0]["detector"]["Bogus"] = 1
    (sensors / "auror-nir.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    recipe = library / "recipes" / "auror_ref.yaml"
    sweep = compose_sweep(recipe, inline_sensor=inline)
    (name,) = sweep.runs
    spec = sweep.runs[name]
    if not inline:
        assert schema_violations(spec) == []                     # the reference hides the block ...
        spec = identity.resolved_run_spec(spec, sensors)           # ... so the resolved spec is checked
    p = conforms(problems.from_schema_violations(spec, sweep.sources[name], schema_violations(spec), recipe=recipe))
    assert (p["layer"], p["field"]) == ("manifold_sensors/auror-nir.yaml", "sensor.entries[0].focal_planes[0].detector")
    assert "'Bogus' was unexpected" in p["detail"] and "matches none of the allowed forms" not in p["detail"]


def test_compose_error_problem(library):
    _edit(library / "recipes" / "auror_ref.yaml", "  - entry_id: auror-nir\n", "  - entry_id: auror-nir-x\n")
    with pytest.raises(ComposeError) as e:
        compose(library / "recipes" / "auror_ref.yaml")
    p = conforms(problems.from_compose_error(e.value, "/compose"))
    assert (p["type"], p["status"], p["layer"], p["field"]) == ("urn:protodirsig:problem:compose", 422,
                                                                 "recipes/auror_ref.yaml", "settings[0].entry_id")
    assert p["detail"] == str(e.value) and p["instance"] == "/compose"


def test_not_found_problem():
    p = conforms(problems.not_found("run", "0" * 64, "/runs/" + "0" * 64))
    assert (p["type"], p["status"]) == ("urn:protodirsig:problem:not-found", 404) and "0" * 64 in p["detail"]


def test_from_schema_violations_needs_a_violation():
    sweep = compose_sweep(RUN_SPECS / "recipes" / "auror_ref.yaml")
    (name,) = sweep.runs
    with pytest.raises(ValueError):
        problems.from_schema_violations(sweep.runs[name], sweep.sources[name], [])


def test_a_spec_not_composed_here_gets_a_problem_without_a_layer():
    spec = copy.deepcopy(compose(RUN_SPECS / "recipes" / "auror_ref.yaml"))
    spec["engine"]["motion"]["kind"] = "bogus"
    p = conforms(problems.from_schema_violations(spec, None, schema_violations(spec)))
    assert (p["layer"], p["field"]) == (None, None) and "/engine/motion/kind" in p["detail"]


# --- through LocalRegistry ----------------------------------------------------------------------------------------

def _submit_recipe(library, tmp_path, recipe="auror_ref.yaml"):
    from protodirsig.registry import LocalRegistry
    return LocalRegistry().submit_recipe(library / "recipes" / recipe, CONFIG_REPO, tmp_path / "work")


@needs_dirsig
def test_submission_problem_names_the_engine_profile_field(library, tmp_path):
    _edit(library / "engine_profiles/tahoe_static_pose.yaml", "    kind: static\n", "    kind: bogus\n")
    r = _submit_recipe(library, tmp_path)
    assert not r.accepted and not r.checks["schema"]
    p = conforms(r.problem)
    assert (p["type"], p["layer"], p["field"]) == ("urn:protodirsig:problem:admission",
                                                    "engine_profiles/tahoe_static_pose.yaml", "engine.motion.kind")
    assert p["detail"].startswith("Schema check failed")


@needs_dirsig
def test_submission_problem_names_an_unstamped_reference(library, tmp_path):
    path = library / "engine_profiles/tahoe_static_pose.yaml"
    text = path.read_text()
    start = text.index("{name: scenes/tahoe/tahoe.scene, content_hash: \"") + len("{name: scenes/tahoe/tahoe.scene, content_hash: \"")
    path.write_text(text[:start] + "sha256:<hash>" + text[text.index('"', start):])
    r = _submit_recipe(library, tmp_path)
    assert not r.accepted and r.checks["schema"] and not r.checks["stamped"]
    p = conforms(r.problem)
    assert (p["layer"], p["field"]) == ("engine_profiles/tahoe_static_pose.yaml", "engine.scenes[0].ref.content_hash")
    assert "Stamp check failed" in p["detail"]


def test_submission_problem_for_a_recipe_that_does_not_compose(library, tmp_path):
    _edit(library / "recipes" / "auror_ref.yaml", "sensor: auror-nir.yaml", "sensor: no-such-sensor.yaml")
    r = _submit_recipe(library, tmp_path)
    p = conforms(r.problem)
    assert (p["type"], p["layer"], p["field"]) == ("urn:protodirsig:problem:compose", "recipes/auror_ref.yaml", "sensor")


@needs_dirsig
def test_accepted_submission_has_no_problem(tmp_path):
    from protodirsig.registry import LocalRegistry
    r = LocalRegistry().submit_recipe(RUN_SPECS / "recipes" / "synthetic_vis.yaml", CONFIG_REPO, tmp_path / "w")
    assert r.accepted and r.problem is None and r.sources and r.recipe.name == "synthetic_vis.yaml"


@needs_dirsig
def test_sweep_runs_carry_their_sources_for_problems(library, tmp_path):
    from protodirsig.registry import LocalRegistry
    recipe = library / "recipes" / "sensor_sweep_tahoe.yaml"
    doc = yaml.safe_load(recipe.read_text())
    j = [m["entry_id"] for m in doc["settings"]].index("auror-nir")
    del doc["settings"][j]["gain"]["value"]
    recipe.write_text(yaml.safe_dump(doc, sort_keys=False))
    sub = LocalRegistry().submit_sweep(recipe, CONFIG_REPO, tmp_path / "sweep")
    run = sub.runs["sensor-sweep-tahoe--auror-nir"]
    assert run.state == "rejected"
    p = conforms(run.submission.problem)
    assert (p["layer"], p["field"]) == ("recipes/sensor_sweep_tahoe.yaml", f"settings[{j}].gain")
