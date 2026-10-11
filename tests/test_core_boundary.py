"""The engine boundary, enforced statically: `manifold.core` knows no engine and `manifold.sim` reaches engines only
through the registry.

Every `.py` under `packages/core` is parsed with `ast`, at every depth (function bodies and `TYPE_CHECKING` blocks
included). Forbidden in core: importing `manifold.sim`, `manifold.engines`, `dirfm`, `protodirsig` or a module named
like a registered engine id, by `import`, `from ... import`, `importlib.import_module(...)` or `__import__(...)` (a
non-literal argument to those is forbidden too: it cannot be checked); a string literal that is such a module path
(a dotted path under one of those roots); a string literal equal to an engine id, except where it is a member name
(a mapping key, a subscript, the name argument of `get`/`pop`/`setdefault`/`getattr`/`hasattr`/`setattr`, the name
columns of a generated model's `_FIELDS` table): `field` is also the problem-details member that names an authored
file's field; and the generator strings of dirfm and `dirsig-engine/1` (any literal naming `dirsig-engine`). Forbidden in `packages/sim`: importing
`manifold.engines.*`, `dirfm` or the transitional `manifold.sim._dirsig` (statically or by a literal module path). Engine packages (`packages/engine-*`) may import `manifold.core` but not `manifold.sim`.

`ALLOWLIST` names today's violations, each with its reason; it shrinks as the round removes them and is empty at the
end (`test_the_allowlist_is_empty_or_explained`).
"""
import ast
import re
from importlib.metadata import entry_points
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "packages" / "core" / "src"
SIM = ROOT / "packages" / "sim" / "src"
ENGINES = sorted((ROOT / "packages").glob("engine-*/src"))
KNOWN_ENGINE_IDS = {"dirsig", "satsim", "usd", "field"}          # the origin values named by the MANIFOLD documents
GENERATOR_STRINGS = {"dirfm", "dirsig-engine/1"}
SIM_ROOTS = ("manifold.engines", "dirfm", "manifold.sim._dirsig")


def engine_ids():
    """The known engine ids and every id registered in the `manifold.engines` entry-point group of this environment."""
    return KNOWN_ENGINE_IDS | {ep.name for ep in entry_points(group="manifold.engines")}


def _roots_core():
    return ("manifold.sim", "manifold.engines", "dirfm", "protodirsig", *sorted(engine_ids()))


def _under(name, roots):
    return any(name == r or name.startswith(r + ".") for r in roots)


DOTTED = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)+$")


def _docstrings(tree):
    nodes = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    return {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, nodes) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)
            and isinstance(n.body[0].value.value, str)}


MEMBER_CALLS = ("get", "pop", "setdefault", "getattr", "hasattr", "setattr")


def _member_names(tree):
    """ids of the string constants used as member names (see the module docstring)."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            out |= {id(k) for k in node.keys if k is not None}
        elif isinstance(node, ast.Subscript):
            out.add(id(node.slice))
        elif isinstance(node, ast.Call) and node.args:
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
            if name in MEMBER_CALLS:
                out.add(id(node.args[1] if name in ("getattr", "hasattr", "setattr") and len(node.args) > 1
                           else node.args[0]))
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_FIELDS" for t in node.targets) \
                and isinstance(node.value, ast.Tuple):
            for row in node.value.elts:
                if isinstance(row, ast.Tuple):
                    out |= {id(e) for e in row.elts[:2]}
    return out


def _dynamic_import(node):
    """The argument node of `importlib.import_module(x)`, `import_module(x)` or `__import__(x)`, else None."""
    if isinstance(node, ast.Call) and node.args:
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
        if name in ("import_module", "__import__"):
            return node.args[0]
    return None


def violations(path, roots, *, literal_rules):
    """`(line, rule, detail)` for each violation in one file. `roots`: forbidden module roots. `literal_rules`: also
    check engine-id and generator literals and dotted module-path literals (core)."""
    tree = ast.parse(path.read_text())
    docs = _docstrings(tree)
    members = _member_names(tree)
    ids = engine_ids()
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(node.lineno, "import", a.name) for a in node.names if _under(a.name, roots)]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and _under(node.module, roots):
            out.append((node.lineno, "import", node.module))
        arg = _dynamic_import(node)
        if arg is not None:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if _under(arg.value, roots):
                    out.append((node.lineno, "dynamic-import", arg.value))
            elif literal_rules:
                out.append((node.lineno, "dynamic-import", "non-literal module name"))
        if literal_rules and isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            v = node.value
            if v in ids and id(node) not in members:
                out.append((node.lineno, "engine-id-literal", v))
            elif v in GENERATOR_STRINGS or "dirsig-engine" in v:
                out.append((node.lineno, "generator-literal", v if len(v) <= 40 else v[:37] + "..."))
            elif DOTTED.match(v) and _under(v, roots):
                out.append((node.lineno, "module-path-literal", v))
    return sorted(set(out))


def _files(src):
    return sorted(p for p in src.rglob("*.py") if "__pycache__" not in p.parts)


def _rel(p):
    return p.relative_to(ROOT).as_posix()


# Today's violations: (file, rule, detail) -> reason. Each entry is removed by the step that fixes it.
ALLOWLIST = {
    ('packages/core/src/manifold/core/run_spec.py', 'dynamic-import', 'non-literal module name'):
        'the DIRSIG interpreter (resolve_run, plugin builders, engine-bound aliases) lives in core; moves to manifold.engines.dirsig (step 4)',
    ('packages/core/src/manifold/core/run_spec.py', 'generator-literal', "; this loader handles only 'new_atmos..."):
        'the DIRSIG interpreter (resolve_run, plugin builders, engine-bound aliases) lives in core; moves to manifold.engines.dirsig (step 4)',
    ('packages/core/src/manifold/core/run_spec.py', 'import', 'manifold.sim._dirsig.atmosphere_patches'):
        'the DIRSIG interpreter (resolve_run, plugin builders, engine-bound aliases) lives in core; moves to manifold.engines.dirsig (step 4)',
    ('packages/core/src/manifold/core/run_spec.py', 'import', 'manifold.sim._dirsig.platform_ref'):
        'the DIRSIG interpreter (resolve_run, plugin builders, engine-bound aliases) lives in core; moves to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/atmosphere_patches.py', 'import', 'dirfm.atmosphere'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/motion_tasks.py', 'import', 'dirfm'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/motion_tasks.py', 'import', 'dirfm.platform_motion'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/motion_tasks.py', 'import', 'dirfm.tasks'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/platform_ref.py', 'import', 'dirfm.ephemeris'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/platform_ref.py', 'import', 'dirfm.platform_sensor'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/platform_ref.py', 'import', 'dirfm.utilities.paths'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/registry.py', 'import', 'manifold.sim._dirsig.simulation'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/sensors.py', 'import', 'dirfm'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/simulation.py', 'import', 'dirfm'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/simulation.py', 'import', 'dirfm.weather'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/simulation.py', 'import', 'manifold.sim._dirsig.adapter'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/simulation.py', 'import', 'manifold.sim._dirsig.motion_tasks'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/simulation.py', 'import', 'manifold.sim._dirsig.platform_ref'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/_dirsig/simulation.py', 'import', 'manifold.sim._dirsig.scene_ref'):
        'the transitional DIRSIG package inside sim; extracted to manifold.engines.dirsig (step 4)',
    ('packages/sim/src/manifold/sim/backend.py', 'import', 'manifold.sim._dirsig.passthrough'):
        'module-level and call-time imports of the DIRSIG pass-through runner and Simulation; replaced by registry calls (step 3)',
    ('packages/sim/src/manifold/sim/backend.py', 'import', 'manifold.sim._dirsig.simulation'):
        'module-level and call-time imports of the DIRSIG pass-through runner and Simulation; replaced by registry calls (step 3)',
    ('packages/sim/src/manifold/sim/engines.py', 'import', 'manifold.sim._dirsig.adapter'):
        'registers the in-tree DIRSIG adapter directly until engines are discovered through entry points (step 3) and extracted (step 4)',
    ('packages/sim/src/manifold/sim/orbit.py', 'import', 'dirfm'):
        'orbit.lookat_motion builds a dirfm FlexMotion; moves to the DIRSIG engine (step 4)',
    ('packages/sim/src/manifold/sim/worker.py', 'import', 'dirfm'):
        'imports Simulation, the pass-through runner and dirfm; replaced by the adapter protocol (step 3)',
    ('packages/sim/src/manifold/sim/worker.py', 'import', 'manifold.sim._dirsig.passthrough'):
        'imports Simulation, the pass-through runner and dirfm; replaced by the adapter protocol (step 3)',
    ('packages/sim/src/manifold/sim/worker.py', 'import', 'manifold.sim._dirsig.simulation'):
        'imports Simulation, the pass-through runner and dirfm; replaced by the adapter protocol (step 3)',
}


def _scan():
    found = {}
    for p in _files(CORE):
        for line, rule, detail in violations(p, _roots_core(), literal_rules=True):
            found.setdefault((_rel(p), rule, detail), []).append(line)
    for p in _files(SIM):
        for line, rule, detail in violations(p, SIM_ROOTS, literal_rules=False):
            found.setdefault((_rel(p), rule, detail), []).append(line)
    for src in ENGINES:
        for p in _files(src):
            for line, rule, detail in violations(p, ("manifold.sim",), literal_rules=False):
                found.setdefault((_rel(p), rule, detail), []).append(line)
    return found


def test_no_boundary_violation_outside_the_allowlist():
    found = _scan()
    unexpected = {k: v for k, v in found.items() if k not in ALLOWLIST}
    assert unexpected == {}, "boundary violations (file, rule, detail): lines\n" + "\n".join(
        f"{k}: {v}" for k, v in sorted(unexpected.items()))


def test_every_allowlist_entry_is_still_a_violation():
    """A fixed violation must leave the allowlist, so the list only shrinks."""
    found = _scan()
    stale = sorted(k for k in ALLOWLIST if k not in found and not k[0].startswith("manifold_contracts/"))
    assert stale == [], f"fixed; remove from ALLOWLIST: {stale}"


def test_the_allowlist_is_empty_or_explained():
    assert all(isinstance(r, str) and r for r in ALLOWLIST.values())


@pytest.mark.parametrize("snippet, expected", [
    ("import manifold.sim.store", [(1, "import", "manifold.sim.store")]),
    ("from manifold.engines.dirsig import x", [(1, "import", "manifold.engines.dirsig")]),
    ("def f():\n    import dirfm", [(2, "import", "dirfm")]),
    ("from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from manifold.sim import x",
     [(3, "import", "manifold.sim")]),
    ("import importlib\nimportlib.import_module('manifold.sim.worker')",
     [(2, "dynamic-import", "manifold.sim.worker"), (2, "module-path-literal", "manifold.sim.worker")]),
    ("__import__(name)", [(1, "dynamic-import", "non-literal module name")]),
    ("X = 'dirsig'", [(1, "engine-id-literal", "dirsig")]),
    ("X = {'tool': 'dirfm'}", [(1, "generator-literal", "dirfm")]),
    ("X = 'protodirsig.worker'", [(1, "module-path-literal", "protodirsig.worker")]),
    ('"""Docs naming manifold.sim and dirsig."""\nX = "manifold.core.compose"', []),
    ("p = {'field': 1}\np['field']\np.get('field')\ngetattr(e, 'field', None)", []),
    ("if origin == 'field':\n    pass", [(1, "engine-id-literal", "field")]),
])
def test_the_scanner_finds_each_form(tmp_path, snippet, expected):
    p = tmp_path / "m.py"
    p.write_text(snippet)
    assert violations(p, _roots_core(), literal_rules=True) == sorted(expected)


def schema_violations_of_the_published_run_spec():
    """The published run-spec schema must not enumerate engine ids nor select an engine block schema: the engine block
    is an open object there, validated at admission by the registered adapter's schema."""
    import json
    doc = json.loads((ROOT / "manifold_contracts" / "run-spec-1.schema.json").read_text())
    out = []
    engine = doc["$defs"]["descriptor"]["properties"]["origin"]["properties"]["engine"]
    if "enum" in engine:
        out.append(("manifold_contracts/run-spec-1.schema.json", "engine-enum", "descriptor.origin.engine"))
    if any("dirsig-engine" in json.dumps(x) for x in doc.get("allOf", [])):
        out.append(("manifold_contracts/run-spec-1.schema.json", "engine-schema-selection", "allOf"))
    return out


def test_the_published_run_spec_schema_names_no_engine():
    found = [v for v in schema_violations_of_the_published_run_spec() if v not in ALLOWLIST]
    assert found == []
    stale = [k for k in ALLOWLIST if k[0].startswith("manifold_contracts/")
             and k not in schema_violations_of_the_published_run_spec()]
    assert stale == [], f"fixed; remove from ALLOWLIST: {stale}"
