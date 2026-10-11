# Why gradient pipelining slowed the full pipeline

## Finding

The regression is caused by **CUDA compute-work-queue serialization delaying independent rollout work**. Raising the compute-connection limit removes the long delays; increasing copy connections alone does not. The extra gradient overlap itself gives a small positive full-pipeline gain when this queue issue is removed.

This corrects the earlier provisional explanation of generic GPU resource contention. The expensive part was waiting to dispatch ready work, not executing that work.

## Mechanism

The prototype moves 19 NetHack encoder/decoder weight-gradient products onto the existing dW side stream, changing the captured training graph's branching and scheduling. The final join before gradient clipping and Muon is unchanged. Rollout inference and the kernel that records its output remain independent of those weight gradients.

CUDA streams are logical ordering constructs, not private hardware queues. Different streams and internal graph execution streams can share finite device work queues. A queued training workload can therefore impose a false dependency on otherwise independent rollout work. NVIDIA documents both [false dependencies from shared work queues](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/environment-variables.html) and [internal stream expansion during CUDA graph replay](https://docs.nvidia.com/dl-cuda-graph/troubleshooting/performance-issues.html#too-many-cuda-streams-channel-serialization).

Each collector calls cudaStreamSynchronize before stepping its CPU environments. Delaying inference or its post-inference recording kernel stalls that collector. The trainer eventually waits for every collector, exposing a rollout tail larger than the approximately 16 ms saved in the training graph. Standalone GPU timing does not include those competing collectors, explaining its positive result.

The traces do not expose hardware queue IDs or the driver's precise internal graph-to-queue assignment. The compute-connection control, ready-work timestamps and absence of long execution spans establish the queue-induced serialization mechanism; no particular undocumented queue-assignment algorithm is claimed.

## Direct timeline evidence

The mature default-setting trace contains 4,096 inference calls over eight batches:

- Stream18: CPU submits inference at 45.738 ms and returns at 45.780 ms. Its preceding upload completes at 46.107 ms. The inference graph starts only at 466.740 ms and completes at 467.549 ms: **420.634 ms after its inputs are ready, then 0.808 ms executing**. Other collector streams execute while it is pending.
- Another collector's inference finishes at 9,872.108 ms, but its independent record_step kernel does not start until 10,234.951 ms: **362.843 ms waiting, then 8.768 microseconds executing**.
- CPU environment steps in that trace top out at 15.1 ms; inference graph execution tops out at 6.16 ms. Neither explains the hundreds-of-milliseconds pauses.
- With 32 connections, the worst inference queue delay falls to **2.950 ms**, and the worst post-inference recording-kernel gap to **1.348 ms**. Inference execution stays similar (mean 1.243 vs 1.263 ms).
- Training graph host submission remains about 133 ms in both traces, so eliminating host submission overhead is not what fixed the stalls.

Exact timestamps, stream IDs and correlation IDs are in `evidence.json`; the SQLite and Nsight reports retain the underlying events.

## Compute versus copy control

Because CUDA_DEVICE_MAX_CONNECTIONS changes both kinds unless overridden, a second pair isolates compute from copy connections. Both use the same pipelined binary, checkpoint, engine and workload, profiling epochs8–13 (3,072 inference calls each):

| Compute connections | Copy connections | Worst inference queue wait | Inference waits >30 ms |
|---|---|---:|---:|
| 32 | 8 | 2.945 ms | 0 |
| 8 | 32 | 810.028 ms | 6 |

Increasing copy connections alone fails; increasing compute connections while keeping copy connections at8 succeeds. This isolates the compute-work-queue setting. These short diagnostic traces are not used as mature throughput measurements.

## Full-pipeline throughput, without profiling

RTX4090, driver595.71.05, CUDA13.0.2. Same 15,552,136-parameter score checkpoint, recorded actions, latest validated engine, 2,048 environments, four buffers, 24 shared CPU workers, horizon128, minibatch4096 and113 optimizer updates per batch. Full forward/backward/optimizer computation with frozen actor weights and optimizer writes to scratch. These are compute benchmarks, not learning experiments.

Each process runs96 batches. The common measured window is epochs64–93 (30 batches). No simultaneous GPU workload, compilation or Nsight profiling.

| Setting | SPS | Mean exposed rollout wait | Batches with >10 ms tail |
|---|---:|---:|---:|
| Pipeline, default connections | 176,257 | 97.1 ms | 9/30 |
| Baseline, 32 connections | 184,782 | 0 ms | 0/30 |
| Pipeline, 32 connections, first | 187,350 | 0 ms | 0/30 |
| Pipeline, 32 connections, repeat | 187,187 | 0 ms | 0/30 |

With the same connection setting, pipelining averages **187,268 SPS**, a **+1.35%** improvement over baseline. The prior default-setting baseline was approximately185k SPS, so raising the limit mainly rescues the pipelined schedule rather than generally accelerating the baseline.

The diagnostic launch setting is `CUDA_DEVICE_MAX_CONNECTIONS=32`, set before CUDA initialization. All of these tests are isolated; no production source or global environment setting was changed.

## Correctness and limits

- All96 observation-batch hashes in every unprofiled process match the original baseline, and frozen checkpoint hashes are unchanged.
- Profiled shorter processes match every comparable observation batch. Their last batch intentionally has no next-rollout prefetch, so it repeats the previous observation state and is excluded from comparison with a longer process's final epoch.
- At32 connections, first/last raw gradients and final BF16 parameters, master weights, optimizer momentum and update buffers match byte-for-byte between baseline and pipeline after113 real optimizer updates. They also match the original default-connection baseline proof.
- The prior1,808-update comparison remains evidence for the unchanged prototype under its original setting; the added32-connection update check is113 updates.
- Nsight changes scheduling enough to reduce the visible full-batch slowdown. Profiled throughput is therefore kept separate from the unprofiled result; traces diagnose the stalls and unprofiled repetitions quantify the net effect.
- This establishes the cause and remedy for the tested model, batch and GPU/driver. It does not establish a universal default for every environment or GPU.
- All protected production and earlier retained optimization files pass their saved hashes. The optional per-collector instrumentation under `diagnosis/source/` was prepared but not built or used. Every measured process uses the original `source/puffer_pipeline` binary.

## Artifacts

`RESULTS.json`, `results.csv`, `EXACT.json`, `evidence.json`, `run.py`, `confirm.py`, `controls.py`, `trace_summary.py`, per-run commands/logs/checkpoints, and `*/timeline.nsys-rep` / `*/timeline.sqlite`. The raw numerical proofs are in the parent experiment's `runs/queue32_proof_0` and `runs/queue32_proof_3`.
