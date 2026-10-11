> **Results invalid for the training objective — missing reward clipping.** Offline reward/GAE/Q targets omitted the trainer’s [-1, 1] reward clamp. Derived critic and variance estimates below require regeneration and refitting; do not use them for training recommendations. Original results are retained for audit. See the [clipping correction](../clipping_correction/REPORT.md).

# Where the advantage variance comes from

**Decision: keep the selective argument-baseline idea, especially drop; park verb-side item-luck subtraction.** Replacing learned item keys with public inventory inputs did not recover a useful verb-side correction. A separate baseline for the chosen verb still reduces item-gradient variance for some verbs, and drop replicates across rollout seeds and at 1B. These are offline estimator results, not demonstrated RL improvements.

## What was measured

- Two frozen 524M captures of one policy run: action seeds 31415 and 27182, 16,777,216 steps each. Fit/validation/audit use disjoint whole environment streams (192/64/256). All-step decomposition uses 8,110,592 valid audit steps per capture. The second seed changes actions but shares the indexed dungeon-seed schedule; audit remains on even streams.
- Existing logs were missing raw inventory. An isolated scratch build replayed the same streams, asserting byte-identical lite records, sparse logits/actions/trunk records and pointer records. It added 1,354,927 pre-action public inventory records. These replays are not new independent samples.
- Public inputs are the appearance glyph, discovered glyph and eight gated item-state bytes already in the policy observation. The old field called `features` is a learned embedding, not raw data. No hidden item identity was supplied.
- Gamma .999207735, lambda .484387815, existing terminal convention and BF16 reward/advantage storage. Exclude 1,024 warm-up steps per agent and the unused last GAE slot in each 512-step horizon. Retain unfinished games. No truncations occurred in the analyzed audit steps.
- State-only and state+verb predictors: 64/64-unit MLPs; fit GAE with seeds 17/29 and TD error with seed 17. Inverse logging-frequency weights restore the natural verb distribution. Public-item predictors use categorical embeddings and gated numeric fields, ordinary and directly centered losses; compare with the existing key-based models and matched 64/64 per-verb state models.
- Auxiliary AdamW .001, weight decay .001, zero initial predictor, at most 1,500 updates, validation early stopping after 300 updates without improvement. No gradient enters the policy. Public-feature models differ in categorical parameter count; this is not an exact capacity ablation.
- Coefficients are fitted only on validation streams, then frozen for transfer. A state-only verb baseline uses one coefficient across all verbs: choosing a coefficient based on the sampled verb would invalidate that baseline. Argument baselines may depend on the chosen verb.
- Decoder-gradient results use all retained events and full verb linear-weight or item query/key/temperature geometry, plus logit checks. They exclude shared-trunk gradients, value/entropy losses, PPO clipping, replay and optimizer effects. Ratios are conditional on the indicated head being used.
- 200 game/stream bootstrap replicates for gradient ratios and 300 for predictive comparisons, conditional on the fitted models. No multiplicity correction or independent training-seed replication. The same audit datasets have been reused across exploratory studies.

## Descriptive TD-error accounting

```text
b = gamma * (1-done) * V(next) - V(current)
delta = reward + b
Var(delta) = Var(reward) + Var(b) + 2*Cov(reward,b)
```

Neither the reward term nor the bootstrap term is pure noise/error. Both contain genuine, potentially predictable variation. The signed covariance is retained; percentages need not each lie in [0,100].

| 524M action seed | Var(TD) | Reward share | Bootstrap share | Covariance share | Largest game share of squared TD | Reward share after removing it |
|---|---:|---:|---:|---:|---:|---:|
| 31415 | 15.868 | 91.5% | 8.7% | -0.2% | 62.5% | 77.7% |
| 27182 | 6.441 | 79.1% | 21.7% | -0.9% | 37.2% | 66.8% |

These are descriptive population-moment estimates, not fitted causal components. After BF16 rounding to match training storage, one reward in the first audit sample is 8,320 during search20; a quaff event in another game has reward 3,056. A subsequent byte-identical replay attributed all 50 raw rewards above 500 across both full captures to the positive-only experience shaping term (at least 99.6% of each reward). The largest event was polymorph; its raw reward 8,308.1494 rounds to 8,320 in BF16. See the [reward-spike attribution report](../reward_spikes/REPORT.md) for game messages, exact reward components and the experience-loss asymmetry.

The all-action summary hides major differences between heads. Below is the second capture’s TD-error decomposition **after multiplication by the full item-decoder parameter score**:

| Item head | Reward share | Bootstrap share | Signed covariance share |
|---|---:|---:|---:|
| quaff | 92.4% | 7.5% | 0.1% |
| read | 0.4% | 99.5% | 0.1% |
| zap | 27.3% | 68.7% | 4.0% |
| puton | 0.0% | 100.0% | -0.0% |
| wear | 0.1% | 99.9% | 0.0% |
| throw | 32.6% | 101.5% | -34.1% |
| takeoff | 0.2% | 100.2% | -0.4% |
| drop | 68.0% | 46.0% | -14.0% |

Read, wear, put-on and take-off item gradients are overwhelmingly driven by the bootstrap term in this sample. That is a reason to examine value predictions and temporal credit for these actions, not evidence that their value predictions are necessarily wrong.

## Value explained variance

| Target | Seed 31415 | Seed 27182 |
|---|---:|---:|
| lambda_return | 0.978 | 0.990 |
| 32_step_bootstrap | 0.645 | 0.793 |
| 128_step_bootstrap | 0.295 | 0.450 |

The lambda target is V + GAE and uses the same value function’s bootstrap; its very high explained variance is partly a consequence of that construction. Longer targets replace more of that bootstrap with observed rewards, but still include outcome randomness and bootstrapping. None of these numbers directly measures irreducible noise or true value-function error.

## Predictability from state and verb

Held-out MSE divided by the zero-residual predictor’s MSE. These fits predict GAE or TD residuals, not total returns. The rows use natural action-frequency weights; values near one mean little additional predictive power. Seed 17 is the primary fit; seed 29 is in the CSV.

| Target / predictor | First audit | Second action seed |
|---|---:|---:|
| adv / state_17 | 0.998 (0.996, 0.999) | 0.999 (0.997, 1.000) |
| adv / verb_17 | 0.998 (0.996, 0.999) | 0.999 (0.997, 1.000) |
| delta / state_17 | 0.999 (0.998, 1.000) | 1.000 (0.999, 1.001) |
| delta / verb_17 | 0.999 (0.997, 0.999) | 0.999 (0.998, 1.000) |

The global state-only correction changes overall verb-logit gradient variance by only about 0.1% on the first capture and provides no improvement on the second. These overall results do not rule out meaningful reductions in particular rare argument heads.

## Do public item features recover the missing item-luck signal?

No substantial gain in these tests. The primary directly centered public-item model uses seed 17; ratios below refer to the full verb-decoder parameter gradient. Ordinary public Q, seed 29, and the learned-key controls are all retained in the raw results.

| Chosen verb | First audit | Second action seed |
|---|---:|---:|
| quaff | 1.000 (1.000, 1.000) | 1.000 (1.000, 1.000) |
| read | 1.000 (1.000, 1.000) | 1.000 (1.000, 1.000) |
| zap | 1.000 (1.000, 1.000) | 1.000 (1.000, 1.000) |
| puton | 1.000 (1.000, 1.000) | 1.000 (1.000, 1.000) |
| wear | 1.000 (1.000, 1.000) | 1.000 (1.000, 1.000) |
| throw | 0.999 (0.997, 1.000) | 1.002 (1.001, 1.004) |
| takeoff | 1.001 (0.998, 1.007) | 0.999 (0.994, 1.005) |
| drop | 1.000 (0.999, 1.000) | 1.000 (0.999, 1.001) |

Chosen-item Q prediction occasionally improves on a state-only predictor, but centering removes almost all of its useful common offset. Public inputs do not provide a reproducible large advantage over learned keys. This weakens the specific representation-bottleneck explanation for this correction; it does not establish that the encoder represents all useful item knowledge or that a stronger counterfactual critic could not help.

## What still works: verb-conditioned argument baselines

These subtract a prediction that depends on state and the chosen verb, but never the sampled item, from the item head’s advantage. Primary model here is a separate 64/64-unit state predictor for each verb. Full item-decoder parameter ratios:

| Item head | First 524M audit | Second 524M audit |
|---|---:|---:|
| quaff | 0.995 (0.990, 1.008) | 0.999 (0.995, 1.005) |
| read | 0.992 (0.973, 1.001) | 0.981 (0.967, 0.997) |
| zap | 0.974 (0.947, 1.002) | 0.994 (0.969, 1.026) |
| puton | 0.576 (0.350, 0.821) | 0.920 (0.474, 0.942) |
| wear | 0.990 (0.982, 0.996) | 0.992 (0.984, 0.999) |
| throw | 0.996 (0.992, 0.999) | 0.997 (0.993, 1.000) |
| takeoff | 0.725 (0.617, 0.904) | 0.879 (0.779, 0.955) |
| drop | 0.855 (0.781, 0.912) | 0.854 (0.763, 0.921) |

Drop and take-off passed the prespecified replicated >=10% point-estimate reduction gate with both game/stream upper intervals below one and survival of largest-game removal. Put-on improves but misses that magnitude gate on the second sample and is strongly outlier-sensitive.

### A constant is an important control

| Item head, second 524M sample | Verb mean | Gradient-optimal constant | Learned state baseline | Learned / optimal constant |
|---|---:|---:|---:|---:|
| takeoff | 0.910 | 0.917 | 0.879 | 0.959 (0.882, 1.073) |
| puton | 0.977 | 0.978 | 0.920 | 0.940 (0.504, 0.960) |
| drop | 0.995 | 0.995 | 0.854 | 0.858 (0.770, 0.925) |

Drop’s improvement requires more than a per-verb offset. For take-off, a constant already removes much of the variance, and the learned model’s incremental benefit over that constant is uncertain. The natural-frequency shared state-only model also performs well on drop at 524M: verb conditioning itself is not established as necessary for that result.

### Follow-up at other learning stages

Only the two replicated candidates were expanded. These are fresh same-stage fits, with validation-fitted coefficients; stages remain from the same policy-training run.

| Item head | 131M | 524M, second capture | 1B |
|---|---:|---:|---:|
| takeoff | 0.904 (0.756, 0.921) | 0.879 (0.779, 0.955) | 1.000 (1.000, 1.000) |
| drop | 0.974 (0.958, 0.987) | 0.854 (0.763, 0.921) | 0.891 (0.845, 0.930) |

A fresh 1B take-off fit selects the zero predictor. Drop retains an approximately 11% reduction at 1B. Freezing the 524M drop critic until 1B gives only about 6% reduction with an interval including one; refitting matters. This supports adaptation and shrinkage, rather than assuming one baseline will help every verb throughout learning.

## Recommendation and limits

1. If proceeding to an online variance-reduction test, prioritize an adaptive drop-item baseline against ordinary GAE, with a per-verb constant control. Measure actual learning and throughput; the offline ratio does not guarantee better score or item use.
2. Keep take-off as a secondary stage-dependent candidate. Its improvement over a constant is not established at 524M, and it disappears in the fresh 1B fit.
3. Park verb-side item-luck subtraction for now. Public observation inputs and direct centering still do not meet the gate. This is a null for these predictors/targets, not a measured upper bound on all action-dependent variance reduction.
4. Investigate the provenance of extreme shaped-reward spikes before changing rewards or clipping them. The global variance summary is heavily tail-driven; clipping could change the objective. For read/wear/put-on, inspect the bootstrap/value contribution specifically rather than transferring that global explanation to every head.

No online training was launched. This study cannot uniquely split stochastic reward noise, true value-function error and true counterfactual action effects from single observed continuations. Shared-trunk PPO behavior and multi-seed learning gains remain untested.

## Artifacts

- [Plan](PLAN.md)
- [All-step moments and largest-game checks](moments.csv)
- [Decoder-gradient component accounting](gradient_components.csv)
- [Value explained variance](value_explained_variance.csv)
- [Held-out prediction comparisons](predictive.csv)
- [416 per-head gradient comparisons](gradients.csv)
- [Global state-only verb baseline](global_state_gradients.csv)
- [Constant controls, stage fits and stale transfers](stage_baselines.csv)
- [Numeric checks](numeric_checks.json), [final integrity checks](final_checks.json)
- Capture: `../prepare_diagnostic_capture.py`, `../diagnostic_vec_hook.h`, `../run_diagnostic_capture.py`. Analysis: `../diagnostic_prepare.py`, `../diagnostic_models.py`, `../diagnostic_audit.py`, `../diagnostic_baselines.py`, `../diagnostic_gradient_components.py`. Report: `../write_diagnostic_report.py`.
