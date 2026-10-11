# NetHack gradient pipelining — 9 October 2026

## Follow-up: regression isolated

The default-setting regression below is explained by CUDA compute-work-queue serialization. Setting `CUDA_DEVICE_MAX_CONNECTIONS=32` removes the rollout stalls and makes the same prototype **+1.35% faster end to end** (184,782 → 187,268 SPS). A compute-versus-copy control isolates compute connections; numerical proofs remain exact. See [the diagnosis](diagnosis/REPORT.md). Production remains unchanged.

The combined candidate changes frozen full-pipeline throughput by **-4.02%**: 184,903 → 177,473 policy steps/second. The standalone GPU-graph result is a screening measurement; the full-pipeline result includes concurrent rollout inference and CPU simulation.

## Change

Queue three custom NetHack decoder weight-gradient GEMMs and sixteen encoder weight-gradient GEMMs on the existing recurrent dW stream. Input-gradient backpropagation continues on the main training stream. Preserve the existing final join before global clipping and Muon. Four products with immediate in-place source overwrites remain serial. No optimizer formula, precision, architecture, reward, hyperparameter or engine change.

The per-stream cuBLAS workspace fix and all validated GPU flags are common to both sides. The source-only candidate diff is `gradient_pipeline.patch`; `source/` also contains optional benchmark instrumentation. All changes remain isolated and production files are unchanged.

## Exactness

All three candidate modes pass a genuine saved mature minibatch sequence of 113 optimizer updates. First and last pre-optimizer raw gradients, final master weights, BF16 weights, momentum and update buffers match byte-for-byte. All checked outputs are finite.

A separate 16-batch updating test compares baseline with the combined candidate over 1,808 optimizer updates: final checkpoints, master weights, momentum, update buffers and all environment-batch observation proofs match exactly. Recorded environment actions stay fixed; this checks implementation equivalence, not on-policy learning. This is bounded test evidence, not a proof for every shape, policy or GPU.

## Fast GPU screen

A one-time 95-second capture saved a full rollout batch at epoch64: mean game age 27,087 turns; 1,552/2,048 games over 10,000 turns. The 2,048 streams are four copies of 512 original recorded streams. The snapshot includes the trainer buffers for observations, actions, log-probabilities, masks, rewards, values, terminals, recurrent states, parameters and optimizer momentum. The simulator workload follows the recorded action corpus; the saved batch is a compute workload, not an on-policy learning dataset.

Each process captures the complete PPO graph, performs two warmups and ten timed replays. Saved parameters and optimizer state are restored outside each timed graph. Weights remain frozen for timing, but forward/loss/backward/optimizer computation executes. End timestamp follows the side-stream join and optimizer. No simultaneous inference or environment work in this screen. Mode order: 0/1/2/3/3/2/1/0.

| Variant | Process means (ms) | Throughput gain |
|---|---:|---:|
| Baseline | 1,290.90 / 1,295.08 | +0.00% |
| Decoder only | 1,290.84 / 1,293.49 | +0.06% |
| Encoder only | 1,279.81 / 1,282.17 | +0.94% |
| Decoder + encoder | 1,276.63 / 1,276.77 | +1.28% |

Each timing process took approximately 18 seconds, including loading and graph setup. Each updating correctness process took approximately four seconds. Per-graph trials are repeated timing observations, not independent learning runs or confidence intervals.

## Full pipeline

Standard four-buffer async scheduling, 2,048 environments, horizon128, 4,096 minibatch, 113 updates per rollout batch, 24 shared workers plus four submitters, one RTX 4090. Fixed 15,552,136-parameter 4B score policy. Latest validated movement engine common to both sides. Full inference, PPO, backward and optimizer work; optimizer application redirected to scratch. Each fresh process runs 96 batches, timing epochs64–94. No concurrent build, profiling or other GPU workload.

| Process | SPS |
|---|---:|
| baseline_a | 185,048 |
| candidate_a | 178,427 |
| candidate_b | 176,518 |
| baseline_b | 184,758 |

Mean gain: **-4.02%**; baseline bracket drift: **-0.16%**.
All 96 observation-batch proofs agree across all four timing processes; the policy checkpoint stays unchanged. These are compute-throughput tests, not resumed learning or a score certificate.

| Process | Mean rollout tail (ms) | Batches with >10ms rollout tail | Median batch time (ms) |
|---|---:|---:|---:|
| baseline_a | 0.00 | 0/31 | 1414.00 |
| candidate_a | 73.64 | 9/31 | 1398.05 |
| candidate_b | 91.14 | 11/31 | 1398.30 |
| baseline_b | 0.00 | 0/31 | 1415.71 |

Rollout tail includes simulation, inference and scheduling; it is not exclusively CPU engine time. Increased tail under gradient overlap is evidence of a full-pipeline interaction, but this experiment does not isolate a GPU resource, scheduling or CPU cause. All tail batches remain included in headline throughput.

## Interpretation

The standalone graph improvement does not establish a useful full-pipeline win in this screen. Keep the prototype and fast benchmark for reference; do not promote it as a validated training speedup.

The first implementation does not pipeline the four buffer-aliasing products, run encoder branches on independent streams, or overlap Muon with the next forward pass. Earlier serial/deferred recurrent-gradient experiments tested a different scheduling change.

## Artifacts

`PLAN.md`, `selected_products.json`, `gradient_pipeline.patch`, `mature_batch.bin`, `SCREEN.json`, `FULL.json`, `gpu_trials.csv`, `runs/*/command.json`, GPU clock/power CSVs and raw logs. `prepare.py`, `run.py`, `screen.py` and `confirm.py` reproduce the experiment. The benchmark and candidate edits exist only under this experiment directory.
