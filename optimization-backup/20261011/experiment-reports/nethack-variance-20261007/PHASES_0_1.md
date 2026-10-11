# NetHack variance-reduction experiment

This workspace is isolated from the active PufferLib checkout. No production
trainer files are changed and no Phase 1 training arm is launched until the
estimator formulas and Phase 0 checks are settled.

## Phase 0: foundations

1. **Enumerable CPU test.** `python toy.py` enumerates a masked,
   epsilon-mixed verb, consumed item and direction heads, an item–direction
   reward interaction, and a stochastic second step. It checks the exact
   unclipped expected gradient against finite differences, the zero mean of
   correction terms, and per-head variance. This currently passes. It includes
   standard policy-based cross-head and next-step controls plus exact-Q
   conditional baselines. The coefficients and Q in this toy come from exact
   enumeration; real experiments fit them on separate episodes.

2. **Baseline seed variance.** `BASELINE.md` and `baseline.json` summarise
   five archived, independently trained 1B-step policies with the same source,
   protocol and 2,000 retained eval games each. `eval_screen_baselines.py`
   evaluates their shared 262.144M-step checkpoints on 6,000 games, discarding
   the first 4,000. Use the resulting five-seed spread for screening-budget
   decisions. Do not substitute the final 1B variance for it. Keep the seed
   unit of analysis as the trained policy, not its thousands of episodes.

3. **Logging.** `source/puffer_diag` has the isolated replay logger from the
   Breakout pilot. It writes per-pass KL, ratio and clip diagnostics, frozen
   versus live advantages, value MSE against frozen returns, and gradient
   norms. NetHack 2.097M-step diag-off and diag-on smoke runs, and runs with
   achievement logging added, all produced byte-identical checkpoints. The
   first minibatch had ratio ~1 and KL near zero. Histogram counts matched
   sample counts in that smoke. This is a correctness check, not an overhead
   certification.

   Achievement logging is isolated in the NetHack experiment source and never
   affects reward: `identified_wands` counts an inventory wand appearance
   observed unknown and later known, `successful_prayers` counts the visible
   favorable-prayer start message (`p_type == 3` in `pray.c`), and
   `full_armour` records ever wearing
   suit, cloak, helmet, gloves, and boots simultaneously. These are precisely
   defined proxies, not a complete NetHack achievement ontology. The prayer
   detector is a lower bound: blind favorable prayers have no light message.
   The initial completion-message detector yielded zero because that message
   was not observable in the NLE topline. A debug run captured the light
   message and the source ties it uniquely to the favorable prayer branch.

   Still needed: held-out KL on a slice excluded from training; a per-head
   policy-gradient variance diagnostic split by verb class; and a sufficiently
   long, uncontended diagnostic-on/off throughput comparison. The existing
   pilot has frozen-return training MSE and critic absorption but not held-out
   KL. Its current CSV is `logs/<run>.reuse.csv`.

## Estimators to audit

For consumed head `h`, let `g_h = score_h * (A - b)`, where `score_h` is
`grad log pi_h(a_h | s)` under the **actual** masked sampling distribution.
The verb distribution includes epsilon mixing; unused heads have zero score.
All corrections below keep the expected **unclipped** policy gradient intact.
PPO clipping is audited separately because exact expectation identities do not
imply an unchanged clipped objective.

- **Policy-based cross-head:** for each other consumed current head `j`, use
  `c_j = log pi_j(a_j | s) + H(pi_j(. | s))`. It has conditional mean zero.
  Subtract `alpha_cross * sum(c_j)` inside head `h`'s advantage. Fit alpha to
  minimize the norm of the logit-gradient variance on independent rollouts.
  Only terms independent of `a_h` when conditioning on its other sampled
  actions are permitted.
- **Future-step:** use the next-step centered log probability
  `c_next = log pi(a_next | s_next) + H(pi(. | s_next))`, summed over heads
  actually consumed at that step. Its mean conditional on `s_next` is zero,
  so subtracting `alpha_future * c_next` from an earlier head's advantage is
  unbiased. If extending beyond one step, apply the declared `gamma*lambda`
  coefficients and retest the complete recursion.
- **Conditional-Q baseline:** `b_h(s,a_other) = sum_a pi_h(a | s) Q(s,a_other,a)`.
  It is independent of the sampled `a_h`.
- **OB:** the score-weighted optimal baseline for a *logit-gradient* vector:
  `sum_a pi_h(a) ||score_h(a)||^2 Q(s,a_other,a)` divided by
  `sum_a pi_h(a) ||score_h(a)||^2`. This definition is explicit; it is not
  automatically optimal for the full shared-network parameter gradient.
  Sweep the proposed shrinkage `kappa` toward the ordinary conditional-Q
  baseline only after Q's held-out error is known.

The toy's `future_rb` is an oracle Rao–Blackwell upper reference that replaces
the future sampled reward with its exact conditional expectation; it is not
the cheap policy-based future-step correction.

## Phase 1a: offline estimator audit

Record checkpoint rollouts with the exact behavior distribution, action masks,
used-head map, old log probabilities, rewards, values, terminals, and recurrent
states. Split by *episode* into fit and audit partitions; do not train a Q on
the same transitions used to judge its correction. Save a versioned log schema
and checkpoint hash. Check that replay of a sample reproduces actions, masks,
and value estimates.

On the frozen audit partition, calculate unclipped per-sample gradient
contributions under plain GAE, cross-head only, OB, future-step only, and
combinations using the exact intended formulas. Repeat after fitting a
per-head Q to one-step targets on the fit partition and freezing it. Report
per-head and per-verb-class sample counts, mean correction, gradient mean,
variance and a bootstrap interval over independent episodes. A correction
passes its zero-mean audit if its mean is compatible with zero at the
predeclared precision and its gradient mean agrees with plain GAE within
sampling error. A variance win must have a bootstrap interval below 1 for
the relevant rare item heads. Account for Q-fit and extra inference time.

These are standard conditional-baseline definitions selected for this study.
The toy verifies the identities for its finite problem; it does not predict
how much variance reduction the NetHack policy will show.

## Phase 1b: online policy-based comparison

Screen at 262.144M training steps, with seed-matched arms A baseline, B
cross-head only, C future-step only, and D both. At least four independent
training seeds per arm. Keep architecture, rewards, masks, optimizer and
evaluation protocol fixed. Evaluate every checkpoint from scratch on a fixed
set of environment seeds. Report metrics at both equal steps and equal
wall-clock; use equal wall-clock as the decision comparison. Predeclare the
primary rare-item-head gradient-variance metric, item achievement rates,
mean/median score and depth, and throughput. Confirm a clear winner at 1B
steps with at least four seeds. Do not infer a win from one run or one rare
event.

Only if the frozen-Q terms beat policy-based terms offline, add a separate
Phase 1c: Q-mean cross-head, then OB with a predeclared κ grid. Put the decoder
or Q rows on AdamW in every Q-based arm and measure that optimizer change as
its own control. Run replay-ratio/KL early-stopping work separately so it
cannot confound the variance-reduction arms.

## Decision gates

- No behavioral change with diagnostics on: identical fixed-seed checkpoint
  where the trainer is deterministic, or a documented tolerance otherwise.
- Measurement completeness: replay histogram counts, rare-verb sample counts,
  held-out KL, per-head variance, and achievement detector spot checks.
- Offline estimator validity: no detected gradient bias, and a clear variance
  reduction on targeted item verbs after uncertainty and runtime are included.
- Online continuation: lower rare-item gradient variance, no material score
  regression, and improved achievement rates or a convincing learning signal
  at equal wall-clock. A negative or ambiguous screen stops that arm.
