---
name: cuda-backend-perf-profile
description: Key CUDA-backend performance facts for pufferlib 4.0 (obs upload dominates rollout; dirty-cache DMA penalty; profile.sh caveats)
metadata: 
  node_type: memory
  type: project
  originSessionId: 1618e734-1bdd-4dcf-a665-a4838df317d9
---

Profiling facts for the pufferlib 4.0 CUDA backend (measured 2026-07-02, RTX 4090, breakout):

- The per-step obs host→device copy dominates rollout GPU time (was ~212 µs vs ~32 µs of kernels/step). Pinned-memory DMA runs at ~half speed (9 GB/s vs 16-22) when the CPU env threads have just dirtied the source lines in cache — confirmed with a standalone dirty-vs-clean test. Fix shipped (2026-07-02): `obs_writeback()` in vecenv.h — clwb/clflushopt the obs slice before `cudaMemcpyAsync` (9→16 GB/s, +6-13% SPS, bit-identical checkpoints verified by md5 of same-seed runs). The user rejected an earlier bf16-CPU-conversion staging layer: envs that want bf16 obs should use the existing `OBS_TENSOR_T PrecisionTensor` + `src/bf16.h` option instead.
- The user requires optimizations to be numerics-preserving (same-seed bit-identical checkpoints); reduction-reordering changes (multi-block var/mean, parallel scans) were reverted for this reason. Validate with: same seed twice → compare `md5sum checkpoints/<env>/<run>/<step>.bin`.
- Drone (and continuous-action envs generally) are train-bound, not rollout-bound: `sum_rows_to_precision_kernel` (logstd grad, ran with C=4 threads serially over 16k rows, 175 µs/call) was ~10% of wall. Fixed 2026-07-02 with block-cooperative smem staging keeping per-column serial add order (bit-exact, 175→91 µs, drone 5.5→6.6M SPS, +20%). Remaining drone costs are launch-bound tiny kernels (cuBLAS splitK storm, per-step casts at 256-agent batches). `index_copy` vectorization (~5% on drone) is value-safe but changes which duplicate prio index wins its write race, so same-seed hashes may diverge.
- Muon NS: a custom fused SIMT kernel was tried and REJECTED by measurement — slower than cuBLAS (595 vs 400 µs/step, FMA-dependency-chain-bound scalar GEMMs) and ~1.3% RMS numeric shift. Shipped instead: per-param parallel streams in muon_step (identical cuBLAS calls, fork/join events, per-param 16B-aligned scratch, per-stream handles with the SAME 32MB workspace — cuBLAS picks algorithms by workspace size and pointer alignment, both must match for bit-exactness). Drone 6.6→7.0M, breakout 11.9→12.1M, hashes identical.
- Cumulative 2026-07-02 (all bit-exact, hash-verified): breakout 11.0→12.1M SPS (+10%), drone 5.5→7.0M (+27%).
- `profile.sh` forces `--vec.num-buffers 1`, which serializes env CPU / PCIe / GPU and understates real overlap (default is 2; 4 is slightly faster still).
- nsys memcpy rows (`CUPTI_ACTIVITY_KIND_MEMCPY`) matter as much as the kernel summary here; kernel-only stats missed the biggest cost.
- Remaining known GPU-time items after the 2026-07 fixes: cuBLAS `Kernel2` tiny GEMMs (~27%, launch-overhead-bound, ~23k of them are Muon Newton-Schulz iterations — a fused small-matrix NS kernel is the next candidate), and the mingru scan kernels which are already near memory-roofline (~800 GB/s effective).
- Repo tests `test_api.py`/`test_muon.py` fail at collection on this branch (missing `pufferlib.emulation`, `heavyball`) — pre-existing, not signal.
