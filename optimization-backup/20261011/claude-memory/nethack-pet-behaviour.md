---
name: nethack-pet-behaviour
description: "2026-09-08 pet census of the t1122 2B policy (per-step trace side build NH_PETLOG + pettype:none control): every role abandons the pet by ~1K turns; pets CAUSE stair yo-yo between dlvl 1-2 for Healer/Wizard/Caveman, no score benefit"
metadata:
  type: project
---

Method: side build of the vec eval (puffer_petlog / puffer_petlog_nopet, burn-in patch + a per-step trace hook in puf_step writing
step/turn/dlvl/hero xy/nearest-pet dist/pet count/hp/gold/xp/score per env to $NH_PETLOG/env<i>.pet; pet glyph range =
NETHACK_GLYPH_PET_OFF..NETHACK_GLYPH_DET_OFF from ocean/nethack/netlib.h; control = "pettype:none," prepended to NETHACK_OPTIONS_TAIL,
a multi-line macro in netlib.h). 512 agents, burn-in 300, ~1900 complete games each; sources restored after each build.

Findings (t1122 2B): pet visible in only 9-72% of the first 100 turns, <=40% of turns 100-1000, ~0 after 1000; last sighting at 1-12% of
game length for every role. Barbarian/Rogue/Ranger/Tourist/Samurai leave it almost immediately (adjacent <5% of early steps). The pet
CAUSES level-1<->2 stair dancing: descents per game with/without pet Healer 11.5/1.7 (>=5 yo-yos 60%/9%, time on dlvl1 after first
descent 80%/53%), Wizard 3.8/1.3 (22%/4%), Caveman 4.1/1.7 (27%/3%), Valkyrie 3.3/2.4; Barbarian/Monk/Samurai/Tourist unchanged.
Score with/without pet: overall 11,552/12,011; Monk 17.5K/21.1K, Rogue 10.8K/8.6K, Ranger 11.3K/9.3K, others within noise (n~150/role,
SE ~±700). User's hypothesis "Wizard/Priest drop the pet at dlvl 2 then farm on 1": the pet-driven yo-yo and extra dlvl-1 time are real
for Wizard (Priest weak); "Monk/Barb leave the pet immediately": Barbarian yes, Monk mostly.
**Why:** the user wants to understand how the policy interacts with pets (mech interp question). **How to apply:** next step = obs
ablation (clear the pet bit e[4]&8 / show the pet as a plain monster) to see whether the yo-yo keys on the pet flag; the trace hook
and the no-pet control are the tools. Related: [[nethack-cert-protocol]], [[nethack-tempo-hygiene]].
