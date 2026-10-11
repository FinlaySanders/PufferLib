> **Results invalid for the training objective — missing reward clipping.** Offline reward/GAE/Q targets omitted the trainer’s [-1, 1] reward clamp. Derived critic and variance estimates below require regeneration and refitting; do not use them for training recommendations. Original results are retained for audit. See the [clipping correction](clipping_correction/REPORT.md).

# Put-on variance-reduction follow-up

The promising signal survives a larger GPU vec test, but the original 75%
reduction was too optimistic to generalize. With the coefficient frozen from
the CPU pilot, the put-on item head's logit-gradient variance falls by 23%
and 18% in two independent rollout seeds at the 524M checkpoint. It does not
help at the 1B checkpoint. Other tested item heads remain close to unchanged.
No policy weights were updated and no production training code was changed.

## What the correction actually is

For the put-on item-selection head:

```
c = log(mu_verb(put_on | state)) + entropy(mu_verb(. | state))
corrected_advantage = GAE_advantage - alpha * c
item_gradient = corrected_advantage * grad(log(mu_item(chosen_item | state)))
```

The verb distribution includes the configured epsilon mixture. Only the verb
and its item head are consumed for put-on, so the earlier “cross-head” control
is exactly this verb term. Once the verb is fixed, it is a state-dependent
baseline for item choice; it does not depend on which item was sampled.
With the baseline and coefficient detached, its expected contribution to the
unclipped, on-policy item gradient is zero. This is not a proof of equivalence
after inserting it into a clipped PPO surrogate or replay updates.

The simple alternative is a fitted constant baseline for this item head.
Both are fitted by minimizing trace gradient variance on separate data.

## Independent test of the pilot coefficient

The CPU pilot fitted `alpha = 0.1025117033`. The table below applies that
unchanged coefficient to newly collected GPU rollouts. Nothing is fitted to
these test samples. Ratios below 1 reduce variance; intervals are 95% episode
bootstraps. Bootstrapping entire agent streams gives similar intervals.

| Checkpoint | Rollout seed | Put-on selections analysed | Verb-control ratio | 95% interval | Pilot constant-baseline ratio |
| --- | ---: | ---: | ---: | --- | ---: |
| 131M | 31415 | 2,028 | 0.886 | 0.471–0.941 | 0.909 |
| 524M | 31415 | 7,747 | 0.769 | 0.677–0.832 | 0.888 |
| 524M | 27182 | 26,256 | 0.819 | 0.707–0.888 | 1.040 |
| 1000M | 31415 | 34,645 | 1.162 | 1.040–1.527 | 602.707 |

The large late constant-baseline ratio comes from applying an inappropriate
negative offset to many nearly zero advantages. This is a warning against
carrying a fixed early coefficient through training. The verb control adapts
to the state, but carrying its early coefficient also increases late variance.
Both 524M collections use the same policy checkpoint; they are independent
rollout seeds, not independently trained policies.

## Refitting at each checkpoint

Whole agent streams are split into fit and audit halves. The first ratio
below fits on odd agents and audits even agents; the second swaps them.
The decoder column applies the logit-fitted coefficient to gradients of the
put-on query projection, shared item-key projection and its temperature.
It is not a full-network or full-PPO gradient measurement.

| Checkpoint / seed | Logit variance ratios | Decoder parameter variance ratios |
| --- | --- | --- |
| 131M / 31415 | 0.913 / 0.623 | 0.931 / 0.580 |
| 524M / 31415 | 0.748 / 0.744 | 0.745 / 0.755 |
| 524M / 27182 | 0.785 / 0.659 | 0.900 / 0.556 |
| 1000M / 31415 | 0.995 / 0.999 | 0.999 / 0.987 |

Some intervals become wide when uncertainty in the fitted coefficient is
included, especially for decoder gradients. `variance.csv` reports both
fixed-fit and refitted-bootstrap intervals, plus both split directions.
The frozen-pilot test above is the cleaner replication result because it
does not refit on either new sample.

Wear, quaff, zap and read show no comparable improvement. Their fitted
verb-control ratios across the three original checkpoints range from about
0.987 to 1.004, rather than the substantial put-on reductions.

## Why it seems to help

In the early and middle samples, put-on advantages weighted by item-score
norm are negative (approximately -0.88 and -0.59). For unlikely put-on
decisions the centered verb log-probability is also negative. Subtracting a
positive multiple of it therefore removes some of this negative offset from
the item-choice update while leaving the verb update alone.

This is consistent with a value baseline that predicts the usual action mix
better than the consequences of this rare verb. A verb-conditioned baseline
can keep a poor decision about *when* to put something on from adding noise
to learning *which item* to choose. That is an interpretation, not evidence
that any particular ring choice was correct.

At the late checkpoint the score-weighted advantage is approximately zero,
and refitted coefficients are small and negative. There is little benefit
left for this particular control.

## Heavy tails and repeated selections

The original 0.249 pilot ratio came from 114 held-out put-on selections in
97 episodes, with only 23 selections having squared item-score norm above
0.01. Five episodes contributed 89% of baseline squared gradient magnitude.

The larger early sample still has severe outliers. One put-on event accounts
for 77% of baseline squared gradient magnitude. Its value estimate falls
from 61.75 to 7.28125 after a zero-reward action, producing GAE near -55.
That observed TD-error outlier helps explain why the pilot magnitude did not
replicate; this trace alone does not explain the cause of the value change.

At 1B, one episode supplies 29,437 of the 34,645 analysed put-on attempts,
all with zero immediate reward. Counts are therefore not independent sample
sizes. Removing that episode still gives essentially no benefit from
refitting (ratios 0.989 / 0.998), and the old coefficient remains harmful
(ratio 1.253, interval 1.069–1.616). The late null is not solely that episode.

## Collection and numerical checks

- Four frozen captures, 16,777,216 environment steps each: 67,108,864 total.
- Same run, `baseline_s2901`, at steps 131,072,000; 524,288,000; 999,817,216.
- 512 environments, four buffers, 32 CPU threads, horizon 512, BF16 GPU policy.
- Fixed step count rather than an episode-completion stopping rule. Steps
  from unfinished games are retained. Drop a fixed 1,024-step warm-up per
  agent and each horizon's unused final GAE slot.
- GAE uses the training gamma/lambda, terminal convention, BF16 reward and
  advantage storage, and per-horizon bootstrap. These are frozen rollouts
  using the training inference path, not samples from a changing online policy.
- Capture records exact BF16 logits and also computes put-on and verb
  probabilities using the sampler's actual CUDA probability helper.
  Reconstructed probabilities agree within 1.8e-6 in absolute error.
- The sparse hook reproduces all 212,992 smoke-test transitions and logged
  events byte-for-byte against the original collector.
- Unchanged pointer backward kernels were compiled in float and BF16 and
  compared on 512 informative selections per capture. Query and key derivative
  relative errors were below 2.5e-7 in float and 1.3e-5 in BF16. No
  trunk/encoder backward claim is made.
- The conditional expected score-weighted control is zero to numerical
  precision; empirical episode-cluster estimates are consistent with zero.
  The raw scalar control need not average zero after conditioning on put-on.

Source commit: `3719caaaf945025e4e1e59c6556560d2ba9e3d1c`.
Engine commit: `e7f6568568242745a7f7ebd8f730367123522cac`.
Each capture manifest records the checkpoint, binary, source-patch and hook
hashes. The hook and collector live in the isolated experiment checkout.

## Decision

There is a repeatable, modest variance-reduction candidate for the put-on
item head during early/mid training. It is not a general 75% improvement,
and not a demonstrated improvement in score or accessory use. A next online
experiment would need a lagged/adaptive coefficient, correct per-head loss
handling, and a separate check of PPO clipping. These results do not justify
enabling it across all item heads or fixing the pilot coefficient permanently.

## Artifacts

- `captures/puton_{early,middle,late}_s31415/`: sparse events, complete step
  streams, put-on pointer activations, manifests and collection timings.
- `captures/puton_middle_s27182/`: independent middle-checkpoint rollout seed.
- `analysis/puton_*/variance.csv`: per-head results, both split directions,
  fixed-fit and refitted episode-bootstrap intervals.
- `analysis/puton_*/head_*.npz`: per-selection analysis data.
- `analysis/puton_transfer.csv`: frozen pilot-coefficient tests, with episode
  and agent-stream intervals.
- `analysis/puton_*/pointer_kernel_check.json`: actual CUDA backward checks.
- `analysis/puton_late_s31415/without_largest_episode.*`: late sensitivity check.
- `run_puton_capture.py`, `puton_followup.py`, `check_pointer_gradients.py`:
  collection, analysis and numerical audit entry points.
