# Patched NetHack trainer: fresh profile

RTX 4090, loaded fixed 4B s705 policy, 512 agents, 4 buffers, 32 environment workers, hidden size 1024, 4 recurrent layers. Retained workspace + strict-reduction patch, existing engine/work-stealing/head-sampler optimisations. Production files unchanged. Loaded weights verified by SHA256. Training completed 16,777,216 steps and final evaluation. Nsight Systems captured 20 seconds after 60 seconds warm-up; game ages around 22,500 turns.

- Complete PPO graphs: 10; mean 1.5406 seconds (previous patched profile 1.548 s, pre-fix profile 2.398 s).
- Mean inter-PPO gap: 283.9 ms; range 251.5–342.5 ms.
- GPU kernel activity: 16.530/20 seconds. Including memory copies: 17.291/20. These are timeline activity, not occupancy.
- All measured inter-PPO gaps: 2.556 s. CPU environment batch ranges overlap 2.473 s (96.8%). GPU kernels occupy 0.739 s of those gaps; copies occupy 0.320 s (overlap possible).
- During 1.542 s of the gaps, CPU environment batches are active with no GPU kernels or copies. This supports CPU rollout completion as the main exposed wait, but environment batch ranges include OpenMP scheduling/synchronisation, not just engine instructions.
- Training and inference kernel activity overlap for 5.452 seconds. Times for overlapping categories must not be added as a wall-clock partition.

## PPO kernel sums

These are sums across GPU kernels, not exclusive wall time. Matrix multiplications include optimiser matrix operations as well as network forward/backward.

- other kernels: 2.981 s (20.1%).
- matrix multiplications and reductions: 9.299 s (62.7%).
- minGRU scans: 0.774 s (5.2%).
- PPO/advantage processing: 0.899 s (6.1%).
- optimizer explicit kernels: 0.867 s (5.8%).

Conclusion: PPO still accounts for most of each update cycle, but faster PPO now exposes CPU rollout completion. Prioritise engine/worker scheduling within the exposed tail; matrix multiplications remain the largest GPU category. minGRU scans are a smaller target. No new code optimisation or learning-equivalence claim is made by this profile.
