#!/usr/bin/env python3
"""Populate external/ (dirfm, agent-docs, DIRSIG link) from external/pins.json.

    python scripts/bootstrap.py status
    python scripts/bootstrap.py install [--link NAME=PATH ...]

dirfm and agent-docs are cloned and checked out at the pinned commit, or symlinked from an existing
checkout with --link. The DIRSIG installation is never copied: it is linked from $DIRSIG_HOME or
~/DIRSIG/<version>. Nothing in a dirfm checkout is ever modified. Standard library only.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "external"
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["status", "install"])
    ap.add_argument("--link", action="append", default=[], metavar="NAME=PATH")
    a = ap.parse_args(argv)
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
