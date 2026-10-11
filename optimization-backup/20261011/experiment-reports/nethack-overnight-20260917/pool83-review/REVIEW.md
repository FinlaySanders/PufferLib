# Shared pool candidate 83 — retained

This recovers the existing shared-pool implementation, not the central-counter
experiment. The latter was slower and is not proposed for retention.

With retained engine PGO61, four inference-buffer submitters share 24 CPU workers.
The initial tests below used20workers; two later worker-count screens selected24.
Submitters also execute environment work. The existing scheduler has separate
OpenMP teams, 32 total threads. Model, action sampling, initial GPU RNG state,
weights, observations, reward and PPO settings are unchanged.

The first matched-policy rollout comparison gave 19.43% higher throughput versus
PGO61 with the existing scheduler. An independent original/current/pool/original
comparison gave 37.62% combined throughput gain versus the original engine and
scheduler (0.209% control drift), versus 17.50% for PGO61 alone in that comparison.
Every arm matched all 32 block observation hashes and loaded-weight/RNG proofs.
These hashes are block-boundary checks, not a complete action trace.

Broader correctness evidence:
- Full concurrent recorded replay: 32 score streams, 4,472,832 decisions and
  10,315,606 keys; all streams completed with exact checks.
- Full concurrent recorded replay: 512 depth streams, 23,855,104 decisions and
  56,604,291 keys; all streams completed with exact checks.
- 60,000 concurrent regions each under regular, ASan/UBSan and TSan builds:
  exactly-once updates, varying and zero-size regions, worker counts including
  20/24/28, destruction and recreation.
- TSan had host memory-mapping startup failures; the non-PIE binary completed on
  its fourth launch. Failures and successful output are preserved separately.
- `shared-pool83.patch` reverses then reapplies exactly to the tested source;
  `manifest.json` records the hashes. The header is byte-identical to the earlier
  shared-pool prototype. This is a feature patch against the documented isolated
  trainer baseline, not a claim that it applies directly to current upstream.

Loaded-policy training completed: +5.90% versus retainedPGO61/WS, with 0.109% control drift. This is observational: asynchronous trajectories differ. A matched 24-thread WS control was 10.97% slower than WS32, while pool20 was 18.28% faster than WS32 (0.167% drift). All block hashes matched. This rules out simply lowering the WS thread count as the explanation. Combined training versus original was subsequently measured; see the current result below.

Evidence: ../pool83/summary.json, ../rollout83/summary.json,
../pool83-gates/results.json, ../pool83-gates/tsan-nopie.json.

## Current configuration and direct combined comparison

Use 24 workers plus 4 submitters, 512 agents and 4 buffers.
`../rollout93/summary.json` compares the original engine with WS32, engine61
with WS32, engine61 with pool24, and the original engine with WS32 again.
Combined throughput improves by 47.6488% (16.68184 seconds versus controls
24.61640 / 24.64465 seconds), with 0.1148% control drift. All 32 observation
boundary hashes, initial RNG states and loaded weights match. The engine
alone improves throughput by 16.6777% in this comparison.

`../pool89-training/summary.json` measures combined loaded-policy training:
observed throughput improves by 14.0610%, taking 23.03018 seconds versus
26.63806 / 25.89886 seconds. Controls drift 2.775%. Asynchronous learning
trajectories differ, so this is not matched-work causal attribution.

Scope limitation: `../depth102/summary.json` measures CPU-only fixed-action
replay of 512 depth streams. The engine alone gains 6.2166%; the combined
engine and pool gains 3.8711%. All timed workload counters match. The large
GPU rollout gain is not a general engine-only or depth-replay gain.

Alignment105, packing103/104, wait policy98, pause97, cross-help101 and
allocator94 are excluded. Allocator94 is documented separately as an optional
runtime choice with no demonstrated training gain.
