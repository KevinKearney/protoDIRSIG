"""The DIRSIG closure test (round 47 spike): compare a run tree's walked closure (`closure.walk`), the files the job
tree contains, and the files the engine opened while it ran, observed with `strace` rather than reasoned about.

Evidence, not the SDK's implementation (Cfg 4.2, A.5). This module is the pure part: it parses the traces and computes
the sets. `scripts/closure_trace.py` builds a job, runs `scene2hdf` and `dirsig5` under `strace` and calls it.

The trace is `strace -ff -y -s 4096 -e trace=open,openat,openat2 -o PREFIX`, one file per thread. `-y` prints the
folder a relative name was opened against (`AT_FDCWD</cwd>` or `<fd></dir>`) and the path the kernel opened
(`= 3</real/path>`, symbolic links resolved). `parse_trace(text, tool, cwd)` returns one `Open` per call: `named` is
the name as the tool passed it, made absolute against that folder and normalized lexically (a link keeps its name),
`real` the opened path (None when the call failed), `write` whether the flags ask for writing (`O_WRONLY`, `O_RDWR`,
`O_CREAT`, `O_TRUNC`), `error` the errno name of a failed call.

`closure_sets(walked, job, opens, places)`: `walked` is the walker's root-relative paths, `job` maps each regular file
the job tree holds before the engine starts (links followed, link names kept) to its real path, `places` names the
folders (`root`, `library`, `install`, `home`, `output`). An opened path is placed by its name first (under the root:
its root-relative name), then by its real path (under the root, or under the library: the tree path that resolves to
it, else `library:<path>`); a file under the installation, the home or the output folder is counted apart, and
anything else (system libraries, `/proc`) is dropped. Returns a dict:

- `listed_not_in_job`: walked paths the job does not contain (set 1).
- `in_job_not_listed`: job paths the walker did not list (set 2).
- `read_in_neither`: tree or library files the engine opened for reading that are neither walked nor in the job
  (set 3), and `generated`, the subset some tool of the same run opened for writing first (a compiled scene).
- `listed_not_read`: walked paths no tool opened.
- `read`: every tree or library file opened for reading, with the tools that opened it.
- `written`: tree files opened for writing (the run's own products in the tree); `library_written`: library files
  opened for writing (must be empty).
- `probed`: tree or library names a tool tried and did not find (`ENOENT`), the tool's search made visible.
- `install`, `home`, `output`: the installation, home and output-folder files opened for reading.
- `elsewhere`: files opened successfully anywhere else outside `SYSTEM` (the operating system's folders), reading
  or writing; the check that the filter dropped nothing but system files.
"""
import os
import re
from dataclasses import dataclass

_LINE = re.compile(r'^(?:\d+\s+)?(open|openat|openat2)\((.*)\)\s+=\s+(.*)$')
_ARGS = re.compile(r'^(?:(AT_FDCWD|-?\d+)(?:<((?:[^>\\]|\\.)*)>)?,\s*)?"((?:[^"\\]|\\.)*)"(?:\.\.\.)?,\s*([^,)]*)')
_RET = re.compile(r'^(-?\d+)(?:<(.*)>)?(?:\s+(E[A-Z0-9]+))?')
_WRITE_FLAGS = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC")
SYSTEM = ("/usr", "/lib", "/lib32", "/lib64", "/bin", "/sbin", "/etc", "/proc", "/sys", "/dev", "/run")


@dataclass(frozen=True)
class Open:
    tool: str
    named: str
    real: str | None
    write: bool
    error: str | None
    directory: bool


def _unescape(s):
    """strace's C-style string escapes (`\\"`, `\\\\`, `\\n`, octal, `\\x..`) decoded as bytes, then UTF-8 with
    surrogateescape so a name keeps its bytes."""
    if "\\" not in s:
        return s
    out, i = bytearray(), 0
    simple = {"n": 10, "t": 9, "r": 13, "v": 11, "f": 12, '"': 34, "\\": 92}
    while i < len(s):
        c = s[i]
        if c != "\\" or i + 1 == len(s):
            out += c.encode("utf-8", "surrogateescape")
            i += 1
            continue
        n = s[i + 1]
        if n in simple:
            out.append(simple[n])
            i += 2
        elif n == "x":
            out.append(int(s[i + 2:i + 4], 16))
            i += 4
        elif n.isdigit():
            j = i + 1
            while j < len(s) and j < i + 4 and s[j] in "01234567":
                j += 1
            out.append(int(s[i + 1:j], 8))
            i = j
        else:
            out += ("\\" + n).encode()
            i += 2
    return out.decode("utf-8", "surrogateescape")


def parse_trace(text, tool, cwd):
    """The `Open`s of one strace output. `cwd` is the folder the tool started in, used when a call shows no folder."""
    opens = []
    for line in text.splitlines():
        m = _LINE.match(line.strip())
        if not m:
            continue
        args, ret = _ARGS.match(m.group(2)), _RET.match(m.group(3))
        if not args or not ret:
            continue
        base = _unescape(args.group(2)) if args.group(2) else cwd
        name = _unescape(args.group(3))
        named = os.path.normpath(os.path.join(base, name))
        flags = args.group(4)
        ok = int(ret.group(1)) >= 0
        real = _unescape(ret.group(2)) if ok and ret.group(2) else (named if ok else None)
        opens.append(Open(tool, named, real, any(f in flags for f in _WRITE_FLAGS),
                          None if ok else (ret.group(3) or "error"), "O_DIRECTORY" in flags))
    return opens


def _under(path, folder):
    return folder is not None and (path == folder or path.startswith(folder.rstrip("/") + "/"))


def _place(path_named, path_real, places, real_to_tree):
    """`(kind, name)`: kind `tree` (name root-relative or `library:<path>`), `install`, `home`, `output` or None."""
    root, root_real = places["root"], os.path.realpath(places["root"])
    if _under(path_named, root):
        return "tree", os.path.relpath(path_named, root)
    real = path_real or path_named
    if _under(real, root_real):
        return "tree", os.path.relpath(real, root_real)
    lib = places.get("library") and os.path.realpath(places["library"])
    if lib and _under(real, lib):
        return "tree", real_to_tree.get(real) or "library:" + os.path.relpath(real, lib)
    for kind in ("install", "home", "output"):
        folder = places.get(kind) and os.path.realpath(places[kind])
        if folder and _under(real, folder):
            return kind, os.path.relpath(real, folder)
    return None, None


def closure_sets(walked, job, opens, places):
    """The three sets and the observations around them; see the module docstring."""
    walked, job_paths = set(walked), set(job)
    real_to_tree = {}
    for rel, real in sorted(job.items()):
        real_to_tree.setdefault(real, rel)
    read, written, library_written, probed, elsewhere = {}, {}, set(), {}, {}
    outside = {"install": {}, "home": {}, "output": {}}
    for o in opens:
        if o.directory:
            continue
        kind, name = _place(o.named, o.real, places, real_to_tree)
        if kind is None:
            path = o.real or o.named
            if o.error is None and not any(_under(path, d) for d in SYSTEM) and not os.path.isdir(path):
                elsewhere.setdefault(path, set()).add(o.tool)
            continue
        if o.error is not None:
            if kind == "tree" and o.error == "ENOENT":
                probed.setdefault(name, set()).add(o.tool)
            continue
        if o.real is not None and os.path.isdir(o.real):
            continue
        if kind != "tree":
            outside[kind].setdefault(name, set()).add(o.tool)
            continue
        if o.write:
            if name.startswith("library:"):
                library_written.add(name)
            written.setdefault(name, set()).add(o.tool)
            continue
        read.setdefault(name, set()).add(o.tool)
    neither = sorted(set(read) - walked - job_paths)
    return {
        "listed_not_in_job": sorted(walked - job_paths),
        "in_job_not_listed": sorted(job_paths - walked),
        "read_in_neither": neither,
        "generated": sorted(p for p in neither if p in written),
        "listed_not_read": sorted(walked - set(read)),
        "read": {p: sorted(t) for p, t in sorted(read.items())},
        "written": {p: sorted(t) for p, t in sorted(written.items())},
        "library_written": sorted(library_written),
        "probed": {p: sorted(t) for p, t in sorted(probed.items()) if p not in read},
        **{k: {p: sorted(t) for p, t in sorted(v.items())} for k, v in outside.items()},
        "elsewhere": {p: sorted(t) for p, t in sorted(elsewhere.items())},
    }


def job_files(root):
    """`{root-relative path: real path}` of every regular file under `root`, symbolic links to folders followed (the
    path keeps the link's name)."""
    out = {}
    for top, dirs, names in os.walk(root, followlinks=True):
        for name in names:
            p = os.path.join(top, name)
            if os.path.isfile(p):
                out[os.path.relpath(p, root)] = os.path.realpath(p)
    return dict(sorted(out.items()))
