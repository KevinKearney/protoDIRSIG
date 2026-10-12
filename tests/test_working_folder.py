"""Files DIRSIG looks for in the working folder (`engine.working_folder`, proposed): `scene_ref.working_folder_files`
finds them from the scene and platform files, `run_spec.resolve_run` requires the member to list exactly those (with
their library refs, so the run id covers their bytes), and `Simulation` copies them into the job's input folder, which
is where DIRSIG runs a layered job. Measured on BayerPattern1 (`pixels.hdf`, named by its platform) and Telecentricity1
(`demo.glist` beside its `.scene`, outside its `gdbdirectory`, and the `Sphere.obj` it names): with the files there
both layered renders are byte-identical to their same-seed pass-through renders (`docs/DIRSIG_layered_comparison.md`).
The library's scenes and platforms need none, so existing jobs and run ids are unchanged (tests/test_id_snapshot.py).
The files here are written by the test (no demo bytes); the render is a 16 x 16 view of a sphere whose geometry list
lies beside its `.scene` and not in its `gdbdirectory`."""
import shutil
from pathlib import Path

import pytest
import yaml

from backend_conformance import wait_for
from manifold.core.dirhash import directory_digest
from manifold.core.identity import run_id
from manifold.core.run_spec import RunSpecError
from manifold.core.spectral import sha256_file
from manifold.engines.dirsig.run_spec import resolve_run
from manifold.engines.dirsig.scene_ref import fingerprint, working_folder_files
from manifold.engines.dirsig.simulation import Simulation, schema_errors
from test_authored_platform import PLATFORM, REL, authored_spec
from test_scene_siblings import GLIST, MAT, SCENE
from test_simulation import CONFIG_REPO, needs_dirsig

ROOT = Path(__file__).resolve().parents[1]
SENSORS = ROOT / "manifold_sensors"
LISTED = SCENE.replace("<gdbdirectory>$SCENE_DIR</gdbdirectory>", "<gdbdirectory>$SCENE_DIR/geometry</gdbdirectory>")
NAMED = PLATFORM.replace("<clocktable/>", "<clocktable/><notes><filename>pixels.txt</filename>"
                         "<filename>/abs/pixels.txt</filename><filename>$HOME/x.txt</filename>"
                         "<filename>../up.txt</filename><filename>absent.txt</filename></notes>")
NAMED_REL = "platforms/Named/named.platform"


def write_scene(folder, scene=LISTED, glist=GLIST):
    """A sphere scene whose geometry list lies beside the `.scene`; its `gdbdirectory` is `geometry/` (exists)."""
    folder.mkdir(parents=True)
    (folder / "ball.scene").write_text(scene)
    (folder / "ball.glist").write_text(glist)
    (folder / "ball.mat").write_text(MAT)
    (folder / "geometry").mkdir()
    (folder / "geometry" / "README").write_text("the gdbdirectory")
    return folder / "ball.scene"


def test_a_list_beside_the_scene_and_outside_its_gdbdirectory(tmp_path):
    scene = write_scene(tmp_path / "ball", glist=GLIST.replace("<sphere>", "<obj><filename>shape.obj</filename></obj>"
                                                               "<obj><filename>kept.obj</filename></obj><sphere>"))
    (scene.parent / "shape.obj").write_text("v 0 0 0\n")
    (scene.parent / "kept.obj").write_text("v 0 0 0\n")
    (scene.parent / "geometry" / "kept.obj").write_text("v 0 0 0\n")          # found in the gdbdirectory: not listed
    platform = tmp_path / "plain.platform"
    platform.write_text(PLATFORM)
    assert working_folder_files(scene, platform) == [
        ("ball.glist", scene.parent / "ball.glist", "ball.scene"),
        ("shape.obj", scene.parent / "shape.obj", "ball.glist")]


@pytest.mark.parametrize("gdb", ["$SCENE_DIR", ""])
def test_a_list_in_the_gdbdirectory_needs_nothing(tmp_path, gdb):
    # PointCollectors2's layout ($SCENE_DIR): DIRSIG finds the list in the job's scene copy.
    scene = write_scene(tmp_path / "ball", scene=SCENE.replace("$SCENE_DIR</gdbdirectory>", f"{gdb}</gdbdirectory>"))
    platform = tmp_path / "plain.platform"
    platform.write_text(PLATFORM)
    assert working_folder_files(scene, platform) == []


def test_a_file_the_platform_names_relative_to_its_folder(tmp_path):
    scene = write_scene(tmp_path / "ball", scene=SCENE)
    platform = tmp_path / "plat" / "named.platform"
    platform.parent.mkdir()
    platform.write_text(NAMED)
    (platform.parent / "pixels.txt").write_text("pixels")
    (tmp_path / "up.txt").write_text("outside the platform's folder")
    assert working_folder_files(scene, platform) == [("pixels.txt", platform.parent / "pixels.txt", "named.platform")]


def test_the_library_scenes_and_platforms_need_nothing():
    # So the job of every existing layered run is assembled as before.
    platforms = sorted((CONFIG_REPO / "platforms").rglob("*.platform"))
    assert platforms
    for platform in platforms:
        assert working_folder_files(CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene", platform) == [], platform


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    lib = tmp_path_factory.mktemp("working_folder") / "config_repo"
    shutil.copytree(CONFIG_REPO / "scenes", lib / "scenes", symlinks=True)      # Tahoe, for the runs that need none
    write_scene(lib / "scenes" / "ball")
    (lib / REL).parent.mkdir(parents=True)
    (lib / REL).write_text(PLATFORM)
    (lib / NAMED_REL).parent.mkdir(parents=True)
    (lib / NAMED_REL).write_text(NAMED)
    (lib / NAMED_REL).with_name("pixels.txt").write_text("pixels")
    return lib


def entry(lib, name, rel):
    return {"name": name, "ref": {"name": rel, "content_hash": sha256_file(lib / rel)}}


def ball_spec(lib, working=True):
    spec = authored_spec(lib)
    spec["engine"]["scenes"] = [{"ref": {"name": "scenes/ball/ball.scene",
                                         "content_hash": directory_digest(lib / "scenes" / "ball")},
                                 "offset": [0, 0, 0]}]
    spec["engine"]["motion"]["position"]["xyz"] = [0.0, 0.0, 1000.0]
    spec["engine"]["motion"]["orientation"]["euler"]["angles"] = [0.0, 0.0, 0.0]
    if working:
        spec["engine"]["working_folder"] = [entry(lib, "ball.glist", "scenes/ball/ball.glist")]
    return spec


def _resolve(tmp_path, spec, lib):
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    return resolve_run(spec, path, lib, SENSORS)


def test_the_listed_files_resolve(tmp_path, library):
    spec = ball_spec(library)
    assert schema_errors(spec) == []
    assert _resolve(tmp_path, spec, library).working_folder == (("ball.glist", library / "scenes/ball/ball.glist"),)
    named = authored_spec(library)
    named["engine"]["platform"]["ref"] = {"name": NAMED_REL, "content_hash": sha256_file(library / NAMED_REL)}
    named["engine"]["working_folder"] = [entry(library, "pixels.txt", "platforms/Named/pixels.txt")]
    assert _resolve(tmp_path, named, library).working_folder == (("pixels.txt", library / "platforms/Named/pixels.txt"),)


def test_a_run_that_needs_none_resolves_as_before(tmp_path, library):
    r = _resolve(tmp_path, authored_spec(library), library)
    assert r.working_folder == ()


def test_an_unlisted_file_is_refused_with_what_to_state(tmp_path, library):
    with pytest.raises(RunSpecError, match=r"ball.scene names ball.glist, which DIRSIG looks for in the job's working "
                                           r"folder; list it in engine.working_folder") as e:
        _resolve(tmp_path, ball_spec(library, working=False), library)
    assert e.value.pointer == "/engine/working_folder"


def test_a_wrong_ref_an_extra_entry_and_a_changed_file_are_refused(tmp_path, library):
    spec = ball_spec(library)
    spec["engine"]["working_folder"][0]["ref"]["name"] = "scenes/ball/ball.mat"
    with pytest.raises(RunSpecError, match="must reference scenes/ball/ball.glist") as e:
        _resolve(tmp_path, spec, library)
    assert e.value.pointer == "/engine/working_folder/0/ref/name"
    spec = ball_spec(library)
    spec["engine"]["working_folder"].append(entry(library, "ball.mat", "scenes/ball/ball.mat"))
    with pytest.raises(RunSpecError, match="ball.mat, a file DIRSIG does not look for") as e:
        _resolve(tmp_path, spec, library)
    assert e.value.pointer == "/engine/working_folder/1/name"
    spec = ball_spec(library)
    spec["engine"]["working_folder"][0]["ref"]["content_hash"] = "sha256:" + "0" * 64
    with pytest.raises(RunSpecError, match="does not match") as e:
        _resolve(tmp_path, spec, library)
    assert e.value.pointer == "/engine/working_folder/0/ref/content_hash"


def test_the_schema(library):
    spec = ball_spec(library)
    spec["engine"]["working_folder"] = []
    assert schema_errors(spec)                                                      # minItems 1
    spec["engine"]["working_folder"] = [{"name": "ball.glist"}]
    assert schema_errors(spec)                                                      # ref required
    passthrough = yaml.safe_load((ROOT / "manifold_run_specs" / "demo_pointcollectors2_passthrough.yaml").read_text())
    assert schema_errors(passthrough) == []
    passthrough["engine"]["working_folder"] = ball_spec(library)["engine"]["working_folder"]
    assert schema_errors(passthrough)                                               # the demo's folder is its own


def test_the_files_are_in_the_run_id(library):
    spec = ball_spec(library)
    other = ball_spec(library)
    other["engine"]["working_folder"][0]["ref"]["content_hash"] = "sha256:" + "1" * 64
    assert run_id(spec, SENSORS) != run_id(other, SENSORS)


def test_the_job_copies_them_into_its_working_folder(tmp_path, library):
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(ball_spec(library), sort_keys=False))
    sim = Simulation.from_run_spec(path, library, tmp_path / "work", SENSORS)
    assert sim.resolved is not None, sim.resolve_error
    in_dir = tmp_path / "work" / "input"
    sim._assemble(in_dir, tmp_path / "work" / "output")
    copy = in_dir / "ball.glist"
    assert not copy.is_symlink() and copy.read_bytes() == (library / "scenes/ball/ball.glist").read_bytes()
    plain = tmp_path / "plain.yaml"
    plain.write_text(yaml.safe_dump(authored_spec(library), sort_keys=False))
    sim = Simulation.from_run_spec(plain, library, tmp_path / "plain", SENSORS)
    sim._assemble(tmp_path / "plain" / "input", tmp_path / "plain" / "output")
    assert not (tmp_path / "plain" / "input" / "ball.glist").exists()                       # default: as before


@needs_dirsig
def test_a_16_by_16_render_finds_the_list_in_the_working_folder(tmp_path, library):
    from manifold.sim.backend import LocalBackend
    path = tmp_path / "ball.yaml"
    path.write_text(yaml.safe_dump(ball_spec(library), sort_keys=False))
    before = fingerprint(library)
    backend = LocalBackend(tmp_path / "work", library, sensor_library=SENSORS)
    status = wait_for(backend, backend.submit_run(str(path))["run_id"], ("rendered", "failed", "cancelled"), timeout=300)
    assert status["state"] == "rendered", status
    in_dir = next((tmp_path / "work").rglob("input/auror_ref")).parent
    assert not (in_dir / "ball.glist").is_symlink() and (in_dir / "ball.glist").read_text() == GLIST
    assert fingerprint(library) == before
    shutil.rmtree(tmp_path / "work", ignore_errors=True)
