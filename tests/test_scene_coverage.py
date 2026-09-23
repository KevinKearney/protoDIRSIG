"""protodirsig.scene_coverage must reproduce the hand-checked Tacoma result (FINDINGS.md, Phase 3)
and fail closed on material kinds it does not understand.

Reads the Tacoma bundle in the DIRSIG install READ-ONLY (skipped if absent); writes only to
pytest's tmp_path.
"""
import os
from pathlib import Path

import pytest

from protodirsig.scene_coverage import scene_coverage

DIRSIG_HOME = Path(os.environ.get("DIRSIG_HOME", Path.home() / "DIRSIG" / "dirsig-2026.38.0.a020954-Linux-x86_64"))
TACOMA_SCENE = DIRSIG_HOME / "Tacoma-08-Apr-2022" / "Tacoma" / "tacoma.scene"


@pytest.mark.skipif(not TACOMA_SCENE.is_file(), reason="Tacoma bundle not present")
def test_tacoma_known_good():
    cov = scene_coverage(TACOMA_SCENE)
    assert cov.mat_file.name == "tacoma.mat"
    assert len(cov.materials) == 42 and not cov.unknown
    assert sum(1 for m in cov.materials if not m.files) == 18            # inline WardBRDF only
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
