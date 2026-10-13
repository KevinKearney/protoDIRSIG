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


def test_risk_b_concurrent_jobs_repeat_the_single_job_bytes_and_the_limit_model_recomputes():
    recs = {r["id"]: r for r in of("B")}
    for size in ("small", "native"):
        assert {recs[f"{size}-n{n}"]["measured"]["n"] for n in (1, 2, 4, 8)} == {1, 2, 4, 8}
    for r in recs.values():
        if r["id"] == "limit-model":
            continue
        ms = r["measured"]
        assert ms["digests_equal_single"] and ms["failed_jobs"] == 0 and ms["swap_pages_out"] == 0
        assert r["configuration"]["threads"] == 1
    tput = [recs[f"native-n{n}"]["measured"]["throughput_jobs_per_hour"] for n in (1, 2, 4, 8)]
    assert tput == sorted(tput)                      # more copies never lowered throughput up to 8
    model = recs["limit-model"]["measured"]
    peak = max(j["peak_rss_kib"] for r in recs.values() if r["id"] != "limit-model" for j in r["measured"]["jobs"])
    assert model["peak_rss_gib"] == round(peak / 2**20, 4) and model["limit"] == 4


def test_risk_c_a_cancelled_dirsig_run_lists_only_its_spec_but_leaves_byte_exact_leading_rows():
    recs = of("C")
    assert sorted(round(r["measured"]["fraction"], 2) for r in recs) == [0.25, 0.5, 0.75]
    rows = []
    for r in recs:
        ms = r["measured"]
        assert ms["verdict"] == "incomplete" and ms["listed"] == ["run_spec.json"] and ms["usable"]
        img = ms["on_disk"]["AurorNIROutput.img"]
        assert img["prefix_equal_full"] and img["header_lines"] <= img["rows_on_disk"] < img["rows_total"]
        rows.append(img["rows_on_disk"])
    assert rows == sorted(rows)
