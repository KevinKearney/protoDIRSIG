"""`docs/Handover_s2s_thread.md` (round 43) against what it quotes: every commit of its round map exists and the rounds
follow one another in the history, every C-n row states what the CONOPS decisions index states, and its suite count is
the review report's. Engine-free; reads committed files and `git`."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "Handover_s2s_thread.md").read_text()
CONOPS = (ROOT / "docs" / "MANIFOLD_DIRSIG_CONOPS_and_Guide.md").read_text()
REPORT = (ROOT / "docs" / "Review_report_since_r27.md").read_text()


def _section(text, heading):
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def test_every_commit_of_the_round_map_exists_in_order():
    rows = re.findall(r"^\| (\d+) \| `([0-9a-f]{7})`\.\.(?:`([0-9a-f]{7})`)? \|", _section(DOC, "## 4."), re.M)
    assert [int(r[0]) for r in rows] == list(range(28, 44))
    commits = [c for _, first, last in rows for c in (first, last) if c]
    for c in commits:
        assert _git("cat-file", "-e", c + "^{commit}").returncode == 0, c
    for older, newer in zip(commits, commits[1:]):
        assert _git("merge-base", "--is-ancestor", older, newer).returncode == 0, (older, newer)


def test_the_decision_rows_state_what_the_index_states():
    index = CONOPS.split("### 10.1 Decisions needed", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| (C-\d{2}) \| [^|]+ \| MANIFOLD \| (yes|no) \| ([^|]+) \|", index, re.M)
    want = {c: (blocks, state.strip()) for c, blocks, state in rows}
    got = re.findall(r"^\| (C-\d{2}) \| [^|]+ \| (yes|no) \| ([^|]+) \|", _section(DOC, "## 7."), re.M)
    assert [c for c, _, _ in got] == [f"C-{n}" for n in range(34, 45)]
    for c, blocks, state in got:
        assert want[c][0] == blocks and want[c][1].startswith(state.strip().split(" (")[0]), c


def test_the_suite_count_is_the_review_reports():
    count = re.search(r"\| (\d+) passed, 2 skipped \(about 10 minutes", REPORT).group(1)
    assert f"({count} passed, 2 skipped at round 43)" in DOC
