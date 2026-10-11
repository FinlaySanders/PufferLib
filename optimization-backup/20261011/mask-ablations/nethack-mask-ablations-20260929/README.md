# NetHack mask ablations — 29 September 2026

Originally 35 training runs: seven variants, five planned seeds each (2901–2905), 1 billion requested steps per run. On 30 September, the user cancelled the remaining four seeds each of `no_verb_eps` and `no_run_search20`. Both completed first-seed results are retained. The revised campaign contains 27 models: five seeds for each of the five continuing variants, plus those two completed models. The trainer rounds down to 999,817,216 steps. Uses the article score recipe: 512 agents, four buffers, 32 threads, horizon 512, 1024-wide four-layer recurrent policy (15,552,136 parameters).

| Variant | Difference from baseline |
|---|---|
| baseline | Current source defaults, explicitly `NH_ZT_MASK=0` |
| no_handless | Disable inferred handless-form restrictions on wield/throw/wear/Elbereth |
| zero_time_on | Enable `NH_ZT_MASK=1` during both training and evaluation |
| no_hostile_rays | Allow every throw/zap/cast direction; keep MOVE and RUN rules |
| no_item_strategy | Remove satiation, fresh-spellbook retention, and shop-affordability gates together |
| no_run_search20 | Disable both RUN and SEARCH20, as in the depth action set, but retain score rewards/hypers |
| no_verb_eps | Remove uniform legal-verb exploration mixture |

All other architecture, rewards, action macros, public observation rules and PPO consumed-head gating remain fixed. In particular, this does not add the later identify-target head or discovery replacement. The three item restrictions and RUN/SEARCH20 are grouped variants, not individual causal estimates for each constituent rule. Peaceful movement avoidance and basic item/class/curse/layering checks remain in place.

## Order and evaluation

Each seed round runs all seven variants. Round 1 starts baseline, no_handless, zero_time_on, no_hostile_rays, no_item_strategy, no_run_search20, no_verb_eps. Each later round rotates that order by one place. `manifest.json` contains the remaining plan, with cancelled jobs removed and completed jobs retained. `manifest.before-cancellation.json` preserves the original 35-run plan; `cancellations.json` records the eight removed jobs.

After each model, a fresh process evaluates it on the pinned fork engine with its own training mask settings and no verb epsilon. Evaluation seed 7, 512 agents, one buffer, 32 threads. Keep exactly 2,000 completed games after dropping the first 4,000; preserve the full raw log as well. `analyze.py` is the unchanged existing burn-in score analyzer, applied to the first 6,000 rows. These are fork ablation results, not new Python Challenge certificates.

The queue records score, maximum depth/XP, BALROG depth/XP progression, per-verb use counters, nonadvancing actions and policy-step-limit episodes. It does not claim actual landmark visits from depth. Existing verb counters measure macro-specific uses, not guaranteed successful game effects.

## Validation

See `VALIDATED.json` and `validation.log`:

- Targeted mask fixtures verify handless, each grouped item gate, hostile rays, RUN/SEARCH20 and zero-time on/off. Blind reading remains blocked; movement masks are unchanged by the ray ablation.
- At 2,097,152 training steps, the all-default ablation binary produces a byte-identical checkpoint to an independently built unchanged source binary.
- Every variant completes a 2,097,152-step smoke training with finite weights.
- A real engine/policy evaluation verifies the episode recorder's 35-column output.

## Operation

The original queue runs in detached tmux session `nethack-mask-ablations`; its replacement runs in `nethack-mask-ablations-continue`. It survives terminal disconnection. It takes an exclusive lock and checks hashes of the binaries, configs, engine and key sources before each training run.

```bash
python3 /puffertank/experiments/nethack-mask-ablations-20260929/status.py
tail -f /puffertank/experiments/nethack-mask-ablations-20260929/queue.log
```

`active.json` records the active process ID, its kernel start tick, command and log. `events.jsonl` records starts, exits, model completion, eval results and replacements. `RESULTS.md` updates after each completed evaluation. Final models are under `checkpoints/nethack/<run>/0000000999817216.bin`.

Training failures get fresh replacement seeds appended after the planned interleaved jobs, with up to two replacement attempts per planned job. Failures and replacement seeds remain visible; replacements are not treated as paired seeds. Repeated failure stops the queue for inspection. A valid complete finite checkpoint is kept even if process teardown fails. Evaluation failures retry the same checkpoint once and otherwise remain flagged without retraining or selecting a better model. Fifteen minutes without any process log output is treated as a stall; only that owned child PID is terminated.

The source snapshot and experimental logging/mask changes are isolated here; see `environment.patch`. The main checkout is not modified by this campaign. `lib/libnethack.so` and `dat/` are copied, and the runtime library/data paths point here. The baseline includes the current cuBLAS fix; parked engine and architecture experiments are not applied.

## Scheduler reload on 30 September

The current `no_hostile_rays_s2902` training and its evaluation finish under the original controller. Its existing source-integrity check then stops it at the next job boundary because `queue.py` has been updated to honour cancellations. This expected controller assertion is not a training failure. `reload_queue.py` is already waiting in the replacement tmux session. It requires the active job to be completed or marked failed, verifies the new controller and all unchanged experimental artifacts, preserves pending replacement seeds, filters cancelled jobs, and starts the updated controller. No training process is stopped or restarted. `QUEUE_RELOAD_STATUS.json` records the handoff state.
