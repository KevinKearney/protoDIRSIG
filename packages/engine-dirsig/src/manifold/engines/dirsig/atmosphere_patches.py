"""dirfm's NewAtmosphere plugin and MODTRAN-tape backend, made usable.

As shipped, every setter on `dirfm.atmosphere.NewAtmospherePlugin` and `ModtranTapeBackend`
raises AttributeError: `_FrozenAttrs` forbids new attributes after `__init__`, and those
`__init__`s never create the attributes the setters assign. `set_multiple_scattering` also
validates against `["None", "Isacc", "Distort"]`, misspelling DIRSIG's `Isaac` and `Disort`
(docs/atm_backends.html).
Upstream fix for dirfm: initialise these attributes to None in the two `__init__`s, and
correct the two names.

`BasicAtmosphereFilePlugin` names an existing `.atm` (a uniform atmosphere's, written by `basic_atmosphere`).
"""
from pathlib import Path

from dirfm.atmosphere import BaseAtmospherePlugin, ModtranTapeBackend, NewAtmospherePlugin
from dirfm.utilities.paths import relativize_path

MULTIPLE_SCATTERING = ("None", "Isaac", "Disort")          # DIRSIG's spelling (atm_backends.html)


class PatchedModtranTapeBackend(ModtranTapeBackend):
    """`ModtranTapeBackend` whose setters work and whose multiple-scattering names are DIRSIG's."""

    def __init__(self):
        super().__init__()
        self._profile = self._atmo_model = self._multiple_scattering = self._boudary_aerosol_model = None

    def set_multiple_scattering(self, model, **parameters):
        assert model in MULTIPLE_SCATTERING, f"Expected one of {MULTIPLE_SCATTERING}, got {model!r}"
        self._multiple_scattering = {"type": model, "parameters": parameters}
        return self


class PatchedNewAtmospherePlugin(NewAtmospherePlugin):
    """`NewAtmospherePlugin(fname)` over an existing database, with working `set_info`/`set_backend`."""

    def __init__(self, fname):
        super().__init__(fname)
        self._info = self._backend = None


class BasicAtmosphereFilePlugin(BaseAtmospherePlugin):
    """`BasicAtmosphere` over an existing `.atm` (the job's file written by `basic_atmosphere.write_atm`). dirfm's
    `BasicAtmospherePlugin` writes its own `.atm` from dirfm objects (weather path relativized into the job, turbulence
    always enabled, no ephemeris); this one names the file as it is, as `platform_ref.PlatformFilesPlugin` does."""

    def __init__(self, atm):
        super().__init__()
        self._atm = Path(atm)

    def prepare(self, dirs):
        assert self._atm.is_file(), f"missing atmosphere input: {self._atm}"

    def get_plugin_name(self):
        return "BasicAtmosphere"

    def get_plugin_inputs(self, dirs=None):
        name = relativize_path(dirs, self._atm, "root") if dirs is not None else self._atm.as_posix()
        return {"atmosphere_filename": name}
