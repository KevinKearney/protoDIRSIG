"""The manifold naming conventions: `MANIFOLD_*` environment variables with the legacy `PROTODIRSIG_*` read as a
deprecated fallback, `urn:manifold:problem:*` problem types, schema `$id`s free of the repository name, and the
`manifold` state directory, with the pre-rename default work root named once and never moved."""
import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest

from manifold.core import _names, errors
from manifold.sim.workspace import Workspace, default_work_root, legacy_work_root, move_command

ROOT = Path(__file__).resolve().parents[1]

ENV_CHECK = """
import json, os, sys, warnings
warnings.simplefilter("always")
from manifold.core import _names
os.environ.update(json.loads(sys.argv[1]))
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    values = [_names.getenv("X_ONE"), _names.getenv("X_ONE"), _names.getenv("X_TWO"), _names.getenv("X_NONE", "dflt")]
print(json.dumps({"values": values, "warnings": [(c.category.__name__, str(c.message)) for c in w]}))
"""


def _env_run(env):
    out = subprocess.run([sys.executable, "-c", ENV_CHECK, json.dumps(env)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_the_new_variable_wins_and_the_legacy_one_warns_once_per_variable():
    got = _env_run({"MANIFOLD_X_ONE": "new", "PROTODIRSIG_X_ONE": "old", "PROTODIRSIG_X_TWO": "legacy"})
    assert got["values"] == ["new", "new", "legacy", "dflt"]
    assert got["warnings"] == [["DeprecationWarning", "PROTODIRSIG_X_TWO is deprecated; set MANIFOLD_X_TWO instead"]]
    got = _env_run({"PROTODIRSIG_X_ONE": "old"})                       # read twice in one process: one warning
    assert got["values"][:2] == ["old", "old"] and len(got["warnings"]) == 1


def test_the_contracts_folder_falls_back_to_the_legacy_variable(monkeypatch, tmp_path):
    from manifold.core import contract
    monkeypatch.delenv("MANIFOLD_CONTRACTS", raising=False)
    monkeypatch.setenv("PROTODIRSIG_CONTRACTS", str(tmp_path))
    monkeypatch.setattr(_names, "_WARNED", set())
    with pytest.warns(DeprecationWarning, match="PROTODIRSIG_CONTRACTS"):
        assert contract.contracts_dir() == tmp_path
    monkeypatch.setenv("MANIFOLD_CONTRACTS", str(tmp_path / "new"))
    assert contract.contracts_dir() == tmp_path / "new"


def test_problem_types_are_manifold_urns():
    kinds = {"compose": errors.COMPOSE, "admission": errors.ADMISSION, "not-found": errors.NOT_FOUND,
             "invalid-request": errors.INVALID_REQUEST, "execution": errors.EXECUTION}
    assert kinds == {k: f"urn:manifold:problem:{k}" for k in kinds}
    schema = (ROOT / "api" / "schemas" / "problem.schema.json").read_text()
    assert all(u in schema for u in kinds.values()) and "urn:protodirsig" not in schema


def test_no_schema_id_names_the_repository():
    schemas = list((ROOT / "manifold_contracts").glob("*.schema.json")) + list((ROOT / "api" / "schemas").glob("*.json"))
    ids = [json.loads(p.read_text()).get("$id") for p in schemas]
    for i in filter(None, ids):
        assert "protodirsig" not in i.lower() and i.split(":", 1)[0] in ("https", "urn"), i      # stable and absolute


def test_the_pre_rename_work_root_is_named_with_the_move_command_and_not_moved(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    new, old = default_work_root(), legacy_work_root()
    assert (new, old) == (tmp_path / "state" / "manifold" / "work", tmp_path / "state" / "protodirsig" / "work")
    (old / "runs" / "a").mkdir(parents=True)
    with caplog.at_level(logging.WARNING, logger=_names.LOGGER_NAME):
        Workspace.local()
    (record,) = caplog.records
    message = record.getMessage()
    assert str(new) in message and str(old) in message and move_command(old, new) in message
    assert (old / "runs" / "a").is_dir() and not any((new / "runs").iterdir())       # nothing moved
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=_names.LOGGER_NAME):
        Workspace.local(work=tmp_path / "explicit")                                     # an explicit root: no warning
    assert caplog.records == []
    subprocess.run(move_command(old, new), shell=True, check=True)                     # the command does the move
    assert (new / "runs" / "a").is_dir() and not old.exists()
    with caplog.at_level(logging.WARNING, logger=_names.LOGGER_NAME):
        Workspace.local()                                                               # moved: no warning
    assert caplog.records == []


def test_the_move_command_creates_the_parent_when_the_new_root_is_absent(tmp_path):
    old, new = tmp_path / "a b" / "work", tmp_path / "x" / "manifold" / "work"
    (old / "runs").mkdir(parents=True)
    assert move_command(old, new).startswith("mkdir -p ")
    subprocess.run(move_command(old, new), shell=True, check=True)
    assert (new / "runs").is_dir() and not old.exists()
