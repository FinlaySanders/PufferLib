# BALROG progression on article policies

Fork evaluations; mean/median of per-episode maximum lookup progression. 4,000 burn-in games discarded, then 10,000 retained per policy. Partial groups are identified by their number of policies. This measures the BALROG metric, not the complete BALROG agent evaluation protocol.

| Cohort | Policies finished | Games | Mean progression | Median progression |
|---|---:|---:|---:|---:|
| Depth 2B | 8 | 80,000 | 15.31% | 12.56% |
| Score 1B | 2 | 20,000 | 10.33% | 7.45% |
| Score 2B | 2 | 20,000 | 11.02% | 7.45% |
| Score 4B | 2 | 20,000 | 11.48% | 11.70% |

Per-policy results

| Policy | Games | Mean progression | Median progression |
|---|---:|---:|---:|
| depth2b_s801 | 10,000 | 16.98% | 12.56% |
| depth2b_s802 | 10,000 | 15.79% | 12.56% |
| depth2b_s803 | 10,000 | 14.73% | 12.56% |
| depth2b_s804 | 10,000 | 14.50% | 9.77% |
| depth2b_s805 | 10,000 | 16.20% | 12.56% |
| depth2b_s806 | 10,000 | 14.93% | 12.56% |
| depth2b_s807 | 10,000 | 14.41% | 12.56% |
| depth2b_s808 | 10,000 | 14.92% | 12.56% |
| fixwt1b_s701 | 10,000 | 10.01% | 7.45% |
| fixwt1b_s702 | 10,000 | 10.66% | 7.45% |
| fixwt2b_s703 | 10,000 | 10.76% | 7.45% |
| fixwt2b_s704 | 10,000 | 11.28% | 11.70% |
| fixwt4b_s705 | 10,000 | 11.78% | 11.70% |
| fixwt4b_s706 | 10,000 | 11.19% | 7.45% |
