#!/usr/bin/env python3
"""Stamp or check `content_hash` on file refs in sensors/*.yaml and run_specs/*.yaml. stdlib only.

    python scripts/stamp_hashes.py            rewrite stale or placeholder hashes in place
    python scripts/stamp_hashes.py --check    list stale hashes, exit 1 if any (CI)

A ref is `{name: <path>, content_hash: "<sha256:...>"}`. The name resolves as the loaders resolve it: a
sensor-spec ref (`*.yaml` without a directory) and spectral curves against `sensors/`; every other name
against `config_repo/`. A name that is not a single file (a `.scene` whose geometry and materials sit beside
it) is left as written, because one file's hash would not identify the asset. The hash is `sha256` of the
file bytes. MANIFOLD's canonical-JSON hash (Metadata_v02 §6.15) replaces it when the registry is built.
"""
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = re.compile(r'(\{name: )([^,}]+)(, content_hash: ")([^"]*)(")')
SKIP_SUFFIX = (".scene",)


def resolve(name, in_sensors_file):
    name = name.strip()
    if name.endswith(SKIP_SUFFIX):
        return None
    candidates = [ROOT / "sensors" / name] if (in_sensors_file or name.startswith("spectral/") or
                                                ("/" not in name and name.endswith(".yaml"))) \
        else [ROOT / "config_repo" / name]
    return next((c for c in candidates if c.is_file()), None)


def digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def process(path, write):
    text, stale = path.read_text(), []
    in_sensors = path.parent.name == "sensors"

    def sub(m):
        target = resolve(m.group(2), in_sensors)
        if target is None:
            return m.group(0)
        want = digest(target)
        if m.group(4) != want:
            stale.append(f"{path.relative_to(ROOT)}: {m.group(2).strip()}")
        return m.group(1) + m.group(2) + m.group(3) + want + m.group(5)
    new = REF.sub(sub, text)
    if write and new != text:
        path.write_text(new)
    return stale


def main(argv):
    check = "--check" in argv
    stale = []
    for f in sorted((ROOT / "sensors").glob("*.yaml")) + sorted((ROOT / "run_specs").glob("*.yaml")):
        stale += process(f, write=not check)
    for s in stale:
        print(("stale  " if check else "stamped ") + s)
    return 1 if (check and stale) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
