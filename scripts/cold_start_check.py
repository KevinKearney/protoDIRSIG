#!/usr/bin/env python3
"""Cold-start check: the CONOPS "Reproduce from zero" section, followed offline in a fresh copy of the repository.

    python scripts/cold_start_check.py            # print every step's result
    python scripts/cold_start_check.py --check    # also exit 1 if any step fails
    python scripts/cold_start_check.py --keep     # keep the temporary copy and print its path

The copy is made outside the repository, in a new temporary directory: `git clone` of the repository, then every file
the working tree would commit (`git ls-files --cached --others --exclude-standard`) copied over it and every deleted
tracked file removed, so uncommitted edits are checked before they are committed. Ignored files (`external/`,
`outputs/`, materialized assets) are not copied: the copy is what a reviewer gets from a clone.

Each result is `ok`, `FAIL` or `not checked: needs <what>`; a step that needs the network, RIT's GitLab, conda's solver,
the DIRSIG install, the SatSim environment or populated assets is reported as not checked, never passed. Steps:

1. section: the CONOPS has one "Reproduce from zero" section and the contents list it;
2. commands: every line of the section's `bash` blocks parses (`shlex`); `python scripts/<x>.py` names a script in
   the copy; `pip install ... -e <dir>` names a directory of the copy holding a `pyproject.toml` (a directory under
   `external/` is filled by `bootstrap.py install` from the network: not checked); any other executable is found on
   `PATH` or, for a path, exists; `export NAME=value` assigns;
3. files: every backticked repository path in the section exists in the copy (a path under a gitignored directory is
   reported as not checked, with what fills it);
4. pins: every entry of `external/pins.json` is well formed for its kind (`git`: url and a 40-hex commit; `install`:
   version and search list; `asset`: path under `external/`, library path, 64-hex sha256, size, url, and, if present,
   a `tracked` copy that exists in the copy with that size and sha256);
5. bootstrap status: `python scripts/bootstrap.py status` runs in the copy and reports every non-asset pin;
6. the SatSim asset link `manifold_config_repo/satsim/assets` resolves (in a clone it dangles until
   `bootstrap.py assets` populates `external/assets/satsim/`: not checked);
7. bootstrap assets offline: `bootstrap.py assets --only satsim/` in the copy restores the tracked IERS snapshot
   without the network; the ephemeris needs the network (not checked);
8. install: a new virtual environment with `--system-site-packages` installs `packages/core` and `packages/sim` from
   the copy (`pip install --no-index --no-deps --no-build-isolation`, not editable) and imports `manifold.core` and
   `manifold.sim` from that environment, not from the repository's editable installs.
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONOPS = "docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md"
HEADING = re.compile(r"^(#+) (?:\d+\. )?Reproduce from zero\b")
IGNORED = {"external/": "`bootstrap.py install` or `assets` (network)", "outputs/": "a run",
           "manifold_config_repo/demos/": "`bootstrap.py assets` (the DIRSIG install)",
           "manifold_config_repo/demo_dirs/": "`bootstrap.py assets` (the DIRSIG install)"}
NEEDS = {"conda": "conda's solver and the network", "git": "the network", "dirsig5": "the DIRSIG install",
         "scene2hdf": "the DIRSIG install"}


def fresh_copy(dest, repo=ROOT):
    """Clone repo into dest and lay the working tree's committable files over it."""
    subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(repo), str(dest)], check=True)
    out = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                         check=True, capture_output=True).stdout.decode()
    for name in filter(None, out.split("\0")):
        src, dst = repo / name, dest / name
        if src.is_symlink():
            if dst.is_symlink() or dst.exists():
                dst.unlink()
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(os.readlink(src))
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            shutil.copymode(src, dst)
        elif dst.exists() or dst.is_symlink():
            dst.unlink()                                  # deleted in the working tree
    return dest


def section(text):
    """(heading line, body) of the one "Reproduce from zero" section, or None; and how many there are."""
    lines = text.splitlines()
    heads = [(i, len(m.group(1))) for i, l in enumerate(lines) if (m := HEADING.match(l))]
    if not heads:
        return None, 0
    i, level = heads[0]
    end = next((j for j in range(i + 1, len(lines)) if re.match(r"#{1,%d} " % level, lines[j])), len(lines))
    return (lines[i], "\n".join(lines[i + 1:end])), len(heads)


def commands(body):
    """Each command line of the section's bash blocks, comments stripped."""
    out, inside = [], False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            inside = line.strip() == "```bash" if not inside else False
            continue
        if inside and line.strip() and not line.strip().startswith("#"):
            out.append(line)
    return out


def ignored(path):
    return next((need for prefix, need in IGNORED.items() if path.startswith(prefix)), None)


def check_command(line, copy):
    """(result, detail) for one command line."""
    try:
        words = shlex.split(line, comments=True)
    except ValueError as e:
        return "FAIL", f"does not parse: {e}"
    if not words:
        return "ok", "comment"
    exe, args = words[0], words[1:]
    if exe == "export":
        return ("ok", "assignment") if all(re.match(r"[A-Za-z_]\w*=", a) for a in args) else ("FAIL", "export without NAME=value")
    if exe == "cd":
        return "ok", "directory change"
    if exe in ("python", "python3") and args and args[0].startswith("scripts/"):
        return ("ok", f"{args[0]} exists") if (copy / args[0]).is_file() else ("FAIL", f"{args[0]} missing")
    if exe in ("python", "python3"):
        return "ok", "python"
    if exe == "pip" or exe.endswith("/pip"):
        if "-e" in args:
            target = args[args.index("-e") + 1]
            if ignored(target) and not (copy / target).exists():
                return "not checked", f"needs {ignored(target)}: {target}"
            d = copy / target
            return ("ok", f"{target} has pyproject.toml") if (d / "pyproject.toml").is_file() else ("FAIL", f"{target}: no pyproject.toml")
        if exe != "pip":
            return "not checked", f"needs the SatSim environment ({exe}) and the network"
        return "not checked", "needs the network (PyPI)"
    if exe == "conda" and args[:1] == ["activate"]:
        return "not checked", "needs the environment `conda env create` makes"
    if exe in NEEDS:
        return "not checked", f"needs {NEEDS[exe]}" + (" (on PATH)" if shutil.which(exe) else f" ({exe} not on PATH)")
    if "/" in exe:
        p = Path(os.path.expanduser(exe))
        return ("ok", f"{exe} exists") if p.exists() else ("not checked", f"needs {exe}")
    return ("ok", f"{exe} on PATH") if shutil.which(exe) else ("not checked", f"needs {exe} on PATH")


def check_files(body, copy):
    results = []
    for token in sorted(set(re.findall(r"`([^`\s]+)`", body))):
        token = token.rstrip(".,;:")
        if "/" not in token or token.startswith(("~", "/", "$", "http", "<")) or "<" in token or "*" in token:
            continue
        if not re.match(r"^[\w.-]+(/[\w.-]+)*/?$", token):
            continue
        top = token.split("/")[0]
        if not (copy / top).exists() and not ignored(token):
            continue                                      # not a repository path (a package path, a schema id)
        if (copy / token).is_symlink() and not (copy / token).exists():
            results.append(("not checked", f"needs assets populated: {token} is a link that dangles in a clone"))
        elif (copy / token).exists():
            results.append(("ok", f"{token} exists"))
        elif ignored(token):
            results.append(("not checked", f"needs {ignored(token)}: {token}"))
        else:
            results.append(("FAIL", f"{token} named in the section does not exist"))
    return results


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_pins(copy):
    results = []
    try:
        pins = json.loads((copy / "external" / "pins.json").read_text())
    except (OSError, ValueError) as e:
        return [("FAIL", f"external/pins.json: {e}")]
    for name, pin in pins.items():
        kind = pin.get("kind")
        bad = []
        if kind == "git":
            bad += [] if re.fullmatch(r"https://\S+\.git", pin.get("url", "")) else ["url"]
            bad += [] if re.fullmatch(r"[0-9a-f]{40}", pin.get("commit", "")) else ["commit"]
        elif kind == "install":
            bad += [] if pin.get("version") else ["version"]
            bad += [] if isinstance(pin.get("search"), list) and pin["search"] else ["search"]
        elif kind == "asset":
            bad += [] if str(pin.get("path", "")).startswith("external/assets/") else ["path"]
            bad += [] if pin.get("library") else ["library"]
            bad += [] if re.fullmatch(r"[0-9a-f]{64}", pin.get("sha256", "")) else ["sha256"]
            bad += [] if isinstance(pin.get("size"), int) and pin["size"] > 0 else ["size"]
            bad += [] if str(pin.get("url", "")).startswith("https://") else ["url"]
            if "tracked" in pin:
                t = copy / pin["tracked"]
                if not t.is_file():
                    bad.append(f"tracked copy {pin['tracked']} missing")
                elif t.stat().st_size != pin.get("size") or sha256(t) != pin.get("sha256"):
                    bad.append(f"tracked copy {pin['tracked']} differs from the pin")
        else:
            bad.append(f"kind {kind!r}")
        results.append(("FAIL", f"pin {name}: {', '.join(bad)}") if bad else ("ok", f"pin {name} ({kind})"))
    return results


def run_py(copy, *args, env=None, timeout=300):
    return subprocess.run([sys.executable, *args], cwd=copy, capture_output=True, text=True, timeout=timeout, env=env)


def check_bootstrap(copy):
    p = run_py(copy, "scripts/bootstrap.py", "status")
    pins = json.loads((copy / "external" / "pins.json").read_text())
    names = [n for n, pin in pins.items() if pin.get("kind") != "asset"]
    rows = {line.split()[0]: line.split()[1] for line in p.stdout.splitlines() if line.split()}
    if p.returncode not in (0, 1) or set(names) - set(rows):
        return [("FAIL", f"bootstrap.py status exit {p.returncode}: {p.stdout[-300:]}{p.stderr[-300:]}")]
    out = [("ok", "bootstrap.py status runs and reports every pin")]
    for n in names:
        if rows[n] != "ok":
            need = "the DIRSIG install" if pins[n].get("kind") == "install" else f"the network ({pins[n].get('url', '')})"
            out.append(("not checked", f"needs {need}, through `bootstrap.py install`: {n} is {rows[n]}"))
    return out


def check_assets(copy):
    link = copy / "manifold_config_repo" / "satsim" / "assets"
    out = []
    if not link.is_symlink():
        return [("FAIL", "manifold_config_repo/satsim/assets is not a link")]
    if not link.exists():
        out.append(("not checked", "needs assets populated: manifold_config_repo/satsim/assets dangles in a clone"))
    pins = json.loads((copy / "external" / "pins.json").read_text())
    tracked = {n: p for n, p in pins.items() if p.get("kind") == "asset" and "tracked" in p}
    if tracked:
        env = dict(os.environ)
        p = subprocess.run([sys.executable, "-c", "import sys, urllib.request\n"
                            "def refuse(*a, **k): raise OSError('network refused by cold_start_check')\n"
                            "urllib.request.urlopen = refuse\n"
                            "sys.argv = ['bootstrap.py', 'assets', '--only', 'satsim/']\n"
                            "sys.path.insert(0, 'scripts'); import bootstrap; sys.exit(bootstrap.main(sys.argv[1:]))"],
                           cwd=copy, capture_output=True, text=True, timeout=300, env=env)
        for n, pin in tracked.items():
            dest = copy / pin["path"]
            ok = dest.is_file() and sha256(dest) == pin["sha256"]
            out.append(("ok", f"{pin['path']} restored offline from {pin['tracked']}") if ok else
                       ("FAIL", f"{pin['path']} not restored from {pin['tracked']}: {p.stdout[-400:]}{p.stderr[-400:]}"))
        for n, pin in pins.items():
            if pin.get("kind") == "asset" and "tracked" not in pin:
                out.append(("not checked", f"needs the network: {pin['path']} from {pin['url']}"))
    return out


def check_install(copy, work):
    venv = work / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", "--without-pip", str(venv)], check=True)
    py = venv / "bin" / "python"
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env["PIP_NO_INDEX"] = "1"
    results = []
    for pkg in ("packages/core", "packages/sim"):
        p = subprocess.run([str(py), "-m", "pip", "install", "--quiet", "--no-index", "--no-deps", "--no-build-isolation",
                            str(copy / pkg)], cwd=work, capture_output=True, text=True, timeout=600, env=env)
        results.append(("ok", f"{pkg} installed from the copy") if p.returncode == 0 else
                       ("FAIL", f"{pkg}: pip exit {p.returncode}: {p.stderr[-400:]}"))
    if any(r == "FAIL" for r, _ in results):
        return results
    p = subprocess.run([str(py), "-c", "import manifold.core.identity, manifold.sim.workspace, sys\n"
                        "print(manifold.core.identity.__file__); print(manifold.sim.workspace.__file__)"],
                       cwd=work, capture_output=True, text=True, timeout=120, env=env)
    files = p.stdout.split()
    if p.returncode != 0 or len(files) != 2:
        return results + [("FAIL", f"import failed: {p.stderr[-400:]}")]
    for f in files:
        inside = Path(f).resolve().is_relative_to(venv.resolve())
        results.append(("ok", f"imported from the new environment: {Path(f).relative_to(venv)}") if inside else
                       ("FAIL", f"imported from outside the new environment: {f}"))
    return results


def run(keep=False, out=print):
    work = Path(tempfile.mkdtemp(prefix="manifold-cold-start-"))
    results = []
    try:
        copy = fresh_copy(work / "clone")
        text = (copy / CONOPS).read_text()
        found, count = section(text)
        if not found:
            return [("FAIL", "no 'Reproduce from zero' section in the CONOPS")]
        heading, body = found
        results.append(("ok", f"one section: {heading}") if count == 1 else ("FAIL", f"{count} 'Reproduce from zero' sections"))
        title = re.sub(r"^#+ (?:\d+\. )?", "", heading)
        contents = text.split("\n## ", 1)[0]
        results.append(("ok", "listed in the contents") if title in contents else ("FAIL", f"'{title}' not in the contents"))
        cmds = commands(body)
        results.append(("ok", f"{len(cmds)} command lines") if cmds else ("FAIL", "no bash command lines"))
        results += [(r, f"`{c.split(' #')[0].strip()[:72]}`: {d}") for c in cmds for r, d in [check_command(c, copy)]]
        results += check_files(body, copy)
        results += check_pins(copy)
        results += check_bootstrap(copy)
        results += check_assets(copy)
        results += check_install(copy, work)
    finally:
        if keep:
            out(f"copy kept at {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if any step fails")
    ap.add_argument("--keep", action="store_true", help="keep the temporary copy")
    args = ap.parse_args(argv)
    results = run(keep=args.keep)
    for r, d in results:
        print(f"not checked: {d}" if r == "not checked" else f"{r:4s} {d}")
    fails = sum(r == "FAIL" for r, _ in results)
    skipped = sum(r == "not checked" for r, _ in results)
    print(f"cold_start_check: {len(results)} results, {fails} failed, {skipped} not checked", file=sys.stderr)
    return 1 if args.check and fails else 0


if __name__ == "__main__":
    sys.exit(main())
