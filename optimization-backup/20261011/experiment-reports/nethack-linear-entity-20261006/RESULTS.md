# Linear entity-output ablation

Five fresh 1B runs, seeds 2901–2905. The final ReLU in the inventory, monster, floor-item and spell entity MLPs is removed before sum/max pooling. The first hidden ReLU, 16-dimensional item representation, pooling, pointers, masks and model dimensions remain unchanged. Evaluation uses the training masks, seed 7, and 2,000 retained games after discarding the first 4,000. Each row below is one trained policy.

| Variant | Seed | Mean score | Median score | Mean max depth | BALROG mean % |
|---|---:|---:|---:|---:|---:|
| linear_entity | 2901 | 13183 | 8492 | 3.04 | 9.38 |
| linear_entity | 2902 | 12964 | 8676 | 3.82 | 9.89 |
| linear_entity | 2903 | 13068 | 8584 | 3.07 | 9.61 |
| linear_entity | 2904 | 12321 | 8283 | 3.11 | 9.22 |
| linear_entity | 2905 | 12255 | 8502 | 3.59 | 9.72 |

BALROG here is the depth/XP progression lookup, not the complete benchmark protocol.

See manifest.json for the interleaved order, events.jsonl for failures/replacements, and runs/*/results.json for action-use and failure statistics.
