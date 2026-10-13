"""notebooks/stage_06_space_to_space.ipynb executed top to bottom, unedited, through `nbclient` (the `python3` kernel of
this environment; the stored kernelspec `protodirsig` is left as it is). It reads `docs/data/s2s_results.jsonl` and the
tolerances of `tests/test_s2s_results.py`, renders nothing and must finish in under 60 seconds; every residual the
test asserts is printed within its tolerance, and the closing table of what the SDK cannot express is present."""
import json
import os
import time
from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat", reason="executing a notebook needs nbformat")
nbclient = pytest.importorskip("nbclient", reason="executing a notebook needs nbclient")

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "stage_06_space_to_space.ipynb"
LIMIT_S = 60
CASES = ("flux closure", "R^2 footprint", "exposure", "sun zenith", "bar level", "look I", "look II", "bar period", "phase")


@pytest.fixture(scope="module")
def executed():
    nb = nbformat.read(str(NOTEBOOK), as_version=4)
    saved = os.environ.pop("MPLBACKEND", None)               # the kernel's inline backend, so the five plots are output
    t0 = time.monotonic()
    try:
        nbclient.NotebookClient(nb, timeout=LIMIT_S, kernel_name="python3",
                                resources={"metadata": {"path": str(NOTEBOOK.parent)}}).execute()
    finally:
        if saved is not None:
            os.environ["MPLBACKEND"] = saved
    wall = time.monotonic() - t0
    out = "\n".join("".join(o.get("text", "") for o in c.outputs if o.get("output_type") == "stream")
                    for c in nb.cells if c.cell_type == "code")
    yield nb, out, wall


def test_the_notebook_runs_within_the_limit(executed):
    assert executed[2] < LIMIT_S, f"{executed[2]:.0f} s"


def test_it_reads_every_record_and_the_test_tolerances(executed):
    out = executed[1]
    n = sum(1 for line in (ROOT / "docs" / "data" / "s2s_results.jsonl").read_text().splitlines() if line.strip())
    assert f"{n} records from docs/data/s2s_results.jsonl; families [1, 2, 3]" in out
    assert "tolerances: TOL_FLUX_PLATE 0.00816," in out


def test_every_case_is_within_its_tolerance(executed):
    out = executed[1]
    assert "OUTSIDE" not in out
    summary = out.split("largest residual", 1)[1]
    for case in CASES:
        line = next(ln for ln in summary.splitlines() if ln.startswith(f"{case:16s} "))
        assert line.endswith("True"), line


def test_the_unresolved_breakdown_and_the_closing_table(executed):
    nb, out, _ = executed
    assert "sub-pixel breakdown: ratio at offsets 0, 0.25, 0.5, 0.75 px" in out
    assert "  200.0 km  0.769  1.794  1.025  1.025" in out
    assert sum(1 for c in nb.cells if c.cell_type == "code" for o in c.outputs if "image/png" in o.get("data", {})) == 5
    last = nb.cells[-1]
    assert last.cell_type == "markdown" and "What the SDK cannot express" in last.source and "| A PSF |" in last.source


def test_the_committed_notebook_names_the_protodirsig_kernel():
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert nb["metadata"]["kernelspec"]["name"] == "protodirsig"


def test_the_reading_guide_section(executed):
    nb, out, _ = executed
    assert any(c.cell_type == "markdown" and c.source.startswith("---\n# 13 — Reading a space-to-space result")
               for c in nb.cells)
    guide = out.split("1. closed form:", 1)[1]
    for step in ("2. window against native:", "3. envelope: ", "4. SatSim controls against their DIRSIG counterparts:",
                 "5. not stated by any spec:"):
        assert step in guide, step
    assert "s2s-hyperresolved-r100km-v0mps-e5ms-l0-z0-d0-w64: 0.9963 of" in guide
    assert "Specular facet: not in the generator's vocabulary" in guide and "Earth limb or albedo: not expressible" in guide
