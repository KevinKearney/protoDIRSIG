# Round 40 state

- preflight: 2026-10-13T09:00:47-04:00; time cap 4 h, deadline 2026-10-13T13:00:47-04:00
- start: clean tree at 3a580de (round 39's last commit, "Close-out, round 39 D: ..."); ARCH_LOG's round 39 section has its OPEN list and final gate (2101 passed, 2 skipped)
- commit trailer: Co-Authored-By alone
- report protocol: as round 20 (prompt_report.md, then outputs/relay/DONE)
- scratch (outside the repository): ~/r40scratch; gate script ~/r40scratch/gate.sh
- baseline suite at 3a580de, alone, no edits: 2101 passed, 2 skipped (9 min 25 s)
- step A: 9 SatSim control renders (each its own command, alone, 11.8-11.9 s; largest process <= 863,280 kB, tree <= 991,820 kB); 127 records
- step A gate 1: 1 failed (test_review_report: SatSim records in no s2s block); fix 1: rows in the unresolved and blur blocks
- step A gate (rerun): 2125 passed, 2 skipped (9 min 24 s, alone); sixteen checks 0 (159 specs, 127 records); core/snapshot diff empty
