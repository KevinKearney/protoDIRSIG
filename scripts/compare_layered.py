#!/usr/bin/env python3
"""Render a DIRSIG demo in the layered form and as authored (pass-through), and compare the images.

    python scripts/compare_layered.py DensityMap1 [PointCollectors2 ...] [--work DIR] [--seed 1] [--timeout 1800]

Per demo, one render at a time, everything under `--work` (default: the state directory's
`manifold/layered-comparison/`, outside the repository):

1. The demo's archive (`$DIRSIG_HOME/demos/zips/<Name>.zip`) is extracted into a private engine-asset library,
   `<work>/<Name>/config_repo/demo_dirs/<Name>/`.
2. Layers are derived from the demo's own files and written under `<work>/<Name>/layers/` (a recipe, a scenario and an
   engine profile; `manifold_sensors/` is the sensor library): the scene and the platform by reference with stamped
   hashes (the platform `as_authored`), the atmosphere as `basic` with `uniform` read from the demo's `.atm`
   (`basic_atmosphere.read_atm`), a static pose from its `.ppd`, the epoch and task windows from its `.tasks`, and
   `engine.run.seed` = `--seed`. The values are the demo's (licensed); they are written only under `--work`, never into
   the repository. The descriptor's sensor is a library stand-in (`STAND_IN_SENSOR`): with an as-authored platform it
   is checked but not applied.
3. Three renders through `Workspace.local` over that library: the layered recipe, the pass-through form at the same
   seed, and the pass-through form without a seed (the reference the demo sweep recorded).
4. Each image the two forms both wrote is compared: shape, per-band mean of each, maximum absolute difference, the
   fraction of pixels differing (any band), and the sha256 of each file. The known input differences (`KNOWN`, plus
   what the derivation found) are listed with the numbers. Nothing is tuned to make the numbers match.
5. Attribution, when the layered image differs from the same-seed pass-through one: the layered job's own input folder
   is copied and rendered once more by `dirsig5` directly (same seed, a scratch HOME) with the demo's own motion file
   in place of the generated one, and its image digests are compared with the pass-through's. A diagnostic outside the
   recipe and the SDK; the recipe is not changed.

Results go to `<work>/results.json` and a markdown table to stdout; `docs/DIRSIG_layered_comparison.md` holds the
numbers and digests from a run of this script (hand-copied; no output byte, no demo value). A render that exceeds
`--timeout` is cancelled, and a render that fails or times out stops that demo (recorded as `stopped`, with the error).
"""
import argparse
import hashlib
import json
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import lxml.etree as et
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "packages" / d / "src") for d in ("core", "sim")]   # the manifold namespace, uninstalled
sys.path.insert(0, str(ROOT / "scripts"))

from compare_outputs import header_for, read_envi                              # noqa: E402
from manifold.core.dirhash import directory_digest                            # noqa: E402
from manifold.core.spectral import sha256_file                                # noqa: E402
from manifold.engines.dirsig.basic_atmosphere import read_atm                 # noqa: E402
from manifold.sim import Workspace                                             # noqa: E402
from manifold.sim.workspace import default_work_root                          # noqa: E402

GENERATOR = {"tool": "dirfm", "revision": "93195cee1ccc4f31a214e114d94c493a1d4cc22f", "spec_schema": "dirsig-engine/1"}
STAND_IN_SENSOR = "synthetic_600_200_vis_1920.yaml"
STAND_IN_ENTRY = "synthetic-600-200-vis-1920"
# The simulation file each demo's reference ran (docs/DIRSIG_demo_sweep.md).
SIMULATION = {"DensityMap1": "demo.sim", "MaterialMap1": "w_mixing.sim", "PointCollectors2": "framing.jsim"}
KNOWN = [
    ("simulation file: the layered job's jsim is written by dirfm (plugins BasicPlatform, BasicAtmosphere, and "
     "SpiceEphemeris unless the .atm fixes the Sun), not the demo's own file"),
    ("motion and tasks: regenerated from the derived values by dirfm (PlatformPosition .ppd, TASKS .tasks with the epoch "
     "in UTC), not the demo's files; PlatformPosition writes positions to 3 and Euler angles to 6 decimals"),
    (".atm: written from the derived uniform values; the demo's <metadata>, <turbulence> and lunar ephemeris values are "
     "not carried"),
    ("scene compile: dirfm runs scene2hdf with --threads <cpu count> and the seed; the pass-through runner runs it with "
     "neither"),
    ("cache: the layered job runs with the user's HOME (DIRSIG material cache); the pass-through run with a per-run HOME"),
    ("descriptor: the layered run's sensor-spec is a library stand-in, checked but not applied (as_authored platform); "
     "its collection is the scene origin and the pose's height"),
]


def _dirsig_home():
    from manifold.engines.dirsig.adapter import locate_dirsig
    home = locate_dirsig()["home"]
    if home is None:
        raise SystemExit("no DIRSIG installation found")
    return Path(home)


def extract(name, target):
    """The demo's archive extracted into `target` (replaced). Returns `target`."""
    zpath = _dirsig_home() / "demos" / "zips" / f"{name}.zip"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    with zipfile.ZipFile(zpath) as zf:
        for m in zf.infolist():
            if m.is_dir() or not m.filename.startswith(f"{name}/"):
                continue
            rel = Path(m.filename[len(name) + 1:])
            if rel.is_absolute() or ".." in rel.parts:
                raise SystemExit(f"{zpath}: unsafe member {m.filename}")
            out = target / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(zf.read(m))
    return target


def simulation_inputs(demo_dir, simulation):
    """{scene, atmosphere, platform, motion, tasks}: the files a `.sim` or a `.jsim` names, relative to `demo_dir`."""
    path = demo_dir / simulation
    if simulation.endswith(".sim"):
        root = et.parse(str(path)).getroot()
        get = {t: root.find(t).get("externalfile") for t in ("scene", "atmosphericconditions", "platform",
                                                              "platformmotion", "tasklist")}
        names = {"scene": get["scene"], "atmosphere": get["atmosphericconditions"], "platform": get["platform"],
                 "motion": get["platformmotion"], "tasks": get["tasklist"]}
    else:
        doc = json.loads(path.read_text())[0]
        plugins = {p["name"]: p.get("inputs", {}) for p in doc["plugin_list"]}
        extra = sorted(set(plugins) - {"BasicAtmosphere", "BasicPlatform"})
        if extra:
            raise ValueError(f"{simulation}: plugins the layered form does not write: {extra}")
        bp = plugins["BasicPlatform"]
        names = {"scene": doc["scene_list"][0]["inputs"], "atmosphere": plugins["BasicAtmosphere"]["atmosphere_filename"],
                 "platform": bp["platform_filename"], "motion": bp["motion_filename"], "tasks": bp["tasks_filename"]}
    return {k: (path.parent / v).resolve().relative_to(demo_dir.resolve()).as_posix() for k, v in names.items()}


def static_pose(ppd):
    """The single-entry `.ppd`'s scene-frame position and `sceneenu` Euler orientation, as `engine.motion`."""
    root = et.parse(str(ppd)).getroot()
    data = root.find("data")
    entries = data.findall("entry")
    if len(entries) != 1:
        raise ValueError(f"{ppd.name}: {len(entries)} entries; the layered form generates one static pose")
    for jitter in ("locationjitter", "orientationjitter"):
        if root.find(jitter) is not None and len(root.find(jitter)):
            raise ValueError(f"{ppd.name}: {jitter} is not empty")
    attrs = {k: data.get(k) for k in ("rotationframe", "rotationorder", "angularunits", "angletype", "spatialunits")}
    if attrs["rotationframe"] != "sceneenu" or attrs["angletype"] != "absolute" or attrs["spatialunits"] != "meters":
        raise ValueError(f"{ppd.name}: {attrs} is not a scene-ENU absolute pose in metres")
    loc = entries[0].find("position/location")
    if loc.get("frame") != "scene":
        raise ValueError(f"{ppd.name}: location frame {loc.get('frame')!r}")
    xyz = [float(loc.findtext(f"point/{a}")) for a in "xyz"]
    angles = [float(entries[0].findtext(f"orientation/eulerangles/cartesiantriple/{a}")) for a in "xyz"]
    return {"kind": "static", "position": {"frame": "scene", "xyz": xyz},
            "orientation": {"kind": "euler", "euler": {"order": attrs["rotationorder"], "units": attrs["angularunits"],
                                                       "frame": "sceneenu", "angles": angles}}}


def epoch_and_windows(tasks):
    """The `.tasks` reference time (UTC, ISO 8601 with Z) and its relative task windows."""
    root = et.parse(str(tasks)).getroot()
    ref = root.find("reference/datetime")
    if ref.get("type") != "absolute":
        raise ValueError(f"{tasks.name}: reference time is not absolute")
    epoch = datetime.fromisoformat(ref.text.strip()).astimezone(timezone.utc)
    windows = []
    for t in root.findall("task"):
        start, stop = t.find("start/datetime"), t.find("stop/datetime")
        if start.get("type") != "relative" or stop.get("type") != "relative":
            raise ValueError(f"{tasks.name}: a task time is not relative")
        windows.append({"start": float(start.text), "stop": float(stop.text)})
    return epoch.strftime("%Y-%m-%dT%H:%M:%S") + (f".{epoch.microsecond:06d}" if epoch.microsecond else "") + "Z", windows


def scene_origin(scene):
    loc = et.parse(str(scene)).getroot().find("sceneorigin/location")
    return float(loc.findtext("latitude")), float(loc.findtext("longitude"))


def write_layers(name, layers, config_repo, seed):
    """The demo's recipe, scenario and engine profile under `layers` (its derivation notes returned)."""
    demo_dir = config_repo / "demo_dirs" / name
    files = simulation_inputs(demo_dir, SIMULATION[name])
    uniform = read_atm(demo_dir / files["atmosphere"])
    motion = static_pose(demo_dir / files["motion"])
    epoch, windows = epoch_and_windows(demo_dir / files["tasks"])
    lat, lon = scene_origin(demo_dir / files["scene"])
    def ref(rel):
        return f"demo_dirs/{name}/{rel}"
    scene_dir = (demo_dir / files["scene"]).parent
    engine = {"generator": GENERATOR,
              "scenes": [{"ref": {"name": ref(files["scene"]), "content_hash": directory_digest(scene_dir)},
                          "offset": [0, 0, 0]}],
              "platform": {"ref": {"name": ref(files["platform"]),
                                   "content_hash": sha256_file(demo_dir / files["platform"])},
                           "library_entry": name.lower(), "output_prefix": "", "split_channels": False,
                           "as_authored": True},
              "motion": motion, "tasks": {"windows": windows},
              "atmosphere": {"plugin": "basic", "uniform": uniform}}
    if "fixed_ephemeris" not in uniform:
        engine["ephemeris"] = {"plugin": "spice"}
    engine["run"] = {"seed": seed}
    key = f"layered_{name.lower()}"
    for sub in ("recipes", "scenarios", "engine_profiles"):
        (layers / sub).mkdir(parents=True, exist_ok=True)
    collection = {"epoch": epoch,
                  "platform": {"class": "aircraft", "position": {
                      "frame": "geodetic", "datum": "WGS84",
                      "latitude": {"value": lat, "provenance": "modeled"},
                      "longitude": {"value": lon, "provenance": "modeled"},
                      "altitude": {"value": motion["position"]["xyz"][2], "provenance": "modeled"},
                      "altitude_reference": "ellipsoid"}},
                  "geometry": {"regime": "oblique"}, "illumination": {"regime": "daylight"},
                  "atmosphere": {"regime": "unspecified"}, "background": {"regime": "synthetic"}, "targets": []}
    (layers / "scenarios" / f"{key}.yaml").write_text(yaml.safe_dump({"collection": collection}, sort_keys=False))
    (layers / "engine_profiles" / f"{key}.yaml").write_text(yaml.safe_dump(
        {"origin": {"kind": "synthetic", "engine": "dirsig"}, "engine": engine}, sort_keys=False))
    recipe = {"compose": "compose/1",
              "meta": {"name": f"layered-{name.lower()}", "tags": ["dirsig-demo", name.lower(), "layered-comparison"],
                       "description": f"DIRSIG demo {name} in the layered form, derived by scripts/compare_layered.py.\n"},
              "sensor": STAND_IN_SENSOR, "scenario": key, "engine_profile": key,
              "settings": [{"entry_id": STAND_IN_ENTRY, "exposure_time": {"value": 0.005, "provenance": "specified"},
                            "frame_rate": {"value": 1000, "provenance": "specified"},
                            "gain": {"value": 1, "provenance": "specified"},
                            "black_level": {"value": 0, "provenance": "specified"}}],
              "fidelity": {"modeled": [], "approximated": [],
                           "absent": ["the descriptor's sensor is a stand-in; the demo's platform is used as authored"],
                           "valid_for": "A layered-versus-pass-through comparison only.\n"}}
    (layers / "recipes" / f"{key}.yaml").write_text(yaml.safe_dump(recipe, sort_keys=False))
    notes = [f"simulation {SIMULATION[name]}: {files}",
             f"atmosphere: {sorted(uniform)}" + ("" if "fixed_ephemeris" in uniform else "; no fixed Sun in the .atm, "
                                                 "so the layered job adds SpiceEphemeris"),
             f"tasks: {len(windows)} window(s)"]
    if SIMULATION[name].endswith(".jsim") and "fixed_ephemeris" in uniform:
        notes.append("the demo's jsim names no ephemeris plugin; DIRSIG takes the .atm's fixed Sun in both forms")
    return key, notes


def passthrough_spec(name, config_repo, seed):
    spec = yaml.safe_load((ROOT / "manifold_run_specs" / "demo_pointcollectors2_passthrough.yaml").read_text())
    meta = spec["descriptor"]["meta"]
    meta["name"] = f"compare-{name.lower()}-passthrough" + ("" if seed is None else f"-seed{seed}")
    meta["tags"] = ["dirsig-demo", name.lower(), "passthrough", "layered-comparison"]
    meta["description"] = f"DIRSIG demo {name} ({SIMULATION[name]}) run as authored by scripts/compare_layered.py.\n"
    spec["engine"]["passthrough"] = {"directory": {"name": f"demo_dirs/{name}",
                                                   "content_hash": directory_digest(config_repo / "demo_dirs" / name)},
                                     "simulation": SIMULATION[name]}
    spec["engine"].pop("run", None)
    if seed is not None:
        spec["engine"]["run"] = {"seed": seed}
    return spec


def render(ws, target, timeout):
    t0 = time.monotonic()
    status = ws.submit_run(target)
    try:
        final = ws.wait(status.run_id, timeout=timeout, poll=1.0)
    except TimeoutError:
        ws.cancel_run(status.run_id)
        return {"run_id": status.run_id, "state": f"timed out after {timeout} s (cancelled)",
                "wall_s": round(time.monotonic() - t0, 1)}
    files = {a.name: Path(a.uri.removeprefix("file://")) for a in final.artifacts if a.name != "run_spec.json"}
    rec = {"run_id": status.run_id, "state": final.state, "wall_s": round(time.monotonic() - t0, 1),
           "files": {n: str(p) for n, p in files.items()},
           "sha256": {n: a.sha256 for n, a in ((a.name, a) for a in final.artifacts) if n != "run_spec.json"}}
    if final.state != "rendered":
        rec["errors"] = [e.get("detail") if isinstance(e, dict) else getattr(e, "detail", str(e)) for e in final.errors]
    return rec


def _images(rec):
    """{image name: path} of the ENVI images (a `.img` with a header) a render wrote, keyed by file name."""
    out = {}
    for p in rec.get("files", {}).values():
        p = Path(p)
        if p.suffix == ".img" and header_for(p) is not None:
            out[p.name] = p
    return out


def compare(a, b):
    """Shape, per-band means, maximum absolute difference and fraction of pixels differing of two ENVI images."""
    x, y = read_envi(a), read_envi(b)
    rec = {"shape_a": list(x.shape), "shape_b": list(y.shape),
           "mean_a": [float(v) for v in x.reshape(x.shape[0], -1).mean(axis=1)],
           "mean_b": [float(v) for v in y.reshape(y.shape[0], -1).mean(axis=1)],
           "sha256_a": hashlib.sha256(Path(a).read_bytes()).hexdigest(),
           "sha256_b": hashlib.sha256(Path(b).read_bytes()).hexdigest()}
    if x.shape == y.shape:
        d = (x != y) & ~(np.isnan(x) & np.isnan(y))
        rec["max_abs_diff"] = float(np.nanmax(np.abs(x - y))) if x.size else 0.0
        rec["fraction_pixels_differ"] = float(d.any(axis=0).mean())
    return rec


def attribute_motion(ws, layered, demo_dir, motion_rel, seed, scratch, timeout):
    """Digests of the layered job re-rendered with the demo's own motion file (see the module docstring, step 5)."""
    import os
    import subprocess
    from manifold.engines.dirsig.adapter import locate_dirsig
    src = ws.backend.store.run_dir(layered["run_id"]) / "input"
    if scratch.exists():
        shutil.rmtree(scratch)
    shutil.copytree(src, scratch / "input", symlinks=True)
    shutil.copy2(demo_dir / motion_rel, scratch / "input" / "motion" / "motion.ppd")
    (scratch / "home").mkdir()
    out = scratch / "output"
    out.mkdir()
    cmd = [str(Path(locate_dirsig()["home"]) / "bin" / "dirsig5"), f"--output_folder={out}", "--random_seed", str(seed),
           "example.jsim"]
    with open(scratch / "dirsig5.log", "w") as log:
        rc = subprocess.run(cmd, cwd=scratch / "input", stdout=log, stderr=subprocess.STDOUT, timeout=timeout,
                            env={**os.environ, "HOME": str(scratch / "home")}, check=False).returncode
    return {"returncode": rc, "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in sorted(out.glob("*.img"))}}


def run_demo(name, work, seed, timeout):
    base = work / name
    config_repo, layers = base / "config_repo", base / "layers"
    extract(name, config_repo / "demo_dirs" / name)
    key, notes = write_layers(name, layers, config_repo, seed)
    ws = Workspace.local(library=layers, config_repo=config_repo, work=base / "runs", sensor_library=ROOT / "manifold_sensors")
    spec_dir = base / "specs"
    spec_dir.mkdir(exist_ok=True)
    out = {"demo": name, "simulation": SIMULATION[name], "seed": seed, "derivation": notes, "known": KNOWN, "runs": {}}
    targets = {"layered": key}
    for label, s in (("passthrough_same_seed", seed), ("passthrough_no_seed", None)):
        from manifold.core.compose import dump
        path = spec_dir / f"{label}.yaml"
        path.write_text(dump(passthrough_spec(name, config_repo, s), label))
        targets[label] = str(path)
    for label, target in targets.items():                                  # one render at a time
        out["runs"][label] = render(ws, target, timeout)
        if out["runs"][label]["state"] != "rendered":                 # a failure or a timeout is a result; stop here
            out["stopped"] = f"{label}: {out['runs'][label]['state']}"
            return out
    layered = _images(out["runs"]["layered"])
    out["comparisons"] = {}
    for label in ("passthrough_same_seed", "passthrough_no_seed"):
        other = _images(out["runs"][label])
        out["comparisons"][label] = {n: compare(layered[n], other[n]) for n in sorted(layered.keys() & other.keys())}
        out["comparisons"][label]["only_layered"] = sorted(layered.keys() - other.keys())
        out["comparisons"][label]["only_passthrough"] = sorted(other.keys() - layered.keys())
    same = out["comparisons"]["passthrough_same_seed"]
    if any(isinstance(c, dict) and c["sha256_a"] != c["sha256_b"] for c in same.values()):
        demo_dir = config_repo / "demo_dirs" / name
        motion = simulation_inputs(demo_dir, SIMULATION[name])["motion"]
        rec = attribute_motion(ws, out["runs"]["layered"], demo_dir, motion, seed, base / "attribution", timeout)
        target = {n: c["sha256_b"] for n, c in same.items() if isinstance(c, dict)}
        rec["matches_passthrough_same_seed"] = {n: rec["sha256"].get(n) == s for n, s in target.items()}
        out["attribution_demo_motion"] = rec
    return out


def table(results):
    lines = [("| Demo | Image | Against | Shape (bands, lines, samples) | Mean layered | Mean pass-through | "
              "Max abs difference | Pixels differing | Identical |"), "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        for label, comps in r.get("comparisons", {}).items():
            for img, c in comps.items():
                if not isinstance(c, dict) or "max_abs_diff" not in c:
                    continue
                same = c["sha256_a"] == c["sha256_b"]
                lines.append(f"| {r['demo']} | {img} | {label} | {tuple(c['shape_a'])} vs {tuple(c['shape_b'])} | "
                             f"{', '.join(f'{v:.6g}' for v in c['mean_a'])} | {', '.join(f'{v:.6g}' for v in c['mean_b'])} | "
                             f"{c['max_abs_diff']:.6g} | {c['fraction_pixels_differ']:.4%} | "
                             f"{'yes' if same else 'no'} |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("demos", nargs="+", choices=sorted(SIMULATION))
    ap.add_argument("--work", type=Path, default=None)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=1800.0)
    a = ap.parse_args(argv)
    work = a.work or default_work_root().parent / "layered-comparison"
    if work.resolve().is_relative_to(ROOT.resolve()):
        raise SystemExit(f"--work {work} is inside the repository; native-size renders are written outside it")
    work.mkdir(parents=True, exist_ok=True)
    results = [run_demo(n, work, a.seed, a.timeout) for n in a.demos]
    (work / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True))
    print(table(results))
    for r in results:
        if "stopped" in r:
            print(f"{r['demo']}: stopped ({r['stopped']}): {(r['runs'][r['stopped'].split(':')[0]].get('errors') or [''])[0][:400]}")
        if "attribution_demo_motion" in r:
            print(f"{r['demo']}: with the demo's own motion file, identical to the same-seed pass-through: "
                  f"{r['attribution_demo_motion']['matches_passthrough_same_seed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
