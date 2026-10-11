# Effect of a 5M-parameter model

Measured 2026-10-10T08:50:27.382618+00:00. **Reducing the model from 15.55M to 5.10M parameters improves mature full-pipeline throughput by only 2.90%, despite nearly halving GPU training time. CPU environment work remains the main constraint.**

## Controlled end-to-end comparison

Current retained engine/GPU optimizations, RTX 4090 / i9-14900K, 2048 environments, four buffers, horizon 128, batch 262,144, minibatch 4,096, 113 PPO updates, 32 CPU workers. Width changes from 1024 to 512; four recurrent layers and internal encoder dimensions remain unchanged. The existing sleeping main-thread wait is enabled in both arms, avoiding additional CPU spinning when GPU training finishes early. All other settings match.

ABBA run order: large, small, small, large. Each run executes 80 epochs, warms for 64, and measures epochs 64–78 without a profiler. Every one of the 80 observation hashes matches across sizes; each actor remains byte-identical before/after the run.

| Measurement | 15.55M | 5.10M |
|---|---:|---:|
|Full-pipeline steps/s|208,875|214,938|
|Two repeats|208,739–209,011|214,717–215,160|
|Billion steps/hour|0.752|0.774|
|PPO host phase, overlapping rollouts|1077.7 ms|552.2 ms|
|Remaining rollout wait after PPO|172.8 ms|662.9 ms|
|GPU training alone, 113 updates|971.0 ms|513.2 ms|
|Allocated GPU memory reported by benchmark|8290 MiB|7884 MiB|

GPU-only timings use five trials per size on corresponding saved mature batches. The large-model diagnostic comes from the immediately preceding attribution study with the same stack; the small-model batch/timing was collected here. These isolated numbers are not full training throughput. The GPU profile confirms that the small PPO graph itself spans about 550 ms while rollouts run.

## Contention and final wait

Two graph-level Nsight epochs at the same mature point: small-model inference takes 0.511 ms during PPO versus 0.261 ms outside it (1.96× latency). The preceding 15.55M trace measured 0.877 versus 0.370 ms (2.37×). Shrinking the model reduces both inference cost and observed interference, but does not remove it.

The small-model last collector finishes about 698 ms after the PPO GPU graph. Of that tail, 593 ms (85.0%) is inside environment/pool ranges and 77 ms (11.1%) is GPU/stream waiting. Pool waiting is nested inside the environment range; it must not be added again. These are last-collector tail fractions, not fractions of all training work.

The Nsight run’s launcher SPS includes profiler-stop overhead and is excluded. Its captured epoch durations are approximately 1.24–1.26 seconds; unprofiled ABBA runs provide the throughput result. No GPU clocks were locked. Coarse utilization samples support greater GPU slack with the smaller model, but are not a precise decomposition.

## Interpretation and limits

The smaller network finishes PPO roughly half a second earlier, then waits for largely the same environment workload. It creates useful GPU margin for future CPU improvements, but only reaches about 0.77B steps/hour here, below the 1B/hour target.

All games are driven by the same mature 4B score-policy recording (512 unique streams repeated four times). Full inference, forward/backward, loss and optimizer compute execute; optimizer writes go to scratch weights. The 5.10M network uses frozen random parameters, while the large network uses the trained score checkpoint. Recorded actions replace those executed by the engine. This isolates compute cost; it does not establish small-model learning quality or valid on-policy training. Internal modality encoders are not uniformly shrunk.

No new optimization was promoted, no production source was edited, and no training was launched. All 16 protected production/historical file hashes remain unchanged. The experimental source remains at its pre-existing v36 state; both sizes use the same immutable attribution_v37 binary with bypass flags disabled.

## Reproduce

- `../MODEL5M.json`: four full comparison runs; `../MODEL5M_DETAIL.json`: capture, isolated GPU timing and profile.
- `../run_model.py`, `../campaign_model.py`: isolated harness extension; `runner.patch` records its difference from the original runner.
- `../runs/model5m_*/command.json`: exact commands, environment overrides and binary/engine hashes. Small-model checkpoint source is explicitly null/random.
- `TIMINGS.csv`, `SUMMARY.json`, `DETAIL_SUMMARY.json`, `TRACE.json`, `INTEGRITY.json`: raw summaries and checks.
- `mature_small.bin`: captured 5.10M batch; `../runs/model5m_small_graph/timeline.nsys-rep` and SQLite: trace. Labels/files must be made unique before rerunning; the harness refuses overwrite.
