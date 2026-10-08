"""`Simulation`: the AUROR_ref job behind a constructor, three conformance checks and `run()`.

Stage 02 (eopticDocs `review/PLAN_2026-10-08_conformance-template-roadmap.md`, Phases 2-3).
What a notebook calls directly; no orchestration framework is imported here or below.

The three checks, and nothing more (radiometric correctness and scientific utility are out of
scope; the vehicle-not-appearing finding in FINDINGS.md passes all three):

1. **Schema**: the run spec parses, the required members of `run-spec/1` and the
   `dirsig-engine/1` body (AV_MANIFOLD_Configuration_v02 A.8) are present, and every enumerated
   engine field holds a value A.8 permits, plus the documented `new_atmosphere` extension.
   `descriptor` is checked for its required blocks only, not field by field, except that
   `descriptor.sensor` must be a `sensor-spec/1` ref with a string `ref.name`. The file itself is
   not opened here.
2. **Resolution**: `run_spec.resolve_auror_run` finds every engine asset in `config_repo`, the
   motion/tasks files in the received tree, and loads the sensor ref beside the run spec as
   `sensor-spec/1`, and
   `run_spec.check_received_files` finds the received motion/tasks/platform files agree with the
   spec.
3. **Execution**: the job is assembled as Stage 01 assembled it and DIRSIG is run with
   `--dry_run --log_info_filename=...`, which loads everything and schedules the captures without
   rendering. A nonzero exit or an `[error]` line on stderr fails it, and the JSON log must
   describe the single capture the spec's task window implies.

DIRSIG is invoked only through dirfm's `DIRSIG.run(**options)`, the one place a `dirsig5`
command line is built; extra flags are passed through its `options`.
"""
import json
import logging
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dirfm import DIRSIG, SCENE
from dirfm.weather import ThermWeatherFilePlugin

from protodirsig.platform_ref import PlatformFilesPlugin
from protodirsig.run_spec import RunSpecError, check_received_files, load_run_spec, resolve_auror_run
from protodirsig.scene_ref import copy_input, reference_scene

# Required members, from AV_MANIFOLD_Metadata_v02 §6 (descriptor) and Configuration_v02 A.8.1.
DESCRIPTOR_REQUIRED = ("meta", "origin", "collection", "sensor", "settings", "fidelity")
ENGINE_REQUIRED = ("generator", "scenes", "platform", "motion", "tasks", "atmosphere")
# Enumerated engine fields (A.8.2-A.8.7). `new_atmosphere` is the documented, non-adopted
# extension (GD_DIRSIG_RunSpec_YAML_v01 §6); A.8.7 adopts only `four_curve` and `basic`.
ENGINE_ENUMS = {
    ("generator", "tool"): {"dirfm"},
    ("generator", "spec_schema"): {"dirsig-engine/1"},
    ("motion", "kind"): {"static", "waypoints", "orbit"},
    ("motion", "orientation", "kind"): {"euler", "lookat"},
    ("atmosphere", "plugin"): {"four_curve", "basic", "new_atmosphere"},
    ("weather", "source"): {"library", "install"},
    ("ephemeris", "plugin"): {"spice"},
}
_MISSING = object()


@dataclass
class ConformanceResult:
    schema_ok: bool
    schema_error: str | None
    resolution_ok: bool
    resolution_mismatches: list[str]
    execution_ok: bool
    execution_log: dict | None
    execution_error: str | None

    @property
    def passed(self):
        return self.schema_ok and self.resolution_ok and self.execution_ok


@dataclass
class RunResult:
    image: Path
    truth: list[Path]
    output_dir: Path
    run_log: dict            # --run_info_filename: scenes (HDF, bounding box, MD5) and plugin inputs
    info_log: dict           # --log_info_filename: per-capture schedule, geometry and filenames
    warnings: list[str] = field(default_factory=list)


def _get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return _MISSING
        d = d[k]
    return d


def schema_errors(spec):
    """Every schema violation in a parsed run spec (empty list = conformant). See module docstring."""
    errs = []
    if spec.get("spec_version") != "run-spec/1":
        errs.append(f"spec_version is {spec.get('spec_version')!r}, expected 'run-spec/1'")
    desc, eng = spec.get("descriptor"), spec.get("engine")
    if not isinstance(desc, dict):
        errs.append("descriptor is missing")
    else:
        errs += [f"descriptor.{k} is missing" for k in DESCRIPTOR_REQUIRED if k not in desc]
        if "sensor" in desc and not isinstance(_get(desc, ("sensor", "ref", "name")), str):
            errs.append("descriptor.sensor.ref.name is missing: descriptor.sensor must be a sensor-spec/1 ref "
                        "(GD_DIRSIG_RunSpec_YAML_v01 §7), not an inline block")
    if not isinstance(eng, dict):
        return errs + ["engine is missing (required for a DIRSIG run)"]
    errs += [f"engine.{k} is missing" for k in ENGINE_REQUIRED if k not in eng]
    for path, allowed in ENGINE_ENUMS.items():
        v = _get(eng, path)
        if v is not _MISSING and v not in allowed:
            errs.append(f"engine.{'.'.join(path)} is {v!r}, not one of {sorted(allowed)}")
    scenes = eng.get("scenes")
    if "scenes" in eng and (not isinstance(scenes, list) or not scenes):
        errs.append("engine.scenes must be a list with at least one entry")
    for i, s in enumerate(scenes if isinstance(scenes, list) else []):
        if not isinstance(_get(s, ("ref", "name")), str):
            errs.append(f"engine.scenes[{i}].ref.name is missing")
    refs = [("platform", "ref")]
    if _get(eng, ("atmosphere", "plugin")) == "new_atmosphere":
        refs.append(("atmosphere", "database", "ref"))
    if _get(eng, ("weather", "source")) == "library":
        refs.append(("weather", "file"))
    for path in refs:
        if not isinstance(_get(eng, path + ("name",)), str):
            errs.append(f"engine.{'.'.join(path)}.name is missing")
    for key in ("library_entry", "output_prefix"):
        if "platform" in eng and _get(eng, ("platform", key)) is _MISSING:
            errs.append(f"engine.platform.{key} is missing")
    samples = _get(eng, ("platform", "integration_samples"))
    if samples is not _MISSING and not (isinstance(samples, int) and samples >= 1):
        errs.append(f"engine.platform.integration_samples is {samples!r}, expected an integer >= 1")
    windows = _get(eng, ("tasks", "windows"))
    if "tasks" in eng and (not isinstance(windows, list) or not windows
                           or not all(isinstance(w, dict) and {"start", "stop"} <= w.keys() for w in windows)):
        errs.append("engine.tasks.windows must be a non-empty list of {start, stop}")
    seed = _get(eng, ("run", "seed"))
    if seed is not _MISSING and not (isinstance(seed, int) and not isinstance(seed, bool)):
        errs.append(f"engine.run.seed is {seed!r}, expected an integer")
    return errs


class _Capture(logging.Handler):
    """Collects what dirfm logs from the DIRSIG processes: their stderr arrives as WARNING records."""

    def __init__(self):
        super().__init__(logging.WARNING)
        self.lines = []

    def emit(self, record):
        self.lines += record.getMessage().splitlines()


def _run_dirsig(job, **options):
    """`job.run(**options)` with dirfm's DIRSIG stderr captured. Returns (error or None, stderr lines)."""
    log = logging.getLogger("dirfm.dirsig")
    cap, level = _Capture(), log.level
    log.addHandler(cap)
    if log.getEffectiveLevel() > logging.WARNING:
        log.setLevel(logging.WARNING)
    try:
        job.run(**options)
        err = None
    except Exception as e:  # noqa: BLE001 -- dirfm raises a bare Exception(stderr) on nonzero exit
        err = f"{type(e).__name__}: {str(e).strip()}"
    finally:
        log.removeHandler(cap)
        log.setLevel(level)
    errors = [ln for ln in cap.lines if ln.lstrip().startswith("[error]")]
    if err is None and errors:
        err = "DIRSIG reported errors on stderr:\n" + "\n".join(errors)
    return err, cap.lines


class Simulation:
    """One AUROR_ref-type job from a run spec. Construct with `Simulation.from_run_spec`.

    `tree_root` is the received run tree (motion and tasks); `config_repo` is the engine-asset
    library (scene, platform, atmosphere database, weather). Both are read-only.
    `work_dir` holds everything written: the job inputs (scene reference, input copies, jsim),
    the dry-run scratch logs and the render output. Defaults to a fresh temporary directory.
    """

    def __init__(self, run_spec_path, tree_root, config_repo, work_dir=None):
        self.run_spec_path, self.tree_root, self.config_repo = Path(run_spec_path), Path(tree_root), Path(config_repo)
        self.work_dir = Path(work_dir) if work_dir is not None else Path(tempfile.mkdtemp(prefix="protodirsig_"))
        self.spec = self.auror_run = None
        self.load_error = self.resolve_error = None
        try:
            self.spec = load_run_spec(self.run_spec_path)
        except Exception as e:  # noqa: BLE001 -- missing file, yaml.YAMLError, RunSpecError (not run-spec/1)
            self.load_error = f"{type(e).__name__}: {e}"
        if self.spec is not None:
            try:
                self.auror_run = resolve_auror_run(self.spec, self.tree_root, self.run_spec_path, self.config_repo)
            except (RunSpecError, KeyError, TypeError) as e:
                self.resolve_error = f"{type(e).__name__}: {e}"

    @classmethod
    def from_run_spec(cls, run_spec_path, tree_root, config_repo, work_dir=None):
        return cls(run_spec_path, tree_root, config_repo, work_dir)

    def _assemble(self, in_dir, out_dir):
        """The Stage 01 job: scene reference, byte-identical input copies, four plugins, seed."""
        r, tree, lib = self.auror_run, self.tree_root, self.config_repo
        ref_file = reference_scene(r.scene, in_dir / "auror_ref")   # wipes and recreates only this subdirectory
        scene = SCENE(r.scene.stem)
        scene._fname = ref_file                                     # private attribute: write() returns it as-is
        # Each input keeps its path relative to the root it came from: per-run files from the
        # received tree, library assets from config_repo.
        inputs = {n: copy_input(src, in_dir / src.relative_to(root)) for n, src, root in [
            ("platform", r.platform, lib), ("motion", r.motion, tree), ("tasks", r.tasks, tree),
            ("weather", r.weather, lib)]}
        db = copy_input(r.atmosphere_db, in_dir / r.atmosphere_db.name)   # beside the jsim, as received
        job = DIRSIG(in_dir, out_dir)
        job.add_plugin(PlatformFilesPlugin(inputs["platform"], inputs["motion"], inputs["tasks"],
                                           split_channels=r.split_channels))
        job.add_plugin(r.atmosphere_plugin(db))
        job.add_plugin(r.ephemeris_plugin())
        job.add_plugin(ThermWeatherFilePlugin(inputs["weather"]))
        job.add_scene(scene, r.scene_offset)
        job.set_seed(r.seed)
        return job

    def _check_log(self, log):
        """Sanity-check a --log_info JSON against the spec's task window; not a schema validation."""
        problems = []
        caps = log.get("capture_list", [])
        windows = self.spec["engine"]["tasks"]["windows"]
        if len(caps) != 1:
            problems.append(f"expected 1 capture, log lists {len(caps)}")
        for c in caps:
            ti, t0 = c.get("task_index"), (c.get("relative_time_window") or [None])[0]
            if not (isinstance(ti, int) and 0 <= ti < len(windows)):
                problems.append(f"capture {c.get('capture_index')}: task_index {ti} outside the spec's {len(windows)} window(s)")
            elif t0 is None or not windows[ti]["start"] - 1e-9 <= t0 <= windows[ti]["stop"] + 1e-9:
                problems.append(f"capture {c.get('capture_index')}: starts at {t0}, outside window "
                                f"[{windows[ti]['start']}, {windows[ti]['stop']}]")
        ref = log.get("run_info", {}).get("reference_date_time")
        epoch = self.spec["descriptor"]["collection"]["epoch"].replace("Z", "+00:00")
        if ref is None or datetime.fromisoformat(ref) != datetime.fromisoformat(epoch):
            problems.append(f"reference datetime {ref} != descriptor.collection.epoch {epoch}")
        return problems

    def validate(self):
        """Run all three checks, each reported independently; never raises for a bad spec."""
        if self.spec is None:
            return ConformanceResult(False, f"run spec did not load: {self.load_error}",
                                     False, ["not checked: run spec did not load"],
                                     False, None, "not attempted: run spec did not load")
        schema = schema_errors(self.spec)

        if self.auror_run is None:
            mismatches = [f"references did not resolve: {self.resolve_error}"]
        else:
            try:
                mismatches = check_received_files(self.spec, self.auror_run)
            except Exception as e:  # noqa: BLE001
                mismatches = [f"received files could not be compared: {type(e).__name__}: {e}"]

        exec_log = exec_err = None
        if self.auror_run is None:
            exec_err = "not attempted: references did not resolve, so no job could be assembled"
        else:
            scratch = self.work_dir / "validate"
            log_file = scratch / "log_info.json"
            log_file.unlink(missing_ok=True)
            try:
                job = self._assemble(scratch / "input", scratch / "output")
                exec_err, _ = _run_dirsig(job, dry_run=None, log_info_filename=str(log_file))
            except Exception as e:  # noqa: BLE001
                exec_err = f"job assembly failed: {type(e).__name__}: {e}"
            if exec_err is None:
                if not log_file.is_file():
                    exec_err = f"dirsig5 exited cleanly but wrote no log at {log_file}"
                else:
                    exec_log = json.loads(log_file.read_text())
                    problems = self._check_log(exec_log)
                    exec_err = "; ".join(problems) if problems else None

        return ConformanceResult(
            schema_ok=not schema, schema_error="; ".join(schema) or None,
            resolution_ok=not mismatches, resolution_mismatches=mismatches,
            execution_ok=exec_err is None, execution_log=exec_log, execution_error=exec_err)

    def run(self, out_dir=None):
        """Assemble and render (Stage 01's job), with --run_info_filename and --log_info_filename
        written beside the images. Raises if the spec did not resolve or DIRSIG fails."""
        if self.auror_run is None:
            raise RunSpecError(f"cannot run: {self.load_error or self.resolve_error}")
        out_dir = Path(out_dir) if out_dir is not None else self.work_dir / "output"
        job = self._assemble(self.work_dir / "input", out_dir)
        run_info, log_info = out_dir / "run_info.json", out_dir / "log_info.json"
        err, stderr = _run_dirsig(job, run_info_filename=str(run_info), log_info_filename=str(log_info))
        if err is not None:
            raise RuntimeError(err)
        info_log = json.loads(log_info.read_text())
        data = info_log["capture_list"][0]["plugin_data"]
        return RunResult(image=Path(data["filename"]), truth=[Path(t) for t in data["truth_filenames"] if t],
                         output_dir=out_dir, run_log=json.loads(run_info.read_text()), info_log=info_log,
                         warnings=[ln for ln in stderr if ln.lstrip().startswith("[warn]")])
