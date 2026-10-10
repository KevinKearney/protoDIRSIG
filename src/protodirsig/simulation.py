"""`Simulation`: the AUROR_ref job behind a constructor, three conformance checks and `run()`.

Stage 02.
What a notebook calls directly; no orchestration framework is imported here or below.

The three checks, and nothing more (radiometric correctness and scientific utility are out of
scope; the vehicle-not-appearing finding passes all three):

1. **Schema**: the run spec conforms to the published schemas, `manifold_contracts/run-spec-1.schema.json` with
   `dirsig-engine-1.schema.json` and `sensor-spec-1.schema.json` (`contract.schema_violations`: required members,
   no unknown keys outside `descriptor.extras`, enumerations, quantities, the conditional rules), plus the
   `semantic_errors` the schemas cannot express. A referenced file is not opened here.
2. **Resolution**: `run_spec.resolve_auror_run` finds every engine asset in `config_repo`, loads
   the sensor ref in the sensor library as `sensor-spec/1`, and accepts the motion as one this
   loader can generate (static, scene frame, `sceneenu` Euler; or orbit: a library TLE over a window, LookAt at a
   scene ENU point) and an epoch with a UTC offset.
   `run_spec.check_library_files`
   finds the library platform template renderable from the sensor-spec and `settings`.
3. **Execution**: the job is assembled (platform rendered by `platform_gen`, other library inputs copied, motion and tasks
   generated from the spec by `motion_tasks`) and DIRSIG is run with
   `--dry_run --log_info_filename=...`, which loads everything and schedules the captures without
   rendering. A nonzero exit or an `[error]` line on stderr fails it, and the JSON log must
   describe one capture per task window of the spec.

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

# The schema check moved to contract (pure, no engine package); re-exported so `from protodirsig.simulation import
# schema_errors` keeps working.
from protodirsig.contract import (DESCRIPTOR_REQUIRED, ENGINE_ENUMS, ENGINE_REQUIRED, _MISSING, _get,  # noqa: F401
                                  schema_errors, schema_violations, semantic_errors)
from protodirsig.admission import validate_spec
from protodirsig.platform_gen import render_platform
from protodirsig.platform_ref import PlatformFilesPlugin
from protodirsig.motion_tasks import generate_motion, generate_tasks
from protodirsig.run_spec import (RunSpecError, check_library_files, is_inline_sensor, load_run_spec,  # noqa: F401
                                 resolve_auror_run, unstamped_refs)
from protodirsig.scene_ref import copy_input, reference_scene



@dataclass
class ConformanceResult:
    schema_ok: bool
    schema_error: str | None
    resolution_ok: bool
    resolution_mismatches: list[str]
    execution_ok: bool
    execution_log: dict | None
    execution_error: str | None
    unstamped: list = field(default_factory=list)   # pointers of refs with the sha256:<hash> placeholder (run_spec.unstamped_refs)
    engine_checked: bool = False                    # True when the DIRSIG dry run was performed

    @property
    def passed(self):
        return self.schema_ok and self.resolution_ok and self.execution_ok


@dataclass
class Frame:
    """One capture of a run: its task, its time window relative to the epoch, and its image and truth files."""
    task_index: int
    time_window: list        # [start, stop], seconds relative to descriptor.collection.epoch
    image: Path
    truth: list[Path]


@dataclass
class RunResult:
    image: Path              # the first capture's image (the only one for a single-window run)
    truth: list[Path]        # the first capture's truth images
    output_dir: Path
    run_log: dict            # --run_info_filename: scenes (HDF, bounding box, MD5) and plugin inputs
    info_log: dict           # --log_info_filename: per-capture schedule, geometry and filenames
    warnings: list[str] = field(default_factory=list)
    frames: list[Frame] = field(default_factory=list)   # every capture, in log order (one per task window)
    propagator: dict | None = None                      # orbit motion: orbit.propagator_provenance(); never in a spec


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

    `config_repo` is the engine-asset library (scene, platform, atmosphere database, weather),
    read-only. `sensor_library` holds the `sensor-spec/1` documents (default `manifold_sensors/`, beside
    the run spec's folder). `work_dir` holds everything written: the job inputs (scene reference, input
    copies, generated motion and tasks, jsim), the dry-run scratch logs and the render output.
    Defaults to a fresh temporary directory.
    """

    def __init__(self, run_spec_path, config_repo, work_dir=None, sensor_library=None):
        self.run_spec_path, self.config_repo = Path(run_spec_path), Path(config_repo)
        self.sensor_library = Path(sensor_library) if sensor_library is not None else None
        self.work_dir = Path(work_dir) if work_dir is not None else Path(tempfile.mkdtemp(prefix="protodirsig_"))
        self.spec = self.auror_run = None
        self.load_error = self.resolve_error = None
        self.resolve_exception = None             # the resolution exception (RunSpecError.pointer names the member)
        try:
            self.spec = load_run_spec(self.run_spec_path)
        except Exception as e:  # noqa: BLE001 -- missing file, yaml.YAMLError, RunSpecError (not run-spec/1)
            self.load_error = f"{type(e).__name__}: {e}"
        if self.spec is not None:
            try:
                self.auror_run = resolve_auror_run(self.spec, self.run_spec_path, self.config_repo, self.sensor_library)
            except (RunSpecError, KeyError, TypeError) as e:
                self.resolve_error = f"{type(e).__name__}: {e}"
                self.resolve_exception = e

    @classmethod
    def from_run_spec(cls, run_spec_path, config_repo, work_dir=None, sensor_library=None):
        return cls(run_spec_path, config_repo, work_dir, sensor_library)

    def _assemble(self, in_dir, out_dir):
        """The Stage 01 job: scene reference, byte-identical library copies, generated motion and
        tasks, four plugins, seed."""
        r, lib = self.auror_run, self.config_repo
        ref_file = reference_scene(r.scene, in_dir / "auror_ref")   # wipes and recreates only this subdirectory
        scene = SCENE(r.scene.stem)
        scene._fname = ref_file                                     # private attribute: write() returns it as-is
        # Library assets keep their manifold_config_repo-relative paths; motion and tasks are generated.
        inputs = {"weather": copy_input(r.weather, in_dir / r.weather.relative_to(lib))}
        # The platform is rendered from the library template, the sensor-spec and `settings`.
        inputs["platform"] = render_platform(r.platform, r.sensor, r.settings[0]["entry_id"], r.settings,
                                             r.integration_samples, r.sensor_library,
                                             in_dir / r.platform.relative_to(lib), r.channel_response).path
        db = copy_input(r.atmosphere_db, in_dir / r.atmosphere_db.name)   # beside the jsim, as received
        motion, tasks = generate_motion(r, in_dir / "motion"), generate_tasks(r, in_dir / "tasks")
        job = DIRSIG(in_dir, out_dir)
        job.add_plugin(PlatformFilesPlugin(inputs["platform"], motion, tasks, split_channels=r.split_channels))
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
        if len(caps) != len(windows):
            problems.append(f"expected {len(windows)} capture(s), one per task window, log lists {len(caps)}")
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

    def validate(self, engine_check="dry_run"):
        """Run the checks, each reported independently; never raises for a bad spec. `unstamped` lists the members
        that carry a placeholder (`sha256:<hash>`, `<git-sha>`); it is reported, not a failed check (`passed` ignores
        it), and `LocalRegistry.submit` refuses such a spec.

        `engine_check`: `"dry_run"` (the default, as before) also assembles the job and runs the DIRSIG dry run;
        `"none"` stops after the engine-free checks (`admission.validate_spec`), so `execution_ok` is True,
        `execution_error` None, `engine_checked` False and `passed` is schema and resolution only. The schema,
        resolution and unstamped parts are `admission.validate_spec` at both levels."""
        if engine_check not in ("none", "dry_run"):
            raise ValueError(f"engine_check is {engine_check!r}; expected 'none' or 'dry_run'")
        if self.spec is None:
            return ConformanceResult(False, f"run spec did not load: {self.load_error}",
                                     False, ["not checked: run spec did not load"],
                                     False, None, "not attempted: run spec did not load")
        report = validate_spec(self.spec, self.run_spec_path, self.config_repo, self.sensor_library,
                               resolved=(self.auror_run, self.resolve_exception))
        schema, mismatches = report.schema_errors, report.resolution_mismatches

        exec_log = exec_err = None
        engine_checked = False
        if engine_check == "none":
            pass
        elif self.auror_run is None:
            exec_err = "not attempted: references did not resolve, so no job could be assembled"
        else:
            engine_checked = True
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
            execution_ok=exec_err is None, execution_log=exec_log, execution_error=exec_err,
            unstamped=report.unstamped, engine_checked=engine_checked)

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
        frames = [Frame(task_index=c["task_index"], time_window=list(c["relative_time_window"]),
                        image=Path(c["plugin_data"]["filename"]),
                        truth=[Path(t) for t in c["plugin_data"]["truth_filenames"] if t])
                  for c in info_log["capture_list"]]
        propagator = None
        if self.auror_run.motion_kind == "orbit":
            from protodirsig.orbit import propagator_provenance
            propagator = propagator_provenance()
        return RunResult(image=frames[0].image, truth=frames[0].truth,
                         output_dir=out_dir, run_log=json.loads(run_info.read_text()), info_log=info_log,
                         warnings=[ln for ln in stderr if ln.lstrip().startswith("[warn]")], frames=frames,
                         propagator=propagator)
