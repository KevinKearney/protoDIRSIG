# protoDIRSIG — dirfm/DIRSIG findings

Running record of capability gaps, behavior/documentation discrepancies, and correctness
traps discovered while building the tutorial notebooks against this DIRSIG install
(`dirsig-2026.38.0.a020954`) and this `dirsig-file-maker` checkout. Each entry states what
was found, how it was confirmed, and what the notebooks do about it. Append to this file
as new findings surface; do not let them live only in commit messages or chat history.

## dirfm capability gaps

**No `EarthGrid` wrapper.** `dirfm/*.py` has no class for DIRSIG's `EarthGrid` plugin
(confirmed by exhaustive grep across the package and `demos/`; the only `grid` hits are
unrelated utilities — `dggrid.py`, `curved_tile_generator.py`, `grid_position_generator.py`).
DIRSIG's bundled `StkImport1` demo is scene-less and uses `EarthGrid` as its only geometry.
`tutorial_orbit_to_ground.ipynb` substitutes a conventional `SCENE` with a `GroundPlane` —
a deliberate stand-in, not a reproduction of the Blue Marble globe.

**No STK-report import path.** `WaypointsLocationEngine` always writes
`source="internal"`/`datetime="relative"`; there is no `source="stk_report"` option, the
mechanism DIRSIG's own `demo.motion` uses to read a `.e` file directly. `frame` is an
unconstrained string, so `frame="ecef"` passes through — that part works.

**No quaternion orientation engine.** The only orientation engines are `Euler`, `LookAt`,
`Spin`, `Velocity`. DIRSIG's STK-import idiom (`orientationengine type="quaternions"`,
`source="stk_report"`) has no dirfm counterpart.

**`LookAtOrientationEngine`'s `up` is always a fixed vector.** It only ever writes
`<up frame="scene" vector="…"/>`. DIRSIG's own nadir-pointing idiom for an orbiting platform
(`StkImport1`'s `stare.motion`, and the FlexMotion manual's "Landsat Orbit" example) uses
`<up type="velocity" frame="ecef">` — an up-reference that tracks instantaneous velocity.
dirfm cannot express that. `tutorial_orbit_to_ground.ipynb` substitutes a fixed vector,
computed and verified per-pass (angle to boresight, roll error vs. true velocity-up over
every sample) rather than assumed — see the notebook's Stage 1 for the check.

**No SGP4/TLE propagator.** A naive `grep -i "sgp4|tle"` returns false positives (substrings
of `title`, `little-endian`, `unitless`); a whole-word search of the package and `demos/`,
plus a search for any SGP4 library import, comes back empty. TLE propagation is done in
plain Python (`skyfield`, Stage 1 of the orbit-to-ground notebook); only the resulting ECEF
samples cross into dirfm via the existing `WaypointsLocationEngine`.

## DIRSIG behavior vs. documentation

**`GROUND_PLANE` is documented as infinite, observed as finite.** `docs/odb.html` states the
plane "extends infinitely in the XY plane" and that a simple plane's anchor X,Y are unused.
Empirically (this DIRSIG build, `2026.38.0.a020954`) a single `GROUND_PLANE` renders as a
finite ~2 km square centered on its anchor (~±1000 m) — geometry outside that footprint is
absent, not just haze-obscured (truth-image center matches the predicted boresight intercept
to within 1 m, confirming the geometry chain otherwise; the black region is a real gap in the
primitive's extent). Open question, not yet resolved: whether the cutoff is intrinsic to the
primitive or an artifact of an inferred scene bounding volume (test: does adding distant
geometry, or an explicit larger scene extent, push the cutoff outward?). If intrinsic, this
is a documentation defect in DIRSIG itself, not a dirfm gap — `GroundPlane(anchor, material)`
has no size parameter because the manual says it shouldn't need one. Working around it with a
tiled grid of `GROUND_PLANE` instances if the cause turns out to be intrinsic; watch
checkerboard-phase alignment across tile seams if `add_checkerboard` is used.

## Correctness traps (methodology, not gaps)

**ECI vs. ECEF is a silent-failure class, not a one-off.** It surfaced twice, differently.
StkImport1's `.e` file declares `CoordinateSystem Fixed` (STK's term for ECEF) — no rotation
needed, confirmed from the file header rather than assumed. Raw SGP4 output is TEME (near-
inertial) with no such self-declaration; treating it as ECEF put the computed sub-satellite
point ~8,000–9,000 km from its actual location, with no error or warning anywhere in the
pipeline. Do not hand-roll the TEME→ECEF rotation (axis order, angle sign, and sidereal-time
model are all easy to get wrong invisibly) — use a maintained library (`skyfield`) and verify
its output independently (this was checked three ways: Z-invariance under a pole-only
rotation, rotation angle vs. an independently computed GMST, rotation rate vs. Earth's known
sidereal rate).

**A nadir-pointing `LookAt` is geometrically singular by default.** The boresight from an
orbiting platform to Earth's center is nearly antiparallel to the default `up = [0,0,1]`
(local vertical), which makes the roll computation ill-conditioned. A horizontal up-vector
(anything near-perpendicular to the boresight) resolves it; verify per-pass rather than
reuse a prior pass's choice — the correct fixed vector depends on the ground track's heading
and the target's location, both of which change if either input changes.

**`pip install -e .` writes into a checkout that must stay read-only.** Installing dirfm
editable from its own directory drops a `dirfm.egg-info/` into the checkout (and, if that
install then fails partway, can leave stray `.git/index.lock` files behind) — a real write to
a directory `prompt.md` designates read-only. If dirfm needs to be importable outside the
documented conda workflow (`pip install -e /path/to/dirsig-file-maker` inside the
`protodirsig` environment), prefer `sys.path.insert(0, ...)` at runtime over a fresh editable
install against the checkout.

## Notebooks (status)

- `notebooks/tutorial_dirfm_basics.ipynb` — Phase 1, complete. 8 stages, executed end to end.
- `notebooks/tutorial_orbit_to_ground.ipynb` — Phase 2, in progress. Stages 0–1 complete,
  executed, and committed (TLE/SGP4 trajectory, dropped the original STK-import approach —
  see `prompt.md` for the full rationale). Stage 2 (ground scene + sensor) in progress;
  current blocker is the `GROUND_PLANE` finite-footprint issue above.

## External reference

`~/dev/agent-docs` (Rendered.ai's agent-context repo) documents a production dirfm
architecture — a node-graph channel (`dirsig_pkg`) wrapping the same `dirfm` primitives used
here, with per-node `exec()` methods, seed-based determinism via `ctx.seed`, and truth-band
annotations. Relevant if protoDIRSIG's batch driver is ever deployed as a Rendered.ai channel
rather than run as a standalone script; not otherwise load-bearing for this project.
