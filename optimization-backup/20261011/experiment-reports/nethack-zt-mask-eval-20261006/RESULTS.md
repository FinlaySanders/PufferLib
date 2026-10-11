# Zero-time mask: frozen-policy comparison

stock C backend; fixed 2026-09-20 12:00 UTC; seed 21; 512 agents; 6,000 completions per arm; drop first 4,000 and retain next 2,000

| Metric | Mask off | Mask on |
|---|---:|---:|
| Mean score | 14,200 | 13,122 |
| Median score | 9,489 | 8,721 |
| Mean maximum depth | 3.57 | 3.50 |
| 10,000-step clockless timeouts | 21/2,000 | 0/2,000 |
| Actions without game-turn advance | 7.30% | 5.68% |
| Invalid macro actions per game | 39.7 | 22.4 |

Role-standardized score means: off 14,112, on 13,196. The score gap is therefore not explained solely by the retained set's role mix.

Stock and environment loggers can order games differently; score and clockless statistics use stock EPLOG, while depth/action statistics use environment EPLOG. This is one frozen policy and one eval seed, so the score difference needs replication.

Fork control with same 1B checkpoint, seed 7, 10,000 retained games: mask off 13,908 mean / 8,993 median; mask on 13,978 / 8,863. No-turn action fraction fell from 8.53% to 5.80%. See `zt_on_baseline_s2901/RESULTS.json`.
