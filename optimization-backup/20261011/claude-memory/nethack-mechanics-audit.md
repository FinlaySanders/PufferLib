---
name: nethack-mechanics-audit
description: "Wiki audit of missing Monk mechanics: death-score = gold+kills+depth ONLY (items=0); ranked ladder — autopickup =\"(*, sell-in-shop yn, zap down, #offer, BUC-drop, engrave-ID, protection racket, #tip"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-03T14:02:40.391Z
---

Full NetHack-wiki audit (2026-07-28, agent-fetched via Wayback; page caches in
session scratchpad). Key facts for the campaign:

**DEATH-SCORE MODEL (Score page):** on death only: 4x exp per kill + 0.9/zm
gold (Monk starts 0) + 50 x (deepest DL - 1) + 10 per use-identified
wand/potion/scroll. CARRIED ITEMS = 0. Strategy triangle: loot->gold (sell),
gold->AC (protection racket), AC->depth (dive). Gems sell 300-4500zm.
Codehappy 35K-game data: +1 early AC ~ +4% long-run survival.

**CORRECTIONS:** unicorn horn is TOOL class (`(`) — our APPLY already admits
it; blocker is autopickup only. `#tip` dumps containers with NO menu — the
menu-head is NOT required for chests/bag-of-holding.

**RANKED LADDER (value x prompt-complexity):**
1. autopickup add `= " ( *` (config only; loadstone caveat on `*`) → unihorn
   apply, ring wear (free action=anti-paralysis, slow digestion=halves food),
   sellable gems
2. sell-in-shop: drop in shop → "Sell it for N gold? [ynq]" → auto-y (ONE
   prompt; top score lever)
3. zap `>`/`<` (wand of digging descent; score is depth-starved)
4. #offer corpse-on-altar yn path; HARD MASKS: never human corpse (smite,
   wipes purchased protection), never former-pet, never own-align unicorn;
   gate cockatrice handling on gloves. Value: prayer-timeout reset -12.5x
   sac value; neutral gift pool incl Magicbane; repairs luck/alignment
5. altar-drop BUC (zero new actions; needs flash msg observable)
6. engrave-ID: E → wand letter → ESC macro; +10 score each; IDs zap-worthy
7. protection racket: #chat → getlin "400*XL" at Minetown priest (reach 50%);
   1st donation 2-4 permanent AC, +1 each to 9; donate at LOW XL (cost 400xXL);
   god-smite wipes it (interacts with sacrifice masks)
8. #tip containers + kick locks (keys/lockpicks are tools → apply admits)
9. Sokoban curriculum (reach 3%, should be early-game default: 1 ring + 1 wand
   + 4 food/level, prize BoH or AoR 50/50; diagonal moves never push boulders =
   safe; luck penalty on boulder-breaking)
10. later: #dip-to-uncurse (4/30), magic fountains at luck>=4

**SKIP for Monk:** #force (needs wield), travel, Oracle consult (costs gold =
net-negative score), #sit/#invoke/#twoweapon/#turn, fountain quaffing ("leading
cause of death" — inability is a safety feature), Excalibur (neutral).
WIELD/body-armor stay legal-but-refused (no-class-pruning doctrine ✓ policy
already correctly refuses).

**Cross-cutting:** Monk intrinsics by XL (poison-res@3, stealth@5, warning@7,
autosearch@9); vegetarian: -1 align per meat (gates sacrifice gifts/prayer;
repairable via sacrifice); satiation drains Wis (Monk cast stat); KICK on
altar/fountain = luck/HP trap (cheap mask); polymorph traps DL7+ destroy robe
(unreplaceable) — top kit hazard in our band; pray on co-aligned altar =
enhanced (free synergy).

Economy-patch candidate (post spell-retrial): items 1+2+3 in one env change +
5-seed A/B on the eps stack. Then 4-7 individually.

**ECONOMY TELEMETRY MEASURED (2026-08-03, puffer_sell probe binary, 10K-ep certified evals on rcmin_s208/rcbase_s209/rcmin_s210; ALL scores bit-exact vs certified ⇒ counters behavior-neutral).** New stats in tree: sells, sale_gold, drop_value, trouble_frac, prayers_fed, altar_steps, altar_seen, wear_blind, cursed_worn_frac; + generated `nh_obj_cost[453]` table in netlib.h (gen_obj_cost.c pattern = gen_obj_armcat; NOTE fast-nle migrated globals ⇒ generator MUST call nh_ctx_new() first or objects[] segvs).
- **SELLING ALREADY WORKS, unnoticed**: deliberate drop in a shop raises the shk's ynaq offer, which renders "[ynaq]" ⊃ "[yn", so handle_prompts' auto-commit answers y. Rate 0.01–0.12 sells/ep, ~27–29 gold each (≈half base cost, confirms shk offer ≈ oc_cost/2).
- **THE PRIZE IS THE DISCARD STREAM: drop_value 1095–2014 zm base/ep** (≈550–1000 gold sellable) vs net gold only ~140/ep — the agent discards 5–7× more value than it collects. Shk purse 1000+30*rnd(100) = 1030–4000 (shknam.c:674) does NOT bind. With 0.35 Minetown reach ⇒ ~300 gold ≈ **270 score expected**, best case 700–900. Blocker = ROUTING (carry loot to shop), not price/purse/supply.
- **ALTARS: exposure dead, but BUC NEED IS REAL.** altar_steps 0.18–0.21/ep, altar_seen 0.23–0.29 (walks past them). Sacrifice is pointless: trouble_frac (Weak+ hunger or hp≤maxhp/7) only 0.010–0.020 and prayers_fed 4.9–6.2/ep ⇒ prayer supply already meets demand (CAVEAT: average hides the right tail — top decile dies 33% fainting). BUT **wear_blind = 92–95% of all WEAR presses** (BUC unknown at decision time) and **cursed_worn_frac 0.069–0.130**. This CORRECTS the 2026-07 ALTAR_ID null ("use-ID saturates knowledge" measured END-of-episode BUC 0.93-0.95 — the wrong timestamp; at decision time the agent is blind). Delivery is the blocker: BUC of unID'd items is hidden state, so altar/pet/holy-water are the only honest mechanisms (never leak — user-endorsed) and altar occupancy caps it at ~1 bulk-ID per 4 episodes ≈ 50–100 score.
- **ROUTING CLAIM REFUTED (2026-08-03, origcfg): SHOP SELLING IS LEARNABLE.** Reproduced the maintainer's original config (commit 5d508154: gold_coef=1, exp 0.0223, descent 4.57, ac 1.0, ent 0.0193, verb_eps 0, async=1, 256 agents, lr 0.00176/γ0.9935/horizon512, 12-term reward) on puffer_orig (HEAD reward + telemetry), 250M, n=2 certified: **sells 7.10/4.67 per ep, sale_gold 213/158, ~32 gold/sale, max_depth 10.0, score 2717**. vs champion sells 0.11 / gold 3.1 / depth 6.5 / score 6380. ⇒ **~50× selling with NO verb/mask/macro — priced highly enough the policy learns the whole acquire→carry→walk-to-Minetown→drop chain.** My "routing is a horizon problem, unreachable by coefficients" claim was WRONG; the 0.1/ep base rate really was a seed and it amplified. COST: it dives and dies (game_time 2568 vs 8200) so score halves — but that config's sweep metric was **max_depth, NOT score** (git 5d508154 [sweep] metric=max_depth), so it was succeeding at its own objective. gold_coef=1 also explains ac_coef=1.0: under a depth objective survival IS the objective.
- **CORPSE-FARM EXPLOIT SURFACE (user-raised, not yet triggered):** CORPSE oc_cost=5 ⇒ shk offers ~2 gold; only hard refusals are oeaten/offer==0. At gold_coef=1 the [−1,1] clamp pays a 2-gold sale the SAME +1 as a 200-gold sale ⇒ value ordering destroyed, many tiny sales strictly optimal. Saturation threshold ≈ gold_coef 0.033 for a typical 30-gold sale (champion 0.0217 sits just under — probably not coincidence). Swept range [0.001,1.0] spends most of its log-space ABOVE it. **DETECTOR: sale_gold/sells ratio** — ~30 = real merchandise (both origcfg seeds clean), single digits = corpse farm. Check on every sweep winner.
- **BUY PATH SHIPPED (2026-08-03).** Before: PICKUP was legal in shops (creating a bill) but NO pay verb existed (PRAY is meta-p, not plain 'p') ⇒ the action space granted the harmful half of buying only — a debt the agent structurally could not clear. Fix = engine accessor `nle_shop_price(nle_ctx_t*)` (−1 off shop goods, else quoted price; uses PUBLIC `get_cost_of_shop_item` — my first cut called `get_cost` which is STATIC_OVL and only linked because the macro expands empty, AND got the return type wrong via implicit decl) + PICKUP masked when price > gold + auto-'p' after an in-shop pickup + `buys` counter. **Trained-ckpt eval: buys 1.03/ep, sells 0.12→0.21 (bought goods become yours, so later drops are real sales), score 7226 vs 7244.** Buying fires 10x more than selling because PICKUP was already a habit — no adoption problem, no new verb.
- **SHOP OBS SHIPPED (obs break, 2026-08-03):** in-shop bit + affordability (gold/price percent, clamped) appended at `extra[NETHACK_EXTRA_SHOP]`/`+1`. obs 4184→**4192**, NH_BL_FEAT 97→**99** (bl_w 64x99=6336, %8 OK), concat→707. **GRADCHECK PASS.** New 2M canary = **7.425**. LANDMINE (cost a full-file gradcheck failure): the layout is duplicated in THREE places — netlib.h `NETHACK_EXTRA_INTS`, nethack.cu `NH_EX_RAW`, and tests/test_nethack_encoder.py (which ALSO had a hardcoded `f = np.zeros((B, 97))`, now `lib.nh_bl_feat()`). Miss `NH_EX_RAW` and every offset after extra shifts 8 bytes ⇒ ALL torch checks fail, not just the new ones.
- **TILE-OCCLUSION LANDMINE (user-caught 2026-08-03, class of bug not a one-off).** `underfoot_glyphs` (winrl.cc:446) sets the hero tile to `vobj_at()` -> **the TOP OBJECT replaces the terrain glyph**, and the policy sees only that one glyph — no pile count, no contents, only a transient "There are several objects here" in the message. Consequences found: (1) **masks that inferred terrain from the map glyph were wrong** — an object lying on a downstair hid the stair and MASKED DOWN OFF, stranding the agent on a littered staircase (same for UP, and the new ALTAR_ID). autopickup `$[%!)/` clears most tiles but NOT scrolls/rings/amulets/tools/gems/spellbooks, and `pickup_burden:unencumbered` stops autopickup entirely once Burdened. FIX: `nle_terrain_underfoot()` = `back_to_glyph(u.ux,u.uy)`, ignores objects; DOWN/UP/ALTAR_ID now key on terrain. (Historical note: an old "DOWN legal if object underfoot" leniency was the WRONG fix — it made DOWN legal everywhere and the policy no-op'd.) (2) **shop affordability priced only the top item** while PICKUP takes the WHOLE pile (select-all) -> billable > approved -> straight back into the debt trap. FIX: sum `get_cost_of_shop_item` over the `nexthere` chain, skipping COIN_CLASS. **LESSON: never infer tile state from the map glyph; ask the engine.** ALTAR_ID verb re-added (verb 22, NUM_ACTIONS 23, dec_od 731, bl_feat 100, gradcheck PASS, canary 5.974) — drops every unknown-BUC unworn non-gold item then pile-grabs; user's call, rationale = masked-to-altar so it cannot hurt (D' proved idle heads free) and armour is already implicitly priced (+600-680 causal) so the critic can see BUC value without a shaping term.
- **SYNTHESIS: shops and altars both fail on ROUTING**, a long-horizon (multi-thousand-step) plan toward a remembered map feature — invisible at γ=0.99737 (~380-step horizon) and unreachable by verbs/masks/head-level ε. Third independent argument for sweeping gamma. Altar SELL/BUY verbs NOT built (correctly): the measurement was the cheaper experiment.

**PICKUP1 RESULT (2026-07-28, group pickup1, 4 completed seeds + 1 killed):**
widened autopickup ALONE (="(* added) = **HARMFUL: mean 5560 vs control 6115
(-550)**. Supply worked (puton_opportunity 25%, end_gems ~3/ep) but conversion
never emerged: sells 0.00 ALL seeds (shop-drop routing not discovered),
ring_worn_frac 0.000 terminal (blind unID'd ring-wearing correctly priced
negative: certain hunger drain, invisible benefits, cursed-weld risk),
unihorn never encountered. Costs of supply-without-conversion: inventory
channel junk (encoder noise/slot distractors), ε-floor force-wearing cursed
rings mid-training, curated manual pickups displaced. **LAW: build conversion
mechanisms (altar-BUC ID, shop routing) BEFORE widening intake.** Reverted to
champion stack (committed + coef fields only, BUILD_OK). Economy ladder
re-ordered: altar-BUC first (zero new actions), then shop routing, then
re-widen pickup.
