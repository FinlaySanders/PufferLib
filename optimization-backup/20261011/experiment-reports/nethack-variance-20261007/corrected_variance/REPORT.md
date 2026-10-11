# Corrected NetHack variance-reduction study

**The old unclipped-target results are superseded.** The corrected primary fits show a reproducible middle-stage benefit for take-off arguments, a larger but less consistent put-on effect, and no substantial drop benefit. These benefits are stage-dependent; fresh 1B state fits often choose zero. Verb-side item-luck subtraction does not produce a replicated large reduction with the tested predictors.

## What was corrected and verified

- The trainer clips total BF16 rewards to [-1, 1] before GAE. The old analysis omitted this.
- Targets now come directly from the unchanged pinned production clamp/GAE kernels. A separately indexed scalar CUDA recurrence matches BF16 advantages and returns bit for bit on synthetic edge cases and every stream: **67,108,864 captured transitions**.
- Verified reward/action alignment, next-slot terminal handling, horizon boundaries, BF16 rounding and importance clipping. GAE gamma .999207735, lambda .484387815, horizon 512. Evaluation captures use on-policy importance=1. The existing combined-done convention is preserved.
- All auxiliary models and coefficients were refitted. No old targets or fitted critics were reused. Exact logged CUDA sampling probabilities replace the previous recomputed approximations (maximum change below 4e-6). Policy parameters and production code are unchanged.
- 144 corrected-target derivative checks passed against the pinned source pointer backward kernels in float and BF16; the full parameter-covariance accumulator also matches an independent dense calculation. Item-score identities and item-Q centering are checked analytically per state. Finite-sample correction-gradient means and game-bootstrap intervals are in a separate CSV.

The raw polymorph and potion events still happened, but both large rewards are +1 during training. The corrected immediate-reward contribution to overall TD variance is 2.7–2.8%, not 79–91%. The bootstrap term dominates this descriptive accounting; that does not prove it is erroneous.

## Design and interpretation

Three checkpoints from training run baseline_s2901: 131M, 524M and approximately 1B steps. Each capture has 512 agents × 32,768 actions; the middle checkpoint has two action seeds. Discard 1,024 warmup steps per agent and each horizon’s final action; retain unfinished games. Fit/validation/audit use 192/64/256 disjoint whole environment streams. Across action seeds and stages, keep stream identities disjoint from fitting. The two action seeds share the dungeon-seed schedule; these are not independent RL training seeds.

Auxiliary state baseline: two 64-unit hidden layers per verb. Item predictors use the same trunk plus 16-dimensional item keys, trained either to predict the chosen-item GAE residual or directly to predict its within-policy centered part. Train with AdamW .001, weight decay .001, at most 1,500 updates, validation early stopping after 300 updates without improvement. Primary auxiliary seed 17; repeat middle fits with seed 29. Gradient-norm-weighted state fits are a separately reported secondary control.

For an argument head, subtract a baseline depending only on state and the chosen verb. For the verb head, subtract Q(item_chosen) minus its expectation over the actual item policy. Both have the required zero-expected-gradient identity for the head they correct. Coefficients in [0,1] are selected on source validation streams using full decoder-gradient variance, then frozen during transfer. Per-verb mean and gradient-optimal constants use the same validation split.

**Ratios below are full decoder-block gradient variance relative to ordinary GAE; lower is better.** Brackets show 95% whole-stream bootstrap intervals. Raw CSVs also include whole-game intervals, logit-space results, fitted coefficients and largest-game removal. Bootstrap intervals are conditional on fitted auxiliary models, with no multiple-testing correction. Shared recurrent/encoder gradients, PPO replay/clipping, entropy/value losses and optimizer effects are outside these measurements.

## Primary middle-stage replication

Same baseline fitted on action seed 31415, evaluated on held-out streams from both action seeds.

| Verb | First audit | Second action seed | Second optimal constant | Second weighted state |
|---|---|---|---:|---|
| wear | 0.997 [0.995, 0.999] | 0.998 [0.996, 0.999] | 1.017 | 0.995 [0.960, 1.035] |
| eat | 0.991 [0.987, 0.995] | 0.994 [0.992, 0.998] | 1.000 | 0.990 [0.984, 1.004] |
| quaff | 0.987 [0.978, 0.992] | 0.991 [0.985, 0.995] | 0.988 | 0.998 [0.964, 1.018] |
| throw | 0.997 [0.993, 1.001] | 0.995 [0.991, 0.998] | 0.991 | 0.993 [0.988, 0.996] |
| zap | 0.967 [0.929, 1.009] | 1.013 [0.969, 1.063] | 1.050 | 1.000 [1.000, 1.000] |
| takeoff | 0.707 [0.599, 0.895] | 0.854 [0.772, 0.909] | 0.913 | 0.887 [0.770, 1.065] |
| puton | 0.568 [0.346, 0.808] | 0.920 [0.466, 0.942] | 0.978 | 0.968 [0.745, 0.979] |
| remove | 1.043 [0.979, 1.067] | 1.011 [0.970, 1.091] | 1.697 | 1.000 [1.000, 1.000] |
| wield | 0.982 [0.976, 0.986] | 0.983 [0.975, 0.989] | 1.032 | 0.921 [0.835, 1.047] |
| apply | 0.985 [0.943, 1.010] | 0.996 [0.972, 1.010] | 1.000 | 0.993 [0.986, 0.996] |
| read | 0.971 [0.949, 0.999] | 0.978 [0.962, 0.998] | 0.999 | 0.987 [0.959, 1.021] |
| drop | 0.997 [0.995, 0.999] | 0.997 [0.994, 0.998] | 0.995 | 1.000 [1.000, 1.000] |

## Each checkpoint with fresh fits

The second middle capture below is also freshly fitted on its own training/validation streams. It complements, rather than replaces, the frozen-model replication above. Verb-Q columns are ordinary item-Q and direct-centered item-Q controls for the **verb** head.

### 131M

| Verb | Audit choices / games | State baseline | Weighted state | Optimal constant | Verb Q | Verb centered Q |
|---|---:|---|---|---:|---:|---:|
| wear | 38702 / 5243 | 1.004 [0.887, 1.111] | 0.992 [0.920, 1.050] | 0.990 | 1.001 | 1.001 |
| eat | 29117 / 5855 | 0.985 [0.972, 0.991] | 1.000 [0.972, 1.037] | 1.005 | 1.000 | 1.000 |
| quaff | 18775 / 3790 | 0.962 [0.939, 0.977] | 0.976 [0.962, 0.985] | 0.981 | 1.000 | 1.000 |
| throw | 54926 / 5512 | 0.990 [0.982, 0.995] | 0.976 [0.960, 0.994] | 0.999 | 1.000 | 1.000 |
| zap | 6283 / 1959 | 0.980 [0.961, 0.991] | 0.988 [0.973, 0.998] | 0.987 | 1.000 | 1.000 |
| takeoff | 8122 / 3333 | 0.903 [0.754, 0.921] | 0.940 [0.781, 0.959] | 0.980 | 1.002 | 1.000 |
| puton | 1018 / 845 | 0.910 [0.477, 0.937] | 0.914 [0.477, 0.941] | 0.957 | 1.000 | 1.000 |
| remove | 698 / 533 | 1.000 [1.000, 1.000] | 1.099 [0.268, 1.425] | 4.686 | 1.000 | 1.054 |
| wield | 22514 / 5240 | 0.937 [0.874, 0.984] | 1.078 [0.925, 1.367] | 0.890 | 0.998 | 0.963 |
| apply | 9373 / 2254 | 0.929 [0.887, 0.969] | 0.942 [0.909, 0.972] | 0.971 | 1.000 | 1.000 |
| read | 12142 / 3078 | 0.990 [0.977, 1.004] | 0.993 [0.983, 1.001] | 0.998 | 1.000 | 1.000 |
| drop | 21109 / 4940 | 0.989 [0.984, 0.993] | 0.977 [0.933, 1.039] | 0.987 | 1.000 | 1.000 |

### 524M, action seed 31415

| Verb | Audit choices / games | State baseline | Weighted state | Optimal constant | Verb Q | Verb centered Q |
|---|---:|---|---|---:|---:|---:|
| wear | 92426 / 3119 | 0.997 [0.995, 0.999] | 1.001 [0.979, 1.025] | 1.014 | 1.000 | 1.000 |
| eat | 47601 / 3276 | 0.991 [0.987, 0.995] | 0.970 [0.960, 0.985] | 0.999 | 1.000 | 1.000 |
| quaff | 13127 / 2308 | 0.987 [0.978, 0.992] | 0.981 [0.942, 1.011] | 0.989 | 1.000 | 1.001 |
| throw | 52990 / 3103 | 0.997 [0.993, 1.001] | 0.998 [0.995, 1.000] | 0.996 | 1.001 | 1.000 |
| zap | 5922 / 1526 | 0.967 [0.929, 1.009] | 1.000 [1.000, 1.000] | 1.035 | 1.002 | 1.000 |
| takeoff | 12310 / 2006 | 0.707 [0.599, 0.895] | 0.787 [0.674, 0.898] | 0.840 | 1.000 | 1.000 |
| puton | 4728 / 816 | 0.568 [0.346, 0.808] | 0.769 [0.647, 0.877] | 0.891 | 1.000 | 1.000 |
| remove | 1512 / 641 | 1.043 [0.979, 1.067] | 1.000 [1.000, 1.000] | 1.805 | 1.000 | 1.000 |
| wield | 21856 / 2804 | 0.982 [0.976, 0.986] | 0.842 [0.813, 0.933] | 0.979 | 0.997 | 1.000 |
| apply | 9378 / 1468 | 0.985 [0.943, 1.010] | 1.001 [0.991, 1.016] | 0.993 | 1.000 | 1.000 |
| read | 36025 / 2192 | 0.971 [0.949, 0.999] | 0.998 [0.979, 1.025] | 0.996 | 1.000 | 1.000 |
| drop | 21135 / 2671 | 0.997 [0.995, 0.999] | 1.000 [1.000, 1.000] | 1.001 | 1.000 | 1.000 |

### 524M, action seed 27182

| Verb | Audit choices / games | State baseline | Weighted state | Optimal constant | Verb Q | Verb centered Q |
|---|---:|---|---|---:|---:|---:|
| wear | 116726 / 3172 | 0.998 [0.994, 1.003] | 0.985 [0.967, 1.000] | 0.997 | 1.000 | 1.000 |
| eat | 49300 / 3334 | 0.997 [0.995, 1.000] | 1.000 [1.000, 1.001] | 1.000 | 1.000 | 1.000 |
| quaff | 16978 / 2351 | 0.981 [0.971, 0.990] | 0.980 [0.967, 0.989] | 0.986 | 1.000 | 1.000 |
| throw | 51640 / 3098 | 1.000 [1.000, 1.000] | 0.992 [0.988, 0.998] | 0.991 | 1.000 | 1.000 |
| zap | 5893 / 1507 | 1.060 [0.974, 1.165] | 1.235 [1.056, 1.493] | 1.118 | 1.000 | 1.000 |
| takeoff | 8909 / 2003 | 0.933 [0.900, 0.948] | 0.797 [0.732, 0.834] | 0.906 | 1.000 | 0.999 |
| puton | 12034 / 804 | 0.895 [0.350, 0.922] | 0.910 [0.385, 0.935] | 0.974 | 1.000 | 1.000 |
| remove | 1559 / 612 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.154 | 1.000 | 1.000 |
| wield | 26950 / 2829 | 0.967 [0.945, 0.982] | 0.907 [0.855, 0.950] | 0.961 | 1.000 | 0.999 |
| apply | 8444 / 1458 | 0.998 [0.990, 1.002] | 1.118 [0.992, 1.836] | 1.002 | 1.000 | 1.000 |
| read | 34015 / 2203 | 1.015 [0.991, 1.042] | 1.013 [0.981, 1.051] | 1.001 | 1.000 | 1.000 |
| drop | 20857 / 2669 | 0.997 [0.994, 0.999] | 0.998 [0.990, 1.007] | 0.995 | 1.000 | 1.000 |

### 1B

| Verb | Audit choices / games | State baseline | Weighted state | Optimal constant | Verb Q | Verb centered Q |
|---|---:|---|---|---:|---:|---:|
| wear | 42583 / 2310 | 1.000 [1.000, 1.000] | 1.004 [0.994, 1.012] | 1.002 | 1.000 | 1.000 |
| eat | 51118 / 2454 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 | 1.000 | 1.000 |
| quaff | 12975 / 1438 | 0.956 [0.907, 1.000] | 0.991 [0.985, 0.998] | 0.997 | 1.000 | 1.000 |
| throw | 47508 / 2347 | 0.997 [0.994, 0.999] | 0.996 [0.994, 0.997] | 0.994 | 1.000 | 1.000 |
| zap | 11228 / 1184 | 1.000 [1.000, 1.000] | 1.431 [1.173, 1.942] | 1.000 | 1.000 | 1.002 |
| takeoff | 9927 / 983 | 1.000 [1.000, 1.000] | 1.041 [0.715, 1.063] | 1.011 | 0.999 | 1.000 |
| puton | 31910 / 166 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 3.488 | 1.000 | 1.011 |
| remove | 1750 / 144 | 0.994 [0.947, 1.023] | 1.000 [1.000, 1.000] | 1.004 | 1.000 | 1.000 |
| wield | 13089 / 1907 | 1.000 [1.000, 1.000] | 1.041 [0.918, 1.289] | 1.134 | 1.001 | 1.005 |
| apply | 6457 / 376 | 1.008 [0.972, 1.023] | 1.062 [0.971, 1.167] | 1.125 | 1.000 | 1.000 |
| read | 11977 / 1286 | 0.992 [0.983, 1.013] | 0.997 [0.962, 1.086] | 1.072 | 1.000 | 1.000 |
| drop | 25185 / 2072 | 1.000 [1.000, 1.000] | 1.006 [1.001, 1.012] | 1.006 | 1.000 | 1.000 |

## Staleness: 524M fits applied unchanged at 1B

| Verb | Frozen 524M state baseline | Fresh 1B state baseline | Frozen weighted baseline |
|---|---|---|---|
| wear | 1.000 [0.999, 1.001] | 1.000 [1.000, 1.000] | 1.023 [1.010, 1.039] |
| eat | 1.006 [1.002, 1.012] | 1.000 [1.000, 1.000] | 1.013 [1.007, 1.023] |
| quaff | 0.990 [0.984, 0.998] | 0.956 [0.907, 1.000] | 0.986 [0.961, 1.021] |
| throw | 1.006 [1.000, 1.012] | 0.997 [0.994, 0.999] | 0.997 [0.994, 1.000] |
| zap | 1.029 [0.996, 1.058] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| takeoff | 0.994 [0.736, 1.011] | 1.000 [1.000, 1.000] | 0.993 [0.722, 1.010] |
| puton | 1.894 [1.235, 6.797] | 1.000 [1.000, 1.000] | 2.576 [1.259, 11.943] |
| remove | 0.988 [0.955, 1.091] | 0.994 [0.947, 1.023] | 1.000 [1.000, 1.000] |
| wield | 0.984 [0.970, 0.999] | 1.000 [1.000, 1.000] | 1.273 [1.071, 1.577] |
| apply | 1.114 [1.032, 1.141] | 1.008 [0.972, 1.023] | 1.062 [0.978, 1.084] |
| read | 1.022 [0.996, 1.094] | 0.992 [0.983, 1.013] | 0.995 [0.965, 1.055] |
| drop | 0.999 [0.997, 1.001] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |

The unweighted frozen put-on baseline has ratio 1.894; the fresh unweighted fit chooses zero correction. Thus a baseline that helps at 524M cannot safely be assumed to help at 1B. Refitting and independent shrinkage matter, and the weighted control must be assessed separately.

## Rarity and dependence

| Stage | Verb | Audit selections | Nontrivial item distributions | Games with nontrivial distributions |
|---|---|---:|---:|---:|
| credit_early_s31415 | takeoff | 8122 | 3013 | 1426 |
| credit_early_s31415 | puton | 1018 | 295 | 247 |
| credit_early_s31415 | drop | 21109 | 16199 | 4027 |
| credit_middle_s31415 | takeoff | 12310 | 3143 | 1236 |
| credit_middle_s31415 | puton | 4728 | 504 | 225 |
| credit_middle_s31415 | drop | 21135 | 17284 | 2370 |
| credit_middle_s27182 | takeoff | 8909 | 3405 | 1230 |
| credit_middle_s27182 | puton | 12034 | 2659 | 225 |
| credit_middle_s27182 | drop | 20857 | 16946 | 2358 |
| credit_late_s31415 | takeoff | 9927 | 766 | 309 |
| credit_late_s31415 | puton | 31910 | 27099 | 40 |
| credit_late_s31415 | drop | 25185 | 18635 | 1802 |

“Nontrivial” means 1 − sum(item_probability²) > .01, independent of the sampled item. At 1B, put-on has 31,910 audit selections but only 40 games with nontrivial item distributions. A large selection count does not imply broad independent coverage.

## Auxiliary fit-seed check

| Verb | First audit, fit seed 17 | First audit, fit seed 29 | Second audit, fit seed 17 | Second audit, fit seed 29 |
|---|---:|---:|---:|---:|
| wear | 0.997 | 1.000 | 0.998 | 1.000 |
| eat | 0.991 | 0.972 | 0.994 | 0.987 |
| quaff | 0.987 | 0.969 | 0.991 | 0.987 |
| throw | 0.997 | 1.031 | 0.995 | 1.016 |
| zap | 0.967 | 1.033 | 1.013 | 1.139 |
| takeoff | 0.707 | 0.697 | 0.854 | 0.828 |
| puton | 0.568 | 0.593 | 0.920 | 0.919 |
| remove | 1.043 | 0.996 | 1.011 | 1.008 |
| wield | 0.982 | 0.983 | 0.983 | 0.984 |
| apply | 0.985 | 0.990 | 0.996 | 0.994 |
| read | 0.971 | 0.971 | 0.978 | 0.983 |
| drop | 0.997 | 0.995 | 0.997 | 0.996 |

## Promotion gate

Require a ≥10% point-estimate reduction in both middle action-seed audits, both game and stream upper bounds below one, and continued benefit after largest-game removal. This gate is a screening rule, not evidence of improved RL learning.

Passing verb/method pairs: takeoff / state, takeoff / Q_mean.

Use the stage, fit-seed and constant-control tables when deciding whether a passing pair is worth an online test. In particular, the previously reported drop improvement is not supported after correcting clipping. Do not restore the old blanket recommendation.

No online policy training was launched. The study does not establish a universal variance-reduction ceiling or a learning-speed benefit. It tests these frozen-feature predictors on these captures.

## Files

- [Primary results](all_primary_results.csv), [weighted controls](all_weighted_results.csv), [rarity](rarity.csv), [promotion gate](promotion_gate.csv).
- [CUDA reference checks](reference_checks.json), [numerical checks](numeric_checks.json), [kernel derivative checks](kernel_gradient_checks.csv), [centering checks](centering_checks.csv).
- [Empirical correction-gradient means](empirical_gradient_correction_means.csv). These component-wise intervals are not multiplicity-adjusted and are not a test of zero norm.
- [Plan](PLAN.md). `data/` contains regenerated targets and source manifests; `models/` contains new fitted predictors; `audit/` contains predictions, coefficients and detailed results.
- [Clipping correction](../clipping_correction/REPORT.md); old reports remain marked invalid.
