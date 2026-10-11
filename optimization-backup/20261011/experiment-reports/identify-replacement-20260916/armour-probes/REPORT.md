# Armour readouts

Frozen trained encoders; only readouts train. Common body armour with fixed appearances, known type and enchantment. Held-out candidate type/enchantment/BUC/erosion combinations. Comparison is AC only, not optimal equipment choice. Six non-armour distractors. Actual worn-mean bypass tested alongside pool.

| Policy | Target | Representation | Readout | Accuracy | Balanced accuracy |
|---|---|---|---|---:|---:|
| identify1b_s701 | type | individual | linear | 82.61% | 82.79% |
| identify1b_s701 | type | individual | MLP | 97.00% | 97.02% |
| identify1b_s701 | enchantment | individual | linear | 37.04% | 37.22% |
| identify1b_s701 | enchantment | individual | MLP | 42.04% | 42.08% |
| identify1b_s701 | buc | individual | linear | 73.95% | 73.36% |
| identify1b_s701 | buc | individual | MLP | 94.37% | 94.45% |
| identify1b_s701 | ac_upgrade | pair | linear | 91.28% | 91.22% |
| identify1b_s701 | ac_upgrade | pair | MLP | 93.64% | 93.61% |
| identify1b_s701 | ac_upgrade | pooled | linear | 67.81% | 67.09% |
| identify1b_s701 | ac_upgrade | pooled | MLP | 67.79% | 67.22% |
| identify1b_s701 | ac_upgrade | pooled_with_worn | linear | 83.64% | 83.50% |
| identify1b_s701 | ac_upgrade | pooled_with_worn | MLP | 83.06% | 82.94% |
| identify1b_s701 | known_noncursed_ac_upgrade | pair | linear | 89.33% | 64.63% |
| identify1b_s701 | known_noncursed_ac_upgrade | pair | MLP | 94.51% | 84.76% |
| identify1b_s701 | known_noncursed_ac_upgrade | pooled | linear | 87.65% | 51.64% |
| identify1b_s701 | known_noncursed_ac_upgrade | pooled | MLP | 87.81% | 52.67% |
| identify1b_s701 | known_noncursed_ac_upgrade | pooled_with_worn | linear | 88.28% | 59.82% |
| identify1b_s701 | known_noncursed_ac_upgrade | pooled_with_worn | MLP | 89.17% | 66.34% |
| idreplace1b_s701 | type | individual | linear | 83.74% | 84.15% |
| idreplace1b_s701 | type | individual | MLP | 98.66% | 98.93% |
| idreplace1b_s701 | enchantment | individual | linear | 43.91% | 43.87% |
| idreplace1b_s701 | enchantment | individual | MLP | 56.19% | 55.12% |
| idreplace1b_s701 | buc | individual | linear | 81.26% | 80.81% |
| idreplace1b_s701 | buc | individual | MLP | 98.00% | 97.95% |
| idreplace1b_s701 | ac_upgrade | pair | linear | 89.21% | 89.20% |
| idreplace1b_s701 | ac_upgrade | pair | MLP | 92.00% | 92.03% |
| idreplace1b_s701 | ac_upgrade | pooled | linear | 58.28% | 57.28% |
| idreplace1b_s701 | ac_upgrade | pooled | MLP | 57.73% | 57.18% |
| idreplace1b_s701 | ac_upgrade | pooled_with_worn | linear | 77.29% | 77.24% |
| idreplace1b_s701 | ac_upgrade | pooled_with_worn | MLP | 77.33% | 77.28% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | pair | linear | 90.91% | 72.48% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | pair | MLP | 95.85% | 89.94% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | pooled | linear | 88.02% | 53.32% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | pooled | MLP | 87.61% | 51.68% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | pooled_with_worn | linear | 88.46% | 57.98% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | pooled_with_worn | MLP | 89.17% | 60.33% |

The pair representation supplies both item vectors explicitly and is a diagnostic upper-path control, not an input currently supplied to the recurrent policy. pooled_with_worn includes the actual worn-mean bypass (equal to the worn suit in these fixtures). Accuracy does not establish policy use or optimal armour choice. No new RL training.
