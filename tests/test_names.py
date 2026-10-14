"""Name-derived strings live in one module (`_names`): no string literal in the package source or the scripts spells
the package's legacy name, outside the names module and the allowlist below. Docstrings and comments are prose, not
literals, and are not checked; imports are statements, not literals."""
import ast
from pathlib import Path

from manifold.core import _names

ROOT = Path(__file__).resolve().parents[1]
NAMES_MODULE = "_names.py"
ALLOWLIST = {}                                                   # root-relative path: why the literal stays
SHIM_DIRS = ("packages/compat-protodirsig",)                     # the compatibility shim spells the legacy name


def _sources():
    files = list((ROOT / "src").rglob("*.py")) + list((ROOT / "packages").glob("*/src/**/*.py")) \
        + list((ROOT / "scripts").glob("*.py"))
    return sorted(p for p in files if not p.relative_to(ROOT).as_posix().startswith(SHIM_DIRS))


def _docstrings(tree):
    nodes = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    return {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, nodes) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)
            and isinstance(n.body[0].value.value, str)}


def legacy_literals(path, legacy=_names.LEGACY_PACKAGE):
    """(line, literal) of each non-docstring string or bytes literal in `path` that contains `legacy` in any case."""
    tree = ast.parse(path.read_text())
    docs = _docstrings(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)) and id(node) not in docs:
            text = node.value if isinstance(node.value, str) else node.value.decode("latin-1")
            if legacy.lower() in text.lower():
                out.append((node.lineno, text))
    return sorted(out)


def test_no_source_literal_spells_the_legacy_name():
    found = {}
    for path in _sources():
        rel = path.relative_to(ROOT).as_posix()
        if path.name == NAMES_MODULE or rel in ALLOWLIST:
            continue
        hits = legacy_literals(path)
        if hits:
            found[rel] = hits
    assert found == {}, "use the constants in _names: " + repr(found)


def test_the_check_finds_a_literal_and_ignores_docstrings_and_imports(tmp_path):
    legacy = _names.LEGACY_PACKAGE
    src = tmp_path / "m.py"
    src.write_text(f'"""Docs about {legacy}."""\nimport os\nX = "{legacy.upper()}_THING"\n'
                   f'def f():\n    """{legacy} again."""\n    return b"{legacy}.worker"\n')
    assert legacy_literals(src) == [(3, f"{legacy.upper()}_THING"), (6, f"{legacy}.worker")]


def test_the_allowlist_names_files_that_exist_and_still_need_it():
    for rel in ALLOWLIST:
        assert legacy_literals(ROOT / rel), f"{rel} no longer spells the legacy name; drop it from the allowlist"


def test_the_constructors_follow_the_constants():
    assert _names.env("CONTRACTS") == _names.ENV_PREFIX + "CONTRACTS"
    assert _names.module("worker") == _names.PACKAGE + ".worker"
    assert _names.problem("compose") == _names.URN_PREFIX + "compose"
    assert _names.FROZEN_IDENTITY_STRINGS == ()                        # the round 17 audit found none
