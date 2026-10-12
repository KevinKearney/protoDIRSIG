"""The SatSim launcher: run by SatSim's own interpreter as `python launcher.py <run_dir>`, never imported by the SDK.

Standard library until SatSim is reached. In this order it:

1. installs a socket guard: any outbound connection or name lookup raises `OSError` naming the policy (the run's
   network slot is `none`) and is appended to `output/network_attempts.log`;
2. reads `<run_dir>/input/launch.json` (written by the adapter's launch plan: the seed, the staged configuration, the
   set folder name);
3. keeps every cache inside the run: `HOME` is the per-run home the plan set; `MPLCONFIGDIR`, `XDG_CACHE_HOME`,
   `XDG_CONFIG_HOME`, `KERAS_HOME` and `NUMBA_CACHE_DIR` are set under it, and `CUDA_VISIBLE_DEVICES` is empty (CPU);
4. sets `SATSIM_SKYFIELD_LOAD_DIR` to the folder of the staged ephemeris (`MANIFOLD_SATSIM_EPHEMERIS`), which SatSim
   reads when it is imported;
5. seeds Python's `random`, numpy's global state and TensorFlow's global seed from the run's seed;
6. configures astropy: no downloads (`utils.data.conf.allow_internet`, `iers.conf.auto_download` off), no maximum age
   for the table (`auto_max_age` None), and the staged IERS snapshot (`MANIFOLD_SATSIM_IERS`) as the Earth-orientation
   table;
7. calls SatSim's Python entry point as the probe did, `gen_multi(config, True, "output", "input", ...)`, with relative
   folders (the working folder is the run folder), so the resolved `config.json` records `_input_dir: input`, the same
   for every repeat, and with a fixed set folder name, so the annotations do not carry a wall-clock time;
8. writes `output/satsim_result.json` (`outcome` `rendered` or `failed`, the seed, the set folder, the versions, the
   elapsed time and, for a failure, the head of the traceback) and exits 0 or 1.

A run stopped by a signal writes no result file; the collector then reports what the frames say.
"""
import json
import os
import socket
import sys
import time
import traceback
from pathlib import Path

STARTED = time.monotonic()
RUN_DIR = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
OUT = RUN_DIR / "output"
OUT.mkdir(parents=True, exist_ok=True)
POLICY = "this run's network slot is none (MANIFOLD policy): SatSim must not connect"


def _guard(*args, **kwargs):
    with open(OUT / "network_attempts.log", "a") as f:
        f.write(f"{time.time():.3f} {args[1:] if len(args) > 1 else args!r}\n")
    raise OSError(f"network access refused: {POLICY}")


socket.socket.connect = _guard
socket.socket.connect_ex = _guard
socket.create_connection = _guard
socket.getaddrinfo = _guard


def _result(doc):
    doc["elapsed_s"] = round(time.monotonic() - STARTED, 3)
    (OUT / "satsim_result.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")


def main():
    launch = json.loads((RUN_DIR / "input" / "launch.json").read_text())
    home = Path(os.environ.get("HOME", RUN_DIR / "home"))
    for var, sub in (("MPLCONFIGDIR", "mpl"), ("XDG_CACHE_HOME", "cache"), ("XDG_CONFIG_HOME", "config"),
                     ("KERAS_HOME", ".keras"), ("NUMBA_CACHE_DIR", "numba")):
        os.environ[var] = str(home / sub)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    ephemeris = Path(os.environ["MANIFOLD_SATSIM_EPHEMERIS"])
    iers_table = Path(os.environ["MANIFOLD_SATSIM_IERS"])
    os.environ["SATSIM_SKYFIELD_LOAD_DIR"] = str(ephemeris.parent)
    os.chdir(RUN_DIR)
    seed = int(launch["seed"])
    import random
    random.seed(seed)
    import numpy
    numpy.random.seed(seed)
    import tensorflow
    tensorflow.random.set_seed(seed)
    from astropy.utils import data as astropy_data, iers
    astropy_data.conf.allow_internet = False
    iers.conf.auto_download = False
    iers.conf.auto_max_age = None
    iers.earth_orientation_table.set(iers.IERS_A.open(str(iers_table)))
    from importlib.metadata import version
    versions = {n: version(n) for n in ("satsim", "tensorflow", "numpy", "astropy", "skyfield")}
    versions["python"] = sys.version.split()[0]
    from satsim import gen_multi
    from satsim.config import load_json, load_yaml
    config = launch["config"]
    ssp = load_json(config) if config.endswith(".json") else load_yaml(config)
    print(f"satsim launcher: seed {seed}, config {config}, set {launch['set']}, satsim {versions['satsim']}",
          flush=True)
    gen_multi(ssp, True, "output", launch["input_dir"], None, None, 0, False, folder_name=launch["set"])
    return {"outcome": "rendered", "seed": seed, "set": launch["set"], "versions": versions}


if __name__ == "__main__":
    try:
        result = main()
    except BaseException as e:  # noqa: BLE001 -- every failure is reported, then the exit status says failed
        text = traceback.format_exc()
        print(text, file=sys.stderr, flush=True)
        _result({"outcome": "failed", "message": f"{type(e).__name__}: {e}",
                 "traceback_head": text.strip().splitlines()[-12:]})
        sys.exit(1)
    _result(result)
    sys.exit(0)
