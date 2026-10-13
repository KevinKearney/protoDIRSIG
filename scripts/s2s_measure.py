#!/usr/bin/env python3
"""Space-to-space measurement harness: render family specs one at a time, reduce each product, keep one results file.

    python scripts/s2s_measure.py run NAME [NAME ...] [--work DIR] [--runs DIR[:PREFIX] ...] [--via workspace]
    python scripts/s2s_measure.py list                  every measurable spec, and whether the results file has it
    python scripts/s2s_measure.py --check               the results file is well formed, every spec id exists, and
                                                        every expected value recomputes from the specs; exit 1 if not

`NAME` is a spec name from `manifold_run_specs/s2s/index.json` (families I, II and III; the SatSim specs are
pass-through runs of another engine and are not measured here). For each name, in order and one at a time:

1. A completed run is looked for: `<root>/<PREFIX><NAME>/` under each `--runs` root, then `<work>/<NAME>/`. A run
   folder counts when its `spec.yaml` parses to the committed spec and `output/` holds the rendered image; it is read,
   never rendered again.
2. Otherwise the committed spec is rendered through `Simulation.run(threads=1)` into `<work>/<NAME>/` (default work
   root: the state directory's `manifold/s2s-measure/`, outside the repository), with `HOME` set to a per-run folder
   so DIRSIG's material caches stay in the run. Every family spec states one thread (`resources.cpu_threads: 1`) and
   seed 1 (`engine.run.seed`), so a render repeats bit for bit (docs/DIRSIG_determinism.md).
   With `--via workspace` the spec goes through the SDK API instead (`Workspace.local`, `submit_run`, `wait`, the
   artifacts saved with `save_artifact`) into `<work>/<NAME>--workspace/`; the spec's thread count and seed apply the
   same way, so the image is the same bytes (checked on the exposure axis, docs/Space_to_space_characterization.md).
   A family is not a sweep: `submit_sweep` takes a recipe, whose one axis is the sensor (compose/1), and the family's
   specs are written outside the composer so that they have no id-snapshot entry (BACKLOG).
3. The product is reduced (below) and its record replaces any record of the same spec in
   `docs/data/s2s_results.jsonl` (one JSON object per line, sorted by spec name).

A record: `spec` (the name), `run_id`, `family`, `source` (the run folder it was read from, home-relative; a
`--workspace` folder was rendered through the SDK API),
`product` (sha256 of the image and of each truth image), `full_pixel` (the signal of a pixel wholly on a plate of
reflectance `REFLECTANCE` facing the Sun at the zenith, e-/m^2 of focal plane, from the run's own job platform:
`full_pixel_signal`), then the primary measurement `method`, `measured`, `expected`, `ratio` (measured / expected) and
`tolerance` (null unless the method defines one), and `also`, the further measurements in the same shape. Expected
values come from the spec's own numbers through `scripts/s2s_scenarios.py` (`expected`, `expected2`, `expected3`).

Methods (values in full pixels unless stated):
- `flux_closure`: the image sum over `full_pixel`, against the expected footprint (projected area over the pixel
  footprint squared, times the cosine of the solar zenith for a plate; the Lambertian sphere's phase function times its
  full-phase footprint for a sphere). Family II's blur group sums a box about the target (its rows, and its columns
  out to the sweep and 6 pixels; the bars, the small plate and the static group's marker plate lie outside), the look
  group the target's rows; family III's background group the 100 x 100 pixels about the sphere.
- `half_level_count`: pixels at or above half of `full_pixel` x cos(solar zenith), against the same expected footprint
  (a plate only; edge pixels make it fall short at short range).
- `peak`: the brightest pixel over `full_pixel` x cos(solar zenith), against 1 (a resolved plate only).
- `streak_length`: family II blur group: the boxcar sweep length (pixels) of the target plate fitted to the mean row
  profile (an exact pixel-overlap model of a plate swept uniformly over the exposure), against speed x exposure over
  the footprint. The model has no optics: DIRSIG's own spread (docs/Space_to_space_characterization.md, round 30)
  reads as about 0.6 pixel of sweep on a static plate, so short sweeps read long.
- `background_period`: family II look group: the mean spacing (pixels) of the bars' rising edges at a quarter of
  `full_pixel` in rows beside the target, against the bar period x cos(look) over the background's footprint.
- `bar_level`: family III background group: the median of the brightest tenth of the barred rows over `full_pixel`,
  against the bars' reflectance ratio (0.25 / 0.5) x cos(solar zenith).
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "packages" / d / "src") for d in ("core", "sim")]
sys.path.insert(0, str(ROOT / "scripts"))

import s2s_scenarios as s2s                                                    # noqa: E402
from compare_outputs import header_for, read_envi                             # noqa: E402

RESULTS = ROOT / "docs" / "data" / "s2s_results.jsonl"
INDEX = s2s.OUT / "index.json"
RECORD_KEYS = ("spec", "run_id", "family", "source", "product", "full_pixel", "method", "measured", "expected", "ratio",
               "tolerance", "also")
MEASUREMENT_KEYS = ("method", "measured", "expected", "ratio", "tolerance")
H, C = 6.62607015e-34, 2.99792458e8


# --- the specs ----------------------------------------------------------------------------------------------------

def index():
    """{name: index entry} of the DIRSIG specs (families 1, 2 and 3)."""
    return {e["name"]: e for e in json.loads(INDEX.read_text()) if e.get("engine", "dirsig") == "dirsig"}


def family(entry):
    return entry.get("family", 1)


def point(entry):
    """The grid point of an index entry: its parameters without the name, run id and family keys."""
    return {k: v for k, v in entry.items() if k not in ("name", "run_id", "family", "engine")}


def expectations(entry):
    """{method: expected value} for an index entry, from the spec's own numbers (s2s_scenarios)."""
    fam, p = family(entry), point(entry)
    out = {}
    if fam == 1:
        ex = s2s.expected(p)
        if ex["footprint_px"] is None:                 # an orbit point: range and speed are the TLE's
            return out
        out["flux_closure"] = ex["footprint_px"] * ex["cos_sun"]
        if p["object_class"] == "hyperresolved":
            out["half_level_count"] = ex["footprint_px"]
            out["peak"] = 1.0
    elif fam == 2:
        ex = s2s.expected2(p)
        out["flux_closure"] = ex["footprint_px"]
        if p["kind"] == "blur":
            out["streak_length"] = ex["target_blur_px"]
        if p["kind"] == "look":
            out["background_period"] = ex["background_period_px"]
    else:
        ex = s2s.expected3(p)
        out["flux_closure"] = ex["expected_px"]
        if p["kind"] == "background":
            out["bar_level"] = s2s.BAR_REFLECTANCE / s2s.REFLECTANCE * ex["background_cos_sun"]
    return out


# --- the full-pixel signal ----------------------------------------------------------------------------------------

def full_pixel_signal(platform, exposure_s):
    """e-/m^2 of focal plane over `exposure_s` for a pixel wholly on a Lambertian plate of reflectance `REFLECTANCE`
    under the UniformAtm hemisphere irradiance `IRRADIANCE` (DIRSIG's units: W/(cm^2 um)) with the Sun at the zenith:
    the job platform's tabulated channel response, aperture, throughput and focal length, and the exact aperture cone
    (the paraxial value over 1 + 1/(4 N^2); round 29 measured DIRSIG to follow the exact cone to 1e-7)."""
    t = Path(platform).read_text()
    lam = np.array([float(x) for x in re.findall(r"<spectralpoint>([0-9.]+)</spectralpoint><value>", t)])
    val = np.array([float(x) for x in re.findall(r"</spectralpoint><value>([0-9.eE+-]+)</value>", t)])
    d = float(re.search(r"<aperturediameter>([0-9.]+)", t).group(1))
    f = float(re.search(r"<focallength>([0-9.]+)", t).group(1)) / 1000.0
    tau = float(re.search(r"<aperturethroughput>([0-9.]+)", t).group(1))
    radiance = s2s.REFLECTANCE * s2s.IRRADIANCE * 1e4 / math.pi                 # W m-2 sr-1 um-1
    photons = radiance * lam * 1e-6 / (H * C)
    per_s = np.trapezoid(photons * val, lam) * tau * (math.pi * d * d / 4.0) / (f * f)
    n = f / d
    return float(per_s * exposure_s / (1.0 + 1.0 / (4.0 * n * n)))


# --- reductions ---------------------------------------------------------------------------------------------------

_SS = np.linspace(0.0, 1.0, 201)


def _swept_plate(u, x0, width, b):
    """Mean overlap of pixel [u - 0.5, u + 0.5] with a plate [x0 + s, x0 + width + s], s uniform over [0, b]."""
    lo = x0 + b * _SS[None, :]
    return np.clip(np.minimum(u[:, None] + 0.5, lo + width) - np.maximum(u[:, None] - 0.5, lo), 0, None).mean(axis=1)


def streak_length(img, width_px):
    """The fitted sweep length (pixels, unsigned) of a plate `width_px` wide in the mean profile of the frame's central
    rows (`img` in full pixels)."""
    from scipy.optimize import minimize
    n = img.shape[0]
    c = n / 2.0
    rows = np.arange(int(c - width_px / 2) + 3, int(c + width_px / 2) - 2)
    prof = img[rows].mean(axis=0)
    u = np.arange(img.shape[1], dtype=float)
    fits = [minimize(lambda q: np.sum((_swept_plate(u, q[0], width_px, q[1]) - prof) ** 2), [x0, b],
                     method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-12})
            for x0 in (c - width_px / 2, c - width_px / 2 - 24) for b in (-24.0, 24.0)]
    return float(abs(min(fits, key=lambda r: r.fun).x[1]))


def background_period(img, gb):
    """The mean spacing (pixels) of the bars' rising edges at 0.25 in the central 200 columns of the rows beside the
    look group's target band (`img` in full pixels, `gb` the background's footprint)."""
    c = img.shape[0] / 2.0
    band = s2s.LOOK["band"] / gb
    rows = np.r_[np.arange(int(c + band) + 4, int(c + band) + 60), np.arange(int(c - band) - 60, int(c - band) - 3)]
    seg = img[rows].mean(axis=0)[150:350]
    up = np.nonzero((seg[1:] >= 0.25) & (seg[:-1] < 0.25))[0]
    return float(np.diff(up).mean()) if len(up) > 1 else None


def reduce(entry, img, s_full):
    """[measurement, ...] of one product (`img`, e-/m^2, lines x samples), the primary one first."""
    fam, p = family(entry), point(entry)
    exp = expectations(entry)
    a = img / s_full
    got = {}
    if fam == 1:
        cos_sun = math.cos(math.radians(p["solar_zenith_deg"]))
        got["flux_closure"] = float(a.sum())
        if p["object_class"] == "hyperresolved":
            got["half_level_count"] = int((a >= 0.5 * cos_sun).sum())
            got["peak"] = float(a.max() / cos_sun)
    elif fam == 2:
        ex = s2s.expected2(p)
        if p["kind"] == "look":
            c = a.shape[0] / 2.0
            band = s2s.LOOK["band"] / ex["background_footprint_m"]
            got["flux_closure"] = float(a[int(c - band) + 2:int(c + band) - 1].sum())
            got["background_period"] = background_period(a, ex["background_footprint_m"])
        elif p["kind"] == "blur":   # the target's box: the bars, the small plate and the static marker lie outside
            c, half = a.shape[0] / 2.0, ex["side_px"] / 2
            reach = half + ex["target_blur_px"] + 6
            got["flux_closure"] = float(a[int(c - half) - 4:int(c + half) + 5, int(c - reach):int(c + reach) + 1].sum())
            got["streak_length"] = streak_length(a, ex["side_px"])
        else:
            got["flux_closure"] = float(a.sum())
    else:
        if p["kind"] == "background":
            got["flux_closure"] = float(a[200:300, 200:300].sum())
            reg = a[340:480, :]
            got["bar_level"] = float(np.median(reg[reg > 0.9 * reg.max()]))
        else:
            got["flux_closure"] = float(a.sum())
    out = []
    for method in ("flux_closure", "half_level_count", "peak", "streak_length", "background_period", "bar_level"):
        if method not in got:
            continue
        m, e = got[method], exp.get(method)
        out.append({"method": method, "measured": m, "expected": e,
                    "ratio": (m / e if (m is not None and e) else None), "tolerance": None})
    return out


# --- runs ---------------------------------------------------------------------------------------------------------

def default_work():
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return base / "manifold" / "s2s-measure"


def committed_spec(name):
    return yaml.safe_load((s2s.OUT / f"{name}.yaml").read_text())


def completed(folder, name):
    """(image, [truth images], platform) of a completed run of `name` in `folder`, or None."""
    spec = folder / "spec.yaml"
    if not spec.is_file() or yaml.safe_load(spec.read_text()) != committed_spec(name):
        return None
    out = folder / "output"
    truth = sorted(i for i in out.glob("*.img") if "truth" in i.name)
    images = [i for i in sorted(out.glob("*.img")) if i not in truth]
    platforms = sorted((folder / "input" / "platforms").rglob("*.platform"))
    if len(images) != 1 or len(platforms) != 1:
        return None
    return images[0], truth, platforms[0]


def render(name, folder):
    """Render the committed spec of `name` into `folder` at one thread; returns the wall time (s)."""
    import shutil
    from manifold.engines.dirsig.simulation import Simulation
    from manifold.engines.dirsig.adapter import locate_dirsig
    import manifold.sim  # noqa: F401  (registers the engines)
    if locate_dirsig()["home"] is None:            # before HOME moves: the default install is under the user's home
        raise SystemExit("no DIRSIG installation found ($DIRSIG_HOME or ~/DIRSIG/<pinned version>)")
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    (folder / "spec.yaml").write_text((s2s.OUT / f"{name}.yaml").read_text())
    home = folder / "home"
    home.mkdir()
    os.environ["HOME"] = str(home)
    sim = Simulation(folder / "spec.yaml", s2s.LIBRARY, work_dir=folder, sensor_library=s2s.SENSORS)
    if sim.resolved is None:
        raise SystemExit(f"{name}: does not resolve: {sim.resolve_error}")
    t0 = time.time()
    sim.run(threads=1)
    return time.time() - t0


def render_workspace(name, folder):
    """Render the committed spec of `name` through the SDK API instead: `Workspace.local` over the repository's
    library (work root `<folder>/../workspace/`), `submit_run` and `wait`; the product, truth images and the job's
    platform are then copied into `folder` in the layout `completed` reads. Returns the wall time (s)."""
    import shutil
    from manifold.engines.dirsig.adapter import locate_dirsig
    from manifold.sim import Workspace
    if locate_dirsig()["home"] is None:
        raise SystemExit("no DIRSIG installation found ($DIRSIG_HOME or ~/DIRSIG/<pinned version>)")
    shutil.rmtree(folder, ignore_errors=True)
    (folder / "output").mkdir(parents=True)
    (folder / "spec.yaml").write_text((s2s.OUT / f"{name}.yaml").read_text())
    ws = Workspace.local(config_repo=s2s.LIBRARY, work=folder.parent / "workspace", sensor_library=s2s.SENSORS)
    t0 = time.time()
    status = ws.submit_run(s2s.OUT / f"{name}.yaml")
    final = ws.wait(status.run_id, timeout=3600, poll=1.0)
    wall = time.time() - t0
    if final.state != "rendered":
        raise SystemExit(f"{name}: run {status.run_id} ended {final.state}: {final.errors}")
    for ref in ws.list_artifacts(status.run_id).artifacts:
        if ref.name.endswith((".img", ".img.hdr", ".hdr")):
            ws.save_artifact(status.run_id, ref.name, folder / "output" / ref.name)
    platforms = sorted(ws.backend.store.run_dir(status.run_id).rglob("*.platform"))
    if len(platforms) != 1:
        raise SystemExit(f"{name}: {len(platforms)} platform files in run {status.run_id}")
    (folder / "input" / "platforms").mkdir(parents=True)
    shutil.copy(platforms[0], folder / "input" / "platforms" / platforms[0].name)
    (folder / "run_id").write_text(status.run_id + "\n")
    return wall


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def measure(name, entry, folder, source):
    image, truth, platform = completed(folder, name)
    img = read_envi(image, header_for(image))[0]
    spec = committed_spec(name)
    s_full = full_pixel_signal(platform, spec["descriptor"]["settings"][0]["exposure_time"]["value"])
    ms = reduce(entry, img, s_full)
    rec = {"spec": name, "run_id": entry["run_id"], "family": family(entry), "source": source,
           "product": {"image": sha256(image), **{t.name: sha256(t) for t in truth}}, "full_pixel": s_full}
    rec.update(ms[0])
    rec["also"] = ms[1:]
    return rec


def _home_relative(path):
    try:
        return "~/" + str(Path(path).resolve().relative_to(Path.home().resolve()))
    except ValueError:
        return str(path)


def load_results(path=RESULTS):
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_results(records, path=RESULTS):
    path.parent.mkdir(parents=True, exist_ok=True)
    records = sorted(records, key=lambda r: r["spec"])
    path.write_text("".join(json.dumps(r, sort_keys=False) + "\n" for r in records))


def run(names, work, runs, via="simulation"):
    idx = index()
    unknown = [n for n in names if n not in idx]
    if unknown:
        raise SystemExit(f"not a DIRSIG spec of manifold_run_specs/s2s/index.json: {', '.join(unknown)}")
    for name in names:                                 # one at a time; the results file is written after each
        found = None
        for root, prefix in runs:
            if completed(root / f"{prefix}{name}", name):
                found = (root / f"{prefix}{name}", _home_relative(root / f"{prefix}{name}"))
                break
        folder = work / (name if via == "simulation" else f"{name}--workspace")
        if found is None and completed(folder, name):
            found = (folder, _home_relative(folder))
        wall = None
        if found is None:
            wall = (render if via == "simulation" else render_workspace)(name, folder)
            found = (folder, _home_relative(folder))
        rec = measure(name, idx[name], found[0], found[1])
        records = [r for r in load_results() if r["spec"] != name] + [rec]
        write_results(records)
        print(json.dumps({"spec": name, "source": rec["source"], "wall_s": None if wall is None else round(wall, 1),
                          "method": rec["method"], "ratio": rec["ratio"], "image": rec["product"]["image"][:16]}))


# --- check --------------------------------------------------------------------------------------------------------

def check(path=RESULTS):
    """Problems of the results file: form, unknown specs, run ids, expected values that do not recompute."""
    problems = []
    try:
        where0 = path.relative_to(ROOT)
    except ValueError:                  # a results file outside the repository (scripts/bigger_host_run.py's tests)
        where0 = path
    if not path.is_file():
        return [f"{where0}: missing"]
    idx = index()
    seen = set()
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines, 1):
        where = f"{where0}:{i}"
        try:
            r = json.loads(line)
        except ValueError as e:
            problems.append(f"{where}: not JSON ({e})")
            continue
        if not isinstance(r, dict) or tuple(r) != RECORD_KEYS:
            problems.append(f"{where}: keys are not {RECORD_KEYS}")
            continue
        name = r["spec"]
        if name in seen:
            problems.append(f"{where}: {name} recorded twice")
        seen.add(name)
        if name not in idx:
            problems.append(f"{where}: {name} is not a DIRSIG spec of {INDEX.relative_to(ROOT)}")
            continue
        entry = idx[name]
        if r["run_id"] != entry["run_id"] or r["family"] != family(entry):
            problems.append(f"{where}: run id or family differs from the index")
        if not (isinstance(r["product"], dict) and re.fullmatch(r"[0-9a-f]{64}", str(r["product"].get("image")))):
            problems.append(f"{where}: no image digest")
        if not (isinstance(r["full_pixel"], (int, float)) and r["full_pixel"] > 0):
            problems.append(f"{where}: full_pixel is not a positive number")
        exp = expectations(entry)
        for m in [{k: r[k] for k in MEASUREMENT_KEYS}] + list(r["also"]):
            if tuple(m) != MEASUREMENT_KEYS:
                problems.append(f"{where}: a measurement's keys are not {MEASUREMENT_KEYS}")
                continue
            e = exp.get(m["method"])
            if (e is None) != (m["expected"] is None) or (e is not None and not math.isclose(e, m["expected"],
                                                                                              rel_tol=1e-12)):
                problems.append(f"{where}: {m['method']}: expected {m['expected']} does not recompute ({e})")
            if m["measured"] is not None and m["expected"]:
                if m["ratio"] is None or not math.isclose(m["ratio"], m["measured"] / m["expected"], rel_tol=1e-12):
                    problems.append(f"{where}: {m['method']}: ratio is not measured / expected")
    if [json.loads(x)["spec"] for x in lines if x.startswith("{")] != sorted(seen):
        problems.append(f"{where0}: records are not sorted by spec name")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="verify the results file; exit 1 on a problem")
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run", help="measure the named specs (render what has no completed run)")
    r.add_argument("names", nargs="+")
    r.add_argument("--work", type=Path, default=None)
    r.add_argument("--via", choices=("simulation", "workspace"), default="simulation",
                   help="render through Simulation.run (default) or the SDK API (Workspace.submit_run)")
    r.add_argument("--runs", action="append", default=[],
                   help="DIR or DIR:PREFIX, a folder of completed runs named <PREFIX><spec name>")
    sub.add_parser("list", help="every measurable spec and whether the results file holds it")
    a = ap.parse_args(argv)
    if a.check:
        problems = check()
        print("\n".join(problems) if problems else f"{len(load_results())} records: well formed, specs indexed, "
                                                   f"expected values recompute")
        return 1 if problems else 0
    if a.cmd == "list":
        have = {r["spec"] for r in load_results()}
        for name in index():
            print(("measured " if name in have else "-        ") + name)
        return 0
    if a.cmd == "run":
        work = (a.work or default_work()).resolve()
        if work.is_relative_to(ROOT.resolve()):
            raise SystemExit(f"--work {work} is inside the repository; renders are written outside it")
        runs = []
        for item in a.runs:
            d, _, prefix = item.partition(":")
            runs.append((Path(d).expanduser().resolve(), prefix))
        run(a.names, work, runs, a.via)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
