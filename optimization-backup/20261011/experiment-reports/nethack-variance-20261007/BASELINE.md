# Existing 1B baseline variance

Five independent training seeds, same archived source, engine and 1B step budget. Each final checkpoint was evaluated on the same 6,000-game fork protocol; the first 4,000 completed games were discarded and the next 2,000 retained.

| Seed | Mean score | Median score | Mean max depth | BALROG mean % |
|---:|---:|---:|---:|---:|
| 2901 | 13199 | 8820 | 3.55 | 9.53 |
| 2902 | 13438 | 9029 | 3.25 | 9.56 |
| 2903 | 13422 | 8656 | 3.94 | 10.19 |
| 2904 | 13398 | 8566 | 4.07 | 10.64 |
| 2905 | 13364 | 8902 | 3.73 | 10.40 |

| Metric | Mean across seeds | Seed SD | 95% t interval for mean |
|---|---:|---:|---:|
| mean_score | 13363.93 | 96.59 | [13243.99, 13483.87] |
| median_score | 8794.70 | 186.22 | [8563.48, 9025.92] |
| mean_max_depth | 3.71 | 0.32 | [3.31, 4.11] |
| mean_balrog_pct | 10.06 | 0.50 | [9.44, 10.69] |

The interval describes the mean over training seeds, not the uncertainty of each 2,000-game evaluation. All policies used the same evaluation seed, but the completion-order episode logs do not establish game-by-game pairing. A future 250M-step screening experiment needs its own matched-checkpoint baseline evaluations; the 1B numbers above must not stand in for that shorter budget.
