# NetHack batching sweep

Completed 24 configurations: eight successful and sixteen failed. Best measured throughput was 242,117 steps/s at 1.98M parameters and 235,289 steps/s at 5.10M parameters, both with 512 environments and a 4096 minibatch. Larger learner minibatches and the successful 1024-environment configurations were slower.

At 1024 environments, minibatches 4096 and 32768 failed CUDA graph creation. The 16384 cases completed at 22.91/23.50 GiB device usage. All 2048/4096 cases failed initial cudaMalloc allocation. The logs do not print the CUDA error code for graph creation failures, so their exact cause is unconfirmed.

A signed 32-bit observation-transpose overflow was discovered and corrected only in the isolated harness. The new wide path passed a 2,411,724,800-element correctness check; successful expanded cases also matched teacher trajectory hashes. See wide-transpose.patch and METHOD.md.

Mature recorded games; full pipeline with frozen policy weights. See [METHOD.md](METHOD.md) for controls and limitations.

| Parameters | Environments | Minibatch | Steps/s | GPU GiB | Rollout tail (s) | PPO tail (s) | Updates/batch |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1.98M | 512 | 4096 | 242,117 | 14.63 | 0.330 | 0.000 | 113 |
| 1.98M | 512 | 16384 | 227,780 | 14.30 | 0.670 | 0.000 | 28 |
| 1.98M | 512 | 32768 | 211,010 | 15.78 | 0.783 | 0.000 | 14 |
| 5.10M | 512 | 4096 | 235,289 | 14.79 | 0.195 | 0.000 | 113 |
| 5.10M | 512 | 16384 | 207,876 | 14.76 | 0.656 | 0.000 | 28 |
| 5.10M | 512 | 32768 | 188,994 | 16.64 | 0.808 | 0.000 | 14 |
| 1.98M | 1024 | 4096 | Failed (rc -6) | — | — | — | — |
| 1.98M | 1024 | 16384 | 184,907 | 22.91 | 1.866 | 0.000 | 56 |
| 1.98M | 1024 | 32768 | Failed (rc -6) | — | — | — | — |
| 5.10M | 1024 | 4096 | Failed (rc -6) | — | — | — | — |
| 5.10M | 1024 | 16384 | 177,671 | 23.50 | 1.737 | 0.000 | 56 |
| 5.10M | 1024 | 32768 | Failed (rc -6) | — | — | — | — |
| 1.98M | 2048 | 4096 | Failed (rc -6) | — | — | — | — |
| 1.98M | 2048 | 16384 | Failed (rc -6) | — | — | — | — |
| 1.98M | 2048 | 32768 | Failed (rc -6) | — | — | — | — |
| 5.10M | 2048 | 4096 | Failed (rc -6) | — | — | — | — |
| 5.10M | 2048 | 16384 | Failed (rc -6) | — | — | — | — |
| 5.10M | 2048 | 32768 | Failed (rc -6) | — | — | — | — |
| 1.98M | 4096 | 4096 | Failed (rc -6) | — | — | — | — |
| 1.98M | 4096 | 16384 | Failed (rc -6) | — | — | — | — |
| 1.98M | 4096 | 32768 | Failed (rc -6) | — | — | — | — |
| 5.10M | 4096 | 4096 | Failed (rc -6) | — | — | — | — |
| 5.10M | 4096 | 16384 | Failed (rc -6) | — | — | — | — |
| 5.10M | 4096 | 32768 | Failed (rc -6) | — | — | — | — |

All successful rows passed three teacher-observation hashes, equality of repeated cohorts, and unchanged initial/final policy parameters. Failures retain logs and command manifests in their case directory.

Timing: six warmed full-pipeline epochs, excluding the final epoch without prefetched rollout. These are short measurements, not confidence intervals. GPU memory includes CUDA context and graph allocations. Larger minibatches reduce optimizer update count and do not establish equal learning quality.
