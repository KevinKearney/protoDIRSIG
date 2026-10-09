"""Absolute electron count of a generated `.platform`, against an analytic value computed from the job's inputs.

Scene: a Lambertian ground plane of reflectance rho (ClassicEmissivity, specularity 0, rho = 1 - emissivity)
under DIRSIG's UniformAtm (BasicAtmosphere `uniformradiativetransfer`: unit path transmission, zero path
radiance), sky fraction 0, so the whole `hemisphereirradiance` E is the sun's scalar irradiance (normal to the
sun; DIRSIG brdfgen manual), and a FixedEphemeris sun. The irradiance is a job input, not DIRSIG solar data.

Expected value, from the sensor-spec's own numbers and curves (not from the generated platform):

    L = rho E cos(zenith) / pi                         E in W/(cm2 um) (the unit DIRSIG reads), L per m2 here
    G# = (1 + 4 F#^2) / (tau pi)                       DIRSIG's definition (basicplatform_plugin.html)
    Q = t * integral L / G# * R(lambda) * lambda / (h c) d lambda      electrons per m2 of focal plane

with R the unit-peak shape x QE x optics curve and tau the scalar throughput (1 when the curve is folded in).
The image's `data units` are electrons/(m^2): electrons per pixel are Q x element area. The textbook 4 F#^2 would
be 1.5-1.9 % off for these sensors; the renders agree to 1e-4.
"""
import math
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest
import yaml
from scipy.constants import c, h

from protodirsig.platform_gen import render_platform
from protodirsig.run_spec import load_run_spec, load_sensor_spec

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "sensors"
TEMPLATE = ROOT / "config_repo" / "platforms" / "AurorNIRDetector" / "AurorNIRDetector.platform"
DIRSIG_HOME = Path(os.environ.get("DIRSIG_HOME", Path.home() / "DIRSIG" / "dirsig-2026.38.0.a020954-Linux-x86_64"))
WEATHER = DIRSIG_HOME / "lib" / "data" / "weather" / "mls.wth"     # required by BasicAtmosphere; no effect here


def _dirsig_on_path():
    os.environ.setdefault("DIRSIG_HOME", str(DIRSIG_HOME))
    if (DIRSIG_HOME / "bin").is_dir() and str(DIRSIG_HOME / "bin") not in os.environ["PATH"].split(os.pathsep):
        os.environ["PATH"] = f"{DIRSIG_HOME / 'bin'}{os.pathsep}{os.environ['PATH']}"
    return shutil.which("dirsig5") and shutil.which("scene2hdf") and WEATHER.is_file()


needs_dirsig = pytest.mark.skipif(not (TEMPLATE.is_file() and _dirsig_on_path()), reason="DIRSIG not present")


def render_plane(work, sensor, entry_id, E, rho, zenith, n=8):
    """Mean of an n x n render of the plane, nadir view from 1 km, with the platform generated for `entry_id`."""
    from dirfm import DIRSIG, SCENE, frames, materials
    from dirfm import atmosphere as atmos
    from dirfm import object_database as odb
    from dirfm.emissivity import Emissivity
    from dirfm.ephemeris import FixedEphemerisPlugin
    from dirfm.platform_motion import PlatformPosition
    from dirfm.tasks import TASKS

    from protodirsig.platform_ref import PlatformFilesPlugin
    from protodirsig.simulation import _run_dirsig

    inp = work / "input"
    inp.mkdir(parents=True)
    settings = [{**load_run_spec(ROOT / "run_specs" / "auror_ref.yaml")["descriptor"]["settings"][0],
                 "entry_id": entry_id, "roi": {"Width": n, "Height": n, "OffsetX": None, "OffsetY": None}}]
    platform = render_platform(TEMPLATE, load_sensor_spec(LIB, sensor), entry_id, settings, 10, LIB,
                               inp / "plane.platform").path
    pos = PlatformPosition(rotationorder="xyz", angularunits="radians")
    pos.add_entry(0.0, [0.0, 0.0, 1000.0], [0.0, 0.0, math.pi])
    motion = pos.write({"root": inp}, name="plane.ppd")
    tasks = TASKS(datetime(2009, 7, 27, 19, 29, 32, tzinfo=timezone.utc))
    tasks.add_start_stop(0.0, 0.0)
    tasks.write({"root": inp}, name="plane.tasks")
    grey = (materials.Material("grey", False).set_rad_solver(materials.ClassicRadiationSolver())
            .add_surface_properties(materials.ClassicEmissivitySurfaceProperty(
                Emissivity("grey.ems").add_curve([0.2, 20.0], [1.0 - rho, 1.0 - rho]), 0)))
    scene = (SCENE("plane").set_origin(frames.GeodeticFrame(39.0, -120.0, 0))
             .add_geometry("world", odb.ObjectDatabase().add_object(odb.GroundPlane([0, 0, 0], grey)))
             .set_properties("vis", "nir", "swir"))
    scene.add_material(grey)
    job = DIRSIG(inp, work / "output")
    job.add_plugin(PlatformFilesPlugin(platform, motion, inp / "plane.tasks"))
    job.add_plugin(atmos.BasicAtmospherePlugin().set_weather(WEATHER)
                   .set_radiative_transfer(atmos.UniformRadiativeTransfer(float(E), 0)))
    job.add_plugin(FixedEphemerisPlugin(solar_zenith=zenith, solar_azimuth=0, lunar_zenith=170, lunar_azimuth=0,
                                        lunar_fraction=0))
    job.add_scene(scene, [0, 0, 0])
    job.set_seed(7)
    err, _ = _run_dirsig(job)
    assert err is None, err
    image = next((work / "output").rglob("AurorNIROutput.img"))                 # the template's image basename
    assert "data units = electrons/(m^2)" in Path(f"{image}.hdr").read_text()
    return np.fromfile(image, dtype="<f8")


def _curve(name):
    rows = [ln for ln in (LIB / name).read_text().splitlines() if ln and not ln.startswith("#")][1:]
    a = np.array([[float(v) for v in r.split(",")] for r in rows])
    return a[:, 0], a[:, 1]


def expected(sensor, E, rho, zenith, t):
    """Electrons per m2 of focal plane, from the sensor-spec's values and curve files (see module docstring)."""
    entry = yaml.safe_load((LIB / sensor).read_text())["sensor"]["entries"][0]
    opt, ch = entry["optics"], entry["focal_planes"][0]["channels"][0]
    wl = np.arange(0.41, 2.0, 1e-5)                                      # um, inside the job bandpass
    m = ch["srf_model"]
    if m["kind"] == "gaussian":
        sigma = m["fwhm"] / (2.0 * math.sqrt(2.0 * math.log(2.0)))
        R = np.exp(-0.5 * ((wl - m["center"]) / sigma) ** 2)
    else:
        R = (np.abs(wl - m["center"]) <= m["width"] / 2.0).astype(float)
    if "qe_reference" in ch:
        R = R * np.interp(wl, *_curve(ch["qe_reference"]["name"]))
    tau = opt["throughput_in_band"]["value"]
    if "throughput_reference" in opt:
        R, tau = R * np.interp(wl, *_curve(opt["throughput_reference"]["name"])), 1.0
    F = opt["focal_length"] / opt["aperture_diameter"]
    G = (1.0 + 4.0 * F ** 2) / (tau * math.pi)
    L = rho * E * 1e4 * math.cos(math.radians(zenith)) / math.pi        # W/(m2 sr um)
    return t * np.trapezoid(L / G * R * (wl * 1e-6) / (h * c), wl)


@needs_dirsig
@pytest.mark.parametrize("sensor, entry_id, E, rho, zenith", [
    ("auror-nir.yaml", "auror-nir", 1.0, 0.5, 0.0),                                         # scalar optics, gaussian
    ("auror-nir.yaml", "auror-nir", 0.2, 0.3, 60.0),                                        # cos(zenith)
    ("synthetic_600_200_vis_1920.yaml", "synthetic-600-200-vis-1920", 0.15, 0.4, 0.0),      # optics and QE curves
], ids=["auror-nir", "auror-nir-zenith60", "synthetic-vis"])
def test_electrons_match_the_analytic_value(tmp_path, sensor, entry_id, E, rho, zenith):
    img = render_plane(tmp_path, sensor, entry_id, E, rho, zenith)
    assert img.std() <= 1e-9 * img.mean()                              # uniform plane, uniform image
    t = load_run_spec(ROOT / "run_specs" / "auror_ref.yaml")["descriptor"]["settings"][0]["exposure_time"]["value"]
    assert img.mean() == pytest.approx(expected(sensor, E, rho, zenith, t), rel=1e-3)
