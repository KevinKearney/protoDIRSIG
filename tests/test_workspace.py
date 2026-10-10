"""The Workspace facade (protodirsig.workspace) over a LocalBackend: models out, ProblemError family raised, one
end-to-end 16 x 16 render and the three-frame pass. The library is a temporary copy of the small layer and sensor files;
the engine assets are the real manifold_config_repo, read only. Each test has a 600 s limit."""
import fcntl
import hashlib
import inspect
import shutil
import signal
import warnings
from pathlib import Path

import pytest
import yaml

import protodirsig
from backend_conformance import two_sensors, variant
from protodirsig import models
from protodirsig.errors import NotFoundError, ProblemError
from protodirsig.workspace import ArtifactContent, Workspace, default_work_root
from test_simulation import CONFIG_REPO, needs_dirsig

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _time_limit():
    def expire(signum, frame):
        raise TimeoutError("test exceeded 600 s")
    old = signal.signal(signal.SIGALRM, expire)
    signal.alarm(600)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, old)


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    root = tmp_path_factory.mktemp("ws_library")
    for d in ("recipes", "scenarios", "engine_profiles"):
        shutil.copytree(ROOT / "manifold_run_specs" / d, root / "manifold_run_specs" / d)
    shutil.copytree(ROOT / "manifold_sensors", root / "manifold_sensors")
    yield root / "manifold_run_specs"
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture(scope="module")
def ws(tmp_path_factory, library):
    work = tmp_path_factory.mktemp("ws_work")
    w = Workspace.local(library=library, config_repo=CONFIG_REPO, work=work)
    yield w
    for run_id in w.backend.store.list_runs():
        if w.get_run(run_id).state in ("accepted", "running"):
            w.cancel_run(run_id)
    shutil.rmtree(work, ignore_errors=True)


def test_the_library_family_returns_models_equal_to_the_backend_documents(ws):
    for kind, lister, getter in (("sensor", ws.list_sensors, ws.get_sensor), ("scenario", ws.list_scenarios, ws.get_scenario),
                                 ("engine_profile", ws.list_engine_profiles, ws.get_engine_profile),
                                 ("recipe", ws.list_recipes, ws.get_recipe)):
        listed = lister()
        assert isinstance(listed, models.LibraryList) and listed.to_dict() == ws.backend.list_resources(kind)
        first = listed.items[0].name
        doc = getter(first)
        assert isinstance(doc, models.SensorDocument if kind == "sensor" else models.LibraryDocument)
        assert doc.to_dict() == ws.backend.get_resource(kind, first)
    with pytest.raises(NotFoundError):
        ws.get_recipe("no_such_recipe")


def test_compose_and_validate_by_library_name(ws, library):
    variant(library, "auror_ref", "ws_small")
    composed = ws.compose("ws_small")
    assert isinstance(composed, models.ComposeResponse) and len(composed.runs) == 1
    checked = ws.validate("ws_small")
    assert isinstance(checked, models.ValidateResponse) and checked.runs[0].valid
    assert checked.runs[0].run_id == composed.runs[0].run_id and checked.runs[0].engine_checked is False


@needs_dirsig
def test_an_end_to_end_run_through_the_facade(ws, library, tmp_path):
    variant(library, "auror_ref", "ws_end_to_end", width=22)
    status = ws.submit_run("ws_end_to_end")
    assert isinstance(status, models.RunStatus) and status.state == "accepted"
    final = ws.wait(status.run_id, timeout=600, poll=0.5)
    assert final.state == "rendered", final.errors
    listed = ws.list_artifacts(status.run_id)
    assert isinstance(listed, models.ArtifactList) and listed.artifacts == final.artifacts
    image = next(a for a in listed.artifacts if a.name.endswith(".img"))
    saved = ws.save_artifact(status.run_id, image.name, tmp_path)
    assert saved == tmp_path / image.name and hashlib.sha256(saved.read_bytes()).hexdigest() == image.sha256
    content = ws.get_artifact(status.run_id, "run_spec.json")
    assert isinstance(content, ArtifactContent) and hashlib.sha256(content.content).hexdigest() == status.run_id
    assert ws.cancel_run(status.run_id).state == "rendered"


def test_a_sweep_submitted_as_a_document(ws, library):
    path = variant(library, "sensor_sweep_tahoe", "ws_sweep_doc", width=23, edit=two_sensors)
    doc = yaml.safe_load(path.read_text())
    store = ws.backend.store
    with open(store.slots / "slot-0.lock", "a") as held:                    # keep the runs accepted, then cancel them
        fcntl.flock(held, fcntl.LOCK_EX)
        sweep = ws.submit_sweep(doc)
        assert isinstance(sweep, models.SweepStatus) and sweep.recipe.name is None and len(sweep.runs) == 2
        assert ws.submit_sweep(doc).sweep_id == sweep.sweep_id == ws.get_sweep(sweep.sweep_id).sweep_id
        for r in sweep.runs:
            assert ws.cancel_run(r.run_id).state == "cancelled"


def test_an_admission_failure_names_layer_and_field(ws, library):
    profile = library / "engine_profiles" / "tahoe_static_pose.yaml"
    text = profile.read_text()
    start = text.index('content_hash: "', text.index("platforms/")) + len('content_hash: "')
    (library / "engine_profiles" / "ws_unstamped.yaml").write_text(text[:start] + "sha256:<hash>" + text[text.index('"', start):])
    variant(library, "auror_ref", "ws_unstamped", edit=lambda d: d.update(engine_profile="ws_unstamped"))
    with pytest.raises(ProblemError) as e:
        ws.submit_run("ws_unstamped")
    assert (e.value.problem["layer"], e.value.problem["field"]) == ("engine_profiles/ws_unstamped.yaml",
                                                                    "engine.platform.ref.content_hash")


@needs_dirsig
def test_the_pass_recipe_lists_three_frames(ws):
    status = ws.submit_run("leo_pass_tahoe")
    final = ws.wait(status.run_id, timeout=600, poll=0.5)
    assert final.state == "rendered", final.errors
    assert sorted({a.frame for a in ws.list_artifacts(status.run_id).artifacts if a.frame is not None}) == [0, 1, 2]


def test_remote_is_phase_three():
    with pytest.raises(NotImplementedError, match="phase 3"):
        Workspace.remote("https://example.invalid")


def test_a_workspace_needs_a_backend():
    with pytest.raises(TypeError):
        Workspace(object())


def test_the_package_exports_workspace_and_version():
    assert protodirsig.Workspace is Workspace and isinstance(protodirsig.__version__, str) and protodirsig.__version__
    assert default_work_root().parts[-2:] == ("protodirsig", "work")


def _sections(doc):
    return {ln.strip() for ln in doc.splitlines()}


def test_every_public_method_has_a_numpy_docstring():
    for name, fn in inspect.getmembers(Workspace, inspect.isfunction) + [
            (n, f.__func__) for n, f in vars(Workspace).items() if isinstance(f, classmethod)]:
        if name.startswith("_"):
            continue
        doc = inspect.getdoc(fn)
        assert doc and doc.splitlines()[0].strip(), name
        params = [p for p in inspect.signature(fn).parameters if p not in ("self", "cls")]
        if params:
            assert {"Parameters", "Returns"} <= _sections(doc), name
    for cls in (Workspace, ArtifactContent):
        assert inspect.getdoc(cls)


def test_every_model_has_a_docstring_with_attributes():
    for name in models.__all__:
        doc = inspect.getdoc(getattr(models, name))
        assert doc and doc.splitlines()[0].strip() and "Attributes" in _sections(doc), name


def test_local_registry_is_deprecated():
    from protodirsig.registry import LocalRegistry
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        LocalRegistry()
    assert any(issubclass(w.category, DeprecationWarning) and "Workspace" in str(w.message) for w in caught)


def test_the_default_work_root_is_the_state_directory_and_the_former_one_is_named_once(tmp_path, monkeypatch, caplog):
    import logging
    from protodirsig.workspace import former_work_root
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    assert default_work_root() == tmp_path / "state" / "protodirsig" / "work"
    old = former_work_root()
    assert old == tmp_path / "cache" / "protodirsig" / "work"
    with caplog.at_level(logging.WARNING, logger="protodirsig"):
        Workspace.local()                                       # no former root: no warning
    assert caplog.records == []
    (old / "runs").mkdir(parents=True)
    with caplog.at_level(logging.WARNING, logger="protodirsig"):
        Workspace.local()
    assert len(caplog.records) == 1 and str(old) in caplog.records[0].getMessage()
    assert (old / "runs").is_dir()                              # left in place, not moved
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="protodirsig"):
        Workspace.local(work=tmp_path / "explicit")             # an explicit work root: no warning
    assert caplog.records == []
    monkeypatch.delenv("XDG_STATE_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert default_work_root() == tmp_path / "home" / ".local" / "state" / "protodirsig" / "work"
