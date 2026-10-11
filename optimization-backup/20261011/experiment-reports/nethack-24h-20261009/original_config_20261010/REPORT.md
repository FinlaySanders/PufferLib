# Original NetHack configuration restored as primary target

Measured 2026-10-10T09:02:57.446752+00:00. The user clarified that **512 environments is the primary optimization target**; 2048 was a scaling experiment. The prior 2048-environment CPU-bottleneck conclusion does not transfer to the original configuration.

## Configuration and result

Original rollout layout: **512 environments, horizon 512, four buffers, batch 262,144, minibatch 4,096**, replay ratio1.78021395 (113 PPO updates). Retain32 shared CPUworkers and current engine/GPU optimizations. Main architecture15.55M; 5.10M (width512 instead of1024, four layers unchanged) is a separate configuration check. Production config already has this original rollout layout and was not edited.

ABBA large/small/small/large,64epochs each,24warmup,39timed epochs24–62. No profiler in headline runs. Frozen actor, full GPU training compute with optimizer writes to scratch, same recorded mature-game actions for both sizes.

|Measurement|15.55M, primary|5.10M, secondary|
|---|---:|---:|
|Full-pipeline SPS|221,431|282,968|
|Repeat range|221,178–221,684|282,690–283,246|
|Billion steps/hour|0.797|1.019|
|PPO host phase during overlap|1181.0 ms|640.9 ms|
|Rollout wait after PPO|0.0 ms|282.0 ms|
|PPO remaining after rollouts|182.2 ms|0.0 ms|

The smaller model improves throughput by 27.8% in this configuration and reaches about1.02Bsteps/hour in the fixed-trajectory compute benchmark. This does not establish its learned playing strength. The 15.55M primary target remains about0.80Bsteps/hour.

## Which side sets the pace?

With the15.55M model, PPO finishes after rollouts in every timed epoch. Thus the main optimization target here is GPU training and its interference with inference. With5.10M, PPO finishes first and rollouts set the pace; that tail includes CPU, inference, transfers and scheduling.

Two separate graph-level epochs per size confirm the ordering: large PPO graph 1184.8ms, with 95.6ms left after the last collector; small PPO graph 635.6ms, with 379.8ms of collection left after it. Profile timing is diagnostic, not headline SPS. The launcher’s profiled SPS includes stop overhead and is excluded.

Five isolated15.55M trials on a newly captured primary-sized mature batch average 1031.99ms for all113PPOupdates. This is equivalent to 254,019SPS if collection/inference were free; it is not actual training throughput. The saved batch now supports fast GPU screens on the original configuration.

## Benchmark priority and caveats

- Primary:512environments/H512,32workers,15.55Mmodel. Use this to screen and confirm implementation wins.
- Secondary:2048environments/H128 scalability. Keep it fast, but do not use it to select the main bottleneck or mix its SPS into primary results.
- Secondary:5.10M model-size scaling. Report separately from implementation speedups.
- The restored original window measures12288–32768decisions per game, while the preceding2048 test measured a different game-age window. Do not attribute their absolute SPS difference solely to environment count.
- Original workload has512unique recorded streams, without the fourfold replication used at2048.
- All64observation hashes in allfour fullruns match each other and the archived512/H512 reference (`nethack-comprehensive-20261008/runs/replay_score_all_2`). Frozen model hashes are unchanged. Profiles and batchcapture pass corresponding prefix checks.
- The small network uses frozen random weights; the large network uses4B s705. Environment actions come from the same recording. Learning quality is untested.
- Existing sleeping main wait is enabled in both arms; exploration is fixed atzero as in the established replay benchmark. No production defaults were changed.
- All16protectedproduction/historicalfiles remain unchanged. No new optimization was promoted.

## Artifacts and next use

- `../PRIMARY_BENCHMARK.json`: canonical target settings.
- `../run_primary.py` / `../campaign_primary.py`: primary harness; default64epochs/start24. The old `run.py` and `run_model.py` remain preserved scaling harnesses, not primary defaults.
- `../ORIGINAL512.json`: unprofiled ABBA comparison; `../ORIGINAL512_TRACE.json`: two profiles and mature-batch capture/GPU timing. Rename labels before rerunning.
- `mature_1024.bin`: canonical GPU microbenchmark batch, original512/H512 shape.
- `SUMMARY.json`, `TIMINGS.csv`, `PROFILE_SUMMARY.json`, `TRACE_large.json`, `TRACE_small.json`, `INTEGRITY.json`: timing and checks.
- `../runs/original512_*/command.json`, `run.log`, `result.json`: exact commands and binary/engine hashes. Nsight reports/SQLite alongside the profile runs.
