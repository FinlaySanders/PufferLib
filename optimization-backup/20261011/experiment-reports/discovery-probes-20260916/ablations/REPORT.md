# Discovery representation ablations

## Outcome

Both alternatives improve held-out identity readout relative to the current additive+ReLU item encoder. Appending a separate signed identity projection reaches 100% linear readout on all three policies and both classes. Replacing appearance once known reaches 86.6–94.4% linear and 100% nonlinear readout. These are frozen-weight representation interventions with newly trained readouts, not newly trained RL agents.

## Designs

Let A be the appearance embedding projected with inv1_w, I the discovered identity projected with invt_w, and S the item-state projection plus bias. I is zero for unknown items.

- Baseline (16 dimensions): ReLU(A + I + S).
- Replace appearance (16): once known, use the true-type glyph through inv1_w and silence invt_w; otherwise preserve the original unknown-item path. This matches the existing NH_DISC_SWAP observation switch. It differs from merely removing A and keeping I.
- Identity bypass (32): concatenate the original ReLU(A + I + S) with signed I. Existing 16 coordinates are preserved; the appended identity cannot be suppressed by appearance through ReLU.
- Separate ReLUs (32): concatenate ReLU(A + S) with ReLU(I).
- Replacement pooled (128): pass replacement item representations through the original frozen inventory value MLP and sum+max pooling with the exact same seven distractors as the baseline benchmark.

The 32-dimensional variants have twice the item width and larger readout heads. Using them in the policy would require changes to pooling, passthrough and pointer projection inputs. Their current results are not an equal-width architecture comparison.

## Results

Accuracy %, linear / nonlinear readout, averaged over two probe seeds. Same balanced synthetic inputs and held-out appearance–identity pair splits as the initial report; each identity is present in training. Eight state templates per pairing, validation-selected learning rate and epoch. Two learning rates per fit, maximum 450 epochs.

| Policy | Class | Current 16D | Replace 16D | Identity bypass 32D | Separate ReLUs 32D |
|---|---|---:|---:|---:|---:|
| identify1b_s701 | rings | 65.5 / 70.3 | 94.4 / 100.0 | 100.0 / 100.0 | 99.9 / 100.0 |
| identify1b_s701 | scrolls | 79.5 / 81.3 | 93.5 / 100.0 | 100.0 / 100.0 | 98.5 / 97.9 |
| identify1b_s702 | rings | 59.2 / 62.9 | 88.4 / 100.0 | 100.0 / 100.0 | 98.8 / 99.9 |
| identify1b_s702 | scrolls | 79.7 / 82.4 | 88.7 / 100.0 | 100.0 / 100.0 | 99.6 / 100.0 |
| identify2b_s703 | rings | 52.9 / 55.4 | 86.6 / 100.0 | 100.0 / 100.0 | 99.5 / 100.0 |
| identify2b_s703 | scrolls | 80.8 / 84.6 | 92.9 / 100.0 | 100.0 / 100.0 | 99.8 / 100.0 |

## Does replacement survive existing pooling?

| Policy | Class | Original pools | Replacement pools |
|---|---|---:|---:|
| identify1b_s701 | rings | 12.1 / 12.4 | 34.2 / 37.6 |
| identify1b_s701 | scrolls | 14.6 / 15.0 | 50.7 / 52.1 |
| identify1b_s702 | rings | 13.1 / 14.5 | 48.4 / 62.7 |
| identify1b_s702 | scrolls | 22.1 / 23.4 | 62.4 / 64.7 |
| identify2b_s703 | rings | 9.2 / 8.7 | 29.6 / 25.0 |
| identify2b_s703 | scrolls | 10.9 / 10.5 | 44.7 / 44.2 |

Replacement also improves pooled readout, but does not solve it: 2B linear readout rises from 9.2% to 29.6% for rings and 10.9% to 44.7% for scrolls. The existing pooling weights were trained for the old representation. This test excludes equipped-item passthrough and asks for the identity of one known item among seven unknown same-class distractors.

## Interpretation and next experiment

- The known-identity path is useful, but combining it additively with appearance before ReLU makes identity harder to recover on unseen pairings. Separate identity coordinates remove that particular interference.
- Replacement is appearance-invariant by construction once known. Test pairings therefore collapse onto representations already seen for that same identity and state. Its perfect nonlinear readout is a desired invariance property, not generalisation to unseen item identities or evidence of improved gameplay.
- Width-preserving replacement is the cheapest RL ablation to run first. A separate identity bypass is the stronger preservation design, but needs a wider encoder/decoder and controlled retraining.
- No production files, checkpoints, or training configuration were changed. No score advantage has been measured. Turning replacement on only at evaluation would introduce a distribution shift for existing policies.

## Files

run.py contains the executable experiment; results.json stores all 96 selected fits and optimization settings. Baseline results and their C reconstruction validation remain in the parent directory. comparison.png plots linear readout.
