---
name: nethack-weapon-diagnostic
description: "REFUTED: policies do NOT throw away their melee weapon (1-7% of throws); they stockpile found weapons as ammo. Per-episode audit flags are a misleading statistic"
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-15T18:28:43.238Z
---

2026-08-15, champion s311, 10 eps/role (scratchpad/wepprobe.c + wepprobe2.c,
built with the demo clang line; measures per-ACTION not per-episode).

| role | bare-handed | threw in-hand / all throws | unwield-toggles / real wields |
|---|---|---|---|
| Knight | 11.7% | 88/1448 (6.1%) | 2/102 |
| Valkyrie | 16.2% | 20/893 (2.2%) | 1/356 |
| Samurai | 10.9% | 15/1156 (1.3%) | - |
| Priest | 1.6% | 65/937 (6.9%) | - |
| Barbarian | 1.6% | 29/1197 (2.4%) | 0/72 |
| Monk | 99.9% | 0/832 | - |

**The "throws its own sword" finding is REFUTED.** Only 1-7% of throws are the
wielded item. Weapon stocks GROW 2->6-9 per episode (autopickup takes all
classes), so the policy is stockpiling found weapons and throwing those —
sane ranged play. Monk is the control: 99.9% bare-handed (correct, martial
arts) and it is the top-scoring role at 11,491.

**The WIELD-toggle hypothesis is also REFUTED**: re-selecting the held item
(which unwields, by design in nethack_verb_wield) happens 0-2 times per 10
episodes vs 72-356 real swaps. Not the cause of bare-handed time.

Bare-handed time for melee roles (Kni 11.7 / Sam 10.9 / Val 16.2%) is
therefore NOT explained by either mechanism and remains unexplained — likely
the gap between dropping/throwing a weapon and re-wielding a replacement,
i.e. swap latency during the 356 real Valkyrie swaps. Low priority: Priest
and Barbarian sit at 1.6% with the same action space, so it is not structural.

**Why:** an episode-level "did it ever do X" flag (the kit audit's format)
massively overstates rare actions — X once in 2,000 steps reads as 10/10.
**How to apply:** for any behavioural claim, count ACTIONS not episodes, and
put a known-correct role in the sample as a control (Monk for wielding).
See [[nethack-kit-audit]], [[nethack-launcher-gap]].
