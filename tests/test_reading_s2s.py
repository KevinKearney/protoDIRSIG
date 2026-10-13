"""The user manual's section 11, "Reading a space-to-space result" (round 41), and its glossary rows, against the
committed records, the envelope and the coverage map: every number it quotes is the records' and every case it calls
not expressible is an empty cell of the coverage map. Engine-free."""
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "User_manual.md"
GLOSSARY = ROOT / "docs" / "User_glossary.md"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


env = _load("s2s_envelope")
RECORDS = {r["spec"]: r for r in (json.loads(x) for x in (ROOT / "docs/data/s2s_results.jsonl").read_text().splitlines())}


def section():
    text = MANUAL.read_text(encoding="utf-8")
    assert "\n## 11. Reading a space-to-space result\n" in text
    return text.split("\n## 11. Reading a space-to-space result\n", 1)[1].split("\n## ", 1)[0]


def total(name):
    return RECORDS[name]["measured"] * RECORDS[name]["full_pixel"]


def test_the_section_follows_the_others_and_links_its_sources():
    text = MANUAL.read_text(encoding="utf-8")
    assert [int(n) for n in re.findall(r"^## (\d+)\.", text, re.M)] == list(range(1, 12))
    s = section()
    for target in ("s2s_envelope.md", "s2s_coverage.md", "Space_to_space_characterization.md",
                   "../notebooks/stage_06_space_to_space.ipynb"):
        assert f"]({target})" in s and (MANUAL.parent / target).is_file(), target
    assert "Section 11 says how to read one of those results." in text


def test_the_window_numbers_are_the_records():
    s = section()
    w = "-w64"
    for name, quoted in (("s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0", "0.9999"),
                         ("s2s-hyperresolved-r100km-v0mps-e5ms-l0-z0-d0", "0.9963"),
                         ("s2s-unresolved-r25km-v0mps-e5ms-l0-z0-d0", "0.9866")):
        assert f"{total(name + w) / total(name):.4f}" == quoted and quoted in s


def test_the_envelope_table_is_the_envelopes():
    s = section()
    rows = {(e["size"], e["motion"], e["labelled"]): e for e in env.envelope()}
    pct = lambda d: f"{100 * d:.1f}"                                              # noqa: E731
    assert pct(rows[("2 to 6", "both", True)]["flux"][0]) == "3.7" and "3.7 % (3.06 px)" in s
    assert pct(rows[("6 to 13", "both", True)]["flux"][0]) == "1.3" and "1.3 % (6.12 px)" in s
    assert pct(rows[("1 to 2", "target", True)]["flux"][0]) == "12.7" and "12.7 % (1.22 px)" in s
    assert pct(rows[("0.5 to 1", "target", True)]["flux"][0]) == "22.2" and "22 % (0.61 px)" in s
    assert pct(rows[("0.3 to 0.5", "fixed", False)]["flux"][1]) == "68.0" and "68 % low" in s
    assert all(abs(d) <= 0.01 for d in rows[("over 13", "fixed", True)]["flux"]) and "| over 13 px, still | within 1 % |" in s
    for size in ("2 to 6", "6 to 13", "over 13"):                 # still or one motion: flux within about 1 %
        for motion in ("fixed", "platform", "target"):
            e = rows[(size, motion, True)]
            assert max(abs(d) for d in e["flux"]) <= 0.0111 or (size, motion) == ("6 to 13", "fixed"), (size, motion)
    beyond = sorted(r["spec"] for r, a, key, _ in env.rows_of_records() if key == ("6 to 13", "fixed", True)
                    and abs(1 - r["ratio"]) > 0.0111)               # the two exceptions the table names
    assert beyond == ["s2s-hyperresolved-r100km-v0mps-e5ms-l60-z0-d0-w64", "s2s-hyperresolved-r100km-v0mps-e5ms-l60-z0-d0p5-w64",
                      "s2s3-phase-hyperresolved-a120-r100km-l60-z60-w64"]
    assert [f"{100 * abs(1 - RECORDS[n]['ratio']):.1f}" for n in beyond] == ["2.7", "2.3", "2.3"]
    assert "| 2.3 to 2.7 % low; 2.3 % high |" in s
    corner = [RECORDS[f"s2s-unresolved-r25km-v0mps-e5ms-l{a}-z0-d0-w64"]["ratio"] for a in (45, 50, 55, 60, 65)]
    assert f"{100 * (1 - max(corner)):.1f}" == "7.5" and f"{100 * (1 - min(corner)):.1f}" == "12.5"
    assert "7.5 to 12.5 % low" in s


def test_the_satsim_numbers_are_the_records():
    s = section()
    sat = [r for r in RECORDS.values() if r["family"] == "satsim"]
    assert max(abs(r["ratio"] - 1) for r in sat) < 6.5e-6 and "to 6e-6" in s
    st = [m["ratio"] for r in sat for m in r["also"] if m["method"] == "streak_length"]
    assert f"{min(st):.3f}" == "0.994" and f"{max(st):.3f}" == "0.998" and "0.994 to 0.998" in s
    dirsig = [next(m for m in RECORDS[n]["also"] if m["method"] == "streak_length")["ratio"]
              for n in ("s2s2-blur-target-e5ms", "s2s2-blur-target-e20ms", "s2s2-blur-target-r100km-e20ms-w64")]
    assert f"{min(dirsig):.3f}" == "0.974" and f"{max(dirsig):.3f}" == "0.976" and "0.974 to 0.976" in s


def test_what_is_not_expressible_is_the_coverage_maps():
    s = section()
    cov = env.cov
    assert "a specular facet" in s and cov.EMPTY[("Specular facet", "resolved")].startswith("not in the generator's")
    assert "an Earth limb or albedo background" in s and cov.EMPTY[("Earth limb or albedo", "resolved")].startswith(
        "not expressible")
    assert "a fixed path count per pixel" in s
    assert "### Candidate ask: a per-pixel path count in `dirsig-engine` (round 40)" in (ROOT / "BACKLOG.md").read_text()


def test_the_glossary_rows():
    text = GLOSSARY.read_text(encoding="utf-8")
    for term in ("closed form, ratio", "native size, `-w64`", "path count, adaptive sampling", "sampling-effect envelope",
                 "SatSim control"):
        assert f"| {term} |" in text, term


def test_the_streak_row_is_the_envelopes():
    s = section()
    rows = {r["spec"]: a for r, a, _, _ in env.rows_of_records()}
    long = [1 - m["ratio"] for r in RECORDS.values() if r["family"] == 2 and rows[r["spec"]]["size_px"] >= 6
            for m in r["also"] if m["method"] == "streak_length" and m["expected"] and m["expected"] >= 6]
    assert f"{100 * min(long):.1f}" == "1.9" and f"{100 * max(long):.1f}" == "3.4" and "1.9 to 3.4 % short" in s
