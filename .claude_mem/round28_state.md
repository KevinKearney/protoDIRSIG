# Round 28 state

- preflight: 2026-10-12T09:50:47-04:00; time cap 4 h, deadline 2026-10-12T13:50:47-04:00
- start: clean tree at 9ded055 (round 27's last commit, "Round 27 log: final gate and OPEN list")
- commit trailer: Co-Authored-By alone
- report protocol: as round 20 (prompt_report.md, then outputs/relay/DONE)
- baseline suite at 9ded055, alone, no edits: 1672 passed, 2 skipped (7 min 30 s)
- note: an external commit 0d8f874 "all night run" (Kevin Kearney, 10:09, pushed to origin) took step A's in-progress code, tests, survey and coverage/sweep reports and this file; not mine, not rewritten; step A's commit holds the rest
- step A: gate 1677 passed, 2 skipped (13 min 39 s; step B renders alongside, one at a time); ten checks 0; id snapshot and packages/core unchanged since 9ded055
- step B: eight rendered (TemperatureMap1, Brdf2, RossLi1, MaterialMap2, PointCollectors1, SubPixelObject1, FastCloud2, VertexNormals2; ~18.5 min of comparison renders plus diagnostics); gate 1677 passed, 2 skipped (7 min 50 s, alone); ten checks 0; id snapshot unchanged
- step C: gate 1677 passed, 2 skipped (8 min 34 s, alone); ten checks 0; boundary tests 23 passed; id snapshot and packages/core unchanged since 9ded055
