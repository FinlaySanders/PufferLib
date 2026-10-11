---
name: nethack-death-anatomy
description: Death census verdict — the death plateau is a FOOD CLOCK; fainting-collapse is the real spike mechanism; supply not timing
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-13T19:17:33.749Z
---

Deep death census (2026-07-30, 19,070 deaths, best/median/worst b1-depthrew 1B finals, 400-rollout evals):
- **Food clock**: fainting share of combat deaths by turn: 0.2% (<3k) → 11% → 30% → 36% (>9k). 22.5% of combat deaths are while Fainting (median turn 9,835) and those are **79% spikes** (helpless free hits) — the old "60% spike invariant" was largely hunger collapse. Fed deaths: 51% spike, median turn 5,837. Better checkpoints starve MORE (they live longer). Score rate is saturated ~0.78/turn (1B seeds differ only in lifespan) → **food supply is THE score lever**.
- **Supply, not timing**: fainting deaths hold median 0 food (34% any); fed deaths hold median 11. Pack runs dry; they don't mis-time eating. Prayer already near-max exploited (only 24.5% of fainting deaths had prayer re-armed).
- **Killers**: 20% non-monster (trap/poison); top monsters soldier ant 7.8%, dwarf, Woodland-elf, hill orc, fire ant, rothe — all at dlvl 2-5 (the farm zone). Mumak 79% spike, dwarf 66%. Poison ends 5.5% of episodes (how==2). 8% die blind.
- **Exonerated**: encumbrance (93.5% unencumbered), suit-breaking-martial-arts (0.7%, suit-wearers outscore), multi-turn SEARCH20 commitment (~13% of fatal steps >1 turn). Fatal verbs: MOVE 59%, ELBERETH 17%, QUAFF 8%.
- **Preventability**: 54% pass a visible <30% HP window; 17% die holding a heal potion; ~50% had some out.
- Next levers: renewable food (corpse-eat-on-kill in farm zone), gold→food/protection conversion at shops (buying needs a #pay path — not in action space), poison mitigation. See [[nethack-mechanics-audit]], [[nethack-reward-ab]].
- **Monk-diet resolution**: corpse aversion = vegetarian conduct; meat = "You feel guilty" + adjalign(-1) (eat.c violated_vegetarian), BUT kills refund alignment (adjalign(mtmp->malign), cap 10+turns/200) → meat is effectively FREE at 139 kills/ep; aversion = early-training lock-in, policy can't see the record (obs has ualign.type only — record hidden, human-parity). Diet log: rations 5.1/ep (eaten before hungry), lichen 0.89, desperation meat 0.38 guilt/ep. Funnel while hungry: 11.85 safe kills → 1.77 stepped-on → ~1.2 eaten (routing gap, not eat-refusal).
- **starve_coef A/B (2026-07-30, group starvepen1): NULL** — per-step penalty at hunger>=Weak (0.02), 5 seeds: 6029±268 vs 6114±90; floor_eats/spike/prayers flat, gt slightly down (mild death-as-penalty-exit risk). Shaping alone can't crack the diet lock-in; starve_coef stays 0.0 (code kept, ini default 0.0). Existing hunger_coef is a transition potential (~0.13/slide, policy-invariant, toothless by design).
- Obs fairness audit (2026-07-30): CLEAN — shuffled_glyph remaps object glyphs to appearance (fixes vanilla NLE identity leak) on map+inv paths; inv_state is doname-parity gated; extra[0] "engraving state" is dead (engine zeroes internal[6], stale comment).

Census infra (reusable): v3 per-death CSV via NETHACK_DEATH_CENSUS env (schema in scratchpad census_an3.py; killer mnum/mlev, last-valid blstats, suit/heals/food inv scan, since_pray, 8-obs hp ring). **GOTCHA: engine tears down blstats at death — read them post-step ONLY when TIME>0, snapshot into stats.last_* fields.** 3×400-rollout evals = ~7 min total. mon_names.txt (381 names) in scratchpad.


2026-08-01 CHAMPION FOOD ECONOMY (8302 carry ckpt, 12-ep corpse-census via
fixed CPU demo): starvation SOLVED (<1% of deaths). Diet: food ration 52%,
lichen corpse 15% (the never-rots/no-poison learnable-first pick), rothe 8%,
tripe/cram/lembas ~10%, opportunistic one-off corpses 15%; 8 guilt events
per ~26K turns. Cadence: median meal gap 673 turns (~12 meals/9K-turn
life); 96/107 meals eaten at NOT-HUNGRY (proactive top-up; only 3 at Weak);
prayers_starving ~6/ep = backstop not staple. Kills ~180/ep = corpse
surplus; autopickup (% class) banks rations while sweeping. Per-episode
food-vs-score analysis (374 eps, 4 ckpts): eats-per-turn r = -0.21..+0.02
vs score — food is LOGISTICS not strategy; floor_eats uncorrelated with
policy quality across ckpts (1.82/0.58/0.86/1.45 vs 8644/7956/7875/6684
demo means). Demo means reproduce strict-eval ordering = demo re-certified
as forensic instrument post-softmax-fix.
2026-08-01: census CSV writers (DEATH_CENSUS / ROUTE_LOG / CORPSE_CENSUS /
DEBUG_ACT env-var blocks) STRIPPED from the 5c-nethack-r2 tree for the
upstream commit, along with support fields (prev2_action, last_dt,
last_pray_turn, last_dnum..last_score Stats snapshot). Dashboard metrics
KEPT (death_hp_t1/t5, death_spike/attrition, death_hunger, hp_hist ring,
floors). Strip verified bit-identical (2M smoke 25.828 pre and post).
To resurrect census: full pre-strip file at scratchpad
bank/nethack_h_with_census.h (this session) or the 4.0 branch.
2026-08-01 later: dashboard metrics ALSO stripped from r2 commit tree per
user (hp_hist ring, death_hp_t1/t5, death_hunger, death_spike/attrition) —
kept death set = upstream original (combat/starved/smited/other, mon_level,
adj_monsters, maxhp). All strips verified bit-identical (2M smoke 25.828).

**2026-08-13 DEATH CENSUS, new-base record ckpts (cap100k s305/s307, 3K eps
each, NH_INV_CENSUS extended: how_done + killer_mlev + pre-death snapshot).**
Causes: combat 83-85%%, POISON 10.5-11%% (2nd cause! likely corpse diet /
poison attacks — killer species unrecoverable, death-step message torn down),
petrified 2.8-3.5%% (trice), god's-wrath how=100 0.2-1.6%%, starved-proper
only 0.4-1.2%%. Food clock TRANSFORMED not gone: 20-26%% of combat deaths
happen while FAINTING (hunger=4) + 5-6%% weak — hunger assists combat kills
instead of starving. NOT overreach: killer mlev mean 3.1-3.3 vs own xp 7.4-
7.6, only 6-7%% killed by >=own-level — chip death by trash mobs while
fainting/swarmed. 37-42%% died from >=1/3 HP within ONE step (spike damage /
poison). Combat-death depth peaks d4-5 (s305) / spreads to d9 (s307 diver-
lean). Levers by size: fainting-combat (~25%% of deaths), poison (~11%%),
petrify (~3%%). Census hook uncommitted (./puffer_census binary).

**DEEP CENSUS round 2 (E/F event lines: eat outcomes + faint onsets +
food-in-pack).** (1) FAINTING = GREED NOT SUPPLY (reverses old "supply not
timing" for new gen): 64%%/49%% of fainting-combat deaths held food IN PACK
(79%%/57%% of faint ONSETS held food) — policy eats 20/ep with textbook
hunger discipline (40K eats at hungry vs 265 at ok, 0 satiated) but keeps
farming through weak→faint while provisioned; faints are individually
survivable so PG underprices the death tail (delayed-cost class). (2) SLOT
WALL DOES NOT KILL: items>=48 deaths have LOWER faint rate (24%%/8%%), MORE
food (3.9-5.1), score 15-16K — full pack = success correlate, cost is missed
pickups only. (3) EATING DISCIPLINE NEAR-PERFECT: 2-4 poisonous-eat events
in 117K meals — poison deaths (~11%%) are poison ATTACKS (stings/soldier
ants at killer_mlev~3), NOT diet; remaining unknown = whether it eats
resistance-granting corpses enough (invisible to msg census). Zero-turn eat
aborts 14-20%% of eat presses. Candidate lever (user call): the ~25%%
fainting-combat class — eat-at-weak is learnable-but-unlearned; masking
SEARCH20 at hunger>=weak would be the paternal shortcut.

**MECHANISM FOUND (round 3): CAPACITY-BLOCKED EATING death spiral.** At
fainting, the policy DOES try to eat (4,345 attempts s305) but 78-90%% are
refused zero-turn with "You can't do that while carrying so much stuff" =
eat.c check_capacity: hunger Weak/Fainting drains Str -> carry capacity
shrinks -> same pack becomes Overtaxed -> engine BLOCKS eating -> faint
helpless -> killed by trash. Food IS edible (rations/fruit/tins; tins = 46%%
of diet, mean eat tau 2.7-3.0); the ACTION is blocked. Recovery = DROP
items first, then eat — two-step never learned. All inputs ARE visible:
hunger state 3 vs 4 distinct through per-blstat normalization, encumbrance
margin obs shipped (#152) — pure unlearned credit chain, no blind spot.
Beware zero-turn eat "aborts" at weak: mostly Monk-speed FREE successful
eats ("Core dumped." = apple pun msg) — true refusals are the carrying-
stuff class. Candidate fixes (user call): EAT legality mask when capacity-
blocked (free-probe principle, removes waste only) vs learnable-first
drop-then-eat vs nothing.

**INTERVENTION TRILOGY CLOSED 2026-08-13 (s305, certified/census):**
control 10,064 / 25.8%% faint-combat / 64%% with-food -> +EAT-capacity-mask
9,042 (−1,022) / 17.1%% / 36%% -> +st[7] weight obs (NH_SFEAT 25, era fork)
9,892 (−172 = NULL) / 22.5%% / 43%%. VERDICT: the fainting class is a PRICED
RISK, not a blind spot — masking forces safer eat-timing and costs ~1K
score; adding weight info lets the policy re-optimize BACK toward the risky
profile and recovers score to parity while fainting rate drifts back up.
Terminal mechanism refined: 94%% of with-food faint deaths were NOT
capacity-locked at death (locks are upstream/transient; the killer is
fainting helplessness + eat-occupation interruption). No score lever here
at 217M; family SHELVED (mask+weight not enthroned, era fork discarded);
census infra + anatomy = the durable win. Weight-obs implementation notes
if revived: winrl st[7]=min(127,owt/4) w/ loadstone apparent-weight gating,
encoder f[24]=st7/127 strictly [0,1], shapes all symbolic via NH_SFEAT,
16x25 numel%%8 OK; liveness signature = census W lines (mean ~64).

**2026-08-23 NH_LAB-era census (16K deaths, vec epdump extended w/ killer
mnum/mlev/hp/hunger/depth/killer-string; nethack_lab_ep binary)**: combat
69%, RAYS 10% (wand+bolts+missile), poison 6-7% (bees/orcish arrows/
rotted corpses 2.4%), wrath 2%, starve-direct 1.7%, stoning 1.1%, traps
1%. Combat strat: 37% at Weak+ hunger (food clock kills THROUGH combat),
55-60% below 30% HP, killers >hero level only 7-13% => ATTRITION SPIRAL
not overmatch; >50% of combat deaths at depth 1-3; Barbarian longest-
lived. Top killers: iron piercer #1 (533), trash mobs (hobgoblin/rats/
jackals ~1.5K), ants/bees, rays ~1.6K, Archon/gargoyle/golem deep-run
enders. Levers ranked: disengagement economics (retreat/rest/eat-before-
Weak), then hazard-bits+intrinsics+ray-exposure (~20% class). Corrected:
rotten-corpse poisoning real (2.4%), probe-5 dilution artifact.

**2026-08-23 CORRECTION (engine-name landmine)**: earlier species
attributions used a monst.c REGEX-ordered name table that is MISALIGNED
vs engine mons[] (drift 2-4, varies along file; red mold=159 not 163,
lurker=97, floating eye=28). TRUE top killers (engine names, 16K census):
rothe #1 (234/299), hill orc, wererat, soldier ant, giant bat, dwarf,
werejackal — ORDINARY MELEE ATTRITION MOBS, not molds/piercers.
Hazard-class killers = 12% of monster deaths (~8% of all; mostly
poison-bit ants/bees). Broad causes/strata (how-codes) unaffected.
RULE: species ids must map through engine truth (nle_mon_name /
generated tables), never source-regex order.

2026-09-07 13:30 t742 KILLER CENSUS (second cert sample, mean 11182/median 7388, 10K games; dump now also carries internal[9] mnum+1, internal[10] mlvl and the killer string via nle_killer_name, C linkage decl next to nle_identity): killed 86% (6303 by monsters, 2290 non-monster), poisoned 10%. No dominant killer: hill orc 4.2%, rothe 3.8%, soldier ant 3.5%, wererat/werejackal 4.4% combined, giant bat, Woodland-elf, giant ant, VAULT GUARD 160 (1.9% of kills, mlvl 12, 17K-score games). RAYS = 14% of all games: bolt of fire 316, lightning 302, cold 284, "wand" (explosion) 294, magic missile 135, death ray 89 at depth ~3, healthy (fainting 1%), xp 8 -> sudden deaths, source (own bounced zap vs monster wand) not attributable from the killer string; agent zaps 2/game. HUNGER (CORRECTED: blstats hunger scale is 0 satiated,1 not hungry,2 hungry,3 weak,4 fainting; NETHACK_HUNGER_WEAK=3): deaths by hunger state = not hungry 56%, hungry 16%, weak 7%, FAINTING 18%, satiated 3%. Monster kills: 23% while fainting, 7% weak; trivial monsters concentrate there (jackal 41% fainting, giant ant 39%, pony 27%, giant bat 23%, rothe 22%). God's wrath deaths: 56% weak + 28% fainting = praying-for-food too often. Poisoned by: rotted glob of gray ooze 21%, orcish arrows 12%, rotted corpses (floor_eats 55/game), killer bees. Stoned 118 = cockatrice/chickatrice. Wrath 137: The Lady (Tourist), Tyr (Valkyrie), Mars/Venus (Ranger). Starved 114. Levers: hunger management (eat before Weak), stop eating rotted corpses/globs, vault guard avoidance, ray safety.

2026-09-07 14:05 FOOD-AT-DEATH + LAST-VERB (4th cert sample, mean 11284; dump fields 53-55 = food items, corpses, last verb): starved (116) carry 2.5 food items on average but BIMODAL: 54% have none at all, the rest hold 1-18 items and still starve (only 0.9 corpses, so mostly non-corpse food they do not eat: tins/eggs? open). Fainting deaths (1921): 52% have no food; weak deaths 20% none; not-hungry deaths carry 8.5 items. Starved games eat 72x/game (39 floor eats) and pray 15x: food strategy = floor corpses + prayer. LAST VERB before death: all deaths moves 26%, ENGRAVES 19% (Elbereth panic), runs 10%, search20 10%, prayers 8%, quaffs 8%. RAY/WAND deaths (1392): last verb search20 24%, moves 24%, runs 12%, zaps NOT in top 6 -> rays are MONSTER wands (Mines gnomes/dwarves, soldiers) hitting a resting agent, not self-bounced zaps. Starved last verb: runs 28%, search20 22%, drops 20%. Cert samples so far: 11310, 11182, 11187, 11284 (trainer 11304/11157/11187/11259) -> ~11.2K +-60 SE.
