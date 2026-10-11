"""The id snapshot (`tests/data/id_snapshot.json`, written by `scripts/id_snapshot.py`): every run id, sweep id,
identity, compose and orbit vector id and committed demo digest the repository derives offline, recomputed and
compared. A rename or a layout change must leave every one of them as recorded. An entry that needs an absent
gitignored asset (a pass-through demo directory) is skipped with the reason; the rest are still checked."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("id_snapshot", ROOT / "scripts" / "id_snapshot.py")
id_snapshot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(id_snapshot)
RECORDED = json.loads((ROOT / "tests" / "data" / "id_snapshot.json").read_text())
ENTRIES = [(group, key) for group in ("recipes", "generated_specs") for key in sorted(RECORDED[group])]


@pytest.fixture(scope="module")
def current():
    return id_snapshot.snapshot()


@pytest.mark.parametrize("group, key", ENTRIES, ids=[f"{g}:{Path(k).name}" for g, k in ENTRIES])
def test_recipe_and_run_spec_ids_are_as_recorded(current, group, key):
    snap, skipped = current
    if f"{group}/{key}" in skipped:
        pytest.skip(skipped[f"{group}/{key}"])
    assert snap[group][key] == RECORDED[group][key]


def test_no_recipe_or_run_spec_is_added_or_removed(current):
    snap, skipped = current
    for group in ("recipes", "generated_specs"):
        assert set(snap[group]) | {k.split("/", 1)[1] for k in skipped if k.startswith(group + "/")} \
            == set(RECORDED[group])


@pytest.mark.parametrize("group", ["vectors", "sweep_digest_table"])
def test_vector_and_digest_ids_are_as_recorded(current, group):
    snap, _ = current
    assert id_snapshot.compare(RECORDED[group], snap[group], {}) == []


def test_the_snapshot_file_is_canonical():
    text = (ROOT / "tests" / "data" / "id_snapshot.json").read_text()
    assert text == id_snapshot.dumps(RECORDED)
    assert str(Path.home()) not in text and "<repo>" in text            # no machine path


def test_an_absent_pass_through_directory_skips_only_its_entries(tmp_path, monkeypatch):
    """A fresh clone has no `manifold_config_repo/demo_dirs/`: its pass-through entries are skipped with the reason,
    and every other entry still compares."""
    monkeypatch.setattr(id_snapshot, "CONFIG", tmp_path)
    snap, skipped = id_snapshot.snapshot()
    assert skipped and all("pass-through directory" in r and "absent" in r for r in skipped.values())
    assert {k.split("/", 1)[0] for k in skipped} == {"recipes", "generated_specs"}
    assert id_snapshot.compare(RECORDED, snap, skipped) == []
    assert id_snapshot.main(["--check"]) == 0
