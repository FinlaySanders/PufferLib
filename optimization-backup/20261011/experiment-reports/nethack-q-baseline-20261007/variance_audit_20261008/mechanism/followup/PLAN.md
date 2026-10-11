# Follow-up: predictable value dips and PPO control sensitivity

CPU only. Keep the active campaign and all pinned files unchanged.

1. Use the two held-out 524M rollout samples (16180, 27182). For put-on,
   take-off, quaff and read, follow rewards, values and episode ends for
   1, 2, 4, 8, 16, 32, 128 and 512 policy decisions. Stop bootstrapping at
   episode boundaries and explicitly exclude right-censored endpoints.
2. Split by pre-action verb sampling probability (<1% versus >=1%). Report
   ordinary and item-policy-Gini-weighted means, with stream-clustered
   bootstrap intervals. The latter weights meaningful item choices without
   selecting on their subsequent advantages. Retain all groups and horizons.
3. Inspect large-gradient event traces. These are selected examples, not an
   unbiased effect estimate. Distinguish a transient value dip from evidence
   of actual long-term opportunity cost; observational futures cannot settle
   a causal counterfactual between verbs or items.
4. On the same captures, perturb item-query directions in a controlled way
   while retaining masks and actual epsilon mixtures. Measure the baseline
   correction before/after PPO clipping, using full verb+item importance
   ratios. Use the already frozen shared neural critic. Include strength 1,
   the previously selected strength, and a strength fitted on validation
   streams only for each perturbation; evaluate on disjoint audit streams.
5. These controlled policy changes are a sensitivity test, not a replay of
   actual training. The files do not contain live per-example PPO values or
   recurrent features after actor updates. Do not claim to have measured
   the online contribution of value drift or clipping from this test.

Use clipped BF16 rewards and the existing gamma. Reproduce saved ratios and
one-step targets before interpreting new calculations. Save CSVs, examples,
input provenance, numerical checks and a report including null results.
