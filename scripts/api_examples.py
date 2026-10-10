#!/usr/bin/env python3
"""Write the request/response examples of the SDK API contract (api/examples/) from the real library.

    python scripts/api_examples.py           (re)write api/examples/*.json
    python scripts/api_examples.py --check   exit 1 if an example differs from what the library gives now

One file per operation, plus `compose.problem.json`, the problem produced by actually composing the
`member_in_two_layers` conformance vector; `submit_run.problem.json`, the admission problem for a schema violation in
an engine profile (edited in a temporary copy of the library, never in place), named by layer file and field with
`protodirsig.problems`; and `list_artifacts.pass.json`, a multi-frame run. Library names,
content hashes, documents, composed specs, provenance and validation outcomes are real; run ids and sweep ids are
computed from the composed specs (`protodirsig.identity`), and the hash of `run_spec.json` is its run id (the
artifact is the canonical JSON of the resolved spec). Hashes of rendered files (images, headers, truth, logs) are
marked placeholders, 64 zeros: no engine is run here. Large bodies are abbreviated, and each example's description
says so.
"""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from protodirsig import problems                                        # noqa: E402
from protodirsig.compose import ComposeError, compose, compose_sweep   # noqa: E402
from protodirsig.contract import schema_violations                       # noqa: E402
from protodirsig.identity import run_id as compute_run_id                  # noqa: E402
from protodirsig.run_spec import check_library_files, load_run_spec, resolve_auror_run   # noqa: E402
from protodirsig.simulation import schema_errors   # noqa: E402

OUT = ROOT / "api" / "examples"
LAYERS = ROOT / "manifold_run_specs"
SENSORS = ROOT / "manifold_sensors"
CONFIG_REPO = ROOT / "manifold_config_repo"
VECTOR = ROOT / "manifold_contracts" / "vectors" / "compose" / "member_in_two_layers"
SWEEP, SINGLE = "sensor_sweep_tahoe", "auror_ref"

PLACEHOLDER = ("Run ids and sweep ids are computed from the composed specs; the hash of `run_spec.json` is the run "
               "id. Everything else is real library data.")
RENDERED_PLACEHOLDER = ("Hashes of rendered files (images, headers, truth images, logs) are placeholders, 64 zeros: "
                        "no run is rendered for these examples.")
ZERO = "0" * 64
ABBREVIATED = "Members shown as `(abbreviated)` are cut from this example; the real body carries them in full."
ABBREVIATION_MARKER = "(abbreviated)"         # the value of every cut member; tests look for it
PASS = "leo_pass_tahoe"
_COMPOSED = {r: compose_sweep(LAYERS / "recipes" / f"{r}.yaml") for r in (SWEEP, SINGLE, PASS)}
RUN_IDS = {n: i for c in _COMPOSED.values() for n, i in c.run_ids.items()}     # computed: identity.run_id
SWEEP_ID = _COMPOSED[SWEEP].sweep_id                                           # computed: identity.sweep_id_from_runs
RUN_DIR = "file:///tmp/protodirsig/runs"


BOGUS_KIND = "bogus"
MUTATED = ("engine_profiles/tahoe_static_pose.yaml", "    kind: static\n", f"    kind: {BOGUS_KIND}\n")


def mutated_problem():
    """The admission problem for the `SINGLE` recipe composed from a temporary copy of the library in which the
    engine profile's `engine.motion.kind` is not an allowed value."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "manifold_run_specs"
        for d in ("recipes", "scenarios", "engine_profiles"):
            shutil.copytree(LAYERS / d, root / d)
        shutil.copytree(SENSORS, Path(tmp) / "manifold_sensors")
        rel, old, new = MUTATED
        text = (root / rel).read_text()
        if text.count(old) != 1:
            raise SystemExit(f"{rel}: expected one {old.strip()!r} to edit")
        (root / rel).write_text(text.replace(old, new))
        recipe = root / "recipes" / f"{SINGLE}.yaml"
        sweep = compose_sweep(recipe)
        (name,) = sweep.runs
        violations = schema_violations(sweep.runs[name])
        return problems.from_schema_violations(sweep.runs[name], sweep.sources[name], violations, "/runs",
                                               recipe=recipe)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cut(d):
    return {k: ABBREVIATION_MARKER for k in d}


def short_spec(spec):
    """A composed spec with meta, sensor and settings in full and every other member cut to its keys."""
    desc = spec["descriptor"]
    keep = ("meta", "sensor", "settings")
    return {"spec_version": spec["spec_version"],
            "descriptor": {k: (v if k in keep or not isinstance(v, dict) else cut(v)) for k, v in desc.items()},
            "engine": cut(spec["engine"])}


def library(kind):
    folder, pattern, name = {"sensors": (SENSORS, "*.yaml", lambda p: p.name),
                             "scenarios": (LAYERS / "scenarios", "*.yaml", lambda p: p.stem),
                             "engine_profiles": (LAYERS / "engine_profiles", "*.yaml", lambda p: p.stem),
                             "recipes": (LAYERS / "recipes", "*.yaml", lambda p: p.stem)}[kind]
    return {name(p): p for p in sorted(folder.glob(pattern))}


def spec_artifact(run_id):
    return {"name": "run_spec.json", "sha256": run_id, "media_type": "application/json",
            "uri": f"{RUN_DIR}/{run_id}/run_spec.json"}


def status(name, state):
    run_id = RUN_IDS[name]
    return {"run_id": run_id, "name": name, "state": state, "errors": [], "artifacts": [spec_artifact(run_id)]}


def get(path):
    return {"method": "GET", "path": path}


def post(path, body, schema):
    return {"method": "POST", "path": path, "body": body, "schema": schema}


def ok(body, schema, code=200, media_type="application/json"):
    return {"status": code, "media_type": media_type, "body": body, "schema": schema}


def examples():
    ex = {}
    kinds = {"sensors": ("sensor", "/sensors"), "scenarios": ("scenario", "/scenarios"),
             "engine_profiles": ("engine_profile", "/engine-profiles"), "recipes": ("recipe", "/recipes")}
    picks = {"sensors": "auror-nir.yaml", "scenarios": "tahoe_static_pose", "engine_profiles": "tahoe_static_pose",
             "recipes": SINGLE}
    for kind, (one, path) in kinds.items():
        lib = library(kind)
        ex[f"list_{kind}"] = {
            "summary": f"List the {kind.replace('_', ' ')} in the library.",
            "description": "Real library data.",
            "request": get(path),
            "response": ok({"items": [{"name": n, "sha256": sha(p)} for n, p in lib.items()]},
                           "schemas/library_list.schema.json")}
        name = picks[kind]
        doc = yaml.safe_load(lib[name].read_text())
        big = kind == "engine_profiles"
        ex[f"get_{one}"] = {
            "summary": f"Read the {one.replace('_', ' ')} `{name}`.",
            "description": "Real library data." + (" " + ABBREVIATED if big else ""),
            "request": get(f"{path}/{name}"),
            "response": ok({"name": name, "sha256": sha(lib[name]),
                            "document": {k: cut(v) if isinstance(v, dict) else v for k, v in doc.items()} if big
                            else doc},
                           "schemas/" + ("sensor_document" if kind == "sensors" else "library_document")
                           + ".schema.json")}

    sweep = compose_sweep(LAYERS / "recipes" / f"{SWEEP}.yaml")
    ex["compose"] = {
        "summary": f"Compose the `{SWEEP}` recipe: one run per sensor.",
        "description": f"Three runs, one per sensor named by the recipe. {PLACEHOLDER} {ABBREVIATED}",
        "request": post("/compose", {"recipe_name": SWEEP}, "schemas/compose_request.schema.json"),
        "response": ok({"sweep_id": SWEEP_ID,
                        "recipe": {"name": SWEEP, "sha256": sha(LAYERS / "recipes" / f"{SWEEP}.yaml")},
                        "is_sweep": sweep.is_sweep,
                        "runs": [{"run_id": RUN_IDS[n], "name": n, "sensor": sweep.sensors[n],
                                  "run_spec": short_spec(s), "provenance": sweep.sources[n]}
                                 for n, s in sweep.runs.items()]},
                       "schemas/compose_response.schema.json")}

    try:
        compose_sweep(next((VECTOR / "recipes").glob("*.yaml")))
        raise SystemExit(f"{VECTOR.name} composed; it should raise ComposeError")
    except ComposeError as e:
        problem = problems.from_compose_error(e, "/compose")
    ex["compose.problem"] = {
        "summary": "A recipe that does not compose: two layers both hold `fidelity`.",
        "description": ("Produced by composing the conformance vector `manifold_contracts/vectors/compose/"
                        f"{VECTOR.name}`, whose scenario also holds `fidelity`, a member the recipe owns. The "
                        "problem names the scenario file and the field."),
        "source": {"conformance_vector": VECTOR.name},
        "request": post("/compose", {"recipe_name": next((VECTOR / "recipes").glob("*.yaml")).stem},
                        "schemas/compose_request.schema.json"),
        "response": ok(problem, "schemas/problem.schema.json", 422, "application/problem+json")}

    ex["submit_run.problem"] = {
        "summary": f"A submission that fails admission: the engine profile sets `engine.motion.kind` to `{BOGUS_KIND}`.",
        "description": (f"Produced from the `{SINGLE}` recipe after editing `{MUTATED[0]}` in a temporary copy of the "
                        f"library (the repository's files are not edited): its `engine.motion.kind` is set to "
                        f"`{BOGUS_KIND}`, a value `dirsig-engine/1` does not allow. The composed spec is checked "
                        "against the contract schemas and the violation is located by the composer's provenance, so "
                        "the problem names the engine profile file and the field in it. No run is created."),
        "source": {"recipe": SINGLE, "edited_layer": MUTATED[0], "edit": f"engine.motion.kind: {BOGUS_KIND}"},
        "request": post("/runs", {"recipe_name": SINGLE}, "schemas/submit_run_request.schema.json"),
        "response": ok(mutated_problem(), "schemas/problem.schema.json", 422, "application/problem+json")}

    spec_path = LAYERS / f"{SINGLE}.yaml"
    spec = load_run_spec(spec_path)
    resolved = resolve_auror_run(spec, spec_path, CONFIG_REPO, SENSORS)
    checks = [("schema", schema_errors(spec)), ("resolution", []), ("content_hash", []),
              ("library_files", check_library_files(spec, resolved))]
    checks = [{"check": c, "passed": not errs, "errors": [{"type": "urn:protodirsig:problem:admission",
                                                            "title": "A check failed", "status": 422,
                                                            "detail": d, "layer": None, "field": None}
                                                           for d in errs]} for c, errs in checks]
    name = spec["descriptor"]["meta"]["name"]
    ex["validate"] = {
        "summary": f"Validate the `{SINGLE}` recipe without the engine.",
        "description": ("The engine-free level: the checks admission runs. The outcomes are real; resolution and "
                        f"content-hash verification are one step today and are reported as two. {PLACEHOLDER}"),
        "request": post("/validate", {"recipe_name": SINGLE, "engine_check": "none"},
                        "schemas/validate_request.schema.json"),
        "response": ok({"engine_check": "none",
                        "runs": [{"name": name, "run_id": RUN_IDS[name], "valid": all(c["passed"] for c in checks),
                                  "engine_checked": False, "checks": checks}]},
                       "schemas/validate_response.schema.json")}

    ex["submit_run"] = {
        "summary": f"Submit the `{SINGLE}` recipe as one run.",
        "description": f"A new run: admitted and executing, so 202 in state `accepted`. {PLACEHOLDER}",
        "request": post("/runs", {"recipe_name": SINGLE}, "schemas/submit_run_request.schema.json"),
        "response": ok(status(name, "accepted"), "schemas/run_status.schema.json", 202)}
    recipe_ref = {"name": SWEEP, "sha256": sha(LAYERS / "recipes" / f"{SWEEP}.yaml")}
    ex["submit_sweep"] = {
        "summary": f"Submit the `{SWEEP}` recipe as a sweep.",
        "description": f"A new sweep of three runs, admitted as a whole: 202, each run `accepted`. {PLACEHOLDER}",
        "request": post("/sweeps", {"recipe_name": SWEEP}, "schemas/submit_sweep_request.schema.json"),
        "response": ok({"sweep_id": SWEEP_ID, "recipe": recipe_ref,
                        "runs": [status(n, "accepted") for n in sweep.runs]},
                       "schemas/sweep_status.schema.json", 202)}
    ex["get_run"] = {
        "summary": "Read the status of a run that is executing.",
        "description": f"The `{SINGLE}` run while DIRSIG renders it; only the resolved run spec exists so far. "
                       + PLACEHOLDER,
        "request": get(f"/runs/{RUN_IDS[name]}"),
        "response": ok(status(name, "running"), "schemas/run_status.schema.json")}
    ex["get_sweep"] = {
        "summary": "Read the status of a sweep while its first run executes.",
        "description": "Each run reports its own state, in the recipe's sensor order. " + PLACEHOLDER,
        "request": get(f"/sweeps/{SWEEP_ID}"),
        "response": ok({"sweep_id": SWEEP_ID, "recipe": recipe_ref,
                        "runs": [status(n, "running" if i == 0 else "accepted") for i, n in enumerate(sweep.runs)]},
                       "schemas/sweep_status.schema.json")}
    ex["cancel_run"] = {
        "summary": "Cancel a run that is executing.",
        "description": f"The `{SINGLE}` run, cancelled while `running`. {PLACEHOLDER}",
        "request": {"method": "POST", "path": f"/runs/{RUN_IDS[name]}/cancel"},
        "response": ok(status(name, "cancelled"), "schemas/run_status.schema.json")}
    ex["list_artifacts"] = {
        "summary": "List the artifacts of a run that has not rendered yet.",
        "description": ("Only the resolved run spec exists before the run renders; the logs, the image, its header "
                        f"and the truth images are listed as they are written. {PLACEHOLDER}"),
        "request": get(f"/runs/{RUN_IDS[name]}/artifacts"),
        "response": ok({"run_id": RUN_IDS[name], "artifacts": [spec_artifact(RUN_IDS[name])]},
                       "schemas/artifact_list.schema.json")}
    ex["get_artifact"] = {
        "summary": "Read the resolved run spec of a run.",
        "description": ("The bytes are the canonical JSON serialization (RFC 8785) of the resolved run spec, the "
                        "spec with its sensor block in place, so they hash to the run id; they are shown here as a "
                        f"parsed document, complete. {PLACEHOLDER}"),
        "request": get(f"/runs/{RUN_IDS[name]}/artifacts/run_spec.json"),
        "response": ok(compose(LAYERS / "recipes" / f"{SINGLE}.yaml", inline_sensor=True),
                       "schemas/run_spec_document.schema.json")}
    pid = RUN_IDS["leo-pass-tahoe"]
    pass_spec = _COMPOSED[PASS].runs["leo-pass-tahoe"]
    assert compute_run_id(pass_spec, SENSORS) == pid
    frames = []
    for k, _ in enumerate(pass_spec["engine"]["tasks"]["windows"]):
        for base, kind in (("AurorNIROutput", "image"), ("truth1", "truth")):
            for ext, media in ((".img", "application/octet-stream"), (".img.hdr", "text/plain")):
                name = f"{base}-t{k:04d}-c0000{ext}"
                frames.append({"name": name, "sha256": ZERO, "media_type": media, "uri": f"{RUN_DIR}/{pid}/{name}",
                               "frame": k})
    logs = [{"name": n, "sha256": ZERO, "media_type": "application/json", "uri": f"{RUN_DIR}/{pid}/{n}"}
            for n in ("run_info.json", "log_info.json")]
    ex["list_artifacts.pass"] = {
        "summary": f"List the artifacts of the rendered `{PASS}` run: three frames.",
        "description": ("A multi-frame run lists one image, one header and one truth product per capture, named "
                        "`<base>-t<task>-c<capture>` as the pass template writes them, each with its zero-based `frame`; "
                        "the run spec and the engine logs belong to the run as a whole and carry no frame. "
                        f"{PLACEHOLDER} {RENDERED_PLACEHOLDER}"),
        "request": get(f"/runs/{pid}/artifacts"),
        "response": ok({"run_id": pid, "artifacts": [spec_artifact(pid)] + logs + frames},
                       "schemas/artifact_list.schema.json")}
    for k, v in ex.items():
        v["operation"] = k.split(".")[0]
    return ex


def render(e):
    return json.dumps(e, indent=2, ensure_ascii=False) + "\n"


def main(argv):
    want = {f"{k}.json": render(v) for k, v in examples().items()}
    have = {p.name: p.read_text() for p in OUT.glob("*.json")}
    if "--check" in argv:
        bad = sorted(n for n in want.keys() | have.keys() if want.get(n) != have.get(n))
        for n in bad:
            print(f"stale, missing or orphaned example: api/examples/{n}")
        return 1 if bad else 0
    OUT.mkdir(parents=True, exist_ok=True)
    for n in have.keys() - want.keys():
        (OUT / n).unlink()
    for n, text in want.items():
        (OUT / n).write_text(text)
    print(f"wrote {len(want)} examples to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
