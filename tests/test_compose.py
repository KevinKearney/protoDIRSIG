"""`protodirsig.compose`: the conformance vectors, the generated run specs, and the composer's own guarantees
(deterministic bytes, `explain` naming each member's layer, errors naming layer file and field, both sensor forms
accepted downstream).

Reads manifold_run_specs/, manifold_sensors/ and manifold_contracts/vectors/ READ-ONLY; writes only to tmp_path.
"""
import importlib.util
import shutil
from pathlib import Path

import pytest
import yaml

from protodirsig.compose import MAX_RUNS, OVERRIDABLE, ComposeError, compose, compose_sweep, dump, explain, sweep_id
from protodirsig.run_spec import check_library_files, load_run_spec, resolve_auror_run
from protodirsig.simulation import schema_errors
from test_simulation import needs_dirsig

ROOT = Path(__file__).resolve().parents[1]
RUN_SPECS = ROOT / "manifold_run_specs"
ALL_RECIPES = sorted((RUN_SPECS / "recipes").glob("*.yaml"))
RECIPES = [r for r in ALL_RECIPES if "sensors" not in yaml.safe_load(r.read_text())]     # one-run recipes
SWEEP = RUN_SPECS / "recipes" / "sensor_sweep_tahoe.yaml"
VECTORS = ROOT / "manifold_contracts" / "vectors" / "compose"
CASES = sorted(p for p in VECTORS.iterdir() if p.is_dir() and p.name != "manifold_sensors")
CONFIG_REPO = ROOT / "manifold_config_repo"


def _script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _recipe(case):
    (recipe,) = (case / "recipes").glob("*.yaml")
    return recipe


def test_vectors_cover_the_required_cases():
    assert {c.name for c in CASES} >= {"auror_ref", "synthetic_vis", "member_in_two_layers", "missing_sensor",
                                       "unresolved_entry_id", "settings_by_entry_id", "inline_sensor",
                                       "engine_override", "engine_override_off_list", "engine_override_missing_path",
                                       "black_level_nonzero"}


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.name)
def test_vector(case):
    """Each case holds the layers and either the expected spec(s) or the expected error's layer and field."""
    recipe = _recipe(case)
    if (case / "expected_error.yaml").is_file():
        want = yaml.safe_load((case / "expected_error.yaml").read_text())
        with pytest.raises(ComposeError) as e:
            compose_sweep(recipe)
        assert (e.value.layer, e.value.field) == (want["layer"], want["field"])
        assert str(e.value).startswith(f"{want['layer']}: {want['field']}: ")
        return
    if (case / "expected_sweep.yaml").is_file():               # a sweep: expected/<run file>.yaml per run, in order
        want = yaml.safe_load((case / "expected_sweep.yaml").read_text())
        sweep = compose_sweep(recipe)
        assert (sweep.sweep_id, list(sweep.runs)) == (want["sweep_id"], want["runs"])
        assert sorted(p.stem for p in (case / "expected").glob("*.yaml")) == sorted(sweep.files.values())
        for name, spec in sweep.runs.items():
            assert spec == yaml.safe_load((case / "expected" / f"{sweep.files[name]}.yaml").read_text())
            assert schema_errors(spec) == []
        return
    for name, inline in (("expected.yaml", False), ("expected_inline.yaml", True)):
        if (case / name).is_file():
            spec = compose(recipe, inline_sensor=inline)
            assert spec == yaml.safe_load((case / name).read_text())
            assert schema_errors(spec) == []


@pytest.mark.parametrize("name", ["auror_ref", "synthetic_vis"])
def test_equivalence_vectors_are_the_repository_layers(name):
    """The two equivalence cases are copies of the repository's layers and sensors; refresh them when those change."""
    case = VECTORS / name
    for path in sorted(case.rglob("*.yaml")):
        rel = path.relative_to(case)
        if rel.name == "expected.yaml":
            assert path.read_bytes() == (RUN_SPECS / f"{name}.yaml").read_bytes()
        else:
            assert path.read_bytes() == (RUN_SPECS / rel).read_bytes(), rel
    for path in (VECTORS / "manifold_sensors").glob("*.yaml"):
        if (ROOT / "manifold_sensors" / path.name).is_file():
            assert path.read_bytes() == (ROOT / "manifold_sensors" / path.name).read_bytes(), path.name


def test_refresh_vectors_is_idempotent():
    """The equivalence vectors are current, so a refresh changes nothing (`scripts/compose.py --refresh-vectors`)."""
    assert _script("compose").refresh_vectors() == []


def test_engine_override_sets_the_allowed_path_only():
    spec = compose(RUN_SPECS / "recipes" / "auror_ref.yaml")
    assert spec["engine"]["platform"]["channel_response"] == "native"
    assert "channel_response" not in compose(RUN_SPECS / "recipes" / "synthetic_vis.yaml")["engine"]["platform"]
    assert "engine_overrides" not in yaml.safe_dump(spec)


def test_generated_run_specs_are_current():
    assert _script("compose").main(["--check"]) == 0, "run scripts/compose.py"


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda p: p.stem)
def test_composition_is_deterministic(recipe):
    rel = recipe.relative_to(RUN_SPECS).as_posix()
    first, second = dump(compose(recipe), rel), dump(compose(recipe), rel)
    assert first == second == (RUN_SPECS / f"{recipe.stem}.yaml").read_text()
    assert first.startswith(f"# GENERATED by scripts/compose.py from recipes/{recipe.stem}.yaml - do not edit\n")


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda p: p.stem)
def test_composed_spec_passes_the_run_spec_checks(recipe):
    assert schema_errors(compose(recipe)) == []
    assert schema_errors(compose(recipe, inline_sensor=True)) == []


def test_explain_names_the_layer_of_every_member():
    recipe = RUN_SPECS / "recipes" / "auror_ref.yaml"
    spec, src = compose(recipe), explain(recipe)
    assert list(src) == ["spec_version", *(f"descriptor.{m}" for m in spec["descriptor"]), "engine",
                         "engine.platform.channel_response"]
    assert {k: v["layer"] for k, v in src.items()} == {
        "spec_version": "rules compose/1",
        "descriptor.meta": "recipes/auror_ref.yaml", "descriptor.settings": "recipes/auror_ref.yaml",
        "descriptor.fidelity": "recipes/auror_ref.yaml",
        "descriptor.collection": "scenarios/tahoe_static_pose.yaml",
        "descriptor.origin": "engine_profiles/tahoe_static_pose.yaml",
        "descriptor.extras": "engine_profiles/tahoe_static_pose.yaml",
        "engine": "engine_profiles/tahoe_static_pose.yaml",
        "engine.platform.channel_response": "recipes/auror_ref.yaml",
        "descriptor.sensor": "manifold_sensors/auror-nir.yaml"}
    assert src["descriptor.sensor"]["content_hash"] == spec["descriptor"]["sensor"]["ref"]["content_hash"]
    assert all(v["content_hash"].startswith("sha256:") for k, v in src.items() if k != "spec_version")
    assert "explain" not in str(spec) and "recipes/" not in yaml.safe_dump(spec)     # provenance stays out of the spec


def test_explain_cli_prints_every_member(capsys):
    recipe = RUN_SPECS / "recipes" / "synthetic_vis.yaml"
    assert _script("compose").main(["--explain", str(recipe)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith(f"sweep_id {sweep_id(recipe)}") and out[1].startswith("run synthetic-vis-static-pose")
    assert any(ln.split()[:2] == ["descriptor.collection", "scenarios/tahoe_static_pose.yaml"] for ln in out)
    assert any("manifold_sensors/synthetic_600_200_vis_1920.yaml" in ln for ln in out) and len(out) == 11


def test_explain_cli_prints_the_sweep_id_and_every_run(capsys):
    assert _script("compose").main(["--explain", str(SWEEP)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith(f"sweep_id {sweep_id(SWEEP)}  (recipes/sensor_sweep_tahoe.yaml, 3 runs)")
    assert [ln.split()[1] for ln in out if ln.startswith("run ")] == [
        "sensor-sweep-tahoe--auror-nir", "sensor-sweep-tahoe--deepscan_850_306_nir_1280",
        "sensor-sweep-tahoe--synthetic_600_200_vis_1920"]


def test_sweep_runs_one_spec_per_sensor():
    sweep = compose_sweep(SWEEP)
    doc = yaml.safe_load(SWEEP.read_text())
    assert sweep.is_sweep and list(sweep.sensors.values()) == doc["sensors"]
    for name, spec in sweep.runs.items():
        d, s = spec["descriptor"], sweep.sensors[name]
        assert name == d["meta"]["name"] == f"{doc['meta']['name']}--{Path(s).stem}"
        assert (d["meta"]["tags"], d["meta"]["description"]) == (doc["meta"]["tags"], doc["meta"]["description"])
        assert d["sensor"]["ref"]["name"] == s and d["fidelity"] == doc["fidelity_by_sensor"][s]
        entries = [e["entry_id"] for e in yaml.safe_load((ROOT / "manifold_sensors" / s).read_text())["sensor"]["entries"]]
        assert [m["entry_id"] for m in d["settings"]] == entries
        assert spec["engine"]["run"] == {"seed": 42}                   # the shared seed, unchanged
        assert schema_errors(spec) == []
        assert sweep.files[name] == f"sensor_sweep_tahoe--{Path(s).stem}"


def test_sweep_composition_is_deterministic():
    a, b = compose_sweep(SWEEP), compose_sweep(SWEEP)
    for name in a.runs:
        text = dump(a.runs[name], a.recipe)
        assert text == dump(b.runs[name], b.recipe) == (RUN_SPECS / f"{a.files[name]}.yaml").read_text()
        assert text.startswith("# GENERATED by scripts/compose.py from recipes/sensor_sweep_tahoe.yaml - do not edit\n")


def test_sweep_id_is_the_recipe_hash_and_stays_out_of_the_specs(tmp_path):
    import hashlib
    sweep = compose_sweep(SWEEP)
    assert sweep.sweep_id == hashlib.sha256(SWEEP.read_bytes()).hexdigest()[:12] == sweep_id(SWEEP)
    assert all(sweep.sweep_id not in yaml.safe_dump(s) for s in sweep.runs.values())
    root = _layers(tmp_path)
    copy = root / "recipes" / SWEEP.name
    copy.write_text(SWEEP.read_text() + "# edited\n")
    edited = compose_sweep(copy, sensor_library=tmp_path / "manifold_sensors")
    assert edited.sweep_id != sweep.sweep_id and edited.runs == sweep.runs


def test_sweep_cap_is_checked_first_and_overridable():
    assert MAX_RUNS == 32
    with pytest.raises(ComposeError, match="3 runs exceed the cap of 2") as e:
        compose_sweep(SWEEP, max_runs=2)
    assert (e.value.layer, e.value.field) == ("recipes/sensor_sweep_tahoe.yaml", "sensors")
    assert len(compose_sweep(SWEEP, max_runs=3).runs) == 3


def test_compose_refuses_a_sweep_and_a_one_run_recipe_works_through_both():
    with pytest.raises(ComposeError, match="use compose_sweep") as e:
        compose(SWEEP)
    assert e.value.field == "sensors"
    for recipe in RECIPES:
        sweep = compose_sweep(recipe)
        spec = compose(recipe)
        assert not sweep.is_sweep and sweep.runs == {spec["descriptor"]["meta"]["name"]: spec}
        assert list(sweep.files.values()) == [recipe.stem]


@pytest.mark.parametrize("recipe", ALL_RECIPES, ids=lambda p: p.stem)
def test_every_composed_run_passes_the_run_spec_checks(recipe):
    for inline in (False, True):
        assert all(schema_errors(s) == [] for s in compose_sweep(recipe, inline_sensor=inline).runs.values())


def _layers(tmp_path):
    """A writable copy of the repository's layers and sensor library."""
    shutil.copytree(RUN_SPECS, tmp_path / "manifold_run_specs")
    shutil.copytree(ROOT / "manifold_sensors", tmp_path / "manifold_sensors")
    return tmp_path / "manifold_run_specs"


@pytest.mark.parametrize("edit, layer, field, match", [
    (lambda r: r.update(color="red"), "recipes/synthetic_vis.yaml", "color", "unknown key"),
    (lambda r: r.update(engine={"run": {"seed": 1}}), "recipes/synthetic_vis.yaml", "engine", "also in engine_profiles/"),
    (lambda r: r.pop("fidelity"), "recipes/synthetic_vis.yaml", "fidelity", "missing"),
    (lambda r: r.update(compose="compose/2"), "recipes/synthetic_vis.yaml", "compose", "implements 'compose/1'"),
    (lambda r: r.update(scenario="no_such"), "scenarios/no_such.yaml", None, "not found"),
    (lambda r: r["settings"][0]["roi"].update(Width=4000), "recipes/synthetic_vis.yaml", "settings", "exceeds detector"),
    (lambda r: r["settings"].append(dict(r["settings"][0])), "recipes/synthetic_vis.yaml", "settings[1].entry_id",
     "two settings members"),
], ids=["unknown-key", "engine-in-recipe", "missing-member", "rules-version", "missing-layer", "roi", "duplicate-entry"])
def test_errors_name_the_layer_file_and_field(tmp_path, edit, layer, field, match):
    root = _layers(tmp_path)
    path = root / "recipes" / "synthetic_vis.yaml"
    recipe = yaml.safe_load(path.read_text())
    edit(recipe)
    path.write_text(yaml.safe_dump(recipe, sort_keys=False))
    with pytest.raises(ComposeError, match=match) as e:
        compose(path)
    assert (e.value.layer, e.value.field) == (layer, field)
    assert "descriptor." not in str(e.value)                       # a layer field, not a composed-document path


def test_member_in_two_layers_belongs_to_its_owner(tmp_path):
    root = _layers(tmp_path)
    path = root / "engine_profiles" / "tahoe_static_pose.yaml"
    path.write_text(path.read_text() + "\ncollection: {epoch: '2020-01-01T00:00:00Z'}\n")
    with pytest.raises(ComposeError, match="layers own disjoint members") as e:
        compose(root / "recipes" / "synthetic_vis.yaml")
    assert (e.value.layer, e.value.field) == ("engine_profiles/tahoe_static_pose.yaml", "collection")
    assert OVERRIDABLE == frozenset()


def test_stamp_hashes_verifies_generated_specs(tmp_path):
    stamp = _script("stamp_hashes")
    text = (RUN_SPECS / "auror_ref.yaml").read_text()
    good = tmp_path / "good.yaml"
    good.write_text(text)
    assert stamp.verify_generated(good) == []
    bad = tmp_path / "bad.yaml"
    bad.write_text(text.replace("sha256:bed58062", "sha256:00000000"))
    assert [s.split(": ", 1)[1] for s in stamp.verify_generated(bad)] == [
        "platforms/AurorNIRDetector/AurorNIRDetector.platform (regenerate with scripts/compose.py)"]


@pytest.mark.skipif(not (CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene").is_file(), reason="manifold_config_repo not present")
@pytest.mark.parametrize("recipe", RECIPES, ids=lambda p: p.stem)
def test_inline_and_ref_sensor_render_the_same_platform(tmp_path, recipe):
    """The resolver accepts both forms of descriptor.sensor and renders the same .platform from each."""
    from protodirsig.platform_gen import render_platform
    out = {}
    for inline in (False, True):
        spec = compose(recipe, inline_sensor=inline)
        run = resolve_auror_run(spec, RUN_SPECS / f"{recipe.stem}.yaml", CONFIG_REPO)
        assert check_library_files(spec, run) == []
        path = tmp_path / f"{inline}.platform"
        render_platform(run.platform, run.sensor, run.settings[0]["entry_id"], run.settings, run.integration_samples,
                        run.sensor_library, path, run.channel_response)
        out[inline] = path.read_bytes()
    assert out[False] == out[True]


@needs_dirsig
def test_submit_recipe_accepts_and_rejects(tmp_path):
    from protodirsig.registry import LocalRegistry
    r = LocalRegistry().submit_recipe(RUN_SPECS / "recipes" / "synthetic_vis.yaml", CONFIG_REPO, tmp_path / "ok")
    assert r.accepted and r.checks == {"compose": True, "schema": True, "resolution": True, "execution": True}
    assert (tmp_path / "ok" / "synthetic_vis.yaml").read_text() == (RUN_SPECS / "synthetic_vis.yaml").read_text()
    bad = _recipe(VECTORS / "unresolved_entry_id")
    r = LocalRegistry().submit_recipe(bad, CONFIG_REPO, tmp_path / "bad")
    assert not r.accepted and r.checks["compose"] is False
    assert r.reasons[0].startswith("Composition failed: recipes/synthetic_vis.yaml: settings[0].entry_id:")


@needs_dirsig
def test_submit_and_run_sweep_keep_each_run_independent(tmp_path, monkeypatch):
    """One run rejected at submission (its QE curve is missing) and one failing at render: the third still
    renders, and each run reports its own state. 16 x 16 windows."""
    from protodirsig.registry import LocalRegistry
    root = _layers(tmp_path)
    recipe = root / "recipes" / SWEEP.name
    recipe.write_text(SWEEP.read_text().replace("Width: 32, Height: 32", "Width: 16, Height: 16"))
    (tmp_path / "manifold_sensors" / "spectral" / "qe" / "synthetic_visgaas.csv").unlink()    # DeepScan's QE
    reg = LocalRegistry()
    sub = reg.submit_sweep(recipe, CONFIG_REPO, tmp_path / "work")
    nir, deep, vis = (f"sensor-sweep-tahoe--{s}" for s in ("auror-nir", "deepscan_850_306_nir_1280",
                                                           "synthetic_600_200_vis_1920"))
    assert sub.sweep_id == sweep_id(recipe) and sub.errors == []
    assert sub.states == {nir: "accepted", deep: "rejected", vis: "accepted"}
    assert any("synthetic_visgaas.csv" in e for e in sub.runs[deep].errors)
    assert all(r.submission.simulation.auror_run.seed == 42 for r in sub.runs.values() if r.state == "accepted")

    def boom(*a, **k):
        raise RuntimeError("render failed on purpose")
    monkeypatch.setattr(sub.runs[vis].submission.simulation, "run", boom)
    out = reg.run_sweep(sub)
    assert out is sub and out.states == {nir: "rendered", deep: "rejected", vis: "failed"}
    assert out.runs[vis].errors == ["RuntimeError: render failed on purpose"]
    assert out.runs[nir].result.image.is_file()


def test_submit_sweep_reports_a_recipe_that_does_not_compose(tmp_path):
    from protodirsig.registry import LocalRegistry
    bad = _recipe(VECTORS / "sweep_sensor_without_settings")
    sub = LocalRegistry().submit_sweep(bad, CONFIG_REPO, tmp_path)
    assert sub.runs == {} and sub.sweep_id == sweep_id(bad)
    assert sub.errors[0].startswith("Composition failed: recipes/sensor_sweep_tahoe.yaml: sensors[1]:")
