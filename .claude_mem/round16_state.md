# Round 16 run state

- preflight: 2026-10-11T10:41:13-04:00
- deadline: 2026-10-11T18:41:13-04:00
- disk: / holds ~/.local/state and manifold_config_repo; 468 GB, 355 GB free at preflight; floor = min(20 GB, 46.8 GB) = 20 GB
- work root: /home/kevin-kearney/.local/state/protodirsig/r16 (probe/, repeats/)
- sweep results (r15): /home/kevin-kearney/.local/state/protodirsig/sweeps/r15-20261011/sweep/results.jsonl

## Steps
- preflight: done; baseline 889 passed, 2 skipped, 233.9 s
- dirsig5 --help: -j/--threads uint (thread count); -s/--random_seed int (random seed); --output_folder string, --output_prefix string (output location, plugin support needed); --run_info_filename/--log_info_filename; --thread_block_size uint
- step 1: committed f29f28a; suite 893 passed, 2 skipped, 233 s; checks 0
- step 2: committed; suite 898 passed, 2 skipped, 244 s; checks 0
- step 3: committed; suite 902 passed, 2 skipped, 241 s; checks 0 (gate fix 1: api examples regenerated)
- step 4: probe started 2026-10-11T11:18:12-04:00; work /home/kevin-kearney/.local/state/protodirsig/r16/probe; demos MaterialOverrides1,NestedMotion1,MoonSat2,StkImport1,CommandedMount2,PlatformJitter2
- step 4d: long SDA repeats started 2026-10-11T11:27:00-04:00, driver subshell pid 410085, work ~/.local/state/protodirsig/r16/repeats (sweep driver --repeat, --report '', disk floor 50 GB = 20 + 30)
- step 4: committed; suite 923 passed, 2 skipped, 246 s; checks 0; probe outputs deleted
