"""A BasicAtmosphere `.atm` written from a run spec's stated values: `engine.atmosphere` of plugin `basic` with
`uniform` (proposed).

DIRSIG's BasicAtmosphere plugin reads a DIRSIG 4 era `.atm` file (`docs/basicatm_plugin.html` in the installation). The
`uniform` member states what the generator writes into it, and nothing else:

  radiative_transfer   <uniformradiativetransfer>: hemisphere_irradiance (spectrally constant, DIRSIG's units for
                       UniformAtm) and sky_fraction (the diffuse share, 0 to 1); no extinction and no path radiance
  weather              <uniformweather><classicdata>: install_file, a weather file shipped with the DIRSIG installation,
                       written as `$DIRSIG_HOME/lib/data/weather/<install_file>` (DIRSIG expands the variable)
  fixed_ephemeris      optional <ephemeris><fixed units=...>: solar_zenith and solar_azimuth in `units` (radians or
                       degrees). DIRSIG then sets up a FixedEphemeris from the file; a SpiceEphemeris plugin in the
                       same job replaces it (measured with DensityMap1), so the loader refuses `engine.ephemeris` beside it

Not written: `<turbulence>` (no first target's output depends on it: DensityMap1's demo renders byte-identical without
it), `<metadata>`, the simple and classic radiative-transfer forms, lunar values. The file is written in that element
order with each number as stated (an integer as an integer, a float in its shortest round-trip form), so a `.atm` with
the same values renders byte-identically to the demo's (DensityMap1, measured).

Imports: the standard library and `lxml` (no engine package); the plugin that names the file in the job is
`atmosphere_patches.BasicAtmosphereFilePlugin`.
"""
from pathlib import Path

import lxml.etree as et

WEATHER_DIR = "$DIRSIG_HOME/lib/data/weather"
ANGLE_UNITS = ("radians", "degrees")


def _text(value):
    """A stated number as DIRSIG reads it: an int as is, a float in its shortest round-trip form."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"expected a number, got {value!r}")
    return str(value) if isinstance(value, int) else repr(float(value))


def weather_path(install_file):
    return f"{WEATHER_DIR}/{install_file}"


def write_atm(uniform, path):
    """Write the `.atm` for an `engine.atmosphere.uniform` block to `path`. Returns `path`."""
    root = et.Element("atmosphericconditions")
    classic = et.SubElement(et.SubElement(root, "uniformweather"), "classicdata")
    et.SubElement(classic, "filename").text = weather_path(uniform["weather"]["install_file"])
    fixed = uniform.get("fixed_ephemeris")
    if fixed is not None:
        node = et.SubElement(et.SubElement(root, "ephemeris"), "fixed", units=fixed["units"])
        et.SubElement(node, "solarzenith").text = _text(fixed["solar_zenith"])
        et.SubElement(node, "solarazimuth").text = _text(fixed["solar_azimuth"])
    rt = uniform["radiative_transfer"]
    node = et.SubElement(root, "uniformradiativetransfer")
    et.SubElement(node, "hemisphereirradiance").text = _text(rt["hemisphere_irradiance"])
    et.SubElement(node, "skyfraction").text = _text(rt["sky_fraction"])
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    et.ElementTree(root).write(str(path), pretty_print=True)
    return path


def read_atm(path):
    """The `uniform` block a uniform-radiative-transfer `.atm` states, parsed back (the members `write_atm` writes).
    Raises ValueError for a file this module would not write (another radiative-transfer form, a weather file outside
    the installation's weather folder, a fixed ephemeris without units other than DIRSIG's default radians)."""
    root = et.parse(str(path)).getroot()
    rt = root.find("uniformradiativetransfer")
    if rt is None:
        raise ValueError(f"{Path(path).name}: no <uniformradiativetransfer>")
    name = (root.findtext("uniformweather/classicdata/filename") or "").strip()
    if not name.startswith(WEATHER_DIR + "/"):
        raise ValueError(f"{Path(path).name}: weather {name!r} is not an installation weather file")
    out = {"radiative_transfer": {"hemisphere_irradiance": _number(rt.findtext("hemisphereirradiance")),
                                  "sky_fraction": _number(rt.findtext("skyfraction"))},
           "weather": {"install_file": name[len(WEATHER_DIR) + 1:]}}
    fixed = root.find("ephemeris/fixed")
    if fixed is not None:
        out["fixed_ephemeris"] = {"units": fixed.get("units", "radians"),
                                  "solar_zenith": _number(fixed.findtext("solarzenith")),
                                  "solar_azimuth": _number(fixed.findtext("solarazimuth"))}
    return out


def _number(text):
    text = (text or "").strip()
    try:
        return int(text)
    except ValueError:
        return float(text)


def uniform_problem(uniform):
    """Why an `engine.atmosphere.uniform` block cannot be written, or None. The schema states the shape; this states the
    rule a reader needs the reason for: a uniform atmosphere names its weather."""
    weather = uniform.get("weather") if isinstance(uniform, dict) else None
    if not isinstance(weather, dict) or not weather.get("install_file"):
        return ("has no weather values: BasicAtmosphere reads its uniform weather from the .atm file and DIRSIG "
                "refuses a .atm without one ('Expected a <filename> in uniform weather'); state weather.install_file, "
                "a weather file of the DIRSIG installation (the demos use mls.wth)")
    return None
