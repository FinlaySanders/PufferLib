# cuBLAS workspace patch: all-environment performance

RTX 4090, upstream 5.0 6ffa5b10dbbbe4d1e8288367c7d9d3acd3bad4a2 versus the exact uncommitted 4 MiB per-stream workspace patch saved in candidate.patch. Serial runs, seed 901. Same environment shapes/backend choices as the determinism matrix. One GPU; OMP_NUM_THREADS=8 except NetHack=32. NetHack uses the clean engine from the previous upstream comparison, excluding deferred engine optimizations.

Full rollout plus training-loop throughput, excluding initial graph capture/warmup (first max(16, epochs/4) updates), the final update, checkpoint saving, logging and final evaluation. Each version uses at least two repeats, in alternating ABBA blocks. Aggregate SPS = summed timed steps / summed timed seconds. Fresh training, not a mature-policy or inference-only benchmark.

| Configuration | Upstream SPS | Patched SPS | Change | Runs/version | Timed seconds upstream/patched |
|---|---:|---:|---:|---:|---:|
| nethack-h512 | 112,413 | 172,815 | +53.73% | 2 | 69.96 / 45.51 |
| nethack-h128 | 174,388 | 174,464 | +0.04% | 2 | 35.33 / 35.31 |
| craftax | 726,449 | 729,356 | +0.40% | 2 | 21.65 / 21.57 |
| breakout-cpu | 14,839,583 | 14,928,209 | +0.60% | 6 | 10.12 / 10.06 |
| breakout-gpu | 42,516,571 | 42,236,322 | -0.66% | 18 | 10.60 / 10.67 |
| g2048 | 738,482 | 738,357 | -0.02% | 2 | 33.37 / 33.37 |
| cartpole | 47,441,893 | 47,744,798 | +0.64% | 40 | 10.50 / 10.43 |
| pong | 7,584,893 | 7,614,638 | +0.39% | 8 | 13.20 / 13.15 |
| drone | 6,793,720 | 6,798,495 | +0.07% | 2 | 29.48 / 29.46 |
| tmaze | 12,401,854 | 12,428,349 | +0.21% | 6 | 12.11 / 12.09 |
| admiral | 6,675,477 | 6,717,771 | +0.63% | 2 | 30.00 / 29.81 |
| nmmo3 | 884,873 | 885,144 | +0.03% | 2 | 35.25 / 35.24 |
| minimal | 8,243,427 | 8,244,202 | +0.01% | 2 | 21.24 / 21.24 |
| asteroids | 4,737,969 | 4,764,602 | +0.56% | 4 | 10.57 / 10.51 |
| snake | 952,690 | 952,422 | -0.03% | 2 | 26.14 / 26.15 |

## Interpretation and limits

Long-horizon NetHack improves 53.7%. All other measured changes are below 1%; these should be described as broadly unchanged, with small measured gains/regressions rather than universal speedups. GPU Breakout measured a small regression (~0.66%). NetHack horizon 128 is unchanged. Craftax repeatability improves without a material throughput gain.

Training trajectories differ where upstream/patch are not bitwise equivalent, so this is end-to-end configuration performance, not a fixed-trajectory kernel microbenchmark. This is not a confidence interval or a mature NetHack performance claim.

An attempted 4976-update CartPole extension produced NaNs on upstream; it is excluded. CartPole instead uses 40 valid 128-update runs per version. Other short measurements were repeated/extended with a cap on run length. Every run included in this table exits successfully and has finite final weights.

Raw data: results.json (initial pass), extended2/results.json (replacement measurements for short cases), final-results.json (selected runs only), final-summary.json, results.csv. Failed CartPole diagnostic retained separately under extended/. No production source edits; original working diff verified unchanged.
