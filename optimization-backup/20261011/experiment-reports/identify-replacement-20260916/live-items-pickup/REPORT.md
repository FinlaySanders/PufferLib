# Live ring and scroll interventions

Real items, frozen policies, 256-decision follow-up (or earlier episode end). Eight search seeds per policy and item class. Known useful / unknown useful / known control arms are matched at intervention. Actual ring equipping and scroll consumption are engine-audited.

| Policy | Item | Arm | Trials | Target attempted | Equipped / consumed | Early deaths |
|---|---|---|---:|---:|---:|---:|
| additive | ring | known_useful | 8 | 0 | 0 | 1 |
| additive | ring | unknown_useful | 8 | 0 | 0 | 1 |
| additive | ring | known_control | 8 | 0 | 0 | 1 |
| additive | scroll | known_useful | 8 | 1 | 1 | 2 |
| additive | scroll | unknown_useful | 8 | 1 | 1 | 0 |
| additive | scroll | known_control | 8 | 0 | 0 | 1 |
| replacement | ring | known_useful | 8 | 0 | 0 | 0 |
| replacement | ring | unknown_useful | 8 | 0 | 0 | 0 |
| replacement | ring | known_control | 8 | 0 | 0 | 0 |
| replacement | scroll | known_useful | 8 | 0 | 0 | 0 |
| replacement | scroll | unknown_useful | 8 | 0 | 0 | 0 |
| replacement | scroll | known_control | 8 | 0 | 0 | 0 |

Ring: uncursed +3 protection, known or unidentified; control known +0 protection. Scroll: uncursed enchant armour with worn armour at enchantment <=2; control known blank paper. All arms disclose uncursed status. Ring unknown identity also hides its enchantment under the normal observation rules.

Blank paper is not consumed by reading, so attempts are the relevant control metric. Trials without eligible contexts are excluded. Later threats and deaths are natural. Policies see different states across training variants: these are not causal comparisons of encoder architecture.

The item is placed on an empty hero tile and delivered through one forced real PICKUP action. The recurrent network processes the pre-pickup observation and subsequently receives the normal pickup message. The pickup itself is experimental, not a policy decision. Small samples and the finite window do not establish zero lifetime use.
