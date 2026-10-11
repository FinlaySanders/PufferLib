---
name: cublas-stream-workspace
description: cuBLAS workspace/stream landmines in src/algo.cu and the user's preference for a one-file fix that keeps upstream structure
metadata:
  type: project
---

2026-09-18, branch `cublas` (base = upstream/5.0 6ffa5b10). Upstream `cublasGemmExDense` calls `cublasSetStream` per GEMM, which unconditionally resets the handle workspace to the default pool, so the 32 MB user workspace was never used.

Verified on the 4090 with breakout (CPU-env 2 buffers and `--cu` GPU-env, async + cudagraphs):
- `cublasCreate` inside graph capture aborts with "cudaStreamEndCapture failed".
- plain `cudaMalloc` inside capture aborts the same way. Anything lazy must be allocated before capture.
- Main thread on the GPU backend runs GEMMs on three streams (train, dW side stream, streams[0]); train and rollout graphs replay concurrently, so they need distinct workspaces. Workers use one stream.
- A train run builds a second trainer in the same process for the final eval (`close_pufferl` frees nothing), so any per-thread stream table must reset in `cublas_init_handle`.
- `CUBLAS_MATH_DISALLOW_REDUCED_PRECISION_REDUCTION` vs default: bit-identical and same speed for bf16/COMPUTE_32F GEMMs here.

User's stated preferences (in order given): small diff to upstream, then "simpler", then "everything set beforehand in memory, small pufferl.cu additions fine", finally "line count does not matter, match the codebase idiom and make it make sense". Final working-tree shape: `struct CublasStream {stream, handle, workspace}` in a fixed thread-local array with a count (mirrors AllocEntry regs/num_regs), `cublas_init_stream(stream)` creates and binds once, `cublas_handle(stream)` is a pure lookup. Only two bare precondition asserts (table full, lookup miss); user disliked message-style asserts on the cuBLAS setup calls, and upstream algo.cu has just two bare asserts. `cublas_init_handle()` resets the count, then inits stream 0 and the dW stream. pufferl.cu calls `cublas_init_stream` beside each stream's creation: train_stream, streams[0] on the GPU backend, and the worker's own stream in vec_thread_main (replacing the worker's init call; workers never run backward). Tried and dropped: linked-list registry, get-or-create table, lazily claimed workspace pool with per-call SetWorkspace.

Codebase idioms confirmed while doing this: braces on almost every if/for, `constexpr int` constants in algo.cu, `assert(call == success && "fn: msg")` on setup calls in pufferl.cu only (algo.cu uses bare precondition asserts, sparingly), "init"/"create" for immediate setup while "register" means deferred (alloc_register then alloc_create), and close_pufferl's comment says all memory is allocated up front and never freed by design.

**Why:** user wants a small, simple diff to upstream with explicit up-front setup. **How to apply:** prefer explicit registration before use over lazy creation; a few lines in pufferl.cu are acceptable. See [[pufferl-off-limits]], [[cuda-backend-perf-profile]].

Readiness evidence 2026-09-18 (4090, breakout, 8M steps, upstream built from a scratch worktree): final checkpoints md5-identical to upstream in all four configs (async=0 1 buffer hidden 128 and 512, async 4 buffers hidden 512, GPU backend hidden 512), SPS equal within noise, peak MiB upstream/patched 3686/3654, 4172/3890, 3676/3724. So the fix is numerically and speed neutral here; frame the PR as correctness, not perf. nethack builds and trains 3M steps clean, tests/test_nethack_encoder.py PASS. Not covered: multi-GPU. Broken upstream independently: tests/profile_kernels.cu and tests/test_osrs_entity_encoders.py do not compile. Comparison harness idea: `git worktree add --detach` in scratchpad plus symlinks to raylib-5.5_linux_amd64 and vendor, then build.sh with an output path.
