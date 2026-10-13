"""scripts/recipe_form.py: the page it writes is one offline file, its embedded listings are the library's, and the
recipe YAML the page's own `recipeYaml` writes for a sample of form states is accepted by `Workspace.validate`
(engine-free). The page's script is run by Node.js on those states (skipped, with the reason, when `node` is absent);
the YAML is read back and compared with the script's `recipe_of`, the members the form writes."""
import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from manifold.sim import Workspace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import recipe_form  # noqa: E402

NODE = shutil.which("node")


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("form") / "index.html"
    assert recipe_form.main(["--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    m = re.search(r'<script id="listings" type="application/json">(.*?)</script>', text, re.S)
    return text, json.loads(m.group(1))


@pytest.fixture(scope="module")
def ws(tmp_path_factory):
    return Workspace.local(work=tmp_path_factory.mktemp("work"))


def test_the_page_is_one_offline_file(generated):
    text, _ = generated
    for pattern in (r"https?://", r"<link\b", r"<script[^>]*\bsrc=", r"@import", r"@font-face", r"url\(", r"<img\b",
                    r"<iframe\b", r"fetch\(", r"XMLHttpRequest"):
        assert not re.search(pattern, text), pattern
    assert text.count("<script") == 2 and "sha256" not in text and "content_hash" not in text


def test_the_listings_are_the_librarys(generated, ws):
    _, data = generated
    assert data["library"] == {"sensors": [i.name for i in ws.list_sensors().items],
                               "scenarios": [i.name for i in ws.list_scenarios().items],
                               "engine_profiles": [i.name for i in ws.list_engine_profiles().items],
                               "recipes": [i.name for i in ws.list_recipes().items]}
    assert [s["name"] for s in data["sensors"]] == data["library"]["sensors"]
    assert list(data["pairs"])[0] == "tahoe_static_pose / tahoe_static_pose"          # auror_ref's pair first
    assert set(data["pairs"]) == {"tahoe_static_pose / tahoe_static_pose", "tahoe_leo_pass / tahoe_leo_pass",
                                  "pointcollectors2_demo / pointcollectors2_demo"}
    offered = {(o["pair"], o["sensor"]) for o in data["offered"]}
    assert len(offered) == 6 and all(p.startswith("tahoe_") for p, _ in offered)
    assert {r["pair"] for r in data["refused"]} == {"pointcollectors2_demo / pointcollectors2_demo"}
    assert all("does not resolve" in r["reason"] for r in data["refused"])


def _states(data, n=24, seed=35):
    """Form states: each offered combination at its defaults, then random edits within the form's limits."""
    rng = random.Random(seed)
    frames = {(s["name"], e["entry_id"]): e["full_frame"] or [data["max_side"]] * 2
              for s in data["sensors"] for e in s["entries"]}
    out = [(o["pair"], o["sensor"], o["entry_id"], {}) for o in data["offered"]]
    for i in range(n):
        o = rng.choice(data["offered"])
        w, h = frames[(o["sensor"], o["entry_id"])]
        edit = {"name": rng.choice(["my-recipe", "Tahoe test 2", "x"]), "width": rng.randint(1, min(w, 64)),
                "height": rng.randint(1, min(h, 64)), "valid_for": rng.choice(["", "a test", "line: with 'quotes'"])}
        if i % 2:
            edit["description"] = 'a "quoted" description: #1'
            edit["modeled"], edit["absent"] = ["radiance"], []
        for k, (lo, hi, _) in data["fields"].items():
            edit[k] = round(rng.uniform(lo, min(hi, 10 * lo + 1)), 6)
        out.append((o["pair"], o["sensor"], o["entry_id"], edit))
    return out


def _page_script(text):
    return re.findall(r"<script>(.*?)</script>", text, re.S)[-1]


@pytest.mark.skipif(NODE is None, reason="running the page's script needs Node.js (node)")
def test_every_sampled_form_state_validates(generated, ws):
    text, data = generated
    states = _states(data)
    program = ("globalThis.LISTINGS = " + json.dumps(data) + ";\n" + _page_script(text) +
               "\nconst S = " + json.dumps([list(s) for s in states]) + ";\n"
               "for (const [p, s, e, edit] of S) { const st = Object.assign(defaults(p, s, e), edit);"
               " console.log(JSON.stringify([st, recipeYaml(st)])); }\n")
    r = subprocess.run([NODE, "-"], input=program, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    outputs = [json.loads(line) for line in r.stdout.splitlines()]
    assert len(outputs) == len(states) == len(data["offered"]) + 24
    for state, text_yaml in outputs:
        recipe = yaml.safe_load(text_yaml)
        assert recipe == recipe_form.recipe_of(state)
        run = ws.validate(recipe).runs[0]
        assert run.valid, (state, [e.detail for c in run.checks for e in c.errors])
        assert set(recipe) == {"compose", "meta", "sensor", "scenario", "engine_profile", "settings", "fidelity"}


@pytest.mark.skipif(NODE is None, reason="running the page's script needs Node.js (node)")
def test_numbers_are_written_as_yaml_numbers(generated):
    text, data = generated
    values = [1e-7, 2.5e-9, 1e21, 0.5, 16, 0.00001]
    program = ("globalThis.LISTINGS = " + json.dumps(data) + ";\n" + _page_script(text) +
               "\nconsole.log(" + json.dumps(values) + ".map(num).join('\\n'));\n")
    r = subprocess.run([NODE, "-"], input=program, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert [yaml.safe_load(t) for t in r.stdout.split()] == values


def test_the_default_recipes_validate_without_node(generated, ws):
    _, data = generated
    for o in data["offered"]:
        sensor = next(s for s in data["sensors"] if s["name"] == o["sensor"])
        entry = next(e for e in sensor["entries"] if e["entry_id"] == o["entry_id"])
        state = recipe_form.default_state(data["pairs"][o["pair"]], sensor, entry)
        assert ws.validate(recipe_form.recipe_of(state)).runs[0].valid, o


def test_the_manual_states_what_the_prototype_is():
    manual = (ROOT / "docs" / "User_manual.md").read_text(encoding="utf-8")
    start = manual.index("\n## 10. The recipe form (a prototype)\n")
    end = manual.find("\n## ", start + 1)
    last = manual[start:end if end != -1 else len(manual)]          # section 10 (section 11 follows it since round 41)
    assert "`python scripts/recipe_form.py`" in last and "a prototype of the recipe step only" in last
    assert "computes and shows no file hash" in last and "they remain files you write" in last
