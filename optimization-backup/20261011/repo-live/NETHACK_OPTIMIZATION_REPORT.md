# NetHack optimization report

Updated 10 October 2026. This consolidates the performance work from September and October: engine optimization, CPU scaling, GPU kernels, cuBLAS workspaces, scheduling, and validation. It includes unsuccessful directions and links to the detailed evidence. It does not replace the separate article results, policy ablations, or drone reports.

## Current result

The latest retained experimental stack delivers approximately **228–229k environment decisions per second**, or **0.82 billion decisions per hour**, on the original **15.55M-parameter model with 512 environments**. One billion per hour requires 277,778 SPS, about **22% more throughput**. We have not reached that target with this model.

The primary configuration is 512 environments, horizon 512, four rollout buffers, 32 shared CPU workers, batch 262,144, PPO minibatch 4,096, and 113 PPO updates per iteration, on an RTX 4090 and i9-14900K. The 2,048-environment configuration is a separate scaling test, not the primary target. [Benchmark definition](/puffertank/experiments/nethack-24h-20261009/PRIMARY_BENCHMARK.json).

These recent measurements execute inference, PPO forward/backward, and optimizer computation, while keeping the acting policy frozen and writing optimizer results to scratch. Recorded mature-game actions hold the environment workload constant. They measure the full computational pipeline, **not learning quality or the wall-clock time of a completed 1B training run**.

| Latest 512-environment comparison | Mean SPS | Change within that experiment |
|---|---:|---:|
| Before entity fusion | 221,217 | Reference |
| Inference entity fusion only | 222,594 | +0.62% |
| Training-forward entity fusion only | 226,354 | +2.32% |
| Both entity fusions | 228,005 | **+3.07%** |
| Later high-priority inference control, both fusions | 228,613 | Reference for priority test |
| Normal-priority inference | 211,891 | **−7.31%** |
| Independent inference control in batching test | 228,476 | Reference for batching test |
| Dispatcher with no request merging | 217,488 | −4.81% |
| Dispatcher combining ready requests | 222,981 | **−2.41%** |

Keep both entity fusions and the existing high-priority independent inference. The latest scheduling experiments did not improve total throughput. These selections are in the experimental stack; the experiments did not change production defaults. [Entity fusion](/puffertank/experiments/nethack-24h-20261009/entity512_20261010/REPORT.md), [priority and batching](/puffertank/experiments/nethack-24h-20261009/overlap512_20261010/REPORT.md).

## How the gains fit together

There is **no fresh, matched comparison of the complete latest stack against untouched upstream 5.0**. We should not present a product of all the percentages as that result. Baselines, worker counts, horizons, model sizes, and validation requirements changed during this work.

| Milestone | Measurement | Before → after | Interpretation |
|---|---|---:|---|
| September cuBLAS workspace fix | Fresh NetHack training, H512 | 112,413 → 172,815 SPS, **+53.7%** | Compared with pristine upstream; this fix is already included in later baselines. |
| September training optimizations | Then-current mature workload | 170,747 → 187,261 SPS, **+9.7%** | Historical stack and shorter timing window; later re-audited. |
| 8 October comprehensive audit | Mature score policy, full pipeline | 98,073 → 176,050 SPS, **+79.5%** | Baseline already has the final workspace fix. |
| Same audit | Early-game full pipeline | 168,700 → 185,122 SPS, **+9.7%** | Demonstrates why early SPS understates the engine benefit. |
| Same audit | Depth-policy full pipeline | 307,818 → 342,137 SPS, **+11.1%** | Different, smaller 4.31M model; absolute SPS is not comparable with score-policy SPS. |
| Compact state plus object allocation pool | Then-current mature full pipeline | 179,826 → 184,508 SPS, **+2.60%** | Corresponding CPU-only gains were about 8–9%. |
| Encoder/decoder gradient overlap, with corrected CUDA queues | 2,048 environments, full pipeline | 184,782 → 187,268 SPS, **+1.35%** | Initial default-queue implementation had slowed the pipeline. |
| Four parallel Muon lanes | 2,048 environments, full pipeline | 187,358 → 193,389 SPS, **+3.22%** | Isolated GPU gain was larger. |
| October GPU/scheduling combination | 2,048 environments, fixed 24 workers | 194,072 → 201,633 SPS, **+3.90%** | Combined measured gain; includes numerical changes. |
| Same combination, also increasing workers to 32 | 2,048 environments | 194,072 → 210,222 SPS, **+8.32%** | Includes CPU configuration change. |
| Return to original configuration | 512 environments, before entity fusion | About 221k SPS | Different regime, not a clean incremental optimization comparison. |
| Both entity fusions | Original 512 configuration | 221,217 → 228,005 SPS, **+3.07%** | Latest independently repeated retained improvement. |

Sources: [cuBLAS performance](/puffertank/experiments/cublas-all-env-perf-20260918/REPORT.md), [September training](/puffertank/experiments/nethack-train-loop-20260918/SUMMARY.md), [October audit](/puffertank/experiments/nethack-comprehensive-20261008/REPORT.md), [compact-state campaign](/puffertank/experiments/nethack-compact-state-20261008/REPORT.md), [gradient overlap](/puffertank/experiments/nethack-gradient-pipeline-20261009/diagnosis/REPORT.md), [parallel Muon](/puffertank/experiments/nethack-muon-parallel-20261009/REPORT.md), [combined measurements](/puffertank/experiments/nethack-24h-20261009/COMBINED_DIRECT_SUMMARY.json).

The October audit also separated contributions on the same mature score workload: baseline **98k**, engine only **126k**, engine plus shared workers **164k**, GPU changes only **101k**, and combined **176k SPS**. At that point most of the improvement came from CPU work and its scheduling. Subsequent improvements moved the bottleneck.

## What changed in the engine and CPU path

### Avoid repeated work

The earliest retained engine work included bulk glyph export, immutable canonical-appearance lookup tables, deferred gold counting, an ordered floor-object coordinate cache, and SIMD filters for coordinates and glyphs. Release/LTO and compiler settings were tested without enabling fast-math. [Initial retained engine](/puffertank/experiments/nethack-perf-20260917/tight-loop/campaign2h/final/REPORT.md).

Later work kept the floor index valid across steps where objects had not changed, reused coordinate matches, avoided unnecessary distant-monster checks, cached nearby track occupancy, and avoided repeated no-gold searches. Removing blanket floor-index invalidation on every input reduced measured rebuilds from **1,019,767 to 323,737**, roughly **68%**, while retaining mutation invalidation. This produced about **6.7% CPU replay improvement** and **6.8% full-pipeline improvement** in that particular 5.10M-model comparison; it was not a 6.8% result for the original 15.55M model. [Recovered engine changes](/puffertank/experiments/nethack-cpu-scaling-20261008/REPORT.md), [invalidation experiment](/puffertank/experiments/nethack-locality-target-20261008/REPORT.md).

Shared CPU workers and avoiding busy waiting mattered as well. The current target uses 32 workers shared across buffers. Worker-count gains must be reported separately from improvements to game logic.

### Make frequently accessed state smaller

The compact-state campaign reduced selected structures and separated hot data: terrain records from 8 to 6 bytes, objects from 96 to 88 bytes, monsters from 144 to 120 bytes, smaller property storage, separate glyph planes, and compact inventory export. Object pooling improved allocation/locality. Individual packing changes were often neutral; the combined compact-state/object-pool implementation gave repeated CPU gains of **8.82% at 512** and **8.10% at 2,048**, versus **2.60%** for the then-current full score-training pipeline.

Additional retained work removed redundant display/glyph work and used fresh profile-guided builds. Some changes helped CPU replay without moving total training time. The compact-state report is chronological: its opening snapshot is older than its later follow-ups. [Campaign and checks](/puffertank/experiments/nethack-compact-state-20261008/REPORT.md).

### Movement subsystem work

We tested compact terrain queries, movement masks and layouts, fast-path eligibility, and an existing compact tile bit for object presence after movement. The final movement/object-presence follow-through improved CPU replay by **0.99% at 512** and **0.84% at 2,048** against matched profile-guided controls. Its measured full-pipeline changes were **−0.02% for score** and **+0.04% for depth**: effectively neutral. It is part of the engine used by subsequent experiments, but is not evidence of a large training-speed gain. [Movement follow-through](/puffertank/experiments/nethack-compact-state-20261008/movement_followthrough_20261009/REPORT.md).

## What changed on the GPU

### cuBLAS workspaces

The workspace fix gave streams their own configured handles/scratch storage. Setting a cuBLAS stream can reset workspace configuration; the implementation must preserve the association correctly.

Upstream graph capture could exhaust an internal allocation budget and cause some GEMMs to choose a different algorithm. Capture interleaving then changed which operations took that path, affecting performance and floating-point results. The detailed investigation identified a machine/driver-specific retained-allocation limit; this was not ordinary physical VRAM exhaustion. Explicit workspaces avoided that failure mode. [Mechanism](/puffertank/experiments/cublas-pool-rule-20260918/REPORT.md), [final patch checks](/puffertank/experiments/cublas-final-check-20260918/REPORT.md).

The large performance effect was specific to the tested long-horizon NetHack workload. In the same performance suite, NetHack H128 changed by only **+0.04%**, Craftax by **+0.40%**, CPU Breakout by **+0.60%**, and GPU Breakout by **−0.66%**. The determinism and configuration fix has broader relevance than its NetHack speedup. Refer to the detailed determinism matrices for the tested configurations, rather than claiming universal equivalence.

### Reduce unnecessary training work

Retained experiment families include head-wise action sampling, batched Muon norm computation, removing unnecessary MinGRU copies, skipping unused log-probability work, coalescing zeroing, storing observations as bytes, and reusing rollout graphs. Historical memory measurements showed large reductions, for example **15.11 to 8.33 GiB** in the October mature-score frozen-pipeline audit. Memory figures depend on the test setup.

The later fast GPU combination also uses selected out-of-place update GEMMs, recurrent scan variants, embedding reductions, identity operations, fused bias/ReLU, and faster feature gathering. **This complete combination changes floating-point numerics** relative to the earlier exact baseline. Its performance gain and its numerical validation are separate results. [Campaign ledger](/puffertank/experiments/nethack-24h-20261009/LEDGER.md), [fusion dispatch audit](/puffertank/experiments/nethack-24h-20261009/FUSION_DISPATCH_AUDIT.md).

### Overlap independent work

Moving independent encoder/decoder weight-gradient GEMMs onto the existing gradient stream initially slowed full throughput by **4.02%**, despite helping the isolated GPU test. Tracing found false dependencies between CUDA work queues: nominally ready inference could wait hundreds of milliseconds. Configuring **32 compute connections** removed this problem and made the overlap worth **1.35%** in the matched full-pipeline test. Increasing copy connections alone did not fix it. [Diagnosis](/puffertank/experiments/nethack-gradient-pipeline-20261009/diagnosis/REPORT.md).

Four Muon lanes then ran independent matrix updates with private scratch/workspaces and a join before applying updates. Isolated PPO throughput improved **10.77%**, but full throughput improved **3.22%**. This is parallel work within an update, not unrestricted pipelining across PPO minibatches. [Parallel optimizer](/puffertank/experiments/nethack-muon-parallel-20261009/REPORT.md).

### Entity encoder fusion

Both inference and training-forward entity paths were fused. The same idea appeared almost neutral in the 2,048-environment regime because faster GPU work exposed more waiting for environments. At the original 512 configuration it reduced the measured PPO phase from **1,182 to 1,147 ms**, yielding the retained **3.07%** full-pipeline gain.

The current kernels include GPU-specific exported implementations for the tested RTX 4090/SM89 environment. They are experimental implementations, not a finished portable replacement for every device and shape. [Candidate and validation](/puffertank/experiments/nethack-24h-20261009/entity512_20261010/REPORT.md).

## What we learned about locality and scaling

More environments really do make each CPU step more expensive in the tested mature-game workload. One controlled comparison measured approximately **100 μs per step at 512** versus **156 μs at 2,048**. Keeping 2,048 resident but only 512 active brought the cost back to about **110 μs**. Holding placement fixed did not remove the effect. This implicates the actively accessed working set, rather than merely allocated memory or worker migration. [Scaling diagnosis](/puffertank/experiments/nethack-scaling-cause-20261008/REPORT.md).

Executing multiple recorded steps on one environment before switching was substantially faster. A later diagnostic measured CPU throughput of **215k versus 354k**, with most of the time difference inside environment stepping. The gap was distributed across monster processing, player logic, observations, burden, display, and floor indexing. It was not one oversized structure or one slow lookup. These bursts use already recorded future actions: their speed is diagnostic headroom, **not an available drop-in online rollout optimization**. [Full gap decomposition](/puffertank/experiments/nethack-compact-state-20261008/full_gap_20261009/REPORT.md).

Hardware performance counters were unavailable. Source instrumentation and sampling locate costly work, but do not uniquely separate cache misses, TLB behavior, bandwidth, and other effects. Flamegraphs helped locate subsystems; they did not prove a single hardware cause. [Flamegraphs](/puffertank/experiments/nethack-flamegraphs-20261009/REPORT.md).

Grouped rollouts did improve an earlier controlled **5.10M-model** 2,048-environment experiment from **165k to 212k SPS (+28.1%)**. However, repartitioning inference batches changes numerical results, and later scheduling variants on the faster stack did not preserve that benefit. We have not established grouping as the best default for the original configuration. [Grouped collection](/puffertank/experiments/nethack-grouped-rollouts-20261008/REPORT.md).

## Current bottleneck and overlap cost

**Original 512 environments, large model:** PPO finishes last. With both entity fusions, rollouts are ready about **157 ms before PPO completes**. There is no exposed rollout tail in the measured epochs, but inference and transfers still interfere with GPU training. “CPU hidden” does not mean collection is free.

Isolated PPO takes about **997 ms**, compared with **1,147 ms** in the full pipeline: approximately **15% longer** when overlapped. This includes scheduling and measurement differences, so it is not all proven removable hardware contention. Recent traces nevertheless confirm execution interference: matched PPO kernel groups take about **13% longer**, while inference kernels take about **2.48×** their isolated duration. Concurrent kernel times cannot be added to obtain wall time.

Reducing inference priority shortened some PPO work but delayed rollouts enough to lose **7.31%** overall. Combining ready inference requests saved **35–56%** of isolated forward time, yet the dispatcher lost **2.41%** overall through the combined costs of scheduling, packing, synchronization, and delayed CPU stepping. We have not assigned an exact share to each overhead. [Latest overlap investigation](/puffertank/experiments/nethack-24h-20261009/overlap512_20261010/REPORT.md).

**2,048 environments:** CPU collection is more limiting. Bypassing PPO improved about **210k to 220–225k SPS**; also bypassing inference added relatively little. These bypasses diagnose limits and are not valid training methods. [Attribution](/puffertank/experiments/nethack-24h-20261009/attribution_20261010/REPORT.md).

**Smaller model:** the 5.10M prototype reached about **283k SPS at 512 environments** before the latest fusion comparison, versus **221k** for the large model. At 2,048, it improved only about **209k to 215k**, despite roughly halving isolated GPU time. This supports the different bottleneck diagnoses. The small model was a frozen prototype driving recorded teacher actions; its policy quality has not been established. [Original configuration](/puffertank/experiments/nethack-24h-20261009/original_config_20261010/REPORT.md), [small-model scaling](/puffertank/experiments/nethack-24h-20261009/model5m_20261010/REPORT.md).

## Unsuccessful, inconclusive, and parked ideas

The ledgers contain the individual trials; the table groups their conclusions. An isolated kernel win is not counted as a training-speed win.

| Direction | Finding and present status |
|---|---|
| Individual structure packing, alternate monster/tile grids, static metadata, prefetch | Many reduced memory or a local operation without reliably improving full throughput. Only measured combinations were retained. |
| Huge pages and allocation alternatives | Small or negligible measured gains; wrapper huge pages were about +0.11% overall. Not a solution to the full locality gap. |
| Larger batches/environment populations | Useful scaling questions, but did not automatically improve SPS; more active game state increased CPU step cost. Learning benefits remain separate. |
| Mandatory cohorts and ready-request batching | Schedule changes could sacrifice useful overlap. Latest original-configuration ready-request dispatcher was slower. |
| Optimizer lane balancing and cached tables | Tested follow-ups were slower or effectively neutral. |
| Batched Muon GEMMs, including relaxed numerics | Small isolated GPU benefits failed the full-pipeline timing gate. Long training checks were not run after failed performance gates. |
| Recurrent GEMM/gate fusion and other small GPU kernels | Some large local gains became well below 1% overall; not counted as retained net wins. |
| Actor weight cache | About +0.80% in one full comparison, below the campaign retention gate, with invalidation audit unfinished. Parked, not proven useless. |
| Dry-tile/liquid fast path | CPU screens were mildly positive, but large control drift invalidated the apparent full-pipeline gain. Inconclusive. |
| 32 MiB workspace variants, cache reservations, copy-graph changes | No established additional overall win on the tested fast stack. |
| Normal-priority inference | Latest original-configuration result −7.31%; rejected for this stack. |

Sources: [compact-state campaign](/puffertank/experiments/nethack-compact-state-20261008/REPORT.md), [Muon follow-ups](/puffertank/experiments/nethack-muon-followups-20261009/REPORT.md), [relaxed GEMMs](/puffertank/experiments/nethack-muon-followups-20261009/relaxed_numerics/REPORT.md), [October ledger](/puffertank/experiments/nethack-24h-20261009/LEDGER.md).

## Correctness: what has and has not been established

1. **Engine behavior:** retained engine candidates underwent recorded-action trajectory checks, observation comparisons, golden trajectories, and fuzz tests. Large checks covered tens of millions of decisions; the movement follow-through checked 67,108,864 decisions across its compared profile-guided builds. This is strong bounded regression evidence, not proof for every possible game.
2. **Important correction to earlier exclusions:** some saved engine changes initially diverged because of an uninitialized attacker-name/message path. A common fix was applied to both controls and candidates before rechecking. A separate fire-trap HP-limit fix was also common to both sides. Recovered optimization results must not be confused with the earlier failed comparison. [Recovery report](/puffertank/experiments/nethack-cpu-scaling-20261008/REPORT.md).
3. **GPU exactness is version-specific:** several individual changes passed exact gradient/master-weight/momentum checks over 113 or 1,808 real optimizer updates. Older out-of-place results did not automatically transfer to the later workspace configuration. The current combined fast GPU stack has measured numerical differences and is not certified bitwise-equivalent to pristine upstream.
4. **Latest entity fusions:** relative to the current experimental stack, saved-batch gradients and optimizer state matched exactly over 113 updates; a separate 1,808-update pipeline check also matched checked checkpoints, actions, values, recurrent state and other recorded tensors. Synthetic tests found rare intermediate rounding differences, so universal bitwise equivalence is not claimed.
5. **Replay hashes are not learning equivalence:** identical observations under forced recorded actions show equal environmental workload. They do not show that freely sampled actions or learned policies would remain identical. Larger inference batches explicitly changed BF16 outputs.
6. **Learning quality:** throughput experiments cannot certify score, depth, or stability after long training with numerically changed kernels. That remains a separate validation requirement before adopting such changes as training defaults.

Recent timing experiments use serialized fresh processes, warmup, repeated/interleaved controls, and profiling runs separate from timing runs. The current primary screen uses 64 epochs, warming through epoch 23 and measuring epochs 24–62. Smaller gains near run-to-run drift are not treated as established improvements.

## Where the retained implementation and evidence live

| Artifact | Location |
|---|---|
| Primary benchmark and runner | [PRIMARY_BENCHMARK.json](/puffertank/experiments/nethack-24h-20261009/PRIMARY_BENCHMARK.json), [run_primary.py](/puffertank/experiments/nethack-24h-20261009/run_primary.py) |
| Latest selected entity additions | [CANDIDATE.json](/puffertank/experiments/nethack-24h-20261009/entity512_20261010/CANDIDATE.json) |
| Immutable measured runner | [attribution_v37](/puffertank/experiments/nethack-24h-20261009/binaries/attribution_v37) |
| Engine used in the latest tests | [libnethack.so](/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/build/libnethack.so) |
| Mature score checkpoint | [fixwt4b_s705.bin](/puffertank/pufferlib/resources/nethack/fixwt4b_s705.bin) |
| Primary saved GPU batch | [mature_1024.bin](/puffertank/experiments/nethack-24h-20261009/original_config_20261010/mature_1024.bin) |
| Current handoff and chronological trials | [HANDOFF.md](/puffertank/experiments/nethack-24h-20261009/HANDOFF.md), [LEDGER.md](/puffertank/experiments/nethack-24h-20261009/LEDGER.md) |
| Latest raw comparisons and integrity checks | [overlap SUMMARY.json](/puffertank/experiments/nethack-24h-20261009/overlap512_20261010/SUMMARY.json), [INTEGRITY.json](/puffertank/experiments/nethack-24h-20261009/overlap512_20261010/INTEGRITY.json) |

The benchmark JSON supplies the base configuration; the entity candidate adds `NH_ENTITY_FUSED=15` and `NH_ENTITY_TRAIN_FUSED=15`. The latest stack also uses the corrected CUDA compute-connection setting and four Muon lanes. Exact commands and environments are retained with individual run logs. Do not substitute the older 2,048-environment saved batch when reproducing the primary configuration.

This document does not promote prototypes or change code. “Retained” means selected in the relevant experimental stack, unless a report explicitly establishes that a change was committed. The latest fusion and scheduling investigations left production files/defaults unchanged.

## Detailed report index

The following index lists performance reports and ledgers present in the experiment families reviewed for this consolidation. Older reports are historical snapshots; later matched checks and corrections take precedence. The campaign ledgers include micro-experiments that do not have standalone reports.

### cuBLAS, cross-environment performance, and determinism

- [breakout-workspace-20260917](/puffertank/experiments/breakout-workspace-20260917/REPORT.md)
- [cublas-4m-remaining-20260918](/puffertank/experiments/cublas-4m-remaining-20260918/REPORT.md)
- [cublas-all-env-perf-20260918](/puffertank/experiments/cublas-all-env-perf-20260918/REPORT.md)
- [cublas-clean-nethack-20260918](/puffertank/experiments/cublas-clean-nethack-20260918/REPORT.md)
- [cublas-env-matrix-20260918](/puffertank/experiments/cublas-env-matrix-20260918/REPORT.md)
- [cublas-final-check-20260918](/puffertank/experiments/cublas-final-check-20260918/REPORT.md)
- [cublas-internals-20260918](/puffertank/experiments/cublas-internals-20260918/REPORT.md)
- [cublas-nethack-4m-perf-20260918](/puffertank/experiments/cublas-nethack-4m-perf-20260918/REPORT.md)
- [cublas-nethack-current-20260918](/puffertank/experiments/cublas-nethack-current-20260918/REPORT.md)
- [cublas-pool-rule-20260918](/puffertank/experiments/cublas-pool-rule-20260918/REPORT.md)
- [cublas-short-horizon-equivalence-20260918](/puffertank/experiments/cublas-short-horizon-equivalence-20260918/REPORT.md)
- [cublas-speed-20260918](/puffertank/experiments/cublas-speed-20260918/REPORT.md)
- [cublas-upstream-equivalence-20260918](/puffertank/experiments/cublas-upstream-equivalence-20260918/REPORT.md)
- [cublas-upstream-match-20260918](/puffertank/experiments/cublas-upstream-match-20260918/REPORT.md)
- [determinism-causes-20260918](/puffertank/experiments/determinism-causes-20260918/REPORT.md)
- [nethack-determinism-cause-20260918](/puffertank/experiments/nethack-determinism-cause-20260918/REPORT.md)

### September profiling and optimization campaigns

- [nethack-batch-sweep-20260918](/puffertank/experiments/nethack-batch-sweep-20260918/REPORT.md)
- [nethack-gemm-opt-20260917](/puffertank/experiments/nethack-gemm-opt-20260917/REPORT.md)
- [nethack-gpu-detail-20260917](/puffertank/experiments/nethack-gpu-detail-20260917/REPORT.md)
- [nethack-perf-20260917 / LEDGER](/puffertank/experiments/nethack-perf-20260917/LEDGER.md)
- [nethack-perf-20260917/tight-loop/campaign2h](/puffertank/experiments/nethack-perf-20260917/tight-loop/campaign2h/REPORT.md)
- [nethack-perf-20260917/tight-loop/campaign2h/final](/puffertank/experiments/nethack-perf-20260917/tight-loop/campaign2h/final/REPORT.md)
- [nethack-reprofile-20260917](/puffertank/experiments/nethack-reprofile-20260917/REPORT.md)
- [nethack-size-profile-20260918](/puffertank/experiments/nethack-size-profile-20260918/REPORT.md)
- [nethack-train-loop-20260918 / RESULTS](/puffertank/experiments/nethack-train-loop-20260918/RESULTS.md)
- [nethack-train-loop-20260918 / SUMMARY](/puffertank/experiments/nethack-train-loop-20260918/SUMMARY.md)
- [nethack-training-profile-20260918](/puffertank/experiments/nethack-training-profile-20260918/REPORT.md)

### October engine, locality, and scaling

- [nethack-compact-state-20261008](/puffertank/experiments/nethack-compact-state-20261008/REPORT.md)
- [nethack-compact-state-20261008/engines/movement_masks](/puffertank/experiments/nethack-compact-state-20261008/engines/movement_masks/REPORT.md)
- [nethack-compact-state-20261008/engines/movement_masks_pgo](/puffertank/experiments/nethack-compact-state-20261008/engines/movement_masks_pgo/REPORT.md)
- [nethack-compact-state-20261008/engines/movement_tile16](/puffertank/experiments/nethack-compact-state-20261008/engines/movement_tile16/REPORT.md)
- [nethack-compact-state-20261008/engines/neighbour_prefilter](/puffertank/experiments/nethack-compact-state-20261008/engines/neighbour_prefilter/REPORT.md)
- [nethack-compact-state-20261008/engines/public_glyph_cache](/puffertank/experiments/nethack-compact-state-20261008/engines/public_glyph_cache/REPORT.md)
- [nethack-compact-state-20261008/engines/public_glyph_cache_release](/puffertank/experiments/nethack-compact-state-20261008/engines/public_glyph_cache_release/REPORT.md)
- [nethack-compact-state-20261008/fast_loop_20261009](/puffertank/experiments/nethack-compact-state-20261008/fast_loop_20261009/REPORT.md)
- [nethack-compact-state-20261008/flat_query_20261009](/puffertank/experiments/nethack-compact-state-20261008/flat_query_20261009/REPORT.md)
- [nethack-compact-state-20261008/floor_metadata_20261009](/puffertank/experiments/nethack-compact-state-20261008/floor_metadata_20261009/REPORT.md)
- [nethack-compact-state-20261008/floor_metadata_diagnosis_20261009](/puffertank/experiments/nethack-compact-state-20261008/floor_metadata_diagnosis_20261009/REPORT.md)
- [nethack-compact-state-20261008/focus_quota_20261009](/puffertank/experiments/nethack-compact-state-20261008/focus_quota_20261009/REPORT.md)
- [nethack-compact-state-20261008/full_gap_20261009](/puffertank/experiments/nethack-compact-state-20261008/full_gap_20261009/REPORT.md)
- [nethack-compact-state-20261008/locality_recheck_20261009](/puffertank/experiments/nethack-compact-state-20261008/locality_recheck_20261009/REPORT.md)
- [nethack-compact-state-20261008/monster_field_trace](/puffertank/experiments/nethack-compact-state-20261008/monster_field_trace/REPORT.md)
- [nethack-compact-state-20261008/movement_causal_tsc_20261009](/puffertank/experiments/nethack-compact-state-20261008/movement_causal_tsc_20261009/REPORT.md)
- [nethack-compact-state-20261008/movement_diagnostic_20261009](/puffertank/experiments/nethack-compact-state-20261008/movement_diagnostic_20261009/REPORT.md)
- [nethack-compact-state-20261008/movement_fastpath_census_20261009](/puffertank/experiments/nethack-compact-state-20261008/movement_fastpath_census_20261009/REPORT.md)
- [nethack-compact-state-20261008/movement_followthrough_20261009](/puffertank/experiments/nethack-compact-state-20261008/movement_followthrough_20261009/REPORT.md)
- [nethack-compact-state-20261008/movement_query_20261009](/puffertank/experiments/nethack-compact-state-20261008/movement_query_20261009/REPORT.md)
- [nethack-compact-state-20261008/movement_subsystem_20261009](/puffertank/experiments/nethack-compact-state-20261008/movement_subsystem_20261009/REPORT.md)
- [nethack-compact-state-20261008/object_presence_20261009](/puffertank/experiments/nethack-compact-state-20261008/object_presence_20261009/REPORT.md)
- [nethack-compact-state-20261008/primary_movement_20261009](/puffertank/experiments/nethack-compact-state-20261008/primary_movement_20261009/REPORT.md)
- [nethack-compact-state-20261008/primary_movement_costs_20261009](/puffertank/experiments/nethack-compact-state-20261008/primary_movement_costs_20261009/REPORT.md)
- [nethack-compact-state-20261008/primary_movement_direct_20261009](/puffertank/experiments/nethack-compact-state-20261008/primary_movement_direct_20261009/REPORT.md)
- [nethack-compact-state-20261008/warming_fields_20261009](/puffertank/experiments/nethack-compact-state-20261008/warming_fields_20261009/REPORT.md)
- [nethack-compact-state-20261008/warming_leaveout_20261009](/puffertank/experiments/nethack-compact-state-20261008/warming_leaveout_20261009/REPORT.md)
- [nethack-comprehensive-20261008](/puffertank/experiments/nethack-comprehensive-20261008/REPORT.md)
- [nethack-cpu-scaling-20261008](/puffertank/experiments/nethack-cpu-scaling-20261008/REPORT.md)
- [nethack-flamegraphs-20261009](/puffertank/experiments/nethack-flamegraphs-20261009/REPORT.md)
- [nethack-grouped-rollouts-20261008](/puffertank/experiments/nethack-grouped-rollouts-20261008/REPORT.md)
- [nethack-locality-target-20261008](/puffertank/experiments/nethack-locality-target-20261008/REPORT.md)
- [nethack-memory-attribution-20261008](/puffertank/experiments/nethack-memory-attribution-20261008/REPORT.md)
- [nethack-memory-locality-20261008](/puffertank/experiments/nethack-memory-locality-20261008/REPORT.md)
- [nethack-monster-locality-20261008](/puffertank/experiments/nethack-monster-locality-20261008/REPORT.md)
- [nethack-scaling-cause-20261008](/puffertank/experiments/nethack-scaling-cause-20261008/REPORT.md)

### October GPU, overlap, and current configuration

- [breakout-muon-parallel-20261009 / CONNECTIONS_REPORT](/puffertank/experiments/breakout-muon-parallel-20261009/CONNECTIONS_REPORT.md)
- [breakout-muon-parallel-20261009](/puffertank/experiments/breakout-muon-parallel-20261009/REPORT.md)
- [nethack-24h-20261009 / LEDGER](/puffertank/experiments/nethack-24h-20261009/LEDGER.md)
- [nethack-24h-20261009/attribution_20261010](/puffertank/experiments/nethack-24h-20261009/attribution_20261010/REPORT.md)
- [nethack-24h-20261009/entity512_20261010](/puffertank/experiments/nethack-24h-20261009/entity512_20261010/REPORT.md)
- [nethack-24h-20261009/floor_boxes](/puffertank/experiments/nethack-24h-20261009/floor_boxes/REPORT.md)
- [nethack-24h-20261009/model5m_20261010](/puffertank/experiments/nethack-24h-20261009/model5m_20261010/REPORT.md)
- [nethack-24h-20261009/original_config_20261010](/puffertank/experiments/nethack-24h-20261009/original_config_20261010/REPORT.md)
- [nethack-24h-20261009/overlap512_20261010](/puffertank/experiments/nethack-24h-20261009/overlap512_20261010/REPORT.md)
- [nethack-gradient-pipeline-20261009](/puffertank/experiments/nethack-gradient-pipeline-20261009/REPORT.md)
- [nethack-gradient-pipeline-20261009/diagnosis](/puffertank/experiments/nethack-gradient-pipeline-20261009/diagnosis/REPORT.md)
- [nethack-muon-followups-20261009](/puffertank/experiments/nethack-muon-followups-20261009/REPORT.md)
- [nethack-muon-followups-20261009/relaxed_numerics](/puffertank/experiments/nethack-muon-followups-20261009/relaxed_numerics/REPORT.md)
- [nethack-muon-parallel-20261009](/puffertank/experiments/nethack-muon-parallel-20261009/REPORT.md)
- [nethack-overlap-20261009](/puffertank/experiments/nethack-overlap-20261009/REPORT.md)
