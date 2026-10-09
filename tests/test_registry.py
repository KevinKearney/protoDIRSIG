"""protodirsig.registry.LocalRegistry must accept the real AUROR_ref run spec and reject a broken
one with a reason naming the failed check.

Reads run_specs/auror_ref.yaml and config_repo READ-ONLY; runs a DIRSIG dry run;
writes only to pytest's tmp_path.
"""
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
