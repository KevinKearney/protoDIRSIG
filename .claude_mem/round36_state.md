# Round 36 state

- preflight: 2026-10-13T02:53:45-04:00; time cap 4 h
- start: clean tree at 8a59ceda0ca171c54846f57bb91bc7448e478bfe (round 35's last commit, "Close-out, round 35 E: ..."); ARCH_LOG's round 35 section has its OPEN list and final gate (1835 passed, 2 skipped)
- commit trailer: Co-Authored-By alone
- report protocol: as round 20 (prompt_report.md, then outputs/relay/DONE)
- scratch (outside the repository): ~/r36scratch
- baseline suite at 8a59ced, alone, no edits: 1835 passed, 2 skipped (8 min 52 s)
- step A: docs/Bigger_host_plan.md (inventory, 7 entries), CONOPS 7.3 resource-slots pointer, README docs list
- step A gate: 1835 passed, 2 skipped (8 min 49 s, alone); thirteen checks 0; core and snapshot unchanged
- step B: scripts/bigger_host_run.py, docs/data/bigger_host_manifest.yaml (7 entries), tests/data/bigger_host_fake_manifest.yaml, tests/test_bigger_host_run.py (24 incl. parametrized); s2s_measure.check accepts a file outside the repo; risk_measure treats *-limit-model as the model; tests/test_risk_measurements.py reads round 33's records only (assertion scope changed)
- step B gate: 1857 passed, 2 skipped (9 min 16 s, alone); fourteen checks 0 (bigger_host_run 7 entries); core and snapshot unchanged
