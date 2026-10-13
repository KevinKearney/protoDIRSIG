"""The known-risk results file (`docs/data/risk_measurements.jsonl`, kept by `scripts/risk_measure.py`): it is well formed,
its derived numbers recompute, and each risk's records say what docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md section 10.1
reports from them.

Engine-free: the records are read, nothing is rendered or cancelled.
"""
import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("risk_measure", ROOT / "scripts" / "risk_measure.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

RECORDS = m.load_results()


def of(risk):
    return [r for r in RECORDS if r["risk"] == risk]


def test_the_results_file_is_well_formed():
    assert RECORDS and m.check() == []


def test_the_check_catches_a_derived_number_that_does_not_recompute(tmp_path):
    bad = copy.deepcopy(of("A")[0])
    bad["measured"]["digests_equal"] = not bad["measured"]["digests_equal"]
    assert m.record_problems(bad) == ["digests_equal does not follow from products"]
    path = tmp_path / "r.jsonl"
    m.write_results([of("A")[0], of("A")[0]], path)
    assert any("recorded twice" in p for p in m.check(path))


def test_risk_a_layered_jobs_write_nothing_in_home_and_home_does_not_change_the_product():
    recs = of("A")
    assert {tuple(r["configuration"]["roi"]) for r in recs} >= {(16, 16), (500, 500)}     # a small and a native job
    for r in recs:
        ms = r["measured"]
        assert ms["home_writes"] == 0 and ms["user_home_documents_dirsig_unchanged"] and ms["fresh_home_files_after"] == 0
        assert ms["digests_equal"] and len(ms["products"]) == 3
        read = [p["path"] for p in ms["home_paths"] if p["found_in_user_home"]]
        assert read == ["$HOME/.config/Rochester Institute of Technology/DIRSIG.conf"]
