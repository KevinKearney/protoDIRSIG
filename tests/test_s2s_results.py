"""The space-to-space results file (`docs/data/s2s_results.jsonl`, written by `scripts/s2s_measure.py`): the closed-form
cases hold to the residuals measured.

Engine-free: the records are read, nothing is rendered. Each tolerance below is the largest residual the committed
records show for that case, rounded up in its third significant digit (docs/Space_to_space_characterization.md,
"Measurement harness and results file"), so a re-measured record that moves further from the closed form fails.
"""
import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("s2s_measure", ROOT / "scripts" / "s2s_measure.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

RECORDS = {r["spec"]: r for r in m.load_results()}

# Tolerances: the largest |measured / closed form - 1| among round 32's records for each case, rounded up in the third
# significant digit (the residuals are listed in docs/Space_to_space_characterization.md, "Measurement harness and
# results file (round 32)").
TOL_FLUX_PLATE = 0.00816       # 20 m plate, 12.5 to 100 km: largest at 100 km (8.159e-3, seed-to-seed scatter, round 30)
TOL_R2 = 0.00721               # equivalent footprint x range^2 against 25 km: largest at 100 km (7.202e-3)
TOL_EXPOSURE = 1.34e-15        # 1 and 20 ms against 5 ms: the image scales exactly (1.332e-15)
TOL_LOOK = 0.000803            # family I, 30 and 60 degrees: largest at 30 (8.021e-4)
TOL_LOOK_BACKGROUND = 0.000822  # family II look group, 15 to 60 degrees: largest at 30 (8.214e-4)
TOL_SUN = 4.54e-05             # family I, solar zenith 30 and 60 degrees: largest at 60 (4.540e-5)
TOL_PHASE = 0.00982            # family III, 10 m sphere, 0 to 150 degrees: largest at 150 (9.812e-3)
TOL_PERIOD = 0.00362           # family II, bar period 0 to 60 degrees: largest at 15 (3.618e-3)
TOL_BAR = 0.000154             # family III, bar level under the Sun at 0 to 75 degrees: largest at 75 (1.534e-4)


def rec(name):
    assert name in RECORDS, f"{name} has no record in {m.RESULTS.relative_to(ROOT)}"
    return RECORDS[name]


def flux(name):
    """(equivalent full pixels, expected footprint) of a record's flux closure."""
    r = rec(name)
    assert r["method"] == "flux_closure"
    return r["measured"], r["expected"]


def total(name):
    """The image sum (e-/m^2): the flux closure's measured value times the full-pixel signal."""
    r = rec(name)
    return r["measured"] * r["full_pixel"]


HYP = "s2s-hyperresolved-r{r}km-v0mps-e{e}ms-l{l}-z{z}-d0"
RANGES = ("12p5", "25", "50", "100")


def test_results_file_checks():
    assert m.check() == []


@pytest.mark.parametrize("r", RANGES)
def test_resolved_plate_flux_closure(r):
    got, want = flux(HYP.format(r=r, e=5, l=0, z=0))
    assert abs(got / want - 1) <= TOL_FLUX_PLATE


@pytest.mark.parametrize("r", ("12p5", "50", "100"))
def test_resolved_footprint_scales_as_range_squared(r):
    """The equivalent footprint (flux over the full-pixel signal) times the range squared is the same at every range
    of the resolved regime, against 25 km."""
    km = {"12p5": 12.5, "25": 25.0, "50": 50.0, "100": 100.0}
    a, _ = flux(HYP.format(r=r, e=5, l=0, z=0))
    b, _ = flux(HYP.format(r="25", e=5, l=0, z=0))
    assert abs(a * km[r] ** 2 / (b * 25.0 ** 2) - 1) <= TOL_R2


@pytest.mark.parametrize("e", (1, 20))
def test_exposure_scaling(e):
    ratio = total(HYP.format(r=25, e=e, l=0, z=0)) / total(HYP.format(r=25, e=5, l=0, z=0))
    assert abs(ratio / (e / 5) - 1) <= TOL_EXPOSURE


@pytest.mark.parametrize("look", (30, 60))
def test_look_angle_scaling(look):
    """A Lambertian plate seen `look` degrees off its normal: the signal follows the projected area, cos(look)."""
    ratio = total(HYP.format(r=25, e=5, l=look, z=0)) / total(HYP.format(r=25, e=5, l=0, z=0))
    assert abs(ratio / math.cos(math.radians(look)) - 1) <= TOL_LOOK


@pytest.mark.parametrize("z", (30, 60))
def test_sun_zenith_scaling(z):
    ratio = total(HYP.format(r=25, e=5, l=0, z=z)) / total(HYP.format(r=25, e=5, l=0, z=0))
    assert abs(ratio / math.cos(math.radians(z)) - 1) <= TOL_SUN


PHASES = ("a0-l0-z0", "a20-l10-z10", "a40-l20-z20", "a60-l30-z30", "a80-l40-z40", "a100-l50-z50", "a120-l60-z60",
          "a135-l67p5-z67p5", "a150-l75-z75", "a60-l0-z60", "a60-l60-z0")


@pytest.mark.parametrize("tail", PHASES)
def test_sphere_phase_function(tail):
    """The hyperresolved 10 m sphere follows the Lambertian phase function, however the angle splits between the
    look and the Sun."""
    got, want = flux(f"s2s3-phase-hyperresolved-{tail}")
    assert abs(got / want - 1) <= TOL_PHASE


@pytest.mark.parametrize("look", (15, 30, 45, 60))
def test_look_angle_scaling_against_a_background(look):
    """Family II's look group: the plate's rows follow cos(look) up to 60 degrees (at 75 the line of sight behind the
    plate leaves the background, docs/Space_to_space_characterization.md, round 30)."""
    ratio = total(f"s2s2-look-l{look}") / total("s2s2-look-l0")
    assert abs(ratio / math.cos(math.radians(look)) - 1) <= TOL_LOOK_BACKGROUND


def also(name, method):
    return next(x for x in rec(name)["also"] if x["method"] == method)


@pytest.mark.parametrize("look", (0, 15, 30, 45, 60))
def test_background_bar_period(look):
    assert abs(also(f"s2s2-look-l{look}", "background_period")["ratio"] - 1) <= TOL_PERIOD


@pytest.mark.parametrize("z", (0, 30, 60, 75))
def test_background_follows_cos_solar_zenith(z):
    assert abs(also(f"s2s3-background-z{z}", "bar_level")["ratio"] - 1) <= TOL_BAR
