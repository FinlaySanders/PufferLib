# Nearby-entity passthrough ablation

Five 1B policies, seeds 2901–2905, compared with the five existing baseline policies in `baseline_reference.json`. Runs begin automatically after all five combined-mask-removal policies finish training and evaluation.

The only policy change is `NH_NO_NEARBY_PASS`: zero the 16-dimensional nearest-monster representation, 16-dimensional nearest-floor-item representation, and 16-dimensional underfoot-item sum in the concatenated encoder output. Their direct backward contributions are disabled too. Monster/item sum and max pooling, inventory passthroughs, pointer keys, observations, rewards, architecture dimensions, initialisation and parameter count remain unchanged. Keeping the 48 zeroed columns isolates their information from a capacity or layout change. This is an experimental ablation; physical removal of the columns would be a later cleanup.

Use the original baseline masks: handless, hostile-ray and strategic item restrictions enabled; zero-time refusal masking off. RUN/SEARCH20 and annealed verb epsilon remain enabled. This does not combine the passthrough removal with the preceding mask removals.

Each run trains for 999,817,216 actual steps (the batch-aligned 1B target) and then performs a separate 6,000-game fork evaluation, discarding the first 4,000 completions and retaining 2,000. The evaluation uses the same ablated GPU policy and baseline masks, with verb epsilon zero. Failed training attempts receive fresh replacement seeds, up to two replacements, and evaluation retries once.

The frozen baseline trainer, engine and configs are copied from the earlier campaign. Production source and the running campaign are untouched. `experiment.patch` contains the encoder change and the corresponding conditional change to the C demo. A demo must be compiled from this isolated source with `NH_NO_NEARBY_PASS` to display these policies correctly; the existing production demo is not the ablated architecture.

## Validation and queue

Builds are CPU-only. GPU validation waits for the prior campaign's `DONE.json`, all five successful per-run completion records, release of its queue lock, and an idle GPU. No fixed-delay start or log-line trigger is used.

Before any 1B job starts:

- Compare the actual forward/backward passthrough kernels against an independent selection-matrix oracle, including invalid entities, empty lists, multiple underfoot items, unchanged surrounding slices and an adjoint check.
- Run 2M-step reference and patched-but-disabled control training; require byte-identical final weights.
- Run 2M-step ablated training; require a different finite checkpoint with the same 15,552,136 parameters and correct baseline settings.
- Run a real evaluation smoke test and check the episode recorder.

Validation failure stops the new campaign. `VALIDATED.json` is only written after all checks pass. It is expected to be absent while waiting for the current batch.

Detached tmux session: `nethack-nearby-pass`.

Status: `python3 /puffertank/experiments/nethack-nearby-pass-20261002/status.py`.

Scheduler state: `SCHEDULER_STATUS.json`. Results: `RESULTS.md` and `runs/*/results.json`.
