# Round 37 state

- preflight: 2026-10-13T04:36:08-04:00; time cap 4 h, deadline 2026-10-13T08:36:08-04:00
- start: clean tree at 3fa0a02 (round 36's last commit, "Close-out, round 36 D: ..."); ARCH_LOG's round 36 section has its OPEN list and final gate (1857 passed, 2 skipped)
- commit trailer: Co-Authored-By alone
- report protocol: as round 20 (prompt_report.md, then outputs/relay/DONE)
- scratch (outside the repository): ~/r37scratch; gate script ~/r37scratch/gate.sh
- baseline suite at 3fa0a02, alone, no edits: 1857 passed, 2 skipped (9 min 19 s)
- step A: docs/Review_report_since_r27.md (18 generated blocks), scripts/review_report.py (--check, --print), tests/test_review_report.py (11 cases), CONOPS Part I pointer, README scripts entry
- step A gate: 1868 passed, 2 skipped (9 min 17 s, alone); fifteen checks 0 (review_report 18 blocks); core and snapshot unchanged
- step C renders so far (one at a time, between gates): foxbat --threads 1, two invocations (590 s stop, then 3 min 47 s); peak RSS 552,652 kB (scene2hdf), 196,564 kB (dirsig5)
- step C renders: foxbat at the default thread count with the noise-floor repeat, one invocation, 5 min 0 s, peak RSS 576,292 kB (scene2hdf); all of C's renders done (three commands, one at a time, none during a suite)
- step B: tests/test_docs_consistency.py (200 cases over 34 committed documents); stage_01 markdown cell 0 and a comment in cell 2 corrected; report section 7; CONOPS Part I sentence
- step B gate, first run: 2 failed (tests/test_status_markers.py: the report's section 7 cited the retired C-13); fix attempt 1: reworded to "id 13", and the consistency test no longer allows a retired id (stricter, matching status_markers)
- step B gate: 2068 passed, 2 skipped (9 min 18 s, alone); fifteen checks 0; core and snapshot unchanged
