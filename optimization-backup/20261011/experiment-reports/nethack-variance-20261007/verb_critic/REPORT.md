> **Results invalid for the training objective — missing reward clipping.** Offline reward/GAE/Q targets omitted the trainer’s [-1, 1] reward clamp. Derived critic and variance estimates below require regeneration and refitting; do not use them for training recommendations. Original results are retained for audit. See the [clipping correction](../clipping_correction/REPORT.md).

# Verb-conditioned baselines: offline investigation

The learned baseline has a real but selective signal. **Drop is the clearest
candidate**: the improvement repeats across middle-checkpoint rollout seeds
and survives a full decoder-parameter-gradient check. Take-off also repeats in
logit space, with a smaller parameter-space benefit. Put-on remains sensitive
to the rollout sample, critic fit and gradient geometry. These results do not
support applying an unscaled learned baseline to every argument head.

No RL policy or production training code was updated. Critic fits are offline
supervised experiments on detached recurrent features. No claim of improved
score, item use, sample efficiency or wall-clock learning is made.

## Scope and measurement

- Same trained policy run, `baseline_s2901`, at 131,072,000, 524,288,000 and
  999,817,216 training steps. These are learning stages, not independent
  training seeds, and "late" here means approximately 1B rather than 4B.
- Four unique frozen rollout streams: 16,777,216 steps per checkpoint with
  rollout seed 31415, plus a second 524M stream with seed 27182. Total:
  **67,108,864 steps**. Repeating those streams to add logging does not add
  independent evidence.
- 16 argument-consuming verbs; 20 verb/head contexts covering all 19 argument
  heads (zap and cast share a direction head). Argument-free verbs have no
  argument-gradient baseline to change.
- Fixed-step sampling retains unfinished episodes. Drop 1,024 warm-up steps
  per agent and the unused final GAE slot of each 512-step horizon. Keep the
  training gamma 0.999207735, lambda 0.484387815, terminal convention and BF16
  reward/advantage storage.
- Common verbs are hash-thinned independently of their outcomes: move/run
  and argument-free verbs 1/64, throw 1/8, eat/drop 1/4; other argument verbs
  retain every event. Complete lightweight streams provide GAE and frequency.
- Fit on 192 complete environment streams; validate on 64; audit on the
  other 256. No episode crosses those splits. Transfer uses all 512 streams
  from seed 27182 without refitting. Rollout seeds change action sampling;
  the indexed dungeon-seed schedule is shared, so this is not independent
  dungeon selection or an independent trained policy.

The reported ratio is trace Var[(A-b) grad log mu_head] divided by the same
quantity with plain GAE. Below one is less variance. It is conditional on the
verb being used. This is **not** the variance of the complete shared-trunk PPO
update, which also includes verb/value/entropy gradients, minibatch temporal
correlations, clipping and replay.

## Estimators tested

The proposed baseline is expressed as a residual:

```
Delta(s,v) predicts E[A_GAE | recurrent_state=s, chosen_verb=v]
Q(s,v) = V(s) + Delta(s,v)
verb advantage = A_GAE
argument advantage = A_GAE - stop_gradient(Delta(s,v))
```

Thus its supervised return target is V + A_GAE, using the same convention as
the original critic. It never sees the chosen item or direction as an input.

Comparators include a verb mean, a constant fitted to gradient variance, the
earlier centered verb-logprob control, a 26-output linear residual, a shared
1024→128→26 ReLU residual (two initialization seeds), and the same MLP trained
with squared logit-score norm weighting. The weighted version targets the
sum of consumed argument-gradient second moments; it is not necessarily
optimal for each individual head or for parameter gradients.

Independent 128-unit critics per verb test whether shared fitting compromises
rare verbs. They have substantially more total capacity than one shared head.
A state-only residual is also tested. Its main control restores natural verb
frequencies with inverse logging-probability weights; an earlier verb-balanced
state-only control is retained in the CSVs but is not a fair ordinary-value
comparison because balancing changes its conditional target mixture.

All learned fits start at zero. AdamW lr .001, weight decay .001, 256 samples
per fitted verb per update, up to 1,500 updates, validation every 50, and 400
updates without improvement for early stopping. Separate per-verb fits also
validate at updates 5, 10 and 20. The zero predictor is a validation candidate:
a ratio of exactly one often means validation rejected the learned correction.
Conditional models use verb-balanced, per-verb RMS-scaled MSE. No gradients
flow into the policy's trunk. Baseline coefficients are one unless labelled
`_cal`: those use validation-only per-verb shrinkage to [0,1], also keeping
zero as an option. Audit results never select weights or shrinkage.

## Replication at the middle checkpoint

This table uses one prespecified shared MLP initialization (17), with no
per-verb cherry-picking. Parentheses are 95% **agent-stream** bootstrap
intervals on the second rollout seed, conditional on the fitted critic.

| Argument | First audit ratio | Second-seed logit ratio | Full second-seed decoder ratio |
| --- | ---: | --- | --- |
| takeoff item | 0.756 | 0.870 (0.825–0.906) | 0.953 (0.816–0.988) |
| puton item | 0.991 | 0.721 (0.533–0.872) | 0.880 (0.503–0.988) |
| drop item | 0.827 | 0.879 (0.731–0.943) | 0.848 (0.788–0.898) |

The second shared-MLP initialization is also in the raw tables; take-off and
drop replicate in logit space with it. Take-off's parameter interval for that
initialization includes one, so its parameter-space evidence is weaker than
drop's. Put-on's first split gives little improvement without shrinkage,
despite a favourable second seed. The old scalar control remains competitive
for put-on and is simpler than a learned critic.

The original small linear head is worth separating from the larger MLP:

| Argument | Linear, first audit | Linear, second seed | Linear, full decoder |
| --- | ---: | ---: | ---: |
| takeoff item | 0.817 | 0.905 | 0.981 |
| puton item | 0.958 | 0.977 | 0.981 |
| drop item | 0.826 | 0.885 | 0.854 |

The full parameter check uses every recorded take-off (21,555), put-on
(26,256) and drop (41,508) selection in the second seed. It covers each query
projection, the shared inventory-key projection, and pointer temperature.
It excludes encoder/recurrent/other-head gradients and optimizer effects.
A preliminary 512-selection check was too unstable for put-on and is retained
as `parameter_check.csv`; the full check supersedes it for conclusions.

## Results by learning stage

These tables use a fixed initialization, not the best model for each cell.
`Linear` is the simple 26-output head. `Q` is the shared MLP, `Weighted Q`
weights its loss by summed argument score norm, and `Separate` trains an
independent weighted critic for each verb. All are unshrunk. Full intervals,
both MLP seeds, constants, state-only controls and shrinkage are in
`all_results.csv`.

### 131M steps

| Argument | Audit selections | Verb control | Linear | Q | Weighted Q | Separate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| move direction | 25,393 | 1.001 | 1.000 | 0.942 | 0.985 | 0.999 |
| run direction | 27,362 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| kick direction | 69,665 | 0.978 | 1.000 | 0.958 | 0.975 | 0.989 |
| wear item | 38,702 | 0.996 | 1.000 | 0.996 | 1.003 | 1.002 |
| eat item | 29,117 | 0.997 | 1.000 | 0.991 | 0.989 | 0.988 |
| quaff item | 18,775 | 1.003 | 1.000 | 1.015 | 0.999 | 0.994 |
| throw item | 54,926 | 1.000 | 1.000 | 0.986 | 0.992 | 0.982 |
| throw direction | 54,926 | 0.998 | 1.000 | 0.982 | 0.994 | 0.993 |
| zap item | 6,283 | 0.995 | 1.000 | 1.057 | 1.028 | 1.034 |
| zap direction | 6,283 | 0.977 | 1.000 | 0.980 | 0.977 | 0.958 |
| takeoff item | 8,122 | 0.947 | 1.000 | 0.848 | 0.972 | 0.934 |
| puton item | 1,018 | 0.910 | 1.000 | 0.902 | 0.923 | 0.921 |
| remove item | 698 | 1.047 | 1.000 | 1.045 | 1.024 | 1.000 |
| wield item | 22,514 | 0.942 | 1.000 | 0.937 | 1.062 | 0.937 |
| apply item | 9,373 | 0.952 | 1.000 | 1.046 | 0.964 | 0.961 |
| apply direction | 9,373 | 0.967 | 1.000 | 1.066 | 0.972 | 0.958 |
| read item | 12,142 | 0.995 | 1.000 | 1.001 | 0.993 | 0.992 |
| drop item | 21,109 | 1.000 | 1.000 | 0.981 | 0.995 | 0.983 |
| cast direction | 51,285 | 0.992 | 1.000 | 1.042 | 0.985 | 0.957 |
| cast spell | 51,285 | 0.967 | 1.000 | 1.007 | 0.924 | 0.978 |

### 524M steps

| Argument | Audit selections | Verb control | Linear | Q | Weighted Q | Separate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| move direction | 29,244 | 1.001 | 1.080 | 1.012 | 1.007 | 1.000 |
| run direction | 20,278 | 1.000 | 1.043 | 0.999 | 1.034 | 1.000 |
| kick direction | 40,706 | 0.980 | 1.008 | 0.996 | 0.982 | 0.974 |
| wear item | 92,426 | 0.998 | 1.011 | 0.993 | 0.995 | 0.993 |
| eat item | 47,601 | 0.994 | 1.017 | 0.998 | 0.996 | 1.000 |
| quaff item | 13,127 | 1.000 | 1.001 | 0.993 | 0.997 | 0.990 |
| throw item | 52,990 | 1.000 | 1.028 | 1.007 | 1.000 | 1.000 |
| throw direction | 52,990 | 1.002 | 1.030 | 1.030 | 0.986 | 1.000 |
| zap item | 5,922 | 0.994 | 1.045 | 1.005 | 1.032 | 0.998 |
| zap direction | 5,922 | 0.988 | 1.003 | 0.977 | 0.974 | 1.005 |
| takeoff item | 12,310 | 0.817 | 0.817 | 0.756 | 0.863 | 0.867 |
| puton item | 4,728 | 0.801 | 0.958 | 0.991 | 1.358 | 1.000 |
| remove item | 1,512 | 1.027 | 9.061 | 2.196 | 1.112 | 1.000 |
| wield item | 21,856 | 0.927 | 0.979 | 0.971 | 1.078 | 0.920 |
| apply item | 9,378 | 1.003 | 1.113 | 1.026 | 1.044 | 0.995 |
| apply direction | 9,378 | 1.003 | 1.140 | 1.020 | 1.068 | 0.995 |
| read item | 36,025 | 1.000 | 0.999 | 1.000 | 1.000 | 1.000 |
| drop item | 21,135 | 1.000 | 0.826 | 0.827 | 0.831 | 0.831 |
| cast direction | 35,966 | 0.978 | 1.042 | 1.004 | 1.000 | 0.970 |
| cast spell | 35,966 | 0.974 | 1.023 | 1.004 | 1.065 | 0.975 |

### 1B steps

| Argument | Audit selections | Verb control | Linear | Q | Weighted Q | Separate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| move direction | 36,921 | 1.000 | 1.000 | 1.000 | 1.002 | 1.000 |
| run direction | 12,939 | 1.000 | 1.000 | 1.000 | 1.015 | 1.000 |
| kick direction | 23,637 | 1.000 | 1.000 | 1.000 | 0.974 | 0.934 |
| wear item | 42,583 | 0.999 | 1.000 | 1.000 | 1.110 | 0.998 |
| eat item | 51,118 | 1.000 | 1.000 | 1.000 | 1.003 | 1.000 |
| quaff item | 12,975 | 1.000 | 1.000 | 1.000 | 1.064 | 1.000 |
| throw item | 47,508 | 1.000 | 1.000 | 1.000 | 1.003 | 1.001 |
| throw direction | 47,508 | 0.997 | 1.000 | 1.000 | 0.990 | 1.022 |
| zap item | 11,228 | 0.999 | 1.000 | 1.000 | 1.010 | 1.000 |
| zap direction | 11,228 | 1.000 | 1.000 | 1.000 | 1.015 | 1.000 |
| takeoff item | 9,927 | 1.000 | 1.000 | 1.000 | 1.042 | 0.958 |
| puton item | 31,910 | 0.996 | 1.000 | 1.000 | 1.508 | 1.000 |
| remove item | 1,750 | 1.015 | 1.000 | 1.000 | 1.057 | 1.000 |
| wield item | 13,089 | 1.000 | 1.000 | 1.000 | 0.965 | 0.962 |
| apply item | 6,457 | 1.000 | 1.000 | 1.000 | 1.077 | 1.014 |
| apply direction | 6,457 | 1.000 | 1.000 | 1.000 | 0.977 | 0.994 |
| read item | 11,977 | 1.000 | 1.000 | 1.000 | 1.004 | 1.000 |
| drop item | 25,185 | 1.000 | 1.000 | 1.000 | 0.880 | 0.877 |
| cast direction | 30,602 | 1.002 | 1.000 | 1.000 | 1.028 | 1.000 |
| cast spell | 30,602 | 1.003 | 1.000 | 1.000 | 1.105 | 1.000 |

## Rarity and effective evidence

Frequency is measured from all unthinned, retained steps, not the thinned
feature sample. These are action selections, not successful item effects.

| Verb | 131M frequency | 524M frequency | 1B frequency |
| --- | ---: | ---: | ---: |
| move | 20.223% | 23.237% | 29.201% |
| run | 21.721% | 15.770% | 10.193% |
| kick | 0.868% | 0.478% | 0.331% |
| wear | 0.477% | 1.114% | 0.533% |
| eat | 1.422% | 2.331% | 2.516% |
| quaff | 0.213% | 0.181% | 0.116% |
| throw | 5.356% | 5.179% | 4.641% |
| zap | 0.078% | 0.075% | 0.134% |
| takeoff | 0.103% | 0.137% | 0.271% |
| puton | 0.013% | 0.048% | 0.214% |
| remove | 0.008% | 0.017% | 0.020% |
| wield | 0.273% | 0.401% | 0.161% |
| apply | 0.111% | 0.126% | 0.059% |
| read | 0.163% | 0.341% | 0.129% |
| drop | 1.017% | 1.029% | 1.239% |
| cast | 0.628% | 0.441% | 0.379% |

Rarity alone does not predict the benefit. Take-off and drop improve midway
through training, while rare read/quaff/zap item heads are mostly unchanged.
Movement has a modest early signal but no comparable middle/late signal.
Separate critics do not reveal a universal hidden win: shared fitting is not
the sole limitation. At 1B, independent weighted drop retains a roughly 12%
logit reduction, but that late result has not been replicated on another
rollout seed or checked in full parameter space.

Counts can be misleading. One late episode supplies 29,437 put-on attempts,
and 92% of put-on selections in its audit half. The early put-on audit has
1,018 selections but only 187 with squared score norm above .01. Its largest
gradient-mass episode contributes 83% of the second moment. Early take-off is
also outlier-sensitive: removing its largest baseline-gradient episode changes
the shared MLP ratio from 0.848 to 1.597. The middle take-off and drop gains
survive their corresponding leave-one-episode-out check (0.726 and 0.792).

One early run-direction episode contributes over 99.8% of that head's audit
squared-gradient mass. A recorded reward of 2,695.6 yields a nearby BF16 GAE
of 1,304. The trace establishes the large reward, not its precise game cause.
This makes an overall early variance-reduction number especially unstable.
Frequency-weighted aggregate argument-logit improvements are around 1% or
less for the tested shared critics; individual-head gains are not equivalent
to comparable improvement in the complete PPO update.

## Why richer critics are not automatically safer

MSE predicts typical returns; gradient variance weights prediction errors by
the action score's magnitude and, in parameter space, its Jacobian. Improving
one objective need not improve the other. One shared verb baseline can help
an item's head and hurt that verb's direction head. Score-norm weighting
helps some cases but remains sensitive to outliers and the geometry used.

The original five-verb fit produced a late put-on variance ratio of 62.5 for
one MLP initialization. The broader shared fit's validation instead selected
zero at that checkpoint. An independent late put-on MSE critic still produced
a 21.8 ratio; validation-only shrinkage disabled it. These are recorded
failures, not evidence that zero or shrinkage always protects unseen states.
Separate data, calibration and allowing no correction are necessary controls.

The likely useful mechanism is removing a predictable state/verb-specific
offset from the argument update. It does **not** change the expected verb
update or directly teach the policy to use rings or scrolls. These fits do
not establish a noise ceiling: failure of these finite critics on current
trunk features is not proof that no better baseline exists.

## Correctness and limits

- Exact masked/epsilon-mixture toy enumeration preserves the expected
  argument gradient. Applying the verb-dependent baseline to the verb gradient
  fails the same test, as expected. Existing score/GAE arrays match the previous
  analysis; maximum float32 score-storage error is below 3e-8.
- New lightweight step streams are byte-identical to prior same-seed streams.
  Additional pointer logging passed a separate byte-identical smoke check.
- Unchanged production CUDA pointer-backward kernels were checked in float
  and BF16 for all three parameter-audit heads. Largest relative discrepancies
  were below 2e-7 and 9e-6 respectively. The full parameter-moment computation
  agrees with explicitly constructed gradients in an independent toy test.
- Intervals bootstrap 400 sets of whole episodes and whole agent streams
  (200 for full parameter gradients). They condition on the fitted critic;
  they do not include all fitting uncertainty or adjust for testing many
  heads/methods. Two shared-model initializations and a held-out rollout seed
  give partial replication, not independent training-seed confirmation.
- Baseline unbiasedness here means preserving the **existing unclipped,
  on-policy GAE estimator**. It does not remove GAE's own approximation error,
  nor establish equivalence after PPO clipping, advantage transformations,
  replay or changing the shared-trunk loss. A custom per-head PPO objective
  requires its own derivation and tests; the current scalar multiplier cannot
  simply be replaced by different advantages without deciding that objective.

## Decision

Do not enable a blanket learned-Q subtraction across the decoder. The clearest
next controlled test is a lagged, detached residual for **drop**, with
**take-off** as a secondary candidate and **put-on** as a guarded comparison
to the simpler scalar control. Keep the verb objective unchanged. Validate
per-head clipping/importance weighting before any policy training, allow the
correction to shrink to zero, and test early/middle/late performance separately.
Rare scroll and wand use currently has no strong evidence of being fixed by
this class of baselines. A substantial reduction in one head's noise is not
yet evidence of better exploration or behaviour.

## Sources and artifacts

Conditioning an argument baseline on other action factors follows
[Wu et al., 2018](https://arxiv.org/abs/1803.07246). The distinction between
value prediction and optimal variance baselines is discussed by
[Greensmith et al., 2004](https://jmlr.org/papers/v5/greensmith04a.html).
[Tucker et al., 2018](https://proceedings.mlr.press/v80/tucker18a.html) motivates
checking actual gradient variance and implementation details rather than
assuming a learned action-conditioned baseline must help. Those papers do not
establish our NetHack results; the recorded experiments above do.

Pinned policy/trainer source: `3719caaaf945025e4e1e59c6556560d2ba9e3d1c`.
Engine: `e7f6568568242745a7f7ebd8f730367123522cac`.
Every capture manifest includes checkpoint and collector hashes. Source
instrumentation is confined to the scratch checkout. Production changes that
already existed in drone files and `ocean/nethack/depth.ini` were left alone.

- `all_results.csv`: all methods, heads, stages and confidence intervals.
- `rarity.csv`, `concentration.csv`, `sensitivity.csv`: event frequencies,
  episode concentration, leave-one-game-out ratios and correction-mean checks.
- `allverbs_middle_s27182/transfer_from_allverbs_middle_s31415.csv`:
  frozen-critic replication across rollout seeds.
- `parameter_full.csv`: full replication-set decoder parameter ratios and
  intervals. `parameter_check.csv` is the preliminary small subset only.
- `checks.json`, `parameter_kernel_check.json`, `parameter_moment_check.json`:
  mathematical, alignment and numerical checks.
- `variance_by_verb.png`: three-stage comparison (raw ratios, not significance).
- Per-capture `.pt` files, fit `.json` logs, predictions and validation
  shrinkage coefficients permit reproduction without retraining the policy.
- `../verb_critic.py`, `../verb_critic_summary.py`,
  `../verb_critic_parameter_check.py`, `../verb_critic_plan.md`: implementation
  and the prospectively recorded plan and scope extensions.
