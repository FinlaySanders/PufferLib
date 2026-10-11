---
name: nethack-kit-audit
description: "Per-role starting-kit usage audit of the champion: spellbooks never read (4 roles), launchers thrown not wielded, sling ammo UNTHROWABLE (THROW mask = weapon class only), body armor dropped"
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-15T16:40:24.148Z
---

2026-08-15 item-level kit audit of champion s311 (scratchpad/kitprobe.c: forced
role via nethack_rc_path_opts, 10 eps/role, tracks each STARTING item by
inventory LETTER within its own episode — appearances shuffle per game, so
otyp-from-glyph is only an identity for fixed-appearance classes; cloaks,
potions, scrolls, books, wands, rings, gems are APPEARANCES). Counts are
"episodes where the policy selected (verb, that item)"; slot-0 fallback picks
filtered by verb item_classes.

**Systematic misses** (n=10 eps each):
- ~~SPELLBOOKS NEVER READ~~ **RETRACTED 2026-08-15 — NOT A GAP.** Books are
  dropped because STARTING SPELLBOOKS TEACH THE SPELLS YOU ALREADY KNOW (a
  Wizard starts knowing force bolt AND carrying its book). Proof
  (scratchpad/bookprobe.c, prints the READ slot-mask + known-spell list at
  reset): every starting book is READ-legal 0 for Wiz/Hea/Pri, and for
  Hea/Pri the READ VERB itself is masked off entirely. Our own gate does it
  (book masked iff spell_ids[j]==true_otyp && spell_knows[j] > 2000, and
  starting spells sit at retention 20000). Dropping a 50-weight redundant
  book is CORRECT play. The bok_s401 arm (one bl bit "carrying an identified
  book teaching an unknown spell") is therefore INERT BY CONSTRUCTION —
  starting books fail the unknown-spell test, found books fail the
  identified test — cert 3,945 vs control 3,520 is unattributable noise, and
  the audit showed 0 READs still. Code removed from tree. LESSON: a
  "never used" row in the kit audit means nothing until you check the item is
  LEGAL — do the mask probe first (the gem gap was real, this one wasn't).
  NOTE seed 401's control (3,520) is the MINIMUM of the idb panel
  (3520/3894/3897/3716/3753), so single-seed wins on s401 are weak evidence.
- LAUNCHERS: never wielded by any launcher role; they are THROWN as missiles
  instead — Ran crossbow THROW 6/10 DROP 6/10, Sam yumi THROW 10/10 DROP
  7/10, Cav sling THROW 8/10. (Fixed by the NH_LAUNCH_OBS arm for
  arrow/bolt roles — see [[nethack-launcher-gap]].)
- **CAVEMAN SLING AMMO IS UNREACHABLE**: flint/rocks are GEM/ROCK class, but
  THROW's item_classes = 1u<<2 (WEAPON only), so the slot head can never
  select them — gems DROP 9/10 and 10/10, 0 throws. Action-space gap, not a
  learning failure. FIX BUILT 2026-08-15: NH_THROW_GEM flag (ifndef default 0,
  netlib.h) adds 1u<<13 to THROW item_classes; flag-off fingerprint verified
  unchanged 486f55e1. Arm lncg_s401 (obs+gem, 217M seed 401) training.
  RESULT lncg_s401 cert 3,830 vs lnc_s401 4,135 (obs only) vs idb_s401 3,520
  (control), all seed 401/217M: behavior FIXED (flint DROP 9-10/10 → 1/10,
  real THROWs 0 → 4/10, sling WIELD 0-1/10 → 3/10; Ran crossbow WIELD held at
  10/10, Sam yumi 9/10) but SCORE −305 vs obs-only. Sling is weak in NetHack
  and the fix widens THROW for all 13 roles, so the action-space cost may
  exceed the gain — do NOT ship gem-throw on n=1; needs a panel or drop it.
  ANALYSIS GOTCHA: kitanalyze.py filters uses by verb item_classes, so gem
  THROWs are discarded unless LEGAL[11] includes 13 — pre-fix arms DO show
  phantom gem v11 counts (slot-0 fallback + letter shift), so read gem arms
  from the raw ITEM lines.
  CONSISTENCY CHECK that proved the gap: lnc_s401 (launcher obs, no gem fix)
  left Caveman at sling WIELD 1/10 and gems DROP 10/10 — visibility cannot
  fix a capability the action space lacks, while the same arm took Ranger
  crossbow WIELD 1/10→10/10 and Sam yumi 0→9/10 at MATCHED budget.
- Healer's starting WAND (sleep — best early panic button) never zapped in 10
  eps (DROP 3/10); Wizard's wand ZAP 6/10, so wands aren't ignored globally.
- Tourist EXPENSIVE_CAMERA (blinds monsters) APPLY 1/10; second camera 0.
- Body armor dropped not worn: Bar RING_MAIL WEAR 3 DROP 8; Kni RING_MAIL
  WEAR 2, SMALL_SHIELD WEAR 2; Val SMALL_SHIELD WEAR 1. Matches the known
  armor bimodality ([[nethack-armor-bimodality]]).
- Arc PICK_AXE (best depth tool) APPLY 4/10, DROP 8/10.
- Melee weapon used as ammo: Kni throws LONG_SWORD 10/10 AND LANCE 10/10,
  Pri MACE 10/10, Val LONG_SWORD 8/10, Bar 2H sword 7/10 — the THROW slot
  head pools the wielded weapon with real missiles.

**Correct behaviors** (don't "fix"): Monk starts weaponless and never wields
(top scorer 11.5K); Healer potions QUAFF 10/10 + 9/10, stethoscope APPLY
7/10; Ranger cloak (displacement — shown under a shuffled appearance name)
WEAR 9/10; Tourist darts THROW 10/10 (bare is correct); Rogue daggers THROW
10/10 (bare multishot is correct); food EAT 8-9/10 everywhere.

**LANDMINE — inv_glyphs is the APPEARANCE, inv_true is the identity.** The
glyph stays the shuffled appearance even for identified items (Knight's helm
reads appear_ot 80 in one game and 81 in the next, true_ot 78 in both; Wizard
cloak 127/126 vs true 127). Any per-otyp table lookup (AC, damage, weight)
MUST use inv_true (== PAD when unidentified) or it silently returns a
different value for the same item across games. Shuffled groups span real
differences: cloaks AC 0 (dwarvish) / 1 (magic resistance) / 3 (protection),
helms 1-2, boots 1-2. Caught by scratchpad/armprobe.c before training.

**AC-UPGRADE OBS BIT (2026-08-15, arm_s401/402)**: NH_ARMOR_OBS flag; new
baked table nh_obj_ac[] (otyp->base AC, parsed from objects.c which stores
10-ac; verified ring mail 3 / leather 2 / plate 7 / mithril 5). Per-slot bit
written into the RESERVED inv_state byte st[7] (declared rsvd, read into the
kernel's st[] but unused — free layout slot), surfaced as SFEAT 24->25.
Honest gating: candidate and worn comparator both need inv_true set
(== dknown && oc_name_known, same condition as st[6]); spe counted only when
the engine marks it known (-128 sentinel => +0); empty slot => 1. Verified
end-to-end: 0 for worn armor, flips to 1 after a scripted TAKEOFF (slot
empty). ALL roles start with armor WORN, so the bit is 0 at reset for
everyone. Harness gotcha: st[7] is zeros unless randomized, which would make
the new column's FD check vacuous.

**AC-BIT RESULT (arm_s401 cert 3,756 vs control 3,520; s402 killed for CPU
contention, so n=1 on the WEAK seed).** Class-keyed census (10 eps/role,
arm | ctl): armor WEAR Kni 3|4, Bar 0|1, Wiz 2|5, Hea 3|4 — WEAR went DOWN
or flat in all four; TAKEOFF collapsed (Kni 0|3, Wiz 0|6, Hea 1|3). So the
bit did NOT increase wearing; it mostly stopped the wear/take-off churn. On
this evidence the narrow (identified-only) version is a null-to-negative for
armor uptake. Calibration: the provably-inert bok bit scored +425 on this
same seed, so anything under ~+600 on s401 is noise.
**KNOWN WEAKNESS of the tested version** (from the kn flag in objects.c):
armor with a randomized description — ALL helms, cloaks, boots, gloves — is
unidentified when found, so the identified-only gate is dark for exactly the
categories most often picked up; only suits/basic shields (desc None => kn=1)
and the always-identified starting kit are covered. Worse, the EMPTY-SLOT
case needs no identification at all (category is shuffle-invariant and the
worn flags are visible) but was gated behind ID anyway. v2 = split into
"fills an empty slot" (no ID needed) + "beats what's worn" (keep the gate);
most roles start with 3-6 empty slots (Wiz/Hea 6, Kni 3).

**AUTO-WEAR UPPER BOUND — CLOSED, WORTH NOTHING. Pair: awear_s401 3,780 vs
idb_s401 3,520 (+260); awear_s402 3,526 vs idb_s402 3,894 (−368). Mean 3,653
vs 3,707 = −54.** The seed-401 "+260" was the flattering seed (its control is
the panel minimum); on the honest seed the scripted armour ladder LOSES.
Scripted the whole armour ladder (NH_AUTOWEAR in netlib.h, nethack_auto_wear
in nethack.h — must live there, not macros.h, since it calls
nethack_slot_usable): greedy AC using ONLY obs-visible facts (category from
appearance, AC/spe only when identified/known, never known-cursed, empty slot
needs no ID), one action per step, swaps pay TAKEOFF + WEAR at full turn
price, and skips body armour for Hea/Mon/Pri/Wiz (suits cost Monks their
martial-arts AC and tax caster spell success). Wear rate ~11/ep before the
class rule, 7.5 after. VERDICT: perfect, free armour discipline buys +260,
LESS than the provably-inert bok bit's +425 on the same seed — armour is not
where the points are at 217M with ac_coef=0. Retires the armour thread
(no v2 obs bit needed).
**WHY it's worth nothing (scratchpad/acprobe.c, n=25 eps each, macro ON vs
control):** AC 7.1→4.9 with the macro vs 7.1→5.0 without — IDENTICAL. The
macro does wear more (3.1 pieces vs 2.6) and acquisition is unchanged (5.0 vs
5.4 acquired), so the extra pieces it puts on are worth ~0.1 AC. The armour
these policies actually encounter in ~2K-step episodes is low-value: the big
AC is the starting suit (already worn), casters skip suits, and heavy suits
lose to pickup_burden:unencumbered. Ceiling is set by ACQUISITION + episode
length, not by the wearing decision. (An n=8 pilot suggested the macro
SUPPRESSED acquisition 2.8 vs 5.2 — that was noise, overturned at n=25;
don't trust n=8 on this metric.)
**METHOD ERROR to avoid:** I called this arm "25% behind" mid-run by
comparing a LIVE rolling log line to .ini series snapshots — different
statistics. The trajectories were in fact near-identical (awear 844/1898/
2813/3555 vs arm 834/1926/2847/3592). Only compare .ini series to .ini
series, and prefer waiting for the cert.

**Why:** kit misuse splits into three distinct causes — action-space gaps
(sling ammo), invisible synergies (launcher↔ammo, fixed by an obs bit), and
delayed-payoff verbs (books, armor). Each needs a different fix; don't treat
them as one problem.
**How to apply:** rebuild the probe with the demo clang line (build.sh
CLOBBERS SRC_FILE); options string MUST end "...TAIL !status_updates" or the
engine hits config_error_done → tty wait → segv in fill_obs. Ranked next
arms: spellbook READ visibility/gate audit, THROW class widening for
gem/rock, Healer wand. See [[nethack-multi-role]], [[nethack-spell-channel]].
