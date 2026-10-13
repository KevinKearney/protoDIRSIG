# Round 41 state

- preflight: 2026-10-13T10:18:31-04:00; time cap 4 h, deadline 2026-10-13T14:18:31-04:00
- start: clean tree at f8ce601 (round 40's last commit, "Close-out, round 40 D: ..."); ARCH_LOG's round 40 section has its OPEN list and final gate (2129 passed, 2 skipped)
- commit trailer: Co-Authored-By alone
- report protocol: as round 20 (prompt_report.md, then outputs/relay/DONE)
- scratch (outside the repository): ~/r41scratch; gate script ~/r41scratch/gate.sh
- baseline suite at f8ce601, alone, no edits: 2129 passed, 2 skipped (9 min 28 s)
- step A: 8 DIRSIG renders (each its own background command, alone, 1.7-4.2 s, dirsig5 <= 129,540 kB); the 8th (both group, 50 km) ran off the 64 px window (my footprint arithmetic: 1.634 m at 50 km, not 2.04), spec and record dropped; 7 kept, 139 records, 172 specs
- slip: a waiter `until ! pgrep -f ...` matched its own command line and hung 10 min; then `pkill -f` killed its own shell (exit 144); no render affected
- step A gate: 2140 passed, 2 skipped (9 min 58 s, alone: near the 10 min background cap; later gates split the suite in two halves); seventeen checks 0 (172 specs, 140 records, coverage 131, envelope 21 rows/110 records); core/snapshot diff empty
- step A, after the gate: the review report's s2s_measure line said 139 records (counted before the last render); corrected to 140; re-checked with review_report --check and tests/test_review_report.py + test_docs_consistency.py (217 passed), not a second full suite
- step B: three defects fixed outside core (missing settings member named; absent black_level written as 0, so "omit it" holds; recipe file outside recipes/ composes via Workspace; engine-package wrong-hash messages print full digests); core hash messages and leo_pass_tahoe fidelity split stay (core; run id + snapshot); black-level message text unchanged (in the id snapshot)
- step B gate (split): half 1 666 passed, 1 skipped (5 min 16 s); half 2 1488 passed, 1 skipped (4 min 23 s): 2154 passed, 2 skipped; seventeen checks 0; core/snapshot diff empty. Found: docs consistency is parametrized over tracked docs, so A's gate did not run its 6 checks on docs/s2s_envelope.md (untracked then); they pass here
- step B, after the gate: the review report's suite count 2140 -> 2154 (a number only)
- step C gate 1: half 1 764 passed, 1 skipped; half 2 1 failed (tests/test_recipe_form.py::test_the_manual_states_what_the_prototype_is: section 10 assumed last); fix 1: the test finds section 10 by its heading (assertion changed, same three content checks)
- step C gate (rerun, split): 764 + 1398 passed, 1 + 1 skipped (2 min 19 s, 8 min 26 s): 2162 passed, 2 skipped; seventeen checks 0; core/snapshot diff empty; after it the review report's suite count 2154 -> 2162
- step D: review report prose (unresolved, blur), characterization pointer, README, BACKLOG round 41 item and pointer, ARCH_LOG round 41 with OPEN; final gate in thirds
- step D (final) gate: thirds 636+503+1023 passed, 2 skipped total; seventeen checks 0; core/snapshot diff empty
