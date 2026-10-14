"""scripts/export_sweep_digests.py on synthetic sweep results, and the committed table's structure."""
import gzip
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("export_sweep_digests", ROOT / "scripts" / "export_sweep_digests.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


def _out(name, i):
    return {"name": name, "size": i, "sha256": f"{i:064x}"}


RECORDS = [
    {"type": "attempt", "demo": "A1", "simulation": "demo.sim", "outcome": "rendered", "repeat": False, "wall_s": 4.0,
     "max_cpu_temp_c": 95.0, "outputs": [_out("b.img", 2), _out("a.img", 1)]},
    {"type": "attempt", "demo": "A1", "simulation": "demo.sim", "outcome": "rendered", "repeat": True,
     "outputs": [_out("a.img", 1), _out("b.img", 3)]},
    {"type": "attempt", "demo": "F1", "simulation": "demo.jsim", "outcome": "failed", "repeat": False, "outputs": [],
     "log_tail": ["[error] secret path /home/u/x"]},
    {"type": "demo", "demo": "A1", "outcome": "rendered", "attempts": []},
    {"type": "stop", "reason": "candidates exhausted"},
]


def _write(tmp_path, records, cut=False):
    p = tmp_path / "results.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in records) + ('{"cut' if cut else ""))
    return p


def test_one_line_per_attempt_with_digests_only(tmp_path):
    results, out = _write(tmp_path, RECORDS, cut=True), tmp_path / "t.jsonl.gz"
    assert export.main(["--results", str(results), "--out", str(out)]) == 0
    lines = [json.loads(x) for x in gzip.decompress(out.read_bytes()).decode().splitlines()]
    assert lines == [
        {"demo": "A1", "simulation": "demo.sim", "outcome": "rendered", "repeat": False, "output_count": 2,
         "outputs": [_out("a.img", 1), _out("b.img", 2)]},
        {"demo": "A1", "simulation": "demo.sim", "outcome": "rendered", "repeat": True, "output_count": 2,
         "outputs": [_out("a.img", 1), _out("b.img", 3)]},
        {"demo": "F1", "simulation": "demo.jsim", "outcome": "failed", "repeat": False, "output_count": 0, "outputs": []}]
    assert b"secret" not in gzip.decompress(out.read_bytes())                  # no log lines, no measurements


def test_the_bytes_are_reproducible_and_check_compares_them(tmp_path, capsys):
    results, out = _write(tmp_path, RECORDS), tmp_path / "t.jsonl.gz"
    export.main(["--results", str(results), "--out", str(out)])
    first = out.read_bytes()
    export.main(["--results", str(results), "--out", str(out)])
    assert out.read_bytes() == first
    assert export.main(["--check", "--results", str(results), "--out", str(out)]) == 0
    assert export.main(["--check", "--out", str(out)]) == 0
    changed = _write(tmp_path, [{**RECORDS[0], "outputs": [_out("a.img", 9)]}] + RECORDS[1:])
    assert export.main(["--check", "--results", str(changed), "--out", str(out)]) == 1
    out.write_bytes(b"not gzip")
    assert export.main(["--check", "--out", str(out)]) == 1
    assert export.main(["--check", "--out", str(tmp_path / "missing.gz")]) == 1


def test_a_table_over_the_limit_keeps_the_first_outputs(tmp_path):
    many = [{"type": "attempt", "demo": "L1", "simulation": "demo.sim", "outcome": "rendered", "repeat": False,
             "outputs": [_out(f"f{i:04d}.img", i) for i in range(300)]}]
    data, truncated = export.table(many, limit=100, keep=5)
    lines = [json.loads(x) for x in gzip.decompress(data).decode().splitlines()]
    assert truncated and lines[0] == {"truncated": 5}
    assert lines[1]["output_count"] == 300 and [o["name"] for o in lines[1]["outputs"]] == [f"f{i:04d}.img" for i in range(5)]
    assert export.check_structure(data) == []
    assert export.table(many)[1] is False


def test_the_committed_table_is_well_formed():
    assert export.OUT.is_file() and export.check_structure(export.OUT.read_bytes()) == []
