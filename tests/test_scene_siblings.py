"""Files a `.scene` names beside it (BACKLOG "Tagged demos" item 11): `scene_ref.scene_named_paths` finds them and
`reference_scene(..., named=...)` copies them into the job's scene folder (not links: `scene2hdf` writes beside the
`.scene`), and links named directories as it links the asset folders. The library's Tahoe scene names none, so the
jobs of existing runs (and every run id) are unchanged. The scenes here are written by the test (no demo bytes); the
render is a 16 x 16 view of a sphere whose geometry list and material file lie beside its `.scene`."""
import shutil
from pathlib import Path

import pytest

from backend_conformance import wait_for
from manifold.core.dirhash import directory_digest
from manifold.engines.dirsig.scene_ref import fingerprint, reference_scene, scene_named_paths
from test_authored_platform import PLATFORM, REL, authored_spec
from test_simulation import CONFIG_REPO, needs_dirsig

SCENE = """<classicscene>
  <metadata><entry><name>Description</name><value>notes.txt</value></entry></metadata>
  <sceneorigin><location frame="geodetic"><latitude>43</latitude><longitude>-78</longitude><altitude>0</altitude></location></sceneorigin>
  <properties features="vis,nir" mingsd="0" maxgsd="0"/>
  <thumbnaillist><thumbnail><filename>$SCENE_DIR/images/thumb.png</filename></thumbnail></thumbnaillist>
  <odbdirectory>$SCENE_DIR</odbdirectory>
  <gdbdirectory>$SCENE_DIR</gdbdirectory>
  <geometrylist enabled="true"><geometrylistinclude name="ball" enabled="true">ball.glist</geometrylistinclude></geometrylist>
  <matfilename>$SCENE_DIR/ball.mat</matfilename>
  <emsdirectory>$SCENE_DIR/optical</emsdirectory>
  <extdirectory>$SCENE_DIR</extdirectory>
  <absdirectory>$SCENE_DIR</absdirectory>
  <srcdirectory>$SCENE_DIR</srcdirectory>
  <mapdirectory>$SCENE_DIR/maps</mapdirectory>
  <maplist/>
</classicscene>
"""
GLIST = """<geometrylist><object><basegeometry><sphere><matid>ball</matid>
<center><point><x>0</x><y>0</y><z>0</z></point></center><radius>1.0</radius></sphere></basegeometry>
<staticinstance/></object></geometrylist>
"""
MAT = """MATERIAL_ENTRY {
    ID = ball
    NAME = Half Gray
    DOUBLE_SIDED = TRUE
    SURFACE_PROPERTIES {
        REFLECTANCE_PROP_NAME = WardBRDF
        REFLECTANCE_PROP {
            DS_WEIGHTS = 0.5 0.0
            XY_SIGMAS  = 0.0 0.0
        }
    }
    RAD_SOLVER_NAME = Simple
    RAD_SOLVER {
        QUALITY = LOW
    }
}
"""


def write_scene(folder, optical=True):
    folder.mkdir(parents=True)
    (folder / "ball.scene").write_text(SCENE)
    (folder / "ball.glist").write_text(GLIST)
    (folder / "ball.mat").write_text(MAT)
    (folder / "notes.txt").write_text("named only in the metadata")
    (folder / "images").mkdir()
    (folder / "images" / "thumb.png").write_bytes(b"png")
    (folder / "maps").mkdir()
    if optical:
        (folder / "optical").mkdir()
        (folder / "optical" / "a.ems").write_text("ems")
    return folder / "ball.scene"


def test_the_named_files_and_directories_beside_a_scene(tmp_path):
    scene = write_scene(tmp_path / "ball")
    assert scene_named_paths(scene) == (("ball.glist", "ball.mat"), ("optical",))


def test_a_listing_is_followed_one_level_and_names_outside_the_folder_are_ignored(tmp_path):
    scene = write_scene(tmp_path / "ball", optical=False)
    (tmp_path / "ball" / "ball.glist").write_text(GLIST.replace("<sphere>", "<obj><filename>shape.obj</filename></obj><sphere>"))
    (tmp_path / "ball" / "shape.obj").write_text("v 0 0 0\n")
    (tmp_path / "outside.mat").write_text(MAT)
    scene.write_text(SCENE.replace("$SCENE_DIR/ball.mat", "../outside.mat"))
    assert scene_named_paths(scene) == (("ball.glist", "shape.obj"), ())


def test_the_library_scene_names_nothing_beside_it():
    # So the job of every existing layered run is assembled as before.
    assert scene_named_paths(CONFIG_REPO / "scenes" / "tahoe" / "tahoe.scene") == ((), ())


def test_named_files_are_copied_and_named_directories_linked(tmp_path):
    scene = write_scene(tmp_path / "lib" / "ball")
    before = fingerprint(scene.parent)
    copy = reference_scene(scene, tmp_path / "job", named=scene_named_paths(scene))
    job = copy.parent
    for name in ("ball.glist", "ball.mat"):
        assert not (job / name).is_symlink() and (job / name).read_bytes() == (scene.parent / name).read_bytes()
    assert (job / "optical").is_symlink() and (job / "maps").is_symlink()
    assert not (job / "notes.txt").exists() and not (job / "images").exists()
    (job / "ball.scene.hdf").write_text("what scene2hdf writes beside the .scene")
    assert fingerprint(scene.parent) == before
    assert not (reference_scene(scene, tmp_path / "plain").parent / "ball.glist").exists()     # default: as before


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    lib = tmp_path_factory.mktemp("siblings") / "config_repo"
    write_scene(lib / "scenes" / "ball")
    (lib / REL).parent.mkdir(parents=True)
    (lib / REL).write_text(PLATFORM)
    return lib


@needs_dirsig
def test_a_16_by_16_render_of_a_scene_with_files_beside_it(tmp_path, library):
    import yaml
    from manifold.sim.backend import LocalBackend
    spec = authored_spec(library)
    spec["engine"]["scenes"] = [{"ref": {"name": "scenes/ball/ball.scene",
                                         "content_hash": directory_digest(library / "scenes" / "ball")},
                                 "offset": [0, 0, 0]}]
    spec["engine"]["motion"]["position"]["xyz"] = [0.0, 0.0, 1000.0]
    spec["engine"]["motion"]["orientation"]["euler"]["angles"] = [0.0, 0.0, 0.0]
    path = tmp_path / "ball.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    before = fingerprint(library)
    backend = LocalBackend(tmp_path / "work", library, sensor_library=Path(__file__).resolve().parents[1] / "manifold_sensors")
    status = wait_for(backend, backend.submit_run(str(path))["run_id"], ("rendered", "failed", "cancelled"), timeout=300)
    assert status["state"] == "rendered", status
    scene_dir = next((tmp_path / "work").rglob("input/auror_ref"))
    assert not (scene_dir / "ball.mat").is_symlink() and (scene_dir / "ball.mat").read_text() == MAT
    assert (scene_dir / "optical").is_symlink()
    assert (scene_dir / "ball.scene.hdf").is_file()                                   # written in the job, not the library
    assert fingerprint(library) == before
    shutil.rmtree(tmp_path / "work", ignore_errors=True)
