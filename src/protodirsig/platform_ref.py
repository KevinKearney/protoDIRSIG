"""Reference existing platform/motion/tasks files and SPICE defaults from a dirfm job.

The plugin-side counterpart of `scene_ref`: a `.platform`, `.ppd`/`.motion` and `.tasks` file
that already exist on disk are used as they are, instead of being rebuilt from dirfm objects. In
the stage jobs the platform is the manifold_config_repo library file and the motion and tasks are
generated from the run spec by `motion_tasks` (Stage 05); the plugin only checks that the three
paths are files.
`PlatformSensorPlugin.prepare()` always regenerates those files, and `DIRSIG.write_files()`
requires a `PlatformSensorPlugin` instance to be present. So `PlatformFilesPlugin` subclasses
it with no attachments, which also means dirfm's coverage loop has nothing to iterate. Use
`scene_coverage` for that.
"""
from pathlib import Path

from dirfm.ephemeris import EphemerisPlugin
from dirfm.platform_sensor import PlatformSensorPlugin
from dirfm.utilities.paths import relativize_path


class PlatformFilesPlugin(PlatformSensorPlugin):
    """`BasicPlatform` over existing files; paths inside the job's in_root are written relative."""

    def __init__(self, platform, motion, tasks, split_channels=False):
        super().__init__()
        self._files = {"platform_filename": Path(platform), "motion_filename": Path(motion),
                       "tasks_filename": Path(tasks)}
        self._split = split_channels

    def prepare(self, dirs):
        missing = [str(p) for p in self._files.values() if not p.is_file()]
        assert not missing, f"missing platform inputs: {missing}"

    def get_plugin_inputs(self, dirs=None):
        render = (lambda p: relativize_path(dirs, p, "root")) if dirs is not None else (lambda p: p.as_posix())
        return {**{k: render(p) for k, p in self._files.items()}, "split_channels": self._split}


class SpiceEphemerisPlugin(EphemerisPlugin):
    """`SpiceEphemeris` with `inputs: {}` (DIRSIG's bundled kernels). dirfm's `SPICEPlugin`
    requires three kernel paths."""

    def __init__(self):
        super().__init__()
        self._name = "SpiceEphemeris"
