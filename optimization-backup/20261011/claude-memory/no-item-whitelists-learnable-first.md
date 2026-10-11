---
name: no-item-whitelists-learnable-first
description: never hardcode item-specific whitelists (e.g. lichen corpses); make behaviors learnable and let RL find the equilibrium
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-07-23T10:45:55.616Z
---

Rejecting the lichen-corpse whitelist (2026-07-23), the user set the principle: no
item-specific hardcoding — remove env-side blockers instead and let the policy learn the
economy (corpse eating, guilt-vs-alignment, freshness-by-memory). Also be open to
strategy inversions: a cost that looks prohibitive (Monk meat guilt breaking prayer) may
be net-positive because the thing it breaks (prayer) is itself replaceable by the new
behavior (corpses ARE food). Sibling of [[no-class-pruning-action-space]].

**Why:** hand-picked exceptions bake in our strategy guesses and don't generalize;
observable-feedback loops (guilt messages, prayer outcomes, food poisoning) make the
tradeoff learnable on equal footing with a human.

**How to apply:** when a "safe subset" whitelist tempts (specific corpse/item/spell),
instead remove the paternalistic env gate wholesale, verify the feedback signals are
observable, and A/B the learnable version. Mask only for LEGALITY, never for safety
that a player could also misjudge.

**2026-08-26 extension (user): learnable-first applies to OBS BITS too.** "We don't want to be
patching with bits that are learnable. Sure we need to give the network basic game information
but it should learn how to use it." Line: static rule tables (oc_skill, armcat, monster stats)
= basic info, fine to expose per-entity; derived state predicates (lnc_ready-style "you are
ready to fire") = patches, last resort only after the learnable path (content-keyed pointers,
wld-carried features) demonstrably fails WITH exploration fixed. Launcher confound: wld +
lnc_ready shipped together — learnable path never tested alone; capacity lab + paired ablation
can settle whether lnc_ready is removable. See encoder_contract.md artifact §3/§6/§7.
