"""Every module in src/protodirsig appears in the module table of the CONOPS and Guide (Part II, section 7)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONOPS = ROOT / "docs" / "MANIFOLD_DIRSIG_CONOPS_and_Guide.md"


def _table_modules():
    lines = CONOPS.read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("## 7. "))
    head = next(i for i in range(start, len(lines)) if lines[i].startswith("| Module |"))
    names = set()
    for ln in lines[head + 2:]:
        if not ln.startswith("|"):
            break
        names |= set(re.findall(r"`([a-z_]+)`", ln.split("|")[1]))
    return names


def test_every_module_is_in_the_conops_module_table():
    modules = {p.stem for p in (ROOT / "src" / "protodirsig").glob("*.py") if p.stem != "__init__"}
    table = _table_modules()
    assert sorted(modules - table) == [], "modules missing from the CONOPS section 7 table"
    assert sorted(table - modules) == [], "CONOPS section 7 table names modules that do not exist"
