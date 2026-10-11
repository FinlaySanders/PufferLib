# GPU profile: pretrained 4B score policy

The strongest targets are small-output training GEMMs and serial action sampling. This is a profile and source inspection, not an implemented optimisation or a speedup forecast.

## Scope

RTX 4090, 128 SMs. Analyse the already-recorded, warmed 15-second Nsight Systems traces for the original/static and retained engine/work-stealing builds. Both use the 4B s705 checkpoint, 512 environments, four buffers, 32 CPU workers and the original asynchronous PPO configuration. GPU kernel timings are matched to inference/PPO NVTX ranges using CUDA correlation IDs. See `analyze.py` and `breakdown.json` for all grouping and launch-shape data.

The old 20-head score policy is the measured network; these percentages are not asserted for newer policies or the depth architecture. No production or trainer files were edited.

## Measured breakdown

Percentages below use **summed kernel durations within each phase**. They are not wall-time percentages: kernels overlap within and across phases.

| Phase / kernel family | Original | Optimised engine |
|---|---:|---:|
| PPO: GEMMs | 78.5% | 77.8% |
| PPO: NetHack-specific kernels | 10.7% | 10.9% |
| PPO: optimiser-named kernels | 3.6% | 3.6% |
| PPO: recurrent kernels | 3.2% | 3.3% |
| Inference: GEMMs | 33.5% | 34.8% |
| Inference: action sampling | 30.6% | 29.6% |
| Inference: NetHack-specific kernels | 30.2% | 29.9% |
| Inference: recurrent kernels | 2.8% | 2.9% |

Family grouping is name-based: GEMMs called by optimisers are counted as GEMMs, not as optimiser-named kernels. Thus this table does not imply the full optimiser costs only 3.6%.

The previous union-of-intervals analysis found GPU kernels active for 88.14% and 92.89% of wall time. That measures whether any kernel is running, not whether all SMs are occupied. Training and inference overlap substantially.

## Priority 1: small-output training GEMMs

GEMMs launching at most 16 blocks, with only 32 threads per block, account for **5.586 seconds / 40.4% of PPO summed kernel time** in the optimised trace, and **4.894 seconds / 41.2%** in the original trace. The pattern is stable across both builds.

These are mostly the `16x16_128x1_nt` and `16x16_128x2_nt` cuBLAS-selected kernels. Examples in the optimised trace:

| Grid blocks | Threads/block | Calls | Total kernel duration | Median call |
|---:|---:|---:|---:|---:|
| 16 | 32 | 2,641 | 1.559 s | 383 us |
| 4 | 32 | 9,240 | 1.516 s | 26.6 us |
| 2 | 32 | 1,980 | 0.940 s | 37.1 us |
| 1 | 32 | 661 | 0.834 s | **1,300 us** |

A one-block kernel can use at most one SM at a time on this 128-SM GPU. Other kernels may concurrently use the remaining SMs, so this does not prove whole-device idleness. It does show very little parallelism within these expensive operations.

Source inspection suggests small weight-gradient matrices with long reduction dimensions are a likely source: `puf_mm_tn` folds batch/slot rows into K while output dimensions are feature widths, and the inventory, spell, monster and item branches invoke it for their gradients. Exact M/N/K and call-site attribution were not recorded by this trace, so the branch-level attribution remains a hypothesis rather than a measured claim.

Next experiment: capture M/N/K and call sites for these GEMMs, then benchmark a split-K reduction or an alternative GEMM algorithm for the offending shapes. Keep architecture and reward unchanged. Any altered reduction order requires numerical/gradient validation and end-to-end testing; it is not guaranteed bit-identical.

## Priority 2: action sampling

`sample_logits` consumes **2.493 seconds / 29.6% of inference summed kernel time** in the optimised trace: 12,631 attributed calls, roughly197 us mean,162 us median,371 us p90. Every call launches **one block of256threads**.

There are 512 environments across four buffers, so each call samples128 environments. The kernel assigns one environment per thread; the other128 threads return immediately. Each active thread then serially visits all20 action heads and their categories, computes masked log-sum-exp and a sampled CDF, and advances its Philox state. Its log-probability includes only the chosen verb's used heads, but sampling still computes all heads.

This is a concrete serial-work / small-grid hotspot. Candidate directions are greater parallelism within a distribution or a more specialised sampling kernel. Naively skipping unused heads changes random-number consumption and emitted action fields, so it is not automatically a behaviour-preserving optimisation. Preserve RNG and action semantics and verify explicitly before making such a change.

## Other observations

The remaining inference work includes many short NetHack feature kernels and GEMMs. Bias/ReLU is about6.4% of inference summed kernel time. Recurrent kernels are only around3% of either phase in this name-based breakdown. Neither is the first target suggested by these traces.

The most promising training-side target is the small-grid GEMMs because PPO is active through most of the asynchronous timeline. Faster sampling is promising too, but its benefit can be partly hidden under simultaneous PPO work. Percentages must not be interpreted as directly additive training speedups.

## Hardware-counter limitation

Nsight Compute is installed, but an isolated one-kernel CUDA probe returned `ERR_NVGPUCTRPERM`. The log is preserved as `counter-probe.log`. Therefore this report does **not** claim measured SM occupancy, DRAM bandwidth, tensor-core utilisation, cache hit rates, or warp-stall reasons. No host settings were changed to bypass the restriction.

The trace has profiler overhead and stochastic trajectories differ between builds. Use its durations and launch shapes to choose experiments; use separate clean timings to establish speedups.
