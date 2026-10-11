# Depth 2B s906 BALROG certificate

Fork evaluation, seed 7, 512 agents. Discard first 4,000 completed games, retain next 10,000. Both SEARCH20 and RUN masked. Progression is max(archived BALROG depth lookup, XP-level lookup) per episode using maximum depth and XP. This measures the BALROG progression metric, not its complete agent evaluation protocol. Instrumented smoke matches original binary scores, depth and episode length.

| Role | Games | Mean BALROG | Max BALROG |
|---|---:|---:|---:|
| Overall | 10000 | 15.90% | 64.65% |
| Archeologist | 761 | 38.87% | 64.65% |
| Barbarian | 716 | 16.94% | 60.16% |
| Caveman | 781 | 13.41% | 55.44% |
| Healer | 755 | 13.19% | 60.16% |
| Knight | 816 | 11.45% | 64.65% |
| Monk | 748 | 20.18% | 64.65% |
| Priest | 796 | 11.86% | 55.44% |
| Ranger | 786 | 13.26% | 60.16% |
| Rogue | 776 | 11.14% | 64.65% |
| Samurai | 767 | 17.37% | 60.16% |
| Tourist | 724 | 10.99% | 64.65% |
| Valkyrie | 772 | 14.38% | 64.65% |
| Wizard | 802 | 14.36% | 60.16% |
