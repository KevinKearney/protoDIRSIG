"""The SatSim adapter (`manifold.core.engine.EngineAdapter`, `proposed`): identity `satsim`, contract `satsim-engine/1`,
mode `passthrough` only.

A run names a SatSim configuration in the engine-asset library (`engine.config`, a file or a directory, stamped), a
required `seed` and `device: cpu`; its descriptor is opaque (`{source: passthrough}`), as for DIRSIG's pass-through
form. SatSim runs in its own interpreter (`interpreter.locate`); `availability()` probes it in a subprocess
(`interpreter.probe_cached`). This module imports neither `satsim`, `tensorflow` nor `numpy`: SatSim is driven, never
bundled.

Assets: the JPL ephemeris `de421.bsp` and a dated IERS snapshot `finals2000A.all` (`ASSETS`), pinned in
`external/pins.json`; admission refuses a run whose asset is missing or differs, naming it.

Resources (`resources()`): CPU threads, any count, carried in the four thread variables the probe found effective
(without a request SatSim runs at TensorFlow's defaults; thread count does not change its outputs, but a requested count
enters the run id like any `cpu_threads` request); about 1 GiB of memory; scratch space; no network; no GPU (a GPU
request or a `device` other than `cpu` is refused: GPU behavior is unverified); SatSim's interpreter.
"""
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath

from manifold.core.dirhash import directory_digest
from manifold.core.engine import CollectedArtifact, Collection, EngineInfo, EnvironmentPolicy, LaunchPlan
from manifold.core.resources import AssetDecl, CpuThreads, GpuSlot, ResourceDeclaration
from manifold.core.run_spec import PLACEHOLDER, RunSpecError
from manifold.engines.satsim import interpreter

HERE = Path(__file__).resolve().parent
ENGINE_ID = "satsim"
CONTRACT = "satsim-engine/1"
SCHEMA_FILE = "satsim-engine-1.schema.json"
THREAD_VARIABLES = ("TF_NUM_INTRAOP_THREADS", "TF_NUM_INTEROP_THREADS", "OMP_NUM_THREADS", "NUMBA_NUM_THREADS")
MEMORY_BYTES = 1 << 30                      # measured peak 0.86 to 0.91 GB (docs/SatSim_probe.md)
SCRATCH_BYTES = 256 << 20
ROOTS = ("fpa", "radar", "passive_rf")
CONFIG_NAMES = ("config.yaml", "config.yml", "config.json")
GPU_UNVERIFIED = "SatSim GPU behavior is unverified (no GPU run has been measured); only device cpu is admitted"
POINTER = "/engine/config"
# The data SatSim would otherwise download (docs/SatSim_probe.md), as hashed assets of the engine-asset library; the same
# sha256, size and source URL are pinned in external/pins.json (`kind: asset`), and `scripts/bootstrap.py assets` keeps
# them. Staged read-only under <run_dir>/assets/<name>; the launcher reads their paths from the variables named here.
EPHEMERIS = AssetDecl("de421.bsp", {"name": "satsim/assets/de421.bsp", "content_hash":
                                    "sha256:a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc"},
                      "MANIFOLD_SATSIM_EPHEMERIS", "JPL planetary ephemeris DE421, read by skyfield")
EARTH_ORIENTATION = AssetDecl("finals2000A.all", {"name": "satsim/assets/finals2000A.all", "content_hash":
                                                  "sha256:0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a"},
                              "MANIFOLD_SATSIM_IERS", "IERS finals2000A Earth orientation, snapshot of 2026-10-11, "
                              "read by astropy with downloads off")
ASSETS = (EPHEMERIS, EARTH_ORIENTATION)
LAUNCHER = HERE / "launcher.py"
SET = "set"                                 # SatSim's set folder name (fixed: its default is the local wall-clock time)
RESULT = "satsim_result.json"
UNSET = ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "SATSIM_SKYFIELD_LOAD_DIR", "SATSIM_SSTR7_PATH",
         "SATSIM_GCVS5_PATH")
FRAME = re.compile(r"\.(\d+)\.[A-Za-z]+$")    # sat_00000.0003.fits: frame 3


def _version():
    try:
        return version("eoptic-manifold-engine-satsim")
    except PackageNotFoundError:
        return "0+unknown"


@dataclass
class SatsimRun:
    """A resolved SatSim run: the library reference, the configuration file (absolute; and its folder when the
    reference is a directory), the parsed configuration, the seed and the device."""
    name: str
    ref_name: str
    config: Path
    directory: Path | None
    document: dict
    seed: int
    device: str


def load_config(path):
    """The parsed SatSim configuration (YAML or JSON, as SatSim reads them)."""
    path = Path(path)
    text = path.read_text()
    if path.suffix == ".json":
        return json.loads(text)
    import yaml
    return yaml.safe_load(text)


def _file_digest(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_config(block, config_repo):
    """`(config file, directory or None)` for `engine.config`; RunSpecError with a pointer on any refusal. An unstamped
    digest is not verified here (validation lists it, submission refuses it)."""
    ref = block.get("config") if isinstance(block, dict) else None
    if not isinstance(ref, dict) or not isinstance(ref.get("name"), str):
        raise RunSpecError(f"engine.config must be a library ref {{name, content_hash}}, got {ref!r}", pointer=POINTER)
    rel = PurePosixPath(ref["name"])
    if rel.is_absolute() or ".." in rel.parts:
        raise RunSpecError(f"engine.config.name {ref['name']!r} must be a path inside the library",
                           pointer=f"{POINTER}/name")
    path = Path(config_repo) / rel
    want = ref.get("content_hash")
    stamped = isinstance(want, str) and PLACEHOLDER not in want
    if path.is_dir():
        found = [path / n for n in CONFIG_NAMES if (path / n).is_file()]
        if len(found) != 1:
            raise RunSpecError(f"SatSim configuration directory {ref['name']!r} must hold exactly one of "
                               f"{', '.join(CONFIG_NAMES)}; it holds {len(found)}", pointer=f"{POINTER}/name")
        try:
            got = directory_digest(path) if stamped else None
        except ValueError as e:
            raise RunSpecError(f"SatSim configuration directory {ref['name']!r} cannot be hashed: {e}",
                               pointer=f"{POINTER}/name") from e
        config, directory = found[0], path
    elif path.is_file():
        got = _file_digest(path) if stamped else None
        config, directory = path, None
    else:
        raise RunSpecError(f"SatSim configuration {ref['name']!r} not found in the library ({path})",
                           pointer=f"{POINTER}/name")
    if got is not None and got != want:
        raise RunSpecError(f"SatSim configuration {ref['name']!r}: content_hash {want} does not match ({got}); run "
                           "scripts/stamp_hashes.py after an intended edit",
                           pointer=f"{POINTER}/content_hash")
    return config, directory


def _references(node, path=()):
    """`(pointer, value)` of each member of a configuration that names another file: `$import`, `$cache`, `path`
    (a star catalog) and `file`."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("$import", "$cache", "path", "file") and isinstance(v, str):
                out.append(("/".join(map(str, (*path, k))), v))
            out += _references(v, (*path, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += _references(v, (*path, i))
    return out


def config_problems(document, directory):
    """Admission problems of a parsed configuration: SatSim's root rule, one set per run, and no file named outside
    what the reference hashes (a single file names none; a directory's references stay inside it)."""
    if not isinstance(document, dict):
        return ["the SatSim configuration is not a mapping"]
    out = []
    roots = [r for r in ROOTS if r in document]
    if len(roots) != 1:
        out.append(f"the SatSim configuration must have exactly one of the roots {', '.join(ROOTS)}; it has "
                   f"{', '.join(roots) or 'none'}")
    samples = (document.get("sim") or {}).get("samples", 1) if isinstance(document.get("sim"), dict) else 1
    if samples != 1:
        out.append(f"sim.samples is {samples!r}: a run is one SatSim set (vary a configuration with a sweep of run "
                   "specs instead)")
    for where, value in _references(document):
        if directory is None:
            out.append(f"the SatSim configuration names a file at {where} ({value!r}); a configuration that names "
                       "other files must be a directory reference so that they are hashed with it")
        else:
            p = PurePosixPath(value)
            if p.is_absolute() or ".." in p.parts or not (Path(directory) / p).exists():
                out.append(f"the SatSim configuration names {value!r} at {where}, which is not a path inside its "
                           "directory")
    return out


class SatsimAdapter:
    """The SatSim engine adapter (pass-through form)."""

    def info(self):
        return EngineInfo(ENGINE_ID, _version(), (CONTRACT,), ("passthrough",),
                          "SatSim (AFRL) electro-optical space-scene simulator, run as authored in its own interpreter")

    def interpreter(self):
        """`(python, source)` or `(None, reason)` (`interpreter.locate`)."""
        return interpreter.locate()

    def availability(self):
        """None when SatSim's interpreter is found and imports `satsim` (probed once per process), else why not."""
        python, source = self.interpreter()
        if python is None:
            return source
        result = interpreter.probe_cached(python)
        return None if result["ok"] else result["reason"]

    def engine_schema(self, engine_block):
        return json.loads((HERE / SCHEMA_FILE).read_text())

    def schemas(self):
        return [self.engine_schema(None)]

    def compose_problems(self, settings):
        return []

    def semantic_rules(self, spec):
        eng = spec.get("engine") if isinstance(spec, dict) else None
        out = []
        if isinstance(eng, dict) and eng.get("device", "cpu") != "cpu":
            out.append(f"engine.device is {eng.get('device')!r}: {GPU_UNVERIFIED}")
        gpu = ((spec.get("resources") or {}).get("gpu") if isinstance(spec, dict) else None) or {}
        if isinstance(gpu, dict) and gpu.get("count"):
            out.append(f"resources.gpu requests {gpu.get('count')} GPU(s): {GPU_UNVERIFIED}")
        return out

    def resolve(self, descriptor, engine_block, context):
        config, directory = resolve_config(engine_block, context.config_repo)
        try:
            document = load_config(config)
        except Exception as e:  # noqa: BLE001 -- any parse failure is a refusal naming the file
            raise RunSpecError(f"SatSim configuration {engine_block['config']['name']!r} does not parse: "
                               f"{type(e).__name__}: {e}", pointer=f"{POINTER}/name") from e
        name = ((descriptor or {}).get("meta") or {}).get("name") or config.stem
        return SatsimRun(name, engine_block["config"]["name"], config, directory, document, engine_block["seed"],
                         engine_block.get("device", "cpu"))

    def library_problems(self, spec, resolved):
        return config_problems(resolved.document, resolved.directory)

    def plan(self, context):
        """Stage the configuration (its digest verified again) read-only in `<run_dir>/input/`, write
        `input/launch.json` and return the plan: `launcher.py` in SatSim's interpreter, in the run folder, with a
        per-run `HOME`, the granted thread count in the four thread variables, and the SDK's Python variables removed."""
        python, source = self.interpreter()
        if python is None:
            raise RuntimeError(f"SatSim cannot run here: {source}")
        engine = context.spec["engine"]
        config, directory = resolve_config(engine, context.config_repo)
        run_dir = Path(context.run_dir)
        inp = run_dir / "input"
        inp.mkdir(parents=True, exist_ok=True)
        if directory is not None:
            shutil.copytree(directory, inp, dirs_exist_ok=True)
            staged = inp / config.relative_to(directory)
        else:
            staged = inp / f"config{config.suffix}"
            shutil.copy2(config, staged)
        for f in [p for p in inp.rglob("*") if p.is_file()]:
            f.chmod(0o444)
        (inp / "launch.json").write_text(json.dumps({"seed": engine["seed"], "set": SET, "input_dir": "input",
                                                     "config": staged.relative_to(run_dir).as_posix()}, indent=1) + "\n")
        return LaunchPlan(argv=(str(LAUNCHER), str(run_dir)), cwd=str(run_dir), interpreter=python,
                          env=EnvironmentPolicy(set={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
                                                unset=UNSET, isolate_home=True, thread_variables=THREAD_VARIABLES),
                          expected_outputs=(RESULT,))

    def collect(self, output_dir, run_dir):
        return collect(output_dir, run_dir)

    def fingerprint(self, spec=None):
        python, source = self.interpreter()
        probe = interpreter.probe_cached(python) if python else None
        return {"satsim": {"interpreter": python, "interpreter_source": source, "probe": probe,
                           "launcher_sha256": hashlib.sha256(LAUNCHER.read_bytes()).hexdigest(),
                           "assets": {a.name: a.ref["content_hash"] for a in ASSETS}}}

    def resources(self, spec=None):
        python, _ = self.interpreter()
        return ResourceDeclaration(cpu_threads=CpuThreads(minimum=1, maximum=None, default=None,
                                                          variables=THREAD_VARIABLES),
                                   memory_bytes=MEMORY_BYTES, gpu=GpuSlot(maximum=0), scratch_bytes=SCRATCH_BYTES,
                                   network="none", assets=ASSETS, interpreter=python)


# --- collection --------------------------------------------------------------------------------------------------------

def role_of(rel):
    """The role of a file in SatSim's set folder (path relative to it): FITS frames `product`, annotations `truth`,
    annotated images and the movie `preview`, the CZML `metadata`, the resolved configurations `config`; anything else
    (an optional product the configuration asked for) `product`."""
    top = rel.split("/", 1)[0] if "/" in rel else ""
    if top == "ImageFiles" and rel.endswith(".fits"):
        return "product"
    if top == "Annotations" and rel.endswith(".json"):
        return "truth"
    if top == "AnnotatedImages":
        return "preview"
    if rel == "satsim.czml":
        return "metadata"
    if rel == "config.json" or re.fullmatch(r"config_pass_\d+\.json", rel):
        return "config"
    return "product"


def fits_shape(path):
    """`[rows, columns]` (NAXIS2, NAXIS1) of a FITS file's primary header, read without numpy; None if unreadable."""
    try:
        with open(path, "rb") as f:
            cards = {}
            while True:
                block = f.read(2880)
                if len(block) < 2880:
                    return None
                for i in range(0, 2880, 80):
                    card = block[i:i + 80].decode("ascii", "replace")
                    key = card[:8].strip()
                    if key == "END":
                        return [int(cards["NAXIS2"]), int(cards["NAXIS1"])] if "NAXIS2" in cards else None
                    if card[8:10] == "= ":
                        cards[key] = card[10:].split("/")[0].strip()
    except (OSError, ValueError, KeyError):
        return None


def _set_folder(out, run_dir):
    """SatSim's set folder in the output folder: the name the launch file fixed, else the one folder there (SatSim's
    own wall-clock name), else None."""
    try:
        name = json.loads((Path(run_dir) / "input" / "launch.json").read_text())["set"]
    except (OSError, ValueError, KeyError):
        name = None
    if name and (out / name).is_dir():
        return out / name
    dirs = [d for d in out.iterdir() if d.is_dir()] if out.is_dir() else []
    return dirs[0] if len(dirs) == 1 else None


def collect(output_dir, run_dir):
    """The artifacts of a SatSim run, with roles and paths relative to the set folder (flattened into names), and the
    verdict: `failed` when the launcher reported a failure (the traceback head and the elapsed time in the record);
    `complete` only when the launcher reported success, every frame was written and SatSim's end-of-run files exist
    (`config_pass_*.json`, and `AnnotatedImages/movie.png` and `satsim.czml` unless the configuration turns them off);
    otherwise `incomplete` (a run stopped by a signal leaves complete frames and no end-of-run files). The worker log is
    copied into the output folder as `worker.log` when collected. `engine_metadata` goes into the execution record."""
    out, run_dir = Path(output_dir), Path(run_dir)
    out.mkdir(parents=True, exist_ok=True)
    if (run_dir / "worker.log").is_file():
        shutil.copyfile(run_dir / "worker.log", out / "worker.log")
    result = None
    if (out / RESULT).is_file():
        try:
            result = json.loads((out / RESULT).read_text())
        except ValueError:
            result = None
    folder = _set_folder(out, run_dir)
    arts, frames, shape = [], set(), None
    for p in sorted(p for p in folder.rglob("*") if p.is_file()) if folder is not None else []:
        rel = p.relative_to(folder).as_posix()
        role = role_of(rel)
        m = FRAME.search(p.name) if role in ("product", "truth", "preview") and p.name != "movie.png" else None
        frame = int(m.group(1)) if m else None
        if role == "product" and p.suffix == ".fits" and frame is not None:
            frames.add(frame)
            shape = shape or fits_shape(p)
        arts.append(CollectedArtifact(p, role, frame, rel.replace("/", "_")))
    for name, role in ((RESULT, "metadata"), ("network_attempts.log", "log"), ("worker.log", "log")):
        if (out / name).is_file():
            arts.append(CollectedArtifact(out / name, role, None, name))
    config = {}
    if folder is not None and (folder / "config.json").is_file():
        try:
            config = json.loads((folder / "config.json").read_text())
        except ValueError:
            config = {}
    fpa = config.get("fpa") if isinstance(config.get("fpa"), dict) else {}
    sim = config.get("sim") if isinstance(config.get("sim"), dict) else {}
    expected = fpa.get("num_frames")
    metadata = {"set_folder": folder.name if folder is not None else None, "frames": len(frames),
                "frames_expected": expected, "image_size": shape, "seed": (result or {}).get("seed"),
                "versions": (result or {}).get("versions"), "elapsed_s": (result or {}).get("elapsed_s")}
    if (out / "network_attempts.log").is_file():
        metadata["network_attempts"] = len((out / "network_attempts.log").read_text().splitlines())
    record = {"engine_metadata": metadata}
    if result is not None and result.get("outcome") == "failed":
        metadata["traceback_head"] = result.get("traceback_head")
        return Collection(tuple(arts), "failed", f"SatSim failed: {result.get('message')}", record)
    missing = []
    if folder is None or not list(folder.glob("config_pass_*.json")):
        missing.append("config_pass_*.json")
    if sim.get("save_movie", True) and not (folder is not None and (folder / "AnnotatedImages" / "movie.png").is_file()):
        missing.append("AnnotatedImages/movie.png")
    if sim.get("save_czml", True) and not (folder is not None and (folder / "satsim.czml").is_file()):
        missing.append("satsim.czml")
    if result is None or missing or (expected is not None and len(frames) != expected):
        why = "the launcher wrote no result (stopped by a signal?)" if result is None else \
            "SatSim's end-of-run files are missing"
        return Collection(tuple(arts), "incomplete",
                          f"SatSim stopped before it finished: {why}; {len(frames)} of "
                          f"{expected if expected is not None else 'an unknown number of'} frames written"
                          f"{'; missing ' + ', '.join(missing) if missing else ''}", record)
    return Collection(tuple(arts), "complete", None, record)
