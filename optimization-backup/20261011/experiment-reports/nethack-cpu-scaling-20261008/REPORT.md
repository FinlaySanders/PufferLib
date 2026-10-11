# NetHack CPU scaling and recovered engine optimizations — 8 October 2026

The recovered engine changes improve mature CPU-only rollouts by **11.1%** and the full 5.10M-model pipeline by **8.9%** at 512 environments. Increasing the number of environments or doubling the training batch does not increase throughput on this machine. These gains are incremental to the previously validated engine14, shared worker pool, cuBLAS workspace fix and retained GPU optimizations; they are not another comparison against upstream.

The changes and builds are isolated in this experiment. Production source, configurations and binaries remain unchanged. **Final validation passed**, with the detailed checks in `VALIDATION.json`.

## Full-pipeline results

| Configuration | Reference SPS | Optimized SPS | Change |
| --- | ---: | ---: | ---: |
| 5.10M, 512 envs, 262,144 batch | 206,121 | 224,393 | +8.9% |
| 5.10M, 1,024 envs, 262,144 batch | 169,084 | 176,329 | +4.3% |
| 5.10M, 2,048 envs, 262,144 batch | 157,643 | 165,732 | +5.1% |
| 5.10M, 1,024 envs, 524,288 batch | 168,567 | 177,124 | +5.1% |
| 15.55M score checkpoint, own actions | 177,131 | 180,375 | +1.8% |
| 4.31M depth checkpoint, own actions | 342,789 | 343,042 | +0.1% |

The first row averages two runs per build in counterbalanced order. Reference range: 204,222–208,020; optimized range: 224,172–224,615. Other rows are single comparisons, so small differences should not be overinterpreted. Raw values and run labels are in `performance.csv` and each `runs/*/result.json`.

All GPU comparisons use the same trainer executable. The CPU-heavy 5.10M workload improves most; the larger score network already hides much of CPU execution, and the depth workload has effectively no exposed engine wait. This is consistent with, but does not alone prove, the earlier CPU/GPU timeline measurements.

At 1,024 environments, doubling the batch changes optimized throughput only from 176k to 177k, while GPU memory rises from 8,205 to 15,061 MiB and batch latency roughly doubles. Increasing the rollout batch alone is not a useful throughput lever in this fixed-4,096-minibatch screen. This does not test whether larger rollout batches learn better, or whether larger PPO minibatches improve GPU efficiency.

## Workload and controls

- Machine: i9-14900K, 24 physical/32 logical CPUs; RTX 4090 24 GiB. One timing job at a time, without concurrent builds or profiling.
- Four rollout buffers, 24 shared-pool workers. The four submitter threads are additional threads, not additional dedicated CPU cores.
- Small-network comparisons replay actions recorded from the mature 4B score checkpoint. Inference, forward/backward PPO and optimizer computation execute, while writes to actor weights are diverted to scratch. The 5.10M actor itself is random and frozen; replay controls the environment workload. This measures throughput, not learning quality or a valid on-policy update.
- The 512 teacher streams are duplicated for 1,024/2,048 environments. Every duplicate must reproduce its source. This controls difficulty but is not a test of a larger population of independently sampled games.
- Warm-up is 8,192 decisions per environment, followed by approximately 4,096 measured decisions. The final batch without an outstanding prefetch is excluded, so measured windows differ slightly with horizon. Horizons are 512/256/128 at fixed 262,144 batch. The separate 1,024-env/512-horizon case tests a larger batch.
- SPS counts policy decisions, not individual NetHack keystrokes. Action macros may advance multiple game turns. The CPU screen reaches a mean game age of about 29,339 turns.
- Own-action score/depth checks use frozen trained policies, with all training computation executed. Separate checks apply real optimizer updates and compare their exact results.
- Reference and optimized libraries are rebuilt with identical Release, LTO and `-fno-semantic-interposition` settings. **No PGO** is used in the new engine comparison, despite historical source-directory names containing `pgo`.

## What was recovered

The patch in `recovered-engine.patch` restores five saved improvements on top of engine14:

1. Keep the floor-object cache across monster-movement passes, invalidating it when the object list actually changes.
2. Reuse the remaining SIMD matches while traversing floor objects instead of repeating their filtering.
3. Avoid irrelevant distant `onscary` work, retaining shopkeeper/priest special cases.
4. Use a small nearby-track occupancy cache to reject impossible player-track lookups.
5. Cache the absence of gold in the player's inventory, with invalidation at inventory mutations.

These are recovered optimizations, not five newly discovered wins. This study resolves the correctness discrepancy that had kept them out of the previously validated package.

## Correctness discrepancy and common fixes

An every-action comparison localized the original engine14-versus-later-engine mismatch to one transient message in 6,291,456 decisions: environment 11, decision 9,017. A teleporting thief's name buffer was initialized only when the victim was visible, then could be used when the attacker was visible independently. Different builds therefore emitted different undefined text. Non-message observation fields, rewards, terminal flags and action masks matched at that point under the recorded actions.

`message-fix.patch` captures the visible attacker's name before relocation in both relevant message paths. It is applied to **both** reference and candidate. This is an intentional correction to exported text and can change a policy's choices; it is not described as preserving the original undefined observation. After the common fix, engine14 and the recovered engine match all 16,777,216 decisions in the full recorded corpus.

The saved sources also predate the October fire-trap fix. `fire-trap-hpmax.patch` is carried forward into **both final builds**. It preserves the random draw and prevents a life-saved monster's maximum HP falling below its current HP. The performance patch remains separate from these correctness fixes.

A fresh timing after carrying forward the fire-trap fix measures 204,030 versus 223,170 SPS (+9.4%). The fire-trap patch changes none of the 16,777,216 recorded decision hashes on this corpus in either build; it remains a deliberate correctness fix for other states.

Final production-observation builds are `engines/base14-final/build/libnethack.so` and `engines/opt61-final/build/libnethack.so`. Their complete source snapshots are adjacent under `source/`. The final hash check, post-fix timing and optimizer-state comparison are recorded in `FINAL_ENGINE_HASHES.json` and `VALIDATION.json`.

Historical stock goldens use an older observation projection. The `*-historical` builds replace only that projection using the previously documented adapter, and are **diagnostic builds, not deployment artifacts**. Their gates cover 34 goldens, 26 fuzz traces, status updates disabled, and interleaved/shuffled multi-game replay. The current observation layout is checked separately by hashing every recorded decision. Passing these bounded checks is not a proof for all seeds or game states.

Completed checks:

- Final reference and optimized builds match at every one of 16,777,216 replayed decisions, hashing observations, rewards, terminal flags and action masks.
- Own-action score and depth policy runs match all 64 and 24 checked batch boundaries respectively.
- After 1,808 real optimizer minibatches, final weights, master parameters, momentum, update buffers and checked rollout observations match exactly. This passes again with both common fixes included.
- Both historical-view builds pass all 34 goldens, all 26 fuzz traces, the status-disabled variant and interleaved/shuffled multi-environment modes.
- Every frozen-policy run retains its initial weights. All eight protected live-source/config hashes match the pre-study snapshot.

## CPU scaling and profile

Repeated CPU-only mature replay at 512 environments rises from **240,235 to 266,888 decisions/s (+11.1%)**. Both builds advance the same number of turns and match observations. Reference repeat range is 236,706–243,765; optimized range is 265,240–268,537.

The initial worker screen on engine14 showed:

| Environments | 8 workers | 16 workers | 24 workers | 28 workers |
| --- | ---: | ---: | ---: | ---: |
| 512 | 134k | 194k | 234k | 240k |
| 2,048 | 108k | 148k | 166k | 174k |

Only the 512/24 control was repeated in that screen; its table value is their average. Using 28 workers may offer a small gain, but it has not been established by repeated full-pipeline comparisons. The retained full-pipeline configuration uses 24 workers. Reducing workers clearly loses throughput. The decline with more environments also occurs without any GPU, so the full-pipeline decline cannot be attributed solely to GPU batch shape. Increased memory working set/locality pressure is plausible, not established by hardware-counter evidence.

Callgrind samples of three mature games put monster movement (`m_move`/`mfndpos`), observation packing, scary-square checks and floor-object traversal near the top. Examples of self instruction shares: `m_move` 8–13%, `mfndpos` 9–13%, observation packing 9–14%, `onscary` 5–7%; floor-object traversal varies substantially by game. These are sampled **instruction counts**, not CPU wall-time fractions or hardware bandwidth measurements. Hardware performance counters were unavailable.

The next CPU targets are the remaining monster-neighbour candidate scan and observation packing, followed by a direct locality/working-set study at 1,024+ games. Increasing environments currently reduces throughput, but its learning benefit remains unmeasured. The user's target is to remove that scaling penalty so that a sweep can explore thousands of environments and larger batches without an implementation-induced disadvantage.

### Follow-up: cost inside game steps at larger populations

An isolated follow-up at `/puffertank/experiments/nethack-population-scaling-20261008` samples wall time and thread CPU time inside `puf_step` every 64 decisions. It uses the final optimized engine, 24 pool workers, four submitting threads, 8,192 warm-up decisions and 2,048 measured decisions per environment. Order: 512, 2,048, 512. The same teacher games are duplicated, with matching final observation hashes and proportional world-turn advances.

| Metric | 512 environments (two controls) | 2,048 environments |
| --- | ---: | ---: |
| CPU-only SPS | 269,347 | 175,618 |
| Mean sampled thread CPU time per game step | 99.3 us | 154.0 us |
| Process CPU seconds per wall second | 27.2–27.5 | 27.5 |
| Major page faults in measured window | 0 | 0 |

Sampled in-step CPU cost increases **55%**, and the average increases for all 512 underlying teacher streams. This points to a substantial loss inside game stepping, not merely extra pool waiting. Thread CPU time excludes descheduled time but includes memory stalls and execution on different CPU core types. Cache/TLB locality, allocation costs, core placement and clock-frequency effects remain to be separated; the measurement does not prove any one of them. Instrumented SPS is a diagnostic comparison, separate from the earlier uninstrumented headline timing.

The next scaling gate should target approximately flat aggregate throughput from 512 to 2,048/4,096 environments, then vary PPO minibatch and rollout batch independently. A large environment population need not force one equally large inference dispatch; the current four-buffer configuration couples those sizes. Smaller dispatches and stable worker ownership are candidates to test, with the usual trajectory checks, rather than established fixes.

## Rejected change and artifacts

Compiling the trainer's host code at `-O3` instead of `-O2` gave no reliable benefit: 221k versus 224k in the repeated optimized-engine comparison. CPU-only `-O3` was essentially tied. It is excluded from the final comparison and package. GPU math, the workspace fix and optimizer algorithms were not changed.

`METHOD.md`, `cpu_scaling.csv`, `performance.csv`, `VALIDATION.json`, `FINALIZATION_STEPS.json`, build logs, source snapshots and per-run command manifests preserve the experiment. The generic result field `engine: engine14` is inherited from the runner; the actual library is unambiguously identified by `command.json`'s `LD_LIBRARY_PATH` and engine SHA. The 1,024-env host-`O3` diagnostic is excluded in favour of the `_all` run using the unchanged trainer.
