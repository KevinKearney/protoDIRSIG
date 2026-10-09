"""scripts/bootstrap.py: pin checking and install, against throwaway git repos and a fake DIRSIG tree.
Writes only to pytest's tmp_path."""
import importlib.util
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap.py"
spec = importlib.util.spec_from_file_location("bootstrap", SCRIPT)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def make_repo(path):
    path.mkdir()
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(path), *args], check=True)
    (path / "f.txt").write_text("x")
    subprocess.run(["git", "-C", str(path), "add", "f.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "c"], check=True)
    return bootstrap.git_head(path)


def fake_pins(tmp_path):
    src = tmp_path / "src_repo"
    sha = make_repo(src)
    dirsig = tmp_path / "DIRSIG" / "dirsig-test"
    (dirsig / "bin").mkdir(parents=True)
    (dirsig / "bin" / "dirsig5").write_text("")
    pins = {
        "dirfm": {"kind": "git", "url": str(src), "commit": sha},
        "dirsig": {"kind": "install", "version": "dirsig-test", "search": [str(tmp_path / "DIRSIG" / "{version}")]},
    }
    return pins, sha, src


def test_status_missing_then_install_then_ok(tmp_path):
    pins, sha, _ = fake_pins(tmp_path)
    ext = tmp_path / "external"
    ext.mkdir()
    assert {n: s for n, s, _ in bootstrap.status(pins, ext)} == {"dirfm": "missing", "dirsig": "missing"}
    msgs = bootstrap.install(pins, external=ext)
    assert any("cloned" in m for m in msgs) and any("linked" in m for m in msgs)
    assert {n: s for n, s, _ in bootstrap.status(pins, ext)} == {"dirfm": "ok", "dirsig": "ok"}


def test_install_leaves_existing_alone_and_reports_dirty_and_mismatch(tmp_path):
    pins, sha, src = fake_pins(tmp_path)
    ext = tmp_path / "external"
    bootstrap.install(pins, links={"dirfm": str(src)}, external=ext)
    assert (ext / "dirsig-file-maker").is_symlink()
    assert "left alone" in " ".join(bootstrap.install(pins, external=ext))
    (src / "f.txt").write_text("changed")
    assert [s for n, s, _ in bootstrap.status(pins, ext) if n == "dirfm"] == ["dirty"]
    pins["dirfm"]["commit"] = "0" * 40
    assert [s for n, s, _ in bootstrap.status(pins, ext) if n == "dirfm"] == ["mismatch"]


def test_real_pins_file_parses():
    pins = bootstrap.load_pins()
    assert set(pins) == {"dirfm", "agent-docs", "dirsig"} and len(pins["dirfm"]["commit"]) == 40
