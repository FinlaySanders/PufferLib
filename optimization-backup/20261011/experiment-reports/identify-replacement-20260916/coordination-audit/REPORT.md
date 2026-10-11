# Armour verb–item coordination audit

Frozen policy counterfactuals, three trajectory seeds per policy. Quiet: no hostile among visible/detected monster tokens, no condition bits, at least 80% HP, not hungry, and current worn item known noncursed. This is a screen-based filter, not proof of safety. Each pair starts from identical pre-action recurrent state. Pool swaps are activation interventions; zero-memory variants are artificial diagnostic controls.

## identify1b_s701
{'n': 117, 'episodes': 8, 'enchantment_known': 48, 'enchantment_unknown': 69, 'quiet': 57}

| Context | Variant | N | P(WEAR) | P(candidate given WEAR) |
|---|---|---:|---:|---:|
| all | downgrade | 376 | 0.006712 | 0.218329 |
| all | downgrade_keys_upgrade_pool | 376 | 0.006761 | 0.221203 |
| all | downgrade_zero_memory | 376 | 0.000034 | 0.137545 |
| all | unknown_both | 376 | 0.006707 | 0.752985 |
| all | unknown_buc | 376 | 0.006723 | 0.977230 |
| all | unknown_enchantment | 376 | 0.006705 | 0.823798 |
| all | upgrade | 376 | 0.006761 | 0.978758 |
| all | upgrade_keys_downgrade_pool | 376 | 0.006712 | 0.978738 |
| all | upgrade_zero_memory | 376 | 0.000102 | 0.995384 |
| quiet | downgrade | 123 | 0.016215 | 0.216217 |
| quiet | downgrade_keys_upgrade_pool | 123 | 0.016225 | 0.218924 |
| quiet | downgrade_zero_memory | 123 | 0.000011 | 0.159197 |
| quiet | unknown_both | 123 | 0.016209 | 0.804561 |
| quiet | unknown_buc | 123 | 0.016211 | 0.999990 |
| quiet | unknown_enchantment | 123 | 0.016209 | 0.898104 |
| quiet | upgrade | 123 | 0.016225 | 0.999994 |
| quiet | upgrade_keys_downgrade_pool | 123 | 0.016215 | 0.999993 |
| quiet | upgrade_zero_memory | 123 | 0.000020 | 0.999838 |

## idreplace1b_s701
{'n': 106, 'episodes': 12, 'enchantment_known': 71, 'enchantment_unknown': 35, 'quiet': 75}

| Context | Variant | N | P(WEAR) | P(candidate given WEAR) |
|---|---|---:|---:|---:|
| all | downgrade | 309 | 0.008947 | 0.599666 |
| all | downgrade_keys_upgrade_pool | 309 | 0.009034 | 0.600293 |
| all | downgrade_zero_memory | 309 | 0.001854 | 0.392163 |
| all | unknown_both | 309 | 0.008786 | 0.642422 |
| all | unknown_buc | 309 | 0.008840 | 0.993479 |
| all | unknown_enchantment | 309 | 0.008786 | 0.685093 |
| all | upgrade | 309 | 0.009034 | 0.993399 |
| all | upgrade_keys_downgrade_pool | 309 | 0.008947 | 0.993024 |
| all | upgrade_zero_memory | 309 | 0.001679 | 0.790399 |
| quiet | downgrade | 73 | 0.010392 | 0.690441 |
| quiet | downgrade_keys_upgrade_pool | 73 | 0.010845 | 0.690982 |
| quiet | downgrade_zero_memory | 73 | 0.000000 | 0.439001 |
| quiet | unknown_both | 73 | 0.010390 | 0.701381 |
| quiet | unknown_buc | 73 | 0.010572 | 0.995953 |
| quiet | unknown_enchantment | 73 | 0.010390 | 0.713901 |
| quiet | upgrade | 73 | 0.010845 | 0.999063 |
| quiet | upgrade_keys_downgrade_pool | 73 | 0.010392 | 0.999064 |
| quiet | upgrade_zero_memory | 73 | 0.000000 | 0.782164 |

Pool-swap assertions passed in every collected case: verb logits follow the pooled summary, exactly, while candidate item vectors remain on the other observation. Thus the isolated route is confirmed without claiming that the decoder should be inverted. Mean probabilities can be dominated by a few states; paired log-odds and medians are included in results.json.
