---
name: no-class-pruning-action-space
description: "give the full item-verb action space, let RL learn class-appropriate use — never pre-prune verbs by class strategy"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
---

When designing the NetHack action/verb set, include ALL legal item-interaction verbs (WEAR, TAKE-OFF, PUT-ON, REMOVE, WIELD, APPLY, READ, DROP, EAT, QUAFF, THROW, ZAP) even ones the current class (Monk) usually shouldn't use — e.g. WIELD, which I wrongly excluded because "a Monk fights bare-handed." The policy should learn not to use them.

**Why:** the user wants generality (the reward sweep can vary configs/class) and a principled "let it learn" design; hard-coding strategy into the action space is the wrong call.

**How to apply:** action masks encode LEGALITY only (an item of that oclass is present, or the worn/wielded bit is set for take-off/remove/un-wield) — never desirability. If a verb creates a one-way trap (WIELD without un-wield = lose martial arts irreversibly, like WEAR without TAKE-OFF), close the trap by making it reversible, don't drop the verb. See [[nethack-env-setup]], [[nethack-arch-campaign]].
