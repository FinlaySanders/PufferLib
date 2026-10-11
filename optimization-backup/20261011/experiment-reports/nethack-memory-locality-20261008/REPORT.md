# NetHack memory-locality investigation — 8 October 2026

The useful new change is small: reduce the internal display-buffer entry from 8 to 4 bytes by storing its glyph as a signed short. The glyph range is checked at compile time. It improves mature CPU replay by about **3%** and the controlled full training pipeline from **165,639 to 170,652 steps/sec (+3.0%)** at 2,048 environments. The live repository is unchanged; the isolated patch is `glyph16.patch`.

The broader tests do **not** support a large speedup from simply rearranging fields or adding huge pages. Locality still matters, but retaining parallel efficiency and reducing actual work/data traffic matter more than blanket packing.

## CPU screen

Same mature trajectories, 2,048 games, 24 pool workers plus four submitters, fixed CPU affinity. The existing opt61-final engine is the baseline, not stock NLE or upstream Puffer. CPU timings exclude inference and training.

| Change | Environment steps/sec | vs baseline mean |
|---|---:|---:|
| Baseline (3 runs) | 179.9k | +0.0% |
| Pack main game-state fields | 180.2k | +0.2% |
| Pack window-port fields | 180.4k | +0.3% |
| Smaller display entries (2 runs) | 185.7k | +3.3% |
| 2 MiB pages for main game state | 182.3k | +1.3% |
| Byte-packed floor-item index | 180.9k | +0.6% |
| Both compact formats (2 runs) | 184.6k | +2.6% |
| 24 workers, no submitter help | 163.3k | -9.2% |
| Fixed weighted worker ownership | 105.5k | -41.3% |

Baseline runs were 180.40k, 180.45k and 178.73k. The glyph candidate repeated at 185.69k and 185.73k. Differences below roughly 1% should be treated as inconclusive in this screen. Most other variants have one timing; the combined compact formats have two. Profiling and smoke tests are excluded.

The smaller display buffer saves 6,720 bytes per game (13.1 MiB across 2,048 games), and the observation copy reads a smaller source array. Compiler-generated copy code may change too: this is evidence for less data movement/cheaper processing, not a measured hardware cache-miss reduction.

The huge-page experiment really used huge pages: smaps reported 4 GiB of AnonHugePages, compared with zero in the baseline. Peak RSS rose from about 1.4 GiB to 5.2 GiB; warmup slowed as well. Its small measured-phase gain does not justify the memory/reset cost. This tests the main game context only, not huge pages for every heap allocation.

Fixed ownership reduces sampled step CPU time from 148.2 to 129.9 microseconds relative to the matching 24-worker/no-submitter control, but throughput falls from 163.3k to 105.5k. It changes P/E work distribution and utilization too, so the latency reduction is not pure evidence of cache improvement. Losing dynamic load balancing is expensive; do not adopt this scheduler.

The byte-packed floor-item index also doubles the SIMD scan width, but did not give a useful gain. The combined version is slightly slower than the simple display change. It is not retained.

## Full pipeline

| Original four-buffer collection | Steps/sec |
|---|---:|
| Existing optimized engine | 165,639 |
| Smaller display entries | 170,652 |

This is one paired full-pipeline run, consistent with the repeated CPU result; it is not a cross-machine or multi-model performance guarantee. The benchmark uses 2,048 environments, a 5.10M-parameter network, horizon 128, rollout batch 262,144 and PPO minibatches of 4,096. It executes inference, simulation, forward/backward and optimizer computation. Weights are frozen via scratch optimizer writes, while recorded actions drive identical mature games. The small network is a fixed random network used for compute measurement, not a trained 5M policy. This is not a learning-curve experiment.

Original inference partitioning and collection scheduling are unchanged. GPU allocation remains 8,301 MiB in both. Mean rollout-tail wait fell from 0.786s to 0.736s per batch. The checked batch observations and frozen weight hashes match in all 96 batches.

## Behavior checks

- 16,777,216 recorded decisions, 512 streams: **zero differences** in hashes covering observations, rewards, terminals and action masks.
- 34 golden trajectories and 26 fuzz traces pass.
- Status updates disabled, interleaved games and shuffled worker threads pass.
- Every CPU screen reproduced the expected final observation hash and identical world-turn advance totals; all duplicate streams also agreed.
- Protected live Puffer/NetHack/drone files retain their original hashes.

The historical goldens use an older observation projection. For this investigation their actions were copied here and rehashed against the **unchanged baseline's current observation interface**. Candidate comparisons were then strict. Original historical files and observation code were not modified. This checks equivalence to the current baseline, not a new assertion that its observations equal stock. These are substantial bounded checks, not an exhaustive proof for every possible game.

## What this says about the larger slowdown

The earlier active-working-set and grouped-collection results remain the stronger evidence for locality effects. This screen narrows the implementation choices: whole-struct repacking and main-context huge pages did not recover the scaling loss. Pinning games permanently to workers was a net loss. A targeted reduction in frequently scanned data gave a modest, real end-to-end benefit.

Hardware cache/TLB counters are unavailable on this host. We cannot assign the original 512-to-2,048 slowdown to a particular cache level or quantify its miss rate. The current statistical CPU profile puts most sampled work in monster movement and floor-object searching; observation filling accounts for around 4–5%. Any substantially larger engine gain probably needs to reduce those searches/data accesses or keep smaller active working sets while preserving overlap and load balance. It is not established by these tests that memory-layout tuning can yield a multiple-fold gain.

## Files

- `METHOD.md`: protocol and caveats.
- `cpu_results.csv`, `SUMMARY.json`: numerical results.
- `runs/*/command.json`: exact commands, binary/engine hashes and environment flags.
- `runs/profile2048/profile.txt`: mature statistical profile.
- `checks/results.json`, `checks/glyph16.json`: behavior gates.
- `training_validation.json`, `LIVE_UNCHANGED.json`: pipeline and live-tree checks.
- `glyph16.patch`: the small candidate retained for review; not applied to the live tree.
- `engines/*/changes.patch`: the other isolated experiments, retained as negative results.
