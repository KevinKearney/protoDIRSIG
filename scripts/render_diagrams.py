#!/usr/bin/env python3
"""Render the controlled drawings in docs/diagrams/ (Mermaid source -> SVG and PNG).

    python scripts/render_diagrams.py            render every drawing whose source changed (or all with --all)
    python scripts/render_diagrams.py --check    exit 1 if a rendered file is missing or its source changed since

The `.mmd` file is the source of truth. `docs/diagrams/manifest.json` records the sha256 of each source at its last
render, so --check detects a source edited without a re-render. Rendering needs `mmdc` (Mermaid CLI) on PATH, or
`npx` (`npm i -g @mermaid-js/mermaid-cli`); set PUPPETEER_EXECUTABLE_PATH or MMDC_PUPPETEER_CONFIG for a system
Chromium. Standard library only.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "docs" / "diagrams"
MANIFEST = DIR / "manifest.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    return sorted(DIR.glob("*.mmd"))


def stale():
    recorded = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    out = []
    for src in sources():
        rendered = [src.with_suffix(e) for e in (".svg", ".png")]
        if recorded.get(src.name) != sha(src) or not all(p.exists() for p in rendered):
            out.append(src)
    return out, recorded


def mmdc():
    exe = shutil.which("mmdc")
    return [exe] if exe else ([shutil.which("npx"), "-y", "@mermaid-js/mermaid-cli"] if shutil.which("npx") else None)


def render(src, cmd, cfg):
    for ext, extra in ((".svg", []), (".png", ["-s", "2"])):
        subprocess.run(cmd + ["-i", str(src), "-o", str(src.with_suffix(ext)), "-b", "white", *extra, *cfg], check=True)


def main(argv):
    todo, recorded = stale()
    if "--check" in argv:
        for s in todo:
            print(f"stale or missing render: {s.relative_to(ROOT)}")
        return 1 if todo else 0
    if "--all" in argv:
        todo = sources()
    if not todo:
        print("drawings are current")
        return 0
    cmd = mmdc()
    if cmd is None:
        sys.exit("mmdc not found: npm i -g @mermaid-js/mermaid-cli (or install node for npx)")
    cfg = []
    conf = os.environ.get("MMDC_PUPPETEER_CONFIG")
    if conf:
        cfg = ["-p", conf]
    elif os.environ.get("PUPPETEER_EXECUTABLE_PATH"):
        tmp = Path(tempfile.mkdtemp()) / "pp.json"
        tmp.write_text(json.dumps({"executablePath": os.environ["PUPPETEER_EXECUTABLE_PATH"], "args": ["--no-sandbox"]}))
        cfg = ["-p", str(tmp)]
    for src in todo:
        render(src, cmd, cfg)
        recorded[src.name] = sha(src)
        print(f"rendered {src.relative_to(ROOT)}")
    MANIFEST.write_text(json.dumps(dict(sorted(recorded.items())), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
