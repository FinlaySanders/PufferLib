`cublasSetStream` resets the handle's workspace to the default pool, so the trainer's allocated scratch buffers were not being used by subsequent dense GEMMs. Restore the workspace after selecting the stream.

Allocate separate workspace for concurrent streams before CUDA graph capture. This matters for GPU environments, where rollout and learner graphs originate from the same host thread: restoring a single thread-local buffer made GPU Breakout produce NaNs. The side-stream weight-gradient handle retains its separate buffer. Also disallow reduced-precision reductions; the workspace-only NetHack candidate failed the actual-gradient accuracy check.

Validation on an RTX 4090:

- CPU and GPU Breakout: baseline and patched versions each repeated for 134M steps. All three saved checkpoints match byte-for-byte within each version/backend; all weights and reported losses are finite.
- 2048: repeated 16.8M-step runs also match checkpoints within each version and have finite weights.
- NetHack final stream-safe patch: 35.371 s → 26.158 s for 3,932,160 timed steps, **+35.2% throughput** (26.0% less time). Baseline/patched/patched/baseline; each run trained 8,388,608 steps from the fixed 4B policy. Timed updates 16–30, excluding warm-up and last update. All saved weights finite.
- Throughput: CPU Breakout +0.02%, GPU Breakout -0.72%, 2048 +2.30%, using reversed-order repeats and excluding warm-up, final evaluation and checkpoint writes.
- Determinism here means repeatability of a given version. The stricter arithmetic changes weights relative to baseline; long-run learning equivalence is not claimed.

The workspace reset is documented in [cuBLAS](https://docs.nvidia.com/cuda/cublas/index.html#cublassetworkspace).
