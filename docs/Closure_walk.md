# The DIRSIG role list, closure walker and closure test on real trees (rounds 46 and 47)

Evidence gathered before the requirements baseline, not the SDK's implementation. The origin admission contract requires a role list and a closure walker for each origin (configuration view `AV_MANIFOLD_Configuration_v02.md`, sections 2.4, 4.1 and 7, Appendix A.2 to A.4). The prototype had neither, only the partial walker in `scene_ref` that finds the files DIRSIG looks for in the working folder. This round builds both for DIRSIG, beside the existing engine modules, and runs them over every tree the repository can build without rendering. `packages/core` is unchanged.

| Piece | Where | Evidence |
|---|---|---|
| Role list (Cfg A.2) as data, with read classes (Cfg 6.2) | `packages/engine-dirsig/src/manifold/engines/dirsig/roles.py` | `tests/test_dirsig_roles.py` |
| Closure walker | `packages/engine-dirsig/src/manifold/engines/dirsig/closure.py` | `tests/test_closure_walk.py` |
| Auror walker fixture (Cfg A.3) | `tests/data/closure_fixture/auror/` | `tests/test_closure_fixture.py` |
| Corpus walk | `scripts/closure_walk.py`, `docs/data/closure_walk.jsonl` | `tests/test_closure_walk_corpus.py` |
| Closure test (round 47, section 6) | `packages/engine-dirsig/src/manifold/engines/dirsig/closure_trace.py`, `scripts/closure_trace.py` | `tests/test_closure_trace.py` |

## 1. The role list

`roles.ROLES` holds Cfg A.2's nineteen roles, namespaced `dirsig:`, each with its read class: the eight parameter roles Cfg 6.2 names (`sim`, `tasks`, `motion`, `platform`, `platform_input`, `weather`, `atmosphere`, `instance_motion`) and eleven asset roles. `roles.REFERENCES` assigns a role from the element that references a file, as `(referrer, field)`: a `.ppd` named by `BasicPlatform`'s `motion_filename` is `dirsig:motion`, a `.ppd` named in a geometry list's `<dynamicinstance>` is `dirsig:instance_motion`, and no entry of the table names an extension.

`roles.UNROLED` lists the referenced fields the table leaves without a role, each with its reason. They are judgments against A.2's wording:

- `REFLECTANCE_PROP` `BRDF_FIT_FILE` and `PARAMETER_FILE`. A BRDF model fit is not a "reflectance, transmittance or emissivity curve", which is the scope A.2 gives `dirsig:other_input`.
- `TEMP_SOLVER` `FILENAME` (a temperature table), `SOURCE_SHAPE` (a light-source shape) and `BUNDLE_FILENAME` (a compiled material bundle). No role names these.
- An `.atm`'s `modtrantape5file`. `dirsig:atmosphere_db` names the built database, not the MODTRAN card.

Core's two artifact-role constants differ in one member. `manifold.core.artifacts.ROLES` (six) holds `preview` and `manifold.core.engine.ROLES` (five) does not. Both constants name a run's outputs, while this list names its inputs, so it follows neither and follows Cfg A.2 instead. The engine package's output side (`adapter.PASSTHROUGH_ROLES`) emits `preview`, so it follows `artifacts.ROLES`. Neither constant was edited.

## 2. The walker

`closure.walk(root, entry)` starts at the simulation file, which may be a `.jsim` (JSON) or a legacy `.sim` (XML). It follows every reference:

- the `.jsim`'s plugin inputs and scene list;
- the `.sim`'s `externalfile` elements;
- an `.atm`'s weather and database;
- a `.platform`'s `<filename>`s;
- a `.scene`'s geometry lists, material file and maps;
- a geometry list's `glist`, `basegeometry`, `localmaterials` and `<dynamicinstance>` file names;
- a material file's `BLOCK.KEY` entries whose key ends in `FILE`, `FILENAME` or `SHAPE`.

It returns each reached file with its role and its path relative to the tree root.

Every violation of Cfg 2.3's path rules is reported, not normalized. The kinds are `absolute` (a drive letter counts), `dotdot`, `non_nfc`, `symlink`, `outside_root`, `form` (a backslash, an empty or `.` segment, a control character) and `variable`. An absolute or escaping reference is reported and not followed.

The walker also reports:

- unresolved references (Cfg A.4 `E_UNRESOLVED`);
- references into the installation, `$DIRSIG_HOME/...`. These lie outside the tree, are covered by the engine data hash (Cfg A.6), and are not violations;
- orphans (Cfg A.4 `W_ORPHAN`);
- a path reached under two roles;
- files no role covers.

Rules and assumptions:

- **Disabled elements.** An element with `enabled="false"` is not followed (Cfg A.2), but its text is checked and its violations are reported with `enabled: false`, because the text is in a hashed file. This is how A.3's map defect is reported: Cfg A.2 says the walker does not walk those maps, while A.3 says it must report their paths.
- **Orphans.** An orphan that parses as a file the walker reads, judged by its root element, is scanned for violations and not followed. This is how A.3's `test.atm` weather path is reported.
- **Compiled scenes.** A `.scene.hdf` reference stands for its `.scene`, because the compiled scene is not in the manifest (Cfg A.2).
- **Symbolic links.** The walker reports the link and reads through it to continue the walk. The manifest path keeps the link's name; nothing is replaced by the link's target and nothing is copied. It lists the files behind a crossed link that no reference reached.
- **Search order.** The walker searches the folders in an order that is measured only for the entry (the folder DIRSIG runs in, Cfg A.6) and for a scene's geometry lists (`gdbdirectory`, then the working folder, from `scene_ref`'s measured rule). For other references the order is the walker's assumption, written in `closure.py`'s docstring. Checking it is the job of the closure test (Cfg A.5), which this round does not run.
- **Unmodelled references.** Any other leaf text, `externalfile` or plugin string that resolves to a file is followed with no role, so an unmodelled reference shows up as an unroled file instead of being lost.
- **Reuse of `scene_ref`.** The walker reuses `scene_ref`'s material-file reader (`_material_entries`), its descriptive subtrees (`SKIPPED`) and its per-key search folders (`MATERIAL_UNHELD_KEYS`, `MATERIAL_SEARCHED_KEYS`).

## 3. The Auror fixture (Cfg A.3)

The fixture tree is assembled from `tests/data/closure_fixture/auror/` and the engine-asset library; its README gives the source of each file. The held trees are `notebooks/dev/AUROR_ref` and `notebooks/dev/AURORA_ref_to_delete`, both gitignored; the library's `scenes/tahoe/`, platform, weather and atmosphere database are byte-identical to the `AUROR_ref` copies.

| A.3 defect | Held tree | Walker |
|---|---|---|
| Absolute map paths `/Users/eoptic/...` in `tahoe.scene` | **Not reproduced.** The held `tahoe.scene` names both maps by relative names against `<mapdirectory>$SCENE_DIR/maps</mapdirectory>`, and both maps are `enabled="false"`. The fixture writes A.3's path into its copy. | Reported: two `absolute` reports from the disabled `materialmap` and `texturemap`, not followed |
| Absolute weather path `/home/rxp7504/...` in `atmospheres/test.atm` | Reproduced, byte for byte, from `AURORA_ref_to_delete` (`AUROR_ref` has no `atmospheres/` folder) | Reported from the orphan scan (`orphan: true`) |
| `test.atm` not referenced by the simulation file | Reproduced: no held `.jsim` names it | Reported: the only orphan |
| Absolute Windows paths `C:/DIRSIG/AUROR/Kevin_DIRSIG/...` in the simulation file (A.3's fourth row) | Reproduced by the held `AurorSimulation.jsim` | Five `absolute` reports (platform, motion, tasks, weather, scene), not followed |

The defective tree reports exactly the three defects. It reaches 25 files, and their roles equal Cfg A.2's Auror mapping: one each of `sim`, `tasks`, `motion`, `platform`, `weather`, `atmosphere_db` and `scene`; three `geometry_list`s, two `geometry_object`s, two `material_db`s, ten `emissivity` files and one `other_input`. The corrected tree passes clean with the same 25 files. Its maps are written `$SCENE_DIR/maps/...` and `test.atm` is deleted.

One more finding about the held layout. The held entry is `jsims/AurorSimulation.jsim`, with `AurorNewAtmosphere` beside it and every other file one folder up. DIRSIG resolves a `.jsim`'s names against the folder it runs in, so this layout cannot be written relative without `../`, which Cfg 2.3 rejects (`test_the_held_layout_needs_a_dotdot_segment`). The fixture places the entry at the root, as Cfg 2.1's example does.

## 4. The corpus

The corpus is every committed run spec under `manifold_run_specs/` (top level and `s2s/`) whose engine is `dirsig`, resolved to its job tree without rendering:

- **Layered.** The job's `input/` folder as `Simulation._assemble` builds it, with the `.jsim` that dirfm writes. Neither `scene2hdf` nor `dirsig5` is run.
- **Pass-through.** The demo directory copied the way `passthrough.run_engine` copies it.

The tree root is the folder DIRSIG runs in. Run with `python scripts/closure_walk.py --work DIR`; the table below is generated from `docs/data/closure_walk.jsonl` (`--table` prints it).

<!-- closure-walk-table -->
| Quantity | Value |
|---|---|
| DIRSIG run specs committed | 162 |
| trees built and walked (layered / pass-through) | 161 (159 / 2) |
| trees not built | 1 |
| walked clean (no violation, unresolved reference, unroled file, role conflict or orphan) | 0 |
| passed (as clean, orphans allowed) | 1 |
| reported a path violation | 159 |
|   of which `absolute` | 0 trees, 0 reports |
|   of which `dotdot` | 0 trees, 0 reports |
|   of which `non_nfc` | 0 trees, 0 reports |
|   of which `symlink` | 159 trees, 4183 reports |
|   of which `outside_root` | 0 trees, 0 reports |
|   of which `form` | 0 trees, 0 reports |
|   of which `variable` | 0 trees, 0 reports |
|   distinct links crossed per layered tree | 2 |
|   files behind a crossed link that no reference reached (sum over trees) | 0 |
|   trees whose only error is the links | 159 |
| reported an unresolved reference | 0 |
| referenced the DIRSIG installation (`$DIRSIG_HOME`) | 155 |
| reported an orphan | 2 |
| reported a role conflict | 0 |
| reached a file the existing `scene_ref` rules did not | 160 trees, 3082 files |
| named by the existing rules but not reached | 0 trees, 0 files |
| **files reached that no role covers** | **4 in 1 trees; 4 distinct tree paths** |
|   by field `REFLECTANCE_PROP.BRDF_FIT_FILE` | 3 |
|   by field `modtrantape5file` | 1 |
<!-- /closure-walk-table -->

What the numbers say:

- **Files no role covers: 4, all in one tree.** This is the number that matters, because an unroled file cannot enter a manifest. All four are in the Brdf1 pass-through tree: three BRDF fit files (`materials/brdf/*.fit`, from `REFLECTANCE_PROP` `BRDF_FIT_FILE`) and the MODTRAN card `mls_ms.tp5` (from `classic_mls.atm`'s `modtrantape5file`). The 159 layered trees have none. If MANIFOLD reads `dirsig:other_input` as covering a BRDF fit, the count drops to one. Whether DIRSIG reads the tape5 at all when an `adbfile` is given is for the closure test to show.
- **Links: every layered tree.** Each of the 159 layered trees crosses the two folders that the job links into the library, `auror_ref/geometry` and `auror_ref/materials`. That is 17 to 51 reports per tree and 4183 in total. For every one of these trees the links are the only error. Every file behind a link that the job names is reached (zero unreached), so here a link view and a copy view of a layered tree would list the same files. This report does not resolve the conflict: Cfg 2.3 rejects links, and which view of a tree is hashed is the program's decision. The pass-through trees hold no link; their resolver already refuses a directory that contains one.
- **No `absolute`, `dotdot`, `non_nfc`, `outside_root`, `form` or `variable` violation in the corpus.** The repository's trees are generated relative, so the defects of section 3 come from received trees.
- **The installation's weather: 155 trees.** These trees reach `$DIRSIG_HOME/lib/data/weather/mls.wth`, outside the tree. 153 layered trees name it from the `.atm` the job writes (`engine.atmosphere.uniform` or `.simple`) and both pass-through trees from the demo's `.atm`. Cfg A.6 has a row for installation weather named by `ThermWeather` (`weather.source: install`); these references come from an `.atm`'s `<classicdata>`, which A.6 does not name.
- **Orphans: the two pass-through trees.** Brdf1 has 9: READMEs, images, and the demo's other `.jsim`, `.sim`, `.ppd` and `.tasks`. PointCollectors2 has 8: images, `points.cpp`, `scans.plot` and three other `.jsim`s. A manifest excludes these with a warning, but the pass-through run's identity today (`dirhash/1` over the directory) covers them. The two identities would cover different file sets.
- **Beyond the existing rules: 160 trees, 3082 files.** This is expected. `scene_ref`'s rules find working-folder files and the files a `.scene` names beside it; they do not enumerate the folders a layered job links wholesale. The reverse count is zero: the walker reached every file the existing rules name.
- **Not built: one.** `manifold_run_specs/pointcollectors2_demo.yaml` (layered, `basic` atmosphere with a file) is refused by the loader (`RunSpecError`: `basic` is handled only with `uniform` or `simple`), so it has no job tree to walk.
- **Passed (orphans allowed): one.** PointCollectors2 as a pass-through tree. No tree walked clean.

## 5. Left for the program

- **Which view of a tree is hashed: the link view, a copy, or the library paths.** Every layered tree reports the two links; nothing was followed in place of the link, and nothing was copied.
- **Whether `dirsig:other_input` covers a BRDF fit file**, and whether a MODTRAN card is in a tree at all. Either answer changes the count of unroled files.
- **Installation weather reached through an `.atm`.** Cfg A.6 names only `ThermWeather`.
- **The pass-through form's orphans,** which `dirhash/1` covers and a manifest would not.
- **A.3's map defect against A.2's disabled-element rule.** The walker reports text in disabled elements without following it. Whether that text is an error (it is in a hashed file) or outside the closure is the program's decision.
- **The search orders the walker assumes,** which the closure test (Cfg A.5), materializing the walked files and starting DIRSIG, would check. That test was not run this round.

## 6. The closure test (round 47)

The walker reads a tree statically. The closure test checks it against a run: it runs the job end to end and records every file the engine opens. Configuration view section 4.2 and Appendix A.5 describe the test as starting DIRSIG on the materialized tree with the smallest unit of work. This test runs the whole job instead, at `--threads=2`, so it observes every read a real render makes.

### 6.1 The method

`scripts/closure_trace.py one SPEC --work DIR` builds the job the way a run builds it and starts the tools the way a run starts them:

- **Layered:** `Simulation.run`, which runs dirfm's `DIRSIG.run`. That starts `scene2hdf --threads <cpu count> <scene>` and then `dirsig5 example.jsim --threads=2 ...`, both in the job's `input/` folder.
- **Pass-through:** `passthrough.run_engine`, which runs `scene2hdf` in each scene's folder and `dirsig5` in the simulation file's folder.

The two tool names resolve to wrappers placed first on `PATH`. The first wrapper to start does two things before any tool has run:

- It walks the tree with `closure.walk`, from the folder DIRSIG runs in.
- It lists the tree's regular files with `closure_trace.job_files`. Links to folders are followed and the paths keep the link names.

Each wrapper then sets `HOME` to an empty folder and runs the real tool from the DIRSIG installation under `strace -ff -y -s 4096 --seccomp-bpf -e trace=open,openat,openat2`. The empty `HOME` follows Cfg A.6: the executor runs DIRSIG with an empty home, so no user plugin and no warm material cache is read. strace is installed on this host (6.19), so the third set is observed, not inferred.

`closure_trace.closure_sets` places each opened file in two steps:

1. **By the name the tool passed,** made absolute against the folder strace reports. A file under the tree root takes its root-relative name.
2. **Otherwise by the path the kernel opened.** A file under the library takes the tree path that resolves to it, or `library:<path>` when no tree path does.

Files under the installation, the empty home and the output folder are counted apart. System files are dropped. The sets compared are:

1. **Listed, not in the job:** walked paths the job does not contain.
2. **In the job, not listed:** the job's files the walker did not list.
3. **Read, in neither:** tree or library files a tool opened for reading that are neither walked nor in the job. Those that a tool of the same run opened for writing first are marked `generated`.

The test also reports **listed, never opened:** the walked paths no tool opened. Alongside the sets it records:

- the tree files the run wrote, and any library file opened for writing;
- the tree names a tool tried and did not find (`ENOENT`), which show the tool's search;
- the installation files opened, with the walker's `$DIRSIG_HOME` references checked against them.

What the trace does not see: a file whose existence a tool checks with `stat` but never opens, and a file read through a descriptor inherited from outside the traced tools. A file opened for both reading and writing is counted as written.

