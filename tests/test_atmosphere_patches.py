"""protodirsig.atmosphere_patches must make dirfm's NewAtmosphere plugin emit the jsim stanza
DIRSIG expects. Writes only to pytest's tmp_path.
"""
import pytest

from dirfm.atmosphere import ModtranTapeBackend
from protodirsig.atmosphere_patches import PatchedModtranTapeBackend, PatchedNewAtmospherePlugin


def test_unpatched_setters_still_fail():
    """Guards the reason the patch exists; if this starts passing, dirfm was fixed upstream."""
    with pytest.raises(AttributeError):
        ModtranTapeBackend().set_profile("p")


def test_patched_plugin_emits_stanza(tmp_path):
    db = tmp_path / "AurorNewAtmosphere"
    db.write_bytes(b"")
    backend = (PatchedModtranTapeBackend().set_profile("New Profile").set_atmospheric_model("MidLatitudeSummer")
               .set_boundary_aerosol_model("RuralVis23Km").set_multiple_scattering("Isaac"))
    plugin = PatchedNewAtmospherePlugin(db).set_backend(backend).set_info("", "", "", "")
    assert plugin.get_plugin_name() == "NewAtmosphere"
    assert plugin.get_plugin_inputs({"root": tmp_path}) == {
        "info": {"name": "", "author": "", "organization": "", "description": ""},
        "backend": {
            "name": "modtran_tape",
            "modtran_profile": "New Profile",
            "tape5_parameters": {
                "atmospheric_model": "MidLatitudeSummer",
                "multiple_scattering": {"type": "Isaac", "parameters": {}},
                "boundary_aerosol_model": {"type": "RuralVis23Km", "parameters": {}},
            },
        },
        "hdf_filename": "AurorNewAtmosphere",          # relative: inside the job's root
    }


def test_multiple_scattering_uses_dirsig_names():
    b = PatchedModtranTapeBackend()
    b.set_multiple_scattering("Disort", streams=16)
    assert b._multiple_scattering == {"type": "Disort", "parameters": {"streams": 16}}
    with pytest.raises(AssertionError):
        b.set_multiple_scattering("Isacc")                # dirfm's misspelling is rejected
