# Inference contention experiments — original 512 environments

2026-10-10. All three requested investigations are complete. Experiments are isolated in this directory; no production code, default, commit, or PR changed. The older goal remains paused.

## Decision

Keep high-priority independent inference and both entity fusions. No scheduling change promoted.
The batching microbenchmark has real efficiency gains, but the tested ready-request dispatcher loses end-to-end throughput and changes BF16 outputs. It is not a behavior-preserving keeper. This rejects this implementation, not every possible dynamic-batching scheduler.

## Workload and measurement

512 independent mature score-policy environments, horizon 512, four rollout buffers, 32 CPU workers, 15.55M parameters, batch 262,144, minibatch 4,096, 113 PPO updates per iteration. Existing CPU optimizations, cuBLAS workspaces, four Muon lanes, and both selected entity fusions are enabled. RTX 4090 / i9-14900K. Runs execute full inference, PPO backward, and optimizer compute, with a frozen actor and scratch updates; recorded actions keep the environment workload identical. These are throughput experiments, not learning-quality trials.

Full runs use 64 epochs, warm through 23, measure 24–62. No simultaneous GPU experiments. Priority is ABBA; broker is independent / merged / single-request / merged / independent. Profiles are excluded from SPS comparisons. Commands, environments, binary/checkpoint hashes, and raw logs are in ../runs/overlap512_*/.

## 1. Inference priority

| Setting | Mean SPS | Iteration ms | Exposed rollout wait ms | PPO finishes last by ms |
|---|---:|---:|---:|---:|
| High priority | 228,613 | 1143.5 | 0.0 | 155.4 |
| Normal priority | 211,891 | 1233.9 | 120.6 | 0.0 |

Normal priority changes SPS by -7.31%. PPO itself finishes sooner (approximately 1113.3 versus 1143.5 ms), but delayed rollouts more than erase that gain. Keep high priority.

## 2. Where contention occurs

One mature concurrent iteration was captured at each priority; isolated PPO and inference were captured separately. Kernel comparisons match name and launch dimensions. Isolated PPO uses the last, warmed 113-update pass.

| Kernel group | High-priority concurrent / isolated duration | Normal-priority concurrent / isolated duration |
|---|---:|---:|
| forward_loss_backward | 1.126× | 1.084× |
| optimizer | 1.138× | 1.064× |
| inference | 2.476× | 2.072× |

High-priority inference graphs span 546 us on average, with only 16 us waiting after the launch API and preceding upload complete. Normal priority spans 887 us with 56 us initial wait. Inference kernel sums per graph are about 498 us high / 420 us normal. Normal priority therefore introduces much more waiting *between* inference kernels, despite less slowdown while they run.

The PPO cost is spread across matrix multiplies, recurrent scans, and optimizer work. For example, selected large PPO GEMM groups slow around 12–18%, recurrent forward/backward scans around 15–17%. Small inference GEMMs and entity kernels often slow 2–4×. Kernel sums are concurrent durations, not additive wall time. This establishes execution interference, but does not separately identify bandwidth, cache, and SM occupancy as the cause.

Only 41/2,048 high-priority graph starts have another request ready but not yet started under the existing schedule. A new broker changes this schedule, so that count cannot predict its eventual batching rate.

## 3. Ready-request batching

First, isolated forward passes on the same saved batch:

| Agents per inference | Time ms | Saving versus separate B128 passes |
|---|---:|---:|
| 128 | 0.168 | 0.0% |
| 256 | 0.219 | 34.9% |
| 512 | 0.293 | 56.5% |

Prototype: four independent collectors upload their own next observations, publish completed uploads, then a dedicated high-priority dispatcher immediately takes the currently pending requests. No fill timer or all-buffer barrier. Recurrent states and observations are gathered, one policy forward executes, states/outputs are scattered, and each buffer uses its own RNG, masks, sampling and rollout index. B128 fallback uses the original forward. The single-request control uses the dispatcher but forbids merging.

| Full pipeline | Mean SPS | Change | Iteration ms | Exposed rollout wait ms |
|---|---:|---:|---:|---:|
| Independent inference | 228,476 | +0.00% | 1144.3 | 0.0 |
| Dispatcher, no merging | 217,488 | -4.81% | 1201.5 | 56.1 |
| Dispatcher, ready batches | 222,981 | -2.41% | 1172.2 | 33.6 |

Batch-count distributions and individual repeats are in SUMMARY.json and BROKER.csv. Batching reduces forward work, but the dispatcher also serializes inference service, adds packing/transfers and synchronization, and postpones CPU stepping for waiting buffers. The overall timing measures these together. We did not attribute a precise fraction to each overhead.

## Correctness and scope

All 64 observation hashes agree across all priority and broker full runs, with equal parameter counts, update counts, and unchanged frozen checkpoint bytes. This verifies equal replay workload, not equal sampled actions or learned trajectories. All 19 protected production/reference files are unchanged.

Changing B128 to B256/B512 changes BF16 outputs on shared inputs. BATCH_NUMERICS.json records the differences. No learning-quality test or claim of exact numerical equivalence is made for batching. Since performance failed the gate, no long training validation was run. Original retained kernels and production defaults remain unchanged.

Node tracing adds overhead. Kernel sums cannot be added as wall time; isolated and concurrent samples match model and shapes but not every state or scheduling condition. The earlier unprofiled isolated-versus-overlap measurement (~997 vs ~1,147 ms PPO) remains the appropriate estimate of the total overlap penalty (~15%), not the much larger inference-only slowdown.

## Artifacts

PLAN.json; PRIORITY.json/results + PRIORITY.csv; PROFILES.json/results; ANALYSIS.json + KERNELS.csv; BATCH_SCREEN.json/results; BATCH_NUMERICS.json; BROKER_SMOKE.json/results; BROKER.json/results + BROKER.csv; SUMMARY.json; INTEGRITY.json. Prototype in source/src/ready_batch.cuh with integration in source/src/pufferl.cu; immutable binary in binaries/ready_batch_v1, source hashes in ready_batch_v1-build.json.
