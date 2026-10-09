"""Every sensors/*.yaml is a sensor-spec/1 document with a detector block that carries the fixed
properties. The modeled window (roi) is a run-spec setting and is absent from the library."""
from pathlib import Path

import pytest
import yaml

SENSORS = Path(__file__).resolve().parents[1] / "sensors"
FILES = sorted(SENSORS.glob("*.yaml"))
DETECTOR_KEYS = {"DeviceVendorName", "DeviceModelName", "SensorWidth", "SensorHeight", "SensorPixelWidth",
                 "SensorPixelHeight", "fill_factor", "channel_layout"}


def test_library_is_not_empty():
    assert {f.stem for f in FILES} >= {"auror-nir", "deepscan_850_306_nir_1280"}


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_entry_shape(path):
    doc = yaml.safe_load(path.read_text())
    assert doc["spec_version"] == "sensor-spec/1"
    assert doc["meta"]["name"] == path.stem
    for entry in doc["sensor"]["entries"]:
        for fp in entry["focal_planes"]:
            det = fp["detector"]
            assert set(det) == DETECTOR_KEYS and not {"roi", "array"} & set(fp)
