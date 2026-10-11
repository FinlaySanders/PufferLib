# Why argument baselines help some heads

Date: 2026-10-08. CPU-only analysis of existing logs and saved captures; no policy updates, new model fits, or changes to the active queue.

The strongest measured distinction is **predictable error shared by a verb's item choices, on states that actually generate substantial item gradients**. Rarity alone does not explain the benefits. For put-on in the historical 524M captures, almost all squared item-gradient magnitude comes from the uniform verb-exploration component. The useful critic appears to absorb a predictable drop in estimated value after these unusual verb choices. This is evidence about the estimator and value predictions, not proof of the true long-term consequences of putting on an item.

There are two separate datasets below. Do not treat them as the same policies:

- Online: completed 1B runs of control/all-arguments/selective at seed 4101, plus the newly completed control training at seed 4102. Critic predictions were recorded before outcomes. Aggregate gradient diagnostics include actual PPO clipping and replay, but only fixed-stride samples and no game IDs.
- Offline: a historical baseline_s2901 checkpoint at 524,288,000 steps, with independent rollout seeds 16180 and 27182. Frozen critics were fitted/selected using seed 31415. Corrected targets include production reward clipping. Held-out environment streams are used throughout; prediction models and coefficients are not fitted here. The two rollout samples are not independent training seeds.

## 1. Put-on's large gradient events are mostly unusual verb choices

Using the historical checkpoint's actual sampling probabilities, epsilon was 0.0039642667. If K verbs are legal, the posterior probability that a sampled verb came from uniform mixing is `(epsilon / K) / mu(verb)`. Averaging this quantity estimates the mixture component's contribution; the actual latent mixture coin was not logged. Float rounding at the probability floor required clipping posterior values at 1 after checking their excess was below 1e-5.

The gradient magnitude here is `||A * (one_hot(item) - item_probabilities)||²` in item-logit space, before PPO replay/clipping. These are shares of the second moment, not independently attributable centered variances.

| Verb | Estimated uniform share of selections, samples 16180 / 27182 | Estimated uniform share of squared item-gradient magnitude |
|---|---:|---:|
| Put-on | 13.5% / 5.4% | 98.1% / 98.7% |
| Take-off | 16.1% / 20.3% | 71.7% / 79.3% |
| Quaff | 9.0% / 9.4% | 43.2% / 19.1% |
| Read | 5.5% / 4.5% | 44.9% / 25.9% |

For put-on, actions with sampling probability below 1% carry 98.3% and 98.9% of the squared gradient magnitude. Their mean advantages are -2.37 and -2.14. Immediate rewards average approximately zero. Put-on events that survive at least four subsequent policy steps carry 99.9% of that magnitude in both samples, so immediate episode endings do not explain this put-on signal.

Interpretation: an unusual verb choice can produce a large common negative advantage, and the item head receives it despite not choosing the verb. A state/verb baseline can subtract the predictable common component without subtracting which item's relative effect. This is the credit-separation mechanism the method was intended to exploit. It does not establish that every sampled item would have exactly the same outcome.

## 2. Which inputs make the useful critics work?

Frozen history-aware tree critics reproduce the saved pointer-decoder parameter-gradient variance ratios. Then groups of pre-action inputs were shuffled on audit data, with three random permutations. Higher ratios after shuffling indicate reliance on the inputs. This can create off-support input combinations, so it is a predictor diagnostic, not a causal game intervention. Group effects are not additive.

| Verb / input shuffled | Original ratio, samples 16180 / 27182 | Ratio after shuffle |
|---|---:|---:|
| Put-on / current V(s) | 0.588 / 0.903 | 0.819 / 0.968 |
| Put-on / inventory summaries | 0.588 / 0.903 | 0.676 / 0.944 |
| Take-off / verb probabilities | 0.761 / 0.807 | 0.846 / 0.929 |
| Take-off / recent value changes | 0.761 / 0.807 | 0.786 / 0.855 |

For put-on, the highest quarter of pre-action values carries 99.1% and 99.6% of the squared pointer-parameter gradient magnitude. In the first sample, this group's mean value is 34.15, mean advantage -1.39, mean immediate reward -0.0011, and mean TD residual -1.28. Most of that residual is therefore a bootstrapped value change, not an explicit immediate penalty. The critic predicts -1.31 on average for this group.

Take-off has a more state-dependent pattern involving the policy's own verb probabilities and recent value changes. The predictor uses these to identify where the verb-conditional residual differs from the ordinary state baseline. Previous wear is among the fitted tree's inputs, but shuffling previous-verb features has only a small effect; there is not enough evidence to attribute the result to a specific wear/take-off loop.

These results support a value-calibration/verb-selection explanation. They do not distinguish true opportunity cost from an error in V(s), and do not demonstrate improved item reasoning.

## 3. Online critics predict little for most other verbs

For the control arm's final 250M steps, the auxiliary critic is trained but its predictions do not alter the actor. Reduction in mean squared rollout advantage is measured against the zero residual predictor. Negative values mean the critic adds error. These are predictive diagnostics, not gradient variance reductions.

| Verb | Mean advantage, seed 4101 | MSE reduction, seed 4101 | MSE reduction, seed 4102 |
|---|---:|---:|---:|
| Put-on | -2.593 | 25.6% | 12.7% |
| Take-off | -0.047 | -1.6% | 2.6% |
| Wield | -0.006 | 1.3% | 1.9% |
| Quaff | -0.106 | 0.7% | 0.8% |
| Read | -0.086 | 0.6% | 0.6% |
| Zap | -0.073 | 0.2% | 0.8% |
| Remove | -0.008 | -1.6% | -2.7% |
| Apply | -0.023 | -0.7% | -1.0% |

In seed 4101, simply subtracting put-on's retrospective mean would remove 23.5% of the advantage second moment, compared with the critic's 25.6%. The critic explains only 2.8% of variance after centering. Thus much of its prediction gain is a large mean offset for that verb.

This is **not universal across seeds**. Seed 4102's final-quarter put-on mean is -0.020, and its gain is mostly state-dependent. It has 808,009 put-on selections versus seed 4101's 5,089. The same verb name hides very different behavior and state distributions.

Wield also showed a relatively consistent online logit-gradient reduction in the all-arguments arm (~12% over the whole first run). It should not be omitted just because it was not selected for the narrow arm. Conversely, take-off's weaker online result and changing prediction quality show that an offline benefit is not a permanent property of a head.

For read/quaff, the fitted state/verb predictors have little usable predictive signal. This is consistent with their mostly null variance results. It is not proof that all remaining variance is irreducible, nor that item outcomes are unimportant. The predictor may lack information or capacity, and state coverage may be inadequate.

## 4. Meaningful choices and independent coverage matter

In the corrected 524M seed-31415 audit:

| Verb | Selections | Nontrivial item distributions |
|---|---:|---:|
| Remove | 1,512 | 42 |
| Put-on | 4,728 | 504 |
| Take-off | 12,310 | 3,143 |
| Quaff | 13,127 | 7,512 |
| Read | 36,025 | 27,899 |

Nontrivial means `1 - sum(p_item²) > .01`. A head with one available choice has zero policy-gradient score; a nearly deterministic choice usually contributes little, although rare alternatives can contribute substantially. Counting selections alone therefore overstates useful support. Remove is rare but almost never has a meaningful item decision in this sample. Quaff and read have many meaningful choices but little prediction improvement, so insufficient choice count cannot explain all nulls.

Ending episodes are another source of heavy tails. In the two confirmation samples, the roughly 1% of quaff selections that immediately end an episode account for 50.1% and 29.3% of its squared logit-gradient magnitude. The raw clipped terminal reward is only about -0.473; the larger advantage also reflects losing the value bootstrap. Whether these events are predictable from richer pre-action inputs remains unmeasured. Take-off's terminal contribution varies sharply between samples, reinforcing the need for independent-game intervals and outlier checks.

## 5. The online objective is not the critic's regression objective

The implementation fits frozen rollout-time GAE residuals, but PPO computes fresh advantages from live value predictions during each replay pass. The policy-gradient term is also importance weighted and clipped. The auxiliary correction uses an exact sampling-distribution importance ratio and remains active when the original PPO term is clipped out. This preserves the intended zero-mean control for fixed policies, but does not make it variance-optimal.

For an argument score g, suppressing signs and minibatch scaling, the implemented form is:

`G_corrected = g * (ratio_PPO * A_live * clip_gate - ratio_exact * b_rollout)`.

The critic instead minimizes `(A_rollout - b)²`. The optimal baseline for this gradient depends on score magnitude, replay, the clip gate, and the live advantage. Different argument heads for the same verb have different score geometry, so one scalar prediction need not benefit all of them equally.

The control always contributes its own variance. It helps only if its covariance with the original gradient is large enough: `Var(G-C) = Var(G) + Var(C) - 2 Cov(G,C)`. Prediction MSE improvement alone is insufficient.

This mismatch is visible in the online logs: late all-arguments put-on improves rollout residual MSE by 42.3%, but its sampled logit-gradient variance ratio is 8.854 (only 137 sampled replay uses, so not a precise population estimate). The logs lack the per-example moments needed to separate clipping, live-value drift, and score weighting as causes. No claim is made that one of these has been isolated.

The current online correction has fixed strength 1. Earlier offline studies fitted strength on held-out data and could switch a bad control off. For example, in the second corrected 524M sample, a read baseline at full strength has logit-variance ratio 1.028, while the preselected smaller coefficient gives 0.989. This is a concrete reason not to interpret the all-head online result as a test of an optimally gated baseline.

## Practical conclusion

The most plausible measured explanation is that put-on/take-off sometimes have a large, predictable state/verb residual, particularly on unusual verb choices. Subtracting that residual can protect argument updates from the common cost or value-estimation error. Other heads either have little predictable residual, few meaningful choices, or prediction errors that are magnified by the gradient geometry and PPO replay/clipping.

This does not yet demonstrate faster learning or better item use. The next discriminating measurement would log, on identical PPO rows, rollout and live advantages, baseline prediction, importance ratio, clip gate, and argument-score norms. That would separate a weak critic from a useful critic applied at the wrong strength or to the wrong gradient. It requires additional isolated instrumentation; it was not added to the running campaign.

## Reproduction and artifacts

- `analyze.py`: online mean-offset decomposition and corrected offline score geometry. Reproduces the existing held-out logit-variance ratios to absolute error below 1e-8.
- `feature_reliance.py`: frozen-model feature shuffles and value bins. Reproduces the existing pointer-parameter ratios to absolute error below 1e-7.
- `transitions.py`: joins episode IDs and steps back to captures; checks episode and verb alignment; describes terminal events and uniform-mixture attribution.
- Raw results: `online_offsets.csv`, `offline_choice_groups.csv`, `offline_gradient_geometry.csv`, `feature_reliance.csv`, `tree_split_gains.csv`, `value_bins.csv`, `transition_groups.csv`.
- Checks: `checks.json`, `feature_checks.json`, `online_inputs.json`.

Run these scripts with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`. They do not import CUDA or use the GPU. Inputs come only from the corrected study and existing online campaign, never the invalid earlier unclipped-reward reports.
