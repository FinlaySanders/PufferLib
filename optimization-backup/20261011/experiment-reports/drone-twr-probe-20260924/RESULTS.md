# Thrust-to-weight decoding results

Three independently trained policies per DR setting, 4,096 fresh episodes per policy/test setting, balanced hover and race. Readouts below are evaluated at 5 seconds on held-out episodes. R²=1 is perfect; R²=0 is the mean-prediction baseline. Values average the three policy seeds. Nonlinear probes use gradient-boosted trees, not policy retraining.

## At each policy’s training distribution

| DR | Hover obs R² | Hover state R² | Race obs R² | Race state R² |
|---|---:|---:|---:|---:|
| 5% | 0.969 | 0.977 | 0.007 | 0.082 |
| 15% | 0.963 | 0.984 | 0.150 | 0.292 |
| 30% | 0.954 | 0.985 | 0.310 | 0.642 |

## Same 30% test distribution

| Training DR | Hover obs R² | Hover state R² | Race obs R² | Race state R² | Mean hover distance at 5 s |
|---|---:|---:|---:|---:|---:|
| 5% | 0.986 | 0.984 | 0.607 | 0.650 | 9.76 cm |
| 15% | 0.965 | 0.976 | 0.455 | 0.538 | 6.71 cm |
| 30% | 0.954 | 0.985 | 0.310 | 0.642 | 5.63 cm |

## Linear readout, tasks combined

| Training DR | Test DR | Observation R² | State R² |
|---|---|---:|---:|
| 5% | 5% | 0.040 | 0.169 |
| 5% | 30% | 0.555 | 0.707 |
| 15% | 15% | 0.167 | 0.395 |
| 15% | 30% | 0.460 | 0.644 |
| 30% | 30% | 0.311 | 0.670 |

## Interpretation

- Yes, physical thrust-to-weight information is decodable. This does not establish that the policy explicitly estimates or causally uses that parameter.
- At 5% DR, nonlinear hover decoding is near perfect from observations alone. A steady control error can expose physical parameters without an explicit recurrent estimate. Race decoding is much weaker.
- Wider test DR improves decoding even for the unchanged 5%-trained policy. Consequently, comparing each policy on its own DR does not establish improved inference from training.
- On the common 30% distribution, racing state decoding is similar for 5% and 30% training (0.650 versus 0.642), but current-observation decoding falls from 0.607 to 0.310. Stronger training gives state a larger readout advantage, rather than a higher absolute R².
- Hover distance after five seconds decreases on the common 30% test, from 9.76 cm to 5.63 cm. This is a short simulated rollout diagnostic, not a full robustness or sim2real certificate.
- Episode attrition before five seconds is small; exact row counts are retained in the result JSONs.

See METHODS.md, models.json, datasets.json, results.json and nonlinear.json for protocol, checkpoint hashes and per-seed results.
