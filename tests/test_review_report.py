"""docs/Review_report_since_r27.md against `scripts/review_report.py`: the generated tables are what the records give.

Engine-free: the script reads the results files, the spec index, the sensor library, committed documents and git
history. A block edited by hand, a block removed and a BACKLOG item the report names that BACKLOG.md lacks are each
refused by the check.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("review_report", ROOT / "scripts" / "review_report.py")
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)


def test_the_committed_report_passes_its_check():
    assert rr.check() == []
    assert rr.main(["--check"]) == 0


def test_every_block_is_in_the_report_once():
    text = rr.REPORT.read_text(encoding="utf-8")
    assert set(rr.blocks_in(text)) == set(rr.BLOCKS)
    assert all(text.count(f"<!-- generated: {name} -->") == 1 for name in rr.BLOCKS)


def test_a_hand_edited_number_is_refused(tmp_path):
    text = rr.REPORT.read_text(encoding="utf-8")
    a, b = rr.blocks_in(text)["flux"]
    edited = text[:a] + text[a:b].replace("0.99992", "0.99993", 1) + text[b:]
    assert edited != text
    copy = tmp_path / "report.md"
    copy.write_text(edited, encoding="utf-8")
    assert any("'flux'" in p for p in rr.check(copy))


def test_a_removed_block_is_refused(tmp_path):
    text = rr.REPORT.read_text(encoding="utf-8")
    copy = tmp_path / "report.md"
    copy.write_text(text.replace("<!-- generated: risk-c -->", "").replace("<!-- end generated: risk-c -->", ""),
                    encoding="utf-8")
    assert any("no generated block 'risk-c'" in p for p in rr.check(copy))


def test_a_backlog_item_that_does_not_exist_is_refused(tmp_path):
    copy = tmp_path / "report.md"
    copy.write_text(rr.REPORT.read_text(encoding="utf-8") + '\n`BACKLOG.md` "No such item"\n', encoding="utf-8")
    assert any("No such item" in p for p in rr.check(copy))


def test_the_rounds_table_has_rounds_28_to_36():
    rows = [line for line in rr.rounds_block().splitlines()[2:]]
    assert [r.split(" | ")[0].strip("| ") for r in rows] == [str(n) for n in range(28, 37)]
    assert ".claude_mem" not in rr.rounds_block()


def test_the_space_to_space_blocks_cover_every_record():
    names = {json.loads(l)["spec"] for l in rr.S2S.read_text().splitlines() if l.strip()}
    shown = "\n".join(rr.BLOCKS[b]() for b in ("flux", "unresolved", "blur", "look", "phase"))
    assert all(f"`{n}`" in shown for n in names)


def test_the_risk_blocks_cover_every_record():
    ids = {json.loads(l)["id"] for l in rr.RISK.read_text().splitlines() if l.strip()}
    shown = "\n".join(rr.BLOCKS[b]() for b in ("risk-a", "risk-b", "risk-c", "risk-d", "risk-e", "risk-f", "risk-g"))
    assert all(f"`{i}`" in shown for i in ids)


def test_the_cone_factor_is_the_sensors():
    assert "| exact-cone factor 1 / (1 + 1 / (4 N²)) | 0.981075 |" in rr.aperture_block()


@pytest.mark.parametrize("owner,block", [("MANIFOLD", "manifold"), ("Kevin", "maintainer")])
def test_the_decision_blocks_hold_every_index_row_of_their_owner(owner, block):
    _, index, _ = rr.conops_tables()
    shown = rr.BLOCKS[block]()
    rows = [r["Ask"] for r in index if r["Owner"].startswith(owner)]
    assert rows and all(f"| {a} |" in shown for a in rows)
