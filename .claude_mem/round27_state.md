# Round 27 state

- preflight: 2026-10-12T08:38:36-04:00; time cap 4 h, deadline 2026-10-12T12:38:36-04:00
- start: clean tree at a04a007 (round 26's last commit, "Round 26 log: final gate and OPEN list")
- commit trailer: Co-Authored-By alone
- report protocol: as round 20 (prompt_report.md, then outputs/relay/DONE)
- baseline suite at a04a007, no edits while it ran: 1667 passed, 2 skipped (8 min 16 s). Rule slip: the step A dry-run measurement (mt_measure.py: one aborted layered job + 8 scene2hdf/dry-run variants) ran beside it; the prompt says "alone". The result equals round 26's final count.
- step A measurement (outside the repo, ~/.local/state/protodirsig/r27/diag/mtA/measure.json): values.img found in the working folder or the scene copy's mapdirectory (auror_ref/maps), not the scene copy's top; needs values.img.hdr or values.hdr beside it; roof_metal_gray.ems found in the working folder or the scene copy's top (emsdirectory $SCENE_DIR); errors raised by scene2hdf
- step A: gate 1672 passed, 2 skipped (9 min 3 s, step B's Polarization4 renders alongside); ten checks 0; id snapshot unchanged; committed 868fe66
- step B1: gate 1672 passed, 2 skipped (7 min 31 s); ten checks 0; id snapshot unchanged; committed 9e64088
- step B2: gate 1672 passed, 2 skipped (7 min 31 s); ten checks 0; id snapshot unchanged; committed 9e89c98
- step C: gate 1672 passed, 2 skipped (7 min 32 s); ten checks 0; id snapshot unchanged; committed 1128e18
- final gate: = C gate (1672 passed, 2 skipped); boundary tests 23 passed; id snapshot unchanged since a04a007
