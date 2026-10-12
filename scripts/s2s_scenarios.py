#!/usr/bin/env python3
"""Space-to-space scenario families I and II: `run-spec/1` documents for parameter grids, from existing members only.

    python scripts/s2s_scenarios.py            (re)write the target scene and the family's run specs
    python scripts/s2s_scenarios.py --check    regenerate in memory, validate every spec, compare with the committed
                                               files; list every difference, exit 1 if any
    python scripts/s2s_scenarios.py --list     print each grid point: name, run id, the derived geometry

What it writes (docs/Space_to_space_characterization.md is the account):
- `manifold_config_repo/scenes/s2s_targets/`: a generated target scene, the family's only new library asset. No DIRSIG
  demo or install scene gives a usable space-to-space geometry for the layered form (the document names the nearest), so
  the scene is written here from stated numbers: square Lambertian plates (SimpleReflectance, reflectance `REFLECTANCE`,
  normal +z), each with a black backstop (`BACKSTOP`: a 400 m square of reflectance 0, 10 m behind it), and nothing
  else. The backstop is the measured handling of an unresolved object against space: DIRSIG spends no samples in a
  pixel whose rays all leave the scene, so a sub-pixel plate with nothing behind it renders zero whatever the
  convergence settings or `::IMPORTANT::` (docs/Space_to_space_characterization.md); behind a surface the pixel is
  sampled. Reflectance 0 and no emission in this band (CONOPS and Guide section 9) keep the background exactly zero, as
  space would be. The plates are kilometres apart so that one frame holds one plate. A plate's class is its size against the pixel footprint at the
  grid's ranges; `unresolved` is named `::IMPORTANT::` (DIRSIG hypersamples it), `unresolved_plain` is the same plate
  without the name. Moving plates (`straight` location engines, the only way the SDK can move a target: authored in the
  scene, not a run-spec member) carry the relative-speed axis.
- `manifold_run_specs/s2s/<name>.yaml`: one run spec per grid point, and `index.json` (name, parameters, run id).
- family II (round 30; `grid2`, `run_spec2`, `scene2_files`): `manifold_config_repo/scenes/s2s_blur/`, a second
  generated scene (blur groups with a barred background 10 km behind the plates, a look group, an orbit group), and
  the `s2s2-*` specs: shutter blur over four exposures for platform motion (expressed as the whole group moving),
  target motion and both; look angle 0 to 75 degrees against the background; the `orbit` form tracking a plate. Its
  plates are the scene's highest geometry and every path inside the scene is under 10 km: a surface about 20 km along
  the ray inside the scene was measured not to be hit (docs/Space_to_space_characterization.md).

The grid is one axis at a time about one baseline per object class (`baseline`, `GRID`), not the full product (which
`grid(full=True)` gives). Axes and how each is expressed with existing members:
- range, look angle off nadir, sub-pixel offset: `engine.motion` kind `static`, the platform placed at the range along
  the look direction from the plate and turned to face it (`pose`); the offset moves the platform by a fraction of the
  pixel footprint along both scene axes. A sub-pixel block crosses three ranges with every offset (`SUBPIXEL_RANGES`).
- relative speed: 0 for a static platform and plate; a moving plate (`MOVING`); or `engine.motion` kind `orbit` (the
  library WORLDVIEW-2 TLE propagated over a window, LookAt at the plate), whose speed and range are the TLE's, not set.
- exposure time: `descriptor.settings[0].exposure_time` (`temporalintegration` time; `integration_samples` 10).
- sun angle: `engine.atmosphere` plugin `basic` with `uniform` values and a `fixed_ephemeris` (no extinction, no path
  radiance, all of `IRRADIANCE` direct). The phase angle is derived and recorded; for a flat Lambertian plate only the
  solar zenith changes the signal.
- object class: which plate the platform faces.
Every spec renders at one thread (`resources.cpu_threads: 1`, docs/DIRSIG_determinism.md) and at the sensor's native
window as the library template sets it (500 x 500: auror-nir records no full frame).
"""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "manifold_config_repo"
SENSORS = ROOT / "manifold_sensors"
OUT = ROOT / "manifold_run_specs" / "s2s"
SCENE_NAME = "s2s_targets"
SCENE_DIR = LIBRARY / "scenes" / SCENE_NAME
SCENE_REF = f"scenes/{SCENE_NAME}/{SCENE_NAME}.scene"
sys.path[:0] = [str(ROOT / "packages" / d / "src") for d in ("core", "sim")]   # the manifold namespace, uninstalled

import manifold.sim  # noqa: E402,F401  (installs the engine registry validation uses)
from manifold.core.dirhash import directory_digest  # noqa: E402
from manifold.core.identity import run_id  # noqa: E402
from manifold.core.spectral import sha256_file  # noqa: E402

GENERATED = "# GENERATED by scripts/s2s_scenarios.py - do not edit\n"
SENSOR = "auror-nir.yaml"
ENTRY = "auror-nir"
PLATFORM = "platforms/AurorNIRDetector/AurorNIRDetector.platform"
TLE = "orbit/worldview2_35946.tle"
EOP = "orbit/iers.npz"
NATIVE = 500                       # the template's detector array; auror-nir's SensorWidth/Height are null
DIRFM_REVISION = "93195cee1ccc4f31a214e114d94c493a1d4cc22f"
ORIGIN = (39.0, -120.0)            # the scene origin: Tahoe's, so the library TLE's pass over Tahoe applies
EPOCH = "2026-09-26T18:50:25Z"     # recipes/leo_pass_tahoe.yaml's: a 120 s window centred on culmination
REFLECTANCE = 0.5
IRRADIANCE = 0.1                   # UniformAtm hemisphere irradiance, spectrally constant (DIRSIG's units)
WEATHER = "mls.wth"                # an install weather file; uniform weather is required by BasicAtmosphere
INTEGRATION_SAMPLES = 10
FRAME_RATE = 10                    # Hz; the longest exposure (20 ms) fits a frame

# object class -> plate: side (m), centre (scene ENU, m), instance name
PLATES = {
    "hyperresolved": {"side": 20.0, "centre": (0.0, 0.0, 0.0), "instance": "hyperresolved"},
    "unresolved": {"side": 0.5, "centre": (50000.0, 0.0, 0.0), "instance": "::IMPORTANT::unresolved"},
    "unresolved_plain": {"side": 0.5, "centre": (-50000.0, 0.0, 0.0), "instance": "unresolved_plain"},
}
# relative speed (m/s) -> a moving unresolved plate: its centre at time 0 (task time 0), heading 90 (DIRSIG `straight`)
MOVING = {1000.0: (0.0, 50000.0, 0.0), 7500.0: (0.0, -50000.0, 0.0)}
BACKSTOP = {"side": 400.0, "depth": 10.0}   # a black plate behind every target (see the module docstring)
ORBIT = "orbit"                    # the relative-speed value of an orbit-kind spec: the TLE's speed, not stated

AXES = ("object_class", "range_m", "relative_speed", "exposure_s", "look_deg", "solar_zenith_deg", "offset_px")
BASELINE = {
    "hyperresolved": {"range_m": 25000.0, "relative_speed": 0.0, "exposure_s": 0.005, "look_deg": 0.0,
                      "solar_zenith_deg": 0.0, "offset_px": 0.0},
    "unresolved": {"range_m": 200000.0, "relative_speed": 0.0, "exposure_s": 0.005, "look_deg": 0.0,
                   "solar_zenith_deg": 0.0, "offset_px": 0.0},
}
BASELINE["unresolved_plain"] = dict(BASELINE["unresolved"])
GRID = {
    "range_m": {"hyperresolved": (12500.0, 25000.0, 50000.0, 100000.0),
                "unresolved": (12500.0, 25000.0, 50000.0, 100000.0, 200000.0, 400000.0, 800000.0),
                "unresolved_plain": (12500.0, 25000.0, 50000.0, 100000.0, 200000.0, 400000.0, 800000.0)},
    "relative_speed": {"unresolved": (0.0, 1000.0, 7500.0, ORBIT)},
    "exposure_s": {c: (0.001, 0.005, 0.02) for c in PLATES},
    "look_deg": {c: (0.0, 30.0, 60.0) for c in PLATES},
    "solar_zenith_deg": {c: (0.0, 30.0, 60.0) for c in PLATES},
    "offset_px": {"unresolved": (0.0, 0.25, 0.5, 0.75), "unresolved_plain": (0.0, 0.25, 0.5, 0.75)},
}
# the sub-pixel block: for the unresolved classes, these ranges crossed with every offset (the plate 1.2, 0.6 and 0.3
# pixel footprints across), beside the one-axis-at-a-time points
SUBPIXEL_RANGES = (12500.0, 25000.0, 50000.0)
# orbit-kind specs: the pass's task time (s from EPOCH) at culmination; range and look angle follow from the TLE
ORBIT_TASK = 60.0


# --- the sensor's numbers ---------------------------------------------------------------------------------------------

def sensor_numbers():
    """(focal length m, pixel pitch m) from the sensor-spec the family names."""
    doc = yaml.safe_load((SENSORS / SENSOR).read_text())
    entry = doc["sensor"]["entries"][0]
    det = entry["focal_planes"][0]["detector"]
    return entry["optics"]["focal_length"] / 1000.0, det["SensorPixelWidth"] * 1e-6


def footprint(range_m):
    """The pixel footprint (m) across the line of sight at `range_m`: range x pitch / focal length."""
    f, p = sensor_numbers()
    return range_m * p / f


# --- the target scene -------------------------------------------------------------------------------------------------

def _plate_obj(side):
    h = side / 2
    v = [(-h, -h, 0.0), (h, -h, 0.0), (h, h, 0.0), (-h, h, 0.0)]
    lines = ["# square plate, normal +z", "mtllib plate.mtl"] + [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in v]
    lines += ["vn 0.000000 0.000000 1.000000", "usemtl plate", "f 1//1 2//1 3//1", "f 1//1 3//1 4//1"]
    return "\n".join(lines) + "\n"


MATERIAL = """MATERIAL_ENTRY {{
    ID           = plate
    NAME         = plate
    EDITOR_COLOR = 0.5, 0.5, 0.5
    DOUBLE_SIDED = FALSE

    RAD_SOLVER_NAME = Generic
    RAD_SOLVER {{
        INITIAL_SAMPLE_COUNT = 100
        SAMPLE_DECAY_RATE    = 2
        MAX_BOUNCES          = 3
        MU_SAMPLES           = 10
        PHI_SAMPLES          = 20
        MIN_QUAD_SAMPLES     = 1
    }}

    TEMP_SOLVER_NAME = DataDriven
    TEMP_SOLVER {{
        TEMPERATURE = 300
    }}

    SURFACE_PROPERTIES {{
        REFLECTANCE_PROP_NAME = SimpleReflectance
        REFLECTANCE_PROP {{
            TXT_FILENAME = ref.txt
        }}
    }}
}}
"""


def _bundle_glist(obj):
    return ('<geometrylist>\n    <object search_paths="local">\n        <localmaterials>plate.mat</localmaterials>\n'
            f'        <basegeometry>\n            <obj>\n                <filename>{obj}</filename>\n'
            '            </obj>\n        </basegeometry>\n        <staticinstance/>\n    </object>\n</geometrylist>\n')


def _xyz(p):
    return f"<x>{p[0]:.1f}</x><y>{p[1]:.1f}</y><z>{p[2]:.1f}</z>"


def _instance(bundle, kind, name, centre, extra=()):
    head = f'    <{kind} name="{name}">'
    body = [f"      <translation><point>{_xyz(centre)}</point></translation>"] if kind == "staticinstance" else list(extra)
    return ["  <object>", "    <basegeometry>", f"      <glist><filename>bundles/{bundle}/{bundle}.glist</filename></glist>",
            "    </basegeometry>", head, *body, f"    </{kind}>", "  </object>"]


def _targets_glist():
    out = ["<geometrylist>"]
    stations = []
    for cls, plate in PLATES.items():
        bundle = "plate_20m" if plate["side"] == 20.0 else "plate_0p5m"
        out += _instance(bundle, "staticinstance", plate["instance"], plate["centre"])
        stations.append(plate["centre"])
    for speed, start in MOVING.items():
        motion = ['      <motion type="flexible">', '        <locationengine type="straight">',
                  f"          <heading>90</heading><velocity>{speed:.1f}</velocity>",
                  f'          <start frame="scene">{_xyz(start)}</start>', "        </locationengine>",
                  '        <orientationengine type="velocity">',
                  '          <constraint type="constant" frame="scene" vector="0,0,1"/>',
                  "        </orientationengine>", "      </motion>"]
        out += _instance("plate_0p5m", "dynamicinstance", f"::IMPORTANT::moving_{int(speed)}", start, motion)
        stations.append(start)
    for i, (x, y, z) in enumerate(stations):
        out += _instance("backstop", "staticinstance", f"backstop_{i}", (x, y, z - BACKSTOP["depth"]))
    return "\n".join(out + ["</geometrylist>"]) + "\n"


def _scene_xml():
    lat, lon = ORIGIN
    return f"""<classicscene>
  <metadata>
    <entry>
      <name>Description</name>
      <value><![CDATA[Space-to-space target plates written by scripts/s2s_scenarios.py: Lambertian squares, no ground.]]></value>
    </entry>
  </metadata>
  <sceneorigin>
    <location frame="geodetic">
      <latitude>{lat:.10f}</latitude>
      <longitude>{lon:.10f}</longitude>
      <altitude>0.0000000000</altitude>
    </location>
  </sceneorigin>
  <properties features="vis,nir,swir" mingsd="0" maxgsd="0"/>
  <odbdirectory>$SCENE_DIR/geometry</odbdirectory>
  <gdbdirectory>$SCENE_DIR/geometry</gdbdirectory>
  <geometrylist enabled="true">
    <geometrylistinclude name="Targets" enabled="true">lists/targets.glist</geometrylistinclude>
  </geometrylist>
  <matfilename>$SCENE_DIR/materials/s2s_targets.mat</matfilename>
  <emsdirectory>$SCENE_DIR/materials/</emsdirectory>
  <extdirectory>$SCENE_DIR/materials</extdirectory>
  <absdirectory>$SCENE_DIR/materials</absdirectory>
  <srcdirectory>$SCENE_DIR/materials</srcdirectory>
  <mapdirectory>$SCENE_DIR/maps</mapdirectory>
</classicscene>
"""


def scene_files():
    """{relative path: text} of the target scene directory."""
    files = {f"{SCENE_NAME}.scene": _scene_xml(), "geometry/lists/targets.glist": _targets_glist(),
             "materials/s2s_targets.mat": ""}
    for bundle, side, rho in (("plate_20m", 20.0, REFLECTANCE), ("plate_0p5m", 0.5, REFLECTANCE),
                              ("backstop", BACKSTOP["side"], 0.0)):
        files[f"geometry/bundles/{bundle}/{bundle}.glist"] = _bundle_glist(f"{bundle}.obj")
        files[f"geometry/bundles/{bundle}/{bundle}.obj"] = _plate_obj(side).replace("mtllib plate.mtl\n", "")
        files[f"geometry/bundles/{bundle}/plate.mat"] = MATERIAL.format()
        files[f"geometry/bundles/{bundle}/ref.txt"] = "".join(f"{w:.1f}   {rho:.2f}\n"
                                                             for w in (0.2, 0.4, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0))
    return files


def write_scene(root=SCENE_DIR, files=None):
    for rel, text in (scene_files() if files is None else files).items():
        path = Path(root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


# --- geometry ---------------------------------------------------------------------------------------------------------

def _rot(axis, a):
    c, s = math.cos(a), math.sin(a)
    if axis == "x":
        return [[1, 0, 0], [0, c, -s], [0, s, c]]
    if axis == "y":
        return [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def pose(point, centre=None):
    """The static platform's scene position (m) and `xyz` Euler angles (radians, sceneenu) for a grid point: at
    `range_m` from the plate centre (`centre`, default the class's plate) along a direction `look_deg` from the zenith
    in the scene's x-z plane (toward -x), turned to face it (nadir: the AUROR pose's angles, [0, 0, pi]); moved
    `offset_px` pixel footprints along +y."""
    cx, cy, cz = centre if centre is not None else PLATES[point["object_class"]]["centre"]
    r, look = point["range_m"], math.radians(point["look_deg"])
    shift = point["offset_px"] * footprint(r)
    pos = [cx - r * math.sin(look) + shift, cy + shift, cz + r * math.cos(look)]
    return [round(v, 6) for v in pos], [0.0, round(look, 9), round(math.pi, 9)]


def phase_deg(point):
    """The angle at the plate between the Sun and the sensor (degrees). The Sun stands in the look plane, on the side
    away from the sensor (azimuth 90, toward +x, when the sensor is toward -x), so phase = look + solar zenith."""
    return point["look_deg"] + point["solar_zenith_deg"]


def expected(point):
    """The run spec's own numbers for a grid point: pixel footprint (m), plate side in pixels, projected area (m^2),
    expected footprint in pixels (projected area / footprint^2) and the cosine factors of the Lambertian plate."""
    plate = PLATES[point["object_class"]]
    g = footprint(point["range_m"]) if point["relative_speed"] != ORBIT else None
    look, sun = math.radians(point["look_deg"]), math.radians(point["solar_zenith_deg"])
    area = plate["side"] ** 2 * math.cos(look)
    return {"footprint_m": g, "side_px": plate["side"] / g if g else None, "projected_area_m2": area,
            "footprint_px": area / g ** 2 if g else None, "cos_sun": math.cos(sun), "phase_deg": phase_deg(point)}


# --- the grid ---------------------------------------------------------------------------------------------------------

def _num_tag(v, scale=1, unit=""):
    s = f"{v * scale:g}".replace(".", "p")
    return s + unit


def point_name(p):
    speed = "orbit" if p["relative_speed"] == ORBIT else _num_tag(p["relative_speed"], 1, "mps")
    return "s2s-{}-r{}-v{}-e{}-l{}-z{}-d{}".format(
        p["object_class"].replace("_", ""), _num_tag(p["range_m"], 1e-3, "km"), speed,
        _num_tag(p["exposure_s"], 1e3, "ms"), _num_tag(p["look_deg"]), _num_tag(p["solar_zenith_deg"]),
        _num_tag(p["offset_px"]))


def grid(full=False):
    """The family's grid points (dicts over AXES), in a fixed order: per class, the baseline, then each axis's other
    values one at a time; with `full`, the product of each class's axis values. An orbit point's range and look angle
    are the TLE's: they are set to the pass's values (`orbit_geometry`) and not varied."""
    points = []
    for cls in PLATES:
        base = {"object_class": cls, **BASELINE[cls]}
        axes = [a for a in AXES[1:] if cls in GRID[a]]
        if full:
            import itertools
            for combo in itertools.product(*(GRID[a][cls] for a in axes)):
                points.append({**base, **dict(zip(axes, combo))})
        else:
            points.append(dict(base))
            for a in axes:
                points += [{**base, a: v} for v in GRID[a][cls] if v != base[a]]
            if "offset_px" in axes:
                points += [{**base, "range_m": r, "offset_px": d} for r in SUBPIXEL_RANGES for d in GRID["offset_px"][cls]]
    seen, out = set(), []
    for p in points:
        if p["relative_speed"] == ORBIT:
            p = {**p, **orbit_geometry()}
        name = point_name(p)
        if name not in seen:
            seen.add(name)
            out.append(p)
    return out


def orbit_geometry(target=None):
    """Range (m, rounded to 1 m) and look angle off nadir (degrees, 0.1) from the library TLE's track at the pass task
    to `target` (scene ENU; default the unresolved plate), by the SDK's propagator: the values an orbit point records,
    not ones it sets."""
    import numpy as np

    from manifold.core import orbit
    _, _, l1, l2 = orbit.read_tle(LIBRARY / TLE)
    traj = orbit.propagate(l1, l2, EPOCH, [ORBIT_TASK], eop=LIBRARY / EOP)
    m = orbit.ecef_to_enu_matrix(*ORIGIN)
    lat, lon = np.radians(ORIGIN)
    n = orbit.WGS84_A / math.sqrt(1 - orbit.WGS84_E2 * math.sin(lat) ** 2)
    o = np.array([n * math.cos(lat) * math.cos(lon), n * math.cos(lat) * math.sin(lon), n * (1 - orbit.WGS84_E2) * math.sin(lat)])
    sat = m @ (traj.pos_itrs[0] - o)
    los = sat - np.array(PLATES["unresolved"]["centre"] if target is None else target)
    rng = float(np.linalg.norm(los))
    return {"range_m": float(round(rng)), "look_deg": round(math.degrees(math.acos(los[2] / rng)), 1)}



# --- family II: shutter blur, look angle with a background, orbit tracking (round 30) -------------------------------
#
# A second generated scene, `s2s_blur` (SCENE2_DIR), so that family I's scene and its 63 specs stay byte-identical.
# Groups, each kilometres from the others so that one frame holds one group:
# - blur groups (BLUR_GROUPS): a 20 m plate (`hyperresolved`), a 0.5 m plate 120 m to its +y side
#   (`::IMPORTANT::unresolved`), and a textured background BLUR["depth"] behind them: a black plate with white bars
#   (reflectance BAR_REFLECTANCE) running along y on its -y side (`bars`), the rest black so that each plate is seen
#   against zero. What moves is scene content (DIRSIG `straight`, heading 90, a fixed orientation): platform motion
#   is the whole group moving the other way (a static platform; the run spec cannot move it at a stated speed),
#   target motion is the plates alone, both is the background at the platform's speed and the plates at the sum. The
#   static group carries a 4 m marker plate 100 m to the target's +x side: the image direction of scene +x.
# - the look group (LOOK): the 20 m plate with bars LOOK["depth"] behind it on both sides of a black band along x.
# - the orbit group (ORBIT_BLUR): a 100 m plate with a black backstop, the LookAt point of the orbit-kind specs.

SCENE2_NAME = "s2s_blur"
SCENE2_DIR = LIBRARY / "scenes" / SCENE2_NAME
SCENE2_REF = f"scenes/{SCENE2_NAME}/{SCENE2_NAME}.scene"
BAR_REFLECTANCE = 0.25
BAR = {"period": 80.0, "width": 40.0}
BLUR = {"range_m": 25000.0, "depth": 10000.0, "base_z": 0.0, "speed": 1000.0, "unresolved_y": 120.0, "marker_x": 100.0,
        "black_side": 1200.0, "bars_x": (-560.0, 560.0), "bars_y": (-600.0, -60.0)}
# group -> (centre x, background speed, plates' speed): speeds along heading 90 (DIRSIG: degrees east of north)
BLUR_GROUPS = {"static": (0.0, 0.0, 0.0), "platform": (2000.0, 1.0, 1.0), "target": (4000.0, 0.0, 1.0),
               "both": (6000.0, 1.0, 2.0)}
BLUR_EXPOSURES = (0.0001, 0.001, 0.005, 0.02)
LOOK = {"centre": (0.0, 5000.0, 10000.0), "range_m": 25000.0, "depth": 500.0, "black_side": 2400.0,
        "black_x": 350.0, "bars_x": (-800.0, 1440.0), "band": 40.0, "bars_y": 1150.0}
LOOK_DEG = (0.0, 15.0, 30.0, 45.0, 60.0, 75.0)
ORBIT_BLUR = {"centre": (0.0, -20000.0, 0.0), "side": 100.0, "backstop": 2000.0}
ORBIT_EXPOSURES = (0.0001, 0.02)


def _rects_obj(rects):
    """An OBJ of axis-aligned rectangles in z = 0, normal +z: rects are (x0, x1, y0, y1) in metres."""
    lines, n = ["# rectangles, normal +z"], 0
    for x0, x1, y0, y1 in rects:
        lines += [f"v {x:.6f} {y:.6f} 0.000000" for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    lines += ["vn 0.000000 0.000000 1.000000", "usemtl plate"]
    for _ in rects:
        lines += [f"f {n + 1}//1 {n + 2}//1 {n + 3}//1", f"f {n + 1}//1 {n + 3}//1 {n + 4}//1"]
        n += 4
    return "\n".join(lines) + "\n"


def _bars(x_range, y_ranges):
    """White bars of BAR["width"] every BAR["period"], centred at multiples of the period in `x_range`, each spanning
    every y range of `y_ranges`."""
    k0, k1 = int(round(x_range[0] / BAR["period"])), int(round(x_range[1] / BAR["period"]))
    w = BAR["width"] / 2
    return [(k * BAR["period"] - w, k * BAR["period"] + w, y0, y1) for k in range(k0, k1 + 1) for y0, y1 in y_ranges]


def _bundles2():
    """{bundle: (rectangles, reflectance)} of the family II scene, centred on their own origins."""
    sq = lambda s: [(-s / 2, s / 2, -s / 2, s / 2)]   # noqa: E731
    return {"plate_20m": (sq(20.0), REFLECTANCE), "plate_0p5m": (sq(0.5), REFLECTANCE),
            "plate_4m": (sq(4.0), REFLECTANCE), "plate_100m": (sq(ORBIT_BLUR["side"]), REFLECTANCE),
            "black_blur": (sq(BLUR["black_side"]), 0.0), "black_look": (sq(LOOK["black_side"]), 0.0),
            "backstop_2km": (sq(ORBIT_BLUR["backstop"]), 0.0),
            "bars_blur": (_bars(BLUR["bars_x"], [BLUR["bars_y"]]), BAR_REFLECTANCE),
            "bars_look": (_bars(LOOK["bars_x"], [(LOOK["band"], LOOK["bars_y"]), (-LOOK["bars_y"], -LOOK["band"])]),
                          BAR_REFLECTANCE)}


def _moving(bundle, name, start, speed):
    motion = ['      <motion type="flexible">', '        <locationengine type="straight">',
              f"          <heading>90</heading><velocity>{speed:.1f}</velocity>",
              f'          <start frame="scene">{_xyz(start)}</start>', "        </locationengine>",
              '        <orientationengine type="euler">',
              '          <data source="internal" datetime="relative" frame="scene" order="xyz" delimiter=" " '
              'loop="false"><![CDATA[0 0 0 0]]></data>',
              "        </orientationengine>", "      </motion>"]
    return _instance(bundle, "dynamicinstance", name, start, motion)


def _place(bundle, name, centre, speed):
    return _moving(bundle, name, centre, speed) if speed else _instance(bundle, "staticinstance", name, centre)


def _blur_glist():
    out = ["<geometrylist>"]
    v = BLUR["speed"]
    for group, (gx, bg, fg) in BLUR_GROUPS.items():
        b = BLUR["base_z"]                       # the background's height; the plates stand BLUR["depth"] above it
        z = b + BLUR["depth"]
        out += _place("plate_20m", f"{group}_target", (gx, 0.0, z), fg * v)
        out += _place("plate_0p5m", f"::IMPORTANT::{group}_unresolved", (gx, BLUR["unresolved_y"], z), fg * v)
        out += _place("bars_blur", f"{group}_bars", (gx, 0.0, b + 1.0), bg * v)
        out += _place("black_blur", f"{group}_background", (gx, 0.0, b), bg * v)
        if group == "static":
            out += _instance("plate_4m", "staticinstance", "static_marker", (gx + BLUR["marker_x"], 0.0, z))
    lx, ly, lz = LOOK["centre"]
    out += _instance("plate_20m", "staticinstance", "look_target", LOOK["centre"])
    out += _instance("bars_look", "staticinstance", "look_bars", (lx, ly, lz - LOOK["depth"] + 1.0))
    out += _instance("black_look", "staticinstance", "look_background", (lx + LOOK["black_x"], ly, lz - LOOK["depth"]))
    ox, oy, oz = ORBIT_BLUR["centre"]
    out += _instance("plate_100m", "staticinstance", "orbit_target", ORBIT_BLUR["centre"])
    out += _instance("backstop_2km", "staticinstance", "orbit_backstop", (ox, oy, oz - BACKSTOP["depth"]))
    return "\n".join(out + ["</geometrylist>"]) + "\n"


def scene2_files():
    """{relative path: text} of the family II scene directory."""
    files = {f"{SCENE2_NAME}.scene": _scene_xml().replace(SCENE_NAME, SCENE2_NAME).replace(
                 "Space-to-space target plates", "Space-to-space blur and look-angle groups"),
             "geometry/lists/targets.glist": _blur_glist(), f"materials/{SCENE2_NAME}.mat": ""}
    for bundle, (rects, rho) in _bundles2().items():
        files[f"geometry/bundles/{bundle}/{bundle}.glist"] = _bundle_glist(f"{bundle}.obj")
        files[f"geometry/bundles/{bundle}/{bundle}.obj"] = _rects_obj(rects)
        files[f"geometry/bundles/{bundle}/plate.mat"] = MATERIAL.format()
        files[f"geometry/bundles/{bundle}/ref.txt"] = "".join(f"{w:.1f}   {rho:.2f}\n"
                                                             for w in (0.2, 0.4, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0))
    return files


def grid2():
    """Family II's points, in a fixed order: the blur groups (the static group at 5 ms, each moving group at every
    BLUR_EXPOSURES value), the look group at every LOOK_DEG value (5 ms), the orbit group at ORBIT_EXPOSURES."""
    pts = [{"kind": "blur", "group": "static", "exposure_s": 0.005, "look_deg": 0.0}]
    pts += [{"kind": "blur", "group": g, "exposure_s": e, "look_deg": 0.0} for g in BLUR_GROUPS if g != "static"
            for e in BLUR_EXPOSURES]
    pts += [{"kind": "look", "group": "look", "exposure_s": 0.005, "look_deg": a} for a in LOOK_DEG]
    pts += [{"kind": "orbit", "group": "orbit", "exposure_s": e, "look_deg": None} for e in ORBIT_EXPOSURES]
    return pts


def point2_name(p):
    tail = f"-l{_num_tag(p['look_deg'])}" if p["kind"] == "look" else f"-e{_num_tag(p['exposure_s'], 1e3, 'ms')}"
    return f"s2s2-{p['kind']}-{p['group']}{tail}" if p["kind"] == "blur" else f"s2s2-{p['kind']}{tail}"


def expected2(p):
    """The run spec's own numbers for a family II point: the pixel footprint (m) at the target and at the background,
    the target's projected area (m^2) and footprint (pixels), and for a blur point the blur lengths (pixels) of the
    target and the background, speed x exposure over the footprint."""
    if p["kind"] == "orbit":
        g = footprint(orbit_geometry(ORBIT_BLUR["centre"])["range_m"])
        side = ORBIT_BLUR["side"]
        return {"footprint_m": g, "side_px": side / g, "footprint_px": side ** 2 / g ** 2}
    look = math.radians(p["look_deg"])
    r = BLUR["range_m"] if p["kind"] == "blur" else LOOK["range_m"]
    depth = BLUR["depth"] if p["kind"] == "blur" else LOOK["depth"]
    g, gb = footprint(r), footprint(r + depth / math.cos(look))
    out = {"footprint_m": g, "background_footprint_m": gb, "side_px": 20.0 / g,
           "projected_area_m2": 400.0 * math.cos(look), "footprint_px": 400.0 * math.cos(look) / g ** 2,
           "background_period_px": BAR["period"] * math.cos(look) / gb if p["kind"] == "look" else BAR["period"] / gb}
    if p["kind"] == "blur":
        _, bg, fg = BLUR_GROUPS[p["group"]]
        rel_bg = bg * BLUR["speed"]
        out["target_blur_px"] = fg * BLUR["speed"] * p["exposure_s"] / g
        out["background_blur_px"] = rel_bg * p["exposure_s"] / gb
        out["unresolved_side_px"] = 0.5 / g
    return out


def run_spec2(p, scene_hash=None):
    """The `run-spec/1` document of family II point `p`: family I's template (sensor, settings, atmosphere with the Sun
    at the zenith, one thread, seed 1) with the scene, the motion, the exposure and the descriptor's words changed."""
    name = point2_name(p)
    if p["kind"] == "orbit":
        geo = orbit_geometry(ORBIT_BLUR["centre"])
        base = {"object_class": "unresolved", **BASELINE["unresolved"], **geo, "relative_speed": ORBIT}
    else:
        base = {"object_class": "hyperresolved", **BASELINE["hyperresolved"], "look_deg": p["look_deg"],
                "range_m": BLUR["range_m"] if p["kind"] == "blur" else LOOK["range_m"]}
    base["exposure_s"] = p["exposure_s"]
    spec = run_spec(base, scene_hash="0" * 64)
    desc, eng = spec["descriptor"], spec["engine"]
    ex = expected2(p)
    if p["kind"] == "blur":
        _, bg, fg = BLUR_GROUPS[p["group"]]
        what = (f"the blur group '{p['group']}' (plates at {fg * BLUR['speed']:g} m/s, background at "
                f"{bg * BLUR['speed']:g} m/s, both along heading 90; the background {BLUR['depth'] / 1000:g} km behind) "
                f"seen at nadir from {BLUR['range_m'] / 1000:g} km, exposure {p['exposure_s'] * 1000:g} ms")
        extras = {"s2s.group": p["group"], "s2s.target_speed": fg * BLUR["speed"],
                  "s2s.background_speed": bg * BLUR["speed"], "s2s.background_depth_m": BLUR["depth"]}
        pos = [BLUR_GROUPS[p["group"]][0], 0.0, BLUR["base_z"] + BLUR["depth"] + BLUR["range_m"]]
        eng["motion"]["position"]["xyz"] = pos
    elif p["kind"] == "look":
        what = (f"the 20 m plate with a bar background {LOOK['depth']:g} m behind it, {p['look_deg']:g} deg off nadir "
                f"at a slant range of {LOOK['range_m'] / 1000:g} km, exposure {p['exposure_s'] * 1000:g} ms")
        extras = {"s2s.group": "look", "s2s.look_deg": p["look_deg"], "s2s.background_depth_m": LOOK["depth"]}
        pos, angles = pose(base, LOOK["centre"])
        eng["motion"]["position"]["xyz"], eng["motion"]["orientation"]["euler"]["angles"] = pos, angles
    else:
        what = (f"the 100 m plate tracked by the orbit form (LookAt at the plate) at {base['range_m'] / 1000:g} km, "
                f"{base['look_deg']:g} deg off nadir (the TLE's), exposure {p['exposure_s'] * 1000:g} ms")
        extras = {"s2s.group": "orbit", "s2s.look_deg": base["look_deg"]}
        eng["motion"]["orientation"]["lookat"]["target"] = list(ORBIT_BLUR["centre"])
    desc["meta"] = {"name": name, "tags": ["s2s", "space-to-space", "family-2", p["kind"]],
                    "description": f"Space-to-space family II: {what}. Written by scripts/s2s_scenarios.py.\n"}
    desc["extras"] = {"s2s.family": 2, "s2s.kind": p["kind"], **extras,
                      "s2s.exposure_s": p["exposure_s"], "s2s.solar_zenith_deg": 0.0}
    eng["scenes"][0]["ref"] = {"name": SCENE2_REF, "content_hash": scene_hash or _ref(SCENE2_REF)["content_hash"]}
    eng["platform"]["output_prefix"] = "s2s2_"
    return spec


# --- the run specs ----------------------------------------------------------------------------------------------------

def _ref(rel, root=LIBRARY):
    path = root / rel
    return {"name": rel, "content_hash": directory_digest(path.parent) if rel.endswith(".scene") else sha256_file(path)}


def run_spec(p, scene_hash=None):
    """The `run-spec/1` document of grid point `p`."""
    name = point_name(p)
    ex = expected(p)
    orbit_kind = p["relative_speed"] == ORBIT
    target = PLATES["unresolved" if p["relative_speed"] not in (0.0, ORBIT) else p["object_class"]]
    if p["relative_speed"] not in (0.0, ORBIT):
        target = {**target, "centre": MOVING[p["relative_speed"]]}
    desc = {
        "meta": {"name": name, "tags": ["s2s", "space-to-space", "family-1", p["object_class"]],
                 "description": (f"Space-to-space family I: the {p['object_class']} plate seen from "
                                 f"{p['range_m'] / 1000:g} km, {p['look_deg']:g} deg off nadir, Sun at "
                                 f"{p['solar_zenith_deg']:g} deg zenith (phase {ex['phase_deg']:g} deg), exposure "
                                 f"{p['exposure_s'] * 1000:g} ms, relative speed {p['relative_speed']}"
                                 f"{'' if orbit_kind else ' m/s'}, offset {p['offset_px']:g} px. Written by "
                                 "scripts/s2s_scenarios.py.\n")},
        "origin": {"kind": "synthetic", "engine": "dirsig"},
        "collection": {"epoch": EPOCH, "platform": {"class": "satellite"},
                       "geometry": {"regime": "space_to_space",
                                    "range": {"value": p["range_m"],
                                              "provenance": "modeled" if orbit_kind else "specified"}},
                       "illumination": {"regime": "daylight"}, "atmosphere": {"regime": "none"},
                       "background": {"regime": "space"}, "targets": [{"class": "space_object"}]},
        "sensor": {"ref": {"name": SENSOR, "content_hash": sha256_file(SENSORS / SENSOR)}},
        "settings": [{"entry_id": ENTRY,
                      "exposure_time": {"value": p["exposure_s"], "provenance": "specified"},
                      "frame_rate": {"value": FRAME_RATE, "provenance": "specified"},
                      "gain": {"value": 1, "provenance": "specified"},
                      "black_level": {"value": 0, "provenance": "specified"},
                      "roi": {"Width": NATIVE, "Height": NATIVE, "OffsetX": None, "OffsetY": None}}],
        "fidelity": {"modeled": ["reflected sunlight from a Lambertian plate", "platform position and pointing",
                                 "temporal integration over the exposure"],
                     "approximated": ["uniform atmosphere: no extinction, no path radiance, spectrally constant Sun"],
                     "absent": ["Earth background", "stars", "optics blur (the template's spatial response is one "
                                "uniform pixel)", "detector noise"],
                     "valid_for": "Geometry and flux-closure studies of a plate against space; not a sensor-performance "
                                  "prediction.\n"},
        "extras": {"s2s.object_class": p["object_class"], "s2s.look_deg": p["look_deg"],
                   "s2s.solar_zenith_deg": p["solar_zenith_deg"], "s2s.phase_deg": ex["phase_deg"],
                   "s2s.offset_px": p["offset_px"], "s2s.relative_speed": p["relative_speed"],
                   "s2s.plate_side_m": PLATES[p["object_class"]]["side"]},
    }
    if orbit_kind:
        motion = {"kind": "orbit",
                  "orbit": {"tle": _ref(TLE), "propagator": "skyfield_sgp4", "earth_orientation": _ref(EOP),
                            "window": {"start": 0.0, "duration": 120.0}, "waypoint_spacing": 1.0},
                  "orientation": {"kind": "lookat", "lookat": {"frame": "sceneenu", "target": list(target["centre"]),
                                                               "up": "along_track"}}}
        windows = [{"start": ORBIT_TASK, "stop": ORBIT_TASK}]
    else:
        pos, angles = pose(p, target["centre"])
        motion = {"kind": "static", "position": {"frame": "scene", "xyz": pos},
                  "orientation": {"kind": "euler", "euler": {"order": "xyz", "units": "radians", "frame": "sceneenu",
                                                             "angles": angles}}}
        windows = [{"start": 0.0, "stop": 0.0}]
    sun_az = 90 if p["look_deg"] > 0 else 0
    engine = {
        "generator": {"tool": "dirfm", "revision": DIRFM_REVISION, "spec_schema": "dirsig-engine/1"},
        "scenes": [{"ref": {"name": SCENE_REF, "content_hash": scene_hash or _ref(SCENE_REF)["content_hash"]},
                    "offset": [0, 0, 0]}],
        "platform": {"ref": _ref(PLATFORM), "library_entry": "auror-nir-detector", "output_prefix": "s2s_",
                     "split_channels": False, "integration_samples": INTEGRATION_SAMPLES},
        "motion": motion,
        "tasks": {"windows": windows},
        "atmosphere": {"plugin": "basic",
                       "uniform": {"radiative_transfer": {"hemisphere_irradiance": IRRADIANCE, "sky_fraction": 0},
                                   "weather": {"install_file": WEATHER},
                                   "fixed_ephemeris": {"units": "degrees", "solar_zenith": p["solar_zenith_deg"],
                                                       "solar_azimuth": sun_az}}},
        "run": {"seed": 1},
    }
    return {"spec_version": "run-spec/1", "descriptor": desc, "engine": engine, "resources": {"cpu_threads": 1}}


def dump(spec):
    return GENERATED + "\n" + yaml.safe_dump(spec, sort_keys=False, width=120)


def family(scene_hash=None):
    """{file name: text} of families I and II: each spec and index.json (family I's entries first, unchanged; family
    II's entries carry `family: 2` and their own parameters)."""
    files, index = {}, []
    for p in grid():
        spec = run_spec(p, scene_hash)
        name = point_name(p)
        files[f"{name}.yaml"] = dump(spec)
        index.append({"name": name, "run_id": run_id(spec, SENSORS), **{a: p[a] for a in AXES}})
    for p in grid2():
        spec = run_spec2(p)
        name = point2_name(p)
        files[f"{name}.yaml"] = dump(spec)
        index.append({"name": name, "run_id": run_id(spec, SENSORS), "family": 2, **p})
    files["index.json"] = json.dumps(index, indent=1) + "\n"
    return files


def validate(files):
    """Problems of the family's specs: schema, resolution against the library, unstamped refs, and a run id that is not
    the one `index.json` records."""
    from manifold.core.admission import validate_spec
    problems = []
    index = {e["name"]: e["run_id"] for e in json.loads(files["index.json"])}
    for fname, text in files.items():
        if not fname.endswith(".yaml"):
            continue
        spec = yaml.safe_load(text)
        r = validate_spec(spec, OUT / fname, LIBRARY, SENSORS)
        for what, items in (("schema", r.schema_errors), ("resolution", r.resolution_mismatches),
                            ("unstamped", r.unstamped)):
            problems += [f"{fname}: {what}: {i}" for i in items]
        if r.run_id != index.get(fname[:-5]):
            problems.append(f"{fname}: run id {r.run_id} is not the index's {index.get(fname[:-5])}")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="compare with the committed files; exit 1 on a difference")
    ap.add_argument("--list", action="store_true", help="print each grid point and its derived geometry")
    args = ap.parse_args(argv)
    scenes = ((SCENE_DIR, scene_files()), (SCENE2_DIR, scene2_files()))
    if args.list:
        for p in grid():
            ex = expected(p)
            print(point_name(p), json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in ex.items()}))
        for p in grid2():
            ex = expected2(p)
            print(point2_name(p), json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in ex.items()}))
        return 0
    problems = []
    for sdir, scene in scenes:
        if not args.check:
            write_scene(sdir, scene)
        problems += [f"scene {sdir.name}/{rel}: differs from the generated text" for rel, text in scene.items()
                     if not (sdir / rel).is_file() or (sdir / rel).read_text() != text]
        stray = sorted(str(p.relative_to(sdir)) for p in sdir.rglob("*") if p.is_file()
                       and str(p.relative_to(sdir)) not in scene) if sdir.is_dir() else []
        problems += [f"scene {sdir.name}/{rel}: not generated" for rel in stray]
    if problems:                                  # the specs' scene hash would be wrong: stop here
        print("\n".join(problems))
        return 1
    files = family()
    if not args.check:
        OUT.mkdir(parents=True, exist_ok=True)
        for old in OUT.glob("*"):
            if old.name not in files:
                old.unlink()
        for fname, text in files.items():
            (OUT / fname).write_text(text)
        print(f"wrote {SCENE_DIR.relative_to(ROOT)}/ and {SCENE2_DIR.relative_to(ROOT)}/ and {len(files) - 1} run specs "
              f"in {OUT.relative_to(ROOT)}/")
    else:
        have = {p.name: p.read_text() for p in OUT.glob("*")} if OUT.is_dir() else {}
        problems += [f"{OUT.name}/{f}: missing or stale" for f, t in files.items() if have.get(f) != t]
        problems += [f"{OUT.name}/{f}: not generated" for f in sorted(set(have) - set(files))]
        again = family()
        problems += [f"{f}: not deterministic" for f in files if again[f] != files[f]]
    problems += validate(files)
    print("\n".join(problems) if problems else f"{len(files) - 1} run specs: generated, valid, ids as indexed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
