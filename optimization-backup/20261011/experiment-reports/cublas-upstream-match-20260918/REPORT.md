# Restore upstream equivalence for the repeatable workloads

Changed the private workspace capacity from 32 MiB to 4 MiB, keeping CUBLAS_DEFAULT_MATH and one handle/workspace per stream. Applied exactly this one-line change to the working tree, uncommitted. No other user edits changed.

NMMO3's 32 MiB results were repeatable but different from upstream. With 4 MiB, both checkpoints match upstream exactly. This shows workspace capacity changes numerical results on that workload; the exact internal GEMM implementation was not traced.

## Verification

18 candidate runs (two per configuration), all successful, with finite saved FP32 weights. Every saved checkpoint matches the corresponding previously verified upstream reference byte-for-byte, and both candidate repeats match.

- CartPole, Pong, Drone, T-maze, GPU Admiral, NMMO3: 32 updates, seed 901, checkpoints at updates 16 and 32. Same valid configurations as ../cublas-env-matrix-20260918/REPORT.md, including single-policy GPU Admiral and adequate evaluation agent counts.
- CPU/GPU Breakout: 134,217,728 steps, seed 901, all three checkpoints match.
- 2048: 16,777,216 steps, seed 901, final checkpoint matches.

Exact commands and hashes: verify/results.json. Baseline references are from the prior two-repeat upstream checks. Source snapshot and binaries: source/. Original diff: before.patch; updated diff: after.patch.

## Limits

This establishes equality for all nine tested configurations with a repeatable upstream reference, on this machine/toolchain. It is not a universal bitwise guarantee for every possible shape, configuration, or GPU. NetHack, Craftax, Minimal, Asteroids and Snake previously failed upstream repeatability, so none supplies a unique reproducible upstream checkpoint to match. Their previous patched results used 32 MiB and do not validate the new 4 MiB variant. Performance was not remeasured here; the earlier 17.2% NetHack gain must not be attributed to this variant without a new benchmark.
