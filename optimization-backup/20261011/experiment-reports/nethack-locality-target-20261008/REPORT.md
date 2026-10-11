# NetHack: locating and removing redundant floor-index rebuilds

The new retained candidate is a **one-line removal**: stop discarding the floor-object index at every input key. Actual object and level mutations still invalidate it. Relative to the previous glyph16 engine, CPU throughput improves **6.7%**, and the controlled full training pipeline improves **6.8%**. The live repository is unchanged.

## Where the time went

Paired native profiles replayed identical mature games in ordinary scheduling and in diagnostic 16-action bursts. Mean sampled CPU time per decision was 150.2 versus 79.4 microseconds. The burst is an offline locality intervention using known future actions, not an online collector that we can simply enable.

Floor lookup was the largest individual localized difference: approximately 23.6 versus 4.2 microseconds per decision, estimated from statistical profile shares. Disassembly locates **3,334 of its 3,868 samples (86.2%) in rebuilding the index**, particularly the dependent object-list walk. This explains why making the SIMD search wider did little: the expensive work was rebuilding its input.

The engine already tracked placement, removal, replacement, splitting, level reset and restore. Blanket invalidation in `nle_step` additionally threw away the same index when nothing changed. Removing that blanket invalidation retains the existing mutation generation and linked-list fallback semantics. The index remains per game, including when games move between worker threads.

Independent measured-phase counters, over 1,048,576 decisions:

| Work | Before | After |
|---|---:|---:|
| Input keys | 2,421,941 | 2,421,941 |
| Floor queries | 39,951,908 | 39,951,908 |
| Invalidations | 3,078,753 | 656,812 |
| Index rebuilds | 1,019,767 | 323,737 |
| Objects visited during rebuilds | 140,929,806 | 48,159,414 |

That is **68.3% fewer rebuilds and 65.8% fewer object visits**. There were no overflow or mid-query fallback calls in this sample. Counter runs overlapped with validation; their timings are excluded from performance claims.

## Performance

2,048 environments, identical mature trajectories, 24 shared-pool workers plus four submitters, same pinned CPUs. Baseline includes the previous smaller display buffer; this is an incremental comparison against our optimized engine, not stock NLE.

| Measurement | Before | After | Throughput gain |
|---|---:|---:|---:|
| CPU replay, mean of two runs | 183,882 SPS | 196,154 SPS | 6.7% |
| Full pipeline, paired run | 169,671 SPS | 181,175 SPS | 6.8% |

CPU repetitions: baseline 183,894 / 183,870; candidate 197,014 / 195,294. The second candidate timing includes native profiling, so it is not a pure repeat without instrumentation. Sampled step CPU time averages 152.4 → 143.0 microseconds. The candidate profile reduces floor lookup's self sample share from 15.7% to 6.3%.

Full pipeline: 5,097,608-parameter network, original four-buffer scheduling, horizon128, batch262144, minibatch4096. All inference and PPO/optimizer computation executes. A fixed random network supplies the compute workload; mature recorded actions drive the games and optimizer writes go to scratch. This is a throughput control, not a learning experiment. Both runs use 96 batches, with steady-state measurement over batches64–94. Rollout-tail wait falls from 0.747 to 0.644 seconds per batch. GPU allocation is 8301 MiB in both. This is one full-pipeline pair on this machine, not a universal speedup guarantee.

## Behavior and audit

- **16,777,216 decision hashes match exactly** for both the release and diagnostic builds: observations, rewards, terminals and masks.
- The diagnostic build additionally compared live floor pointers, ordering and coordinates against the cache on every indexed lookup; the complete replay passed (351.9 seconds).
- Both builds pass 34 goldens, 26 fuzz traces, status updates disabled, interleaved games and shuffled-thread replay.
- All **96 full-pipeline batch observation hashes match**, and frozen weight hashes match before/after and across variants.
- All eight protected live source hashes match the prior baseline.

Golden/fuzz actions use the prior experiment's unchanged-reference current-observation hashes. Original historical recordings were not altered. These are bounded behavior checks, not an exhaustive proof over all game states. `AUDIT.md` and `mutation-audit.txt` document mutation paths.

## What remains

This recovers one concrete piece of the larger locality gap. It does **not** recover the full nearly2× offline burst improvement. The remaining profile is dominated by monster movement and neighbouring-tile checks, with observation and inventory work also sensitive to keeping state hot. Moving whole structs and enabling huge pages previously gave little benefit. A larger remaining gain requires reducing those data accesses or keeping more of each game's active state local while preserving parallel utilization.

Hardware cache/TLB counters are unavailable. The causal evidence here is the removed work, unchanged queries/trajectories and measured throughput, not a claimed exact L1/L2/L3 miss-rate change.

## Artifacts

- `persistent-floor-index.patch`: this change only, on top of glyph16.
- `combined-locality.patch`: prior glyph16 plus this change, against opt61-final.
- `engines/persist/source` and `engines/persist/build/libnethack.so`: complete retained source and release library.
- `ARTIFACTS.json`: source/library hashes.
- `cpu_results.csv`, `CPU_SUMMARY.json`, `training_validation.json`: results.
- `profile_comparison.csv`, `fobj-disasm.txt`: localization evidence.
- `runs/*/command.json`: commands, settings and artifact hashes.
- `checks/`: strict replay results and every-decision hashes.
- `engines/diag_*` and `persist_verify`: diagnostic-only builds, not deployment artifacts.
