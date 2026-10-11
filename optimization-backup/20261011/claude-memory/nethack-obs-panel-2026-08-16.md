---
name: nethack-obs-panel-2026-08-16
description: "10-arm 5-seed 217M panel: only bl128 (+223) cleared; the INERT spellbook bit scored +71 and is now the null calibration. Plus the max-pool/wielded-item diagnosis"
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-16T13:33:53.133Z
---

2026-08-16 overnight, 51 runs, control = idb_s401-405 embed panel (**3756, sd
155**; seed 401 = 3520 is the panel MINIMUM and flatters every paired arm by
~236 — the source of yesterday's fake single-seed wins).

| arm | n | mean | vs panel | beats own ctrl |
|---|---|---|---|---|
| **bl128** blstats hid 64->128 | 5 | **3980** | **+223±93** | 4/5 |
| bok spellbook bit — **INERT NULL** | 5 | 3828 | +71±173 | 4/5 |
| invhid32 inv slot 16->32 (SPKEY decoupled) | 5 | 3795 | +39 | 2/5 |
| p1x32 patch bottleneck 16->32 | 5 | 3817 | +60±114 | 4/5 |
| lnc launcher trio obs | 5 | 3797 | +40±142 | 2/5 |
| acx AC-upgrade bit | 5 | 3708 | −48±86 | 2/5 |
| loc384 crop hid 256->384 | 5 | 3690 | −66±105 | 1/5 |
| gem2 launcher+gem (oclass-13 fix) | 5 | 3686 | −70±89 | 1/5 |
| emb48 glyph embed 32->48 | 5 | 3657 | −99±91 | 1/5 |
| film identity FiLM on encoder out | 5 | 3614 | −142±200 | 2/5 |

**THE NULL IS THE RESULT.** bok cannot change any decision (starting books
teach known spells; READ mask blocks re-reading) yet scored **+71, beat its
control 4/5, and swung 838 pts across seeds** (3197 on seed 403 — a clean
rc=0 run that just trained badly, 1147 eplen vs 1345). So the floor for
"this did something" at 5v5 is ~±200, and nine of ten arms are retired.
Pattern: **widening an existing compressed channel won; every derived
feature / structured addition lost** (acx, film, and the earlier reverted
entity channel). emb48 and loc384 say spatial capacity is NOT the lever.

**Wielded-item diagnosis (scratchpad/rangeprobe.c, Ranger-forced CPU rollout,
1B lnc arm, 12 eps).** Shots by range: **1:1729 2:115 3:48 4:37 5:6 6:2 7:4
8:5** — 85% of "archery" is fired at an ADJACENT monster, 2.6% at range >=4.
And **3033 melee attacks while wielding the LAUNCHER** vs 4 with a melee
weapon; the bow is held 23788/25000 steps. Engine source: `BOW()` passes
damage dice `2,2` — a wielded bow is **d2**, not the d4 I claimed earlier,
vs d4 for the dagger it replaced. So the launcher bits didn't buy ranged
combat; they bought a permanent 50% melee damage cut.
**Root cause is representational asymmetry:** AC is an engine outcome scalar
sitting in blstats, so armour changes are visible; NetHack has **no attack
stat**, and the wielded item reaches the trunk ONLY through inv pool =
55 slots -> 16 dims each -> project to 128 -> **elementwise max**. Max-pool
CAN express wielded-routing (weight the W_WEP bit high) but **gradients flow
only through the argmax**, so it is chicken-and-egg to learn.
Selection is fine and separate: 12 cosine pointer heads score per-slot keys
(the same invh reps) with learned log-tau — that is why the arm reached 83%
launcher use. Selection machinery good, situational-awareness machinery lossy.

**RUNNING (2026-08-16 13:32, scratchpad/wield_queue.sh):** wield pass-through
`NH_WIELD_CAT` (scratchpad/wield.patch, 136 lines) = the first W_WEP slot's
16-dim rep copied to the concat tail (790->806), backward adds the tail grad
into inv_grad beside the keygrad add, before the shared relu mask; slot index
saved as wield_idx. Gradcheck PASS (NH_TEST_WIELD=1, harness matches the
first-match rule since it randomises st[5]). Flag-off fpgate PASS both arms.
5x217M, then the **bl128 1B pair** (bl1b_s311/312) vs the 7,035 record.
Caveat to hold: the d2-bow pathology exists only WITH launcher obs, which is
not shipping — on the baseline this is a bet that trunk-visible held-item
state helps generally (only baseline symptom: 11-16% bare-handed time for
Kni/Sam/Val, still unexplained). 16 dims on a 750 concat may be under the
±200 resolution; if null, the follow-up is wielded+quivered at 32-dim slots.
Also found: **20 of the 126 blstats features are hard-zero** under
NH_ID_EMBED (role/race/gender one-hots, nethack.cu:519) — free simplification.
See [[nethack-launcher-gap]], [[nethack-film-arm]], [[nethack-env-setup]].
