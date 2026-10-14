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
`packages/core/src/manifold/core/dirhash.py` is loaded by file path.

`assets` also covers the pinned data assets of `external/pins.json` (`kind: asset`: a file under `external/assets/`,
its sha256, size and source URL; SatSim's ephemeris and IERS snapshot), which the engine-asset library sees through a
link. `--status` verifies each (ok, missing, mismatch) and fetches nothing; without `--status` a missing one is fetched
from its URL into a temporary file, kept only when its size and sha256 match the pin, and made read-only; a mismatching
file is reported, never replaced. A pin with a `tracked` member (the IERS snapshot, which cannot be re-fetched) is
restored from that committed copy under `external/snapshots/` instead, offline, after the same check. Nothing is fetched
unless the user runs the command.
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
_spec = importlib.util.spec_from_file_location("_dirhash", ROOT / "packages" / "core" / "src" / "manifold" / "core" / "dirhash.py")
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

def dirsig_executable(path):
    """Return the DIRSIG executable for this platform, if present."""
    names = ("dirsig5.exe", "dirsig5") if os.name == "nt" else ("dirsig5",)
    for name in names:
        candidate = Path(path) / "bin" / name
        if candidate.is_file():
            return candidate
    return None

def dirsig_version(path):
    """Return the version string reported by the DIRSIG executable."""
    executable = dirsig_executable(path)
    if executable is None:
        return None

    try:
        result = subprocess.run(
            [str(executable), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    return (result.stdout or result.stderr).strip()

def find_dirsig(pin, environ=None):
    """The DIRSIG install directory named by the pin's search list, or None."""
    environ = os.environ if environ is None else environ
    for cand in pin["search"]:
        cand = cand.replace("{version}", pin["version"])
        if cand == "$DIRSIG_HOME":
            cand = environ.get("DIRSIG_HOME", "")
        if cand:
            p = Path(cand).expanduser()
            if p.is_dir() and dirsig_executable(p):
                return p
    return None


def status(pins, external=EXTERNAL, environ=None):
    """One line per dependency: (name, state, detail). state: ok, mismatch, dirty, missing."""
    rows = []
    for name, pin in pins.items():
        if pin["kind"] == "asset":                       # data assets: `assets` verifies and fetches them
            continue
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
            if not dirsig_executable(target):
                rows.append((name, "missing", f"{target} has no bin/dirsig5"))
            elif not dirsig_version(target):
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
        if pin["kind"] == "asset":
            continue
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


def pinned_status(pin, root=ROOT):
    """`ok`, `missing` or `mismatch` for a pinned data asset (`kind: asset` in pins.json); reads, never fetches."""
    path = Path(root) / pin["path"]
    if not path.is_file():
        return "missing"
    ok = path.stat().st_size == pin["size"] and hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]
    return "ok" if ok else "mismatch"


def fetch_pinned(pin, root=ROOT, opener=None):
    """Fetch a missing pinned asset from its URL and keep it only if size and sha256 match. Returns a message;
    raises AssetError on a refusal (the downloaded bytes are discarded). A pin with a `tracked` member (the
    repository-relative path of a committed copy) is restored from that copy instead, offline, under the same check."""
    import urllib.request
    path = Path(root) / pin["path"]
    state = pinned_status(pin, root)
    if state == "ok":
        return f"ok        {pin['path']}"
    if state == "mismatch":
        raise AssetError(f"{pin['path']} exists and does not match its pin; not replaced (move it aside to fetch)")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.part")
    tracked = pin.get("tracked")
    try:
        if tracked:                                      # a committed copy: restored offline, never fetched
            shutil.copyfile(Path(root) / tracked, tmp)
            if hashlib.sha256(tmp.read_bytes()).hexdigest() != pin["sha256"] or tmp.stat().st_size != pin["size"]:
                raise AssetError(f"{pin['path']}: the tracked copy {tracked} does not match the pin; not restored")
            tmp.chmod(0o444)
            os.replace(tmp, path)
            return f"restored  {pin['path']} (from {tracked})"
        with (opener or urllib.request.urlopen)(pin["url"]) as src, open(tmp, "wb") as out:
            shutil.copyfileobj(src, out)
        got = hashlib.sha256(tmp.read_bytes()).hexdigest()
        if got != pin["sha256"] or tmp.stat().st_size != pin["size"]:
            raise AssetError(f"{pin['path']}: {pin['url']} served {tmp.stat().st_size} bytes with sha256 {got[:16]}..., "
                             f"not the pinned {pin['size']} bytes {pin['sha256'][:16]}...; discarded"
                             + (f" (a snapshot taken {pin['snapshot']}: the URL now serves a newer table)"
                                if pin.get("snapshot") else ""))
        tmp.chmod(0o444)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return f"fetched   {pin['path']}"


def pinned_assets(pins_path=None):
    return {n: p for n, p in load_pins(pins_path).items() if p.get("kind") == "asset"}


def assets(library=LIBRARY, dirsig=EXTERNAL / "dirsig", only=None, status_only=False, out=print, pins_path=None,
           root=ROOT, opener=None):
    """The `assets` command. Returns the exit code: 0 when every selected entry is ok (or was placed). The pinned data
    assets are included for the repository's own library, or when `pins_path` names a pins file."""
    entries = [e for e in load_manifest(library)["assets"] if only is None or e["path"].startswith(only)]
    failed = 0
    pinned = pinned_assets(pins_path) if pins_path is not None or Path(library) == LIBRARY else {}
    for name, pin in pinned.items():
        if only is not None and not pin["library"].startswith(only):
            continue
        if status_only:
            state = pinned_status(pin, root)
            failed += state != "ok"
            out(f"{state:9s} {pin['path']} ({name})")
            continue
        try:
            out(fetch_pinned(pin, root, opener))
        except (AssetError, OSError) as e:
            failed += 1
            out(f"failed    {e}")
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
