"""docs/Authoring_friction_audit.md against the repository: every count is recomputed from the committed files with the
document's counting rule, and every refusal it quotes is produced here (engine-free: `validate`, and `submit_run`
refusals that create nothing)."""
import copy
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from manifold.core.errors import AdmissionError, ProblemError
from manifold.sim import Workspace

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "Authoring_friction_audit.md").read_text(encoding="utf-8")
LAYERS = ROOT / "manifold_run_specs"
SENSORS = ROOT / "manifold_sensors"
S2S = LAYERS / "s2s" / "s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0.yaml"


def leaves(doc, path=""):
    """The document's fields: (path, value) of every scalar and every list of scalars."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            yield from leaves(v, f"{path}.{k}" if path else k)
    elif isinstance(doc, list) and any(isinstance(x, (dict, list)) for x in doc):
        for i, v in enumerate(doc):
            yield from leaves(v, f"{path}[{i}]")
    else:
        yield path, doc


def counts(path):
    fields = list(leaves(yaml.safe_load(path.read_text())))
    return len(fields), sum(p.endswith("content_hash") for p, _ in fields)


@pytest.fixture(scope="module")
def ws(tmp_path_factory):
    return Workspace.local(work=tmp_path_factory.mktemp("work"))


def outcome(ws, target):
    """("valid", None) / ("invalid", the failing checks' details joined) / ("raised", the problem's detail)."""
    try:
        run = ws.validate(target).runs[0]
    except ProblemError as e:
        return "raised", e.problem["detail"]
    details = " | ".join(e.detail for c in run.checks if not c.passed for e in c.errors)
    return ("valid", None) if run.valid else ("invalid", details)


@pytest.mark.parametrize("rel, fields, hashes", [
    ("manifold_run_specs/recipes/auror_ref.yaml", 25, 0),
    ("manifold_run_specs/scenarios/tahoe_static_pose.yaml", 18, 0),
    ("manifold_run_specs/engine_profiles/tahoe_static_pose.yaml", 34, 4),
    ("manifold_sensors/auror-nir.yaml", 43, 0),
    ("manifold_run_specs/auror_ref.yaml", 76, 5),
    ("manifold_sensors/deepscan_850_306_nir_1280.yaml", 47, 1),
    ("manifold_sensors/synthetic_600_200_vis_1920.yaml", 49, 2),
    ("manifold_run_specs/engine_profiles/tahoe_leo_pass.yaml", 43, 6),
    ("manifold_run_specs/s2s/s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0.yaml", 72, 3),
    ("manifold_run_specs/recipes/demo_brdf1_passthrough.yaml", 12, 1),
    ("manifold_run_specs/recipes/demo_pointcollectors2_passthrough.yaml", 12, 1),
])
def test_field_and_hash_counts(rel, fields, hashes):
    assert counts(ROOT / rel) == (fields, hashes)


def test_the_count_tables_state_those_numbers():
    assert "| `recipes/auror_ref.yaml` | 25 | 0 |" in DOC
    assert "| `scenarios/tahoe_static_pose.yaml` | 18 | 0 |" in DOC
    assert "| `engine_profiles/tahoe_static_pose.yaml` | 34 | 4 (" in DOC
    assert "| `manifold_sensors/auror-nir.yaml` | 43 | 0 |" in DOC
    assert "(`manifold_run_specs/auror_ref.yaml`) | 76 | 5 (" in DOC
    assert "`deepscan_850_306_nir_1280.yaml` 47 fields, 1 hash; `synthetic_600_200_vis_1920.yaml` 49 fields, 2 hashes" in DOC
    assert "`engine_profiles/tahoe_leo_pass.yaml`, has 43 fields and 6 hashes" in DOC
    assert "72 fields, 3 hashes (sensor, scene, platform), 1 generator revision" in DOC
    assert "| 20 + 18 + 34 + 43 = 115 | 4 + 0 + 10 + 0 = 14 |" in DOC and 20 + 18 + 34 + 43 == 115


def test_copied_values_of_the_engine_profile_and_the_s2s_spec():
    profile = dict(leaves(yaml.safe_load((LAYERS / "engine_profiles" / "tahoe_static_pose.yaml").read_text())))
    names = [p for p in profile if p.endswith(".name") and ("ref" in p or "file" in p)]
    assert len(names) == 4 and "engine.platform.library_entry" in profile and "engine.generator.revision" in profile
    spec = dict(leaves(yaml.safe_load(S2S.read_text())))
    names = [p for p in spec if p.endswith("ref.name")]
    assert len(names) == 3 and "engine.platform.library_entry" in spec and "engine.generator.revision" in spec


REQUIRED = [("compose",), ("meta", "name"), ("sensor",), ("scenario",), ("engine_profile",),
            ("settings", 0, "entry_id"), ("settings", 0, "exposure_time"), ("settings", 0, "frame_rate"),
            ("settings", 0, "gain"), ("settings", 0, "black_level"), ("settings", 0, "roi", "Width"),
            ("settings", 0, "roi", "Height"), ("fidelity", "modeled"), ("fidelity", "approximated"),
            ("fidelity", "absent"), ("fidelity", "valid_for")]
OPTIONAL = [("meta", "tags"), ("meta", "description"), ("settings", 0, "roi", "OffsetX"),
            ("settings", 0, "roi", "OffsetY"), ("engine_overrides",)]


def _without(doc, path):
    d = copy.deepcopy(doc)
    node = d
    for k in path[:-1]:
        node = node[k]
    del node[path[-1]]
    return d


def test_the_required_recipe_fields(ws):
    recipe = ws.get_recipe("auror_ref").document
    assert outcome(ws, recipe) == ("valid", None)
    for path in REQUIRED:
        assert outcome(ws, _without(recipe, path))[0] != "valid", path
    for path in OPTIONAL:
        assert outcome(ws, _without(recipe, path)) == ("valid", None), path
    value_fields = 4 * 2                            # exposure_time, frame_rate, gain, black_level: value, provenance
    assert len(REQUIRED) - 4 + value_fields == 20
    kind, detail = outcome(ws, _without(recipe, ("settings", 0, "gain")))
    assert kind == "invalid" and "descriptor.settings[0] (entry 'auror-nir') has no 'gain'" in detail
    assert "leaves 20 required fields" in DOC


def test_changing_one_thing(ws):
    recipe = ws.get_recipe("auror_ref").document
    window = copy.deepcopy(recipe)
    window["settings"][0]["roi"].update(Width=16, Height=16)
    assert outcome(ws, window) == ("valid", None)
    sensor = copy.deepcopy(recipe)
    sensor["sensor"] = "synthetic_600_200_vis_1920.yaml"
    kind, detail = outcome(ws, sensor)
    assert kind == "raised" and "settings[0].entry_id: 'auror-nir' names no entry of the listed sensors" in detail
    sensor["settings"][0]["entry_id"] = "synthetic-600-200-vis-1920"
    kind, detail = outcome(ws, sensor)
    assert kind == "invalid" and "channel_response native cannot carry a spectral curve" in detail
    del sensor["engine_overrides"]
    assert outcome(ws, sensor) == ("valid", None)
    vis = copy.deepcopy(ws.get_recipe("synthetic_vis").document)
    assert "engine_overrides" not in vis
    vis["sensor"], vis["settings"][0]["entry_id"] = "auror-nir.yaml", "auror-nir"
    assert outcome(ws, vis) == ("valid", None)


def test_the_s2s_spec_and_its_sensor_library(ws, tmp_path):
    kind, detail = outcome(ws, S2S)
    assert kind == "invalid" and "sensor 'auror-nir.yaml' not found in the sensor library" in detail
    assert "manifold_run_specs/manifold_sensors" in detail
    with_sensors = Workspace.local(work=tmp_path / "w", sensor_library=SENSORS)
    run_id = next(e["run_id"] for e in json.loads((LAYERS / "s2s" / "index.json").read_text()) if e["name"] == S2S.stem)
    assert with_sensors.validate(S2S).runs[0].run_id == run_id and with_sensors.validate(S2S).runs[0].valid
    assert ws.validate(yaml.safe_load(S2S.read_text())).runs[0].valid


def test_a_recipe_file_outside_the_library_composes_as_its_document(ws, tmp_path):
    recipe = ws.get_recipe("auror_ref").document
    path = tmp_path / "my_recipe.yaml"
    path.write_text(yaml.safe_dump(recipe))
    assert outcome(ws, path) == ("valid", None)
    assert outcome(ws, yaml.safe_load(path.read_text())) == ("valid", None)


@pytest.fixture
def own_library(tmp_path):
    lib = tmp_path / "lib"
    for d in ("recipes", "scenarios", "engine_profiles"):
        shutil.copytree(LAYERS / d, lib / d)
    return lib


def _profile_with(lib, name, content_hash):
    profile = yaml.safe_load((lib / "engine_profiles" / "tahoe_static_pose.yaml").read_text())
    if content_hash is None:
        del profile["engine"]["platform"]["ref"]["content_hash"]
    else:
        profile["engine"]["platform"]["ref"]["content_hash"] = content_hash
    (lib / "engine_profiles" / f"{name}.yaml").write_text(yaml.safe_dump(profile))


def test_the_three_hash_states(own_library, tmp_path):
    for name, value in (("missing", None), ("placeholder", "sha256:<hash>"), ("wrong", "sha256:" + "0" * 64)):
        _profile_with(own_library, name, value)
    w = Workspace.local(library=own_library, work=tmp_path / "w", sensor_library=SENSORS)
    base = w.get_recipe("auror_ref").document

    def recipe(profile):
        r = copy.deepcopy(base)
        r["engine_profile"] = profile
        return r
    kind, detail = outcome(w, recipe("missing"))
    assert kind == "invalid" and "'content_hash' is a required property" in detail
    run = w.validate(recipe("placeholder")).runs[0]
    stamp = next(c for c in run.checks if c.check == "content_hash")
    assert run.valid and stamp.passed and "carries a placeholder" in stamp.errors[0].detail
    with pytest.raises(AdmissionError) as e:
        w.submit_run(recipe("placeholder"))
    assert ("Stamp check failed: /engine/platform/ref carry a placeholder instead of a stamped value; run "
            "scripts/stamp_hashes.py") in e.value.problem["detail"]
    kind, detail = outcome(w, recipe("wrong"))
    assert kind == "invalid" and "does not match the file (sha256:bed58062f31a...)" in detail
    assert re.search(r"sha256:[0-9a-f]{12}\.\.\.\)", detail)
    assert not list((tmp_path / "w" / "runs").glob("*/*"))          # nothing was created by the refusal


def test_stamp_hashes_reads_only_the_repository():
    source = (ROOT / "scripts" / "stamp_hashes.py").read_text()
    assert 'files = sorted((ROOT / "manifold_sensors").glob("*.yaml"))' in source
    assert 'run_specs = ROOT / "manifold_run_specs"' in source
    assert 'ROOT / "manifold_config_repo" / name' in source
    assert 'check = "--check" in argv' in source and "argparse" not in source


def test_notebook_five_cells():
    nb = json.loads((ROOT / "notebooks" / "stage_05_sdk_auror_demo.ipynb").read_text())
    cells = nb["cells"]
    code = [i for i, c in enumerate(cells) if c["cell_type"] == "code"]
    assert len(cells) == 24 and len(code) == 11
    assert code == [3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 22]
    assert "has 24 cells, 11 of them code; the first is a pointer to the quick start" in DOC


def test_the_default_roots_point_into_the_checkout():
    from manifold.sim import workspace
    assert workspace.REPOSITORY == Path(workspace.__file__).resolve().parents[5] == ROOT
