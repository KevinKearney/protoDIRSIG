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

## Referencing a pre-existing scene: not a gap, and no import path is needed

The question that prompted this entry: dirfm's `SCENE` class has no method that reads an
existing `.scene` file into a Python object, and no code anywhere in the package parses
GDB/ODB/GLIST geometry back out of disk. The initial reading of that fact — that dirfm
cannot use a pre-built scene such as the bundled `Tacoma-08-Apr-2022` demo — does not
survive a look at DIRSIG5's own file architecture, which was checked independently against
the framework documentation and a second, unrelated dirfm-based codebase.

Background: DIRSIG5's simulation entry point is the `.jsim` file, whose `scene_list` is a
list of `{inputs, offset}` entries. `inputs` is a filesystem path to a `.scene` XML file — a
string, not an embedded or parsed structure. `scene2hdf` compiles that path's contents to an
HDF acceleration structure, and `dirsig5` renders against the compiled HDF. Nothing between
the jsim and the renderer requires a `.scene` file's contents to pass through any
intermediate object model; the path is the interface. RIT's own scene-format documentation
(`docs/new/scene.html`) confirms there is no scene-to-scene include or reference mechanism
inside the `.scene` format itself — a scene references geometry lists (`<geometrylist>`,
which can point at GDB, GLIST, or ODB files) and exactly one material database
(`<matfilename>`), and nothing resembling a nested or included scene. The one
cross-scene extension mechanism that exists — `DIRSIG_BUNDLE_PATH`, an environment variable
naming a search directory of reusable material/object bundles — is a search-path convention
for shared assets, not a scene-reference mechanism, and unrelated to this question.

The implication: "running a scene" (DIRSIG5's stated primary use case) and "authoring a
scene programmatically" (dirfm's stated purpose, per its own README) are operations at
different layers. The runtime consumes a scene by path; nothing above the runtime needs to
read a scene's contents to use it. dirfm's `SCENE` class exists to build the XML that path
points at — construct geometry and material objects in Python, then serialize; it was never
positioned as a general-purpose scene reader, and DIRSIG's own architecture gives it no
reason to be one. The intuition that a scene-running tool must be able to load scenes treats
"scene" as an opaque asset type requiring a parser, the way an image library must decode
JPEG to use one; DIRSIG's model is closer to a build system consuming an already-compiled
object file — nothing reads apart the file's insides once its path is known.

Independent corroboration: Rendered.ai's `dirsig-channel` repository
(https://github.com/Rendered-ai/dirsig-channel) is a second, unrelated production consumer
of dirfm, built as a node-graph "channel" for synthetic-data generation. Every scene node in
that codebase (e.g., a "Desert Highway" node) constructs its scene by calling `SCENE()` and
the `glist` geometry classes from Python, the same object-graph-authoring pattern used here;
no code path in that repository opens or references a pre-existing `.scene` file either.
Two independent dirfm-based systems treating "generate a scene from code" as the only
scene-construction pattern is evidence this is normal usage of the library as designed, not
a gap both projects independently failed to notice.

Direct evidence in the source, re-read from the checkout rather than recalled: `SCENE.__init__`
(`dirfm/scene.py`) sets `self._fname = None` unconditionally. `SCENE.write()`'s first
statement is `if hasattr(self, '_fname') and self._fname is not None: return self._fname` —
before any geometry or material serialization runs. No method in the class ever assigns
`_fname` prior to `write()` except `write()` itself (which sets it once serialization is
complete, presumably for idempotent re-calls). The only way `_fname` is non-`None` on entry
to `write()` is if a caller set it directly. That is a deliberate escape hatch: a `SCENE`
instance can stand in for an already-existing scene file, with `write()` becoming a no-op
that just returns the given path.

Practical mechanism, worked out from `DIRSIG.add_scene()` and `DIRSIG.write_files()`
(`dirfm/dirsig.py`): `add_scene()` only asserts `isinstance(scene, SCENE)`, so a bare
`SCENE("tacoma")` with `_fname` set manually satisfies it. `write_files()` calls the
scene's directory setters (`set_ems_dir`, `set_ext_dir`, `set_abs_dir`, `set_src_dir`,
`set_map_dir`) before calling `write()` — each of these only asserts the target directory
exists and stores the path; none inspect scene content, so they are harmless regardless of
what the scene actually contains. `write()` then returns the pre-set `_fname` immediately.
The resulting path flows into `JSIM`'s `scene_list` exactly as a freshly-authored scene's
path would. Concretely:

```python
tacoma_scene = SCENE("tacoma")
tacoma_scene._fname = Path("/path/to/Tacoma-08-Apr-2022/Tacoma/tacoma.scene")
dirsig.add_scene(tacoma_scene, offset=[0, 0, 0])
```

One loose end this shortcut introduces: `write_files()` also calls `s._check_coverage(...)`
per scene, which runs against `self._material` — a `MaterialsDatabase` populated only with
the default dummy material, since the bare `SCENE` never had Tacoma's real
`materials/tacoma.mat` loaded into it. That check will most likely raise on a real spectral
band request. It is non-fatal — `write_files()` wraps the call in `try/except Exception as
e: logger.warning(e)` — but its pass/fail result carries no information about whether
Tacoma's actual materials cover the requested bands. Any claim about that scene's spectral
coverage needs to be checked against `tacoma.mat` directly, not inferred from dirfm's
coverage check.

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

*Update 2026-09-23 — resolved: intrinsic.* Adding a small object 4 km from the anchor left
the square unchanged, so the cutoff does not come from the scene's bounding volume. The truth
image puts every hit within ±1000 m of the anchor, to well under a pixel. `scene2hdf` itself
warns *"Found infinite plane geometry, emulating with a limited, facetized representation"*.
That warning is the only place the limit appears, and it does not give the size. So the ODB
page's "infinite" is a documentation defect. The Phase 2 notebook's Stage 2 (§2.5) contains
the probe render, and it uses a 3 × 3 tiling on a 2 km pitch with every anchor on a
2 × `WIDTH` grid, so the checkerboard phase agrees across the overlapping seams.

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

## 2026-09-23 — Phase 3 (Tacoma scene reference) findings

**The `_fname` mechanism exactly as written above writes about 650 MB into the scene's
directory.** `scene2hdf` writes `<scene>.hdf` and `asset_report.txt` next to the `.scene`
file it is given, and it has no output-path option (`scene2hdf --help`). Setting
`_fname = .../Tacoma/tacoma.scene` therefore compiles `tacoma.scene.hdf` (653 MB) *into the
DIRSIG install*. **A symlink does not avoid this.** With `_fname` pointing at a symlink to
`tacoma.scene`, `scene2hdf` resolves the link and writes beside the real file (confirmed on
the Phase 2 scene in a scratch directory), while `dirsig5` looks beside the link and fails
with `Path "…/tacoma.scene.hdf" does not exist`. Confirmed the hard way: the first Tacoma
test run used the symlink approach and wrote both files into
`Tacoma-08-Apr-2022/Tacoma/`. They were new files, not modifications (confirmed against a
pre-run snapshot of the tree). They were deleted immediately, the directory mtime was
restored, and a fresh snapshot matched the original on path, size, mtime and mode. Only the
directory's ctime changed, and that cannot be restored. Nothing else under the install
changed. **What works:** a real copy of only the 3.4 KB `tacoma.scene` XML in
`outputs/tacoma_scene_input/tacoma_ref/`, beside symlinks `geometry/`, `materials/` and
`maps/` pointing at the originals, with `_fname` set to that copy. The scene resolves every
asset through `$SCENE_DIR/…`, so the real assets are read in place and `scene2hdf`'s output
lands under `outputs/` (confirmed: asset directories untouched). This bends prompt.md's "never
copied into protoDIRSIG" for one small XML file. The user approved that trade over writing
into the install. `tutorial_tacoma_scene.ipynb` fingerprints the whole Tacoma tree around every
render and asserts it is unchanged. **General rule:** any scene referenced via `_fname` from a
read-only location needs this treatment, because referencing a scene by path always writes
next to it.

**The coverage check on a referenced scene passes vacuously; it does not raise.** The entry
above predicted `_check_coverage()` "will most likely raise" on the bare `SCENE`. It does not.
The bare `SCENE`'s only material is dirfm's placeholder `Dummy`, which has no surface
properties, so `Material._check_coverage` iterates over nothing and returns. Called directly,
it returns `None` for 0.4–0.7 µm *and* for 5–50 µm. During `write_files()` the only log line
is `Testing scene coverage for band [0.4-0.7] …`, with no warning. So the check is not merely
uninformative: it looks like a pass. Coverage for Tacoma was checked by parsing `tacoma.mat`
by hand. Every referenced `.ems`/`.fit` file covers 0.40–0.78 µm, the inline Ward materials
have no wavelength dependence, and so the visible band is covered.

**Tacoma's `features="vis,nir"` is not backed by every material.** `lt_blue_panel.ems` ends
at 0.78 µm, and `orange_panel.ems` / `dark_orange_panel.ems` at 0.80 µm. The ground texture
maps are defined only for 0.4–0.7 µm. Not exercised here (RGB only), but a NIR channel on
this scene would depend on DIRSIG's behaviour past the end of a curve.

**DIRSIG has a native SGP4 location engine; dirfm doesn't wrap it.** The Tacoma bundle's
own orbital shot (`shots/oct17/skysat1-oct17.motion`) uses
`<locationengine type="sgp4"><data source="internal"><tle1>…</tle1><tle2>…</tle2>`, meaning
DIRSIG propagates the TLE itself. This refines the "No SGP4/TLE propagator" gap above: the
gap is in dirfm, not DIRSIG. It is also an independent cross-check (run in Phase 4a, below): render
the same pass once from our skyfield ITRS waypoints and once from DIRSIG's SGP4 engine, and
compare the truth images. The same file uses a LookAt with a *fixed `frame="scene"` point*
(target stare), which is the pointing Phase 3 adopted. A nadir LookAt would have put the
boresight about 62 km from Tacoma's 914 m scene on the chosen pass.

**Tacoma: a surface at z ≈ −0.1 m outside the ground mesh.** *(Resolved in Phase 4c below: it is a declared `BOX` of water in `tacoma.odb`; the "no obvious candidate" statement here was a search error.)* The scene's ground is a
single 914.4 m square mesh (`ground_large.obj` at (−145.3, 183.1) m). Rays outside it do not
miss: the truth image is 0 % `NaN`, and those pixels hit a surface at z = −0.100 … −0.038 m.
None of the scene's three geometry lists (`terrain.odb`, `tacoma.odb`, `targets.glist`)
declares an obvious candidate (no `GROUND_PLANE`, no larger mesh), and a search of the ODB,
GLIST and `scene2hdf` docs found no documented implicit backdrop. Not investigated further.
Side note: `terrain.odb` and `tacoma.odb` both instance `ground_large.obj` at the same place,
so the ground is doubled and coplanar. It is harmless (same material), but untidy.

**Hard shadows render as exactly zero radiance under `SimpleRadiativeTransfer`.** In the Tacoma
render, 0.77 % of pixels are exactly 0 in all three bands, and all of them are ground hits
(z ≈ 0) directly beside buildings, containers and cranes: hard shadows, not water. This is
consistent with no diffuse skylight reaching shadowed ground under this sky model. Not
verified against the DIRSIG docs. Relevant to any use of the basics notebook's minimal
atmosphere for imagery where shadow detail matters.

**Result.** With the pointing above, the frame's centre pixels hit Tacoma 0.28 m (0.14 px)
from the aimed-at ground centre, according to the truth image.

## 2026-09-23 — Phase 4a: skyfield pipeline vs. DIRSIG's native SGP4 engine

**Result: the two agree to 5 cm apart from one term. DIRSIG's native engine does not apply
UT1−UTC, and that single term accounts for the whole 33 m difference.**

*Method* (`scripts/crosscheck_sgp4.py`, output `outputs/sgp4_check/result.json`). The
Tacoma notebook's pass was rendered twice (WorldView-2, `PASS_EPOCH` 2026-09-28T19:13:53Z,
one frame at t = 60 s). The two runs were identical except for the location engine: (A)
`protodirsig.orbit`'s skyfield ITRS waypoints, exactly as the notebook uses them; (B) the same
two TLE lines in a hand-written `<locationengine type="sgp4">`, via a 10-line subclass of
dirfm's `LocationEngine`. Everything else was the same: scene reference (via
`protodirsig.scene_ref`), sensor, atmosphere, `TASKS`, and the stare LookAt. The sensor adds
the Geolocation truth collector to Intersection. Comparing boresight intercepts alone would
prove nothing, because a stare LookAt puts the frame centre on the aim point whatever the
platform position (the centre intercepts of A and B do agree to 0.1 mm). So each run's
**platform ECEF position was recovered from its truth image**: every one of the 262,144
pixels gives an ECEF hit point Pᵢ and a sensor-to-hit distance dᵢ, and S solves
|S − Pᵢ| = dᵢ by Gauss–Newton least squares. *Calibration*: on run A, whose true position is
known because t = 60 s is a waypoint row, the recovered S matches to **0.05 mm** (fit RMS
0.02 mm). So the truth `Distance` is the exact geometric range from the platform position at
the capture time. No light-time offset (2.6 ms ≈ 19 m along-track) is applied to the platform
position.

*Numbers.* Native − skyfield = **33.17 m**: along-track −8.62 m, cross-track +32.03 m,
radial 0.00 m. ECEF Δz = −0.035 m. The difference is a rotation about the Earth's polar axis
by **1.4110″** (6.841 × 10⁻⁶ rad), with a 5.2 cm residual after removing that rotation. At
Earth's rotation rate that is **0.09381 s**, and skyfield's UT1−UTC at the frame is
**0.09385 s** (the IERS table bundled with skyfield 1.54, which covers this date through its
predictions), a match to 0.05 %. The sign is right for DIRSIG taking UT1 = UTC: an Earth angle
too small by ω·DUT1 leaves the satellite rotated east in ECEF. The equation of the equinoxes
(GAST − GMST = 7.57″) is ruled out, since it is 5× too large. With the frame rotation
removed, SGP4 itself agrees to centimetres: the propagator version (DIRSIG documents Vallado
"SGP4 Version 2008-11-03"; skyfield uses `sgp4` 2.26), the gravity constants and the TLE-epoch
handling are all consistent. The pixel-wise truth shows the difference only through
perspective: median XY shift 2 mm, 99th percentile 0.13 m, max 0.44 m, and a median distance
change of −2.55 m (the along-LOS part of the 33 m). The radiance images differ by up to
3.6 × 10⁻⁴, as expected for two unseeded runs (Phase 1, Stage 8).

*What this establishes.* (1) **The skyfield pipeline is independently confirmed**: an
independent SGP4 propagation of the same TLE lands within 5 cm of it once the one convention
difference is accounted for. (2) **The difference is DIRSIG's, not ours.** Mapping TEME to
Earth-fixed uses Earth rotation, which runs on UT1, not UTC. skyfield applies the IERS DUT1;
DIRSIG's native `sgp4` engine evidently does not. That is inferred from the fit (0.05 %
match, cm residual); DIRSIG's docs don't say either way. (3) **Size of the effect for anyone
using the native engine:** position error ≈ r·ω·|DUT1|. For LEO (r ≈ 7,150 km) that is
about 0.52 m per millisecond of DUT1: 33 m today, and up to about 470 m at the ±0.9 s bound
IERS allows. Earth-fixed errors of that size move the ground track by nearly the same amount
(the rotation is about the pole, so ground points under the satellite shift by ≈ ω·DUT1·R⊕,
about 29 m today). (4) **Practical rule:** keep the skyfield waypoint path for anything where
tens of metres matter. The native engine is fine where tens of metres don't. Because a stare
LookAt re-points at the target, the target stays centred either way; what changes is the
platform position, the view geometry and the range.

## 2026-09-23 — Phase 4b: the coverage check for referenced scenes is now a tested helper

`src/protodirsig/scene_coverage.py` replaces the Phase 3 hand-check. `scene_coverage(scene)`
follows the `.scene`'s `<matfilename>` and `<emsdirectory>` to the real material database and
reports each material's wavelength span. Inline `WardBRDF` is wavelength-independent.
`ClassicEmissivity` and `ShellTarget` get the intersection of their `.ems`/`.fit` spans, and a
multi-curve `.ems` file contributes its narrowest curve. `covers(a, b)` and `gaps(a, b)` then
answer the question dirfm's `_check_coverage()` only *appears* to answer for a `_fname` scene.
It is deliberately **fail-closed**: an unrecognised surface property or file key, or a
referenced file that doesn't exist, marks the material unknown, and `covers()` is then False
for every band. So it cannot reproduce dirfm's vacuous pass. `tests/test_scene_coverage.py`
pins Tacoma: 42 materials, 18 wavelength-independent, 0 unknown, span exactly
(0.40, 0.78) µm, covers 0.4–0.7, and does not cover 0.4–0.9. The only NIR gaps are materials
using `lt_blue_panel`, `orange_panel` or `dark_orange_panel`, and 5–50 µm is rejected (the band
dirfm waved through). The test also pins the fail-closed behaviour on synthetic `.mat` files.
`tutorial_tacoma_scene.ipynb` Stage 0 now calls the helper and asserts `covers(0.4, 0.7)`
instead of parsing `tacoma.mat` inline. Scope limit, by design: it knows only the three
property kinds this project has met. A new scene will report its unknown materials by name
rather than pass.

## 2026-09-23 — Phase 4c: the z ≈ −0.1 m off-mesh surface is declared geometry (resolved)

**It is not a DIRSIG default. `tacoma.odb` (line 316) declares a `BOX` primitive,
`LOWER_EXTENT = -10000, -10000, -10`, `UPPER_EXTENT = 10000, 10000, -0.1`,
`MATERIAL_IDS = 3005`: a 20 km × 20 km water slab whose top face sits 0.1 m below the 914 m
ground mesh.** Material 3005 is "Water" (`muddy_water.ems`, `SPECULAR_FRACTION = 0`), the
same material the ground mesh's material map assigns to its water pixels
(`materials.png` dc 0 → 3005). So the backdrop is the scene authors' open water around the
port, not an untraced surface. **The Phase 3 statement that no geometry list declared a
candidate was wrong**: that search grepped for `GROUND_PLANE`, `OBJ_FILENAME` and "water",
never for `BOX`.

*How it was pinned down, in the prompt's order, with what each step ruled out.*
(1) **Geometry of the hits**, from the Phase 4a render's Geolocation + Intersection truth
(70,219 off-mesh pixels, 274–982 m from the origin). A fit of scene z = a + b·d² gives
a = −0.0996 m and b = −3.8 × 10⁻¹⁰ m⁻¹ (3 mm RMS). The surface is **flat** in scene ENU. An
ellipsoid-following default Earth would need b = −1/(2R) = −7.8 × 10⁻⁸ m⁻¹, 200× larger, so
that is ruled out. The same data show DIRSIG's scene-ENU and ECEF truth agree with our
tangent-plane conversion to < 0.1 mm. The −0.038 m end of the printed z range is edge pixels
mixed with the mesh. (2) **Origin altitudes:** Tacoma's only declared altitude is 0.0 m
(the scene origin), so −0.1 is not a georeferencing value. (3) **Docs:** the ODB, GLIST and
`scene2hdf` pages document no implicit backdrop. The only "default" surface is the
*"default earth core"* in the DIRSIG5 release notes, for rays that miss all user scenes.
Here no ray misses (0 % `NaN`), because the 20 km box catches them, so that path is never
exercised. (4) **Scene variants:** `state1.scene` and `state2.scene` don't include
`tacoma.odb`, but their own `state1.odb` / `state2.odb` declare the identical `BOX`. The
surface is present in all three variants because each variant's geometry declares it, not
because of a binary default. The `asset_report.txt` lists files only and is uninformative
here. Searching the ODBs for `BOX` found it directly.

*The caveat this leaves.* Same material, different radiance: in the Phase 3 render, box-water
pixels have median RGB (2.73, 3.66, 2.55) × 10⁻⁴, while in-mesh water pixels (51,952,
identified through `materials.png` at the truth texture coordinates, using the scene's
`flipy="true"`) have (1.68, 2.49, 1.37) × 10⁻⁴. **The box's water is about 1.6× brighter.**
The likely cause is the `.scene`'s `<texturemap>` for matid 3005 (`3in_texture.png`,
0.4–0.7 µm). It modulates *any* surface with material 3005, and the BOX primitive supplies its
own UV parameterisation (truth U, V confined to 0.43–0.57 over the frame) instead of the
mesh's image-wide UVs, so it samples a different part of the texture. This is **not
verified**. The "untraced backdrop" risk is therefore closed, but a **radiometric seam at the
mesh edge** remains. Anything radiometric across that edge (water statistics, contrast
against the port) should use only in-mesh pixels, or the discrepancy should be characterised
first.

## 2026-10-06 — Phase 5: the received AUROR_ref run tree, re-run from a static pose

`notebooks/dev/auror_scene_buildup.ipynb` (the discovery log; the tutorial is
`notebooks/dirfm_tutorials/tutorial_auror_scene.ipynb`) re-runs `AUROR_ref/` (received, gitignored; built on
Windows with DIRSIG/scene2hdf `2025.51 (822ab24)`) on this install (`2026.38 (a020954)`) and
compares it with the shipped `jsims/AurorNIROutput.img` + `truth1.img`. `AUROR_ref/` is
fingerprinted (68 paths) around every render and is unchanged. **Note:** the phase prompt said
this file already assessed AUROR_ref's contents. It did not (no prior mention of AUROR or
Tahoe), so the assessment below is new, read from the tree's files in the discovery log's
Stage 0.

**`NewAtmospherePlugin` is not usable as dirfm ships it: a gap, not "fully wrapped".**
The interface is as expected (`NewAtmospherePlugin(fname)` takes an existing database path;
`get_plugin_inputs()` → `info`/`backend`/`hdf_filename`). But every setter on it and on
`ModtranTapeBackend` raises `AttributeError`, because `_FrozenAttrs` forbids new attributes
after `__init__`. `ModtranTapeBackend.__init__` never creates `_profile`, `_atmo_model`,
`_multiple_scattering` or `_boudary_aerosol_model`, and `NewAtmospherePlugin.__init__` never
creates `_info` or `_backend`. So `set_profile`, `set_atmospheric_model`,
`set_boundary_aerosol_model`, `set_multiple_scattering`, `set_info`, `set_backend` and
`get_plugin_inputs()` all fail. Separately, `set_multiple_scattering` asserts the model is in
`["None", "Isacc", "Distort"]`. `"Isacc"` is a typo: DIRSIG's `docs/atm_backends.html` and the
AUROR jsim both spell it `"Isaac"`, which is rejected (and `"Distort"` is likewise a typo for
DIRSIG's `"Disort"`). The workaround lives in
protoDIRSIG, with dirfm untouched. Two subclasses pre-declare those attributes in `__init__`,
before the freeze, after which dirfm's own setters work; `"Isaac"` is assigned to
`_multiple_scattering` in exactly the shape the setter would store. `ModtranTapeBackend` also
has no way to emit `extract_profile` (DIRSIG default false, so omitting it is equivalent). Per
`docs/newatm_plugin.html`, the backend block is `atm_builder`'s recipe for *building* the
database; with an existing HDF it is not what the render uses. Upstream fix (for whoever
maintains dirfm): initialise those six attributes to `None` in the two `__init__`s, and correct
`"Isacc"`/`"Distort"`. *Factored out (later the same day):* `src/protodirsig/atmosphere_patches.py`
(`PatchedModtranTapeBackend`, whose `set_multiple_scattering` validates against DIRSIG's
`None`/`Isaac`/`Disort`, and `PatchedNewAtmospherePlugin`), pinned by
`tests/test_atmosphere_patches.py`, which also asserts the unpatched setter still fails, so it
flags an upstream fix.

**Other dirfm gaps met here.** `SPICEPlugin` requires three kernel paths, so the jsim's
`SpiceEphemeris` with `inputs: {}` needs a two-line `EphemerisPlugin` subclass.
`PlatformSensorPlugin.prepare()` always regenerates platform/motion/tasks XML, so there is no
way to reference existing files. A bare `Plugin` subclass for `BasicPlatform` (the plan's fix)
**fails** in `DIRSIG.write_files()` with `UnboundLocalError: platform_plugin_idx`:
`write_files()` locates the platform by `isinstance(p, PlatformSensorPlugin)` and assumes one
exists. The working shape is a `PlatformSensorPlugin` subclass with no attachments, a no-op
`prepare()`, and its own `get_plugin_inputs()`. With no attachments, dirfm's coverage loop does
not run. *Factored out:* `src/protodirsig/platform_ref.py` (`PlatformFilesPlugin`,
`SpiceEphemerisPlugin`), plus `scene_ref.copy_input` for byte-identical input copies.

**`scene_coverage.py` did not see `geometrylistinclude`-contributed materials: extended.**
It read only `<matfilename>`, so on `tahoe.scene` it returned `covers(0.41, 2.0) == True` for
10 materials without ever seeing `Gidder_mat`, the vehicle's material, which lives in the
bundle `geometry/bundles/hypersonic/hypersonic.mat` and is reached via `lists/hypersonic.glist`.
That is a fail-open result from a helper built to fail closed. **Tacoma had the same blind
spot.** `targets.glist` brings in `tribar` and `helicopter` bundles (6 local materials). They
are all inline Ward (wavelength-independent), so Phase 4b's Tacoma verdicts stand, but by luck.
The helper now follows enabled `.glist` includes recursively through `<basegeometry><glist>`
to every `<localmaterials>`, honouring `search_paths="local"`. It also understands
`SimpleReflectance`/`TXT_FILENAME` and resolves `MATERIAL_MAP` LUT proxies (Tacoma's
`TriBarTarget`) to their targets, and it skips disabled texture maps. Missing includes, bundle
glists or `.mat` files become unknown materials, so the helper stays fail-closed.
`tests/test_scene_coverage.py` pins Tacoma (42 scene + 6 bundle materials, same spans and
verdicts), AUROR (`Gidder_mat` from `hypersonic.mat`, 0.40–3.0 µm, covers 0.41–2.0) and three
synthetic fail-closed cases. `pytest` is not installed in the `protodirsig` env (it is a `dev`
extra), so the tests were run by calling the test functions directly; all 7 pass.

**What the tree is (read from its files).** One surviving jsim, wiring
`AurorNIRDetector.platform` (500 × 500, 10 µm pitch, f = 306 mm, one Gaussian channel at
0.85 µm, σ 0.0637 µm, in a 0.41–2.0 µm bandpass; output `AurorNIROutput`; truth `Collection 1`
→ `truth1` with `GeoLocation`; the other 10 truth collections are empty). Five of its six paths
are absolute Windows paths; `hdf_filename` is relative (`"AurorNewAtmosphere"`, beside the
jsim), not a Windows path as the plan said. `tahoe.scene` has
`features="vis,nir,swir,sources,exoatm"`, both maps disabled, terrain all material 1 (`gray.ems`),
plus a ~2 m bundle vehicle (`Gidder_mat`: reflectance 0, `DataDriven` 1500 K) on a `straight`
dynamic instance starting at scene (−400, 400, 50 000). Motion is **one static pose**: (−400,
400, 550 000) in `sceneenu`, Euler (0, 0, π), i.e. 500 km directly above the vehicle. The tasks
reference `2009-07-27T11:29:32-08:00` is 17 years stale and uses PST for a July date.
**The atmosphere database was built for a different site**: its HDF origin is 43.12° N,
−78.45° E, 250 m (western NY), and its stored sun (zenith 36.24°, azimuth 238.56°) matches that
site at the task time (skyfield: 36.27°/238.63°), not Tahoe (21.50°/155.52°). The original run
used the same file, so the comparison is like for like, but the absolute radiometry is not Tahoe's.

**Version-compile outcome.** The scene was recompiled fresh by `scene2hdf 2026.38 (a020954)`
into `outputs/auror_scene_input/auror_ref/`. The shipped `tahoe.scene.hdf` was not used. Both
are 25.67 MB. Byte comparison is meaningless: two compiles by *this* install already hash
differently. The generated jsim matches the original except for the six path rewrites (each to
a byte-identical copy), `extract_profile` (omitted; default false), `multiple_scattering.parameters:
{}` (added; DIRSIG's own example has it) and `offset: "0,0,0"` (dirfm always writes one).
`dirsig5` warns that materials 11–19 are unused (consistent with the disabled map), that the
scene is >10 km across, and that every curve starting at 0.40 µm is "insufficient" for its
internal 0.35–2.55 µm grid (outside the channel's response).

**Comparison result: 2026.38 vs 2025.51.**
Headers identical except the generator string; corner geo-points within 2.2 m.
Geometry: both frame centres hit within 0.5 m of scene (−400, 400), directly under the sensor.
Per-pixel ECEF hits differ from the reference by 1.3 m median (p99 3.4 m, ≈ 0.07 px), with an
ENU mean of ~1 mm, so this is scatter, not a shift. An unseeded **same-version repeat** render
(`outputs/auror_scene_repeat_output/`) is the baseline: 91 % of truth pixels are bit-identical to
ours, against 1 % for the reference. So the version change altered where in each pixel the
recorded ray lands; within a version that is reproducible. Radiometry: image means agree to
<0.01 %, median per-pixel ratio 1.0001. Per pixel, ours vs the reference differ by 2.9 % median
(r = 0.86), while the same-version repeat differs by 0.001 % median (p99 0.04 %, r = 0.9999). So
the cross-version scatter is a different Monte Carlo realisation, not run-to-run variation. It
behaves like one: its spread (0.045) is no more than two independent ~4 % noise fields give, its
8-px-smoothed std (0.0016) equals the white-noise expectation, and the smoothed images correlate
at r = 0.9997. **No systematic radiometric or geometric change between 2025.51 and 2026.38 is
detectable.** Side result: two unseeded runs on one install agree to ~4 × 10⁻⁴, the same order
as Phase 4a's 3.6 × 10⁻⁴.

**Unexplained, and identical in both versions: the vehicle is not in the image.**
A 1500 K blackbody (`Gidder_mat`, emissivity 1) is ~207× the
direct-sun ground radiance in the 0.85 µm channel (computed from the atmosphere database's own
irradiance and transmission). With a 0.63 m² top-down silhouette (0.24 % of a 16.3 m pixel), it
should add about +49 % to the 2×2 block at the boresight (which passes through that block's
shared corner). Both renders show a *negative* summed excess there (−3 % ours, −7 % reference),
about 6σ below expectation, and the brightest pixel in either frame is noise at an unrelated
location. Not investigated, because that means altering the received scene. Candidates: the
`straight` dynamic instance's time base placing the vehicle elsewhere at task time 0 (100 m/s
clears the ~8 km field in ~40 s); emission not evaluated for this material in these bands
(`DataDriven` temperature, or `features` listing no thermal band); bundle placement. Since both
versions agree, it is a property of the received configuration. Resolve it before using
AUROR_ref as a detection reference.

## 2026-10-07 — Stage 01: the AUROR_ref job driven from a MANIFOLD run spec

`notebooks/stage_01_auror_from_runspec.ipynb` is a new notebook, started from a copy of
`notebooks/dirfm_tutorials/tutorial_auror_scene.ipynb`, which stays as it was. The new notebook takes its
scene, platform, atmosphere, weather and ephemeris references, and its seed, from
`run_specs/auror_ref.yaml`, a vendored copy of eopticDocs
`projects/MANIFOLD/04-guides/auror_ref_run_spec.yaml`, which is edited there. The values are no
longer written into its cells. `src/protodirsig/run_spec.py` loads and resolves it, and
`tests/test_run_spec.py` pins it. `scene_ref`, `platform_ref` and `atmosphere_patches` are
reused unchanged. Stage notebooks (`stage_NN_<slug>`) are staged implementation toward a
MANIFOLD-aligned generator, numbered separately from the `tutorial_*` dirfm notebooks.

**Scope boundary: `engine.motion` and `engine.tasks` are not used to regenerate anything.**
`AUROR_ref` is a received tree, and its `motion/AurorMotion.ppd` and `tasks/AurorTask.tasks`
are referenced as files. The run spec's `motion`/`tasks` blocks describe what those files
already encode, and they name no file, so the loader finds the tree's single `.ppd` and
`.tasks`. `run_spec.check_received_files` compares the spec against the files instead: static
pose (−400, 400, 550 000), Euler (0, 0, π) xyz radians `sceneenu`; window [0, 0];
`descriptor.collection.epoch` `2009-07-27T19:29:32Z` against the tasks reference
`11:29:32-08:00`; `integration_samples` 10 against the platform's `<samples>`. All agree.
Generating motion and tasks from a run spec in dirfm is a later stage.

**What the run spec does not carry, or carries but cannot be applied here.**
- *`engine.platform.output_prefix: auror_nir_` is not applied.* The received jsim has no
  `output_prefix`, and its outputs are `AurorNIROutput`/`truth1`. `PlatformFilesPlugin` emits
  no prefix, and the instructions said to reuse it unchanged. dirfm's `DIRSIG.set_output_prefix`
  stores `_prefix` but nothing reads it (only `PlatformSensorPlugin.set_output_prefix`, which
  regenerates the platform, emits one). Applying the prefix would rename the outputs, so the
  job would no longer reproduce the tree. The value appears in no file in the tree, so it looks
  like an authoring choice in the YAML, not a description of the tree. Settle it in eopticDocs.
- *The NewAtmosphere backend recipe* (MODTRAN tape: `New Profile`, `MidLatitudeSummer`,
  `RuralVis23Km`, `Isaac`) has no field in the run spec. `descriptor.collection.atmosphere.regime:
  mid_latitude_summer` is a vocabulary term, not this recipe. `run_spec.py` fixes it as the
  received jsim's values (`AUROR_ATMOSPHERE_BACKEND`), as part of the `new_atmosphere` special
  case. It does not affect the render, which reads the existing database (Phase 5).
- *`new_atmosphere` is the only atmosphere plugin accepted*, with a specific `RunSpecError`
  otherwise. `ephemeris` accepts only `spice`; weather accepts only `source: library`.
- *Scene layout.* `scenes/tahoe` (config-repo nested layout) resolves to the tree-root
  `tahoe.scene`, a local workaround for the layout question the guide leaves open (§6).
- *Loading* is plain `yaml.safe_load`. Metadata_v02 §6.15's strict loader (duplicate-key and
  unknown-key rejection, canonical-JSON hashing) belongs to the MANIFOLD registry side, which is
  not built. The `content_hash` placeholders are not checked.

**Seeded render.** `engine.run.seed` (42) goes to `DIRSIG.set_seed`, which passes
`--random_seed` to both `scene2hdf` and `dirsig5` (both accept it). The render is no longer the
unseeded Phase 5 realisation. The geometry and truth assertions in the display cells pass
unchanged. PyYAML (6.0.3, already present transitively) is now declared in `pyproject.toml`
and `environment.yml`. The tests ran under the env's interpreter with pytest from a scratch
`--target` directory, because pytest is still not installed in the env: 20 passed (9 new).

## 2026-10-08 — Stage 02: conformance checks, `Simulation` and `LocalRegistry`

Phases 2–4 of eopticDocs `review/PLAN_2026-10-08_conformance-template-roadmap.md`. Phases 1, 5
and 6 (sensor-spec split, asset repository, sweeps/ChipMaker) are not built.
`src/protodirsig/simulation.py` (`Simulation`, `ConformanceResult`, `RunResult`, `schema_errors`)
and `src/protodirsig/registry.py` (`LocalRegistry`, `SubmissionResult`) are new, pinned by
`tests/test_simulation.py` and `tests/test_registry.py`. Neither imports any orchestration
framework. `run_spec`, `scene_ref`, `platform_ref` and `atmosphere_patches` are reused unchanged.
`notebooks/stage_02_conformance_template.ipynb` is a new notebook copied from stage 01, which
stays as it was. The prompt said `git mv`.

**What the execution-conformance check invokes.** It assembles the same job Stage 01 assembled,
under `<work_dir>/validate/`, and runs it through dirfm's `DIRSIG.run(**options)`. That method is
the only code that builds a `dirsig5` command line, and it already forwards arbitrary options
(`None` becomes `--flag`, a value becomes `--flag=value`). No dirfm change was needed, and nothing
in protoDIRSIG calls `dirsig5` itself. The resulting calls:
`scene2hdf --threads N auror_ref/tahoe.scene --random_seed 42`, then
`dirsig5 <in>/example.jsim --output_folder=<out> --dry_run --log_info_filename=<work>/validate/log_info.json --random_seed 42`.
The real render (`Simulation.run`) drops `--dry_run` and adds
`--run_info_filename=<out>/run_info.json --log_info_filename=<out>/log_info.json`. All three flag
spellings were confirmed against `dirsig5 --help` (2026.38). The bare `--run_info`/`--log_info`
also exist as shortcuts for the default filenames, so the guide's prose and its examples are
both valid. The check fails on a nonzero exit (dirfm raises with DIRSIG's stderr), or on a
`[error]` line in stderr captured from dirfm's `dirfm.dirsig` logger. A dry run takes about 0.7 s,
including `scene2hdf`, and writes no images. Example: a corrupt `AurorNewAtmosphere` exits nonzero
with `Could not open NewAtmosphere HDF`, and no log is written.

**What the JSON log is checked against today (not a schema validation of DIRSIG's format).** The
`--log_info` file must list exactly one capture. Its `task_index` must name one of the spec's
`engine.tasks.windows`, its `relative_time_window` must start inside that window, and its
`run_info.reference_date_time` must equal `descriptor.collection.epoch`.

**How the schema and resolution checks are split.** `resolve_auror_run` raises `RunSpecError` for
bad values and for files it cannot find alike, so wrapping it as the schema check would report a
missing scene as a schema failure. Instead, `simulation.schema_errors` checks values on their own:
required `run-spec/1` and `dirsig-engine/1` members, and the enumerated engine values in
Configuration_v02 A.8.2–A.8.8 plus the `new_atmosphere` extension. `descriptor` is checked for its
six required blocks only. Resolution is `resolve_auror_run` plus `check_received_files`. All
three checks always run. Execution is attempted whenever the references resolve, even if the
schema check failed, so that each verdict is independent evidence. A schema-valid spec this
tree-specific loader can't handle (`four_curve`) fails resolution, with the loader's message.

**Side observations.**
- `run_info.json`'s `plugin_list` records only `NewAtmosphere` and `BasicPlatform`. The jsim's
  `SpiceEphemeris` and `ThermWeather` don't appear, so `run_info` is not a complete record of the
  plugins.
- The roadmap asks what `engine.run.seed` actually seeds. Configuration_v02 A.8.8 and the
  command lines above agree: dirfm's `set_seed` passes `--random_seed` to both `scene2hdf` and
  `dirsig5`, and both binaries list the option. It does reproduce a render. Stage 02's seed-42
  render (`outputs/stage_02_auror/output/`) is byte-identical to Stage 01's (`cmp` on
  `AurorNIROutput.img` and `truth1.img`). The two ran on different days, with the job assembled
  by different code (notebook cells, then `Simulation`).
- Compile-once is not adopted. `DIRSIG.run` always runs `scene2hdf`, so a `submit` followed by
  `run()` compiles the scene twice (into `validate/input/` and `input/`). At about a second each
  that doesn't matter for one job. It will for sweeps (Phase 6).

## 2026-10-08 — Stage 03: `descriptor.sensor` resolved as a `sensor-spec/1` ref

Roadmap Phase 1. `descriptor.sensor` is now a ref, `{ref: {name: sensors/auror-nir.yaml,
content_hash: "sha256:<hash>"}}`, to a `sensor-spec/1` document (GD_DIRSIG_RunSpec_YAML_v01 §7).
Two files were vendored, each with a one-line "edit it in eopticDocs" header:
`run_specs/auror_ref.yaml` (refreshed) and `run_specs/sensors/auror-nir.yaml` (new). Before
vendoring, I checked the extraction: the sensor block is identical to the old inline one once
parsed, and nothing else in `descriptor` or `engine` changed.

What this stage adds:
- `run_spec.load_sensor_spec(run_spec_path, name)` loads the referenced file. It returns the
  whole document, as `load_run_spec` does. It raises `RunSpecError` if the file is missing, does
  not parse, is not `sensor-spec/1`, or has no `sensor` mapping.
- `resolve_auror_run(spec, tree, run_spec_path)` calls it and stores the document as
  `AurorRun.sensor`.
- `simulation.schema_errors` requires `descriptor.sensor.ref.name` to be a string. It does not
  open the file; that is resolution's job.
- The sensor is not consumed by `_assemble` or anywhere else in the DIRSIG job, and no
  `content_hash` is verified (by-name trust, §7).

Tests: 35 passed (7 new). The stage 02 notebook was re-run unmodified, and the stage 01 notebook
was re-run after a one-line change (below).

**Judgment calls (not specified by §7 or the stage prompt):**
- *Resolution root.* The sensor ref resolves against the run spec's own directory
  (`run_specs/`), while every `engine` ref resolves against the tree root (`AUROR_ref/`). §7 says
  the sensor ref has "the same `ref` shape" as `engine.scenes[]`/`engine.platform`, but it does not
  say what a ref name is relative to. In eopticDocs the two roots happen to coincide (`04-guides/`
  holds both the run spec and `sensors/`). Here they are two roots, and Phase 5's asset repository
  will need a single rule.
- *Inline sensor blocks are now rejected*, by both the schema check and resolution. §7 does not
  say whether `run-spec/1` still allows an inline `descriptor.sensor` as an alternative to the
  ref. The prompt asked for ref-only, so an old-style spec fails rather than being accepted.
- *`load_sensor_spec` also requires a `sensor` mapping*, beyond the `spec_version` check the prompt
  named. It does not reject extra top-level keys, although §7 says "nothing else". That matches
  the plain-loader stance everywhere else (no unknown-key rejection; strict loader deferred).
- *`run_spec_path` is a required argument*, not optional with a skip. An optional argument would
  silently leave the sensor unchecked. The prompt named `Simulation.__init__` as "the one call
  site", but `notebooks/stage_01_auror_from_runspec.ipynb` also calls `resolve_auror_run`. Its call
  now passes `RUN_SPEC` (a one-line source change), and it was re-executed to confirm.
- *The schema check sits in the `descriptor` branch* of `schema_errors`, as its own short check,
  not in the `engine`-only refs loop.
- *The eopticDocs sources were uncommitted* in that repo when vendored (the guide, the run spec,
  and an untracked `sensors/`). The vendored copies match its working tree on 2026-10-08, not a
  commit.

## 2026-10-08 — Stage 04: `config_repo/`, the engine-asset library, as the resolution root

Roadmap Phase 5 (eopticDocs `review/PLAN_2026-10-08_conformance-template-roadmap.md`), with the
layout from GD_DIRSIG_RunSpec_YAML_v01 §9 and Configuration_v02 A.8: `scenes/<scene>/<scene>.scene`,
`platforms/<platform>/<platform>.platform`, `weather/<name>.wth`, and the proposed, non-adopted
`atmosphere/<name>`. The refreshed `run_specs/auror_ref.yaml` differs from the Stage 03 copy only
in three `ref.name` values (`scenes/tahoe/tahoe.scene`,
`platforms/AurorNIRDetector/AurorNIRDetector.platform`, `atmosphere/AurorNewAtmosphere`) and in
comments. I checked that with `diff` before going on.

**A copy, not a move. `AUROR_ref/` is untouched**: its fingerprint (75 paths) is unchanged across
the copy step, the tests and both notebook renders. Before copying I confirmed that `tahoe.scene`
has no `<scenebasedirectory>` override and no absolute path (`grep -niE
"scenebasedirectory|/home/|/Users/|C:"`: no matches). Its only asset references are
`$SCENE_DIR/materials/tahoe.mat` and `lists/*.glist` relative includes, so the
`{tahoe.scene, geometry/, materials/}` bundle moved as a unit with no edits.
`scene_ref.reference_scene` needed no change, because it symlinks the asset directories beside
wherever the `.scene` file sits.

The copy is 22 files, 57 MB, with no symlinks. Post-copy comparison, all with empty output:
`diff -r AUROR_ref/geometry config_repo/scenes/tahoe/geometry`,
`diff -r AUROR_ref/materials config_repo/scenes/tahoe/materials`, `diff` on `tahoe.scene`, on the
platform file and on `saw.wth`, and `cmp` on `AurorNewAtmosphere`. **Git storage:** each of the 22
files hashes (`git hash-object`) to a blob already in `.git` (`git cat-file -e`: 22 of 22 exist,
0 new). Committing `config_repo/` adds only tree objects, not another copy of the content.

**`_scene_file`'s flat/nested fallback is removed.** A scene ref now resolves to exactly
`config_repo / ref.name`, with `RunSpecError` naming the attempted path otherwise.
`tests/test_run_spec.py::test_no_flat_scene_fallback` pins this: the old `scenes/tahoe` ref no
longer finds `AUROR_ref/tahoe.scene`, a flat `tahoe.scene` at the library root fails, and the
received tree is not accepted as a library.

**Three resolution roots now.** `resolve_auror_run(spec, tree, run_spec_path, config_repo)`
resolves engine assets in `config_repo`, motion and tasks in `tree`, and the sensor ref beside the
run spec. `Simulation(run_spec_path, tree_root, config_repo, work_dir=None)` stores both trees,
and `_assemble` gives each copied input its path relative to the root it came from.

**Result.** 36 tests passed, one of them new (`test_no_flat_scene_fallback`); the rest were
updated. Both stage notebooks were re-run top to bottom. DIRSIG now reads every asset from
`config_repo/`: its own `[warn]` lines name `config_repo/scenes/tahoe/materials/...`. Both
fingerprints are unchanged across each render (`AUROR_ref` 75 paths, `config_repo` 36). The
stage 01 and stage 02 seed-42 renders are byte-identical to each other (`cmp`), with the same
image statistics as before the migration.

**Not migrated.**
- `run_specs/sensors/auror-nir.yaml`: a descriptor-side ref resolved beside the run spec (§7).
  Whether a sensor library joins the asset repository is left open by the guide.
- `AUROR_ref/motion/*.ppd` and `AUROR_ref/tasks/*.tasks`: per-run artifacts the generator would
  emit from `engine.motion`/`engine.tasks`, not reusable library content (guide §3).
- Also not copied: `AUROR_ref/jsims/AurorSimulation.jsim` (the received job file) and
  `_to_delete/` (gitignored). There is no `maps/`: the scene's map list is disabled, and its
  `.pgm` files exist nowhere in the tree.

**Judgment calls the stage prompt did not anticipate:**
- *A third caller.* `LocalRegistry.submit` also builds a `Simulation`, so it now takes
  `config_repo` as well: `submit(run_spec_path, tree_root, config_repo, work_dir=None)`. The prompt
  listed only the two notebooks.
- *Argument order.* `config_repo` is a required positional argument, added last on
  `resolve_auror_run` and before the optional `work_dir` on `Simulation` and `submit`. Neither
  root defaults to the other. Every caller (tests, notebooks, registry) was updated.
- *More notebook changes.* Besides the `CONFIG_REPO` cell and threading it through, both
  notebooks' summary prints (`rel = lambda p: p.relative_to(AUROR)`) and stage 01's own
  `copy_input` loop would have raised for library paths, so they now use the root each path
  came from. Markdown that described the old flat fallback was updated, including stage 02's
  "Not the finished template" paragraph, which had been stale since Stage 03. The display cells
  are unchanged.
- *The `needs_tree` test guard* now checks for `AUROR_ref/motion` and `tasks`, the only things the
  tree supplies, instead of `AUROR_ref/tahoe.scene`. A matching `needs_config_repo` guard was added,
  and `needs_dirsig` requires both trees. No guard was weakened.
- *The spec-vs-file check reads the library platform file.* `check_received_files` compares
  `integration_samples` against `run.platform`, which is now config_repo's copy, not the received
  one. The two are byte-identical today. If they ever diverge, the check is against the library.
- *A comment in the vendored run spec says `config_repo/scenes/tahoe/` holds `maps/`.* It doesn't
  (see above). That comment is in the eopticDocs source, so it is left as vendored.
- *The job's input layout changed.* The jsim now references
  `platforms/AurorNIRDetector/AurorNIRDetector.platform` inside the work directory, not the flat
  path. This is cosmetic; the content is byte-identical.

## Notebooks (status)

- `notebooks/dirfm_tutorials/tutorial_dirfm_basics.ipynb` — Phase 1, complete. 8 stages, executed end to end.
- `notebooks/dirfm_tutorials/tutorial_orbit_to_ground.ipynb` — Phase 2, in progress. Stages 0–2 complete,
  executed, and committed (TLE/SGP4 trajectory, dropped the original STK-import approach —
  see `prompt.md` for the full rationale; Stage 2 works around the `GROUND_PLANE` extent with
  a tiled ground). Stage 3 (final render + comparison) not yet written.
- `notebooks/dirfm_tutorials/tutorial_auror_scene.ipynb` — Phase 5, complete. Tutorial, 3 stages, executed end
  to end: AUROR_ref's configuration driven through dirfm via `scene_ref`, `scene_coverage`,
  `platform_ref` and `atmosphere_patches`, rendered on this install, image and geolocation
  truth displayed.
- `notebooks/stage_01_auror_from_runspec.ipynb` — Stage 01, complete, started from a copy of
  the tutorial: the same 3-stage AUROR_ref job, now driven from
  `run_specs/auror_ref.yaml` via `run_spec`, seeded, executed end to end. Staged
  implementation, not a tutorial.
- `notebooks/stage_02_conformance_template.ipynb` — Stage 02, complete: the stage 01 job
  submitted through `LocalRegistry` (schema, resolution and execution checks), and rendered
  through `Simulation.run()` only if accepted, with DIRSIG's JSON run/info logs. Executed end to
  end.
- `notebooks/dev/auror_scene_buildup.ipynb` — Phase 5 discovery log (not a tutorial): how the
  dirfm gaps were found and bridged, and the comparison against the shipped 2025.51 render with
  a same-version repeat as the baseline. Kept as executed; it predates the `src/` helpers.
- `notebooks/dirfm_tutorials/tutorial_tacoma_scene.ipynb` — Phase 3, complete. 3 stages, executed end to end:
  Tacoma referenced via `_fname`, WorldView-2 pass over Tacoma, render + truth-centre check.
  Reuses `src/protodirsig/` (`orbit.py` from Phase 2, `sensors.py` from Phase 1, and since
  Phase 4 `scene_ref.py` and `scene_coverage.py`), with `tests/test_orbit.py` and
  `tests/test_scene_coverage.py` pinning them to verified results.

## External reference

`~/dev/agent-docs` (Rendered.ai's agent-context repo) documents a production dirfm
architecture — a node-graph channel (`dirsig_pkg`) wrapping the same `dirfm` primitives used
here, with per-node `exec()` methods, seed-based determinism via `ctx.seed`, and truth-band
annotations. Relevant if protoDIRSIG's batch driver is ever deployed as a Rendered.ai channel
rather than run as a standalone script; not otherwise load-bearing for this project.

`Rendered-ai/dirsig-channel` (https://github.com/Rendered-ai/dirsig-channel) is the public
production codebase corroborating the scene-construction finding above — a second,
independent dirfm consumer that also builds every scene from code rather than loading one.
