"""`scripts/bootstrap.py assets`: the asset manifest (assets/1) materialized from a synthetic zip (no DIRSIG demo bytes)
into a temporary library root, with refusals and verification."""
import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bootstrap", ROOT / "scripts" / "bootstrap.py")
boot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boot)
SCHEMA = json.loads((ROOT / "manifold_contracts" / "assets-1.schema.json").read_text())
FILES = {"Demo1/demo.scene": b"<scene/>\n", "Demo1/geometry/a.obj": b"v 0 0 0\n", "Demo1/materials/m.mat": b"mat\n",
         "Demo1/demo.platform": b"<platform/>\n", "Demo1/README.txt": b"readme\n"}
SCENE_MEMBERS = ["demo.scene", "geometry/a.obj", "materials/m.mat"]


def _zip(dirsig, files=FILES, extra=None):
    path = dirsig / "demos" / "zips" / "Demo1.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
        for info, data in (extra or []):
            z.writestr(info, data)
    return path


def _scene_digest(tmp_path):
    d = tmp_path / "expect"
    for m in SCENE_MEMBERS:
        (d / m).parent.mkdir(parents=True, exist_ok=True)
        (d / m).write_bytes(FILES[f"Demo1/{m}"])
    return boot.dirhash.directory_digest(d), sum(len(FILES[f"Demo1/{m}"]) for m in SCENE_MEMBERS)


@pytest.fixture
def setup(tmp_path):
    dirsig, library = tmp_path / "dirsig", tmp_path / "library"
    library.mkdir()
    _zip(dirsig)
    digest, size = _scene_digest(tmp_path)
    manifest = {"version": "assets/1", "assets": [
        {"path": "demos/Demo1/scenes/demo", "kind": "directory", "digest": digest, "size": size,
         "source": {"kind": "zip", "archive": "{dirsig}/demos/zips/Demo1.zip", "prefix": "Demo1", "members": SCENE_MEMBERS}},
        {"path": "demos/Demo1/demo.platform", "kind": "file",
         "digest": "sha256:" + hashlib.sha256(FILES["Demo1/demo.platform"]).hexdigest(), "size": len(FILES["Demo1/demo.platform"]),
         "source": {"kind": "zip", "archive": "{dirsig}/demos/zips/Demo1.zip", "prefix": "Demo1/demo.platform"}}]}
    (library / "assets.json").write_text(json.dumps(manifest))
    return dirsig, library, manifest


def _run(library, dirsig, **kw):
    lines = []
    rc = boot.assets(library, dirsig, out=lines.append, **kw)
    return rc, lines


def test_the_manifests_validate_against_the_schema(setup):
    Draft202012Validator.check_schema(SCHEMA)
    v = Draft202012Validator(SCHEMA)
    assert list(v.iter_errors(setup[2])) == []
    assert list(v.iter_errors(json.loads((ROOT / "manifold_config_repo" / "assets.json").read_text()))) == []
    bad = json.loads(json.dumps(setup[2]))
    bad["assets"][0]["path"] = "../outside"
    assert list(v.iter_errors(bad))


def test_extraction_places_the_files_and_verifies(setup):
    dirsig, library, manifest = setup
    assert _run(library, dirsig, status_only=True)[1] == ["missing   demos/Demo1/scenes/demo", "missing   demos/Demo1/demo.platform"]
    rc, lines = _run(library, dirsig)
    assert rc == 0 and lines == ["placed    demos/Demo1/scenes/demo", "placed    demos/Demo1/demo.platform"]
    scene = library / "demos/Demo1/scenes/demo"
    assert sorted(p.relative_to(scene).as_posix() for p in scene.rglob("*") if p.is_file()) == sorted(SCENE_MEMBERS)
    assert boot.dirhash.directory_digest(scene) == manifest["assets"][0]["digest"]
    assert not (scene / "README.txt").exists() and not list(library.glob(".assets-tmp-*"))
    assert _run(library, dirsig, status_only=True)[1] == ["ok        demos/Demo1/scenes/demo", "ok        demos/Demo1/demo.platform"]
    assert _run(library, dirsig) == (0, ["ok        demos/Demo1/scenes/demo", "ok        demos/Demo1/demo.platform"])


def test_a_tampered_member_fails_verification(setup):
    dirsig, library, _ = setup
    _zip(dirsig, {**FILES, "Demo1/geometry/a.obj": b"v 9 9 9\n"})
    rc, lines = _run(library, dirsig)
    assert rc == 1 and lines[0].startswith("failed    demos/Demo1/scenes/demo: digest")
    assert not (library / "demos/Demo1/scenes/demo").exists()                # nothing placed from a failed entry


@pytest.mark.parametrize("name", ["Demo1/../../evil.txt", "/etc/evil.txt"], ids=["dotdot", "absolute"])
def test_an_escaping_member_is_refused(setup, name):
    dirsig, library, manifest = setup
    _zip(dirsig, {**FILES, name: b"x"})
    entry = {"path": "demos/Demo1/evil", "kind": "file", "digest": "sha256:" + hashlib.sha256(b"x").hexdigest(), "size": 1,
             "source": {"kind": "zip", "archive": "{dirsig}/demos/zips/Demo1.zip", "prefix": name}}
    with pytest.raises(boot.AssetError, match="escapes"):
        boot.materialize(entry, library, dirsig)
    entry2 = {**manifest["assets"][0], "source": {**manifest["assets"][0]["source"], "members": ["../../evil.txt"]}}
    with pytest.raises(boot.AssetError):
        boot.materialize(entry2, library, dirsig)
    assert not (library.parent / "evil.txt").exists()


def test_a_symlink_member_is_refused(setup):
    dirsig, library, manifest = setup
    link = zipfile.ZipInfo("Demo1/geometry/link.obj")
    link.external_attr = (0o120777 << 16)
    _zip(dirsig, extra=[(link, "a.obj")])
    entry = {**manifest["assets"][0], "source": {**manifest["assets"][0]["source"], "members": SCENE_MEMBERS + ["geometry/link.obj"]}}
    with pytest.raises(boot.AssetError, match="symbolic link"):
        boot.materialize(entry, library, dirsig)


def test_an_existing_different_file_is_reported_not_overwritten(setup):
    dirsig, library, _ = setup
    target = library / "demos/Demo1/demo.platform"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"<platform>mine</platform>\n")
    rc, lines = _run(library, dirsig, only="demos/Demo1/demo.platform")
    assert rc == 1 and "exists and differs; not overwritten" in lines[0]
    assert target.read_bytes() == b"<platform>mine</platform>\n"
    assert _run(library, dirsig, status_only=True, only="demos/Demo1/demo.platform")[1] == ["mismatch  demos/Demo1/demo.platform"]


def test_only_limits_the_work(setup):
    dirsig, library, _ = setup
    assert _run(library, dirsig, only="demos/Demo1/scenes") == (0, ["placed    demos/Demo1/scenes/demo"])
    assert not (library / "demos/Demo1/demo.platform").exists()


def test_status_reports_no_source(setup):
    dirsig, library, _ = setup
    (dirsig / "demos" / "zips" / "Demo1.zip").unlink()
    rc, lines = _run(library, dirsig, status_only=True)
    assert rc == 1 and lines == ["no source demos/Demo1/scenes/demo", "no source demos/Demo1/demo.platform"]
    rc, lines = _run(library, dirsig)
    assert rc == 1 and "not found" in lines[0]


def test_an_absent_manifest_is_empty(tmp_path):
    assert boot.load_manifest(tmp_path) == {"version": "assets/1", "assets": []}


def test_the_demo_subtree_is_gitignored():
    import subprocess
    r = subprocess.run(["git", "check-ignore", "-q", "manifold_config_repo/demos/X/scenes/x/x.scene"], cwd=ROOT)
    assert r.returncode == 0
    r = subprocess.run(["git", "check-ignore", "-q", "manifold_config_repo/assets.json"], cwd=ROOT)
    assert r.returncode == 1


def test_stamp_hashes_skips_an_absent_demo_subtree(tmp_path, monkeypatch, capsys):
    """A fresh clone before `bootstrap.py assets`: a layer that names demo assets checks clean (the targets are absent,
    so they are skipped, as any unresolvable name is)."""
    sspec = importlib.util.spec_from_file_location("stamp_hashes", ROOT / "scripts" / "stamp_hashes.py")
    stamp = importlib.util.module_from_spec(sspec)
    sspec.loader.exec_module(stamp)
    layer = tmp_path / "manifold_run_specs" / "engine_profiles" / "demo.yaml"
    layer.parent.mkdir(parents=True)
    layer.write_text('engine:\n  scenes:\n    - ref: {name: demos/Demo1/scenes/demo/demo.scene, content_hash: "sha256:'
                     + "a" * 64 + '"}\n  platform:\n    ref: {name: demos/Demo1/demo.platform, content_hash: "sha256:'
                     + "b" * 64 + '"}\n')
    monkeypatch.setattr(stamp, "ROOT", tmp_path)
    assert stamp.main(["--check"]) == 0 and capsys.readouterr().out == ""
