"""protodirsig.registry.LocalRegistry must accept the real AUROR_ref run spec and reject a broken
one with a reason naming the failed check.

Reads manifold_run_specs/auror_ref.yaml and manifold_config_repo READ-ONLY; runs a DIRSIG dry run;
writes only to pytest's tmp_path.
"""
import pytest

from protodirsig.registry import LocalRegistry
from test_simulation import CONFIG_REPO, SENSORS, SPEC, broken_spec, needs_dirsig


@needs_dirsig
def test_accepts_real_spec(tmp_path):
    r = LocalRegistry().submit(SPEC, CONFIG_REPO, tmp_path)
    assert r.verdict == "accepted" and r.accepted and r.reasons == []
    assert r.checks == {"schema": True, "resolution": True, "execution": True, "stamped": True}


@needs_dirsig
def test_rejects_missing_scene(tmp_path):
    path = broken_spec(tmp_path, lambda s: s["engine"]["scenes"][0]["ref"].update(name="scenes/no_such_scene"))
    r = LocalRegistry().submit(path, CONFIG_REPO, tmp_path / "work", SENSORS)
    assert r.verdict == "rejected" and not r.accepted
    assert r.checks["schema"] and not r.checks["resolution"]
    assert any(reason.startswith("Resolution check failed") and "no_such_scene" in reason for reason in r.reasons)


def _misspell_fidelity(s):
    s["descriptor"]["fidelty"] = s["descriptor"].pop("fidelity")


def _measured_without_conditions(s):
    s["descriptor"]["settings"][0]["exposure_time"]["provenance"] = "measured"


@needs_dirsig
@pytest.mark.parametrize("edit, where", [
    (_misspell_fidelity, "/descriptor"),
    (lambda s: s["descriptor"]["origin"].update(engine="dirsg"), "/descriptor/origin/engine"),
    (_measured_without_conditions, "/descriptor/settings/0/exposure_time"),
    (lambda s: s["descriptor"]["collection"]["geometry"].pop("range"), "/descriptor/collection/geometry"),
], ids=["misspelled_descriptor_key", "invalid_origin_engine", "measured_without_conditions", "targets_without_range"])
def test_submit_enforces_the_run_spec_schema(tmp_path, edit, where):
    """Admission (LocalRegistry.submit -> Simulation.validate -> schema_errors) rejects what run-spec/1 rejects,
    including the four kinds of violation the hand-written check used to miss."""
    path = broken_spec(tmp_path, edit)
    r = LocalRegistry().submit(path, CONFIG_REPO, tmp_path / "work", SENSORS)
    assert r.verdict == "rejected" and not r.accepted and not r.checks["schema"]
    schema = [reason for reason in r.reasons if reason.startswith("Schema check failed")]
    assert schema and where in schema[0], r.reasons


@needs_dirsig
def test_submissions_carry_their_run_ids(tmp_path):
    """SubmissionResult.run_id is identity.run_id of the submitted spec; each run of a sweep carries its id and the
    sweep the id derived from them."""
    import yaml

    from protodirsig import identity
    from protodirsig.compose import compose_sweep
    r = LocalRegistry().submit(SPEC, CONFIG_REPO, tmp_path / "one", SENSORS)
    assert r.run_id == identity.run_id(yaml.safe_load(SPEC.read_text()), SENSORS) and len(r.run_id) == 64
    recipe = SPEC.parent / "recipes" / "sensor_sweep_tahoe.yaml"
    sub = LocalRegistry().submit_sweep(recipe, CONFIG_REPO, tmp_path / "sweep")
    composed = compose_sweep(recipe)
    assert sub.sweep_id == composed.sweep_id and {n: s.run_id for n, s in sub.runs.items()} == composed.run_ids
    assert all(s.submission.run_id == s.run_id for s in sub.runs.values())


LEO = SPEC.parent / "leo_pass_tahoe.yaml"
REF_CATEGORIES = [                          # (spec, path to the {name, content_hash} object, its JSON Pointer)
    ("sensor", SPEC, ("descriptor", "sensor", "ref"), "/descriptor/sensor/ref"),
    ("scene", SPEC, ("engine", "scenes", 0, "ref"), "/engine/scenes/0/ref"),
    ("platform", SPEC, ("engine", "platform", "ref"), "/engine/platform/ref"),
    ("atmosphere_database", SPEC, ("engine", "atmosphere", "database", "ref"), "/engine/atmosphere/database/ref"),
    ("weather_file", SPEC, ("engine", "weather", "file"), "/engine/weather/file"),
    ("tle", LEO, ("engine", "motion", "orbit", "tle"), "/engine/motion/orbit/tle"),
    ("earth_orientation", LEO, ("engine", "motion", "orbit", "earth_orientation"), "/engine/motion/orbit/earth_orientation"),
]


def _unstamp(spec_path, keys, tmp_path):
    import yaml
    spec = yaml.safe_load(spec_path.read_text())
    node = spec
    for k in keys:
        node = node[k]
    assert "<" not in node["content_hash"], "the repository spec should be stamped"
    node["content_hash"] = "sha256:<hash>"
    path = tmp_path / "unstamped.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    return path


def test_unstamped_refs_of_the_generated_specs_are_empty():
    import yaml

    from protodirsig.run_spec import unstamped_refs
    for path in sorted(SPEC.parent.glob("*.yaml")):
        spec = yaml.safe_load(path.read_text())
        assert unstamped_refs(spec) == [], path.name
        assert spec["engine"]["generator"]["revision"] == "<git-sha>"     # not a content ref; not counted


@pytest.mark.parametrize("name, spec_path, keys, pointer", REF_CATEGORIES, ids=[c[0] for c in REF_CATEGORIES])
def test_unstamped_refs_names_each_category(tmp_path, name, spec_path, keys, pointer):
    import yaml

    from protodirsig.run_spec import unstamped_refs
    assert unstamped_refs(yaml.safe_load(_unstamp(spec_path, keys, tmp_path).read_text())) == [pointer]


@needs_dirsig
@pytest.mark.parametrize("name, spec_path, keys, pointer", REF_CATEGORIES, ids=[c[0] for c in REF_CATEGORIES])
def test_submit_refuses_an_unstamped_reference(tmp_path, name, spec_path, keys, pointer):
    """A placeholder hash passes the schema and validate (the authoring state) but not admission: the run id of an
    unstamped spec would not identify the bytes the run reads."""
    path = _unstamp(spec_path, keys, tmp_path)
    r = LocalRegistry().submit(path, CONFIG_REPO, tmp_path / "work", SENSORS)
    assert r.verdict == "rejected" and r.checks == {"schema": True, "resolution": True, "execution": True,
                                                    "stamped": False}, r.reasons
    (reason,) = r.reasons
    assert reason.startswith("Stamp check failed") and pointer in reason and "scripts/stamp_hashes.py" in reason
    c = r.simulation.validate()
    assert c.passed and c.unstamped == [pointer]
