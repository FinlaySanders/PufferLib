# Grouped NetHack rollout collection

2,048 resident games; horizon 128; batch 262,144; minibatch 4,096; 24 shared CPU workers. A logical buffer owns its game IDs, action RNG, recurrent state and stream. Cohort gating changes only when that buffer advances: no future teacher actions are executed without inference. Actor weights remain the original per-rollout snapshot; PPO still uses full batches.

Compare four buffers of 512, sixteen buffers of 128 without gating, then four active buffers (512 games) at a time with chunk lengths 16/64/128. Warm each game 8,192 decisions before measurement. First use recorded mature trajectories to control game complexity, then validate live sampling and real optimizer updates with identical buffer counts. Different buffer counts can change GPU numerical reductions; same-buffer scheduling must be bitwise exact.

The experimental source is isolated here. Live repositories and libraries are untouched. The recovered opt61 final engine includes the prior correctness fixes. Existing benchmark instrumentation had a four-entry completion array: it is now sized to the buffer count. Teacher replay maps by global game ID rather than logical buffer index. Full rollout hashes and learner-state snapshots are enabled only for correctness runs.
