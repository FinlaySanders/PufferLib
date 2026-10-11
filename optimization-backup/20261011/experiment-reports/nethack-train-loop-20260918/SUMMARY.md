# Two-hour NetHack training optimization report

18 September 2026, 10:19–12:19 UTC. Baseline already includes engine61, environment pool83, the cuBLAS workspace fix, strict reductions and the head sampler. These are incremental gains over that baseline, not over upstream PufferLib. Production sources are unchanged.

## Main result: 9.7% more training throughput

| Workload | Baseline SPS | Retained SPS | Gain |
|---|---:|---:|---:|
| Mature recorded workload, three short repeats | 170,747 | 187,261 | 9.7% |
| Mature games, live actions after saved prefix | 170,930 | 185,945 | 8.8% |
| Early live training, 15.55M parameters | 175,051 | 190,659 | 8.9% |
| Early live training, 1.98M parameters | 348,802 | 390,413 | 11.9% |
| Mature recorded workload, 1.98M parameters (short repeats) | 241,006 | 245,682 | 1.9% |

GPU allocation in matched normal-update tests falls from 15,597 MiB (15.2 GiB) to 8,095 MiB (7.9 GiB), a 48.1% reduction. Frozen tests have an additional scratch allocation; compare like with like.

## Retained implementation changes

1. Batch independent per-matrix Muon normalization kernels while preserving each reduction tree and rounding.
2. Use separate C/D outputs in cuBLASLt for accumulating Newton–Schulz GEMMs, eliminating preliminary copies.
3. Remove redundant MinGRU state/input copies; preserve input lifetime through backward completion.
4. Skip unused action-head log-probability work and coalesce unused gradient zeroing. The PPO objective is unchanged.
5. Store raw byte observations without expanding the rollout buffers to BF16. The encoder reads the same byte values; learned activations remain BF16.
6. Reuse eight rollout graphs with one-step staging instead of capturing one per buffer, time step and async slot. This primarily saves memory.

## Correctness evidence

- Normal mature replay: all 15,552,136 FP32 master weights, FP32 optimizer momentum and BF16 updates are byte-identical after 1,808 updates.
- Live early training: the same checks pass at 15.55M and 1.98M parameters; observation hashes agree.
- Mature live actions: observation hashes agree after switching off action replay following the saved prefix.
- Main tests enable recurrent carry (`reset_every_horizon=0`); a separate live-updating reset-at-horizon pair also has identical checkpoints and observation hashes.
- Standalone normalization oracle covers five input patterns over 4,588,861 elements each. Byte-storage transpose oracle covers all 65,536 bit patterns.
- Synchronous training and reset-at-horizon are additional checkpoint/trajectory checks. These are finite deterministic checks, not a proof for every architecture, precision, CUDA version or GPU. Retained cuBLASLt plans and byte containers target the tested BF16 NetHack configuration.

## Benchmark protocol and limits

One RTX4090, 512 environments, four rollout buffers, 24 environment-pool workers, horizon512, minibatch4096, replay ratio1.78021395 (113 updates/batch), four recurrent layers, hidden width1024. Six steady-state batches (epochs8–13) are timed in each 16-batch run. SPS counts policy/environment decisions, not NetHack keystrokes.

The mature workload is initialized by replaying 12,288 decisions per environment. It represents established score-farming games, not a deep Castle-policy corpus. The main controlled replay benchmark continues recorded environment actions while executing real inference, sampling, forward, loss, backward and optimizer work. It is a compute benchmark, not a valid learning-quality evaluation. Frozen mode redirects parameter writes to scratch while preserving the mature policy. The supplementary mature-live test stops replay after the prefix; the policy then chooses its own actions, with zero initial recurrent memory and eight warmup batches before timing. Early live tests really update the policy. The small model is randomly initialized, not a trained mature small-policy checkpoint.

## Remaining bottleneck

Measured GPU training-stream intervals per batch (concurrent rollout interference is included; these are not exclusive GPU utilization shares):

| Stage | Baseline ms | Retained ms |
|---|---:|---:|
| Forward and importance-cache work | 303.8 | 261.2 |
| Advantages and PPO loss | 41.8 | 12.5 |
| Backward | 493.8 | 495.0 |
| Muon optimizer and final cast | 690.3 | 623.5 |

Backward computation and optimizer matrix work dominate the remaining training-stream time. The smaller model is much more sensitive to mature rollout cost; its short-run SPS varies by several percent, so no mature-workload speedup is established for it. Smaller local kernel timings did not reliably improve end-to-end throughput, so the acceptance criterion was full-pipeline SPS.

Nsight node tracing worked for the baseline but repeatedly stalled while finalizing optimized traces. Verified profiler PIDs were stopped; no training job was mistaken for a successful trace. The final stage timings use working GPU globaltimer instrumentation instead.

## Rejected or parked ideas

Fused optimizer cast; direct bias atomics; stream priorities; cached embedding tables; fused entity pooling; sampled timing events; batched host uploads; sampler shared-memory caching; parallel Muon streams; compact normalization grids; identity-row indexing; grouped entity GEMMs; alternative scan load geometry and shared mask packing; fused final Muon writes; repeated-message reuse; WMMA entity MLPs; serialized/deferred backward GEMMs; shared bias reductions. They were flat or slower in full training. SM-target tuning also changed checkpoint bits. Alternate cuBLASLt heuristic ranks reached up to ~193k SPS but changed checkpoint bits and were not accepted. See RESULTS.md for individual screens and prepare_*.py for prototypes.

## Artifacts

- `minimal/` and `optimizations-only.patch`: stripped implementation, rebuilt and checked against the baseline checkpoint. `build_minimal.sh` rebuilds it. `retained/` adds validation instrumentation.
- `optimizations-only.patch`: implementation changes relative to the existing batch-sweep benchmark source. `retained.patch` also includes optional validation instrumentation; not a drop-in upstream PR. `build_retained.sh` rebuilds it and `reproduce.sh TAG` runs the controls and update proof on this box.
- `best.json`, `final-state-proof.json`, `final-phases.json`: machine-readable result and correctness evidence.
- `RESULTS.md`, `results.json`: all screens, including rejected ones.
- Each case directory contains exact command/environment, full log and checkpoint. The rollout-tail diagnostic assumes async mode and is not valid in the two synchronous correctness cases.
