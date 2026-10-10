#!/usr/bin/env python3
"""Populate external/ (dirfm, agent-docs, DIRSIG link) from external/pins.json, and materialize library assets.

    python scripts/bootstrap.py status
    python scripts/bootstrap.py install [--link NAME=PATH ...]
    python scripts/bootstrap.py assets [--only PATH_PREFIX]
    python scripts/bootstrap.py assets --status

dirfm and agent-docs are cloned and checked out at the pinned commit, or symlinked from an existing
checkout with --link. The DIRSIG installation is never copied: it is linked from $DIRSIG_HOME or
~/DIRSIG/<version>. Nothing in a dirfm checkout is ever modified.

`assets` materializes the entries of `manifold_config_repo/assets.json` (`assets/1`,
manifold_contracts/assets-1.schema.json): library files that cannot be committed (a DIRSIG demo's scene, platform,
motion or atmosphere files), each a `file` or a `directory` under `manifold_config_repo/`, extracted from its source
archive (`{dirsig}` is the linked install, external/dirsig) into a gitignored path and verified against its digest
(sha256 of a file's bytes; the `dirhash/1` digest of a directory). A member whose path escapes the target, a symbolic
link member and a name `dirhash/1` forbids are refused; an existing file that differs is reported and never
overwritten. Each entry is extracted into a temporary directory and moved into place only after its digest verifies.
`--status` classifies each entry as ok, missing, mismatch or no source, extracting nothing. Standard library only;
`src/protodirsig/dirhash.py` is loaded by file path.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "external"
LIBRARY = ROOT / "manifold_config_repo"
_spec = importlib.util.spec_from_file_location("_dirhash", ROOT / "src" / "protodirsig" / "dirhash.py")
dirhash = importlib.util.module_from_spec(_spec)             # by path: stdlib only, no package import
_spec.loader.exec_module(dirhash)
DIRS = {"dirfm": "dirsig-file-maker", "agent-docs": "agent-docs", "dirsig": "dirsig"}


def load_pins(path=None):
    return json.loads(Path(path or EXTERNAL / "pins.json").read_text())


def _git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def git_head(repo):
    rc, out, _ = _git(repo, "rev-parse", "HEAD")
    return out if rc == 0 else None


def git_dirty(repo):
    rc, out, _ = _git(repo, "status", "--porcelain")
    return rc == 0 and bool(out)


def find_dirsig(pin, environ=None):
    """The DIRSIG install directory named by the pin's search list, or None."""
    environ = os.environ if environ is None else environ
    for cand in pin["search"]:
        cand = cand.replace("{version}", pin["version"])
        if cand == "$DIRSIG_HOME":
            cand = environ.get("DIRSIG_HOME", "")
        if cand:
            p = Path(cand).expanduser()
            if p.is_dir() and (p / "bin" / "dirsig5").exists():
                return p
    return None


def status(pins, external=EXTERNAL, environ=None):
    """One line per dependency: (name, state, detail). state: ok, mismatch, dirty, missing."""
    rows = []
    for name, pin in pins.items():
        path = Path(external) / DIRS[name]
        if pin["kind"] == "git":
            if not path.exists():
                rows.append((name, "missing", f"run install; pin {pin['commit'][:10]}"))
                continue
            head = git_head(path)
            if head != pin["commit"]:
                rows.append((name, "mismatch", f"at {(head or 'not a git repo')[:10]}, pin {pin['commit'][:10]}"))
            elif git_dirty(path):
                rows.append((name, "dirty", "checkout has local changes; dirfm must stay unmodified"))
            else:
                rows.append((name, "ok", pin["commit"][:10]))
        else:
            if not path.exists():
                found = find_dirsig(pin, environ)
                rows.append((name, "missing", f"run install; found at {found}" if found else
                             f"expected {pin['version']} under $DIRSIG_HOME or ~/DIRSIG"))
                continue
            target = path.resolve()
            if not (target / "bin" / "dirsig5").exists():
                rows.append((name, "missing", f"{target} has no bin/dirsig5"))
            elif target.name != pin["version"]:
                rows.append((name, "mismatch", f"{target.name}, pin {pin['version']}"))
            else:
                rows.append((name, "ok", str(target)))
    return rows


def install(pins, links=None, external=EXTERNAL, environ=None):
    """Create what is missing. Returns a list of messages. Never touches an existing path."""
    links = links or {}
    external = Path(external)
    external.mkdir(exist_ok=True)
    msgs = []
    for name, pin in pins.items():
        path = external / DIRS[name]
        if path.exists() or path.is_symlink():
            msgs.append(f"{name}: present, left alone")
            continue
        if name in links:
            path.symlink_to(Path(links[name]).expanduser().resolve(), target_is_directory=True)
            msgs.append(f"{name}: linked to {links[name]}")
        elif pin["kind"] == "git":
            rc, _, err = _git(external, "clone", "--quiet", pin["url"], str(path))
            if rc != 0:
                msgs.append(f"{name}: clone failed: {err}")
                continue
            rc, _, err = _git(path, "checkout", "--quiet", pin["commit"])
            msgs.append(f"{name}: cloned at {pin['commit'][:10]}" if rc == 0 else f"{name}: checkout failed: {err}")
        else:
            found = find_dirsig(pin, environ)
            if found is None:
                msgs.append(f"{name}: not found; set DIRSIG_HOME or install {pin['version']} under ~/DIRSIG")
            else:
                path.symlink_to(found, target_is_directory=True)
                msgs.append(f"{name}: linked to {found}")
    return msgs


# --- library assets (assets/1) -------------------------------------------------------------------------------------

class AssetError(Exception):
    pass


def load_manifest(library=LIBRARY):
    path = Path(library) / "assets.json"
    if not path.is_file():
        return {"version": "assets/1", "assets": []}
    doc = json.loads(path.read_text())
    if doc.get("version") != "assets/1":
        raise AssetError(f"{path}: version is {doc.get('version')!r}, expected 'assets/1'")
    return doc


def _archive(entry, dirsig):
    src = entry["source"]
    if src.get("kind") != "zip":
        raise AssetError(f"{entry['path']}: source kind {src.get('kind')!r} is not supported (only 'zip')")
    return Path(src["archive"].replace("{dirsig}", str(dirsig)))


def _digest(path, kind):
    if kind == "directory":
        return dirhash.directory_digest(path)
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _safe_name(name):
    """A relative POSIX path that stays inside its target, with no name dirhash/1 forbids."""
    p = PurePosixPath(name)
    if name.startswith("/") or p.is_absolute() or ".." in p.parts or not p.parts:
        raise AssetError(f"member {name!r} escapes the target directory")
    if "\\" in name or "\n" in name:
        raise AssetError(f"member {name!r} has a backslash or a newline (dirhash/1 forbids them)")
    return p


def _members(entry, archive):
    """[(ZipInfo, relative target path)] the entry selects: a file's one member, or a directory's members under the
    prefix (all of them, or the `members` listed, relative to the prefix)."""
    src = entry["source"]
    prefix = src.get("prefix", "")
    infos = {i.filename: i for i in archive.infolist()}
    if entry["kind"] == "file":
        if prefix not in infos:
            raise AssetError(f"{entry['path']}: member {prefix!r} is not in {src['archive']}")
        chosen = [(infos[prefix], PurePosixPath(PurePosixPath(entry["path"]).name))]
    else:
        base = prefix.rstrip("/") + "/" if prefix else ""
        names = [base + m for m in src["members"]] if src.get("members") else \
            [n for n in infos if n.startswith(base) and not n.endswith("/")]
        missing = [n for n in names if n not in infos]
        if missing:
            raise AssetError(f"{entry['path']}: members not in {src['archive']}: {missing[:3]}")
        chosen = [(infos[n], _safe_name(n[len(base):])) for n in names]
    for info, rel in chosen:
        _safe_name(info.filename if entry["kind"] == "file" else str(rel))
        if stat.S_ISLNK(info.external_attr >> 16):
            raise AssetError(f"member {info.filename!r} is a symbolic link; library assets are real files")
        if info.is_dir():
            raise AssetError(f"member {info.filename!r} is a directory, not a file")
    return chosen


def asset_status(entry, library=LIBRARY, dirsig=EXTERNAL / "dirsig"):
    """`ok`, `missing`, `mismatch` or `no source` for one manifest entry, extracting nothing."""
    target = Path(library) / entry["path"]
    exists = target.is_dir() if entry["kind"] == "directory" else target.is_file()
    if exists:
        try:
            return "ok" if _digest(target, entry["kind"]) == entry["digest"] else "mismatch"
        except ValueError:
            return "mismatch"
    return "missing" if _archive(entry, dirsig).is_file() else "no source"


def materialize(entry, library=LIBRARY, dirsig=EXTERNAL / "dirsig"):
    """Extract one entry into place and verify it. Returns a message; raises AssetError on any refusal."""
    library = Path(library)
    target = library / entry["path"]
    _safe_name(entry["path"])
    archive_path = _archive(entry, dirsig)
    if not archive_path.is_file():
        raise AssetError(f"{entry['path']}: source {archive_path} not found (link the DIRSIG install as external/dirsig: "
                         "scripts/bootstrap.py install)")
    if asset_status(entry, library, dirsig) == "ok":
        return f"ok        {entry['path']}"
    with zipfile.ZipFile(archive_path) as archive:
        chosen = _members(entry, archive)
        staging = library / f".assets-tmp-{uuid.uuid4().hex}"
        try:
            root = staging / ("d" if entry["kind"] == "directory" else "")
            for info, rel in chosen:
                dest = root / rel
                if not dest.resolve().is_relative_to(root.resolve()):
                    raise AssetError(f"member {info.filename!r} escapes the target directory")
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
            staged = root if entry["kind"] == "directory" else root / chosen[0][1]
            got = _digest(staged, entry["kind"])
            if got != entry["digest"]:
                raise AssetError(f"{entry['path']}: digest {got} does not match the manifest's {entry['digest']}")
            placed = []
            files = [p for p in staged.rglob("*") if p.is_file()] if entry["kind"] == "directory" else [staged]
            for f in files:
                dest = target / f.relative_to(staged) if entry["kind"] == "directory" else target
                if dest.exists():
                    if dest.read_bytes() != f.read_bytes():
                        raise AssetError(f"{dest.relative_to(library)} exists and differs; not overwritten (move it "
                                         "aside to let bootstrap.py place the manifest's version)")
                    continue
                placed.append((f, dest))
            for f, dest in placed:
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.replace(f, dest)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    if asset_status(entry, library, dirsig) != "ok":
        raise AssetError(f"{entry['path']}: placed, but the target does not verify (extra files in the directory?)")
    return f"placed    {entry['path']}"


def assets(library=LIBRARY, dirsig=EXTERNAL / "dirsig", only=None, status_only=False, out=print):
    """The `assets` command. Returns the exit code: 0 when every selected entry is ok (or was placed)."""
    entries = [e for e in load_manifest(library)["assets"] if only is None or e["path"].startswith(only)]
    failed = 0
    for entry in entries:
        if status_only:
            state = asset_status(entry, library, dirsig)
            failed += state != "ok"
            out(f"{state:9s} {entry['path']}")
            continue
        try:
            out(materialize(entry, library, dirsig))
        except AssetError as e:
            failed += 1
            out(f"failed    {e}")
    return 1 if failed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["status", "install", "assets"])
    ap.add_argument("--link", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--only", default=None, metavar="PATH_PREFIX", help="assets: only entries under this path")
    ap.add_argument("--status", action="store_true", help="assets: classify each entry, extract nothing")
    a = ap.parse_args(argv)
    if a.command == "assets":
        try:
            return assets(only=a.only, status_only=a.status)
        except AssetError as e:
            print(f"failed    {e}")
            return 1
    pins = load_pins()
    if a.command == "install":
        links = dict(x.split("=", 1) for x in a.link)
        bad = set(links) - set(pins)
        if bad:
            ap.error(f"unknown dependency {sorted(bad)}; known: {sorted(pins)}")
        for m in install(pins, links):
            print(m)
    rows = status(pins)
    for name, state, detail in rows:
        print(f"{name:12s} {state:9s} {detail}")
    return 0 if all(s == "ok" for _, s, _ in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
