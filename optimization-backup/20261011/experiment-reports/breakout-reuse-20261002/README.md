# Breakout reuse pilot — 2 October 2026

Question: why does more reuse of a rollout batch hurt learning? This is a small first stage of `reuse_experiment.md`, running alongside the frozen NetHack mask campaign.

## Setup

- Isolated detached checkout at `source/`, based on PufferLib `3719caaa`.
- CPU Breakout environment, GPU policy/trainer. Tuned `config/breakout.ini`: 4096 agents, 32-step horizon, 65536-sample minibatches, 8 CPU workers, 4 layers of width 32 (16,164 parameters).
- Two seeds (73, 74), fresh initialization. Same 55M requested environment steps per run (54,919,168 actual), same tuned rewards/optimizer/LR schedule.
- Requested reuse: 1.88528275, 7.541131, 16. Integer minibatch rounding gives **1.5, 7.5, 16 effective passes** respectively, since the rollout contains only two minibatches. The nominal fourfold setting is therefore fivefold in actual updates relative to the tuned setting. Both quantities must be reported.
- Original asynchronous actor/learner path and CUDA graphs remain enabled.
- Six diagnostic training runs, interleaved by seed. Two additional matched diagnostics-off runs measure overhead and check full-run checkpoint identity.
- Each final policy gets the same builtin 10,000-episode evaluation. This creates fresh evaluation environments, as in the original trainer. Training scores and final evaluation scores must not be conflated.
- One Breakout job at a time, CPU nice 15; both experiments share the 4090. Nice does not reserve GPU capacity. Concurrent timing is not an uncontended throughput benchmark.

## What is measured

Read-only side kernels record per-pass PPO losses, approximate KL, mean ratio, clip fraction, the fraction with PPO-clipped policy gradients, a 66-bin log-ratio histogram, total preclip gradient norm, and gradient clipping frequency. Advantages and returns computed once from rollout-time values are frozen for comparison; training continues to recompute live targets. We log advantage magnitude, mean, standard deviation, cosine similarity/RMSE against frozen advantages, and value MSE against frozen returns.

The last time position is a GAE bootstrap position with forced-zero advantage. Advantage statistics exclude it; PPO/ratio/histogram statistics include it to match the actual loss kernel. `pass=-1` separately tracks the first minibatch of each batch; it duplicates those samples and must not be pooled with pass 0–15.

Frozen values come from the actor. In async training, differences at the first minibatch include actor/learner lag. Even synchronous bf16 inference and training have slightly different batching/rounding: initial advantage RMSE was 0.00124, ratio 1.00046, KL 1.53e-6. We do not demand impossible bit equality of those two forward paths.

All statistics accumulate on device and are read/reset only at normal logging intervals. Whole epochs are captured, with distinct graph nodes for each minibatch; bucket pointers are fixed for those nodes and do not rely on changing a captured host scalar. Off launches no diagnostic kernels. The PPO, GAE and optimizer kernels are unchanged; all extra kernels live in `src/reuse_diag.cuh`.

Histogram quantiles are approximate; ±infinity denotes a censored tail outside [-1,1]. The exact outside-clip fraction comes from PPO's existing clip statistic, not a histogram boundary estimate. Gradient norm includes policy, critic and entropy gradients: it does not identify Muon as a causal explanation on its own.

## Deliberately deferred

No holdout (the proposed minimum-16-slice rule disables it for tuned Breakout), control variate, target-KL early stopping, or algorithm changes in this pilot. Use the results to choose a follow-up. A holdout experiment needs an explicit alternative batching design.

## Validation and outputs

`validation/report.json`: all 20 checkpoints match byte-for-byte across the pristine build, new build with diagnostics off, and diagnostics on, independently for synchronous and asynchronous modes. Histogram totals and minibatch/valid-advantage sample counts are checked automatically. `pilot.py` also requires the full 55M-step on/off checkpoints to match per seed.

- `pilot.log`, `active.json`: live progress.
- `results.jsonl`, `runs/*/result.json`: completion records and provenance.
- `runs/*/stdout.log`: unmodified trainer output.
- `logs/*.reuse.csv`: raw pass statistics and all histogram bins at normal log intervals.
- `logs/breakout/*.ini`: configs and original training/evaluation summaries.
- `checkpoints/breakout/*/*.bin`: final policies.
- tmux session: `breakout-reuse`.

The main trainer source and all running NetHack code/binaries/configs are untouched. `NETHACK_ABLATIONS.md` records the queue failure/replacement. Nothing is committed or pushed.

## Completion and interruptions

All six pilot policies completed. One seed-74 / 16-pass attempt aborted on a CUDA rollout graph-launch assertion early in training; its logs are retained in `failure-debug/attempt1*`. An identical retry completed, and its full 55M-step checkpoint exactly matches a fresh run of the pristine trainer at the same seed/reuse. The original assertion's cause has not been established; it must not be called a confirmed numerical failure or attributed to GPU contention without evidence.

NetHack seed 2901 also exited with SIGSEGV at 11:09:35 UTC (last logged 295.7M steps). Its existing queue automatically started seed 2902 and scheduled replacement seed 10135. No NetHack artifacts/settings were modified. No core dump was available. The two failures have different observed symptoms; whether there is any connection is unknown.

Read `RESULTS.md` for the completed score comparison. The two seeds favor 7.5 actual passes over the tuned 1.5; 16 passes is mixed. These results do not establish a universal reuse failure or identify its cause. Diagnostic-only overhead measured +3.43% and -1.75% across the two concurrent timing pairs; a precise <3% guarantee needs a controlled timing test.

A 20-epoch, 16-pass Compute Sanitizer memcheck restricted to the new diagnostic kernels completed with **0 errors**, saved in `failure-debug/sanitize16_s74.log`. This does not establish the cause of the earlier graph-launch failure.
