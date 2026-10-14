"""The documents against each other and against the repository (round 37's consistency pass).

Scope: every committed Markdown file under `docs/`, `README.md`, and every committed Markdown file and notebook under
`notebooks/` (a notebook's markdown cells for links; all its cells for the rest). Engine-free; nothing is rendered or
executed.

- Every relative link (`[text](target)`, an `#anchor` dropped) resolves to a file or folder in the repository.
- Every `scripts/...` or `tests/...` path a document names exists (a pattern with `*`, `<` or `{` is skipped, and so is
  a path inside a link's target, which the link rule covers).
- Every backticked repository path with a file extension (its first folder one of the repository's top-level folders:
  `docs/...md`, `notebooks/...ipynb`, `manifold_run_specs/...yaml` and so on) exists.
- Every `C-n` a document names has a row in the CONOPS decisions index (section 10.1); a retired id (section 10 names
  id 13) has none, so it is not cited.
- Every command in a code fence that runs `python scripts/<name>.py` names a script that exists, and each `--option`
  it passes is one the script defines (the rule of `tests/test_authoring_guide.py`, applied to every document).
- No document cites `.claude_mem/` (the relay's working notes are not a human document).
"""
import json
import re
import shlex
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONOPS = ROOT / "docs" / "MANIFOLD_DIRSIG_CONOPS_and_Guide.md"


def documents():
    """The committed documents in scope (`git ls-files`; a gitignored folder such as `notebooks/dev/` is no document)."""
    try:
        tracked = subprocess.run(["git", "ls-files", "docs", "notebooks", "README.md"], cwd=ROOT, check=True,
                                 capture_output=True, text=True).stdout.split()
        paths = [ROOT / p for p in tracked]
    except (OSError, subprocess.CalledProcessError):            # not a checkout: every file on disk
        paths = [*(ROOT / "docs").rglob("*"), ROOT / "README.md", *(ROOT / "notebooks").rglob("*")]
    return sorted(p for p in paths if p.is_file() and p.suffix in (".md", ".ipynb") and ".ipynb_checkpoints" not in p.parts)


def cells(path):
    """[(kind, text)]: one markdown cell for a Markdown file; a notebook's cells."""
    if path.suffix == ".md":
        return [("markdown", path.read_text(encoding="utf-8"))]
    nb = json.loads(path.read_text(encoding="utf-8"))
    return [(c["cell_type"], "".join(c["source"])) for c in nb["cells"]]


DOCS = documents()
IDS = [str(p.relative_to(ROOT)) for p in DOCS]

LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMAGE = re.compile(r"!\[[^\]\n]*\]\(([^)\s]+)\)")
PATH = re.compile(r"(?<![\w./~$-])((?:scripts|tests)/[\w./-]*\w)")
CN = re.compile(r"\bC-(\d{2})\b")
FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.M | re.S)
COMMAND = re.compile(r"(?:^|[\s;&|(!])(?:\S*/)?python3?\s+(scripts/\w+\.py)\b([^\n]*)")


def external(target):
    return re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#")


@pytest.mark.parametrize("doc", DOCS, ids=IDS)
def test_every_relative_link_resolves(doc):
    bad = []
    for kind, text in cells(doc):
        if kind != "markdown":
            continue
        for m in list(LINK.finditer(text)) + list(IMAGE.finditer(text)):
            target = m.group(1).split("#", 1)[0]
            if not target or external(m.group(1)):
                continue
            if not (doc.parent / target).exists():
                bad.append(m.group(0))
    assert not bad, f"{doc.relative_to(ROOT)}: links that resolve to nothing: {bad}"


def named_paths(text):
    text = LINK.sub(lambda m: m.group(0).split("](", 1)[0], text)       # a link's target is the link rule's
    for m in PATH.finditer(text):
        p = m.group(1).split("::", 1)[0].rstrip(".")
        if any(ch in text[m.start():m.end() + 1] for ch in "*<{"):
            continue
        yield p


@pytest.mark.parametrize("doc", DOCS, ids=IDS)
def test_every_named_script_and_test_path_exists(doc):
    missing = sorted({p for _, text in cells(doc) for p in named_paths(text) if not (ROOT / p).exists()})
    assert not missing, f"{doc.relative_to(ROOT)}: names paths that do not exist: {missing}"


CODE = re.compile(r"`([^`\s]+)`")
EXTENSION = re.compile(r"\.(md|ipynb|py|ya?ml|jsonl?|gz|tsv|svg|png|mmd)$")
TOP = sorted(p.name for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith("."))


def repository_paths(text):
    for m in CODE.finditer(text):
        p = m.group(1).rstrip(".,;:")
        if "/" in p and p.split("/", 1)[0] in TOP and EXTENSION.search(p) and not any(c in p for c in "*<{$~"):
            yield p


@pytest.mark.parametrize("doc", DOCS, ids=IDS)
def test_every_backticked_repository_file_exists(doc):
    missing = sorted({p for _, text in cells(doc) for p in repository_paths(text) if not (ROOT / p).exists()})
    assert not missing, f"{doc.relative_to(ROOT)}: names files that do not exist: {missing}"


def decision_index():
    """The C-n of the section 10.1 index, and the retired ids section 10 names."""
    text = CONOPS.read_text(encoding="utf-8")
    index = text.split("### 10.1 Decisions needed", 1)[1].split("\n## ", 1)[0]
    rows = {int(n) for n in re.findall(r"^\| C-(\d{2}) \|", index, re.M)}
    retired = {int(n) for n in re.findall(r"id (\d+) was retired", text)}
    return rows, retired


def test_the_decision_index_is_found():
    rows, retired = decision_index()
    assert len(rows) > 40 and retired == {13} and not rows & retired


@pytest.mark.parametrize("doc", DOCS, ids=IDS)
def test_every_c_number_has_a_row_in_the_decisions_index(doc):
    rows, _ = decision_index()
    named = {int(n) for _, text in cells(doc) for n in CN.findall(text)}
    assert not named - rows, f"{doc.relative_to(ROOT)}: C-numbers with no row in section 10.1: {sorted(named - rows)}"


def commands(text):
    """(script, argv) of each `python scripts/<name>.py ...` in the code fences of a markdown text."""
    for body in FENCE.findall(text):
        body = body.replace("\\\n", " ")
        for line in body.splitlines():
            line = line.split(" #", 1)[0]
            for m in COMMAND.finditer(line):
                rest = re.split(r"[;&|>]", m.group(2), maxsplit=1)[0]
                try:
                    yield m.group(1), shlex.split(rest)
                except ValueError:
                    yield m.group(1), rest.split()


def notebook_commands(doc):
    for kind, text in cells(doc):
        if kind == "markdown":
            yield from commands(text)
        else:                                                   # shell escapes in code cells
            for line in text.splitlines():
                if line.lstrip().startswith("!"):
                    yield from commands(f"```\n{line.lstrip()[1:]}\n```\n")


@pytest.mark.parametrize("doc", DOCS, ids=IDS)
def test_a_fenced_command_uses_only_options_its_script_defines(doc):
    bad = []
    for script, argv in notebook_commands(doc):
        path = ROOT / script
        if not path.is_file():
            bad.append(f"{script}: no such script")
            continue
        source = path.read_text(encoding="utf-8")
        for arg in argv:
            if arg.startswith("--") and len(arg) > 2:
                name = arg.split("=", 1)[0]
                if f'"{name}"' not in source and f"'{name}'" not in source:
                    bad.append(f"{script} defines no option {name}")
    assert not bad, f"{doc.relative_to(ROOT)}: {sorted(set(bad))}"


@pytest.mark.parametrize("doc", DOCS, ids=IDS)
def test_no_document_cites_the_relay_notes(doc):
    assert not any(".claude_mem" in text for _, text in cells(doc)), f"{doc.relative_to(ROOT)} cites .claude_mem/"


def test_the_scope_is_the_documents():
    assert CONOPS in DOCS and ROOT / "README.md" in DOCS
    assert any(p.suffix == ".ipynb" for p in DOCS) and len(DOCS) > 25
