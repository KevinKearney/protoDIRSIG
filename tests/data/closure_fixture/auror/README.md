# The Auror walker fixture (Cfg A.3)

`tests/test_closure_fixture.py` assembles the Auror tree in a temporary folder from the files here and from the engine-asset library, then walks it with `manifold.engines.dirsig.closure.walk`.

| File here | Source |
|---|---|
| `AurorSimulation_held.jsim` | the held `notebooks/dev/AUROR_ref/jsims/AurorSimulation.jsim` (gitignored), byte for byte: five absolute Windows paths `C:/DIRSIG/AUROR/Kevin_DIRSIG/...` |
| `Auror.jsim` | the same file with the prefix `C:/DIRSIG/AUROR/Kevin_DIRSIG/` removed and the scene named `scenes/tahoe/tahoe.scene` (Cfg A.3's fourth row, "rewrite to tree-relative paths"); nothing else changed |
| `atmospheres/test.atm` | the held `notebooks/dev/AURORA_ref_to_delete/atmospheres/test.atm`, byte for byte: weather `/home/rxp7504/DIRSIG/MDA/Tahoe_hypersonic/weather/saw.wth` |
| `tasks/AurorTask.tasks`, `motion/AurorMotion.ppd` | the held `notebooks/dev/AUROR_ref/` files, byte for byte |

From the library (`manifold_config_repo/`, byte-identical to the held `AUROR_ref` copies): `scenes/tahoe/` (scene, geometry, materials), `platforms/AurorNIRDetector/AurorNIRDetector.platform` (placed at `platforms/AurorNIRDetector.platform`), `weather/saw.wth` and `atmosphere/AurorNewAtmosphere` (placed beside the `.jsim`, which names it bare).

What the held trees reproduce of Cfg A.3:

- **Absolute map paths in `tahoe.scene`: not reproduced.** The held `tahoe.scene` (identical to the library's) names its two maps by relative names, `material_map_small.pgm` and `texture_map_small.pgm`, against `<mapdirectory>$SCENE_DIR/maps</mapdirectory>`, and both maps are `enabled="false"`. The fixture writes A.3's path, `/Users/eoptic/Documents/DIRSIG/scenes/tahoe/maps/<name>`, into the two `<filename>` elements of its copy; the corrected tree writes `$SCENE_DIR/maps/<name>`.
- **Absolute weather path in `atmospheres/test.atm`: reproduced**, from the held `AURORA_ref_to_delete` tree (the held `AUROR_ref` tree has no `atmospheres/` folder).
- **`test.atm` orphaned: reproduced.** No held `.jsim` names it.
- **Absolute Windows paths in the simulation file (A.3's fourth row): reproduced** by `AurorSimulation_held.jsim`.
- The held entry is `jsims/AurorSimulation.jsim`, with `AurorNewAtmosphere` beside it and every other file one folder up. DIRSIG resolves a `.jsim`'s relative names against the folder it runs in (Cfg A.6), so that layout cannot be written relative without a `..` segment, which Cfg 2.3 rejects; the fixture places the entry at the root, as Cfg 2.1's example does (`Auror.jsim`).
