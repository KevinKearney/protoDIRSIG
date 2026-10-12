#!/usr/bin/env python3
"""Survey a folder of DIRSIG scenes that is not the install's demo archive, with `survey_demos.py`'s own reader.

    python scripts/survey_transfer.py ROOT [--map-absolute] [--json]

ROOT is a folder laid out as DIRSIG's Documents folder: `scenes/<scene>/` with `shots/<shot>/<simulation>` inside and
optionally `atmospheres/` and `platforms/` beside `scenes/` (for example a folder of scenes received from a user, or
the install's `Documents_Folder-*/DIRSIG`). Every `.sim` and `.jsim` under ROOT is surveyed as one demo: a directory
stands in for the demo zip (the same `infos`, `read`, `resolve` and `under`), so the verdict (`ready`, `near`, `far`,
`unparsed`) and its causes are `survey_demos._survey`'s, against what the SDK covers today. A reference resolves inside
ROOT only. With `--map-absolute`, an absolute `/Users/<name>/Documents/DIRSIG/<rest>` reference (the author's own
machine, as DIRSIG's Documents-folder scenes write them) resolves to `<ROOT>/<rest>` and is listed; without it, any
absolute reference is unresolved. Read only: nothing is written under ROOT. Prints a markdown table, or JSON with
`--json`. The results for the scenes Kevin received are in `docs/DIRSIG_transfer_scenes.md`.
"""
import argparse
import json
import os
import posixpath
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import survey_demos as sd                                                     # noqa: E402

ABSOLUTE = re.compile(r"^/Users/[^/]+/Documents/DIRSIG/")


class _Info:
    def __init__(self, size):
        self.file_size = size


class DirDemo(sd.Demo):
    """A directory read as `survey_demos.Demo` reads a zip; members are POSIX paths relative to the root."""

    def __init__(self, root, map_absolute=False):
        self.root = self.path = Path(root)
        self.infos = {}
        for d, _, files in os.walk(self.root):
            for f in files:
                p = Path(d) / f
                self.infos[p.relative_to(self.root).as_posix()] = _Info(p.stat().st_size)
        self.map_absolute = map_absolute
        self.absolute = []

    def read(self, member):
        return (self.root / member).read_bytes()

    def resolve(self, base_dir, ref):
        ref = ref.strip().replace("\\", "/")
        if ref.startswith("/"):
            self.absolute.append(ref)
            if self.map_absolute and ABSOLUTE.match(ref):
                name = ABSOLUTE.sub("", ref)
                return name if name in self.infos else None
            return None
        name = posixpath.normpath(posixpath.join(base_dir, re.sub(r"^\$SCENE_DIR/?", "", ref)))
        return name if name in self.infos else None


def survey_simulation(demo, sim):
    """The survey record of one simulation file of `demo`, plus every file it names and whether ROOT holds it."""
    rec = {"name": sim, "verdict": "unparsed", "reason": None}
    primary = sd._primary_sim
    sd._primary_sim = lambda d: (sim, [sim])
    demo.absolute = []
    try:
        sd._survey(demo, rec)
    except (sd.Unparsed, KeyError, ValueError, AttributeError, TypeError) as e:
        rec["verdict"], rec["reason"] = "unparsed", str(e) if isinstance(e, sd.Unparsed) else f"{type(e).__name__}: {e}"
    finally:
        sd._primary_sim = primary
    text = demo.read(sim).decode("utf-8", "replace")
    named = re.findall(r'externalfile="([^"]+)"', text) + re.findall(r'"[a-z_]*filename"\s*:\s*"([^"]+)"', text) \
        + re.findall(r'"inputs"\s*:\s*"([^"]+)"', text)
    base = posixpath.dirname(sim)
    rec["named"] = {n: demo.resolve(base, n) is not None for n in named}
    rec["absolute"] = sorted({n for n in named if n.startswith("/")})
    return rec


def survey(root, map_absolute=False):
    demo = DirDemo(root, map_absolute)
    sims = sorted(m for m in demo.infos if m.endswith((".sim", ".jsim")))
    return [survey_simulation(demo, s) for s in sims]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("root", type=Path)
    ap.add_argument("--map-absolute", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    records = survey(a.root, a.map_absolute)
    if a.json:
        print(json.dumps(records, indent=1))
        return 0
    print("| Simulation | Verdict | Cause | Named files absent | Absolute references |")
    print("|---|---|---|---|---|")
    for r in records:
        cause = r["reason"] or "; ".join(r.get("missing") or []) or "—"
        absent = ", ".join(f"`{n}`" for n, ok in r["named"].items() if not ok) or "—"
        print(f"| `{r['name']}` | {r['verdict']} | {cause} | {absent} | {len(r['absolute'])} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
