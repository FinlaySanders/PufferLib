# Controlled policy decisions

Counterfactual forwards from real policy trajectories. Policy weights and pre-action recurrent state are held fixed within each comparison. These are output probabilities, not executed actions or a gameplay success test. Original action masks are held fixed; selected items remain in the same legal item class/armour slot. Potion target is set to known uncursed healing versus known uncursed water at 10% versus 90% HP. Armour target copies an eligible worn item type/erosion and has known enchantment three points above/below it. Armour swap comparisons do not establish that wearing immediately is optimal during combat.

## identify1b_s701: healing
310 contexts across 10 episodes.

| Condition | P(verb) | P(target given verb) | P(verb and target) | Multiple-choice contexts | P(target given verb), multiple-choice only |
|---|---:|---:|---:|---:|---:|
| healing_high_hp | 0.0000 | 0.1528 | 0.0000 | 296 | 0.11268411365249364 |
| healing_low_hp | 0.3527 | 0.8768 | 0.2787 | 296 | 0.8710093235764862 |
| water_high_hp | 0.0000 | 0.3344 | 0.0000 | 296 | 0.3029674340620699 |
| water_low_hp | 0.1009 | 0.3406 | 0.0073 | 296 | 0.3094083654514891 |

## identify1b_s701: armour
188 contexts across 6 episodes.

| Condition | P(verb) | P(target given verb) | P(verb and target) | Multiple-choice contexts | P(target given verb), multiple-choice only |
|---|---:|---:|---:|---:|---:|
| downgrade | 0.0053 | 0.2226 | 0.0000 | 166 | 0.11959026160707613 |
| upgrade | 0.0053 | 0.9677 | 0.0053 | 166 | 0.9633801719632588 |

## idreplace1b_s701: healing
294 contexts across 12 episodes.

| Condition | P(verb) | P(target given verb) | P(verb and target) | Multiple-choice contexts | P(target given verb), multiple-choice only |
|---|---:|---:|---:|---:|---:|
| healing_high_hp | 0.0001 | 0.3550 | 0.0000 | 246 | 0.2290967323003 |
| healing_low_hp | 0.3824 | 0.7863 | 0.2742 | 246 | 0.7446494157809084 |
| water_high_hp | 0.0001 | 0.7692 | 0.0000 | 246 | 0.7242083258235094 |
| water_low_hp | 0.1366 | 0.4257 | 0.0012 | 246 | 0.31367849958502153 |

## idreplace1b_s701: armour
156 contexts across 6 episodes.

| Condition | P(verb) | P(target given verb) | P(verb and target) | Multiple-choice contexts | P(target given verb), multiple-choice only |
|---|---:|---:|---:|---:|---:|
| downgrade | 0.0087 | 0.6033 | 0.0086 | 119 | 0.47990174353503756 |
| upgrade | 0.0090 | 0.9943 | 0.0090 | 119 | 0.992476473868193 |

