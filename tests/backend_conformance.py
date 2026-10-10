"""The Backend conformance suite: what any implementation of `protodirsig.backend.Backend` must do, as wire documents
that validate against api/schemas/ and errors that carry problem details.

`BackendConformance` is a base class; a subclass supplies the fixtures `backend` (class-scoped, an empty work root)
and `library` (class-scoped, a writable copy of the layer root whose recipes render 16 x 16), and the hooks below
that reach into the implementation (holding runs in `accepted`, killing a worker, listing a run's processes). A future
RemoteBackend runs the same tests by subclassing it. Every wait is bounded (WAIT_S).
"""
import copy
import hashlib
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml

from api_schema import errors as schema_errors
from protodirsig import identity
from protodirsig.backend import Backend
from protodirsig.compose import compose
from protodirsig.errors import AdmissionError, InvalidRequestError, NotFoundError, ProblemError

WAIT_S = 600
UNKNOWN = "0" * 64


def wait_for(backend, run_id, states, timeout=WAIT_S):
    deadline = time.monotonic() + timeout
    while True:
        status = backend.get_run(run_id)
        if status["state"] in states:
            return status
        if time.monotonic() > deadline:
            raise AssertionError(f"run {run_id[:12]} still {status['state']} after {timeout} s: {status['errors']}")
        time.sleep(0.25)


def variant(library, base, name, width=16, height=16, edit=None):
    """A copy of recipe `base` with a `width` x `height` window on every settings member (a distinct run id per
    window), written as recipes/<name>.yaml; `edit(doc)` changes it further."""
    doc = yaml.safe_load((library / "recipes" / f"{base}.yaml").read_text())
    for m in doc["settings"]:
        m["roi"] = {"Width": width, "Height": height, "OffsetX": None, "OffsetY": None}
    if edit:
        edit(doc)
    path = library / "recipes" / f"{name}.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return path


def two_sensors(doc):
    keep = ["auror-nir.yaml", "synthetic_600_200_vis_1920.yaml"]
    doc["sensors"] = keep
    doc["settings"] = [m for m in doc["settings"] if m["entry_id"] != "deepscan-850-306-nir-1280"]
    doc["fidelity_by_sensor"] = {k: v for k, v in doc["fidelity_by_sensor"].items() if k in keep}


def assert_problem(err, status, type_suffix):
    assert isinstance(err, ProblemError)
    assert schema_errors("problem", err.problem) == [], err.problem
    assert err.problem["status"] == status and err.problem["type"].endswith(type_suffix), err.problem


class BackendConformance:
    # --- hooks a subclass implements ----------------------------------------------------------------------------

    @contextmanager
    def hold_execution(self, backend):
        """Keep new runs in `accepted` while the block runs."""
        pytest.skip("hold_execution not supported by this backend")
        yield

    def kill_worker(self, backend, run_id):
        pytest.skip("kill_worker not supported by this backend")

    def execution_snapshot(self, backend, run_id):
        """Whatever records that a run was executed (compared before and after a resubmission)."""
        pytest.skip("execution_snapshot not supported by this backend")

    def run_processes(self, backend, run_id):
        """The live processes executing a run."""
        pytest.skip("run_processes not supported by this backend")

    def second_backend(self, backend):
        """Another instance over the same state."""
        pytest.skip("second_backend not supported by this backend")

    def sensor_library(self, library):
        return library.parent / "manifold_sensors"

    # --- shared fixture: one rendered run -----------------------------------------------------------------------

    @pytest.fixture(scope="class")
    @classmethod
    def rendered(cls, backend, library):
        recipe = variant(library, "auror_ref", "conformance_rendered")
        t0 = time.monotonic()
        first = backend.submit_run(recipe)
        returned_s = time.monotonic() - t0
        final = wait_for(backend, first["run_id"], ("rendered", "failed", "cancelled"))
        assert final["state"] == "rendered", final["errors"]
        return {"recipe": recipe, "first": first, "returned_s": returned_s, "final": final}

    # --- tests --------------------------------------------------------------------------------------------------

    def test_is_a_backend(self, backend):
        assert isinstance(backend, Backend)

    # --- the library family -----------------------------------------------------------------------------------

    KIND_FOLDERS = {"recipe": "recipes", "scenario": "scenarios", "engine_profile": "engine_profiles"}

    def _library_files(self, library, kind):
        folder = self.sensor_library(library) if kind == "sensor" else library / self.KIND_FOLDERS[kind]
        return {(p.name if kind == "sensor" else p.stem): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in folder.glob("*.yaml")}

    @pytest.mark.parametrize("kind", ["sensor", "scenario", "engine_profile", "recipe"])
    def test_the_library_lists_every_resource(self, backend, library, kind):
        listed = backend.list_resources(kind)
        assert schema_errors("library_list", listed) == []
        assert {r["name"]: r["sha256"] for r in listed["items"]} == self._library_files(library, kind)
        assert [r["name"] for r in listed["items"]] == sorted(r["name"] for r in listed["items"])

    @pytest.mark.parametrize("kind", ["sensor", "scenario", "engine_profile", "recipe"])
    def test_the_library_reads_every_resource(self, backend, library, kind):
        for item in backend.list_resources(kind)["items"]:
            doc = backend.get_resource(kind, item["name"])
            assert schema_errors("sensor_document" if kind == "sensor" else "library_document", doc) == []
            folder = self.sensor_library(library) if kind == "sensor" else library / self.KIND_FOLDERS[kind]
            path = folder / (item["name"] if kind == "sensor" else f"{item['name']}.yaml")
            assert doc["document"] == yaml.safe_load(path.read_text()) and doc["sha256"] == item["sha256"]

    def test_an_unknown_resource_is_not_found(self, backend):
        with pytest.raises(NotFoundError) as e:
            backend.get_resource("recipe", "no_such_recipe")
        assert_problem(e.value, 404, "not-found")

    def test_a_malformed_resource_names_its_file(self, backend, library):
        path = library / "scenarios" / "conformance_malformed.yaml"
        path.write_text("collection: [unclosed\n")
        try:
            with pytest.raises(AdmissionError) as e:
                backend.get_resource("scenario", "conformance_malformed")
            assert_problem(e.value, 422, "admission")
            assert e.value.problem["layer"] == "scenarios/conformance_malformed.yaml"
        finally:
            path.unlink()

    def test_compose_returns_a_compose_response(self, backend, library):
        doc = backend.compose(library / "recipes" / "sensor_sweep_tahoe.yaml")
        assert schema_errors("compose_response", doc) == []
        assert doc["is_sweep"] and len(doc["runs"]) == 3
        one = backend.compose(library / "recipes" / "auror_ref.yaml", inline_sensor=True)
        assert schema_errors("compose_response", one) == [] and "sensor_system" in one["runs"][0]["run_spec"]["descriptor"]["sensor"]

    def test_compose_error_is_a_problem_naming_layer_and_field(self, backend, library):
        bad = variant(library, "auror_ref", "conformance_bad_compose", edit=lambda d: d.update(color="red"))
        with pytest.raises((InvalidRequestError, AdmissionError)) as e:
            backend.compose(bad)
        assert_problem(e.value, 422, "compose")
        assert (e.value.problem["layer"], e.value.problem["field"]) == ("recipes/conformance_bad_compose.yaml", "color")

    def test_validate_none_needs_no_engine(self, backend, library, monkeypatch, tmp_path):
        def no_process(*a, **k):
            raise AssertionError("an engine or worker process was started by validate at engine_check='none'")
        good = variant(library, "auror_ref", "conformance_validate")
        spec = compose(good)
        spec["engine"]["motion"]["kind"] = "bogus"
        bad = tmp_path / "bad_spec.yaml"
        bad.write_text(yaml.safe_dump(spec, sort_keys=False))
        monkeypatch.setattr(subprocess, "Popen", no_process)
        ok = backend.validate(good)
        ko = backend.validate(bad)
        monkeypatch.undo()
        for doc in (ok, ko):
            assert schema_errors("validate_response", doc) == [], doc
            assert doc["engine_check"] == "none" and not doc["runs"][0]["engine_checked"]
        assert ok["runs"][0]["valid"] and all(c["passed"] for c in ok["runs"][0]["checks"])
        assert ok["runs"][0]["run_id"] == identity.run_id(compose(good), self.sensor_library(library))
        run = ko["runs"][0]
        assert not run["valid"]
        schema = next(c for c in run["checks"] if c["check"] == "schema")
        assert not schema["passed"] and "/engine/motion/kind" in schema["errors"][0]["detail"]

    def test_submit_run_returns_at_once_and_renders(self, backend, library, rendered):
        first, final = rendered["first"], rendered["final"]
        assert first["state"] == "accepted" and schema_errors("run_status", first) == []
        assert first["run_id"] == identity.run_id(compose(rendered["recipe"]), self.sensor_library(library))
        assert schema_errors("run_status", final) == [] and final["errors"] == []
        names = [a["name"] for a in final["artifacts"]]
        assert names[0] == "run_spec.json" and any(n.endswith(".img") for n in names)
        listed = backend.list_artifacts(first["run_id"])
        assert schema_errors("artifact_list", listed) == [] and listed["artifacts"] == final["artifacts"]
        for ref in listed["artifacts"]:
            assert schema_errors("artifact_ref", ref) == []
            data, media = backend.get_artifact(first["run_id"], ref["name"])
            assert hashlib.sha256(data).hexdigest() == ref["sha256"] and media == ref["media_type"]
        spec_bytes, _ = backend.get_artifact(first["run_id"], "run_spec.json")
        assert hashlib.sha256(spec_bytes).hexdigest() == first["run_id"]

    def test_resubmission_returns_the_existing_run(self, backend, rendered):
        run_id = rendered["first"]["run_id"]
        before = self.execution_snapshot(backend, run_id)
        again = backend.submit_run(rendered["recipe"])
        assert again["run_id"] == run_id and again["state"] == "rendered"
        assert self.execution_snapshot(backend, run_id) == before

    def test_an_unstamped_reference_is_refused(self, backend, library):
        profile = library / "engine_profiles" / "tahoe_static_pose.yaml"
        text = profile.read_text()
        start = text.index("platforms/")
        start = text.index('content_hash: "', start) + len('content_hash: "')
        unstamped = library / "engine_profiles" / "conformance_unstamped.yaml"
        unstamped.write_text(text[:start] + "sha256:<hash>" + text[text.index('"', start):])
        recipe = variant(library, "auror_ref", "conformance_unstamped",
                         edit=lambda d: d.update(engine_profile="conformance_unstamped"))
        runs_before = self._runs(backend)
        with pytest.raises(AdmissionError) as e:
            backend.submit_run(recipe)
        assert_problem(e.value, 422, "admission")
        p = e.value.problem
        assert (p["layer"], p["field"]) == ("engine_profiles/conformance_unstamped.yaml", "engine.platform.ref.content_hash")
        assert "/engine/platform/ref" in p["detail"] and self._runs(backend) == runs_before

    def _runs(self, backend):
        return sorted(getattr(getattr(backend, "store", None), "list_runs", lambda: [])())

    def test_a_sweep_with_a_failing_member_creates_nothing(self, backend, library):
        def bad_member(doc):
            two_sensors(doc)
            j = [m["entry_id"] for m in doc["settings"]].index("synthetic-600-200-vis-1920")
            del doc["settings"][j]["gain"]["value"]
        recipe = variant(library, "sensor_sweep_tahoe", "conformance_bad_sweep", edit=bad_member)
        runs_before = self._runs(backend)
        with pytest.raises(AdmissionError) as e:
            backend.submit_sweep(recipe)
        assert_problem(e.value, 422, "admission")
        errs = e.value.problem["errors"]
        assert [x["run"] for x in errs] == ["sensor-sweep-tahoe--synthetic_600_200_vis_1920"]
        assert errs[0]["layer"] == "recipes/conformance_bad_sweep.yaml" and errs[0]["field"].endswith(".gain")
        assert self._runs(backend) == runs_before

    def test_a_cancelled_sweep_run_does_not_change_the_other(self, backend, library):
        recipe = variant(library, "sensor_sweep_tahoe", "conformance_sweep", width=17, edit=two_sensors)
        with self.hold_execution(backend):
            sweep = backend.submit_sweep(recipe)
            assert schema_errors("sweep_status", sweep) == []
            assert [r["state"] for r in sweep["runs"]] == ["accepted", "accepted"]
            keep, drop = sweep["runs"][0]["run_id"], sweep["runs"][1]["run_id"]
            assert backend.cancel_run(drop)["state"] == "cancelled"
        assert wait_for(backend, keep, ("rendered", "failed", "cancelled"))["state"] == "rendered"
        after = backend.get_sweep(sweep["sweep_id"])
        assert schema_errors("sweep_status", after) == []
        assert [r["state"] for r in after["runs"]] == ["rendered", "cancelled"]
        again = backend.submit_sweep(recipe)
        assert again["sweep_id"] == sweep["sweep_id"] and [r["state"] for r in again["runs"]] == ["rendered", "cancelled"]

    def test_cancel_an_accepted_run_and_a_final_run(self, backend, library, rendered):
        recipe = variant(library, "auror_ref", "conformance_cancel_accepted", width=18)
        with self.hold_execution(backend):
            run_id = backend.submit_run(recipe)["run_id"]
            cancelled = backend.cancel_run(run_id)
            assert cancelled["state"] == "cancelled" and schema_errors("run_status", cancelled) == []
        time.sleep(2)
        assert backend.get_run(run_id)["state"] == "cancelled"
        assert self.run_processes(backend, run_id) == []
        final = rendered["final"]
        assert backend.cancel_run(final["run_id"]) == backend.get_run(final["run_id"])

    def test_cancel_a_running_run_stops_its_processes(self, backend, library):
        recipe = variant(library, "auror_ref", "conformance_cancel_running", width=500, height=500)
        run_id = backend.submit_run(recipe)["run_id"]
        status = wait_for(backend, run_id, ("running", "rendered", "failed"))
        if status["state"] != "running":
            pytest.skip(f"the run finished ({status['state']}) before it could be cancelled while running")
        time.sleep(1.0)
        assert self.run_processes(backend, run_id), "no process executes the running run"
        assert backend.cancel_run(run_id)["state"] == "cancelled"
        assert self.run_processes(backend, run_id) == []
        time.sleep(1)
        assert backend.get_run(run_id)["state"] == "cancelled"

    def test_unknown_ids_raise_not_found(self, backend):
        for call in (lambda: backend.get_run(UNKNOWN), lambda: backend.list_artifacts(UNKNOWN),
                     lambda: backend.get_artifact(UNKNOWN, "run_spec.json"), lambda: backend.cancel_run(UNKNOWN),
                     lambda: backend.get_sweep(UNKNOWN), lambda: backend.get_run("not-an-id")):
            with pytest.raises(NotFoundError) as e:
                call()
            assert_problem(e.value, 404, "not-found")

    def test_an_unknown_artifact_name_raises_not_found(self, backend, rendered):
        with pytest.raises(NotFoundError) as e:
            backend.get_artifact(rendered["first"]["run_id"], "no_such_file.img")
        assert_problem(e.value, 404, "not-found")

    def test_a_multi_frame_run_lists_per_frame_artifacts(self, backend, library):
        run_id = backend.submit_run(library / "recipes" / "leo_pass_tahoe.yaml")["run_id"]
        final = wait_for(backend, run_id, ("rendered", "failed", "cancelled"))
        assert final["state"] == "rendered", final["errors"]
        framed = [a for a in final["artifacts"] if "frame" in a]
        assert sorted({a["frame"] for a in framed}) == [0, 1, 2]
        for f in (0, 1, 2):
            assert any(a["name"].endswith(f"-t{f:04d}-c0000.img") and a["frame"] == f for a in framed)
        assert all("frame" not in a for a in final["artifacts"] if a["name"].endswith(".json"))

    def test_a_killed_worker_leaves_a_failed_run(self, backend, library):
        recipe = variant(library, "auror_ref", "conformance_killed", width=19)
        with self.hold_execution(backend):
            run_id = backend.submit_run(recipe)["run_id"]
            self.kill_worker(backend, run_id)
            status = wait_for(backend, run_id, ("failed",), timeout=30)
        assert status["errors"][0]["type"] == "urn:protodirsig:problem:execution"
        assert schema_errors("run_status", status) == []

    def test_two_instances_see_the_same_runs(self, backend, rendered):
        other = self.second_backend(backend)
        run_id = rendered["first"]["run_id"]
        assert other.get_run(run_id) == backend.get_run(run_id)
        assert other.list_artifacts(run_id) == backend.list_artifacts(run_id)

    def test_a_sweep_recipe_is_not_a_run(self, backend, library):
        with pytest.raises(InvalidRequestError) as e:
            backend.submit_run(library / "recipes" / "sensor_sweep_tahoe.yaml")
        assert_problem(e.value, 422, "invalid-request")
        assert "submit_sweep" in e.value.problem["detail"]

    def test_copying_the_spec_does_not_change_its_id(self, backend, library):
        recipe = library / "recipes" / "auror_ref.yaml"
        a = backend.compose(recipe)["runs"][0]
        assert a["run_id"] == identity.run_id(copy.deepcopy(a["run_spec"]), self.sensor_library(library))
