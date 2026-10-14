#!/usr/bin/env python3
"""Write an offline HTML form that fills in a `compose/1` recipe from the library's listings (a prototype).

    python scripts/recipe_form.py                       write outputs/recipe_form/index.html
    python scripts/recipe_form.py --out DIR/index.html  write it elsewhere

At generation time the script reads the library through `Workspace` (engine-free: `list_sensors`, `list_scenarios`,
`list_engine_profiles`, `list_recipes` and the documents): the sensors with their entries and full frames, and the
scenario and engine-profile pairs the shipped one-run and sweep recipes use. Each pair is offered with each sensor
only when the recipe the form would write for it by default passes `Workspace.validate`; the rest are listed in the
page with the reason. The page embeds these listings as JSON and builds the recipe in the browser: the user picks a
scenario and engine profile, a sensor and a window and sets the free fields (name, exposure time, frame rate, gain,
fidelity); the page shows the YAML to copy or download. It writes only what a user authors in a recipe (the 20
required fields of `docs/Authoring_friction_audit.md`, section 2, `black_level` at 0, with `meta.description` when
given); it computes and
shows no hash, and the layers stay files. One HTML file: no network, no external script, style sheet or font.
"""
import argparse
import copy
import html
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "packages" / d / "src") for d in ("core", "sim")]   # the manifold namespace, uninstalled

from manifold.core.errors import ProblemError  # noqa: E402
from manifold.sim import Workspace             # noqa: E402

DEFAULT_OUT = ROOT / "outputs" / "recipe_form" / "index.html"
WINDOW = 16                                    # the default window, pixels a side
MAX_SIDE = 4096                                # the window limit when a sensor states no full frame
FIELDS = {                                     # the free numeric fields: (min, max, step); black level is fixed at 0
    "exposure_time": (1e-6, 10.0, "any"),
    "frame_rate": (0.001, 100000.0, "any"),
    "gain": (0.001, 1000.0, "any"),
}


def sensors(ws):
    """[{name, entries: [{entry_id, full_frame: [w, h] or null}]}] of the sensor library."""
    out = []
    for item in ws.list_sensors().items:
        doc = ws.get_sensor(item.name).document
        entries = []
        for e in doc["sensor"]["entries"]:
            det = e["focal_planes"][0]["detector"]
            full = [det.get("SensorWidth"), det.get("SensorHeight")]
            entries.append({"entry_id": e["entry_id"], "full_frame": full if None not in full else None})
        out.append({"name": item.name, "entries": entries})
    return out


def pairs(ws):
    """{"<scenario> / <engine profile>": {scenario, engine_profile, recipe, settings, fidelity}} from the shipped
    recipes that name a sensor (or sensors), in recipe order; the first recipe of a pair gives its defaults."""
    out = {}
    for item in ws.list_recipes().items:
        doc = ws.get_recipe(item.name).document
        if "scenario" not in doc or not ("sensor" in doc or "sensors" in doc):
            continue                                          # a pass-through recipe names no scenario or sensor
        key = f"{doc['scenario']} / {doc['engine_profile']}"
        if key in out:
            continue
        first = doc["sensor"] if "sensor" in doc else doc["sensors"][0]
        fidelity = doc.get("fidelity") or doc["fidelity_by_sensor"][first]
        out[key] = {"scenario": doc["scenario"], "engine_profile": doc["engine_profile"], "recipe": item.name,
                    "settings": copy.deepcopy(doc["settings"][0]), "fidelity": fidelity}
    return out


def default_state(pair, sensor, entry):
    """The form's state when a pair and a sensor are first picked."""
    s = pair["settings"]
    return {"name": "my-recipe", "description": "", "scenario": pair["scenario"],
            "engine_profile": pair["engine_profile"], "sensor": sensor["name"], "entry_id": entry["entry_id"],
            "width": WINDOW, "height": WINDOW,
            **{k: s[k]["value"] for k in FIELDS},
            "modeled": list(pair["fidelity"]["modeled"]), "approximated": list(pair["fidelity"]["approximated"]),
            "absent": list(pair["fidelity"]["absent"]), "valid_for": pair["fidelity"]["valid_for"].strip()}


def recipe_of(state):
    """The recipe document a form state stands for; the page's `recipeYaml` writes the same members."""
    meta = {"name": state["name"]}
    if state["description"]:
        meta["description"] = state["description"]
    member = {"entry_id": state["entry_id"],
              **{k: {"value": state[k], "provenance": "specified"} for k in FIELDS},
              "black_level": {"value": 0, "provenance": "specified"},
              "roi": {"Width": state["width"], "Height": state["height"]}}
    return {"compose": "compose/1", "meta": meta, "sensor": state["sensor"], "scenario": state["scenario"],
            "engine_profile": state["engine_profile"], "settings": [member],
            "fidelity": {k: state[k] for k in ("modeled", "approximated", "absent", "valid_for")}}


def listings(ws):
    """The JSON the page embeds: sensors, the offered combinations (pair x sensor entry) and the refused ones."""
    sens, prs = sensors(ws), pairs(ws)
    offered, refused = [], []
    for key, pair in prs.items():
        for s in sens:
            for e in s["entries"]:
                state = default_state(pair, s, e)
                try:
                    run = ws.validate(recipe_of(state)).runs[0]
                    reason = None if run.valid else "; ".join(x.detail for c in run.checks if not c.passed
                                                              for x in c.errors)
                except ProblemError as exc:
                    reason = exc.problem["detail"]
                row = {"pair": key, "sensor": s["name"], "entry_id": e["entry_id"]}
                (offered if reason is None else refused).append(row if reason is None else {**row, "reason": reason})
    return {"sensors": sens, "pairs": prs, "offered": offered, "refused": refused, "fields": FIELDS,
            "window": WINDOW, "max_side": MAX_SIDE,
            "library": {"sensors": [i.name for i in ws.list_sensors().items],
                        "scenarios": [i.name for i in ws.list_scenarios().items],
                        "engine_profiles": [i.name for i in ws.list_engine_profiles().items],
                        "recipes": [i.name for i in ws.list_recipes().items]}}


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Recipe form (prototype)</title>
<style>
body { font-family: sans-serif; margin: 1.5em; max-width: 72em; color: #222; }
fieldset { border: 1px solid #bbb; margin: 0 0 1em 0; }
label { display: block; margin: 0.4em 0; }
input, select, textarea { font: inherit; }
textarea { width: 100%; }
pre { background: #f4f4f4; padding: 0.8em; white-space: pre-wrap; word-break: break-word; }
.note { color: #555; font-size: 0.9em; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5em; }
.grid > * { min-width: 0; }
</style>
</head>
<body>
<h1>Recipe form (prototype)</h1>
<p class="note">Fills in a <code>compose/1</code> recipe from the library as it was when this page was written (__WHEN__) by <code>scripts/recipe_form.py</code>. It writes only what a recipe author chooses; every file it names stays as the library holds it, and it computes no hash. Load the YAML as a dict: <code>ws.validate(yaml.safe_load(open("my_recipe.yaml")))</code>, then <code>ws.submit_run(...)</code> (a recipe file outside the library's <code>recipes/</code> folder does not compose by file name).</p>
<div class="grid">
<form id="form" autocomplete="off">
<fieldset><legend>What to simulate</legend>
<label>Scenario / engine profile <select id="pair"></select></label>
<label>Sensor <select id="sensor"></select></label>
<label>Name <input id="name" required pattern="\\S.*"></label>
<label>Description (optional) <input id="description" size="50"></label>
</fieldset>
<fieldset><legend>Camera settings</legend>
<label>Window width (pixels) <input id="width" type="number" min="1" step="1" required></label>
<label>Window height (pixels) <input id="height" type="number" min="1" step="1" required></label>
<label>Exposure time (s) <input id="exposure_time" type="number" required></label>
<label>Frame rate (Hz) <input id="frame_rate" type="number" required></label>
<label>Gain <input id="gain" type="number" required></label>
<p class="note">Black level is 0: DIRSIG applies any other value before the focal-plane conversion, and the SDK refuses it.</p>
</fieldset>
<fieldset><legend>Fidelity (one item per line)</legend>
<label>Modeled <textarea id="modeled" rows="3"></textarea></label>
<label>Approximated <textarea id="approximated" rows="3"></textarea></label>
<label>Absent <textarea id="absent" rows="2"></textarea></label>
<label>Valid for <textarea id="valid_for" rows="3"></textarea></label>
</fieldset>
</form>
<div>
<h2>Recipe</h2>
<p><button id="copy" type="button">Copy</button> <a id="download" download="my_recipe.yaml" href="#">Download</a> <span id="status" class="note"></span></p>
<pre id="yaml"></pre>
<h2>Not offered</h2>
<p class="note">Combinations of the library that the SDK's checks refused when this page was written:</p>
<ul id="refused"></ul>
</div>
</div>
<script id="listings" type="application/json">__LISTINGS__</script>
<script>
"use strict";
const L = typeof document !== "undefined" ? JSON.parse(document.getElementById("listings").textContent) : globalThis.LISTINGS;

function q(s) { return JSON.stringify(String(s)); }                     // a JSON string is a YAML scalar
function list(items) { return "[" + items.map(q).join(", ") + "]"; }
function num(x) {                                                    // a YAML 1.1 float needs a dot before an exponent
  const t = String(Number(x));
  return /e/.test(t) && !/\\./.test(t) ? t.replace("e", ".0e") : t;
}

function recipeYaml(s) {
  const lines = ["compose: compose/1", "", "meta:", "  name: " + q(s.name)];
  if (s.description) lines.push("  description: " + q(s.description));
  lines.push("", "sensor: " + q(s.sensor), "scenario: " + q(s.scenario), "engine_profile: " + q(s.engine_profile), "",
    "settings:", "  - entry_id: " + q(s.entry_id));
  for (const k of ["exposure_time", "frame_rate", "gain"])
    lines.push("    " + k + ": {value: " + num(s[k]) + ", provenance: specified}");
  lines.push("    black_level: {value: 0, provenance: specified}",
    "    roi: {Width: " + num(s.width) + ", Height: " + num(s.height) + "}", "", "fidelity:");
  for (const k of ["modeled", "approximated", "absent"]) lines.push("  " + k + ": " + list(s[k]));
  lines.push("  valid_for: " + q(s.valid_for));
  return lines.join("\\n") + "\\n";
}

function defaults(pairKey, sensorName, entryId) {
  const p = L.pairs[pairKey], st = p.settings, f = p.fidelity;
  return {name: "my-recipe", description: "", scenario: p.scenario, engine_profile: p.engine_profile,
    sensor: sensorName, entry_id: entryId, width: L.window, height: L.window,
    exposure_time: st.exposure_time.value, frame_rate: st.frame_rate.value, gain: st.gain.value,
    modeled: f.modeled.slice(), approximated: f.approximated.slice(), absent: f.absent.slice(),
    valid_for: f.valid_for.trim()};
}

function fullFrame(sensorName, entryId) {
  const s = L.sensors.find(x => x.name === sensorName);
  const e = s.entries.find(x => x.entry_id === entryId);
  return e.full_frame || [L.max_side, L.max_side];
}

if (typeof document !== "undefined" && document.getElementById("form")) {
  const $ = id => document.getElementById(id);
  const lines = t => t.split("\\n").map(x => x.trim()).filter(x => x);
  for (const key of Object.keys(L.pairs)) if (L.offered.some(o => o.pair === key)) $("pair").add(new Option(key, key));
  for (const r of L.refused) { const li = document.createElement("li"); li.textContent = r.pair + " with " + r.sensor + ": " + r.reason; $("refused").appendChild(li); }
  for (const [k, [lo, hi, step]] of Object.entries(L.fields)) { $(k).min = lo; $(k).max = hi; $(k).step = step; }

  function fill(s) {
    for (const k of ["name", "description", "width", "height", "exposure_time", "frame_rate", "gain", "valid_for"]) $(k).value = s[k];
    for (const k of ["modeled", "approximated", "absent"]) $(k).value = s[k].join("\\n");
    const [w, h] = fullFrame(s.sensor, s.entry_id);
    $("width").max = w; $("height").max = h;
  }
  function sensors() {
    const key = $("pair").value; $("sensor").innerHTML = "";
    for (const o of L.offered.filter(o => o.pair === key)) $("sensor").add(new Option(o.sensor + " (" + o.entry_id + ")", o.sensor + "|" + o.entry_id));
  }
  function picked() { const [s, e] = $("sensor").value.split("|"); return defaults($("pair").value, s, e); }
  function state() {
    const s = picked();
    for (const k of ["name", "description", "valid_for"]) s[k] = $(k).value.trim();
    for (const k of ["width", "height", "exposure_time", "frame_rate", "gain"]) s[k] = Number($(k).value);
    for (const k of ["modeled", "approximated", "absent"]) s[k] = lines($(k).value);
    return s;
  }
  function show() {
    const ok = $("form").checkValidity(), text = recipeYaml(state());
    $("yaml").textContent = text;
    $("status").textContent = ok ? "" : "a field is out of range or empty; fix it before using this recipe";
    $("download").href = "data:application/x-yaml;charset=utf-8," + encodeURIComponent(text);
    $("download").download = (state().name || "my_recipe").replace(/[^A-Za-z0-9_.-]+/g, "_") + ".yaml";
  }
  $("pair").addEventListener("change", () => { sensors(); fill(picked()); show(); });
  $("sensor").addEventListener("change", () => { fill(picked()); show(); });
  $("form").addEventListener("input", show);
  $("copy").addEventListener("click", () => {
    const text = $("yaml").textContent;
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(() => { $("status").textContent = "copied"; });
  });
  sensors(); fill(picked()); show();
}
</script>
</body>
</html>
"""


def page(data, when):
    """The HTML page with the listings embedded (`</` escaped so the JSON cannot close its script element)."""
    blob = json.dumps(data, indent=1).replace("</", "<\\/")          # pairs keep the recipes' order
    return PAGE.replace("__LISTINGS__", blob).replace("__WHEN__", html.escape(when))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="the HTML file to write")
    ap.add_argument("--library", type=Path, help="the layer library (default: the repository's manifold_run_specs/)")
    ap.add_argument("--sensor-library", type=Path, help="the sensor library (default: manifold_sensors/ beside it)")
    ap.add_argument("--config-repo", type=Path, help="the engine-asset library (default: manifold_config_repo/)")
    args = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as work:                 # validate stores nothing; the workspace needs a root
        ws = Workspace.local(library=args.library, config_repo=args.config_repo, work=work,
                             sensor_library=args.sensor_library)
        data = listings(ws)
    library = (args.library or ROOT / "manifold_run_specs").resolve()
    library = library.relative_to(ROOT) if library.is_relative_to(ROOT) else library
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page(data, f"library {library}"), encoding="utf-8")
    print(f"wrote {args.out}: {len(data['offered'])} combinations offered, {len(data['refused'])} refused")
    return 0


if __name__ == "__main__":
    sys.exit(main())
