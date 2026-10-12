# Round 30 state

- preflight: 2026-10-12T13:41:32-04:00; time cap 4 h, deadline 2026-10-12T17:41:32-04:00
- start: clean tree at 91ebb4f (round 29's last commit, "Round 29 log: final gate and OPEN list")
- commit trailer: Co-Authored-By alone
- report protocol: as round 20 (prompt_report.md, then outputs/relay/DONE)
- baseline suite at 91ebb4f, alone, no edits: 1684 passed, 2 skipped (7 min 46 s)
- scratch (outside the repository): ~/r30scratch (measure.py, diag_conv.py, gate.sh, results/, work/, home/)
- 13:58 first native render done (static 83.7 s); image: scene +x toward decreasing column, scene -y toward increasing row
- A design notes: family II in a second generated scene s2s_blur (family I's scene and 63 specs untouched). First layout (background 25 km below the targets at z=-25 km, then at z=0 with targets at 25 km) rendered no background: probes (16x16, truth) show a background more than ~20 km along the ray inside the scene is not hit: from 20 km visible, from 21 km the pixel takes 1 path, earth core fraction 1, status 4 (radiance 0); with --disable_earth_core: void fraction 1, 20 paths. Same threshold (20 vs 21 km) with the background raised 10 km. Layout used: background 10 km behind the targets, targets at the top of the scene.
- orbit pair (0.1 and 20 ms): same 28 pixels lit, sum ratio 200.0: LookAt holds the plate over the exposure
- A renders (native, one per process): 15 (static, 12 moving, orbit pair) ~30 min render; diagnostics: probes d_pz*, d2-d8 (16 to 128 px, seconds each)
- A, a first batch killed both-e20ms at the per-render 170 s timeout (no result used); each later render ran as its own background command
- A judgment: family II's look and orbit groups are in the same generated scene and specs as the blur groups (one asset), committed with step A; B adds the look measurements
- step A: gate 1689 passed, 2 skipped (7 min 46 s, alone); eleven checks 0; boundary 23 passed; core and snapshot unchanged
- B renders: 6 native look renders (~8 min) + one native truth render of l75 (35 s)
- step B: gate 1690 passed, 2 skipped (7 min 55 s, alone); eleven checks 0; boundary 23 passed; core and snapshot unchanged
- C: about 6 min render (16x16 variations, 5 native 100/50 km seed renders, one 82 s 4000-path render); all three explained with observed causes
- step C: gate 1690 passed, 2 skipped (8 min 11 s, alone); eleven checks 0; boundary 23 passed; core and snapshot unchanged
