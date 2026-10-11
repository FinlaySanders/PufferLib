> **Results invalid for the training objective — missing reward clipping.** Offline reward/GAE/Q targets omitted the trainer’s [-1, 1] reward clamp. Derived critic and variance estimates below require regeneration and refitting; do not use them for training recommendations. Original results are retained for audit. See the [clipping correction](clipping_correction/REPORT.md).

# NetHack head-gradient variance: small offline pilot

Follow-up: [PUTON_REPORT.md](PUTON_REPORT.md) reports 67M frozen vec steps.
The pilot's put-on signal repeats more modestly at early/middle checkpoints
but disappears at the late checkpoint. The original 0.25 magnitude should
not be treated as a general variance-reduction estimate.

This is a feasibility and estimator check, not a training result. No policy
weights were updated. The pinned source is `3719caaaf945025e4e1e59c6556560d2ba9e3d1c`;
the engine is `e7f6568568242745a7f7ebd8f730367123522cac`. The vec capture hook
lives only in `capture-source/`, an isolated scratch checkout. The production
PufferLib trainer and NetHack environment were not changed.

| Checkpoint | Collector | Raw steps | Complete-episode steps | Episodes | Fit / audit | Elapsed vec eval |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 131M | CPU inference | — | 1,846,108 | 1,617 | 805 / 812 | — |
| 131M | vec + GPU inference | 212,992 | 102,615 | 137 | 71 / 66 | 2.2 s |
| 524M | vec + GPU inference | 393,216 | 176,660 | 130 | 64 / 66 | 4.5 s |
| 1000M | vec + GPU inference | 491,520 | 225,886 | 129 | 62 / 67 | 5.9 s |

The vec timings include full per-step capture of 742 masked logits, 1024 trunk
features, actions, masks, reward, value, done and truncated, using 128 games on
32 CPU threads and one GPU. The raw rate was roughly 84k–97k steps/s. We kept
the complete episodes for analysis and preserved the raw files separately.
The vec files use whole-agent fit/audit splitting, with odd agents fitting and
even agents auditing. The CPU pilot uses odd/even episodes. The three vec
checkpoints come from one training run. Verb epsilon was held at the value
corresponding to each checkpoint (0.005, 0.0039643, 0.00000152).

The enumerated masked/epsilon toy passes finite-difference and zero-mean
gradient checks. Vec captures contain legal sampled actions in all 20 heads,
all 13 roles, finite logits and trunk features. The first action after reset
is included: mean complete-episode returns from the trace match the trainer
dashboard to three decimal places at every checkpoint. Policy and frozen-Q controls
were fitted on the fit split and evaluated on held-out episodes. Empirical
score-weighted control means and a subset of true final-linear decoder
parameter-gradient variances were checked. See `analysis/*/control_checks.csv`
and `parameter_spotcheck.csv`.

As a determinism check, the captures were repeated after changing only whether
the first post-reset action was written. For every one of the 128 agents at
each checkpoint, all later actions, masks, logits, trunk features, rewards,
values and terminal flags matched byte-for-byte across the two captures.

For the common verb, movement, eat-item and throw-item heads, the held-out
policy-correction variance ratio to plain GAE is approximately 1.00 at each
checkpoint (1.00 means no reduction). The larger 1.85M-step CPU early pilot
agrees on those common heads. Rare heads are unresolved: the vec audits contain
only 43/49/194 zap selections and 35/81/146 read selections at early/middle/late.
Some fitted correction coefficients then explode, producing implausibly large
variance ratios. These are unstable small-sample estimates, not evidence of a
useful or harmful training effect. The frozen linear per-head Q usually fails
to improve held-out one-step MSE over the existing value estimate; its
variance corrections often worsen the ratio. The Q model needs a better target
or regularization before testing it online.

The CPU early pilot has one exception worth a targeted follow-up: the put-on
item head's held-out logit-gradient variance ratio is 0.249 (114 selections in
97 audit episodes; episode-bootstrap 95% interval 0.203–0.373). Decomposing
the cross-head control shows this is entirely the chosen verb's centered
log-probability; no other head is active when put-on uses this item head.
Removing the five audit episodes with the largest plain-GAE squared gradients
(89% of that squared-gradient total) leaves a ratio of 0.439 with the original
fit coefficient. Thus the effect is concentrated in rare high-gradient events,
but it is not solely one episode. It has not been replicated at another
checkpoint or on a large vec sample, and does not establish an online gain.

One apparent exception is the Q-weighted optimal baseline on the verb head:
its variance ratios are 0.73, 0.65 and 0.82 in the three vec pilots. This does
not replicate in the larger CPU early pilot (ratio 1.00). The short vec pilots
stop after roughly 128 completed games and drop unfinished trajectories, so
their evaluated episodes favour games that end sooner. The CPU collector also
uses float32 inference instead of the vec policy's BF16 GPU inference. We have
not isolated which difference explains the discrepancy. The Q baseline should
be tested on a larger vec sample and checked against true parameter-gradient
variance before claiming a useful win.

Raw captures are under `captures/vec_{early,middle,late}_raw/`; complete
episode copies are under `captures/vec_{early,middle,late}_pilot/`. Policy and
Q variance tables, fit coefficients, episode moments, centered-control checks
and parameter-gradient spot checks are under `analysis/vec_*_pilot/`.
The larger CPU early pilot is under `captures/early_pilot/` and
`analysis/early_pilot/`.

The next offline test, if pursued, should target rare item verbs with more
vec episodes and predeclared minimum audit counts. There is no clear pilot
signal to justify starting the proposed online variance-reduction arms yet.
