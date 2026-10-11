"""Every name-derived string of the package, in one place: the import root, the environment-variable prefix, the
problem-type URN prefix, the state directory name, the legacy aliases, and the strings frozen because they are part
of recorded content.

Code builds these strings from the constants here rather than spelling the package name; `tests/test_names.py` fails
when a string literal holding the package name appears in source outside this module. Standard library only.
"""

PACKAGE = "protodirsig"                       # the import root
DISTRIBUTION = "protodirsig"                  # the distribution whose version the package reports
ENV_PREFIX = "PROTODIRSIG_"                   # environment variables: ENV_PREFIX + "CONTRACTS", ...
URN_PREFIX = "urn:protodirsig:problem:"       # problem types: URN_PREFIX + "compose", ...
STATE_DIR_NAME = "protodirsig"                # $XDG_STATE_HOME/<STATE_DIR_NAME>/work
LOGGER_NAME = PACKAGE                         # the logging.getLogger name
TEMP_PREFIX = PACKAGE + "_"                   # tempfile.mkdtemp prefixes

# Legacy aliases: the names a previous release used, still read (and warned about) where a reader may meet them.
LEGACY_PACKAGE = "protodirsig"
LEGACY_ENV_PREFIX = "PROTODIRSIG_"
LEGACY_STATE_DIR_NAME = "protodirsig"

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


def module(name):
    """The dotted path of a submodule of the package (`"worker"` -> `"protodirsig.worker"`)."""
    return f"{PACKAGE}.{name}"


def problem(kind):
    """The problem-type URN of `kind` (`"compose"`, `"admission"`, ...)."""
    return URN_PREFIX + kind
