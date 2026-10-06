"""protodirsig.scene_coverage must reproduce the hand-checked Tacoma result (FINDINGS.md, Phase 3)
and fail closed on material kinds it does not understand.

Reads the Tacoma bundle in the DIRSIG install and the received AUROR_ref tree READ-ONLY (each
skipped if absent); writes only to pytest's tmp_path.
"""
import math
import os
from pathlib import Path

import pytest

from protodirsig.scene_coverage import scene_coverage

DIRSIG_HOME = Path(os.environ.get("DIRSIG_HOME", Path.home() / "DIRSIG" / "dirsig-2026.38.0.a020954-Linux-x86_64"))
TACOMA_SCENE = DIRSIG_HOME / "Tacoma-08-Apr-2022" / "Tacoma" / "tacoma.scene"
AUROR_SCENE = Path(__file__).resolve().parents[1] / "AUROR_ref" / "tahoe.scene"   # gitignored


@pytest.mark.skipif(not TACOMA_SCENE.is_file(), reason="Tacoma bundle not present")
def test_tacoma_known_good():
    cov = scene_coverage(TACOMA_SCENE)
    assert cov.mat_file.name == "tacoma.mat"
    scene_mats = [m for m in cov.materials if m.source == cov.mat_file]
    assert len(scene_mats) == 42 and not cov.unknown
    assert sum(1 for m in scene_mats if not m.files) == 18               # inline WardBRDF only
    # targets.glist's two bundles (Phase 5): tribar (a MATERIAL_MAP proxy over two Ward
    # materials) and helicopter (three Ward greys) -- all wavelength-independent.
    assert sorted(p.parent.name for p in cov.bundle_mats) == ["helicopter", "tribar"]
    bundle = [m for m in cov.materials if m.source != cov.mat_file]
    assert len(bundle) == 6 and all(m.span == (-math.inf, math.inf) for m in bundle)
    assert cov.span == (0.4, 0.78)                                       # the Phase 3 finding
    assert cov.covers(0.4, 0.7)                                          # the RGB band used
    gaps = {m.name for m in cov.gaps(0.4, 0.9)}                          # 'vis,nir' is not backed
    assert gaps and all(any(f in ("lt_blue_panel.ems", "orange_panel.ems", "dark_orange_panel.ems")
                            for f in m.files) for m in cov.gaps(0.4, 0.9)), gaps
    assert not cov.covers(5.0, 50.0)            # the band dirfm's vacuous check waved through
    assert {(lo, hi) for _, _, lo, hi in cov.texture_bands} == {(0.4, 0.7)}


def test_fails_closed_on_unknown_property(tmp_path):
    (tmp_path / "x.mat").write_text(
        "MATERIAL_ENTRY {\n    ID = 1\n    NAME = mystery\n"
        "    SURFACE_PROPERTIES {\n        REFLECTANCE_PROP_NAME = SomethingNew\n    }\n}\n")
    (tmp_path / "x.scene").write_text("<classicscene><matfilename>$SCENE_DIR/x.mat</matfilename></classicscene>")
    cov = scene_coverage(tmp_path / "x.scene")
    assert cov.unknown and cov.span is None and not cov.covers(0.5, 0.6)


def test_missing_file_is_unknown(tmp_path):
    (tmp_path / "x.mat").write_text(
        "MATERIAL_ENTRY {\n    ID = 1\n    NAME = gone\n    SURFACE_PROPERTIES {\n"
        "        EMISSIVITY_PROP_NAME = ClassicEmissivity\n        EMISSIVITY_PROP {\n"
        "            FILENAME = nope.ems\n        }\n    }\n}\n")
    (tmp_path / "x.scene").write_text("<classicscene><matfilename>$SCENE_DIR/x.mat</matfilename></classicscene>")
    assert not scene_coverage(tmp_path / "x.scene").covers(0.5, 0.6)


@pytest.mark.skipif(not AUROR_SCENE.is_file(), reason="AUROR_ref tree not present")
def test_auror_bundle_material_is_seen():
    """Gidder_mat lives only in the hypersonic bundle's hypersonic.mat, reached through
    geometrylistinclude lists/hypersonic.glist -> bundles/hypersonic/hypersonic.glist."""
    cov = scene_coverage(AUROR_SCENE)
    assert len([m for m in cov.materials if m.source == cov.mat_file]) == 10 and not cov.unknown
    gidder = [m for m in cov.materials if m.id == "Gidder_mat"]
    assert len(gidder) == 1 and gidder[0].source.name == "hypersonic.mat"
    assert gidder[0].files == {"ref.txt": (0.4, 3.0, 1)}
    assert cov.span == (0.4, 3.0) and cov.covers(0.41, 2.0) and not cov.covers(0.3, 2.0)
    assert cov.texture_bands == []                          # its only texture map is disabled


def _bundle_scene(tmp_path, bundle_mat, ref_txt="0.5 0.1\n1.5 0.1\n"):
    b = tmp_path / "geometry" / "bundles" / "b"
    b.mkdir(parents=True)
    (tmp_path / "geometry" / "lists").mkdir()
    (tmp_path / "s.mat").write_text("")
    (b / "b.glist").write_text('<geometrylist><object search_paths="local"><localmaterials>b.mat'
                               '</localmaterials></object></geometrylist>')
    if bundle_mat is not None:
        (b / "b.mat").write_text(bundle_mat)
    (b / "r.txt").write_text(ref_txt)
    (tmp_path / "geometry" / "lists" / "l.glist").write_text(
        "<geometrylist><object><basegeometry><glist><filename>bundles/b/b.glist</filename>"
        "</glist></basegeometry></object></geometrylist>")
    (tmp_path / "x.scene").write_text(
        "<classicscene><gdbdirectory>$SCENE_DIR/geometry</gdbdirectory>"
        '<geometrylist><geometrylistinclude enabled="true">lists/l.glist</geometrylistinclude></geometrylist>'
        "<matfilename>$SCENE_DIR/s.mat</matfilename></classicscene>")
    return tmp_path / "x.scene"


SIMPLE = ("MATERIAL_ENTRY {\n    ID = v\n    NAME = v\n    SURFACE_PROPERTIES {\n"
          "        REFLECTANCE_PROP_NAME = SimpleReflectance\n        REFLECTANCE_PROP {\n"
          "            TXT_FILENAME = r.txt\n        }\n    }\n}\n")


def test_bundle_through_include_chain(tmp_path):
    cov = scene_coverage(_bundle_scene(tmp_path, SIMPLE))
    assert [m.id for m in cov.materials] == ["v"] and cov.span == (0.5, 1.5)
    assert cov.covers(0.6, 1.4) and not cov.covers(0.4, 1.4)


def test_missing_bundle_mat_fails_closed(tmp_path):
    cov = scene_coverage(_bundle_scene(tmp_path, None))
    assert cov.unknown and not cov.covers(0.6, 1.4)


def test_material_map_target_missing_fails_closed(tmp_path):
    proxy = ("MATERIAL_ENTRY {\n    ID = p\n    MATERIAL_MAP {\n        IMAGE_FILENAME = m.png\n"
             "        LUT {\n            0:v\n            255:gone\n        }\n    }\n}\n")
    cov = scene_coverage(_bundle_scene(tmp_path, SIMPLE + proxy))
    p = next(m for m in cov.materials if m.id == "p")
    assert "r.txt" in p.files and p.unknown and not cov.covers(0.6, 1.4)
