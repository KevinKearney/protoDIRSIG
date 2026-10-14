"""Artifact roles and run verdicts (`proposed`, C-34): the role vocabulary of `artifact_ref`, the DIRSIG pass-through
mapping from file names to roles, and the verdict a status carries in each final state, including statuses stored
before verdicts existed."""
import json

import pytest

from manifold.core.artifacts import ROLES, ArtifactError, artifact_ref
from manifold.engines.dirsig.adapter import passthrough_role
from manifold.sim.store import DEFAULT_VERDICT


def test_the_initial_role_set_is_named_in_the_schema_and_the_vocabulary_stays_free():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "api" / "schemas" / "artifact_ref.schema.json").read_text())
    role = schema["properties"]["role"]
    assert "enum" not in role and all(f"`{r}`" in role["description"] for r in ROLES)
    status = json.loads((root / "api" / "schemas" / "run_status.schema.json").read_text())
    assert set(status["properties"]["verdict"]["enum"]) == set(DEFAULT_VERDICT.values())


def test_artifact_ref_carries_a_role_from_the_vocabulary(tmp_path):
    f = tmp_path / "a.img"
    f.write_bytes(b"x")
    assert artifact_ref(f, role="product")["role"] == "product" and "role" not in artifact_ref(f)
    assert artifact_ref(f, role="calibration")["role"] == "calibration"           # free: a new word is accepted
    with pytest.raises(ArtifactError, match="lowercase word"):
        artifact_ref(f, role="Product image")


@pytest.mark.parametrize("name, role", [
    ("demo.img", "product"), ("demo-t0000-c0000.img", "product"), ("demo.img.hdr", "metadata"),
    ("demo_truth.img", "truth"), ("demo_truth.img.hdr", "metadata"), ("sub/Truth-c0.img", "truth"),
    ("run_info.json", "log"), ("log_info.json", "log"), ("stub_engine_args.json", "metadata"),
    ("dirsig.log", "log"), ("stdout.txt", "log"), ("quicklook.png", "preview"), ("demo.weird", "product"),
    ("copied/demo.scene", "config"), ("demo.platform", "config"), ("table.csv", "metadata")])
def test_the_passthrough_role_of_a_file(name, role):
    assert passthrough_role(name) == role


def test_a_status_stored_before_verdicts_gets_the_one_its_state_implies(tmp_path):
    from manifold.sim.store import RunStore
    store = RunStore(tmp_path / "work")
    run_dir = store.runs / ("ab" * 32)
    run_dir.mkdir(parents=True)
    for state, verdict in (("rendered", "complete"), ("failed", "failed"), ("cancelled", "incomplete")):
        (run_dir / "status.json").write_text(json.dumps({"run_id": "ab" * 32, "name": "x", "state": state,
                                                         "errors": [], "artifacts": []}))
        assert store._status("ab" * 32)["verdict"] == verdict
    (run_dir / "status.json").write_text(json.dumps({"run_id": "ab" * 32, "name": "x", "state": "failed",
                                                     "verdict": "incomplete", "errors": [], "artifacts": []}))
    assert store._status("ab" * 32)["verdict"] == "incomplete"            # a recorded verdict is kept
