# Where armour readout deteriorates

Frozen RL encoders; supervised readouts only. Same held-out armour candidate configurations as preceding test. Nested distractor sets preserve the same two armour items. Compare pre-ReLU, slot ReLU, MLP1 ReLU, MLP2 ReLU, and aggregation. Pool+worn uses actual pre-MLP worn-mean bypass. Paired vectors and raw public inputs are diagnostic controls, not current recurrent-policy inputs.

| Policy | Target | Stage | Distractors | Readout | Accuracy | Balanced accuracy |
|---|---|---|---:|---|---:|---:|
| identify1b_s701 | enchantment | pre16 | paired / individual | linear | 62.13% | 62.91% |
| identify1b_s701 | enchantment | pre16 | paired / individual | MLP | 92.92% | 93.82% |
| identify1b_s701 | ac_upgrade | pre16 | paired / individual | linear | 94.72% | 94.69% |
| identify1b_s701 | ac_upgrade | pre16 | paired / individual | MLP | 98.58% | 98.59% |
| identify1b_s701 | known_noncursed_ac_upgrade | pre16 | paired / individual | linear | 95.42% | 87.55% |
| identify1b_s701 | known_noncursed_ac_upgrade | pre16 | paired / individual | MLP | 98.89% | 97.63% |
| identify1b_s701 | enchantment | slot16 | paired / individual | linear | 37.04% | 37.22% |
| identify1b_s701 | enchantment | slot16 | paired / individual | MLP | 42.04% | 42.08% |
| identify1b_s701 | ac_upgrade | slot16 | paired / individual | linear | 91.28% | 91.22% |
| identify1b_s701 | ac_upgrade | slot16 | paired / individual | MLP | 93.64% | 93.61% |
| identify1b_s701 | known_noncursed_ac_upgrade | slot16 | paired / individual | linear | 89.33% | 64.63% |
| identify1b_s701 | known_noncursed_ac_upgrade | slot16 | paired / individual | MLP | 94.51% | 84.76% |
| identify1b_s701 | enchantment | mlp1_64 | paired / individual | linear | 37.31% | 37.27% |
| identify1b_s701 | enchantment | mlp1_64 | paired / individual | MLP | 38.56% | 38.53% |
| identify1b_s701 | ac_upgrade | mlp1_64 | paired / individual | linear | 91.42% | 91.41% |
| identify1b_s701 | ac_upgrade | mlp1_64 | paired / individual | MLP | 92.21% | 92.19% |
| identify1b_s701 | known_noncursed_ac_upgrade | mlp1_64 | paired / individual | linear | 89.86% | 68.27% |
| identify1b_s701 | known_noncursed_ac_upgrade | mlp1_64 | paired / individual | MLP | 92.79% | 79.44% |
| identify1b_s701 | enchantment | mlp2_64 | paired / individual | linear | 18.74% | 19.03% |
| identify1b_s701 | enchantment | mlp2_64 | paired / individual | MLP | 19.39% | 20.11% |
| identify1b_s701 | ac_upgrade | mlp2_64 | paired / individual | linear | 77.00% | 76.67% |
| identify1b_s701 | ac_upgrade | mlp2_64 | paired / individual | MLP | 78.16% | 77.87% |
| identify1b_s701 | known_noncursed_ac_upgrade | mlp2_64 | paired / individual | linear | 87.89% | 57.79% |
| identify1b_s701 | known_noncursed_ac_upgrade | mlp2_64 | paired / individual | MLP | 88.42% | 63.57% |
| identify1b_s701 | enchantment | public_input | paired / individual | linear | 50.40% | 50.89% |
| identify1b_s701 | enchantment | public_input | paired / individual | MLP | 92.11% | 92.78% |
| identify1b_s701 | ac_upgrade | public_input | paired / individual | linear | 96.88% | 96.88% |
| identify1b_s701 | ac_upgrade | public_input | paired / individual | MLP | 97.11% | 97.14% |
| identify1b_s701 | known_noncursed_ac_upgrade | public_input | paired / individual | linear | 97.89% | 95.65% |
| identify1b_s701 | known_noncursed_ac_upgrade | public_input | paired / individual | MLP | 98.64% | 96.95% |
| identify1b_s701 | ac_upgrade | summax | 0 | linear | 68.75% | 68.08% |
| identify1b_s701 | ac_upgrade | summax | 0 | MLP | 71.66% | 70.96% |
| identify1b_s701 | ac_upgrade | summax_plus_worn | 0 | linear | 85.32% | 85.22% |
| identify1b_s701 | ac_upgrade | summax_plus_worn | 0 | MLP | 84.84% | 84.75% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax | 0 | linear | 87.77% | 52.31% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax | 0 | MLP | 88.50% | 59.88% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 0 | linear | 89.05% | 62.20% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 0 | MLP | 90.49% | 72.24% |
| identify1b_s701 | ac_upgrade | summax | 2 | linear | 68.36% | 67.67% |
| identify1b_s701 | ac_upgrade | summax | 2 | MLP | 68.06% | 67.46% |
| identify1b_s701 | ac_upgrade | summax_plus_worn | 2 | linear | 85.02% | 84.93% |
| identify1b_s701 | ac_upgrade | summax_plus_worn | 2 | MLP | 84.29% | 84.15% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax | 2 | linear | 87.61% | 52.02% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax | 2 | MLP | 87.96% | 54.96% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 2 | linear | 89.05% | 62.33% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 2 | MLP | 90.00% | 65.95% |
| identify1b_s701 | ac_upgrade | summax | 6 | linear | 67.81% | 67.09% |
| identify1b_s701 | ac_upgrade | summax | 6 | MLP | 67.71% | 67.11% |
| identify1b_s701 | ac_upgrade | summax_plus_worn | 6 | linear | 83.64% | 83.50% |
| identify1b_s701 | ac_upgrade | summax_plus_worn | 6 | MLP | 83.00% | 82.88% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax | 6 | linear | 87.65% | 51.64% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax | 6 | MLP | 87.79% | 52.59% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 6 | linear | 88.28% | 59.82% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 6 | MLP | 89.27% | 66.60% |
| identify1b_s701 | ac_upgrade | summax | 14 | linear | 67.85% | 67.10% |
| identify1b_s701 | ac_upgrade | summax | 14 | MLP | 67.39% | 66.79% |
| identify1b_s701 | ac_upgrade | summax_plus_worn | 14 | linear | 84.05% | 83.95% |
| identify1b_s701 | ac_upgrade | summax_plus_worn | 14 | MLP | 82.43% | 82.24% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax | 14 | linear | 87.35% | 50.80% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax | 14 | MLP | 87.71% | 52.21% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 14 | linear | 88.44% | 60.44% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 14 | MLP | 88.93% | 61.60% |
| identify1b_s701 | ac_upgrade | summax | 30 | linear | 67.53% | 66.77% |
| identify1b_s701 | ac_upgrade | summax | 30 | MLP | 66.54% | 65.97% |
| identify1b_s701 | ac_upgrade | summax_plus_worn | 30 | linear | 83.81% | 83.68% |
| identify1b_s701 | ac_upgrade | summax_plus_worn | 30 | MLP | 82.00% | 81.81% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax | 30 | linear | 87.57% | 51.26% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax | 30 | MLP | 87.61% | 52.15% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 30 | linear | 88.68% | 61.38% |
| identify1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 30 | MLP | 88.60% | 60.80% |
| identify1b_s701 | ac_upgrade | sum_only | 6 | linear | 65.42% | 64.72% |
| identify1b_s701 | ac_upgrade | sum_only | 6 | MLP | 66.94% | 66.38% |
| identify1b_s701 | ac_upgrade | max_only | 6 | linear | 66.09% | 65.31% |
| identify1b_s701 | ac_upgrade | max_only | 6 | MLP | 67.08% | 66.37% |
| idreplace1b_s701 | enchantment | pre16 | paired / individual | linear | 57.33% | 57.44% |
| idreplace1b_s701 | enchantment | pre16 | paired / individual | MLP | 97.17% | 97.28% |
| idreplace1b_s701 | ac_upgrade | pre16 | paired / individual | linear | 92.47% | 92.43% |
| idreplace1b_s701 | ac_upgrade | pre16 | paired / individual | MLP | 98.20% | 98.22% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | pre16 | paired / individual | linear | 94.80% | 85.93% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | pre16 | paired / individual | MLP | 98.62% | 97.00% |
| idreplace1b_s701 | enchantment | slot16 | paired / individual | linear | 43.91% | 43.87% |
| idreplace1b_s701 | enchantment | slot16 | paired / individual | MLP | 56.19% | 55.12% |
| idreplace1b_s701 | ac_upgrade | slot16 | paired / individual | linear | 89.21% | 89.20% |
| idreplace1b_s701 | ac_upgrade | slot16 | paired / individual | MLP | 92.00% | 92.03% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | slot16 | paired / individual | linear | 90.91% | 72.48% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | slot16 | paired / individual | MLP | 95.85% | 89.94% |
| idreplace1b_s701 | enchantment | mlp1_64 | paired / individual | linear | 26.36% | 26.21% |
| idreplace1b_s701 | enchantment | mlp1_64 | paired / individual | MLP | 26.56% | 26.51% |
| idreplace1b_s701 | ac_upgrade | mlp1_64 | paired / individual | linear | 83.79% | 83.79% |
| idreplace1b_s701 | ac_upgrade | mlp1_64 | paired / individual | MLP | 85.59% | 85.57% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | mlp1_64 | paired / individual | linear | 90.16% | 69.11% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | mlp1_64 | paired / individual | MLP | 91.05% | 73.76% |
| idreplace1b_s701 | enchantment | mlp2_64 | paired / individual | linear | 14.33% | 14.46% |
| idreplace1b_s701 | enchantment | mlp2_64 | paired / individual | MLP | 13.00% | 12.23% |
| idreplace1b_s701 | ac_upgrade | mlp2_64 | paired / individual | linear | 64.80% | 64.30% |
| idreplace1b_s701 | ac_upgrade | mlp2_64 | paired / individual | MLP | 65.65% | 65.19% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | mlp2_64 | paired / individual | linear | 88.10% | 57.65% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | mlp2_64 | paired / individual | MLP | 88.46% | 59.85% |
| idreplace1b_s701 | enchantment | public_input | paired / individual | linear | 50.40% | 50.89% |
| idreplace1b_s701 | enchantment | public_input | paired / individual | MLP | 92.11% | 92.78% |
| idreplace1b_s701 | ac_upgrade | public_input | paired / individual | linear | 96.88% | 96.88% |
| idreplace1b_s701 | ac_upgrade | public_input | paired / individual | MLP | 97.11% | 97.14% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | public_input | paired / individual | linear | 97.89% | 95.65% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | public_input | paired / individual | MLP | 98.64% | 96.95% |
| idreplace1b_s701 | ac_upgrade | summax | 0 | linear | 59.60% | 58.56% |
| idreplace1b_s701 | ac_upgrade | summax | 0 | MLP | 61.26% | 60.48% |
| idreplace1b_s701 | ac_upgrade | summax_plus_worn | 0 | linear | 76.80% | 76.72% |
| idreplace1b_s701 | ac_upgrade | summax_plus_worn | 0 | MLP | 78.14% | 78.12% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax | 0 | linear | 87.92% | 52.93% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax | 0 | MLP | 88.32% | 54.90% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 0 | linear | 88.87% | 58.82% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 0 | MLP | 89.58% | 63.04% |
| idreplace1b_s701 | ac_upgrade | summax | 2 | linear | 58.14% | 57.14% |
| idreplace1b_s701 | ac_upgrade | summax | 2 | MLP | 59.21% | 58.60% |
| idreplace1b_s701 | ac_upgrade | summax_plus_worn | 2 | linear | 77.11% | 77.05% |
| idreplace1b_s701 | ac_upgrade | summax_plus_worn | 2 | MLP | 77.08% | 77.08% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax | 2 | linear | 88.06% | 53.21% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax | 2 | MLP | 87.79% | 52.25% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 2 | linear | 88.83% | 58.87% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 2 | MLP | 89.01% | 60.57% |
| idreplace1b_s701 | ac_upgrade | summax | 6 | linear | 58.28% | 57.28% |
| idreplace1b_s701 | ac_upgrade | summax | 6 | MLP | 57.59% | 57.06% |
| idreplace1b_s701 | ac_upgrade | summax_plus_worn | 6 | linear | 77.31% | 77.26% |
| idreplace1b_s701 | ac_upgrade | summax_plus_worn | 6 | MLP | 77.19% | 77.14% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax | 6 | linear | 88.02% | 53.32% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax | 6 | MLP | 87.61% | 51.68% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 6 | linear | 88.46% | 57.98% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 6 | MLP | 89.19% | 60.21% |
| idreplace1b_s701 | ac_upgrade | summax | 14 | linear | 57.81% | 56.86% |
| idreplace1b_s701 | ac_upgrade | summax | 14 | MLP | 57.15% | 56.42% |
| idreplace1b_s701 | ac_upgrade | summax_plus_worn | 14 | linear | 77.63% | 77.58% |
| idreplace1b_s701 | ac_upgrade | summax_plus_worn | 14 | MLP | 76.03% | 75.95% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax | 14 | linear | 87.96% | 53.62% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax | 14 | MLP | 87.67% | 52.25% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 14 | linear | 88.48% | 58.86% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 14 | MLP | 88.79% | 58.11% |
| idreplace1b_s701 | ac_upgrade | summax | 30 | linear | 57.17% | 56.21% |
| idreplace1b_s701 | ac_upgrade | summax | 30 | MLP | 56.62% | 55.73% |
| idreplace1b_s701 | ac_upgrade | summax_plus_worn | 30 | linear | 77.11% | 77.05% |
| idreplace1b_s701 | ac_upgrade | summax_plus_worn | 30 | MLP | 76.19% | 76.07% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax | 30 | linear | 88.10% | 54.24% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax | 30 | MLP | 87.69% | 52.66% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 30 | linear | 88.87% | 59.22% |
| idreplace1b_s701 | known_noncursed_ac_upgrade | summax_plus_worn | 30 | MLP | 88.46% | 57.18% |
| idreplace1b_s701 | ac_upgrade | sum_only | 6 | linear | 57.89% | 56.67% |
| idreplace1b_s701 | ac_upgrade | sum_only | 6 | MLP | 57.29% | 56.67% |
| idreplace1b_s701 | ac_upgrade | max_only | 6 | linear | 57.55% | 56.37% |
| idreplace1b_s701 | ac_upgrade | max_only | 6 | MLP | 57.53% | 56.81% |

Interpretation: changes in readout accuracy locate difficulty for these probes, not proven information loss. The readout is trained separately at each inventory size. The known-noncursed target is imbalanced, so use balanced accuracy (chance 50%). Exact enchantment classification penalizes being off by one. Synthetic common body armour does not cover resistances, weight, casting penalties or the full recurrent state. This does not test a wider RL-trained encoder.
