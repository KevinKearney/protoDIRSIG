"""The notebooks' code cells import from the manifold packages, validated without running a notebook: each code cell
is parsed (IPython `%` and `!` lines dropped), every `manifold` module it imports must resolve, and every name it
imports from one must exist. No code cell imports the deprecated `protodirsig`."""
import ast
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted(p for p in (ROOT / "notebooks").rglob("*.ipynb")
                   if "dev" not in p.relative_to(ROOT / "notebooks").parts and ".ipynb_checkpoints" not in p.parts)


def _cells(path):
    for cell in json.loads(path.read_text(encoding="utf-8"))["cells"]:
        if cell["cell_type"] == "code":
            lines = "".join(cell["source"]).splitlines()
            yield "\n".join("" if ln.lstrip().startswith(("%", "!")) else ln for ln in lines)


def _imports(path):
    """(module, name or None) for each import statement of a code cell."""
    out = []
    for src in _cells(path):
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Import):
                out += [(a.name, None) for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                out += [(node.module, a.name) for a in node.names]
    return out


def test_there_are_notebooks_to_check():
    assert len(NOTEBOOKS) >= 9


@pytest.mark.parametrize("path", NOTEBOOKS, ids=[p.name for p in NOTEBOOKS])
def test_every_manifold_import_of_a_notebook_resolves(path):
    imports = _imports(path)
    assert not [m for m, _ in imports if m.split(".")[0] == "protodirsig"], "a code cell imports the deprecated shim"
    for module, name in imports:
        if module.split(".")[0] != "manifold":
            continue
        assert importlib.util.find_spec(module) is not None, f"{path.name}: {module} does not resolve"
        if name is not None:
            mod = importlib.import_module(module)
            assert hasattr(mod, name) or importlib.util.find_spec(f"{module}.{name}") is not None, \
                f"{path.name}: {module} has no {name}"
