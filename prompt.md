## Phase 1 — dirfm fundamentals (complete)

Build an incremental, heavily-commented Jupyter notebook that tutorials the DIRFM library (a Python wrapper that generates DIRSIG input files and drives DIRSIG runs). Target audience: an engineer who knows Python but has never touched DIRSIG or DIRFM.

ENVIRONMENT
- Working directory / project root: /home/kevin-kearney/dev/protoDIRSIG. This is the project — all notebooks, outputs, and any supplementary code go here.
- DIRFM is a read-only library dependency, checked out at /home/kevin-kearney/dev/dirsig-file-maker and installed editable into the protodirsig conda environment (see environment.yml). Never write into this checkout — no notebooks, no output directories, nothing. Only read from it: its source (dirfm/*.py) for API reference, and demos/test_PrimitiveObjects1.py and demos/geometry/*.obj etc. as reference material/assets to read, not to modify.
- DIRSIG binaries: /home/kevin-kearney/DIRSIG/dirsig-2026.38.0.a020954-Linux-x86_64/bin (must contain scene2hdf and dirsig5 on PATH for DIRSIG.run() to work — set this via os.environ["PATH"] in the first notebook cell, don't assume the kernel's shell already has it; don't hardcode this path if it can instead be read from a DIRSIG_HOME environment variable with a documented fallback).
- Write the notebook to notebooks/tutorial_dirfm_basics.ipynb inside protoDIRSIG. Use outputs/tutorial_<n>_input and outputs/tutorial_<n>_output (relative to the protoDIRSIG project root) as the in_root/out_root DIRSIG(...) directories for each stage. These are already gitignored.
- Reference /home/kevin-kearney/dev/dirsig-file-maker/demos/test_PrimitiveObjects1.py as the canonical minimal working example — read it before writing anything, and don't invent API surface not present in the dirfm source. If a needed class/method isn't obvious from the demos, grep the dirfm package (materials.py, object_database.py, platform_sensor.py, atmosphere.py, platform_motion.py, scene.py, dirsig.py) rather than guessing.

STRUCTURE — one stage per section, each section = markdown cell(s) explaining the concept and why it's needed, then a code cell that runs and renders/inspects output before moving to the next stage. Do not front-load explanation of features not yet used. Each stage's code cell should execute successfully (run scene2hdf + dirsig5) before the next stage is written — verify by actually executing the notebook top to bottom, not by inspection alone.

Stage 0 — Orientation: what DIRSIG is, what DIRFM automates (the file-generation problem DIRFM solves — no manual XML/JSON), the object model at a glance (SCENE holds materials+geometry, DIRSIG holds scenes+plugins+mediums, plugins are the platform/atmosphere, everything gets compiled by write_files()/run() into a .jsim + .scene + supporting files, then scene2hdf and dirsig5 are shelled out to). Set PATH, confirm shutil.which("scene2hdf") and shutil.which("dirsig5") both resolve.

Stage 1 — Absolute minimum render: one Material (simple Lambertian via a WardBrdfSurfaceProperty + GenericRadiationSolver, following the pattern in test_PrimitiveObjects1.py's create_materials), one ObjectDatabase primitive (a single GroundPlane or Sphere), one SCENE with a GeodeticFrame origin and set_properties("vis"), the minimal PlatformSensorPlugin tree required to get an image out (StaticMount → GenericInstrument with FocalLengthInstrumentProperty → FocalPlane with BasicCaptureMethod/SpectralResponse/one FunctionalChannel → DetectorArray with IndependentDetectorClock), a PlatformPosition motion with one fixed entry, a TASKS with one start/stop pair, and a minimal BasicAtmospherePlugin with SimpleRadiativeTransfer. Assemble on a DIRSIG(in_root, out_root), add_scene/add_plugin, call .run(), open the resulting .img.hdr with the `spectral` package and display it inline (matplotlib imshow), explaining each object's role in a markdown cell directly above the code that creates it.

Stage 2 — More geometry and materials: add a second and third material with different reflectances, add multiple ObjectDatabase primitives (Sphere, Box, Cylinder, Disk) to the same scene, explain how material objects are passed directly to primitives rather than referenced by ID string.

Stage 3 — Sensor realism: widen the spectral band, add a second FunctionalChannel (multi-band capture), increase DetectorArray element count, explain FocalPlane/CaptureMethod/DetectorArray relationships and how they map to the rendered image's channel count.

Stage 4 — Platform motion and timing: switch from a single fixed PlatformPosition entry to a short multi-entry trajectory (or introduce FlexMotion with a StraightLocationEngine/LookAtOrientationEngine if that fits more naturally), and a TASKS window that spans that trajectory, explaining relative vs. absolute datetime handling.

Stage 5 — Atmosphere fidelity: swap SimpleRadiativeTransfer for UniformRadiativeTransfer or ClassicRadiativeTransfer, or introduce a weather file path, explaining what changes physically in the render.

Stage 6 — Mesh-based geometry via GLIST: replace or augment the primitives with a Wavefront (.obj) instance read from the dirfm checkout's demos/geometry (read-only reference asset), explaining GLIST vs ObjectDatabase (instancing vs. procedural primitives) and StaticInstance placement/orientation.

Stage 7 — Wrap-up: multi-scene composition with add_scene offsets, or Bundle usage for reusable assets — pick whichever is more illustrative — and a closing markdown cell summarizing the full object graph built across the notebook (a short ASCII or prose diagram of DIRSIG → scenes/plugins/mediums → their sub-objects).

Stage 8 — Determinism and render-quality knobs (Phase 1 completion): DIRSIG.run() forwards arbitrary keyword arguments as `--key=value` flags to `dirsig5` (see `run()` in `dirsig.py`), and `DIRSIG.set_seed(seed)` adds `--random_seed` to both the `scene2hdf` and `dirsig5` invocations. Demonstrate both, reusing Stage 1's scene/sensor/atmosphere rather than building new ones.

First, determinism: call `set_seed()` with a fixed integer, run the identical configuration twice into two separate output directories, and compare the two resulting radiance images programmatically (e.g. `numpy.allclose` on the ENVI arrays, or a difference image). State plainly, in a markdown cell, whether the comparison shows bitwise-identical or only statistically-similar output — don't assert reproducibility beyond what the comparison actually shows. This is the reproducibility gap named in the MANIFOLD DIRSIG-automation charter (seed capture alone doesn't establish which reproducibility standard is met); this stage is where that gets checked empirically instead of assumed.

Second, render-quality knobs: run the same configuration at two quality settings via `run(convergence=..., max_nodes=...)` — a fast/noisy "preview" setting (e.g. `convergence="3,3,0", max_nodes="1"`) and a slower/cleaner "production" setting (e.g. `convergence="20,100,1e-6", max_nodes="4"`) — display both images side by side and report wall-clock time for each. Explain what convergence's three numbers control; consult the DIRSIG5 reference documentation at https://dirsig.cis.rit.edu/docs/new/ (the Feature Manuals / Usage Guides sections cover the `dirsig5` CLI and its convergence controls) for the authoritative meaning rather than guessing from `dirsig5 --help` alone if that's ambiguous.

Close Stage 8 with a markdown cell stating, in one paragraph, what this establishes for provenance going forward: that a recorded seed plus convergence/max_nodes settings are the minimum fields needed to reproduce a run, and — based on what was actually observed in the determinism comparison above, not asserted in advance — whether that reproduction is bitwise or statistical.

CONSTRAINTS
- Never write, modify, or delete anything under /home/kevin-kearney/dev/dirsig-file-maker. It is read-only reference material and an editable-installed dependency, not part of this project.
- Markdown cells should be dense with the "why," not just restate the code — explain what each DIRFM class corresponds to in DIRSIG's file format (e.g., "this becomes the <matfilename> element in the .scene XML") where it clarifies the mapping.
- Every code cell must actually run in this environment before you move to the next stage — don't write stages 2–7 speculatively without executing stage 1's output first.
- Keep each stage additive: reuse/extend the previous stage's objects rather than rewriting from scratch, so the diff between stages is visible. Stage 8 reuses Stage 1's objects specifically (not Stage 7's composite), since it's isolating seed/convergence behavior, not building on the geometry progression.
- After the notebook runs end to end, tell me the git status of the protoDIRSIG repo and give me the actual `git add`/`git commit` commands to save it — don't just describe the action, and don't ask me to run intermediate commits per stage since this is prototype/tutorial work.


---

## Phase 2 — orbit-to-ground reference demo (StkImport1)

Build a notebook, run via dirfm, that reconstructs the orbit-to-ground portion of DIRSIG's bundled StkImport1 demo: a real LEO satellite (WorldView-2) trajectory, sourced from STK-exported ephemeris/attitude, driving a sensor that images toward Earth.

CONTEXT
StkImport1 is DIRSIG's only bundled demo of this shape (satellite-to-ground; Ssa1/Ssa2/Ssa3 are satellite-to-satellite, GeoLocation1 isn't orbital). It ships at
/home/kevin-kearney/DIRSIG/dirsig-2026.38.0.a020954-Linux-x86_64/demos/zips/StkImport1.zip
— unzip it into a scratch location to read (never write into the DIRSIG install directory itself). Read StkImport1/README.txt in full before writing anything; it documents the STK import mechanism and the scene-less EarthGrid setup this demo actually uses.

CAPABILITY CHECK — DO THIS FIRST, DON'T ASSUME EITHER ANSWER
1. Does dirfm expose DIRSIG's EarthGrid plugin? Grep the dirfm package (atmosphere.py, object_database.py, glist.py, scene.py, and anywhere else plausible) for "EarthGrid" or "grid". Report what you find before proceeding.
2. Does dirfm's FlexMotion wrap STK .e/.a ingestion directly, or only generic waypoint/quaternion entries? Check flexible_motion.py's WaypointsLocationEngine and the orientation engines for anything STK-specific (an import path, a file-format argument) versus plain numeric (time, position) / (time, quaternion) tuples.

Do not guess at either answer or invent API surface to paper over a gap. If dirfm doesn't wrap STK import, write a small, explicit ephemeris parser (a `.e` file is STK's plain-text ephemeris report format — read a few lines to confirm the structure, don't assume a schema) that extracts (time, ECEF or ECI position) samples from StkImport1/WORLDVIEW-2_35946.e and (time, quaternion or Euler) from StkImport1/WORLDVIEW-2_35946.a, then feeds those samples into dirfm's WaypointsLocationEngine / the matching orientation engine as plain numeric entries. Note explicitly in a markdown cell whether the source ephemeris is ECI or ECEF and, if ECI, that Earth rotation must be accounted for before feeding positions into an ECEF-based engine (DIRSIG's own motion model is ECEF-referenced per the DIRS motion/temporal documentation) — get this wrong and the trajectory will be silently incorrect, not just imprecise.

If dirfm has no EarthGrid wrapper (the likely outcome), don't attempt to reproduce the scene-less setup. Substitute a conventional SCENE with an ObjectDatabase GroundPlane (or a real-ish ground material, following the Stage 1/2 pattern from tutorial_dirfm_basics.ipynb) as the imaging target, and say explicitly in a markdown cell that this is a deliberate substitution for a plugin dirfm doesn't expose — not a faithful reproduction of DIRSIG's own EarthGrid-based Earth backdrop. The educational content preserved is the real orbital motion driving a ground-imaging pass; the literal Earth-globe rendering is not in scope for this stage.

ENVIRONMENT
- Working directory / project root: /home/kevin-kearney/dev/protoDIRSIG.
- dirfm is read-only, checked out at /home/kevin-kearney/dev/dirsig-file-maker, installed editable. Never write into it.
- DIRSIG binaries: /home/kevin-kearney/DIRSIG/dirsig-2026.38.0.a020954-Linux-x86_64/bin, PATH set explicitly in the notebook per the existing tutorial_dirfm_basics.ipynb convention (DIRSIG_HOME env var with a documented fallback).
- Write the notebook to notebooks/tutorial_orbit_to_ground.ipynb. Use outputs/orbit_to_ground_input and outputs/orbit_to_ground_output (already covered by the outputs/ gitignore pattern).
- Extract StkImport1.zip to a scratch subdirectory under outputs/ (e.g. outputs/_stkimport1_reference/) for reading its README/.e/.a files — this is reference material read once at the top of the notebook, not a build target; treat it the same as the dirfm demos/ directory (read-only reference, never a place other stages write to).

STRUCTURE
Follow the same convention as tutorial_dirfm_basics.ipynb: markdown cell explaining the concept and why it's needed, then a code cell, each stage additive and actually executed before the next is written.

Stage 0 — Orientation and capability check: the two questions above, answered from the source, before any dirfm objects are built.

Stage 1 — Trajectory reconstruction: parse (or import, if dirfm supports it) the WorldView-2 ephemeris/attitude into a FlexMotion location + orientation engine pair. Plot the parsed trajectory (position vs. time, or ground track if you have lat/lon) before wiring it into a scene, as a sanity check independent of DIRSIG — catching a parsing error here is cheaper than debugging it through a failed render.

Stage 2 — Minimal ground scene and sensor: build the substitute SCENE (or the real EarthGrid setup, if Stage 0 found it's supported) plus a sensor sized for a recognizable single-frame image, reusing the Stage-1-style sensor tree from tutorial_dirfm_basics.ipynb rather than reinventing it. Set TASKS to a window matching the real 2-minute WorldView-2 pass window from the STK data (21 May 2012 16:36 UTC per StkImport1's README), or a stated subset of it.

Stage 3 — Render and compare: run it, display the output, and write a closing markdown cell comparing what was actually reconstructed against the original StkImport1 demo — what's faithful (real orbital dynamics, real pass timing), what's substituted (ground representation), and what that implies for using dirfm on genuinely orbital MANIFOLD scenarios versus the airborne/terrestrial scenarios tutorial_dirfm_basics.ipynb already covers.

CONSTRAINTS
- Never write, modify, or delete anything under /home/kevin-kearney/dev/dirsig-file-maker or the DIRSIG install directory.
- Don't invent dirfm API surface — if something needed isn't in the source, that's a finding to report (per Stage 0), not a gap to silently code around with a guess.
- After the notebook runs end to end, report protoDIRSIG's git status and give the actual git add/git commit commands — don't just describe the action.


---

## Phase 3 — Tacoma scene render from a LEO detector (minimum viable)

Build the simplest notebook that renders the bundled Tacoma demo scene as seen by a sensor
on a real LEO trajectory. This is a minimum-approach notebook, not a progressive tutorial:
fewer stages than Phase 1/2, heavy on markdown explaining *why* each piece is there, thin on
new mechanism — everything needed here was already built and verified in Phase 1 (sensor
tree) and Phase 2 (TLE/SGP4 trajectory, up-vector verification), and should be reused, not
re-derived. The one genuinely new piece is referencing an existing scene instead of building
one from dirfm's geometry classes; that mechanism is already found and written up in
FINDINGS.md ("Referencing a pre-existing scene") — read that section before writing any code.

CONTEXT
The Tacoma demo scene ships with this DIRSIG install at
/home/kevin-kearney/DIRSIG/dirsig-2026.38.0.a020954-Linux-x86_64/Tacoma-08-Apr-2022/Tacoma/
(`tacoma.scene`, `terrain.odb`, `tacoma.odb`, `materials/tacoma.mat`, plus `state1.scene`/
`state2.scene` variants — use the base `tacoma.scene`, not the state variants, unless there's
a reason to prefer one). It declares its own geodetic origin internally (47.27°N, 122.41°W,
0 m altitude — Port of Tacoma, WA) and its own material database; nothing about it needs to
be reconstructed. Treat it exactly like the DIRSIG install and the dirfm checkout: read-only
reference material, never written to or copied into protoDIRSIG.

MECHANISM — the scene reference
dirfm's `SCENE.write()` short-circuits and returns `self._fname` immediately if it's already
set, bypassing all of `SCENE`'s own geometry/material serialization. Use this directly:

```python
tacoma_scene = SCENE("tacoma")
tacoma_scene._fname = Path("/home/kevin-kearney/DIRSIG/dirsig-2026.38.0.a020954-Linux-x86_64/"
                            "Tacoma-08-Apr-2022/Tacoma/tacoma.scene")
dirsig.add_scene(tacoma_scene, offset=[0, 0, 0])
```

State this plainly in a markdown cell as what it is: a private attribute assignment against
an escape hatch dirfm's own `write()` method provides, not a documented public API. Note the
one known side effect: `DIRSIG.write_files()` will also call `_check_coverage()` on this bare
`SCENE`, which only knows about its default dummy material, not Tacoma's real
`materials/tacoma.mat`. That call is non-fatal (wrapped in try/except upstream) but tells you
nothing about whether Tacoma's real materials cover the sensor's requested band — check
`tacoma.mat` by hand (or just proceed with a "vis" band, which Tacoma's own
`<properties features="vis,nir" .../>` declares support for) rather than trust dirfm's check
here.

STRUCTURE — three stages, each additive, each actually executed before the next is written

Stage 0 — Orientation: what's new here (referencing an existing scene) versus what's reused
(sensor tree from Phase 1, TLE/SGP4/up-vector methodology from Phase 2) — a short markdown
cell, not a restatement of either prior notebook. Load the Tacoma scene reference per the
mechanism above and confirm the referenced path exists before proceeding.

Stage 1 — Trajectory over Tacoma: reuse Phase 2's TLE-fetch-and-propagate approach (skyfield,
TEME→ITRS, the same correctness checks already validated there — don't re-derive or
re-justify them, cite FINDINGS.md and move on) but select a pass over Tacoma's coordinates
(47.27°N, 122.41°W) instead of Rochester. Any currently-active LEO imaging-class satellite's
TLE is fine — reuse WorldView-2 for continuity with Phase 2 unless a cleaner pass geometry is
easy to find with another satellite. Compute the up-vector the same verified way (per-pass
angle-to-boresight and roll-vs-velocity-up checks, not copied from Phase 2's numeric result,
which was specific to a different ground track and target). Plot the ground track and confirm
the selected pass actually brings the satellite over Tacoma before wiring anything into
dirfm.

Stage 2 — Assemble, run, render: `add_scene()` the Tacoma reference from Stage 0, reuse the
Phase 1 sensor tree pattern sized for a single recognizable frame, drive it with Stage 1's
motion, set a minimal `BasicAtmospherePlugin`/`SimpleRadiativeTransfer` (per Phase 1's Stage
1 pattern — this notebook isn't the place to explore atmosphere fidelity), and a `TASKS`
window matching the pass. Run it, display the resulting image, and close with a short
markdown cell stating what the image actually shows (does the Tacoma geometry appear where
the boresight-intercept calculation predicts it should — a truth-image center check, the same
kind used to characterize the `GROUND_PLANE` finding in FINDINGS.md) rather than asserting
success without checking.

CONSTRAINTS
- Never write, modify, or delete anything under the DIRSIG install directory, the Tacoma
  scene directory specifically, or the dirfm checkout.
- Don't re-implement or re-verify what Phase 1/2 already built and checked — import or copy
  the relevant helper code (TLE fetch/propagation, up-vector check, sensor tree construction)
  rather than writing parallel versions in this notebook. If the existing code isn't factored
  for reuse, factor out the minimum needed (e.g. a small shared module under a sensible
  location in protoDIRSIG) rather than duplicating it inline — use judgment on how much
  refactor is worth it against how minimal this notebook is supposed to be.
- Write the notebook to notebooks/tutorial_tacoma_scene.ipynb. Use
  outputs/tacoma_scene_input and outputs/tacoma_scene_output as the in_root/out_root.
- If Tacoma's real material coverage turns out not to support the band actually requested,
  that's a finding to report, not something to silently narrow the sensor around without
  saying so.
- After the notebook runs end to end, append a new dated entry to FINDINGS.md if anything
  unexpected turns up (e.g., the coverage check's actual behavior against a real material
  database, or anything about the `_fname` mechanism not already captured there) — don't let
  it live only in this conversation. Report protoDIRSIG's git status and give the actual
  `git add`/`git commit` commands; don't just describe the action.


---

## Phase 4 — close out the three items flagged from Phase 3's findings

Three follow-ups from the Phase 3 review, in priority order. Do them in order; each is
independent of the others and should be its own commit. Read FINDINGS.md's Phase 3 section
in full before starting — don't re-derive context already written there.

### 4a — Cross-check the skyfield trajectory against DIRSIG's own SGP4 engine

Every correctness claim about the TLE/SGP4/frame-conversion pipeline in `orbit.py` so far
rests on checks internal to that pipeline (GMST comparison, Z-invariance, sidereal rate) —
never against an independent propagation of the same TLE. DIRSIG has its own SGP4 location
engine (found in Tacoma's `shots/oct17/skysat1-oct17.motion`:
`<locationengine type="sgp4"><data source="internal"><tle1>…</tle1><tle2>…</tle2>`), which
dirfm does not wrap but which can be driven directly by hand-writing that one `<motion>`
block (or by using dirfm's `JSIM`/raw XML writing where it's more direct than fighting
`FlexMotion`'s Python wrapper to emit XML it wasn't designed to emit — use judgment on
whichever is less code for a single-purpose comparison).

Render the same WorldView-2-over-Tacoma pass from `tutorial_tacoma_scene.ipynb` twice:
once exactly as that notebook already does (skyfield TEME→ITRS waypoints), once driving the
identical geometry (same TLE, same epoch, same pass window) through DIRSIG's native
`sgp4` location engine instead. Keep everything else — scene reference, sensor, atmosphere,
task window — identical between the two runs, so any difference in the resulting images is
attributable to the trajectory source, not to some other varying input.

Compare the two truth images quantitatively (pixel-wise boresight-intercept position, not
just a visual diff) and state the result plainly: either this confirms the skyfield pipeline
independently, in which case say so and cite the specific numbers, or it reveals a
discrepancy, in which case that's the more important finding, and the two candidate causes
to check first are DIRSIG's SGP4 implementation details (which TLE epoch convention, which
gravity model — check `docs/new/` for whatever DIRSIG's SGP4 documentation says) and any
frame-convention mismatch between the two paths' motion inputs (ECEF vs. whatever DIRSIG's
native engine expects internally — don't assume it's ECEF just because ours is). Add this
result as a new dated FINDINGS.md entry; don't leave it as chat output only. A new notebook
isn't required for this — a short script or a scratch cell block is fine, since this is a
one-off verification, not a tutorial artifact — but the comparison method and result belong
in FINDINGS.md regardless of where the code lives.

### 4b — Make the vacuous-coverage-check finding load-bearing, not just documented

FINDINGS.md's Phase 3 section already establishes that `SCENE._check_coverage()` on a
`_fname`-referenced scene passes silently regardless of actual material coverage, because the
bare `SCENE`'s only material is dirfm's placeholder `Dummy`. Tacoma's own coverage happened to
be fine because it was checked by hand against `tacoma.mat`. That manual check needs to
become a repeatable, checked step, not a one-time exercise repeated from memory each time this
mechanism is used.

Write a small helper in `src/protodirsig/` (co-locate with `orbit.py`/`sensors.py`, name it
for what it does — e.g. a `scene_coverage` module or function) that parses a scene's real
material database (`.mat` file referenced by the `.scene` XML's `<matfilename>`) and reports
the wavelength range each material actually covers, so a `_fname`-referenced scene's coverage
can be checked programmatically against a requested band rather than by hand-reading the
`.mat` file's XML. It doesn't need to be a general DIRSIG material parser — just enough to
answer "does this scene's real materials cover band [a, b]" for the cases this project
actually uses. Add a short test (following `tests/test_orbit.py`'s pattern) that runs it
against Tacoma's real `materials/tacoma.mat` and asserts the known-good result (covers
0.40–0.78 µm per the existing finding) so a future scene reference has something to compare
against besides re-reading XML by hand. Wire `tutorial_tacoma_scene.ipynb`'s existing
band-coverage markdown/code cell to call this helper instead of (or in addition to,
your judgment) the manual narrative that's there now.

### 4c — Investigate the z ≈ −0.1 m off-mesh surface

FINDINGS.md flags this as "not investigated further," but it's a bigger risk than it might
look: an untraced backdrop with no documented source can produce a plausible-looking image
with wrong radiometry, silently, which is a worse failure mode than an obvious rendering
error. Before the Tacoma scene is used for anything beyond a boresight-geometry demo, narrow
down what that surface actually is.

Starting points: check whether `scene2hdf`'s verbose/debug output (or `asset_report.txt`,
already produced by every render) names an implicit ground or bounding geometry; check
DIRSIG's `docs/new/` for any documented default/fallback surface behavior when a ray misses
all declared geometry (search terms: "miss", "background", "default surface", "bounding");
check whether the z-value is exactly one of Tacoma's declared origin/anchor altitudes
(coincidence would suggest it's related to scene-level georeferencing, not a stray object);
and check the two other Tacoma scene variants (`state1.scene`, `state2.scene`) for whether
the same surface appears there too (if it's scene-file-independent, that points toward a
`scene2hdf`/`dirsig5` binary default rather than something in `tacoma.scene` itself).

Report findings even if inconclusive — if the cause can't be pinned down with reasonable
effort, say so explicitly in FINDINGS.md along with what was ruled out, rather than leaving
the entry exactly as it stands now. Don't spend disproportionate time here relative to 4a/4b;
this is a "narrow it down," not "solve it definitively," task.

CONSTRAINTS
- Same as Phase 3: never write, modify, or delete anything under the DIRSIG install
  directory or the dirfm checkout. If 4a's DIRSIG-native-SGP4 render needs its own scene
  reference, reuse the same copy-XML-plus-symlink-assets pattern already built for Tacoma in
  Phase 3, and reuse the fingerprint guard already written for
  `tutorial_tacoma_scene.ipynb` rather than writing a parallel one.
- Report git status and give the actual `git add`/`git commit` commands after each of 4a,
  4b, 4c — three separate commits, not one, since they're independent pieces of work and
  Kevin may want to review them separately.


---

## Phase 5 — AUROR_kevin SWIR demo (Notebook 4)

Build a notebook that runs the SWIR demo run tree handed over at
`AUROR_kevin/_20260720_KevinSWIRDemo/` (inside protoDIRSIG, not the DIRSIG install or the
dirfm checkout). This tree was built by someone else on a different machine with a different
DIRSIG version — read it as received, don't guess at what it means.

CONTEXT
The tree has `jsims/`, `motion/`, `output/`, `platforms/`, `scenes/tahoe/`, `tasks/`,
`weather/`. Every file each component references exists and is self-contained ($SCENE_DIR-
relative in the scene, no external references elsewhere) — the content is complete. The one
file that is not portable is `jsims/KevinSWIRDemo.jsim` itself: its `motion_filename`,
`platform_filename`, `tasks_filename`, the weather plugin's `filename`, and the scene's
`inputs` are absolute paths under `/Users/rj.pearsall/Documents/DIRSIG/...` — a different
person's machine. Rewrite these to point at the local files; don't try to run the jsim as-is.

Two things to resolve, not assume:

1. `scenes/tahoe/tahoe.scene.hdf` (already compiled, 1.06 GB) and `output/swir.img` /
   `swir.img.hdr` were both produced by DIRSIG `2025.09 (8cfb36b)` (per
   `jsims/material_report.json` and the image header's description field). This install is
   `2026.38 (a020954)`. Don't reuse the existing `.hdf` — recompile the scene fresh against
   this install's `scene2hdf`, the same way `scene_ref.py` already does for Tacoma. Treat
   `output/swir.img` as a reference artifact from a different version to compare against,
   not a target to reproduce bit-for-bit.
2. The jsim's `FourCurveAtmosphere` plugin stanza is `{"conditions": "mls_rural_50km"}` with
   no database path — DIRSIG apparently resolves this against some built-in default.
   `dirfm.atmosphere.FourCurveAtmospherePlugin` has no such default: it requires an explicit
   HDF path (`modtran_output`) and validates the named condition exists inside it. This
   install ships four-curve databases under `lib/data/atm/` and the
   `FourCurveAtm_Databases-*/` directories (10/20/100 km variants) — check each one's
   `Conditions` group (via `h5py`, same approach `FourCurveAtmospherePlugin` itself uses) for
   `mls_rural_50km`. If none contains it, pick the closest available condition and state
   explicitly, in a markdown cell, which one was substituted and why — this is a deviation
   from the original run, the same way Phase 3 flagged its stare-vs-nadir pointing deviation,
   not something to pick silently.

Smaller thing to flag, not fix: `tasks/PacificTime_11.30AM.tasks`'s reference datetime is
`2026-07-16T11:30:00.0000-08:00`. Pacific time in July is daylight time (UTC−7), not standard
time (UTC−8) as the file has it. State this discrepancy in a markdown cell and use the file's
stated offset as given unless there's a clear reason to correct it — don't silently change
someone else's input file's meaning.

CAPABILITY CHECK — confirm before building, don't assume either answer
dirfm already wraps every plugin this jsim uses — confirm each, don't take this list on
faith:
- `BasicPlatform` — `dirfm.platform_sensor.PlatformSensorPlugin`. Its `prepare()` always
  rebuilds `platform`/`motion`/`tasks` XML from Python objects; there is no `SCENE`-style
  `_fname` short-circuit for wrapping the existing `.platform`/`.ppd`/`.tasks` files
  directly. Resolve this the same way `scripts/crosscheck_sgp4.py` already resolved an
  equivalent gap in Phase 4a (a minimal custom `Plugin` subclass implementing only
  `get_plugin_name`/`get_plugin_inputs`, pointed at copies of the existing files) rather than
  fighting `PlatformSensorPlugin`'s object model to reproduce files that already exist.
- `SpiceEphemeris` — `dirfm.ephemeris`, no inputs needed, matches the original jsim's empty
  `inputs: {}`.
- `ThermWeather` — `dirfm.weather.ThermWeatherFilePlugin(fname)` already takes an existing
  `.wth` path directly; point it at a copy of `weather/saw.wth`.
- `FourCurveAtmosphere` — `dirfm.atmosphere.FourCurveAtmospherePlugin`, per the database
  question above.

CONSTRAINTS
- Never write into the DIRSIG install directory or the dirfm checkout (standing rule,
  unchanged).
- Don't modify or overwrite anything under `AUROR_kevin/_20260720_KevinSWIRDemo/` — it's
  received reference material (scene assets, the original platform/motion/tasks/weather
  files, and the original rendered output), not a working directory. Copy what needs copying
  into protoDIRSIG's own `outputs/` tree, following the copy-XML-plus-symlink-assets pattern
  `scene_ref.py` already implements for Tacoma, rather than compiling in place. The same
  scene2hdf-writes-beside-the-scene risk documented for Tacoma applies here; reuse the
  existing fingerprint guard around this tree too, not a new one.
- Write the notebook to `notebooks/tutorial_swir_demo.ipynb`.
- Reuse `src/protodirsig/scene_ref.py` and `scene_coverage.py` where they fit; extend them if
  this scene's layout needs something they don't already handle, rather than writing a
  parallel one-off.

STRUCTURE — minimum viable, same convention as Phase 3: markdown explaining what's new versus
reused, each stage additive and actually executed before the next is written.

Stage 0 — Orientation and capability check: the questions above, answered from the source
(grep dirfm, inspect the bundled HDF databases with h5py), before any dirfm objects are
built. State plainly that the `_fname`/custom-Plugin-subclass mechanism here is the same
reference-an-existing-file pattern established for Tacoma's scene and Phase 4a's SGP4 engine,
not new mechanism.

Stage 1 — Reference and assemble: build the scene reference, the platform/motion/tasks
reference (via the capability check's resolution), the weather reference, and the atmosphere
plugin (with its resolved or substituted condition). Assemble on a `DIRSIG` object but don't
run yet — inspect the resulting jsim's plugin/scene list and confirm it matches the original
`KevinSWIRDemo.jsim` apart from the path rewrite and the atmosphere database necessity.

Stage 2 — Run and compare: run it (fresh `scene2hdf` compile, fingerprint-guarded), load the
resulting `swir.img` and the original reference `output/swir.img` as ENVI arrays, and compare
them quantitatively, not just visually. State which differences are expected (DIRSIG version,
any atmosphere condition substitution) versus anything unexplained — don't assert a match
without checking, following the same truth-check discipline as Phase 3.

Append any new findings (the atmosphere database resolution, the version-compile outcome, the
timezone discrepancy's actual effect if checked) to FINDINGS.md. Report git status and the
actual `git add`/`git commit` commands when done.


---

## Phase 6 — AUROR_ref hypersonic-target run (Notebook 5)

Build a notebook that runs the run tree at `AUROR_ref/` (inside
protoDIRSIG, not the DIRSIG install or the dirfm checkout). Read it as received, the same way
Phase 5 treated the SWIR demo tree — this is a different person's run, on a different DIRSIG
version, and it is not a duplicate of the SWIR demo's Tahoe configuration. Don't conflate the
two: this scene variant omits `mwir`, adds a `hypersonic.glist` geometry inclusion (material
`Gidder_mat`) on top of the Tahoe background, and has both the material map and texture map
disabled. Treat it as its own scene, not an alternate rendering of the one Phase 5 used.

CONTEXT
The tree has `jsims/AurorSimulation.jsim` (+ `material_report.json`, plus a bare-filename HDF5
file `jsims/AurorNewAtmosphere`), `motion/AurorMotion.ppd`, `platforms/` (three `.platform`
files), `tasks/AurorTask.tasks`, `weather/saw.wth`, and `tahoe.scene` (+ compiled
`tahoe.scene.hdf`) at the tree root. The one jsim present references only one of the three
platform files (`AurorNIRDetector.platform`) — the other two (`AurorHSICamera.platform`,
`AurorPlatform.platform`) have matching pre-rendered outputs elsewhere in the tree
(`result.img`, `auror.img`) but no jsim of their own survives to explain them. Use only
`AurorNIRDetector.platform`, matching the one jsim that exists; don't try to reconstruct the
other two's jsims from the platform files alone.

`jsims/AurorSimulation.jsim` itself is not portable: `platform_filename`, `motion_filename`,
`tasks_filename`, the weather plugin's `filename`, the atmosphere plugin's `hdf_filename`, and
the scene's `inputs` are Windows-style absolute paths under `C:/DIRSIG/AUROR/Kevin_DIRSIG/...`
(inconsistently slashed — forward and back slashes both appear). Rewrite these to point at the
local files; don't try to run the jsim as-is.

Two things to resolve, not assume:

1. `tahoe.scene.hdf` (already compiled, 25.7 MB — far smaller than the SWIR demo tree's 1.06
   GB compile of what is nominally "the same" base scene) and every pre-rendered `.img` in
   `jsims/` (`auror.img`, `AurorNIROutput.img`, `MultiBandCamera_rgb.img`,
   `MultiBandCamera_rgb_truth.img`, `result.img`, `truth1.img`) were produced by scene2hdf
   `2025.51 (822ab24)` per `jsims/material_report.json` — a third distinct version from both
   this install (`2026.38 (a020954)`) and the SWIR demo tree's (`2025.09 (8cfb36b)`). Don't
   reuse the existing `.hdf`; recompile fresh against this install, same as Phase 5 did.
   Treat every existing `.img` as a reference artifact to compare against, not a target to
   reproduce bit-for-bit — and note that only `AurorNIROutput.img`/`truth1.img` correspond to
   the platform this notebook actually uses, so that's the only pair worth a quantitative
   comparison; the other outputs have no surviving jsim/platform pairing to validate against.
2. The jsim's atmosphere plugin is `NewAtmosphere`, not `FourCurveAtmosphere`. This is already
   fully wrapped by `dirfm.atmosphere.NewAtmospherePlugin` (confirmed by reading
   `dirfm/atmosphere.py`) — not a gap. `NewAtmospherePlugin(fname)` takes an existing HDF path
   directly (same reference-an-existing-file pattern as `ThermWeatherFilePlugin` and `SCENE`'s
   `_fname`), so point it at a copy of `jsims/AurorNewAtmosphere`. The inline MODTRAN tape5
   config in the jsim (`modtran_profile`, `atmospheric_model = "MidLatitudeSummer"`,
   `boundary_aerosol_model.type = "RuralVis23Km"`, `multiple_scattering.type = "Isaac"`) must
   still be reconstructed via `dirfm.atmosphere.ModtranTapeBackend`'s setters
   (`set_atmospheric_model`, `set_boundary_aerosol_model`, `set_multiple_scattering`,
   `set_profile`, etc.) and attached with `set_backend()`/`set_info()` before
   `get_plugin_inputs()` is called — the plugin needs both the existing HDF reference and the
   backend description reconstructed in Python; it doesn't infer one from the other.

Smaller things to flag, not fix:
- `tasks/AurorTask.tasks`'s reference datetime is `2009-07-27T11:29:32.0000-08:00` — stale
  relative to every other file in the tree (2026). Use it as given; state the discrepancy in a
  markdown cell.
- The scene's disabled material/texture maps and missing `mwir` feature are internally
  consistent with a single-target detection/geolocation run (the platform's truth collectors
  are `Collection 1`→`truth1`, `GeoLocation`→`NewCollection`; nothing in the platform's
  bandpass needs `mwir`) rather than a land-classification demo like Phase 5's. Say this
  plainly in a markdown cell rather than treating the disabled maps as something to "fix" or
  re-enable.

CAPABILITY CHECK — confirm before building, don't assume either answer
- `BasicPlatform` — `dirfm.platform_sensor.PlatformSensorPlugin`. Same gap as Phase 5: its
  `prepare()` always rebuilds `platform`/`motion`/`tasks` XML from Python objects, no
  `_fname`-style short-circuit. Resolve it the same way — a minimal custom `Plugin` subclass
  (`get_plugin_name`/`get_plugin_inputs` only) pointed at copies of
  `AurorNIRDetector.platform`, `AurorMotion.ppd`, `AurorTask.tasks` — reusing the pattern
  already established in `scripts/crosscheck_sgp4.py` and Phase 5, not re-deriving it.
- `SpiceEphemeris` — `dirfm.ephemeris`, no inputs, matches the jsim's empty `inputs: {}`.
- `ThermWeather` — `dirfm.weather.ThermWeatherFilePlugin(fname)`, point at a copy of
  `weather/saw.wth`.
- `NewAtmosphere` — `dirfm.atmosphere.NewAtmospherePlugin`, per the resolution above. Confirm
  by reading `dirfm/atmosphere.py` directly in the notebook's orientation stage (don't take
  this spec's description on faith) before building the plugin.

CONSTRAINTS
- Never write into the DIRSIG install directory or the dirfm checkout.
- Don't modify or overwrite anything under `AUROR_ref/` — received
  reference material, not a working directory. Copy what needs copying into protoDIRSIG's own
  `outputs/` tree via `scene_ref.py`'s existing copy-XML-plus-symlink-assets pattern and
  fingerprint guard, the same as Phase 3 and Phase 5.
- Write the notebook to `notebooks/tutorial_auror_hypersonic.ipynb`.
- Reuse `src/protodirsig/scene_ref.py` and `scene_coverage.py` where they fit; extend rather
  than duplicate if this scene's `hypersonic.glist` inclusion needs something they don't
  already handle (check whether `scene_coverage.py`'s material-DB parsing handles a
  `geometrylistinclude`-contributed material like `Gidder_mat`, which isn't in the base
  scene's own `.mat` file the same way Tacoma's materials are — confirm, don't assume either
  way).

STRUCTURE — minimum viable, same convention as Phase 3/5: markdown explaining what's new
versus reused, each stage additive and actually executed before the next is written.

Stage 0 — Orientation and capability check: confirm `NewAtmospherePlugin`'s interface and
`ModtranTapeBackend`'s setters by reading `dirfm/atmosphere.py` directly; confirm the
`BasicPlatform` gap and its resolution exactly mirror Phase 5's precedent. State plainly which
mechanisms are new to this notebook (`NewAtmospherePlugin`, the `hypersonic.glist` inclusion)
versus reused unchanged from Phase 3/5.

Stage 1 — Reference and assemble: build the scene reference (including the `hypersonic.glist`
inclusion), the platform/motion/tasks reference via the capability check's resolution, the
weather reference, and the `NewAtmosphere` plugin (existing HDF + reconstructed backend).
Assemble on a `DIRSIG` object but don't run yet — inspect the resulting jsim's plugin/scene
list and confirm it matches the original `AurorSimulation.jsim` apart from the path rewrite.

Stage 2 — Run and compare: run it (fresh `scene2hdf` compile, fingerprint-guarded), load the
resulting render and the original reference `AurorNIROutput.img`/`truth1.img` as ENVI arrays,
and compare quantitatively. State which differences are expected (DIRSIG version) versus
anything unexplained.

Append any new findings (the `NewAtmosphere` resolution, the version-compile outcome, whether
`scene_coverage.py` needed extending for the `hypersonic.glist` material) to FINDINGS.md.
Report git status and the actual `git add`/`git commit` commands when done.
