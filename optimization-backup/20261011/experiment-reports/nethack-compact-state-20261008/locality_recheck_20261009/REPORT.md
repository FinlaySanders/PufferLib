# Remaining NetHack locality gap — 9 October 2026

## Result

The latest retained engine still has a large mature-game standard-versus-burst gap. Two serial repeats per arm give **+21.44% throughput at 512 games and +67.04% at 2048 games** when 16 known recorded actions are executed before switching games. These are diagnostic CPU-replay gains, not a new production or training speedup.

| Games | Standard SPS | Burst16 SPS | Throughput difference | Standard sampled step µs | Burst sampled step µs |
|---:|---:|---:|---:|---:|---:|
| 512 | 294,536 | 357,679 | +21.44% | 92.48 | 77.86 |
| 2048 | 216,232 | 361,198 | +67.04% | 129.73 | 78.41 |

Normal 512 and 2048 replay exactly the same 8192–10240 decision window on the same 512 unique recorded mature score-policy trajectories; 2048 duplicates each stream four times. Both sizes approach the same throughput in bursts. The added cost from cycling among more games largely disappears in this diagnostic. That supports locality as an ongoing priority.

At 2048 games, normal throughput repeats differ by 0.016%, and burst repeats by 0.011%. At 512 they differ by 0.22% and 0.40%. These repeat ranges are descriptive, not confidence intervals for other machines or game distributions. Paired game-bootstrap intervals for sampled step-time ratios are in summary.json.

## What this establishes—and what it does not

- Sampled time inside puf_step falls by 39.56% at 2048, so fewer scheduler submissions alone cannot explain the gain.
- Earlier selective prewarming supplied causal evidence for a data-locality penalty. This fresh test confirms the broader locality/scheduling gap on the latest engine; it does not separately measure data-cache, instruction-cache, branch-prediction or TLB effects.
- Burst replay knows future actions. Ordinary policy inference must observe a state before selecting its next action; the burst mode cannot simply be enabled in training.
- These CPU results do not imply a 67% end-to-end training gain. No production defaults or engine code were changed.
- The previous 141→91→77µs measurements used an earlier engine and machine conditions. Do not subtract these percentages to estimate how much old headroom was recovered.

## Paired profile

The unchanged engine was profiled separately under both schedules. Profiled timings are excluded from the native table. Monster-turn processing (movemon inclusive) accounts for 62.6% of normal samples and 69.6% of burst samples; m_move and mfndpos together account for 38.4% and 44.9% of self samples. Higher percentage under burst does not mean more absolute work: the total cost is lower.

Estimated self-time reductions are largest in movement/neighbour checks, followed by observation construction, monster-loop bookkeeping, movement handling, inventory/burden checks and floor-object lookup. The benefit is distributed. profile_comparison.csv contains approximate attribution (sample fractions scaled by separately measured step CPU time), not exact function timers or hardware misses. Inclusive rows overlap.

## Standard-rollout scheduling screens

**Common ready-buffer order:** 216,386→216,580 SPS (+0.09%; 1 control / 1 candidate runs).

**Recheck preferred ready buffer after useful work:** 216,301→236,933 SPS (+9.54%; 2 control / 2 candidate runs).

These use one action per environment per submission, the same recorded actions and engine, unchanged ordinary warm-up, original per-region work stealing and synchronization. Flags change only the order in which workers service ready buffers. The recheck variant gained 9.54% in the repeated 2048 CPU test. It is not retained as a default because the smaller workload regresses and full training is flat.

## Follow-up validation and limits

- 512 early: candidate changes of -1.02%, +3.50%. The repeat reverses execution order; each ratio uses its own matched control.
- 512 mature: candidate changes of -3.74%, -4.68%. The repeat reverses execution order; each ratio uses its own matched control.
- Recheck scheduling matches 4,194,304 immutable per-decision hashes at 2048 games, with 0 differences.
- Full training pipeline: 185,406→185,017 SPS (-0.21%, effectively flat in this single pair). All 96 batch-state proofs and frozen actor hashes match.
- Full-pipeline setup: 15,552,136-parameter score policy, 2048 games, 4 buffers, horizon 128, batch 262144, minibatch 4096, 24 pool workers, 96 epochs; measure epochs 64–94. Includes inference and PPO/optimizer computation with actor weights frozen and recorded mature actions. CPU replay uses pinned workers; the pipeline keeps the pre-existing affinity behavior.
- Both full-pipeline arms have zero rollout-tail wait in the measured window. The current GPU workload hides this CPU improvement. A changed model size or batching configuration needs its own measurement.

The 512 scheduling slowdown coincides with roughly ten times more voluntary context switches in the first mature screen. This supports a locality-versus-utilization tradeoff; it is not an exact attribution of every lost cycle. A useful next scheduler experiment would preserve the large-population locality gain while avoiding excess waiting at smaller populations. No new training speedup or universal default is established.

## Correctness and provenance

- Retained source: `/puffertank/experiments/nethack-compact-state-20261008/engines/monmove_guard_pgo/source`.
- Retained library SHA256: `2a5cfac52f27a7430383c00e0c2a84ae96cdc12c64c2decbb993aeea8ec2ce84`.
- Original native harness SHA256: `219cc75c660141103929fbed7e05e27ab92799ade5232a61037a432cd6a34f6d`.
- Every normal and burst run matches immutable endpoint observation hash b97835c62aaf388f, final mean game time 29502.23, and the appropriate total world-turn advance count.
- Separate burst16 verification matches **1,048,576 per-decision hashes**, with **0 mismatches**, against the pre-existing opt61 reference. Each hash covers observation, reward, terminal and action mask. The hash-check timing is excluded from performance comparisons.
- 24 pinned workers plus 4 submitters; warm 8192 then measure 2048 decisions/game; all heavy jobs serialized. Machine settings unchanged.
- Exact commands, environment, binaries, source patches and raw logs are in protocol.json and runs/*/command.json. Raw numeric outputs are native_runs.csv, summary.json and profile_comparison.csv.

## Decision

Locality remains more promising than broad SIMD work as an explanation for the large-env slowdown. Simple ready-buffer ordering did not recover it. Do not equate the observed burst headroom with an immediately available optimization: a successful standard-rollout change must avoid/retain the same data accesses while preserving utilization and inference dependencies.
