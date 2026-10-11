# NetHack model-size full-pipeline profile

## Outcome

Reducing recurrent width improves full-pipeline throughput, but scaling from 15.55M to about 1M parameters does not yield a proportional speedup. At 1–2M the environment phase is much more exposed and throughput is close to a plateau. At 5M rollouts still finish after PPO; at 15.55M PPO finishes last and occupies nearly the full training cycle.

## Controlled comparison

Same mature 4B-policy action stream drives the live engine at all sizes. Networks still execute inference, PPO loss, backward and full optimizer work, with optimizer writes directed to scratch parameters. Four recurrent layers throughout; width changes only. NetHack modality encoders retain their internal dimensions. Smaller networks use frozen random parameters. This measures workload scaling, not their playing strength or valid on-policy learning. See `METHOD.md`.

Hardware/config: RTX 4090, retained engine61 and pool83, 24 workers plus 4 coordinators, 512 games, 4 buffers, horizon 512, minibatch 4096, replay ratio 1.78021395, asynchronous PPO and CUDA graphs. Every run performs 10,485,760 decisions. Every observation hash at batches 31, 37 and 39 matches the teacher, and all parameter files remain unchanged.

## Throughput

Mean batch durations from batches 24–30 with capture inactive, measured in two passes. Nsight is attached, but the capture range starts at batch 32. These are controlled replay timings, not a quality-matched training comparison or a claimed clean standalone benchmark.

| Parameters | Width | Steps/s | Relative to 15.55M | Batch seconds, two passes |
|---|---:|---:|---:|---|
| 1.11M | 64 | 240,360 | 1.41x | 1.100, 1.081 |
| 1.98M | 224 | 243,420 | 1.43x | 1.082, 1.072 |
| 5.10M | 512 | 231,837 | 1.36x | 1.130, 1.131 |
| 15.55M | 1024 | 170,334 | 1.00x | 1.540, 1.538 |

## Where time moves

Lower-overhead graph traces, same batches 32–37, trimmed by 250ms at each end. PPO graph envelopes include internal gaps. Environment fractions average each coordinator’s phase time; these columns overlap and must not be added.

| Parameters | PPO graph span (% wall) | GPU graph/copy idle (% wall) | Coordinator environment phase (%) | All four coordinators in environment while GPU idle (% wall) |
|---|---:|---:|---:|---:|
| 1.11M | 62.2 | 16.7 | 73.2 | 12.2 |
| 1.98M | 64.7 | 15.5 | 73.0 | 11.0 |
| 5.10M | 77.2 | 9.8 | 68.4 | 6.9 |
| 15.55M | 100.0 | 0.0 | 50.1 | 0.0 |

## Which side finishes last?

The following timing uses actual PPO GPU graph completion and the final stream synchronization of each rollout coordinator. It covers five complete batches (33–37). The remaining rollout time includes both inference and CPU simulation; it is not all engine time.

| Parameters | Batch duration (s) | Rollouts remaining after PPO (s) | PPO remaining after rollouts (s) |
|---|---:|---:|---:|
| 1.11M | 1.150 | 0.448 | 0.000 |
| 1.98M | 1.163 | 0.419 | 0.000 |
| 5.10M | 1.215 | 0.305 | 0.000 |
| 15.55M | 1.546 | 0.000 | 0.089 |

At 1–2M, roughly 36–39% of each traced batch remains after PPO has completed, waiting for rollouts. At 5M this is about 25%. Separately, all four coordinators are in the environment phase with no GPU graph/copy running for about 11–12% of wall time at 1–2M, and 7% at 5M. This directly shows CPU environment work on the critical path, rather than merely inferring it from local wait counters. The 15.55M run instead finishes rollouts before PPO.

## GPU kernel workload

Separate node-level captures provide individual kernel durations, with greater tracing overhead. Percentages below divide summed kernel time into work categories; concurrent kernels can overlap, so these are not additive wall-time costs. Optimizer includes Newton–Schulz matrix operations, clipping, updates and cast.

| Parameters | Inference | Training forward/loss/backward | Optimizer |
|---|---:|---:|---:|
| 1.11M | 46.9% | 38.4% | 14.6% |
| 1.98M | 45.8% | 39.3% | 15.0% |
| 5.10M | 45.2% | 38.7% | 16.1% |
| 15.55M | 44.7% | 32.3% | 22.9% |

## Interpretation and limits

The parameter count is 12 H² + 1,987 H + 934,536 with four layers. Shrinking recurrent width leaves about 0.935M width-independent parameters and their encoder work, plus the same observation processing, action-head structure, game simulation and training-update count. Parameter count is therefore not proportional to either GPU computation or total elapsed time.

Engine optimization matters more for smaller models. GPU neural-network and optimizer work are the more exposed targets for the 15.55M model. The measured balance is specific to this rollout/update ratio, hardware and mature score-policy workload; deeper depth-policy games can move the balance toward the engine again. The modest difference between the two smallest sizes should not be treated as a reliable architecture ranking.

Raw Nsight reports, SQLite exports, command manifests, logs and unchanged-weight/observation proofs are in each `h*-graph` and `h*-node` directory. `summary.json` contains the numeric results. Failed setup attempts are preserved separately and excluded. Production checkout was not modified.
