---
name: wandb-bridge
description: "Native wandb logging for 5c trainer — jsonl emission + sync script, replaces the tailer"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-09-03T21:59:25.373Z
---

2026-08-01: replaced the frame-parsing wandb tailer. `base.wandb=True` makes
the trainer write `<log_dir>/<env>/<run_id>.jsonl` (one JSON line per epoch,
all last_log keys incl. agent_steps) + config ini up front. Bridge:
`scripts/wandb_sync.py --project encoders --group G --name N -- ./puffer
train nethack ...` (live, injects base.wandb/run_id, summary+exit on child
end) or `--file X.jsonl` (post-hoc import — any historical run re-syncable).
x-axis via define_metric(step_metric=agent_steps), no step monotonicity
issues. Metric names namespaced (env/score not score — old tailer runs used
bare names). AGGREGATION SEMANTICS: jsonl env/* = cumulative
episode-weighted mean since run start (vec_log clear=0), wiped at eval
boundary so eval tail converges to the citable warm-eval mean; the
DASHBOARD METRICS PANEL = run-average of that history — my 2M canary
"score 25.828" is that double-smoothed panel number (final-epoch cumulative
mean is ~40.9), still valid as a bit-determinism canary. Validated e2e:
warwick-dcs/encoders/runs/dbjzjicz. Staged, not yet committed.

READING GOTCHA (2026-08-05): `run.summary["env/score"]` is ONE epoch row, and
per-row sigma at 250M is ~600-730 — single rows have flipped my read twice in
one session (a −452 gap read as −1081; the worst run read as the best). Always
average the last ~30 rows of `scan_history(keys=[...])` and quote the sigma;
cross-check mean60 to confirm the window isn't the noise source. `scan_history`
also avoids the `history(samples=N)` row cap that made me report truncated runs
as full — for length use `summary["agent_steps"]`, never the row count. Tails
still run −70 to −450 optimistic vs certified 10K evals, which stay the arbiter.

2026-08-12 REMOVED FROM SHIPPED CODE (user call, with warm-start): pufferl.cu
wandb block + scripts/wandb_sync.py + default.ini `wandb` key all deleted on
the cleanup branch — PR ships NO wandb integration. Both live in git history
(815dd8e4 wandb integration; warm-start in the pre-cleanup diff). FUTURE RUNS
that need wandb streaming or warm-start fine-tunes must re-apply as LOCAL
patches (cherry-pick 815dd8e4 or hand-restore ~30 lines) — never re-add to
main without asking. Gates PASS (both inert without base.wandb/load_model_path).

2026-08-12 PM RE-COMMITTED (user call, supersedes the never-commit rule):
28a92bab "wandb + burnin eval" = pufferl.cu wandb jsonl block + NEW eval row
({agent_steps(post-eval), eval/score, eval/n} streamed after the inline 10K
eval — wandb summary now carries the certified number; verified 2M+50M) +
eval_loop burnin_games restore + scripts/wandb_sync.py. Warm-start stays out.

2026-08-14 STRIPPED AGAIN — FINAL (user call, resolves the PR question):
58d36aaf "nethack challenge" (squash) deletes scripts/wandb_sync.py + the three
pufferl.cu jsonl blocks (-180). Burnin ALSO stripped in the same squash (see
[[nethack-cert-protocol]]; scratchpad/burnin.patch re-adds it); end-of-run
logs/<env>/<run>.ini config+[metrics] writer KEPT (core logging, independent
of wandb — fpgate non-wandb runs produce full inis). Both fingerprint arms
PASS unchanged. Re-apply for monitoring: `git apply scratchpad/wandb.patch`
(verified) + scratchpad/wandb_sync.py.keep — build a side binary, never
re-commit. Certs are always readable from logs/*.ini without wandb.

2026-09-03: scripts/wandb_sync.py is back in the tree (committed d9bf2b77) but the
trainer has no wandb code, so wrapping `./puffer train` fails instantly with
"missing key [base] wandb" (child exits rc=0 in ~2 s — check the run log, a
chain script will race through every seed). Run plainly, import logs/<env>/<run>.ini
[metrics] post-hoc (box-only scripts/wandb_ini_import.py did this for the sweep).

2026-09-07: scripts/wandb_sync.py DELETED from 5.0-nethack in the release cleanup (user request). Recover from commit d9bf2b77 (`git show d9bf2b77:scripts/wandb_sync.py`) if needed.
