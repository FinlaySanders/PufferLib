# NetHack mask ablations

Five 1B runs per variant; paired planned seeds 2901–2905. Evaluation uses the training masks, seed 7, and 2,000 retained games after discarding the first 4,000. Each row below is one trained policy.

| Variant | Seed | Mean score | Median score | Mean max depth | BALROG mean % |
|---|---:|---:|---:|---:|---:|
| baseline | 2901 | 13199 | 8820 | 3.55 | 9.53 |
| baseline | 2902 | 13438 | 9029 | 3.25 | 9.56 |
| baseline | 2903 | 13422 | 8656 | 3.94 | 10.19 |
| baseline | 2904 | 13398 | 8566 | 4.07 | 10.64 |
| baseline | 2905 | 13364 | 8902 | 3.73 | 10.40 |
| no_handless | 2901 | 13133 | 8644 | 4.20 | 10.48 |
| no_handless | 2902 | 13668 | 9013 | 3.82 | 10.48 |
| no_handless | 2903 | 14761 | 9106 | 3.63 | 10.40 |
| no_handless | 2904 | 13081 | 8475 | 2.93 | 9.47 |
| no_handless | 2905 | 13950 | 9128 | 3.19 | 9.78 |
| no_hostile_rays | 2901 | 14443 | 8858 | 3.48 | 9.80 |
| no_hostile_rays | 2902 | 12873 | 9044 | 3.23 | 9.40 |
| no_hostile_rays | 2903 | 12751 | 8104 | 2.88 | 9.18 |
| no_hostile_rays | 2904 | 13466 | 8873 | 3.05 | 9.57 |
| no_hostile_rays | 2905 | 13549 | 8504 | 2.78 | 9.69 |
| no_item_strategy | 2901 | 13457 | 8916 | 3.02 | 9.77 |
| no_item_strategy | 2902 | 13312 | 8759 | 3.05 | 9.52 |
| no_item_strategy | 2903 | 12461 | 7971 | 3.00 | 9.15 |
| no_item_strategy | 2904 | 13735 | 9068 | 3.29 | 9.79 |
| no_item_strategy | 2905 | 14209 | 9028 | 3.57 | 10.33 |
| no_run_search20 | 2901 | 4893 | 2870 | 8.63 | 11.37 |
| no_verb_eps | 2901 | 9261 | 5792 | 2.96 | 7.76 |
| zero_time_on | 2901 | 12648 | 8558 | 3.02 | 9.32 |
| zero_time_on | 2902 | 13132 | 8974 | 3.14 | 9.58 |
| zero_time_on | 2903 | 13009 | 8820 | 3.84 | 10.22 |
| zero_time_on | 2904 | 12442 | 7926 | 3.10 | 9.10 |
| zero_time_on | 2905 | 13892 | 8540 | 3.25 | 9.71 |

Strategic item restrictions are a grouped ablation of satiated eating, fresh spellbook rereading, and shop affordability. RUN and SEARCH20 are also grouped. BALROG here is the depth/XP progression lookup, not the complete benchmark protocol.

See manifest.json for the interleaved order, events.jsonl for failures/replacements, and runs/*/results.json for action-use and failure statistics.
