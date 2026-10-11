# Follow-up: value dips, corrective action sequences, and baseline strength

2026-10-08. All work was CPU-only. No production or campaign code was changed, no actor was trained, and the interleaved online queue continued unchanged.

## Findings

The put-on signal is associated with unusual verb choices followed very often by an immediate remove command. Its negative value residual generally persists over subsequent actions. A small value-dependent baseline explains a substantial part of the variance benefit. These observations support a predictable verb/state cost or value-estimation error, but do not establish which game mechanic caused the value drop or whether the estimate is accurate.

The clipping hypothesis needs qualification. In a controlled offline sensitivity test, moderate policy changes generally preserve the put-on and take-off benefit. Larger changes can make a full-strength correction harmful; shrinking its coefficient helps. For quaff, the frozen neural critic already increases variance before any policy drift or clipping. Thus clipping is not a sufficient explanation for all unsuccessful heads.

These are estimator and trajectory results from a historical 524M checkpoint, not new online learning results. They do not establish why the current training arms have not improved score.

## Scope and data

- Policy: baseline_s2901 at 524,288,000 steps, the existing corrected study checkpoint.
- Captures: credit_middle_s16180 and credit_middle_s27182. Different action-sampling seeds, shared indexed dungeon-seed schedule. These are not independent training seeds.
- Audit: even-indexed environment streams. For fitting controls, source capture 31415 supplies training/validation streams; source audit data are not used to fit. Sensitivity-test coefficient fits use only odd validation streams of the corresponding capture, never its even audit streams.
- Four item heads: quaff, take-off, put-on and read. Each uses only verb and item, so the joint action probability is the full consumed-head probability, not an item-only approximation.
- Actual epsilon mixture, masks, corrected BF16 rewards clipped to [-1,1], gamma 0.999207735. Production combined-done handling is retained.
- Unless specified otherwise, variance is the trace of the item-logit gradient covariance. It excludes shared-trunk, value, entropy and optimizer effects. Earlier pointer-parameter results must not be numerically interchanged with these logit results.

## 1. The value residual does not simply rebound after one action

For every captured action, follow the original trajectory for 1, 2, 4, 8, 16, 32, 128 and 512 policy decisions. Compute:

`sum(discounted clipped rewards) + gamma^n * V(endpoint) - V(start)`.

Stop bootstrapping at episode termination and exclude right-censored endpoints. Longer-horizon numbers are bootstrapped return residuals, not direct measurements of true advantage or pure value error. A 512-policy-step horizon may span many more game turns because actions include macros.

The table below selects actions whose verb had less than 1% sampling probability, then weights by the pre-action item-policy Gini, `1 - sum(p_item²)`. This gives weight to meaningful item decisions without selecting on the observed advantage. Intervals resample complete environment streams. Raw unweighted results and all horizons are retained in trajectories.csv.

| Verb | Sample | One-step residual | 16-step residual | 128-step residual |
|---|---|---:|---:|---:|
| Put-on | 16180 | -1.64 [-1.97, -1.30] | -2.67 [-3.89, -1.72] | -4.16 [-6.70, -1.77] |
| Put-on | 27182 | -1.96 [-2.70, -1.36] | -2.07 [-3.16, -0.86] | -3.72 [-6.66, -0.95] |
| Take-off | 16180 | -0.43 [-0.48, -0.38] | -0.80 [-1.15, -0.50] | -2.08 [-3.03, -1.35] |
| Take-off | 27182 | -0.46 [-0.60, -0.37] | -0.80 [-1.24, -0.47] | -1.94 [-2.70, -1.22] |

This argues against a simple one-step value dip that immediately cancels. It does not prove that the action caused the whole deficit: state selection, continuing value bias, subsequent policy decisions and outcome randomness remain confounded.

## 2. Immediate commands often reverse the selected equipment choice

Joined the next action and its selected inventory slot from the original sparse action captures, checking episode, step and verb exactly. The percentages below condition on the same low-probability verb selections.

| Sequence | Sample 16180 | Sample 27182 |
|---|---:|---:|
| Put-on followed immediately by remove | 76.8% | 76.8% |
| Put-on followed by remove on the same slot | 76.7% | 76.7% |
| Take-off followed immediately by wear | 80.2% | 78.6% |
| Take-off followed by wear on the same slot | 59.4% | 58.8% |

These are **selected commands and slots**, not verified successful equipment changes. The captures do not include the intervening message, exact item identity or complete before/after game state. In particular, a matching slot does not prove an identical resulting state: turns pass, effects can trigger, discoveries can change, and recurrent memory changes.

One illustrative put-on event (sample 16180, agent 496, episode 8, step 3655) has value 89.5 before put-on, 86.5 before the following remove, and 74.0 on the next decision. Both immediate rewards are zero; the episode continues. Value stays around 73–76 for the next several actions. Other examples include take-off followed by wear with a positive advantage, and dangerous take-off selections shortly before episode termination. Full traces are in examples.json; these examples were selected by large gradient magnitude and are not population estimates.

This makes corrective action sequences a concrete lead. It does not establish a universal penalty for wearing a ring or taking off armour, nor show that all item choices have the same consequences.

## 3. A very small baseline recovers part of the benefit

Fit five deliberately small controls on source capture 31415: a constant, a multiple of V, a multiple of V times the inferred uniform-exploration probability, a multiple of V gated on verb probability below 1%, and a three-feature combination. The objective is item-logit gradient variance, with a small fixed regularizer and validation-only strength shrinkage. All features are available before sampling the item. Coefficients are then frozen for both other captures.

For the **single-coefficient V-only control**:

| Head | Ratio on 16180 | Ratio on 27182 |
|---|---:|---:|
| Put-on | 0.794 [0.745, 0.827] | 0.865 [0.698, 0.928] |
| Take-off | 0.861 [0.787, 0.914] | 0.920 [0.831, 0.950] |
| Quaff | 0.986 [0.980, 0.994] | 0.993 [0.987, 0.998] |
| Read | 0.987 [0.983, 0.992] | 0.988 [0.984, 0.993] |

Ratios below 1 are less variance. Intervals resample environment streams conditional on the fitted control. This was an exploratory follow-up, with no multiplicity adjustment or new training-seed replication.

Put-on's fitted correction is approximately `-0.00912 * V`; this is an empirical coefficient for this checkpoint, not a recommended universal training constant. A plain constant does much less for put-on (ratios 0.970 / 0.973, intervals including 1). Explicitly gating the V term on rare/exploratory verbs does not improve the replicated result over V alone. For take-off, even a constant captures a substantial part of the gain (0.883 / 0.914).

The complex critic is therefore not discovering uniquely complicated item effects in order to obtain every bit of the benefit. A broad value-dependent offset already explains some of it. Read and quaff have small but statistically detectable reductions under this simple estimator; those ~1% effects should not be described as useful learning gains.

## 4. Critic quality matters before clipping

The frozen shared neural critic from the recovery study, applied at strength 1 with no policy change or clipping, gives:

| Head | Ratio on 16180 | Ratio on 27182 |
|---|---:|---:|
| Put-on | 0.639 [0.523, 0.795] | 0.708 [0.436, 0.844] |
| Take-off | 0.792 [0.733, 0.843] | 0.867 [0.735, 0.924] |
| Quaff | 1.311 [1.082, 1.787] | 1.223 [1.061, 1.415] |
| Read | 0.986 [0.979, 0.994] | 0.986 [0.976, 0.997] |

Quaff's bad result is already present without PPO replay/clipping. Refitting only a scalar correction strength on validation streams reduces its ratios to 0.994 / 0.988; that mostly turns an unhelpful correction down rather than recovering a large improvement.

This offline shared critic is not the current online tanh critic. It uses different inputs/normalization/training and source snapshots. The result demonstrates an estimator failure mode and a usable diagnostic, not the measured source of the current online quaff result.

## 5. Controlled policy drift shows a strength failure mode

Perturb the normalized item query along three fixed random directions, retaining all masks. Add the resulting query/key logit difference to the logged distribution. Test relative query changes 0, .03, .1 and .3, plus small verb-logit shifts. Use the full changed verb+item probability divided by the actual old sampling probability, including epsilon. Keep advantage targets fixed so policy drift/clipping are isolated.

The original PPO policy-gradient term gets its normal clip gate. The zero-mean baseline correction remains ungated, matching the experimental design. Coefficients are either 1, the previously frozen offline coefficient, or a coefficient fitted on disjoint validation streams for the specified perturbation.

For query size .1, all tested put-on full-strength ratios with clipping remain below 1 (0.565–0.738). Take-off remains below 1 as well (0.761–0.860). Thus modest changes do not universally destroy the benefit. At size .3, put-on spans 0.621–3.258: reporting only a median would hide a real failure.

The strongest put-on failure in sample 27182 has mean item KL 0.0521, maximum sampled joint importance ratio 49.1, and only 2.19% of rows clipped. About 59.8% of the correction's squared magnitude is concentrated on those clipped rows.

| Correction strength | No clipping | PPO clipping |
|---|---:|---:|
| Full strength 1 | 2.913 | 3.258 |
| Previously frozen strength 0.363 | 0.907 | 0.951 |
| Validation-fitted strength for each condition | 0.914 | 0.924 |

The correction can therefore become too large under policy drift before clipping; clipping can further worsen the mismatch. Shrinking the control can prevent this in the controlled example. It would be incorrect to claim this proves the actual online failure was caused by clipping: actual per-example live advantages, changed features and importance ratios were not recorded.

This test uses double-precision probability calculations and fixed captured features/advantages. It does not reproduce BF16 PPO behavior-logprob rounding, recurrent-state changes, the live value updates, Muon or end-to-end training. Bootstrap intervals are supplied for the zero-drift case; the perturbed cases are sensitivity measurements rather than population-effect claims.

## What this suggests next

1. Judge and gate a baseline by **actual argument-gradient variance**, not only its regression MSE. Use a lagged or separately fitted per-head coefficient, frozen for the samples it corrects, so the correction remains independent of the current sampled item. Allow a head to receive no correction.
2. The online investigation still needs a small isolated capture of rollout/live advantages, baseline predictions, full importance ratios, clip gates and score norms on the same PPO rows. That would distinguish critic prediction error, value drift, ratio tails and clipping in the actual run. It was not added to the pinned queue.
3. To understand the game mechanism, log item descriptions, successful equipment changes, game turns, HP and messages around put-on/remove and take-off/wear sequences. The current files establish the selected command pattern but cannot establish the complete state change.

An unbiased control leaves the expected argument-gradient signal unchanged. It can reduce noise around that signal; it cannot repair a biased value target, change what the reward favors, or create a missing learning signal about which ring is useful. That distinction remains a plausible reason why offline variance reductions have not yet translated into better behavior or score, but an online causal test is still needed.

## Validation and artifacts

- trajectories.py and common.py: full trajectory joins; one-step residuals checked against corrected CUDA targets.
- checks_and_intervals.py: 2,976 independent reverse-recursion n-step return checks, including episode endings and right censoring; stream-clustered intervals for zero-drift controls.
- ppo_sensitivity.py: zero-drift logit variance matches saved reference values; explicit conditional enumeration confirms the importance-weighted baseline control has zero expected item gradient.
- undo_sequences.py: exact episode/step/verb joins for next-action slots.
- simple_controls.py: source-only coefficient fits and validation shrinkage; no actor updates.
- Raw outputs: trajectories.csv, undo_sequences.csv, examples.json, simple_controls.csv, simple_control_fits.json, ppo_sensitivity.csv, onpolicy_intervals.csv and numerical check JSONs.
- PLAN.md records the initial questions and scope. The simple-controls check was added after the trajectory findings and is labelled exploratory.

All scripts use one CPU numerical-library thread. No CUDA imports or GPU work were used.
