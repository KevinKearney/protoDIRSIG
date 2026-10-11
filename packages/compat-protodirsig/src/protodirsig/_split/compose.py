"""`protodirsig.compose`: `manifold.core.compose`, plus `black_level_problem` (now the DIRSIG engine's rule)."""
from manifold.core.compose import *  # noqa: F401,F403
from manifold.engines.dirsig.run_spec import black_level_problem  # noqa: F401
