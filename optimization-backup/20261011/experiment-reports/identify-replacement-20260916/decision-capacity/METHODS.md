# Decision diagnosis and architecture capacity

## Frozen-policy counterfactuals
Two actual RL-trained 1B policies, three independent environment seeds each, 8,000 original-policy decisions per seed. Every 64 decisions, collect eligible potion or armour contexts. Each variant starts from identical pre-action recurrent state. Restore the original post-forward recurrent state and original logits before sampling/executing the actual action, so counterfactuals do not drive the trajectory.

Healing test: an eligible non-water potion is made known and uncursed, with identity healing or water, and current HP is set to 10% or 90% of unchanged max HP. Real gameplay history and remaining observation are held fixed. Water uses its fixed appearance. This is a controlled counterfactual, not a guarantee of a naturally occurring observation/history pair. Multiple eligible items are reported separately to avoid interpreting a forced single-item selection as evidence of learned discrimination.

Armour test: find an eligible carried armour piece and a known-type, known-enchantment worn item of the same slot. Candidate copies the worn type/erosion and is known uncursed, with enchantment three points above or below the worn piece, within representable bounds. These forwards test relative preferences. They do not assert that immediately wearing armour is optimal in a dangerous situation.

Measure P(verb), P(target item | verb), and their product. Contexts in the same episode are correlated; report episode coverage and avoid treating all frames as independent games. No counterfactual gameplay rollouts or score certificates are claimed.

## Supervised architecture capacity
Fresh encoders and readouts jointly trained with direct supervision on common-body-armour upgrade predicates. Three initialization seeds, two learning rates, validation selection, held-out candidate state combinations, identical dataset and training budget for each architecture. No new RL training. Baseline reproduces the slot16 -> MLP64 -> MLP64 -> sum/max topology plus worn-item bypass, with a single fresh embedding table rather than factorized embedding tables. See capacity_protocol.json.

This measures whether each topology can learn the requested features under direct demand. It does not measure whether RL will learn them, or whether a wider/bypass policy gets better gameplay outcomes.
