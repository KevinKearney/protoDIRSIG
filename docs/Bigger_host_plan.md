# Bigger host plan

The measurements that rounds 15 to 35 skipped, truncated or ran at reduced scale on the relay host (a 4-core, 8-thread i5-1135G7 laptop, 11.0 GiB MemTotal, a 10-minute limit per background command and a 4 GB limit on the summed memory of concurrent jobs), deferred to a larger host. Sources: the OPEN lists of rounds 29 to 35, `docs/data/risk_measurements.jsonl`, `BACKLOG.md` and the CONOPS. Times are wall times on the laptop unless stated; memory is peak resident set size of one job.

## Inventory

| # | Entry | From | Spec or script | Jobs | Threads per job | Peak memory per job | Time at native size | Disk | Results file (appends to) | Check |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `s2s-unlabelled-points` | round 29 OPEN 6, round 32 OPEN 4: the unlabelled plate's look, Sun, exposure and offset points, never rendered | 18 specs `manifold_run_specs/s2s/s2s-unresolvedplain-*` (at 200 km: exposure 1 and 20 ms, look 30 and 60, Sun 30 and 60, offsets 0.25, 0.5, 0.75; offsets 0.25, 0.5, 0.75 at 12.5, 25 and 50 km), 500 x 500; reductions of `scripts/s2s_measure.py` | 18 | 1 | 159,644 KiB (the 25 km plate job of the same scene, `risk_measurements.jsonl` B `native-n1`) | 4.3 s (200 km, 9 specs), 73.9 s (12.5 km, 3), 70.0 s (25 km, 3), 22.5 s (50 km, 3), from round 32's render of the zero-offset point at each range; 537.9 s summed | under 0.1 GB | `docs/data/s2s_results.jsonl`: 18 records (89 to 107) | `python scripts/s2s_measure.py --check` |
| 2 | `s2s-blur-both` | round 32 OPEN 4: family II's `both` blur group, past round 32's 60-minute cap | 4 specs `manifold_run_specs/s2s/s2s2-blur-both-e{0p1,1,5,20}ms.yaml`, 500 x 500 | 4 | 1 | not measured (family II's scene); measured by the runner's probe | 204 s at 20 ms (round 30); 121.8, 125.5, 139.6 s for the `platform` group at 0.1, 1, 5 ms (round 32); 591 s summed | under 0.1 GB | `docs/data/s2s_results.jsonl`: 4 records (to 111) | `python scripts/s2s_measure.py --check` |
| 3 | `concurrency-native` | round 33 risk B (N = 1, 2, 4, 8 on 4 cores; N stopped at 8), round 33 OPEN 5 | `s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0`, 500 x 500, N concurrent copies, each its own HOME and folder; N = 1, 2, 4, 8, 16, 32, 64 and the host's physical core count, N not above the cores | up to 8 batches | 1 per job, N per batch | 159,644 KiB | 70.7 s for one job; batches of 1, 2, 4, 8 took 70.7, 78.1, 113.2, 198.1 s | under 0.1 GB per job | `docs/data/risk_measurements.jsonl`: one risk B record per batch (`native-<host>-n<N>`) and one `native-<host>-limit-model` | `python scripts/risk_measure.py --check` |
| 4 | `lightcurve1-full` | round 33 risk E (LightCurve1 cut to samples 0 to 150), round 33 OPEN 4, BACKLOG "Determinism follow-ups" | LightCurve1 `box_spin.jsim` as shipped (840 samples), dirsig5 directly; renders `t1-a`, `t2-a`, `t2-b`, `t4-a`, `t4-b`, `td-a`, `td-b`, `td-c` (1, 2, 4 threads, DIRSIG's default); the 12 pairs of round 33 | 8 | 1, 2, 4, the host's hardware threads | not measured; measured by the runner's probe (one sample) | 691.9 s at the default 8 threads (demo sweep, round 15); about 40 min at one thread (round 33; round 20's one-thread render held about 62 % of its outputs at 1873 s); the cut's ratios 1 : 0.57 : 0.37 : 0.33 for 1, 2, 4, 8 threads | 13.5 GB per render (13,481 MB of outputs, demo sweep), 108 GB for 8 | `docs/data/risk_measurements.jsonl`: 12 risk E records (`lightcurve1-full-<host>-<a>-vs-<b>`) | `python scripts/risk_measure.py --check` |
| 5 | `capture-order-native` | round 33 risk D (element counts over 100 divided by 4: Thermal2 80 x 60, Polarization4 44 x 36, Fireball1 80 x 60), round 33 OPEN 1 (Thermal2's descending trigger times killed by the OOM killer) | Thermal2 `demo.sim`, Polarization4 `pi.sim`, Fireball1 `demo.sim` at the demos' own size, dirsig5 directly on the demo's files, one thread, seed 1: as authored, each capture alone, the captures reversed | 3 (7, 6 and 4 renders) | 1 | reduced size, as authored: 107,456, 257,276 and 107,436 KiB; Thermal2 reversed: 5,558,920 KiB anonymous RSS and 13,170,604 KiB virtual when killed 7 s after start (no limit); each render runs under an address-space limit of 24 GiB | demo sweep at the default 8 threads, as authored: 116.3, 244.3 and 6.1 s; reduced size at one thread: 30.2, 11.6 and 1.4 s | under 0.1 GB | `docs/data/risk_measurements.jsonl`: 3 risk D records (`<demo>-native`) | `python scripts/risk_measure.py --check` |
| 6 | `forest-layered-comparison` | round 32 OPEN 2: forest not compared, both forms past the 150 s render timeout | `scripts/compare_layered.py --source forest=<install>/Documents_Folder-07-Feb-2024/DIRSIG/scenes/forest:shots/rgb/rgb.sim --threads 1`, 1024 x 1024 RGB | 1 (3 renders, 5 when the layered image differs) | 1 | not measured | each of the first two renders over 150 s at the default thread count (cancelled); one thread about 3.5 times the default's wall (BACKLOG "Scenes Kevin transferred") | not measured | `<work>/forest-layered-comparison/forest/results.json` (`compare_layered.py`'s results file; round 32's numbers are in `docs/DIRSIG_transfer_scenes.md`) | `results.json` holds forest with a status other than `stopped` |
| 7 | `sweep-capped-demos` | CONOPS "Demo sweep": 2 simulation files hit the 1800 s cap | `scripts/sweep_demos.py --only FocusDistance1,SumoTraffic1 --per-run-timeout 21600`: FocusDistance1 `demo.jsim`, SumoTraffic1 `multi_frame.sim` | 2 | DIRSIG's default | not measured | over 1800 s each at the default 8 threads (cancelled at 1800.8 and 1800.3 s) | 1.96 GB in FocusDistance1's run directory at the cap | `<work>/sweep-capped-demos/demos/sweep/results.jsonl` (`sweep_demos.py`'s results file; round 15's digests are in `docs/data/demo_sweep_digests.jsonl.gz`) | a `demo` line per demo in `results.jsonl` |

Totals: 7 entries; 52 to 54 renders outside entry 3 (18 + 4 + 8 + 17 + 3 to 5 + 2) and entry 3's batches (1 + 2 + 4 + 8 + 16 + 32 + 64 = 127 copies on a host of 64 cores or more, plus a batch of the core count); the repository's two results files gain 22 s2s records and up to 24 risk records (9 B, 12 E, 3 D).

## Not in the manifest

| From | Measurement | Reason |
|---|---|---|
| round 34 OPEN 1 | foxbat through `compare_layered.py --threads 1` | not limited by the host (round 34 rendered nothing by its scope); run on this host in round 37, `docs/DIRSIG_layered_comparison.md` round ten |
| round 31 OPEN 4 | the hyperresolved sphere's converged residual (seeds at 64 x 64) | not limited by the host; no record schema holds seed variants of one spec |
| round 35 OPEN 5 | the manual's sweep and space-to-space examples at their shipped sizes | examples, not measurements; the space-to-space plate at 500 x 500 is in `s2s_results.jsonl` |
| round 32 OPEN 3 | MicroScene1, MegaScene1, LidarJungle, Trona, RITBusLoop | their `.scene` and material files are not on the host |

## Manifest and runner

`docs/data/bigger_host_manifest.yaml` holds one entry per row of the inventory (its driver, items, results file, check, `est_s` and, where an earlier round measured it, `peak_mib`); `scripts/bigger_host_run.py` runs it.

| Item | Rule |
|---|---|
| Host | physical cores (unique core ids in `/proc/cpuinfo`, at most the CPUs the process may use), MemTotal and MemAvailable (`/proc/meminfo`) |
| Peak memory of one job | `<work>/peaks.json` if cached, else the manifest's `peak_mib`, else the entry's smallest instance (`probe`) run alone and its peak RSS read from `wait4`, then cached; `capture-order-native`: its address-space limit (24 GiB) |
| Concurrency | min(cores / threads per job, floor(0.75 x MemAvailable / (1.25 x peak))), at least 1, at most `--max-jobs` and the entry's own cap (`concurrency-native`: 1, its batches are the concurrency); an item over the budget alone or over the cores is "exceeds host" and not run; an item at DIRSIG's default thread count runs alone |
| Jobs | one process each (`_job`), one thread unless the item states more, `HOME` a folder of its own under `<work>/<entry>/`, `DIRSIG_HOME` from the runner |
| Order | entries one after another, in manifest order; items of one entry concurrently |
| Results | written by the runner alone as each job ends: `s2s_results.jsonl` with `s2s_measure.py`'s record, `risk_measurements.jsonl` with `risk_measure.py`'s (checked before writing); `command` entries keep their script's own results file under the work root |
| Resume | an item whose result is in the results file is skipped; an entry with all its results is skipped; a killed invocation loses the jobs in flight only; SIGTERM stops the jobs in flight and exits 130 |
| Log | `<work>/runner.log`, one JSON object per event (probe, peak, start, job-start, job-end, recorded, record-failed, exceeds-host, skip, killed, interrupted, end) |
| `--dry-run` | the plan for this host and, with `--assume-cores N --assume-mem-gb M`, for a host of N cores and M GB (MemAvailable 0.9 x M); nothing run, probed or written |
| `--only NAME[,NAME]` | these entries only |
| `--check` | the manifest is well formed, its drivers and items known, its results files the repository's, every entry named in this document |

Tests: `tests/test_bigger_host_run.py` (the dry run on assumed hosts, the concurrency rule, the stub driver `sleep` for concurrency, resume, an interrupted invocation (SIGKILL and SIGTERM), the probe and a failed job; the capture, light-curve and command drivers on synthetic files; the fake two-entry manifest `tests/data/bigger_host_fake_manifest.yaml` of 16 x 16 jobs when DIRSIG is installed).

## Validation on the 4-core laptop (round 36)

The fake manifest `tests/data/bigger_host_fake_manifest.yaml` (two entries: three family I specs, and risk B batches of 1 and 2 copies, all cut to 16 x 16, results under the work root) run with `--max-jobs 4 --max-mem-gb 4`, one invocation at a time, nothing else running:

| Invocation | Exit | Events | Results |
|---|---|---|---|
| first | 0 | 2 probes (peaks 128,396 and 128,480 KiB), 3 jobs (2 s2s jobs together, then the batch of 2), 5 recorded | 3 s2s records, 3 risk B records (n1, n2, limit model); `s2s_measure.check` and `risk_measure.check` on them: no problem; both batches' images equal the single job's |
| second, same work root | 0 | 2 skips ("results present"), 0 jobs, 0.2 s | unchanged |
| first, SIGKILL after the first record | 137 | the probe recorded | 1 s2s record |
| resume | 0 | 1 probe, 3 jobs (the 2 s2s items left and the batch of 2) | 3 + 3 records, image digests equal to the first invocation's |
| first, SIGTERM after the first record | 130 | the probe recorded, `interrupted` logged, the jobs in flight stopped | 1 s2s record |
| resume | 0 | 1 probe, 3 jobs | 3 + 3 records, image digests equal to the first invocation's |

### Plans (`--dry-run`, round 36, results files at 28d8093)

As printed in round 36. Round 43 lowered `capture-order-native`'s `est_s` (3600, 2199 and 55 s to 998, 2712 and 69 s); a dry run now prints that entry at 3779, 2712 and 2712 s on the three assumed hosts and the totals 15416, 14547 and 14745 s, as the run instructions' table below.

This host:

Host (this host): 4 cores, 8 hardware threads, MemTotal 11.0 GiB, MemAvailable 7.3 GiB; memory budget 75% of MemAvailable, a job counts 1.25 x its peak

| Entry | Driver | Items (pending / done / exceeds host) | Threads per job | Peak per job (source) | Concurrency | Estimated wall (s) | Disk (GB) |
|---|---|---|---|---|---|---|---|
| s2s-unlabelled-points | s2s | 18 (18 / 0 / 0) | 1 | 156 MiB (manifest: risk B native-n1, the 25 km plate job in the same scene) | 4 | 144 | 0 |
| s2s-blur-both | s2s | 4 (4 / 0 / 0) | 1 | - (unmeasured) | 4* | 204 | 0 |
| concurrency-native | concurrency | 7 (3 / 0 / 4) | 1, 2, 4, 8, 16, 32, 64 | 156 MiB (manifest: risk B native-n1) | 1 | 262 | 0 |
| lightcurve1-full | lightcurve | 8 (8 / 0 / 0) | 1, 2, 4, 8 | - (unmeasured) | 4* | 6590 | 108 |
| capture-order-native | capture_order | 3 (0 / 0 / 3) | 1 | 24576 MiB (the address-space limit of a job) | 1 | 0 | 0 |
| forest-layered-comparison | command | 1 (1 / 0 / 0) | 1 | - (unmeasured) | 1 | 2625 | 0 |
| sweep-capped-demos | command | 1 (1 / 0 / 0) | 8 | - (unmeasured) | 1 | 3600 | 0 |

Total estimated wall time: 13425 s (3.73 h), entries one after another; estimates are one-thread wall times on the 4-core laptop (est_s). * the cores' bound: the job's memory is unmeasured, and the entry's probe (run alone first) sets the memory bound.

`--assume-cores 16 --assume-mem-gb 64`:

Host (assumed, 16 cores, 64 GB): 16 cores, 16 hardware threads, MemTotal 59.6 GiB, MemAvailable 53.6 GiB; memory budget 75% of MemAvailable, a job counts 1.25 x its peak

| Entry | Driver | Items (pending / done / exceeds host) | Threads per job | Peak per job (source) | Concurrency | Estimated wall (s) | Disk (GB) |
|---|---|---|---|---|---|---|---|
| s2s-unlabelled-points | s2s | 18 (18 / 0 / 0) | 1 | 156 MiB (manifest: risk B native-n1, the 25 km plate job in the same scene) | 16 | 74 | 0 |
| s2s-blur-both | s2s | 4 (4 / 0 / 0) | 1 | - (unmeasured) | 16* | 204 | 0 |
| concurrency-native | concurrency | 7 (5 / 0 / 2) | 1, 2, 4, 8, 16, 32, 64 | 156 MiB (manifest: risk B native-n1) | 1 | 658 | 0 |
| lightcurve1-full | lightcurve | 8 (8 / 0 / 0) | 1, 2, 4, 16 | - (unmeasured) | 16* | 4476 | 108 |
| capture-order-native | capture_order | 3 (3 / 0 / 0) | 1 | 24576 MiB (the address-space limit of a job) | 1 | 5854 | 0 |
| forest-layered-comparison | command | 1 (1 / 0 / 0) | 1 | - (unmeasured) | 1 | 2625 | 0 |
| sweep-capped-demos | command | 1 (1 / 0 / 0) | 16 | - (unmeasured) | 1 | 3600 | 0 |

Total estimated wall time: 17491 s (4.86 h), entries one after another; estimates are one-thread wall times on the 4-core laptop (est_s). * the cores' bound: the job's memory is unmeasured, and the entry's probe (run alone first) sets the memory bound.

`--assume-cores 32 --assume-mem-gb 128`:

Host (assumed, 32 cores, 128 GB): 32 cores, 32 hardware threads, MemTotal 119.2 GiB, MemAvailable 107.3 GiB; memory budget 75% of MemAvailable, a job counts 1.25 x its peak

| Entry | Driver | Items (pending / done / exceeds host) | Threads per job | Peak per job (source) | Concurrency | Estimated wall (s) | Disk (GB) |
|---|---|---|---|---|---|---|---|
| s2s-unlabelled-points | s2s | 18 (18 / 0 / 0) | 1 | 156 MiB (manifest: risk B native-n1, the 25 km plate job in the same scene) | 32 | 74 | 0 |
| s2s-blur-both | s2s | 4 (4 / 0 / 0) | 1 | - (unmeasured) | 32* | 204 | 0 |
| concurrency-native | concurrency | 7 (6 / 0 / 1) | 1, 2, 4, 8, 16, 32, 64 | 156 MiB (manifest: risk B native-n1) | 1 | 856 | 0 |
| lightcurve1-full | lightcurve | 8 (8 / 0 / 0) | 1, 2, 4, 32 | - (unmeasured) | 32* | 4476 | 108 |
| capture-order-native | capture_order | 3 (3 / 0 / 0) | 1 | 24576 MiB (the address-space limit of a job) | 2 | 3600 | 0 |
| forest-layered-comparison | command | 1 (1 / 0 / 0) | 1 | - (unmeasured) | 1 | 2625 | 0 |
| sweep-capped-demos | command | 1 (1 / 0 / 0) | 32 | - (unmeasured) | 1 | 3600 | 0 |

Total estimated wall time: 15435 s (4.29 h), entries one after another; estimates are one-thread wall times on the 4-core laptop (est_s). * the cores' bound: the job's memory is unmeasured, and the entry's probe (run alone first) sets the memory bound.

`--assume-cores 64 --assume-mem-gb 256`:

Host (assumed, 64 cores, 256 GB): 64 cores, 64 hardware threads, MemTotal 238.4 GiB, MemAvailable 214.6 GiB; memory budget 75% of MemAvailable, a job counts 1.25 x its peak

| Entry | Driver | Items (pending / done / exceeds host) | Threads per job | Peak per job (source) | Concurrency | Estimated wall (s) | Disk (GB) |
|---|---|---|---|---|---|---|---|
| s2s-unlabelled-points | s2s | 18 (18 / 0 / 0) | 1 | 156 MiB (manifest: risk B native-n1, the 25 km plate job in the same scene) | 64 | 74 | 0 |
| s2s-blur-both | s2s | 4 (4 / 0 / 0) | 1 | - (unmeasured) | 64* | 204 | 0 |
| concurrency-native | concurrency | 7 (7 / 0 / 0) | 1, 2, 4, 8, 16, 32, 64 | 156 MiB (manifest: risk B native-n1) | 1 | 1054 | 0 |
| lightcurve1-full | lightcurve | 8 (8 / 0 / 0) | 1, 2, 4, 64 | - (unmeasured) | 64* | 4476 | 108 |
| capture-order-native | capture_order | 3 (3 / 0 / 0) | 1 | 24576 MiB (the address-space limit of a job) | 5 | 3600 | 0 |
| forest-layered-comparison | command | 1 (1 / 0 / 0) | 1 | - (unmeasured) | 1 | 2625 | 0 |
| sweep-capped-demos | command | 1 (1 / 0 / 0) | 64 | - (unmeasured) | 1 | 3600 | 0 |

Total estimated wall time: 15633 s (4.34 h), entries one after another; estimates are one-thread wall times on the 4-core laptop (est_s). * the cores' bound: the job's memory is unmeasured, and the entry's probe (run alone first) sets the memory bound.

## Still deferred at round 43

Every entry is still pending: no round since 36 ran one. For the capture-order case and the full-size specs of the combined-motion (`both`) group, the manifest now carries an `estimate` block (informational: the runner reads only `est_s` and `peak_mib`), from the records:

| Entry | Item | Renders | Peak memory per render (estimate) | Wall time at one thread (estimate) | Basis |
|---|---|---|---|---|---|
| `s2s-blur-both` | the four `s2s2-blur-both-e*ms` specs at 500 x 500 | 4 | about 160 MiB (the probe measures it; no `peak_mib` is set) | 591 s summed, 121.8 to 204 s each (`est_s`) | the both group's 64 x 64 renders of round 41 peaked at most 129,540 kB, and family I's 500 x 500 plate job at 159,644 KiB (risk B `native-n1`); the times are round 30's 20 ms render and round 32's platform group at 0.1, 1 and 5 ms. Their 64 x 64 counterparts (`s2s2-blur-both-e*ms-w64`) are records |
| `capture-order-native` | Thermal2 | 7 (as authored, 5 single captures, reversed) | about 140 MiB as authored; reversed: the 24 GiB limit | 752 to 998 s | as authored 360 to 483 s: 116.3 s at 8 threads (demo sweep) times the one-thread cost 3.1 to 3.7 (`docs/DIRSIG_determinism.md`), and 30.2 s at the reduced size times 16 (element counts over 100 divided by 4 on each axis). Peak: the reduced render's 107,456 KiB plus the demo's 33.8 MB of outputs. Reversed: without a limit 5,558,920 KiB anonymous memory in 7 s, and under a 2 GiB limit `bad_alloc` "while generating a scheduled event queue" at 614,628 KiB, so the growth does not depend on the image size and reaches 24 GiB in about 32 s (risk D `thermal2-reduced`) |
| `capture-order-native` | Polarization4 | 6 (as authored, 4 single planes, reversed) | about 252 MiB | 558 to 2712 s | as authored 186 to 904 s (11.6 s reduced times 16; 244.3 s at 8 threads times 3.1 to 3.7); peak the reduced 257,276 KiB plus 0.8 MB of outputs (risk D `polarization4-reduced`) |
| `capture-order-native` | Fireball1 | 4 (as authored, 2 single planes, reversed) | about 112 MiB | 57 to 69 s | as authored 19 to 23 s (1.4 s reduced times 16; 6.1 s at 8 threads times 3.1 to 3.7); peak the reduced 107,436 KiB plus 7.4 MB of outputs (risk D `fireball1-reduced`) |

An item's time counts its single captures together as about one render and its reversed render as one (Thermal2's as 32 s); `est_s` is the upper end. The runner still counts each capture-order job at its 24 GiB limit, so the concurrency on the assumed hosts is unchanged (1, 2 and 5 demos at once).

Not in the manifest and still open: family II's `both` group from 50 km at 64 x 64 sweeps 24.48 px, more than the window holds (round 41 dropped its spec and record); a point there needs a larger window or a shorter exposure, which this host can render (BACKLOG "Space-to-space: what round 41 leaves open").

## Run instructions for the larger host

Before: a checkout at this commit or later, the `protodirsig` environment (`environment.yml`), the pinned DIRSIG installation (`~/DIRSIG/<version>` or `$DIRSIG_HOME`, `external/pins.json`) with its `Documents_Folder-07-Feb-2024` (entry 6), `prlimit` (util-linux), 120 GB free under the work root (entry 4: 108 GB), and `python scripts/bootstrap.py status` clean.

The command (from the repository root; the work root defaults to `~/.local/state/manifold/bigger-host/`, outside the repository):

```
python scripts/bigger_host_run.py --dry-run && nohup python scripts/bigger_host_run.py > ~/bigger_host.out 2>&1 &
```

Rerun the same command after any stop: it skips every item whose result is recorded. `--only NAME` runs one entry.

Expected wall time per entry, from `est_s` (the laptop's one-thread wall times; the larger host's cores may be faster or slower) at the plan's concurrency:

| Entry | 16 cores, 64 GB (s) | 32 cores, 128 GB (s) | 64 cores, 256 GB (s) | Basis |
|---|---|---|---|---|
| `s2s-unlabelled-points` | 74 | 74 | 74 | 18 jobs at 156 MiB, the longest 73.9 s |
| `s2s-blur-both` | 204 | 204 | 204 | probe (121.8 s) alone, then 3 together; the longest 204 s |
| `concurrency-native` | 658 | 856 | 1054 | batches one after another; 70.7 to 198.1 s per batch (laptop, N up to 8), 198.1 s assumed above 8 |
| `lightcurve1-full` | 4476 | 4476 | 4476 | t1 (2400 s) beside t2 and t4, then td x 3 alone (691.9 s each at 8 threads); one-sample probe first |
| `capture-order-native` | 3779 | 2712 | 2712 | 1, 2, 5 demos at once under the 24 GiB limit; per demo, all its renders at one thread, the upper end of round 43's estimate (section "Still deferred at round 43"); Thermal2's reversed render reaches the limit in about 32 s |
| `forest-layered-comparison` | 2625 | 2625 | 2625 | 5 renders x 525 s (3.5 x the 150 s the default count exceeded): a lower bound |
| `sweep-capped-demos` | 3600 | 3600 | 3600 | 2 x 1800 s (the cap they exceeded): a lower bound; at the host's default thread count |
| Total | 15416 (4.3 h) | 14547 (4.0 h) | 14745 (4.1 h) | entries one after another |

Afterwards, the user checks:

1. `<work>/runner.log`: an `end` event; no `job-end` with a non-zero `rc`, no `killed`, `record-failed` or `exceeds-host` event (each is a finding: an exit 137 is recorded, not repeated unchanged).
2. `python scripts/bigger_host_run.py --dry-run`: every entry 0 pending (entries 6 and 7 are done when their own results files exist).
3. `python scripts/s2s_measure.py --check` (111 records) and `python scripts/risk_measure.py --check` (31 plus the host's 9 B, 12 E and 3 D records).
4. `python -m pytest tests/test_s2s_results.py tests/test_risk_measurements.py tests/test_bigger_host_run.py`.
5. `<work>/forest-layered-comparison/forest/results.json`: forest's status and image comparison, copied by hand into `docs/DIRSIG_transfer_scenes.md`; `<work>/sweep-capped-demos/demos/sweep/results.jsonl`: each demo's outcome and wall time, copied into `docs/DIRSIG_demo_sweep.md`'s prose.
6. `git diff --stat`: only `docs/data/s2s_results.jsonl` and `docs/data/risk_measurements.jsonl` changed; commit them with `<work>/peaks.json`'s figures in the message; then delete the work root (entry 4's renders hold 108 GB).
