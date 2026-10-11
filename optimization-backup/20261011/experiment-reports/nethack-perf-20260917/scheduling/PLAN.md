# Scheduling experiments

Recovered original patches are hashed under parked-scheduling/. No production trainer source is modified.

First: work stealing only. Both policy source trees have independent src copies. Only the per-buffer environment-step scheduler changes; reset and all PPO/action/log-prob logic remain untouched. The old profiling blocks are omitted. Each worker claims from its contiguous home block then others via padded atomic counters.

run_workstealing.py waits for all earlier timings/integration to terminate, builds static and WS native/replay binaries, compares raw8env inference traces with the frozen reference, verifies full32 selected streams, then runs three ABA repeats at512env with8Pcores and32logicalCPUs. Same candidate03 engine for both arms isolates scheduling. Replay startup/warmup excluded. Three repeated real1M-step depth training ABA tests follow; compare actual wall time, not panel SPS. Training measurements include startup/final8episodeeval and must be labelled accordingly.

Next: shared pool is not yet applied. Code inspection found issues to resolve before porting: shared lazy spin_max initialisation; no visible worker shutdown/join in recovered patch; and a potential buffer-reuse race where a worker that saw active can still access claim counters while the submitter clears/reinitialises them for the next region. Historical successful trajectories are not proof these races are impossible. Need explicit region quiescence/lifetime handling and concurrency checks. Do not silently present a repaired pool as the exact historical patch.
