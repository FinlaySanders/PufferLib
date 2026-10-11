# Batched Muon GEMMs with numerical differences allowed

The user explicitly allowed changes in floating-point results for this experiment. Both batching variants were therefore timed through the full pipeline and tested with real optimizer updates on a saved batch; bitwise differences were not a rejection criterion.

## Performance

| Variant | GPU PPO graph (ms) | GPU throughput change | Full-pipeline SPS | Net change | GPU memory in mature batches (MiB) |
|---|---:|---:|---:|---:|---:|
| Four-stream Muon control | 1151.33 | +0.00% | 193,181 | +0.00% | 8840.1 |
| Batch matching small matrices | 1138.80 | +1.10% | 192,839 | -0.18% | 8396.1 |
| Batch all matching matrices | 1137.73 | +1.20% | 190,877 | -1.19% | 8314.1 |

Two independent processes per variant, in control–small–all–all–small–control order, separately for GPU and full-pipeline timing. GPU processes execute two warmups and twelve measured complete PPO graphs from a restored mature rollout. Each graph includes 113 optimizer updates. Full processes run 80 rollout batches and time batches 64–78.

Full timing uses the established controlled mature-game workload: a frozen 15,552,136-parameter 4B policy, optimizer writes to scratch, 2,048 environments (four copies of 512 recorded streams), horizon 128, minibatch 4,096 and 24 shared CPU workers. The entire rollout/inference/forward/backward/optimizer pipeline executes. These are compute benchmarks, not resumed learning runs. Every variant preserves the frozen actor weights and all per-batch environment observation hashes.

The control already includes the cuBLAS workspace fix, four-stream Muon, gradient pipelining, CUDA_DEVICE_MAX_CONNECTIONS=32 and the retained engine optimizations. RTX 4090, same binary and engine for all three variants.

## Exposed rollout wait

| Variant | Mean exposed rollout tail (ms per batch) |
|---|---:|
| Four-stream Muon control | 89.05 |
| Batch matching small matrices | 104.60 |
| Batch all matching matrices | 119.66 |

The GPU-only gain does not become a useful end-to-end throughput gain here. The larger exposed rollout tail offsets the faster training graph. This measures delayed rollout readiness; it does not isolate CPU simulation from GPU inference, transfers or scheduling. GPU memory is a per-batch allocation snapshot, not a measured peak.

## Numerical checks

Both implementations retain global clipping, momentum, normalization and all five Newton–Schulz iterations. The candidate replaces equal-shaped individual matrix products with cuBLAS pointer-array batched products and disjoint scratch. Small-only batching includes 16×32, 64×16, 64×64 and 16×48 groups; broad batching also includes four 3072×1024 recurrent matrices.

| Variant | Relative L2 difference in master weights after 113 updates | Maximum absolute weight difference | Finite weights, momentum and updates |
|---|---:|---:|---|
| Batch matching small matrices | 0.04174% | 0.01707339 | True |
| Batch all matching matrices | 0.04040% | 0.02028676 | True |

The first raw gradient is identical for each candidate and control. Subsequent optimization trajectories diverge. The table measures accumulated differences after 113 updates on one controlled saved batch, not the error of an individual GEMM.

## Short real-training sanity test

The user requested stopping training checks once the timing results showed no useful gain. The control and small-only runs had already finished 8,388,608 steps each; the all-matrix run was stopped by SIGTERM on its verified PID. Its nonzero exit was requested cancellation, not an observed numerical failure. No further training validation was performed and no learning-quality conclusion is drawn.

## Artifacts

RESULTS.json contains aggregate timing, individual process values, numerical comparisons and training sanity checks. gpu.json, full.json, proof.json and on_policy.json contain the runner results. campaign.py reproduces each stage. ../runs/relaxed_* contain exact commands, binary hashes, logs, GPU telemetry, checkpoints and raw state dumps. The experimental source remains in ../source. Production training sources are unchanged.
