"""Files DIRSIG looks for in the working folder (`engine.working_folder`, proposed): `scene_ref.working_folder_files`
finds them from the scene and platform files, `run_spec.resolve_run` requires the member to list exactly those (with
their library refs, so the run id covers their bytes), and `Simulation` copies them into the job's input folder, which
is where DIRSIG runs a layered job. Measured on BayerPattern1 (`pixels.hdf`, named by its platform) and Telecentricity1
(`demo.glist` beside its `.scene`, outside its `gdbdirectory`, and the `Sphere.obj` it names): with the files there
both layered renders are byte-identical to their same-seed pass-through renders (`docs/DIRSIG_layered_comparison.md`).
Files a material file names by the measured keys (Polarization5, BundledMaterials1) follow the same path.
The library's scenes and platforms need none, so existing jobs and run ids are unchanged (tests/test_id_snapshot.py).
The files here are written by the test (no demo bytes); the render is a 16 x 16 view of a sphere whose geometry list
lies beside its `.scene` and not in its `gdbdirectory`, and another of a sphere whose emissivity file is named relative
to its scene's folder and not to its `emsdirectory`."""
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


# Files a material file names (round 26). Measured: DIRSIG looks for a `PARAMETER_FILE`, `BRDF_FIT_FILE` or
# `EMISSIVITY_FILE` in the working folder and the `emsdirectory` only (Polarization5: each missing file stops its layered
# dry run in turn, `./materials/grass.ems` last), and for a `BUNDLE_FILENAME` in the working folder only when the
# `emsdirectory` is empty (BundledMaterials1). A `TEMP_SOLVER` `FILENAME` is found without them (DataDrivenTempSolver1).
NAMES = """MATERIAL_ENTRY {
    ID = ball
    SURFACE_PROPERTIES {
        REFLECTANCE_PROP {
            PARAMETER_FILE = ./optical/a.brdf
            BRDF_FIT_FILE = ./optical/b.fit
            EMISSIVITY_FILE = ./optical/c.ems
            EMISSIVITY_FILE = d.ems
            EMISSIVITY_FILE = optical/both.ems
            EMISSIVITY_FILE = $SCENE_DIR/optical/c.ems
            EMISSIVITY_FILE = ../up.ems
            EMISSIVITY_FILE = ./optical/absent.ems
            TXT_FILENAME = ./optical/u.txt
        }
    }
    BUNDLE_FILENAME = "bundles/e.mat.hdf"
    TEMP_SOLVER {
        FILENAME = ./optical/t.txt
    }
}
"""
EMS = "1\n" + "1.0\n" * 91 + "CURVE_BEGIN\n0.20 0.50\n20.00 0.50\n"     # the "new" .ems format: one flat curve
PAINTED = """MATERIAL_ENTRY {
    NAME = Painted
    ID = ball
    SPECIFIC_HEAT = 0.1000
    THERMAL_CONDUCTIVITY = 20.0000
    MASS_DENSITY = 1.0000
    SPECULARITY = 0.10
    SOLAR_ABSORPTION = 0.2500
    THERMAL_EMISSIVITY = 0.9000
    EXPOSED_AREA = 0.4500
    EMISSIVITY_FILE = ./optical/ball.ems
    THICKNESS = 4.0
}
"""
PAINTED_REL = "scenes/painted/ball.scene"


def write_named(folder, scene=SCENE, mat=NAMES):
    """A sphere scene (emsdirectory `$SCENE_DIR/optical`) whose material file names files by the measured keys."""
    write_scene(folder, scene=scene)
    (folder / "ball.mat").write_text(mat)
    (folder / "optical" / "optical").mkdir(parents=True)
    (folder / "bundles").mkdir()
    for rel in ("optical/a.brdf", "optical/b.fit", "optical/c.ems", "optical/d.ems", "optical/both.ems",
                "optical/optical/both.ems", "optical/u.txt", "optical/t.txt", "bundles/e.mat.hdf"):
        (folder / rel).write_text(rel)
    (folder.parent / "up.ems").write_text("outside the scene's folder")
    return folder / "ball.scene"


def test_files_a_material_file_names_relative_to_the_scene_and_outside_its_emsdirectory(tmp_path):
    scene = write_named(tmp_path / "ball")
    platform = tmp_path / "plain.platform"
    platform.write_text(PLATFORM)
    top = scene.parent
    assert working_folder_files(scene, platform) == [
        ("bundles/e.mat.hdf", top / "bundles/e.mat.hdf", "ball.mat"),
        ("optical/a.brdf", top / "optical/a.brdf", "ball.mat"),
        ("optical/b.fit", top / "optical/b.fit", "ball.mat"),
        ("optical/c.ems", top / "optical/c.ems", "ball.mat")]


def test_with_an_empty_emsdirectory_every_named_file_is_from_the_working_folder(tmp_path):
    scene = write_named(tmp_path / "ball", scene=SCENE.replace("$SCENE_DIR/optical</emsdirectory>", "</emsdirectory>"),
                        mat="MATERIAL_ENTRY {\n    BUNDLE_FILENAME = bundles/e.mat.hdf\n    EMISSIVITY_FILE = optical/d.ems\n}\n")
    platform = tmp_path / "plain.platform"
    platform.write_text(PLATFORM)
    top = scene.parent
    assert working_folder_files(scene, platform) == [("bundles/e.mat.hdf", top / "bundles/e.mat.hdf", "ball.mat"),
                                                     ("optical/d.ems", top / "optical/d.ems", "ball.mat")]


def test_a_material_file_that_names_none_or_is_absent_needs_nothing(tmp_path):
    scene = write_named(tmp_path / "ball", mat=MAT)
    platform = tmp_path / "plain.platform"
    platform.write_text(PLATFORM)
    assert working_folder_files(scene, platform) == []
    (scene.parent / "ball.mat").unlink()
    assert working_folder_files(scene, platform) == []


@pytest.fixture(scope="module")
def painted(tmp_path_factory):
    """A library whose sphere's material file names its emissivity file relative to the scene's folder, which is not
    relative to the `emsdirectory` (`$SCENE_DIR/optical`), as Polarization5's does."""
    lib = tmp_path_factory.mktemp("working_folder_mat") / "config_repo"
    folder = lib / "scenes" / "painted"
    write_scene(folder, scene=SCENE)
    (folder / "ball.mat").write_text(PAINTED)
    (folder / "optical").mkdir()
    (folder / "optical" / "ball.ems").write_text(EMS)
    (lib / REL).parent.mkdir(parents=True)
    (lib / REL).write_text(PLATFORM)
    return lib


def painted_spec(lib, working=True):
    spec = authored_spec(lib)
    spec["engine"]["scenes"] = [{"ref": {"name": PAINTED_REL, "content_hash": directory_digest(lib / "scenes" / "painted")},
                                 "offset": [0, 0, 0]}]
    spec["engine"]["motion"]["position"]["xyz"] = [0.0, 0.0, 1000.0]
    spec["engine"]["motion"]["orientation"]["euler"]["angles"] = [0.0, 0.0, 0.0]
    if working:
        spec["engine"]["working_folder"] = [entry(lib, "optical/ball.ems", "scenes/painted/optical/ball.ems")]
    return spec


def test_a_material_file_entry_is_required_resolved_and_copied(tmp_path, painted):
    with pytest.raises(RunSpecError, match=r"ball.mat names optical/ball.ems, which DIRSIG looks for in the job's "
                                           r"working folder; list it in engine.working_folder") as e:
        _resolve(tmp_path, painted_spec(painted, working=False), painted)
    assert e.value.pointer == "/engine/working_folder"
    spec = painted_spec(painted)
    assert schema_errors(spec) == []
    assert _resolve(tmp_path, spec, painted).working_folder == (
        ("optical/ball.ems", painted / "scenes/painted/optical/ball.ems"),)
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    sim = Simulation.from_run_spec(path, painted, tmp_path / "work", SENSORS)
    assert sim.resolved is not None, sim.resolve_error
    in_dir = tmp_path / "work" / "input"
    sim._assemble(in_dir, tmp_path / "work" / "output")
    copy = in_dir / "optical" / "ball.ems"
    assert not copy.is_symlink() and copy.read_text() == EMS
    other = painted_spec(painted)
    other["engine"]["working_folder"][0]["ref"]["content_hash"] = "sha256:" + "1" * 64
    assert run_id(spec, SENSORS) != run_id(other, SENSORS)


@needs_dirsig
def test_a_16_by_16_render_finds_the_emissivity_file_in_the_working_folder(tmp_path, painted):
    from manifold.sim.backend import LocalBackend
    path = tmp_path / "painted.yaml"
    path.write_text(yaml.safe_dump(painted_spec(painted), sort_keys=False))
    before = fingerprint(painted)
    backend = LocalBackend(tmp_path / "work", painted, sensor_library=SENSORS)
    status = wait_for(backend, backend.submit_run(str(path))["run_id"], ("rendered", "failed", "cancelled"), timeout=300)
    assert status["state"] == "rendered", status
    in_dir = next((tmp_path / "work").rglob("input/auror_ref")).parent
    assert (in_dir / "optical" / "ball.ems").read_text() == EMS
    assert fingerprint(painted) == before
    shutil.rmtree(tmp_path / "work", ignore_errors=True)


def test_every_library_scene_needs_nothing():
    # The material-file rule included: every .scene in the library (Tahoe, the demo folders kept there) needs no file in
    # the working folder, so their jobs and run ids are unchanged.
    scenes = sorted(CONFIG_REPO.rglob("*.scene"))
    assert len(scenes) > 1
    for scene in scenes:
        assert working_folder_files(scene, CONFIG_REPO / "platforms" / "AurorNIRDetector" / "AurorNIRDetector.platform") == [], scene


# Files a material file names that the job's scene copy does not hold (round 27). Measured by dry runs: DIRSIG looks for
# an `EMISSIVITY_PROP` `FILENAME` in the working folder and the `emsdirectory` only, and for a `TEMP_SOLVER`
# `IMAGE_FILENAME`, a texture `IMAGE` `FILENAME` or a `MATERIAL_MAP` `IMAGE_FILENAME` in the working folder and the
# `mapdirectory` only (MappedTherm1's `roof_metal_gray.ems` beside its `.scene` with `emsdirectory` `$SCENE_DIR`, and its
# `values.img`, which needs its ENVI header beside it; ChipMaker2's `materials/*.ems`, `maps/texture.png` and
# `maps/material.png`).
UNHELD_SCENE = SCENE.replace("$SCENE_DIR/optical</emsdirectory>", "$SCENE_DIR</emsdirectory>")
UNHELD = """MATERIAL_ENTRY {
    ID = ball
    SURFACE_PROPERTIES {
        EMISSIVITY_PROP_NAME = ClassicEmissivity
        EMISSIVITY_PROP {
            FILENAME = beside.ems
            FILENAME = geometry/linked.ems
        }
        REFLECTANCE_PROP {
            IMAGE_FILENAME = r.png
        }
        TEXTURE_MAP {
            IMAGE_LIST {
                IMAGE {
                    FILENAME = maps/t.png
                    FILENAME = u.png
                }
            }
        }
    }
    TEMP_SOLVER_NAME = MappedTherm
    TEMP_SOLVER {
        IMAGE_FILENAME = v.img
        IMAGE_FILENAME = w.img
        IMAGE_FILENAME = gone.img
        FILENAME = s.txt
    }
    MATERIAL_MAP {
        IMAGE_FILENAME = maps/m.png
        IMAGE_FILENAME = $SCENE_DIR/m.png
        IMAGE_FILENAME = ../up.png
    }
}
"""
CLASSIC = """MATERIAL_ENTRY {
    ID = ball
    NAME = Classic
    DOUBLE_SIDED = TRUE
    SURFACE_PROPERTIES {
        EMISSIVITY_PROP_NAME = ClassicEmissivity
        EMISSIVITY_PROP {
            FILENAME = ball.ems
        }
    }
    RAD_SOLVER_NAME = Simple
    RAD_SOLVER {
        QUALITY = LOW
    }
}
"""
CLASSIC_REL = "scenes/classic/ball.scene"


def test_files_a_material_file_names_that_the_scene_copy_does_not_hold(tmp_path):
    scene = write_scene(tmp_path / "ball", scene=UNHELD_SCENE)
    top = scene.parent
    (top / "ball.mat").write_text(UNHELD)
    (top / "maps").mkdir()
    for rel in ("beside.ems", "geometry/linked.ems", "r.png", "maps/t.png", "u.png", "maps/u.png", "v.img",
                "v.img.hdr", "w.img", "w.hdr", "s.txt", "maps/m.png", "m.png"):
        (top / rel).write_text(rel)
    (tmp_path / "up.png").write_text("outside the scene's folder")
    platform = tmp_path / "plain.platform"
    platform.write_text(PLATFORM)
    # Not listed: a file the copy holds where DIRSIG looks (`geometry/` is linked; `maps/u.png` in the mapdirectory),
    # an unmeasured block (`REFLECTANCE_PROP`), a `TEMP_SOLVER` `FILENAME`, an absent file, a variable, `..`.
    assert working_folder_files(scene, platform) == [(n, top / n, "ball.mat") for n in (
        "beside.ems", "maps/m.png", "maps/t.png", "v.img", "v.img.hdr", "w.hdr", "w.img")]


def test_a_file_the_scene_copy_holds_in_the_emsdirectory_needs_nothing(tmp_path):
    scene = write_scene(tmp_path / "ball", scene=SCENE)                          # emsdirectory $SCENE_DIR/optical
    top = scene.parent
    (top / "ball.mat").write_text(CLASSIC)
    (top / "optical").mkdir()                                                   # named by the .scene: linked in the copy
    (top / "optical" / "ball.ems").write_text(EMS)
    (top / "ball.ems").write_text(EMS)
    platform = tmp_path / "plain.platform"
    platform.write_text(PLATFORM)
    assert working_folder_files(scene, platform) == []


@pytest.fixture(scope="module")
def classic(tmp_path_factory):
    """A library whose sphere's material file names its emissivity file beside the `.scene` in a `ClassicEmissivity`
    `FILENAME`, with the `emsdirectory` `$SCENE_DIR`, as MappedTherm1's does: the scene copy does not hold it."""
    lib = tmp_path_factory.mktemp("working_folder_unheld") / "config_repo"
    folder = lib / "scenes" / "classic"
    write_scene(folder, scene=UNHELD_SCENE)
    (folder / "ball.mat").write_text(CLASSIC)
    (folder / "ball.ems").write_text(EMS)
    (lib / REL).parent.mkdir(parents=True)
    (lib / REL).write_text(PLATFORM)
    return lib


def classic_spec(lib, working=True):
    spec = authored_spec(lib)
    spec["engine"]["scenes"] = [{"ref": {"name": CLASSIC_REL, "content_hash": directory_digest(lib / "scenes" / "classic")},
                                 "offset": [0, 0, 0]}]
    spec["engine"]["motion"]["position"]["xyz"] = [0.0, 0.0, 1000.0]
    spec["engine"]["motion"]["orientation"]["euler"]["angles"] = [0.0, 0.0, 0.0]
    if working:
        spec["engine"]["working_folder"] = [entry(lib, "ball.ems", "scenes/classic/ball.ems")]
    return spec


def test_an_unheld_material_file_is_required_resolved_copied_and_in_the_run_id(tmp_path, classic):
    with pytest.raises(RunSpecError, match=r"ball.mat names ball.ems, which DIRSIG looks for in the job's working "
                                           r"folder; list it in engine.working_folder") as e:
        _resolve(tmp_path, classic_spec(classic, working=False), classic)
    assert e.value.pointer == "/engine/working_folder"
    spec = classic_spec(classic)
    assert schema_errors(spec) == []
    assert _resolve(tmp_path, spec, classic).working_folder == (("ball.ems", classic / "scenes/classic/ball.ems"),)
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    sim = Simulation.from_run_spec(path, classic, tmp_path / "work", SENSORS)
    assert sim.resolved is not None, sim.resolve_error
    in_dir = tmp_path / "work" / "input"
    sim._assemble(in_dir, tmp_path / "work" / "output")
    assert not (in_dir / "ball.ems").is_symlink() and (in_dir / "ball.ems").read_text() == EMS
    assert not (in_dir / "auror_ref" / "ball.ems").exists()                         # the scene copy does not hold it
    other = classic_spec(classic)
    other["engine"]["working_folder"][0]["ref"]["content_hash"] = "sha256:" + "1" * 64
    assert run_id(spec, SENSORS) != run_id(other, SENSORS)


@needs_dirsig
def test_a_16_by_16_render_finds_the_unheld_emissivity_file_in_the_working_folder(tmp_path, classic):
    from manifold.sim.backend import LocalBackend
    path = tmp_path / "classic.yaml"
    path.write_text(yaml.safe_dump(classic_spec(classic), sort_keys=False))
    before = fingerprint(classic)
    backend = LocalBackend(tmp_path / "work", classic, sensor_library=SENSORS)
    status = wait_for(backend, backend.submit_run(str(path))["run_id"], ("rendered", "failed", "cancelled"), timeout=300)
    assert status["state"] == "rendered", status
    in_dir = next((tmp_path / "work").rglob("input/auror_ref")).parent
    assert (in_dir / "ball.ems").read_text() == EMS
    assert fingerprint(classic) == before
    shutil.rmtree(tmp_path / "work", ignore_errors=True)
