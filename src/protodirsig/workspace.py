"""`Workspace`: the SDK's user-facing class, a facade over any `backend.Backend`.

Every method is an operation of the SDK API (`api/operations.md`, `sdk-api/1`) and returns the typed model generated
from its schema (`protodirsig.models`); errors are the `errors.ProblemError` family, raised unchanged from the backend.
`Workspace.local(...)` builds a `LocalBackend`; `Workspace.remote(...)` is phase 3. Two helpers, `wait` and
`save_artifact`, are built only from the operations and are not part of the contract.

Imports no engine package at module level (the backend's worker process is the only engine-bound code).
"""
import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path

from protodirsig import models
from protodirsig.backend import Backend, LocalBackend
from protodirsig.compose import MAX_RUNS

REPOSITORY = Path(__file__).resolve().parents[2]
FINAL_STATES = ("rendered", "failed", "cancelled")


def default_work_root():
    """The default work root of `Workspace.local`: `$XDG_CACHE_HOME/protodirsig/work`, else
    `~/.cache/protodirsig/work`.

    Returns
    -------
    pathlib.Path
        The folder runs are stored under when no `work` is given.
    """
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "protodirsig" / "work"


@dataclass(frozen=True)
class ArtifactContent:
    """The bytes of one artifact and their media type, as `Workspace.get_artifact` returns them.

    Attributes
    ----------
    content : bytes
        The artifact's bytes; their sha256 equals the `sha256` of its reference.
    media_type : str
        The media type of the artifact (for example `application/json`).
    """
    content: bytes
    media_type: str


class Workspace:
    """The SDK facade: library reads, composition, validation, submission, status, cancel and artifacts.

    Parameters
    ----------
    backend : protodirsig.backend.Backend
        Any backend: a `LocalBackend` (see `Workspace.local`) or, in phase 3, a remote one.

    Examples
    --------
    >>> ws = Workspace.local(work="/tmp/protodirsig-work")              # doctest: +SKIP
    >>> status = ws.submit_run("leo_pass_tahoe")                          # doctest: +SKIP
    >>> ws.wait(status.run_id).state                                      # doctest: +SKIP
    'rendered'
    """

    def __init__(self, backend):
        if not isinstance(backend, Backend):
            raise TypeError(f"a Backend is required, got {type(backend).__name__}")
        self.backend = backend

    # --- constructors ---------------------------------------------------------------------------------------------

    @classmethod
    def local(cls, library=None, config_repo=None, work=None, max_parallel=1, sensor_library=None):
        """A workspace over a `LocalBackend` on this machine.

        Parameters
        ----------
        library : str or pathlib.Path, optional
            The layer root (the folder holding `recipes/`, `scenarios/`, `engine_profiles/`); default the
            repository's `manifold_run_specs/`.
        config_repo : str or pathlib.Path, optional
            The engine-asset library, read only; default the repository's `manifold_config_repo/`.
        work : str or pathlib.Path, optional
            The work root runs are stored under; default `default_work_root()`.
        max_parallel : int, optional
            How many runs render at once (default 1).
        sensor_library : str or pathlib.Path, optional
            The sensor library; default the `manifold_sensors/` beside `library`.

        Returns
        -------
        Workspace
            The workspace.

        Examples
        --------
        >>> ws = Workspace.local(work="/tmp/protodirsig-work")              # doctest: +SKIP
        >>> [s.name for s in ws.list_sensors().items]                         # doctest: +SKIP
        ['auror-nir.yaml', 'deepscan_850_306_nir_1280.yaml', 'synthetic_600_200_vis_1920.yaml']
        """
        library = Path(library) if library is not None else REPOSITORY / "manifold_run_specs"
        config_repo = Path(config_repo) if config_repo is not None else REPOSITORY / "manifold_config_repo"
        work = Path(work) if work is not None else default_work_root()
        return cls(LocalBackend(work, config_repo, max_parallel=max_parallel, sensor_library=sensor_library,
                                library=library))

    @classmethod
    def remote(cls, url, token=None):
        """A workspace over a remote backend (phase 3; not built).

        Parameters
        ----------
        url : str
            The REST server's base URL.
        token : str, optional
            An access token.

        Returns
        -------
        Workspace
            Never: this raises.

        Raises
        ------
        NotImplementedError
            Always: `RemoteBackend` is phase 3.
        """
        raise NotImplementedError("RemoteBackend is phase 3")

    # --- the library family ---------------------------------------------------------------------------------------

    def _list(self, kind):
        return models.LibraryList.from_dict(self.backend.list_resources(kind))

    def _get(self, kind, name):
        doc = self.backend.get_resource(kind, name)
        return (models.SensorDocument if kind == "sensor" else models.LibraryDocument).from_dict(doc)

    def list_sensors(self):
        """The library's sensors, by file name, with the sha256 of each file.

        Returns
        -------
        protodirsig.models.LibraryList
            One item per sensor file, sorted by name.
        """
        return self._list("sensor")

    def list_scenarios(self):
        """The library's scenarios, by file stem, with the sha256 of each file.

        Returns
        -------
        protodirsig.models.LibraryList
            One item per scenario file, sorted by name.
        """
        return self._list("scenario")

    def list_engine_profiles(self):
        """The library's engine profiles, by file stem, with the sha256 of each file.

        Returns
        -------
        protodirsig.models.LibraryList
            One item per engine profile file, sorted by name.
        """
        return self._list("engine_profile")

    def list_recipes(self):
        """The library's recipes, by file stem, with the sha256 of each file.

        Returns
        -------
        protodirsig.models.LibraryList
            One item per recipe file, sorted by name.
        """
        return self._list("recipe")

    def get_sensor(self, name):
        """One library sensor as authored: a `sensor-spec/1` document.

        Parameters
        ----------
        name : str
            The sensor's file name (`auror-nir.yaml`) or stem.

        Returns
        -------
        protodirsig.models.SensorDocument
            Its name, the sha256 of its file and the parsed document.

        Raises
        ------
        protodirsig.errors.NotFoundError
            No sensor of that name.
        protodirsig.errors.AdmissionError
            The file does not parse or is not a `sensor-spec/1` document (the problem names the file).
        """
        return self._get("sensor", name)

    def get_scenario(self, name):
        """One library scenario as authored.

        Parameters
        ----------
        name : str
            The scenario's file stem.

        Returns
        -------
        protodirsig.models.LibraryDocument
            Its name, the sha256 of its file and the parsed document.

        Raises
        ------
        protodirsig.errors.NotFoundError
            No scenario of that name.
        protodirsig.errors.AdmissionError
            The file does not parse or is not a scenario (the problem names the file and key).
        """
        return self._get("scenario", name)

    def get_engine_profile(self, name):
        """One library engine profile as authored.

        Parameters
        ----------
        name : str
            The engine profile's file stem.

        Returns
        -------
        protodirsig.models.LibraryDocument
            Its name, the sha256 of its file and the parsed document.

        Raises
        ------
        protodirsig.errors.NotFoundError
            No engine profile of that name.
        protodirsig.errors.AdmissionError
            The file does not parse or is not an engine profile (the problem names the file and key).
        """
        return self._get("engine_profile", name)

    def get_recipe(self, name):
        """One library recipe as authored.

        Parameters
        ----------
        name : str
            The recipe's file stem.

        Returns
        -------
        protodirsig.models.LibraryDocument
            Its name, the sha256 of its file and the parsed document.

        Raises
        ------
        protodirsig.errors.NotFoundError
            No recipe of that name.
        protodirsig.errors.AdmissionError
            The file does not parse or is not a recipe (the problem names the file and key).
        """
        return self._get("recipe", name)

    # --- compose, validate, submit --------------------------------------------------------------------------------

    def compose(self, recipe, inline_sensor=False, max_runs=MAX_RUNS):
        """Compose a recipe into its run specs, without running anything.

        Parameters
        ----------
        recipe : str, pathlib.Path or dict
            A library recipe name, a recipe file, or a recipe document.
        inline_sensor : bool, optional
            Put each sensor's block in place instead of a reference (the run ids are the same).
        max_runs : int, optional
            The most runs a sweep may compose to.

        Returns
        -------
        protodirsig.models.ComposeResponse
            The sweep id and, per run, its run id, name, sensor, run spec and provenance.

        Raises
        ------
        protodirsig.errors.ProblemError
            The recipe does not compose (the problem names the layer file and field), or is unknown.

        Examples
        --------
        >>> ws.compose("sensor_sweep_tahoe").sweep_id                         # doctest: +SKIP
        """
        return models.ComposeResponse.from_dict(self.backend.compose(recipe, inline_sensor=inline_sensor,
                                                                     max_runs=max_runs))

    def validate(self, target, engine_check="none"):
        """Check a run spec or recipe without submitting it.

        Parameters
        ----------
        target : str, pathlib.Path or dict
            A library recipe name, a recipe or run spec file, or a recipe or run spec document.
        engine_check : {"none", "dry_run"}, optional
            `none` (default): the engine-free checks. `dry_run`: also a DIRSIG dry run (needs DIRSIG installed).

        Returns
        -------
        protodirsig.models.ValidateResponse
            Per run: `valid`, whether the engine was checked, and each check with its problems.

        Raises
        ------
        protodirsig.errors.ProblemError
            The recipe does not compose, or the target is unknown or not a recipe or run spec.

        Examples
        --------
        >>> ws.validate("auror_ref").runs[0].valid                            # doctest: +SKIP
        True
        """
        return models.ValidateResponse.from_dict(self.backend.validate(target, engine_check=engine_check))

    def submit_run(self, target):
        """Admit and start one run; returns at once.

        Parameters
        ----------
        target : str, pathlib.Path or dict
            A one-run recipe (library name, file or document) or a run spec (file or document).

        Returns
        -------
        protodirsig.models.RunStatus
            The run's status: `accepted` for a new run, the current state for one already submitted.

        Raises
        ------
        protodirsig.errors.AdmissionError
            Admission failed (schema, resolution, library files, an unstamped reference); nothing was created.
        protodirsig.errors.InvalidRequestError
            The recipe composes to several runs (use `submit_sweep`).

        Examples
        --------
        >>> status = ws.submit_run("leo_pass_tahoe")                          # doctest: +SKIP
        >>> status.state                                                      # doctest: +SKIP
        'accepted'
        """
        return models.RunStatus.from_dict(self.backend.submit_run(target))

    def submit_sweep(self, recipe):
        """Admit every run of a sweep recipe as a whole and start them; returns at once.

        Parameters
        ----------
        recipe : str, pathlib.Path or dict
            A library recipe name, a recipe file or a recipe document.

        Returns
        -------
        protodirsig.models.SweepStatus
            The sweep id, the recipe, and the status of each run in sensor-list order.

        Raises
        ------
        protodirsig.errors.AdmissionError
            Any run failed admission; the problem lists every failing run and nothing was created.
        """
        return models.SweepStatus.from_dict(self.backend.submit_sweep(recipe))

    # --- status, cancel, artifacts --------------------------------------------------------------------------------

    def get_run(self, run_id):
        """The status of one run.

        Parameters
        ----------
        run_id : str
            The run id (64 hex digits).

        Returns
        -------
        protodirsig.models.RunStatus
            Its state, errors and artifacts.

        Raises
        ------
        protodirsig.errors.NotFoundError
            No run of that id.
        """
        return models.RunStatus.from_dict(self.backend.get_run(run_id))

    def get_sweep(self, sweep_id):
        """The status of one sweep.

        Parameters
        ----------
        sweep_id : str
            The sweep id (64 hex digits).

        Returns
        -------
        protodirsig.models.SweepStatus
            The recipe and each run's status.

        Raises
        ------
        protodirsig.errors.NotFoundError
            No sweep of that id.
        """
        return models.SweepStatus.from_dict(self.backend.get_sweep(sweep_id))

    def cancel_run(self, run_id):
        """Cancel a run that is `accepted` or `running`; a run in a final state is returned unchanged.

        Parameters
        ----------
        run_id : str
            The run id.

        Returns
        -------
        protodirsig.models.RunStatus
            The run's status after the call.

        Raises
        ------
        protodirsig.errors.NotFoundError
            No run of that id.
        """
        return models.RunStatus.from_dict(self.backend.cancel_run(run_id))

    def list_artifacts(self, run_id):
        """The references of a run's artifacts so far.

        Parameters
        ----------
        run_id : str
            The run id.

        Returns
        -------
        protodirsig.models.ArtifactList
            One reference per artifact (name, sha256, media type, `file://` URI, and `frame` for per-capture
            products).

        Raises
        ------
        protodirsig.errors.NotFoundError
            No run of that id.
        """
        return models.ArtifactList.from_dict(self.backend.list_artifacts(run_id))

    def get_artifact(self, run_id, name):
        """The bytes of one artifact.

        Parameters
        ----------
        run_id : str
            The run id.
        name : str
            The artifact's name, as `list_artifacts` gives it.

        Returns
        -------
        ArtifactContent
            The bytes and their media type.

        Raises
        ------
        protodirsig.errors.NotFoundError
            No run of that id, or no artifact of that name.
        """
        content, media_type = self.backend.get_artifact(run_id, name)
        return ArtifactContent(content, media_type)

    # --- helpers, not part of the contract ------------------------------------------------------------------------

    def wait(self, run_id, timeout=None, poll=2.0):
        """Poll `get_run` until the run reaches a final state. A helper, not an operation of the contract.

        Parameters
        ----------
        run_id : str
            The run id.
        timeout : float, optional
            Seconds to wait at most; None waits without limit.
        poll : float, optional
            Seconds between polls (default 2).

        Returns
        -------
        protodirsig.models.RunStatus
            The run's final status (`rendered`, `failed` or `cancelled`).

        Raises
        ------
        TimeoutError
            The run was not final after `timeout` seconds.
        protodirsig.errors.NotFoundError
            No run of that id.

        Examples
        --------
        >>> ws.wait(status.run_id, timeout=600).state                         # doctest: +SKIP
        'rendered'
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            status = self.get_run(run_id)
            if status.state in FINAL_STATES:
                return status
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(f"run {run_id} is still {status.state} after {timeout} s")
            time.sleep(poll)

    def save_artifact(self, run_id, name, destination):
        """Write one artifact to a file and verify its sha256 against `list_artifacts`. A helper, not an operation of
        the contract.

        Parameters
        ----------
        run_id : str
            The run id.
        name : str
            The artifact's name.
        destination : str or pathlib.Path
            The file to write, or an existing directory to write `name` into.

        Returns
        -------
        pathlib.Path
            The file written.

        Raises
        ------
        protodirsig.errors.NotFoundError
            No run of that id, or no artifact of that name.
        ValueError
            The bytes do not match the reference's sha256 (nothing is left at the destination).
        """
        refs = {a.name: a for a in self.list_artifacts(run_id).artifacts}
        content = self.get_artifact(run_id, name)
        want = refs[name].sha256 if name in refs else None
        got = hashlib.sha256(content.content).hexdigest()
        if want is not None and got != want:
            raise ValueError(f"artifact {name} of run {run_id}: sha256 {got} does not match its reference {want}")
        path = Path(destination)
        if path.is_dir():
            path = path / name
        path.write_bytes(content.content)
        return path
