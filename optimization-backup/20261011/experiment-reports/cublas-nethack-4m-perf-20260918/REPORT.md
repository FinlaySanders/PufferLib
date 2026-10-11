# NetHack 4 MiB cuBLAS performance check

Upstream 5.0 versus the current cublas branch, normal random initialization, clean fast-nle e7f656856. Deferred optimizations excluded. RTX 4090, 512 environments, 32 CPU threads. Four serial ABBA runs, 8,388,608 training steps each, seed 901. Timing covers rollout and PPO update for epochs 16–30, excluding startup, checkpoint writing and final evaluation. Each run contributes 3,932,160 measured steps.

| Variant | Steps/second |
|---|---:|
| Upstream | 112,696 |
| Per-stream handle/workspace, 4 MiB | 173,061 |

Throughput improvement: 53.6%; time reduction: 34.9%.

Both patched final checkpoints are bitwise identical. Upstream final checkpoints differ between repeats; patched checkpoints do not match either unique upstream reference (there is no repeatable upstream reference in this test). All four runs exited successfully with finite checkpoint values. This establishes repeatability of this patched configuration, not universal equivalence. This is an early-training performance check, not a late-game benchmark.

Clean engine SHA256: 7881e86e083b10c971d373c0351d56d7fa0df5f4bc3bba6743c32f61e77e8cc2.
Source diff unchanged after testing. Commands, hashes and per-run timings are in results.json; scratch timing instrumentation is in validate.py.
