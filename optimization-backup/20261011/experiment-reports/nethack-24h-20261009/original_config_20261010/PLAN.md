# Restore the original configuration as the primary optimization target

User correction: 2048 environments was a scaling test. Use the original 512 environments, horizon 512, four buffers, batch262144, minibatch4096, 113PPO updates. Retain32 shared CPUworkers and the optimized implementation. Primary model15.55M; 5.10M is a secondary model-size check. Production config already matches these rollout dimensions and is not edited.

Run ABBA large/small/small/large,64epochs, warm24, measure24–62. This restores the original mature benchmark window, with12288–32768 decisions per environment. The previous2048/H128 benchmark used a different per-game window; do not attribute cross-configuration SPS differences solely to environment count. Compare sizes within this restored workload.

Frozen actor, scratch optimizer writes, identical recorded actions, full inference and training computation. Small network random/frozen. Check all64observation hashes against the historical512/H512 replay and across current repeats. Use phase timings to determine whether a fresh profile is needed. Keep scaling evidence separately labelled.
