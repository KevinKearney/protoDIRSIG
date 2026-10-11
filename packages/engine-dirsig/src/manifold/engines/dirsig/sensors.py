"""Sensor and atmosphere builders from tutorial_dirfm_basics.ipynb (Stages 1 and 3), made importable."""
from pathlib import Path

from dirfm import atmosphere as atmos
from dirfm import platform_sensor as ps

WEATHER = Path("$DIRSIG_HOME/lib/data/weather/mls.wth")   # $DIRSIG_HOME expanded by DIRSIG


def make_camera(spectral_response, focal=500, nx=200, ny=150, pitch=8, image="demo", truth=("Intersection",)):
    """The basics notebook's sensor tree: StaticMount -> GenericInstrument -> one FocalPlane.

    `focal` in mm, `pitch` in microns; 1 Hz IndependentDetectorClock; `truth` collections
    (default: Intersection only, as in the basics notebook).
    """
    tc = ps.TruthCollection("truth")
    for name in truth:
        tc.add_collection(name)
    return ps.PlatformSensorPlugin().add_attachment(
        ps.Attachment(
            ps.StaticMount("Mount").set_rotation("xyz", "degrees", 0, 0, 0)
        ).add_attachment(
            ps.Attachment(
                ps.GenericInstrument("Instrument")
                .add_property(ps.FocalLengthInstrumentProperty(focal))
                .add_focal_plane(
                    ps.FocalPlane("FPA")
                    .set_capture_method(
                        ps.BasicCaptureMethod("Simple")
                        .set_image_file(ps.ImageFile(image))
                        .set_spectral_response(spectral_response)
                    )
                    .set_detector_array(
                        ps.DetectorArray("microns")
                        .set_clock(ps.IndependentDetectorClock(1, 0))
                        .set_elements(nx, ny, pitch, pitch, pitch, pitch, 0, 0, False, True)
                    )
                    .set_truth_collection(tc)
                )
            )
        )
    )


def pan_response():
    """Basics Stage 1: one 0.4-0.8 um panchromatic channel."""
    return (ps.SpectralResponse().set_band("microns", 0.4, 0.8)
            .add_channel(ps.FunctionalChannel("Pan", 0.6, 0.4)))


def rgb_response():
    """Basics Stage 3: 0.4-0.7 um band, R/G/B functional channels (image bands 0, 1, 2)."""
    return (ps.SpectralResponse().set_band("microns", 0.4, 0.7)
            .add_channel(ps.FunctionalChannel("Red", 0.65, 0.10))
            .add_channel(ps.FunctionalChannel("Green", 0.55, 0.10))
            .add_channel(ps.FunctionalChannel("Blue", 0.45, 0.10)))


def build_pan_camera():
    """Exactly tutorial_dirfm_basics.ipynb Stage 1's camera (500 mm, 200x150, 8 um, pan)."""
    return make_camera(pan_response())


def make_rgb_camera(focal=500, nx=320, ny=240, pitch=8, truth=("Intersection",)):
    """tutorial_dirfm_basics.ipynb Stage 3's make_rgb_camera() (plus optional extra truth)."""
    return make_camera(rgb_response(), focal=focal, nx=nx, ny=ny, pitch=pitch, truth=truth)


def simple_atmosphere():
    """Basics Stage 1 atmosphere: BasicAtmospherePlugin + SimpleRadiativeTransfer(260) + mls.wth."""
    return (
        atmos.BasicAtmospherePlugin()
        .set_radiative_transfer(atmos.SimpleRadiativeTransfer(260))
        .set_weather(WEATHER)
    )
