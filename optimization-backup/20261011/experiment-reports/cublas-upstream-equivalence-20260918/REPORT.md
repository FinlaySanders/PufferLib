# Upstream checkpoint equivalence: PASS

Baseline: upstream/5.0 at 6ffa5b10dbbbe4d1e8288367c7d9d3acd3bad4a2.
Candidate: candidate.patch (current working diff), default cuBLAS math mode.

| Environment | Steps per run | Matches upstream | Repeatability |
|---|---:|---|---|
| CPU Breakout | 134,217,728 | All 3 checkpoints identical | Both versions identical |
| GPU Breakout | 134,217,728 | All 3 checkpoints identical | Both versions identical |
| 2048 | 16,777,216 | Final checkpoint identical | Both versions identical |

Each environment ran upstream / candidate / candidate / upstream, seed 901, default environment config. RTX 4090, CUDA_VISIBLE_DEVICES=0, OMP_NUM_THREADS=8; runs and builds serial. Every run exited successfully, all saved FP32 weights were finite, and logs had no nonfinite losses. Comparison uses SHA-256 of complete checkpoint files. Full commands and hashes are in results.json; source snapshots and binaries are under source/.

This establishes checkpoint equivalence for these configurations on this machine; it does not establish equivalence for NetHack, other shapes, hardware or CUDA versions. No throughput claim is made by this test.
