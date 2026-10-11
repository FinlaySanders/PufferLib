> **Results invalid for the training objective — missing reward clipping.** Offline reward/GAE/Q targets omitted the trainer’s [-1, 1] reward clamp. Derived critic and variance estimates below require regeneration and refitting; do not use them for training recommendations. Original results are retained for audit. See the [clipping correction](../clipping_correction/REPORT.md).

# Directly fitting centered item differences

**Result: still no useful verb-head variance reduction on the real captures.** The critic was trained on the centered item difference itself, with gradients through the policy-weighted average of all candidate items. This removes the previous ordinary-Q loss’s incentive to spend capacity predicting an item-independent state offset.

The primary full verb-decoder parameter variance ratios across all stages and transfers were **0.99944–1.00104**. One is unchanged; lower is better. No arm approaches the prespecified 10% reduction gate.

Even the best exploratory point estimate among all tested seeds, loss weights, coefficient variants and transfers was 0.99770 for takeoff (weighted_17, credit_late_s31415 → credit_late_s31415): a 0.23% decrease, with stream 95% interval (0.98856, 1.00384). This is a description of the full search, not a selected improvement claim.

The positive control worked: an injected, known state–item signal was learned and removed. Its variance ratio was **0.282**, compared with **0.260** when subtracting the true injected signal. Those are synthetic targets, not NetHack gains.

No policy updates, new rollouts, or production trainer/engine edits were made.

## What changed

```text
c(s,v,i) = f(s,v,i) - sum_j mu(j|s,v) * f(s,v,j)
training loss = mean w * [c_chosen^2 - 2*A_GAE*c_chosen]
verb gradient estimate = (A_GAE - alpha_v*c_chosen) * grad log mu_verb
```

The loss equals weighted squared error against A_GAE minus a constant target-square term. Both sides of the centering operation participate in critic backpropagation; policy probabilities and features are detached. Adding a state/verb-only constant to every item prediction cancels in the output and its training gradients. Because the centered term has zero conditional expectation over the item choice, a frozen correction preserves the expected unclipped verb gradient under the logged behavior distribution.

This is a correction to **verb credit**, not the earlier Q(s,verb) baseline for argument heads. A null here does not invalidate the selective argument-head improvements in [the earlier report](../verb_critic/REPORT.md).

## Protocol

- Reused four existing 16,777,216-step captures: 131M, 524M and 1B checkpoints of `baseline_s2901`, plus another 524M action-sampling seed. 67,108,864 unique recorded environment steps; this follow-up collected none. Stages are from one training run.
- Capture source `3719caaaf945025e4e1e59c6556560d2ba9e3d1c`; engine `e7f6568568242745a7f7ebd8f730367123522cac`. Per-capture manifests and the [previous study](../verb_credit/REPORT.md) pin the original artifacts.
- Same frozen 1024-dimensional trunk and 16-dimensional candidate keys, 64/64-unit interaction MLP, fit-only normalization and target scale as the ordinary-Q comparison. Fit all 55 candidate slots and center using their actual masked probabilities.
- Four fits per verb/stage: MSE seeds 17 and 29; parameter-score-norm-weighted MSE seed 17; and weighted MSE after subtracting the existing frozen state/verb residual from the target. A state/verb-only residual cannot change the population centered optimum, but can affect finite-sample fitting.
- AdamW .001, weight decay .001, batch 512, at most 1,200 updates, stop after 300 updates without centered validation-loss improvement. The initial zero predictor remains a candidate. Fits/validation/audit use disjoint complete environment streams (192/64/256), matching the earlier split. No checkpoint or coefficient selected on audit.
- Gamma .999207735 and lambda .484387815, same BF16 reward/advantage conventions. Discard 1,024 warm-up steps per agent and unused final horizon positions; retain unfinished games. Throw is independently hash-thinned 1/8 and drop 1/4; other tested verbs retain all logged events.
- Primary: MSE seed 17, alpha fitted on validation to minimize full parameter-gradient variance, bounded [0,1]. Also evaluate an unrestricted signed alpha and fixed alpha=1 for every fit. This checks whether shrinkage is hiding a useful predictor.
- Both logit-space and full 26×1024 verb-weight gradient moments use all audit events and the epsilon-adjusted verb score. Encoder/recurrent/value/entropy gradients, PPO clipping/replay and optimizer transformations are outside this measurement.
- 200 bootstrap replicates over episodes and environment streams, plus removal of the largest baseline squared-gradient episode. Intervals condition on fitted models and coefficients; they do not cover variation across independently trained policies or adjust for multiple comparisons.
- Transfers freeze the 524M critic, input normalization and validation coefficient. Recenter under target probabilities. Only even streams are audited on transfer too, because indexed dungeon-seed schedules overlap between action-sampling seeds.
- This follow-up was designed after inspecting the prior null on the same captures. Its held-out audit is separate from fitting, but is reused exploratory evidence, not an independent confirmatory dataset.

## Primary results by checkpoint

Parentheses are stream-clustered 95% intervals. Raw CSVs also include episode intervals, logit-space results and signed componentwise mean-gradient differences. A ratio exactly one can mean that validation retained the zero predictor or set alpha to zero.

### 131M

| Verb | Audit events / games | Ordinary Q | Direct centered fit (95% CI) | Alpha | Without largest game |
|---|---:|---:|---:|---:|---:|
| quaff | 18,775 / 3,790 | 0.99852 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |
| read | 12,142 / 3,078 | 1.00000 | 1.00010 (0.99980, 1.00031) | 1 | 1.00010 |
| zap | 6,283 / 1,959 | 1.00004 | 1.00028 (0.99913, 1.00157) | 0.239 | 1.00030 |
| puton | 1,018 / 845 | 1.00000 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |
| wear | 38,702 / 5,243 | 1.00120 | 1.00102 (0.99949, 1.00333) | 1 | 1.00181 |
| throw | 54,926 / 5,512 | 0.99989 | 0.99999 (0.99973, 1.00018) | 0.229 | 0.99989 |
| takeoff | 8,122 / 3,333 | 1.00121 | 0.99977 (0.99923, 1.00012) | 0.115 | 0.99970 |
| drop | 21,109 / 4,940 | 1.00000 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |

### 524M

| Verb | Audit events / games | Ordinary Q | Direct centered fit (95% CI) | Alpha | Without largest game |
|---|---:|---:|---:|---:|---:|
| quaff | 13,127 / 2,308 | 1.00001 | 1.00045 (1.00002, 1.01731) | 1 | 1.00900 |
| read | 36,025 / 2,192 | 1.00000 | 0.99963 (0.99876, 1.00005) | 1 | 0.99940 |
| zap | 5,922 / 1,526 | 1.00188 | 1.00036 (0.99959, 1.00130) | 1 | 1.00037 |
| puton | 4,728 / 816 | 1.00000 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |
| wear | 92,426 / 3,119 | 1.00000 | 0.99996 (0.99922, 1.00084) | 1 | 0.99993 |
| throw | 52,990 / 3,103 | 1.00243 | 1.00020 (0.99960, 1.00070) | 1 | 1.00005 |
| takeoff | 12,310 / 2,006 | 0.99965 | 1.00002 (0.99949, 1.00074) | 1 | 1.00002 |
| drop | 21,135 / 2,671 | 1.00000 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |

### 1B

| Verb | Audit events / games | Ordinary Q | Direct centered fit (95% CI) | Alpha | Without largest game |
|---|---:|---:|---:|---:|---:|
| quaff | 12,975 / 1,438 | 1.00000 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |
| read | 11,977 / 1,286 | 1.00000 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |
| zap | 11,228 / 1,184 | 1.00000 | 1.00064 (0.99679, 1.00429) | 1 | 1.00052 |
| puton | 31,910 / 166 | 1.00000 | 0.99988 (0.99884, 1.00087) | 1 | 0.99984 |
| wear | 42,583 / 2,310 | 1.00000 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |
| throw | 47,508 / 2,347 | 1.00000 | 0.99986 (0.99887, 1.00073) | 1 | 0.99984 |
| takeoff | 9,927 / 983 | 0.99950 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |
| drop | 25,185 / 2,072 | 0.99969 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |

## Transfer

### Second 524M action-sampling seed

| Verb | Audit events / games | Ordinary Q | Direct centered fit (95% CI) | Alpha | Without largest game |
|---|---:|---:|---:|---:|---:|
| quaff | 16,978 / 2,351 | 1.00000 | 0.99975 (0.99410, 1.00499) | 1 | 0.99819 |
| read | 34,015 / 2,203 | 1.00000 | 0.99988 (0.99915, 1.00070) | 1 | 0.99987 |
| zap | 5,893 / 1,507 | 1.00000 | 0.99969 (0.99936, 0.99994) | 1 | 0.99965 |
| puton | 12,034 / 804 | 1.00000 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |
| wear | 116,726 / 3,172 | 1.00000 | 1.00065 (0.99989, 1.00236) | 1 | 1.00093 |
| throw | 51,640 / 3,098 | 1.00126 | 1.00027 (1.00000, 1.00065) | 1 | 1.00032 |
| takeoff | 8,909 / 2,003 | 1.00105 | 0.99998 (0.99914, 1.00069) | 1 | 0.99998 |
| drop | 20,857 / 2,669 | 1.00000 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |

### Frozen 524M critic applied at 1B

This includes representation drift, not just an old critic on unchanged policy features.

| Verb | Audit events / games | Ordinary Q | Direct centered fit (95% CI) | Alpha | Without largest game |
|---|---:|---:|---:|---:|---:|
| quaff | 12,975 / 1,438 | 1.00002 | 1.00104 (0.99921, 1.00822) | 1 | 1.00326 |
| read | 11,977 / 1,286 | 1.00000 | 0.99944 (0.99901, 1.00024) | 1 | 0.99942 |
| zap | 11,228 / 1,184 | 0.99991 | 1.00005 (0.99976, 1.00038) | 1 | 1.00007 |
| puton | 31,910 / 166 | 1.00000 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |
| wear | 42,583 / 2,310 | 1.00000 | 1.00011 (0.99554, 1.00388) | 1 | 1.00010 |
| throw | 47,508 / 2,347 | 0.99724 | 1.00001 (0.99936, 1.00061) | 1 | 0.99997 |
| takeoff | 9,927 / 983 | 0.99994 | 0.99980 (0.99948, 1.00000) | 1 | 0.99980 |
| drop | 25,185 / 2,072 | 1.00000 | 1.00000 (1.00000, 1.00000) | 0 | 1.00000 |

## Alternative objectives and coefficient checks

Ranges below span all eight verbs, three self-fitted stages and both transfers. They describe variability across comparisons, not confidence intervals.

| Fit / coefficient | Min parameter ratio | Max parameter ratio |
|---|---:|---:|
| mse_17 | 0.99944 | 1.00104 |
| mse_29 | 0.99949 | 1.00186 |
| weighted_17 | 0.99770 | 1.03308 |
| residual_weighted_17 | 0.99895 | 1.01011 |
| mse_17_unrestricted | 0.99899 | 1.04210 |
| mse_17_unscaled | 0.99888 | 1.00499 |

Validation retained the initial zero predictor in 24 of 96 real-data fits. The primary bounded coefficient is nonzero in 26 of 40 stage/transfer comparisons. Evaluating alpha=1 and allowing signed coefficients does not recover a large benefit. Some weighted or unrestricted fits worsen variance by several percent.

## Sanity checks and interpretation

The planted state–item interaction used real saved keys, masks and probabilities, plus synthetic noise and a state term. Learned correction: 0.28223 (0.23776, 0.33262); known exact correction: 0.26049 (0.22103, 0.30813). This confirms that the implementation and small model can recover this particular signal; it does not prove that real item consequences are equally representable.

Analytic centering-gradient tests, constant-offset cancellation and masked-output gradient tests passed at float64 roundoff. Maximum conditional centering residual on real predictions was 3.29e-13. Old-critic comparator ratios match the original report, and transferred coefficients exactly match their source-validation values. Production source hashes are unchanged.

Conditional centering is an exact algebraic property under the stored probabilities; finite sampled means need not be zero. One of the 40 primary stream-bootstrap intervals for the sampled control mean excludes zero (524M wear), with no multiplicity correction. All sample means and signed gradient-component intervals are retained; this isolated result does not establish a systematic bias. Original sampler-probability checks had maximum absolute discrepancy 4.78e-6.

The outcome weakens the hypothesis that ordinary-Q loss was simply distracted by the shared state offset. Direct optimization of item differences still finds almost no reproducible reduction with these keys and GAE targets. It does not distinguish weak true item effects from insufficient representations, sparse counterfactual coverage, heavy tails or limited target quality. Only the selected item has an observed outcome in these captures. A short GAE lambda still includes longer-term predictions through the value bootstrap.

**Decision:** do not launch online verb-side item-luck experiments from this result. No tested variant passes the >=10% reduction gate, let alone replication. The earlier verb-conditioned argument baseline remains a separate, more promising candidate for selected heads.

## Artifacts

- [Prespecified plan](PLAN.md)
- [All 1,120 real-data result rows](all_results.csv)
- [Fit summaries](fits.csv) and per-model JSON training histories in each stage directory
- [Signed gradient differences and intervals](bias_components.csv)
- [Planted-control results](planted_results.csv)
- [Implementation checks](checks.json), [completion checks](final_checks.json)
- Fitter/auditor: `../centered_item.py`; runner: `../run_centered_item.py`; report generator: `../write_centered_item_report.py`.
