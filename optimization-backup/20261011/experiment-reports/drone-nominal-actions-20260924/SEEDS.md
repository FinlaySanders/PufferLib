# Five-seed comparison

89,128,960 training steps per run; default config and DR=0.05. Training seeds 901–905, both training mappings. All evaluated on fixed nominal mapping, eval seed 901, 512 agents, 4096 requested episodes per policy. Means below average logged metrics across five policies; no pooled episode-level claim. Source metrics printed to 3 decimals. Fixed variant also uses nominal reset RPMs.

| Train seed | Old hover error (cm) | Fixed hover error (cm) | Old race completion | Fixed race completion |
|---|---:|---:|---:|---:|
| 901 | 2.8 | 2.5 | 98.9% | 99.3% |
| 902 | 3.0 | 2.3 | 98.6% | 99.2% |
| 903 | 2.9 | 2.5 | 99.0% | 99.3% |
| 904 | 2.6 | 2.0 | 99.8% | 97.9% |
| 905 | 2.7 | 2.6 | 97.2% | 99.1% |
old perf: mean=0.85080 sample_sd=0.00444
old hover/perf: mean=0.70500 sample_sd=0.00752
old hover/ema_dist: mean=0.02800 sample_sd=0.00158
old hover/ema_vel: mean=0.05860 sample_sd=0.00182
old race/completed: mean=0.98700 sample_sd=0.00949
fixed perf: mean=0.84620 sample_sd=0.00409
fixed hover/perf: mean=0.69760 sample_sd=0.01081
fixed hover/ema_dist: mean=0.02380 sample_sd=0.00239
fixed hover/ema_vel: mean=0.07160 sample_sd=0.00623
fixed race/completed: mean=0.98960 sample_sd=0.00598
