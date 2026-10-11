# Linear entity-output ablation

Five fresh 1B score policies, seeds 2901–2905, use the same frozen source,
engine, score configuration and evaluation protocol as the September mask
ablation baseline. The only difference is `-DNH_ENT_LINPOOL`: the final
inventory, monster, floor-item and spell entity MLP layer has no ReLU before
sum/max pooling. Earlier ReLUs, 16-dimensional item representations,
pointer keys, model dimensions and action masks remain unchanged.

Each policy trains for 999,817,216 batch-aligned steps and is evaluated on
the fork for 6,000 completed games (discard 4,000, retain 2,000). The
per-run episode log also records maximum depth/XP, BALROG progression,
action use, invalid macros and no-turn actions. Existing baseline results
are in `baseline_reference.json`; score comparisons must account for
variation across independently trained policies.

The isolated build is checked against the frozen reference with a 2M-step
byte-identical control, numeric encoder/decoder gradient checks under the
linear-output flag, a finite 2M-step ablation checkpoint and a real eval
smoke test. Validation failure stops the queue.

The detached scheduler waits for the stock mask batch's `STATUS.json` to
report `complete` and for the GPU to be idle. Failed training seeds are
replaced with fresh seeds, up to two retries; failures remain recorded.

Status: `SCHEDULER_STATUS.json`, `active.json`, `events.jsonl`, and
`RESULTS.md`. Source and models are self-contained in this directory;
production files are unchanged.
