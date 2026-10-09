# Sensor model, round two -- real-data intake, generator coverage, absolute radiometry, a sweep notebook

## CONTEXT

protoDIRSIG now renders the job's `.platform` from a `sensor-spec/1` entry plus the run spec's `settings`
(`src/protodirsig/platform_gen.py`, `spectral.py`). Read these before anything else, in this order, and
re-verify what they claim rather than trusting this prompt:

- `docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md` sections 3.2, 4, 7, 9 (the "Sensor radiometry" block) and 10 (rows C-14
  to C-18). It is the as-built document and the only human-facing record.
- `sensors/README.md`, `sensors/spectral/README.md` (the `spectral-curve/1` format), `contracts/sensor-spec-1.schema.json`.
- `src/protodirsig/platform_gen.py`, `spectral.py`, `run_spec.py`, `simulation.py`; `scripts/stamp_hashes.py`.
- `tests/test_platform_render.py`, `tests/test_sensor_render.py`, `tests/test_sensor_library.py`,
  `tests/test_spectral_curves.py`, `tests/test_hashes.py`.
- `.claude_mem/ARCH_LOG.md`, last entry (2026-10-09): every decision already made, with reasons. Treat them as
  standing unless a step below says otherwise. `.claude_mem/` is your working memory: log there, never cite it from
  `docs/`, `BACKLOG.md`, READMEs, notebooks or code comments.

State at the start: three library sensors (`auror-nir`, `deepscan_850_306_nir_1280`, `synthetic_600_200_vis_1920`),
three synthetic curves (`sensors/spectral/qe/synthetic_visgaas.csv`, `qe/synthetic_silicon.csv`,
`optics/synthetic_vis_lens.csv`, 0.150-14.000 um at 1 nm), two run specs (`auror_ref.yaml`, `synthetic_vis.yaml`),
109 passing tests.

Facts established last round that shape this work:

- DIRSIG takes one response per channel. With `fluxunits="electronspersecond"` it treats that response as QE.
  `platform_gen` writes a tabulated channel carrying optics x shape x QE on the template's 0.41-2.0 um bandpass
  grid, refuses a channel with more than 0.1 % of its response outside that grid, and `spectral.Curve.at` refuses
  to extrapolate (`extrapolation: none`).
- A native DIRSIG gaussian channel (`normalize="false"`) peaks at 1/sqrt(2 pi), width = sigma. `auror_ref.yaml` keeps
  `engine.platform.channel_response: native` to reproduce the received tree; every other run spec is `tabulated`.
  Kevin decides whether that changes. Do not change it.
- `roi` lives in `descriptor.settings`; the generator writes it into `xelementcount` and `yelementcount`.
- Renders: a 500 x 500 window takes about 7 minutes; a 16 x 16 window takes seconds. Tests use 16 x 16.
- Python 3.11 is required (3.10 fails five tests on `datetime.fromisoformat`). `jsonschema` is a dev dependency.
- `content_hash` on a file ref is the sha256 of the file bytes. After editing any sensor-spec, curve or
  `config_repo` file, run `python scripts/stamp_hashes.py`; `--check` is a test.

Kevin will not be available to review any of this before or during the work -- make the calls this prompt leaves
open yourself, record each with its reasoning in `.claude_mem/ARCH_LOG.md`, and proceed; do not stall for
confirmation. Measured results go in `.claude_mem/FINDINGS.md`. Whatever changes the as-built contract also goes in
the CONOPS (section 10 row if it touches MANIFOLD) or `BACKLOG.md`, in plain prose with no pointer to the logs.

## STEP 1 -- real-data intake for spectral curves

Kevin will replace the synthetic curves with real ones (Teledyne SCION QE; later lens and filter data). Real data
will not look like the synthetic files: coarser and non-uniform grids, nanometres, percent, a range of about
0.3-1.7 um rather than 0.150-14.000 um. As built, a real SCION curve fails: the job bandpass (0.41-2.0 um) extends
past 1.7 um and `Curve.at` refuses to extrapolate.

1. Write `scripts/import_curve.py` (stdlib plus numpy, no new dependencies): reads a two-column CSV or whitespace
   text, takes `--kind qe|optics|filter`, `--name`, `--wavelength-unit nm|um`, `--percent`, `--provenance
   vendor_typical|measured`, `--source <text>`, and writes `sensors/spectral/<kind>/<name>.csv` in `spectral-curve/1`
   at the input's own wavelength grid, sorted and de-duplicated, values checked into [0, 1] (reject, do not clip,
   values that are out of range by more than rounding).
2. Outside the measured range the file must say what the detector does, explicitly. Add `--pad-zero-to LO,HI`
   (um): writes zero rows at LO and HI, and records the padding in the header (`# padding: zero below X um and above
   Y um; not measured`). No implicit padding anywhere. Decide whether padding to the template's bandpass edges or to
   0.150-14.000 is the better default recommendation, and say so in `sensors/spectral/README.md`.
3. The header carries `provenance`, `source` and an `acquired` date; extend `spectral.REQUIRED` and the README table
   only if you add a required key, and keep the three existing synthetic files valid.
4. Tests (`tests/test_import_curve.py`): nm and percent input round-trips; descending or duplicated wavelengths are
   fixed or rejected as you decide; out-of-range values are rejected; padding is recorded and only where asked; the
   output is read back by `read_curve` and passes the `test_spectral_curves` shape test; a padded curve composes with a
   channel through `platform_gen` without raising.
5. Run it on a fabricated vendor-style file in a temp directory to prove it works. Do not add a fabricated curve to
   `sensors/`.

## STEP 2 -- generator coverage the tests do not yet reach

Find and close the gaps. Known ones:

- The `srf_reference` path (a curve in place of `srf_model`) has no test. Add a `filter` curve file (a synthetic
  rectangular band, in a temp library) and assert the generated platform equals the one from the matching
  `srf_model: {kind: rectangular}`.
- Only single-channel entries are rendered. Add a two-channel entry in a temp library and assert the platform has
  two tabulated channels with the right names, gain and bias, and that a real 16 x 16 render produces a two-band
  image. Check how `split_channels` interacts and report it.
- A native rectangular channel's amplitude is unmeasured. Measure it the way the gaussian was (render native against
  tabulated, 16 x 16) and record the factor in CONOPS section 9. If edges matter (grid-aligned edges, inclusive or
  exclusive), say which DIRSIG uses.
- More than one focal plane or sensor entry, and a `settings` list of other than one member, must fail with a specific
  error before any render. Confirm each does and test it.
- Re-read `platform_gen.py` for any value the sensor-spec or settings model that the generator does not write
  (readout, `SensorShutterMode`, `AdcBitDepth`, pixel offsets, flips). For each: write it if DIRSIG has an element for
  it and a test can pin it, otherwise list it in `BACKLOG.md` under "Generator scope". Do not invent DIRSIG elements;
  confirm against the install docs (`$DIRSIG_HOME/docs/basicplatform_plugin.html`).

## STEP 3 -- absolute radiometric check

The render tests establish shape, linearity, additivity and geometry, not the electron count. Attempt an
independent one, bounded:

1. Build the simplest scene with a known radiance: a Lambertian plane of known reflectance under a known
   irradiance, vacuum or an explicitly negligible path, looked at by a `tabulated` sensor. Take the irradiance
   from DIRSIG's own solar data in the install (find the file the renderer actually reads; confirm, do not assume),
   not from your own memory of a solar constant.
2. Compute the expected electrons per pixel analytically: integral of L(lambda) * tau(lambda) * QE(lambda) *
   (pi / (4 F#^2)-type geometric factor for the pixel area, check DIRSIG's own G# definition in the docs) *
   t_int * lambda / (h c) d lambda, with the sensor's own curves. Compare with the render.
3. Agreement to a few percent is a pass. A mismatch is a finding, not a failure to hide: find which factor
   accounts for it (units, G#, pi, the 0.399 native amplitude, `aperturethroughput`), say so in FINDINGS.md, and
   record it in CONOPS section 9.
4. If a defensible independent reference is not reachable in a reasonable effort (for example, DIRSIG's solar
   irradiance cannot be separated from its own render), stop, record what you tried, and leave the BACKLOG item
   "Absolute radiometric check" in place with that detail. Do not write a test that computes its expected value
   from the generator's own output.
5. If it passes, add it as a test (small window, a few seconds) and delete the BACKLOG item.

## STEP 4 -- a new-user notebook for the sensor sweep

`notebooks/stage_03_sensor_sweep.ipynb`, in the stage-notebook style (read `notebooks/README.md` and
`stage_02_conformance_template.ipynb` first; extend them, do not rewrite them). It shows a new user:

- the sensor library and one entry's blocks (`detector`, optics, channel, curve references), the three spectral
  curves plotted, and the composed channel response for each sensor on one plot;
- `derive_run_spec` turning `auror_ref.yaml` into a run spec for another sensor, and `LocalRegistry.submit`
  accepting it;
- the same scenario rendered with two sensors in a small window (the notebook's own ROI override, 32 x 32 or
  smaller, minutes not hours), the two images side by side, and the ground sample distance of each from the
  GeoLocation truth against pitch / focal length x range;
- a closing cell that states plainly what is synthetic and what is not.

Execute it top to bottom, save with outputs, keep it importable from a fresh clone (paths via `external/` and the repo
root, the way the bootstrap sets them; do not add new `~/DIRSIG` or sibling-checkout assumptions). Add its entry to
`notebooks/README.md` and a line to CONOPS section 8.

## STEP 5 -- housekeeping, only if Steps 1-4 are done

- Notebook text that cites `FINDINGS.md` (about 27 places across six notebooks; `grep -c FINDINGS notebooks/*.ipynb
  notebooks/*/*.ipynb`): replace each with a pointer to the CONOPS section that now holds the fact, or delete the
  sentence if the CONOPS does not hold it. Do not re-execute notebooks for a text-only change; edit the cell source
  only, and keep each notebook's JSON valid.
- Remove the BACKLOG item for it when done.

## CAPABILITY CHECK

Before writing anything:

- Run `python -m pytest tests -q` on Python 3.11 with `DIRSIG_HOME` set and `dirfm` importable; it should show 109
  passed. If it does not, stop and report why before changing anything.
- Confirm `scripts/stamp_hashes.py --check` exits 0.
- Grep the DIRSIG docs for `G#`, `solar`, `irradiance` and the channel shapes before Step 3, and for `rectangular`
  before the rectangular measurement in Step 2.
- Confirm where `dirfm` and the DIRSIG install are linked (`external/`, `scripts/bootstrap.py status`).

## CONSTRAINTS

- Do not modify `dirfm`, and do not touch `config_repo/` beyond what a step requires. No symlinks in `config_repo/`.
- Never guess a sensor value: unknown is `null`. Synthetic data is labelled `provenance: synthetic` and is never
  described as vendor or measured.
- Do not change `auror_ref.yaml`'s `channel_response: native`, the placement of `roi` in `settings`, or the
  one-run-spec-per-sensor rule. A finding that argues for changing one goes in the BACKLOG as an item.
- Keep the project light: one BACKLOG, one CONOPS. No new tracking documents, no process scaffolding. Delete
  anything you make obsolete.
- Run 500 x 500 renders never, except one if a step explicitly needs it; tests and notebooks use small windows.
- Every judgment call must be stated with its reasoning in `.claude_mem/ARCH_LOG.md`. Do not make a silent choice
  and reveal it only in a commit message.
- Each step is its own commit. After editing any hashed file, run `scripts/stamp_hashes.py` before committing.
  Run the full suite before each commit.

Report `git status` and the actual `git add` / `git commit` commands at the end of each step, and a final summary
of what passed, what is a finding, and what stayed open.
