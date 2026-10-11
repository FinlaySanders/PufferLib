# NetHack performance: current versus validated optimisations

8 October 2026. Local RTX 4090, i9-14900K. Exact inputs, commands, hashes, logs and profiles are retained alongside this report.

## Result

| Workload | Current SPS | Retained SPS | Gain | Current rollout tail | Retained rollout tail |
|---|---:|---:|---:|---:|---:|
| early | 168,700 | 185,122 | +9.7% | 0.048s | 0.000s |
| score | 98,073 | 176,050 | +79.5% | 1.224s | 0.049s |
| depth | 307,818 | 342,137 | +11.1% | 0.008s | 0.002s |

These are full-pipeline policy decisions per second with fixed policies: inference, PPO forward/backward, gradient clipping and optimizer computation all run, while parameter updates go to scratch storage. They are not rollout-only SPS or a learning-quality result. Current already includes the final cuBLAS workspace fix; the gains above do not count that fix again.

Early and mature-score tests use the same 15,552,136-parameter architecture. The depth policy has 4,311,176 parameters and masks RUN/SEARCH20, using the common batch/replay settings for this study; compare its two implementations, not its absolute SPS against the larger score model.

The current mature-score run loses about 1.22 seconds per batch waiting for rollouts after PPO has finished. The safe engine plus pool removes most of that tail; GPU changes alone barely improve this workload. Consequently, asynchronous execution does not guarantee that simulation is hidden: it only overlaps work until the slower side becomes the critical path.

![Throughput and component attribution](throughput.png)

![Throughput as the frozen mature policy develops older games](mature_workload.png)

## What is actually retained

- Current stream-owned 4 MiB cuBLAS workspaces with default math, common to both sides.
- Engine14: retained lookup/SIMD/LTO snapshot, library SHA256 `70fe544048cd5f9e159d98be3222f35536e508299228e88f61a3c10c968bc403`.
- Shared pool83: 24 workers plus four submitting coordinators, against current per-buffer static OpenMP with 32 requested threads.
- Head-parallel sampling, batched Muon norms, MinGRU copy removal, unused-head log-probability skipping, coalesced PPO zeroing, byte observation storage and rollout graph reuse.

## Component measurements on the mature score workload

| Configuration | Mean SPS | Repeat range | Rollout time left after PPO |
|---|---:|---:|---:|
| Current | 98,073 | 97,892–98,255 (n=2) | 1.224s |
| Engine only | 125,943 | 125,693–126,193 (n=2) | 0.597s |
| Engine + shared pool | 164,255 | 164,166–164,344 (n=2) | 0.052s |
| GPU changes only | 100,905 | 100,699–101,111 (n=2) | 1.232s |
| Engine + pool + GPU changes | 176,050 | 176,044–176,055 (n=2) | 0.049s |

Rollout tail includes CPU simulation, scheduling, transfers and inference. It is not exclusively engine time. The main CPU/GPU timeline below identifies where overlap is lost. Component improvements are measured together; percentages from historical experiments are not multiplied.

## Workload and memory checks

| Workload / build | Parameters | Mean current game turn | Games beyond 10k turns | Games currently at depth ≥8 | VRAM during measurement |
|---|---:|---:|---:|---:|---:|
| early / current | 15,552,136 | 117 | 0.0% | 0.0% | 15.11 GiB |
| early / all | 15,552,136 | 117 | 0.0% | 0.0% | 8.33 GiB |
| score / current | 15,552,136 | 30,357 | 75.3% | 1.0% | 15.11 GiB |
| score / all | 15,552,136 | 30,357 | 75.3% | 1.0% | 8.33 GiB |
| depth / current | 4,311,176 | 997 | 0.0% | 31.3% | 14.47 GiB |
| depth / all | 4,311,176 | 997 | 0.0% | 31.3% | 7.86 GiB |

## CPU/GPU timelines

| Capture | PPO graph/kernel active | Inference active | Overlap | GPU graph/kernel-or-copy idle | All coordinators in environment while GPU idle |
|---|---:|---:|---:|---:|---:|
| graph_depth_all | 99.7% | 66.8% | 66.8% | 0.3% | 0.0% |
| graph_depth_current | 99.1% | 77.3% | 77.1% | 0.7% | 0.0% |
| graph_early_all | 99.9% | 66.5% | 66.5% | 0.1% | 0.0% |
| graph_early_current | 95.2% | 69.1% | 67.3% | 2.5% | 1.1% |
| graph_score_all | 89.9% | 70.8% | 67.2% | 5.1% | 3.3% |
| graph_score_current | 53.0% | 42.6% | 31.2% | 33.1% | 22.3% |
| graph_small_all | 58.9% | 48.0% | 35.3% | 22.2% | 16.9% |
| graph_small_current | 33.4% | 30.2% | 15.1% | 47.6% | 35.0% |
| node_depth_all | 87.1% | 53.4% | 44.9% | 1.3% | 0.2% |
| node_score_all | 81.8% | 41.3% | 33.1% | 6.3% | 3.1% |
| node_score_current | 48.1% | 30.0% | 16.7% | 34.4% | 22.2% |
| node_small_all | 51.6% | 34.9% | 19.2% | 24.0% | 14.7% |

![GPU overlap by workload](gpu_overlap.png)

Graph traces show graph envelopes, including internal gaps. Node traces show individual kernel intervals and add more profiling overhead. Activity is not SM occupancy; overlapping columns must not be summed.

## Training GPU phases

| Capture | Forward | GAE/loss | Backward + gradient waits | Optimizer + cast |
|---|---:|---:|---:|---:|
| graph_depth_all | 161.1 ms | 8.8 ms | 301.3 ms | 286.3 ms |
| graph_depth_current | 204.4 ms | 29.5 ms | 306.9 ms | 295.9 ms |
| graph_early_all | 257.6 ms | 13.5 ms | 465.7 ms | 676.9 ms |
| graph_early_current | 300.4 ms | 30.0 ms | 464.7 ms | 701.1 ms |
| graph_score_all | 255.5 ms | 11.9 ms | 489.4 ms | 662.0 ms |
| graph_score_current | 278.1 ms | 29.5 ms | 479.9 ms | 648.1 ms |
| graph_small_all | 175.3 ms | 12.4 ms | 327.3 ms | 279.1 ms |
| graph_small_current | 197.6 ms | 32.2 ms | 318.0 ms | 281.4 ms |
| node_depth_all | 165.5 ms | 9.4 ms | 310.5 ms | 308.3 ms |
| node_score_all | 257.4 ms | 12.1 ms | 498.8 ms | 676.4 ms |
| node_score_current | 281.9 ms | 27.8 ms | 484.4 ms | 661.0 ms |
| node_small_all | 177.7 ms | 12.4 ms | 333.3 ms | 294.9 ms |

These are elapsed training-stream intervals during concurrent rollout work, not isolated kernel costs or additive whole-program shares. Separate `kernel_breakdown.json` files report summed kernel durations and top kernels.

## Model-size comparison on identical mature engine actions

| Model | Build | Mean SPS | Repeat range | Rollout tail |
|---|---:|---:|---:|---:|
| 15.55M | current | 97,841 | 97,591–98,090 | 1.231s |
| 15.55M | all | 176,633 | 176,588–176,679 | 0.044s |
| 5.10M | current | 105,785 | 105,467–106,102 | 1.637s |
| 5.10M | all | 208,666 | 208,314–209,018 | 0.446s |

The 5.10M model is randomly initialized and frozen; a recorded mature score policy drives the live game. Its inference, training and optimizer still execute. This controls simulation demand, not playing strength or valid on-policy learning. Batch observation hashes are checked against the teacher.

## Recent research control: auxiliary-critic overhead

| Policy workload | Auxiliary critic | Mean SPS | Repeat range |
|---|---:|---:|---:|
| early | Disabled | 167,769 | 166,983–168,554 |
| early | Control mode 0, fitting + logging | 164,076 | 163,897–164,254 |
| recent_score | Disabled | 109,102 | 108,821–109,384 |
| recent_score | Control mode 0, fitting + logging | 107,921 | 107,903–107,939 |

This uses the exact recent research source with profiling-only edits. Mode 0 leaves the policy objective unchanged but still fits the auxiliary critic and records diagnostics. The mature checkpoint is control_s4101 at 999,817,216 steps, distinct from the 4B article score workload above.

## Correctness findings and excluded changes

A depth profiling launch exited during startup without producing a trace. The same binary passed a standalone smoke run and a subsequent profiled rerun, whose observations match the unprofiled workload. The failed attempt is retained as runs/failed_graph_depth_current_startup; its cause is not established and no timing from it is used.

The current 4 MiB cuBLAS implementation is common to all builds. The saved out-of-place Muon/cuBLASLt variant failed exact update matching under this implementation. Removing only its flag restored identical master weights, momentum and final update buffers after 1,808 minibatch updates, along with all trajectory-boundary hashes. It is excluded from the validated package.

The later engine44 and engine61 snapshots diverge reproducibly from the current engine at the epoch-16 observation boundary in the mature score test. Engine-only/GPU-only isolation located the discrepancy in the engine snapshots. Engine14 matches all 64 observation boundaries in the full mature test and is used instead. This narrows the problem to changes after engine14; it does not identify the exact source change responsible. See MISMATCH.md. Provisional engine61 timings are excluded from the result table.

Boundary-hash matching is evidence on these trajectories, not a claim of exhaustive equivalence at every action or across every seed. The archived engine14 reports contain its earlier golden/replay tests. New full-pipeline endpoint comparisons independently check the loaded weights and game observations.

## Reproduction and limits

See METHOD.md, manifest.json, *-build.json, run.py and every runs/*/command.json. Raw throughput is in throughput.csv; full timing/age/hash series are in result.json. No other GPU workload ran during measurements, and compilation was kept outside unprofiled measurement jobs. Nsight traces are separate from the headline timings. CPU hardware/software perf counters are unavailable in this container, so CPU conclusions use coordinator/worker NVTX ranges, resource accounting and joint GPU timelines.

The initial matrix was interrupted for the correctness investigation; command timestamps preserve the actual order. Reported ranges describe repeated measurements, not formal confidence intervals. These tests freeze policy weights and initialize fresh optimizer state; they are workload profiles, not resumed-learning experiments. No live trainer/engine source or defaults were changed.

## Interpretation

The present backend is rollout-limited for the mature score policy, while early/random and this depth workload are predominantly GPU-limited. In the mature graph capture, recorded GPU graph/copy idle time falls from 33.1% to 5.1% with the safe package. Node captures independently show the same distinction. These are measured overlap results, not an assumption based on async being enabled.

Within the retained 15.55M training stream, Muon plus the final cast takes about 47% of elapsed training time, backward about 34%, forward about 18%, and GAE/loss about 1%. Inference overlaps those phases on the same GPU. Their elapsed durations therefore include resource contention and cannot be interpreted as isolated operation costs.

The smaller-model experiment holds observations/game actions fixed. Its graph/copy idle time is about 48% on current and 22% on retained code: reducing network work exposes more rollout cost. A small depth policy that dies or resets sooner is consequently not a reliable speed proxy for a small network playing mature score-policy games.

Long-lived score-policy games have a very different state and action mix from early/random games. This study measures their combined cost; it does not separately attribute the slowdown to game age, number of objects/monsters, or macro-action length.

The next safe integration target is engine14 plus the shared pool and the verified GPU flags. Later engine snapshots need their new observation mismatch localized before reuse; the out-of-place optimizer needs its current-stack numerical discrepancy resolved. For further 15.55M GPU gains, focus on Muon and network matrix/backward work. For smaller models, rollout latency remains a major target. No roofline or SM-occupancy measurement was made, so matrix-kernel prominence alone does not establish compute versus memory-bandwidth saturation.

## Sampling kernel in the full-pipeline node traces

| Build | Mean sampler kernel time | Share of summed inference kernel time |
|---|---:|---:|
| Current | 178.6 μs | 32.5% |
| Retained | 29.5 μs | 6.0% |

This comparison includes concurrent PPO and profiling effects. It is not the historical isolated-kernel speedup, nor an end-to-end speedup. Raw per-kernel and GPU phase CSVs accompany the report.

## Research-control overhead summary

Early/random: 167,769 SPS with auxiliary-Q disabled, 164,076 with control-mode fitting/logging enabled (-2.2%). Same policy and environment trajectory, two repeats per mode.
Recent 1B checkpoint: 109,102 SPS with auxiliary-Q disabled, 107,921 with control-mode fitting/logging enabled (-1.1%). Same policy and environment trajectory, two repeats per mode.
