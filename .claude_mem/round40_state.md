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
- step B: 6 DIRSIG renders (5 + the look-60 off-corner control), each its own command, 1.4-3.5 s, dirsig5 <= 129,164 kB; 133 records. Slip: the first (look 60) ran as a foreground command (output to its file)
- step B gate: 2129 passed, 2 skipped (9 min 28 s, alone); sixteen checks 0 (165 specs, 133 records, coverage 124); core/snapshot diff empty
- step C: BACKLOG candidate ask (per-pixel path count) and a CONOPS pointer; no render
- step C gate: 2129 passed, 2 skipped (9 min 30 s, alone); sixteen checks 0; core/snapshot diff empty
