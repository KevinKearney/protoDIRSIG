# manifold_sensors/

The sensor library: one `sensor-spec/1` document per sensor system.

| File | Sensor |
|---|---|
| `auror-nir.yaml` | AUROR NIR; reproduces the received platform |
| `deepscan_850_306_nir_1280.yaml` | 1280-pixel NIR |
| `synthetic_600_200_vis_1920.yaml` | 1920-pixel VIS |

A recipe names a file here (`sensor: auror-nir.yaml`, `manifold_run_specs/recipes/`); the composed run spec refers to it
by name and hash, `descriptor.sensor.ref`, or carries its `sensor` block inline, and the name resolves against this
folder. Files here are never copied into a run spec's layers. `platform_gen` renders the DIRSIG `.platform` from the entry and the run spec's
`settings`. CONOPS and Guide §4.

`spectral/` holds the QE, optics and filter curves entries reference (`spectral-curve/1`; see its README).
Schema: `manifold_contracts/sensor-spec-1.schema.json`. `content_hash` values are stamped and checked with
`python scripts/stamp_hashes.py [--check]`; run it after editing any file here.

Future MANIFOLD home: a library of validated sensor profiles, versioned apart from run specs.
