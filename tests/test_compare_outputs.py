"""scripts/compare_outputs.py on synthetic ENVI images and text (no DIRSIG, no demo)."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("compare_outputs", ROOT / "scripts" / "compare_outputs.py")
co = importlib.util.module_from_spec(spec)
spec.loader.exec_module(co)

HDR = """ENVI
description = {{DIRSIG image, created {when}}}
samples = {s}
lines = {l}
bands = {b}
header offset = 0
data type = {t}
interleave = {il}
byte order = {bo}
band names = {{
 band 1,
 band 2}}
"""


def envi(d, name, arr, when="Sun Oct 11 03:06:39 2026", il="bsq", dtype="<f4", t=4):
    """Write `arr` (bands, lines, samples) as `<name>.img` with `<name>.img.hdr`."""
    d.mkdir(parents=True, exist_ok=True)
    b, l, s = arr.shape
    data = {"bsq": arr, "bil": arr.transpose(1, 0, 2), "bip": arr.transpose(1, 2, 0)}[il]
    data.astype(dtype).tofile(d / f"{name}.img")
    (d / f"{name}.img.hdr").write_text(HDR.format(when=when, s=s, l=l, b=b, t=t, il=il,
                                                  bo=1 if dtype.startswith(">") else 0))


@pytest.fixture
def img():
    rng = np.random.default_rng(7)
    return (rng.random((2, 8, 10)) * 100 + 1).astype(np.float32)


@pytest.mark.parametrize("il, dtype", [("bsq", "<f4"), ("bil", "<f4"), ("bip", ">f4"), ("bsq", "<f8")])
def test_read_envi_by_its_header(tmp_path, img, il, dtype):
    envi(tmp_path, "x", img, il=il, dtype=dtype, t=5 if dtype.endswith("8") else 4)
    got = co.read_envi(tmp_path / "x.img")
    assert got.shape == (2, 8, 10) and np.array_equal(got, img.astype(np.float64))
    assert co.read_header(tmp_path / "x.img.hdr")["band names"] == "band 1,  band 2"


def _classes(tmp_path, mask=()):
    return {r["name"]: r for r in co.headers_only(co.compare_dirs(tmp_path / "a", tmp_path / "b", mask))}


def test_identical_and_metadata_only(tmp_path, img):
    envi(tmp_path / "a", "x", img)
    envi(tmp_path / "b", "x", img, when="Mon Oct 12 04:00:00 2026")
    r = _classes(tmp_path)
    assert r["x.img"]["class"] == "identical" and r["x.img.hdr"]["class"] == "metadata"


def test_float_order_and_sampling_noise_are_told_apart(tmp_path, img):
    small = img * (1 + 3e-7 * np.sign(np.random.default_rng(1).standard_normal(img.shape))).astype(np.float32)
    noisy = img + np.random.default_rng(2).normal(0, 1.0, img.shape).astype(np.float32)
    envi(tmp_path / "a", "x", img)
    envi(tmp_path / "a", "y", img)
    envi(tmp_path / "b", "x", small)
    envi(tmp_path / "b", "y", noisy)
    r = _classes(tmp_path)
    assert r["x.img"]["class"] == "float-order" and r["x.img"]["max_value_rel"] <= co.FLOAT_ORDER_REL
    assert r["y.img"]["class"] == "sampling-noise"
    y = r["y.img"]
    assert 0.5 < y["rms"] < 1.5 and y["rms_rel"] == pytest.approx(y["rms"] / y["signal_rms"])
    assert y["fraction_values_differ"] > 0.9 and y["fraction_pixels_differ"] == pytest.approx(1.0)
    assert r["x.img.hdr"]["class"] == "identical"


def test_a_truth_image_with_one_different_hit_is_sampling_noise(tmp_path):
    ids = np.zeros((1, 4, 4), dtype=np.float32)
    other = ids.copy()
    other[0, 2, 3] = 5
    envi(tmp_path / "a", "t", ids)
    envi(tmp_path / "b", "t", other)
    t = _classes(tmp_path)["t.img"]
    assert t["class"] == "sampling-noise" and t["fraction_pixels_differ"] == pytest.approx(1 / 16)


def test_text_masks_paths_dates_and_pids(tmp_path):
    a = "run /home/u/.local/state/r16/runs/X/C0-1/output/demo.img at 2026-10-11T03:06:39Z pid 4411\nvalue 1.5\n"
    b = "run /home/u/.local/state/r16/runs/X/C0-2/output/demo.img at 2026-10-11T03:07:02Z pid 4502\nvalue 1.5\n"
    lines, worst = co.text_diff(a, b)
    assert lines == [] and worst is None
    assert co.mask("C0-1 started 11:22:33", ["C0-1"]) == "<mask> started <time>"
    assert co.mask("~/Documents/DIRSIG/cache and Mon Oct  5 01:02:03 2026") == "<path> and <datetime>"


@pytest.mark.parametrize("a, b, cls", [
    ("t 1.000000 2.0\n", "t 1.000001 2.0\n", "float-order"),
    ("t 1.0 2.0\n", "t 1.1 2.0\n", "sampling-noise"),
    ("state ok\n", "state failed\n", "sampling-noise"),
    ("t 1.0\n", "t 1.0\nextra 2\n", "sampling-noise"),
])
def test_text_differences_are_classified_by_their_numbers(tmp_path, a, b, cls):
    for side, text in (("a", a), ("b", b)):
        (tmp_path / side).mkdir()
        (tmp_path / side / "data_recorder.txt").write_text(text)
    assert _classes(tmp_path)["data_recorder.txt"]["class"] == cls


def test_binary_files_and_missing_files(tmp_path):
    for side, data in (("a", b"\0\1\2"), ("b", b"\0\1\3")):
        (tmp_path / side).mkdir()
        (tmp_path / side / "demo.bin").write_bytes(data)
    (tmp_path / "a" / "only_a.txt").write_text("x")
    r = _classes(tmp_path)
    assert r["demo.bin"]["class"] == "unclassified" and r["only_a.txt"]["class"] == "only in A"


def test_main_exit_status(tmp_path, img, capsys):
    envi(tmp_path / "a", "x", img)
    envi(tmp_path / "b", "x", img)
    assert co.main([str(tmp_path / "a"), str(tmp_path / "b")]) == 0
    envi(tmp_path / "b", "x", img + 1)
    assert co.main([str(tmp_path / "a"), str(tmp_path / "b"), "--json"]) == 1
    assert '"sampling-noise"' in capsys.readouterr().out


def test_a_renumbered_label_band_is_an_index_relabel(tmp_path):
    rng = np.random.default_rng(3)
    labels = rng.integers(0, 6, size=(1, 30, 40)).astype(np.float32)
    other = np.choose(labels.astype(int), [3, 5, 0, 1, 4, 2]).astype(np.float32)   # the same labels, renumbered
    radiance = rng.random((1, 30, 40)).astype(np.float32)
    envi(tmp_path / "a", "t", np.concatenate([radiance, labels]))
    envi(tmp_path / "b", "t", np.concatenate([radiance, other]))
    t = _classes(tmp_path)["t.img"]
    assert t["class"] == "index-relabel"
    assert [(b["band"], b["class"], b["relabel_consistent"]) for b in t["bands"]] == [("band 2", "index-relabel", 1.0)]
    noisy = other.copy()
    noisy[0, :15, :] = rng.integers(0, 6, size=(15, 40))                          # half the pixels re-drawn
    envi(tmp_path / "b", "t", np.concatenate([radiance, noisy]))
    assert _classes(tmp_path)["t.img"]["class"] == "sampling-noise"


def test_relabel_consistency_is_none_for_non_integer_bands():
    a = np.array([[0.5, 1.0]])
    assert co.relabel_consistency(a, a + 1) is None
    assert co.relabel_consistency(np.array([[0.0, 1.0, 2.0]]), np.array([[5.0, 5.0, 5.0]])) == 0.0   # not a permutation
