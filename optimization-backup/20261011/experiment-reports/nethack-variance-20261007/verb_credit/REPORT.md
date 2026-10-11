> **Results invalid for the training objective — missing reward clipping.** Offline reward/GAE/Q targets omitted the trainer’s [-1, 1] reward clamp. Derived critic and variance estimates below require regeneration and refitting; do not use them for training recommendations. Original results are retained for audit. See the [clipping correction](../clipping_correction/REPORT.md).

# Verb-side credit separation: offline study

Policy, trainer and engine were frozen. This study changes only offline gradient estimators and fits auxiliary critics; it does not train or improve an RL policy.

## Main result

**No tested item-luck correction met the gate for online training.** Across freshly fitted 131M/524M/1B critics, the primary decoder-parameter variance ratios for the six priority verbs range from 0.9985 to 1.0024. The second action seed and frozen 524M-to-1B transfer also show no useful reduction. This is a null result for these learned critics and targets, not a proof that all item-dependent variance reduction is impossible.
The blend produces large raw variance reductions but changes the mean gradient. At 1B the existing shared verb critics select their zero predictor: blending then simply multiplies the advantage and its gradient by (1-alpha). Variance falls by (1-alpha)^2 and squared mean falls by the same factor; this supplies no noise-to-signal improvement. For example, late quaff has variance ratio 0.0907 while suppressing its mean gradient by 69.9%.

## Protocol

- One trained policy run (`baseline_s2901`) at 131M, 524M and 1B steps. These are stages of one run, not independent training seeds.
- 16,777,216 fixed environment steps per stage, plus a second action-sampling seed at 524M. Repeated collection adds item keys and verifies existing trajectories; it is not additional independent evidence.
- Source `3719caaaf945025e4e1e59c6556560d2ba9e3d1c`; engine `e7f6568568242745a7f7ebd8f730367123522cac`. Each capture manifest pins checkpoint, binary and logging-source hashes.
- Discard 1,024 warm-up steps per environment and each horizon’s unused final GAE position. Same gamma, lambda, BF16 reward/advantage storage and terminal convention as the previous study. Retain unfinished episodes.
- Fit odd-numbered streams except agent%8==7; choose model checkpoints and coefficients on agent%8==7; audit even streams. No episode/agent crosses these sets. Transfer evaluates even streams too, because dungeon seed schedules overlap across action seeds.
- Item predictor: separate per-verb 1024-d trunk and 16-d candidate key -> summed 64-d preactivations -> ReLU -> 64 -> ReLU -> scalar. This permits state-item interactions. Predict A_GAE; using V+A_GAE is equivalent after item centering. AdamW .001, weight decay .001, batch 512, at most 1,200 updates, early stopping after 300 non-improving updates. Fit-only normalization; zero predictor included. Unweighted seeds 17/29, parameter-score-norm-weighted seed 17, and an additive linear control.
- Fit scalar alpha to verb decoder gradient variance on validation streams. Primary alpha is restricted to [0,1]; a separately reported unrestricted signed coefficient tests calibration. Both parameter-optimal and logit-optimal coefficients are recorded; evaluated estimators use parameter-optimal alpha.
- Blend uses existing state/verb residuals and coefficient beta*s, beta in [0,1], s=n/(n+100), n=validation episodes with nontrivial verb scores. This is a prespecified regularizer, not an unbiasedness guarantee.
- Bootstrap 200 replicates over games and over environment streams. Intervals condition on fitted critics/coefficient selection and are not corrected for multiple comparisons. Signed mean differences are available for every verb-logit component. Norms of estimated differences are positive quantities, not significance tests.
- Exact verb-decoder parameter geometry is the 26x1024 linear weight block (no bias), using the epsilon-adjusted score. It excludes encoder, recurrent, value, entropy, PPO clipping/replay and optimizer effects. Invariance is relative to the unclipped on-policy GAE estimator.
- Prioritize quaff/read/zap/puton/wear/throw. Takeoff/drop serve as diagnostic comparisons. Auxiliary fitting and all predictor inputs use no post-action information.

## Primary centered correction

Fixed model: interaction MSE seed 17, alpha in [0,1]. Ratio 1 means unchanged variance. Parentheses are stream-clustered 95% intervals; these are full-sample decoder-parameter measurements.

### 131M

| Verb | Audit selections / games | Variance ratio (95% CI) | Alpha | Without largest episode |
|---|---:|---:|---:|---:|
| quaff | 18,775 / 3,790 | 0.9985 (0.9952, 1.0001) | 1 | 0.9977 |
| read | 12,142 / 3,078 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| zap | 6,283 / 1,959 | 1.0000 (0.9997, 1.0004) | 1 | 1.0000 |
| puton | 1,018 / 845 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| wear | 38,702 / 5,243 | 1.0012 (0.9997, 1.0040) | 1 | 1.0021 |
| throw | 54,926 / 5,512 | 0.9999 (0.9995, 1.0001) | 1 | 0.9998 |
| takeoff | 8,122 / 3,333 | 1.0012 (1.0002, 1.0028) | 1 | 1.0016 |
| drop | 21,109 / 4,940 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |

### 524M

| Verb | Audit selections / games | Variance ratio (95% CI) | Alpha | Without largest episode |
|---|---:|---:|---:|---:|
| quaff | 13,127 / 2,308 | 1.0000 (1.0000, 1.0005) | 1 | 1.0002 |
| read | 36,025 / 2,192 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| zap | 5,922 / 1,526 | 1.0019 (0.9994, 1.0061) | 0.232 | 1.0021 |
| puton | 4,728 / 816 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| wear | 92,426 / 3,119 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| throw | 52,990 / 3,103 | 1.0024 (0.9993, 1.0054) | 1 | 1.0022 |
| takeoff | 12,310 / 2,006 | 0.9997 (0.9989, 1.0002) | 1 | 0.9996 |
| drop | 21,135 / 2,671 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |

### 1B

| Verb | Audit selections / games | Variance ratio (95% CI) | Alpha | Without largest episode |
|---|---:|---:|---:|---:|
| quaff | 12,975 / 1,438 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| read | 11,977 / 1,286 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| zap | 11,228 / 1,184 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| puton | 31,910 / 166 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| wear | 42,583 / 2,310 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| throw | 47,508 / 2,347 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| takeoff | 9,927 / 983 | 0.9995 (0.9974, 1.0009) | 1 | 0.9993 |
| drop | 25,185 / 2,072 | 0.9997 (0.9988, 1.0010) | 1 | 1.0002 |

## Transfer without refitting

The item predictor, fit normalization and validation coefficient remain frozen. The item expectation is recomputed using the target checkpoint’s actual probabilities and masks. The 524M-to-1B test includes feature-representation drift as well as policy drift; it is more severe than a short online critic lag.

### Second action seed at 524M

| Verb | Audit selections / games | Variance ratio (95% CI) | Alpha | Without largest episode |
|---|---:|---:|---:|---:|
| quaff | 16,978 / 2,351 | 1.0000 (0.9998, 1.0002) | 1 | 1.0000 |
| read | 34,015 / 2,203 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| zap | 5,893 / 1,507 | 1.0000 (0.9991, 1.0011) | 0.232 | 1.0000 |
| puton | 12,034 / 804 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| wear | 116,726 / 3,172 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| throw | 51,640 / 3,098 | 1.0013 (0.9993, 1.0040) | 1 | 1.0013 |
| takeoff | 8,909 / 2,003 | 1.0011 (0.9998, 1.0026) | 1 | 1.0012 |
| drop | 20,857 / 2,669 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |

### 524M critic on the 1B policy

| Verb | Audit selections / games | Variance ratio (95% CI) | Alpha | Without largest episode |
|---|---:|---:|---:|---:|
| quaff | 12,975 / 1,438 | 1.0000 (0.9999, 1.0002) | 1 | 1.0001 |
| read | 11,977 / 1,286 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| zap | 11,228 / 1,184 | 0.9999 (0.9991, 1.0006) | 0.232 | 0.9999 |
| puton | 31,910 / 166 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| wear | 42,583 / 2,310 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |
| throw | 47,508 / 2,347 | 0.9972 (0.9931, 1.0011) | 1 | 0.9971 |
| takeoff | 9,927 / 983 | 0.9999 (0.9990, 1.0008) | 1 | 0.9998 |
| drop | 25,185 / 2,072 | 1.0000 (1.0000, 1.0000) | 0 | 1.0000 |

## Blend: variance and mean-gradient change

The table gives estimated norm(mean corrected gradient - mean original gradient) / norm(mean original gradient). Large percentages do not by themselves establish statistical significance. Componentwise game/stream intervals are in bias_components.csv.

| Stage | Verb | Variance ratio | Estimated mean-gradient change | Chosen-logit signed change (stream 95% CI) |
|---|---|---:|---:|---|
| early | wear | 0.009 | 256.7% | 0.01244 (0.004061, 0.01903) |
| early | quaff | 0.028 | 81.1% | -0.08833 (-0.1498, -0.04169) |
| early | throw | 0.052 | 111.4% | -0.0004022 (-0.001925, 0.001382) |
| early | zap | 0.151 | 317.5% | 0.02016 (-0.0049, 0.04327) |
| early | puton | 0.407 | 34.2% | 0.01246 (0.00568, 0.0182) |
| early | read | 0.028 | 181.3% | 0.02997 (0.01759, 0.04401) |
| middle | wear | 0.022 | 117.3% | -0.002742 (-0.006898, 0.0009093) |
| middle | quaff | 0.043 | 63.8% | -0.02845 (-0.2236, 0.113) |
| middle | throw | 0.026 | 430.2% | 0.005818 (0.004312, 0.007563) |
| middle | zap | 0.106 | 58.7% | -0.01682 (-0.03733, -0.0008244) |
| middle | puton | 0.260 | 72.0% | -0.008412 (-0.02406, -0.0009165) |
| middle | read | 0.041 | 109.3% | -0.02106 (-0.04742, -0.008741) |
| late | wear | 0.026 | 84.0% | 0.01244 (0.005922, 0.01774) |
| late | quaff | 0.091 | 69.9% | -0.2959 (-0.8096, -0.09643) |
| late | throw | 0.029 | 82.9% | 0.0005872 (-0.0008183, 0.002276) |
| late | zap | 0.072 | 73.1% | -0.004831 (-0.01795, 0.008311) |
| late | puton | 0.557 | 25.4% | 0.0001046 (-0.0003431, 0.004338) |
| late | read | 0.060 | 75.6% | -0.0001073 (-0.02685, 0.0251) |

## Controls, limitations and decision

- Additive, second-initialization, weighted and unrestricted-alpha results are all retained in all_results.csv. No method is selected based on its audit performance.
- The unrestricted signed-alpha comparison was added as an exploratory calibration diagnostic after the first middle bounded audit. It did not rescue the result and is not used to select the primary method.
- Raw column advantage_r2 is the squared association between the fixed predicted control and advantage on audit data, not an oracle ceiling or cross-validated R-squared. advantage_explained.csv instead reports 1 - Var(A-alpha*c)/Var(A) for the validation-fitted coefficient, with game/stream intervals.
- The centered correction has zero conditional expectation by construction even for an inaccurate critic. Numerical centering checks and empirical signed gradient shifts supplement that identity. Accuracy determines variance reduction, not this guarantee.
- Near-deterministic item distributions leave little item-selection randomness to remove. Conversely a null result can reflect weak counterfactual prediction from the saved representations. This experiment does not establish an oracle ceiling or prove that items do not affect outcomes.
- The target is short-lambda GAE, not an independently measured long-horizon causal effect of item use. Item-only predictors marginalize over directions; direction-interaction critics are a follow-up if a promising item signal appears.
- A useful candidate must replicate a parameter ratio <=0.9 with an interval excluding 1 on a priority verb, remain robust to large episodes, and have acceptable overhead. Offline gradient variance alone does not demonstrate improved learning.
- No online run has been launched.

## Artifacts

- `PLAN.md`: protocol and declared comparisons.
- `toy.json`, `checks.json`: exact identities, moment checks and parameter-gradient checks.
- `all_results.csv`: all methods, checkpoints, transfers, both gradient spaces and both clustering schemes.
- `bias_components.csv`: mean-gradient differences for every verb-logit coordinate.
- `rarity.csv`: counts, action frequency, entropy and advantage scales.
- Per-capture directories: fitted auxiliary models, predictions, coefficients and bootstrap samples.
- `*_trajectory_check.json`: original/expanded logs match byte for byte.
- Capture manifests and raw records: `../captures/credit_*`.

## Combined verb and selected-item decoder blocks

At 524M, combine the primary verb correction with a separately validation-scaled existing MLP argument baseline. These parameter blocks are disjoint, so their variance traces add. Shared-trunk covariance is not measured. Intervals use the same clustered resampling for both blocks.

| Verb | Argument baseline only | Verb correction only | Both (stream 95% CI) |
|---|---:|---:|---:|
| quaff | 0.9998 | 1.0000 | 0.9999 (0.9967, 1.0001) |
| read | 0.9991 | 1.0000 | 0.9991 (0.9979, 0.9997) |
| zap | 0.9970 | 1.0017 | 0.9986 (0.9897, 1.0052) |
| puton | 0.9347 | 1.0000 | 0.9347 (0.8355, 0.9791) |
| wear | 0.9997 | 1.0000 | 0.9997 (0.9988, 1.0002) |
| throw | 1.0000 | 1.0018 | 1.0018 (0.9995, 1.0041) |
| takeoff | 0.9693 | 0.9997 | 0.9690 (0.9505, 0.9817) |
| drop | 0.9750 | 1.0000 | 0.9750 (0.9473, 0.9864) |

The earlier argument-side benefit remains distinct from the new verb-side null. On this split, takeoff/drop combined improvements come almost entirely from the argument baseline.

## Frequency-weighted aggregate over covered verbs

These point estimates combine the full verb-gradient vectors with the natural verb frequencies in audit streams. They include between-verb mean effects. The eight covered verbs account for only about 7–8% of environment steps; this is not full-policy or full-PPO variance.

| Stage | Covered step fraction | Primary parameter variance ratio |
|---|---:|---:|
| credit_early_s31415 | 7.50% | 0.999221 |
| credit_middle_s31415 | 8.28% | 1.000029 |
| credit_late_s31415 | 7.40% | 0.999993 |
