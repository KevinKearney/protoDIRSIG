"""Reference a pre-built DIRSIG scene from a read-only location, and prove it stayed untouched.

Factored out of tutorial_tacoma_scene.ipynb Stage 0/2. Why this shape (FINDINGS.md, Phase 3):
`scene2hdf` writes `<scene>.hdf` + `asset_report.txt` beside the *resolved* `.scene` file and
has no output-path option, so pointing dirfm's `SCENE._fname` at a read-only scene (or at a
symlink to one) writes into that directory. Copying only the `.scene` XML next to symlinks of
its asset directories keeps every write under our own directory while the assets are read in
place through `$SCENE_DIR/...`.
"""
import filecmp
import shutil
from pathlib import Path

ASSET_DIRS = ("geometry", "materials", "maps")


def reference_scene(scene_file, ref_dir, asset_dirs=ASSET_DIRS):
    """Copy `scene_file` (XML only) into a fresh `ref_dir` beside symlinks to its asset dirs.

    Returns the path of the copy — the value to assign to a dirfm `SCENE._fname`. `ref_dir` is
    wiped first; `shutil.rmtree` unlinks symlinks without following them, so the originals are
    never touched.
    """
    scene_file, ref_dir = Path(scene_file), Path(ref_dir)
    if ref_dir.exists():
        shutil.rmtree(ref_dir)
    ref_dir.mkdir(parents=True)
    copy = ref_dir / scene_file.name
    shutil.copy2(scene_file, copy)
    for sub in asset_dirs:
        if (scene_file.parent / sub).is_dir():
            (ref_dir / sub).symlink_to(scene_file.parent / sub, target_is_directory=True)
    assert filecmp.cmp(scene_file, copy, shallow=False)
    return copy


def fingerprint(root):
    """(relative path, size, mtime_ns, mode) for `root` and everything under it, sorted.

    Compare a before/after pair with `==` to assert a directory tree was not modified.
    """
    root = Path(root)
    return sorted((str(p.relative_to(root)), p.lstat().st_size, p.lstat().st_mtime_ns, p.lstat().st_mode)
                  for p in [root, *root.rglob("*")])
