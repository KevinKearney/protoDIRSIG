"""notebooks/stage_05_sdk_auror_demo.ipynb executed top to bottom, unedited, through `nbclient` (the `python3` kernel of
this environment; the notebook's stored kernelspec `protodirsig` is left as it is), with its two work folders moved
under the test's temporary directory. The engine-free steps are checked always; the render and repeat, and the layered
comparison, are checked when the notebook ran them, and skipped with the reason the notebook printed otherwise (no
DIRSIG engine, no demo archive), never passed without their output. The whole notebook must finish in under 10 minutes."""
import json
import os
import time
from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat", reason="executing a notebook needs nbformat")
nbclient = pytest.importorskip("nbclient", reason="executing a notebook needs nbclient")

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "stage_05_sdk_auror_demo.ipynb"
LIMIT_S = 600


@pytest.fixture(scope="module")
def executed(tmp_path_factory):
    """(the printed text of every code cell, in order, and the wall time) of one execution."""
    tmp = tmp_path_factory.mktemp("stage05")
    nb = nbformat.read(str(NOTEBOOK), as_version=4)
    saved = {k: os.environ.get(k) for k in ("STAGE05_WORK", "STAGE05_LAYERED_WORK", "MPLBACKEND")}
    os.environ.update(STAGE05_WORK=str(tmp / "work"), STAGE05_LAYERED_WORK=str(tmp / "layered"), MPLBACKEND="Agg")
    t0 = time.monotonic()
    try:
        nbclient.NotebookClient(nb, timeout=LIMIT_S, kernel_name="python3",
                                resources={"metadata": {"path": str(NOTEBOOK.parent)}}).execute()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    wall = time.monotonic() - t0
    texts = []
    for cell in nb.cells:
        if cell.cell_type == "code":
            texts.append("".join(o.get("text", "") for o in cell.outputs if o.get("output_type") == "stream"))
    yield texts, wall


def _skip_reason(text, marker):
    return next((ln for ln in text.splitlines() if ln.startswith(f"SKIPPED: {marker}")), None)


def test_the_notebook_runs_within_the_limit(executed):
    _, wall = executed
    assert wall < LIMIT_S, f"{wall:.0f} s"


def test_the_engine_free_steps(executed):
    out = "\n".join(executed[0])
    assert "loader round trip equal : True" in out and "run id of the file      : True" in out
    assert "engine-block violations : []" in out
    assert "valid=True  engine_checked=False" in out
    assert "valid=False" in out and "engine.atmosphere.uniform has no weather values" in out
    assert "Expected a <filename> in uniform weather" in out
    assert "same run id: True" in out


def test_render_and_repeat(executed):
    out = "\n".join(executed[0])
    reason = _skip_reason(out, "submitting")
    if reason:
        pytest.skip(reason)
    assert "valid=True  engine_checked=True" in out and "dry_run        passed" in out
    assert "final     : rendered, verdict complete" in out
    assert "\nproduct\n" in out and "same id: True" in out
    assert "second run : rendered verdict complete" in out
    assert "byte-identical True" in out and "byte-identical False" not in out
    assert "every product reference's sha256 equal: True" in out


def test_the_layered_comparison(executed):
    out = "\n".join(executed[0])
    reason = _skip_reason(out, "the layered comparison")
    if reason:
        pytest.skip(reason)
    assert "layered      rendered  verdict complete" in out and "pass-through rendered  verdict complete" in out
    assert "images both forms wrote: ['demo.img']" in out
    assert "shape (bands, lines, samples): (1, 16, 16) vs (1, 16, 16)" in out
    assert "max abs difference          : 0.0" in out and "byte-identical              : True" in out


def test_the_committed_notebook_names_the_protodirsig_kernel():
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert nb["metadata"]["kernelspec"]["name"] == "protodirsig"
