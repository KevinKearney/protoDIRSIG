#!/usr/bin/env python3
"""Survey DIRSIG's shipped demos and write the coverage table (`docs/DIRSIG_demo_coverage.md`).

    python scripts/survey_demos.py --out docs/DIRSIG_demo_coverage.md
    python scripts/survey_demos.py --demos DIR --out FILE
    python scripts/survey_demos.py --check                 exit 1 if the committed table differs from a fresh survey

Reads every `<Name>.zip` under `--demos` (default `external/dirsig/demos/zips`, the DIRSIG install this repository
links) in place with `zipfile`; nothing is extracted. For each demo it parses the simulation file (a DIRSIG5 `.jsim`, or
a legacy `.sim`; with several, `demo.jsim`, then `demo.sim`, then the first by name) and the files it references:
scenes, atmosphere, platform, motion and tasks. It records names, plugin and element names, counts and sizes only, never
file contents (a section headed "First demo: what it took" already in `--out` is kept), and classifies each demo against what the SDK's engine body and loader cover today (CONOPS section 3.2
and `run_spec.resolve_run`): `ready` (nothing missing), `near` (exactly one missing feature), `far` (two or more, or a
non-imaging sensor) or `unparsed` (the layout was not understood; the reason is given). A value that cannot be read is
`unknown`. Standard library plus `lxml`.
"""
import argparse
import json
import posixpath
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

from lxml import etree as et

ROOT = Path(__file__).resolve().parents[1]
DEMOS = ROOT / "external" / "dirsig" / "demos" / "zips"
OUT = ROOT / "docs" / "DIRSIG_demo_coverage.md"
CONTROL = (".sim", ".jsim", ".platform", ".ppd", ".motion", ".tasks", ".atm", ".options")
DOCS = ("readme",)
ATMOSPHERES = {"NewAtmosphere", "BasicAtmosphere", "FourCurveAtmosphere"}
EPHEMERIDES = {"SpiceEphemeris", "FixedEphemeris", "DataDrivenEphemeris"}
WEATHERS = {"ThermWeather", "NsrdbWeather"}
PLATFORMS = {"BasicPlatform"}
NON_IMAGING = {"lidar", "radar", "laser", "gatedfocalplane", "datarecorder"}
SENSOR_PLUGINS = {"ChipMaker", "SphericalCollector", "LightCurve", "PointCollectors", "OrthoImage"}
# Platform elements that name a camera feature the SDK's platform generator does not write (platform_gen refuses a
# distortion model, a channel layout other than single, ...), by element name.
PLATFORM_FEATURES = {"distortion": "lens distortion", "psf": "point spread function", "focusdistance": "focus distance",
                     "fieldcount": "field selector array", "channelpattern": "color filter array",
                     "detectormodel": "detector model (noise, quantization)", "gainmodel": "gain model",
                     "xoversample": "spatial response"}
VERDICT_ORDER = ("ready", "near", "far", "unparsed")
SIZE = lambda b: f"{b / 1e6:.2f}"                                                  # noqa: E731
KEPT = "## First demo: what it took"            # a hand-written section kept when the table is regenerated


class Unparsed(Exception):
    pass


def _xml(data, what):
    try:
        return et.fromstring(data)
    except et.XMLSyntaxError as e:
        raise Unparsed(f"{what} is not XML ({e.msg})") from e


class Demo:
    """One zip: its members and the readers the survey needs."""

    def __init__(self, path):
        self.path = Path(path)
        self.zip = zipfile.ZipFile(self.path)
        self.infos = {i.filename: i for i in self.zip.infolist() if not i.is_dir()}

    def read(self, member):
        return self.zip.read(self.infos[member])

    def resolve(self, base_dir, ref):
        """A member named by `ref` relative to `base_dir` (a member's directory), or None."""
        ref = ref.strip().replace("\\", "/")
        ref = re.sub(r"^\$SCENE_DIR/?", "", ref)
        name = posixpath.normpath(posixpath.join(base_dir, ref))
        return name if name in self.infos else None

    def under(self, directory):
        prefix = directory.rstrip("/") + "/"
        return [m for m in self.infos if m.startswith(prefix)]


def _primary_sim(demo):
    sims = sorted(m for m in demo.infos if m.endswith((".sim", ".jsim")))
    if not sims:
        raise Unparsed("no .sim or .jsim simulation file")
    for want in ("demo.jsim", "demo.sim"):
        for s in sims:
            if posixpath.basename(s) == want:
                return s, sims
    return sims[0], sims


def _scene_members(demo, scene):
    """The members a `.scene` references: the file, the directories named by `*directory` elements and `$SCENE_DIR`
    paths, and the files named by geometry lists, material files and maps (one level into `.glist`/`.odb`)."""
    base = posixpath.dirname(scene)
    found = {scene}
    root = _xml(demo.read(scene), posixpath.basename(scene))
    pending = []
    for el in root.iter():
        text = (el.text or "").strip() if len(el) == 0 else ""
        if not text:
            continue
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag.endswith("directory"):
            directory = posixpath.normpath(posixpath.join(base, re.sub(r"^\$SCENE_DIR/?", "", text)))
            if directory != posixpath.normpath(base):                  # the scene's own folder: named files only
                found.update(demo.under(directory))
            continue
        member = demo.resolve(base, text)
        if member:
            found.add(member)
            if member.endswith((".glist", ".odb")):
                pending.append(member)
        elif text.startswith("$SCENE_DIR/") and posixpath.dirname(text[11:]):
            found.update(demo.under(posixpath.normpath(posixpath.join(base, posixpath.dirname(text[11:])))))
    for listing in pending:
        try:
            sub = _xml(demo.read(listing), posixpath.basename(listing))
        except Unparsed:
            continue
        for el in sub.iter():
            text = (el.text or "").strip() if len(el) == 0 else ""
            member = demo.resolve(posixpath.dirname(listing), text) or demo.resolve(base, text) if text else None
            if member:
                found.add(member)
    return {m for m in found if m == scene or not _is_control(m)}


def _is_control(member):
    """A simulation control file or documentation, never scene data."""
    name = posixpath.basename(member).lower()
    return name.endswith(CONTROL) or name.startswith(DOCS) or name.endswith((".html", ".mp4", ".gif"))


def _platform(demo, member):
    root = _xml(demo.read(member), posixpath.basename(member))
    instruments = [el.get("type") or "unknown" for el in root.iter("instrument")]
    planes = list(root.iter("focalplane"))
    captures = sorted({el.get("type") or "unknown" for el in root.iter("capturemethod")})
    polarizers = sorted({el.get("type") for el in root.iter("polarizer") if el.get("type") not in (None, "none")})
    mounts = sorted({el.get("type") or "unknown" for el in root.iter("mount")})
    arrays = []
    for arr in root.iter("detectorarray"):
        x, y = arr.findtext("xelementcount"), arr.findtext("yelementcount")
        arrays.append(f"{x.strip()}x{y.strip()}" if x and y else "unknown")
    channels = sum(1 for _ in root.iter("channel"))
    tags = {el.tag for el in root.iter() if isinstance(el.tag, str)}
    features = [label for tag, label in PLATFORM_FEATURES.items() if tag in tags]
    if any(el.get("type") == "functional" for el in root.iter("detectorarray")):
        features.append("functional detector array")
    if any(el.get("type") == "external" for el in root.iter("clock")):
        features.append("external clock (triggers)")
    return {"instruments": instruments, "focal_planes": len(planes), "captures": captures, "polarizers": polarizers,
            "mounts": mounts, "array": arrays[0] if arrays else "unknown", "channels": channels,
            "features": features}


def _motion(demo, member):
    root = _xml(demo.read(member), posixpath.basename(member))
    if member.endswith(".ppd"):
        entries = len(root.findall("data/entry"))
        jitter = any(len(root.find(t)) for t in ("locationjitter", "orientationjitter") if root.find(t) is not None)
        return {"motion": "static (.ppd)" if entries == 1 else f".ppd waypoints ({entries} entries)",
                "orientation": "euler (.ppd)", "jitter": jitter, "location": "ppd", "entries": entries, "source": None}
    loc = root.find("locationengine")
    ori = root.find("orientationengine")
    source = loc.find("data").get("source") if loc is not None and loc.find("data") is not None else None
    lt = loc.get("type") if loc is not None else "unknown"
    return {"motion": f"FlexMotion {lt}" + (f" ({source})" if source else ""),
            "orientation": ori.get("type") if ori is not None else "unknown", "jitter": False, "location": lt,
            "entries": None, "source": source}


def _atmosphere_file(demo, member):
    root = _xml(demo.read(member), posixpath.basename(member))
    rt = [c.tag for c in root if isinstance(c.tag, str) and c.tag.endswith("radiativetransfer")]
    weather = [c.tag for c in root if isinstance(c.tag, str) and c.tag.endswith("weather")]
    return rt[0] if rt else "unknown", weather[0] if weather else "unknown"


def survey(path):
    """The survey record of one demo zip; never raises (an unreadable layout is `unparsed` with the reason)."""
    path = Path(path)
    rec = {"name": path.stem, "zip_bytes": path.stat().st_size, "verdict": "unparsed", "reason": None}
    try:
        demo = Demo(path)
    except zipfile.BadZipFile as e:
        rec["reason"] = f"not a zip archive ({e})"
        return rec
    rec["uncompressed_bytes"] = sum(i.file_size for i in demo.infos.values())
    try:
        _survey(demo, rec)
    except (Unparsed, KeyError, ValueError, AttributeError, TypeError) as e:
        rec["verdict"], rec["reason"] = "unparsed", str(e) if isinstance(e, Unparsed) else f"{type(e).__name__}: {e}"
    return rec


def _survey(demo, rec):
    sim, sims = _primary_sim(demo)
    base = posixpath.dirname(sim)
    rec["sim"] = posixpath.basename(sim)
    rec["variants"] = len(sims)
    refs = {"scenes": [], "atm": None, "platform": None, "motion": None, "tasks": None}
    plugins = []
    if sim.endswith(".jsim"):
        try:
            doc = json.loads(demo.read(sim))
        except ValueError as e:
            raise Unparsed(f"{rec['sim']} is not JSON ({e})") from e
        entry = doc[0] if isinstance(doc, list) else doc
        for s in entry.get("scene_list", []):
            ref = s.get("inputs") if isinstance(s, dict) else s
            refs["scenes"].append(ref if isinstance(ref, str) else (ref or {}).get("filename", "unknown"))
        for p in entry.get("plugin_list", []):
            name, inputs = p.get("name", "unknown"), p.get("inputs") or {}
            plugins.append(name)
            if name in PLATFORMS:
                refs["platform"], refs["motion"] = inputs.get("platform_filename"), inputs.get("motion_filename")
                refs["tasks"] = inputs.get("tasks_filename")
            if name == "BasicAtmosphere":
                refs["atm"] = inputs.get("atmosphere_filename") or inputs.get("filename")
        rec["format"] = "jsim"
    else:
        root = _xml(demo.read(sim), rec["sim"])
        for child in root:
            ref = child.get("externalfile")
            if child.tag == "scene":
                refs["scenes"].append(ref)
            elif child.tag == "atmosphericconditions":
                refs["atm"] = ref
            elif child.tag in ("platform", "platformmotion", "tasklist"):
                refs[{"platform": "platform", "platformmotion": "motion", "tasklist": "tasks"}[child.tag]] = ref
            elif child.tag == "options":
                plugins.append("(options file)")
        rec["format"] = "sim"
    missing = []

    # scenes
    scenes = [demo.resolve(base, s) for s in refs["scenes"] if isinstance(s, str)]
    if None in scenes:
        raise Unparsed(f"{rec['sim']}: a scene it names is not in the archive (generated, or shipped elsewhere)")
    if not scenes and "EarthGrid" not in plugins:
        raise Unparsed(f"{rec['sim']}: names no scene and no EarthGrid")
    rec["scenes"] = [posixpath.basename(s) for s in scenes]
    members = set()
    for s in scenes:
        members |= _scene_members(demo, s)
    rec["scene_bytes"] = sum(demo.infos[m].file_size for m in members)
    rec["scene_members"] = sorted(members)
    if len(set(scenes)) > 1:
        missing.append("several scenes")
    if not scenes:
        missing.append("no scene file (the Earth is the EarthGrid plugin)")

    # atmosphere and weather
    atmos = [p for p in plugins if p in ATMOSPHERES]
    if rec["format"] == "sim" or "BasicAtmosphere" in atmos:
        atm = demo.resolve(base, refs["atm"]) if refs["atm"] else None
        rt, weather = _atmosphere_file(demo, atm) if atm else ("unknown", "unknown")
        rec["atmosphere"] = f"BasicAtmosphere (.atm, {rt})"
        rec["weather"] = f"{weather} (.atm)"
        missing.append(f"BasicAtmosphere .atm ({rt}, {weather})")
    elif "FourCurveAtmosphere" in atmos:
        rec["atmosphere"], rec["weather"] = "FourCurveAtmosphere", "unknown"
        missing.append("FourCurveAtmosphere")
    elif "NewAtmosphere" in atmos:
        rec["atmosphere"] = "NewAtmosphere"
        rec["weather"] = "unknown"
    else:
        rec["atmosphere"], rec["weather"] = "none named", "unknown"
        missing.append("no atmosphere plugin")
    weathers = [p for p in plugins if p in WEATHERS]
    if weathers:
        rec["weather"] = weathers[0]
        if weathers[0] != "ThermWeather":
            missing.append(weathers[0])
    elif rec["atmosphere"] == "NewAtmosphere":
        missing.append("weather without a ThermWeather file")

    # ephemeris
    eph = [p for p in plugins if p in EPHEMERIDES]
    rec["ephemeris"] = eph[0] if eph else ("implicit (.sim)" if rec["format"] == "sim" else "none named")
    if eph and eph[0] != "SpiceEphemeris":
        missing.append(eph[0])

    # other plugins
    for p in plugins:
        if p not in ATMOSPHERES | EPHEMERIDES | WEATHERS | PLATFORMS:
            missing.append("simulation options file" if p == "(options file)" else f"plugin {p}")

    # platform
    plat = demo.resolve(base, refs["platform"]) if refs["platform"] else None
    if plat is None:
        sensors = [p for p in plugins if p in SENSOR_PLUGINS]
        if not sensors or any(p in PLATFORMS for p in plugins):
            raise Unparsed(f"{rec['sim']}: no platform file in the archive ({refs['platform']})")
        rec.update(instruments=[f"{p} plugin" for p in sensors], mounts=[], array="unknown", channels="unknown",
                   captures=[], motion="none (sensor plugin)", orientation="unknown", moving=False, tasks="unknown",
                   non_imaging=True)
        missing.append("a sensor plugin instead of BasicPlatform")
        rec["missing"] = list(dict.fromkeys(missing))
        rec["verdict"] = "far"
        return
    p = _platform(demo, plat)
    rec.update(instruments=p["instruments"], mounts=p["mounts"], array=p["array"], channels=p["channels"],
               captures=p["captures"])
    non_imaging = sorted({t for t in p["instruments"] if t in NON_IMAGING})
    rec["non_imaging"] = bool(non_imaging)
    for t in non_imaging:
        missing.append(f"non-imaging sensor: {t}")
    imaging = [t for t in p["instruments"] if t not in NON_IMAGING]
    if len(imaging) > 1 or p["focal_planes"] > 1:
        missing.append("several instruments or focal planes")
    for m in p["mounts"]:
        if m != "static":
            missing.append(f"{m} mount")
    for c in p["captures"]:
        if c not in ("simple", "protolidar"):
            missing.append(f"capture method {c}")
    for pol in p["polarizers"]:
        missing.append(f"polarizer {pol}")
    missing += p["features"]

    # motion
    mot = demo.resolve(base, refs["motion"]) if refs["motion"] else None
    if mot is None:
        raise Unparsed(f"{rec['sim']}: no motion file in the archive ({refs['motion']})")
    m = _motion(demo, mot)
    rec["motion"], rec["orientation"] = m["motion"], m["orientation"]
    rec["moving"] = not (m["location"] in ("ppd", "fixed") and (m["entries"] in (None, 1)))
    if m["location"] == "ppd" and m["entries"] != 1:
        missing.append(".ppd waypoint motion")
    if m["jitter"]:
        missing.append("platform jitter")
    if m["location"] == "waypoints":
        missing.append("STK report import" if m["source"] == "stk_report" else "waypoints motion")
    elif m["location"] == "sgp4":
        missing.append("sgp4 location engine")
    elif m["location"] not in ("ppd", "fixed"):
        missing.append(f"location engine {m['location']}")
    if m["orientation"] == "quaternions":
        missing.append("quaternion orientation")
    elif m["orientation"] == "lookat" and m["location"] == "fixed":
        missing.append("LookAt orientation from a fixed location")

    # tasks
    tasks = demo.resolve(base, refs["tasks"]) if refs["tasks"] else None
    rec["tasks"] = len(_xml(demo.read(tasks), "tasks").findall("task")) if tasks else "unknown"

    rec["missing"] = list(dict.fromkeys(missing))
    n = len(rec["missing"])
    rec["verdict"] = "far" if rec["non_imaging"] or n >= 2 else ("near" if n == 1 else "ready")


def survey_all(folder):
    return [survey(p) for p in sorted(Path(folder).glob("*.zip"))]


def _cell(value):
    if value is None or value == []:
        return "-"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value).replace("|", "/")


def recommendations(records):
    """The recommended first three: (i) the simplest ready/near static ground-imaging demo with the smallest scene,
    (ii) a near demo whose one missing feature is an atmosphere or weather plugin, (iii) a moving-platform demo with
    the fewest missing features."""
    parsed = [r for r in records if r["verdict"] in ("ready", "near", "far") and not r.get("non_imaging")]
    static = sorted((r for r in parsed if r["verdict"] in ("ready", "near") and not r["moving"]),
                    key=lambda r: (len(r["missing"]), r["scene_bytes"], r["name"]))
    family = static[0]["missing"][0].split()[0] if static and static[0]["missing"] else None
    atmos = sorted((r for r in parsed if r["verdict"] == "near" and
                    re.search(r"Atmosphere|Weather|weather", r["missing"][0])),
                   key=lambda r: (r["missing"][0].split()[0] == family, r["scene_bytes"], r["name"]))
    moving = sorted((r for r in parsed if r["moving"]), key=lambda r: (len(r["missing"]), r["scene_bytes"], r["name"]))
    picks = []
    for group in (static, atmos, moving):
        pick = next((r for r in group if r["name"] not in {p["name"] for p in picks}), None)
        if pick:
            picks.append(pick)
    return picks


def placement(r):
    """The library placement step 9's vocabulary gives a demo: the scene directory as a `directory` asset, the other
    files the run needs as `file` assets, under manifold_config_repo/demos/<Name>/."""
    if not r["scenes"]:
        return f"no scene directory; the platform, motion, tasks and atmosphere files as `file` assets under `demos/{r['name']}/`"
    scene = r["scenes"][0]
    stem = scene.removesuffix(".scene")
    return (f"directory asset `demos/{r['name']}/scenes/{stem}/` ({len(r['scene_members'])} archive members: "
            f"`{scene}` and the files it references, {SIZE(r['scene_bytes'])} MB); the platform, motion, tasks and "
            f"atmosphere files the run reads as `file` assets under `demos/{r['name']}/`")


def render(records, demos_label="external/dirsig/demos/zips"):
    """The coverage table document (markdown). Deterministic for the same records."""
    counts = Counter(r["verdict"] for r in records)
    needed, unlocks = Counter(), Counter()
    for r in records:
        for f in r.get("missing", []):
            needed[f] += 1
        if r["verdict"] == "near":
            unlocks[r["missing"][0]] += 1
    lines = ["# DIRSIG demo coverage", "",
             f"Which of DIRSIG's {len(records)} shipped demos the SDK could regenerate today, and what each still needs. Generated by `python scripts/survey_demos.py --out docs/DIRSIG_demo_coverage.md` from the demo archives in the DIRSIG installation (`{demos_label}`), read in place; regenerate it after a loader feature lands. It is derived from file names, plugin and element names, counts and sizes only, and contains no demo file contents.",
             "",
             "A verdict compares a demo's simulation file, platform, motion and atmosphere with what the SDK's engine body and loader cover (the run-spec contract's engine block and `run_spec.resolve_run`): `ready` needs nothing new (one scene, `NewAtmosphere` with a `ThermWeather` file, SPICE ephemeris, static or orbit motion, one imaging instrument); `near` needs exactly one missing feature; `far` needs two or more, or has a non-imaging sensor; `unparsed` means the layout was not understood, with the reason. A value that cannot be read is `unknown`. A legacy `.sim` carries its atmosphere and uniform weather in one `.atm` file, counted as one feature, and its ephemeris is implicit. Platform features are recognized by element name (lens distortion, point spread function, field selectors and so on); a behaviour with no distinct element, such as a rolling shutter, is not seen, so a `near` verdict is an upper bound on readiness. Scene size is the `.scene` file and the archive members it references.",
             "", "## Summary", "", "| Verdict | Demos |", "|---|---|"]
    lines += [f"| `{v}` | {counts.get(v, 0)} |" for v in VERDICT_ORDER]
    lines += ["", "## Missing features, by the demos each would unlock", "",
              "`Unlocks` counts the `near` demos for which the feature is the only one missing; `Needed by` counts every demo that needs it.",
              "", "| Feature | Unlocks | Needed by |", "|---|---|---|"]
    for f in sorted(needed, key=lambda f: (-unlocks[f], -needed[f], f)):
        lines.append(f"| {_cell(f)} | {unlocks[f]} | {needed[f]} |")
    lines += ["", "## All demos", "",
              "| Demo | Verdict | Simulation | Zip MB | Scene MB | Scenes | Atmosphere | Weather | Ephemeris | Motion | Orientation | Mounts | Instruments | Array | Channels | Tasks | Missing features |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    order = {v: i for i, v in enumerate(VERDICT_ORDER)}
    for r in sorted(records, key=lambda r: (order[r["verdict"]], r["name"])):
        if r["verdict"] == "unparsed":
            lines.append(f"| {r['name']} | `unparsed` | - | {SIZE(r['zip_bytes'])} | - | - | - | - | - | - | - | - | - | - | - | - | {_cell(r['reason'])} |")
            continue
        sim = f"{r['sim']}" + (f" (+{r['variants'] - 1})" if r["variants"] > 1 else "")
        lines.append(" | ".join(["", r["name"], f"`{r['verdict']}`", _cell(sim), SIZE(r["zip_bytes"]),
                                 SIZE(r["scene_bytes"]), _cell(r["scenes"]), _cell(r["atmosphere"]), _cell(r["weather"]),
                                 _cell(r["ephemeris"]), _cell(r["motion"]), _cell(r["orientation"]), _cell(r["mounts"]),
                                 _cell(r["instruments"]), _cell(r["array"]), _cell(r["channels"]), _cell(r["tasks"]),
                                 _cell(r["missing"]), ""]).strip())
    picks = recommendations(records)
    lines += ["", "## Recommended first three", ""]
    why = ["the simplest static ground-imaging demo that is `ready` or `near`, with the smallest scene",
           "a `near` demo whose one missing feature is an atmosphere or weather plugin other than the first's",
           "a moving-platform demo with the fewest missing features"]
    for i, (r, reason) in enumerate(zip(picks, why), 1):
        missing = ", ".join(r["missing"]) or "none"
        note = ""
        if r["name"] == "StkImport1":
            note = " Its orbit has already been reconstructed from a TLE in `notebooks/dirfm_tutorials/tutorial_orbit_to_ground.ipynb`."
        lines.append(f"{i}. **{r['name']}** (`{r['verdict']}`): {reason}. Missing: {missing}. Scene size {SIZE(r['scene_bytes'])} MB; reference-run cost unknown (not stated in the archive's file names or sizes). Placement: {placement(r)}.{note}")
    lines += ["", "`StkImport1` (a WorldView-2 pass from STK reports) has been reconstructed from a TLE in `notebooks/dirfm_tutorials/tutorial_orbit_to_ground.ipynb`; `Ssa1` to `Ssa3` image a satellite from a satellite, which needs space-object imaging against space (a backlog item) as well as their missing features above."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--demos", default=str(DEMOS))
    ap.add_argument("--out", default=None)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if --out (default docs/DIRSIG_demo_coverage.md) differs from a fresh survey")
    args = ap.parse_args(argv)
    folder = Path(args.demos)
    if not folder.is_dir():
        print(f"no demo archives at {folder} (link the DIRSIG installation as external/dirsig)", file=sys.stderr)
        return 2
    try:
        label = folder.resolve().relative_to(ROOT).as_posix() if folder.is_relative_to(ROOT) else str(folder)
    except ValueError:
        label = str(folder)
    if folder.resolve() == DEMOS.resolve():
        label = "external/dirsig/demos/zips"
    text = render(survey_all(folder), label)
    if args.check:
        out = Path(args.out) if args.out else OUT
        old = out.read_text() if out.is_file() else ""
        want = text + ("\n" + old[old.index(KEPT):] if KEPT in old else "")
        if old != want:
            print(f"stale: {out} (regenerate with scripts/survey_demos.py --out {out})")
            return 1
        return 0
    if args.out:
        out = Path(args.out)
        old = out.read_text() if out.is_file() else ""
        if KEPT in old:                                       # keep the hand-written findings section and after
            text += "\n" + old[old.index(KEPT):]
        out.write_text(text)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
