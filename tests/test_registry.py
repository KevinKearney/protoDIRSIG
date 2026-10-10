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
    assert r.checks == {"schema": True, "resolution": True, "execution": True}


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
