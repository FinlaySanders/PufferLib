# NetHack memory attribution — 8 October 2026

## Finding

The locality benefit is distributed across several data structures. In an unchanged native engine, reading selected per-game data immediately before a decision reduces the timed decision from **141.33 to 90.93 microseconds** (ratio **0.643**, game-clustered 95% interval **0.628–0.660**). The reads themselves cost **54.59 microseconds**, so this intervention does **not** deliver a throughput gain. The control preparation costs 0.97 microseconds: total preparation plus decision is 142.30 versus 145.52 microseconds.

A fresh 16-action burst reference gives **77.46 microseconds/decision** and **364,600 SPS**, versus about 198k SPS under standard scheduling. Prewarming the selected data removes about **79% of the measured per-decision latency difference** to that reference. This is causal evidence for a substantial data-locality penalty. It is not an exact hardware cache-miss decomposition, and that percentage is not a realizable speedup.

The source-level address trace and native interventions point in the same direction. Moving only monster records changes a small fraction of the accessed state. Staying on one game reuses its inventory, floor objects, map grids, glyphs, object-type table, hero state, RNG and other data together.

## Address capture

Same 512 recorded mature trajectories used by the previous CPU benchmarks. Capture 32 decisions per environment after 8,192 warm-up decisions: **16,384 captured decisions**. A smaller early pilot captures four decisions per environment after 128 warm-up decisions.

Clang 18 instruments explicit engine loads/stores. An external runtime deduplicates 64-byte lines per decision, records access counts and the first accessing PC, and labels addresses from context offsets and pre-step object/monster lists. It does not instrument libc/libstdc++ memory operations, compiler spill traffic, or the Puffer observation-packing wrapper. Instrumented timings are not performance results. Access counts and within-step replacement cannot be used as hardware cache-miss counts.

| Capture | Mean traced KiB/decision | Median | p90 | Mean per-game union across capture |
|---|---:|---:|---:|---:|
| Early pilot | 37.02 | 35.25 | 46.37 | 51.59 KiB |
| Mature | 61.57 | 59.06 | 88.69 | 115.61 KiB |

91.8% of mature line touches are classified directly. Most remaining touches originate in the inventory-export vectors, strings/window state, and trap records; first-PC symbolization is retained separately. A line spanning adjacent fields receives the category of its first instrumented access, so very small field-level counts are approximate. Objects newly allocated during the decision are not present in the pre-step range snapshot.

Selected mature categories:

| Data | Mean KiB/decision | Lines also touched on preceding decision |
|---|---:|---:|
| Glyph buffer, including interleaved dirty flags | 6.60 | 100.0% |
| Hero inventory object records | 5.63 | 100.0% |
| Monster records | 4.25 | 96.6% |
| Floor object records | 4.23 | 65.5% |
| Agent glyph output | 3.30 | 100.0% |
| Terrain grid | 2.97 | 73.8% |
| Per-game object-type table | 2.79 | 96.9% |
| RNG state | 2.69 | 74.9% |
| Monster-pointer grid | 2.51 | 70.9% |
| Hero state | 2.18 | 98.6% |
| Floor-object-pointer grid | 2.01 | 69.5% |
| Monster inventory records | 1.44 | 88.1% |

Reuse percentages exclude the first captured decision, which has no recorded predecessor. These percentages describe address reuse, not whether a hardware cache retained the line.

The machine has 36 MiB shared L3, 2 MiB L2 per P core, and 4 MiB L2 shared by each four-E-core cluster. Multiplying the traced per-decision footprint by 512 versus 2,048 active games suggests substantial capacity pressure; it is not a cache simulator because there is shared data, partial overlap, asynchronous scheduling and untraced traffic. Hardware performance counters remain unavailable. No host settings were changed.

### Capture validation and limitation

The trace library passes 34 golden trajectories, 26 fuzz traces, status-disabled replay, interleaved games and shuffled-thread tests. Its first full wrapper capture failed after thread migration. Address capture therefore uses fixed worker ownership with initialization on the same workers; production code was not changed. The pilot and mature capture then reproduce the native reference final observations, ages and world-turn advances exactly:

- Pilot: `83c188a86f5e384c`, 15,092 turn advances.
- Mature: `e6bece5873023caa`, 114,452 turn advances.

These are golden-corpus and end-state checks, not an every-decision proof of the instrumented capture. The native causal measurements below use the original GCC/LTO engine and the original shared work-stealing pool, so the instrumentation and fixed-ownership workaround cannot create their timing result.

## Native selective warming

2,048 games, 24 workers plus four submitters, original four buffers and standard rollouts. Warm 8,192 decisions/game and measure the next 2,048, using unchanged recorded actions. P/E workers and submitters use the same affinity as prior benchmarks. The only intervention is reading selected live data before selected decisions. No game memory is written.

Select approximately 1/32 decisions by a fixed hash of environment and tick, then randomly assign a group. Record thread CPU time separately for preparation and the engine/wrapper step. There are **131,243 samples**, no sampled worker migrations, and no samples above the predeclared 10 ms outlier check. Cluster bootstrap resamples the 512 underlying trajectory streams, combining their four duplicated environments. Intervals describe timing samples on this machine/workload, not general game or hardware performance.

| Warmed data | Samples | Step us | Preparation us | Step ratio | 95% interval |
|---|---:|---:|---:|---:|---:|
| Control | 13,260 | 141.33 | 0.97 | 1.000 | reference |
| Glyph buffer + output | 13,173 | 135.55 | 3.03 | 0.959 | 0.941–0.978 |
| Map grids | 13,091 | 131.24 | 8.04 | 0.929 | 0.909–0.948 |
| Hero + inventory | 13,199 | 130.35 | 10.38 | 0.922 | 0.902–0.945 |
| Monsters + inventories | 13,167 | 132.60 | 9.04 | 0.938 | 0.918–0.958 |
| Object-type table | 13,083 | 134.97 | 4.71 | 0.955 | 0.937–0.973 |
| RNG | 13,049 | 138.54 | 2.70 | 0.980 | 0.963–0.998 |
| Vision grids | 12,883 | 139.34 | 2.65 | 0.986 | 0.967–1.005 |
| Floor objects | 13,149 | 130.53 | 25.12 | 0.924 | 0.906–0.944 |
| All selected groups | 13,189 | 90.93 | 54.59 | 0.643 | 0.628–0.660 |

Effects overlap and are not additive. Warming entire grids/chains also reads bytes the next decision may not need. The control helper still incurs a small call/timer cost. Both P-core and E-core subsets show the all-groups effect: 131.2→87.7 us and 149.9→93.7 us respectively.

Full replay still produces observation hash `b97835c62aaf388f`, age 29,502.23 and 28,920,368 turn advances.

## Nonblocking prefetch diagnostic

Repeating the randomized diagnostic with L2-targeted prefetch instructions instead of blocking reads does not produce a large net saving:

| Group | Step us | Preparation us | Combined us |
|---|---:|---:|---:|
| Control | 140.55 | 0.98 | 141.53 |
| All selected groups | 101.68 | 48.49 | 150.17 |
| Static arrays + hero state, no object-chain walks | 129.85 | 9.34 | 139.19 |

Linked lists still have to be walked to obtain their addresses. Prefetching entire arrays issues many unnecessary requests and provides little lead time. The static-only result is a small sampled difference, not evidence of an end-to-end improvement. No prefetch intervention is promoted. The full replay outcome remains identical.

## Focused standard-rollout candidates

Two independent candidates were screened with standard native rollouts:

1. **Separate glyph and dirty-flag planes.** The mandatory full glyph scan reads 3,360 bytes of contiguous glyphs instead of striding through 6,720 bytes of glyph/flag records. Dirty-flag order, display callbacks and displayed values are preserved. Total allocation falls from 6,720 to 5,040 bytes.
2. **Compact inventory export cache.** Keep the existing inventory callback, optional strings and RNG draws. At that same update, cache glyph/letter/class arrays. Each observation copies 220 contiguous bytes rather than walking records containing two strings. Identification-sensitive fields still read live engine state as before.

Both pass the golden/fuzz/status/interleaved/shuffled gates. Final native screen:

| Variant | Runs | SPS | Change from baseline mean | Sampled CPU us/decision |
|---|---:|---:|---:|---:|
| Retained baseline | 2 | 199,814 | reference | 140.30 |
| Separate glyph/dirty planes | 1 | 200,953 | +0.57% | 139.37 |
| Compact inventory export cache | 1 | 200,705 | +0.45% | 139.37 |

Baseline controls were 199,873 and 199,754 SPS. Both candidates reproduce the same final observation hash and 28,920,368 world-turn advances. The sub-1% candidate differences in a single screen do not establish a useful gain; **neither is promoted**. Both patches remain isolated and reviewable. The separate complete 16,777,216-decision hash gate and GPU/full-training pipeline were not run for these rejected candidates. There is no claimed new training speedup.

This closes the attribution study: cold per-game data accounts for most of the standard-versus-burst latency gap, but loading it just before use moves the cost, and these two local layout changes are too small to recover that gap. The evidence supports reducing repeated work across multiple structures or retaining their contents across steps while preserving load balance. It does not support claiming that one allocator change or a simple prefetch loop will deliver the burst speedup under standard collection.

## Artifacts

- `captures/{pilot_fixed,mature}/`: raw per-game line traces, categories, summaries and capture commands.
- `trace/`: source copy, runtime, category definitions and instrumented build.
- `warm/{mature2048,prefetch2048}/`: randomized native event CSVs, bootstrap summaries and commands.
- `runs/burst_reference/`: fresh locality reference using the unchanged native engine.
- `engines/{split_glyph,inventory_cache}/`: isolated candidate source, libraries and patches.
- `checks/`: pinned reference corpora and gate results.
- `analyze_trace.py`, `analyze_warm.py`: analysis scripts.

The retained production baseline remains `/puffertank/experiments/nethack-locality-target-20261008/engines/persist/build/libnethack.so`; it is unchanged by this study. No live repository or training defaults are changed.

All eight protected live file hashes match the starting manifest (`live_integrity.json`). All experiment processes have finished. No branches, commits or training defaults were changed.
