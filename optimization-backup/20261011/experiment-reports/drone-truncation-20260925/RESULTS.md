# Drone termination/truncation comparison

3 paired training seeds per setting, ~89.13M steps each, 4,096 evaluation episodes per policy. Values below are means of reported evaluation metrics across the three seeds. Same evaluator and evaluation seed for both arms.

| DR | Handling | Overall perf | Hover distance (cm) | Hover speed (m/s) | Race completion |
|---|---|---:|---:|---:|---:|
| 5% | Single done | 0.847 | 2.47 | 0.071 | 99.23% |
| 5% | Separate timeout bootstrap | 0.851 | 2.40 | 0.066 | 99.20% |
| 30% | Single done | 0.752 | 6.97 | 0.159 | 81.43% |
| 30% | Separate timeout bootstrap | 0.759 | 6.10 | 0.163 | 79.97% |

## Per-seed results

| DR | Seed | Handling | Perf | Hover distance (cm) | Race completion |
|---|---|---|---:|---:|---:|
| 5% | 901 | Done | 0.848 | 2.50 | 99.4% |
| 5% | 901 | Separate | 0.848 | 2.50 | 98.9% |
| 5% | 902 | Done | 0.849 | 2.30 | 98.6% |
| 5% | 902 | Separate | 0.855 | 2.20 | 99.6% |
| 5% | 903 | Done | 0.844 | 2.60 | 99.7% |
| 5% | 903 | Separate | 0.851 | 2.50 | 99.1% |
| 30% | 901 | Done | 0.744 | 7.20 | 79.8% |
| 30% | 901 | Separate | 0.751 | 6.60 | 80.4% |
| 30% | 902 | Done | 0.771 | 5.70 | 83.9% |
| 30% | 902 | Separate | 0.774 | 5.30 | 79.0% |
| 30% | 903 | Done | 0.740 | 8.00 | 80.6% |
| 30% | 903 | Separate | 0.751 | 6.40 | 80.5% |

All final checkpoints are finite. The 2M-step no-timeout original/off/on checkpoints match byte-for-byte. CUDA GAE scalar-reference checks and environment final-observation/failure-precedence/reset checks pass.

See METHODS.md and experiment.patch. Production workspace was not modified by this experiment.
