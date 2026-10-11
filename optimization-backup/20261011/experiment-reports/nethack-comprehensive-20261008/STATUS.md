# Completed — NetHack comprehensive performance study

All measurements, twelve Nsight captures, repeated model-size comparisons, auxiliary-Q comparisons and final checks are complete. No study jobs remain on the GPU. Live tracked changes are the same pre-existing drone files and depth.ini; protected file hashes are unchanged.

Read REPORT.md for conclusions, METHOD.md for the protocol, and FINAL_VALIDATION.json for validation. FINISHED.json records completion. There are 24 passing final checks plus passing exact-update checks after 1,808 minibatch updates. Source, binaries, commands, checkpoint hashes, raw timings, traces, kernel CSVs and charts are retained here.

Fresh full-pipeline results (RTX 4090 / i9-14900K, policy updates discarded):
- Early/random 15.55M: 168.7k current →185.1k retained SPS.
- Mature score 15.55M: 98.1k →176.1k.
- Depth 4.31M: 307.8k →342.1k, a separate shorter-game workload.
- Same mature recorded actions at 5.10M: 105.8k →208.7k.
- Mature components: engine alone125.9k; engine+pool164.3k; GPU-only100.9k; all176.1k.
- Research auxiliary-Q fitting/logging overhead:2.2% early,1.1% recent1B.

The current cuBLAS4MiB/default-math fix is common to both sides. Retained means engine14 + pool83 + tested GPU flags. Out-of-place Muon/cuBLASLt failed update equality on the current stack and is excluded. Engine44/61 failed a new mature observation-boundary comparison and are excluded; exact responsible change remains unidentified. The validated subset matches the tested boundary trajectories, not an exhaustive all-seed equivalence guarantee.

A single Nsight depth launch failed at startup without a trace. Standalone smoke and full profiled retry passed with matching observations; failed artifact preserved and no timing used. Its cause is not established.

The main explanation: mature current rollouts outlast PPO by1.22s/batch; retained reduces that to0.05s. GPU graph/copy idle falls33%→5%. Retained15.55M PPO elapsed time is roughly47%optimizer,34%backward,18%forward,1%GAE/loss, with inference concurrent. Smaller models expose CPU rollout limits again (22%GPU idle even retained).

No further run is queued, and no production source/default/commit was changed by this study.
