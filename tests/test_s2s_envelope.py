"""The space-to-space sampling-effect envelope (`scripts/s2s_envelope.py`, `docs/s2s_envelope.md`): engine-free, from the
committed records."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


env = _load("s2s_envelope")
sm = _load("s2s_measure")


def test_the_committed_document_is_current_and_every_row_is_explained():
    assert env.problems() == []
    assert env.DOC.read_text() == env.document()


def test_every_dirsig_record_is_in_one_row_or_excluded_with_a_reason():
    rows = env.rows_of_records()
    assert len(rows) == sum(1 for r in sm.load_results() if r["family"] != "satsim")
    for r, a, key, why in rows:
        assert (key is None) != (why is None), r["spec"]
        if key is not None:
            assert a["size_px"] >= env.MIN_PX and key[0] == env.size_bin(a["size_px"])
    env_rows = env.envelope(rows)
    assert sum(e["records"] for e in env_rows) == sum(k is not None for _, _, k, _ in rows)


def test_the_rows_round_41_filled():
    keys = {(e["size"], e["motion"]) for e in env.envelope()}
    for cell in (("2 to 6", "fixed"), ("2 to 6", "platform"), ("2 to 6", "target"), ("2 to 6", "both"),
                 ("6 to 13", "platform"), ("0.5 to 1", "target")):
        assert cell in keys, cell


def test_the_combined_motion_deficit_grows_as_the_plate_shrinks():
    ratio = {r["spec"]: r["ratio"] for r in sm.load_results()}
    a, b, c = (1 - ratio[n] for n in ("s2s2-blur-both-e5ms-w64", "s2s2-blur-both-r100km-e20ms-w64",
                                      "s2s2-blur-both-r200km-e20ms-w64"))      # 24.48, 6.12 and 3.06 px
    assert abs(a) < 0.001 < b < c


def test_a_short_streak_is_fitted_in_its_column_sums_and_long_ones_as_before():
    import numpy as np
    for width in (6.12, 12.24, 24.48):          # every committed blur plate: central rows clear of the edges
        c = 32.0
        assert np.arange(int(c - width / 2) + 3, int(c + width / 2) - 2).size > 0
    img = np.zeros((64, 64))
    u = np.arange(64, dtype=float)
    prof = sm._swept_plate(u, 30.0, 3.06, 3.06)
    img[30:34] = prof                           # a 3.06 px tall plate: two full rows and two rows 0.53 covered
    img[30] *= 0.53
    img[33] *= 0.53
    assert abs(sm.streak_length(img, 3.06) - 3.06) < 0.01
