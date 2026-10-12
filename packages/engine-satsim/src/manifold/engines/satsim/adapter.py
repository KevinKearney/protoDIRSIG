"""The SatSim adapter (`manifold.core.engine.EngineAdapter`, `proposed`): identity `satsim`, contract `satsim-engine/1`,
mode `passthrough` only.

A run names a SatSim configuration in the engine-asset library (`engine.config`, a file or a directory, stamped), a
required `seed` and `device: cpu`; its descriptor is opaque (`{source: passthrough}`), as for DIRSIG's pass-through
form. SatSim runs in its own interpreter (`interpreter.locate`); `availability()` probes it in a subprocess
(`interpreter.probe_cached`). This module imports neither `satsim`, `tensorflow` nor `numpy`: SatSim is driven, never
bundled.

Resources (`resources()`): CPU threads, any count, carried in the four thread variables the probe found effective
(without a request SatSim runs at TensorFlow's defaults; thread count does not change its outputs, but a requested count
enters the run id like any `cpu_threads` request); about 1 GiB of memory; scratch space; no network; no GPU (a GPU
request or a `device` other than `cpu` is refused: GPU behavior is unverified); SatSim's interpreter.
"""
import hashlib
import json
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath

from manifold.core.dirhash import directory_digest
from manifold.core.engine import Collection, EngineInfo, EnvironmentPolicy, LaunchPlan
from manifold.core.resources import CpuThreads, GpuSlot, ResourceDeclaration
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
        raise RunSpecError(f"SatSim configuration {ref['name']!r}: content_hash {want[:19]}... does not match "
                           f"({got[:19]}...); run scripts/stamp_hashes.py after an intended edit",
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
        raise RuntimeError("SatSim execution is not built yet: the launcher arrives with the launch plan")

    def collect(self, output_dir, run_dir):
        return Collection((), "failed", "SatSim execution is not built yet", {})

    def fingerprint(self, spec=None):
        python, source = self.interpreter()
        probe = interpreter.probe_cached(python) if python else None
        return {"satsim": {"interpreter": python, "interpreter_source": source, "probe": probe}}

    def resources(self, spec=None):
        python, _ = self.interpreter()
        return ResourceDeclaration(cpu_threads=CpuThreads(minimum=1, maximum=None, default=None,
                                                          variables=THREAD_VARIABLES),
                                   memory_bytes=MEMORY_BYTES, gpu=GpuSlot(maximum=0), scratch_bytes=SCRATCH_BYTES,
                                   network="none", interpreter=python)
