# Current figure data

## AutoAscend comparison

The current bars use our 2026-09-14 AutoAscend evaluation: median **5,527.5**, mean
**8,988.0484**, over **8,064 attempts** on the original Python challenge interface.
This includes 7,610 environment completions, 446 agent exceptions and eight
720-second timeouts. Exceptions and timeouts retain the last live score; none
were retried or excluded. Treating unfinished attempts as zero gives median
4,444 and mean 7,661.3157. These differ from the published 2021/2023 baselines,
which remain in the data as historical references.

Suggested caption: “AutoAscend evaluated for 8,064 attempts; each RL training
length pools two policies evaluated for 4,032 games each. AutoAscend exceptions
and 12-minute timeouts retain their last score, following its runner's attempt
accounting.”

Measured summary: `autoascend/results/summary.json`. Runner and protocol:
`autoascend/README.md`. Compared with this baseline, 4B RL achieves 2.08x median
and 2.19x mean score.

## Per-role depth

`roles_depth_mean.png` and `roles_depth_median.png` use the overnight
**depth-trained 2B policies**, seeds 801–808. They pool 80,000 fork-evaluated
episodes: 10,000 per policy after dropping each evaluation's first 4,000.
Depth is the deepest dungeon level reached in an episode; role statistics pool
individual episodes, rather than averaging per-seed medians. The score charts
continue to use the separate score-trained 1B/2B/4B policies.

Per-role counts, statistics, source paths and SHA-256 hashes are recorded in
`depth_policy_role_results.json`. These are fork evaluations, not Python
challenge certificates. No 1B depth-trained results are included in these charts.

## Medusa and Castle visitation

`landmark_reach_by_role.png` uses a separate, instrumented evaluation of the same
eight overnight depth-trained 2B policies. The two rates count actual entry into
Medusa's level and the Castle, using engine level identities, not depth cutoffs.
Entering a level does not imply defeating its enemies. Each seed contributes
10,000 episodes after dropping its first 4,000; the plot pools the 80,000 kept
episodes. Instrumentation and provenance are in `landmarks/`; the figure is only
rendered after all eight completed result artifacts have been validated.

## Supervised inventory encoder comparison

`inventory_encoder_supervised.png` shows three tasks from the 16-task benchmark:
item count, maximum known enchantment, and wielded known enchantment. Bars are
median test R² across three fit seeds; dark/light green distinguish absence or
presence of the equipped-item passthrough. Six architectures share input data
and a 16→64→64 per-item network, with sum/max/both pooling.

The figure uses only completed supervised fits. Frozen-policy probe results are
not included. Exact values and source hashes are in
`supervised_encoders/inventory/supervised_figure_data.json`. Rebuild with
`python3 resources/article/supervised_encoders/inventory/render_supervised.py`.
Suggested article prose and caption are in
`supervised_encoders/inventory/article_section.md`.
