# NetHack grouped rollout collection — 8 October 2026

With 2,048 resident games, processing 512 at a time in four concurrent batches of 128 increased the full-pipeline mature-game rate from 165,176 to 211,600 steps/s (+28.1%) in the controlled 5.10M-parameter workload. The 512-environment reference reached 220,782 steps/s: grouping recovered most of the population-scaling loss. This is measured pipeline throughput, not the earlier CPU-only burst upper bound.

All timing runs perform inference, simulation, rollout storage, GAE, PPO forward/backward, and optimizer computation. Optimizer writes go to scratch so the acting and training weights stay fixed throughout timing. No training-quality claim is made.

The engine is the same opt61-final library throughout (including the previous correctness fixes); these gains are incremental over the existing optimizations. Machine: i9-14900K and RTX 4090. Batch 262,144, minibatch 4,096, 24 shared environment workers, horizon 128 at 2,048 environments. Every case runs alone.

For controlled timing, real inference runs before every action, but recorded mature-policy actions then drive the games to hold environment complexity fixed. The 5.10M network is frozen random initialization, not a trained small policy. The identical original 512 teacher streams are repeated across the larger population. Timing follows about 8,192 warmup decisions per game; the timed window is approximately decisions 8,320–12,288 (31 batches), with late games averaging roughly 28–30k world turns. The 512-environment reference uses horizon 512 to retain the same total batch, with a nearby 8,192–12,288 decision window. Thus it is a throughput reference, not an identical learning configuration.

| 5.10M workload | Inference batches | Active games | Chunk | Steps/s | Change vs mean baseline |
|---|---:|---:|---:|---:|---:|
| Original schedule, first | 4 × 512 | 2048 | — | 164,554 | -0.4% |
| Original schedule, repeat | 4 × 512 | 2048 | — | 165,798 | +0.4% |
| Smaller batches, ungated | 16 × 128 | 2048 | — | 154,650 | -6.4% |
| Grouped | 16 × 128 | 512 | 16 | 202,654 | +22.7% |
| Grouped | 16 × 128 | 512 | 64 | 210,738 | +27.6% |
| Grouped | 16 × 128 | 512 | 128 | 211,600 | +28.1% |
| Larger grouped batches | 8 × 256 | 512 | 128 | 193,588 | +17.2% |
| Original layout, one active stream | 4 × 512 | 512 | 128 | 139,202 | -15.7% |
| Original layout, two active streams | 4 × 512 | 1024 | 128 | 168,760 | +2.2% |
| 512 resident games, reference | 4 × 128 | 512 | — | 220,782 | +33.7% |

The original baseline repeats differ by 0.76%. 64- and 128-step groups are essentially tied in this screen; the 0.4% difference is not evidence of a robust chunk-size winner. The 16-buffer prototype uses about 468 MiB more GPU memory. One active inference stream saves CPU work but loses overlap and is slower overall; its large-policy test was pruned. Two original-size streams retain exact numerics but give only a small smaller-model gain.

## Actual 15.55M score policy

These are natural policy-selected rollouts from the fixed 4B s705 checkpoint, using 2,048 distinct environment seeds. The original per-game action RNG mapping is retained in every case. The complete training computation still runs with fixed weights.

| Schedule | Steps/s | Change | Rollout tail after learner | Learner tail after rollout |
|---|---:|---:|---:|---:|
| Original four batches | 163,411 | +0.0% | 0.203 s/batch | 0.000 s/batch |
| Four active 128-game batches | 177,418 | +8.6% | 0.017 s/batch | 0.037 s/batch |
| Two active original 512-game batches | 166,721 | +2.0% | 0.169 s/batch | 0.000 s/batch |

The smaller-batch grouped case gives an observed +8.6% here and nearly removes the rollout tail. However, repartitioning changes floating-point policy outputs and hence eventual trajectories: final mean game ages were 28,235 and 30,070. This is a natural-workload pilot, not an exactly trajectory-matched causal estimate. The controlled 5.10M comparison above is the clean speed measurement. No GPU trace was taken in this study, so tail timing is not a decomposition of CPU time versus inference GPU time.

## Behavior and determinism

- The engine binary and environment source did not change. Every completed 96-batch teacher-driven case has identical observation checkpoints. Within each original four-buffer group, the benchmark also checks that duplicated games are byte-identical. Earlier engine goldens/fuzz remain in the preceding engine study; they were not rerun for this scheduling-only experiment.
- Scheduling the same sixteen buffers differently passed exact comparisons after 1,808 real optimizer updates: weights, momentum, update tensors, rollout observations/actions/values/log-probabilities/rewards/dones/masks, initial recurrent states and final recurrent states. A separate live 15.55M-policy comparison also passed all of these after 1,808 updates.
- The original four-buffer layout with one or two active streams also matched the original schedule exactly after 1,808 updates on the teacher-driven workload.
- Changing four buffers of 512 to sixteen buffers of 128 is **not bitwise identical**, even after preserving the original per-game action RNG. A frozen, two-batch diagnostic proved identical initial weights and RNG bytes, identical observations/rewards/dones/masks, but different policy outputs. Among 2,621,440 compared head samples, 1,802 differed (0.0687%); 136 of 131,072 verb samples differed (0.104%). Differences already occur in the first forward step before any update. These are batch-size-dependent forward differences; exact GPU-kernel/reduction attribution was not traced. Consequently, the full cross-layout optimizer-state comparison fails. Do not describe the faster repartitioned version as exactly matching the old run.
- Timing checkpoints remained byte-identical to their loaded weights. Live PufferLib sources, the protected drone edits, and depth.ini retain their original hashes. Everything added here is isolated.

## Interpretation and next use

This is evidence that locality improvements can survive real inference and training. The useful implementation must also retain enough concurrent inference/environment work: shrinking the active set alone is insufficient. Keep 2,048 independent game/RNN/RNG states, advance a subset while others sleep, and train on the same complete rollout batch using the same actor snapshot. There are no stale actions, skipped games, altered rewards, or extra policy updates between groups.

The 28% configuration is suitable for further experiments with a new inference partition, but is not promoted to a production default. If exact reproduction of the old partition is mandatory, retain it and use the original-layout results above; do not assume the larger speedup carries over. Fixed-layout scheduling itself is exact in the checks performed. No learning-benefit test of bigger batches was run.

## Reproduction and artifacts

- `source/` and `collector.patch`: isolated benchmark implementation and diff against the previous comprehensive harness. The patch includes proof instrumentation and fixes the old harness's hard-coded four-entry completion array; it is not a polished upstream PR.
- `manifest.json`, `all-build.json`: exact source/binary/engine hashes, build flags and machine.
- `run.py`, `bench.py`, `confirm.py`, `original_layout.py`, `two_streams.py`, `numerics.py`: exact experiment commands. Each case has its own `command.json`, raw log, GPU telemetry, results and frozen/checkpoint proofs.
- `results.csv`, `summary.json`, `VALIDATION.json`, `NUMERICS.json`: machine-readable results and the explicitly failed cross-partition comparison. `proof_*` and `numeric*` timings are correctness diagnostics, not mature throughput measurements.

Example controlled grouped measurement (new output label required):

```sh
python /puffertank/experiments/nethack-grouped-rollouts-20261008/run.py my_grouped all small \
  agents=2048 horizon=128 buffers=16 cohort=4 chunk=128 \
  epochs=96 start=64 end=95 \
  replay=/puffertank/experiments/nethack-comprehensive-20261008/actions
```

`live=1` uses normal unique game seeds and no teacher replay; use workload `score` to load the actual 4B policy. `canonical=1` preserves the old four-buffer per-game sampler RNG mapping when repartitioning. Timing freezes weights by default; `update=1 proof=1` enables real-update correctness checks. All finished jobs are stopped normally; nothing was committed or pushed.
