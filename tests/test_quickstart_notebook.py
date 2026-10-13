"""notebooks/quickstart_sdk.ipynb executed top to bottom, unedited, through `nbclient` (the `python3` kernel of this
environment; the stored kernelspec `protodirsig` is left as it is), with its work folder moved under the test's
temporary directory. The checks always; the two renders and the images when the notebook ran them, skipped with the
reason it printed otherwise (no DIRSIG engine), never passed without their output. Also its form: at most eight code
cells, each after one markdown sentence, no internal term in the markdown, and the glossary and the table of messages
linked before the first SDK message appears. Notebook 5 keeps its code cells and outputs, with one pointer cell on top."""
import json
import os
import re
import time
from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat", reason="executing a notebook needs nbformat")
nbclient = pytest.importorskip("nbclient", reason="executing a notebook needs nbclient")

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "quickstart_sdk.ipynb"
STAGE05 = ROOT / "notebooks" / "stage_05_sdk_auror_demo.ipynb"
LIMIT_S = 300
INTERNAL = ("run spec", "run id", "provenance", "engine block", "admission", "adapter", "layer", "content hash")


@pytest.fixture(scope="module")
def executed(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("quickstart")
    nb = nbformat.read(str(NOTEBOOK), as_version=4)
    saved = {k: os.environ.get(k) for k in ("QUICKSTART_WORK", "MPLBACKEND")}
    os.environ["QUICKSTART_WORK"] = str(tmp / "work")
    os.environ.pop("MPLBACKEND", None)                      # the inline backend, so the images are output
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
    code = [c for c in nb.cells if c.cell_type == "code"]
    texts = ["".join(o.get("text", "") for o in c.outputs if o.get("output_type") == "stream") for c in code]
    images = [sum(o.get("output_type") == "display_data" and "image/png" in o.get("data", {}) for o in c.outputs)
              for c in code]
    yield texts, images, wall


def _skip_unless_rendered(out):
    reason = next((ln for ln in out.splitlines() if ln.startswith("SKIPPED: running needs DIRSIG")), None)
    if reason:
        pytest.skip(reason)


def test_the_notebook_runs_within_the_limit(executed):
    assert executed[2] < LIMIT_S, f"{executed[2]:.0f} s"


def test_the_checks(executed):
    texts = executed[0]
    assert texts[0].startswith("DIRSIG ready: ")
    assert "'roi': {'Width': 16, 'Height': 16" in texts[1] and "sensor  : auror-nir.yaml" in texts[1]
    assert texts[2] == "ready to run: True\n"
    assert texts[5].splitlines()[-1] == "ready to run: True"


def test_two_renders_and_their_images(executed):
    texts, images, _ = executed
    out = "\n".join(texts)
    _skip_unless_rendered(out)
    assert texts[3] == "result: rendered | complete? complete\n"
    assert texts[4].startswith("lines, samples, bands: (16, 16, 1) | mean: ") and images[4] == 1
    assert texts[6] == "result: rendered | complete? complete\n" and images[6] == 1


def test_the_form_of_the_notebook():
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cells = nb["cells"]
    assert nb["metadata"]["kernelspec"]["name"] == "protodirsig"
    code = [i for i, c in enumerate(cells) if c["cell_type"] == "code"]
    assert 1 <= len(code) <= 8
    for i in code:                                           # one sentence before each code cell, saying what to change
        before = "".join(cells[i - 1]["source"])
        assert cells[i - 1]["cell_type"] == "markdown" and before.count(". ") == 0 and before.endswith(".")
        assert "change" in before.lower()
    markdown = "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "markdown").lower()
    for term in INTERNAL:
        assert term not in markdown, term
    first_message = next(i for i, c in enumerate(cells) if c["cell_type"] == "code" and "validate" in "".join(c["source"]))
    before = "".join("".join(c["source"]) for c in cells[:first_message])
    assert "(../docs/User_glossary.md)" in before and "(../docs/User_manual.md#7-when-the-sdk-refuses)" in before


def test_the_message_table_anchor_exists():
    manual = (ROOT / "docs" / "User_manual.md").read_text(encoding="utf-8")
    assert "\n## 7. When the SDK refuses\n" in manual


def test_notebook_five_points_to_the_quick_start_and_is_otherwise_unchanged():
    nb = json.loads(STAGE05.read_text(encoding="utf-8"))
    top = nb["cells"][0]
    assert top["cell_type"] == "markdown"
    text = "".join(top["source"])
    assert "(quickstart_sdk.ipynb)" in text and "(../docs/User_manual.md)" in text
    assert "".join(nb["cells"][1]["source"]).startswith("# Stage 05")
    assert sum(c["cell_type"] == "code" for c in nb["cells"]) == 11
