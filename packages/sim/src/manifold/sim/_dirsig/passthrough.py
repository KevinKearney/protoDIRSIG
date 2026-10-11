"""The pass-through engine form (proposed): DIRSIG runs a library demo directory's simulation file as authored.

A pass-through run spec has an opaque descriptor (`meta`, `origin`, `fidelity`, `opaque: {source: passthrough}`) and an
engine block `{generator, mode: passthrough, passthrough: {directory: {name, content_hash}, simulation}, run?}`: the
directory is a library ref under the engine-asset library, identified by its `dirhash/1` digest, and `simulation` is the
`.sim`/`.jsim` file inside it. Nothing is generated: no scene, platform, motion, tasks or sensor layer is read.

`resolve_passthrough(spec, config_repo)` is admission's resolution for the form: it refuses a missing directory, a stamped
digest that does not match, a directory `dirhash/1` cannot hash (a symbolic link or another non-regular file inside it),
and a simulation path that escapes the directory or names no file, each with a `RunSpecError.pointer`; an unstamped
digest is left to `run_spec.unstamped_refs` (validation lists it, submission refuses it).

`run_engine(run, work_dir, engine, dry_run=False)` first compiles the scenes the simulation file names with the
`scene2hdf` beside the engine (DIRSIG5 reads a compiled `<scene>.hdf` and does not compile it; the compiled files stay in
the copy and are not artifacts), then runs the engine on a copy of the directory under `work_dir/input/`
(the engine may write beside the simulation file, for example a compiled scene, and the library is never written),
with `--output_folder <work_dir>/output` and the run's seed; files the engine writes into the copy instead of the output
folder are moved into it. `engine` is the `dirsig5` executable (a stub in tests). With `home`, both tools run with
`HOME` set to that folder (created if missing) and every other variable, `DIRSIG_HOME` included, inherited: DIRSIG writes
its material caches under `$HOME/Documents/DIRSIG/cache`, so a per-run home keeps them out of the user's cache and lets
the run record them (`cache_state`). While the tools run, `ThermalSampler` reads the maximum temperature over
`/sys/class/thermal/thermal_zone*/temp` (`$MANIFOLD_THERMAL_ZONES` overrides the folder) every 5 seconds (`max_cpu_temp_c` in the result, None without sensors), and the cores' current frequencies with it
(`cpu_freq_khz`, `$MANIFOLD_CPUFREQ` overrides `/sys/devices/system/cpu`).
`tool_version` is a tool's version line as the tool prints it.

Imports: the standard library, `manifold.core.run_spec` and `manifold.core.dirhash`; no engine package.
"""
import os
import shutil
import subprocess
import threading
from pathlib import Path, PurePosixPath

from manifold.core import _names
from manifold.core.passthrough_spec import OPAQUE, POINTER, PassthroughRun, is_passthrough, resolve_passthrough  # noqa: F401  (re-exported)

THERMAL_ZONES = _names.getenv("THERMAL_ZONES", "/sys/class/thermal")   # overridable for tests
CPU_FREQ = _names.getenv("CPUFREQ", "/sys/devices/system/cpu")             # overridable for tests
THROTTLE_SUSPECT_C = 90.0         # a run is throttle_suspect at this maximum temperature ...
THROTTLE_FREQ_FRACTION = 0.9      # ... with a core below this fraction of cpuinfo_max_freq


def scenes_of(simulation):
    """The `.scene` files a simulation file names, relative to its folder: a `.jsim`'s `scene_list[].inputs`, a `.sim`'s
    `<scene externalfile>` (whitespace allowed around `=`, either quote). A reference to a compiled scene,
    `<name>.scene.hdf`, stands for `<name>.scene`, the file `scene2hdf` compiles into it. Unreadable files give an empty
    list."""
    import json
    text = Path(simulation).read_text(errors="replace")
    found = []
    if str(simulation).endswith(".jsim"):
        try:
            doc = json.loads(text)
        except ValueError:
            return []
        for entry in doc if isinstance(doc, list) else [doc]:
            for s in (entry.get("scene_list") or []) if isinstance(entry, dict) else []:
                ref = s.get("inputs") if isinstance(s, dict) else s
                if isinstance(ref, str):
                    found.append(ref)
    else:
        import re
        found = re.findall(r"<scene\b[^>]*?externalfile\s*=\s*[\"']([^\"']+)[\"']", text)
    scenes = [ref[:-len(".hdf")] if ref.endswith(".scene.hdf") else ref for ref in found]
    return list(dict.fromkeys(ref for ref in scenes if ref.endswith(".scene")))


def compile_scenes(simulation, engine, timeout=None, log=None, env=None):
    """Compile every scene the simulation names with the `scene2hdf` beside `engine` (DIRSIG5 reads a scene's
    compiled HDF, `<scene>.hdf`, and does not compile it itself), in the scene's own folder. Returns
    `[(scene, exit status)]`, or None when there is no `scene2hdf` beside the engine (a stub engine)."""
    tool = Path(engine).parent / "scene2hdf"
    if not tool.is_file():
        return None
    results = []
    for ref in scenes_of(simulation):
        scene = (Path(simulation).parent / ref)
        with open(log, "ab") if log else open(os.devnull, "wb") as sink:
            proc = subprocess.run([str(tool), scene.name], cwd=scene.parent, stdout=sink, stderr=subprocess.STDOUT,
                                  timeout=timeout, env=env)
        results.append((ref, proc.returncode))
    return results


def tool_version(tool):
    """The version a DIRSIG tool prints for `--version`: the value of its `Version:` line, else its first non-empty
    line; None when the tool is missing or prints nothing."""
    if tool is None or not Path(tool).is_file():
        return None
    try:
        out = subprocess.run([str(tool), "--version"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = [ln.strip() for ln in (out.stdout or out.stderr or "").splitlines() if ln.strip()]
    for ln in lines:
        if ln.lower().startswith("version:"):
            return ln.split(":", 1)[1].strip()
    return lines[0] if lines else None


def max_zone_temp_c(root=THERMAL_ZONES):
    """The maximum temperature over `<root>/thermal_zone*/temp` in degrees C, or None when no zone can be read."""
    temps = []
    for f in Path(root).glob("thermal_zone*/temp"):
        try:
            temps.append(int(f.read_text().strip()) / 1000.0)
        except (OSError, ValueError):
            continue
    return max(temps) if temps else None


def cpu_freq_khz(root=CPU_FREQ):
    """`{min, max, cpuinfo_max}` in kHz: the minimum and maximum `scaling_cur_freq` over `<root>/cpu*/cpufreq` and the
    largest `cpuinfo_max_freq`; None when no core's current frequency can be read."""
    def read(name):
        values = []
        for f in Path(root).glob(f"cpu[0-9]*/cpufreq/{name}"):
            try:
                values.append(int(f.read_text().strip()))
            except (OSError, ValueError):
                continue
        return values
    cur, top = read("scaling_cur_freq"), read("cpuinfo_max_freq")
    return {"min": min(cur), "max": max(cur), "cpuinfo_max": max(top) if top else None} if cur else None


def throttle_suspect(max_c, freq):
    """At or above THROTTLE_SUSPECT_C with a core below THROTTLE_FREQ_FRACTION of `cpuinfo_max`; where the frequency
    is unknown (`freq` None or without `cpuinfo_max`), the temperature alone decides."""
    if max_c is None or max_c < THROTTLE_SUSPECT_C:
        return False
    if not freq or freq.get("min") is None or not freq.get("cpuinfo_max"):
        return True
    return freq["min"] < THROTTLE_FREQ_FRACTION * freq["cpuinfo_max"]


class ThermalSampler:
    """Samples `max_zone_temp_c` at entry, every `interval` seconds while active, and at exit; `max_c` is the maximum
    seen, None when the sensors are unavailable. The CPU frequency (`cpu_freq_khz`) is sampled with the temperature
    while active, the first time after `min(1, interval)` seconds, but not at entry or exit, when the tools are not
    running and idle cores would read low; `freq` is `{min, max, cpuinfo_max}` over those samples, None when there
    was none or the files are unavailable."""

    def __init__(self, interval=5.0, root=THERMAL_ZONES, freq_root=CPU_FREQ):
        self.interval, self.root, self.freq_root, self.max_c, self.freq = interval, root, freq_root, None, None
        self._stop = threading.Event()
        self._thread = None

    def _sample(self, freq=False):
        t = max_zone_temp_c(self.root)
        if t is not None and (self.max_c is None or t > self.max_c):
            self.max_c = t
        f = cpu_freq_khz(self.freq_root) if freq else None
        if f is not None:
            old = self.freq or f
            self.freq = {"min": min(old["min"], f["min"]), "max": max(old["max"], f["max"]),
                         "cpuinfo_max": max((v for v in (old["cpuinfo_max"], f["cpuinfo_max"]) if v), default=None)}

    def _loop(self):
        wait = min(1.0, self.interval)
        while not self._stop.wait(wait):
            self._sample(freq=True)
            wait = self.interval

    def __enter__(self):
        self._sample()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()
        self._sample()
        return False


def cache_state(home):
    """`{files, bytes}` of DIRSIG's cache folder under `home` (`Documents/DIRSIG/cache`)."""
    folder = Path(home) / "Documents" / "DIRSIG" / "cache"
    files = [p for p in folder.rglob("*") if p.is_file()] if folder.is_dir() else []
    return {"files": len(files), "bytes": sum(p.stat().st_size for p in files)}


def _snapshot(root):
    return {p.relative_to(root): (p.stat().st_size, p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}


def run_engine(run, work_dir, engine, dry_run=False, timeout=None, log=None, home=None):
    """Run `engine` on a copy of the run's directory. Returns `{returncode, command, moved, output, compiled,
    max_cpu_temp_c, cpu_freq_khz}`: `moved` lists files the engine wrote into the copy, which are moved into `<work_dir>/output/`.
    Never writes into the library. `home`: the `HOME` both tools run with (None: inherited)."""
    with ThermalSampler() as thermal:
        result = _run_engine(run, work_dir, engine, dry_run, timeout, log, home)
    return {**result, "max_cpu_temp_c": thermal.max_c, "cpu_freq_khz": thermal.freq}


def _run_engine(run, work_dir, engine, dry_run, timeout, log, home):
    env = None
    if home is not None:
        Path(home).mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "HOME": str(home)}
    work_dir = Path(work_dir)
    copy = work_dir / "input" / run.directory.name
    if copy.exists():
        shutil.rmtree(copy)
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(run.directory, copy, symlinks=False)
    out = work_dir / ("validate_output" if dry_run else "output")
    out.mkdir(parents=True, exist_ok=True)
    compiled = compile_scenes(copy / run.simulation_rel, engine, timeout, log, env)
    if compiled and any(code != 0 for _, code in compiled):
        return {"returncode": next(code for _, code in compiled if code != 0), "command": ["scene2hdf"], "moved": [],
                "output": out, "compiled": compiled}
    before = _snapshot(copy)
    command = [str(engine), f"--output_folder={out}"]
    if run.seed is not None:
        command.append(f"--random_seed={run.seed}")
    if dry_run:
        command.append("--dry_run")
    command.append(run.simulation_rel.rsplit("/", 1)[-1])
    cwd = copy / PurePosixPath(run.simulation_rel).parent
    with open(log, "ab") if log else open(os.devnull, "wb") as sink:
        proc = subprocess.run(command, cwd=cwd, stdout=sink, stderr=subprocess.STDOUT, timeout=timeout, env=env)
    moved = []
    for rel, stamp in sorted(_snapshot(copy).items()):
        if before.get(rel) != stamp:
            dest = out / rel.name if (out / rel.name).exists() is False else out / str(rel).replace("/", "_")
            shutil.move(str(copy / rel), dest)
            moved.append(dest.name)
    return {"returncode": proc.returncode, "command": command, "moved": moved, "output": out, "compiled": compiled}
