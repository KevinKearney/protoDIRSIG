# manifold_run_specs/

Run specs, authored as layers and composed into the single `run-spec/1` document MANIFOLD receives
(CONOPS and Guide §3.5, rules `compose/1`).

| Path | Holds |
|---|---|
| `recipes/<name>.yaml` | a run: `meta`, `settings`, `fidelity`, and the names of its sensor, scenario and engine profile |
| `scenarios/<name>.yaml` | `descriptor.collection` |
| `engine_profiles/<name>.yaml` | `descriptor.origin`, `descriptor.extras` and the `dirsig-engine/1` block for one scenario |
| `<name>.yaml` | the composed run spec for `recipes/<name>.yaml`; generated, tracked, do not edit |

The sensor is a file in `manifold_sensors/`, named by the recipe and never copied. A new sensor is a new library
file and a new recipe; a new engine is a new engine profile. Each member of the composed spec comes from exactly
one layer: a member in two layers is an error.

```bash
python scripts/compose.py                                   # write every <name>.yaml from its recipe
python scripts/compose.py --check                           # fail if a generated file is stale
python scripts/compose.py --explain manifold_run_specs/recipes/auror_ref.yaml   # member -> layer file, hash
python scripts/stamp_hashes.py                              # after editing a layer or sensor file, then compose
```

`LocalRegistry().submit_recipe(recipe, config_repo)` composes and submits in one call. The source comments for
every engine and collection value are in the layer files; the generated files carry none.
