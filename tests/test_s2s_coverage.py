"""The space-to-space coverage map (`docs/s2s_coverage.md`, written by `scripts/s2s_coverage.py` from
`docs/data/s2s_results.jsonl`): the committed document is current, every record is classified, and every empty cell
states why. Engine-free: nothing is rendered."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("s2s_coverage", ROOT / "scripts" / "s2s_coverage.py")
cov = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cov)

RECORDS = cov.classified()


def test_the_committed_map_passes_its_check():
    assert cov.main(["--check"]) == 0


def test_every_record_has_one_shape_one_background_and_one_class():
    shapes = [row for group, row, _, _ in cov.RULES if group == "Shape"]
    backgrounds = [row for group, row, _, _ in cov.RULES if group == "Background"]
    cs = cov.cells(RECORDS)
    for rows in (shapes, backgrounds):
        counted = [r["spec"] for row in rows for c in cov.CLASSES for r, _ in cs[(row, c)]]
        assert sorted(counted) == sorted(r["spec"] for r, _ in RECORDS)
    assert {a["size_class"] for _, a in RECORDS} <= set(cov.CLASSES)


def test_the_size_classes_follow_the_pixel_footprint():
    by = {r["spec"]: a for r, a in RECORDS}
    assert by["s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0"]["size_class"] == "hyperresolved"
    assert by["s2s-hyperresolved-r100km-v0mps-e5ms-l0-z0-d0"]["size_class"] == "resolved"      # 6.1 px
    assert by["s2s-unresolved-r12p5km-v0mps-e5ms-l0-z0-d0"]["size_class"] == "resolved"        # 1.22 px
    assert by["s2s-unresolved-r200km-v0mps-e5ms-l0-z0-d0"]["size_class"] == "unresolved"
    assert by["s2s3-phase-unresolved-a0-l0-z0"]["size_class"] == "unresolved"                  # 0.61 px


def test_a_stale_document_is_refused(tmp_path, monkeypatch):
    doc = tmp_path / "s2s_coverage.md"
    doc.write_text(cov.DOC.read_text().replace("| Motion | Platform motion |", "| Motion | Platform motion  |"))
    monkeypatch.setattr(cov, "DOC", doc)
    assert cov.main(["--check"]) == 1


def test_an_empty_cell_without_a_reason_is_refused(monkeypatch):
    key = next(k for k, got in cov.cells(RECORDS).items() if not got)
    monkeypatch.setattr(cov, "EMPTY", {k: v for k, v in cov.EMPTY.items() if k != key})
    assert any("states no reason" in p for p in cov.problems(RECORDS))
    assert "NO REASON STATED" in cov.document(RECORDS)


def test_a_reason_for_a_filled_cell_is_refused(monkeypatch):
    key = next(k for k, got in cov.cells(RECORDS).items() if got)
    monkeypatch.setattr(cov, "EMPTY", {**cov.EMPTY, key: "stale"})
    assert any("still states a reason" in p for p in cov.problems(RECORDS))
