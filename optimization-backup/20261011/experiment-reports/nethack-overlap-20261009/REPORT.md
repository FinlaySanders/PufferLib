# Further pipelining experiments

All candidates were tested on top of four-stream Muon, gradient pipelining and 32 CUDA compute connections. Production files and previous experiment sources are unchanged. None of the candidates reached the predeclared 1% full-pipeline gain needed for confirmation. The 0.6% priority result is a small unconfirmed signal; retain the existing baseline for now.

## Full pipeline

| Candidate | SPS by process | Mean SPS | Change |
| --- | ---: | ---: | ---: |
| Current four-stream Muon baseline | 193,346, 193,098 | 193,222 | +0.00% |
| Higher inference priority | 194,397 | 194,397 | +0.61% |
| Asynchronous rollout archive | 193,351 | 193,351 | +0.07% |
| Next encoder / optimizer overlap | 190,572 | 190,572 | -1.37% |

Control drift in the initial bracket: -0.13%. The gate for further repetition was at least 1% improvement in the first full-pipeline screen; none crossed it. Single-process candidate measurements remain screening results.

Each full-pipeline process runs 80 batches and measures batches 64–78 (15 batches). Compare candidates to the fresh controls here: the previous Muon report used a longer 64–94 window. All processes advance through identical recorded-action observation sequences. Actor/model weights stay frozen during timing while all optimizer work executes into scratch weights. This measures compute throughput, not learning or score.

## GPU-only training graph

| Variant | Graph times, ms | Mean, ms | Throughput change |
| --- | ---: | ---: | ---: |
| Current four-stream Muon baseline | 1148.809, 1151.062 | 1149.935 | +0.00% |
| Next encoder / optimizer overlap | 1136.612, 1137.663 | 1137.138 | +1.13% |
| Same split update, fenced | 1150.036, 1150.585 | 1150.311 | -0.03% |

Two warmups and ten measured graphs per process; baseline, overlap, fenced, fenced, overlap, baseline order. Each saved-batch graph performs 113 PPO updates. The saved batch is restored between trials. The fenced control changes the update partition and placement while withholding the intended overlap.

## Exposed waits in the full pipeline

| Process | Mean rollout tail, ms | Mean PPO tail, ms | Largest rollout tail, ms | GPU allocation, MiB |
| --- | ---: | ---: | ---: | ---: |
| screen_baseline_a | 88.93 | 0.00 | 105.50 | 8840.1 |
| screen_priority_a | 69.09 | 0.00 | 84.18 | 8840.1 |
| screen_archive_a | 87.05 | 0.00 | 106.59 | 8840.1 |
| screen_forward_a | 122.00 | 0.00 | 140.32 | 8856.1 |
| screen_baseline_b | 89.42 | 0.00 | 121.87 | 8840.1 |

A positive rollout tail means collection finishes after PPO. Collection includes both CPU simulation and GPU inference; these timings alone do not attribute that wait entirely to CPU execution.

## Correctness

- The serial and overlapping forward variants match the preceding validated result after 113 actual updates: first/last raw gradients, final momentum, updates, FP32 master weights and BF16 weights, all finite.
- All three candidates and the new baseline match after 1,808 live optimizer updates, including final weights and optimizer state. Rollout hashes also match for observations, sampled actions, rewards, terminals, masks, values, log probabilities, initial recurrent states and final recurrent states.
- Performance runs match every logged recorded-action observation hash and preserve the frozen actor checkpoint.
- These are exactness checks for the tested model/workload, not a claim covering every architecture or GPU.

## Implementations

Inference priority uses the device-supported high-priority CUDA stream for inference, leaving training priority unchanged. No policy sampling or batching changes.

The asynchronous archive copies the one-step inference tensors into rollout storage on another stream. An inference-complete event protects the read; an archive-complete event prevents the next inference from overwriting those tensors. The CPU can consume actions and simulate meanwhile. The last archive is drained before the horizon is released to training.

The next-encoder prototype retains the global gradient norm, clipping, Nesterov and per-matrix normalization. Muon runs on four side streams with private scratch and cuBLAS workspaces. When every encoder matrix update is ready, those weights are updated and cast, then the next encoder forward begins. Remaining updates join and their weights are applied before the next recurrent/decoder pass. The previous backward is already complete and no previous activation reader remains. No gradient accumulation or stale-weight approximation is introduced.

## Reproduction

RTX 4090, CUDA 13.0.2, driver 595.71.05. Fixed 4B score checkpoint, 15.55M parameters; 2,048 environments, horizon 128, minibatch 4,096, 113 PPO updates/batch, 24 pool workers plus 4 submitters. All tests use CUDA_DEVICE_MAX_CONNECTIONS=32, NH_GRAD_PIPELINE=3 and PUF_MUON_LANES=4.

`prepare.py`, `check.py`, `full_screen.py` and per-run `command.json` preserve the setup. `optimizer_forward.patch` and `trainer_overlap.patch` contain the prototypes. Measurements are in `CHECK.json`, `FULL.json`, `RESULTS.json` and `results.csv`. Per-process output and GPU telemetry are in `runs/`.
