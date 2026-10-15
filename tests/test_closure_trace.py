"""The closure test's pure part (round 47 A): `closure_trace.parse_trace` reads strace's `-y` output, and
`closure_trace.closure_sets` computes the three sets (walked but not in the job, in the job but not walked, opened but
in neither) and the files walked but never opened. `scripts/closure_trace.py` runs the engine under strace."""
import os
import shutil
import subprocess

import pytest

from manifold.engines.dirsig.closure_trace import Open, closure_sets, job_files, parse_trace

TRACE = r'''openat(AT_FDCWD</w/input>, "example.jsim", O_RDONLY) = 3</w/input/example.jsim>
openat(AT_FDCWD</w/input>, "auror_ref/geometry/a.glist", O_RDONLY|O_CLOEXEC) = 4</lib/scenes/s/geometry/a.glist>
openat(AT_FDCWD</w/input>, "missing.ems", O_RDONLY) = -1 ENOENT (No such file or directory)
openat(5</w/input/auror_ref>, "s.scene.hdf", O_RDWR|O_CREAT|O_TRUNC, 0644) = 6</w/input/auror_ref/s.scene.hdf>
openat(AT_FDCWD</w/input>, "/opt/dirsig/lib/data/weather/mls.wth", O_RDONLY) = 7</opt/dirsig/lib/data/weather/mls.wth>
openat(AT_FDCWD</w/input>, "caf\303\251 \"q\".txt", O_RDONLY) = 8</w/input/caf\303\251 "q".txt>
openat(AT_FDCWD</w/input>, "auror_ref", O_RDONLY|O_DIRECTORY) = 9</w/input/auror_ref>
open("rel.txt", O_RDONLY) = 10</w/input/rel.txt>
--- SIGCHLD {si_signo=SIGCHLD} ---
+++ exited with 0 +++
'''


def test_parse_trace_reads_names_folders_results_and_flags():
    opens = parse_trace(TRACE, "dirsig5", "/w/input")
    assert len(opens) == 8
    jsim, glist, missing, hdf, wth, cafe, folder, rel = opens
    assert (jsim.named, jsim.real, jsim.write, jsim.error) == ("/w/input/example.jsim", "/w/input/example.jsim",
                                                               False, None)
    assert glist.named == "/w/input/auror_ref/geometry/a.glist" and glist.real == "/lib/scenes/s/geometry/a.glist"
    assert missing.real is None and missing.error == "ENOENT"
    assert hdf.named == "/w/input/auror_ref/s.scene.hdf" and hdf.write          # a dirfd folder, write flags
    assert wth.named == "/opt/dirsig/lib/data/weather/mls.wth"
    assert cafe.named == '/w/input/café "q".txt'                                   # octal bytes and quotes decoded
    assert folder.directory and not jsim.directory
    assert rel.named == "/w/input/rel.txt"                                         # open(): the start folder


def _tree(tmp_path):
    """A job root with one file, a link into a library folder of two files, and an installation."""
    root, lib, inst = tmp_path / "w" / "input", tmp_path / "lib", tmp_path / "inst"
    (lib / "geometry").mkdir(parents=True)
    (lib / "geometry" / "a.glist").write_text("a")
    (lib / "geometry" / "b.obj").write_text("b")
    root.mkdir(parents=True)
    (root / "example.jsim").write_text("{}")
    (root / "extra.txt").write_text("x")
    (root / "auror_ref").mkdir()
    (root / "auror_ref" / "geometry").symlink_to(lib / "geometry")
    (inst / "lib").mkdir(parents=True)
    (inst / "lib" / "mls.wth").write_text("w")
    return root, lib, inst


def _open(tool, named, real=None, write=False, error=None):
    return Open(tool, str(named), None if error else str(real or named), write, error, False)


def test_closure_sets(tmp_path):
    root, lib, inst = _tree(tmp_path)
    job = job_files(root)
    assert sorted(job) == ["auror_ref/geometry/a.glist", "auror_ref/geometry/b.obj", "example.jsim", "extra.txt"]
    walked = ["example.jsim", "auror_ref/geometry/a.glist", "not_there.ems"]
    (root / "auror_ref" / "s.scene.hdf").write_text("h")                      # written during the run
    opens = [
        _open("dirsig5", root / "example.jsim"),
        _open("scene2hdf", lib / "geometry" / "a.glist"),                       # by its real path: mapped back
        _open("scene2hdf", root / "auror_ref" / "s.scene.hdf", write=True),
        _open("dirsig5", root / "auror_ref" / "s.scene.hdf"),
        _open("dirsig5", root / "undeclared.dat", error="ENOENT"),
        _open("dirsig5", inst / "lib" / "mls.wth"),
        _open("dirsig5", "/usr/lib/libc.so.6"),                                 # a system file: dropped
        _open("dirsig5", tmp_path / "stray.cfg"),                               # anywhere else: reported
    ]
    (tmp_path / "stray.cfg").write_text("s")
    (root / "late.cfg").write_text("c")                                       # not in the job before the run
    opens.append(_open("dirsig5", root / "late.cfg"))
    s = closure_sets(walked, job, opens, {"root": str(root), "library": str(lib), "install": str(inst),
                                          "home": str(tmp_path / "home"), "output": str(tmp_path / "w" / "out")})
    assert s["listed_not_in_job"] == ["not_there.ems"]
    assert s["in_job_not_listed"] == ["auror_ref/geometry/b.obj", "extra.txt"]
    assert s["read_in_neither"] == ["auror_ref/s.scene.hdf", "late.cfg"]
    assert s["generated"] == ["auror_ref/s.scene.hdf"]
    assert s["listed_not_read"] == ["not_there.ems"]
    assert s["read"]["auror_ref/geometry/a.glist"] == ["scene2hdf"]
    assert s["written"] == {"auror_ref/s.scene.hdf": ["scene2hdf"]} and s["library_written"] == []
    assert s["probed"] == {"undeclared.dat": ["dirsig5"]}
    assert s["install"] == {"lib/mls.wth": ["dirsig5"]}
    assert s["elsewhere"] == {str(tmp_path / "stray.cfg"): ["dirsig5"]}


def test_a_library_file_no_tree_path_reaches_is_named_as_library(tmp_path):
    root, lib, inst = _tree(tmp_path)
    (lib / "other.mat").write_text("m")
    s = closure_sets([], job_files(root), [_open("scene2hdf", lib / "other.mat"),
                                           _open("scene2hdf", lib / "other.mat", write=True)],
                     {"root": str(root), "library": str(lib)})
    assert s["read_in_neither"] == ["library:other.mat"]
    assert s["library_written"] == ["library:other.mat"]


@pytest.mark.skipif(shutil.which("strace") is None, reason="strace not installed")
def test_parse_trace_on_real_strace_output(tmp_path):
    root, lib, inst = _tree(tmp_path)
    log = tmp_path / "trace"
    proc = subprocess.run(["strace", "-ff", "-y", "-s", "4096", "-qq", "-e", "trace=open,openat,openat2",
                           "-o", str(log), "sh", "-c", "cat auror_ref/geometry/a.glist; : < nope"], cwd=root,
                          capture_output=True)
    if b"Operation not permitted" in proc.stderr:
        pytest.skip("ptrace not permitted on this host")
    opens = [o for f in tmp_path.glob("trace.*") for o in parse_trace(f.read_text(), "cat", str(root))]
    s = closure_sets(["auror_ref/geometry/a.glist"], job_files(root), opens, {"root": str(root),
                                                                             "library": str(lib)})
    assert s["read"] == {"auror_ref/geometry/a.glist": ["cat"]}
    assert s["probed"] == {"nope": ["cat"]}
    assert os.path.realpath(root / "auror_ref/geometry/a.glist") == str(lib / "geometry" / "a.glist")
