# Model-size check, 2026-10-10

Width 1024 (15,552,136 parameters) versus width 512 (5,097,608 parameters), four layers. Other architecture and rollout/PPO settings unchanged. Current retained optimizations, 32 workers, sleeping main wait in both arms. Frozen random small network, trained large network; identical recorded mature actions override environment actions. All inference, backward and optimizer compute runs, updates go to scratch weights. This is a compute configuration experiment, not a comparison of learned scores.

ABBA full timings: 80 epochs, warm 64, time 64–78. Compare all observation hashes across widths and frozen initial/final model hashes within each run. Follow up with a graph-level profile and isolated GPU timing only as needed to explain the full timing result. No production source changes.
