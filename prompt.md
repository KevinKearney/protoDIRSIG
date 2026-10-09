# Make the vehicle (URSO) actually appear -- tutorial fix plus a sidebar distillation

## CONTEXT

FINDINGS.md (lines ~400-480) diagnosed why the vehicle target is invisible in the AUROR_ref render
and left it unresolved. Re-verify these numbers yourself -- don't trust this prompt's arithmetic
blindly:

- The vehicle uses material `Gidder_mat`
  (`config_repo/scenes/tahoe/geometry/bundles/hypersonic/hypersonic.mat`, reached via
  `lists/hypersonic.glist`), geometry `hypersonic.obj` in the same directory -- a real multi-facet
  mesh (9227 vertices, 9224 faces), not a simplified shape. The material's reflectance is driven by
  `REFLECTANCE_PROP_NAME = SimpleReflectance`, `TXT_FILENAME = ref.txt`, a six-line wavelength[um]/
  reflectance table (0.4 through 3.0 um) with every value set to 0.00 -- so the "zero reflectance,
  pure emitter" behavior is a content problem in one small text file, not a material-schema
  limitation, and the real mesh is already present and does not need to be approximated by a disk
  for anything other than the tutorial-level fix below. `TEMP_SOLVER_NAME = DataDriven`,
  `TEMPERATURE = 1500`, drives the existing 1500 K blackbody emission term.
- `ref.txt` and `hypersonic.obj`/`hypersonic.mat`/`hypersonic.glist` exist in at least two places:
  the live `config_repo/scenes/tahoe/geometry/bundles/hypersonic/` and the test-fixture copy under
  `notebooks/dev/AUROR_ref/geometry/bundles/hypersonic/` (per Stage 05's config_repo/fixture split).
  Confirm which copy is actually resolved for a generated AUROR run today, and grep for every other
  reference to `ref.txt`, `hypersonic.obj`, `hypersonic.mat`, `hypersonic.glist`, and `Gidder_mat`
  across `config_repo`, `tests/fixtures`, and any generated job directories before changing
  anything -- you need the full set of places a change propagates to, not an inventory trusted from
  this prompt.
- The vehicle is a ~2 m-scale bundle on a `straight` dynamic instance starting at scene-ENU
  (-400, 400, 50000). The sensor's single static pose is at (-400, 400, 550000) -- 500 km directly
  above, Euler (0, 0, pi). `run_specs/auror_ref.yaml` has `geometry.range.value: 500000` and
  `targets: [{class: vehicle_air}]`.
- Sensor optics, from `eopticDocs/.../sensors/auror-nir.yaml`: 85 mm aperture, 306 mm focal length
  (f/3.6), single NIR channel at 0.85 um (Gaussian bandpass, sigma 0.0637 um), 10 um pixel pitch.
  IFOV = 10um / 306mm * 500000m = ~16.3 m/pixel.
- FINDINGS.md's silhouette estimate: ~0.63 m^2 top-down area, ~0.24% of one 16.3 m pixel's area --
  small enough that DIRSIG's default pixel sampling (one ray per pixel center, or an adaptive grid
  of sub-elements per `subsamples.html`) can miss it entirely regardless of sample count, since
  sub-sampling increases ray density per pixel, not targeted coverage of sub-pixel geometry. DIRSIG
  has no general "oversample this region of the scene" control for this.
- FINDINGS.md flagged an untested kinematic candidate: the `straight` dynamic instance's time base
  may place the vehicle outside the sensor's field at task time 0 (100 m/s clears an ~8 km field in
  ~40 s). Confirm or rule this out before attributing non-appearance purely to sub-pixel geometry or
  material physics -- it could be a third, independent bug, and both steps below depend on the
  vehicle actually being in-frame at the task's evaluation time.

Two approaches, assigned to two places in the repo by complexity, not by priority. Kevin will not be
available to review either one before or during this work -- make the calls this prompt leaves open
yourself, record the reasoning in FINDINGS.md, and proceed; don't stall waiting for confirmation.

## STEP 1 -- tutorial fix (stage_02_conformance_template.ipynb)

An oversized, visibility-only Lambertian disk, kept deliberately simple. At ~16.3 m/pixel IFOV,
5-10 pixels of subtense means a disk diameter of roughly 82-163 m -- recompute from the live
geometry, don't hardcode. This is 1-2 orders of magnitude larger than the vehicle's real
~0.9 m-scale silhouette, and that's fine: this is sandbox work, not mission simulation, and the
goal is only to make the target show up reliably in the conformance-template workflow. No
flux-conservation derivation is needed here -- pick a reasonable Lambertian albedo (0.8 is a fine
starting point) and move on. Keep this notebook at tutorial-level complexity; don't pull any of
Step 2's machinery into it. Confirm the vehicle is now visible, re-run the notebook top to bottom,
report the render result and the albedo/size used, and commit as its own commit.

## STEP 2 -- sidebar distillation, using the real bundle

Outside `stage_02_conformance_template.ipynb`, in `notebooks/dev/` or wherever
`notebooks/README.md`'s own conventions for exploratory work say it belongs (confirm, don't assume)
-- build a physically grounded point-source intensity from DIRSIG's own renderer, using the actual
`hypersonic.obj` mesh, not a disk approximation:

1. Give the mesh a nonzero, physically plausible reflectance by replacing `ref.txt`'s all-zero
   table with real values across its tabulated wavelengths (a flat ~0.3-0.8 Lambertian reflectance
   is a reasonable starting assumption absent a real measured curve for this airframe -- state
   which value and why). **Decide yourself, and record the reasoning in FINDINGS.md, whether to
   edit the live `ref.txt` in place or introduce a new reflectance-curve file (e.g.
   `ref_reflective.txt`) and point a new/duplicated material at it, leaving the original
   emitter-only `Gidder_mat`/`ref.txt` untouched.** The deciding factor is whether anything else in
   the repo (other run specs, other fixtures, other scenes) still depends on the original
   zero-reflectance behavior -- your grep from the CONTEXT section settles this; if `Gidder_mat` is
   only ever used by AUROR_ref's vehicle target, editing in place is simpler and there is no
   original behavior to preserve. If it's shared, don't mutate it under other consumers.
2. Render the real mesh at close range, oriented and posed so the solar illumination vector and the
   mesh-to-sensor view vector match AUROR_ref's actual task-epoch geometry exactly. Range itself
   doesn't matter for this step, only the two angles, since radiance from a Lambertian reflector is
   range-invariant; choose whatever close range makes the mesh comfortably resolved (tens of pixels
   across).
3. Run this close-range pass with no atmosphere (vacuum, or an explicitly negligible path) between
   the close sensor and the mesh. The native point-source mechanism (step 5) already applies
   source-to-sensor transmission when the result is placed in the full 500 km scene; including
   atmosphere in both passes double-counts it.
4. Integrate the close-range radiance map into a single radiant intensity: sum per-pixel radiance
   over the mesh's rendered footprint, weighted by each pixel's solid angle and range^2, which
   reduces to mean radiance times the mesh's true projected area at the rendered pose:
   I(lambda) = L_bar * A_proj, in W/sr. Using the real mesh here (rather than a disk) means this
   number already reflects the true silhouette and any self-shadowing/faceting at the real phase
   angle -- that's the whole point of using the actual asset instead of an idealization.
5. Write the result into a static `.int` file (wavelength[um], radiant intensity[W/sr/um] -- see
   `int.html`; the manual places no constraint on spectral sampling) and define the vehicle as a
   GLIST `<basesource><pointsource matid="...">` entry per `sources.html`'s "User-Defined Sources"
   section (`OPTICAL_DESCRIPTION = SOURCE`, `INTENSITY_FILENAME`, no angular shaping needed for a
   single static pose). Confirm the GLIST/material schema yourself in the local docs before writing
   it; this prompt summarizes but does not reproduce the full syntax.
6. Render AUROR_ref's full scene with this point source in place of (or alongside -- your call,
   state which and why) the existing hypersonic bundle target. Check `secondarysources.threshold`
   in the `.options` file (default 1.0e-05) against the computed intensity and report whether it
   would be dropped and what adjusting it to retain it implies.
7. Report the result against Step 1's tutorial-disk result and against FINDINGS.md's original +49%
   emitter-based expectation for the true-sized object.
8. Write up the method -- including the ref.txt in-place-vs-new-file decision and why, the assumed
   reflectance value, the computed I(lambda), and the render result -- in FINDINGS.md as a new dated
   entry, and commit separately from Step 1.

A third mechanism exists, the `LightCurve` sensor plugin (`lightcurve_plugin.html`) -- an
independent magnitude-vs-time diagnostic, not a focal-plane renderer, and incompatible with
AUROR_ref's `new_atmosphere` setup per the manual. Worth a one-line mention in FINDINGS.md as a
possible independent validation path, not worth implementing here.

## CAPABILITY CHECK

Before writing anything:
- Re-derive the IFOV/silhouette-fraction numbers from the current `run_specs/auror_ref.yaml`, the
  hypersonic bundle geometry, and `eopticDocs/.../sensors/auror-nir.yaml` -- don't assume this
  prompt's numbers are still current.
- Grep the DIRSIG install docs for `pointsource`, `basesource`, `secondarysources`, and `int.html`'s
  file format before writing any `.int` file or material block.
- Grep for every reference to `ref.txt`, `hypersonic.obj`, `hypersonic.mat`, `hypersonic.glist`, and
  `Gidder_mat` across `config_repo`, `tests/fixtures`, and any generated job directories -- this is
  what the in-place-vs-new-file decision in Step 2.1 turns on.
- Confirm which GLIST/scene/material files are actually resolved for a generated AUROR run today
  (per Stage 05's config_repo/fixture split) so you edit the live copies, not stale ones.
- Read `notebooks/README.md` to confirm where exploratory/sidebar notebooks belong before placing
  the distillation notebook; `notebooks/dev/` is a reasonable guess, not a mandate.

## CONSTRAINTS

- Don't modify `dirfm` itself.
- Don't touch `config_repo/`'s other contents beyond what each step specifically requires.
- Keep Step 1 and Step 2 as separate commits.
- Don't fix the kinematic candidate (the `straight` dynamic instance's time base) as a silent side
  effect of either step -- if you find the vehicle isn't in-frame at task time 0, stop and report it
  in FINDINGS.md rather than patching it inline; it's a prerequisite bug, not part of either
  approach's scope, and you won't have Kevin available to weigh in on how to fix it.
- Every judgment call this prompt leaves to you (ref.txt in-place vs. new file, the assumed
  reflectance value, point-source-replaces-vs-alongside the bundle) must be stated explicitly with
  its reasoning in FINDINGS.md -- don't make a silent choice and only reveal it in a git log message.

Report git status and the actual git add/git commit commands at the end of each step.
