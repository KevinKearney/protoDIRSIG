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


def _relative_name(text):
    """`text` as a name relative to a folder (`$SCENE_DIR/` removed, backslashes as slashes), or None when it is empty,
    absolute, names a variable or leaves the folder."""
    text = re.sub(r"^\$SCENE_DIR/?", "", (text or "").strip().replace("\\", "/"))
    if not text or text.startswith(("$", "/")) or ".." in Path(text).parts:
        return None
    return Path(text).as_posix()


def working_folder_files(scene_file, platform_file):
    """`[(name, source, named_by)]`: the files DIRSIG looks for in the working folder, the folder it runs in, which is
    the demo's folder for a pass-through run and the job's input folder for a layered one (measured on BayerPattern1
    and Telecentricity1, `docs/DIRSIG_layered_comparison.md`). `name` is the path relative to the working folder,
    `source` the file it is copied from, `named_by` the file that names it. Two rules:

    - a file the `.platform` names in a `<filename>` by a relative name that lies relative to the platform's folder
      (BayerPattern1's `pixels.hdf`; DIRSIG does not look beside the platform file);
    - a geometry list the `.scene` names in a `<geometrylistinclude>` by a relative name that lies beside the `.scene`
      and not in its `<gdbdirectory>` (DIRSIG looks in the working folder and the `gdbdirectory` only), and every file
      that list names in a `<filename>` that lies beside the list and not in the `gdbdirectory` (Telecentricity1's
      `demo.glist` and `Sphere.obj`).

    Empty for a scene and platform that need neither, which is every library scene and platform: their jobs are
    assembled as before. Sorted by name; a name found twice is kept once (the first source in rule order)."""
    scene_file, platform_file = Path(scene_file), Path(platform_file)
    out = {}

    def parse(path):
        try:
            return et.parse(str(path)).getroot()
        except (et.XMLSyntaxError, OSError):
            return None

    plat = parse(platform_file)
    for el in (plat.iter("filename") if plat is not None else ()):
        name = _relative_name(el.text)
        if name is not None and (platform_file.parent / name).is_file():
            out.setdefault(name, (platform_file.parent / name, platform_file.name))
    scene = parse(scene_file)
    if scene is not None:
        top = scene_file.parent
        gdb = top / (_relative_name(scene.findtext("gdbdirectory")) or "")
        for el in scene.iter("geometrylistinclude"):
            name = _relative_name(el.text)
            if name is None or not (top / name).is_file() or (gdb / name).is_file():
                continue
            out.setdefault(name, (top / name, scene_file.name))
            listing = parse(top / name)
            for item in (listing.iter("filename") if listing is not None else ()):
                member = _relative_name(item.text)
                if member is not None and ((top / name).parent / member).is_file() and not (gdb / member).is_file():
                    out.setdefault(member, ((top / name).parent / member, Path(name).name))
    return [(name, src, by) for name, (src, by) in sorted(out.items())]


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
