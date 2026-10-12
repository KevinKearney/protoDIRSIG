"""scripts/status_markers.py: the repository's documents pass, and each rule fails on a document that breaks it."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("status_markers", ROOT / "scripts" / "status_markers.py")
sm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sm)

CN_TABLE = """## 10. Convergence

| ID | Item | Our position | Build | Agreement | Evidence | Outcome |
|---|---|---|---|---|---|---|
| C-01 | a | b | `built` | `agreed` | `tests/test_x.py` | **accepted** |
| C-02 | a | b | `planned` | `proposed` | — | |
"""


def _repo(tmp_path, body):
    (tmp_path / "docs").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_thing():\n    pass\n")
    (tmp_path / sm.CONOPS).write_text("# Doc\n\n" + body + "\n\n" + CN_TABLE + "\nSee C-01 and C-02.\n")
    return tmp_path


def _problems(tmp_path, body):
    return sm.run(_repo(tmp_path, body))[0]


def test_repository_documents_pass():
    problems, _, markers = sm.run()
    assert problems == []
    assert len(markers) > 100


def test_check_exit_status():
    assert sm.main(["--check"]) == 0


@pytest.mark.parametrize("body", [
    "**Thing** `built / proposed` (`tests/test_x.py`).",
    "**Thing** `built / internal`, as `test_thing` shows.",
    "**Thing** `planned / proposed`.",
    "### Admission `open`",
    "**Thing** `built, partial / internal`: only the static form (`tests/test_x.py`).",
    "**Thing** `built / agreed` (C-01, `tests/test_x.py`).",
    "| Item | Build | Agreement |\n|---|---|---|\n| a | `built` (`tests/test_x.py`) | `proposed` |\n| b | — | `open` |",
    "<!-- status-legend -->\n`proposed` alone inside the legend.\n<!-- /status-legend -->",
    "```\n# proposed: inside a code block\n```",
])
def test_allowed(tmp_path, body):
    assert _problems(tmp_path, body) == []


@pytest.mark.parametrize("body, fragment", [
    ("**Thing** `built / maybe` (`tests/test_x.py`).", "outside the legend"),
    ("**Thing** `proposed`.", "one axis"),
    ("**Thing** `built` (`tests/test_x.py`).", "one axis"),
    ("**Thing** `proposed / built`.", "build term comes first"),
    ("**Thing** `open / proposed`.", "build term comes first"),
    ("**Thing** `planned / agreed` (C-02).", "no accepted Outcome"),
    ("**Thing** `planned / agreed`.", "names no C-n"),
    ("**Thing** `built / proposed`.", "without named evidence"),
    ("**Thing** `built / proposed` (`tests/test_gone.py`).", "does not exist"),
    ("**Thing** `built / proposed` (`test_gone`).", "does not exist"),
    ("**Thing** `built, partial / proposed` (`tests/test_x.py`).", "limits"),
    ("## Part `built, partial / proposed`\n\nText `tests/test_x.py`.", "states no limits"),
    ("The pass-through form (proposed) runs.", "unbackticked"),
    ("Status: proposed. More.", "Status:"),
    ("| Item | Status |\n|---|---|\n| a | `built` |", "Status column"),
    ("| Item | Build | Agreement |\n|---|---|---|\n| a | `proposed` | `proposed` |", "does not start with a build term"),
    ("| Item | Build | Agreement |\n|---|---|---|\n| a | `built` (`tests/test_x.py`) | `planned` |", "not an agreement term"),
    ("| Item | Build | Agreement |\n|---|---|---|\n| a | — | `proposed` |", "only with `open`"),
    ("| Item | Build | Agreement |\n|---|---|---|\n| a | `built` | `internal` |", "without named evidence"),
    ("| Item | Build | Agreement |\n|---|---|---|\n| a | `built, partial` (`tests/test_x.py`) | `internal` |", "without its limits"),
])
def test_refused(tmp_path, body, fragment):
    problems = _problems(tmp_path, body)
    assert any(fragment in p for p in problems), problems
