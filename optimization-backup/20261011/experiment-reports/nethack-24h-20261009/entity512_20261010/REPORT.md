# Entity-encoder fusion on the original 512-environment configuration

Both inference and training-forward fusion improve full-pipeline throughput from **221,217 to 228,005 SPS (+3.07%)**, or **0.821 billion steps/hour**. Training fusion alone gives +2.32%; inference alone is +0.62% and remains below the predeclared 1% retention gate. The combined variant is a useful experimental candidate; no production or benchmark defaults were changed.

## Configuration and method

512 environments, horizon 512, four buffers, 32 shared CPU workers, the original 15,552,136-parameter model, batch 262,144, minibatch 4,096 and 113 PPO updates per batch. Same optimized engine, immutable `attribution_v37` binary, model, flags, and recorded mature-game actions throughout. Only `NH_ENTITY_FUSED` and `NH_ENTITY_TRAIN_FUSED` change, each using mask 15 for all four entity branches.

Eight sequential 64-epoch processes: baseline, inference, training, both, both, training, inference, baseline. Warm up through epoch 23 and time epochs 24–62. Full inference, forward/backward and optimizer computations execute; actor weights remain frozen and optimizer writes go to scratch. These are compute-throughput measurements, not learning curves.

| Variant | Mean SPS | Gain | Two-run range | PPO host phase |
|---|---:|---:|---:|---:|
| Current stack | 221,217 | +0.00% | 220,504–221,930 | 1182.1 ms |
| Inference fusion | 222,594 | +0.62% | 222,227–222,961 | 1174.8 ms |
| Training-forward fusion | 226,354 | +2.32% | 226,132–226,577 | 1155.2 ms |
| Both | 228,005 | +3.07% | 227,921–228,089 | 1146.6 ms |

The closing baseline is 0.64% slower than the opening baseline. Both training and combined candidates exceed both controls on both repeats and pass the predeclared gate. Inference alone does not. The small additional benefit of inference over training fusion is less firmly established than the overall combined gain.

## Why this differs from the 2048-environment result

At 512 environments, all timed epochs have zero exposed rollout tail: PPO finishes last. Combined fusion shortens the average batch/PPO host phase from 1,182.1 to 1,146.6 ms. Rollouts are still ready about 157 ms before PPO finishes with both fusions.

In the earlier 2048-environment experiment, training fusion saved about 28 ms of isolated GPU work but added almost the same amount of waiting for rollouts. Its full-pipeline gain there was only 0.32%, or 0.46% with inference fusion too. The original configuration exposes the useful GPU saving. This does not imply every previous GPU microbenchmark win will transfer.

## Validation

- Every one of the 64 observation-boundary hashes in each of eight timing runs matches the historical original-configuration reference. Frozen actor hashes agree before and after each run. Commands and environment overrides differ only in the intended fusion switches and output paths.
- Each enabled fusion loads all four entity branches; disabled variants have no corresponding activation markers.
- A fresh saved-batch comparison using the original shape performs 113 genuine optimizer updates. Training fusion matches the first and last raw gradients, final FP32 master weights, BF16 parameters, optimizer momentum and update buffers exactly. A repeated control also matches exactly. All checked values are finite.
- Full inference on the saved mature batch uses the actual 128-agent inference shape. All 95,104 output BF16 elements match exactly; repeated controls agree.
- The combined path then passes a separate 16-batch / 1,808-update pipeline comparison (4,194,304 environment decisions). Final checkpoint, master weights, momentum, updates, policy actions/log-probabilities/values, rollout hashes and recurrent-state hashes match exactly, with finite checked state. Environment actions remain replayed; this is implementation validation, not an on-policy learning experiment.
- All 19 protected source/reference/binary/batch hashes remain unchanged. No production changes, commits or pushes. GPU idle at completion.

These are bounded exactness checks relative to the current experimental stack, not a claim of equivalence to pristine upstream or proof for every input, GPU and shape. Earlier synthetic testing observed rare intermediate rounding differences, so universal bitwise equivalence is not claimed.

## Artifacts

`FULL.json` and `FULL.results.json` retain the schedule and raw results; `SUMMARY.json` and `TIMINGS.csv` contain the comparisons; `CHECKS.json`, `UPDATES.json` and their result files retain numerical validation; `CHECK_SUMMARY.json` and `INTEGRITY.json` summarize the checks. Individual commands, hashes and logs are under `../runs/entity512_*`.

Reproduce with `python ../campaign_primary.py FULL.json` after assigning fresh run labels. `summarize.py` checks the configurations, observation hashes, activation markers and timing gate. Do not run timing jobs concurrently.

## Follow-up: GPU overlap cost

With both fusions, two fresh isolated GPU processes (five measured trials each, after warmup) take 996.35 and 997.23 ms for the complete 113-update PPO workload: mean **996.79 ms**. The preceding full-pipeline PPO host phase is **1,146.63 ms**. The gap is **149.84 ms**, or **15.03% longer than isolated PPO** (13.07% of the full phase).

This is an overlap-associated gap, not a clean measurement of wholly avoidable hardware contention: the full pipeline also executes inference and transfers, and uses a host-phase measurement over multiple batches rather than a repeated saved GPU batch. Isolated PPO corresponds to 262,988 SPS if all other work were free, which is not an achieved training speed. The original pre-fusion graph profile supports interference qualitatively, but no new post-fusion kernel-level contention decomposition has been run.

High-priority inference is currently enabled, inherited from the CPU-limited 2048-environment tests where it helped. Retesting normal versus high inference priority is a plausible next scheduling experiment now that rollouts finish early. No priority change has been made. Full serialization, larger cache reservations, and fewer Muon lanes are not established wins. `ISOLATED_GPU.json`, its results and `OVERLAP_COMPARISON.json` retain the new measurements.
