# NetHack upstream nondeterminism: workspace reset during concurrent inference

## Finding

Upstream initializes a private cuBLAS workspace, but cublasGemmExDense calls cublasSetStream before each GEMM. That resets the workspace to the cuBLAS default pool. Concurrent inference streams consequently run without the intended private workspace. In this NetHack workload, that produces non-repeatable inference outputs even before the first training update.

## Controlled evidence

Clean engine e7f656856, upstream trainer 6ffa5b10, normal initialization, same seed 901. Diagnostic copies only; no production edits. Two repeats per control, 4 training updates (1,048,576 transitions) with original 8.4M-step learning schedule, checkpoint each update. Saved initial weights and first rollout actions, values, log probabilities, rewards, terminals and initial recurrent states.

| Control | Initial weights match | First rollout matches | All four checkpoints match |
|---|---|---|---|
| Original upstream, 4 rollout buffers | Yes | No | No |
| Same + CUBLAS_WORKSPACE_CONFIG=:4096:8 | Yes | No | No |
| Same + restore workspace immediately after cublasSetStream | Yes | Yes | Yes |
| Original upstream, 1 rollout buffer | Yes | Yes | Yes |

Default pair: first differing values at zero-based rollout timestep 362, in buffer 3 (agents 384–511); first differing sampled action at timestep 362, agent 407, head 18. Initial recurrent states match. Divergence therefore predates the first PPO update. The first observations affected by action divergence feed back into subsequent engine trajectories; final policy differences are not merely a checkpoint-save artifact.

The workspace-restoration control changes only one line in upstream algo.cu and keeps CUBLAS_DEFAULT_MATH. This experimental CPU-only control restores g_cublas_workspace or g_cublas_dw_workspace after setting the stream. It is not proposed as a general patch: GPU rollout/training streams on one host thread need separate scratch buffers, as provided by the user's current per-stream implementation.

NVIDIA documents that cublasSetStream resets the workspace and that multi-stream execution can select internal implementations non-deterministically based on workspace availability. Explicit per-stream workspaces or handles are documented remedies. Our controls identify this path; we have not identified the specific internal GEMM algorithm or kernel that first changes. The documented environment-variable workaround did not fix this captured-graph workload in our test and should not be claimed as a solution here.

Source: https://docs.nvidia.com/cuda/archive/13.1.0/cublas/index.html#results-reproducibility

Full-length evidence from preceding clean test: both current-patch 8.4M-step runs matched exactly; upstream runs did not (../cublas-clean-nethack-20260918/REPORT.md). CPU/GPU Breakout and 2048 are separately repeatable and match upstream in the prior checks; this NetHack failure does not invalidate those results.

## Reproduction artifacts

- trace.py: generates diagnostic source and original/bounded tests.
- run.py: runs diagnostic binary (corrected eval_agents=8).
- controls.py: workspace-restoration and one-buffer controls.
- results.json / controls.json: SHA256 for all snapshots and checkpoints.
- summary.json: comparison table.
- source/src: diagnostic source, currently with one-line workspace restoration.
- Per-run directories: logs, snapshots, and checkpoints.
- failed-eval-agents1: discarded initial harness attempt; training completed but evaluation rejected one eval agent with four buffers. Excluded from results.

The existing cuBLAS working diff was verified unchanged.
