# Supervised architecture comparison

Fresh embeddings, encoder, and readout jointly supervised; NO RL training. Common body-armour fixture only, all types/enchantments known.

| Architecture | Parameters | AC upgrade balanced accuracy | Noncursed upgrade balanced accuracy |
|---|---:|---:|---:|
| baseline16 | 39474 | 96.57% | 98.49% |
| wide32 | 43458 | 96.64% | 98.51% |
| signed16 | 39474 | 96.44% | 98.33% |
| signed_bypass16 | 45618 | 96.57% | 98.40% |
| candidate_access16 | 41522 | 96.64% | 98.21% |

All architectures have existing worn-item bypass. baseline16 matches the 16->64->64 sum/max topology, using a single fresh item embedding table instead of the RL factorized embedding tables.
wide32 changes slot width to 32. signed16 removes the initial ReLU. signed_bypass16 appends sum/max of signed preactivations and signed worn representation after the MLP pool.
candidate_access16 additionally exposes the designated carried candidate slot: diagnostic access control, not a general implementable candidate selector.
Supervision demands AC-upgrade and known-noncursed AC-upgrade simultaneously. Balanced loss and balanced accuracy prevent majority-class success.
This measures learnability under this budget, not RL performance. Randomly initialized readouts and fresh trained encoders cannot be compared as if these were trained-policy interventions.
