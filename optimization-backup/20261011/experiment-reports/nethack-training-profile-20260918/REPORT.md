# Fixed-policy full training profile — 18 September 2026

The full pipeline is GPU-side limited in this configuration, in both fresh-policy games and mature 4B score-policy games. This differs from rollout-only measurements: PPO occupies the GPU while much of the environment work runs concurrently. Mature gameplay raises batch time modestly; CPU starvation is not the dominant full-training cost here.

## Method

Retained engine61 + shared pool83, 24 workers plus 4 submitters; RTX 4090; 512 environments, four rollout buffers, horizon 512; 4-layer, width-1024 policy; minibatch 4096 and replay ratio 1.78021395 (113 minibatches per training batch). CUDA graphs and asynchronous rollout/training are enabled. Both conditions use the same configuration.

The early condition uses random initial parameters. The mature condition loads fixed 4B score policy s705, with 60 seconds of warm-up. Every forward, PPO loss, backward, gradient clipping, Muon update, and BF16 cast runs. Updates and casts write scratch weights; forward/backward and actor copies use unchanged policy parameters. Recurrent and game states continue normally. Fresh optimizer state is used: this is a workload profile, not resumed learning.

All four 33,554,432-step runs finished with initial and final checkpoints byte-identical. Mature initial checkpoints also match s705. See `weight-proof.json`. Only isolated experiment sources were changed.

## Early versus mature

Graph-level captures provide batch timing and CPU phase measurements. Separate node-level captures provide actual kernel intervals. Each uses the 13-second interior of a 15-second trace.

| Measurement | Fresh policy | Mature 4B score policy |
|---|---:|---:|
| Mean current game turn | 118 | 24,239 |
| Games beyond 10,000 turns (%) | 0.0 | 68.6 |
| Training batch duration, graph trace (s) | 1.494 | 1.543 |
| Policy steps/s, graph trace | 175,515 | 169,908 |
| PPO graph envelope, wall time (%) | 98.5 | 94.9 |
| Any GPU kernel active, node trace (%) | 96.9 | 97.5 |
| Any GPU kernel or copy active, node trace (%) | 99.3 | 99.5 |
| PPO kernel intervals, node trace (%) | 92.7 | 93.0 |
| Inference kernel intervals, node trace (%) | 38.4 | 44.2 |
| PPO/inference kernel overlap, node trace (%) | 34.1 | 39.7 |
| Mean coordinator environment phase (%) | 41.2 | 43.8 |
| Mean coordinator GPU wait (%) | 40.0 | 37.7 |

PPO and inference overlap; their percentages must not be added. GPU activity means at least one kernel/copy is active, not SM occupancy or peak GPU efficiency. Graph envelopes include internal gaps. Coordinator percentages are averages across four threads, not serial wall-time components.

## GPU targets

| Summed GPU kernel duration within the 13-second node trace | Fresh | Mature |
|---|---:|---:|
| PPO forward/loss/backward (s) | 7.13 | 7.26 |
| PPO optimizer including Newton–Schulz GEMMs (s) | 5.29 | 5.17 |
| Rollout inference (s) | 9.85 | 9.86 |
| Optimizer share of PPO kernel duration (%) | 42.62 | 41.59 |

These are summed kernel durations and include concurrent streams; they are not additive elapsed time. Optimizer classification follows the training-stream sequence from the first Muon norm kernel through the weight update and subsequent cast. Per-kernel details are in each node capture’s `kernel_breakdown.json`.

The useful next targets are neural-network matrix operations and the substantial Muon optimizer workload, including opportunities to reduce small-kernel and matrix-operation overhead. Rollout inference also competes for GPU resources. Further engine work can improve evaluation speed and heavier/deeper environments, but it should not be assumed to translate proportionally into training SPS at these settings.

## Limits

This mature workload is long-lived score-farming gameplay, predominantly on shallow floors; it is not a deep Castle-policy profile. Warm-up and game-age markers demonstrate mature games rather than just a loaded checkpoint. Two independent tracing modes corroborate GPU-side activity, but profiling adds overhead: these SPS values are not a clean performance benchmark. Detailed node tracing increases launch overhead, so use the lighter trace for timing and CPU-phase conclusions. Freezing weights prevents degradation but does not establish that the interrupted resumed-training attempt actually degraded.

## Reproduction and artifacts

`METHOD.md`, `profiling-only.patch`, `capture.py`, `analyze.py`, `kernel_breakdown.py`, `summary.json`, and `weight-proof.json` are alongside this report. Each capture directory contains its exact command and selected environment overrides, raw Nsight report, SQLite export, logs, initial/final checkpoints, and analysis. Capture labels can only be reused after choosing fresh output directories.
