"""docs/User_manual.md and docs/User_glossary.md against the SDK.

Every fenced block of the manual follows a marker comment, `<!-- run: always -->`, `<!-- run: engine -->` or
`<!-- run: shell -->`. The Python blocks are executed in order in one namespace from the repository's root folder, with
the manual's work folders (`"outputs/...`) moved under the test's temporary directory (the one substitution made); the
`engine` blocks only when `Workspace.list_engines` reports DIRSIG available, else they are skipped with that reason,
never passed without their output. The shell block is run as written. Each row of the refusal table is produced here and
its title and detail compared with the row."""
import contextlib
import copy
import io
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from manifold.core import problems
from manifold.core.errors import TITLES, ProblemError
from manifold.sim import Workspace

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "User_manual.md"
GLOSSARY = ROOT / "docs" / "User_glossary.md"
BLOCK = re.compile(r"<!-- run: (always|engine|shell) -->\n```(\w+)\n(.*?)```", re.S)


def blocks():
    """(kind, language, code) of every fenced block, in order."""
    return [(m.group(1), m.group(2), m.group(3)) for m in BLOCK.finditer(MANUAL.read_text(encoding="utf-8"))]


def test_every_block_has_a_marker():
    text = MANUAL.read_text(encoding="utf-8")
    assert text.count("```") == 2 * len(blocks()) and len(blocks()) == 10
    assert all((kind == "shell") == (lang == "bash") for kind, lang, _ in blocks())


@pytest.fixture(scope="module")
def executed(tmp_path_factory):
    """{block index: printed text} of every Python block run, and the reason the engine blocks were skipped."""
    tmp = tmp_path_factory.mktemp("manual")
    namespace, out, skipped = {}, {}, None
    cwd = Path.cwd()
    import os
    os.chdir(ROOT)
    try:
        for i, (kind, lang, code) in enumerate(blocks()):
            if lang != "python":
                continue
            if kind == "engine":
                dirsig = next(e for e in namespace["ws"].list_engines().items if e.engine_id == "dirsig")
                if not dirsig.available:
                    skipped = f"the DIRSIG engine is not available: {dirsig.reason}"
                    continue
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exec(compile(code.replace('"outputs/', f'"{tmp}/'), f"{MANUAL.name} block {i}", "exec"), namespace)
            out[i] = buf.getvalue()
    finally:
        os.chdir(cwd)
    return out, skipped, namespace


def _printed(executed, first_line):
    out = executed[0]
    index = next(i for i, (_, _, code) in enumerate(blocks()) if code.startswith(first_line))
    if index not in out:
        pytest.skip(executed[1])
    return out[index]


def test_install_and_check(executed):
    text = _printed(executed, "from manifold.sim import Workspace")
    assert re.search(r"^dirsig (available|not available: .+)$", text, re.M)
    r = subprocess.run([sys.executable, "scripts/bootstrap.py", "status"], cwd=ROOT, capture_output=True, text=True)
    assert [ln.split()[0] for ln in r.stdout.splitlines()] == ["dirfm", "agent-docs", "dirsig"]


def test_the_check_and_the_run_id(executed):
    assert _printed(executed, 'recipe = ws.get_recipe("auror_ref")') == "ready to run: True\n"
    assert _printed(executed, "again = ws.compose(recipe)") == "True\n"


def test_one_image(executed):
    assert _printed(executed, "status = ws.submit_run(recipe)") == "rendered complete\n"
    roles = _printed(executed, "for a in ws.list_artifacts(final.run_id)")
    assert re.search(r"^product +\S+\.img$", roles, re.M) and re.search(r"^config +run_spec\.json$", roles, re.M)
    image = _printed(executed, "from pathlib import Path")
    assert re.fullmatch(r"\S+\.img \(16, 16, 1\) \S+\n", image)


def test_a_sweep_and_a_space_to_space_run(executed):
    lines = _printed(executed, 'sweep = ws.get_recipe("sensor_sweep_tahoe")').splitlines()
    assert lines == [f"sensor-sweep-tahoe--{s} rendered complete" for s in
                     ("auror-nir", "deepscan_850_306_nir_1280", "synthetic_600_200_vis_1920")]
    assert _printed(executed, "import yaml") == "rendered complete\n"


def test_the_printed_refusal(executed):
    text = _printed(executed, "import copy")
    assert text.splitlines()[0] == "The recipe does not compose"
    assert "names no entry of the listed sensors" in text


# --- the refusal table -----------------------------------------------------------------------------------------------

def table_rows():
    """(title, detail fragment) of each row of the refusal table."""
    text = MANUAL.read_text(encoding="utf-8")
    table = text[text.index("| Title | What the detail says"):].split("\n\n")[0].splitlines()[2:]
    rows = []
    for line in table:
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append((cells[0], re.fullmatch(r"`(.+)`", cells[1]).group(1)))
    return rows


def _pattern(fragment):
    return re.escape(fragment).replace(re.escape("..."), ".*").replace(re.escape("<name>"), ".+?") \
        .replace(re.escape("<run id>"), "[0-9a-f]{64}")


@pytest.fixture(scope="module")
def refusals(tmp_path_factory):
    """{detail fragment: problem} for each case of the table, produced here."""
    tmp = tmp_path_factory.mktemp("refusals")
    ws = Workspace.local(work=tmp / "work")
    base = ws.get_recipe("auror_ref").document

    def edit(fn):
        r = copy.deepcopy(base)
        fn(r)
        return r

    def raised(call):
        try:
            call()
        except ProblemError as e:
            return e.problem
        raise AssertionError("no refusal")

    def checked(target, w=ws):
        run = w.validate(target).runs[0]
        return next(e for c in run.checks for e in c.errors if not c.passed).to_dict()

    vis = "synthetic_600_200_vis_1920.yaml"
    out = {}
    out["settings[0].entry_id: 'auror-nir' names no entry of the listed sensors"] = raised(
        lambda: ws.validate(edit(lambda r: r.update(sensor=vis))))
    out["meta.name: missing or not a string"] = raised(lambda: ws.validate(edit(lambda r: r["meta"].pop("name"))))
    out["channel_response native cannot carry a spectral curve"] = checked(edit(
        lambda r: (r.update(sensor=vis), r["settings"][0].update(entry_id="synthetic-600-200-vis-1920"))))
    out["has no 'gain': every settings member of a DIRSIG run states exposure_time, frame_rate and gain"] = checked(
        edit(lambda r: r["settings"][0].pop("gain")))
    s2s = ROOT / "manifold_run_specs" / "s2s" / "s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0.yaml"
    out["sensor 'auror-nir.yaml' not found in the sensor library"] = checked(s2s)
    lib = tmp / "lib"
    import shutil
    for d in ("recipes", "scenarios", "engine_profiles"):
        shutil.copytree(ROOT / "manifold_run_specs" / d, lib / d)
    profile = yaml.safe_load((lib / "engine_profiles" / "tahoe_static_pose.yaml").read_text())
    for name, value in (("placeholder", "sha256:<hash>"), ("wrong", "sha256:" + "0" * 64)):
        p = copy.deepcopy(profile)
        p["engine"]["platform"]["ref"]["content_hash"] = value
        (lib / "engine_profiles" / f"{name}.yaml").write_text(yaml.safe_dump(p))
    own = Workspace.local(library=lib, work=tmp / "own", sensor_library=ROOT / "manifold_sensors")
    out["carry a placeholder instead of a stamped value; run scripts/stamp_hashes.py"] = raised(
        lambda: own.submit_run(edit(lambda r: r.update(engine_profile="placeholder"))))
    out["content_hash ... does not match the file"] = checked(edit(lambda r: r.update(engine_profile="wrong")), own)
    out["No recipe 'auror_reff'."] = raised(lambda: ws.get_recipe("auror_reff"))
    out["the recipe composes to 3 runs (it names several sensors); submit it with submit_sweep"] = raised(
        lambda: ws.submit_run("sensor_sweep_tahoe"))
    out["Run <name> (<run id>) failed while executing: ..."] = problems.execution_failed(
        "0" * 64, "auror-ref-static-pose", "dirsig5 exited 1")
    return out


def test_the_refusal_table(refusals):
    rows = table_rows()
    assert len(rows) == 10 and {f for _, f in rows} == set(refusals)
    for title, fragment in rows:
        problem = refusals[fragment]
        assert problem["title"] == title, fragment
        assert re.search(_pattern(fragment), problem["detail"]), (fragment, problem["detail"])
    assert {t for t, _ in rows} == set(TITLES.values())


# --- the glossary and the links --------------------------------------------------------------------------------------

def test_the_glossary_maps_the_users_words():
    text = GLOSSARY.read_text(encoding="utf-8")
    words = [ln.split("|")[1].strip() for ln in text.splitlines() if ln.startswith("| ") and "---" not in ln][1:]
    for word in ("simulation", "sensor", "scene", "camera settings", "result", "check before running"):
        assert word in words, word
    for term in ("recipe", "run spec", "run id", "engine profile, engine block", "validate, admission",
                 "run status, artifacts", "content hash", "provenance"):
        assert f"| {term} |" in text, term
    assert "(User_manual.md)" in text


def test_the_manual_links_the_glossary_and_the_guides():
    text = MANUAL.read_text(encoding="utf-8")
    first = text.split("\n## ")[0]
    assert "(User_glossary.md)" in first and "(../notebooks/quickstart_sdk.ipynb)" in first
    assert (MANUAL.parent / "../notebooks/quickstart_sdk.ipynb").is_file()
    for target in ("Authoring_layered_form.md", "Engine_author_guide.md", "Authoring_friction_audit.md",
                   "../notebooks/stage_06_space_to_space.ipynb"):
        assert f"]({target})" in text and (MANUAL.parent / target).is_file(), target
