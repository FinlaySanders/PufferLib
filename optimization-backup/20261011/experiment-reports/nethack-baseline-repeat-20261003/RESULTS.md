# Fresh NetHack baseline replication

Five fresh 1B baseline runs, seeds 2906–2910. All original masks and entity passthroughs remain enabled. Evaluation uses seed 7 and 2,000 retained games after discarding the first 4,000. Each row below is one trained policy.

| Variant | Seed | Mean score | Median score | Mean max depth | BALROG mean % |
|---|---:|---:|---:|---:|---:|
| baseline | 10146 | 13350 | 8404 | 3.64 | 10.14 |
| baseline | 10247 | 14153 | 9007 | 3.48 | 9.81 |
| baseline | 2906 | 14399 | 9808 | 3.33 | 9.93 |
| baseline | 2909 | 13370 | 8932 | 3.38 | 9.66 |
| baseline | 2910 | 14251 | 9034 | 4.10 | 10.70 |

Strategic item restrictions are a grouped ablation of satiated eating, fresh spellbook rereading, and shop affordability. RUN and SEARCH20 are also grouped. BALROG here is the depth/XP progression lookup, not the complete benchmark protocol.

See manifest.json for the queued order, events.jsonl for failures/replacements, and runs/*/results.json for action-use and failure statistics.
