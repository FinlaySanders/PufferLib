# Frozen nearby-entity probe

CPU float32 reconstruction of frozen checkpoint entity arms, validated against the C demo; not bit-identical native BF16 activations.

Entire environment streams, shared across score/depth corpora: train 0–3, validation 4–5, test 6–7.

Shared off-policy historical corpus; decoding is not evidence of causal use or guaranteed on-policy generalization.

Only scenes with at least two valid entities are fitted. Underfoot reconstruction additionally requires an underfoot item. Empty scenes do not inflate scores.

| Policy | Target | Readout input | Probe | Held-out R² | Test states |
|---|---|---|---|---:|---:|
| baseline_s2901 | nearest_monster | pool_only | linear | 0.549 | 387 |
| baseline_s2901 | nearest_monster | pool_only | MLP | 0.592 | 387 |
| baseline_s2901 | nearest_monster | direct_summary_control | linear | 1.000 | 387 |
| baseline_s2901 | nearest_monster | direct_summary_control | MLP | 0.997 | 387 |
| baseline_s2901 | nearest_floor_item | pool_only | linear | 0.569 | 2967 |
| baseline_s2901 | nearest_floor_item | pool_only | MLP | 0.636 | 2967 |
| baseline_s2901 | nearest_floor_item | direct_summary_control | linear | 1.000 | 2967 |
| baseline_s2901 | nearest_floor_item | direct_summary_control | MLP | 0.999 | 2967 |
| baseline_s2901 | underfoot_items | pool_only | linear | 0.742 | 826 |
| baseline_s2901 | underfoot_items | pool_only | MLP | 0.832 | 826 |
| baseline_s2901 | underfoot_items | direct_summary_control | linear | 1.000 | 826 |
| baseline_s2901 | underfoot_items | direct_summary_control | MLP | 0.999 | 826 |
| no_nearby_pass_s2901 | nearest_monster | pool_only | linear | 0.564 | 387 |
| no_nearby_pass_s2901 | nearest_monster | pool_only | MLP | 0.573 | 387 |
| no_nearby_pass_s2901 | nearest_monster | direct_summary_control | linear | 1.000 | 387 |
| no_nearby_pass_s2901 | nearest_monster | direct_summary_control | MLP | 0.996 | 387 |
| no_nearby_pass_s2901 | nearest_floor_item | pool_only | linear | 0.622 | 2967 |
| no_nearby_pass_s2901 | nearest_floor_item | pool_only | MLP | 0.692 | 2967 |
| no_nearby_pass_s2901 | nearest_floor_item | direct_summary_control | linear | 1.000 | 2967 |
| no_nearby_pass_s2901 | nearest_floor_item | direct_summary_control | MLP | 0.998 | 2967 |
| no_nearby_pass_s2901 | underfoot_items | pool_only | linear | 0.906 | 826 |
| no_nearby_pass_s2901 | underfoot_items | pool_only | MLP | 0.922 | 826 |
| no_nearby_pass_s2901 | underfoot_items | direct_summary_control | linear | 1.000 | 826 |
| no_nearby_pass_s2901 | underfoot_items | direct_summary_control | MLP | 0.999 | 826 |

R² measures recovery of learned summary vectors, not accuracy of all game facts. A good readout establishes accessibility; causal use needs intervention. The direct-summary control is a ceiling check, including for the ablated policy where that summary is computed only for this analysis.
