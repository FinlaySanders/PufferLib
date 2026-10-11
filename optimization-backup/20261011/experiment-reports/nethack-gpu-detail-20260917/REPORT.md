# Detailed warmed NetHack training profile

## Conclusion

The current score workload is limited by the GPU PPO update. CPU rollout simulation is nearly completely overlapped. The primary shape-specific opportunity is small-output weight-gradient GEMMs with very long reductions; Muon matrix operations are the next large component. Faster sampling reduces inference cost but does not remove the update bottleneck.

## Scope and evidence

- RTX 4090, 128 SMs; 512 environments, 32 CPU workers, asynchronous rollout/update overlap.
- Loaded actual fixed 4B score checkpoint s705, old 20-head article architecture, normal PPO/config; fresh optimiser state. This is not a profile of the newer depth/identify policy.
- Isolated candidate14 engine + work-stealing + optimised head sampler. Production sources unchanged.
- 64 updates / 16,777,216 steps completed; checkpoint loaded bytes match the source checkpoint.
- Nsight CUDA/NVTX capture: 15 seconds after 120-second warmup. Games are mature (typically over 20,000 turns on average), not fresh random-policy starts.
- Six complete PPO graph launches analysed. Both capture slots have identical node indices, operations and dependency edges. Each executed graph exactly matches all 100,920 kernel-node indices. Instantiation changes the upper graph-ID bits; lower node indices are preserved.
- Capture-time instrumentation records matrix dimensions, source call sites and graph dependencies; no added timed GPU synchronisations or numerical changes.

Mean observed PPO graph span: **2.398 s**. Mean duration-weighted dependency path: **2.336 s**, accounting for **97.4%** of the observed span. Gaps between successive PPO graph executions are only 0.7–2.6 ms. Normal unprofiled epochs nearby are approximately 2.35–2.37 seconds.

## Dependency-path breakdown

These rows are non-overlapping contributions along the computed longest dependency path, expressed against the observed update span. They are not sums of all concurrent GPU work.

| Component | ms/update | % of update span |
|---|---:|---:|
| Small-output long-reduction gradients | 848.7 | 35.4% |
| Muon matrix operations | 513.6 | 21.4% |
| NetHack custom kernels | 256.5 | 10.7% |
| backward other GEMMs | 254.4 | 10.6% |
| forward other GEMMs | 124.8 | 5.2% |
| Other kernels | 111.2 | 4.6% |
| Optimizer/norm kernels | 84.1 | 3.5% |
| Recurrent kernels | 76.7 | 3.2% |
| Device copies/memsets | 66.0 | 2.8% |
| Remaining scheduling/gap time | 62.1 | 2.6% |

## Four largest problematic gradients

The following four alone consume about 0.59 s per update on the dependency path. Shapes refer to C = AᵀB with output M×N and reduction length K. All use one-warp blocks, with only 1–16 blocks on a 128-SM GPU.

| Gradient | M × N | K | Blocks | Approx. ms/update |
|---|---:|---:|---:|---:|
| Inventory numerical-state projection (`inv1s_wgrad`) | 16 × 24 | 225,280 | 2 | 153 |
| Inventory entity MLP second layer (`mv2_wgrad`) | 64 × 64 | 225,280 | 16 | 151 |
| Decoder inventory-key projection (`k_wgrad`) | 16 × 16 | 225,280 | 1 | 143 |
| Inventory entity MLP first layer (`mv1_wgrad`) | 64 × 16 | 225,280 | 4 | 140 |

Here 225,280 = 4,096 training observations × 55 inventory slots. Related monster/floor-item gradients reduce 65,536 rows and contribute another substantial block of time. Across these long-reduction, small-output shapes, the dependency-path cost is about 0.85 s/update.

The present cuBLAS-selected WMMA kernels parallelise across the tiny output, leaving very few blocks to perform the long reduction. This establishes poor launch parallelism, not a measured occupancy or bandwidth figure: hardware counters are unavailable.

## Why earlier percentages were misleading

- The earlier 30% sampling figure was a fraction of **inference kernel time**, not total training time. In this profile the optimised sampler sums to 0.366 seconds over 15 seconds (5.9% of summed inference kernel time); inference largely overlaps PPO.
- The earlier approximately 3.6% “optimiser” category counted kernels with optimiser names. Muon’s GEMMs were classified under generic GEMM. The explicit source mapping now shows Muon matrix work alone is approximately 0.514 s/update (21.4%); optimiser/norm kernels add further work.
- Kernel activity near 100% does not mean the GPU is efficiently utilised: one active block can occupy the timeline while almost all SMs are idle.

## Next optimisation to test

First benchmark a shape-aware weight-gradient path that parallelises the long reduction (e.g. a suitable split-K GEMM algorithm), then measure the complete asynchronous epoch. Follow with Muon matrix-operation profiling/algorithm selection. Preserve architecture and PPO settings. Changes to reduction order require explicit numerical/gradient checks; bitwise equality must not be assumed. No speedup is promised by adding the component percentages: other paths and rollout contention can become limiting.

## Limits and failed attempts

- The weighted DAG path includes measured kernel/copy durations but does not model scheduler/resource contention counterfactually. It is attribution, not an exact prediction of a faster implementation.
- Hardware counters are blocked (`ERR_NVGPUCTRPERM`); no occupancy, bandwidth or tensor-core utilisation claim is made.
- Initial profiler attempts failed due to the metadata collector selecting a conflicting CUPTI library and an OS-runtime tracing/startup interaction. The latter’s exact cause was not established. A subsequent CUDA-only run produced interleaved metadata because the capture flag was shared across inference threads. Those attempts remain in `profile/`, `profile-retry/`, `profile-cuda/` and debug logs; excluded from attribution. Final instrumentation is thread-local and uses the already loaded CUPTI library.
- No production code, engine library, reward, architecture or training configuration was changed. Profiling additions live only in this experiment directory.

## Artifacts

- `profile-final/timeline.nsys-rep` and `timeline.sqlite`: raw warmed trace.
- `profile-final/graphs.jsonl`: shapes, source arguments and DAG.
- `profile-final/gemms.csv`: all per-operation timing rows.
- `profile-final/summary.json`: coverage, six complete dependency paths and timing attribution.
- `profile-final/validation.json`: checkpoint and production-preservation checks.
- `analyze.py`, `report.py`, `run_final.py`: analysis and reproduction.
- `source/src/graph_detail.cuh`, instrumented isolated `algo.cu` / `pufferl.cu`: capture-only instrumentation.
