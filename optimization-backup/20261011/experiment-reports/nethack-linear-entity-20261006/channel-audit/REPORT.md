# Inventory entity channel audit

Four completed 1B `linear_entity` checkpoints (seeds 2901–2904) were compared with the four matched baseline checkpoints. For each pair, the same observations came from a baseline-driven CPU rollout at two game seeds (811 and 1447), 4,000 decisions each, sampled every eight decisions. This produced 146,035 occupied inventory-slot rows across the eight pair/trajectory combinations. Each channel is counted as dead if it was exactly zero on every occupied slot in that combination. The table averages channel counts across those eight combinations.

| Inventory stage | Baseline dead / 64 | Linear-output dead / 64 | Baseline active <1% | Linear-output active <1% |
|---|---:|---:|---:|---:|
| First MLP ReLU | 1.9 | 10.8 | 3.6 | 18.3 |
| Final entity output | 11.6 | 0.0 | 17.3 | 0.0 |
| Both stages combined | 13.5 | 10.8 | 20.9 | 18.3 |

Removing the final ReLU eliminates exact-zero channels at that output, but substantially more channels go dead in the preceding ReLU layer. Across the two stages the reduction is small. The linear outputs all vary by at least 0.01 standard deviation in this sample, but that alone does not establish that they carry useful new information. The 16-dimensional per-slot representation and the monster, floor-item and spell arms are not covered by this table. The sampled game trajectories are also early-game heavy, with only five terminal episodes in total.

`collect.c` loads both checkpoints, drives one baseline policy and evaluates both encoders on identical observations. It recomputes the inventory MLP's final activation directly from each checkpoint's weights: ReLU for baseline, identity for `NH_ENT_LINPOOL`. This matters because the standalone CPU demo still has the baseline ReLU hard-coded. Raw outputs are `s*_game*.txt` in this directory. This is a diagnostic outside the frozen experiment `source/` tree.

## Why the two counts move in opposite directions

The inventory path is `r = ReLU(item projection)`, `h = ReLU(W1 r + b1)`, then either `y = ReLU(W2 h + b2)` (baseline) or `y = W2 h + b2` (ablation). Removing the last ReLU makes an exact-zero output unlikely by construction. All 64 outputs can vary as mixtures of a smaller number of active `h` units; 64 varying outputs do not imply 64 independent learned features.

The extra silent `h` units are a training outcome, not a mathematical consequence of the changed forward pass. On identical observations from the final baseline policy, the 131M-step `linear_entity` checkpoints of seeds 2901/2902 had **0/0** silent first-layer units; their 1B-step checkpoints had **11/15**. Matched baseline counts moved **1→2** and **1→1**. For the final linear seed 2901, the 11 silent units had negative pre-activations on every one of 19,464 sampled item rows, although their input and outgoing weight norms remained substantial. Only one first-layer channel in each of final linear seeds 2901/2902 was *structurally* dead (all input weights nonpositive and bias nonpositive, given nonnegative `r`); most were silent on this sample, not universally dead. See `early290{1,2}_details.txt`, `final2901_details.txt`, and `weights.c`.

The removed final ReLU also removes its backward gradient gate. That changes how the policy trains the preceding layer, and it plausibly explains why some first-layer units drifted below zero during training. The audit establishes **that** this happened, but it does not isolate which gradient or which of the four changed entity arms caused it. It would be premature to call it deliberate pruning or an improvement in representation quality.

For a scale check on seed 2901's 11 silent first-layer units at 1B steps: their 16-input weight-row L2 norms have median **1.11** (range 0.54–1.62), versus **1.56** for the 53 active units. The outgoing 64-weight column norms have median **1.17** (range 0.89–1.69), versus **1.46** for active units. At 131M steps, those same 11 units had median input/output norms 0.88/1.03. Their median number of positive input weights fell from **6 of 16** to **3 of 16** by 1B. Because the item representation is nonnegative, this shift helps explain their negative pre-activations on visited items. “Substantial weights” means nonzero weights of comparable order to the active units, not proof those silent channels are carrying useful information; their norms are somewhat smaller than active units'.
