"""Library listing and reading (protodirsig.library.LibraryReader) over the repository library and temporary copies."""
import shutil
from pathlib import Path

import pytest
import yaml

from api_schema import errors as schema_errors
from protodirsig.errors import AdmissionError, InvalidRequestError, NotFoundError
from protodirsig.library import KINDS, LibraryReader
from protodirsig.spectral import sha256_file

ROOT = Path(__file__).resolve().parents[1]
RUN_SPECS = ROOT / "manifold_run_specs"
FOLDERS = {"sensor": ROOT / "manifold_sensors", "scenario": RUN_SPECS / "scenarios",
           "engine_profile": RUN_SPECS / "engine_profiles", "recipe": RUN_SPECS / "recipes"}
reader = LibraryReader()


@pytest.mark.parametrize("kind", KINDS)
def test_every_file_is_listed_with_its_digest(kind):
    listed = reader.list(kind)
    files = sorted(FOLDERS[kind].glob("*.yaml"))
    want = sorted(({"name": p.name if kind == "sensor" else p.stem, "sha256": sha256_file(p).removeprefix("sha256:")}
                   for p in files), key=lambda r: r["name"])
    assert listed == want and listed
    assert schema_errors("library_list", {"items": listed}) == []


@pytest.mark.parametrize("kind", KINDS)
def test_get_round_trips_every_resource(kind):
    for item in reader.list(kind):
        doc = reader.get(kind, item["name"])
        path = FOLDERS[kind] / (item["name"] if kind == "sensor" else f"{item['name']}.yaml")
        assert doc == {"name": item["name"], "sha256": item["sha256"], "document": yaml.safe_load(path.read_text())}
        assert schema_errors("sensor_document" if kind == "sensor" else "library_document", doc) == []


def test_a_sensor_is_found_by_its_stem_too():
    assert reader.get("sensor", "auror-nir") == reader.get("sensor", "auror-nir.yaml")


@pytest.mark.parametrize("kind, name", [("recipe", "no_such_recipe"), ("sensor", "no_such.yaml"),
                                        ("scenario", "../recipes/auror_ref"), ("engine_profile", "")])
def test_a_missing_name_is_not_found(kind, name):
    with pytest.raises(NotFoundError) as e:
        reader.get(kind, name)
    assert schema_errors("problem", e.value.problem) == [] and e.value.status == 404


def test_an_unknown_kind_is_an_invalid_request():
    with pytest.raises(InvalidRequestError):
        reader.list("platform")


@pytest.fixture
def copy(tmp_path):
    root = tmp_path / "manifold_run_specs"
    for d in ("recipes", "scenarios", "engine_profiles"):
        shutil.copytree(RUN_SPECS / d, root / d)
    shutil.copytree(ROOT / "manifold_sensors", tmp_path / "manifold_sensors")
    return LibraryReader(root)


def _write(path, text):
    path.write_text(text)
    return path


@pytest.mark.parametrize("kind, file, text, layer, field", [
    ("recipe", "recipes/broken.yaml", "compose: [unclosed\n", "recipes/broken.yaml", None),
    ("recipe", "recipes/noscen.yaml", "compose: compose/1\nmeta: {name: x}\nsensor: auror-nir.yaml\n"
     "engine_profile: tahoe_static_pose\nsettings: []\nfidelity: {}\n", "recipes/noscen.yaml", "scenario"),
    ("scenario", "scenarios/extra.yaml", "collection: {}\nengine: {}\n", "scenarios/extra.yaml", "engine"),
    ("engine_profile", "engine_profiles/half.yaml", "origin: {kind: synthetic, engine: dirsig}\n",
     "engine_profiles/half.yaml", "engine"),
    ("scenario", "scenarios/list.yaml", "- not a mapping\n", "scenarios/list.yaml", None),
])
def test_a_malformed_layer_names_the_file(copy, kind, file, text, layer, field):
    _write(copy.root / file, text)
    with pytest.raises(AdmissionError) as e:
        copy.get(kind, Path(file).stem)
    p = e.value.problem
    assert (p["layer"], p["field"]) == (layer, field) and schema_errors("problem", p) == []


def test_a_sensor_that_is_not_sensor_spec_names_the_file_and_key(copy):
    doc = yaml.safe_load((copy.sensor_library / "auror-nir.yaml").read_text())
    doc["sensor"]["bogus"] = 1
    _write(copy.sensor_library / "bad.yaml", yaml.safe_dump(doc))
    with pytest.raises(AdmissionError) as e:
        copy.get("sensor", "bad.yaml")
    assert (e.value.problem["layer"], e.value.problem["field"]) == ("manifold_sensors/bad.yaml", "sensor")
