# Round 39 state

- preflight: 2026-10-13T07:39:22-04:00; time cap 4 h, deadline 2026-10-13T11:39:22-04:00
- start: clean tree at e93c508 (round 38's last commit, "Close-out, round 38 D: ..."); ARCH_LOG's round 38 section has its OPEN list and final gate (2090 passed, 2 skipped)
- commit trailer: Co-Authored-By alone
- report protocol: as round 20 (prompt_report.md, then outputs/relay/DONE)
- scratch (outside the repository): ~/r39scratch; gate script ~/r39scratch/gate.sh
- baseline suite at e93c508, alone, no edits: 2090 passed, 2 skipped (9 min 22 s)
- step A: hyp (2) re-measure (no render); renders: scratch both-e5ms-w64 at fixed 1000 paths (93 s), 20 paths seed 1 and 2; committed s2s2-blur-both-e5ms-n2-w64 (byte-identical), s2s2-blur-target-r100km-e20ms-w64; scratch r100km at 1000 paths. Six renders. Peaks <= 129,472 kB.
- slip: the r100km-1000-path and 20-path-seed-2 scratch renders ran in one background command (sequentially, one at a time)
- step A gate: 2093 passed, 2 skipped (9 min 20 s, alone); sixteen checks 0 (s2s_scenarios 135 specs, s2s_measure 103 records)
- step B: 8 renders (look 15, 45, 50, 55, 65 at the corner; look 60 at offsets 0.25, 0.5; unlabelled at 60), each its own command, 1.5-1.8 s, peaks <= 128,860 kB; 111 records
- step B gate: 2095 passed, 2 skipped (9 min 25 s, alone); sixteen checks 0 (143 specs, 111 records)
