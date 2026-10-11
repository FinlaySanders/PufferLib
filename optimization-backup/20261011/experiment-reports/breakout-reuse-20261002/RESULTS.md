# Breakout reuse pilot results

Two-seed pilot; final fresh-environment evaluations of at least 10,000 completed games per policy. All train for 54,919,168 environment steps. Score is the mean episode score. Timing shares a GPU/CPUs with NetHack.

| Setting | Actual passes | Seed 73 score | Seed 74 score | Mean ± sample SD | Mean training seconds |
|---|---:|---:|---:|---:|---:|
| tuned | 1.5 | 780.70 | 850.06 | 815.38 ± 49.05 | 17.92 |
| fourfold | 7.5 | 847.78 | 860.61 | 854.19 ± 9.07 | 24.03 |
| passes16 | 16.0 | 859.19 | 805.52 | 832.36 ± 37.95 | 28.74 |

## Validation and overhead

The first 20 checkpoints in both sync and async mode match byte-for-byte across pristine/off/on builds. First-minibatch sync ratio is 1.000455, KL 1.53e-6, frozen/live advantage RMSE 0.001243 (bf16 rounding). Histogram/sample counts pass.

Seed 73: full 55M-step checkpoints and final eval scores match exactly. Training time off 17.537s, on 18.137s; change +3.43%.

Seed 74: full 55M-step checkpoints and final eval scores match exactly. Training time off 18.026s, on 17.710s; change -1.75%.

These timings do not certify a sub-3% overhead budget: the concurrent workload changes during each run.

## Pass diagnostics

Nearest normal logging window to 10%, 50%, and 90% of training; each row averages that window. `first/last` below means the first/last reuse pass within that window, not the beginning/end of training. Raw CSV retains every pass. Advantages exclude the bootstrap position.

| Run | Training fraction | Pass | KL | PPO zeroed % | Grad norm | Advantage magnitude / frozen | Cosine with frozen | Value MSE vs frozen |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fourfold_s73 | 10% (epoch 41) | 0 | 0.31652 | 7.86 | 0.236 | 0.922 | 0.701 | 0.0539 |
| fourfold_s73 | 10% (epoch 41) | 7 | 0.17134 | 4.35 | 0.202 | 0.805 | 0.640 | 0.0434 |
| fourfold_s73 | 50% (epoch 206) | 0 | 0.14995 | 3.01 | 0.322 | 0.984 | 0.836 | 0.0824 |
| fourfold_s73 | 50% (epoch 206) | 7 | 0.12798 | 2.62 | 0.297 | 0.916 | 0.759 | 0.0566 |
| fourfold_s73 | 90% (epoch 384) | 0 | 0.01054 | 0.18 | 0.210 | 0.999 | 0.980 | 0.0496 |
| fourfold_s73 | 90% (epoch 384) | 7 | 0.01032 | 0.19 | 0.135 | 0.984 | 0.977 | 0.0466 |
| fourfold_s74 | 10% (epoch 43) | 0 | 0.22738 | 5.02 | 0.331 | 0.952 | 0.715 | 0.0708 |
| fourfold_s74 | 10% (epoch 43) | 7 | 0.15723 | 3.76 | 0.287 | 0.835 | 0.659 | 0.0647 |
| fourfold_s74 | 50% (epoch 200) | 0 | 0.20859 | 4.18 | 0.401 | 0.976 | 0.823 | 0.0964 |
| fourfold_s74 | 50% (epoch 200) | 7 | 0.16707 | 3.14 | 0.378 | 0.900 | 0.764 | 0.0737 |
| fourfold_s74 | 90% (epoch 387) | 0 | 0.00930 | 0.15 | 0.212 | 0.999 | 0.984 | 0.0534 |
| fourfold_s74 | 90% (epoch 387) | 7 | 0.00886 | 0.14 | 0.138 | 0.987 | 0.979 | 0.0511 |
| passes16_s73 | 10% (epoch 44) | 0 | 0.22807 | 4.92 | 0.325 | 0.971 | 0.689 | 0.1033 |
| passes16_s73 | 10% (epoch 44) | 15 | 0.21999 | 4.71 | 0.287 | 0.785 | 0.612 | 0.0740 |
| passes16_s73 | 50% (epoch 203) | 0 | 0.25267 | 4.50 | 0.310 | 0.996 | 0.813 | 0.1013 |
| passes16_s73 | 50% (epoch 203) | 15 | 0.21825 | 3.88 | 0.373 | 0.929 | 0.725 | 0.0883 |
| passes16_s73 | 90% (epoch 372) | 0 | 0.02905 | 0.53 | 0.245 | 0.998 | 0.960 | 0.0562 |
| passes16_s73 | 90% (epoch 372) | 15 | 0.02934 | 0.58 | 0.155 | 0.976 | 0.953 | 0.0501 |
| passes16_s74 | 10% (epoch 49) | 0 | 0.29694 | 6.30 | 0.406 | 0.946 | 0.632 | 0.1063 |
| passes16_s74 | 10% (epoch 49) | 15 | 0.23384 | 5.15 | 0.275 | 0.737 | 0.558 | 0.0769 |
| passes16_s74 | 50% (epoch 207) | 0 | 0.19472 | 3.60 | 0.350 | 0.988 | 0.782 | 0.0939 |
| passes16_s74 | 50% (epoch 207) | 15 | 0.19968 | 3.66 | 0.357 | 0.913 | 0.696 | 0.0778 |
| passes16_s74 | 90% (epoch 378) | 0 | 0.03025 | 0.53 | 0.257 | 0.998 | 0.958 | 0.0515 |
| passes16_s74 | 90% (epoch 378) | 15 | 0.03053 | 0.58 | 0.159 | 0.971 | 0.942 | 0.0445 |
| tuned_s73 | 10% (epoch 33) | 0 | 0.02160 | 0.37 | 0.291 | 0.963 | 0.695 | 0.0294 |
| tuned_s73 | 10% (epoch 33) | 1 | 0.02646 | 0.30 | 0.289 | 0.940 | 0.613 | 0.0365 |
| tuned_s73 | 50% (epoch 206) | 0 | 0.13639 | 2.93 | 0.455 | 0.982 | 0.898 | 0.0768 |
| tuned_s73 | 50% (epoch 206) | 1 | 0.09713 | 2.19 | 0.344 | 0.943 | 0.872 | 0.0724 |
| tuned_s73 | 90% (epoch 378) | 0 | 0.00782 | 0.13 | 0.252 | 0.998 | 0.992 | 0.0581 |
| tuned_s73 | 90% (epoch 378) | 1 | 0.00662 | 0.09 | 0.173 | 0.994 | 0.990 | 0.0567 |
| tuned_s74 | 10% (epoch 38) | 0 | 0.01319 | 0.07 | 0.275 | 0.948 | 0.764 | 0.0345 |
| tuned_s74 | 10% (epoch 38) | 1 | 0.02287 | 0.28 | 0.262 | 0.912 | 0.677 | 0.0389 |
| tuned_s74 | 50% (epoch 211) | 0 | 0.19828 | 3.63 | 0.443 | 0.988 | 0.901 | 0.0725 |
| tuned_s74 | 50% (epoch 211) | 1 | 0.17802 | 3.25 | 0.520 | 0.958 | 0.874 | 0.0686 |
| tuned_s74 | 90% (epoch 373) | 0 | 0.00496 | 0.07 | 0.240 | 0.999 | 0.995 | 0.0630 |
| tuned_s74 | 90% (epoch 373) | 1 | 0.00608 | 0.09 | 0.207 | 0.996 | 0.993 | 0.0605 |
