# Round 42 state

- preflight: 2026-10-13T11:58:19-04:00; time cap 4 h, deadline 2026-10-13T15:58:19-04:00
- start: clean tree at 41405dc (round 41's last commit, "Close-out, round 41 D: ..."); ARCH_LOG's round 41 section has its OPEN list and final gate (2162 passed, 2 skipped)
- suite count at start (round 41 final gate): 2162 passed, 2 skipped
- commit trailer: Co-Authored-By alone
- report protocol: as round 20 (prompt_report.md, then outputs/relay/DONE)
- scratch (outside the repository): ~/r42scratch; gate script ~/r42scratch/gate.sh (suite in thirds, each its own background command)
- baseline suite at 41405dc, alone (in thirds, each its own background command): 636 + 503 + 1023 passed, 2 skipped = 2162 passed, 2 skipped (195 s, 220 s, 185 s). Slip: during thirds 2 and 3 untracked new files (scripts/study_build.py, docs/study/data/document_figures.csv) were in the tree; no tracked file was edited
- step A gate (thirds): 636 + 503 + 1107 passed, 2 skipped (189, 220, 183 s; the third grows by docs consistency's six checks over the 14 new study documents); 17 checks 0, study_build has no --check yet (C); core/snapshot diff empty
- step B gate (thirds): 636 + 503 + 1113 passed, 2 skipped; 17 checks 0 (study_build --check in C); core/snapshot diff empty
- step C gate (thirds): 626 + 530 + 1116 = 2272 passed, 2 skipped (176, 274, 182 s); 18 checks 0 incl. study_build --check; core/snapshot diff empty. (A first third ran before a claims-map label fix and was rerun.)
