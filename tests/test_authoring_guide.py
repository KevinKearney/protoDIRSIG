"""docs/Authoring_layered_form.md: every code block is a spec excerpt or a command the repository already runs.

Each fenced block follows a marker comment. `<!-- block: spec <file> <key path> -->`: the YAML block parses to exactly
the member at that key path of the committed run spec, and the run spec passes the engine-free checks
(`admission.validate_spec`: schema, resolution with stamped hashes verified, the library files, nothing unstamped).
`<!-- block: command -->`: each line is `python scripts/<script>.py ...`, the script exists, and each option the line
passes is one the script defines. The run ids the guide states are the ones the checks compute. Engine-free.
"""
import re
import shlex
from pathlib import Path

import pytest
import yaml

import manifold.sim  # noqa: F401  (installs the engine registry admission uses)
from manifold.core.admission import validate_spec

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "Authoring_layered_form.md"
SENSORS = ROOT / "manifold_sensors"
BLOCK = re.compile(r"^<!-- block: (?P<marker>[^>]*?) -->\n```(?P<lang>\w+)\n(?P<body>.*?)^```$", re.M | re.S)
FENCE = re.compile(r"^```\w", re.M)


def blocks():
    return [(m["marker"].split(), m["lang"], m["body"]) for m in BLOCK.finditer(GUIDE.read_text(encoding="utf-8"))]


SPECS = [(b[0][1], b[0][2], b[2]) for b in blocks() if b[0][0] == "spec"]
COMMANDS = [line for b in blocks() if b[0][0] == "command" for line in b[2].splitlines() if line.strip()]


def member(doc, path):
    for key in path.split("."):
        doc = doc[key]
    return doc


def test_every_code_block_has_a_marker():
    text = GUIDE.read_text(encoding="utf-8")
    assert len(FENCE.findall(text)) == len(blocks()) > 0
    assert all(b[0][0] in ("spec", "command") for b in blocks())
    assert {lang for (marker, lang, _) in blocks()} == {"yaml", "bash"}
    assert all(lang == ("yaml" if marker[0] == "spec" else "bash") for marker, lang, _ in blocks())


@pytest.mark.parametrize("path,key,body", SPECS, ids=[f"{p}:{k}" for p, k, _ in SPECS])
def test_a_spec_excerpt_is_the_member_of_the_committed_file(path, key, body):
    doc = yaml.safe_load((ROOT / path).read_text())
    assert yaml.safe_load(body) == member(doc, key)


@pytest.mark.parametrize("path", sorted({p for p, _, _ in SPECS}))
def test_each_named_spec_is_admitted_and_its_stated_run_id_is_computed(path):
    spec_path = ROOT / path
    report = validate_spec(yaml.safe_load(spec_path.read_text()), spec_path, sensor_library=SENSORS)
    assert report.valid, (report.schema_errors, report.resolution_mismatches)
    assert report.unstamped == []
    section = GUIDE.read_text(encoding="utf-8").split(f"`{path}`", 1)[1].split("\n### ", 1)[0]
    assert f"`{report.run_id}`" in section, f"the guide does not state {path}'s run id {report.run_id}"


@pytest.mark.parametrize("line", COMMANDS)
def test_a_command_names_a_script_and_options_it_defines(line):
    argv = shlex.split(line)
    assert argv[0] == "python" and re.fullmatch(r"scripts/\w+\.py", argv[1]), line
    script = ROOT / argv[1]
    assert script.is_file(), argv[1]
    source = script.read_text(encoding="utf-8")
    for arg in argv[2:]:
        if arg.startswith("--"):
            assert f'"{arg.split("=", 1)[0]}"' in source, f"{argv[1]} defines no option {arg}"
