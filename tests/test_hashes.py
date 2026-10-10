"""Stamped `content_hash` values: current in the repo, verified by the loaders, restamped by the script."""
import importlib.util
import shutil
from pathlib import Path

import pytest

from protodirsig.run_spec import RunSpecError, load_run_spec, resolve_auror_run
from protodirsig.spectral import SpectralError, read_curve, resolve_curve

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "manifold_run_specs" / "auror_ref.yaml"
spec = importlib.util.spec_from_file_location("stamp_hashes", ROOT / "scripts" / "stamp_hashes.py")
stamp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stamp)


def test_repo_hashes_are_current():
    assert stamp.main(["--check"]) == 0, "run scripts/stamp_hashes.py"


def test_edited_sensor_spec_fails_resolution(tmp_path):
    lib = tmp_path / "manifold_sensors"
    shutil.copytree(ROOT / "manifold_sensors", lib)
    (lib / "auror-nir.yaml").write_text((lib / "auror-nir.yaml").read_text() + "\n# edited\n")
    run = load_run_spec(SPEC)
    with pytest.raises(RunSpecError, match="stamp_hashes"):
        resolve_auror_run(run, SPEC, ROOT / "manifold_config_repo", lib)


def test_placeholder_hash_is_not_verified(tmp_path):
    lib = tmp_path / "manifold_sensors"
    shutil.copytree(ROOT / "manifold_sensors", lib)
    (lib / "auror-nir.yaml").write_text((lib / "auror-nir.yaml").read_text() + "\n# edited\n")
    run = load_run_spec(SPEC)
    run["descriptor"]["sensor"]["ref"]["content_hash"] = "sha256:<hash>"
    assert resolve_auror_run(run, SPEC, ROOT / "manifold_config_repo", lib).sensor["meta"]["name"] == "auror-nir"


def test_edited_curve_fails(tmp_path):
    lib = tmp_path / "manifold_sensors"
    shutil.copytree(ROOT / "manifold_sensors", lib)
    path = lib / "spectral" / "qe" / "synthetic_visgaas.csv"
    path.write_text(path.read_text().replace("0.900,0.800000", "0.900,0.700000"))
    ref = {"name": "spectral/qe/synthetic_visgaas.csv", "content_hash": stamp.digest(ROOT / "manifold_sensors/spectral/qe/synthetic_visgaas.csv")}
    with pytest.raises(SpectralError, match="content_hash"):
        resolve_curve(lib, ref)
    assert read_curve(path).value.max() == pytest.approx(0.8, abs=0.11)      # the file itself still parses


def test_stale_scene_digest_fails_resolution():
    run = load_run_spec(SPEC)
    run["engine"]["scenes"][0]["ref"]["content_hash"] = "sha256:" + "0" * 64
    with pytest.raises(RunSpecError, match=r"scene directory tahoe: content_hash .* does not match the directory.*stamp_hashes"):
        resolve_auror_run(run, SPEC, ROOT / "manifold_config_repo")


def test_scene_placeholder_is_not_verified():
    run = load_run_spec(SPEC)
    run["engine"]["scenes"][0]["ref"]["content_hash"] = "sha256:<hash>"
    assert resolve_auror_run(run, SPEC, ROOT / "manifold_config_repo").scene.name == "tahoe.scene"


def test_repo_scene_refs_carry_the_directory_digest():
    run = load_run_spec(SPEC)
    assert run["engine"]["scenes"][0]["ref"]["content_hash"] == \
        stamp.dirhash.directory_digest(ROOT / "manifold_config_repo" / "scenes" / "tahoe")


def test_check_reports_a_stale_scene_digest(tmp_path, monkeypatch, capsys):
    scene = tmp_path / "manifold_config_repo" / "scenes" / "s"
    (scene / "geometry").mkdir(parents=True)
    (scene / "s.scene").write_text("<scene/>\n")
    (scene / "geometry" / "g.obj").write_text("v 0 0 0\n")
    ref = f'{{name: scenes/s/s.scene, content_hash: "{stamp.dirhash.directory_digest(scene)}"}}'
    layer = tmp_path / "manifold_run_specs" / "engine_profiles" / "p.yaml"
    layer.parent.mkdir(parents=True)
    layer.write_text(f"engine:\n  scenes:\n    - ref: {ref}\n")
    generated = tmp_path / "manifold_run_specs" / "g.yaml"
    generated.write_text(f"{stamp.GENERATED} from recipes/r.yaml - do not edit\n\nengine:\n  scenes:\n  - ref:\n"
                         f"      name: scenes/s/s.scene\n      content_hash: {stamp.dirhash.directory_digest(scene)}\n")
    monkeypatch.setattr(stamp, "ROOT", tmp_path)
    assert stamp.main(["--check"]) == 0
    (scene / "geometry" / "g.obj").write_text("v 0 0 1\n")               # a geometry edit, the .scene file unchanged
    capsys.readouterr()
    assert stamp.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "stale  manifold_run_specs/engine_profiles/p.yaml: scenes/s/s.scene" in out
    assert "manifold_run_specs/g.yaml: scenes/s/s.scene (regenerate" in out
    assert stamp.main([]) == 0 and stamp.dirhash.directory_digest(scene) in layer.read_text()


def test_engine_profiles_carry_the_pinned_dirfm_revision():
    for path in sorted((ROOT / "manifold_run_specs" / "engine_profiles").glob("*.yaml")):
        assert f'revision: "{stamp.pinned_revision()}"' in path.read_text(), path.name


def test_check_reports_and_stamps_a_placeholder_generator_revision(tmp_path, monkeypatch, capsys):
    (tmp_path / "external").mkdir()
    shutil.copy2(ROOT / "external" / "pins.json", tmp_path / "external" / "pins.json")
    layer = tmp_path / "manifold_run_specs" / "engine_profiles" / "p.yaml"
    layer.parent.mkdir(parents=True)
    layer.write_text('engine:\n  generator: {tool: dirfm, revision: "<git-sha>", spec_schema: dirsig-engine/1}\n')
    generated = tmp_path / "manifold_run_specs" / "g.yaml"
    generated.write_text(f"{stamp.GENERATED} from recipes/r.yaml - do not edit\n\nengine:\n  generator:\n    tool: dirfm\n"
                         "    revision: 0123abc\n    spec_schema: dirsig-engine/1\n")
    monkeypatch.setattr(stamp, "ROOT", tmp_path)
    assert stamp.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "p.yaml: engine.generator.revision <git-sha>" in out
    assert "g.yaml: engine.generator.revision 0123abc (regenerate" in out
    stamp.main([])
    assert f'revision: "{stamp.pinned_revision()}"' in layer.read_text()
