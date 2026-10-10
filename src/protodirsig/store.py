"""The run store: one directory per run under a work root, keyed by run id; the state of every run lives here.

Layout (proposed; MANIFOLD's analogue is `<work>/<run_id>/inputs`):

    <work_root>/runs/<run_id>/
        run_spec.json     the RFC 8785 canonical bytes of the resolved run spec (sensor inline): sha256 = run id
        run_spec.yaml     the same spec as YAML, what the executor loads (canonical JSON is not fed to the YAML
                          loader: PyYAML reads numbers such as 5e-07 as strings)
        status.json       a `run_status` document (run_id, name, state, errors, artifacts)
        execution.json    the execution record (times, worker pid and process group, versions); never in a run id
        job.json          the worker's inputs (config repository, sensor library, work root, max_parallel)
        artifacts.json    the artifact references of a rendered run, hashed once
        worker.log        the worker's output
        status.lock       the lock that serializes status and record updates
        input/ output/    the DIRSIG job
    <work_root>/sweeps/<sweep_id>/sweep.json   sweep id, recipe name and sha256, run ids in sensor-list order
    <work_root>/slots/slot-<i>.lock           one per parallel worker slot

`create_run` writes a run into a temporary directory and renames it into place, so a run directory is either absent or
complete; two creators of one run id race safely (one gets `created=True`). `update_status` is a compare-and-set
under an exclusive `fcntl.flock`, written by temporary file and `os.replace`. `reap` fails a run whose worker died.
States: `accepted`, `running`, then one final state, `rendered`, `failed` or `cancelled`.

POSIX only (`fcntl`, `/proc`, process groups). Imports: the standard library, `yaml`, and pure `protodirsig` modules
(`identity`, `errors`, `problems`); no engine package.
"""
import fcntl
import hashlib
import json
import os
import re
import shutil
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import yaml

from protodirsig import identity, problems
from protodirsig.errors import NotFoundError

STATES = ("accepted", "running", "rendered", "failed", "cancelled")
FINAL = ("rendered", "failed", "cancelled")
ACTIVE = ("accepted", "running")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")               # artifact_ref.schema.json `name`
ID = re.compile(r"^[0-9a-f]{64}$")
MEDIA_TYPES = {".img": "application/octet-stream", ".hdr": "text/plain", ".log": "text/plain", ".txt": "text/plain",
               ".json": "application/json", ".png": "image/png"}
RUN_LEVEL = ("run_info.json", "log_info.json")                  # engine logs: the run as a whole, no frame
WORKER_GRACE_S = 60                                             # an active run with no worker pid this old is dead


class ArtifactError(ValueError):
    """Artifact names that collide or do not match the `artifact_ref` pattern: recorded as a failed run."""


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def media_type(path):
    return MEDIA_TYPES.get(Path(path).suffix.lower(), "application/octet-stream")


def sha256_bytes_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def artifact_ref(path, name=None, frame=None):
    """An `artifact_ref` document for a file: name (its base name), sha256 of the bytes, media type, `file://` URI."""
    path = Path(path).resolve()
    ref = {"name": name or path.name, "sha256": sha256_bytes_of(path), "media_type": media_type(path),
           "uri": path.as_uri()}
    if frame is not None:
        ref["frame"] = frame
    return ref


def _write_json(path, doc):
    """Write by temporary file and `os.replace`, so a reader sees the old or the new document, never half of one."""
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def _read_json(path):
    return json.loads(Path(path).read_text())


def _frames(run_dir):
    """[(frame, image path, truth paths)] from the engine's log_info.json, in task order (task, then capture)."""
    log = run_dir / "output" / "log_info.json"
    if not log.is_file():
        return []
    caps = _read_json(log).get("capture_list", [])
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


def _pid_is_worker(pid):
    """The process exists, is not a zombie, and is a protodirsig worker (by its command line, where /proc exists)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    proc = Path("/proc") / str(pid)
    if not proc.is_dir():
        return True                                             # no /proc: existence is all that can be checked
    try:
        stat = (proc / "stat").read_text()
        if stat[stat.rindex(")") + 2] in "ZX":
            return False
        return b"protodirsig.worker" in (proc / "cmdline").read_bytes()
    except (OSError, ValueError, IndexError):
        return False


class RunStore:
    """The runs and sweeps under one work root. Every method reads or writes the files, so two stores (two
    `LocalBackend` instances, two processes) on one work root see the same runs."""

    def __init__(self, work_root):
        self.root = Path(work_root).resolve()
        self.runs, self.sweeps, self.slots = self.root / "runs", self.root / "sweeps", self.root / "slots"
        for d in (self.runs, self.sweeps, self.slots):
            d.mkdir(parents=True, exist_ok=True)

    # --- runs ---------------------------------------------------------------------------------------------------

    def run_dir(self, run_id):
        if not isinstance(run_id, str) or not ID.match(run_id):
            raise NotFoundError("run", run_id)
        return self.runs / run_id

    def _complete(self, d):
        try:
            _read_json(d / "status.json")
            return True
        except (OSError, ValueError):
            return False

    def create_run(self, spec_resolved, name, job):
        """Create the run directory for a resolved run spec (sensor inline). Returns `(run_id, created)`: `created` is
        False when the run already exists (nothing is written). Raises ValueError if the stored bytes would not hash
        to the run id or the YAML form would not reproduce it."""
        canonical = identity.canonical_json(spec_resolved)
        run_id = identity.sha256_hex(canonical)
        target = self.runs / run_id
        if target.exists() and self._complete(target):
            return run_id, False
        tmp = self.runs / f".tmp-{uuid.uuid4().hex}"
        tmp.mkdir()
        try:
            (tmp / "run_spec.json").write_bytes(canonical)
            (tmp / "run_spec.yaml").write_text(yaml.safe_dump(spec_resolved, sort_keys=False, allow_unicode=True,
                                                              width=110, default_flow_style=False))
            if hashlib.sha256((tmp / "run_spec.json").read_bytes()).hexdigest() != run_id:
                raise ValueError("run_spec.json does not hash to the run id")
            reloaded = yaml.safe_load((tmp / "run_spec.yaml").read_text())
            if identity.run_id(reloaded, self.root) != run_id:
                raise ValueError("run_spec.yaml does not reproduce the run id (the YAML round trip changed a value)")
            (tmp / "status.lock").touch()
            (tmp / "job.json").write_text(json.dumps({**job, "work_root": str(self.root)}, indent=1) + "\n")
            _write_json(tmp / "execution.json", {"run_id": run_id, "submitted_at": utc_now()})
            spec_ref = {"name": "run_spec.json", "sha256": run_id, "media_type": "application/json",
                        "uri": (target / "run_spec.json").as_uri()}
            _write_json(tmp / "status.json", {"run_id": run_id, "name": name, "state": "accepted", "errors": [],
                                              "artifacts": [spec_ref]})
            if target.exists():                                     # incomplete leftover: replace it
                if self._complete(target):                          # ... unless another creator just finished it
                    return run_id, False
                stale = self.runs / f".stale-{uuid.uuid4().hex}"
                try:
                    os.rename(target, stale)
                    shutil.rmtree(stale, ignore_errors=True)
                except OSError:
                    pass
            try:
                os.rename(tmp, target)
            except OSError:                                         # another creator won the race
                if self._complete(target):
                    return run_id, False
                raise
            return run_id, True
        finally:
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)

    @contextmanager
    def _locked(self, run_id):
        d = self.run_dir(run_id)
        if not d.is_dir():
            raise NotFoundError("run", run_id)
        with open(d / "status.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield d
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _status(self, run_id):
        d = self.run_dir(run_id)
        try:
            return _read_json(d / "status.json")
        except (OSError, ValueError):
            raise NotFoundError("run", run_id) from None

    def read_status(self, run_id, reap=True):
        """The run's `run_status` document; an active run whose worker died is failed first (`reap`)."""
        if reap:
            self.reap(run_id)
        return self._status(run_id)

    def update_status(self, run_id, expected_states, new):
        """Compare-and-set: if the state is one of `expected_states`, merge `new` into the status and write it.
        Returns `(updated, status)`; a stale expected state leaves the status unchanged and returns False."""
        with self._locked(run_id) as d:
            status = _read_json(d / "status.json")
            if status["state"] not in expected_states:
                return False, status
            if "state" in new and new["state"] not in STATES:
                raise ValueError(f"unknown state {new['state']!r}")
            status = {**status, **new}
            _write_json(d / "status.json", status)
            return True, status

    def read_record(self, run_id):
        return _read_json(self.run_dir(run_id) / "execution.json")

    def update_record(self, run_id, fields):
        """Merge `fields` into the execution record."""
        with self._locked(run_id) as d:
            record = {**_read_json(d / "execution.json"), **fields}
            _write_json(d / "execution.json", record)
            return record

    def read_job(self, run_id):
        return _read_json(self.run_dir(run_id) / "job.json")

    def list_runs(self):
        """The ids of every complete run, each reaped first."""
        ids = sorted(p.name for p in self.runs.iterdir() if ID.match(p.name) and self._complete(p))
        for run_id in ids:
            self.reap(run_id)
        return ids

    def artifacts(self, run_id):
        """A rendered run's cached references (`artifacts.json`); otherwise `run_spec.json` and the engine logs that
        exist, hashed now."""
        d = self.run_dir(run_id)
        status = self.read_status(run_id)
        cached = d / "artifacts.json"
        if status["state"] == "rendered" and cached.is_file():
            return _read_json(cached)
        return artifacts_for(d, final=False)

    def write_artifacts(self, run_id, refs):
        _write_json(self.run_dir(run_id) / "artifacts.json", refs)

    def reap(self, run_id):
        """Fail an active run whose worker is gone: the recorded pid is not a live `protodirsig.worker`, or no worker
        pid was recorded and the run was submitted more than WORKER_GRACE_S ago. Returns True if it failed the run."""
        status = self._status(run_id)
        if status["state"] not in ACTIVE:
            return False
        try:
            record = self.read_record(run_id)
        except (OSError, ValueError):
            record = {}
        pid = (record.get("worker") or {}).get("pid")
        if pid is not None:
            if _pid_is_worker(pid):
                return False
            why = f"the worker (pid {pid}) is no longer running"
        else:
            submitted = record.get("submitted_at")
            age = time.time() - datetime.fromisoformat(submitted.replace("Z", "+00:00")).timestamp() if submitted else 1e9
            if age <= WORKER_GRACE_S:
                return False
            why = f"no worker was started within {WORKER_GRACE_S} s of submission"
        problem = problems.execution_failed(run_id, status["name"], f"{why}; the run did not finish")
        updated, _ = self.update_status(run_id, ACTIVE, {"state": "failed", "errors": [problem]})
        if updated:
            self.update_record(run_id, {"finished_at": utc_now(), "reaped": why})
        return updated

    # --- sweeps -------------------------------------------------------------------------------------------------

    def create_sweep(self, sweep_id, record):
        """Write `sweeps/<sweep_id>/sweep.json` unless it exists. Returns `(record, created)`."""
        if not ID.match(sweep_id):
            raise ValueError(f"not a sweep id: {sweep_id!r}")
        d = self.sweeps / sweep_id
        if (d / "sweep.json").is_file():
            return _read_json(d / "sweep.json"), False
        tmp = self.sweeps / f".tmp-{uuid.uuid4().hex}"
        tmp.mkdir()
        _write_json(tmp / "sweep.json", {"sweep_id": sweep_id, **record})
        try:
            os.rename(tmp, d)
            return _read_json(d / "sweep.json"), True
        except OSError:
            shutil.rmtree(tmp, ignore_errors=True)
            return _read_json(d / "sweep.json"), False

    def read_sweep(self, sweep_id):
        """The sweep record; NotFoundError for an unknown id."""
        try:
            if ID.match(str(sweep_id)):
                return _read_json(self.sweeps / sweep_id / "sweep.json")
        except (OSError, ValueError):
            pass
        raise NotFoundError("sweep", sweep_id)
