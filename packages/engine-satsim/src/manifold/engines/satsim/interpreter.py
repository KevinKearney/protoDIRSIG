"""Finding SatSim's interpreter and probing it, without importing SatSim, TensorFlow or numpy here.

`locate()` returns `(python, source)` from the first of: the environment variable `MANIFOLD_SATSIM_PYTHON`; the key
`satsim.python` of `$XDG_CONFIG_HOME/manifold/engines.yaml` (`~/.config/manifold/engines.yaml` when the variable is
unset); the conda environment named `satsim` under the conda base of the `conda` on `PATH` (`<base>/envs/satsim/bin/
python`; conda itself is not run). It returns `(None, reason)` when none gives an existing file; a source that is set
but names no file is the reason (later sources are not tried, so a misconfiguration is not hidden).

`probe(python)` runs the interpreter once in a subprocess (`-B`, so nothing is written into its environment; `HOME`,
matplotlib and cache folders in a temporary directory; a socket guard; `PROBE_TIMEOUT_S`): it imports `satsim` and
reports the versions of satsim, tensorflow, numpy, astropy, skyfield and Python. The result is cached per process and
interpreter (`probe_cached`) and is recorded with each run (the adapter's fingerprint).
"""
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ENV_VAR = "MANIFOLD_SATSIM_PYTHON"
CONDA_ENV = "satsim"
PROBE_TIMEOUT_S = 60
PACKAGES = ("satsim", "tensorflow", "numpy", "astropy", "skyfield")

PROBE = r"""
import json, socket, sys
def _refuse(*a, **k):
    raise OSError("network access is not allowed in the SatSim availability probe")
socket.socket.connect = _refuse
socket.socket.connect_ex = _refuse
socket.create_connection = _refuse
socket.getaddrinfo = _refuse
from importlib.metadata import version, PackageNotFoundError
import satsim
out = {"python": sys.version.split()[0], "executable": sys.executable}
for name in %r:
    try:
        out[name] = version(name)
    except PackageNotFoundError:
        out[name] = None
print("MANIFOLD_SATSIM_PROBE " + json.dumps(out, sort_keys=True))
""" % (PACKAGES,)

_CACHE = {}


def config_file(environ=None):
    environ = os.environ if environ is None else environ
    base = environ.get("XDG_CONFIG_HOME") or str(Path(environ.get("HOME", "~")).expanduser() / ".config")
    return Path(base) / "manifold" / "engines.yaml"


def locate(environ=None):
    """`(python, source)` or `(None, reason)`; see the module docstring for the order."""
    environ = os.environ if environ is None else environ
    value = environ.get(ENV_VAR)
    if value:
        p = Path(value).expanduser()
        return (str(p), f"${ENV_VAR}") if p.is_file() else (None, f"${ENV_VAR} names {value}, which is not a file")
    cfg = config_file(environ)
    if cfg.is_file():
        import yaml
        try:
            doc = yaml.safe_load(cfg.read_text()) or {}
        except yaml.YAMLError as e:
            return None, f"{cfg} is not valid YAML: {e}"
        value = ((doc.get("satsim") or {}) if isinstance(doc, dict) else {}).get("python")
        if value:
            p = Path(str(value)).expanduser()
            return (str(p), str(cfg)) if p.is_file() else (None, f"{cfg} satsim.python names {value}, which is not a "
                                                                 "file")
    conda = shutil.which("conda", path=environ.get("PATH"))
    if conda:
        base = Path(conda).resolve().parents[1]
        p = base / "envs" / CONDA_ENV / "bin" / "python"
        if p.is_file():
            return str(p), f"conda environment {CONDA_ENV!r} ({base})"
        return None, (f"no SatSim interpreter: ${ENV_VAR} is unset, {cfg} names none, and the conda base {base} has no "
                      f"environment {CONDA_ENV!r}")
    return None, f"no SatSim interpreter: ${ENV_VAR} is unset, {cfg} names none, and conda is not on PATH"


def probe(python, timeout=PROBE_TIMEOUT_S):
    """`{"ok": bool, "reason": str|None, "versions": {...}, "seconds": float}` for one interpreter (not cached)."""
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="manifold-satsim-probe-") as home:
        env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
        env.update(HOME=home, MPLCONFIGDIR=str(Path(home) / "mpl"), XDG_CACHE_HOME=str(Path(home) / "cache"),
                   XDG_CONFIG_HOME=str(Path(home) / "config"), PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
                   TF_CPP_MIN_LOG_LEVEL="3", CUDA_VISIBLE_DEVICES="")
        try:
            res = subprocess.run([python, "-B", "-c", PROBE], capture_output=True, text=True, env=env, cwd=home,
                                 timeout=timeout, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return {"ok": False, "reason": f"the SatSim probe of {python} did not finish in {timeout} s", "versions": {},
                    "seconds": round(time.monotonic() - started, 2)}
        except OSError as e:
            return {"ok": False, "reason": f"{python} cannot be run: {e}", "versions": {},
                    "seconds": round(time.monotonic() - started, 2)}
    seconds = round(time.monotonic() - started, 2)
    lines = [ln for ln in res.stdout.splitlines() if ln.startswith("MANIFOLD_SATSIM_PROBE ")]
    if res.returncode != 0 or not lines:
        tail = (res.stderr.strip().splitlines() or ["no output"])[-1]
        return {"ok": False, "reason": f"{python} cannot import satsim (exit status {res.returncode}): {tail}",
                "versions": {}, "seconds": seconds}
    versions = json.loads(lines[-1].split(" ", 1)[1])
    return {"ok": True, "reason": None, "versions": versions, "seconds": seconds}


def probe_cached(python):
    """`probe(python)`, once per process and interpreter."""
    if python not in _CACHE:
        _CACHE[python] = probe(python)
    return _CACHE[python]


def clear_cache():
    _CACHE.clear()
