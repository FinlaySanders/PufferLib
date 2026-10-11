# Combined NetHack mask removal — 2 October 2026

Five fresh 1B runs with handless, hostile-ray, and strategic item restrictions removed together. Seeds 2901–2905 match the completed baseline policies recorded in `baseline_reference.json`. This follows the individual ablations in `/puffertank/experiments/nethack-mask-ablations-20260929`.

Uses the exact same frozen binary, engine, configuration, architecture and hyperparameters as that batch. Uniform verb exploration and RUN/SEARCH20 remain enabled; zero-time masking remains off. The three ablation flags are passed in both training and evaluation. Actual training length is 999,817,216 steps per policy.

After each run, evaluate on the fork with seed 7, 512 environments, one buffer and 32 threads, with verb epsilon disabled. Drop the first 4,000 completed games and retain the next 2,000. Preserve raw episode scores, depth/XP progression, and action-use counters. The five finished policies will contribute 10,000 retained games.

The queue runs in detached tmux session `nethack-mask-combined`. Failures receive a fresh replacement seed, up to two replacement attempts; evaluation retries once. No production source edits are needed. `source` points to the hash-checked parent snapshot; binaries, engine and runtime configs are independent copies.

Status: `python3 /puffertank/experiments/nethack-mask-combined-20261002/status.py`.
Results: `RESULTS.md`, `runs/*/results.json`, `events.jsonl`.

Original baseline-equivalence and individual-mask validation is recorded in `PARENT_VALIDATED.json`. A fresh combined-mask training/evaluation smoke check is recorded in `VALIDATED.json` before launch.

## Queue recovery — 2 October, 17:15 UTC

The controller ended with `KeyboardInterrupt` around 17:12 UTC while seed 2904 was at approximately 450M steps. Both processes were stopped; the origin of the interrupt is unknown. The two completed evaluations (2902 and 2903) were preserved. The interrupted attempt's logs and checkpoints remain in place, with an `INTERRUPTED.json` record; the old queue state is archived under `recovery/20261002T171522Z/`.

The queue was restarted in detached tmux after all frozen artifact hashes were verified. The remaining order is seed 2905, replacement 10135 for the earlier seed-2901 crash, then replacement 10138 for interrupted seed 2904. Both replacements start fresh under the existing retry policy. Training and evaluation settings are unchanged.
