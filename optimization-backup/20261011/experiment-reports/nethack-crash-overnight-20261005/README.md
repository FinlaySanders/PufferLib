# Patched NetHack crash stress queue — 5 October 2026

Five sequential 1B-step training runs on GPU 0 using the isolated fire-trap fix, with GDB fault capture. They use the original frozen trainer, data and configs; only the engine library, seed and isolated output paths differ. No source or binaries in the PufferLib working tree are changed.

| Order | Run | Reason |
| --- | --- | --- |
| 1 | combined_s2901 | Original combined-mask run crashed at ~295.7M steps. |
| 2 | baseline_s2908 | Original baseline crashed at ~531.9M; targeted patched 560M run passed, but no full 1B run yet. |
| 3 | baseline_s10147 | Original baseline replacement crashed at ~825.5M. |
| 4 | combined_s2911 | Fresh seed for the combined-mask configuration. |
| 5 | baseline_s2912 | Fresh seed for the baseline configuration. |

The queue holds the original campaign lock, runs one trainer at a time, checks for an idle GPU before each run, and **stops on the first signal, nonzero trainer exit, missing final checkpoint or supervisor error**. A clean pass is evidence for the patched build on that seed, not proof that every historical crash had the same cause. Check `QUEUE_STATUS.json`, `queue.jsonl`, and `runs/<run>/STATUS.json`; faults include `signal.json`, GDB backtrace/registers in `training.log`, and engine traces in the run directory. The final checkpoint for a clean run is `checkpoints/nethack/<run>/0000000999817216.bin`.

The patched engine SHA-256 is `ad1007c6a0c3880a00f5866b99304423d6483c72fff90fefadce8c7689f132a3`. Original trainer SHA-256 is `59095fb74818d56ec72af64d816d4f0c88f1942c010cccb11b12abe9db3df5d1`. The earlier patched seed-2907 1B run passed at `/puffertank/experiments/nethack-crash-patched-1b-s2907-r2-20261005`.

## Score evaluations

`evaluate.py` waits for training to finish, then evaluates the six patched policies (the five queued here plus the earlier patched seed 2907) with the established seed-7 protocol: 6,000 games, first 4,000 discarded, next 2,000 retained. Status is in `EVAL_STATUS.json`; results appear in `EVAL_RESULTS.json` and `evals/*/results.json`.

At the user's request, training seed 2912 was intentionally stopped at ~08:52 UTC on 6 October; its two partial checkpoints are preserved and it is excluded from score comparisons. The short evaluation waiter was cancelled before it evaluated anything. `long_eval_now.py` started the long certs directly at ~08:54 UTC. It evaluates all **20 completed policies** across the original baseline, later baseline, original combined-removal, and patched cohorts. Each gets **14,000 games, with 4,000 burn-in and 10,000 retained**, on the pinned patched engine. It records per-policy scores, the first 2,000 retained games for comparison with previous evaluations, and between-policy spread. Status is in `LONG_EVAL_STATUS.json`; results appear in `LONG_EVAL_RESULTS.json` and `long_evals/*/*/results.json`. The queue runs serially on the single GPU and stops on a fault or failed evaluation.
