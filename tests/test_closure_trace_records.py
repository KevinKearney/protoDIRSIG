"""The closure test's records (round 47 B to D): `docs/data/closure_trace.jsonl` holds one record per traced tree,
written by `scripts/closure_trace.py`; `docs/Closure_walk.md` section 6.2 lists the first record's files in full. The
trees are not rerun here."""
import importlib.util
import re
from pathlib import Path

from manifold.engines.dirsig import roles

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("closure_trace_script", ROOT / "scripts" / "closure_trace.py")
ct = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ct)
STEP_B = "manifold_run_specs/s2s/s2s-hyperresolved-r100km-v0mps-e5ms-l0-z0-d0-w64.yaml"
SETS = ("listed_not_in_job", "in_job_not_listed", "read_in_neither", "generated", "listed_not_read")


def test_records_are_unique_committed_dirsig_specs():
    specs = [r["spec"] for r in ct.load()]
    assert len(specs) == len(set(specs))
    assert set(specs) <= set(ct.cw.specs())


def test_records_are_well_formed():
    for r in ct.load():
        if "walked" not in r:
            assert not r["ran"] and r["error"]
            continue
        assert r["threads"] == 2 and r["unparsed"] == 0
        assert r["walked"] == len(r["roles"]) and set(r["roles"].values()) <= set(roles.ROLES) | {None}
        assert set(r["generated"]) <= set(r["read_in_neither"]) and set(r["generated"]) <= set(r["written"])
        assert set(r["listed_not_read"]) <= set(r["roles"]) and not set(r["listed_not_read"]) & set(r["read_by"])
        assert set(r["read_in_neither"]) <= set(r["read_by"]) and not set(r["read_in_neither"]) & set(r["roles"])
        assert set(r["install_listed_not_read"]) <= set(r["install_listed"])
        assert r["read"] == len(r["read_by"])
        assert r["library_written"] == []                 # the library is never written


def test_the_first_record_is_step_b_and_the_document_lists_it():
    r = ct.load()[0]
    assert r["spec"] == STEP_B and r["mode"] == "layered" and r["ran"]
    text = (ROOT / "docs" / "Closure_walk.md").read_text()
    section = text.split("### 6.2 One tree in full", 1)[1].split("\n### ", 1)[0]
    listed = dict(re.findall(r"^\| `([^`]+)` \| (?:`([^`]+)`|none \(not walked\)) \|", section, re.M))
    assert set(listed) == set(r["roles"]) | set(r["read_by"])
    for path, role in listed.items():
        assert (role or None) == r["roles"].get(path)
    assert {k: r[k] for k in SETS} == {"listed_not_in_job": [], "in_job_not_listed": [],
                                       "read_in_neither": ["auror_ref/s2s_targets.scene.hdf"],
                                       "generated": ["auror_ref/s2s_targets.scene.hdf"], "listed_not_read": []}
