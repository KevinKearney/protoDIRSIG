"""The corpus closure walk (round 46 D): `docs/data/closure_walk.jsonl` holds one record per committed DIRSIG run spec,
and the table in `docs/Closure_walk.md` is the one `scripts/closure_walk.py` computes from those records. The trees are
not rebuilt here (`python scripts/closure_walk.py --work DIR` does that)."""
import importlib.util
from pathlib import Path

from manifold.engines.dirsig import roles
from manifold.engines.dirsig.closure import VIOLATION_KINDS

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("closure_walk", ROOT / "scripts" / "closure_walk.py")
cw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cw)


def test_one_record_per_committed_dirsig_spec():
    assert [r["spec"] for r in cw.load()] == cw.specs()


def test_records_are_well_formed():
    for r in cw.load():
        assert r["mode"] in ("layered", "passthrough")
        if not r["built"]:
            assert r["reason"]
            continue
        assert set(r["roles"]) <= set(roles.ROLES) | {"(none)"}
        assert r["roles"].get(roles.ENTRY_ROLE) == 1
        assert sum(r["roles"].values()) == r["files"]
        assert len(r["unroled"]) == r["roles"].get("(none)", 0)
        assert set(r["violations"]) <= set(VIOLATION_KINDS)
        assert ("symlink" in r["violations"]) == bool(r["links"])


def test_the_document_table_is_computed_from_the_records():
    text = (ROOT / "docs" / "Closure_walk.md").read_text()
    block = text.split(cw.BEGIN, 1)[1].split(cw.END, 1)[0].strip()
    assert block == cw.table(cw.load())
