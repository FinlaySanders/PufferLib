# Known versus unknown useful items

Two frozen 1B policies (additive and replacement discovery), eight trajectory seeds per policy, two item classes, three matched arms: 96 trials per delivery mode. Search starts after 20 real policy decisions, with up to 2,000 decisions to find an eligible state. Follow the policy for 256 decisions or until episode termination. No training or production edits.

Ring arms: uncursed +3 protection with identity/enchantment known; the same physical ring with identity unknown; known uncursed +0 protection control. At least one free finger, no cursed gloves, no limbless form. All arms disclose uncursed status. The unknown ring's enchantment is hidden by the normal engine observation rule, so this compares full knowledge against unidentified appearance, not type knowledge alone.

Scroll arms: uncursed enchant armour, known versus unidentified; known uncursed blank-paper control. Player wears armour, and all worn armour has publicly known enchantment between -3 and +2. This avoids the ordinary over-enchantment destruction risk at delivery. No confusion/other condition bits. Later situations may change naturally. Blank paper remains after reading, so its read-attempt rate is meaningful; zero consumption is intrinsic to that control.

All trials begin at >=80% HP, not hungry, not swallowed/busy, no live hostile within eight squares, <=45 inventory items, and the useful type not yet globally discovered. No existing inventory item of the useful type (or blank paper for scroll trials), preventing stack merging and manipulation of existing discoveries. The current implementation also applies the worn-armour enchantment filter to ring trials. Eligibility uses engine state for experiment selection, not policy observations. Normal policy observations, masks and memory are used thereafter.

Known arms call the engine's discovery routine; unknown arms preserve the undiscovered type. Objects are constructed without random enchantment/blessing, with actual game state and weight updated. At delivery, assertions verify the target appears in the real inventory, public identification state matches the arm, and both verb and target are legal. Matched triples are checked for identical seed, episode, intervention step, role, object ID, inventory letter, pre-delivery turn and AC.

Actual ring equips and scroll useup are audited by the pre-existing item-audit engine. Scroll consumption must match the target object ID and READ verb. Selected actions alone do not count as successful use. Log all subsequent target availability, knowledge, action probabilities, nearby threats and chosen verbs. Both models use the same diagnostic engine; artifact paths and hashes are retained.

Interpretation limits: eight selected opportunities per policy/class, correlated trajectories across delivery variants, limited early-game window, and possible later threats/death. Failure to act is not evidence of zero lifetime use. These tests assess whether making a useful item known is sufficient to elicit use; they do not by themselves localize a neural bottleneck. Unknown and control arms can be used rationally for experimentation. Different policies encounter different game states, so their rates do not isolate architecture causally.

## Delivery

Items are added directly to inventory, without a pickup message. Search limit may truncate follow-up if an intervention happens near decision 2000; results explicitly record elapsed time.
