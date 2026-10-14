"""Suite-wide setup: install the engine registry `manifold.sim` discovers as `manifold.core`'s default, so a test that
imports only `manifold.core` composes and validates exactly as the SDK does."""
import manifold.sim  # noqa: F401  (installs the default engine registry)
