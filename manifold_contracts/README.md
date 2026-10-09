# manifold_contracts/

Machine-readable contracts: JSON Schemas for `run-spec/1`, `sensor-spec/1`, and `dirsig-engine/1`, the
governed vocabulary, test vectors, and validators. Today: `sensor-spec-1.schema.json` (proposed; validated in `tests/test_sensor_library.py`). The other checks live in
`src/protodirsig/simulation.py` (`schema_errors`) and move here as schemas when they are written.

`vectors/compose/<case>/` are conformance vectors for a run-spec input constructor (rules `compose/1`, CONOPS and
Guide §3.5 and C-21). Each case holds layer files (`recipes/`, `scenarios/`, `engine_profiles/`) and either
`expected.yaml` (the composed run spec, sensor by ref), `expected_inline.yaml` (sensor inline), or
`expected_error.yaml` (`layer` and `field` the error must name). `vectors/compose/manifold_sensors/` is the cases'
sensor library. `tests/test_compose.py` runs every case against `protodirsig.compose`; another constructor passes
by producing the same specs and the same error locations.

Future MANIFOLD home: the `manifold-contracts` repository, versioned by immutable git tag. Where a schema
file and a field table disagree, the schema wins.
