# Online variance-reduction audit: first completed paired seed (4101)

The correction reduces some logged argument-gradient variance. The selective takeoff/puton arm has the clearest puton signal, but this has not produced a demonstrated learning or score improvement. The all-argument arm is mixed, and its puton benefit does not persist in the final quarter. All three actors trained from scratch to 999,817,216 steps.

## What was measured

For each recorded active-head gradient, the trainer stores both the original PPO policy gradient and the gradient after the correction, on exactly the same training row and current policy. This is a within-run counterfactual: it does not compare gradient variance across different trained policies. We calculate the trace of covariance, E[||g||²] − ||E[g]||². Ratios below 1 mean less variance. These are **logit-space policy-gradient diagnostics**, excluding entropy and the value loss, not full actor parameter gradients or optimizer-update variance. Both PPO clipping and the added IS correction are included.
Rows are sampled at nt % 64 == 0, i.e. fixed positions within each 512-step horizon, not a random sample of all positions. Minibatch replay repeats observations. Counts below are sampled training-row uses, not independent actions or games. Game IDs are absent, so game-clustered uncertainty cannot be recovered. Reported ratios are descriptive, with no significance claim.

## Whole-run ratios

| Head | All arguments ratio | Selective ratio | All-arm sampled uses | Selective sampled uses |
|---|---:|---:|---:|---:|
| verb | 1.000 | 1.000 | 27,582,848 | 27,582,848 |
| wear item | 1.013 | 1.000 | 127,829 | 126,909 |
| eat item | 1.010 | 1.000 | 660,777 | 622,725 |
| quaff item | 0.898 | 1.000 | 41,394 | 43,560 |
| throw item | 0.998 | 1.000 | 1,714,543 | 1,623,613 |
| zap item | 0.979 | 1.000 | 24,504 | 32,203 |
| takeoff item | 0.940 | 0.928 | 52,381 | 32,840 |
| puton item | 0.810 | 0.608 | 3,285 | 3,228 |
| remove item | 0.992 | 1.000 | 3,142 | 2,637 |
| wield item | 0.881 | 1.000 | 95,094 | 85,569 |
| apply item | 1.079 | 1.000 | 93,559 | 47,100 |
| read item | 1.054 | 1.000 | 30,569 | 37,004 |
| drop item | 0.836 | 1.000 | 298,484 | 275,528 |
| move direction | 0.984 | 1.000 | 5,159,719 | 5,706,472 |
| run direction | 0.998 | 1.000 | 5,732,575 | 5,287,798 |
| kick direction | 1.017 | 1.000 | 311,256 | 232,228 |
| throw direction | 1.011 | 1.000 | 1,714,543 | 1,623,613 |
| zap/cast direction | 1.343 | 1.000 | 162,518 | 180,588 |
| apply direction | 1.181 | 1.000 | 93,559 | 47,100 |
| spell | 0.926 | 1.000 | 138,014 | 148,385 |

Verb variance stays unchanged to numerical precision. Every head in the control and every unmodified head in the selective arm has ratio 1, validating the logged comparisons.

## Training-stage dependence

| Arm / item head | 0–250M | 250–500M | 500–750M | 750–1,000M |
|---|---:|---:|---:|---:|
| all_arguments / takeoff item | 1.100 | 0.655 | 0.964 | 0.903 |
| all_arguments / puton item | 2.451 | 0.652 | 3.857 | 8.854 |
| takeoff_puton / takeoff item | 1.088 | 0.935 | 0.631 | 0.894 |
| takeoff_puton / puton item | 0.834 | 0.637 | 0.540 | 0.383 |
| all_arguments / wield item | 0.835 | 0.852 | 0.932 | 0.950 |
| all_arguments / quaff item | 1.005 | 0.871 | 1.174 | 1.011 |

The selective puton ratio improves in every broad quarter (0.834 → 0.637 → 0.540 → 0.383), but the last quarter contains just 172 logged active-head uses, including replay. The all-argument arm’s puton ratio reaches 8.854 in its final quarter, from 137 logged uses. Do not interpret either late estimate as a precise population effect.

## Outliers and pooling

For an outlier sensitivity check, partition each run into non-overlapping 64-epoch windows (~16.8M steps), center within each window, and pool the resulting variance sums. Then discard the three windows with the largest original-gradient variance contribution. This is a descriptive sensitivity check, not a prespecified statistical test.

| Arm / head | Pooled within-window ratio | Ratio after dropping top 3 windows | Largest window share of original variance |
|---|---:|---:|---:|
| takeoff_puton / takeoff item | 0.928 | 0.971 | 26.1% |
| takeoff_puton / puton item | 0.611 | 0.653 | 48.9% |
| all_arguments / takeoff item | 0.940 | 0.862 | 75.3% |
| all_arguments / puton item | 0.806 | 1.816 | 38.1% |
| all_arguments / wield item | 0.881 | 0.898 | 25.9% |
| all_arguments / quaff item | 0.898 | 1.065 | 84.6% |
| all_arguments / drop item | 0.836 | 1.021 | 99.8% |

The selective puton reduction survives this removal (~35% less variance). The all-arm puton and quaff reductions do not. The apparent drop-head reduction is dominated by one window carrying 99.8% of its original gradient variance; it should not be called a broad success. Wield is a more consistent all-arm improvement across quarters and this outlier check.
Pooling within individual epochs gives different rare-head ratios (selective puton 0.881 overall, 1.757 in the final quarter). Many such epochs contain few or zero puton audit rows, and repeated observations from PPO replay are not independent. Very small within-epoch samples are not a reliable substitute for the missing independent-game or parameter-gradient audit. Both summaries are supplied in heads.csv rather than selecting the most favorable one.

## Critic prediction versus gradient variance

In the final quarter, the all-arm puton predictor reduces raw residual squared error to 0.577 of the zero predictor while its sampled gradient variance is higher. Fitting residual MSE is therefore not sufficient to guarantee lower variance of the actual clipped PPO gradient. The online correction has fixed strength 1 and is not fitted to the score-weighted, clipping-dependent gradient objective. This is a plausible reason to investigate, not a demonstrated cause from the aggregate logs.
Independent of gradient diagnostics, the first-seed evaluation scores were control mean 14,085, all-argument mean 13,438, and selective mean 12,619 (10,000 retained games each after 4,000 burn-in). There is no demonstrated score benefit so far. More paired training seeds are needed.

The active queue and pinned source/config were left unchanged. Raw calculations: heads.csv, critic.csv, windows.csv.
