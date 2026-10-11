"""The pass-through engine form (proposed): contract, identity, admission, composition, stamping and the dry-run level.

A synthetic demo directory (no DIRSIG demo bytes) is placed in a temporary engine-asset library; the engine is the stub
`tests/stub_engine.py`, never DIRSIG.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from protodirsig import identity
from protodirsig.admission import validate_spec
from protodirsig.compose import ComposeError, compose_sweep
from protodirsig.contract import schema_errors
from protodirsig.dirhash import directory_digest
from protodirsig.errors import AdmissionError
from protodirsig.passthrough import resolve_passthrough
from protodirsig.problems import locate
from protodirsig.run_spec import RunSpecError, unstamped_refs

ROOT = Path(__file__).resolve().parents[1]
VECTOR = ROOT / "manifold_contracts" / "vectors" / "identity" / "passthrough"
EXPECTED = json.loads((VECTOR / "expected.json").read_text())
STUB = Path(__file__).with_name("stub_engine.py")


def stub_engine(folder):
    """An executable that runs the stub engine with this interpreter."""
    path = Path(folder) / "dirsig5-stub"
    path.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{STUB}" "$@"\n')
    path.chmod(0o755)
    return path


def _spec():
    return yaml.safe_load((VECTOR / "spec.yaml").read_text())


@pytest.fixture
def library(tmp_path):
    """A temporary engine-asset library holding the vector's directory at demo_dirs/PassthroughVector."""
    lib = tmp_path / "config_repo"
    shutil.copytree(VECTOR / "tree", lib / "demo_dirs" / "PassthroughVector")
    return lib


# --- contract and identity ------------------------------------------------------------------------------------------

def test_the_vector_digest_is_reproducible_by_the_shell_pipeline():
    if not all(shutil.which(t) for t in ("find", "sort", "xargs", "sha256sum")):
        pytest.skip("find, sort, xargs or sha256sum is not installed")
    out = subprocess.run("LC_ALL=C find . -type f -printf '%P\\0' | LC_ALL=C sort -z | xargs -0 -r sha256sum | sha256sum",
                         shell=True, cwd=VECTOR / EXPECTED["directory"], capture_output=True, text=True, check=True)
    assert "sha256:" + out.stdout.split()[0] == EXPECTED["digest"] == directory_digest(VECTOR / "tree")
    assert _spec()["engine"]["passthrough"]["directory"]["content_hash"] == EXPECTED["digest"]


def test_the_vector_spec_conforms_and_has_the_recorded_run_id():
    spec = _spec()
    assert schema_errors(spec) == []
    assert identity.run_id(spec, ROOT / "manifold_sensors") == EXPECTED["run_id"]
    other = copy.deepcopy(spec)
    other["engine"]["passthrough"]["simulation"] = "other.jsim"
    assert identity.run_id(other, ROOT / "manifold_sensors") != EXPECTED["run_id"]      # the path is part of the id


@pytest.mark.parametrize("edit, fragment", [
    (lambda s: s["descriptor"].pop("opaque"), "go together"),
    (lambda s: s["engine"].pop("mode"), "go together"),
    (lambda s: s["engine"].update(scenes=[]), "/engine"),
    (lambda s: s["descriptor"].update(sensor={"ref": {"name": "x.yaml", "content_hash": "sha256:<hash>"}}), "/descriptor"),
    (lambda s: s["engine"]["passthrough"].update(simulation="../escape.jsim"), "/engine/passthrough/simulation"),
    (lambda s: s["engine"]["passthrough"].update(simulation="demo.txt"), "/engine/passthrough/simulation"),
], ids=["opaque_without_mode", "mode_without_opaque", "layered_member", "sensor_in_opaque", "escaping_path", "not_a_sim"])
def test_the_schema_and_semantic_rules_refuse_mixed_forms(edit, fragment):
    spec = _spec()
    edit(spec)
    errors = schema_errors(spec)
    assert errors and any(fragment in e for e in errors), errors


def test_documents_valid_before_stay_valid():
    for path in sorted((ROOT / "manifold_run_specs").glob("*.yaml")):
        assert schema_errors(yaml.safe_load(path.read_text())) == [], path.name


# --- admission ------------------------------------------------------------------------------------------------------

def test_a_stamped_directory_resolves(library):
    run = resolve_passthrough(_spec(), library)
    assert run.simulation == library / "demo_dirs" / "PassthroughVector" / "demo.jsim" and run.seed == 1
    report = validate_spec(_spec(), None, library, ROOT / "manifold_sensors")
    assert report.valid and report.unstamped == [] and report.run_id == EXPECTED["run_id"]


def _refusal(spec, library):
    with pytest.raises(RunSpecError) as e:
        resolve_passthrough(spec, library)
    return e.value


def test_a_missing_directory_is_refused(library):
    shutil.rmtree(library / "demo_dirs")
    assert _refusal(_spec(), library).pointer == "/engine/passthrough/directory/name"


def test_a_digest_mismatch_is_refused(library):
    (library / "demo_dirs" / "PassthroughVector" / "demo.scene").write_text("<scene>edited</scene>\n")
    assert _refusal(_spec(), library).pointer == "/engine/passthrough/directory/content_hash"


def test_a_symlink_inside_is_refused(library):
    (library / "demo_dirs" / "PassthroughVector" / "link.obj").symlink_to("geometry/box.obj")
    e = _refusal(_spec(), library)
    assert e.pointer == "/engine/passthrough/directory/name" and "symbolic link" in str(e)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs on this platform")
def test_a_non_regular_file_inside_is_refused(library):
    os.mkfifo(library / "demo_dirs" / "PassthroughVector" / "pipe")
    assert _refusal(_spec(), library).pointer == "/engine/passthrough/directory/name"


@pytest.mark.parametrize("simulation", ["missing.jsim", "../outside.jsim", "/abs/demo.jsim", "geometry"])
def test_a_simulation_path_that_escapes_or_is_missing_is_refused(library, simulation):
    spec = _spec()
    spec["engine"]["passthrough"]["simulation"] = simulation
    assert _refusal(spec, library).pointer == "/engine/passthrough/simulation"


def test_an_unstamped_digest_is_listed_and_refused_at_submission(library, tmp_path):
    spec = _spec()
    spec["engine"]["passthrough"]["directory"]["content_hash"] = "sha256:<hash>"
    assert unstamped_refs(spec) == ["/engine/passthrough/directory"]
    report = validate_spec(spec, None, library, ROOT / "manifold_sensors")
    assert report.valid and report.unstamped == ["/engine/passthrough/directory"]
    from protodirsig.backend import LocalBackend
    backend = LocalBackend(tmp_path / "work", library, engine=stub_engine(tmp_path))
    with pytest.raises(AdmissionError) as e:
        backend.submit_run(spec)
    assert "/engine/passthrough/directory" in e.value.problem["detail"]
    assert backend.store.list_runs() == []


# --- composition ----------------------------------------------------------------------------------------------------

RECIPE = """compose: compose/1
meta: {name: synthetic-passthrough}
passthrough:
  directory: {name: demo_dirs/PassthroughVector, content_hash: "DIGEST"}
  simulation: demo.jsim
engine_profile: passthrough_runtime
fidelity: {modeled: [], approximated: [], absent: [], valid_for: a test}
"""
PROFILE = """origin: {kind: synthetic, engine: dirsig}
engine:
  generator: {tool: dirfm, revision: "93195cee1ccc4f31a214e114d94c493a1d4cc22f", spec_schema: dirsig-engine/1}
  run: {seed: 1}
"""


@pytest.fixture
def layers(tmp_path):
    root = tmp_path / "manifold_run_specs"
    (root / "recipes").mkdir(parents=True)
    (root / "engine_profiles").mkdir()
    (root / "scenarios").mkdir()
    (tmp_path / "manifold_sensors").mkdir()
    (root / "recipes" / "synthetic_passthrough.yaml").write_text(RECIPE.replace("DIGEST", EXPECTED["digest"]))
    (root / "engine_profiles" / "passthrough_runtime.yaml").write_text(PROFILE)
    return root


def test_a_passthrough_recipe_composes(layers):
    sweep = compose_sweep(layers / "recipes" / "synthetic_passthrough.yaml")
    ((name, spec),) = sweep.runs.items()
    assert schema_errors(spec) == [] and spec["engine"]["mode"] == "passthrough"
    assert spec["descriptor"]["opaque"] == {"source": "passthrough"} and "sensor" not in spec["descriptor"]
    assert sweep.run_ids[name] == identity.run_id(spec, layers.parent / "manifold_sensors") and sweep.sensors[name] is None
    src = sweep.sources[name]
    assert src["engine.passthrough"]["layer"] == "recipes/synthetic_passthrough.yaml"
    assert locate("/engine/passthrough/simulation", src, spec=spec) == ("recipes/synthetic_passthrough.yaml",
                                                                        "passthrough.simulation")
    assert locate("/engine/run/seed", src, spec=spec) == ("engine_profiles/passthrough_runtime.yaml", "engine.run.seed")


@pytest.mark.parametrize("edit, layer, field", [
    (("engine_profiles/passthrough_runtime.yaml", "  run: {seed: 1}\n", "  run: {seed: 1}\n  scenes: []\n"),
     "engine_profiles/passthrough_runtime.yaml", "engine.scenes"),
    (("recipes/synthetic_passthrough.yaml", "engine_profile:", "sensor: auror-nir.yaml\nengine_profile:"),
     "recipes/synthetic_passthrough.yaml", "sensor"),
    (("recipes/synthetic_passthrough.yaml", "  simulation: demo.jsim\n", ""), "recipes/synthetic_passthrough.yaml",
     "passthrough"),
    (("engine_profiles/passthrough_runtime.yaml", "origin:", "extras: {}\norigin:"),
     "engine_profiles/passthrough_runtime.yaml", "extras"),
], ids=["layered_member_in_profile", "sensor_in_recipe", "no_simulation", "extras_in_profile"])
def test_layer_ownership_stays_disjoint(layers, edit, layer, field):
    rel, old, new = edit
    path = layers / rel
    path.write_text(path.read_text().replace(old, new, 1))
    with pytest.raises(ComposeError) as e:
        compose_sweep(layers / "recipes" / "synthetic_passthrough.yaml")
    assert (e.value.layer, e.value.field) == (layer, field)


def test_the_library_reads_a_passthrough_recipe(layers):
    from protodirsig.library import LibraryReader
    doc = LibraryReader(layers).get("recipe", "synthetic_passthrough")
    assert doc["document"]["passthrough"]["simulation"] == "demo.jsim"


# --- stamping -------------------------------------------------------------------------------------------------------

def test_stamp_hashes_stamps_and_checks_a_passthrough_directory(tmp_path, monkeypatch, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location("stamp_hashes", ROOT / "scripts" / "stamp_hashes.py")
    stamp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stamp)
    shutil.copytree(VECTOR / "tree", tmp_path / "manifold_config_repo" / "demo_dirs" / "PassthroughVector")
    recipe = tmp_path / "manifold_run_specs" / "recipes" / "r.yaml"
    recipe.parent.mkdir(parents=True)
    recipe.write_text(RECIPE.replace("DIGEST", "sha256:<hash>"))
    monkeypatch.setattr(stamp, "ROOT", tmp_path)
    assert stamp.main(["--check"]) == 1 and "demo_dirs/PassthroughVector" in capsys.readouterr().out
    assert stamp.main([]) == 0 and EXPECTED["digest"] in recipe.read_text()
    assert stamp.main(["--check"]) == 0
    (tmp_path / "manifold_config_repo" / "demo_dirs" / "PassthroughVector" / "extra.txt").write_text("x")
    assert stamp.main(["--check"]) == 1


# --- validation levels ----------------------------------------------------------------------------------------------

def _backend(tmp_path, library, layers, engine):
    from protodirsig.backend import LocalBackend
    (layers.parent / "manifold_sensors").mkdir(exist_ok=True)
    return LocalBackend(tmp_path / "work", library, library=layers, engine=engine)


def test_validate_none_and_dry_run_with_a_stub_engine(tmp_path, library, layers):
    backend = _backend(tmp_path, library, layers, stub_engine(tmp_path))
    none = backend.validate("synthetic_passthrough")
    assert none["runs"][0]["valid"] and not none["runs"][0]["engine_checked"]
    dry = backend.validate("synthetic_passthrough", engine_check="dry_run")
    run = dry["runs"][0]
    assert run["valid"] and run["engine_checked"] and run["checks"][-1] == {"check": "dry_run", "passed": True, "errors": []}
    assert not list((library / "demo_dirs" / "PassthroughVector").glob("*.hdf"))      # the library is not written


def test_dry_run_reports_an_engine_failure(tmp_path, library, layers, monkeypatch):
    monkeypatch.setenv("STUB_ENGINE_EXIT", "3")
    run = _backend(tmp_path, library, layers, stub_engine(tmp_path)).validate("synthetic_passthrough", "dry_run")["runs"][0]
    assert not run["valid"] and run["engine_checked"] and "exit status 3" in run["checks"][-1]["errors"][0]["detail"]


def test_dry_run_without_an_engine_is_not_engine_checked(tmp_path, library, layers, monkeypatch):
    backend = _backend(tmp_path, library, layers, None)
    monkeypatch.setattr(backend, "_engine", lambda: None)
    run = backend.validate("synthetic_passthrough", "dry_run")["runs"][0]
    assert not run["engine_checked"] and not run["valid"] and "no DIRSIG" in run["checks"][-1]["errors"][0]["detail"]
