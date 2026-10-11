# Online argument-baseline experiment

Four paired seeds, each run from scratch for 1B requested steps. Order per seed: control → all consumed argument heads → takeoff/puton.

Fresh evaluation per model: first 4,000 completions discarded, next 10,000 retained. The auxiliary critic is disabled during evaluation.

| Arm | Seed | Mean score | Median score | Mean max depth | BALROG % | Training seconds |
|---|---:|---:|---:|---:|---:|---:|
| control | 4101 | 14085 | 8899 | 3.67 | 10.29 | 8671 |
| all_arguments | 4101 | 13438 | 8238 | 4.23 | 10.81 | 9011 |
| takeoff_puton | 4101 | 12619 | 8917 | 3.13 | 9.40 | 9081 |
| control | 4102 | 12714 | 8112 | 4.02 | 10.03 | 8601 |
| all_arguments | 4102 | 13287 | 8640 | 3.21 | 9.43 | 8891 |

Do not interpret an arm from one seed. Report paired differences across complete seed triplets; evaluation episode intervals do not replace between-training-seed uncertainty.
Training time includes startup and graph capture. Equal-step screening is reported alongside actual wall clock; it is not an equal-wall-clock learning experiment.
BALROG is the depth/XP lookup only. Per-action use counts are in runs/*/results.json.
