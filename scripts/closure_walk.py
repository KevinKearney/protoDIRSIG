#!/usr/bin/env python3
"""The closure walk over the corpus (round 46 D): every DIRSIG run tree the repository can build without rendering,
walked with `manifold.engines.dirsig.closure.walk`, one record per tree in `docs/data/closure_walk.jsonl` and the
summary table of `docs/Closure_walk.md`.

    python scripts/closure_walk.py --work DIR        build and walk every tree under DIR (outside the repository),
                                                     write the records and the table
    python scripts/closure_walk.py --table           print the summary table computed from the committed records

The trees are the committed run specs under `manifold_run_specs/` (top level and `s2s/`) whose `descriptor.origin.engine`
is `dirsig`, resolved to job trees: a layered spec through `Simulation._assemble` (the job's `input/` folder as the
render would see it, with the `.jsim` dirfm writes, `example.jsim`; no `scene2hdf`, no `dirsig5`), a pass-through spec
as `passthrough.run_engine` copies its directory (`shutil.copytree(..., symlinks=False)`; no compile). The tree root is
the folder DIRSIG runs in: the job's `input/` for a layered tree, the directory copy for a pass-through one. Each tree is
removed after its walk.

A record: `spec` (repository-relative), `mode`, `built` (false with `reason` when the spec does not resolve), `entry`,
`files`, `roles` (count per role), `unroled` (`[path, referrer, field]`), `violations` (count per kind), `disabled`
(violations from disabled elements), `orphan_violations`, `links`, `behind_links` (count), `unresolved`, `install`,
`orphans`, `role_conflicts`, `beyond_rules` and `rules_missed`.

`beyond_rules` compares the walk with the existing partial walker, `scene_ref`: the files the walker reached from a
scene, geometry list, material file or platform that neither `scene_ref.working_folder_files(scene, platform)` (the
working-folder rules) nor `scene_ref.scene_named_paths(scene, asset_dirs=())` (the scene's leaf texts, a listing one
level) names. `rules_missed` is the reverse: files those rules name that the walk did not reach.
"""
import argparse
import contextlib
import io
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "manifold_config_repo"
SENSORS = ROOT / "manifold_sensors"
SPECS = ROOT / "manifold_run_specs"
RECORDS = ROOT / "docs" / "data" / "closure_walk.jsonl"
DOC = ROOT / "docs" / "Closure_walk.md"
BEGIN, END = "<!-- closure-walk-table -->", "<!-- /closure-walk-table -->"
SCENE_SIDE = {"dirsig:scene", "dirsig:geometry_list", "dirsig:material_db", "dirsig:platform"}


def specs():
    """The committed DIRSIG run specs, repository-relative, sorted."""
    out = []
    for path in sorted(SPECS.glob("*.yaml")) + sorted((SPECS / "s2s").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        if isinstance(doc, dict) and doc.get("spec_version") and \
                ((doc.get("descriptor") or {}).get("origin") or {}).get("engine") == "dirsig":
            out.append(path.relative_to(ROOT).as_posix())
    return out


def _quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args)


def build(spec, work):
    """`(mode, tree root, entry, scene files, platform file, scene prefix)` of one spec's job tree under `work`, or
    `(mode, None, reason, ...)`."""
    from manifold.core.run_spec import load_run_spec
    from manifold.engines.dirsig.passthrough_spec import is_passthrough, resolve_passthrough
    doc = load_run_spec(ROOT / spec)
    if is_passthrough(doc):
        run = resolve_passthrough(doc, LIBRARY)
        copy = work / "input" / run.directory.name
        shutil.copytree(run.directory, copy, symlinks=False)
        return "passthrough", copy, run.simulation_rel, None, None, ""
    from manifold.engines.dirsig.simulation import Simulation
    sim = Simulation.from_run_spec(ROOT / spec, LIBRARY, work, SENSORS)
    if sim.resolved is None:
        return "layered", None, sim.resolve_error or sim.load_error, None, None, ""
    job = _quiet(sim._assemble, work / "input", work / "output")
    _quiet(lambda: job.write_files().write(work / "input" / "example.jsim"))
    r = sim.resolved
    return "layered", work / "input", "example.jsim", [r.scene], r.platform, "auror_ref/"


def rules(scenes, platform, prefix):
    """The root-relative files scene_ref's rules name."""
    from manifold.engines.dirsig.scene_ref import scene_named_paths, working_folder_files
    named = set()
    for scene in scenes:
        named |= {name for name, _, _ in working_folder_files(scene, platform or scene.parent / "-")}
        named |= {prefix + f for f in scene_named_paths(scene, asset_dirs=())[0]}
    return named


def record(spec, work):
    from manifold.engines.dirsig.closure import walk
    from manifold.engines.dirsig.passthrough import scenes_of
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    try:
        mode, root, entry, scenes, platform, prefix = build(spec, work)
        if root is None:
            return {"spec": spec, "mode": mode, "built": False, "reason": entry}
        w = walk(root, entry)
        if scenes is None:                                    # pass-through: the tree's own scene and platform
            scenes = [root / s for s in scenes_of(root / entry)]
            plats = [root / f.path for f in w.files if f.role == "dirsig:platform"]
            platform = plats[0] if plats else None
            scenes = [s for s in scenes if s.is_file()]
        named = rules(scenes, platform, prefix)
        roles = {f.path: f.role for f in w.files}
        referrer_role = {f.path: roles.get(f.referrer) for f in w.files}
        reached_scene_side = {f.path for f in w.files if referrer_role[f.path] in SCENE_SIDE}
        return {
            "spec": spec, "mode": mode, "built": True, "entry": entry, "files": len(w.files),
            "roles": dict(sorted(Counter(f.role or "(none)" for f in w.files).items())),
            "unroled": [[f.path, f.referrer, f.field] for f in w.unroled],
            "violations": dict(sorted(Counter(v.kind for v in w.violations).items())),
            "disabled": sum(1 for v in w.violations if not v.enabled),
            "orphan_violations": sum(1 for v in w.violations if v.orphan),
            "links": w.links, "behind_links": len(w.behind_links),
            "unresolved": [list(u) for u in w.unresolved], "install": [list(i) for i in w.install],
            "orphans": w.orphans, "role_conflicts": [list(c) for c in w.role_conflicts],
            "beyond_rules": sorted(reached_scene_side - named),
            "rules_missed": sorted(named - set(roles)),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


def summary(records):
    """The table rows: (quantity, value)."""
    built = [r for r in records if r["built"]]
    kinds = Counter(k for r in built for k in r["violations"])
    unroled = [u for r in built for u in r["unroled"]]
    unroled_fields = Counter(u[2] for u in unroled)
    unroled_paths = {(r["mode"], u[0]) for r in built for u in r["unroled"]}

    def n(pred):
        return sum(1 for r in built if pred(r))
    rows = [
        ("DIRSIG run specs committed", len(records)),
        ("trees built and walked (layered / pass-through)",
         f"{len(built)} ({n(lambda r: r['mode'] == 'layered')} / {n(lambda r: r['mode'] == 'passthrough')})"),
        ("trees not built", len(records) - len(built)),
        ("walked clean (no violation, unresolved reference, unroled file, role conflict or orphan)",
         n(lambda r: not (r["violations"] or r["unresolved"] or r["unroled"] or r["role_conflicts"]
                          or r["orphans"]))),
        ("passed (as clean, orphans allowed)",
         n(lambda r: not (r["violations"] or r["unresolved"] or r["unroled"] or r["role_conflicts"]))),
        ("reported a path violation", n(lambda r: r["violations"])),
    ]
    for kind in ("absolute", "dotdot", "non_nfc", "symlink", "outside_root", "form", "variable"):
        rows.append((f"  of which `{kind}`", f"{n(lambda r, k=kind: k in r['violations'])} trees, "
                                             f"{sum(r['violations'].get(kind, 0) for r in built)} reports"))
    rows += [
        ("  distinct links crossed per layered tree",
         ", ".join(sorted({str(len(r["links"])) for r in built if r["mode"] == "layered"})) or "none"),
        ("  files behind a crossed link that no reference reached (sum over trees)",
         sum(r["behind_links"] for r in built)),
        ("  trees whose only error is the links",
         n(lambda r: set(r["violations"]) == {"symlink"} and not (r["unresolved"] or r["unroled"]
                                                                  or r["role_conflicts"]))),
        ("reported an unresolved reference", n(lambda r: r["unresolved"])),
        ("referenced the DIRSIG installation (`$DIRSIG_HOME`)", n(lambda r: r["install"])),
        ("reported an orphan", n(lambda r: r["orphans"])),
        ("reported a role conflict", n(lambda r: r["role_conflicts"])),
        ("reached a file the existing `scene_ref` rules did not", f"{n(lambda r: r['beyond_rules'])} trees, "
         f"{sum(len(r['beyond_rules']) for r in built)} files"),
        ("named by the existing rules but not reached", f"{n(lambda r: r['rules_missed'])} trees, "
         f"{sum(len(r['rules_missed']) for r in built)} files"),
        ("**files reached that no role covers**", f"**{len(unroled)} in {n(lambda r: r['unroled'])} trees; "
         f"{len(unroled_paths)} distinct tree paths**"),
    ]
    for fld, count in sorted(unroled_fields.items()):
        rows.append((f"  by field `{fld}`", count))
    return rows


def table(records):
    lines = ["| Quantity | Value |", "|---|---|"]
    lines += [f"| {q} | {v} |" for q, v in summary(records)]
    return "\n".join(lines)


def load():
    return [json.loads(line) for line in RECORDS.read_text().splitlines() if line.strip()]


def write_doc(records):
    text = DOC.read_text()
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    DOC.write_text(f"{head}{BEGIN}\n{table(records)}\n{END}{tail}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", type=Path, help="scratch folder outside the repository")
    ap.add_argument("--table", action="store_true", help="print the table from the committed records")
    args = ap.parse_args(argv)
    if args.table:
        print(table(load()))
        return 0
    if args.work is None:
        ap.error("--work or --table")
    work = args.work.resolve()
    if work == ROOT or ROOT in work.parents:
        ap.error("--work must be outside the repository")
    out = []
    for i, spec in enumerate(specs(), 1):
        out.append(record(spec, work / "tree"))
        print(f"{i} {spec} {'built' if out[-1]['built'] else 'NOT BUILT'}", flush=True)
    RECORDS.write_text("".join(json.dumps(r, sort_keys=False) + "\n" for r in out))
    if DOC.exists() and BEGIN in DOC.read_text():
        write_doc(out)
    print(table(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
