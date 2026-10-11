---
name: formability-first-encoders
description: "User doctrine: encoders must keep every representation class FORMABLE (esp. relations); demand prunes usage, never existence — missing paths fail silently (launcher lesson)"
metadata:
  type: feedback
---

Encoders must be precisely general: every contract class (esp. RELATIONS via gate→query→keys
paths) kept formable in every arm at nominal cost. Demand-driven representation selects among
formable representations only — it cannot conjure unformable ones.

**Why:** a missing path fails silently — pre-wld the bow↔ammo relation was UNFORMABLE and the
Ranger meleed for 1B steps looking "converged"; the pure-archer counterfactual was invisible.
Cost asymmetry is measured: unused capacity ≈ free (bok bit inert), missing capacity = a lost
playstyle. My earlier "demand decides, add capacity when demand shows" was backwards at the
existence level; user corrected it ("relational representations are important").

**How to apply:** audit arms with a formability column (feature source → entity set: does a
gate→query→keys path exist?); every ✗ needs written justification. Known silent holes
2026-08-26: monster↔inventory, item↔terrain, spell↔monster. GATE channels on focused entities
(wielded, nearest hostile, underfoot) are the cheap enabler. See [[no-item-whitelists-learnable-first]],
encoder_contract.md artifact §1/§3.

**2026-08-26 AUDIT DONE (contract §8):** 11 relations audited, source-verified + demand-probed
(240K champion-h frames). Served ✓: hero↔{monsters,items,terrain} (EXACT per-token),
wielded↔inventory (proven), item↔terrain (per-oclass counts ‖ crop), message↔state.
Soft holes ◐: monster↔inventory + spell↔monster — species identity reaches h at only
0.418 top-1 (floor 0.153), dist R² .36, underfoot presence .836; class-level served by threat
block/hazard bits. Justified ✗: two-slot inv↔inv verbs (decoder has 1 slot pointer/verb; no
such verb in action space), monster↔monster pairwise. FIXES (both ~0-param, unproposed):
nearest-hostile GATE (concat labm token-0 features, bypass attn) hardens both ◐;
underfoot GATE (labi dx=dy=0 token) serves floor-eat/pickup (live corpse/lichen demand).
Probe tooling: inline in transcript (declab dumps: h at byte 4812, TOKM 4526, TOKI 4654).
