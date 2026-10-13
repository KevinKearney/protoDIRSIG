"""The pass-through engine form's run-spec side (proposed): recognizing the form and resolving its directory and
simulation file against the engine-asset library, which admission does without running anything. Running the form is
`manifold.engines.dirsig.passthrough`, which re-exports these names.

`resolve_passthrough(spec, config_repo)` is admission's resolution for the form: it refuses a missing directory, a stamped
digest that does not match, a directory `dirhash/1` cannot hash (a symbolic link or another non-regular file inside it),
and a simulation path that escapes the directory or names no file, each with a `RunSpecError.pointer`; an unstamped
digest is left to `run_spec.unstamped_refs` (validation lists it, submission refuses it).

Imports: the standard library, `manifold.core.run_spec` and `manifold.core.dirhash`; no engine package.
"""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from manifold.core.dirhash import directory_digest
from manifold.core.run_spec import PLACEHOLDER, RunSpecError

POINTER = "/engine/passthrough"
OPAQUE = {"source": "passthrough"}


def is_passthrough(spec):
    """True for a spec whose engine block is the pass-through form."""
    eng = spec.get("engine") if isinstance(spec, dict) else None
    return isinstance(eng, dict) and eng.get("mode") == "passthrough"


@dataclass
class PassthroughRun:
    """A resolved pass-through run: the library directory, the simulation file in it (absolute and relative), the
    seed (None if the spec states none)."""
    name: str
    directory: Path
    simulation: Path
    simulation_rel: str
    seed: int | None = None


def resolve_passthrough(spec, config_repo):
    """Resolve a pass-through spec against the engine-asset library; RunSpecError with a pointer on any refusal."""
    eng = spec["engine"]
    block = eng.get("passthrough")
    if not isinstance(block, dict):
        raise RunSpecError("engine.passthrough is missing: the pass-through form names a directory and a simulation "
                           "file", pointer=POINTER)
    ref = block.get("directory")
    if not isinstance(ref, dict) or not isinstance(ref.get("name"), str):
        raise RunSpecError(f"engine.passthrough.directory must be a library ref {{name, content_hash}}, got {ref!r}",
                           pointer=f"{POINTER}/directory")
    directory = Path(config_repo) / ref["name"]
    if not directory.is_dir():
        raise RunSpecError(f"pass-through directory {ref['name']!r} not found: {directory} is not a directory "
                           "(run scripts/bootstrap.py assets to place a demo directory)",
                           pointer=f"{POINTER}/directory/name")
    want = ref.get("content_hash")
    try:
        got = directory_digest(directory) if isinstance(want, str) and PLACEHOLDER not in want else None
    except ValueError as e:
        raise RunSpecError(f"pass-through directory {ref['name']!r} cannot be hashed: {e}",
                           pointer=f"{POINTER}/directory/name") from e
    if got is not None and got != want:
        raise RunSpecError(f"pass-through directory {ref['name']!r}: content_hash {want} does not match the "
                           f"directory ({got}); run scripts/stamp_hashes.py after an intended edit",
                           pointer=f"{POINTER}/directory/content_hash")
    sim = block.get("simulation")
    rel = PurePosixPath(sim) if isinstance(sim, str) and sim else None
    if rel is None or rel.is_absolute() or ".." in rel.parts:
        raise RunSpecError(f"engine.passthrough.simulation {sim!r} must be a relative path inside the directory",
                           pointer=f"{POINTER}/simulation")
    path = directory / rel
    if not path.resolve().is_relative_to(directory.resolve()) or not path.is_file():
        raise RunSpecError(f"engine.passthrough.simulation {sim!r} names no file in {ref['name']!r}",
                           pointer=f"{POINTER}/simulation")
    seed = (eng.get("run") or {}).get("seed")
    name = ((spec.get("descriptor") or {}).get("meta") or {}).get("name") or directory.name
    return PassthroughRun(name, directory, path, str(rel), seed if isinstance(seed, int) else None)
