# Original supervised encoder experiments

Recovered on 2026-09-14 from the August experimental scratch directory. Files in
`original/` are unchanged copies; `provenance.json` records source paths and
SHA-256 hashes. These were scratch experiments, not the current upstream encoder
test suite. They have not been rerun as part of this recovery.

| Code | Comparison and tasks |
| --- | --- |
| `branchlab_gpu.py`, `branchlab_v3.py`, `branchlab_v4.py` | Map encoders: pooled patches, relative-position tokens, attention, sparse entity tokens. Predict stairs and monster geometry, counts; compare held-out R² and speed. |
| `setlab.py` | Inventory set encoders: sum, mean, max, attention, combinations and other variants. Eighteen targets covering existence, counting, relationships, retrieval, conjunctions and extremes. Real observations and synthetic data; multiple seeds and learning rates. |
| `klab.py` | Pointer key depth: linear, shallow nonlinear, intermediate and deep keys. Supervised slot selection for matching, weapons and ammunition. |
| `fentlab_gpu.py` | Deep versus fused entity transformations with sum/max pooling. Synthetic hinge, product, conditional-count and best-uncursed targets; held-out R². |
| `msglab.py`, `msglab2.py` | Frozen message-representation probes plus directly trained message encoders. |
| `spelllab.py` | Spell representation and aggregation experiments for counts, presence, failure rate, level and forgetting. |

The recorded map datasets still exist at `/puffertank/auxdata/{farmer,merchant,digger}.bin`.
Their layout file is `/tmp/aux_layout.json` (also copied here). Inventory data is
`/tmp/inv_lab1b_s702.bin`, `/tmp/inv_s702_long.bin` and
`/tmp/inv_lab1b_s701.bin`; message and spell data are `/tmp/msg_s701.bin` and
`/tmp/spell_feats.npz`. All were checked to exist during recovery.

Before rerunning, replace hard-coded scratch output paths: `setlab.py` resumes
from existing historical JSONL files and otherwise may skip completed runs.
Also preserve each dataset's historical observation layout; today's observations
cannot be substituted into these parsers without updating their offsets.

For an article demonstration, start with the set-encoder benchmark: compare a
small selection of sum/mean/max/combined encoders on count, maximum and relation
tasks. Use identical inputs, matched training budgets, held-out examples and
multiple seeds. Keep architecture-capacity measurements separate from probes of
frozen RL policies. Historical reports are useful leads, but rerun selected
comparisons before treating them as new article results. A low fitted score is
evidence under that training setup, not by itself a proof of impossibility.
