# contracts/

Machine-readable contracts: JSON Schemas for `run-spec/1`, `sensor-spec/1`, and `dirsig-engine/1`, the
governed vocabulary, test vectors, and validators. Empty today. The checks live in
`src/protodirsig/simulation.py` (`schema_errors`) and move here as schemas when they are written.

Future MANIFOLD home: the `manifold-contracts` repository, versioned by immutable git tag. Where a schema
file and a field table disagree, the schema wins.
