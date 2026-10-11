# Inventory encoder capacity and RL representation probes

**Policy:** fixed 4B score policy s705. Fresh native vec rollouts through its
actual C/CUDA encoder. The collector records public inventory glyphs,
discovered-type glyphs, normalized state features, slot representations, the
384-dimensional inventory branch output, and the global encoder output.
No checkpoint fitting or RL updates occur during collection.

**Data:** 65,536 training, 16,384 validation and 16,384 test observations.
Each split uses different initial dungeon seeds and action seeds. Sampling is
once per 16 policy steps, after 256 forward calls of warmup. Splits are separate
rollouts, not random partitions of neighboring frames in the same games.
These are observations, not independent evaluation episodes. The distribution
is the score policy's own play; results do not establish capacity on every
possible inventory state.

**Six supervised architectures:** sum, max, or sum+max pooling, each with/without
passthrough. All use glyph+kind+subtype embeddings (32), a 16-dimensional slot
representation and a 64→64 ReLU value MLP. Sum is scaled by 0.2 as in production.
Discovered identity contributes zero when unknown. Widths are fixed; output
sizes and head parameter counts naturally differ and are recorded.
Passthrough matches production: wielded and quivered [slot representation +
state features], worn-item mean representation, and amulet/ring/eyewear slots.
The first 512 observations in each split validate passthrough reconstruction
against captured CUDA outputs within bf16 numerical tolerance.

**Frozen probes:** linear readouts over the actual RL-trained inventory branch,
with the same six slices/passthrough ablations. No encoder weights are trained.
These ablations measure decodability from the trained sum+max+passthrough policy;
they are not six separately RL-trained policies. Coordinates are standardized
using training data only, an invertible change for a linear readout. The main
comparison is supervised full branch versus frozen full branch. Recorded global
encoder outputs are retained for a later probe but are not used here.

**Targets:** counts of items, known cursed/blessed items and armor; sum of visible
stack quantities (each capped at 30 by the existing encoder); blessed armor
presence; bow/arrow or crossbow/bolt compatibility; maximum known enchantment;
best known uncursed enchantment; wielded enchantment/curse; quivered quantity;
worn armor count, maximum known worn enchantment, worn ring count, and presence
of a known cursed worn item. Unknown enchantments and absent queried equipment
are masked, not assigned fictional labels. `target_coverage.json` reports support.
The cursed-wielded target is rare (31 positive test frames) and should not anchor
an article conclusion.

**Fit:** a 30-epoch pilot showed continuing validation improvement, so the final
comparison uses up to 150 epochs, 3 initialization seeds, Adam, batch size 1,024, learning rates
0.0003 and 0.001. Validation plateaus halve the learning rate (patience 8, minimum 0.00001);
after at least 60 epochs, 30 epochs without meaningful improvement stop a fit.
Each seed selects its epoch and learning rate on validation
loss, then evaluates once on test. Equal-weight masked per-target losses use
train-standardized regression MSE and binary cross entropy. Supervised encoder
and readout train together; frozen probes train only the readout. Report
three-seed medians, individual seeds and learning curves; inspect convergence
before calling any number a supervised ceiling.

**Relative decodability:** frozen R² / supervised R² for regression, and
(frozen AUC − 0.5) / (supervised AUC − 0.5) for binary targets. Suppress ratios
when the supervised gain above baseline is ≤0.1. Do not clip ratios above one:
supervised fitting provides an empirical reference, not a mathematical maximum.
These ratios do not measure mutual information, the fraction of behavior
learned, or whether the policy causally uses a feature. Passthrough may make a
feature available without RL needing to learn it.

Original source and engines are untouched. Collector patches, binary/data/model
hashes and full outputs are under
`/puffertank/experiments/inventory-supervised-20260914`. `run.py` runs the pilot; `refine.py` preserves it under `results_30epochs/`,
freezes the final implementation, trains supervised arms before probes, and
writes article tables via `summarize.py` after all 36 selected fits complete.
Each selected fit searches two learning rates (72 training jobs total).

## Nonlinear readout comparison

`run_nonlinear.py` freezes each of the 18 supervised encoders and also uses the
captured RL-policy representations. For each representation it fits a fresh
linear head and a 128-unit ReLU MLP head on the identical 16 targets, with the
same train/validation/test splits, three seeds and two learning rates. Only the
head changes; encoders stay frozen. This includes freshly fitted linear heads
on supervised representations to separate readout optimization from nonlinearity.
The supervised checkpoints originally trained with linear heads; this is a
post-training decodability test, not a new end-to-end encoder comparison.

`nonlinear_results/` holds 72 selected fits. `collect_nonlinear.py` validates
completion and emits `results/nonlinear_summary.{json,csv}`. An MLP improvement
shows information recoverable by a nonlinear readout under this protocol. A
failed MLP still does not prove that the information is absent.
