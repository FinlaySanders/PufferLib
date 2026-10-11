# Parallel Muon on default Breakout

Isolated test on the current generic trainer; production files unchanged.
RTX 4090, CUDA 13.0.2, CUDA_DEVICE_MAX_CONNECTIONS=32 for every arm.
Default Breakout: hidden size 32, four recurrent layers, 16,192 parameters,
4,096 environments, horizon 32, minibatch 65,536, three PPO updates per batch,
async collection, CUDA graphs and BF16. CPU backend uses eight worker threads.
Both backends use GPU policy training; CPU/GPU labels refer to simulation.
Control already includes the cuBLAS workspace fix.

## Full training throughput

| Environment | Original SPS | Batched-normalisation serial | Two streams | Four streams | Four vs original | Four vs batched serial |
|---|---:|---:|---:|---:|---:|---:|
| CPU | 14.590M | 14.609M | 14.657M | 14.597M | +0.04% | -0.08% |
| GPU | 41.825M | 42.413M | 48.171M | 49.936M | +19.39% | +17.74% |

These are full-pipeline agent steps/second, not optimizer-only throughput.
Fresh runs interleaved original/serial/2/4/4/2/serial/original, with the same
training seed 901 and horizon/budget within each backend. CPU runs train for
1,024 batches and GPU runs for 2,048. Timing excludes the first 128 batches
(initialisation, CUDA graph capture and warm-up) and final unprefetched batch,
includes normal logging/host overhead within the measured interval, and excludes
final checkpoint/state writes. Aggregate SPS is total measured steps / total time.
Clocks were not locked. The original vs candidate-serial-without-batching pilot
also checked that instrumentation and added buffers did not change the control.

## Repeat ranges and GPU training time

GPU time below is elapsed PPO work while collection is running, not an isolated
GPU benchmark; concurrent inference can affect it.

| Environment | Arm | SPS repeat range | Mean GPU PPO ms/batch |
|---|---|---:|---:|
| CPU | original | 14.561–14.619M | 2.626 |
| CPU | batched_serial | 14.609–14.609M | 2.591 |
| CPU | parallel_2 | 14.599–14.716M | 2.263 |
| CPU | parallel_4 | 14.584–14.609M | 2.094 |
| GPU | original | 41.805–41.845M | 3.109 |
| GPU | batched_serial | 42.381–42.446M | 3.064 |
| GPU | parallel_2 | 48.156–48.187M | 2.675 |
| GPU | parallel_4 | 49.926–49.945M | 2.420 |

## Numerical checks

For each backend, all arms and both repeats match bit for bit on final FP32
master weights, BF16 parameters, momentum, optimizer updates, recurrent training
state, and both slots of captured observations, actions, rewards and values.
That covers 3,072 optimizer updates on CPU Breakout and 6,144 on GPU Breakout,
plus 768-update pilots. CPU and GPU trajectories are compared within each backend.
All final master weights are finite. Exactness here describes these tested runs,
not a proof for every possible configuration.

## Interpretation

Parallel Muon helps GPU Breakout despite its small model: independent small matrix
updates can run concurrently. On CPU Breakout it reduces GPU PPO time but hardly
changes full throughput, so optimizer time is not the limiting part of that
pipeline at these settings. This test does not attribute the remaining collection
time to specific CPU routines, transfers or inference kernels.

Files: `full.json`, `pilot.json`, `results.csv`, per-run `result.json` with per-batch
timings and state hashes, `optimizer.patch`, source and build logs. `commit.txt`
and `protected.json` record the starting production revision and exact file hashes.
