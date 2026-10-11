# Method: current NetHack full-pipeline profile

## Question and baseline

Measure why training throughput changes with policy maturity, whether rollouts remain hidden by PPO, which saved optimizations help on the current stack, and how a smaller model shifts the limit. All timings are new local measurements, not products of historical speedup percentages.

The live baseline is PufferLib commit `3719caaaf945025e4e1e59c6556560d2ba9e3d1c`. The current stream-owned 4 MiB cuBLAS workspaces and default math mode are common to both sides. The saved trainer changes were integrated in an isolated copy and compiled with feature flags; the baseline disables them. See integration-and-instrumentation.patch and the baseline audit files. No live source, experiment queue or default configuration was modified.

Hardware: RTX 4090, i9-14900K (24 physical cores / 32 logical CPUs). One GPU workload runs at a time. Compilation is separated from throughput runs. Current requests 32 OpenMP threads split among four buffers; the candidate shared pool has 24 workers plus four coordinators. This compares the saved package settings, not a thread-count-only controlled experiment.

## Fixed policies, complete training compute

Every batch runs inference, recurrent PPO forward/backward, GAE, loss, clipping, Muon, weight updates and casts. Optimizer writes are redirected to shadow weights so actor and learner parameters remain fixed. Optimizer state starts fresh; this is a computational workload, not a resumed-learning experiment. Loaded and final actual policy hashes must match. Gradients and shadow parameters are not used to change gameplay.

Common settings: 512 environments, four buffers, horizon 512, minibatch 4096, replay ratio 1.78021395 (113 minibatch updates per batch), async rollouts, CUDA graphs, seed 901, fixed verb epsilon zero and zero-time masking disabled. Normal exploration annealing is disabled for comparability. No evaluation jobs or intermediate checkpoint saves are timed.

Workloads:

- Early: random frozen 15,552,136-parameter policy (1024 wide, four recurrent layers).
- Mature score: article 4B s705, identical architecture.
- Depth: compatible 2B s906 policy, 4,311,176 parameters (512 wide, three layers), RUN and SEARCH20 masked. Its absolute speed is not a like-for-like model-size comparison with the score policy.
- Small: random frozen ~5.10M policy with the mature score policy's recorded environment actions. Inference and full training compute still run. This holds game workload fixed, not policy quality; the resulting learning inputs are deliberately off-policy and updates are discarded.
- Recent research: exact auxiliary-Q campaign source with profiling-only instrumentation, using its own random policy or control_s4101 1B checkpoint. `NH_Q_MODE=0` still fits/logs the auxiliary critic; compare against the variable being absent.

## Timing and profiling

Unprofiled endpoints run 64 batches (16,777,216 decisions), with two repeats per build. Measure epochs 24–62 inclusive to exclude startup, early episode population transients and the last batch without rollout prefetch. SPS is decisions divided by wall-clock differences at consecutive safe batch barriers, including ordinary bookkeeping. Internal timing, boundary hashes and game-age counters are enabled consistently on both sides.

Early/mature safe comparisons reused the two completed current repeats after correctness investigations interrupted the original ABBA plan; depth, size and auxiliary comparisons use ABBA ordering. Exact commands and timestamps are saved. Ranges describe repeated measurements, not confidence intervals over seeds.

Rollout tail is elapsed time after PPO finishes until all rollouts are ready. It includes CPU game work, scheduling, inference and transfers. A positive tail proves rollouts are not completely hidden; it does not by itself isolate engine time.

Nsight profiles run separately from headline measurements. Graph captures cover interior epochs 24–31; node captures cover 24–27. Graph envelopes include internal scheduling gaps. Node traces expose individual kernels but add more overhead. Joint timelines measure interval unions rather than adding overlapping CPU/GPU work. Activity percentages are not SM occupancy. Training-stream timestamps separate forward, GAE/loss, backward and optimizer intervals while inference is concurrent. Summed kernel durations are reported separately and are not additive wall time.

CPU hardware and software perf counters are unavailable in this container. CPU conclusions use coordinator/worker NVTX ranges, resource accounting and GPU timelines; there is no claim of a CPU instruction-level profile. GPU utilization/power/clock samples are aligned to measured batch wall-clock timestamps.

## Correctness gates and exclusions

The saved out-of-place Muon/cuBLASLt variant fails exact update matching with the current cuBLAS implementation. Removing only its flag restores identical master weights, momentum and final update buffers after 1,808 minibatch updates, with matching observations. It is excluded. The original saved variant used different cuBLAS workspace/math settings; historical results do not establish correctness after porting.

The later engine44 and engine61 snapshots diverge reproducibly at the epoch-16 observation boundary in the mature test. Engine-only/GPU-only isolation locates the difference in the engine snapshots. The exact offending change is not identified in this performance study. Their provisional timings remain in raw artifacts but are excluded from headline summaries.

The earlier engine14 (candidate14-lto-local; SHA256 `70fe544048cd5f9e159d98be3222f35536e508299228e88f61a3c10c968bc403`) passes the 64-boundary mature comparison and is used for the retained package. Safe endpoint/component and replay comparisons additionally check their batch-boundary observation hashes. Boundary matching is not exhaustive every-action/seed equivalence; archived engine tests supply earlier golden/replay evidence.

The retained trainer flags are shared pool83, head-parallel sampling, batched Muon norms, MinGRU copy removal, unused-head log-probability skipping, coalesced PPO zeroing, byte observations and rollout graph reuse. Exact flag sets are in *-build.json. Policy, engine and executable hashes accompany each run.

## Artifacts

REPORT.md gives the interpretation; throughput.csv includes all measurements, including diagnostics, and summary.json identifies safe headline comparisons. Each runs/<label> contains command.json, result.json, run.log, aligned gpu.csv, policy proofs, and (where applicable) Nsight/SQLite traces and analysis.json. FINAL_VALIDATION.json records final comparisons. Failed candidates and MISMATCH.md are retained explicitly.
