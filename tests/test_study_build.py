"""The space-to-space study (`docs/study/`, `scripts/study_build.py`): the committed files are what the builder writes from
the records, every table and figure the manuscript names exists, every number in the manuscript's prose is a field, and
the study cites no working notes.

Engine-free: nothing is rendered; the builder reads the committed records and `git log`.
"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "docs" / "study"
spec = importlib.util.spec_from_file_location("study_build", ROOT / "scripts" / "study_build.py")
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)


def test_check_passes():
    assert sb.check() == []


def test_every_table_and_figure_the_manuscript_names_exists():
    text = (STUDY / "manuscript.md").read_text()
    tables, figures = sb.referenced()
    assert tables and figures
    for t in tables:
        assert (STUDY / "tables" / f"{t}.md").is_file(), t
    for f in figures:
        assert (STUDY / "figures" / f"{f}.png").is_file(), f
        assert (STUDY / "figures" / f"{f}.pdf").is_file(), f
    for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        assert (STUDY / target).is_file(), target
    assert len(re.findall(r"^Table: ", text, flags=re.M)) == len(tables)


def test_a_number_typed_into_the_prose_is_refused():
    template = (STUDY / "manuscript.template.md").read_text()
    assert sb.stray_numbers(template) == []
    bad = template.replace("# Limitations {#sec:limitations}", "# Limitations {#sec:limitations}\n\nThe window moves it by 1.3 %.")
    assert [line for _, line in sb.stray_numbers(bad)] == ["The window moves it by 1.3 %."]


def test_every_field_resolves_to_a_record_or_a_cited_figure():
    st = sb.Study()
    _, used = sb.render(st)
    ids = {r["id"] for r in st.data}
    for section, field, text, refs in used:
        assert text != "", field
        for ref in refs:
            if ref.startswith("doc:"):
                assert ref[4:] in st.doc, ref
            elif not ref.startswith(("table:", "figure:")):
                assert ref in ids, (field, ref)


def test_every_record_has_a_reproduce_entry_and_a_commit():
    rows = sb.load_consolidated()
    assert len(rows) == len(sb.s2s_records()) + len(sb.risk_records())
    for r in rows:
        assert tuple(k for k in r if k not in ("record", "reproduce")) == sb.COLUMNS
        assert not r["source"].startswith(str(ROOT))
        assert r["reproduce"]["configuration"], r["id"]
        assert r["relay_host"] in ("yes", "no", "manual"), r["id"]
        if r["dataset"] == "s2s":
            assert r["reproduce"]["command"].startswith("python scripts/s2s_measure.py run " + r["id"])
            assert (ROOT / r["reproduce"]["spec"]).is_file()
            assert r["commit"], r["id"]


def test_the_log_figures_name_a_commit_and_no_working_notes():
    import csv
    import subprocess
    with (STUDY / "data" / "log_figures.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows and list(rows[0]) == ["id", "value", "round", "definition", "commit"]
    for r in rows:
        assert subprocess.run(["git", "cat-file", "-e", r["commit"]], cwd=ROOT).returncode == 0, r["commit"]


def test_no_working_notes_are_cited_in_the_study():
    for path in STUDY.rglob("*"):
        if path.is_file():
            assert b".claude_mem" not in path.read_bytes(), path


def test_the_docs_consistency_test_covers_the_study():
    spec = importlib.util.spec_from_file_location("docs_consistency", ROOT / "tests" / "test_docs_consistency.py")
    dc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dc)
    docs = {p.relative_to(ROOT).as_posix() for p in dc.documents()}
    for name in ("manuscript.md", "manuscript.template.md", "README.md", "claims.md"):
        assert f"docs/study/{name}" in docs
