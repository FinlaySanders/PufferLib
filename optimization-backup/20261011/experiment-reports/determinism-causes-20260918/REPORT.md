# Upstream repeatability investigation

Baseline: upstream 5.0 6ffa5b10; one RTX 4090; seed 901; serial repeated processes, default BF16. All diagnostic edits are in this directory, not the working branch. Initial weights, first-rollout tensors and checkpoints were compared byte-for-byte. All included runs exited successfully and all saved weights are finite.

## Findings

| Environment | Baseline observation | Isolated control | Result |
|---|---|---|---|
| NetHack | First rollout diverges before PPO; async=0 still gives different checkpoints | Restore workspace immediately after cublasSetStream (previous investigation and current patch checks) | Repeats |
| Craftax | First rollout and first checkpoint match; second checkpoint differs | Only restore workspace after cublasSetStream, 4 MiB | All four diagnostic updates match |
| Snake | First rollout and all four checkpoints differ | Replace four process-global rand() calls with rand_r(&env->rng) | First rollout and all four checkpoints match |
| Minimal | Initial rollout matches; first differing checkpoint at update 26 | Replace shared-memory float atomicAdd with fixed-order accumulation | All 32 checkpoints match |
| Asteroids | Initial rollout matches; first differing checkpoint at update 20 | Same fixed-order accumulation change | All 32 checkpoints match |

### Workspace path: NetHack and Craftax

Upstream src/algo.cu sets a private workspace at handle initialization, but cublasGemmExDense calls cublasSetStream before every GEMM, which resets that workspace. Restoring the workspace alone makes the diagnostic pairs repeat. Existing per-stream handles/workspaces fix this path without sharing scratch across concurrent streams. These controls strongly implicate the workspace/captured-GEMM path; the specific internal cuBLAS algorithm or scratch allocation that first differs has not been traced.

NetHack's historical size condition deserves qualification. The standard configuration has horizon=512, buffers=4, agents=512, so horizon*buffers>agents. Disabling async overlap while retaining those dimensions does NOT restore repeatability (four checkpoints differ). Reducing horizon to 128 gives equality, and both unmodified upstream and the workspace-restoration control repeat through all 32 updates in that configuration. Thus reducing horizon removes this failure, but that alone does not establish an indexing bug or prove it is the historical bug. The old shared RNG-offset approach was replaced by per-buffer persistent RNG states (eeddcebd); that replacement remains in the current source. The exact historical threshold-specific change has not been conclusively identified.

### Snake

spawn_snake and spawn_food in ocean/snake/snake.h use rand(), which shares one process-wide RNG stream. Concurrent environments consume draws in scheduling-dependent order. Per-environment rng already exists and is seeded by the vector environment. The isolated diagnostic substitutes rand_r(&env->rng), leaving the trainer untouched. This changes the RNG sequence, so it restores repeatability rather than reproducing an old upstream trajectory.

### Minimal and Asteroids

me_grad_entity_kernel / ae_grad_entity_kernel scatter floating-point contributions using shared-memory atomicAdd. Atomicity prevents lost updates, but does not fix addition order. The diagnostic assigns each feature channel to one thread and sums contributions in ascending j order, eliminating contention and fixing rounding order. No cuBLAS change is included in these controls. Short four-update tests did not expose either failure; 32-update tests did, and the ordered-sum controls repeat through all 32 updates. These are diagnostic implementations, not performance-validated production fixes.

## Artifacts and limits

run.py, resume.py, long.py and short_horizon.py contain exact transformations and commands. results.json files contain all hashes; summary.json lists mismatches. Failed Minimal attempts (absent state buffer and insufficient eval agents) are retained under failed-* and excluded. No production source was changed. Limited to the tested seed, GPU, sizes and durations; not a universal determinism guarantee.
