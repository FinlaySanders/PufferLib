# Current cuBLAS patch: training throughput

Upstream 5.0 at 6ffa5b10 versus candidate.patch. RTX 4090, seed 901, default environment configs, OMP_NUM_THREADS=8. Serial upstream/candidate/candidate/upstream runs; 134,217,728 steps per Breakout run, 16,777,216 per 2048 run. Timed full rollout + training loop, excluding first quarter and final update, startup/evaluation/checkpoint/logging. Throughputs aggregate timed steps divided by summed time over both repeats.

| Environment | Upstream SPS | Candidate SPS | Change |
|---|---:|---:|---:|
| cpu | 14,536,699 | 14,614,525 | +0.54% |
| gpu | 42,516,878 | 42,624,051 | +0.25% |
| g2048 | 739,028 | 738,919 | -0.01% |

No material throughput change on these three workloads. Every saved checkpoint remains byte-identical to upstream; both versions reproduce on repeat runs. All saved FP32 weights are finite. Current NetHack performance was not measured by this test; earlier strict-math measurements do not establish performance of this version. Full commands, timing samples and hashes are in results.json and run logs.
