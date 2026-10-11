# Discovery-channel probes — 2026-09-16

## Main finding

Known identity is present, but its readout is sensitive to the appearance contribution and the ReLU. This is evidence of a representation/generalisation problem worth ablating, not proof that identities are absent or that replacing the encoder will improve RL score.

## Frozen-encoder readout

Test accuracy (%), mean of two readout initialization seeds. Each entry is linear / 128-unit ReLU MLP. Chance: rings 3.57%, scrolls 4.76%.

| Policy | Class | Before ReLU | After ReLU | After ReLU, appearance removed | Sum+max inventory pools | Appearance only |
|---|---|---:|---:|---:|---:|---:|
| identify1b_s701 | rings | 94.1 / 96.4 | 65.5 / 70.3 | 99.1 / 100.0 | 12.1 / 12.4 | 3.2 / 3.1 |
| identify1b_s701 | scrolls | 96.2 / 97.6 | 79.5 / 81.3 | 100.0 / 100.0 | 14.6 / 15.0 | 4.1 / 4.2 |
| identify1b_s702 | rings | 93.0 / 95.8 | 59.2 / 62.9 | 94.2 / 100.0 | 13.1 / 14.5 | 3.0 / 3.6 |
| identify1b_s702 | scrolls | 97.5 / 98.8 | 79.7 / 82.4 | 98.2 / 100.0 | 22.1 / 23.4 | 3.4 / 5.0 |
| identify2b_s703 | rings | 92.2 / 94.0 | 52.9 / 55.4 | 94.6 / 100.0 | 9.2 / 8.7 | 2.7 / 3.3 |
| identify2b_s703 | scrolls | 97.8 / 97.8 | 80.8 / 84.6 | 100.0 / 100.0 | 10.9 / 10.5 | 4.3 / 3.8 |

## Protocol and limits

- Frozen final checkpoints of the two identify-head 1B runs and the completed 2B run. Only probes are trained. SHA256s and model paths are in manifest.json.
- Balanced synthetic factorial inventory inputs: 28 ring identities × 28 appearances, or 21 magical scroll identities × 41 shuffled labels, each with eight item-state templates. Blank paper is excluded because its appearance is fixed. These are appearance glyph IDs, not literal name strings.
- Train/validation/test hold out appearance–identity pairs together with all their state templates. Every identity is seen in training. This tests generalisation to unseen pairings, not unseen identities. No adjacent game frames are randomly split; this stage is synthetic and has no episodes.
- Separate linear-softmax and nonlinear probes; 2 seeds, 2 learning rates; up to 450 epochs. Learning rate and epoch chosen by validation cross-entropy, test used only for reporting. Train accuracy and chosen epochs are in results.json; these are finite-budget readouts, not information-theoretic bounds.
- Identity-only means zeroing the frozen appearance projection before ReLU, keeping identity and item-state contributions. Appearance-only omits the true-type contribution while leaving the known-type flag fixed. It is a label-independence control, not an evaluation of unidentified-item gameplay.
- Pooling test has one known target and seven unknown same-class distractors with different appearances, and asks for the known target identity from sum+max pools. It excludes equipped-item passthrough and is harder than the single-item task. It does not establish loss across the entire encoder, recurrent state or pointer keys.
- Python reconstruction checked against C CPU encoder: maximum slot error <1.5e-6, pool error <1.2e-7. CPU inference is fp32; training uses bf16.

## Policy interventions on real trajectories

Three action/dungeon seeds per policy, 8,000 CPU-demo policy decisions per seed. Every 64th decision, sample the first known ring/scroll in inventory. Save the full observation and pre-action recurrent state. Independently swap its appearance, swap its known identity, or hide identity. Restore the original state and logits before sampling the actual action, so interventions never affect the trajectory. Masks remain fixed. These are local input interventions, not coherent remappings of every observation/history channel.

| Policy | Scroll states / games | Appearance swap: READ item argmax changed | Identity swap: READ item argmax changed |
|---|---:|---:|---:|
| identify1b_s701 | 166 / 6 | 15.2% | 24.2% |
| identify1b_s702 | 128 / 4 | 3.9% | 4.7% |
| identify2b_s703 | 203 / 5 | 17.7% | 29.1% |

These are conditional item-head preferences, not frequencies of actual reads. Baseline joint probability of reading the sampled item is usually tiny. States within each game are correlated and collection favours early inventory slots. Rings were observed in only one game each for s702 and s703, and none for s701; ring behavioural conclusions are unsupported. Full counts and probability changes are in policy_results.json.

## Practical conclusion

The discovery path is not disconnected. Known identity affects item selection, but the representation is not appearance-invariant. The largest controlled readout degradation occurs after additive mixing and ReLU, particularly for rings. A useful next architecture ablation is a separate identity pathway (concatenation or a bypass), or replacing appearance once identity is known. Neither should be adopted solely on this probe: test supervised capacity and RL behaviour first.

## Artifacts

- results.json: every fit, train/test accuracy, selected optimization settings.
- policy_results.json / policy_cases.jsonl: intervention summaries and each case.
- Each model directory: exported frozen weights, recorded raw observations/recurrent states, baseline and intervention logits, held-out heatmaps.
- validation.json: numerical comparison with the C encoder.
