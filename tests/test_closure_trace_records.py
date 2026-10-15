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


def test_the_corpus_order_is_breadth_first():
    specs = ct.cw.specs()
    order = ct.order(specs)
    assert sorted(order) == sorted(specs)
    first = {}
    for i, spec in enumerate(order):
        first.setdefault(ct._signature(spec), i)
    assert sorted(first.values()) == list(range(len(first)))      # one spec of every kind before any second one


def test_the_document_table_is_computed_from_the_records():
    text = (ROOT / "docs" / "Closure_walk.md").read_text()
    block = text.split(ct.BEGIN, 1)[1].split(ct.END, 1)[0].strip()
    assert block == ct.table(ct.load())


def test_the_two_passes_agree():
    """The corpus ran twice (section 6.3); every recorded field agrees for every spec except the wall time and the raw
    counts of open calls and per-thread trace files (`opens`, `trace_files`), which vary with the threads a run starts
    (the extra calls are ones the test drops: system files or folders); the first pass predates `elsewhere`."""
    import json
    first = {r["spec"]: r for r in map(json.loads, ct.FIRST_PASS.read_text().splitlines())}
    second = ct.load()
    assert set(first) == {r["spec"] for r in second}
    for r in second:
        keys = (set(r) | set(first[r["spec"]])) - {"seconds", "elsewhere", "opens", "trace_files"}
        assert {k: r.get(k) for k in keys} == {k: first[r["spec"]].get(k) for k in keys}, r["spec"]
        assert r.get("elsewhere", {}) == {}
