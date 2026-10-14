"""scripts/cold_start_check.py: its parsing and per-step rules on synthetic inputs (the whole check, which clones the
repository and installs into a new virtual environment, runs as a pre-commit `--check`, not in the suite)."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("cold_start_check", ROOT / "scripts" / "cold_start_check.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)


def test_the_conops_has_one_section_with_commands():
    found, count = cs.section((ROOT / cs.CONOPS).read_text())
    assert count == 1 and found[0].startswith("## ")
    cmds = cs.commands(found[1])
    assert any("bootstrap.py install" in c for c in cmds) and any("smoke_run.py --render" in c for c in cmds)


def test_commands_are_read_from_bash_blocks_only():
    body = "text `python x`\n\n```bash\n# a comment\npython scripts/a.py   # note\n\n```\n\n```\nnot bash\n```\n"
    assert cs.commands(body) == ["python scripts/a.py   # note"]


def test_command_rules(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "a.py").write_text("")
    (tmp_path / "packages" / "p").mkdir(parents=True)
    (tmp_path / "packages" / "p" / "pyproject.toml").write_text("")
    (tmp_path / "packages" / "q").mkdir()
    assert cs.check_command("python scripts/a.py --x", tmp_path)[0] == "ok"
    assert cs.check_command("python scripts/b.py", tmp_path)[0] == "FAIL"
    assert cs.check_command("pip install --no-deps -e packages/p", tmp_path)[0] == "ok"
    assert cs.check_command("pip install --no-deps -e packages/q", tmp_path)[0] == "FAIL"
    assert cs.check_command("pip install -e external/dirsig-file-maker", tmp_path)[0] == "not checked"
    assert cs.check_command("pip install pytest", tmp_path) == ("not checked", "needs the network (PyPI)")
    assert cs.check_command("conda env create -f environment.yml", tmp_path)[0] == "not checked"
    assert cs.check_command("export A=1 B=2", tmp_path)[0] == "ok"
    assert cs.check_command("export A", tmp_path)[0] == "FAIL"
    assert cs.check_command("python scripts/a.py 'unclosed", tmp_path)[0] == "FAIL"
    assert cs.check_command("/no/such/tool --x", tmp_path)[0] == "not checked"


def test_pin_rules(tmp_path):
    (tmp_path / "external").mkdir()
    (tmp_path / "snap.all").write_bytes(b"table")
    good = {"kind": "asset", "path": "external/assets/x", "library": "l/x", "url": "https://h/x",
            "sha256": hashlib.sha256(b"table").hexdigest(), "size": 5, "tracked": "snap.all"}
    pins = {"g": {"kind": "git", "url": "https://h/r.git", "commit": "a" * 40},
            "bad_git": {"kind": "git", "url": "https://h/r.git", "commit": "short"},
            "i": {"kind": "install", "version": "v", "search": ["$X"]},
            "a": good, "a_bad_copy": {**good, "size": 6}, "a_no_copy": {**good, "tracked": "gone.all"},
            "k": {"kind": "other"}}
    (tmp_path / "external" / "pins.json").write_text(json.dumps(pins))
    got = {d.split()[1]: r for r, d in cs.check_pins(tmp_path)}
    assert got == {"g": "ok", "bad_git:": "FAIL", "i": "ok", "a": "ok", "a_bad_copy:": "FAIL", "a_no_copy:": "FAIL",
                   "k:": "FAIL"}


def test_files_named_in_a_section(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "a.py").write_text("")
    (tmp_path / "manifold_config_repo").mkdir()
    (tmp_path / "manifold_config_repo" / "link").symlink_to("../nowhere")
    body = "`scripts/a.py`, `scripts/b.py`, `external/assets/x/`, `manifold_config_repo/link`, `manifold.core`, `~/x/y`"
    got = {d.split(": ")[-1].split()[0]: r for r, d in cs.check_files(body, tmp_path)}
    assert got == {"scripts/a.py": "ok", "scripts/b.py": "FAIL", "external/assets/x/": "not checked",
                   "manifold_config_repo/link": "not checked"}
