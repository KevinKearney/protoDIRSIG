"""Reference a pre-built DIRSIG scene from a read-only location, and prove it stayed untouched.

Factored out of tutorial_tacoma_scene.ipynb Stage 0/2. Why this shape:
`scene2hdf` writes `<scene>.hdf` + `asset_report.txt` beside the *resolved* `.scene` file and
has no output-path option, so pointing dirfm's `SCENE._fname` at a read-only scene (or at a
symlink to one) writes into that directory. Copying only the `.scene` XML next to symlinks of
its asset directories keeps every write under our own directory while the assets are read in
place through `$SCENE_DIR/...`.
"""
import filecmp
import re
import shutil
from pathlib import Path

import lxml.etree as et

ASSET_DIRS = ("geometry", "materials", "maps")
SKIPPED = ("metadata", "thumbnaillist")              # descriptive subtrees: DIRSIG renders without the files they name
LISTINGS = (".glist", ".odb")                        # files whose named files are followed one level


def reference_scene(scene_file, ref_dir, asset_dirs=ASSET_DIRS, named=None):
    """Copy `scene_file` (XML only) into a fresh `ref_dir` beside symlinks to its asset dirs.

    Returns the path of the copy — the value to assign to a dirfm `SCENE._fname`. `ref_dir` is
    wiped first; `shutil.rmtree` unlinks symlinks without following them, so the originals are
    never touched.

    `named` (optional, the `(files, directories)` of `scene_named_paths`): the files are copied into
    `ref_dir` at their relative paths, byte-identical (not linked: `scene2hdf` writes beside the
    `.scene`), and the directories are linked like the asset dirs. Without it nothing else is placed.
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
    files, dirs = named or ((), ())
    for rel in dirs:
        (ref_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        (ref_dir / rel).symlink_to(scene_file.parent / rel, target_is_directory=True)
    for rel in files:
        copy_input(scene_file.parent / rel, ref_dir / rel)
    assert filecmp.cmp(scene_file, copy, shallow=False)
    return copy


def _leaf_texts(root):
    """The text of every leaf element outside the descriptive subtrees, with `$SCENE_DIR` removed."""
    for el in root.iter():
        if (isinstance(el.tag, str) and len(el) == 0 and (el.text or "").strip()
                and not any(a.tag in SKIPPED for a in el.iterancestors())):
            yield re.sub(r"^\$SCENE_DIR/?", "", el.text.strip().replace("\\", "/"))


def scene_named_paths(scene_file, asset_dirs=ASSET_DIRS):
    """`(files, directories)`: the paths, relative to the scene's folder, that a `.scene` names inside that folder
    and that `reference_scene` does not place by default (outside `asset_dirs`). A leaf element's text that resolves
    against the folder to a regular file is a file (followed one level when it is a `.glist` or `.odb`, its names
    resolved against its own folder, then the scene's); to a directory other than the folder itself, a directory.
    Files under a returned directory are not returned. Metadata and thumbnails are not read. Sorted tuples."""
    scene_file = Path(scene_file)
    top = scene_file.parent.resolve()

    def inside(path):
        try:
            rel = path.resolve().relative_to(top)
        except ValueError:
            return None                                           # outside the scene's folder: not placed here
        return None if not rel.parts or rel.parts[0] in asset_dirs else rel

    def names(xml_file, bases):
        try:
            root = et.parse(str(xml_file)).getroot()
        except (et.XMLSyntaxError, OSError):
            return []
        out = []
        for text in _leaf_texts(root):
            for base in bases:
                cand = base / text
                if cand.exists():
                    out.append(cand)
                    break
        return out

    files, dirs = set(), set()
    found = names(scene_file, [top])
    for path in list(found):
        if path.is_file() and path.suffix in LISTINGS and inside(path) is not None:
            found += names(path, [path.parent, top])
    for path in found:
        rel = inside(path)
        if rel is None or path.resolve() == scene_file.resolve():
            continue
        (files if path.is_file() else dirs if path.is_dir() else set()).add(rel.as_posix())
    files = {f for f in files if not any(f.startswith(d + "/") for d in dirs)}
    return tuple(sorted(files)), tuple(sorted(dirs))


def copy_input(src, dst):
    """Copy one read-only input file to `dst`, asserted byte-identical. Returns `dst`. Used so a
    job references its own copy, never the original: in the stage jobs, the manifold_config_repo platform,
    weather and atmosphere database (motion and tasks are generated, not copied)."""
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    assert filecmp.cmp(src, dst, shallow=False)
    return dst


def fingerprint(root):
    """(relative path, size, mtime_ns, mode) for `root` and everything under it, sorted.

    Compare a before/after pair with `==` to assert a directory tree was not modified.
    """
    root = Path(root)
    return sorted((str(p.relative_to(root)), p.lstat().st_size, p.lstat().st_mtime_ns, p.lstat().st_mode)
                  for p in [root, *root.rglob("*")])
