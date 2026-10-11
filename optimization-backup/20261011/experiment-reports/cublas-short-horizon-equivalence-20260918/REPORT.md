# Current branch: repeatability and upstream equality

PASS: short-horizon NetHack, actual current branch versus upstream 5.0 (6ffa5b10), on RTX 4090.

Four serial ABBA runs, seed 901, normal initialization, clean fast-nle e7f656856, 512 agents, four rollout buffers, horizon 128, async enabled, 32 updates / 2,097,152 steps each. Production sources were copied directly, with no diagnostic trainer instrumentation. A checkpoint was saved every update.

All 32 checkpoints are bitwise identical across all four runs (128 saved checkpoints). Both upstream repeats and both patched repeats match. All weights finite and all runs successful.

The current full git diff exactly matches cublas-upstream-match-20260918/after.patch, and both algo.cu and pufferl.cu match that verification's source snapshot. Its nine passing configurations therefore remain applicable: CPU Breakout, GPU Breakout, 2048, CartPole, Pong, Drone, T-maze, GPU Admiral, NMMO3.

Combined: all TEN tested repeatable upstream configurations repeat with the current patch and match upstream byte-for-byte. This is bounded evidence for these tested shapes, seed, durations and machine, not a universal guarantee. Default long-horizon NetHack and other non-repeatable upstream configurations are excluded from cross-version equality claims.

The working diff is unchanged. Exact commands and hashes: results.json.
