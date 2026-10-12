"""The SatSim engine (`satsim`, `satsim-engine/1`, pass-through only, `proposed`): an adapter that drives a SatSim the
user installed in its own interpreter. Nothing here imports `satsim`, `tensorflow` or `numpy`; they are imported only by
`launcher.py`, which runs in SatSim's interpreter. SatSim is driven, never bundled."""
