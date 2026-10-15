"""The walker fixture of Cfg A.3 (round 46 C): the Auror tree's defects are reported and the corrected tree passes.

The tree is assembled from `tests/data/closure_fixture/auror/` and the engine-asset library (the README there gives the
source of each file). The held trees do not reproduce A.3's absolute map paths in `tahoe.scene` (its maps are named
relative to `$SCENE_DIR/maps` and both are disabled), so the fixture writes A.3's path into its copy; both maps stay
`enabled="false"`, so the walker reports the paths from the disabled elements without following them (Cfg A.2)."""
import shutil
from pathlib import Path

import pytest

from manifold.engines.dirsig.closure import walk

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "data" / "closure_fixture" / "auror"
LIBRARY = ROOT / "manifold_config_repo"
MAPS = ("material_map_small.pgm", "texture_map_small.pgm")
A3_MAP = "/Users/eoptic/Documents/DIRSIG/scenes/tahoe/maps/{}"
A3_WEATHER = "/home/rxp7504/DIRSIG/MDA/Tahoe_hypersonic/weather/saw.wth"
HELD_PREFIX = "C:/DIRSIG/AUROR/Kevin_DIRSIG/"

# Cfg A.2's Auror mapping, at the fixture's paths.
EXPECTED = {
    "Auror.jsim": "dirsig:sim",
    "AurorNewAtmosphere": "dirsig:atmosphere_db",
    "motion/AurorMotion.ppd": "dirsig:motion",
    "platforms/AurorNIRDetector.platform": "dirsig:platform",
    "scenes/tahoe/geometry/bundles/hypersonic/hypersonic.glist": "dirsig:geometry_list",
    "scenes/tahoe/geometry/bundles/hypersonic/hypersonic.mat": "dirsig:material_db",
    "scenes/tahoe/geometry/bundles/hypersonic/hypersonic.obj": "dirsig:geometry_object",
    "scenes/tahoe/geometry/bundles/hypersonic/ref.txt": "dirsig:other_input",
    "scenes/tahoe/geometry/lists/hypersonic.glist": "dirsig:geometry_list",
    "scenes/tahoe/geometry/lists/terrain.glist": "dirsig:geometry_list",
    "scenes/tahoe/geometry/objects/small.obj": "dirsig:geometry_object",
    **{f"scenes/tahoe/materials/emissivity/{n}.ems": "dirsig:emissivity"
       for n in [f"class{i}" for i in range(1, 10)] + ["gray"]},
    "scenes/tahoe/materials/tahoe.mat": "dirsig:material_db",
    "scenes/tahoe/tahoe.scene": "dirsig:scene",
    "tasks/AurorTask.tasks": "dirsig:tasks",
    "weather/saw.wth": "dirsig:weather",
}


def _assemble(root, corrected):
    root.mkdir(parents=True, exist_ok=True)
    for rel in ("Auror.jsim", "tasks/AurorTask.tasks", "motion/AurorMotion.ppd"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURE / rel, root / rel)
    shutil.copytree(LIBRARY / "scenes" / "tahoe", root / "scenes" / "tahoe")
    (root / "platforms").mkdir()
    shutil.copy2(LIBRARY / "platforms" / "AurorNIRDetector" / "AurorNIRDetector.platform", root / "platforms")
    (root / "weather").mkdir()
    shutil.copy2(LIBRARY / "weather" / "saw.wth", root / "weather")
    shutil.copy2(LIBRARY / "atmosphere" / "AurorNewAtmosphere", root)
    scene = root / "scenes" / "tahoe" / "tahoe.scene"
    text = scene.read_text()
    for name in MAPS:
        assert text.count(f"<filename>{name}</filename>") == 1
        text = text.replace(f"<filename>{name}</filename>",
                            f"<filename>{('$SCENE_DIR/maps/' + name) if corrected else A3_MAP.format(name)}</filename>")
    scene.write_text(text)
    if not corrected:
        (root / "atmospheres").mkdir()
        shutil.copy2(FIXTURE / "atmospheres" / "test.atm", root / "atmospheres")
    return root


# Each assembled tree holds a 47 MB mesh; it is removed after use (pytest keeps three sessions' temporary folders).
@pytest.fixture(scope="module")
def defective(tmp_path_factory):
    root = _assemble(tmp_path_factory.mktemp("auror_defective"), corrected=False)
    yield walk(root, "Auror.jsim")
    shutil.rmtree(root)


@pytest.fixture(scope="module")
def corrected(tmp_path_factory):
    root = _assemble(tmp_path_factory.mktemp("auror_corrected"), corrected=True)
    yield walk(root, "Auror.jsim")
    shutil.rmtree(root)


@pytest.fixture
def tree(tmp_path):
    yield tmp_path / "tree"
    shutil.rmtree(tmp_path / "tree", ignore_errors=True)


def test_the_held_scene_names_its_maps_relative_and_disabled():
    """A.3's first defect is not in the held tree: recorded here, so a change to the library scene shows."""
    text = (LIBRARY / "scenes" / "tahoe" / "tahoe.scene").read_text()
    assert "/Users/" not in text and all(f"<filename>{n}</filename>" in text for n in MAPS)
    assert text.count('enabled="false"') == 2 and "<mapdirectory>$SCENE_DIR/maps</mapdirectory>" in text


def test_defect_one_the_absolute_map_paths_in_tahoe_scene(defective):
    found = {(v.text, v.field) for v in defective.violations
             if v.kind == "absolute" and v.referrer == "scenes/tahoe/tahoe.scene" and not v.enabled}
    assert found == {(A3_MAP.format(MAPS[0]), "materialmap.filename"), (A3_MAP.format(MAPS[1]), "texturemap.filename")}


def test_defect_two_the_absolute_weather_path_in_test_atm(defective):
    assert [(v.kind, v.text, v.field) for v in defective.violations
            if v.referrer == "atmospheres/test.atm" and v.orphan] == [("absolute", A3_WEATHER, "classicdata.filename")]


def test_defect_three_test_atm_is_an_orphan(defective):
    assert defective.orphans == ["atmospheres/test.atm"]
    assert "atmospheres/test.atm" not in {f.path for f in defective.files}


def test_the_defective_tree_reports_those_three_and_nothing_else(defective):
    assert len(defective.violations) == 3 and defective.kinds() == ["absolute"]
    assert not defective.passes
    assert not (defective.unresolved or defective.unroled or defective.role_conflicts or defective.install)
    assert {f.path: f.role for f in defective.files} == EXPECTED


def test_the_corrected_tree_passes(corrected):
    assert corrected.passes and corrected.clean
    assert not (corrected.violations or corrected.orphans or corrected.unresolved or corrected.install)
    assert {f.path: f.role for f in corrected.files} == EXPECTED


def test_the_held_simulation_file_names_five_absolute_windows_paths(tree):
    """Cfg A.3's fourth row: the held `.jsim` as received. Its five references are reported and not followed; the
    atmosphere database, named bare, resolves beside it."""
    root = _assemble(tree, corrected=True)
    shutil.copy2(FIXTURE / "AurorSimulation_held.jsim", root)
    w = walk(root, "AurorSimulation_held.jsim")
    assert sorted((v.kind, v.field) for v in w.violations) == sorted(
        ("absolute", f) for f in ("BasicPlatform.platform_filename", "BasicPlatform.motion_filename",
                                  "BasicPlatform.tasks_filename", "ThermWeather.filename", "scene_list.inputs"))
    assert all(v.text.startswith(HELD_PREFIX) for v in w.violations)
    assert {f.path for f in w.files} == {"AurorSimulation_held.jsim", "AurorNewAtmosphere"}


def test_the_held_layout_needs_a_dotdot_segment(tree):
    """The held entry sits in `jsims/` with every other file one folder up; DIRSIG resolves the `.jsim`'s names against
    the folder it runs in, so a relative form of that layout names `../`, which Cfg 2.3 rejects."""
    root = _assemble(tree, corrected=True)
    (root / "jsims").mkdir()
    shutil.move(root / "AurorNewAtmosphere", root / "jsims")
    text = (FIXTURE / "AurorSimulation_held.jsim").read_text().replace(HELD_PREFIX, "../")
    (root / "jsims" / "AurorSimulation.jsim").write_text(text)
    (root / "Auror.jsim").unlink()
    w = walk(root, "jsims/AurorSimulation.jsim")
    assert w.kinds() == ["dotdot"] and len(w.violations) == 5
    assert {f.path for f in w.files} >= {"platforms/AurorNIRDetector.platform", "jsims/AurorNewAtmosphere"}
