"""`dirhash/1` (protodirsig.dirhash): the directory digest a `.scene` reference carries.

The fixture under manifold_contracts/vectors/identity/dirhash/ must give the recorded manifest and digest, and the
shell pipeline of the definition must agree. Forbidden entries raise; any change to a file's bytes, name or presence
changes the digest; creation order does not. A validate run (a DIRSIG dry run) must leave the Tahoe scene directory's
digest unchanged.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from protodirsig.dirhash import directory_digest, directory_manifest, is_directory_ref
from protodirsig.simulation import Simulation
from test_simulation import CONFIG_REPO, SPEC, needs_dirsig

PROJECT = Path(__file__).resolve().parents[1]
VECTOR = PROJECT / "manifold_contracts" / "vectors" / "identity" / "dirhash"
EXPECTED = json.loads((VECTOR / "expected.json").read_text())
TREE = VECTOR / EXPECTED["directory"]
SHELL = "LC_ALL=C find . -type f -printf '%P\\0' | LC_ALL=C sort -z | xargs -0 -r sha256sum"
FILES = {"a.txt": b"one\n", "B.txt": b"two\n", "a/b.txt": b"three\n", "a/c/d.dat": b"\x00\x01", "é.txt": b"four\n"}


def _tree(root, files=FILES, order=None):
    for rel in order or files:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(files[rel])
    return root


def test_fixture_gives_the_recorded_manifest_and_digest():
    assert directory_manifest(TREE).decode("utf-8") == EXPECTED["manifest"]
    assert directory_digest(TREE) == EXPECTED["digest"]


def test_fixture_meets_the_vector_requirements():
    files = [p.relative_to(TREE).as_posix() for p in TREE.rglob("*") if p.is_file()]
    assert len(files) >= 4 and any("/" in f for f in files) and any(not f.isascii() for f in files)


@pytest.mark.skipif(not all(shutil.which(t) for t in ("find", "sort", "xargs", "sha256sum")),
                    reason="find, sort, xargs or sha256sum is not installed")
@pytest.mark.parametrize("which", ["fixture", "tahoe"])
def test_shell_pipeline_agrees(which):
    root = TREE if which == "fixture" else CONFIG_REPO / "scenes" / "tahoe"
    if not root.is_dir():
        pytest.skip(f"{root} not present")
    out = subprocess.run(SHELL, shell=True, cwd=root, capture_output=True, check=True).stdout
    assert out == directory_manifest(root)
    assert "sha256:" + subprocess.run("sha256sum", input=out, capture_output=True, check=True).stdout.split()[0].decode() \
        == directory_digest(root)


def test_an_empty_directory_has_the_empty_manifest(tmp_path):
    (tmp_path / "only" / "empty" / "subdirectories").mkdir(parents=True)
    want = EXPECTED["empty_directory"]
    assert directory_manifest(tmp_path).decode() == want["manifest"] == ""
    assert directory_digest(tmp_path) == want["digest"]
    if all(shutil.which(t) for t in ("find", "sort", "xargs", "sha256sum")):
        out = subprocess.run(SHELL, shell=True, cwd=tmp_path, capture_output=True, check=True).stdout
        assert out == b""                                            # xargs -r: no sha256sum run on empty input
        assert "sha256:" + subprocess.run("sha256sum", input=out, capture_output=True, check=True).stdout.split()[0] \
            .decode() == want["digest"]


def test_a_symlink_raises(tmp_path):
    _tree(tmp_path)
    (tmp_path / "a" / "link.txt").symlink_to(tmp_path / "a.txt")
    with pytest.raises(ValueError, match=r"link\.txt.*symbolic link"):
        directory_digest(tmp_path)


def test_a_symlinked_directory_raises(tmp_path):
    _tree(tmp_path / "t")
    (tmp_path / "t" / "more").symlink_to(tmp_path / "t" / "a", target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic link"):
        directory_digest(tmp_path / "t")


def test_a_newline_in_a_file_name_raises(tmp_path):
    _tree(tmp_path)
    (tmp_path / "a" / "two\nlines.txt").write_bytes(b"x")
    with pytest.raises(ValueError, match="backslash or a newline"):
        directory_digest(tmp_path)


def test_a_backslash_in_a_file_name_raises(tmp_path):
    _tree(tmp_path)
    (tmp_path / "back\\slash.txt").write_bytes(b"x")
    with pytest.raises(ValueError, match="backslash or a newline"):
        directory_digest(tmp_path)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs on this platform")
def test_a_fifo_raises(tmp_path):
    _tree(tmp_path)
    os.mkfifo(tmp_path / "a" / "pipe")
    with pytest.raises(ValueError, match="pipe.*not a regular file"):
        directory_digest(tmp_path)


def _add(root):
    (root / "a" / "new.txt").write_bytes(b"new\n")


def _remove(root):
    (root / "a" / "b.txt").unlink()


def _rename(root):
    (root / "a" / "b.txt").rename(root / "a" / "b2.txt")


def _move(root):
    (root / "a" / "b.txt").rename(root / "b.txt")             # same name and bytes, another directory


def _one_byte(root):
    data = bytearray((root / "a" / "c" / "d.dat").read_bytes())
    data[0] ^= 1
    (root / "a" / "c" / "d.dat").write_bytes(bytes(data))


@pytest.mark.parametrize("change", [_add, _remove, _rename, _move, _one_byte], ids=lambda f: f.__name__[1:])
def test_any_change_changes_the_digest(tmp_path, change):
    root = _tree(tmp_path)
    before = directory_digest(root)
    change(root)
    assert directory_digest(root) != before


def test_empty_directories_and_metadata_do_not_count(tmp_path):
    root = _tree(tmp_path)
    before = directory_digest(root)
    (root / "empty" / "nested").mkdir(parents=True)
    os.utime(root / "a.txt", (0, 0))
    os.chmod(root / "B.txt", 0o600)
    assert directory_digest(root) == before


def test_creation_order_does_not_matter(tmp_path):
    first = _tree(tmp_path / "one", order=sorted(FILES))
    second = _tree(tmp_path / "two", order=sorted(FILES, reverse=True))
    assert directory_digest(first) == directory_digest(second)


def test_not_a_directory_raises(tmp_path):
    (tmp_path / "f").write_bytes(b"")
    with pytest.raises(ValueError, match="not a directory"):
        directory_digest(tmp_path / "f")


def test_directory_refs_are_scene_files():
    assert is_directory_ref("scenes/tahoe/tahoe.scene")
    assert not is_directory_ref("platforms/auror.platform") and not is_directory_ref(None)


@needs_dirsig
def test_a_validate_run_leaves_the_scene_directory_unaltered(tmp_path):
    scene_dir = CONFIG_REPO / "scenes" / "tahoe"
    before = directory_digest(scene_dir)
    c = Simulation.from_run_spec(SPEC, CONFIG_REPO, tmp_path).validate()
    assert c.passed, c
    assert directory_digest(scene_dir) == before
