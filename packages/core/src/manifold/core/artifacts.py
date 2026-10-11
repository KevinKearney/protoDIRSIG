"""Artifact references: the `artifact_ref` document of a file (name, sha256 of its bytes, media type, `file://` URI,
the zero-based `frame` of a per-capture product, and the `role` its engine's adapter gave it, `proposed`) and the name
rule every reference list obeys. Engine-neutral:
what an engine produced is its adapter's to say (`EngineAdapter.collect`); the references are built here.

Imports: the standard library only.
"""
import hashlib
import re
from pathlib import Path

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")               # artifact_ref.schema.json `name`
MEDIA_TYPES = {".img": "application/octet-stream", ".hdr": "text/plain", ".log": "text/plain", ".txt": "text/plain",
               ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".fits": "application/fits", ".czml": "application/json", ".yaml": "application/yaml"}
ROLES = ("product", "truth", "preview", "log", "config", "metadata")   # the initial set of `role` (proposed; free)
ROLE = re.compile(r"^[a-z][a-z0-9_]*$")                              # artifact_ref.schema.json `role` pattern
VERDICTS = ("complete", "incomplete", "failed")                        # run_status.schema.json `verdict` (proposed)


class ArtifactError(ValueError):
    """Artifact names that collide or do not match the `artifact_ref` pattern: recorded as a failed run."""


def media_type(path):
    return MEDIA_TYPES.get(Path(path).suffix.lower(), "application/octet-stream")


def sha256_bytes_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def artifact_ref(path, name=None, frame=None, role=None):
    """An `artifact_ref` document for a file: name (its base name), sha256 of the bytes, media type, `file://` URI, and
    the frame and role when given (the vocabulary is free, `ROLES` its initial set; a role not matching `ROLE` is an
    ArtifactError)."""
    if role is not None and not ROLE.match(role):
        raise ArtifactError(f"artifact role {role!r} is not a lowercase word ({ROLE.pattern}); the initial set is "
                            f"{', '.join(ROLES)}")
    path = Path(path).resolve()
    ref = {"name": name or path.name, "sha256": sha256_bytes_of(path), "media_type": media_type(path),
           "uri": path.as_uri()}
    if frame is not None:
        ref["frame"] = frame
    if role is not None:
        ref["role"] = role
    return ref


def check_artifact_names(refs):
    """ArtifactError when a name is outside the `artifact_ref` pattern or used twice."""
    names = [r["name"] for r in refs]
    bad = sorted({n for n in names if not NAME.match(n)})
    dup = sorted({n for n in names if names.count(n) > 1})
    if bad or dup:
        raise ArtifactError(f"artifact names {'not matching ' + NAME.pattern + ': ' + str(bad) if bad else ''}"
                            f"{'; ' if bad and dup else ''}{'used twice: ' + str(dup) if dup else ''}")
    return refs
