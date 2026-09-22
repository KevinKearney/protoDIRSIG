Build an incremental, heavily-commented Jupyter notebook that tutorials the DIRFM library (a Python wrapper that generates DIRSIG input files and drives DIRSIG runs). Target audience: an engineer who knows Python but has never touched DIRSIG or DIRFM.

ENVIRONMENT
- DIRFM source/repo: /home/kevin-kearney/dev/dirsig-file-maker (package importable as `dirfm`; core objects re-exported from dirfm/__init__.py: JSIM, DIRSIG, TASKS, SCENE, plus submodules dirfm.atmosphere, dirfm.materials, dirfm.platform_sensor, dirfm.platform_motion, dirfm.object_database, dirfm.glist, dirfm.frames).
- DIRSIG binaries: /home/kevin-kearney/DIRSIG/dirsig-2026.38.0.a020954-Linux-x86_64/bin (must contain scene2hdf and dirsig5 on PATH for DIRSIG.run() to work — set this via os.environ["PATH"] in the first notebook cell, don't assume the kernel's shell already has it).
- Write the notebook to demos/tutorial_dirfm_basics.ipynb inside the dirfm repo. Use demos/tutorial_<n>_output and demos/tutorial_<n>_input as the in_root/out_root DIRSIG(...) directories for each stage, mirroring the convention in demos/test_PrimitiveObjects1.py.
- Reference demos/test_PrimitiveObjects1.py as the canonical minimal working example — read it before writing anything, and don't invent API surface not present in the dirfm source. If a needed class/method isn't obvious from the demos, grep the dirfm package (materials.py, object_database.py, platform_sensor.py, atmosphere.py, platform_motion.py, scene.py, dirsig.py) rather than guessing.

STRUCTURE — one stage per section, each section = markdown cell(s) explaining the concept and why it's needed, then a code cell that runs and renders/inspects output before moving to the next stage. Do not front-load explanation of features not yet used. Each stage's code cell should execute successfully (run scene2hdf + dirsig5) before the next stage is written — verify by actually executing the notebook top to bottom, not by inspection alone.

Stage 0 — Orientation: what DIRSIG is, what DIRFM automates (the file-generation problem DIRFM solves — no manual XML/JSON), the object model at a glance (SCENE holds materials+geometry, DIRSIG holds scenes+plugins+mediums, plugins are the platform/atmosphere, everything gets compiled by write_files()/run() into a .jsim + .scene + supporting files, then scene2hdf and dirsig5 are shelled out to). Set PATH, confirm shutil.which("scene2hdf") and shutil.which("dirsig5") both resolve.

Stage 1 — Absolute minimum render: one Material (simple Lambertian via a WardBrdfSurfaceProperty + GenericRadiationSolver, following the pattern in test_PrimitiveObjects1.py's create_materials), one ObjectDatabase primitive (a single GroundPlane or Sphere), one SCENE with a GeodeticFrame origin and set_properties("vis"), the minimal PlatformSensorPlugin tree required to get an image out (StaticMount → GenericInstrument with FocalLengthInstrumentProperty → FocalPlane with BasicCaptureMethod/SpectralResponse/one FunctionalChannel → DetectorArray with IndependentDetectorClock), a PlatformPosition motion with one fixed entry, a TASKS with one start/stop pair, and a minimal BasicAtmospherePlugin with SimpleRadiativeTransfer. Assemble on a DIRSIG(in_root, out_root), add_scene/add_plugin, call .run(), open the resulting .img.hdr with the `spectral` package and display it inline (matplotlib imshow), explaining each object's role in a markdown cell directly above the code that creates it.

Stage 2 — More geometry and materials: add a second and third material with different reflectances, add multiple ObjectDatabase primitives (Sphere, Box, Cylinder, Disk) to the same scene, explain how material objects are passed directly to primitives rather than referenced by ID string.

Stage 3 — Sensor realism: widen the spectral band, add a second FunctionalChannel (multi-band capture), increase DetectorArray element count, explain FocalPlane/CaptureMethod/DetectorArray relationships and how they map to the rendered image's channel count.

Stage 4 — Platform motion and timing: switch from a single fixed PlatformPosition entry to a short multi-entry trajectory (or introduce FlexMotion with a StraightLocationEngine/LookAtOrientationEngine if that fits more naturally), and a TASKS window that spans that trajectory, explaining relative vs. absolute datetime handling.

Stage 5 — Atmosphere fidelity: swap SimpleRadiativeTransfer for UniformRadiativeTransfer or ClassicRadiativeTransfer, or introduce a weather file path, explaining what changes physically in the render.

Stage 6 — Mesh-based geometry via GLIST: replace or augment the primitives with a Wavefront (.obj) instance from demos/geometry, explaining GLIST vs ObjectDatabase (instancing vs. procedural primitives) and StaticInstance placement/orientation.

Stage 7 — Wrap-up: multi-scene composition with add_scene offsets, or Bundle usage for reusable assets — pick whichever is more illustrative given what demos/bundles/* already contains — and a closing markdown cell summarizing the full object graph built across the notebook (a short ASCII or prose diagram of DIRSIG → scenes/plugins/mediums → their sub-objects).

CONSTRAINTS
- Markdown cells should be dense with the "why," not just restate the code — explain what each DIRFM class corresponds to in DIRSIG's file format (e.g., "this becomes the <matfilename> element in the .scene XML") where it clarifies the mapping.
- Every code cell must actually run in this environment before you move to the next stage — don't write stages 2–7 speculatively without executing stage 1's output first.
- Keep each stage additive: reuse/extend the previous stage's objects rather than rewriting from scratch, so the diff between stages is visible.
- After the notebook runs end to end, tell me the git status of the dirfm repo and give me the actual `git add`/`git commit` commands to save it — don't just describe the action, and don't ask me to run intermediate commits per stage since this is prototype/tutorial work.
