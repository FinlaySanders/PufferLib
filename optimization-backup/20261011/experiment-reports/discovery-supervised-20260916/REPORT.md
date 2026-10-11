# Fresh supervised discovery encoders

These experiments train fresh encoders and linear readouts jointly. They are distinct from the earlier frozen RL-policy probes. No RL policies were retrained or modified.

## Main robustness experiment

Balanced synthetic rings and scrolls, half known and half unknown. Joint targets: identity when known, appearance when unknown, blessed/uncursed/cursed/unknown status, enchantment-known flag, visible numeric enchantment where applicable, quantity and equipped status. Thirty-two fixed state templates have independently sampled features; scrolls have no numeric enchantment or equipped flag.

Accuracy is median over three fresh training seeds (range in parentheses), with learning rate and checkpoint selected on validation.

| Class | Design | Known identity | Unknown appearance | BUC | Numeric enchantment RMSE | Quantity RMSE |
|---|---|---:|---:|---:|---:|---:|
| rings | Current additive 16D | 99.44% (99.09–99.94) | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | 0.730 | 2.633 |
| rings | Replacement 16D | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | 0.696 | 2.646 |
| rings | Separate paths 16D | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | 99.89% (90.92–100.00) | 0.853 | 2.759 |
| rings | Separate paths 32D | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | 0.710 | 2.625 |
| scrolls | Current additive 16D | 99.93% (99.85–100.00) | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | N/A | 2.747 |
| scrolls | Replacement 16D | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | N/A | 2.740 |
| scrolls | Separate paths 16D | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | N/A | 2.812 |
| scrolls | Separate paths 32D | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | 100.00% (100.00–100.00) | N/A | 2.733 |

## Interpretation

The earlier frozen-network failures are not evidence of an absolute identity-capacity limit in the additive architecture. Direct supervision can teach a fresh encoder to make identity highly readable despite randomised appearances. This points to how RL learns and uses the representation, its training distribution and objective, rather than showing that the current architecture cannot encode identity.

Replacement builds appearance invariance into known-item inputs. Separate paths preserve identity without forcing it through the same addition and ReLU as appearance. These remain plausible inductive biases for RL, but supervised identity accuracy alone cannot establish a score advantage or explain all failures to use items.

## Designs

- Additive 16D: ReLU(appearance projection + gated identity projection + state projection + bias), matching the current item design.
- Replacement 16D: use known identity through the appearance projection once discovered, otherwise the original appearance. This is the NH_DISC_SWAP concept.
- Separate 16D: concatenate 8 ReLU appearance/state coordinates with 8 signed identity coordinates. Same total item width, but different allocation.
- Separate 32D: concatenate 16 appearance/state with 16 identity coordinates. Extra capacity, not an equal-width comparison.

All models have trainable 32D residual+kind+subtype glyph embeddings. Identity projection starts at zero; the separate identity path is signed so its gradient is not blocked by ReLU at zero. All encoder and readout parameters train jointly. Unknown-item identity is masked before forming a representation and excluded from the identity loss.

## Protocol and limitations

- 28 ring identities × 28 appearances; 21 magical scroll types × 41 possible labels. Blank paper excluded.
- Each identity appears in training. Its appearance pairings are partitioned into train/validation/test, with all state templates kept together per pair. This tests held-out pairings, not unseen identities.
- For replacement, different known appearances collapse to the same representation by design. Perfect held-out-pair performance does not imply broader semantic understanding.
- Synthetic and class-balanced; not sampled from RL gameplay. State templates are shared across splits; unseen state-combination generalisation is not tested.
- Three training seeds, Adam at 0.001 and 0.003, up to 500 full-batch epochs; validation every five epochs; early stop after epoch 100 with patience 60. Validation selects learning rate and epoch; test does not select configurations.
- Equal averaging of target losses: cross entropy/BCE for categorical flags and MSE for scaled numeric features. This is not equal task difficulty.
- Most fits still select late checkpoints; finite-budget errors should not be called hard architectural ceilings.
- Only item representations are tested here. Pooling, recurrent policy decisions and score need separate evaluation.

## Initial pass

The root results.json also contains 48 fits with simpler 16-state templates: identity-only and multitask objectives, four architectures, two classes, three seeds. Those templates correlate some state features. The independent-state robustness pass above is the primary multitask result. All runs and curves are retained.

## Validation and provenance

validation.json checks that changing hidden true identity cannot affect unknown-item outputs or identity-path gradients, and that appearance replacement is invariant to appearance once known. Code hashes are stored alongside the results. Models are fresh, not loaded from any RL checkpoint.
