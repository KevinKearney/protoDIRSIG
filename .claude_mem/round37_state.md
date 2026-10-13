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
