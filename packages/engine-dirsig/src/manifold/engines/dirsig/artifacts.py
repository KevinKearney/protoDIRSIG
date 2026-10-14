"""The artifact references of a DIRSIG run as the run store records them: `artifacts_for` (a layered run: the run spec,
the run-level logs and, once rendered, each capture's image, header and truth products with `frame`, in task order
from the engine's `log_info.json`) and `passthrough_artifacts` (a pass-through run: the run spec and every file the
engine wrote). The adapter's `collect` reports the same files with roles; the worker builds the references.
"""
import json
from pathlib import Path

from manifold.core.artifacts import NAME, ArtifactError, artifact_ref, check_artifact_names  # noqa: F401

RUN_LEVEL = ("run_info.json", "log_info.json")                  # engine logs: the run as a whole, no frame


def _frames(run_dir):
    """[(frame, image path, truth paths)] from the engine's log_info.json, in task order (task, then capture)."""
    log = run_dir / "output" / "log_info.json"
    if not log.is_file():
        return []
    caps = json.loads(log.read_text()).get("capture_list", [])
    caps = sorted(caps, key=lambda c: (c.get("task_index", 0), c.get("capture_index", 0)))
    out = []
    for i, c in enumerate(caps):
        data = c.get("plugin_data", {})
        resolve = lambda p: Path(p) if Path(p).is_absolute() else run_dir / "output" / p      # noqa: E731
        out.append((i, resolve(data["filename"]), [resolve(t) for t in data.get("truth_filenames", []) if t]))
    return out


def _header(image):
    for h in (image.with_name(image.name + ".hdr"), image.with_suffix(".hdr")):
        if h.is_file():
            return h
    return None


def artifacts_for(run_dir, final=False):
    """The artifact references of a run: `run_spec.json`; `run_info.json` and `log_info.json` once written; and, for a
    rendered run (`final`), every capture's image, its ENVI header if present and its truth products and their
    headers, each with `frame`, the capture's zero-based index in task order. Names are file base names; a collision or
    a name outside the `artifact_ref` pattern raises ArtifactError (the run is failed, nothing is renamed)."""
    run_dir = Path(run_dir)
    refs = [artifact_ref(run_dir / "run_spec.json")]
    refs += [artifact_ref(run_dir / "output" / n) for n in RUN_LEVEL if (run_dir / "output" / n).is_file()]
    if final:
        for frame, image, truth in _frames(run_dir):
            for p in [image, _header(image)] + [x for t in truth for x in (t, _header(t))]:
                if p is not None:
                    if not p.is_file():
                        raise ArtifactError(f"capture {frame}: {p.name} is named by the engine log but was not written")
                    refs.append(artifact_ref(p, frame=frame))
    names = [r["name"] for r in refs]
    bad = sorted({n for n in names if not NAME.match(n)})
    dup = sorted({n for n in names if names.count(n) > 1})
    if bad or dup:
        raise ArtifactError(f"artifact names {'not matching ' + NAME.pattern + ': ' + str(bad) if bad else ''}"
                            f"{'; ' if bad and dup else ''}{'used twice: ' + str(dup) if dup else ''}")
    return refs


def passthrough_artifacts(run_dir):
    """The artifact references of a rendered pass-through run: `run_spec.json`, then every file the engine wrote into
    `output/`, sorted by name, with no frame. A file in a subfolder of `output/` is named by its path with `/` replaced
    by `_`; names are checked like `artifacts_for`'s."""
    run_dir = Path(run_dir)
    out = run_dir / "output"
    refs = [artifact_ref(run_dir / "run_spec.json")]
    files = sorted(p for p in out.rglob("*") if p.is_file()) if out.is_dir() else []
    refs += [artifact_ref(p, name=p.relative_to(out).as_posix().replace("/", "_")) for p in files]
    names = [r["name"] for r in refs]
    bad = sorted({n for n in names if not NAME.match(n)})
    dup = sorted({n for n in names if names.count(n) > 1})
    if bad or dup:
        raise ArtifactError(f"artifact names {'not matching ' + NAME.pattern + ': ' + str(bad) if bad else ''}"
                            f"{'; ' if bad and dup else ''}{'used twice: ' + str(dup) if dup else ''}")
    return refs
