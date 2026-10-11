"""The dummy engine process, standard library only (it runs in an interpreter other than the SDK's).

    <python> engine.py <run_dir>

Reads `<run_dir>/run_spec.json` (the engine block), writes `output/frame-NN.txt` (one per step, `sleep_s` apart, each
holding the label, the asset table's first line, the thread count and the interpreter), `output/dummy.log`, and last
`output/DONE`, the end-of-run marker; with `fail` it exits 3 instead of writing the marker.
"""
import json
import os
import sys
import time
from pathlib import Path

run_dir = Path(sys.argv[1])
block = json.loads((run_dir / "run_spec.json").read_text())["engine"]
out = run_dir / "output"
out.mkdir(parents=True, exist_ok=True)
table = Path(os.environ["DUMMY_TABLE"]).read_text().splitlines()[0]
log = open(out / "dummy.log", "a")
log.write(f"interpreter {sys.executable}\nthreads {os.environ.get('DUMMY_THREADS')}\nhome {os.environ.get('HOME')}\n")
log.flush()
for i in range(block["steps"]):
    time.sleep(float(block.get("sleep_s", 0)))
    (out / f"frame-{i:02d}.txt").write_text(json.dumps({"frame": i, "label": block.get("label"), "table": table,
                                                        "threads": os.environ.get("DUMMY_THREADS"),
                                                        "interpreter": sys.executable}) + "\n")
    log.write(f"frame {i}\n")
    log.flush()
if block.get("fail"):
    sys.exit(3)
(out / "DONE").write_text("complete\n")
