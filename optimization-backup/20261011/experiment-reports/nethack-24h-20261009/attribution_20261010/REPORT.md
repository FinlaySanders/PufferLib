# What limits the current NetHack overlap?

Measured 2026-10-10T07:30:33.042112+00:00 on the local RTX 4090 / i9-14900K. **The mature workload is primarily constrained by the CPU environment simulation and worker pool. GPU contention is measurable, but accelerating PPO alone cannot reach 1B steps/hour.**

## Controlled measurements

All full runs: existing 15.55M score actor, 2048 environments, 4 buffers, horizon 128, batch 262,144, minibatch 4,096, 113 PPO updates per batch. Same retained engine and GPU flags. Actor frozen, optimizer writes to scratch. Identical recorded actions; 64 full warmup epochs followed by 15 timed mature epochs. The 2048 environments repeat 512 unique recorded streams four times, as in the established benchmark. No production defaults changed.

Diagnostic bypasses start only at epoch 64. Without inference, PPO is also disabled; stale recurrent/model tensors are therefore never trained on. Environment stepping and host/device copies remain. **The bypass rows measure collection capacity, not training throughput.**

| Work performed | CPU workers | SPS | Repeats |
|---|---:|---:|---:|
| Full training |32|210,279|2|
| Full training |24|202,260|1|
| Full training |16|183,495|1|
| Rollout inference + environment; PPO disabled |32|220,420|2|
| Environment + transfers; PPO and inference disabled |32|222,094|2|

The two full controls were 209,783 and 210,776 SPS (+0.473% drift). The PPO-free repeats were 220,044 and 220,795 SPS; engine-plus-transfer repeats 221,833 and 222,355 SPS.

## Control for main-thread spinning

Disabling PPO makes the main thread spin for the whole collection interval, consuming ~0.96 logical CPU instead of ~0.20 during normal full training. Repeat all three 32-worker modes using the existing condition-variable main wait:

| Work performed, main thread sleeps while waiting | SPS | Repeats |
|---|---:|---:|
|Full training|210,846|1|
|PPO disabled|224,876|1|
|PPO and inference disabled|225,967|1|

With this control, removing PPO changes throughput by +6.65%; removing both PPO and inference changes it by +7.17%. Sleeping alone changes full throughput by only +0.27% versus the repeated controls; this is not established as a new optimization. These follow-up arms have one repetition each. GPU SM clocks also fall from ~2700–2715 to ~2520 MHz when PPO is removed, so the bypass differences include DVFS effects; no global clocks were altered.

## Where the final wait is spent

Two graph-level Nsight epochs on the full stack. PPO GPU graph spans were 1.073 s each. The last collector finished about 216 ms later. Partitioning that collector's remaining CPU wall-time ranges:

| Phase | Mean ms | Share of final tail |
|---|---:|---:|
|Environment stepping and worker-pool waits|180.38|83.5%|
|Waiting for inference/stream completion|29.61|13.7%|
|Submitting GPU work|3.96|1.8%|
|Submitting observation uploads|1.76|0.8%|

The environment range is 82–85% of the exposed tail in these two epochs. This is **not** an assertion that 82–85% of all training computation is CPU work. Worker-pool tail waits are nested within that range: ~48–58 ms waiting for other workers on the final collector. They can reflect long game steps, scheduling, or contention; they do not prove the scheduler itself is defective.

Inference GPU graph span averages 0.877 ms while PPO runs, versus 0.370 ms outside it. Thus GPU contention remains real. These phase groups are observational; the no-PPO arms provide the complementary controlled intervention. The full control's unprofiled final wait averages ~161 ms, smaller than the profiled ~216 ms. Use the trace for attribution, unprofiled runs for throughput. The profile launcher's 78.8k SPS additionally includes profiler-stop overhead in the clock interval and is explicitly excluded.

CPU process accounting observes ~31 of 32 logical CPUs used in full 32-worker training and the bypass cases. This includes spinning and CPU-side GPU submission, so it is not 31 cores of pure NetHack work. At 24 workers it falls to ~27.6 logical CPUs, at 16 workers ~19.8. GPU utilization samples are coarse 1 Hz measurements, not a wall-time decomposition.

## GPU-only training and target

Five isolated trials on the saved mature batch execute all 113 PPO updates: mean **970.95 ms**, equivalent to **269,986 environment steps/s** if collection/inference were free. This is a representative-batch diagnostic, not end-to-end throughput.

The 1B/hour target allows **943.72 ms per 262,144-step batch**. The current best engine-plus-transfer diagnostic above is 225,967 SPS, requiring about 22.9% more throughput to reach that target even before accounting for policy work. That is a limit of the current implementation/schedule under this test, not a hardware ceiling. GPU training alone also needs roughly 2.9% higher throughput to fit the target budget, with additional margin needed for inference/overlap.

## Decision

Prioritize CPU environment work and the worker-pool critical path. More GPU fusion alone has limited near-term value on this mature workload. The overlap already hides most PPO cost; the remaining CPU workload must become faster. Retain GPU contention as the next constraint rather than calling the system exclusively CPU-bound.

This study does not identify a particular cache miss, memory-layout defect, or scheduler bug. Those need separate engine/pool experiments. No performance winner was promoted and no production code was edited.

## Reproducibility and correctness

All 11 full/bypass runs match every one of the 80 reference observation hashes and retain the exact frozen actor checkpoint hash. Full runs execute 113 updates; diagnostic no-training modes execute 0 despite the legacy BATCH_PERF field still printing configured 113. This checks identical environment workloads, not equivalence of live learning under GPU rounding changes.

- Commands, binary/engine/checkpoint hashes and logs: `../runs/attribution_*/command.json`, `run.log`, `result.json`.
- Immutable diagnostic binary: `../binaries/attribution_v37`, SHA256 `1aaf25f9a6b9fc0512c2902e917036561768f7c86b79ca20cde35a1cc5f695bb`.
- Instrumentation patch: `DIAGNOSTIC.patch`; original source backup: `pufferl.before.cu`; immutable snapshot: `../snapshots/attribution_v37/`.
- Campaign specifications: `../ATTRIBUTION.json`, `../ATTRIBUTION_SLEEP.json`, `../ATTRIBUTION_GPU.json`. Labels must be made unique before rerunning; runner refuses to overwrite existing runs.
- Raw tables: `ATTRIBUTION.csv`, `ATTRIBUTION_SLEEP.csv`; structured timing/proof summaries: `ATTRIBUTION_SUMMARY.json`, `ATTRIBUTION_SLEEP_SUMMARY.json`.
- Profile: `../runs/attribution_graph_20261010/timeline.nsys-rep` and `timeline.sqlite`; analysis: `TRACE.json`, `analyze_trace.py`.
- CPU/GPU observations: `cpu_samples.jsonl`, `UTILIZATION.json` and each run's `gpu.csv`.
- Protected production/historical file integrity: `INTEGRITY.json`.

The experimental working source was restored to its pre-diagnostic v36 state after the tests. Diagnostic v37 source/binary and the patch remain saved for reproduction.
