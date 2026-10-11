"""`protodirsig.admission`: `manifold.core.admission`, plus the DIRSIG resolution names it used to import."""
from manifold.core.admission import *  # noqa: F401,F403
from manifold.core.passthrough_spec import is_passthrough, resolve_passthrough  # noqa: F401
from manifold.core.run_spec import RunSpecError, check_library_files, resolve_run, unstamped_refs  # noqa: F401
