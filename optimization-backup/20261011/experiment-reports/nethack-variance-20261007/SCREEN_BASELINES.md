# Baseline at 262.144M steps

Five independent training seeds. Each checkpoint was evaluated for 6,000 fork-engine games with evaluation seed 7; the first 4,000 completed games were discarded and the next 2,000 retained.

| Seed | Mean score | Median score | Mean max depth |
|---:|---:|---:|---:|
| 2901 | 5457 | 3688 | 3.11 |
| 2902 | 5861 | 3778 | 2.52 |
| 2903 | 5851 | 3646 | 3.26 |
| 2904 | 6058 | 3759 | 2.71 |
| 2905 | 4754 | 3018 | 3.12 |

| Metric | Mean across seeds | Seed SD | 95% t interval for mean |
|---|---:|---:|---:|
| mean_score | 5596.09 | 518.96 | [4951.71, 6240.46] |
| median_score | 3577.60 | 317.64 | [3183.20, 3972.00] |
| mean_max_depth | 2.95 | 0.31 | [2.56, 3.33] |

The confidence interval describes variation across the five trained policies, not the sampling error of each 2,000-game evaluation. Completion-order logs do not support per-game pairing even though the evaluation seed is fixed.
