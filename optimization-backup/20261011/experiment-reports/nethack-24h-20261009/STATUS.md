# NetHack throughput status

Updated 2026-10-10T10:22:03.971416+00:00. Requested original512 inference-priority, overlap-kernel, and ready-request batching tests COMPLETE. Original goal remains paused. No new optimization promoted.

Primary remains512 environments / horizon512 / fourbuffers /32workers /15.55Mmodel. Keep both entity fusions from entity512_20261010 (previous +3.07%) and high-priority independent inference. Fresh priority ABBA: high 228,613 SPS, normal 211,891 (-7.31%). Ready-request dispatcher: 222,981 SPS versus fresh independent 228,476 (-2.41%). No production defaults/source changed.

Matched profiled PPO kernels take about13% longer under overlap; inference kernels about2.5x, with only16us initial ready wait versus546us graph duration. Normal priority creates long intra-inference gaps and exposed rollout wait. Larger batches save35–56% isolated forward time but dispatcher overhead/lost concurrency makes this implementation slower overall; batch-size BF16 outputs also differ, so not a behavior-preserving candidate.

Read overlap512_20261010/REPORT.md, SUMMARY.json, ANALYSIS.json, KERNELS.csv and INTEGRITY.json. All64 replay observation proofs match; 19protectedfiles unchanged. GPU/profiler timing sums are not additive wall time. 2048remainssecondary; main pipeline remains GPU/overlap limited, not the earlier2048CPU-limited regime.
