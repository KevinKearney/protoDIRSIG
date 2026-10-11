"""Every name-derived string of the package, in one place: the import root, the environment-variable prefix, the
problem-type URN prefix, the state directory name, the legacy aliases, and the strings frozen because they are part
of recorded content.

Code builds these strings from the constants here rather than spelling the package name; `tests/test_names.py` fails
when a string literal holding the pre-rename package name appears in source outside this module. `getenv` reads an
environment variable under the current prefix and falls back to the legacy prefix with one `DeprecationWarning` per
variable per process. Standard library only.
"""
import os
import warnings

PACKAGE = "manifold"                          # the import root: a PEP 420 namespace, no distribution ships its __init__
CORE_PACKAGE = PACKAGE + ".core"              # distribution eoptic-manifold-core
SIM_PACKAGE = PACKAGE + ".sim"                # distribution eoptic-manifold-sim
DISTRIBUTION_CORE = "eoptic-manifold-core"    # distribution names carry the eoptic- prefix (a public PyPI "manifold"
DISTRIBUTION_SIM = "eoptic-manifold-sim"      # project exists); the import name stays manifold
DISTRIBUTION = DISTRIBUTION_SIM               # the distribution whose version the SDK reports
WORKER_MODULE = SIM_PACKAGE + ".worker"       # python -m WORKER_MODULE <run_dir>
ENV_PREFIX = "MANIFOLD_"                      # environment variables: ENV_PREFIX + "CONTRACTS", ...
URN_PREFIX = "urn:manifold:problem:"          # problem types: URN_PREFIX + "compose", ...
STATE_DIR_NAME = "manifold"                   # $XDG_STATE_HOME/<STATE_DIR_NAME>/work
LOGGER_NAME = PACKAGE                         # the logging.getLogger name
TEMP_PREFIX = PACKAGE + "_"                   # tempfile.mkdtemp prefixes

# Legacy aliases: the names a previous release used, still read (and warned about) where a reader may meet them.
LEGACY_PACKAGE = "protodirsig"
LEGACY_ENV_PREFIX = "PROTODIRSIG_"
LEGACY_STATE_DIR_NAME = "protodirsig"         # $XDG_STATE_HOME/protodirsig/work: named once, never moved
LEGACY_WORKER_MODULE = LEGACY_PACKAGE + ".worker"   # the worker's command line in run records from before start times

# Frozen identity strings: a name-derived string that reaches content an id hashes (a descriptor member, an engine
# block member such as a generator name, a settings provenance label) would be part of the identity of existing runs
# and must not change with a rename. The round 17 audit found none: the package name appears in no hashed member (the
# engine generator is `dirfm`; provenance labels are `specified` and `modeled`), only in YAML comments, which are not
# parsed and so not hashed. Keep this empty unless such a string appears.
FROZEN_IDENTITY_STRINGS = ()

# Frozen record member: the execution record (`execution.json`, not hashed) names the SDK version under this key.
# Renaming it would change a recorded member, which this round does not; it stays until a record schema change.
RECORD_VERSION_KEY = "protodirsig_version"


def env(name):
    """The environment variable `name` (`"CONTRACTS"`, ...) under the current prefix."""
    return ENV_PREFIX + name


_WARNED = set()


def getenv(name, default=None):
    """The value of `MANIFOLD_<name>`; if it is not set, of the legacy `PROTODIRSIG_<name>`, with one
    `DeprecationWarning` per variable per process; else `default`."""
    new, old = ENV_PREFIX + name, LEGACY_ENV_PREFIX + name
    if new in os.environ:
        return os.environ[new]
    if old in os.environ:
        if old not in _WARNED:
            _WARNED.add(old)
            warnings.warn(f"{old} is deprecated; set {new} instead", DeprecationWarning, stacklevel=2)
        return os.environ[old]
    return default


def module(name):
    """The dotted path of a module under the import root (`"sim.worker"` -> `"manifold.sim.worker"`)."""
    return f"{PACKAGE}.{name}"


def problem(kind):
    """The problem-type URN of `kind` (`"compose"`, `"admission"`, ...)."""
    return URN_PREFIX + kind
