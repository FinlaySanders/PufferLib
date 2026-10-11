# Does the CUDA connection setting enable parallel Muon on GPU Breakout?

Default Breakout configuration, same binaries and numerical checks as REPORT.md.
Batched matrix normalisation enabled in both serial and parallel arms; the changes
are one vs four Muon streams, and CUDA_DEVICE_MAX_CONNECTIONS unset vs 32.
Eight interleaved fresh runs, 2,048 batches each, seed 901. First 128 batches and
final unprefetched batch excluded from throughput, as in the main benchmark.

| Connections | Serial SPS | Four-stream SPS | Parallel gain |
|---|---:|---:|---:|
| Default (unset) | 42.234M | 49.340M | +16.83% |
| 32 | 42.453M | 49.950M | +17.66% |

Every run matched bit for bit on final master weights, BF16 parameters, momentum,
updates, recurrent state, and captured observations, actions, rewards and values,
after 6,144 optimizer updates. All production source hashes remain unchanged.

This tests the current isolated prototype on this machine. It cannot establish
why a previous experiment or a maintainer did not discover the optimisation.
Raw per-run results and commands: connections.json and connections-*/result.json.
