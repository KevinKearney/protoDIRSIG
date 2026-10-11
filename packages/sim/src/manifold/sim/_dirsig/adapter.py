"""The DIRSIG engine adapter (`manifold.core.engine.EngineAdapter`): `dirsig-engine/1` engine blocks, layered and
pass-through modes.

Identity: engine id `dirsig`, contract `dirsig-engine/1`, modes `layered` and `passthrough`. Schema: the engine block is
validated against `dirsig-engine-1.schema.json`. Composition rule: a non-zero `black_level` is refused (DIRSIG applies it
as a channel bias). Semantic rules: integer members read from YAML as floats. Resolution: `run_spec.resolve_run` for a
layered block, `resolve_passthrough` for `mode: passthrough`; the library-file check renders the platform template
(`run_spec.check_library_files`). Importing this module loads no engine package (dirfm loads only when a job is built).
"""
from manifold.core.contract import load_schema
from manifold.core.engine import EngineInfo, ResolveContext
from manifold.core.passthrough_spec import is_passthrough, resolve_passthrough
from manifold.core.run_spec import black_level_problem, check_library_files, resolve_run

ENGINE_ID = "dirsig"
CONTRACT = "dirsig-engine/1"
SCHEMA_FILE = "dirsig-engine-1.schema.json"
# Required engine members and enumerations as dirsig-engine-1.schema.json states them (Configuration_v02 A.8.1-A.8.7);
# kept for callers and tests. `new_atmosphere` is the documented, non-adopted extension (CONOPS and Guide §10).
ENGINE_REQUIRED = ("generator", "scenes", "platform", "motion", "tasks", "atmosphere")
ENGINE_ENUMS = {
    ("generator", "tool"): {"dirfm"},
    ("generator", "spec_schema"): {CONTRACT},
    ("motion", "kind"): {"static", "waypoints", "orbit"},
    ("motion", "orientation", "kind"): {"euler", "lookat"},
    ("motion", "orbit", "propagator"): {"skyfield_sgp4"},           # the orbit form (proposed, CONOPS §3.2)
    ("motion", "orientation", "lookat", "frame"): {"sceneenu"},
    ("motion", "orientation", "lookat", "up"): {"along_track"},
    ("atmosphere", "plugin"): {"four_curve", "basic", "new_atmosphere"},
    ("weather", "source"): {"library", "install"},
    ("ephemeris", "plugin"): {"spice"},
}


def _version():
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version("eoptic-manifold-sim")
    except PackageNotFoundError:
        return "0+unknown"


def _get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


class DirsigAdapter:
    """The DIRSIG adapter. Stateless; one instance serves every run."""

    def info(self):
        return EngineInfo(ENGINE_ID, _version(), (CONTRACT,), ("layered", "passthrough"),
                          "DIRSIG 5 through dirfm (layered) or a library demo directory run as authored (pass-through)")

    def engine_schema(self, engine_block):
        return load_schema(SCHEMA_FILE)

    def compose_problems(self, settings):
        """(field, message) for each recipe settings member the engine cannot apply."""
        out = []
        for i, m in enumerate(settings or []):
            problem = black_level_problem(m)
            if problem:
                out.append((f"settings[{i}].black_level", problem))
        return out

    def semantic_rules(self, spec):
        """Integer members read from YAML as floats: JSON Schema's `integer` accepts 42.0, the generator needs an
        integer (`engine.run.seed`, `engine.platform.integration_samples`)."""
        eng = spec.get("engine") if isinstance(spec, dict) else None
        errs = []
        if isinstance(eng, dict):
            seed = _get(eng, ("run", "seed"))
            if isinstance(seed, float):
                errs.append(f"engine.run.seed is {seed!r}, expected an integer")
            samples = _get(eng, ("platform", "integration_samples"))
            if isinstance(samples, float):
                errs.append(f"engine.platform.integration_samples is {samples!r}, expected an integer >= 1")
        return errs

    def resolve(self, descriptor, engine_block, context: ResolveContext):
        spec = {"spec_version": "run-spec/1", "descriptor": descriptor, "engine": engine_block}
        if is_passthrough(spec):
            return resolve_passthrough(spec, context.config_repo)
        return resolve_run(spec, context.run_spec_path, context.config_repo, context.sensor_library)

    def library_problems(self, spec, resolved):
        if is_passthrough(spec):
            return []                                       # no library files beyond the directory: nothing to render
        return check_library_files(spec, resolved)

    def plan(self, context):
        raise NotImplementedError

    def execute(self, context, hook=None):
        raise NotImplementedError

    def collect(self, output_dir, run_dir):
        raise NotImplementedError

    def fingerprint(self, spec=None):
        return {}

    def resources(self, spec=None):
        return None
