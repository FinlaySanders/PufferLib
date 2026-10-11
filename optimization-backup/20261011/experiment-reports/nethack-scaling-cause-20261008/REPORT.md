# Why mature NetHack steps get slower at larger populations

Completed 8 October 2026. **The evidence strongly favours working-set/locality costs as the dominant explanation.** Hardware performance counters are unavailable, so this is controlled-intervention evidence, not a direct measurement of cache or TLB misses. The experiments do not identify a particular cache level or fully separate data-cache, instruction-cache, address-translation, branch-predictor and DRAM effects.

## Results

All rows use the same fixed engine, teacher games and actions. The 2,048-game population duplicates the same 512 teacher streams. End observations and world-turn advances match after normalization by the number of active games.

| Configuration | Sampled CPU time inside a step | CPU-only SPS |
| --- | ---: | ---: |
| 512 games, ordinary scheduling | 100.4 us | 272k |
| 2,048 games, ordinary scheduling | 156.1 us | 178k |
| 512 games, fixed CPU placement (two controls) | 105.0 us | 261k |
| 2,048 games, fixed CPU placement | 155.2 us | 180k |
| 2,048 resident, only 512 active, fixed placement | 110.0 us | 249k |
| 2,048 games, 16 recorded actions before switching games, fixed placement | 77.5 us | 364k |
| 2,048 games, tcmalloc, fixed placement | 153.6 us | 182k |

The ordinary-scheduling comparison reproduces the previous roughly 55% rise in per-step CPU time. Fixed-placement 512 controls before and after the interventions give 104.8/105.2 us and 261.9k/260.7k SPS. Other rows are individual diagnostic measurements, not confidence intervals from repeated runs.

### What the interventions tell us

1. **Thread placement is not the main explanation.** Pinning workers and submitters changes 2,048-game throughput only from 178k to 180k. Games can still migrate between workers through work stealing; this test removes OS migration of threads, not movement of game data between cores.
2. **Clock speed and P/E-core mix do not explain most of the loss.** With ordinary scheduling, P-core step time rises 91→145 us and E-core time 108→166 us. P-core frequency sampled from sysfs falls about 5%; E-core frequency falls less than 1%. The work fraction on P-cores is 44.6% versus 46.0%. With fixed placement, the larger population is slower despite higher reported clocks. Sysfs frequencies are proxies, not per-step cycle counts.
3. **The active working set matters much more than total resident memory.** All 2,048 games are initialized and warmed identically; then three quarters are left resident but inactive. Stepping the remaining 512 costs 110 us instead of 155 us, versus 105 us for the pinned 512-game control. About 90% of that excess sampled CPU time disappears. RSS stays about 1,447 MiB, versus about 675 MiB for the smaller population. There are no major page faults during measurement.
4. **Reusing a game's state is highly effective.** Sixteen recorded actions per game before switching doubles CPU-only throughput and halves CPU time inside `puf_step`. The latter excludes the outer pool claim/wait operations, so this cannot be explained solely by amortizing scheduler overhead. Lower reported clocks accompany the faster execution. Improved data/instruction/translation locality is the leading interpretation; branch-predictor reuse and allocation locality are not independently separated.
5. **Changing the allocator does not remove the gap.** Installed tcmalloc changes the pinned large-population result by about 1%, which is too small to explain the slowdown. This does not prove that allocation is free or that every possible allocator/layout change is ineffective.

The CPU has a shared 36 MiB L3. This makes a capacity/locality explanation plausible, but total RSS is not the cache working set and does not prove an L3-capacity boundary.

## Method and limitations

- CPU replay only; no GPU job or build ran concurrently with timing.
- i9-14900K, 24 pool workers plus four submitting threads. Fixed placement assigns one worker per physical core and the four submitters to spare P-core SMT siblings. Approximately 28 CPU-seconds per wall second are consumed in these runs; that is not a claim of 28 physical cores.
- Engine: `/puffertank/experiments/nethack-cpu-scaling-20261008/engines/opt61-final/build/libnethack.so`, including the common message and fire-trap fixes.
- Each game receives 8,192 warm-up decisions, then 2,048 measured decisions, reaching an average game age of 29,502 turns. The warm-up schedule remains one action per game even for the burst intervention.
- Step sampling uses a deterministic dispersed 1/64 schedule based on original stream and decision. This avoids sampling only the first, cold action of every 16-action burst. Duplicate streams sample the same actions. Measurements include thread CPU time, wall time and the core type; 65,536 samples are collected in each full 2,048-game run.
- `/sys` frequency/temperature samples are collected every 250 ms and tagged by warm-up/measurement phase. Temperature alone is not used to infer throttling.
- Gameplay checks compare final observations for all duplicates and world-turn advances; they are bounded checks, not exhaustive hidden-state equivalence.
- `perf stat` was attempted and denied access even to `task-clock`; no hardware cache-miss, TLB-miss or retired-instruction counts are claimed.
- The 16-action intervention uses known future actions from the recording. **It is a diagnostic, not an online collector or demonstrated training speedup.** A live policy must run inference between successive game actions.
- Tests and instrumentation are isolated here. Production source and configuration are unchanged.

## Implication for thousands of environments

The result supports keeping the large population while processing smaller groups through short rollout chunks, so recently used game state has a better chance of staying near the executing cores. A frozen rollout-policy snapshot would need to perform inference between actions within each group. Stable game-to-worker ownership and a smaller frequently accessed state are other candidates.

That is the next full-pipeline experiment, not an already validated optimization. It must account for GPU inference efficiency, preserve per-game recurrent state and RNG streams, and retain the intended rollout/update semantics. The 364k replay number is not a forecast of its training SPS.

Reproduction and raw evidence: `run.py`, `replay.c`, `env_pool.h`, `build.json`, `manifest.json`, `method.json`, `results.csv`, `summary.json`, and per-case logs/telemetry. The profiler checks all case observation hashes agree and normalized world-turn advances agree.
