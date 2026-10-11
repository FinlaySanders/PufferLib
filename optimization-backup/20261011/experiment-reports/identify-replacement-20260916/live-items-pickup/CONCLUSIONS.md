# Rings and scrolls: persistent known/unknown interventions

Completed 192 diagnostic trajectories: two policies, eight seeds, two item classes, three item arms, two delivery modes. Delivery modes reuse the same seeds and are not independent replications. The main table uses real in-game pickup delivery. Follow-up is 256 policy decisions or earlier death. All 96 pickup trials passed public-knowledge and legal-action assertions; all matched triples agreed at intervention. No trial was truncated by the search budget after delivery.

| Policy | Ring: known +3 protection | Ring: unknown +3 protection | Ring: known +0 control | Scroll: known enchant armour | Scroll: unknown enchant armour | Blank-paper target reads |
|---|---:|---:|---:|---:|---:|---:|
| Additive | 0/8 equipped | 0/8 equipped | 0/8 equipped | 1/8 consumed | 1/8 consumed | 0/8 |
| Replacement | 0/8 equipped | 0/8 equipped | 0/8 equipped | 0/8 consumed | 0/8 consumed | 0/8 |

The additive policy consumed the known and unidentified enchant-armour scroll in the same seed, at policy step 120 (100 decisions after delivery). Consumption is confirmed by the engine useup hook with matching object ID and READ verb. Ring equips are checked using both actual worn state and engine setworn events.

In the separate silent-inventory-insertion experiment, additive used none of the targets. Replacement equipped the ring in 1/8 trials in every arm, including the +0 control, and read none of the target scrolls. Thus the broad low-use result is not removed by changing delivery mode, though individual trajectories change.

Inference: full identification of a beneficial item is not sufficient to reliably trigger use in these selected early-game contexts. This weakens an explanation based solely on items remaining unidentified. It does not distinguish whether the pooled representation fails to expose useful information to action selection, or RL has not learned the downstream value of using it. Individual-item probe accuracy cannot settle that distinction. No evidence here supports calling the decoder inverted.

Limitations: eight opportunities per policy/class, only two useful item types, finite early-game follow-up, later threats and deaths. Known/unknown ring also differs in publicly visible enchantment, as required by normal engine rules. +3 protection consumes ring nutrition and is not universally optimal in every subsequent situation. No natural-use frequency, lifetime-use or architecture-superiority claim is justified from these counts. Full per-trial outcomes, death counts, action probabilities and methods are in the linked experiment directories.
