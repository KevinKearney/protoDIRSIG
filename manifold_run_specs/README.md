# manifold_run_specs/

Run specs, authored as layers and composed into the single `run-spec/1` document MANIFOLD receives
(CONOPS and Guide §3.5, rules `compose/1`).

| Path | Holds |
|---|---|
| `recipes/<name>.yaml` | a run, or a sweep: `meta`, `settings`, `fidelity`, and the names of its sensor (or `sensors`), scenario and engine profile |
| `scenarios/<name>.yaml` | `descriptor.collection` |
| `engine_profiles/<name>.yaml` | `descriptor.origin`, `descriptor.extras` and the `dirsig-engine/1` block for one scenario |
| `<name>.yaml` | the composed run spec for a one-run `recipes/<name>.yaml`; generated, tracked, do not edit |
| `<name>--<sensor>.yaml` | one composed run spec per sensor of a sweep recipe; generated, tracked, do not edit |

The sensor is a file in `manifold_sensors/`, named by the recipe and never copied. A new sensor is a new library
file and a new recipe (or a new entry in a sweep's `sensors`); a new engine is a new engine profile. Each member of
the composed spec comes from exactly one layer: a member in two layers is an error. A recipe may set an allowed
engine path with `engine_overrides` (today only `platform.channel_response`; `recipes/auror_ref.yaml` sets
`native`).

**Sweeps.** `sensors: [<file>, ...]` instead of `sensor:` makes one run per listed sensor, sharing the scenario,
engine profile and seed. `settings` is keyed by `entry_id` across the listed sensors, and each run takes its
sensor's members. Run names are `<meta.name>--<sensor file stem>`; `fidelity_by_sensor: {<file>: {...}}` gives a
run its own fidelity. At most 32 runs. The sweep id is the first 12 hex digits of the recipe file's sha256; it is
printed by `--explain` and never written into a run spec. `recipes/sensor_sweep_tahoe.yaml` is the example: the
three library sensors, 32 x 32 windows.

```bash
python scripts/compose.py                                   # write every <name>.yaml from its recipe
python scripts/compose.py --check                           # fail if a generated file is stale
python scripts/compose.py --explain manifold_run_specs/recipes/sensor_sweep_tahoe.yaml   # sweep id; per run: member -> layer, hash
python scripts/compose.py --refresh-vectors                 # rewrite the equivalence vectors after editing their layers
python scripts/stamp_hashes.py                              # after editing a layer or sensor file, then compose
```

`LocalRegistry().submit_recipe(recipe, config_repo)` composes and submits one run; `submit_sweep(recipe, config_repo)`
submits every run of a sweep and `run_sweep(...)` renders the accepted ones, each run with its own state. The source comments for
every engine and collection value are in the layer files; the generated files carry none.
