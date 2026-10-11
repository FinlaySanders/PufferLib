# Fresh baseline replication — 3 October 2026

Five new 1B baseline runs (seeds 2906–2910) to check whether the unusually small between-run spread of baseline seeds 2901–2905 repeats. Keep these five results identifiable separately from the original baseline group.

Uses byte-identical copies of the original mask-ablation campaign's trainer binary, engine, runtime configs and analysis script. All original handless, hostile-ray and strategic item masks are enabled; zero-time masking is off. RUN/SEARCH20 and verb exploration are unchanged. All entity passthroughs are present. Model size is 15,552,136 parameters; training uses 512 environments, four buffers and 32 threads. Requested length is 1B steps; the final complete training batch is 999,817,216 steps.

After each run, evaluate with the existing fork protocol: seed 7, 512 environments, one buffer, 32 threads, epsilon disabled, 6,000 games total. Discard the first 4,000 and retain 2,000. This gives 10,000 retained games across the five new policies. Failed training attempts receive fresh replacement seeds (10145–10149, then 10245–10249), with at most two replacements per planned run; evaluations retry once. A finite complete checkpoint remains usable if only trainer teardown fails, matching the existing campaign protocol.

The detached tmux session `nethack-baseline-repeat` waits for the nearby-passthrough campaign's DONE artifact, all five successful per-run evaluations, its queue lock to be released, and an idle GPU. It then runs these five sequentially. It holds the predecessor lock during the new campaign to prevent overlap from a restart. It survives terminal disconnection.

`VALIDATED.json` is inherited validation evidence from the original campaign, not a newly run GPU test. `PREPARED.json` records local hash/config/scheduler checks. All runtime artifacts and scripts are pinned in `manifest.json`; `source` points to the preserved original source snapshot.

Status: `python3 /puffertank/experiments/nethack-baseline-repeat-20261003/status.py`
Results: `RESULTS.md`, `runs/*/results.json`, `events.jsonl`.

## Held for speedup review — 2026-10-03T11:45:53Z

The waiting scheduler was stopped by its verified PID before any baseline training started. All five jobs remain queued. The active nearby-passthrough campaign continues unchanged. Restart only after the speedup review is complete; see `HELD.json`.

## Resumed — 2026-10-03T13:28:32Z

User requested starting the five queued baseline seeds now. The original binary, engine and settings are unchanged; no speedup package was enabled. The old hold record is preserved in `history/HELD-speedup-review.json`.
