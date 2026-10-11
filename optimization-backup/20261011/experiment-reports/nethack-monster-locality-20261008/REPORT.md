# Monster-state locality — 8 October 2026

**No candidate is promoted.** Per-game monster pooling gives a small repeatable CPU gain (**1.63%**), but the controlled full pipeline improves only **0.57%** in one pair. Guard-test ordering, merging key searches and compact monster occupancy are flat in their first screens. The previous persistent-floor-index engine remains the retained baseline. The live repositories and training defaults are unchanged.

## What was tried

1. **Guard test order:** movemon samples concentrate near the isgd flag at offset 65. Check mx before isgd so ordinary monsters skip that second-line flag read. Disassembly confirms the intended order; performance does not improve.
2. **Per-game monster pool:** allocate unchanged 144-byte monster records in reusable blocks of 64 belonging to each nh_ctx. Addresses remain stable, dead slots are reused, and blocks are freed at episode teardown. This avoids interleaving individual monster allocations with other games' allocations and unrelated objects. No monster/save format changes.
3. **Single-pass key search:** monhaskey formerly walked a monster's inventory up to three times for a credit card, skeleton key and lock pick. A single pass returns the same boolean, including the restriction on credit cards. It reduces scans but gives no useful gain in this screen.
4. **Compact occupancy:** answer MON_AT from a 1,680-byte occupancy plane rather than a 13,440-byte pointer grid. Real pointer lookup remains direct. Placement, removal, worm segments, generation, save/free, restore and teardown update both. The extra plane gives no useful speedup.

These are independent candidates on top of the same baseline; they are not cumulatively combined.

## CPU results

Identical mature action streams, 2,048 environments, 24 shared-pool workers plus four submitters, fixed CPU affinity. Warm 8,192 decisions per game, then measure 2,048. No build, other benchmark or profiler runs concurrently. Baseline includes all previous retained engine changes, glyph16 and persistent floor indexing; **it is not upstream or stock NLE**.

| Variant | Repetitions | Steps/s | Relative to baseline mean | Sampled CPU µs/decision |
|---|---:|---:|---:|---:|
| Baseline | 2 | 198,194 | +0.00% | 141.33 |
| Guard test order | 1 | 197,287 | -0.46% | 141.85 |
| Monster pool | 2 | 201,433 | +1.63% | 139.06 |
| Single-pass keys | 1 | 199,112 | +0.46% | 140.67 |
| Compact occupancy | 1 | 197,634 | -0.28% | 141.76 |

Baseline repetitions: 199,158 and 197,231 SPS. Pool: 201,432 and 201,434 SPS. Differences below about 1% are inconclusive in this screen, rather than evidence of an improvement. Mean pool peak RSS is about 9 MiB higher across the 2,048 games. Its sampled step CPU time falls from 141.33 to 139.06 microseconds.

Every timing reproduces observation hash b97835c62aaf388f, identical duplicate streams, and 28,920,368 world-turn advances. Raw timings and commands are in runs/, cpu_results.csv and CPU_SUMMARY.json.

## Full-pipeline check

| Latest retained engine | Monster pool | Difference |
|---:|---:|---:|
| 181,948 SPS | 182,987 SPS | +0.57% |

Mean rollout-tail wait is 0.6388 → 0.6299 seconds per batch. GPU allocation is 8301.1 MiB in both.

This uses the unchanged benchmark binary and original four-buffer scheduling: 5,097,608-parameter network, 2,048 games, horizon128, batch262144 and minibatch4096. It executes inference and PPO forward/backward/optimizer computation, with optimizer writes directed to scratch. A fixed random network provides the compute workload and recorded mature actions drive the games. It is a controlled throughput test, not a learned small-policy or learning-quality comparison. There are 96 batches, with timing over batches64–94. All 96 batch proofs and initial/final frozen parameter hashes match across variants.

This is one full-pipeline pair. A 0.57% difference does not establish a useful training speedup. Given the allocator/lifecycle complexity, leave the pool experimental.

## Correctness and scope

- All four candidates pass 34 golden trajectories, 26 fuzz traces, status-updates-disabled replay, interleaved games and shuffled worker-thread replay.
- Historical action traces use the already-pinned, unchanged modern-baseline observation hashes. No references were repinned to a candidate.
- All CPU outcomes match and both full-pipeline runs match in all 96 batch proofs.
- The real pool allocator passes an isolated 80-context lifecycle test, including block growth, slot reuse with live neighbours and game isolation. Valgrind reports zero errors and zero definitely/indirectly/possibly lost bytes. Remaining reachable allocations are loader/libstdc++ bookkeeping.
- All eight protected live file hashes are unchanged (live_integrity.json).
- Because none is promoted, the separate complete 16,777,216-decision hash gate was **not run for these candidates**. The optional occupancy-versus-pointer diagnostic is implemented but was not built/run. These are bounded behavior checks, not proof over all possible game states.

## What this says about the larger locality gap

This particular monster-record placement change recovers only a small part of the earlier near-2× offline burst headroom. A function called monster movement also spends substantial time on floor objects, inventory chains, terrain and other map grids; its profile share is not all accesses to struct monst. Instruction sampling found these additional pointer walks directly. Keeping a whole game hot benefits all those structures, while this pool changes only monster allocation/storage. Hardware cache/TLB counters remain unavailable, so neither the exact cache level nor its miss-rate reduction is claimed.

This does not prove that all monster-state layouts are exhausted. It does rule out a large gain from the tested simple pooling, guard reordering and byte occupancy changes on this workload. Keep the earlier validated floor-index win; don't add these changes to the default engine based on the present results.

## Artifacts

- Retained engine: /puffertank/experiments/nethack-locality-target-20261008/engines/persist/build/libnethack.so
- Experimental sources and libraries: engines/{guard_first,monster_pool,onepass_keys,monster_grid}/
- Reviewable patches: guard_first.patch, monster_pool.patch, onepass_keys.patch, monster_grid.patch
- AUDIT.md: ownership, deallocation and occupancy mutation paths
- ARTIFACTS.json: changed files and library hashes
- checks/: exact quick-gate results and pool lifecycle memory check
- training_validation.json: full-pipeline comparison/proofs
- m_move.disasm, movemon.disasm, mfndpos.disasm: original retained-engine profile localization
