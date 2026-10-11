# cuBLAS workspace PR validation

Final candidate: /puffertank/pufferlib-cublas-workspace, branch fix-cublas-workspace, based on upstream/5.0 at 6ffa5b10.

## Determinism

CPU and GPU Breakout each ran baseline / patched / patched / baseline for 134,217,728 training steps per run, seed 901, default configuration. All three saved checkpoints (65,536,000; 131,072,000; 134,217,728 steps) match byte-for-byte between repeats of each version. Every saved FP32 weight is finite; logs contain no nonfinite losses. This tests within-backend repeatability, not CPU-vs-GPU trajectory equality. The strict-reduction setting changes weights relative to baseline.

2048 similarly passes repeat checkpoint equality and finite-weight checks across 16,777,216-step runs, seed 901, default configuration.

## Throughput

RTX 4090, serial runs, reversed order on repeat. Timed training-loop updates exclude the first quarter and final update; startup, evaluation, logging and checkpoint writing excluded. Rollout and PPO work are included. Scripts, per-epoch logs, commands and full checkpoint hashes are retained in this directory.

| Environment | Baseline steps/s | Patched steps/s | Change |
|---|---:|---:|---:|
| Breakout CPU | 14,662,777 | 14,665,836 | +0.02% |
| Breakout GPU | 42,532,315 | 42,224,006 | -0.72% |
| 2048 | 739,260 | 756,228 | +2.30% |

## Rejected initial patch

Restoring one workspace per host-thread handle is unsafe when GPU rollout and learner graphs captured from that thread overlap on different streams. GPU Breakout produced NaNs with both workspace-only and workspace-plus-strict variants. Repeated invalid checkpoint hashes are NOT accepted as determinism evidence; those throughput measurements are invalid.

The final patch registers separate stream-specific scratch buffers before graph capture. The side-stream dW handle retains its own workspace. CPU workers register their inference stream. Unregistered streams retain cuBLAS's default pool. All final validation above uses this revised implementation.

## Final NetHack confirmation

NetHack final stream-safe patch: 35.371 s → 26.158 s for 3,932,160 timed steps, **+35.2% throughput** (26.0% less time). Baseline/patched/patched/baseline; each run trained 8,388,608 steps from the fixed 4B policy. Timed updates 16–30, excluding warm-up and last update. All saved weights finite.
