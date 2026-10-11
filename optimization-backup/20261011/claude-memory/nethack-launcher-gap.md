---
name: nethack-launcher-gap
description: "NOT A GAP after all: the champion refuses launchers because a wielded bow is a 1d4 club and it fights adjacent. Fix worked, cost Rangers 1,685 pts at 1B"
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-15T22:20:30.506Z
---

2026-08-15, user-spotted (watched Ranger throwing arrows). Engine mechanic:
throwing ammo WITH matching launcher wielded = firing (multishot + skill
bonuses, "You shoot"); without = weak improvised toss. Census instrument
(scratchpad-style side build on eps-dump): at THROW decode, classify thrown
otyp as ammo (arrows 1-4/ya 5→any bow 65-68, bolt 6→crossbow 70, flint
445/rock 446→sling 69) and scan inv_state st[5]&2 (W_WEP) for the launcher.
Validated on how=100 truncation rows (live snapshots; death rows tear down):
Sam=katana(39), Val=long sword(37), Wiz=quarterstaff(61) — canonical start
weapons, sensor proven. Result on embed champion s311: **0 launched /
28,764 bare** across all 13 roles; Ranger wields DAGGER(17), throws 85
ammo/ep bare (Sam 44). First instrument attempt (topline strncmp "You
shoot/throw") was WRONG — the THROW macro's final message is the outcome
line; classify at action layer, not messages.

**Action-space PROOF (scripted probe, scratchpad/shootprobe.c)**: WIELD head 8
selects the launcher, THROW head 3 + dir fires — fresh gnomish Ranger (starts
DAGGER wielded, crossbow+bolts in pack; race varies the kit, bow-wielded-at-
start was wrong): bare throw = 1 bolt "misses Sirius"; after WIELD crossbow
("+1 crossbow (weapon in hand)") the same THROW = "You shoot 3 crossbow
bolts" — 3x multishot at basic skill, first try. Mechanism fully available;
policy is pure status-quo (never discovers the one WIELD step). Gotchas:
nethack_verb_wield TOGGLES (re-selecting wielded item unwields via '-');
build.sh line ~106 sets SRC_FILE="" so SRC_FILE env is CLOBBERED — compile
probes manually with the demo clang line (see probe header) + sed the
multi splice role for forced-role envs.

**Why:** WIELD-launcher is a delayed-payoff verb (immediate melee downgrade,
diffuse later throw gains) = same absorbing-state class as the bimodal
verbs; and the obs gives no visibility of the ammo↔launcher synergy.
**Masking ruled out as cause (code audit)**: WIELD masks only known-cursed
weld; THROW verb/slots/dirs identical in both wield states — no rejection
loop exists. The punishment is MELEE (launcher in hand = 1d4 no-skill
bashing in the dominant combat mode) + the wield toggle + all-1 dir
fallback wasting ammo. Per-slot wielded bit IS in the obs (st[5] flags in
SFEAT); only the ammo↔launcher RELATION is invisible.
**How to apply:** fix arm BUILT 2026-08-15 (NH_LAUNCH_OBS, ifndef default 0
in netlib.h + nethack.cu — sed BOTH for side builds): 3 bl features at
NH_F_LAUNCH (wielding-launcher / matching-ammo-in-pack / unwielded-matching-
launcher-exists), extras 77→80 at NETHACK_EXTRA_LAUNCH, env fill in
pack_obs, demo mirrored, harness NH_TEST_LAUNCH=1. Flag-off fingerprint
UNCHANGED 486f55e1 (inert); gradcheck 3 arms PASS. A/B lnc_s401-405 ×217M
running vs idb_s401-405 panel (3,756). On win: flip default + rerun
shoot-census for launched>0.

**Sling coverage VERIFIED end-to-end** (scratchpad/gemprobe.c, 8 Caveman
resets): flint/rock come through inv_glyphs as TRUE otyps 445/446 (gray-stone
appearance shuffling does NOT hit them, unlike cloaks — Wizard's MR cloak
reads as CLOAK_OF_DISPLACEMENT), so ammo_match fires; bits read wl=0 ammo=0
avail=1 at start and wl=1 ammo=1 avail=0 after WIELD sling, exactly as
designed; with NH_THROW_GEM the gem slot's THROW mask entry = 1. Caveman kit
is race-invariant: club 59, sling 69, flint 445, rock 446, leather 113.
KNOWN IMPRECISION (fix before any full panel): engine is_ammo accepts ALL of
GEM_CLASS (objects.c GEM() macro sets oc_skill -P_SLING for every gem), so
diamonds/glass are legal sling ammo; nethack_ammo_match only maps otyp
445/446 → sling, so gems picked up later (Mines are full of them) don't light
the ready bit, while the class-based THROW mask DOES let them be thrown.
One-liner: match gem oclass 13 for launcher 69 instead of the two otyps.

**FIRST RESULT (2026-08-15, n=1 of 5)**: lnc_s401 cert **4,135** vs paired
control idb_s401 3,520 (+615, above ALL 5 control seeds; panel best 3,897).
Behavior FIXED — paired CPU rollout, Ranger-forced env, seed 123, 8 eps,
same probe (scratchpad/rollprobe.c, build with role:Ranger sed + matching
NH_LAUNCH_OBS): lnc_s401 = 1,092 launched / 274 bare (80% fired), 41
launcher wields; champion s311 = **0 launched / 908 bare, 0 launcher
wields** (28 other wields — it wields, never a launcher). Visibility alone
flipped it, no masks/macros/rewards. Watch it: side demo built with
NH_LAUNCH_OBS=1 + role:Ranger → `NH_MULTI=1 NH_WEIGHTS=<lnc ckpt>
./nethack_ranger` (ckpt float count 3,958,432 = champion + 1,728 = bl_w 64*3
+ proj 512*3; bl feats ride the concat, so BOTH grow). Training stays FULL
multi-role (multi_role=1 in run ini); role-forcing is side-build only. Obs change = ABI bump
(old checkpoints keep loading only if layout preserved — see silent-shift
landmine in [[nethack-env-setup]]). Ranged-kit rates: Ran 8.2 throws/1Kt,
Tou 24 (darts, correctly bare), Rog daggers fine bare. Expected value:
Ranger/Samurai ranged damage ~3x when fired (multishot + skill).
See [[nethack-bimodal-verbs]], [[nethack-multi-role]].

**1B RESULT — behaviour holds, score does NOT. lnc1b_s311 cert 6,869 vs the
seed-matched record idemb1b_s311 7,035 = −166.** Same seed, same budget, same
config; only the three launcher bits differ (plus a patch-kernel rewrite
verified bit-identical at default flags). Archery SURVIVED at scale: forced-
Ranger rollout gives 1,413 launched / 294 bare (83%) and 21 launcher wields
vs 26 other, versus the record's 0 launched / 908 bare / 0 launcher wields.
Rolling trajectories were interleaved throughout (deltas swinging +1,070 to
−582 at adjacent checkpoints, while the record itself jumped 4,955→7,069
between 700M and 800M).
**MECHANISM (user spotted the AC gap):** at 1B the arm is a LATERAL TRADE, not
a failure. Final metrics record vs arm — min_ac 3.47 vs 4.08, death_ac 5.38 vs
5.97, wears/ep 11.78 vs 8.95 (−24%, gap WIDENS through training), max_depth
4.06 vs 3.82, episode_length 2154 vs 2143 (identical). Same action budget, so
steps spent wielding+firing are steps not spent wearing or descending. It
buys archery and funds it from armour+depth tempo — and armour was separately
proven worth ~nothing today (auto-wear upper bound −54), so the net is ~0.
Implication: the binding constraint is neither archery nor armour but whatever
consumes the productive share of the ~2,150 steps.
**And the 217M gain was a SMALL-BUDGET artefact**: +615/+73 at 217M, −166 at
1B. Same shape as the 2B budget result — differences that look real at low
budget wash out once the mixture finds stronger scoring lines. Archery is
genuinely fixed and genuinely worth nothing at the scale we ship at.
**Decision: do NOT commit the arm on score.** Keep scratchpad/launcher_obs.patch
if the ranged-damage behaviour is ever wanted for its own sake (e.g. a
diving/survival objective where per-hit damage matters more than farm tempo).


**PER-ROLE DECOMPOSITION KILLS THE THREAD (8K-ep censuses, record vs arm).**
Tested the hypothesis "archery is positive but masked by the worse-armour
basin" — it predicts launcher roles UP, others DOWN. Reality is the reverse:
launcher-kit roles Ran/Sam/Cav average **−874** vs **−412** for the other ten,
and RANGER — the role that went 0% → 83% launcher use — is the single worst
role in the game at **−1,685** (6,951 → 5,266). Sam −881. Overall census mean
6,794 → 6,308.
**So the "gap" was never a gap.** A wielded bow is a 1d4 no-skill club, and
this policy's kills come from ADJACENT combat (the 9x9 crop is its detailed
view). Wielding launchers makes it worse at what it actually does; 3-arrow
volleys plus ammo retrieval don't pay for flailing in melee. The champion's
refusal to wield a launcher is CORRECT PLAY for a melee-farming strategy that
1B steps of training discovered. The 217M "+615" was a weak-melee regime
artefact.
**EVAL-TIME ABLATION (the settling test, 2026-08-15).** NH_NOLAUNCH_WIELD
(ifndef guard in nethack.h slot mask: WIELD illegal for otyp 65-70) run on the
ARM'S OWN 1B weights, 8K eps. Instrument is clean — the ten non-launcher roles
move **+5±125** (mask provably inert where it should be); overall 6,243 ->
5,858; launcher roles 6,902 -> 5,545 (−1,357±220): Ran −4,569, Cav −236, Sam
−174.
**Archery IS load-bearing inside the arm, and the arm is STILL worse.** The
arm's Ranger reorganised its whole play around the launcher — remove it and the
policy is out of distribution and collapses to 697 (dies at xp 3.3 / dlvl 1.9
vs 6.9 / 3.66, turns 15.0K -> 6.5K, wears 8.8 -> 2.4). That collapse is NOT a
measurement of archery's worth; it is a policy deprived of its main line. The
real comparison stands: archery Ranger 5,266 vs the record's melee Ranger
6,951, with 6K fewer turns, worse AC (4.19 vs 3.29), half the wears and 2x the
throws (350.9 vs 170.5). It converted survival tempo into shooting.
**Verdict on "archery recovered score lost to a worse armour basin"**: NO —
launcher roles are the worst-hit, not the best. There IS a general basin loss
across the other ten (mean −412, worst Rog −1,229 / Kni −971) but archery
needed to offset it and instead added to it. Unattributable (same seed, but
different binary = different trajectory; no paired control for basin).
**BUILD LANDMINE — the first ablation census was GARBAGE and looked like a
result.** puffer_abl was built with NH_LAUNCH_OBS effectively off, so the arm's
checkpoint (15,833,728 B = record 15,826,816 + 1,728 floats for bl_w 64*3 +
proj) loaded SHIFTED past bl_w — no error, just degenerate play (score ~5 all
13 roles, engraves 907/ep, runs 739, max_depth 1.007, starved 4,120/8,003).
Cause: NH_LAUNCH_OBS passed via env/CFLAGS, which build.sh clobbers
(EXTRA_CFLAGS=() line 104, SRC_FILE="" line ~106). **Rule: sed the #define in
BOTH netlib.h and nethack.cu, and ALWAYS build the flag-OFF control binary and
census it first — it must reproduce the banked number (6,243 vs banked 6,308)
before any ablation number is believed.** See silent-shift in
[[nethack-env-setup]].
**SEED-401 CORRECTION (2026-08-15 night, user pushback earned it):** every
"single-seed" arm result of the day was paired against idb_s401 = 3,520, the
PANEL MINIMUM (mean 3,756, SD 155) — a free ~+236. Re-measured vs the panel
mean: lnc +379/+211 (n=2), bok +189 (n=1, the PROVABLY INERT book bit = the
empirical null of "add a feature, retrain"), lncg gems +74, arm AC bit +1,
ihid32 −118, p1x32 −189/+264. So gem throw was NOT −305 (that was lncg_s401 −
lnc_s401, two single seeds) and the AC bit was not +237. All unresolved. Night
queue (scratchpad/night_queue.sh, priority queue with readiness, control =
idb_s401-405): lnc s403-405 · gem2 (launcher + gem throw with the oclass-13
sling-ammo fix at both pack_obs call sites) ·5 · film ·5 · emb48 ·5 · loc384
·5 · bl128 ·5 · acx s402-405 · bok s402-405 (5-seed NULL calibration) · p1x32
s403-405 (existing puffer_p1x32w has the smem fixes) · invhid32 ·5 (NH_INV_HID
32 with NH_SPKEY decoupled to 16 + nh_spq_bwd zeroes the unused query dims —
the original ihid32 silently widened spell keys too). gem2's control is the
lnc panel, not idb. Whatever clears at 217M needs a 1B pair (launcher flipped
sign between budgets). Two-panel SE(diff) ≈ 98 → nothing under ±200 resolves.
**Why:** NetHack theory ("Rangers should shoot") assumed a ranged playstyle
the agent doesn't have and shouldn't adopt at this scoring horizon.
**How to apply:** before "fixing" a behaviour that looks wrong by domain
theory, check whether the theory's premise (here: fighting at range) matches
what the policy actually does. And decompose per-role — the aggregate −166
looked like noise and hid a −1,685 on the affected role. Armour was NOT the
explanation: partial corr(score, min_ac | episode_length) = −0.17 at n=21
across the 217M family, i.e. armour is mostly a PROXY for surviving longer.

**GAP BROKEN 2026-08-23**: NH_LAB 1B policies FIRE — fireprobe census
(engine-truth ammo_and_launcher vs uwep): s702 lineages fire 782 (full) /
586 (noaux) per 100K steps, ~all Ranger + Samurai trickle; firing Rangers
stop hand-throwing (36/6 bare vs 554/735) and wield bow 8-10% of frames.
s701 lineages of BOTH arms: 0 fires, 1-2 wield frames — seed-bimodal
basin (PG absorbing state), NOT aux-dependent; the arch made the basin
reachable. Score-neutral at 1B (Ranger = 1/13 of eps). Tool:
tools/interp/fireprobe.c + nle_throw_kind() in vendor nle.c.

**2026-08-24 CLOSED for Ranger in v5 (v51b_s701 30K-ep census, engine-truth
counters)**: Ranger fires 168/ep (100% of episodes, 90.3% of its ammo
launcher-propelled vs champion-era 0/28,764) — the wield readout +
lnc_ready conjunction (NH_INV2) did its job. It wields the bow 93.1% of
steps, melee weapon 0.5% -> emergent PURE-ARCHER build (point-blank fire +
221 dagger throws/ep), mean 7,177 med 6,238 (highest med/mean ratio of any
role = most consistent). Wield-ammo blunder near-extinct everywhere
(<=1.7%). Monk 98.6% bare = correct martial arts; Tourist dart-spam
correct. REMAINING GAP: SAMURAI hand-throws its arrows (52.8/ep, 4.1%
fire eff.) with katana wielded 87% — never learned wield-swap-to-fire;
arguably rational (katana melee) but arrows wasted. Kit telemetry now
env-side: Stats fires/ammo_hand/nonammo_throws/wield_steps[5] + epdump
cols 22-30 (gated NH_EPDUMP); vendor helpers nle_wield_class +
nle_throw_fire_kind (read-only); eval binary nethack_v5ce3 (atan2+V5+
all dumps).

**2026-08-26 MATCHLAB (scratchpad matchlab.py): lnc_ready predicted REMOVABLE at capacity
level.** Synthetic pointer lab mirroring production (wld gate -> query MLP -> qnorm dot over
16d keys): matched-ammo selection from static rule-table features (per-slot skill category,
is-launcher/is-ammo) with NO ready/match bit = 1.000 accuracy (3-seed median; chance .06).
rules-noemb arm (identity zeroed) = 1.000 on UNSEEN type-ids too -> the mechanism learns the
rule itself. With embeds available it takes the pair-memorization shortcut (novel-id .151) —
fine for fixed tables, classic shortcut learning. bit-only novel-id failures were untrained-
embed-noise artifacts. Per user's learnable-first-obs rule: keep per-slot rule-table features
(legit basic info), drop derived conjunctions; remaining step = paired RL ablation (drop
lnc_ready, keep wld + skill features) — exploration is the other variable, verb-eps did that
work historically.

**2026-08-26 SOURCE-VERIFIED CORRECTION (user pushback, twice earned): the champion V5 obs has
NO launcher bits.** winrl.cc inv_state flags byte = worn/wield/swap/quiver/poison/grease/
erodeproof ONLY; nle_lnc_bits/nle_throw_kind/nle_wield_class are LAB-CENSUS helpers (the
slot_class/slot_flags/si filler feeds lab dumps, no env consumer). NH_LAUNCH_OBS bits arm was
never committed. So the v5 archer learned bow↔ammo from RAW IDENTITY + wielded flag through
wld gate + content-keyed pointer — the "lnc_ready conjunction" phrase in the 08-24 entry means
the NETWORK's learned conjunction, not an obs bit (phrasing misled two later readings; write
mechanisms, not shorthand). Learnable-first validated at 1B: no ablation needed, there is
nothing to ablate. matchlab identity-shortcut (0.997) = the actual mechanism for fixed tables.
