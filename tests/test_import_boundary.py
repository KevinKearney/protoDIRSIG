"""The import boundary: the composer, registry and loader do not load the propagator, and `orbit` loads no engine
package at import. Each check runs in a fresh interpreter, so modules imported by other tests do not count.

`dirfm` is not yet outside the boundary of `compose`, `registry` and `run_spec`: `run_spec` imports
`atmosphere_patches` and `platform_ref` (both `dirfm` subclasses) at module level, and `compose` and `registry`
import `run_spec`. Those three are the engine-bound set; the dirfm check is asserted only for modules that pass it.
"""
import json
import subprocess
import sys

import pytest

PROPAGATOR = ("skyfield", "sgp4")
ENGINE = ("dirfm",)
DIRFM_BOUND = {"protodirsig.compose", "protodirsig.registry", "protodirsig.run_spec"}   # known; not refactored yet


def _loaded(module):
    code = (f"import json, sys, {module}\n"
            f"print(json.dumps(sorted({{m.split('.')[0] for m in sys.modules}})))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    return set(json.loads(out))


@pytest.mark.parametrize("module", ["protodirsig.compose", "protodirsig.registry", "protodirsig.run_spec",
                                    "protodirsig.orbit"])
def test_module_does_not_load_the_propagator(module):
    assert _loaded(module).isdisjoint(PROPAGATOR)


@pytest.mark.parametrize("module", ["protodirsig.orbit"])
def test_module_does_not_load_the_engine_package(module):
    assert _loaded(module).isdisjoint(ENGINE)


def test_the_engine_bound_set_is_as_recorded():
    """If one of these stops loading dirfm, move it to the test above and shrink DIRFM_BOUND."""
    assert {m for m in DIRFM_BOUND if "dirfm" in _loaded(m)} == DIRFM_BOUND
