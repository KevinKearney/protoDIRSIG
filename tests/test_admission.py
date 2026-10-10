"""Engine-free validation (protodirsig.admission.validate_spec) and `Simulation.validate(engine_check)`.

validate_spec reports each failure the registry tests cover without raising and never runs an engine;
`Simulation.validate("none")` stops before the dry run; `Simulation.validate()` is unchanged.
"""
import copy

import pytest

from protodirsig import identity, simulation
from protodirsig.admission import validate_spec
from protodirsig.run_spec import load_run_spec
from protodirsig.simulation import Simulation
from test_simulation import CONFIG_REPO, SENSORS, SPEC, needs_dirsig

needs_config_repo = pytest.mark.skipif(not (CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene").is_file(),
                                       reason="manifold_config_repo not present")


def _spec(edit=None):
    spec = copy.deepcopy(load_run_spec(SPEC))
    if edit:
        edit(spec)
    return spec


@needs_config_repo
def test_a_valid_spec_is_valid_without_an_engine():
    r = validate_spec(_spec(), SPEC, CONFIG_REPO)
    assert (r.valid, r.schema_ok, r.resolution_ok, r.engine_checked, r.unstamped) == (True, True, True, False, [])
    assert r.run_id == identity.run_id(load_run_spec(SPEC), SENSORS) and r.run is not None


@needs_config_repo
@pytest.mark.parametrize("edit, schema_ok, resolution_ok, unstamped, text", [
    (lambda s: s["engine"]["motion"].update(kind="bogus"), False, False, [], "/engine/motion/kind"),
    (lambda s: s["engine"]["scenes"][0]["ref"].update(name="scenes/no_such_scene"), True, False, [], "no_such_scene"),
    (lambda s: s["engine"]["platform"]["ref"].update(content_hash="sha256:" + "1" * 64), True, False, [], "stamp_hashes"),
    (lambda s: s["engine"]["platform"]["ref"].update(content_hash="sha256:<hash>"), True, True, ["/engine/platform/ref"],
     None),
], ids=["bad_schema", "unresolvable_reference", "hash_mismatch", "placeholder"])
def test_each_failure_is_reported_not_raised(edit, schema_ok, resolution_ok, unstamped, text):
    r = validate_spec(_spec(edit), SPEC, CONFIG_REPO)
    assert (r.schema_ok, r.resolution_ok, r.unstamped, r.engine_checked) == (schema_ok, resolution_ok, unstamped, False)
    assert r.valid == (schema_ok and resolution_ok)
    if text:
        assert text in " ".join(r.schema_errors + r.resolution_mismatches)


def test_a_spec_that_is_not_a_mapping_is_reported():
    r = validate_spec(["not", "a", "spec"], SPEC, CONFIG_REPO)
    assert not r.valid and r.run is None and r.run_id is None


@needs_config_repo
def test_validate_none_runs_no_engine(tmp_path, monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("_run_dirsig called at engine_check='none'")
    monkeypatch.setattr(simulation, "_run_dirsig", refuse)
    monkeypatch.setattr(Simulation, "_assemble", refuse)
    c = Simulation.from_run_spec(SPEC, CONFIG_REPO, tmp_path).validate("none")
    assert c.passed and not c.engine_checked and c.execution_ok and c.execution_error is None
    assert c.execution_log is None and not (tmp_path / "validate").exists()


@needs_config_repo
def test_validate_none_reports_what_validate_spec_reports(tmp_path):
    path = tmp_path / "bad.yaml"
    import yaml
    path.write_text(yaml.safe_dump(_spec(lambda s: s["engine"]["weather"]["file"].update(name="weather/none.wth"))))
    c = Simulation.from_run_spec(path, CONFIG_REPO, tmp_path / "w", SENSORS).validate("none")
    r = validate_spec(yaml.safe_load(path.read_text()), path, CONFIG_REPO, SENSORS)
    assert not c.passed and c.resolution_mismatches == r.resolution_mismatches and c.unstamped == r.unstamped


def test_validate_rejects_an_unknown_level(tmp_path):
    with pytest.raises(ValueError):
        Simulation.from_run_spec(SPEC, CONFIG_REPO, tmp_path).validate("full")


@needs_dirsig
def test_validate_with_no_argument_still_runs_the_dry_run(tmp_path):
    c = Simulation.from_run_spec(SPEC, CONFIG_REPO, tmp_path).validate()
    assert c.passed and c.engine_checked and c.execution_log is not None
