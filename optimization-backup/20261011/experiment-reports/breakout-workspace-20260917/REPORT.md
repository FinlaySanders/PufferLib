# Breakout cuBLAS workspace benchmark

RTX 4090; current Breakout configuration (4096 agents, 8 CPU workers, 4 layers, width 32). Each run trains 134,217,728 steps from the same seed. Timed updates 256–1022 exclude startup, graph capture and final update; each timed block contains 100,532,224 steps. Two runs per variant, reverse order on repeat. Timing includes rollout and PPO, with existing GPU synchronisation; excludes logging, final evaluation and checkpoint writing.

| Variant | Timed seconds (repeats) | Aggregate steps/s | Throughput change |
|---|---|---:|---:|
| baseline | 6.8898, 6.9079 | 14,572,285 | +0.00% |
| workspace | 6.8503, 6.8297 | 14,697,709 | +0.86% |
| strict | 6.8152, 6.8870 | 14,673,901 | +0.70% |

workspace: restore the private 32 MiB workspace after cublasSetStream. strict: workspace fix plus CUBLAS_MATH_DISALLOW_REDUCED_PRECISION_REDUCTION (the retained NetHack patch).

These are throughput measurements, not evidence of matched learning or numerical equivalence. Production sources were not edited; all changes and outputs are isolated here.

NVIDIA documents the workspace reset: https://docs.nvidia.com/cuda/cublas/index.html#cublassetworkspace
