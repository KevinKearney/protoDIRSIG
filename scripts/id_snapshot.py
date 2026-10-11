#!/usr/bin/env python3
"""Every id the repository derives offline, as one sorted, canonical JSON snapshot: `tests/data/id_snapshot.json`.

    python scripts/id_snapshot.py            (re)write tests/data/id_snapshot.json
    python scripts/id_snapshot.py --check    recompute and compare; list every changed id, exit 1 if any

What it holds:
- `recipes`: for each committed recipe (`manifold_run_specs/recipes/*.yaml`, pass-through and demo recipes included),
  the run id of each run it composes to and its sweep id (a one-run recipe has a one-run sweep id).
- `generated_specs`: the run id of each committed generated run spec (`manifold_run_specs/*.yaml`).
- `vectors`: the run ids of every composed document in `manifold_contracts/vectors/compose/`, the sweep id of each
  case that composes, the identity vectors (`run_ids.json`, the pass-through spec's run id and directory digest, the
  `dirhash/1` tree digest), and the orbit vector (the sha256 of its data files and of the propagated ITRS positions
  rounded to 1 mm).
- `sweep_digest_table`: per attempt of `docs/data/demo_sweep_digests.jsonl.gz`, the sha256 of the canonical JSON of
  its sorted output digests, and the sha256 of the decompressed table.

An entry that needs a gitignored asset (a pass-through demo directory under `manifold_config_repo/demo_dirs/`) is
recorded when the asset is present; when it is absent the entry is listed under `skipped` with the reason and the
comparison leaves the recorded value alone, so a fresh clone still checks the rest.
"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "tests" / "data" / "id_snapshot.json"
RUN_SPECS = ROOT / "manifold_run_specs"
SENSORS = ROOT / "manifold_sensors"
CONFIG = ROOT / "manifold_config_repo"
VECTORS = ROOT / "manifold_contracts" / "vectors"
DIGESTS = ROOT / "docs" / "data" / "demo_sweep_digests.jsonl.gz"
sys.path[:0] = [str(ROOT / "packages" / d / "src") for d in ("core", "sim")]   # the manifold namespace, uninstalled

import manifold.sim  # noqa: E402,F401  (installs the engine registry compose and validation use)
from manifold.core import identity                                           # noqa: E402
from manifold.core.compose import ComposeError, compose_sweep               # noqa: E402
from manifold.core.dirhash import directory_digest                          # noqa: E402


def _sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _missing_asset(doc):
    """The gitignored pass-through directory a recipe or run spec names, when it is absent; else None."""
    doc = doc or {}
    block = doc.get("passthrough") or (doc.get("engine") or {}).get("passthrough") or {}   # a recipe, a run spec
    name = (block.get("directory") or {}).get("name")
    if name and not (CONFIG / name).is_dir():
        return f"pass-through directory manifold_config_repo/{name} is absent (gitignored; scripts/bootstrap.py places it)"
    return None


def _recipes(skipped):
    out = {}
    for path in sorted((RUN_SPECS / "recipes").glob("*.yaml")):
        key = path.relative_to(ROOT).as_posix()
        reason = _missing_asset(yaml.safe_load(path.read_text()))
        if reason:
            skipped[f"recipes/{key}"] = reason
            continue
        sweep = compose_sweep(path)
        out[key] = {"run_ids": {name: sweep.run_ids[name] for name in sweep.runs}, "sweep_id": sweep.sweep_id}
    return out


def _generated(skipped):
    out = {}
    for path in sorted(RUN_SPECS.glob("*.yaml")):
        key = path.relative_to(ROOT).as_posix()
        spec = yaml.safe_load(path.read_text())
        reason = _missing_asset(spec)
        if reason:
            skipped[f"generated_specs/{key}"] = reason
            continue
        out[key] = identity.run_id(spec, SENSORS)
    return out


def _compose_vectors():
    compose = VECTORS / "compose"
    library = compose / "manifold_sensors"
    run_ids, sweeps = {}, {}
    for case in sorted(p for p in compose.iterdir() if (p / "recipes").is_dir()):
        for doc in sorted(case.rglob("expected*.yaml")):
            spec = yaml.safe_load(doc.read_text())
            if isinstance(spec, dict) and "descriptor" in spec:
                run_ids[doc.relative_to(compose).as_posix()] = identity.run_id(spec, library)
        for recipe in sorted((case / "recipes").glob("*.yaml")):
            key = recipe.relative_to(compose).as_posix()
            try:
                sweeps[key] = compose_sweep(recipe, sensor_library=library).sweep_id
            except ComposeError as e:
                sweeps[key] = {"compose_error": str(e).replace(str(ROOT), "<repo>")}   # no machine path
    return run_ids, sweeps


def _orbit():
    folder = VECTORS / "orbit"
    out = {p.name: _sha256_file(p) for p in sorted(folder.iterdir()) if p.is_file() and p.suffix != ".md"}   # data, not prose
    want = json.loads((folder / "expected.json").read_text())
    from manifold.core import orbit  # skyfield, sgp4: imported here only
    _, _, l1, l2 = orbit.read_tle(folder / want["tle_file"], 35946)
    traj = orbit.propagate(l1, l2, want["epoch_utc"], want["t_s"])
    mm = [[int(round(float(v) * 1000)) for v in row] for row in traj.pos_itrs]
    out["propagated_itrs_mm_sha256"] = identity.sha256_hex(identity.canonical_json(mm))
    return out


def _vectors():
    idv = VECTORS / "identity"
    run_ids, sweeps = _compose_vectors()
    passthrough_spec = yaml.safe_load((idv / "passthrough" / "spec.yaml").read_text())
    return {
        "compose_run_ids": run_ids,
        "compose_sweep_ids": sweeps,
        "identity_run_ids_json": json.loads((idv / "run_ids.json").read_text()),
        "passthrough": {"run_id": identity.run_id(passthrough_spec, SENSORS),
                        "digest": directory_digest(idv / "passthrough" / "tree")},
        "dirhash": directory_digest(idv / "dirhash" / "tree"),
        "orbit": _orbit(),
    }


def _sweep_digest_table():
    raw = gzip.decompress(DIGESTS.read_bytes())
    attempts = {}
    for n, line in enumerate(raw.decode().splitlines()):
        rec = json.loads(line)
        outputs = sorted([o["name"], o["sha256"], o["size"]] for o in rec["outputs"])
        key = f"{n:04d} {rec['demo']} {rec['simulation']}{' repeat' if rec['repeat'] else ''}"
        attempts[key] = identity.sha256_hex(identity.canonical_json(outputs))
    return {"table_sha256": hashlib.sha256(raw).hexdigest(), "attempts": attempts}


def snapshot():
    skipped = {}
    snap = {"recipes": _recipes(skipped), "generated_specs": _generated(skipped), "vectors": _vectors(),
            "sweep_digest_table": _sweep_digest_table()}
    return snap, skipped


def _flatten(node, prefix=""):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            out.update(_flatten(v, f"{prefix}/{k}" if prefix else k))
        return out
    return {prefix: node}


def compare(recorded, current, skipped):
    """Changed, added and removed entries, ignoring entries skipped for an absent asset."""
    want, got = _flatten(recorded), _flatten(current)
    skip = tuple(skipped)
    problems = []
    for key in sorted(set(want) | set(got)):
        if key.startswith(skip):
            continue
        if key not in got:
            problems.append(f"missing: {key}")
        elif key not in want:
            problems.append(f"new: {key}")
        elif want[key] != got[key]:
            problems.append(f"changed: {key}: {want[key]} -> {got[key]}")
    return problems


def dumps(snap):
    return json.dumps(snap, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    snap, skipped = snapshot()
    for key, reason in sorted(skipped.items()):
        print(f"skipped {key}: {reason}")
    if "--check" in argv:
        problems = compare(json.loads(SNAPSHOT.read_text()), snap, skipped)
        for p in problems:
            print(p)
        print(f"id snapshot: {'unchanged' if not problems else f'{len(problems)} changed'}")
        return 1 if problems else 0
    if skipped:
        print("refusing to write a snapshot with skipped entries; place the assets first (scripts/bootstrap.py)")
        return 1
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(dumps(snap))
    print(f"wrote {SNAPSHOT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
