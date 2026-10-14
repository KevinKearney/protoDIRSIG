"""The dummy engine's adapter (`manifold.core.engine.EngineAdapter`), a test fixture.

Identity `dummy`, contract `dummy-engine/1`, mode `layered`. Its schema is `dummy-engine-1.schema.json`; its semantic rule
refuses whitespace in `engine.label`; it declares one resource slot (1 to 2 threads, default 1, carried in
`DUMMY_THREADS`) and one asset (`table`, the library file `dummy/table.txt`, path in `DUMMY_TABLE`); its launch plan runs
`engine.py` in the interpreter `MANIFOLD_DUMMY_PYTHON` names (default `/usr/bin/python3`), not the SDK's, with a per-run
`HOME`; its collection reports frames (`product`) and the log (`log`), and says `incomplete` when the end-of-run marker
`DONE` is missing.
"""
import hashlib
import json
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from manifold.core.engine import CollectedArtifact, Collection, EngineInfo, EnvironmentPolicy, LaunchPlan
from manifold.core.resources import AssetDecl, CpuThreads, GpuSlot, ResourceDeclaration

HERE = Path(__file__).resolve().parent
ENGINE_ID = "dummy"
TABLE_BYTES = b"dummy table v1\nrow 2\n"
TABLE_REF = {"name": "dummy/table.txt", "content_hash": "sha256:" + hashlib.sha256(TABLE_BYTES).hexdigest()}


def interpreter():
    return os.environ.get("MANIFOLD_DUMMY_PYTHON", "/usr/bin/python3")


class DummyAdapter:
    def info(self):
        try:
            v = version("eoptic-manifold-engine-dummy")
        except PackageNotFoundError:
            v = "0+unknown"
        return EngineInfo(ENGINE_ID, v, ("dummy-engine/1",), ("layered",), "test fixture")

    def availability(self):
        return None if Path(interpreter()).exists() else f"no interpreter at {interpreter()}"

    def engine_schema(self, engine_block):
        return json.loads((HERE / "dummy-engine-1.schema.json").read_text())

    def compose_problems(self, settings):
        return []

    def semantic_rules(self, spec):
        label = (spec.get("engine") or {}).get("label")
        return [f"engine.label {label!r} contains whitespace"] if isinstance(label, str) and label.split() != [label] \
            else []

    def resolve(self, descriptor, engine_block, context):
        return {"steps": engine_block["steps"], "sleep_s": engine_block.get("sleep_s", 0)}

    def library_problems(self, spec, resolved):
        return []

    def plan(self, context):
        return LaunchPlan(argv=(str(HERE / "engine.py"), str(context.run_dir)), cwd=str(context.run_dir),
                          interpreter=interpreter(),
                          env=EnvironmentPolicy(isolate_home=True, thread_variables=("DUMMY_THREADS",)),
                          expected_outputs=("DONE",))

    def collect(self, output_dir, run_dir):
        out = Path(output_dir)
        frames = sorted(out.glob("frame-*.txt")) if out.is_dir() else []
        arts = tuple([CollectedArtifact(p, "product", i) for i, p in enumerate(frames)] +
                     ([CollectedArtifact(out / "dummy.log", "log")] if (out / "dummy.log").is_file() else []))
        if not (out / "DONE").is_file():
            return Collection(arts, "incomplete", f"the dummy engine stopped before its end-of-run marker "
                              f"({len(frames)} frames written)", {"frames_written": len(frames)})
        return Collection(arts, "complete", None, {"frames_written": len(frames)})

    def fingerprint(self, spec=None):
        return {"dummy": {"interpreter": interpreter(), "engine_script": "engine.py"}}

    def resources(self, spec=None):
        return ResourceDeclaration(cpu_threads=CpuThreads(minimum=1, maximum=2, default=1, variables=("DUMMY_THREADS",)),
                                   gpu=GpuSlot(maximum=0), network="none",
                                   assets=(AssetDecl("table", TABLE_REF, "DUMMY_TABLE", "a small hashed table"),))
