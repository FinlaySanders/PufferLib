# Correction: offline variance analysis omitted training reward clipping

The production trainer and the pinned capture snapshot both clamp the **total reward to [-1, 1] before GAE**. The original offline analyses used raw rewards, rounded to BF16 where applicable, without this clamp. This is an analysis error; it does not require a trainer change.

Code locations:
- Current production `src/pufferl.cu:1487`: `clamp_precision_kernel(..., -1.0f, 1.0f, ...)` in `train_epoch_gpu`.
- Pinned `capture-source/src/pufferl.cu:1521`: the same operation before the minibatch GAE call.
- GAE consumes these clipped rewards. PPO ratio clipping, value clipping and gradient clipping are separate operations.

Thus the 8,308.1494 raw polymorph reward becomes 8,320 in BF16 rollout storage and **1 in the training buffer**. The 4,292.3594 gain-level potion reward also becomes **1**. Raw game-event attribution and deterministic replay checks remain valid. The claim that those large magnitudes dominate training variance is withdrawn.

## Recomputed descriptive moments

Same 8,110,592 audit transitions per capture, same gamma and terminal handling. Only apply the missing reward clamp. `b = gamma * (1-done) * V(next) - V(current)`; `delta = clipped_reward + b`. These descriptive moments are not an attribution of irreducible noise or value-function error.

| Action seed | Reward share before (invalid) | Reward share after clipping | Largest game's squared-TD share before | After clipping |
|---|---:|---:|---:|---:|
| 31415 | 91.48% | 2.78% | 62.45% | 0.214% |
| 27182 | 79.12% | 2.73% | 37.17% | 0.212% |

After clipping, the bootstrap term accounts for approximately 100.1% of TD variance, with a negative covariance contribution of about -2.8% to -2.9% balancing the positive reward contribution. These shares add to 100%; they are not independent nonnegative fractions. About 1.94% of audit rewards are clipped.

## Scope of the invalidation

Missing clipping appears in `offline_analyze.py`, `q_analysis.py`, `puton_followup.py`, `verb_critic.py`, `verb_credit.py`, and `diagnostic_prepare.py`. Derived cached advantages, TD/Q targets, fitted critics and variance-reduction ratios must be regenerated/refitted before making training recommendations. This includes the earlier favorable drop/put-on results and the verb-side nulls. Clipping may change either conclusion; neither is established for the real training objective by the old runs.

The enumerable toy tests, planted-signal checks as synthetic checks, logged policy outputs, source snapshots and raw replay records are not invalidated by this finding. The game mechanic allowing rewarded XP regains after unpenalised XP losses remains, but each resulting total reward is capped at +1 during training.

Only the descriptive moment calculation has been rerun here. No auxiliary critics were refitted and no online training was started. Original tables/CSVs are retained for audit and their reports have been marked. Do not reuse old cached targets for a corrected run.

Artifacts: `moments.csv` and `../check_reward_clipping.py`.

## Corrected rerun completed

The full corrected rerun is now in [corrected_variance/REPORT.md](../corrected_variance/REPORT.md). It uses production CUDA targets, fresh fits and both game/stream audits. The historical unclipped results remain invalid.
