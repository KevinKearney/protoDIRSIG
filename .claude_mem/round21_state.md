# Round 21 state

- preflight: 2026-10-11T23:08:01-04:00; time cap 4 h, deadline 2026-10-12T03:08:01-04:00
- start: clean tree at 8272643 (round 20's last commit); memory 10 GB total, about 7 GB available at start; disk 351 GB free
- commit trailer: Co-Authored-By alone
- step C probe started 2026-10-11T23:08:15-04:00: `setsid nohup timeout 120m python scripts/probe_determinism.py --work ~/.local/state/protodirsig/r21-lightcurve --results ~/.local/state/protodirsig/sweeps/r15-20261011/sweep/results.jsonl --demos LightCurve1 --conditions C1 --timeout 3900`; PID 733969 (`timeout`, process-group leader, pgid 733969), python child 733970; output `~/.local/state/protodirsig/r21-lightcurve/probe.out`. Two single-thread renders one after the other (C1 rep 1 then rep 2), never concurrent; 120-minute cap on the whole process, 65 minutes per render.
- step A: gate 1575 passed, 2 skipped (second run; first failed on a C-n citation in api/README)
