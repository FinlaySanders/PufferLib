# Parallel Muon with 32 CUDA compute connections

Independent matrix updates on 4 streams improve the mature-game full-pipeline benchmark from 187,358 to 193,389 SPS (+3.22%). This is incremental over gradient pipelining and the CUDA queue fix.

## GPU training graph screen

| Optimizer streams | First process, ms | Second process, ms | GPU throughput gain |
| --- | ---: | ---: | ---: |
| 1 | 1272.702 | 1276.285 | +0.00% |
| 2 | 1201.723 | 1204.584 | +5.93% |
| 4 | 1149.843 | 1151.335 | +10.77% |

Two warmups and ten measured full PPO graphs/process. Order: 1, 2, 4, 4, 2, 1 streams. The saved mature batch is restored before every graph; it contains 113 optimizer steps.

## Full pipeline

| Run order | Streams | SPS | Mean exposed rollout tail, ms | Largest tail, ms | GPU allocation, MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline_a | 1 | 187,583 | 0.000 | 0.000 | 8748.1 |
| candidate_a | 4 | 193,117 | 90.136 | 130.758 | 8840.1 |
| candidate_b | 4 | 193,662 | 85.597 | 127.426 | 8840.1 |
| baseline_b | 1 | 187,133 | 0.000 | 0.000 | 8748.1 |

Serial-control drift: -0.24%. Candidate throughput corresponds to 0.696 billion steps/hour on this workload.

Each process runs 96 rollout batches; the measurement covers batches 64–94 (31 batches). These are wall-clock rates with CPU simulation, GPU inference and the full PPO update pipeline concurrent. The simulation follows saved action streams and the actor stays frozen; optimizer computation still runs and writes to scratch. This is a performance benchmark, not an on-policy learning or score experiment.

## Correctness

- 1, 2 and 4 streams match the previous validated serial result bit-for-bit after 113 updating minibatches: raw first/last gradients, final parameter updates, momentum, FP32 master weights and BF16 parameters. All values finite.
- The selected candidate and serial control match after 1,808 live optimizer updates: final checkpoint, optimizer state and every recorded-action rollout observation hash.
- All four performance runs have identical observation hashes and unchanged frozen actor checkpoints.
- Production files and protected earlier experiment sources are unchanged.

## What changed

Global clipping, Nesterov momentum and batched matrix normalization remain serial. The independent Newton–Schulz matrix updates are distributed round-robin across streams, each with private scratch and its own cuBLAS handle/workspace. All streams join before the flat weight update and cast. The five Newton–Schulz iterations, math mode and arithmetic are unchanged. No work from the next minibatch is overlapped in this experiment.

Both sides use CUDA_DEVICE_MAX_CONNECTIONS=32 and NH_GRAD_PIPELINE=3. The earlier parallel Muon test used a different stack and default CUDA queues, so these measurements do not isolate which difference explains its old negative result.

## Workload and artifacts

RTX 4090, CUDA 13.0.2, driver 595.71.05. Fixed 4B score policy, 15,552,136 parameters; 2,048 environments, horizon 128, minibatch 4,096, 113 PPO updates/batch, 24 CPU pool workers plus 4 submitters. The environment action workload is four copies of 512 saved streams. Saved batch age averages 27,087 game turns; 1,552/2,048 games exceed 10,000 turns.

- `parallel_muon.patch`: experimental source patch relative to the latest gradient-pipeline source.
- `PLAN.md`: predeclared correctness/performance gates.
- `SCREEN.json`, `FULL.json`, `RESULTS.json`, `results.csv`: measurements and exact hashes.
- `runs/*/command.json`, `run.log`, `gpu.csv`: reproducible commands, output and GPU telemetry.
- `protected_before.json`, `protected_after.json`: verification of untouched production files.
