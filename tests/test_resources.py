"""Typed resource slots (proposed; `manifold.core.resources`): parsing a run's requests, checking them against an
engine's declaration and a backend's capacity, allocating concurrent grants (GPUs exercised with stub capacities, no
hardware), the identity rule, and `LocalBackend`: a GPU request is refused at admission on a backend with none, admitted
on a stub backend that advertises GPUs, and a granted thread count reaches the engine."""
import json

import pytest
import yaml

from manifold.core import identity
from manifold.core.errors import AdmissionError
from manifold.core.resources import (Capacity, CpuThreads, GpuDevice, GpuSlot, Grant, ResourceDeclaration, allocate,
                                     check, identity_view, parse_request)
from test_passthrough import EXPECTED, library, layers, stub_engine  # noqa: F401  (fixtures)

DECL = ResourceDeclaration(cpu_threads=CpuThreads(1, 8, None, ("OMP_NUM_THREADS",)),
                           gpu=GpuSlot(maximum=2, device_class=None), network="optional")
GPUS = Capacity(cpu_threads=8, memory_bytes=16 << 30,
                gpus=(GpuDevice("0", "a100", 40 << 30), GpuDevice("1", "a100", 40 << 30), GpuDevice("2", "t4", 16 << 30)),
                network=False)
NONE = Capacity(cpu_threads=8, memory_bytes=16 << 30)


def test_parse_request():
    r = parse_request({"cpu_threads": 2, "memory_bytes": 1024, "gpu": {"count": 1, "device_class": "a100"}})
    assert (r.cpu_threads, r.memory_bytes, r.gpu.count, r.gpu.device_class, r.network) == (2, 1024, 1, "a100", "none")
    assert parse_request(None) == parse_request({})
    for bad in ({"cpu_threads": 0}, {"cpu_threads": 1.5}, {"gpu": 1}, {"network": "yes"}, {"threads": 2},
                {"assets": [{"ref": {}}]}):
        with pytest.raises(ValueError):
            parse_request(bad)


def test_check_against_the_declaration_and_the_capacity():
    assert check(parse_request({"cpu_threads": 4}), DECL, NONE) == []
    assert "runs with 1 to 8" in check(parse_request({"cpu_threads": 9}), DECL)[0]
    gpu = parse_request({"gpu": {"count": 1}})
    assert check(gpu, DECL) == []                                      # no capacity: the declaration only
    (problem,) = check(gpu, DECL, NONE)
    assert "advertises no matching GPU" in problem
    assert check(gpu, DECL, GPUS) == []
    assert "matching GPU" in check(parse_request({"gpu": {"count": 2, "device_class": "t4"}}), DECL, GPUS)[0]
    assert "at most 2" in check(parse_request({"gpu": {"count": 3}}), DECL, GPUS)[0]
    assert "allows no network" in check(parse_request({"network": "allow"}), DECL, GPUS)[0]
    no_net = ResourceDeclaration()
    assert "declares no network" in check(parse_request({"network": "allow"}), no_net)[0]


def test_allocation_of_gpus_threads_and_memory_with_a_stub_capacity():
    one = parse_request({"gpu": {"count": 1, "device_class": "a100"}, "cpu_threads": 4, "memory_bytes": 8 << 30})
    g1 = allocate(one, DECL, GPUS, [])
    assert g1 == Grant(4, 8 << 30, ("0",))
    g2 = allocate(one, DECL, GPUS, [g1])
    assert g2 == Grant(4, 8 << 30, ("1",))
    assert allocate(one, DECL, GPUS, [g1, g2]) is None                 # threads, memory and both a100s are taken
    small = parse_request({"gpu": {"count": 1, "memory_bytes": 20 << 30}})
    assert allocate(small, DECL, GPUS, [Grant(0, 0, ("0", "1"))]) is None   # the t4 has too little memory
    assert allocate(parse_request({}), DECL, GPUS, [g1, g2]) == Grant(None, 0, ())   # the engine's default: not reserved


def test_the_run_id_keeps_only_the_slots_that_can_change_the_result():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    spec = yaml.safe_load((root / "manifold_run_specs" / "auror_ref.yaml").read_text())
    sensors = root / "manifold_sensors"
    base = identity.run_id(spec, sensors)
    assert identity.run_id({**spec, "resources": {"memory_bytes": 1 << 30, "scratch_bytes": 1, "network": "none"}},
                           sensors) == base
    threaded = identity.run_id({**spec, "resources": {"cpu_threads": 1, "memory_bytes": 1}}, sensors)
    assert threaded != base and threaded == identity.run_id({**spec, "resources": {"cpu_threads": 1}}, sensors)
    assert identity_view({"memory_bytes": 1}) is None and identity_view({"gpu": {"count": 1}, "network": "none"}) == \
        {"gpu": {"count": 1}}


def _profile(layers, resources):
    path = layers / "engine_profiles" / "passthrough_runtime.yaml"
    doc = yaml.safe_load(path.read_text())
    doc["resources"] = resources
    path.write_text(yaml.safe_dump(doc, sort_keys=False))


def test_a_gpu_request_is_refused_here_and_admitted_on_a_backend_that_advertises_gpus(tmp_path, library, layers):
    """An engine that declares one GPU (the DIRSIG adapter with that declaration, in an explicit registry): refused at
    admission on this backend, which advertises none; admitted on a stub backend advertising two, which grants a
    device. DIRSIG itself declares no GPU, so its runs are refused by the declaration."""
    from backend_conformance import wait_for
    from manifold.core.compose import compose_sweep
    from manifold.core.engine import Registry
    from manifold.engines.dirsig.adapter import DirsigAdapter
    from manifold.sim.backend import LocalBackend

    class OneGpu(DirsigAdapter):
        def resources(self, spec=None):
            return ResourceDeclaration(gpu=GpuSlot(maximum=1))
    reg = Registry()
    reg.register("dirsig", OneGpu, source="test")
    _profile(layers, {"gpu": {"count": 1}})
    sweep = compose_sweep(layers / "recipes" / "synthetic_passthrough.yaml", registry=reg)
    (name,) = sweep.runs
    assert sweep.runs[name]["resources"] == {"gpu": {"count": 1}}
    assert sweep.sources[name]["resources"]["layer"] == "engine_profiles/passthrough_runtime.yaml"
    here = LocalBackend(tmp_path / "work", library, library=layers, engine=stub_engine(tmp_path), registry=reg)
    with pytest.raises(AdmissionError) as e:
        here.submit_run("synthetic_passthrough")
    assert "resources.gpu requests 1 GPU(s); this backend advertises no matching GPU(s)" in e.value.problem["detail"]
    assert here.store.list_runs() == []                                 # nothing created
    stub = LocalBackend(tmp_path / "work2", library, library=layers, engine=stub_engine(tmp_path), registry=reg,
                        capacity=GPUS)
    final = wait_for(stub, stub.submit_run("synthetic_passthrough")["run_id"], ("rendered", "failed"), timeout=120)
    assert final["state"] == "rendered", final["errors"]
    assert stub.store.read_record(final["run_id"])["resources"]["granted"]["gpu_ids"] == ["0"]
    default = LocalBackend(tmp_path / "work3", library, library=layers, engine=stub_engine(tmp_path), capacity=GPUS)
    with pytest.raises(AdmissionError) as e:
        default.submit_run("synthetic_passthrough")                     # the discovered DIRSIG adapter: no GPU
    assert "the engine declares at most 0" in e.value.problem["detail"]


def test_a_granted_thread_count_reaches_the_engine_and_the_record(tmp_path, library, layers):
    from backend_conformance import wait_for
    from manifold.sim.backend import LocalBackend
    _profile(layers, {"cpu_threads": 2, "memory_bytes": 1 << 20})
    backend = LocalBackend(tmp_path / "work", library, library=layers, engine=stub_engine(tmp_path))
    final = wait_for(backend, backend.submit_run("synthetic_passthrough")["run_id"], ("rendered", "failed"), timeout=120)
    assert final["state"] == "rendered", final["errors"]
    run_dir = backend.store.run_dir(final["run_id"])
    args = json.loads((run_dir / "output" / "stub_engine_args.json").read_text())["args"]
    assert "--threads=2" in args
    rec = backend.store.read_record(final["run_id"])
    assert rec["resources"]["granted"] == {"cpu_threads": 2, "memory_bytes": 1 << 20, "gpu_ids": []}
    assert rec["resources"]["requested"] == {"cpu_threads": 2, "memory_bytes": 1 << 20}
    assert json.loads((backend.store.slots / "resources.json").read_text()) == {}      # released
    stored = json.loads((run_dir / "run_spec.json").read_text())
    assert stored["resources"] == {"cpu_threads": 2}                    # memory is not part of the run id


def test_the_asset_rule_refuses_unstamped_missing_and_mismatched_assets(tmp_path):
    from manifold.core.dirhash import directory_digest
    from manifold.core.resources import AssetDecl, asset_digest, asset_problems, assets_for
    lib = tmp_path / "library"
    (lib / "ephemeris").mkdir(parents=True)
    (lib / "ephemeris" / "de.bsp").write_bytes(b"planets")
    (lib / "catalog").mkdir()
    (lib / "catalog" / "a.txt").write_text("stars")
    good_file = {"name": "ephemeris/de.bsp", "content_hash": asset_digest(lib / "ephemeris" / "de.bsp")}
    good_dir = {"name": "catalog", "content_hash": directory_digest(lib / "catalog")}
    decl = ResourceDeclaration(assets=(AssetDecl("ephemeris", good_file, "EPHEMERIS"),
                                       AssetDecl("catalog", {"name": "catalog", "content_hash": "sha256:<hash>"})))
    request = parse_request({"assets": [{"name": "catalog", "ref": good_dir}]})
    assets = assets_for(decl, request)
    assert assets == [("ephemeris", good_file, "EPHEMERIS"), ("catalog", good_dir, None)]   # the request supplies it
    assert asset_problems(assets, lib) == []
    assert "unstamped" in asset_problems(assets_for(decl, parse_request({})), lib)[0]
    assert "not found" in asset_problems([("x", {"name": "nope", "content_hash": good_file["content_hash"]}, None)], lib)[0]
    (lib / "ephemeris" / "de.bsp").write_bytes(b"changed")
    assert "does not match" in asset_problems(assets, lib)[0]
    assert "no library reference" in asset_problems([("x", None, None)], lib)[0]
