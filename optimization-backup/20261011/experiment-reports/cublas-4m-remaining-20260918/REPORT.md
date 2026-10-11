# Remaining environments: exact current 4 MiB branch

Eight serial runs, two per environment, seed 901, 32 training updates. Exact configurations and commands reused from the upstream repeatability matrix, including single-GPU Craftax and adequate evaluation agent counts. No diagnostic RNG or reduction fixes included. All runs exited successfully; all 16 checkpoints have finite weights. Full working diff unchanged.

| Environment | Upstream repeats | Current branch repeats | Consistent equality across versions |
|---|---|---|---|
| Minimal | No | No | No |
| Asteroids | No | No | No |
| Snake | No | No | No |
| Craftax | No | Yes | No |

One Minimal candidate run happened to match one of the two upstream reference runs at both saved checkpoints; the other did not. This is not a repeatability or cross-version-equivalence pass. No other candidate run matched either upstream reference.

Combined with prior verification: all ten tested repeatable upstream configurations remain repeatable and match exactly under the current patch. Default long-horizon NetHack and Craftax become repeatable under the patch, but do not match the non-repeatable upstream references. Minimal, Asteroids and Snake remain non-repeatable and need separate environment/encoder fixes.

Limits: tested seed, shapes, duration, machine/toolchain only. Exact commands and SHA256 hashes: results.json; summary: summary.json.
