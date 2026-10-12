# Round 20 state

- preflight: 2026-10-11T21:52:21-04:00; time cap 4 h, deadline 2026-10-12T01:52:21-04:00
- start: clean tree at 3dd039b (round 19's last commit, "Documents: SatSim reference run, ..."); round 19's ARCH_LOG final gate and OPEN list present
- suite at start: 1532 passed, 2 skipped (8 min 20 s, LightCurve1 probe renders running alongside)
- commit trailer: Co-Authored-By alone (the attribution reminder supplies no Claude-Session line)

## Markers at start (backticked unless noted; counts per file)

| File | `built` | `built, partial` | `proposed` | `open` | `planned` | unbackticked "proposed" (marker-like) |
|---|---|---|---|---|---|---|
| docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md | 37 | 8 | 79 | 10 | 0 | 6 (legend prose, three layout-block comments, C-21 and C-22 "Proposed:") plus 1 prose ("conventions, proposed for") |
| api/README.md | 1 | 0 | 1 | 0 | 0 | 1 (Status line) |
| api/operations.md | 1 (+12 Status cells `built`, unbackticked) | 0 | 2 | 0 | 0 | 7 |
| api/requirements.md | 0 | 0 | 0 | 0 | 0 | 1 (Status line) |
| api/openapi.yaml | 0 | 0 | 0 | 0 | 0 | 3 |
| api/schemas/*.json (descriptions) | 0 | 0 | 2 | 0 | 0 | 5 |
| README.md | 0 | 0 | 0 | 0 | 0 | 1 |
| BACKLOG.md | 0 | 0 | 1 | 0 | 0 | 4 |

The prompt's "3 uses of planned" in the CONOPS: none is a marker at HEAD (one prose "planned in BACKLOG.md"); counted 0.
- step 2+3: committed f3d709b; 1563 passed, 2 skipped
- step 4: committed 67abf29; 1568 passed, 2 skipped
- step 7: dropped (both single-thread LightCurve1 renders timed out at 1873 s, ~62 % of outputs)

## Report protocol (round 20; later prompts may say "report protocol as round 20")

- At the end of a round, write the final report to `prompt_report.md` at the repository root (gitignored, never committed), with these sections in this order: commits table (hash, step, suite count); gates; what was proved and not proved; judgment calls; OPEN; tests edited (assertion changes versus import-only); time used; the exact `git push` instruction (the round never pushes; a hook blocks it).
- Then, last, write `outputs/relay/DONE` (create `outputs/relay/` if absent; `outputs/` is gitignored): one line, `<round id> <tip commit hash> <ISO 8601 timestamp> <outcome>`, outcome one of `complete`, `stopped`, `partial`. Example: `round20 67abf29... 2026-10-11T23:59:00-04:00 complete`.
- If the round stops early (a failed preflight, a restored step that stops later steps, the time cap), still write both files, with outcome `stopped` (nothing after the stop point done) or `partial` (some later independent steps done).
- The relay script waits for `outputs/relay/DONE`; its presence is the completion signal, so nothing may write it before `prompt_report.md` is complete.
- Also print the final report in the terminal as the round's last message.
- step 5: committed 2190beb; 1575 passed, 2 skipped
- step 6: report protocol recorded above; final gate 1575 passed, 2 skipped
