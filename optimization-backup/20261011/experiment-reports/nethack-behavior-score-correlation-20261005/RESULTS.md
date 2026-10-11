# 1B NetHack ablation: behaviour versus score

Each observation is one independently trained policy. All 40 policies used the same
1B training length and fork evaluation protocol (2,000 retained games after 4,000 burn-in).
Original and repeat baseline cohorts are separate blocks within-arm, but one
baseline arm between arms. The single-seed no-RUN/SEARCH20 and no-verb-epsilon
experiments are excluded. The correlations and nominal p-values are exploratory;
only the separate 22-verb rate scans below apply a multiple-test correction.
Counters measure logged uses. Item verbs increment only after the item
selection succeeds; MOVE, DOWN, UP, and KICK never increment this counter.
The JSON includes within-block shuffle p-values (20,000 shuffles) and exact
between-arm permutation p-values (all 5,040 orderings).

`Within` = Pearson correlation of policy-level values after subtracting the
mean of each five-policy block (40 policies, eight blocks). `Between` = Pearson
correlation of seven arm means. Length rates divide logged uses by
policy decisions (episode length). Advancing rates divide by decisions
that advanced the game clock. Neither is a count of in-game turns.
Both rates use a factor of 1,000 and do not correct for depth/role mix.
The terminal BL_TIME field is zero in these logs, so true game-turn
totals cannot be recovered here. The prior report mislabelled advancing
decisions as game turns; this report corrects that denominator.

## Arm means

Medians below are averages of policy medians, not a pooled episode median.

| Arm | Policies | Mean score | Median score | Throws/game | Zaps/game | Casts/game | RUN/game |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 10 | 13634 | 8916 | 193.8 | 5.17 | 14.28 | 481.0 |
| no_handless | 5 | 13719 | 8873 | 223.5 | 5.24 | 14.85 | 597.6 |
| no_hostile_rays | 5 | 13416 | 8677 | 160.4 | 3.05 | 12.22 | 529.0 |
| no_item_strategy | 5 | 13435 | 8748 | 218.2 | 4.25 | 14.09 | 543.5 |
| zero_time_on | 5 | 13025 | 8564 | 182.9 | 3.46 | 14.22 | 474.6 |
| all_three_removed | 5 | 13426 | 8572 | 198.1 | 3.21 | 12.05 | 473.7 |
| no_nearby_pass | 5 | 13040 | 8584 | 216.7 | 4.46 | 15.86 | 523.3 |

## mean_score

| Behaviour | Within | Between | Pooled |
|---|---:|---:|---:|
| throw | +0.07 | +0.17 | +0.10 |
| zap | +0.10 | +0.48 | +0.22 |
| cast | -0.46 | -0.23 | -0.39 |
| run | +0.23 | +0.43 | +0.26 |
| search20 | +0.49 | +0.66 | +0.52 |
| wear | +0.25 | +0.70 | +0.33 |
| eat | +0.41 | +0.45 | +0.39 |
| read | +0.13 | +0.67 | +0.21 |
| pickup | -0.06 | +0.61 | +0.03 |
| apply | +0.03 | +0.03 | +0.00 |
| policy_steps | +0.66 | +0.76 | +0.68 |
| advancing_decisions | +0.68 | +0.80 | +0.71 |
| depth | +0.12 | +0.12 | +0.13 |
| xp | +0.58 | +0.78 | +0.64 |
| turnless_fraction | +0.13 | +0.46 | +0.21 |
| macro_illegal | +0.34 | +0.65 | +0.36 |
| throw_per_1k_policy_steps | -0.06 | +0.02 | -0.04 |
| zap_per_1k_policy_steps | +0.05 | +0.41 | +0.17 |
| cast_per_1k_policy_steps | -0.56 | -0.39 | -0.51 |
| run_per_1k_policy_steps | +0.14 | +0.28 | +0.16 |
| search20_per_1k_policy_steps | -0.22 | -0.28 | -0.26 |
| throw_per_1k_advancing_decisions | -0.05 | +0.05 | -0.02 |
| zap_per_1k_advancing_decisions | +0.06 | +0.42 | +0.18 |
| cast_per_1k_advancing_decisions | -0.55 | -0.36 | -0.49 |
| run_per_1k_advancing_decisions | +0.15 | +0.31 | +0.17 |
| search20_per_1k_advancing_decisions | -0.20 | -0.14 | -0.21 |

## median_score

| Behaviour | Within | Between | Pooled |
|---|---:|---:|---:|
| throw | -0.18 | +0.26 | -0.09 |
| zap | -0.01 | +0.78 | +0.18 |
| cast | -0.47 | +0.22 | -0.34 |
| run | +0.01 | +0.45 | +0.06 |
| search20 | +0.42 | +0.24 | +0.37 |
| wear | +0.13 | +0.35 | +0.18 |
| eat | +0.34 | +0.05 | +0.25 |
| read | -0.02 | +0.39 | +0.03 |
| pickup | -0.14 | +0.78 | -0.01 |
| apply | -0.05 | +0.20 | -0.05 |
| policy_steps | +0.42 | +0.53 | +0.43 |
| advancing_decisions | +0.40 | +0.58 | +0.43 |
| depth | +0.19 | +0.41 | +0.24 |
| xp | +0.64 | +0.83 | +0.69 |
| turnless_fraction | +0.17 | +0.25 | +0.18 |
| macro_illegal | +0.10 | +0.86 | +0.20 |
| throw_per_1k_policy_steps | -0.28 | +0.17 | -0.19 |
| zap_per_1k_policy_steps | -0.04 | +0.75 | +0.14 |
| cast_per_1k_policy_steps | -0.53 | +0.08 | -0.41 |
| run_per_1k_policy_steps | -0.06 | +0.38 | -0.01 |
| search20_per_1k_policy_steps | -0.00 | -0.41 | -0.11 |
| throw_per_1k_advancing_decisions | -0.27 | +0.18 | -0.17 |
| zap_per_1k_advancing_decisions | -0.04 | +0.75 | +0.14 |
| cast_per_1k_advancing_decisions | -0.52 | +0.10 | -0.40 |
| run_per_1k_advancing_decisions | -0.05 | +0.39 | -0.00 |
| search20_per_1k_advancing_decisions | +0.07 | -0.42 | -0.05 |

## Within each five-policy block (mean score)

| Behaviour | baseline_original | baseline_repeat | no_handless | no_hostile_rays | no_item_strategy | zero_time_on | all_three_removed | no_nearby_pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| throw | +0.30 | -1.00 | +0.66 | -0.07 | -0.14 | +0.79 | +0.11 | +0.16 |
| zap | -0.21 | -0.29 | -0.25 | +0.40 | +0.48 | +0.17 | +0.06 | +0.24 |
| cast | +0.72 | -0.13 | -0.85 | -0.62 | -0.56 | +0.12 | -0.49 | -0.16 |
| run | +0.68 | -0.12 | +0.32 | +0.42 | -0.72 | +0.20 | +0.70 | +0.62 |
| search20 | +0.47 | +0.77 | +0.46 | -0.92 | +0.78 | +0.48 | +0.98 | +0.57 |
| wear | +0.18 | +0.76 | -0.28 | +0.54 | +0.62 | +0.27 | -0.12 | +0.22 |
| eat | -0.04 | -0.37 | +0.54 | -0.48 | +0.54 | +0.12 | +0.93 | +0.66 |
| read | +0.39 | +0.41 | +0.44 | +0.20 | -0.31 | -0.85 | -0.13 | +0.47 |
| pickup | +0.65 | -0.18 | +0.56 | +0.07 | -0.89 | +0.43 | -0.21 | +0.39 |
| apply | +0.26 | +0.01 | -0.25 | +0.09 | +0.70 | -0.60 | +0.07 | -0.08 |
| policy_steps | +0.61 | +0.88 | +0.64 | +0.36 | +0.56 | +0.89 | +0.91 | +0.87 |
| advancing_decisions | +0.42 | +0.79 | +0.79 | +0.27 | +0.60 | +0.88 | +0.92 | +0.86 |
| depth | +0.15 | +0.16 | +0.01 | +0.55 | +0.83 | +0.21 | -0.28 | -0.06 |
| xp | -0.22 | +0.33 | +0.94 | +0.76 | +0.85 | +0.37 | +0.53 | +0.76 |
| turnless_fraction | +0.40 | +0.31 | -0.09 | +0.41 | +0.25 | +0.68 | -0.29 | +0.58 |
| macro_illegal | +0.32 | +0.33 | +0.90 | +0.04 | +0.82 | +0.62 | +0.69 | +0.57 |
| throw_per_1k_policy_steps | +0.26 | -1.00 | +0.58 | -0.23 | -0.30 | +0.75 | -0.06 | -0.18 |
| zap_per_1k_policy_steps | -0.26 | -0.34 | -0.32 | +0.40 | +0.46 | +0.11 | -0.03 | +0.18 |

## Checks on interpretation

The within-block score correlations for throws and zaps are near zero
even though both actions fall when hostile-ray masking is removed.
Between seven arm means, zaps correlate with median score (r=+0.78),
but the exact two-sided permutation p-value is 0.050; this is suggestive
with only seven design variants. Using only the original five-policy
baseline cohort instead of both baseline cohorts gives r=+0.73.

Mean score correlates with episode policy-step length (within r=+0.66).
Raw SEARCH20/game rises with mean score (within r=+0.49), but its
per-1,000-policy-step correlation is -0.22; eating changes from +0.41
to approximately zero. Those count correlations mainly track length.
Length-normalized casts and prayers remain inverse to mean score
(r=-0.56 and -0.55, FDR q=0.026 each across 22 logged verbs).
Cast rate is also inverse to median score (r=-0.53, q=0.042).
This is association, not evidence that casting or praying causes
lower score; a struggling policy may do more of both.
Uniformly averaging each role's episode means changes the within-arm
correlations little: throw +0.07, zap +0.13, cast -0.46, RUN +0.21,
SEARCH20 +0.49. Role mix does not explain the main patterns.

Every individual-block correlation uses only five policies; a large
coefficient in one block is especially unstable. The rate scan and
between-arm permutations do not establish that an action causes a score
change. Different ablations can shift several behaviours at once.


## All verbs

The machine-readable [correlations.json](correlations.json) includes all
26 verbs, both rate denominators, score outcomes, and block correlations.
[policies.csv](policies.csv) contains the 40 policy-level observations.
