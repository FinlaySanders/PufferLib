# Combined NetHack mask removal

Five fresh 1B runs, seeds 2901–2905, with handless, hostile-ray and strategic item restrictions removed together. Evaluation uses the training masks, seed 7, and 2,000 retained games after discarding the first 4,000. Each row below is one trained policy.

| Variant | Seed | Mean score | Median score | Mean max depth | BALROG mean % |
|---|---:|---:|---:|---:|---:|
| all_three_removed | 10135 | 14202 | 8845 | 3.07 | 9.88 |
| all_three_removed | 10138 | 13147 | 8530 | 2.97 | 9.45 |
| all_three_removed | 2902 | 12583 | 7874 | 3.19 | 9.32 |
| all_three_removed | 2903 | 14080 | 8925 | 3.12 | 9.78 |
| all_three_removed | 2905 | 13118 | 8686 | 3.98 | 10.45 |

Strategic item restrictions are a grouped ablation of satiated eating, fresh spellbook rereading, and shop affordability. RUN and SEARCH20 are also grouped. BALROG here is the depth/XP progression lookup, not the complete benchmark protocol.

See manifest.json for the interleaved order, events.jsonl for failures/replacements, and runs/*/results.json for action-use and failure statistics.
