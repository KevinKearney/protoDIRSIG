# Sensor files: correct `radiometric_reference` to the quantity the image carries

## CONTEXT

Every `sensor-spec/1` channel carries `radiometric_reference: {quantity: spectral_radiance, unit: "W/(m2.sr.um)"}`
(`sensors/auror-nir.yaml`, `deepscan_850_306_nir_1280.yaml`, `synthetic_600_200_vis_1920.yaml`; the comment says
"enum for electron flux TBD (A.9.1)"). The generated `.platform` writes `imagefile fluxunits="electronspersecond"`,
and `tests/test_absolute_radiometry.py` establishes that the image is electrons per m2 of focal plane (multiply by
element area for e-/pixel). The field therefore states a quantity the image does not carry. In
`contracts/sensor-spec-1.schema.json` the field is only `{"type": "object"}`, so nothing rejects it.

Detector_v02 (`AV_MANIFOLD_Detector_v02.md`, A.9.1; also `docs/DIRSIG_Platform_Decomposition.md` lines ~205-263 and
~312) closes `radiometric_reference.quantity` to {`radiance`, `spectral_radiance`, `irradiance`,
`brightness_temperature`, `digital_number`} and records that `@fluxunits=electronspersecond` is unmappable without an
electron-flux member. This work states what the file says truthfully and records the gap against Detector_v02; it
does not edit Detector_v02.

Read first, and re-verify rather than trust this prompt: `docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md` sections 4, 9 (the
"Sensor radiometry" block) and 10; `src/protodirsig/platform_gen.py`; `tests/test_absolute_radiometry.py`;
`tests/test_sensor_library.py`; `tests/test_sensor_render.py` (`B2`); `contracts/sensor-spec-1.schema.json`; the last
entries of `.claude_mem/ARCH_LOG.md`. `.claude_mem/` is working memory: log there, never cite it from `docs/`,
`BACKLOG.md`, READMEs, notebooks or code comments.

## STEP 0 - capability check

- Python 3.11 environment with `jsonschema` and pytest; `python -m pytest -q` passes at the start (148 tests).
- `grep -rn radiometric_reference` over the repository excluding `external/`, `outputs/` and `.git/`; list every
  hit. Known: the three sensor files, the schema, `tests/test_sensor_render.py` (`B2`), `notebooks/stage_03_sensor_sweep.ipynb`,
  BACKLOG, `docs/DIRSIG_Platform_Decomposition.md`.

## STEP 1 - determine the quantity, fix the files and the schema (one commit)

1. From `test_absolute_radiometry.py` and `platform_gen.py`, state exactly what a pixel value is: its units
   (electrons per m2 of focal plane per exposure, or per second), whether the exposure time is already applied, and
   what `fluxunits` does in DIRSIG. Check the DIRSIG documentation (`grep -rn fluxunits` under the install `docs`)
   and one 16 x 16 render with the exposure time doubled. Log the finding. If the value scales with exposure time,
   the unit says so.
2. Choose the representation. Default, unless step 1 contradicts it: `quantity: electron_exposure`,
   `unit: "e-/m2"` (focal-plane-referred; `e-/m2/s` if the image is a rate), marked as a proposed extension to the
   Detector_v02 enumeration. If a Detector_v02 member is in fact correct for the image, use it and log why.
3. Set the field in the three sensor files, replacing the stale comment with one line naming the quantity and
   that it is a proposed enum member. Unknown values stay `null`; do not invent `scale` or `offset`.
4. Schema: replace `{"type": "object"}` by an object with required `quantity` and `unit`, optional `scale` and
   `offset`, `additionalProperties: false`, `quantity` an enum of the five Detector_v02 members plus the proposed
   member. Define it once under `$defs`.
5. Tests: (a) schema rejects an entry whose `radiometric_reference.quantity` is outside the enum and one that omits
   `unit`; (b) a library-wide test that every channel's `radiometric_reference.quantity` is consistent with what
   `platform_gen` renders (an `imagefile` with `fluxunits=electronspersecond` requires the electron member), so the
   field cannot drift from the generator again; (c) update `B2` in `tests/test_sensor_render.py`.
6. `notebooks/stage_03_sensor_sweep.ipynb` prints a `radiometric_reference` block (line ~253): update the source and
   re-execute the notebook end to end; the output must contain no stale text.
7. Run `scripts/stamp_hashes.py` (the sensor files changed), then `scripts/stamp_hashes.py --check`, then the full
   suite. The generated `.platform` must be unchanged for all three sensors (the field is not rendered); show that
   with a before/after XML comparison on the sensors.

Commit: `Correct radiometric_reference to the electron image quantity`.

## STEP 2 - documents (one commit)

- `docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md`: section 4 field table and section 9 radiometry block state the
  quantity and unit; add row C-20 to section 10 (`radiometric_reference` electron member, status `proposed`, the
  question: does Detector_v02 add an electron-flux member, or does `imagefile` electrons map elsewhere?). Remove
  the statement that the field is "TBD" or mislabelled anywhere it appears.
- `BACKLOG.md`: delete the `radiometric_reference` clause from the Generator-scope paragraph (~line 80) and add
  nothing else; the open question lives in C-20.
- `docs/DIRSIG_Platform_Decomposition.md`: leave the Detector_v02 enumeration as quoted (it records the source),
  and add one line at ~263 / ~312 pointing to CONOPS C-20.
- `sensors/README.md` and `contracts/README.md`: only if they now state something false.

Commit: `Document the electron quantity and add C-20`.

## CONSTRAINTS

- Do not modify `dirfm`, `config_repo/`, `auror_ref.yaml`'s `channel_response: native`, the placement of `roi`, or
  the one-run-spec-per-sensor rule.
- Never guess a sensor value; unknown is `null`.
- Keep the project light: one BACKLOG, one CONOPS, no new tracking documents. Do not rename folders in this work.
- No 500 x 500 renders; use 16 x 16 windows. `/tmp` on this machine is a 5.5 GB tmpfs: delete scratch renders.
- Every judgment call, with reasons, goes in `.claude_mem/ARCH_LOG.md`.
- Run the full suite before each commit.

Report `git status` and the actual `git add` / `git commit` commands at the end of each step, and a final summary of
what passed, what is a finding, and what stayed open.
