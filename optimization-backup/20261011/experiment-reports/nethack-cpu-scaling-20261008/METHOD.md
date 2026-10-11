# CPU scaling and optimization study

Base: validated engine14 and shared pool from the 8 October comprehensive study. Live project files and previous study artifacts remain untouched.

First screen: fixed 5.10M network, replay the same 512 mature score-policy action streams, duplicate streams for larger env counts. 512/1024/2048 envs, four buffers, 262144-decision training batch, horizons 512/256/128. Fixed per-environment warm-up and measured decisions; all inference, PPO, and optimizer work executes with frozen actor weights. This is a throughput control, not a learning comparison: horizons differ and recorded actions are off-policy for the small network.

Check duplicated observations equal their source, frozen weights unchanged, and boundary hashes match the earlier teacher wherever decisions align. Larger training batches and worker counts are separate follow-ups. Repeats and counterbalanced order for finalists.

CPU candidates: short recorded gameplay replay screening, matched observations, then full training pipeline checks. Profile CPU simulation and observation work independently of scheduler waits. Hardware perf unavailable previously; use Callgrind instruction profiles if still unavailable. Later engine44/61 remain quarantined until the observation discrepancy is resolved.

Completed outcome: the discrepancy was localized to undefined message text and corrected identically in both comparison engines. The recovered optimization package then passed every-action replay, optimizer equality and golden/fuzz gates. See REPORT.md and VALIDATION.json. Final builds also carry the previously established fire-trap fix.
