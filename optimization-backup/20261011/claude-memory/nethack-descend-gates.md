---
name: nethack-descend-gates
description: "Descent-gate family closed 2026-08-06: strict dlvl-1/xp-8 bank is SURVIVAL-limited (not time/spell/nutrition) — 3 certified refutations; zone bank 1-4/xp7 = 6784/depth 4.88/maxhp 41.8, the live branch"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-06T17:21:58.125Z
---

Autoascend-style descent gating (mask DOWN until xp threshold), all certified
10K-episode evals, 250M, champion+ac stack. Knobs: bank_floor/bank_xp in env
(generalized from the old descend_gate==8 special); mask_cast; max_episode_steps.

**Strict dlvl-1/xp-8 = dead, survival-limited. Three refutations:**
- aa_s301 (casts, 10K cap): 3678 / depth 1.54 / xp 6.34. Siege pathology:
  15.5K game turns, 2200 protection casts/ep burning ~10 nutrition each
  (non-wizard hunger cost = 2x energy; stacked-protection AC caps so the spam
  bought NOTHING), prayers_fed 10.4, death_weak 0.46, 25% truncated.
- aanc_s301 (no casts, killed 72M): xp pace IDENTICAL to cast arm -> not
  nutrition-limited.
- aanc2_s301 (no casts, 100K cap): 3444 / depth 1.24, episodes FREE to run
  100K steps yet still die at ~5.5K steps / 16K turns (combat 0.69 x weak
  0.64, killer mon_level 1.3). Not time-limited.
=> The bank needs ~320 exp from the dlvl-1 spawn trickle; every death resets
it; the policy can't survive dlvl 1 long enough. Autoascend wins via scripted
never-die play (Elbereth/retreat/prayer discipline) + uncapped episodes
(confirmed in its global_logic.py: BE_ON_FIRST_LEVEL until xlvl >= 8), NOT
via any signal RL currently lacks. Do not revisit strict banking without a
survival breakthrough.

**Zone bank dlvl 1-4 / xp 7 (zb_s301) = the live branch: 6784 / depth 4.88 /
min_ac -2.35 / maxhp 41.8** (vs ~6900-7000 champion+ac at 250M — approx
score-neutral). Bank FILLS (training xp 7.05; upper-Mines spawn density +
corpse food economy; death_starved 0.010). Strongest certified character ever
at 250M (maxhp 41.8 vs ~30; min_ac mostly protection-spell transient — armor
alone ~+1, see epscore memory for the ac decomposition). Post-unlock the
policy hovers at dlvl 4-5 (reach_d10 0.025): gates manufacture strength but
nothing converts it to depth — same lesson as the old parity gate
(alive-but-shallow 7.03/5702). SUPERSEDED BY fsc: fractional scout ALONE (scout_ready=1.0, NO bank, from
scratch) certified 7170.4 / depth 6.16 / min_ac -2.41 / deep_mines 0.136 =
ALL-TIME 250M RECORD (beats rcminf best-of-8 7123) at full champion depth —
both worlds from the soft pacing, no mask. zbf replicate s302 6790 showed
bank+fraction is just bank-limited (zbf mean 6907±117 ≈ zb). Anneal zba
(warm-start zbf, bank lifted, 100M): 6426/5.94 but score still climbing at
cutoff, maxhp 45.9 record — gate is removable scaffolding, but fsc shows you
may not need the scaffold at all. fsc = the new default platform; single seed,
needs replicate + 1B.

**CHALLENGE-RATIO EXP (2026-08-07, xrfc = exp_rel 0.8/floor 0.5 replacing linear
exp on CURRENT champion env):** certified 3,625/3,693 (seeds 304/307 — spread 69
vs controls' 874: strongest variance compressor ever measured; deletes the
farm-basin lottery). Depth bell 8 (d10+ 30%, max 22), AC@d10 −4.5, min_ac −4.39
= campaign-best AC. vs class predecessor xrf_s301 (same reward, pre-AC-delta env,
2,682/bell-10): modern env +977 score, +3 AC at every depth, −1.5 depth. Frontier
3-point read: champ (6.4, 7,345) / xrfc (8.1, 3,659) / xrf (9.6, 2,682) —
−1,840/level on the champ-xrfc leg vs −670/level xrfc-xrf ⇒ explore MILDER doses
(exp_rel 0.3-0.5, floor ~0.3) or #125 gated composition. At matched d10-12:
champ episodes 12,100 vs xrfc 5,335 (survivorship caveat). Depth ledger context:
diver-class evals show champion has ZERO episodes past d15 in 10K; divers reach
Medusa's doorstep (d24 max, plain combat deaths, no stoning past d18).

**2026-08-14 DIVE-11 via box sweep (warwick-dcs/nethackiseasytohack4, 384
runs, metric=max_depth)**: winner 0306 promoted into ocean/nethack/depth.ini
(full recipe + max_depth sweep ranges; floor_coef reward implemented in tree,
gated, gate-inert at 0). Our re-run on the challenge stack (depth306_s73,
366M, seed 73) CERTIFIED 10.96 mean depth / 10K eps — near-exact behavioral
clone of box 0306 (score 2710 vs 2774, searches 94 vs 92, mines floors 3.9
vs 3.8, death_ac +2.85 identical). Route: stairs + Minetown dip (~4 mines
floors, floor_coef-funded) + ~3.4 levels skipped via falls; single-turn
SEARCH heavy (90-180/ep, s20+RUN masked); min_ac contaminated by protection
casts — use death_ac (gap corr casts +0.46). SWEEP RANGES PINNED at edges:
descent_coef=1 (max), exp_coef=0.01 (min), gold_coef=0.001 (min),
death_penalty=0 (max), horizon=512 (max), agents=512 (max) — widen box
ranges (descent to ~4, exp/gold to ~0, horizon 1024) for the next round.
Depth-recipe multi_role arm untested (pickaxe roles should out-dive Monk).
**Route model CORRECTED via NH_TRACE demo hook (105 traced eps, depth306_s73)**:
trapdoor-skip theory WRONG — falls 0.15/ep. Bimodal by entrance luck: 63% find
the mines branch on dlvl 2-4, dive mines to med dlvl 8 (abs ~10-11) and DIE
there (only 4/66 return); 37% never find it and stair-sprint main at ~22
turns/level (tail to main dlvl 26, zero mines). Mines preferred because open
caves = no search-jams; main has hidden-corridor stalls (1.6 floors/ep >150
turns, where the ~92 searches/ep concentrate). The 10.96 certified mean =
the mines-bottom death wall (~abs 11), not a descent-speed limit — levers:
survive deeper mines (armor) or bias to main-sprint mode. NH_TRACE lives in
the demo auto loop (uncommitted, env-gated).
**Pickaxe confirmed**: depth Monk applies 15/ep, 95% = glyph 2140 PICK_AXE
(dig-down; APPLY macro auto-answers '>' for otyp 234/50). Mines mode = kill
dwarves -> PICKUP pick -> dig; a second convergent digger after multi-Arc.
Backtracking works (2 up-moves/ep, entrance hunting) — it just never climbs
OUT of mines: death_penalty~0 makes die-and-reset cheaper than a paid-nothing
climb (the pinned death_penalty=0 CREATES no-return diving).
**Demo consolidated 2026-08-14 (uncommitted)**: ONE composite renderer
(reference layout: 18-row msg log, map box, boxed status, full-height
categorized inventory; ~127x50 term) for interactive AND auto modes; env vars
NH_TTY=1 (map panel = real game screen), NH_MULTI=1, NH_TRACE=1, NH_SEED,
NH_WEIGHTS. nethack_tty side binary + wt_tty worktree RETIRED. puf_render
stays the minimal committed hook. Gate PASS after tty-sink re-add.
Demo weights (2026-08-14): resources/nethack/nethack_score_weights.bin =
multi1b_s305 (default; pair with NH_MULTI=1), nethack_depth_weights.bin =
depth306_s73; NH_WEIGHTS accepts "score"/"depth" shorthands or a path. Old
nethack_weights.bin (v3fbc_s702, pre-challenge layout) git-rm'd — incompatible
with the +20-extras binary.
