"""The DIRSIG engine process: `python -m <package>.runner <run_dir>`, launched by the worker from the adapter's plan.

Reads `job.json` and `run_spec.yaml` from the run directory, calls `DirsigAdapter.execute` (which writes
`engine_result.json`) and exits 0; the worker reads the outcome through `DirsigAdapter.collect`.
"""
import json
import sys
from pathlib import Path

import yaml

from manifold.core.engine import RunContext


def main(run_dir):
    from manifold.engines.dirsig.adapter import DirsigAdapter
    run_dir = Path(run_dir).resolve()
    job = json.loads((run_dir / "job.json").read_text())
    spec = yaml.safe_load((run_dir / "run_spec.yaml").read_text())
    context = RunContext(run_dir, spec, job["config_repo"], job.get("sensor_library"), run_dir / "output",
                         {"engine": job.get("engine", "auto")})
    DirsigAdapter().execute(context)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m <dirsig engine package>.runner <run_dir>")
    sys.exit(main(sys.argv[1]))
