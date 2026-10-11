# Bounded ready-buffer preference — 9 October 2026

Hypothesis: periodically complete a full ready-buffer sweep while otherwise retaining the locality of the previous preferred-buffer recheck. Reduce small-population waiting without losing the large-population gain.

| Variant | 2048 games | 512 games |
|---|---:|---:|
| Unbounded preference | +9.04% | -3.58% |
| Limit 4 productive scans | +4.44% | -1.32% |
| Limit 16 productive scans | +7.32% | -2.10% |

Decision: neither quota solves the tradeoff. Park both as universal defaults. Smaller quotas reduce both the large-population gain and the small-population regression. No new optimisation retained. A future scheduler hypothesis should address placement/contention directly rather than another arbitrary quota.

Method: unchanged retained engine; CPU-only isolated env_pool.h patch. Same prepared state for every trial, with memory, private files and file positions restored. Warm8064 in chunks128, then128 ordinary settle decisions per child. Ordinary measured decisions only:2048x512 and512x2048. Mode order baseline/quota4/quota16/unbounded/unbounded/quota16/quota4/baseline. 24 pinned workers +4 submitters, heavy tests serialized. Each variant repeated twice. Control ranges0.33% at2048 and0.16% at512; descriptive, not confidence intervals. Native endpoints, game times and total world-turn advances match across all sixteen trials. Every-step proof/full golden/fuzz/full training NOT rerun for these parked variants; no claim beyond the bounded screen. Previous fast-loop snapshot validation remains separate evidence, not validation of these new quotas.

At512, mean voluntary context switches were5764 baseline,18715 quota4,28905 quota16 and48062 unbounded. The quota reduces waiting but does not remove the performance loss. This is correlation with waiting, not an exclusive causal attribution.

Exact sources, build command, patch, run commands and results are in this directory. Retained engine and8 protected production files unchanged. No production edits, commit or push. No running job remains.
