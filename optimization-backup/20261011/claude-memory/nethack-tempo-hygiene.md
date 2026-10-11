---
name: nethack-tempo-hygiene
description: "Tempo = the within-family score lottery (valid_moves r=.58, throws .67); NH_WASTELOG census found hunger-refusal spam loops (CAST 5.6M steps, EAT 1M); legality masks shipped (CAST@uhunger<=10, EAT@no-floor-food via nle_food_underfoot)"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-13T16:36:13.229Z
---

**The within-family (config-fixed) score lottery is a TEMPO lottery** (n=100,
21 cohorts): max_xp .90, game_time .89, throws .67, eats .65, valid_moves .58,
wears .41 — while utility-verb richness is ~0 (pickups .06, applies -.03,
zaps .13). Lucky seeds fight more, waste fewer steps, live longer. Effective-
turn rate (valid_moves/episode_length) ordered the fraction family exactly:
80.6%/75.3%/61.0% -> 7170/6274/6737-certified.

**NH_WASTELOG census** (env var; per-episode per-verb zero-clock-step counts +
1/97 message samples; permanent infra in nethack_add_log/puf_step): waste =
17.8-36.9%% of ALL steps. Composition: universal MOVE/RUN-into-walls (~1.5M
steps/policy, phase-2: dir-mask); DROP menu-aborts ("Never mind."); and the
big one, HUNGER-REFUSAL SPAM LOOPS in unlucky basins: fscfix_s302 spent 5.6M
steps (72%% of its waste, 27%% of its LIFE) on "You are too hungry to cast
that spell"; fscfix_s301 1M steps on "You don't have anything to eat" (EAT was
floor-legal on ANY object incl. its own drops).

**Masks shipped 2026-08-06 21:3x** (goldens 34/34, no-globals, gradcheck OK):
- CAST masked when internal[7] (raw u.uhunger) <= 10 — exact spell.c:953 gate.
- EAT floor-legality now requires actual food in the pile: new engine accessor
  nle_food_underfoot() (walks level.objs at u.ux/u.uy for FOOD_CLASS; corpses
  included), replacing the any-object test.
Validation arm: fh_s304, group fschyg, fraction config.

**Score-config depth ledger** (the user asked "which experiment got a score
config deepest" — answer: NONE beat plain champion): rcminf_s214 7123 @ 6.51
depth / 0.167 deep_mines is the deepest score-config point at 250M; every
depth intervention was parity-or-worse at its score level; only BUDGET moves
both (1B: 8086 @ 6.37). The 6.5 wall is unbroken above ~5K score.

**Fraction family CLOSED at n=4**: 7170/6530 (old env) + 6274/6737 (fixed) =
mean ~6.7K +-400, env fix neutral (paired eval transfer 7149 vs 7170 cert).
7170 was the lottery (4th best-of-N mirage caught 2026-08-06). REPLICATED
value: depth 5.9-6.35 + deep_mines 0.10-0.14 in all 4 draws at champion-level
score — but note champion's own best (rcminf) matches even that. Fraction =
default platform mainly because it certifies consistently, not because it
dominates.

**Feature-liveness audit 2026-08-06 (NH_FEATAUDIT, wt_audit, 16M steps over
fh_s304 eval): CLEAN.** 57/67 scalar sources vary. The 10 constants are all
benign: 6 invcnt dims for classes a Monk never carries (RANDOM/ILLOBJ/ROCK/
BALL/CHAIN/VENOM — dead by rarity, trimmable someday), in_yn/in_getlin zero
by design (prompts auto-answered pre-pack), internal[11-12] unused fork
padding (not policy-visible anyway — only blstats+extra reach the obs).
Elbereth ward bit CONFIRMED live end-to-end post-fix. The dead-sensor class
is closed: no other wired-but-dead policy inputs exist. Quirk filed: misc[]
prompt flags retain mid-macro values (internal[] twins don't); not
policy-visible. Audit hook lives in wt_audit pack_obs; re-run after any obs
change.

**Hidden-state leak audit (prayer cooldown), 2026-08-06: CLEAN.** u.ublesscnt
is exported at internal[5] (fork debug export) but NEVER consumed: not packed
(obs = glyphs+blstats+extra+inv+msg only), no PRAY mask (masking on it would
leak via the action-mask input). DO-NOT-PACK slot: internal[5]. Leak-safety
principle for masks: only mirror engine responses obtainable for FREE by
attempting (too-hungry cast, no-food eat, cant-reach engrave, quoted prices);
never mask on state whose probe has a cost (prayer anger, unidentified BUC).

**VALIDATED 2026-08-06 22:22 — hunger masks = first upward lottery compressor.
fh_s305 certified 7225 = ALL-TIME 250M RECORD** (beats rcminf best-of-8 7123);
fh pair 7144/7225 (mean 7185+-40) vs unmasked-fixed trio 6274/6737/6354 (mean
6455+-140): +730, ZERO overlap, ranks 1&3 of the 7-run family. fh_s305 also
min_ac -2.61 (deepest ever) + deep_mines 0.150. USER'S HYPOTHESIS CONFIRMED
in-family: early-window (8-30M) valid-rate orders final score 5/6 monotone
(62.2->6416 ... 75.3->7523 tail); masks raise the EARLY tempo floor, which is
where the basin gets seeded (rhymes with the 20M SEARCH-thrash 6/6 predictor).
Population-level early r=0.09 only — the effect is stack-local, measure
in-family. fh config (fraction + hunger masks) = NEW DEFAULT PLATFORM; next
decision: 1B on it. GOTCHA #7 (process): kill-after-sentinel RACED the chain
loop by 9s -> orphan fscfix_s303 trained concurrently (GPU contention slows
wall-clock, results unaffected; orphan certified 6354 as free 3rd control).
Kill chains BEFORE their sentinel window or use a pre-loop guard file.

**2026-08-07 round-3 masks + A/B verdicts.** Abort trace (NH_ABORTLOG in
item_use) found: DROP aborts = 100%% gold ($ skipped by the bracket parser;
policy exploited drop-gold as a no-op refuge 23/game) -> COIN removed from
DROP classes (0x3EFFF). WEAR aborts = cursed-slot hammering -> layering +
known-cursed-swap mask (aborts -83%%, residue = intended unknown-curse free
probes). Successful drops are FREE actions in NetHack (burden management, not
waste) — census "waste" must mean zero-clock AND no state change.
Empty-msg movement waste = vault-GUARD escort deadlock (PM_GUARD 80%% of
monster-target bumps) + Mines peaceful bumping (110K auto-declined "Really
attack" per 1.5K games) + RUN instant-stops. Peaceful-move + diagonal-doorway
masks SHIPPED (matched-seed 250M A/B: mvon 6774 vs mvoff 6513 = +260 TRAINING
value despite -260 eval-transfer dip on old ckpts — transfer cost != training
cost, direction confirmed). RUN-adjacent mask REVERTED (harmful -716: RUN
away from adjacent = FLEEING, a real behavior; instant-stops were a subset).
Trice/stoning CLOSED: probe negative (-342/-282, step-mask RAISES stoning:
policy already handles live trices, hazard = trice touch-attacks + gloveless
edges; corpse autopickup exonerated — ">corpse" exception is LIVE via POSIX
regex unanchored match). Vault gold: policy could never drop gold (parser),
so guard always turns hostile eventually; hostile-guard fights are legitimate
and murder-free — no kill-switch needed, deadlock fix = peaceful mask.
**s502 411M EVENT: seed-unique ENTROPY COLLAPSE + ESCAPE** (entropy 0.30->
0.047, ~2M steps untrained-level play, fast recovery; no KL/NaN; siblings
clean; verb_eps floor = likely rescuer). Watch loss/entropy live in cohorts;
non-recovering collapse = the floor-killer risk for all-seeds-above-8K.
drop_value 126K spikes = stash-churn double-count artifact (free drops +
autopickup regrab recount full stack value; log-only, reward-inert).
Env FINAL for cohort rerun: hunger x2, engrave-sites, gold-drop, cursed-wear
layering, peaceful-move, diagonal-doorway. fh1b partial cohort (old env):
7672/8748/7810/7780, s502=all-time record, depth wall 6.5 holds at 1B.

**CONSOLIDATED STOCKTAKE 2026-08-07 ~11:00.**
Matched-seed env ledger (n=3 per cell): sensor-era 6455 -> +hunger masks 6981
(+526, the one consistently positive subset) -> +round2/3 6754 (-227+-260 vs
+260 in the controlled sub-A/B = NEUTRAL; "upward lottery compressor" claim
DEMOTED to hypothesis after fhv2_s304 drew 6454 on the masked env, breaking
the fh-pair separation). Masks are mechanically perfect + score-free; the
distributional claims (wears-rate->100%, floor lift, spread compression) need
the n=10 cohort. All 6 hygiene-env draws ARE wearers (8-11/ep) vs historical
0.16-16 span — user's void-gradient-poisoning theory of ARMOR BIMODALITY
(WEAR was 60% free aborts -> verb-head gradient mostly noise -> coin-flip
adoption; gating/eps were partial symptom treatments) accumulating support.
CAST verdict pair: execution value -593 (s502 probe: masking cast on the
trained caster), acquisition tax +239 (mc_s306 7013 vs mvon_s306 6774, CAST
masked from birth, matched seed; also = armor-only reward test, min_ac 0.66
pure armor). CASTLOG@1B: s502 casts like an expert — 94%% protection, median
cast at 100%% HP, re-cast cadence 224 turns (decay-tracking; castf@250M was
2-turn spam), Pw-surplus-gated, depth-scaled (peak dlvl 4-6). Casting skill
MATURES with budget; the 250M tax cannot price the 1B payoff — cohort keeps
CAST (or hedged split) pending user call.
ARMOR REWARD REDESIGN (user-driven, pending): monotone-best is front-run by
protection (spell spends the episode AC budget -> armor pays zero after),
duration-blind, sparse. Plan: armor-only (uspellprot export) DELTA form +
per-term conservation ledger (accrue account, bounded symmetric payout,
losses persist -> both chosen (armor churn) and stochastic (decay) clamp
arbitrage die; churn = strictly negative). Build as matched arm vs monotone.
Env-forensics one-liners: policy could NEVER drop gold in project history
($ missing from bracket parser); dropping = free action (burden mgmt is legit,
census waste must be zero-clock AND no-state-change); drop_value spikes =
stash-churn double-count (log-only); vault-guard escort deadlock was the #1
empty-move sink (PM_GUARD 80%%); verb stats count ATTEMPTS not successes
project-wide; misc[] retains mid-macro prompt flags (quirk, filed).

**MONK-FAST CLOCK PHYSICS 2026-08-13 (NH_TAU_DUMP forensics, commit
2ee2a492).** The Monk (Agent-mon-hum-neu-mal) is intrinsically Fast (speed 16
vs 12-pt action cost) -> EXACTLY 25%% of elementary actions consume ZERO
game-turns (free bonus actions: uniform across verbs 24.5-26.4%%, uniform
across episode deciles, empty message, healthy HP, incl. free KILLS). tau0
histogram bucket = mostly this FEATURE, not waste; mean tau of every 1-turn
verb = 0.75-0.79, SEARCH20 mean tau = 12.25 (20 actions x0.75 minus
interruptions; only 0.8%% fully voided). Macro policies HIDE free actions
inside macros; elementary-only policies expose them as tau0 steps — never
read tau0 deltas across policies as waste deltas. True zero-turn waste is
~1.5-3%% of steps (RUN wall-bumps 13.2%% of RUNs = top channel, MOVE stone
bumps, air kicks, peaceful declines). Death-stall / prompt-thrash hypotheses
REFUTED (no terminal clustering, WEAR aborts 2.6%%). Rolling training-mode
verb stats (eps+sampling) overstate eval behavior ~3x (wears 220 rolling vs
80 certified-eval, real tau 1.65 armor churn ~6%% of game time in the
nomacro diver). Tool: NH_TAU_DUMP=prefix -> per-env files, Z lines (verb,
slot, step, hp, hpmax, depth, msg) for tau<=0, A (verb,tau) else, D eplen;
analyzer scratchpad/tau_autopsy.py. TAU CODE REMOVED FROM TREE 2026-08-13
per user (histogram + dump both); recover from reflog commits 909e9877 /
2ee2a492 / 5de37dc2 (unpushed, orphaned by reset) or re-derive from here.

**RUN-adjacency census (corrected) 2026-08-07:** RUN void rates by context:
free 10.2%%, ADJACENT-AIMED-AWAY 58.8%% (flight WORKS 41%% -> the verb-level
mask's -716 = confirmed flight amputation; away-void is probabilistic =
UNMASKABLE, ~27 void steps/game accepted), aimed-at-hostile ~100%% (directional
RUN-head mask SHIPPED, validated 8233~=control, removes ~47 presses/game).
CENSUS PLACEMENT GOTCHA: blstats refresh happens at nle_obs_refresh AFTER
nethack_execute — any counter reading TIME before the refresh sees stale
clocks (invalidated the first 70K/70K read; 2nd placement bug of the day
after the STONELOG how==0-branch anchor). RULE: every new counter must pass a
sanity invariant (e.g., free-state rates must be plausible) before belief;
put step-outcome counters at the valid_moves site, never before refresh.

**AC-DELTA LEDGER VALIDATED 2026-08-07 14:20 (user-designed reward, replaces
monotone min-ac).** Form: account += ac_coef*(prev_ac - ac); payout
clamp(account, +-ac_coef)/step, remainder carries; spells INCLUDED (cycles
self-cancel under conservation -> no armor-only carve-out needed). Trio
(seeds 304/305/306, final env, group acdelta): 7345 (new all-time 250M
record) / 6984 / 7246 = MEAN 7192 +-108, TIGHTEST 3-seed cell ever (range
361), vs same-env monotone cell 6754 (+438) and hunger-cell 6981 (+211).
Depth cell record too: 6.40/6.66/6.58 (all >=6.4; masked-env monotone sat
5.9-6.4). Mechanisms clean: pump ratio r_clip/r_raw ~0.79 (arbitrage would
be >>1; old pump 8x), casting alive ~15-21/ep (protection persists on pure
survival value), takeoffs ~0, throws UP (34.5 = family best; throws_rate
+0.53 = top behavioral rate per the normalized correlation table; raw new
table: xp .89, game_time .88, throws .68, eats .65, valid .61, depth -.46).
AMMO CENSUS: supply loop healthy (up 99.6 vs down 73.2/ep, ratio 1.36, end
stock 26.5; 17% dry-tail) -> throw-rate is engagement choice, not scarcity.
SPELL-DRAW LOTTERY: protection-start episodes +700-850 over sleep/healing
(both 1B seeds, edge universal — NOT the weak-seed differentiator; weak s501
= flat -800 all buckets = its waste). "none" bucket = >20K-turn spell-
retention expiry = elite-tail marker (5%, mean ~21K). Sleep = 74% fail for
Monk (rationally shelved); healing usable-but-unused (crisis timing never
learned); DETECT MONSTERS (learned from books) cast 97% below-half-HP =
emergent crisis behavior — crisis-conditioning IS learnable when payoff is
VISIBLE (map fills next step); healing's payoff is not. Slot-'a' tyranny:
CAST only reaches first spell; July had a spell-pointer head — restore as
future action-space item + multi-spell obs. VARIANCE ARCHAEOLOGY: matched
twins identical to 60M, diverge 60-175M — variance is mid-training-made
(fork experiment vetoed by user).
