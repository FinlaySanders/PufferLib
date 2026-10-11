# Nearby-entity passthrough ablation

Five fresh 1B runs, seeds 2901–2905, with nearest-monster, nearest-floor-item and underfoot-item passthroughs zeroed. Baseline masks and inventory passthroughs are retained. Evaluation uses the training masks, seed 7, and 2,000 retained games after discarding the first 4,000. Each row below is one trained policy.

| Variant | Seed | Mean score | Median score | Mean max depth | BALROG mean % |
|---|---:|---:|---:|---:|---:|
| no_nearby_pass | 2901 | 12930 | 8152 | 3.08 | 9.43 |
| no_nearby_pass | 2902 | 13585 | 8973 | 4.27 | 11.02 |
| no_nearby_pass | 2903 | 13126 | 8280 | 3.25 | 9.37 |
| no_nearby_pass | 2904 | 13169 | 8980 | 3.42 | 9.47 |
| no_nearby_pass | 2905 | 12388 | 8537 | 4.26 | 10.09 |

Strategic item restrictions are a grouped ablation of satiated eating, fresh spellbook rereading, and shop affordability. RUN and SEARCH20 are also grouped. BALROG here is the depth/XP progression lookup, not the complete benchmark protocol.

See manifest.json for the interleaved order, events.jsonl for failures/replacements, and runs/*/results.json for action-use and failure statistics.
