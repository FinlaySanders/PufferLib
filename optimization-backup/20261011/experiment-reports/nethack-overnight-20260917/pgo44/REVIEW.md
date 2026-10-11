# Movement-history cache candidate

Status: retained after broad engine correctness, rollout and loaded-training checks. No production edits or pushes.

## Change

The combined six-file patch is `../candidate-through-track40.patch`. Relative to PGO20, this adds one per-game proximity-count grid for the last 50 hero positions. History insertion/removal adjusts each position's 3x3 neighborhood. `gettrack` immediately rejects a query with zero nearby positions; otherwise it runs the original traversal and distance-skipping heuristic unchanged. This preserves even unusual teleporting histories. The extra duplicate-position shortcut was measured and reverted.

The combined patch also contains the previously validated removal of redundant floor-index invalidation, cached remaining SIMD floor-query matches, and distant-monster scare-check fast path. It does not change rewards, observations, actions, model architecture or PPO.

## Evidence

- Exact 7,725,056-case cache/search oracle, including stationary histories, walking, discontinuities, resets, wraparound and edge coordinates. Cache counts are directly checked.
- Complete selected32score traces and all512depth traces pass; raw observation snapshots match.
- Raw historical goldens preserve the same15 known baseline export mismatches. These are not reported as passes. The explicit historical-view adapter passes34goldens, status, interleaved, shuffled and26fuzz cases.
- Writable data symbols have identical names, sizes and sections versus PGO20.
- Patch reverse-application matches the original baseline hashes; forward-application matches the frozen candidate hashes.
- Fresh PGO: selected score replay +3.11%, excluded score streams +2.20% versus PGO20. Depth gains are close to noise.
- Fixed-policy rollout: original controls24.418/24.563 seconds, PGO20 21.523, candidate21.316 for4,194,304 measured decisions. Combined +14.89%, control drift0.60%; incremental gain overPGO20 about0.97%. Initial RNG states and32block-boundary packed observations match. Full action-level correctness is separately checked by recorded replay.

Frozen source: `../pgo44-source`, with `../pgo44-source-manifest.json` for642engine files and `../pgo44-source-assets.json` for unchanged auxiliary assets. Candidate library: `variant/libnethack.so`.

## Rebuild and screen without touching existing artifacts

Run from the experiment root, after other timed work has stopped:

```sh
trial=$(mktemp -d "$PWD/repro-pgo44-XXXXXX")
cp pgo44.py "$trial/"
cp -a pgo44-source "$trial/engine-source"
python "$trial/pgo44.py" "$PWD/pgo20/variant"
```

This collects fresh matching compiler profiles, builds with profile-use, verifies selected score/depth recordings, then runs paired timings. It relies on the preserved recorded corpora, data and build dependencies referenced in the script. Do not reuse profiles across changed source or claim independent speedups multiply.

Loaded training: {"seconds": {"baseline-before": 26.184596062, "pgo44": 24.65295148, "baseline-after": 26.363266229}, "mean_turns": {"baseline-before": 22733.674666666666, "pgo44": 23137.65066666667, "baseline-after": 23017.569333333333}, "gain_percent": 6.575195131564837, "drift_percent": 0.6823483798525709, "measured_steps": 3932160, "caveat": "Async loaded-training trajectories differ; this is a combined observation versus original, not a clean incremental cache gain."}
