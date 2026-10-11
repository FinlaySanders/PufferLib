# Altar audit results

128,000 natural policy decisions: eight seeds × 8,000 decisions × two frozen 1B policies. Includes partial episodes.

| Policy | Decisions with altar glyph on map | Episodes with altar glyph | Decisions standing on altar | ALTAR_ID legal | Unknown-BUC opportunity | Selected ALTAR_ID |
|---|---:|---:|---:|---:|---:|---:|
| additive | 659 | 6 | 5 | 5 | 5 | 0 |
| replacement | 3357 | 4 | 20 | 20 | 20 | 0 |

No masking mismatch was observed while standing on a natural altar. Mean masked ALTAR_ID probability on these legal decisions:
- additive: 3.76058104e-10
- replacement: 2.1856265e-05

## Controlled execution and choice

Corrected controlled-v2 only; the earlier synthetic fixture is invalid and excluded. Put an aligned altar under a healthy player with naturally held unknown-BUC items. Eight matched contexts per policy, forced ALTAR_ID versus free policy choice, 128-decision follow-up.

| Policy | Forced tests | Eligible items revealed | Missing items | Free-choice legal decisions | Free ALTAR_ID selections |
|---|---:|---:|---:|---:|---:|
| additive | 8 | 11/11 | 0 | 149 | 0 |
| replacement | 8 | 13/13 | 0 | 241 | 0 |

All 24 eligible items were BUC-identified and retrieved in 16 forced actions, taking 2–4 game turns per action in these inventories. The freely acting policies never chose ALTAR_ID in these controlled contexts either.

## Effect of information

A matched-state diagnostic temporarily reveals BUC, refreshes public observations and legal masks, and forwards from the same recurrent state. BUC affects some conditional item distributions (especially eating/dropping in these inventories), while immediate verb distributions usually change little. This demonstrates sensitivity, not improved return. The supplied information includes legal-mask changes for known curses, so distribution changes are not purely an encoder effect.

Following real forced identification also changes later actions, but the drop/pickup macro consumes turns and changes world trajectories. These follow-ups therefore do not isolate the benefit of information. Unknown-BUC items were naturally encountered, not selected to guarantee a valuable equipment decision.

## Interpretation

Observed bottlenecks are sparse altar opportunities and extremely low learned willingness to use ALTAR_ID when it is legal. The basic action/mask implementation works in the tested cases. This is consistent with failure to learn the delayed value of identification; it is not proof of its cause or evidence of an encoder defect. BUC revelation has no dedicated reward term in the inspected training environment. No claim that these policies never use altars in all games is justified from this sample.
