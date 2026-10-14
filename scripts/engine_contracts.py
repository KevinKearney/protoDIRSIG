#!/usr/bin/env python3
"""The engine contracts a non-Python consumer needs: each registered engine's engine-block schemas published under
`manifold_contracts/`, and the admission vectors for engine selection.

    python scripts/engine_contracts.py           (re)write the published schemas and manifold_contracts/vectors/admission/
    python scripts/engine_contracts.py --check   exit 1 if a registered engine's schema is not published, is published
                                                 under another $id or differs, or a vector differs from what admission
                                                 gives now

The engines are those discovered in this environment (`manifold.sim.engines`). An engine's schemas are what its
adapter's optional `schemas()` returns, else `engine_schema(None)`; each must have a `$id` under the contract base
(`manifold.core.contract.CONTRACTS_BASE`), which names its published file `manifold_contracts/<file>`. Published means
that file exists and holds the same document (compared as canonical JSON).

The admission vectors (`vectors/admission/<case>.json`) state, for the schema stage of admission: a run spec, the
registry it is checked against (engine ids and their schema `$id`s), and the verdict: admitted or not, which rule
refused it (`run-spec-schema`, `unregistered-engine`, `engine-block-schema`) and the JSON Pointers at fault. Error
messages are not part of a vector (they are the validator's own text). Cases: a valid run spec, an engine id no
registered adapter serves, and an engine block its adapter's schema rejects.
"""
import copy
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "manifold_contracts"
VECTORS = CONTRACTS / "vectors" / "admission"
BASE_SPEC = ROOT / "manifold_run_specs" / "auror_ref.yaml"
sys.path[:0] = [str(ROOT / "packages" / d / "src") for d in ("core", "sim")]   # the manifold namespace, uninstalled

import manifold.sim  # noqa: E402,F401  (installs the discovered engine registry)
from manifold.core import contract                                         # noqa: E402
from manifold.core.engine import Registry                                  # noqa: E402
from manifold.core.identity import canonical_json                          # noqa: E402
from manifold.sim import engines                                           # noqa: E402


def engine_schemas(registry=None):
    """{engine_id: [schema document, ...]} for every engine of the registry whose adapter loads."""
    reg = registry or engines.registry()
    out = {}
    for engine_id in reg.ids():
        adapter = reg.find(engine_id)
        if adapter is not None:
            out[engine_id] = contract.adapter_schemas(adapter)
    return out


def schema_problems(registry=None):
    problems = []
    reg = registry or engines.registry()
    for st in reg.listing():
        if reg.find(st.engine_id) is None:
            problems.append(f"{st.engine_id}: its adapter does not load ({st.reason}); its schemas cannot be checked")
    for engine_id, docs in engine_schemas(reg).items():
        for doc in docs:
            sid = doc.get("$id")
            loc = contract.published_location(sid)
            if loc is None:
                problems.append(f"{engine_id}: schema $id {sid!r} is not under {contract.CONTRACTS_BASE}")
                continue
            path = ROOT / loc
            if not path.is_file():
                problems.append(f"{engine_id}: {sid} is not published ({loc} is missing)")
            elif canonical_json(json.loads(path.read_text())) != canonical_json(doc):
                problems.append(f"{engine_id}: {loc} differs from the schema the adapter applies")
    return problems


def publish(registry=None):
    for engine_id, docs in engine_schemas(registry).items():
        for doc in docs:
            loc = contract.published_location(doc.get("$id"))
            if loc is None:
                raise SystemExit(f"{engine_id}: schema $id {doc.get('$id')!r} is not under {contract.CONTRACTS_BASE}")
            path = ROOT / loc
            text = json.dumps(doc, indent=2) + "\n"
            if not path.is_file() or canonical_json(json.loads(path.read_text())) != canonical_json(doc):
                path.write_text(text)
                print(f"published {loc}")


def verdict(spec, registry):
    """The schema stage of admission as a vector states it: `admitted`, `rule`, `paths`."""
    core = sorted({v["path"] for v in contract.run_spec_violations(spec)})
    if core:
        return {"admitted": False, "rule": "run-spec-schema", "paths": core}
    engine_id = (spec.get("descriptor", {}).get("origin") or {}).get("engine")
    if registry.find(engine_id) is None:
        return {"admitted": False, "rule": "unregistered-engine", "paths": ["/descriptor/origin/engine"]}
    block = sorted({v[0] for v in contract.engine_block_violations(spec, registry)})   # (path, message, at)
    if block:
        return {"admitted": False, "rule": "engine-block-schema", "paths": block}
    return {"admitted": True, "rule": None, "paths": []}


def _dirsig_only():
    reg = Registry()
    reg.register("dirsig", engines.load_target("manifold.engines.dirsig.adapter:DirsigAdapter"))
    return reg


def vectors():
    base = yaml.safe_load(BASE_SPEC.read_text())
    reg = _dirsig_only()
    unregistered = copy.deepcopy(base)
    unregistered["descriptor"]["origin"]["engine"] = "nosuch"
    bad_block = copy.deepcopy(base)
    bad_block["engine"]["motion"]["kind"] = "teleport"
    cases = {"valid": ("The AUROR reference run spec; DIRSIG registered: admitted.", base),
             "unregistered_engine": ("descriptor.origin.engine names an engine no registered adapter serves: refused "
                                     "before any engine-block check, at the engine id.", unregistered),
             "engine_block_invalid": ("The engine block violates the registered DIRSIG adapter's schema (an unknown "
                                      "motion kind): refused at the engine block; the run-spec schema alone accepts "
                                      "it, since it leaves the engine block open.", bad_block)}
    registry = [{"engine_id": e, "schemas": [d["$id"] for d in docs]} for e, docs in engine_schemas(reg).items()]
    out = {}
    for name, (description, spec) in cases.items():
        out[name] = {"description": description, "registry": registry, "run_spec": spec,
                     "run_spec_schema_alone": not contract.run_spec_violations(spec), "expected": verdict(spec, reg)}
    return out


def _text(doc):
    return json.dumps(doc, indent=1, sort_keys=False) + "\n"


def main(argv):
    check = "--check" in argv
    problems = []
    if check:
        problems += schema_problems()
        for name, doc in vectors().items():
            path = VECTORS / f"{name}.json"
            if not path.is_file() or path.read_text() != _text(doc):
                problems.append(f"vectors/admission/{name}.json differs from what admission gives now")
        for p in problems:
            print(p, file=sys.stderr)
        return 1 if problems else 0
    publish()
    VECTORS.mkdir(parents=True, exist_ok=True)
    for name, doc in vectors().items():
        (VECTORS / f"{name}.json").write_text(_text(doc))
    print(f"wrote {len(vectors())} admission vectors to {VECTORS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
