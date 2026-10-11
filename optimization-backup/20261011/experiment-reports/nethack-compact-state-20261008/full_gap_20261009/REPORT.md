# Full normal-versus-burst gap accounting — 9 October 2026

## What is established

The complete CPU-time budget is **130.70 → 79.87 µs per recorded policy decision**, a **50.83 µs** gap. **98.2% is inside puf_step**. Native replay throughput is **214,945 → 353,806 SPS (+64.6%)**. There is no large unaccounted scheduler-CPU bucket.

Matched interventions establish a substantial data-locality component: preparing the same data on both sides reduces the inside-step gap **50.71 → 10.93 µs**, closing **39.78 µs (78.4%)**. Game-cluster bootstrap 95% interval for the closed gap: 38.42–41.21 µs. This is a diagnostic intervention, not an optimization: preparation costs more than it saves.

The functional budget is complete. The remaining hardware mechanisms are **not fully identified**: these measurements cannot assign every residual cycle uniquely to cache levels, TLBs, instruction delivery, branch prediction, contention, migration or frequency. Read the residual and concurrency controls below before interpreting the locality fraction.

## Fixed workload and scope

- Same unchanged retained GCC/PGO engine and recorded actions; 2048 game instances repeat 512 distinct recorded trajectories four times.
- Warm 8192 decisions/game, normally measure the next 512 (1,048,576 decisions/case). Placement and final solo controls measure 128 instead; do not add absolute effects from different windows.
- Intel i9-14900K. Original layout: 24 workers (8 P cores + 16 E cores), plus four submitters on P-core siblings; submitters also execute work. No GPU inference/training in this CPU-replay diagnostic.
- Burst16 executes 16 already-recorded actions before switching games. It cannot simply become a training default because live actions depend on the intervening observations.
- Quiesced, single-thread parent snapshots restore filesystem contents and open-file offsets for each case. Identical endpoint observations and world-turn totals throughout.
- Heavy work serialized. No engine edits, production edits, new retained candidate, commits, pushes or host-setting changes.

## All-step accounting and exclusive profile

| Exclusive CPU-time category | Normal µs | Burst16 µs | Gap µs |
|---|---|---|---|
| Monster movement + neighbours | 46.86 | 34.08 | 12.78 |
| Other engine code | 17.32 | 9.09 | 8.23 |
| Player movement / core loop | 9.23 | 3.02 | 6.21 |
| Engine observation/interface | 8.31 | 3.22 | 5.09 |
| Inventory weight / burden | 5.88 | 1.62 | 4.26 |
| Map display / vision | 10.72 | 6.69 | 4.03 |
| Other monster processing | 13.83 | 10.14 | 3.69 |
| Floor-object index | 4.30 | 1.73 | 2.58 |
| Puffer environment / harness inside step | 7.87 | 6.26 | 1.60 |
| Runtime libraries / unresolved | 4.25 | 2.78 | 1.47 |
| Outside puf_step | 2.14 | 1.23 | 0.90 |
| Total | 130.70 | 79.87 | 50.83 |

Process CPU time and every puf_step are timed directly. Inside-step rows are **nonoverlapping sampled program-counter self-time estimates**, scaled to the unprofiled all-step total; they are not exact per-function timers or cache-miss counts. Rows therefore sum by construction; that does not prove a unique hardware-causal explanation.

Accounting changes native throughput by approximately −0.38% normal / −1.12% burst. The disabled-path process-CPU gap is 51.23 µs, versus 50.83 µs with clocks: roughly 0.40 µs perturbation of the gap. Signal profiling adds about 3% overhead and is excluded from native speed numbers. Four profiles (normal, burst, burst, normal), per-thread CPU timers at 971 Hz, explicit inside-step flags, no dropped samples.

`Other engine code` contains many named functions rather than an unmeasured gap. The largest individual contributions are:

| Engine function (self time) | Normal µs | Burst µs | Gap µs |
|---|---|---|---|
| m_move.localalias.lto_priv.0 | 25.33 | 18.21 | 7.12 |
| mfndpos.localalias.lto_priv.0 | 21.51 | 15.85 | 5.66 |
| nethack_rl::NetHackRL::fill_obs(nle_observation*) [clone .localalias] [clone .lto_priv.0] | 6.07 | 1.71 | 4.36 |
| encumber_msg.localalias.lto_priv.0 | 3.81 | 1.13 | 2.67 |
| domove_core | 2.81 | 0.25 | 2.56 |
| nh_fobj_next.localalias.lto_priv.0 | 4.26 | 1.72 | 2.54 |
| newsym.localalias.lto_priv.0 | 5.11 | 2.67 | 2.44 |
| movemon.localalias.lto_priv.0 | 4.81 | 2.43 | 2.39 |
| minliquid.localalias.lto_priv.0 | 2.93 | 1.24 | 1.69 |
| rhack.localalias | 1.15 | 0.14 | 1.01 |
| readchar.localalias.lto_priv.0 | 1.05 | 0.09 | 0.96 |
| nle_weight | 1.29 | 0.34 | 0.95 |
| isaac64_update.lto_priv.0 | 2.68 | 1.86 | 0.82 |
| moveloop.localalias.lto_priv.0 | 2.04 | 1.43 | 0.61 |
| calc_capacity.localalias.lto_priv.0 | 0.62 | 0.07 | 0.55 |

Engine symbols come from the unchanged engine. The generic accounting executable was subsequently rebuilt to add affinity cases; its old sampled addresses should **not** be used for exact source-line attribution within the wrapper. Its module-level inside-step category remains valid. Raw engine-function attribution is in function_budget.json.

## Why earlier compact-data wins were small

The earlier source-access trace measured about 835.56 distinct virtual 64-byte lines touched per step. These are not hardware misses. Compact floor metadata removed only 0.32% of total touched lines; incremental floor indexing removed 2.93%. Those changes affect a small part of a distributed slowdown. The current exclusive profile assigns only 2.58 µs of the 50.83 µs gap to the floor index itself.

Previously omitted pointed-to data matter: per-game object-type table (lazy slot 40, allocated by src/o_init.c) and glyph buffer (slot 15, src/display.c) account for 111.43 touched lines/step in the earlier trace. Reading the main context warms their pointers, not these allocations.

## Data preparation experiments

One deterministic sample per approximately 64 decisions. Same sampled states across arms, with per-game grouping across duplicate copies and repeats. Rejected samples are those with wall time > CPU time × 1.10 + 2 µs, to avoid preemption contamination. Intervals resample the 512 distinct games; they do not represent machine-to-machine uncertainty. Old path-counter fields are zero on the unchanged engine and are not used as work counts.

Original five regions (terrain, two position grids, floor records, monster records) reduced sampled step time 129.01 → 107.67 µs, at 21.64 µs additional preparation: essentially no net saving. Expanding to inventories, the complete context, suspended coroutine stack and other allocations reduced it further. Read-only lazy-allocation sweep, repeated in reverse order:

| Data read before step | Step µs | Extra preparation µs | Net saving µs |
|---|---|---|---|
| control | 129.08 | 0.00 | -0.00 |
| all expanded groups | 94.83 | 94.06 | -59.81 |
| object-type table | 124.74 | 3.63 | 0.71 |
| glyph buffer | 127.12 | 1.75 | 0.21 |
| all lazy allocations | 122.13 | 14.12 | -7.18 |
| all expanded + lazy + nle context | 86.83 | 123.17 | -80.92 |
| targeted context + entities + lazy + stack | 88.61 | 67.45 | -26.98 |
| nle interface context | 129.49 | 10.72 | -11.13 |

Selected-data preparation includes the engine context, floor/monster records, player and monster inventories and container contents, live saved coroutine stack, lazy context allocations and NLE context. It omits broad Puffer observation/wrapper and window-object reads, which cost substantially more than they save. Reading every expanded region reaches 86.83 µs, but costs an extra 123.17 µs before the step.

Pre-reading alone is not sufficient evidence for the fraction of the burst gap: burst execution might also benefit. The matched control is:

| Condition | Normal step µs | Burst step µs | Remaining gap µs |
|---|---|---|---|
| No preparation | 128.99 | 78.28 | 50.71 |
| Read selected game data | 88.33 | 77.40 | 10.93 |
| Read and write back identical bytes | 90.68 | 78.80 | 11.89 |

Reading selected data adds 68.48 µs before a normal sampled step and 20.08 µs before a burst sampled step. Normal stepping benefits by 40.66 µs, burst by only 0.88 µs. The difference is the measured 39.78 µs gap closure. Effects from individual warmed regions overlap and must not be added.

The write-back arm stores each sampled byte unchanged after reading it to request ownership of writable cache lines. It preserves hashes but is slightly worse; it does not establish cache-line ownership as the missing fix. Broad warming also touches otherwise unused pages and may incur snapshot copy-on-write/page faults; preparation is charged separately, not hidden. This is not a proposed production implementation.

## Concurrency and placement controls

Original all-step placements, 128-decision window:

| Placement | Normal step µs | Burst step µs | Normal SPS | Burst SPS |
|---|---:|---:|---:|---:|
| Original 24 workers | 129.10 | 78.59 | 213,269 | 347,183 |
| 24 workers, submitters wait | 120.84 | 76.51 | 196,289 | 309,565 |
| 24 workers, weighted fixed ownership | 101.50 | 70.41 | 130,753 | 167,628 |
| 8 dedicated P workers, submitters on E cores | 67.64 | 46.18 | 117,070 | 171,716 |
| 1 dedicated P worker, submitters on E cores | 52.50 | 36.80 | 18,876 | 26,971 |
| 1 E worker, submitters on other E cores | 83.55 | 58.74 | 11,823 | 16,821 |
| Original 24 workers, final control | 129.56 | 78.80 | 212,390 | 346,717 |

Both core types benefit from bursts. Fixed ownership reduces step latency but loses throughput through poor utilization. Fewer concurrent workers reduce step latency but also change cache sharing, SMT, frequency and memory contention. These are **not clean independent additive estimates of migration or cache bandwidth**. Four busy-waiting submitters make outside-step process CPU enormous in the one-worker diagnostics; this does not mean the engine acquired extra work.

Final paired data-warming control, same 128-decision window, with either one dedicated P worker or the original layout:

| Workers | Mode | Normal step µs | Burst step µs | Gap µs |
|---|---|---|---|---|
| 1 | No preparation | 52.62 | 36.70 | 15.92 |
| 1 | Read selected game data | 45.33 | 36.34 | 8.99 |
| 24 | No preparation | 128.96 | 80.11 | 48.86 |
| 24 | Read selected game data | 89.68 | 78.25 | 11.44 |

The warmed residual remains **8.99 µs on a single dedicated P worker**, versus 11.44 µs in the mixed-core layout. Inter-worker migration and concurrent engine workers are therefore not necessary for this residual. The test does not distinguish remaining unwarmed/re-evicted data from instruction-side locality, branch prediction or other execution effects.

This is one timing observation per cell, with game-cluster intervals in solo_warming_results.json. The larger 512-decision warming experiment above supplies the repeated primary estimate. Do not subtract the solo and mixed-core microsecond gaps as if both represented an identical processor frequency and composition.

## Practical conclusion and remaining limit

There is measurable locality headroom spread across movement, core state, observation production, inventory checks and display state. Warm reads remove most of the normal-versus-burst penalty without changing the game. The earlier idea that one floor/monster struct change would recover the full gap was too narrow.

A useful optimization must avoid or overlap repeated data fetching while retaining load balancing and policy-inference dependencies. Blind prewarming and fixed ownership fail that throughput test. Raw object size, source load counts, and smaller code size are insufficient success metrics: measure the actual hot working set, normal-schedule CPU time and end-to-end throughput.

The remaining residual is explicitly measured, not silently labelled cache. Hardware PMU access is unavailable on this host (`perf_event_paranoid=4`); no setting was changed. Exact cache-level/TLB/front-end attribution remains unproven. Existing source-access tracing and these interventions do not substitute for hardware counters.

## Correctness and artifacts

**983,040 immutable per-decision hashes checked, zero mismatches**, covering observations, rewards, terminals and masks. All 99 native/proof cases have matching endpoints within their workload. These are replay checks on the existing corpus, not a claim of universal semantic equivalence for all possible games; the engine itself was unchanged.

All 8 protected live files, 1290 retained-source files, retained library and immutable reference unchanged. No new optimization retained. Final hashes in integrity_after.json; exact validation counts in validation.json.

- Main accounting: runs/accounting2048, accounting_summary.json, gap_budget.csv.
- Profile: profile_results.json, function_budget.json, profile_functions.json, symbols.json, raw pc.case*.samples/maps.
- Placement: runs/placement2048/result.json.
- Preparation: expanded_warm, expanded_warm_lazy, warm_paired, warm_solo; run.log and command.json for every case group.
- Numeric summaries/CSVs: warming_*, lazy_warming_*, paired_warming_*, solo_warming_*.
- Source/build recipes: setup.py, prepare_warm.py, prepare_lazy_warm.py, per-harness build_commands.json and snapshot/diag/env_pool sources.
- Original immutable reference: /puffertank/experiments/nethack-cpu-scaling-20261008/runs/final_hash_opt61/hashes.bin, SHA256 4d35f6965a68e81b13d55f6032ed39b09839cd3525ede0c71a12918f7bc9d047.
- Retained engine SHA256: 2a5cfac52f27a7430383c00e0c2a84ae96cdc12c64c2decbb993aeea8ec2ce84.
