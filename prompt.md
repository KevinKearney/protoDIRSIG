# Split the AUROR_ref work: keep the discovery log, write an actual tutorial notebook

`notebooks/tutorial_auror_scene.ipynb` (uncommitted) is a discovery log — it documents finding
and fixing the dirfm gaps (`NewAtmospherePlugin`, `BasicPlatform`, `SpiceEphemeris`), the
`scene_coverage.py` blind spot, and the version-comparison investigation, as that work
happened. That's valuable and should be kept, but it isn't what the other three notebooks are:
a tutorial someone reads to learn dirfm usage. Split it into two artifacts.

STEP 1 — Preserve the discovery log
`git mv notebooks/tutorial_auror_scene.ipynb notebooks/dev/auror_scene_buildup.ipynb` (create
`notebooks/dev/`). Don't edit its content — it's a record of what was actually found and
fixed, not something to retroactively clean up. Add a one-line note at the top of its first
markdown cell: this is a development/discovery log, not a tutorial; see
`notebooks/tutorial_auror_scene.ipynb` for the tutorial version and `FINDINGS.md` for the
dated entry.

STEP 2 — Factor the now-working mechanisms into reusable helpers, not inline notebook code
Three things were built ad hoc in the discovery notebook to work around real dirfm gaps. They
should become proper, importable pieces of `src/protodirsig/`, the same way the Tacoma
notebook's `_fname` pattern became `scene_ref.py` and the coverage check became
`scene_coverage.py` — not re-pasted into the new notebook as inline subclass definitions.

- The `NewAtmospherePlugin`/`ModtranTapeBackend` fix (pre-declaring the frozen attributes
  `__init__` never creates, correcting the `"Isacc"`/`"Isaac"` typo) — this is a real dirfm bug
  with nothing AUROR-specific about it. Put the corrected subclasses somewhere reusable (e.g.
  `src/protodirsig/atmosphere_patches.py`), with a one-line comment pointing at the FINDINGS.md
  entry and the fix dirfm itself should eventually apply upstream.
- The file-referencing `PlatformSensorPlugin` subclass (no attachments, no-op `prepare()`, its
  own `get_plugin_inputs()` pointing at existing platform/motion/tasks files) is the same
  reference-an-existing-file need that `scene_ref.py` already solves for scenes. Generalize it
  there or alongside it (your judgment on the cleanest shape) rather than keeping it
  AUROR-specific, since any future received run tree will hit the same `PlatformSensorPlugin`
  gap.
- The bare `SpiceEphemeris` subclass (empty inputs) is small enough it may not need its own
  module — use judgment; if it's one two-line class, a shared `src/protodirsig/ephemeris.py`
  is fine too.

Write a short test for the atmosphere patch (construct it, call the setters, confirm
`get_plugin_inputs()` emits the expected stanza) following the existing test conventions. The
platform/ephemeris pieces don't need new tests beyond what the tutorial notebook itself
exercises by using them.

STEP 3 — Write the actual tutorial: `notebooks/tutorial_auror_scene.ipynb` (new file, same
path the discovery log used to occupy)

This notebook's job is for someone to read it and understand how to drive AUROR_ref's
configuration through dirfm — not to document the debugging process that got here. Match the
other three tutorials' structure (title, short per-stage markdown, code, output) but keep the
markdown transactional: state what each cell does and why it's the right call for this scene,
not how it was discovered or what else was tried. No "this didn't work, so" narrative, no
investigation log, no quantitative version-comparison section — that's the discovery
notebook's job now.

Minimum content:
- One-paragraph intro: what AUROR_ref is (a received static-pose detection scene with an
  embedded vehicle target), what this notebook builds (the dirfm job that reproduces it) and
  runs on this install.
- Reference the scene via `_fname` (reuse `scene_ref.py` directly, as Tacoma's notebook does).
- Reference the platform/motion/tasks files via the new reusable helper from Step 2 — one or
  two lines, not a rederivation of why `PlatformSensorPlugin` doesn't fit.
- Build the `NewAtmosphere` plugin via the Step 2 helper, with the one-line comment that the
  atmosphere database's site doesn't match Tahoe's (this is a received-input fact worth a
  reader knowing, not a discovery to narrate).
- Reference the weather file via `ThermWeatherFilePlugin`.
- Assemble, run (fresh `scene2hdf` compile against this install, fingerprint-guarded the same
  way as the Tacoma notebook), and display the result: load `AurorNIROutput.img`/`truth1.img`
  as ENVI arrays and show the rendered image and the truth/geolocation output, the way a reader
  would actually look at what the sensor produced.
- One short markdown note, near the display: the embedded vehicle target does not appear in
  this render (see `FINDINGS.md`'s dated entry for the investigation) — state the fact plainly
  for a reader who will otherwise wonder why the image looks like bare terrain, without
  re-running the investigation here.

Do not reproduce in this notebook: the dirfm-gap debugging narrative, the AttributeError/typo
diagnosis, the coverage-helper investigation, or the cross-version quantitative comparison —
all of that stays in `notebooks/dev/auror_scene_buildup.ipynb` and `FINDINGS.md`.

CONSTRAINTS
- Never write into the DIRSIG install directory or the dirfm checkout.
- Don't modify or overwrite anything under `AUROR_ref/`.
- Reuse `src/protodirsig/scene_ref.py` and `scene_coverage.py` as they stand; extend them only
  per Step 2.
- `scene_coverage.py`'s existing bundle-material fix and its tests are correct as committed in
  the discovery work — no changes needed there beyond what Step 2 asks.

Report git status and the actual `git add`/`git commit`/`git mv` commands when done — note the
rename needs `git add` on both the old and new paths (or let `git add -A` pick it up) for git
to record it as a rename rather than a delete+add.
