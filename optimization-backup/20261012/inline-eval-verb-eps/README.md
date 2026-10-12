# Inline final eval runs with un-annealed verb_eps (handoff, 2026-10-12)

Since a3338d99 ("Hacky multigpu close fix", 2026-09-07) `run_train` closes the trainer and runs the final 10K-episode eval on a fresh
`eval_make` context. `create_pufferl` -> `nethack_policy_init` re-uploads `train.verb_eps` (base, un-annealed) to the device, and
`eval_loop` never calls `nethack_policy_on_rollout`, so the eval samples uniform random legal verbs at the base rate (0.5% in the
champion config, ~14 random verbs per game). `eval_make` zeroes `train.verb_eps` only when `base.eval_agents != -1`; the default -1
(use the training agent count) keeps it. Before a3338d99 the eval reused the live trainer, where verb_eps had annealed to 0.

Measured (1B champion seed 3001, this box): inline final point 9,714.6 vs the standalone certification protocol (eval_agents=512 =>
verb_eps 0, 14K games, first 4K dropped) 12,871.7 +- 144 SE, median 8,756 — in line with the certified 1B runs (14,317 / 13,003).
Cold start of the fresh vec explains only ~4% of the gap (first-10K mean of the same cert data: 12,354); the rest is verb_eps.
Signature: inline-eval dashboards show searches 1.97/game vs 0.82 at train end, episode_length 2771 vs 3498, throws 152 vs 198.

Consequence: every inline final point since 09-07 for a config with verb_eps > 0 is biased low, and sweeps consume these points.

Fix (`inline_eval_verb_eps.patch`, one hunk in `eval_make`): zero `train.verb_eps` in the `eval_agents == -1` branch too. The
remaining cold-start censoring (~4%) is the separate burn-in question (`base.burnin_games`, side patches exist).
`pufferl_patched.cu` is the patched copy of src/pufferl.cu at 3719caaa; `git apply --check` passes on that tree.
