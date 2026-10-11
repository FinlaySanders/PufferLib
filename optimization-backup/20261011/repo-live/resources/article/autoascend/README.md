# AutoAscend on the stock Python challenge

Drone workspace: /workspace/autoascend-benchmark.
Agent: https://github.com/maciej-sypetkowski/autoascend
Pinned commit: 8527910bd85c4d851c18ad912aae606c92cd516a (existing local clone).
The agent and /workspace/nle-stock sources are unchanged.

Runner uses gym.make("NetHackChallenge-v0") with default options, timeout and
unseeded resets, exactly as the RL Python runner. No fixed clock.
Unlike AutoAscend's supplied simulation launcher, it does not modify NLE to
enable seeds, reduce no_progress_timeout to 1000, or truncate at 720 seconds.

Compatibility adapter passes the first 26 blstats fields expected by AutoAscend;
the additional public alignment field is omitted. get_seeds returns None only
for diagnostic logging. The agent's own RNG remains its upstream default.
Dependencies are installed in an isolated Python 3.12 venv; packages.txt records
versions. This is a contemporary-environment re-evaluation, not an exact
reproduction of the 2021 software stack.

env_score is the last live blstats score before termination, matching our RL
certificates (NLE blanks the terminal observation's blstats). All attempted
games are logged, including errors. A nonterminal failure stops that worker and
makes a full certificate incomplete; do not silently drop or replace failures.
No first-completion cutoff or burn-in; each worker must finish its assigned games.

4-game smoke precedes a planned 96-worker x 42-game run (4,032 episodes).
No result is a certificate until all assigned episodes are accounted for and
termination/error records have been audited.

## Restart with upstream recovery enabled

The first full run stopped after 87 completed games: upstream AutoAscend asserted
that it expected a wear prompt but received an eat-corpse prompt. That attempt
is preserved under cert4032 and is not a certificate.

The replacement run is cert4032_recovery (PID 1233940 at launch), using
run_recovery.py. It enables AutoAscend's own panic_on_errors option (equivalent
to upstream --panic-on-errors), which recovers through its existing ESC/reset
strategy. No agent source edits. Panic counts/messages are recorded.
All 4,032 games start fresh; no successful-game selection from the first run.
This setting is part of the benchmark configuration and must be reported.

## Restart with upstream-style attempt accounting (2026-09-14)

The first recovery-enabled batch stopped at 102 environment completions and one
`Cyclic Panic: UNKNOWN`. This was a harness failure: a bot exception cancelled
all workers. Those partial results are not a baseline.

`run_attempts.py` follows the failure-accounting convention in upstream
`bin/main.py:single_simulation`: retain each attempted game, record exceptions
and timeouts, then continue. A bot failure is **not** an environment completion.
The original bot source and stock engine are unchanged. No failed games are
retried or excluded. Infrastructure failures before any action still stop the
batch. The per-game wall-clock limit is 720 seconds, matching upstream's runner.
The run retains our existing `panic_on_errors=True`, challenge-default
no-progress limit and unseeded real-clock environment.

Run directory: `/workspace/autoascend-benchmark/cert4032_attempts`.
96 workers x 42 attempts = 4,032 attempts. Previous aborted batches are excluded.

Scores use last live `blstats[9]`, consistently with our RL evaluation; upstream's
own reported score is recorded separately. Summary emits aggregate scores only
when the entire worker/episode matrix is present, with no duplicates. It reports
all outcome counts, and additionally mean/median treating unfinished attempts as
zero. These are evaluations with agent-error/timeout accounting, **not** 4,032
naturally completed challenge games. Publish the failure count and timeout rule
alongside any comparison. This does not replace the published AutoAscend results.

Validation: a separate 4-worker x 2-attempt run with forced 2-second timeouts
recorded all eight timeouts and continued to every worker's second attempt.
Underlying panic tracebacks are now preserved even when `wrapper.main()` raises.

## Pooled completed baseline

Both `cert4032_attempts` and `cert4032_attempts_r2` are complete (4,032 attempts each). The current figure baseline pools all 8,064 rows: mean 8,988.048363095239; median 5,527.5. There were 7,610 environment completions, 446 agent exceptions and eight timeouts. All attempts retain their last live score, with no retries or exclusions. `results/pooled_attempts.json` preserves the pooled score rows and SHA256s of all 192 source worker files; `results/summary_batch1.json` preserves the previous baseline.
