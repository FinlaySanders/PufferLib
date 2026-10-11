# Zero-time mask: stock C replication

Stock C backend; fixed clock 2026-09-20 12:00 UTC; 512 agents; first 6000 completions per arm; drop first 4000, retain next 2000.

| Frozen policy / seed | Off mean ± SE | On mean ± SE | Δ mean | Δ role-standardized | Off → on median | Timeouts off → on |
|---|---:|---:|---:|---:|---:|---:|
| fixwt4b_s705_s21 | 20,060 ± 568 | 19,167 ± 556 | -893 (-4.5%) | -420 | 12,084 → 10,683 | 24 → 1 |
| fixwt2b_s703_s21 | 17,513 ± 500 | 18,320 ± 550 | +808 (+4.6%) | +1,139 | 10,432 → 10,289 | 14 → 1 |
| fixwt1b_s701_s21 | 15,088 ± 417 | 13,912 ± 394 | -1,177 (-7.8%) | -979 | 9,268 → 8,722 | 19 → 0 |
| fixwt4b_s706_s21 | 19,483 ± 591 | 19,655 ± 603 | +172 (+0.9%) | +387 | 11,036 → 10,353 | 20 → 0 |
| fixwt2b_s704_s21 | 16,889 ± 485 | 16,935 ± 469 | +46 (+0.3%) | +92 | 10,102 → 10,407 | 19 → 0 |
| baseline_s2901_s32 | 13,193 ± 348 | 14,035 ± 362 | +842 (+6.4%) | +561 | 8,186 → 9,300 | 26 → 0 |

Earlier baseline_s2901_s21: off 14,200 ± 360; on 13,122 ± 343; Δ −1,078 (−7.6%); timeouts 21 → 0 in 2,000 retained games.

These are completion-order samples. The stock and environment loggers may list concurrent completions in different orders; score and timeout figures come from the stock log, and depth/action figures from the environment log. Results from one checkpoint or eval seed do not establish a population-wide effect.
