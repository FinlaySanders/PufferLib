---
name: nethack-env-setup
description: "NetHack env state — 14 verbs x 7 MultiDiscrete heads (per-verb slot heads, dir head, REST 20s macro), obs v3 3616B (full grid + underfoot + inv entities), det oracle 1bd8681f267da6f6; reward shaping history; vendored NLE quirks; demo infers arch"
metadata: 
  node_type: memory
  type: project
  originSessionId: 606daed2-1cb2-4460-b763-dedb01d708ec
---

NetHack env rewritten opinionated 2026-07-05 (uncommitted, `nethack` branch): nethack.h ~430 lines + nethack_fs.h (114, vardir plumbing), ZERO preprocessor conditionals. Fixed contract: obs = 990 bytes (21x21 glyph crop int16 + 27 blstats int32, unchanged — encoder compatible); actions = 19 (16 moves + > + < + kick ^D, added 2026-07-06 for locked doors). Kick raises "In what direction?" — that prompt is left live (pass-through check at top of nethack_handle_prompts, MUST precede yn auto-answer since getdir goes through yn_function), so the agent's next movement key answers it: kick-through-door is a learnable two-step sequence.

Bugs fixed (all probe-verified, scratchpad death_probe.c pattern):
1. Death-step score clawback: NLE zeroes blstats on done, so reward included score_coef*(0 - prev_score) at every death — shaping now skipped entirely on the terminal step.
2. Dungeon escape via auto-'y': agent spawns on dlvl-1 upstairs; '<' triggers "Beware, there will be no return! Still climb?" (do.c:1140) which auto-'y' confirmed → ESCAPED (how_done=14) ended ~75% of random episodes, many at step 1. Now declined via message check "no return". Random episode length went 1-1581 → 633-1920.
3. Scout yo-yo farm: visited bitmap used to clear on every level change; now per-depth bitmaps (64 levels) cleared once per episode.

Notes: no eat action — starvation (~turn 1000-2000) is the natural episode cap; re-adding actions = edit NETHACK_ACTION_TABLE (+ retrain, head size changes). chars/message always bound to side buffers (tools/prompt heuristic) but not in obs tensor. Truncation at 10K steps reported as terminal (vecenv has no truncation channel). how_done enum in vendor/nle/src/include/hack.h:137 (0=DIED, 3=STARVING, 14=ESCAPED).

2026-07-06 update: 500M-step run of the swept config plateaued at depth ~4.1 (2x steps bought ~nothing → structural ceiling, not undertraining). Added action 19 = 's' search (live_view.c table was stale-18 and got synced) and death-reason logs (death_combat/death_starved/death_other/truncated fractions per episode; how_done read on done, sentinel -2 set at reset since only really_done() sets it). Search WORKED: depth ~4.5 at only 80M steps. Death mix trained: 95% combat.

2026-07-06 reward rework (with user, design debated): (1) descent bonus now pays ONLY on new episode-max depth (old per-transition form was yo-yo farmable: down-up-down re-earned; may be why sweep drove descent_coef to 0.025). Max form = potential-based, never taxes retreat, neutral on Sokoban's upward branch. (2) hp_coef: HP POTENTIAL (simple delta, symmetric — heals repay damage; user rejected asymmetric loss-only and gamma-correction as unnecessary), death step cashes out -hp_coef*prev_hp on top of death_penalty (dying at high HP forfeits more). Default 0, sweep log_normal 5e-4..0.1. Rationale: dense precursor of combat deaths (95%); death_penalty carries the preference, potential densifies it. (3) max_depth logged per episode (depth-at-death under-reports; consider sweep metric = max_depth). Verified: bench sum_reward bit-identical at hp_coef=0. (4) Behavioral metrics added: prayers, prayers_low_hp (at <=25% maxHP — the learned-panic-button signal; ratio computed downstream), searches, damage_taken, game_time (turns, not steps), max_xp_level. A 'prayed' episodes-fraction metric was added then REMOVED as redundant with the count (user: fewer, orthogonal metrics). Random-policy baselines: prayers 4.1/ep, prayers_low_hp 0.05, searches 5.1/ep, damage 5.5, game_time 84.

2026-07-06 later: added action 20 = pray (0x80|'p', NETHACK_NUM_ACTIONS=21) + death_penalty coef (terminal step of game-over carries death_penalty instead of 0; truncation still 0; config -0.5, sweep uniform -3..0; gamma sweep block added logit_normal 0.95-0.9995 — old 0.985 = ~68-step credit horizon was flagged too short). Pray's yn confirm ("to pray" message check) is exempted from illegal_penalty in nethack_handle_prompts — without that every pray was penalized. Probe-verified: pray consumes ~3 game turns, illegal count unchanged. Random policy now pray-spams → god smite → episodes ~128 steps and death_combat=1.0 early (smites count as DIED); expected, penalty teaches restraint. Demo CAND_A={21,20}: the 20-action checkpoints load, 19 no longer. Remaining levers: eat action (if death_starved grows), downsampled full-map obs channel.

Build quirks (still true): install bison/flex/libbz2-dev; cmake-configure vendor/nle/src/build; `make -C vendor/nle/src/build nethack`; `bash build.sh nethack`. Ignore stale vendor/nle/lib/libnethack.so; real lib+data in vendor/nle/src/build/ (NETHACKDIR=<repo>/vendor/nle/src/build/dat for standalone tools). Full docs in ocean/nethack/README.md.

Demo: `./nethack` plays the trained policy — CPU puffernet port of the custom encoder in nethack.c. Arch (hidden/layers/actions 19-or-18) is INFERRED from checkpoint float count (demo_infer_arch; ambiguity resolved by fewest layers), so any checkpoint dropped into resources/nethack/nethack_weights.bin just works. Demo eval is faithful: brackets training dashboard within ~3%.

Sweep result 2026-07-06 (overnight, metric=depth, 19-action space): top hypers = hidden 128 / 5 layers, lr 3.2e-4, gamma 0.985, replay 3.47 (saved in config/nethack.ini). Retrained 259M steps: score 406.9, depth 3.98, illegal_actions 0.227/ep, valid_moves 70% (was ~50%), SPS 161K (train-bound 55% at this model size). Demo eval of that checkpoint (resources/): 111 eps, avg_score 394, avg_depth 4.07, max dlvl 10, KICK = 4.3% of actions. Previous best score was 211.9 — the env bugfixes + sweep roughly doubled it.

2026-07-08: Minetown diagnosed as the depth-5 wall (peaceful-@ deaths): auto-'y' committed "Really attack?" (sole site uhitm.c:241) -> hostile watch/shopkeepers; obs can't see peaceful flag (not in glyphs, message excluded); no move-without-attack/pay/drop. FIX: "eally attack" yn prompts now ESC'd (nethack.h commit check) — peacefuls unattackable, bump still costs illegal_penalty. Added reach_* area funnel logs (episode_areas bitmask set in nethack_shaped_reward from NLE_BL_DNUM/DLEVEL; dnum: 0 main, 2 mines, 4 soko; minetown = mines lvl>=3, deep_mines = lvl>=5, main_d5 = main depth>=5): flat-float Log protocol makes per-episode 0/1 -> proportions automatically. Demo prints them. Config pinned from big5 sweep run: num_layers=4 (sweep sampled 4.919; bindings.cu int cast truncates), score_coef 0.125, death_penalty -0.385, clip_coef 0.01 (clipfrac ~0.43 is expected), 188.7M steps; weights bin = 4-layer ckpt (old 3-layer incompatible). Result after ESC change: score 1102 (prev ~1050), max_depth 5.48, death_combat 98.4%, starved 1.4% (pray solved hunger); funnel mines 42% -> town band 16.5% -> past 4.7% (was ~0), main_d5 38%, soko 0.2%. Wall is now pure combat attrition at XL~4 vs depth 5-7 (damage 91/ep ~ 3x maxHP). pickup_types trimmed $?!/ -> $ (2026-07-08, probe-verified over 200k random steps: all autopickup msgs '$ - N gold pieces', 0 item pickups, 'You see here a potion' underfoot — shop debt trap gone; scrolls/potions/wands were unusable anyway). Pickup-fix retrain: NO measurable change (score 1043 vs 1102, funnel ratios flat) -> traps weren't binding; wall = combat attrition.

2026-07-08 v1 bundle shipped (ALL checkpoints broken — obs layout + head both changed): actions 22/23 = WEAR 'W' / EAT 'e' via shared nethack_do_use_item (getobj filters candidates per verb; macro answers with RANDOM letter from the prompt bracket via env->rng LCG — first-letter wedges on refused items; EAT declines floor-food "eat it" prompts first, carried food only). PARSER GOTCHA (probe-caught): prompt is "[<letters> or ?*]" (invent.c:1690) — naive space-skip swallows "or" as candidates 'o'/'r' → "You don't have that object." + illegal ESC; space AFTER letters terminates, leading "- " (allownone) skipped. Obs now 1070 bytes: +20 int32 extra segment (ublesscnt cooldown | prev_action (-1 at reset) | 18 per-oclass inv counts; stack=1, worn included — monk starts wearing its 2 armor so W-at-start = clean no-op "anything else to wear", no penalty). Vendored winrl.cc: internal[5] = u.ublesscnt (was dead core-seed slot); inv gate split so binding inv_glyphs/letters/oclasses is ~free (only inv_strs pays doname(); inv_oclasses pads with MAXOCLASSES=18, inv_letters with 0). env binds inv_* side buffers (nethack_bind_obs). NH_BL_FEAT 45→88 (25+7hunger+13cond+1cooldown+24prevact+18counts), concat 1176; both encoder test suites extended + PASS; demo CAND_A collapsed to {24}. wears/eats log = presses that CHOSE an item (not raw presses). Probe results: 28/33 wears dropped AC (one rose — cursed/ill-fitting, accepted), eats work, cooldown 300ish at start & re-rolls on pray. pickup_types now $[%. resources weights bin = 2M-step smoke ckpt (placeholder, needs real retrain).

2026-07-08 xp_coef term added (post-choke-fix retrain still flat: score 1089, max_depth 5.24, death_other fixed at 0.024; demo diagnostic: policy presses WEAR 5.4% of actions / ~69x per ep but only ~1 success/ep — armor is SUPPLY-blocked (dwarf gear sits past the wall at Mines 3+), not usage-blocked; engraves 28.7/ep + searches 60/ep + 2657 turns/ep = survival toolkit used but converts to zero depth; diagnosis: agents descend underleveled at XL~4.2 vs depth 5-7): reward += xp_coef * (XL - episode_max_xp) on new episode-max only, same yo-yo/drain-proof max form as descent, inside nethack_shaped_reward's existing episode_max_xp tracking (pay before update). ini xp_coef=0.5, sweep block log_normal 0.01-3.0. Probe-verified with xp_coef=10: 6/6 real levelups paid exactly, 0 spurious, 0 unpaid; NOTE reset artifact — post-death step reads zeroed blstats so XL looks 0->1, correctly unpaid via max-form. Next lever after this: full re-sweep (hypers stale across 5 structural changes; hidden 64 tiny, gamma 0.992 = 125-step horizon vs 955-step episodes). (first v1 retrain was a DUD: death_other 0.468): ungated EAT = NetHack choke() suicide — eating past Satiated kills (how_done=1 CHOKING → death_other bucket); probe: mash-EAT dies in 12 presses from spawn, random walk w/ EAT every 4th step choked 293/300 eps. FIX 1: satiated gate in c_step — a==23 && blstats[NLE_BL_HUNGER]==0 skips the game step entirely (stepped flag; no nle_step, no handle_prompts → no stale-prompt ESC risk, illegal=0). FIX 2: corpse filter — % autopickup puts corpses in pack where they age (my 'carried food is safe' claim was wrong); pick_candidate drops letters whose inv_glyphs fall in body range [1144, 1144+381) (GLYPH_BODY_OFF/NUMMONS 3.6.6, probe-printed from hack.h); all-corpse candidate list → driver ESCs the prompt itself penalty-free. Post-fix probe: 0 chokes, hist 59 DIED/13 STARVING/3 abnormal over 75 eps (eps now live so long the 400K-step budget ran out — itself the confirmation); random-walk starvation ~17% is correct/expected. Choking dominated so hard that corpse poisoning never registered (0/300) but filter is cheap insurance.

2026-07-08 sweep config restyled to house style (nmmo3/drone pattern): GOTCHA — sweep.py's _params_from_puffer_sweep reads ONLY min/max/scale; `mean` keys in ini sweep blocks are silently IGNORED (norm_mean hardcoded 0 = range midpoint), so center ranges on the believed-good value. total_timesteps now scale=time (= 1/log2(max/min) ≈ 0.3, narrower cost-axis steps); downsample=50 (nmmo3; default 5) = finer Pareto curve bins. Train/policy spaces are INHERITED from default.ini [sweep.*] — nethack sweep automatically includes hidden_size Pow2 [32,1024], num_layers [1,8], lr/gamma/ent/horizon/vtrace/etc + vec.num_buffers — env ini only defines env reward blocks + cost axis. hp_coef floor lowered 0.0005→0.0001 (old sweep pinned AT floor). Style: scale-free magnitudes = log_normal wide; bounded penalties = uniform [min,0]. Verified by dry parse: Hyperparameters(args['sweep']) prints 28-dim space, metric=max_depth goal=maximize. CLAMP-SIZED MAXES, user's WLOG rule adopted: max = 1 (= the clamp) for all unit-per-event terms (exp dlog1p ≤ ~0.7/kill [first-kill tail 3.5], xp dXL 1, descent 1, scout 1 tile; penalties min -1) — coef > 1 is UNREPRESENTABLE (one event already saturates the step), so 1 is the natural bound. EXCEPTION hp_coef max 0.01: its unit is HP (event = 3-65 HP), 1-equivalent ≈ 1/65; max 1 would re-create the score bug (all hits/heals → identical ±1). Co-fire corner (exp+xp both near 1 on levelup kills) is now IN the search space and clips ~40% on those steps — read reward_saturated when interpreting sweep winners. All ini [env] values verified inside ranges.

2026-07-08 REWARD CLAMP DISCOVERY + score removal (xp_coef retrain matched previous run EXACTLY — user guessed clamp, confirmed): pufferlib.cu:1529 hard-clamps per-step rewards to [-1,1] before advantages. Probe (trained policy, 250K steps, old coefs): 100% of levelup steps AND 100% of descent steps saturated; 69.9% of positive reward mass clipped. So xp_coef AND descent_coef were arithmetically invisible (rode on already-saturated kill/descent steps) — several flat runs explained; effective reward was binary +1 per eventful step. Root cause: botl_score() = gold + exp + 50*depth (botl.c:405), so score_coef*delta = NetHack's fixed weights (depth at 50x descent_coef) + heavy tail. FIX: score REMOVED from reward (still logged as perf/score; prev_score kept for logs) → exp_coef * (log1p(exp)-log1p(prev_exp)) via NLE_BL_EXP=19 (dense per-kill, potential phi=log1p(exp), tail-compressed; drain correctly negative); ini exp_coef=0.3, sweep 0.01-3.0; gold deliberately unrewarded (no shop actions). Added reward_saturated log metric (fraction of steps |r|>1, should stay ~0 — climbing = a term is being clipped again). Post-fix probe: 0/536 levelups, 0/623 descents saturated, 0% mass lost. math.h now included in nethack.h. NOTE: episode_return scale dropped ~136 → single digits — vf_coef/value hypers swept under old scale, re-sweep even more due. Dashboard episode_return was always env-side UNCLAMPED (blind to clamp).

2026-07-08 SCORE-EQUIVALENT DECOMPOSED REWARD (user: "match the previous reward that we know worked"; the [train] block deletion — runs inheriting default.ini lr 0.015/clip 0.2/ent 0.001 — was the REAL instability cause, user restored it): botl_score() = gold(net of umoney0, FLOORED at 0) + u.urexp + 50*(deepest-1) [+1000/lvl past 20], and more_experienced does urexp += 4*exper + rexp — so urexp = 4x uexp for kills (rexp-only events: wand/potion/scroll ID +10, unreachable in our action space) and losexp NEVER drops urexp (drain lowers uexp only). Exact match to old score_coef=0.125 run: gold_coef=0.125 (NEW term, tracks start_gold for the net-of-start floor), exp_coef=0.5 LINEAR POSITIVE-PART max(0,duexp) (log1p form removed, math.h dropped), descent_coef=6.304871250090293 (=50*0.125+old 0.054871), xp 0.5, scout/hp/illegal/death = old exact values. match_probe.c (scratchpad): 249804 policy steps, 2 pre-clamp mismatches (rare theft/drain negatives, both clamp to -1 anyway) → POST-CLAMP IDENTICAL signal; 100% descents + 56% exp-gain steps saturate = old regime reproduced, reward_saturated now EXPECTED high (README updated). Sweep: added gold_coef block log_normal [0.001,1], descent max raised to 10. Rebuilt _C.so + ./nethack.

2026-07-08 REWARD SCALE IS NOT A GENTLENESS KNOB (user sanity-tested ÷100-÷10000 coefs → "super unstable"): pufferlib.cu:820 normalizes advantages per minibatch ((adv-mean)/(std+1e-8)) → policy-update magnitude is INVARIANT to reward scale; shrinking rewards only shrinks signal vs noise floors (critic vf-grads scale linearly with reward while lr/vf_coef fixed → critic lags; bf16 storage of rewards/values/advantages → r below the bf16 spacing of V it's added to in r+gammaV'-V), then normalization amplifies the noise to full gradient strength. Also the test's scaling was NON-uniform (exp ÷3000, xp ÷5000, illegal ÷10000 vs others ÷100) = silently different reward function. Well-conditioned regime: eventful steps 0.01-1, returns O(1-10). RETUNED COEFS (probe: 0 saturated steps / 250K, 548 levelups + 607 descents clean): exp 0.3 (kill 0.03-0.2), descent 0.2 (4-lvl trapdoor 0.8), xp 0.3 (levelup kill co-fire 0.51), scout 0.001 (~300-tile level ≈ 1.5 descents; old 0.0047 made scouting 26x descent income), hp 0.003 (10-HP hit ≈ one kill's income; prayer heal 0.195), illegal -0.1, death -0.5; all inside sweep ranges. Real stability test = lower lr, not rewards.

2026-07-08 earlier: Elbereth macro shipped — action 21 ('E' in table, NETHACK_NUM_ACTIONS=22), nethack_do_elbereth in nethack.h: 'E' gated on yn+"write with" (getobj polls via yn_function, invent.c:1691), '-', then FLAG-PRIORITY loop (xwait -> yn "current engraving" answered 'n' (wipe+rewrite) -> getlin chars). CRITICAL GOTCHA probe-verified: after '-', NLE raises xwait --More-- ("You write in the dust...") ALONGSIDE getlin; xwait swallows all keys except space/return, so typing without clearing it first loses the text and the generic cleanup ESCs the getlin ("Never mind."). Dust-typo mechanic: fingertip dust writes degrade probabilistically at WRITE time (got "Elbeyeth" with exact input echo) — monsters only respect legible exact "Elbereth", so duds happen; rewrite path fixes (verified read-back "Elbereth", illegal=0, clock advances). engraves log metric added. live_view table intentionally stays 21 raw keys (macro isn't a key). Demo CAND_A now {22,21}: 21-action ckpts (current weights bin) still load/play; TRAINING head 22 -> fresh runs only. Watch engraves + damage_taken + max_depth next run.

2026-07-10 v2 OBS + DUAL-VIEW ENCODER (user-driven, entity-based-RL blog informed; ALL prior checkpoints broken again): obs now **3506 bytes** = full 79x21 glyph grid int16 (map memory included, straight memcpy of env->glyphs — env-side crop DELETED) | 27 blstats int32 | 20 extra int32. NETHACK_CROP=9 is now a GPU/demo-side view param only; the encoder derives the egocentric crop from blstats x,y (0-based, glyph-aligned). Encoder (src/nethack.cu FULLY REWRITTEN, conv1/conv2/cuDNN/dT-table machinery ALL DELETED): shared embed (5977x32) → local = 9x9 per-cell embeds flattened (2592) → linear 256; global = 8x4-patch embed SUMS over the map (10x6=60 tokens, implicit zero-pad at ragged edges, token position encoded by per-token weight blocks in the flatten-linear 1920→128); concat [loc 256|glb 128|bl_hid 64|bl_feats 88]=536 → proj → hidden. Params 2.2M (was 586K; loc_w 664K dominates). Backward: dE = per-cell 32-dim scatter from BOTH views (nh_dE_scatter_kernel, tok_mode flag; NH_HOT_T=16 smem rows, 4KB — no opt-in needed), hist runs over grid+crop glyphs, fxp rows-convert trow=32. Weight reg order (demo must match): embed, loc_w/b, glb_w/b, bl_w/b, proj_w/b. Gradcheck 9/9 PASS. **RESULT @5M steps seed 42: score 130.4 vs 10.5 conv baseline (12x), episode_length 3210 vs 538, entropy 2.05 vs 3.10, demo presses DOWN_STAIRS and hits dlvl 2 immediately — the global map view unlocked navigation. SPS ~600-617K (unchanged). New det oracle: 5M/ckpt-20/seed42 md5-of-md5s = 754d2acc9956632c (x2 verified).** resources/nethack/nethack_weights.bin is old-arch (demo refuses cleanly; refresh from any new ckpt). Upgrade paths noted: attention over the 60 tokens (earn with evidence — patches+MLP already beat conv), entity lists (needs fixed-size padding + ragged attention, phase 2).

2026-07-10 v2 FOLLOW-UP: **200M full run (seed 7, user's hidden-512/1-layer config): score 1415.4, entropy 0.323, no instability — all-time best (old tuned arch peaked ~1102), +28% on first try.** NOTE all v2 validation runs used the user's experiment config = hidden 512 x 1 LAYER (params 2.2M — the math check that caught it) with a MINIMAL [train] block inheriting default.ini (lr 0.015!) — the new arch is robust to those hypers here (130@5M, 1415@200M). Mean-pool patch tokens TRIED AND REJECTED: init-scale theory said sums run hot (uniform patches ≈ 32x one embedding), but mean-pooling measured WORSE at 5M on both seeds tested (55.1/75.8 vs 130.4/85.9) — sum's magnitude carries patch-context signal and muon absorbs scale; sum-pool kept, oracle 754d2acc re-verified bit-exact after revert. USER-INSTABILITY POSTMORTEM (score ≤20, 1.1M SPS, "didn't change anything"): their run did NOT use v2 — all v2 files uncommitted in the puffertank working tree; any other checkout/box runs the OLD conv encoder, which under the new config (+ inherited default lr 0.015 — the 2026-07-08 [train]-deletion foot-gun re-created by the "experiment" commit) sits at ~10-20 score; degenerate cheap level-1 envs explain 1.1M SPS on a bigger box. High SPS + low score = degenerate-policy signature (good policies DROP SPS: 1415-run ended at 279K).

2026-07-10 FUSED PATCH-MAX GLOBAL BRANCH (user's design, replacing the flatten-linear global): per patch embed+flatten (32cells x 32d = 1024) -> 16 (bottleneck keeps fused per-glyph table T[g, pos*16+k] = 5977x512 = 6MB L2-resident) -> 128 -> elementwise MAX over 60 tokens, max FUSED into the expand kernel so (B,60,128) never exists in memory. Weights: glb1_w (16,1024)/b, glb2_w (128,16)/b; reg order embed, loc_w/b, glb1_w/b, glb2_w/b, bl_w/b, proj_w/b. Kernels: nh_permute_g1 + glyph_T GEMM per fwd (like old conv1 table); nh_patch_max_kernel (block/sample: 60x16 tokens in smem from table gather, then 128 outs x 60-token max in registers, argmax saved, strict > + fixed order = deterministic); bwd nh_patch_max_bwd (block/sample, dW2+dt16 in fixed-point smem, dt16 relu-masked overwrites t16) + b1 colsum + nh_dT_patch_scatter (thread per (b,tk,k) elem, quantize once, 32 pos adds, NH_HOT_G=10 hot rows 40KB smem) -> dT rows-convert -> dE=dT@W', dW'=dT^T@E, unpermute; local dE added via nh_fxp_add_rows on top of the GEMM result; PAD-glyph rows touched by ragged edge patches need nh_count_pad_kernel seeding counts[5976] += 261*B or the rows-cast guard misses them. GRADCHECK LESSON: FD CANNOT verify glb1 (weights shared by all 60 max-pooled tokens -> perturbation flips near-tied argmax winners below the kink detector) — added float64 TORCH AUTOGRAD REFERENCE to tests/test_nethack_encoder.py (full encoder replica incl. bl-feat expansion; all 11 tensors exact to ~1e-6, FD skips glb1 with a note). Det oracle (this arch): 9ae9ecbce2184b31 x2. 5M seed 42: 79.8 (vs 130.4 flatten-sum same seed — noisy scale). 200M seed-7 A/B: fused patch-max 1270.0 (entropy 0.390, final SPS 215K) vs flatten-sum 1415.4 (0.323, 279K) — max-pool ~10% BEHIND on the single seed pair tested; ONE seed each, unresolved whether real or noise (5M seed spread was ±30%). Both archs verified + deterministic; max-pool is the one LIVE in the working tree (sum version recoverable from this log + git diff history). Params 2.0M vs 2.2M.

2026-07-10 VERDICT — FUSED PATCH-MAX IS THE KEEPER: seed-11 50M pair: flatten-sum **COLLAPSED (score 1.34, entropy 0.001** — policy locked to one action; the user's reported "never above ~20" instability reproduced, so that report was likely the sum arch's real failure mode, not (only) a stale build) vs fused patch-max **460.1, entropy 0.58, healthy**. Full picture: seed 7 @200M sum 1415 / max 1270; seed 11 @50M sum COLLAPSED / max 460. The sum branch's ~32x-hot global features (sum of uniform-patch embeds) are the suspected fragility — wins big when it works, dies completely on other seeds; max-pool bounded features = robust. Max-pool restored as the LIVE build (nethack_max.cu/nethack_sum.cu snapshots in session scratchpad — scratchpad is EPHEMERAL; the max variant is the working tree, sum recoverable from the memory of this session's diffs only). Between-seed variance is huge (seed 7 vs 11 at 50M: max 935 vs 460) — ALWAYS pair seeds when comparing archs.

2026-07-11 SMITE LOGGING: god-wrath deaths (fry_by_god in pray.c, killer.name = "the wrath of ...") were binned as death_combat (how_done=DIED). Engine: nle_done (fast-nle src/nle.c) now reports NLE_HOW_WRATH=100 (defined in nletypes.h) when DIED + killer prefix matches; goldens 34/34 PASS (golden hash covers glyphs/chars/colors/specials/blstats/message only — how_done changes are invisible to it). Env: Log.death_smited field + nethack_add_log branch + binding.c dict_set. Reward path untouched (reads only obs.done, never how_done) — no oracle impact. Probe (scratchpad smite_probe.c, linked against build-smite scratch lib): 40 pray-spam eps → 29 smited / 11 combat (angry-god minion kills legitimately stay combat). Moloch's-indifference is also DIED-not-combat but unreachable (no #offer action). DEPLOYED 2026-07-11 ~10:12: real build/ engine rebuilt after user's run exited + probe re-verified 29/40 against deployed lib; _C.so was already current; build-smite/ deleted. GOTCHA that bit the user: `build.sh nethack` builds libnethack.so ONLY if missing — engine source edits need an explicit `cmake --build vendor/fast-nle/build --target nethack -j` or the metric silently stays dead while the dashboard row exists. Metric verdict (user's runs): early training 54% of deaths were smites, ~20% for much of the run, trailing to 2-5% — smites were a large hidden chunk of "death_combat".

2026-07-11 PRAY REMOVED from action space (user: "try just removing prayer"; smite tax during learning + unobservable ugangr floor): NETHACK_NUM_ACTIONS 24→23, table drops 0x80|'p', ELBERETH/WEAR/EAT shift to 20/21/22, ACT_PRAY case + prayers/prayers_low_hp Log+Stats+binding metrics + macros.h "to pray" yn exemption all deleted. Encoder NH_ACTIONS 23 → NH_BL_FEAT 88→87, NH_CONCAT 536→535 (obs UNCHANGED 3506B — ublesscnt extra kept as vestigial to avoid an obs break; README notes this). death_smited metric kept (should now pin at 0 = regression check). Demo NAMES/-BL_FEAT/CONCAT literals + test literals (rng -1..23, bl_w (64,87), zeros 87, range(23), proj (H,535)) updated; encoder suite PASS (FD + torch ref ≤1.4e-6); demo rebuilt (build.sh nethack --fast). ALL CHECKPOINTS BROKEN (head + bl_feat). NEW det oracle (23-action, swept-hypers config): **53c1dad19154ef75** x2. 5M seed-42: score 74.4, death_starved 0.289 (was ~0 with pray), eats 4.4/ep — starvation pressure is back and EAT must carry hunger; watch death_starved on long runs (eat action + corpse filter exist but food supply may bind). If starvation walls runs, alternatives: re-add pray with ugangr+Luck exposed, or leave as-is if descent improves. scratchpad/smite_probe.c now stale (references ACT_PRAY).

2026-07-11 FLOOR-CORPSE EATING (stage 1 of principled-action-space plan; stage 2 = inventory entity obs + {verb,slot} MultiDiscrete heads — backend already supports multi-head, see convert's ACT_SIZES {9,5}): EAT macro now ACCEPTS floor "eat it?" offers (macros.h nethack_do_use_item, param renamed decline→floor_offer; "atrice" substring declined = cockatrice+chickatrice instant-petrification guard); carried-corpse letter filter kept. CRITICAL DISCOVERY: macro change alone was dead code — autopickup ($[%) scoops corpses on step-on before any floor offer fires. Fix: AUTOPICKUP_EXCEPTION=">corpse" — config-FILE-only directive, so env writes per-process rc file (nethack_fs.h nethack_rc_path, vardir base + atomic tmp+rename) with the OPTIONS= line + APE, passes settings.options="@<path>". GOTCHA: APE prefix '<' = ALWAYS grab, '>' = NEVER (backwards from intuition; first attempt silently no-opped — probe caught byte-identical trajectories). ENGINE BUG FOUND+FIXED en route: set_duplicate_opt_detection used SIZE(boolopt/compopt) which are per-env POINTER macros post-migration → SIZE()=0 → 0-byte alloc indexed by real option idx → heap corruption; only reachable via config-file reads (NLE never did until @rc). Fixed with BOOLOPT_COUNT/COMPOPT_COUNT; goldens 34/34 PASS. Verified end-to-end: kill→step-on→EAT probe eats lichen/goblin corpses (6/40 attempts; misses = ~50% corpse-drop + pet steals). _C.so + demo rebuilt. ORACLE for the floor-eat era was never baselined (user's runs kept GPU busy; 53c1dad19154ef75 = 23-action pre-floor-eat, STALE). Probes: scratchpad floor_eat_probe(2).c, rc_bisect.c.

2026-07-11 FLOOR-EAT VERDICT + HUNGER POTENTIAL: floor_eats metric shipped (macros.h accept-branch counter -> Stats/Log/binding; subset of eats). User's 100M run: floor_eats 2.4/ep (~11% of eats) but score/game_time/starved IDENTICAL to pre-floor-eat baseline (530/5170/0.164 vs 524/5129/0.159) — corpses cover only ~5-10% of the ~5.2K/ep nutrition budget; usage is accidental, not reinforced (credit gap). No-pray 100M baseline ≈ 524-530 score, game_time ~5.1K (pray was worth ~2x score via survival time), truncated 22% (satiated-EAT no-op = free wait button; ~2.3K no-turn steps/ep — truncation dodges death_penalty, watch this). User adopted num_layers=3 in config. HUNGER POTENTIAL shipped: r += hunger_coef*(prev_hu - hu), hu = clamp(blstats[NLE_BL_HUNGER],1,6) — Satiated==NotHungry (no overeat reward; eating at NotHungry pays 0 BY DESIGN — gradient is eat-when-Hungry(+1)/Weak(+2), decay charges -1/level), farm-proof potential, terminal step skipped (shaping fn not called on done), prev_hunger seeded clamped at reset. ini hunger_coef=0.05 (weak-eat pays 0.1), sweep log_normal 0.002-0.25 (0.25 = Fainted->NotHungry Δ4 saturates the ±1 clamp, WLOG rule). Probe (scratchpad hunger_probe.c, coef=10): 300K steps, 0 mismatches, 64 decay charges + 7 recoveries paid exactly. hunger_coef=0 is bit-exact with old rewards (0*Δ adds ±0.0f). Stage-2 plan: inventory entities + {verb,slot} heads (underfoot swap ALREADY SHIPPED, below). Hunger-potential 100M result: score 659 (+24%), starved HALVED 16.4%->8.7% via eat TIMING (floor_eats flat 2.4 — not harvesting), depth 1.40 + reach_mines 1.4% (first mines entry in no-pray era; decay charge taxes camping), game_time slightly down (shorter but more productive lives).

2026-07-11 UNDERFOOT GLYPHS SHIPPED (settings-gated engine patch): nle_settings.underfoot_glyphs (default 0 -> goldens untouched, 34/34 PASS with rebuilt replayer — NOTE settings struct layout changed, ALWAYS rebuild replay_golden after nletypes.h edits); winrl.cc fill_obs patches obs->glyphs[hero cell] AFTER the dirty-row copy every fill: vobj_at top object else back_to_glyph terrain, through shuffled_glyph; glyphs-only (chars/tty untouched); accessor nle_underfoot_glyphs() in nle.c. Env opts in at init (nethack.h). Hero glyph NEVER at center now (was constant/useless — crop centers via blstats x,y); corpses/stairs underfoot visible through the SAME embedding vocab. Probe (scratchpad underfoot_probe.c): 200K steps, hero_at_center=0, body-glyph at center 449x, agrees with "You see here...corpse" msg 247/253 (6 = stacked objects, top shown — correct). Stock NLE has this blind spot in ALL spatial channels (verified: store_screen_description also gets display glyph) — our agents now see strictly more than stock here. No obs layout change; old checkpoints load but center-cell semantics shifted (retrain). DET ORACLE (current era: 23 actions + floor-eat + hunger_coef 0.05 + underfoot glyphs, 5M/ckpt-20/seed42): **b1c34a2ad5bec072** x2. UNDERFOOT 100M RESULT: score 988, depth 5.23 (was 1.40!), mines 41%/town 13%/main_d5 37%, starved 1.4%, trunc 4.6%, wears 0.95 — mechanism was STAIRS visibility (pressing '>' needs standing on occluded stairs), not corpses (floor_eats DROPPED to 0.72; short 2.2K-turn diving lives). Wall is back to depth-5 combat attrition at XL 4 (death_combat 93%) → stage 2 (item use) is the binding constraint. 2026-07-11 STAGE 2 SHIPPED (inventory entities + {verb,slot} factored actions; ALL checkpoints broken — obs AND heads): obs v3 = 3616B (v2 3506 + 55 inv slot glyphs int16 LE appended at NETHACK_OFF_INV; empty slots = pad 5976 via inv_oclasses<18 test — inv_glyphs alone is NOT fully padded). Actions = MultiDiscrete ACT_SIZES {23, 55} (binding.c; backend already iterates heads, cf. convert {9,5}); env reads actions[0]=verb, actions[1]=slot; WEAR/EAT answer getobj with inv_letters[slot] IF listed in the bracket parse (nethack_parse_candidates replaces random pick; env->rng pick GONE), invalid slot -> ESC + illegal=1 + stats.illegal_actions++ (use_item returns -1/0/1); floor-eat accept ignores slot (fires before inventory prompt). ENCODER: inv branch = per-slot embed -> shared 32->16 linear (inv1_w/b, kaiming/zero, seed order after glb2) -> relu -> FLATTEN in slot order (position must survive pooling would kill it — policy must NAME a slot index) = 880 dims; concat [loc 256|glb 128|inv 880|bl_hid 64|bl 87] = 1415. Fused T_inv = E@inv1_w^T (5977x16) via direct dot kernel (no permute); bwd: relu+bias colsum (bacc gets 6th segment [.. |glb1 16|inv1 16], flush kernel now 6 tensors), dTinv plain-global-atomic fxp scatter (55x16/sample too small for hot machinery) -> convert-all -> dinv1_w = dTinv^T@E splitk; dE += dTinv@inv1_w via dE_tmp GEMM + nh_add_inplace AFTER local add_rows. Weight reg order: embed, loc, glb1(w,xy,b), glb2(w,b), inv1(w,b), bl, proj. VERIFIED: full FD+torch suite PASS first try (14 tensors ≤1.2e-6; embed check covers inv dE path). PENDING: demo (nethack.c) NOT ported — refuses checkpoints via float-count inference, actions calloc'd to 2 so it compiles/runs; README not updated for v3/heads. Slot-head semantics: direct inventory position (obs slot k == action slot k), NOT per-verb candidate index.

STAGE-2 OPEN ISSUES (2026-07-11 end of session, MUST FIX before trusting runs):
1. DETERMINISM ORACLE FAILS: 5M seed-42 x2 gave b51e2c993707da9b vs e02fc78f25c8353e (first mismatch ever). 5M training itself runs fine (eats 2.9/ep directed, floor 0.26, depth 1.19). Encoder gradients are torch-verified so math is right; nondeterminism suspects to bisect: (a) cublasLt algo selection on the NEW small GEMM shapes (puf_mm_nn (5977,16)x(16,32) dE_tmp; splitk on dTinv (5977,16)); (b) something in multi-head sampling; (c) env-side (less likely). Bisect: hash encoder fwd+bwd outputs standalone x2 (test harness), then vecenv-only, then full train. All new kernels use fxp integer atomics (associative) + sequential loops — reviewed clean.
1-ROOT CAUSE FOUND (probable): binding.c NUM_ATNS was left at **1** while ACT_SIZES had 2 heads — vecenv strides env->actions by NUM_ATNS, so env i's slot action aliased env i+1's verb (scrambled actions across ALL envs), AND the CPU/GPU action buffers were allocated N*1 while sampling writes N*2 → OOB writes into adjacent allocations → races → the continuous nondeterminism. Also explains the terrible slot learning in the stage-2 100M runs (slot inputs were noise). FIXED: NUM_ATNS 2 (convert convention: NUM_ATNS = number of heads). ALL stage-2 run results before this fix are INVALID as evidence about the arch (474/555/367 runs all had scrambled actions + corrupted memory). ALSO ADDED: action masking — binding MY_ACTION_MASK (23+55=78), env->action_mask field auto-wired by vecenv, filled at end of nethack_pack_obs (verbs all-1 except EAT masked while Satiated — kills the free wait button; slots 1 only for armor oclass 3 / food oclass 7; all-invalid fallback = slot 0; masking applied in sampling AND train recompute, cf. chess). illegal_penalty -0.003 in ini (bracketing: 0 free-lottery, -0.01 suppressed exploration — mostly moot now that masking prevents most invalid picks). POST-FIX ORACLE: **4ec15b8ba8ae48d8 x2 — DETERMINISM RESTORED** (NUM_ATNS was the source). Post-fix 100M (seed 73 default, masking + -0.003): score 639, eats 22.2 (highest ever — item system fully works), illegal 35, valid_moves 74% (best step economy ever), truncated 2.8%, wears 0.03, BUT depth 1.15 — this run settled into dlvl-1 farming (game_time 5550, starved 13.4%): the improved food economy strengthened the camping optimum, so descent_coef 0.81 no longer tips it (the underfoot-era 988/depth-5.2 run pre-dated masked-EAT's food abundance). Strategy equilibrium is seed-sensitive — pair seeds before judging.

2026-07-11 MANUAL DIM SWEEP (100M each, seed 73, greedy ladder on post-NUM_ATNS-fix build): descent_coef 0.81->3.0: 639/depth1.15 -> 866/5.05 (REGIME FLIP, kept; ini updated; saturates clamp per descent like 2800 era). embed 64: 865/4.87 even (+800K params, eats tripled to 33 but no score — food not binding in dive regime) REVERTED. NH_INV_HID 16->32: 920/5.20 KEPT (concat 2295, +450K proj params; src currently at inv32). crop 13: 843/4.64 + SPS 329K REVERTED (9x9+global wins again). hidden 768: 945/5.29 but SPS 318K vs ~500K — fixed-steps win, fixed-compute wash; left at 512 in ini. Binding constraint in dive regime = combat attrition (92% combat deaths XL~3.8) — next levers: QUAFF/READ/ZAP verbs, pointer head, NOT encoder width. FINALIZED: seed-11 confirmed inv32 config (938/depth 5.19 vs seed-73 920/5.20 — tight pair). Test literals updated (proj (H,2295), inv1_w (32,32)), gradcheck PASS on final dims. **DET ORACLE (final stage-2 config: 23+55 heads, inv_hid 32, masking, descent 3.0, hunger 0.05, illegal -0.003): eb933225f4dfe372 x2.** 2026-07-11 QUAFF SHIPPED (verb 23, NETHACK_NUM_ACTIONS=24): 'q' via nethack_do_use_item gate "want to drink"; fountain/sink yn offers ("rink from the") DECLINED in the floor_offer branch (cmd=='q' check) so the potion prompt follows; pickup_types $[%! (potions autopicked); slot mask + oclass 8; quaffs metric; NH_ACTIONS 24 -> BL_FEAT 88, CONCAT 2296; gradcheck PASS; probe: 6/6 slot-directed heals ("You feel better"). ORACLE (quaff build): **8fe12cec94b59767 x2**. 100M: score 901 (within 918-945 noise band — no gain yet), quaffs 0.59/ep (policy uses it, modestly), combat deaths/damage UNCHANGED (92.5%/77) — potion supply at depth<=5 is small, most potions unidentified (harmful gamble), and quaff-at-low-HP timing has the same credit gap eat-timing had (hp_coef 0.00057 pays ~0.008/heal — weak signal; consider hp_coef bump or sweep). HP_COEF BRACKET (100M each): 0.00057 quaffs 0.59 / **0.002 KEPT: score 904, depth 5.23, quaffs 0.82 (+38%), no cowardice** / 0.005 COWARDICE (score 809, depth 4.4, combat deaths 81%, quaffs DOWN — HP-pain avoidance dominates healing income; this env prices caution steeply). ini at 0.002. **CURRENT DET ORACLE (final session config: 24+55 heads, quaff, inv_hid 32, masking, descent 3.0, hunger 0.05, hp 0.002, illegal -0.003): ddaabcf14a394221 x2.** 2026-07-11 PRAYER RESTORED (verb 24, NETHACK_NUM_ACTIONS=25; "to pray" yn exemption back in handle_prompts; prayers/prayers_low_hp metrics back; NH_ACTIONS 25 -> BL_FEAT 89 CONCAT 2297; gradcheck PASS): 100M = **1177 (campaign best, +30% over no-pray 904), depth 5.35 (deepest), starved 0.0%, smited only 1.8%** (vs 54% early-training in the original chaos era — the modern env's food economy spaces prayers naturally), prayers 2.1/ep (~6% at low HP — mostly maintenance), quaffs UP to 1.43, game_time 2884. Prayer now funds DIVING not camping (old 1286 pray-best was a depth-1.1 Elbereth camper). Verb not masked by cooldown (kept the experiment pure; ublesscnt in obs); ugangr exposure still optional future work. **CURRENT DET ORACLE (25+55 heads, pray+quaff, inv_hid 32, masking, descent 3.0/hunger 0.05/hp 0.002/illegal -0.003): 6b13f63c6233534d x2.** 2026-07-11 DEATH-ANATOMY LOGGING (log-only, oracle UNCHANGED 6b13f63c verified): engine nle_done exports killer via name_to_mon(killer.name) -> internal[9]=mnum+1, [10]=mlevel (NLE_INTERNAL_SIZE 9->11; slots 6-8 are rewritten by fill_obs, hence 9/10; goldens 34/34). Env: death_mon_level/death_burst_turns (turns since last >=75% HP)/death_adj_monsters (glyph<381 8-neighbors, tracked per step, read at death)/death_maxhp. **VERDICT (100M): killers are mlevel 2.67 vs our XL 4.79 — NOT underleveled-ambush; burst 32 turns, adj 1.1 = slow 1v1 attrition duels vs weaker monsters. Damage 77/ep vs maxhp 36 with regen ~1HP/10turns = recovery deficit between consecutive duels.** Fix ranking REORDERED: healing throughput + disengagement (Elbereth unused at 0.08/ep — mid-duel credit gap) + THROW pre-softening > pure XL pacing. CORRECTION: the 1613 run was **200M** (user bumped ini total_timesteps mid-session) vs 1177@100M — the delta is 2x TRAINING, not a binary lottery (that theory retracted; alignment-shift divergence remains a theoretical caveat but was not demonstrated). So: pray-config scales 1177@100M -> 1613@200M, depth 6.02, XL 4.79 — still improving with steps. Death-anatomy VERDICT unaffected (per-episode means at convergence). 2026-07-11 THROW SHIPPED then INDICTED (verb 25, 26 actions; oracle 3f7de08e36060f28 x2; probe 5/5 after fixing PARSER BUG: getobj brackets can lead with '$' (gold) which aborted candidate parsing — n==0 skip set now '-',' ','$'): 200M = score 1375 (vs 1613 pre-throw), **throws 0.012/ep (two-step direction protocol unlearnable: a non-move follow-up wastes both actions), quaffs COLLAPSED 1.43->0.04 (weapon autopickup ')' diluted slot economy), damage UP 77->123**. VERDICT: two-step direction is dead; DIRECTION HEAD build approved by user + evidence: ACT_SIZES {12,55,8} (verbs MOVE,RUN,>,<,KICK,SEARCH,ELBERETH,WEAR,EAT,QUAFF,PRAY,THROW; dir=8 vi-keys), KICK/THROW answer their direction prompt IN-STEP (atomic), NUM_ATNS 3 (!!), MY_ACTION_MASK 75, BL_FEAT 76 (verb onehot 12), CONCAT 2284, dir head trains dense on every move. SHIPPED + VERIFIED: dir_probe 148/200 exact moves, throws atomic (no live prompt), gradcheck PASS, **ORACLE 5cd7e2db76692803 x2**. 200M: score 1549 (noise-band of pre-throw 1613 — the 3-head rework costs nothing), **quaffs 2.52 (best ever), throws 0.248 (20x the two-step build), depth 5.73, game_time 3210, starved 0.1%**. The two-step-throw regression fully recovered. Factored space is the platform for ZAP (directional, same heads). 2026-07-11 PRAYER-CLOCK ABLATION (user flagged ublesscnt as the one superhuman obs channel — humans bound the cooldown from prev_action+TIME, never see the re-roll): extra[0] now ZEROED in pack_obs (slot kept, layout stable). 200M verdict: **NOT load-bearing** — smited 2.1% (vs 1.8%), score 1495 (noise band of 1549), depth 5.89 (deeper), prayers UP 2.1->3.4 with prayers_low_hp 0.12->0.61 (shifted to panic-button use — more human-like without the clock). ORACLE (clock-zeroed build): 9e5507adde1e2b64 x2. DELETE the plumbing (extra slot + engine internal[5] export + encoder cooldown feat) at the next obs break. SLOT POSITION-DEPENDENCE DIAGNOSTIC (2026-07-11, log-only, oracle 9e5507adde1e2b64 reproduced + score bit-identical 1494.794 — rebuild-stable): use_slot_mean/valid_slot_mean metrics (Stats counters in item-verb success branches — floor eats excluded — and in the mask-fill loop). 200M: **use 5.18 vs valid 9.51 — uses skew early, CONSISTENT WITH position dependence but CONFOUNDED**: late slots are dominated by accumulated weapons (rationally un-thrown by a melee monk), early slots by starting food/armor. Decisive refinement queued: within-type version (quaffed-potion slot mean vs valid-POTION slot mean, oclass 8 only) — same plumbing, swap the counters. POINTER HEAD BUILD APPROVED (user: "just make the change and validate"), design locked:
- logits_slot[b,i] = dot(q_b, s_bi) / sqrt(32), q = ptr_q_w (32,512) @ hidden (no bias or with), s_bi = inv branch per-slot 32-d relu vectors (a->inv_out rows BEFORE flatten — already computed, reuse as keys directly, no key projection v1).
- PLUMBING PROBLEM: decoder only sees hidden; keys live in encoder activations. Solution: custom NethackDecoder in src/nethack.cu replacing DefaultDecoder for this env (check how Encoder/Decoder pairs register; [torch] decoder = DefaultDecoder in default.ini — nethack may need a decoder override hook like the encoder has). Decoder needs the encoder activations pointer: both structs created in nethack.cu — stash encoder activations ptr where decoder forward can reach it (same registration flow; beware rollout vs train activation structs — pair them per phase, and cudagraphs capture fixed pointers so wiring at reg time is safe).
- Decoder forward: verb (12) + dir (8) + value stay linear from hidden (existing decoder weight layout minus 55 rows); slot logits via q·k kernel (B×55 dots of 32 — trivial). Backward: dq = sum_i dlogit_i * s_i; ds_i += dlogit_i * q (flows into inv branch backward — inv_out grad already plumbed! ADD pointer grads into a->inv_grad path BEFORE the existing inv backward... careful: inv_out is consumed by concat AND now by keys — two grad paths sum); dW_q = dq^T @ hidden (splitk).
- Masking: applied post-logits in sampling (mask machinery is logits-agnostic ✓).
- Verify: torch reference extension (pointer math in float64), FD on ptr_q_w, oracle x2, 200M A/B vs 1495/1549 band + use_slot_mean vs valid_slot_mean gap closing = the validation criterion.
- Demo: port becomes even more owed.
- IMPLEMENTED (compiles, encoder suite + 5M smoke/oracle running at session edge): NethackDecoder in src/nethack.cu after create_nethack_encoder (weights lin_w (21,H) verb|dir|value + q_w (32,H); fwd nh_dec_assemble_kernel dot-loop; bwd nh_dec_dtmp/dq/keygrad kernels + puf_mm_tn wgrads + two puf_mm_nn + add for grad_input; reg_train sets nh_dec_acts_train + nh_ptr_keygrad statics); encoder reg_train/rollout set nh_enc_acts_train/roll + B statics (decoder picks ea by input B); encoder backward adds keygrad->data into inv_grad after slice, before relu mask, gated on nh_ptr_keygrad != null (encoder-only harness unaffected); hooks create_custom_decoder in ocean.cu + call in pufferlib.cu after inline Decoder init. Value at out[:,75] (last), slot logits [12,67) — layout matches DefaultDecoder/sampling. Decoder grads NOT torch-verified (encoder suite doesn't cover decoder) — validation = smoke behavior + oracle determinism + 200M use_slot gap.
POINTER-DECODER BUG HUNT RESOLVED (2026-07-11, ~15 debug iterations): symptom NaN losses from epoch 1. ROOT CAUSE: **pufferlib.cu casts ANY decoder weights to DecoderWeights and reads ->continuous/->logstd (sample site ~695 + train site ~1635); my shorter struct made ->continuous read heap garbage (true) and ->logstd alias q_w → sampler ran CONTINUOUS (wrote Gaussian floats as actions) while the loss recomputed discrete → (int) casts out of range → act_logit sentinel 0 → logp +9991 → inf/NaN.** FIX: NethackDecoderWeights now leads with a DecoderWeights-identical header {weight_unused, logstd(null), hidden_dim, output_dim, continuous=false} — any custom decoder MUST do this. Other fixes en route: Decoder.activation_size hook added to framework (calloc'd sizeof(DecoderActivations) before — heap corruption with bigger structs); per-registration encoder-decoder pairing (a->enc = nh_enc_last at reg; single static was wrong for multi-buffer rollouts); slot logits clamped ±10 with backward gate (q·k is scale-free); NH_DEC_PAD 24 (21-row GEMM alignment paranoia, kept). DEBUG LESSONS: precision_t is 2 BYTES (bf16) — host-side cudaMemcpy debug dumps must not assume f32; `VAR= cmd` (empty env var) still passes getenv() — control runs must UNSET; teardown segfault with --cudagraphs -1 = pre-existing cudaGraphExecDestroy quirk, benign. Pointer decoder gated behind NH_PTR_DECODER env var until 200M-validated. Post-fix tiny smoke: policy -0.000 healthy, eats 2.2/ep @40K.
POINTER 200M VERDICT (oracle 4d3c23b3cfd76014 x2, gradcheck PASS): **v1 LOSES — score 1204 vs flat 1495-1549 (-20%), quaffs COLLAPSED 2.4->0.002, entropy stuck at 3.10 (under-converged), illegal 61, use_slot 4.1 vs valid 8.8 (gap not closed).** Interesting: at 5M the pointer led (quaffs 1.44 vs typical ~0.3; use_slot ABOVE valid) — early sample-efficiency win that then degrades — suspected cause: raw relu'd keys are non-negative & correlated -> poor discrimination + the ±10 clamp/fixed 1/sqrt(32) temp give flat distributions; standard fix = normalized (cosine) attention with learnable temperature + a key projection instead of raw inv features. POINTER V2 (cosine attention: key projection k_w (32,32) over inv features, L2-normalized q/k, learnable tau init 10 w/ fxp-deterministic grad, clamp deleted; full normalization-Jacobian backward; oracle e02557ebefcdb1b5 x2): 200M = **1235 (v1 1204, flat 1495-1549) — still -18%; quaffs STILL collapsed (0.012); use_slot 4.35 vs valid 8.82 unclosed**; eats 9.1 fine. Interpretation: shared normalized-key geometry lets the dominant use (food) crowd out rare uses (potions) — per-slot independent rows don't compete this way; a v3 would need per-verb queries. 2026-07-11 **PER-VERB SLOT HEADS = THE WINNER (v3 goal via factorization, no custom decoder)**: ACT_SIZES {12,55,55,55,55,8} — dedicated slot head per item verb (wear/eat/quaff/throw), each masked to ITS class only (3/7/8/2), env reads actions[1+verb_idx], dir at [5]; NUM_ATNS 6, MY_ACTION_MASK 240; DEFAULT decoder (240+1 out). ORACLE **00046c04f480b7fd x2**. 200M: **score 1519 (flat band ✓), quaffs 3.09, throws 2.95 (12x!), wears 0.50 (10x), eats 11.2, use_slot 7.5 vs valid 9.1 (gap CLOSED-ish), depth 5.54 (deepest), illegal 29, starved 0.1%** — score parity with categorically richer item use; verb-conditioning + class-tight masks (quaff head sees only potions) fixed the crowding AND the discovery problem in one move. Quaffs at 3.0/ep by 40K steps in smoke (v2 needed 5M). THIS IS THE DEFAULT NOW.
2026-07-11 ZAP SHIPPED (verb 12 'z', NETHACK_NUM_ACTIONS=13; FIFTH per-verb slot head masked to wands oclass 11; ACT_SIZES {13,55x5,8}, NUM_ATNS 7, MY_ACTION_MASK 296; pickup $[%!)/ ; dir answered in-step; zaps metric; NH_ACTIONS 13 -> BL_FEAT 77 CONCAT 2285; gradcheck PASS). ORACLE **a91833ae104ecb57 x2**. 200M: score 1456 (in-band), **zaps 0.062/ep (wand scarcity at depth<=6 — verb works, pays deeper), throws UP to 4.52, quaffs 2.95, use_slot 8.4 vs valid 9.3 (tightest yet)**, depth 5.55, starved 0.4%. Demo actions calloc 7 (port still owed). ORDER-INVARIANCE note: masks+stable monk loadout defuse it empirically (use/valid gap closed); residual = within-episode slot churn on consumption; queued cheap fix = env-side CANONICAL INVENTORY ORDERING (sort obs inv block by class+glyph, permutation map back to letters) — ahead of any attention revival. Assertion hardening queued: static_assert DecoderWeights header layout + NUM_ATNS-vs-ACT_SIZES count startup check.
2026-07-11 FORK PUSHED: 5678c7a7c to FinlaySanders/fast-nle main (underfoot+inv-sync+killer/wrath+config-fix+putchar gate; user identity, no attribution). PufferLib repo still uncommitted (user's).
SWEEP RANGES SET (evidence-centered; Protein centers on range midpoint — mean key ignored): hp [5e-4, 6e-3] (bracket 0.0006 weak/0.002 good/0.005 cowardice), illegal uniform [-0.01, 0] (bracket 0/-0.003/-0.01), hunger [0.01, 0.25] (mid 0.05 = believed), descent [0.5, 10] + xp [0.05, 1] jointly = the dive-vs-grind pacing question (THE sweep objective per combat-death anatomy), scout [1e-4, 0.01] (26x-income lesson), gold [0.01, 1], death [-1, 0] kept, timesteps [1e8, 4e8] time-scaled. NOTE ent_coef inherited range predates 7-head entropy summing — expect lower optimum.
2026-07-11 (sweep running on tinybox, ~24h): HARDENING ASSERTS SHIPPED (static_assert DecoderWeights header offsets in nethack.cu; _Static_assert NUM_ATNS==len(ACT_SIZES) in vecenv.h — both of today's catastrophic bugs now compile errors). **DEMO PORTED to 7-head arch** (nethack.c): DEMO_BL_FEAT/OD derived from env defines (future-proof), inv branch (embed->inv1 32x32->relu, flattened between glb and bl_out in concat), decoder (DEMO_OD+1=297,H) bias-free, make_multidiscrete 7 heads over fused logits+value buffer, demo_sample applies env action_mask (-1e9) before sampling, env_open allocs mask so pack fills it, items print incl quaffs/throws/zaps/prayers. VERIFIED live: arch inferred from ckpt, 3 eps avg 1037 @ 49M-step ckpt, full action repertoire in histogram. Usage: ./nethack [steps] [ms_per_frame, 0=headless]; ckpt: cp newest ckpt_1b .bin -> resources/nethack/nethack_weights.bin. 1B convergence run DETACHED locally (log scratchpad/s2_1b.log, ckpts scratchpad/ckpt_1b/) — check progress, recopy ckpt for better demo, harvest final score. No obs/env changes while sweep runs (results must land on the swept env).
USER DEMO-WATCH FINDINGS (2026-07-11): never rests to regen, never retreats up, "carrying too much" spam (pack at unencumbered ceiling — crowds out potion/wand pickup; no DROP verb), suspected shopkeeper anger (pickup debt trap RE-ARMED by $[%!)/  — was the documented pre-item-era trap; THROW also hits peacefuls unguarded). DIAGNOSTICS SHIPPED (log-only, oracle a91833ae reproduced ✓ sweep-safe): regen_ticks (+1-HP steps), ups_hurt (UP at <50% HP), burdened_frac (NLE_BL_CAP>0), pack_full_frac ("arrying too much" msg steps). 5M baselines: regen 45.8/ep, ups_hurt 1.1, burdened 0.001, pack_full 0. QUEUED FIXES (post-sweep, behavior-changing): shop-aware autopickup engine gate (in_rooms SHOPBASE, settings-gated like underfoot); DROP verb if burdened_frac grows; rest/retreat = watch sweep's gamma/hp_coef winners first. use_slot/valid metrics still coarse (union over 4 heads' valid sums).
OLD DECISION (superseded): **pointer line PARKED — flat head stays DEFAULT** (pointer v2 available via NH_PTR_DECODER=1, deterministic + healthy, just worse); revisit only with per-verb-query evidence.
EXTERNAL REVIEW (user's other agent) TRIAGE 2026-07-11: (1) empty-slot masking concern = ALREADY HANDLED by MY_ACTION_MASK at sample+train (verified in ppo_discrete_head during NaN hunt) — entropy normalizes over legal slots only; (2) tau robustness real for v3: cos=out/tau division (blows up tau->0), no positivity constraint — use tau=exp(theta) + store raw cos scratch; ALSO unknown: muon behavior on 1-elem params (Newton-Schulz on 1x1); (3) verb-conditioned query (AlphaStar autoregressive verb->query) = THE v3 design, matches quaff-crowding diagnosis; (4) **glyph-only keys/features lose item state (BUC/enchant/charges/count) — affects FLAT head too; fix = engine per-slot int export (killer-export pattern) at next obs break — QUEUED**; (5) stale comments fixed (NH_PTR_SCALE removed, patch/inv-dim doc drift corrected); (6) dq kernel warp-per-sample perf note (only if pointer revives); tie-behavior confirmed safe (env resolves sampled slot index verbatim, no canonicalization). All framework fixes (activation_size, DecoderWeights header contract, pairing) are in-tree and benefit any future custom decoder.
- PLUMBING DISCOVERED: encoder hook = create_custom_encoder(env_name,&enc) in src/ocean.cu (~line 590: `else if (env_name == "nethack") create_nethack_encoder(enc);`), called from pufferlib.cu ~1715 where Decoder is built INLINE right after (line ~1716, fields .forward=decoder_forward etc from models.cu:485-552, .hidden_dim/.output_dim/.continuous) — ADD create_custom_decoder(env_name,&decoder) mirror hook in ocean.cu + call it after the inline init. Decoder output layout must stay (B, 12+55+8 logits [+value?] — check decoder_output_size=act_n+1 and how sampling slices heads). Encoder-activations sharing for keys: file-scope statics in nethack.cu set at reg_train/reg_rollout (store ptr + its B; decoder forward picks by input.shape[0]; cudagraph-safe since fixed after registration). Custom decoder FULL SPEC: DefaultDecoder = ONE linear weight (output_dim+1, hidden) → out (B, 75+1), value at LAST index, sampling slices heads by act_sizes offsets over that buffer (models.cu:475-545). NethackDecoder weights: lin_w (21,512) [12 verb|8 dir|1 value] + ptr_q_w (32,512). Fwd: tmp = in@lin_w', q = in@q_w', assemble kernel: out[:,0:12]=tmp[:,0:12], out[:,12+i]=dot(q_b, inv_out[b,i*32:+32])*rsqrt(32) (keys = encoder a->inv_out rows, POST-relu), out[:,67:75]=tmp[:,12:20], out[:,75]=tmp[:,20]. Bwd: split grad_out → dtmp/dslot; dq[b]=Σ_i dslot[b,i]*s_bi (kernel B×32, loop 55, deterministic); keygrad[b,i,:]=dslot[b,i]*q_b into decoder-owned (B_TT,1760) buffer; dW: splitk both; dinput = dtmp@lin_w + dq@q_w (add kernel). ENCODER SIDE: nethack_encoder_backward after nh_slice(inv_grad←concat) does nh_add_inplace(inv_grad += keygrad) BEFORE relu_bias_bwd (both consumers are post-relu ✓). Wiring: file statics in nethack.cu {enc acts ptr + B} for train & rollout set at reg time; decoder picks by input.shape[0] (B_TT 32768 vs rollout 512, distinct); keygrad ptr static for encoder. Hook: add create_custom_decoder(env_name,&decoder) in ocean.cu + call in pufferlib.cu after inline Decoder init (~line 1727). cudagraph-safe (ptrs fixed post-registration). Remaining backlog: tinybox sweep on new coef set, demo port (very stale now — 3 heads), pointer head (pending potion-restricted diagnostic), ugangr. GOTCHA: multi-file python-batch edits — assert-all-before-write per file, and remember partial application across FILES when one assert fails (later files untouched, earlier seds may have run). NOTE one teardown SEGFAULT after a completed run (post-dashboard, exit path; 1 in ~20 runs today — watch, don't chase). Checkpoints broken again. Demo port still owed. Next levers by evidence: QUAFF/READ/ZAP verbs (combat deaths 92% at XL~4 = the wall; food NOT binding — embed-64 tripled eats, zero score), pointer head if slot generalization stalls, fresh tinybox sweep on new dynamics.
1-OLD-PROGRESS: encoder fwd+bwd is BIT-DETERMINISTIC across processes (scratchpad det_enc.py, gradhash f1d628e00fba64ab x2, B=64 x3 iters) — nondeterminism is NOT in src/nethack.cu. Remaining suspects: cublasLt algo selection on TRAINING-scale NEW shapes (decoder atn 23->78, proj concat 536->1415, B_TT=32768) possibly picking split-K (nondet float atomics), or multi-head sampling path (convert-style envs never had an oracle — the multi-head training path is oracle-UNTESTED territory). Classification result: runs 3/4 = 26a0f589b34475ca / 9cd1b1bed50982d2 — ALL FOUR DISTINCT = continuous accumulation-order nondeterminism (not an algo flip). Encoder RE-exonerated at B=8192 hidden=512 (gradhash 19c89971ac349258 x2) — src/nethack.cu is clean at scale too. Remaining suspects, in order: (1) DECODER path with atn_dim 78 (23+55) — its GEMMs/backward at B_TT never ran under an oracle at this width; check puf_mm algo for (B_TT,512)x(512,78) wgrad reductions; (2) multi-head sampling/logprob/entropy kernels in pufferlib.cu (never oracle-tested — convert had no oracle); (3) MinGRU/muon shape-independent paths (unchanged, unlikely). Next bisect: freeze policy updates (lr=0) and hash rollout trajectories x2 (isolates sampling/eval from training math), then hash decoder grads standalone. NOTE runs 1/2 were pre-inv-sync-fix build, 3/4 post — 3 vs 4 same-build mismatch is the valid evidence.
2-FIXED (engine, goldens 34/34 PASS): winrl.cc fill_obs syncs inventory_ once per game when obs->inv_glyphs is bound (update_inventory callback only fires on CHANGES; starting inventory predates the moveloop). inv_synced_ member on NetHackRL. Note: sync lands on the FIRST c_step (nle_start/drain predate moveloop, fill early-returns) — reset-time obs still has stale/empty inv for exactly one decision; slot actions verified live from step 1 (slot_probe.c: food slot 'g' eats +1, wrong slot ESC +1 illegal).
2-ORIG: INV BUFFERS EMPTY AT RESET: slot_probe.c right after c_reset found inv_letters all zero (probe food/nonfood = -1, EAT with any slot ESCs "Never mind"), yet training logs show carried eats happening — so inv_* side buffers fill only after some step/inventory-update callback, not by nle_start+drain. Consequences: first-obs inv block all pad; slot actions dead until first fill. Fix candidates: force an update_inventory/fill at reset (winrl fills inv in fill_obs? check the inv gate from the speed campaign — likely gated on program_state or a dirty flag), or env-side no-op step at reset. Probe: scratchpad slot_probe.c.

2026-07-11 REST SHIPPED (verb 13, NETHACK_NUM_ACTIONS=14; user-approved single experiment while tinybox sweep runs — local checkout only, sweep unaffected): macro = NetHack-native count-prefixed search `20s` — c_step sends '2','0' (digits build count, no turns, each its own nle_step, done-guarded) then 's' which runs the multi-turn search OCCUPATION inside one nle_step with the game's native interruption (monster/pet/damage aborts it). Distinct from SEARCH verb 5 (single 's' = probe-this-wall vs camp-until-healed). No new reward terms (hp potential pays banked regen, hunger decay is the natural cost). rests metric (Stats/Log/binding). Encoder NH_ACTIONS 14 -> BL_FEAT 78, CONCAT 2286; test literals updated; gradcheck PASS. Probe (scratchpad rest_probe.c; compile needs -I vendor/fast-nle/build/_deps/deboost_context-src/include for fcontext): 1045 rests, avg 13.9 game turns/env step, hist peak 14-16, ~10% full 20-21, ~10% instant abort (adjacent pet/monster), pet-action messages legitimately interrupt ("kitten drops a gold piece") — authentic occupation behavior. ALL CHECKPOINTS BROKEN (verb head + bl_feat); demo needs a REST-era ckpt. **DET ORACLE (14-verb REST build): 1bd8681f267da6f6 x2.** 200M VERDICT — **REST FLIPPED THE EQUILIBRIUM TO A PROFITABLE DLVL-1 XP FARM: score 1929 (campaign best, +27% over 1519) but depth 1.115**; game_time 11992 (4x dive runs), rests 769/ep (~10K of 12K turns spent resting), eats 55.7, prayers 11.9, XL 5.5, ups_hurt 0.001 (never needs retreat — heals in place). CAUSE: REST deleted the recovery deficit that made camping lossy (old camp equilibrium 639); dense repeatable exp income per kill (urexp=4x exper) out-earns one-shot clamped descent bonuses (~+4.5 total for the whole ladder to 5.5); PPO maximizes per-episode return (111.5) and safe-slow beats risky-fast (dive = 3x score/turn but 1/4 the lifetime). Demo eval (70 eps, 213M ckpt now in resources bin; user's old 13-verb bin backed up scratchpad/nethack_weights_13verb_user.bin): avg 1580, depth 1.20, DOWN_STAIRS pressed ONCE in 120K steps, REST = 38% of ALL actions, deaths 90% combat but killer_lvl 1.0 (dies to trivia when farm luck runs out), QUAFF verb spammed 8K presses -> 62 real drinks (mask fallback slot -> cheap illegal; cosmetic). Score/turn: farm 0.16 vs dive 0.5 — farm likely plateaus ~2K (XL curve doubles, dlvl-1 spawn throttled) while dive line was still scaling (1177@100M->1613@200M). OPEN: dive-vs-grind pricing is exactly the sweep's descent/xp axis — read winners before repricing by hand; alternative = depth-scaled descent income. REST itself is mechanically validated (interruption, regen banking work). FIX SHIPPED same day (user: "mask rest at full hp and rerun"): REST masked when NLE_BL_HP >= NLE_BL_HPMAX (one line beside the satiated-EAT gate) — healing use survives, fast-forward button gone. **ORACLE (masked-REST build): 7b2489be199b1055 x2. 200M VERDICT — BEST HONEST RUN EVER: score 1806 (+19% over 1456-1519 pre-REST band, vs farm's 1929), depth 5.60 (dive regime fully restored), game_time 3680, rests 119.8/ep (intended role), regen_ticks 67 (most healing ever, spent while hurt), damage_taken 225 vs pre-REST 77 (3x combat throughput absorbed and survived), XL 5.04, prayers back to 3.1, quaffs 2.56, illegal 25.6.** ups_hurt still ~0 — retreat unnecessary when you can heal in place. Demo weights bin = this run's 213M ckpt (farm ckpt was briefly in the bin before it). Lesson pattern: new capability verbs may need a legality gate tying them to their intended purpose, or the policy finds the degenerate use (EAT/choke -> satiated mask; REST/farm -> full-HP mask). Masked-REST demo (47 eps): avg 2270, depth 3.38, max dlvl 7, deaths combat 66%/starved 0%, burst_turns COLLAPSED 32->8.5 (slow-bleed death mode CLOSED; residual deaths are <9-turn spikes needing avoidance/pre-softening, not recovery) — BUT EAT = 44% of all presses (52.8K presses, ~8 real eats/ep): with REST masked at full HP the policy adopted empty-prompt ESC (zero turns, -0.003) as the next idle button. VERB-ITEM MASK SHIPPED (user-approved): item verb masked when its slot head has no legal item (head_verb[5] beside head_oc; s[0]=1 fallback kept for the sampler). Trade-off accepted: EAT-with-empty-pack on floor corpse now masked (floor offer fired pre-prompt) — didn't bind (floor_eats UP 0.47->1.25; agents carry rations). ORACLE (verb-mask build): 142e4d2a2607218c x2. 200M: score 1638 (vs 1806 rest-mask single seed — likely noise, still above 1456-1613 history), depth 5.33, **item-use quality step-change: wears 0.39 (14x), zaps 0.61 (13x), throws 9.5 (2.4x), quaffs 3.5, eats 33 (casual overeating, harmless), prayers back to 1.5**, illegal 38.8 (UP from 25.6 — residual prompt mismatches scale with 14x more item attempts), rests 119, regen 70, game_time 3598. Masked verbs = pressable verbs always mean something -> discovery of rare verbs (wear/zap) unblocked. DEMO-BUILD GOTCHA (bit me here): `bash build.sh nethack` rebuilds ONLY _C.so; `--fast` rebuilds ONLY ./nethack demo — the demo statically compiles nethack.h (mask fill included), so ANY env/mask edit needs BOTH builds or demo evals run stale semantics. Stale-demo signature: policy trained under a mask, sampled without it -> spams the newly-unmasked actions it never learned to avoid (EAT/QUAFF/THROW = 85% of presses, 7K-step episodes). Discard such evals entirely. EDIT GOTCHA (repeat offender): `case NETHACK_ACT_ZAP:` appears TWICE in nethack.h (slot-dispatch switch + verb switch) — batch-edit anchors must include the next line.

GOTCHA (pgrep self-match variant #5): a guard `pgrep -f "pu[f]fer train"` INSIDE a script whose later lines literally say `puffer train nethack ...` matches the script's OWN cmdline — the bracket trick protects the pattern from itself, not from other literal text in the same script. 3-4 "trainer live" aborts were FALSE. Fix: anchor as `pgrep -f "venv/bin/pu[f]fer train"` (real trainer cmdlines contain venv/bin/, bare launch lines don't).

## 2026-07-12: pointer decoder v3 + pooled inventory (trunk diet) — SHIPPED
User-approved arch change (no obs/env change; obs still 3616B v3):
- ENCODER (src/nethack.cu): trunk no longer sees the 1760-dim inventory flatten. inv_out (B,55,32) stays as pointer keys; new inv2 (128x32 + bias) maps each slot 32->128 with elementwise max over slots FUSED in kernel (patch-encoder trick: (B,55,128) never materializes; argmax saved; fxp smem backward; ds lands in inv_grad with every entry written so no memset). NH_CONCAT 2286 -> 654 ([loc 256|glb 128|inv_pool 128|bl 64|blfeat 78]). bias_acc gained a 7th segment; nh_bias_flush_kernel now takes 7 outputs.
- DECODER: the old NH_PTR_DECODER env-gated pointer decoder (stale 77-logit single-slot-head layout) rebuilt as v3 and made UNCONDITIONAL for nethack (ocean.cu): [14 verb | 5x55 slots | 8 dir | value]. Five per-verb queries (q_w 160xH), shared keys k_w (32x32) over inv_out, per-head learnable tau (init 10, barely moves: ~9.99 at 200M), cosine logits. lin_w (24xH, 23 rows used) for verb/dir/value. keygrad -> encoder inv slice wiring unchanged (enc reg immediately precedes dec reg per buffer in policy_reg_*; pairing verified in models.cu).
- Net params: -0.9M (proj 1.17M->335K, dense decoder 153K->95K, +4K inv2). Slot identity now position-invariant via keys; canonical inventory reordering NO LONGER NEEDED.
- Tests: tests/test_nethack_cuda.cu + test_nethack_encoder.py now cover the DECODER too (float64 torch ref: fwd values, lin/q/k/tau grads, keygrad, grad_input) plus inv2 in encoder refs; inv2_w in fd_skip (shared max-pool weights). PASS at ~1e-7.
- ORACLE: 97496c5909d3acdf x2 (supersedes 142e4d2a2607218c; interim 5428344e was pre-tau-pad).
- 200M RESULT: train score 1716 / depth 5.74 (best-ever depth; vs 1638 verb-mask, 1806 rest-mask); corrected-checkpoint CUDA eval 1739.6/5.73.

### CHECKPOINT ALIGNMENT GOTCHA (cost a debugging session — READ BEFORE ADDING PARAMS)
Every param tensor MUST have numel % 8 == 0. The bf16 param allocator aligns each tensor to 16 bytes (8 bf16 elems), but master_weights (fp32, saved/loaded as the .bin) is an ELEMENTWISE flat cast of the first total_elems elements — if a tensor breaks the multiple-of-8 rule, param block gets a real gap, master/optimizer walk compactly => the file layout after that tensor is [tensor | orphan-optimizer-junk pad | rest shifted, last pad-size elems TRUNCATED]. tau was first offender (5 elems): fixed by padding tau to 8 (NH_TAU_PAD; entries 5..7 dead). The 200M ran on the {5} build: its checkpoint = [.. tau(5) | 3 muon-orphan floats (~65!) | mingru minus last 3]. Correct conversion to {8} format: APPEND 3 zeros at END (the 8-slot tau region already exists as tau5+orphan3). I first wrongly INSERTED 3 after tau -> every mingru weight shifted by 3 -> policy collapsed to score ~50/depth 1.05 in BOTH demo and fresh-load CUDA eval while training dashboard said 1716. Debug ladder that found it: demo low -> CUDA rollout-only eval also low (demo exonerated) -> train() interleave recovers fast (weights mostly good) -> rollout-only SUSTAINS after recovery (no runtime-state dependency) -> inspected 3 floats after tau: 65.09/-0.135/65.38 = optimizer orphans, not zeros -> layout understood. puffernet demo loader assumes multiples-of-8 too (get_weights_aligned rounds cumulative idx to 8).
- Demo port updated (pool loop + 5-head cosine pointer + new float accounting incl tau pad; arch inference: ENC_FIXED has inv2, DEC_FIXED = 1024+8, H*(654+1+24+160)).
- CORRECTED DEMO EVAL (pointer+pool 200M, 97 eps): score 1822.9 / depth 5.87 / max dlvl 10 — BEST honest result (vs 1669 verb-mask demo, 1806 rest-mask train). Areas mines 46%/minetown 26%/deep 10%/main_d5 38%. NEW BEHAVIORS: Elbereth 8.6/ep (was 0.2), hurt-retreat loop (UP presses 102/ep, ups_hurt 94.6 — climb when hurt, REST 173/ep regen 106, re-descend). wears DROPPED to 0.05/ep (73 presses; pointer keys may not separate armor well — watch; item-state obs break feeds keys directly). deaths combat 94% killer_lvl 2.8 burst 22.5 maxhp 39.9; burdened 7.2%.
- 2026-07-12b (post-review hardening): tau -> LOG-tau (raw tau crossing 0 would NaN the backward, which divides by it; chain rule dltau = tau*sum(g*cos); init logf(10); demo/test mirrored; resources bin tau values ln()-converted in place). ORACLE: b88b75c14fe5a39d x2 (CURRENT; supersedes 97496c59; matched even with a concurrent eval process on the GPU). Review pushback: empty-slot masking in the cos kernel is REDUNDANT — the action mask already excludes empty slots per class-tight head at sampling AND train logprob recompute, so their logits never enter a softmax and upstream grad is exactly 0 (backward kernels early-out on gi==0). Parked experiment candidates from review: mean-pool alongside max (dense backward for mean path is the work), factorized glyph embedding (insert as materialized E_eff at top of forward; existing dE paths retarget E_eff grad).

## 2026-07-12c: item-state obs v4 SHIPPED — but run confounded by FARM RETURN
- obs v4 4056B: engine exports inv_state (8 int8/slot, doname-gated: buc/bknown, spe/known+class, quan, ero1/2, flags[worn,wield,swap,quiver,poison,grease,proof-rknown], typeknown). 34 goldens PASS (flag reads, no RNG). shuffled_glyph already de-leaks identity (appearance glyphs) — existing obs was honest. Encoder: 17 feats via inv1s_w (32x17=544, mult-8 ok) beside embed in slot MLP; keys/pool unchanged. Gradcheck PASS. Probe validated gating live. ORACLE: 38e32b2dc99aa18d x2 (CURRENT).
- 200M RESULT: score 2220 train / 2861 demo BUT depth 1.14, THE SPAWN-CAMP FARM AGAIN (hp-mask hole: agent stays slightly hurt so REST stays legal; heal loop = pray 10.5/ep + quaff + rest 253/ep; demo eps avg 8371 steps, HALF TRUNCATE at 10K cap, throws 58/ep at spawns). Item-state likely made the farm MORE sustainable (heal-economy management). Experiment confounded — no verdict on item-state value for descent play until farm closed.
- Farm-fix candidates: (1) RECOMMENDED REST gate hp <= 3/4 hpmax (time-banking dies; SEARCH-camping costs 1 press/turn vs 10K step cap; trims top of legit heal loop), (2) truncation pays death penalty (hurts nothing else much), (3) reward surgery on exp income (invasive, sweeps affected). Weights bin = farm ckpt (obs v4 demo validated: 3,670,872 floats).
- REFRAME (user decision 2026-07-12): farming score is LEGITIMATE — score is the objective (NLE NetHackScore task + NetHack Challenge rank by ascensions-then-median-score; our logged score is real botl score). Do NOT add further REST/wait gates. Item-state verdict: NEW BEST 2220 train / 2861 demo (+57% vs pointer+pool 1823). 10K-step episode cap is part of the benchmark definition (farmed score scales with cap — never change it casually). Depth becomes a secondary metric; later: sweep with metric=depth to force descent when wanted (sweep.metric currently score).

## 2026-07-12d: ROTTEN-FOOD LEAK found+fixed; leak-free rerun = DOUBLE TRANSITION
- Invariance test (scratchpad invariance_probe.c, KEEP recipe): bind obs.inv_strs (doname = player's literal view), assert field<->string both directions live over 100K steps. FIRST RUN CAUGHT A REAL LEAK: erosion bits are overloaded storage (#define orotten oeroded rotten food / odiluted potions / norevive corpses); doname prints erosion ONLY from weapon/armor/weptool/ball/chain class branches — NOT is_damageable (food is "damageable" via is_rottable, still never displayed). Export now class-gated: 831,555 checks, 0 violations. Goldens 34/34 still pass. Also: quan was already clamped 127 at export (reviewer NaN concern not live); defensive fmaxf added in kernel/demo/test anyway.
- The 2220 farm PB trained WITH the leak (eats 24/ep — rottenness vision fed the farm food economy). LEAK-FREE 200M RERUN: descent 4.6 -> farm (~1.1, score 1450->2000) -> BACK to descent (first-ever farm exit!), converged 1775/depth 5.69. Leak was worth ~250-400 pts to the farm; leak-free farm (~1850-2000) ~ parity with descent (~1780-2150) -> attractors near value-degenerate, policy can oscillate. Honest item-state marginal vs pointer+pool (1716/5.74): ~+60, noise-level on train score.
- ORACLE: 5fc0c5bc83301b3b x2 (CURRENT). Phase-transition analysis (both leaky runs): descent to depth ~6 then abrupt farm switch w/ transient collapse (score 176 valley), identical farm fingerprints across seeds (throws 56/58, rests 253/262, prayers 10.5/10.9 = prayer-as-food-on-cooldown, prayers_low_hp ~0). Punctuated equilibrium; descent-peak checkpoints worth preserving (run 1783853671032 has ~140M-step descent ckpts).
- LEAK-FREE DEMO EVAL (30 eps): avg 1963.9 / depth 5.43 / max dlvl 12 — NEW HONEST BEST (+7.7% vs pointer+pool 1822.9). Policy is a HYBRID: mostly descends (mines 40/minetown 17/main_d5 43%), ~20% of episodes settle into farm mode and ride the cap (right tail 3600-7030; median 1428 vs mean 1964 — mean is tail-driven). 40% episodes truncate. wears still ~0.07 (Monk body-armor hypothesis: refusing armor may be correct martial-arts play, not a pointer defect). Weights bin = this ckpt.
- ESTIMATOR CORRECTION (2026-07-12): demo means are NOISY on tail-heavy policies (n=30, SE ~±290; farm-tail draws dominate). Frozen-policy CUDA eval (load ckpt, rollouts-only, ~2000 eps) is the headline estimator: pointer+pool 1739.6 vs leak-free item-state 1748.1 — item-state marginal on score ~= ZERO (earlier +7.7% demo claim was tail sampling luck). Train-dashboard lags final policy only when still improving (farm run +29% lag; converged runs ~0). Item-state's real effects are behavioral: hybrid strategy mix, item-economy sharpness, leak exploitation capacity.
- RECURRENT-STATE SEMANTICS GAP (2026-07-12, important): native rollouts NEVER zero mingru state on episode done (mingru_gate sees no terminals; state carries across episodes). Demo zeroes per episode (NLE convention). Same weights behave differently: zero-start -> 20% farm-mode, len 3793, 40% trunc, demo 1964; carried -> descent-dominant, len ~950-2150, trunc 0-15%, 1748-1867. Strategy selection lives in the state's initial condition. Carried-state single-stream demos can trap degenerate loops across episodes (saw eats 190/ep nibble loop; training's 512 parallel streams dilute this to 10.7). Demo has NH_KEEP_STATE=1 env-var toggle for carried-state evals. For NLE-comparable numbers: zero-start with LARGE n. Fixing rollouts to zero-on-done = training-semantics change + new oracle — user decision, not taken.
- HORIZON 256 EXPERIMENT (2026-07-12): WORSE at 200M — train 1588/depth 4.73, frozen eval 1678/4.82 (vs h64: 1775 / 1748/5.68). Pure descent (never found farm), plateaued ~5.3 at 60% then drifted to 4.7. Same minibatch-update count but 4x fewer policy iterations (1526 vs 6103 epochs) — slower convergence dominates any memory benefit at this budget. REVERTED (was CLI flag only; config untouched); weights bin restored to leak-free h64 ckpt (run 1783856794734). PGREP GOTCHA: guard `pgrep -f "pu[f]fer train"` matches its own compound command if the launch string is in the SAME command line — run guard and launch as separate calls.

## 2026-07-12e: FACTORIZED EMBEDDING (residual) — s42 paired win; ENGINE CRASH REPRODUCER FOUND
- E_eff = E_res + E_kind[14x32] + E_sub[944x32], zero-init factors (init function == baseline). Mapping GENERATED from engine display.h macros (scratchpad gen_glyph_map.c -> src/nethack_glyph_map.h, exhaustiveness+species-share asserted; sub shares one row per species across mon/pet/detect/body/ridden/swallow/statue incl the 3048-glyph swallow block; NH_GM_QUAL macro for host/device include). Backward: embed_wgrad IS dE_res; CSR row-sum kernels for factors. BOTH backward weight-grad GEMMs (dw_perm, inv1_wgrad) must use E_eff not E_res. Gradcheck PASS. ORACLE: f3ed7d298c0f8600 x2 (CURRENT).
- PAIRED s42 result (only variable = factorization): frozen eval 1748->1957.7 (+12%), depth 5.68->6.07 (best-ever plateau 6.1), smooth descent, no farm phase. MECHANISM CONFIRMED: pet/detected<->monster cosines 0->+0.10..0.14, corpse<->monster -> -0.14 (shared species content, kind vectors oppose: threat-vs-food separation); untouched kinds (ridden/zap/explode) exactly 0.00 = negative control. Basin-luck dominates cross-seed: s123 farm-from-birth 1190/depth 1.1. --train.seed does NOT diversify runs (3 bit-identical 200M runs = strongest determinism demo yet); use top-level --seed.
- ENGINE SEGFAULT REPRODUCER (the sweep-killer class): seed 777 crashes deterministically at ~43M steps (exit 139) in attack_checks() <- attack() <- domove_core() (uhitm.c), mov 0x30(%rdx) — likely stale/dead mtmp (mtmp->data deref). gdb backtrace in scratchpad gdb_seed777.log; O0-debug repro in flight. Repro: puffer train nethack --seed 777, dies ~21% in.
- Multi-seed factorized finals: s42 descent 1979.8/6.11 (frozen 1957.7/6.07), s123 farm-from-birth 1202.6/1.12 (frozen 1189.9), s777-under-ASAN farm 1638.9/1.13 (completed clean!). Basin choice dominates cross-seed variance; paired s42 (+12%, +0.4 depth) is the evidence.
- CRASH HUNT UPDATE: ASAN run of seed 777 completed 200M CLEAN (zero reports) -> UAF RULED OUT. Crash is heap-content-dependent (O0 runs crashed at different sites: newsym display.c:863 / attack_checks uhitm.c:158, both deref m_at(x,y) grid pointer), multi-env-only, invisible to ASAN => uninitialized heap read (MSAN class — fork's msan-hunt branch exists for this) OR cross-thread race. Single-thread discriminator run in flight (--vec.num-threads 1, seed 777). Artifacts: scratchpad gdb_seed777.log, gdb_o0_seed777.log, gdb_autopsy.log, asan_seed777.log; ASAN build at vendor/fast-nle/build-asan (ENABLE_ASAN cmake opt; run with LD_PRELOAD="libasan.so build-asan/libnethack.so" ASAN_OPTIONS=protect_shadow_gap=0:detect_leaks=0 — CUDA works).

- 2026-07-12f: REMOVED the full-HP REST mask (was `HP>=HPMAX -> mask REST`). Reasoning: it's a strategy-shaping mask on a VALID action, not a validity mask; under the score objective + farming-is-legitimate it has no principled basis (idle-banking turns for spawn-XP is a legit score strategy). Empirically it never stopped farming anyway (masked heal-cycle farms hit 1975-2220 vs unmasked free-idle 1929) — removing lets the agent pick its own score-optimal policy. Only REST gate left: none (REST always samplable). EAT-satiated + verb-item masks unchanged. ORACLE: f74af441d94fb415 x2 (CURRENT; supersedes the HP>=HPMAX era). Env-only change (no encoder/gradcheck). Head-to-head 200M vs factorized baseline (f3ed7d29 oracle, frozen-eval 1958/depth6.07) NOT yet run — user said just remove.

2026-07-13 TRIGRAM MESSAGE ENCODER SHIPPED (user: "implement the message encoder"; design converged over prior turns w/ user's chat agent). NetHack topline was the biggest thrown-away signal (combat detail, ID hints, prayer/altar feedback, shop prices) — already captured in env->message[256] every step, just never packed into obs. **Trigram bag** (char-trigrams -> hash NH_MSG_VOCAB=4096 buckets, key=(c0<<16|c1<<8|c2)*2654435761u>>20 on lowercased chars, keep spaces -> NH_MSG_HID=32 embed -> normalized SUM scaled 1/sqrt(count+1), concat RAW no-relu like bl_feats). Sum not max (bag=vote-not-existence; also dodges argmax-scatter contention that makes nh_patch_max_bwd the top kernel — sum bwd is flat broadcast scatter-add). GPU hashes from raw chars (obs +NH_MSG_LEN=128 bytes tail, smaller than pre-hashed ids + keeps CPU free). Files: src/nethack.cu (constants NH_MSG_*; NethackEncoderWeights.msg_w 4096x32; acts msg_ids(FloatTensor fp32 - hash ids up to 4095 need fp32 like glyph_idx, NOT bf16), msg_out, dmsg_acc(LongTensor fxp), msg_wgrad; kernels nh_msg_lc/hash/ids/pool/bwd; nh_concat_kernel +msg arg; fwd ids+pool before concat; bwd memset+scatter+fxp_to_precision; init puf_normal_init; reg_params/train/rollout msg_w+acts, msg_wgrad registered LAST to stay pairwise-aligned w/ params for muon). Env ocean/nethack/nethack.h: NETHACK_OFF_MSG/MSG_LEN 128/OBS_SIZE; pack_obs strnlen+memcpy+memset pad. Test shim TENSOR_ACC/GRAD_ACC(msg_w); test_nethack_encoder.py make_obs random lowercase msgs, torch_encoder trigram-bag ref (threaded msg through torch_check+dec_check). obs 4056->4184B, concat 654->686. **Gradcheck PASS (msg_w FD 2.28e-3, torch-exact 4.62e-8). DET ORACLE d6ea4e80b7ae5c8c x2 (was 71f23e53). 5M train runs clean/deterministic.** SPS impact expected low-single-digit % (compute negligible; cost is +128 obs bytes hitting copy-bound rollout) — NOT yet measured. NOT DONE (follow-ups): (1) entity channel (text-match monster/object names in the same msg field -> E_eff share; the FAIR way vs pline-hook typed entities which LEAK hallucination/unID ground truth); (2) demo ocean/nethack/nethack.c mirror lacks the msg branch + needs new weights (training unaffected); (3) all checkpoints incompatible (arch change) - train from scratch. Levers if underperforms: bump NH_MSG_HID 32->64, IDF/stop-trigram down-weight, multi-line topline capture (winrl change, reopens goldens).

2026-07-13 MESSAGE ENCODER — FIRST RESULTS (farming config, no-msg baseline seeds 1/2 = 2655/2880 @340M): message-on scored 2991 (seed73 @280M) and 3011 (seed7 @340M) — both ABOVE baseline band, +130..+360 on the step-matched seed7, consistent across 2 seeds (not a lucky draw). Depth UNCHANGED ~1.13 (still farming) — messages buy score WITHIN the farm (combat/ID/prayer feedback), not deeper descent. SPS cost small but real: seed7 steady 158.8K vs no-msg 174K (~9%, fully heat-soaked over 340M; seed73's 176K reading was less throttled). Not yet run: matched-seed A/B or deep-dive config (where msgs should matter more). Entity channel = next value-add.

2026-07-13 MESSAGE ENCODER 3-SEED (farming, no-msg baseline 2655/2880 @340M): msg-on = 2991(s73@280M), 3011(s7@340M), 3285(s11@340M). Two 340M runs mean ~3148 vs no-msg ~2767 = +380, consistent across 3 seeds. Depth ~1.1 throughout (farming; msgs improve HOW it farms not regime). PRIVILEGE AUDIT PASSED: obs->message is display-only (winrl toplines/msg-window, cleared each step no-stale), NOT wizard mode (name Agent-mon-hum-neu-mal), respects hallucination/ID (mon_nam/xname render partial knowledge - can't leak true species/otyp), bag sees strictly less than full line. Only benign edge: disclose:+ end-of-game text could hit terminal post-death msg (post done=1, unexploitable). Whole obs remains player-visible.

2026-07-13 MESSAGE ENCODER 4-SEED (farming): +seed12=3160@340M. Three 340M msg-on seeds cluster tight: 3011/3160/3285 (mean 3152) vs no-msg 2767 (2655/2880) = +385 ~14%, well-replicated. Depth ~1.1 all (farms better not deeper). SPS ~160K steady (~8-9% cost). WHY IT HELPS (structural, high-confidence): message is the ONLY obs channel carrying EVENT feedback (hit/miss/kill, incoming-attack cause, action success/failure of factored verbs) vs glyphs/blstats=STATE; de-aliases actions whose only effect was a message (miss=no-op before) -> cleaner credit assignment; agent auto-dismisses prompts so was acting blind to this modality. Prayer-clock ablated so message is now the fair prayer-outcome signal. Which channel dominates = unmeasured (probe TODO). Validated real win.

2026-07-14 RUNG-2 ENTITY CHANNEL SHIPPED (grounds monster names in the topline into the shared glyph embedding; param-free): env-side matcher (nethack.h) scans obs->message for monster names -> base monster glyph ids (GLYPH_MON_OFF=0 so id==permonst index), packs up to NETHACK_ENT_MAX=8 int16 LE after the msg block; obs 4184->4200B, NETHACK_OFF_ENT. Name table = generated ocean/nethack/nethack_entity_names.h (scratchpad gen_entity_names.c dlsyms mons[] from libnethack.so, 381 names). Matcher = first-char buckets sorted longest-first, case-insensitive, WORD-BOUNDARY, longest-match ("gnome lord" beats "gnome", "sewer rat" real; "yourself"/"combat"/"scrape" reject "elf"/"bat"/"ape"). FAIR: reads same bytes as trigram bag, monster glyphs unshuffled (identity==appearance), hallucination fake names miss table -> silent. Encoder (nethack.cu): nh_ent_ids_kernel decodes (0xFFFF/>=vocab -> -1 sentinel, front-packed), nh_ent_pool_kernel normalized-sums E_eff[id] rows (NH_EMBED_DIM=32, 1/sqrt(count+1)) -> concat[718] after msg (NH_ENT_CONCAT_OFF); NO new params (bwd scatters into embed_wgrad=dE_eff via fxp accumulator BEFORE the ekind/esub CSR factor sums, co-trains E_res/E_kind/E_sub with map+inv). gradcheck PASS (torch-exact embed/ekind/esub/proj ~1e-7; bumped FD rel_tol 1.5e-2->2.5e-2, the sub-unit-grad ratio floors denom at 1.0 so it's an ABS tol at the fp32 FD roundoff floor ~1.6e-2, smaller eps is worse; entity landscape-shift nudged loc_b/inv1s_w over). matcher unit-test 12/12 (scratchpad matcher_test.c). ORACLE dbc6883c2af3aa94 x2 (was d6ea4e80). DETERMINISM GOTCHA (cost one oracle round): lazy static-index build raced the multithread env -> non-det hash; fixed with pthread_once (nh_ent_once). SCOPE: monsters-only v1 (objects deferred — appearance-shuffle means true-name->identity-glyph would break appearance-space consistency). Rung 3 (template-id + E_eff args, engine pline hooks) still deferred. 340M seed-23 run (wandb encoders/entity-channel) = score 3201.6, depth 1.13 — INSIDE the msg-only cluster (3011/3160/3285 mean 3152, spread ±270), +49 over mean = single-seed noise, NO score signal either way (as predicted; judge on 5-seed battery + forensic judges not one mean). SPS ~120K, within +-5K of msg-only (my earlier "160K" was a thermal-cold mid-run read; final SPS drifts to ~120K both) — entity channel is THROUGHPUT-NEUTRAL (param-free + SPS-free; no cost flag). Grounding-vs-binding open: chat-agent critique landed — rung 2.5 (positional grammar role-split) WITHDRAWN (hand-coded English = crosses curation line), rung 3 (engine-typed template+args) shelved-not-targeted (event-type redundant w/ bag; binding only bites at multi-entity messages). DECISION ROUTED BY 2 measurements (deferred to after-run, GPU now free): (1) multi-entity frequency = frac of non-empty msg-steps naming >=2 distinct species (routes whether binding is even a problem; prior small) via a Stats counter read off eval (random-policy harness undersamples combat); (2) trunk decoding probe: single-entity identity+event-type (clean labels, validates GROUNDING which is orthogonal to binding). Objects deferred indefinitely (would inject per-game dynamic state into a compile-time-static channel). KEPT the entity channel (user: "leave it") despite the inconclusive score — throughput-neutral so no cost, revisit-for-diving noted.

2026-07-14 ENTITY SUM||MAX SHIPPED (user "try the sum + max and run it"): entity summary now [normalized-sum | elementwise-max] E_eff, NH_ENT_HID 32->64, concat 718->750 (obs UNCHANGED 4200 — encoder-internal only). Max is raw (bounded, count-invariant, existence/salience-shaped — the codebase's own patch/inv max-pool pattern, apt for the <=8-element entity arm where the 250-voter trigram bag's sum is not). nh_ent_pool_kernel writes both halves + saves argmax (first-winner strict >, ent_amax IntTensor B×32); bwd: sum half scatters to all matched rows, max half routes to argmax winner only, both fxp->embed_wgrad before factor sums (still param-free). Launches use NH_EMBED_DIM=32 threads (NOT NH_ENT_HID) since each thread owns one embed dim across both halves. gradcheck PASS (torch-exact embed/ekind/esub ~1e-7; same-glyph-id ties harmless — same dE_eff row). ORACLE 257fbc0a0b82e3e9 x2 (was dbc6883c sum-only). 340M seed-31 run (wandb encoders/entity-summax, run n93n5u42) = score 3147.5, depth 1.13 — INSIDE msg-only band (mean 3152) AND FORENSICALLY IDENTICAL to entity-sum seed23 (3201): death_combat 0.840 vs 0.826, death_mon_level 1.236 vs 1.235, burst 25.0 vs 23.9, damage 281 vs 273, game_time 15089 vs 15356, XP 6.07 vs 6.12, quaffs 5.7 vs 6.0, prayers 15.3 vs 15.1 — every pre-registered judge within noise. VERDICT: the max branch is INERT; neither entity form (sum or sum||max) shows a score OR forensic signal in this farming regime (2 seeds, data-rich-regime prior confirmed). This config farms hard: 15K turns/life, killed by lvl-1 monsters, depth 1.1 — farming optimum not perception-limited. RECOMMEND revert sum||max -> sum-only (max added kernel+ent_amax+2x concat for zero signal; oracle back to dbc6883c) OR keep (costless). Text-encoder thread near evidence ceiling; NEXT = 2 cheap measurements (multi-entity freq counter, grounding decode probe) then PIVOT to diving config (real frontier + fair grounding re-test where data is sparse). NOTE trigram bag stays pure sum (untouched). NOTE these entity runs = current farming config, game_time 15K (vs pray-config 2884 era).

2026-07-14 ENTITY CHANNEL REVERTED (user "revert both"): whole rung-2 channel removed (git checkout of the 3 uncommitted files + rm generated header) — inert in farming (2 seeds forensically flat), a curation+maintenance surface not earning default inclusion; recoverable from this session's diff, re-attach as the experimental arm of a DIVING A/B (sparse-data regime = grounding's one fair test). Shipped encoder = committed message-only trigram bag (proven +14% floor). ORACLE FINDING: reverted build = b3b66c40ba4dfbf9 x2 (bit-det), obs 4184/concat 686/gradcheck PASS = byte-identical to committed HEAD 8215eb9c "text encoder + hypers". This does NOT match the memory's d6ea4e80 — because d6ea4e80 was baselined mid-commit BEFORE the "+hypers" config landed; b3b66c40 is the TRUE oracle for the committed message-only farming config. Progression on current committed config: msg-only b3b66c40 -> +entity-sum dbc6883c -> +entity-sum||max 257fbc0a. Text-encoder thread CLOSED for farming (grounding inert); next = pivot to diving config (real frontier + fair grounding re-test).

2026-07-14 SWEEP-CONFIG TRANSFER TESTS (user copying tinybox sweep winners from project nethack-decoderedered2, sweep ran PRE-text-encoder on another machine; we're on 8215eb9c = +message. KEY: the FARMING config we compare against is ALSO a pre-encoder sweep result, so the message-encoder tailwind is SYMMETRIC and CANCELS in cfg1-vs-farming — that comparison is fair; only absolute-vs-tinybox-reported numbers are confounded. Reward coefs (env block) are encoder-INVARIANT (upstream of obs) so transfer cleanly = why diving showed up; train hypers mildly encoder-sensitive. True optimum for current build unknown -> transfer tests are a cheap proxy; re-sweep-on-current-build is the expensive real answer if the good region proves sensitive): config/nethack.ini NOW HOLDS sweep-cfg1 (farming config recoverable via git checkout config/nethack.ini). cfg1 env: gold 0.0354 exp 0.259 descent 1.888 xp 0.281 scout 0.0169 hp 0.0190 hunger 0.0236 illegal -0.00695 death -0.634; train: lr 0.0131 gamma 0.9953 gae_l 0.730 replay 1.394 clip_coef 1.0 vf 2.968 vf_clip 4.084 max_grad 1.097 ent 0.00522 beta1 0.825 beta2 0.9936 vtrace_rho 3.877 vtrace_c 4.605 prio_a 0.746 prio_b 0.739 total_timesteps 179M. RESULT (seed73, 179M, wandb encoders/sweep-cfg1 run 0ntrxp7l): score 3058, DEPTH 3.11 (vs farming 1.1!), max_xp 5.9, death_combat 0.875/other 0.125, death_mon_level 1.74, game_time 10753 — a genuine DIVING policy. cfg1 rebalances reward away from kill-farming (exp 1.0->0.26) toward progression (xp/descent/hp up) -> escapes the depth-1 grind trap, claims the +50/level score term. Score 3058@179M ~= farming 3152@340M but HALF compute + 3x depth + still climbing at end => compute-matched likely ahead. clip_coef=1 = PPO band [0,2], clipfrac observed 0.000 (clip inert; stability from V-trace rho/c clip + adv-norm).

2026-07-14 cfg1 EXTENDED TO 340M (seed73, wandb encoders/sweep-cfg1-340m run 7l67krg8) — DIVING NARRATIVE OVERTURNED: score 3287 but DEPTH COLLAPSED 3.11->1.18, game_time 10753->15220, death_mon_level 1.74->1.20 = CONVERGED TO FARMING. The depth-3.11 at 179M was a MID-TRAINING TRANSIENT; the sweep (total_timesteps 179M) caught cfg1 in its diving phase, but its CONVERGENT behavior is farming. CORRECTION to "scores higher because it descends" (that was the 179M transient) -> the real story is BETTER GRINDING. Note: not a strict extension (anneal_lr=1 -> 340M run anneals LR over 340M, different schedule from step 1; same seed). KEY INSIGHTS: (1) the depth-1 farming attractor is ROBUST — cfg1's hard reward rebalance (exp 1.0->0.26, xp/descent/hp up) DELAYED but did not PREVENT farming convergence; reward-coef tweaks within sweep ranges won't hold diving. (2) FARMING OUT-SCORES DIVING: 3287 farmed > 3058 dived, so under pure score + 10K cap the agent converging to farming is CORRECT optimization — chasing depth may be FIGHTING the objective. Strategic Q surfaced: is diving actually the goal, or does score just reward farming? cfg1@340M=3287 sits at TOP of farming band (mean 3152, best 3285). config/nethack.ini still holds cfg1 (farming recoverable via git).

2026-07-14 cfg1 IS BIMODAL — seed-17 @340M REFUTES the seed-73 conclusions (classic pair-seeds-before-judging trap; I over-concluded from one seed): seed17 @340M (wandb run egncoo0i) = score 3807, DEPTH 3.89 (DIVING), game_time 9745, death_mon_level 1.98, max_xp 6.2. vs seed73 @340M = 3287/depth 1.18 (FARMING). SAME config, same 340M, seed decides the basin. RETRACTIONS: (a) "farming attractor robust / diving is a transient" FALSE — seed17 dives at full convergence; (b) "farming out-scores diving" FALSE — 3807(dive) > 3287(farm); (c) "chasing depth fights the objective" FALSE — depth 3.89 WON on score. CORRECT PICTURE: cfg1 has >=2 convergent strategy modes (farming ~3287/d1.2 vs diving ~3807/d3.9), basin is SEED-DEPENDENT (seed73 even shows a diving@179M -> farming@340M basin TRANSITION). Diving is a LEGIT high-scoring mode (best number seen), not a detour. 3807 diving is the top score of the whole exploration. IMPLICATION: judge configs on a MULTI-SEED battery (never 1); open Q = mode-split fraction + can we bias toward the diving basin (it wins).

2026-07-14 cfg1 @340M 5-SEED BATTERY (seeds 73/17/101/102/103, wandb encoders/sweep-cfg1-340m): BIMODALITY CONFIRMED CLEAN. FARM cluster: s73=3287/d1.18, s103=3392/d1.16 (mean 3340). DIVE cluster: s17=3807/d3.89, s101=3796/d3.91, s102=3816/d3.69 (mean 3806, spread ONLY +-10!). Two discrete attractors, tight WITHIN-basin (dive +-10, farm +-50), seed selects basin. Split 3 dive / 2 farm. KEY: (1) diving reliably beats farming ~3806 vs ~3340 = +14% across 3 indep diving seeds (not a fluke); (2) diving is the MAJORITY basin 3/5; (3) cfg1 DOMINATES old farming config on BOTH modes (its farm mode 3340 > old farm 3152; dive mode 3806 >> all) = strictly better config, only cost is seed-variance. cfg1 overall mean ~3620. s101 (wandb "smart-rain-111") segfaulted MID-TRAINING at 266M/340M (rc139) — NOT teardown (my earlier note was wrong); its 3796/d3.91 was the 266M dashboard value not a final eval, but already firmly diving so mode holds. HYPOTHESIS: diving runs reach deeper/more-varied states = more exposed to engine panic->segv edge cases (cf. crash-hardening memory) => diving may be more crash-prone than farming. Re-running s101 to 340M to confirm/get clean number. RERUN (wandb faithful-valley-114/pohcxyrr) COMPLETED CLEAN rc=0 to 340M: score 3873.6, depth 3.80, death_mon_level 1.88, max_xp 6.21 = DIVING confirmed. So the 266M crash was TRANSIENT not deterministic -> diving-crash-prone hypothesis WEAKENED (clean rerun). Clean full-340M DIVE cluster now s17=3807/s102=3816/s101=3873 (mean ~3832); FARM s73=3287/s103=3392 (mean ~3340); dive beats farm ~15%, 3/5 seeds dive.

2026-07-14 EVAL HIDDEN-STATE (user Q) — CORRECTED by repo maintainer (my first read was WRONG): the MinGRU state is 0'ed EACH EPOCH, NOT carried. Mechanism: reset_state DEFAULTS TRUE (config/default.ini:21) -> `if(reset_state) puf_zero(&graph.mb_state)` (pufferlib.cu:1595) zeros the TRAIN BPTT seed every epoch -> policy is TRAINED assuming zero initial state at the start of each horizon-64 sequence => effective recurrent memory <= horizon (64 steps), resets each epoch. (I over-read the rollout buffer_states carry and missed that the train seed resets each epoch, which is what actually shapes the learned policy.) MAINTAINER'S CORRECT-RECURRENCE TRIFECTA (has it in his latest "5c"): must do ALL THREE together — (1) 0 on term (episode done), (2) preserve state across epochs, (3) seed the train with the carried state. Miss ANY one -> WORSE than the current 0-each-epoch setup. So a partial change (e.g. eval-only reset-on-terminal) is expected to hurt, not help. IMPLICATION: the "cpu eval reset-on-term" experiment is a partial change (only #1) on a policy trained zero-each-epoch (<=64-step mem) -> off-distribution, would dip for the wrong reason; not a clean test. ALSO the CPU demo (nethack.c) is ARCH-STALE: DEMO_CONCAT lacks the +32 message branch (= NH_MSG_HID), so it can't run current message-encoder weights anyway. Checkpoints DO save: checkpoints/nethack/<wandbRunId>/<step:016d>.bin (e.g. pohcxyrr = seed101 rerun). Real path to test recurrence = implement full trifecta in training + A/B, or pull maintainer's 5c.

2026-07-14 SWEEP cfg2 5-SEED (env: gold 0.094 exp 0.136 descent 1.163 xp 0.258 scout 0.020 hp 0.0059 hunger 0.012 illegal -0.0082 death -0.774; train: lr 0.0164 clip 0.934 gamma 0.9949 gae_l 0.808 vf 2.66 vf_clip 3.15 max_grad 1.58 prio_a 0.967 total 130M; wandb encoders/sweep-cfg2; seed73@130M rest@340M, PAIRED w/ cfg1). RESULTS: s73@130M 2339/d4.14(dive), s17@340M 3591/d4.36, s101@340M 3486/d4.28, s102@340M 3572/d4.47, s103@340M 2930/d1.17(FARM). => cfg2 ALSO BIMODAL (340M: 3 dive/1 farm, same 3/1 as cfg1 -> bimodality is a property of the whole rebalanced-reward region, not cfg1-special). KEY: cfg2 dives DEEPER (d4.3-4.5 vs cfg1 d3.7-3.9) but scores LOWER (dive ~3550 vs cfg1 ~3832; farm 2930 vs cfg1 3340); cfg1 BEATS cfg2 on score EVERY paired seed. MECHANISM: reward shapes the STYLE of diving — cfg2 low exp(0.136)+low hp(0.0059) = RECKLESS deep dive (deeper, shorter lives game_time ~8000 vs cfg1 ~10000, less exp accum) = more depth/less score; cfg1 higher exp+hp = CAREFUL exp-rich dive = less depth/more score. (cfg2 has LOWER descent_coef yet dives deeper — gutting exp/hp makes farming unattractive + survival cheap.) VERDICT: for SCORE cfg1 wins; for DEPTH (deep-content/reset-curriculum research) cfg2 goes deeper (4.4). Both bimodal w/ tight dive clusters (+-50). NEXT LEVER: bias toward diving basin (already 3/5) -> push reward past phase boundary (more descent/xp, less exp) for unimodal-dive, OR state-set/reset curriculum to inject deep-content signal (discussed as potential research direction: reward-induced strategy bifurcation + reset-curriculum fix = workshop-tier finding).

2026-07-31 CHAMPION ARCH UPDATE (committed by user): action space = 19
MultiDiscrete heads — verb (22) + 12 per-verb item-slot heads (55) + **6
per-verb DIRECTION heads** (8 each: MOVE RUN KICK THROW ZAP APPLY, map =
nethack_dir_head() in netlib.h). Logits 730 (+value 731), mask width 730 ==
logits width (shadow-row machinery dormant). Decoder lin block 71 rows
(pad 72). THROW's dir row = target-ray mask; PUFFER_HEAD_GATING and
NETHACK_THROW_DIRMASK are DEFAULT-ON (=0 disables), flip bit-verified.
Champion recipe = ZERO FLAGS (eps 0.005 + anneal-start 0.4 also
defaulted; each =0 disables; probes must set PUFFER_VERB_EPS=0 for bare);
recert reference pv_s207 = 6403.2 (250M explicit). Arm 6501±276, record
pv_s211 = 6984, ablation −238 (aim lives in the head). KERNEL LANDMINE
CLASS (2 found): trainer hardcodes dormant until env grows — mask_stride
from A_total (fixed: stride from shape) and MAX_ATN_HEADS 16 stack arrays
in the PPO kernel (fixed: 32 + runtime guard; symptom = garbage gradients
with PERFECT rollout sampling → policy learns freeze exploit). Check 5c's
pufferl.cu for both during migration. NETHACK_DEBUG_ACT=<file> knob dumps
verb,slot,dir,mask-bits per step (skips reset transients).

2026-07-31 5C PORT (task #101, worktree /puffertank/pufferlib-5c branch
5c-nethack, ALL UNCOMMITTED — user commits): champion stack transplanted onto
upstream HEAD 67a69341 in ONE session; ./puffer train nethack RUNS (5M smoke:
score 41.9, all 19 heads firing under eps-floor, carry semantics on).
FACTS: (1) their ocean/nethack snapshot was our env at ~affdb64e vintage
already adapted (nethack.cu differed by 27 lines = no free_* hooks +
activation_size; macros.h/fs.h/glyph_map.h byte-identical); encoder "port"
= sed rename PrecisionTensor/FloatTensor/ByteTensor/IntTensor/LongTensor →
Prec/Float/Byte/Int/Long. (2) upstream already HAS action-mask sampling
(always-allocated, mask_size from config [vec] action_mask_size — SET 730!)
+ head-consume gating (same weak symbol; PUFFER_PROVIDES_HEAD_CONSUME_MAP
define when env provides it in-header) + per-head arrays sized [NUM_ATNS]
(both our kernel landmines absent by construction). (3) PORTED: whole
committed env into their pufferenv.h frame (their Env struct = ours + Log/
Agent[1]/tag/boundary_reached; extern "C" wrapper REQUIRED on nle_* decls —
env compiles as C++ there; nvcc forbids designated array inits → NETHACK_VERBS/
VERB_STAT flattened positional), Monk restored (their snapshot played
VALKYRIE), floor-reward descent restored (theirs was max-depth-only),
puf_log extended (floors + death anatomy), per-verb consume map, demo 19-head,
nethack.cu champion dims, verb-eps mixture into algo.cu (machinery + PPO fwd
mixture/verb_mix_scale + bwd d_lp_h) + pufferl.cu sample_logits (mixture +
last-legal fallback port) + verb_eps_update hooks in rollouts() and async
prefetch path + pre-capture init in create_pufferl (cudaMalloc-before-
capture constraint, same as head_consume); head-gating flipped default-on.
Config: champion [env] coefs + their carry train block (horizon 512, lr
0.00176, clip 0.479, ent 0.019 — CO-ADAPTED to their old max-depth reward,
resweep pending) + metric=score + action_mask_size 730.
LADDER 2/4 DONE (2026-07-31 late): **GRADCHECK PASS both trees at champion
arch** (tests/test_nethack_encoder.py updated for 730: nh_dec_pad/
nh_num_actions exports, N_DIRS derived, PAD-row lin ref — driver was stale
single-dir; main-tree run = first gradcheck of the 19-head decoder). 5c
harness = tests/test_nethack_cuda.cu incl ../src/pufferl.cu with
PRECISION_FLOAT + ENV_HEADER + -DPUFFER_NETHACK, build_test.sh (nvcc:
-Xlinker for rpath, nccl wheel link + LD_LIBRARY_PATH at run). GOTCHA: 5c
puf_mm needs cublas_init_handle() (create_pufferl does it; harness must
too) — without it everything downstream of matmuls is garbage while embed
grads look plausible. Errors IDENTICAL main-vs-5c to the last digit
(dec_out 3.25e-07, keygrad 1.44e-06) = same float math bit-for-bit.
**OBS FINGERPRINT PASS: fingerprint.c (scratchpad; FNV-1a64 over obs+mask
+rew+term per step, LCG 19-head action stream, rng=0) — main == 5c EXACTLY:
5K steps/54 eps = 811e36d13a9b8450; 20K steps/212 eps = 60e5fedf7ddb1bb9.**
Envs byte-identical across episode boundaries/deaths/prompts.
250M BASELINE (5c-base wandb group, tailer-mirrored — native binary has NO
wandb; scratchpad wandb_tailer.py parses dashboard frames, step = epoch x
131072): first run 5cb_s207 SEGV at 95M exit 139 SILENT (matches known
seed x trajectory class signature; n=1 can't rule out port bug — if a 2nd
seed dies mid-run, suspect the port). At 95M: score 2435 (healthy for
mismatched hypers), **max_depth 8.3 — carry policies dive deeper than
wipe-semantics at this stage** (ours ~6), search20 83/ep, throws 7.2,
wears 4.1. Config = champion env + THEIR carry train block (horizon 512,
lr 0.0018, clip 0.479 — deliberately not ours; ours is co-adapted to
wipe+h64; bridge arm idea: their trainer + reset_every_horizon=1 + our
block). **5cb_s310 COMPLETED: final rolling 4194 @250M** (ckpt
checkpoints/nethack/1785531958728/0000000249954304.bin) — strategy shifted
vs wipe-champion: max_depth 9.3 (vs 6.2), minetown 41%, killer-mlev 3.7,
search20 167/ep, throws only 7 — dive-heavy depth-chaser profile (their
hypers were tuned for max-depth reward). **10K carry-matched eval = 3604.812** — the citable 5c-base number
(./puffer eval, eval_episodes=10000, base.load_model_path pins ckpt;
trainer does NOT auto-run it; NOTE eval reads ~590 BELOW final rolling
4194 — opposite of our box's rolling/terminal relation; don't mix scales).
**4.0-HYPERS-ON-CARRY ARM COLLAPSED (user killed): 5c40_s207 score 365
peak → single digits by ~99M, per-update kl 1.79** — our champion block
(lr 0.0119, clip 1.0) does NOT transfer to 5c-carry despite both trainers
being Muon; systematic, not seed noise. Carry hyper-tuning needs the sweep
(other box) or an lr-bracket (1/2,1/4,1/8). OPS LESSONS (both hit tonight,
both self-inflicted): (1) re-hit the banked pgrep-own-cmdline gotcha via
os.popen('pgrep -f puffer train') inside wandb_tailer liveness check →
tailer immortal → chain stuck at wait $TPID; tailer now exits on 2min log
silence, no pgrep. (2) NEVER edit a script bash is currently executing
(byte-offset reads → executes garbage mid-word) — killed the first
40hypers launcher. (3) wandb_tailer STEPS_PER_EPOCH must match the run's
horizon*agents (env var now; 512*256 hardcode made a h64 run look >300M).
Then: reset_every_horizon 1v0 A/B at THEIR block (the controlled carry
test). Our recert constants DO NOT apply to 5c.

2026-07-31 LATE — 5C TRAINER MISMATCH ROOT-CAUSED + FIXED (task #106):
4.0-config runs on 5c underperformed massively (wipe+4.0block 250M eval
1978 vs champion 6403; no delayed-payoff verb adoption, wears 0.46, throw
spray 60/ep). TWO defects: (1) **MY CONFIG MISTRANSLATION (the causal one
for our config): 5c muon reads train.momentum (their default 0.95), NOT
beta1 — our beta1=0.805 never applied; effective step lr/(1-m) = 0.237 vs
intended 0.061 = 4x hot.** Explains async-carry collapse (kl 1.8), weak
sync runs, "sync slower than async" red herring. Fixed in ini both trees
(momentum = 0.805399553172738 + comment). (2) UPSTREAM BUG (inert for our
1-minibatch config, bites multi-mb configs like their carry 19 mb/batch):
commit a6066343 "messy but fast kernel optims" hoisted advantage+prio CDF
out of the minibatch loop on the FALSE premise they're loop-invariant —
rollouts.ratio/values are mutated by per-mb scatter-backs; hoist killed
vtrace correction + value refresh (ratio stays 1.0-filled; scatter-backs
dead; vtrace clip hypers dead). Restored per-mb recompute in
train_impl (uncommitted in worktree + main-dir 5c files). PROOF: fixed
wipe run 4077@135M = IN champion band (pre-fix 1450@147M), full verb
economy adopted (wears 5.5, engr 22, throws 17, depth 6.2). NOTE
total_minibatches for 4.0 config = 1 → advantage fix inert there;
momentum was the fix; keep both. MORNING TODO: fold fixes into `nethack`
commit on 5c-nethack; rebase onto upstream 2aee8960 (11 commits ahead,
"purge python"/"env ports to 5.0" churned their ocean/nethack — ours wins
wholesale; re-audit their trainer refactors); upstream PR/report for
a6066343 with 1978-vs-fixed receipt; add `upstream` remote (PufferAI).
EVAL-SEMANTICS GOTCHA: ./puffer eval carries state; for wipe-trained
policies pass base.reset_every_horizon=1 to the EVAL too (earlier 5cw
evals didn't → biased; fleet does).
OVERNIGHT FLEET (launched 23:0x): 10 x 1B on fixed trainer, interleaved
paired seeds 207-211: 5 carry (committed defaults) vs 5 wipe
(reset_every_horizon=1) = THE reset-semantics A/B at 1B, n=5/cell;
PUFFER_VERB_EPS_ANNEAL_START=0.2 (1B protocol); crash-substitute seed+103;
10K matched-semantics eval per run; wandb groups 5c-1b-carry/5c-1b-wipe;
~70min/run. 4.0-lineage 1B reference: l1b_s301 = 6740 (record 7473 @1B dd).

2026-08-01 EARLY — 1B FLEET RESULTS + EVAL-PROTOCOL CORRECTION (user-caught):
the 5c native trainer has a BUILT-IN warm terminal eval (main loop runs
train_epochs + eval_epochs; rollout-only until env/n > eval_episodes=10K,
eps annealed to 0) — the FINAL dashboard frame = the 4.0-COMPARABLE number
(4.0 terminal evals are the same warm protocol). My separate ./puffer eval
runs are a COLD protocol (burnin_games=0 in their default.ini, zero states,
up to 4096 agents) = −1400..−2100 on memory policies; NEVER compare cold-5c
vs warm-4.0. Tailer wandb summaries can catch late-TRAINING window peaks
(9006/9381) — raw log final frame is ground truth.
**CORRECTED 1B TABLE (warm in-run 10K evals, floor reward, fixed trainer,
eps a=0.2): carry s207=8283, s208=8076 (teardown segv AFTER eval+final
ckpt — recoverable-crash lesson: check wandb/log before writing off exit
139), s311=7808 → mean 8056±238 n=3; wipe s207=7714 n=1 (user froze wipe
cell, carry-only for s209-211). 4.0 refs same protocol: b1dd (depth-delta)
7207±238 record 7473; floor-reward l1b 6740. => EVERY fixed-5c 1B run
beats the 4.0 all-time record; fixed trainer > 4.0 trainer even at wipe
(+241 vs record); carry adds ~+570 (paired s207). Cold recovery eval of
s208 = 5945 (cold penalty −2131). zap adoption: s207 5.0/ep (first-ever
wand use), s311 0.0 — new coin, lottery open.**

2026-08-01 ~06:00 EVAL PROTOCOL v2 (two more user-caught holes): (1) 5c
STANDALONE evals re-arm the verb-eps floor: eval loop drives rollouts() ->
verb_eps_update(global_step~0) -> frac<anneal_start -> eps=BASE 0.005 for
the whole eval. MUST export PUFFER_VERB_EPS=0 for any ./puffer eval (4.0
probes pin it; the fleet-chain evals + first burned-in suite did NOT).
(2) completion-order/censoring: all-completed 10K window censors up to
eval_agents(1250) in-flight LONG episodes at cutoff (biased low ~<=12%);
burnin 4000 absorbs cold-start + short-first transient; tighten further
via base.eval_agents=512 or bigger num_games. IN-RUN final-frame numbers
are INFLATED (~+1050 on carry s207: 8283 frame vs 7229 burned-in ε-on) —
window mixes late-training episodes; NOT citable. CITABLE 5C PROTOCOL:
./puffer eval + PUFFER_VERB_EPS=0 + base.burnin_games=4000 + matched
reset_every_horizon. Bare suite running on 4 banked 1B ckpts (bare10k_*
logs). ε-on burned-in interims (superseded): carry s207 7229, s208 6716.

2026-08-01 06:14 — **FINAL VERIFIED 1B TABLE (strictest protocol: bare
PUFFER_VERB_EPS=0 + burnin 4000 + eval_agents 512 + 10K all-completed,
matched reset semantics; ~4min/eval): carry s207=8302, s208=7829,
s311=7857 -> MEAN 7996±265 n=3; wipe s207=7010 n=1.** vs 4.0 refs: record
7473, dd arm 7207±238, floor 6740 => carry beats ALL-TIME RECORD on every
seed (+523..+829); wipe-5c 7010 ≈ dd-arm-level (fixed trainer ~record-
class even without carry); carry-vs-wipe paired s207 = +1292. IN-RUN
final frames were ACCURATE all along (8283≈8302, 8076≈7829, 7808≈7857 —
±3%; frames slightly high-variance but unbiased): my intermediate probes
were the biased ones (ε re-arm −1000, cold −1400..−2100). VERDICT #106:
mismatch FIXED and surpassed — fixed-5c trainer + carry = new campaign
frontier at 1B. Champion checkpoints: carry s207 =
pufferlib-5c/checkpoints/nethack/1785538780674/0000000999981056.bin.
Remaining fleet: carry s209/210/211 were cancelled mid-fleet by user
pivots — rerun for n=5 if wanted. Morning docket: commit fixes (per-mb adv
+ momentum ini + eps-eval note), upstream rebase (2aee8960), a6066343 bug
report, THEN 4.0-side implications (their trainer lacks episode-aligned
zeroing + carry — the 8302 recipe is 5c-only).

2026-08-01 ~06:50 — ZAP ABLATION + 250M CAMPAIGN: paired strict eval on
1b_carry_s207 (control 8301.817 = EXACT repeat of verification run — 5c
eval is DETERMINISTIC, fixed seed; dormant-knob inertness certified):
ZAP-masked 8252.5 => **zaps causally worth only −49; the +460 zapper-vs-
non-zapper cohort gap = BASIN MARKER not cause** (dir-eps s209 law again).
New env knobs in 5c worktree (uncommitted): NETHACK_MASK_ZAP (eval
ablation), NETHACK_ZAP_DIRMASK (opt-in target-ray mask on ZAP dir row,
same accept-set/fallback as THROW's). LAUNCHED (user): 250M x {ctrl,
zapdm} x seeds 207-211 interleaved on committed defaults (carry, eps a=0.4
250M protocol), crash-sub +103, per-run strict eval (bare/burnin4000/
512env); groups 5c-250m-ctrl / 5c-250m-zapdm; ~25min train + ~4min eval
per run => ~5h. ctrl doubles as the first fixed-trainer 250M carry
baseline. Expectation calibrated: zapdm prize ~+50 unless mechanism raises
adoption (THROW precedent: ablation 18/ep pre-fix -> +468 post-mechanism).

2026-08-01 10:20 - 250M CAMPAIGN CLOSED at n=4/3 (user call; zapdm_s210
killed at 185M, s211 pair never ran). ZAPDM VERDICT: NULL - paired deltas
+602/-853/+70 (mean -60) = basin noise around the ablation's -49; neither
cell adopted wands (zaps ~0 at 250M carry - bottleneck is wand
ACQUISITION/identification, not aim; dirmask lever parked, knob dormant in
tree). CTRL CELL = NEW 250M BASELINE (fixed 5c trainer, carry, committed
defaults, strict evals): 6617/7491/6647/6998 = 6938+-405 (n=4) - every
seed > 4.0 champion 6403; ceiling 7491 > old 1B record 7473. Profile law
(4-run forensics): winners = conjunction wears~8 AND search20~600 AND
throws~30 (depth/routing identical everywhere); seed variance = armor-
depth + farm-intensity commitment (~800) - next lever = whatever
stabilizes those coins under carry (sweep or mechanism). Eval logs:
eval_250m_* in scratchpad bank; strict protocol throughout.
OUTSTANDING DOCKET: commit 5c uncommitted work (trainer adv fix + zap
knobs on top of f4a664b0/80333a56), upstream rebase 2aee8960, a6066343 bug
report, add upstream remote, complete carry-1B n=5 (s209-211 slots),
wandb-in-binary TODO, 5c dashboard omits game_time/valid_moves (TUI
truncation).

2026-08-01 ~11:15 — DEMO "DRIFT" SOLVED (user-driven; my drift theory was
WRONG): golden test (scratchpad golden_demo.c sed-renames demo main +
dumps stage tensors; golden_compare.py loads ckpt slices into the float
CUDA harness via nh_set_* + new nh_dec_forward_hidden entry) proved the
CPU demo forward pass is EXACT: encoder 7.2e-07 / decoder 3.3e-07 /
mingru-vs-f64 1.7e-06 rel err. MinGRU math line-identical both ports.
**REAL BUG: _softmax_multidiscrete (src/puffercpu.h) had NO max-
subtraction — logits > ~88 overflow expf -> inf/inf -> sampling loop never
fires -> default action index 0 (MOVE north; wall-walks consume no game
turn -> 10K-step/600-turn freeze episodes).** Explains the ENTIRE
historical demo-gap record: early soft policies under threshold ("within
3%"), sharpened policies over it (1B champ 4533-vs-6903 era included).
Fixed (max-subtraction) both trees; 4.0 branch's puffernet.h presumably
has the same bug — fix when there. Fixed-demo check on 8302 champion:
n=143 eps mean 7381 / median 5863 / max 28830 = faithful (single-env,
right-skew). ALSO: demo_find_weights now prefers staged resources/
nethack/nethack_weights.bin over checkpoint auto-scan (main dir has ~1500
old run dirs; smokes were hijacking the demo — user watched a 3M policy).
MAIN DIR (/puffertank/pufferlib, branch 5c-nethack) = authoritative now:
full parity with worktree, ./puffer + ./nethack built, champion weights
staged (NOTE resources/nethack/nethack_weights.bin is TRACKED — user
decides commit-vs-restore). Watching: ./nethack (interactive, per-step) or
./puffer render nethack base.load_model_path=... (GPU, 64-step frames).

2026-08-01 LOGIT-SCALE LAW (softmax-overflow postmortem): champion logits
grow ~linearly with TRAINING STEPS — 250M ckpt: mean-max 20.6, peak 64.6,
0% steps >88; 1B champion: mean-max 37.8, peak 332.9, 3.0% >88 (expf
overflow line ~88.7). CAUSE: PPO only sees logit gaps + entropy grad
vanishes on saturated softmax + muon weight_decay=0 + **Muon updates are
magnitude-normalized (orthogonalized)** — full-size steps along the
"sharpen" direction even at vanishing gradients => one-way scale ratchet;
GPU logsumexp is overflow-proof so training never pays. A/B on 8302 ckpt
(same seed/weights, only max-subtraction differs): fixed mean 7929 /
freeze 3% vs naive 1765 / freeze 43% = the fix is +4.5x on eval; freeze =
self-trap (most-confident states overflow -> action-0 -> same state).
IMPLICATIONS: (1) any 3rd-party CPU/naive-softmax consumer of our ckpts
needs max-subtraction (upstream _softmax_multidiscrete bug — report with
a6066343); (2) 4B+ runs will push peaks ~4x higher — bf16 rounding at
|logit|~1000 could eventually bite even GPU (watch); (3) optional
future guard: small logit L2/wd on decoder rows.

2026-08-01 ~13:00 — REBASED ONTO UPSTREAM a392d21c (fresh-branch replay,
NOT git-rebase: their pufferl.cu churned 1834 lines): branch 5c-nethack-r2.
Upstream fixed: ocean.cu stale includes (nmmo3/minimal re-ported; nethack
include ACTIVE UNCONDITIONALLY — our ocean.cu diff = ZERO now). Upstream
did NOT fix: adv-hoist ("once per train" alive) + naive softmax (renamed
_multidiscrete(...,hard); sample branch still raw expf) — both re-applied.
API drift handled: softmax_multidiscrete -> multidiscrete(md,in,out,0)
(demo call site), zero_frozen uses num_policies/policy_layout (was
frozen_banks/bank_layout), sample_logits gained env_actions arg, eval
unified (prints dashboard frames, no bot_eval line — old score-grep
patterns DEAD; eval overrides now anchor at vec.total_agents put).
Designated-init ORDER gotcha (C++): Hypers/PPOKernelArgs inserts must
match struct decl order. Re-applied full set: env wholesale, verb-eps ini
stack, head-gating one-line flip (upstream style kept), adv-per-mb,
render cmd, eval eps-pin, softmax fix, demo weights-priority+telemetry,
tests. VALIDATED: train smoke 26.68@10M-total (NOT bit-comparable to
pre-rebase 27.15 — upstream trainer refactor changed numerics; health ok),
eval mode works, demo on champion weights avg 9790/3eps. NUMBERS
RESET: all pre-rebase baselines (6938 cell, 1B 7996) belong to the OLD
trainer build; re-baseline before next science. Old branches: 5c-nethack
(80333a56-era), commit 29dec921 = full pre-rebase port on 67a69341.

2026-08-01 13:20 — R2 BASELINE (rebased build, branch 5c-nethack-r2 @
upstream a392d21c): r2b_s207 250M converged warm eval = **7266** (old
build same seed 6617, old cell 6938±405) — rebase carries champion
performance, top-of-band. Profile: wears 8.3 / throws 30.3 / engraves 31 /
min_ac 0.84 / zaps 0. NEW 250M REFERENCE (n=1; extend to n=4-5 before
tight A/Bs). RICH DEMO VIEWER shipped: interactive ./nethack now renders
6-line message history (dim->bold) + right-side inventory panel with REAL
item names via ocean/nethack/objnames.h (generated from engine objects.c
obj_descr_baseline[] via cpp — regenerate if engine objects change), quan/
spe(+N, sentinel -128 filtered)/(worn) markers + extended status line.
Headless episode-stats path unchanged. All in working tree for commit.

2026-08-01 COMMIT-PREP CLEANUP (r2 tree): ALL experiment env vars stripped
from the env — MASK_SEARCH20/THROW/WIELD/ZAP, THROW_GATE, THROW_AIM,
SEARCH_COUNT, RUN_COUNT, THROW_DIRMASK, ZAP_DIRMASK, FLOOR_PAY. Dirmasks
now unconditional (single ray_verbs loop). FLOOR_PAY replaced by
`floor_coef` env reward key (nethack.ini, default 0.0, composes with
descent_coef — sweepable). Census CSV writers + death-anatomy metrics
(hp_hist/death_hp_t*/spike/attrition) also stripped. Struct + API restored
to upstream agents[0] shape; c_*/puf_* split gone; sync_buffers revived
with a call at top of puf_step (UPSTREAM BUG: their sync_buffers has no
caller -> flat action_mask NULL-deref; report with receipts). Future
ablations = one-line code edits, not env vars. Every strip verified
bit-identical (2M smoke 25.828). Pre-strip file: scratchpad
bank/nethack_h_with_census.h + git history.

2026-08-01 SHIPPED: cleaned champion port committed as ed566bb4 "nethack"
(12 files, 1278/144) on branch 5c-nethack (fresh replay on upstream
a392d21c; old lineage kept as local 5c-nethack-prev), force-pushed to fork
origin/5c-nethack by user. Contains: 19-head env+decoder, dirmasks
(unconditional), floor_coef reward key, sync_buffers fix, softmax
max-subtraction, verb-eps (lean form: no accessor/setter, update inside
rollout_start), demo+curses viewer with inv_strs/colors sinks, gradcheck
harness (inline python build, build_test.sh deleted). Advantage-hoist fix
DROPPED from tree (upstream match; inert at 1 minibatch) — maintainer
actively reworking it (knows: "learning issues with clamping", tight-clip
asymmetric-truncation vs frozen-staleness dilemma; our loose clips 2.77/4.5
= sweep-found relief valve). Canonical 2M smoke = 25.828 (nosync/unmasked
variant = 32.7 — mask-dead canary). vendor/nle = July 3 pre-fast-nle clone
with 15 DIRTY local files — do not delete without checking.

2026-08-01 evening, r2 build (all via wandb bridge, groups speed-test /
eps-gating-abl, single seeds): clean baseline 250M = 20.3 MIN wall (user's
28m was interrupted-session artifact), score 7145 tail-50. SPEED: nomacro
(RUN+SEARCH20 masked) 9.9m/2426 — macros cost 2x wall, buy ~4700 pts;
async 11.0m/1588 — async STILL collapses post-momentum-fix (staleness x
carry, keep base.async=0, receipts dated post-rebase); composed 8.0m but
score 9 (dead) — 8m = GPU-train floor, further speed must be train-side.
ABLATIONS validate shipped defaults: noeps 5648 (-1300, matches eps
campaign), nogate 6075 (-900, edge of noise but consistent with lineage);
noboth killed at 107M. puffer_nomacro binary in repo root (delete when
done).

2026-08-01 OVERNIGHT: 2B fleet launched (task bctg35et8, wandb group
champ-2b, ~3h/run x4): paired A/B on seeds 207/208 — champion defaults
(eps anneal_start 0.4 relative = constant to 800M, one doubling past the
1B-validated regime) vs anneal_start=0.15 (~300M constant, matching 4.0
long-run absolute-scaling practice a=0.2@1B/a=0.08@4B). Questions: (1)
does score scale past 1B records 7996±265/8302; (2) is relative-0.4
too much eps at 2B. Crash-tolerant sequential; checkpoints per run_id.

2026-08-01 NIGHT PIPELINE (final form after user revisions): (1) reward
PRUNING matrix task b98e60mlm — rcbase + zeroed ac/status/heal/hp/hunger/
illegal_penalty/exp x seeds 207-210, seed-major, group reward-abl; verdict
= paired deltas vs rcbase, score-neutral arm => delete coef from config +
sweep space. (2) chained task bzu6u8ct2: 2B champion cell n=4 s207-210
group champ-2b (vs 1B 7996±265/8302). 2B a15-schedule arm CANCELLED by
user (defaults only). Earlier aborted: big-lever matrix (descent/xp/gold —
wrong end, user wants pruning). GOTCHA repeated twice: pkill -f patterns
matching own compound command (heredoc/args contain trainer strings) —
kill via TaskStop or run pkill in a command not containing the literal.

2026-08-02 morning: 2B cell CANCELLED by user (never launched). Pipeline =
matrix -> makeups (rcbase_s209 timeout-124 hang @66min!, rc0_heal_s207
exit-245 crash — both rerun) -> rcmin n=4. INTERIM MATRIX (n=2 pairs):
exp_coef HARD KEEPER (-4888! dense per-kill gradient, NOT redundant with
xp_coef — prior wrong), status -537 keeper, illegal -328 borderline,
ac -146 / hp -149 / hunger -111 prune candidates.

2026-08-02 ~10:00 PRUNING MATRIX VERDICT (n=4 arms, n=3 control 6997±545,
tail-50): PRUNE ac(+1 paired)/hp(+95)/hunger(+162)/illegal(-65)/heal(+211
n=2, crashes=engine not config)/status(-270 borderline, first-out on
bisect). KEEP exp (-4548±63 KEYSTONE: removal collapses whole strategy —
wears 1.6, s20 64, throws 0.1). ac shaping proven redundant: armor
self-sustains post-adoption (wears/min_ac identical without it); ac reward
is telescoping potential (not farmable, zero armor-cycling observed).
status_coef/heal_coef were hand-set round numbers (never swept). PRAYER
UPDATE: current champions pray ~7-10/ep (mostly starving) = routine food
strategy — old 0.3/ep backstop figure is STALE. rcmin cell launched
(6 coefs zeroed, s207/208/210/211, task bamkm311n): reward = exp/gold/
descent/xp/scout/death only.

2026-08-02 REWARD PRUNE SHIPPED (user decision, all 6): nethack.h reward =
gold/exp/descent/floor/xp/scout/death ONLY; hp/hunger/illegal/ac/heal/
status REMOVED (code+fields+dict_gets; stat tracking kept for metrics;
death payout lost its hp_coef clawback — matches tested arm). NEW 2M CANARY
= 23.107 (old 25.828 dead with champion reward). GOTCHA (cost 5 runs): CLI
env.X=0 overrides CANNOT CREATE missing [env] keys, only override existing
— never delete ini keys while old binaries are queued; keys restored as
zeros (new binary ignores). puffer_champion = HEAD-source binary kept for
champion-reward controls (new binary cannot express champion reward).
rcmin_s207 = 7208 (+155 vs control). Salvage chain bqqmqv0n1: equivalence
proof + rcmin 208/210/211 + rcbase_s209 control (doubles as alter_cost
hang-fix verify). Commit TODO: drop 6 ini keys + [sweep.env.*] blocks for
the pruned coefs. User committed wandb bridge as 815dd8e4.

2026-08-02 REWARD ECONOMY (analyze in CLIPPED units — trainer hard-clamps
rewards to [-1,1], pufferl.cu ~1542, maintainer warns of reward hacks):
saturation thresholds: 46 gold / 12 exp pts / 0.5 depth-level per step =>
exp is a +1-PER-KILL EVENT DETECTOR (50-150 events/ep, the dense backbone —
explains keystone -4548), descent = +1/level, big gold piles = +1.
death_penalty -0.82 = ~82% of max single event, the ONLY loud negative —
NOT small (env-side share <1% is misleading). Env-side decomposition of
return 186/ep: gold+exp ~77%, scout 16% (0.074x407 tiles), descent 6%,
xp 2%; pruned-six net <1%. Untested keepers: gold/scout/descent/xp/death
(exp proven). gold likely partially redundant with kill channel post-clip.

2026-08-02 ~13:10 MATRIX CLOSED (all n=4, tail-50): rcbase 7128±523;
heal +25 / hunger +130 / ac -99 / hp -117 / illegal -206 = clean nulls;
status -354 (largest non-exp, consistent sign, still in noise — WATCH item;
restore-first candidate if pruned config underperforms; possibly undertuned
not useless); exp -4703±63 keystone; rcmin (6 pruned) 6703±462, paired
-227. PRUNE SHIPPED (user call). Verification trifecta: equivalence
bit-exact PASS; tended_shop fix = 3 ex-crash runs completed; alter_cost
fix = s209 completed 7518 (also filled the n=4 control). New 2M canary
23.107 (pruned reward). Engine fixes awaiting fork commits in
vendor/fast-nle + NetHack upstream issue (alter_cost hang SHIPPED IN 5.0.0
stable, verified against NetHack-5.0.0_Released tag).

2026-08-11 CLEANUP + PUSH VERIFIED: branch head 9b468e8c "cleanup" (masks +
telemetry + gitignore), user pushed. 2M-step paired-train FINGERPRINT
(seed 777, NH_ALLPICK+NH_DISC_SWAP, terminal ckpt sha256) = IDENTICAL
between puffer_champbin (the binary that trained full1b_s701=9,424 and
champ1b_s701) and the pushed-tree rebuild — pushed code proven behaviorally
identical. 2M is the right fingerprint size (~90s; 16M overkill). GOTCHA:
killing a sequential fingerprint task's TRAIN leaves the wrapper alive to
run its next stage — racing a relaunch on same run_ids/logs clobbers them;
always fresh run_ids on rerun. combo (allpick+discswap) 1B: s701=8,288 ONE
DRAW vs full's 9,424 (s702 killed un-certed) — combo unproven, discoveries
17.7/ep record (identification EFFICIENCY: half the tests, more knowledge).
PR description draft in scratchpad PR_DESCRIPTION.md. Fork push = required
pre-PR step (build.sh clones the fork).

2026-08-11 PM — GREAT CLEANUP (branch `cleanup`, soft-reset review flow):
champion behavior IS the code now. Folded/removed with per-edit 2M
fingerprint gates (ALL PASS, ref hash 6706efb1 = champbin+NH_ALLPICK):
all-class autopickup = default (pickup_types dropped from options; fs.h
zeroed); 14 forensics hooks + NH_ABL_DISC + NH_SPELL off-arm + verb-only
entropy knob + demo MSGLOG removed; REWARD GRAVEYARD removed (18 config
keys, 19 struct fields: discovery/floor/heal/depth_alive/exp_log/sqrt/rel/
rel_floor/depth/frontier/site_rel/descent_depth/scout_depth + bank_floor/
bank_xp/descend_gate/mask_cast/max_episode_steps; reward fn = 7 champion
terms; r_raw ledger 9→6; floors/heal_hp/cures stats kept). Demo keeps only
NH_SEED/NH_WEIGHTS. Sole surviving experiment flag: NH_DISC_SWAP.
fpgate.sh = rebuild + bare 2M seed-777 train + sha256 vs recorded ref;
~90s. Bit-exact rules: removed terms must be +0.0f adds, live-term float
order preserved. NOT yet merged to 5c-nethack; nethack.cu/pufferl/tests
review pending; final step = commit cleanup + gradcheck + goldens + merge.
CLEANUP FINALE: also folded the 8 legacy mask ablation flags (CSWAP/RAYV2/
ENGID/ELBTER/MASK_TRICE/PEACE/DOOR/DIRRUN) to champion defaults — gate 7/7
PASS; sole env flag left = NH_DISC_SWAP (+ demo NH_SEED/NH_WEIGHTS). Demo
weights swapped to full1b_s701 terminal ckpt (9,424 record, matches shipped
allpick default; old carve bin recoverable from git). demo_find_weights
restored to documented order (NH_WEIGHTS → newest ckpt → resources; removed
resources-first staging hack). src/algo.cu now ZERO delta vs base. Campaign
.gitignore junk moved to .git/info/exclude; committed ignores = /puffer,
/nethack, experiments.ini. default.ini sweep-dim comment-out must STAY:
child ini cannot delete inherited sweep sections and min==max pins NaN the
GP (space_normalize 0/0) — flagged in PR description. PR_DESCRIPTION.md
(scratchpad) rewritten to post-cleanup reality. Tree left UNCOMMITTED on
`cleanup` branch for user's VS Code review; user drives commit/merge.
constellation.c PUF_TABLE_MAX_COLS bump REVERTED (user call) — file back to
base, out of PR. Standalone viz tool only (not in ./puffer; sweep unaffected);
consequence: constellation viewer exit(1)s on full nethack logs (~311 cols:
196 config + 115 metrics > 256). Fix if needed later = trim stat export or
dynamic labels, not shared-infra edits.
2026-08-12 RESTYLE (drone-style, user-directed): ocean/nethack/* restyled to
ocean/drone conventions — brief 1-2 line experimental notes kept (user call),
lowercase section banners, one statement/line, no column alignment (defines,
struct fields, assignments flushed), inline { a; b; } blocks flattened,
netlib.h rewritten (sections: object tables/glyphs/obs layout/engine state/
actions/options/verb table/telemetry). LEDGER BUG found+fixed during restyle:
add_log still looped i<9 over r_raw[6]/r_clip[6] (graveyard-pass leftover) —
OOB telemetry corruption (r_clip/exp..descent double, r_raw/death doubled,
reach_mines/minetown garbage since graveyard commit; training unaffected,
gate can't see log writes). Restyle gotchas: dropped NETHACK_PATH_MAX in
netlib rewrite (build caught); braceless-for + split-if broke demo spellname
loop (build caught). MOVE door check now reuses tg (was 2nd identical
nle_terrain_underfoot call). Gates: netlib+macros PASS, nethack.h PASS.
fs.h already clean. README verb count fixed 22→26. NH_DISC_SWAP kept (user).
nethack.cu restyled too (same session): alignment flushed, 9 "----" banners
-> lowercase, 10 packed one-liners split, perf-design comments kept; -w diff
verified banners+braces only; gate PASS. Whole ocean/nethack/ now drone-style.
Logging prune + extern cleanup (2026-08-12): reward ledger REMOVED entirely
(r_raw/r_clip/r_death fields+math+13 wandb keys; t[] kept = summation order);
dead extern nle_spells v1 removed; 2-SUFFIX RENAME across fork+env:
nle_spells2->nle_spells (v1 deleted, internal nle_spell_summary2->_summary),
nle_cast_blocked2->nle_cast_blocked (internal spell.c predicate ->
nle_cast_blocked_impl; the 2 existed because C flat namespace collided with
the internal name). Fork commit 44b709096 LOCAL-ONLY, needs user push (build
clones branch head; fresh clones break until pushed). All gates PASS.
wandb-bridge memory note: r_raw/* keys no longer exported.
LOGGING PRUNE COMPLETE (user-directed, all gates PASS): r_raw/r_clip/r_death
ledger gone; reach_* + reach_d10 -> depth_ge_5/10/15 + mines_depth/
sokoban_depth (popcount floors_bits[2]/[4], soko ascends so floors-visited
not dlevel); death anatomy focused to combat/starved/weak(Weak+ incl
fainting)/other/mon_level + NEW death_ac (last_ac tracked per living step,
seeded at reset; death-step blstats torn down); survival diagnostics cut to
min_ac + burdened_frac (dropped ac-mean, damage, heal_hp, cures, prayer
quartet, armor_swaps, wear_blind, cursed_worn, altar_steps + their per-step
scans + prev_hp/prev_bad_cond/COND_* defines). Named keys 50->35. Old wandb
panels on removed keys go empty. Demo HUD updated.
Prune finale (all gates PASS): economy sale_gold+drop_value cut (msg_number
parser + nh_obj_cost table deleted); reads export NULLed (== reads_scroll +
reads_book, mask-provable); reward fn final form: single fn, direct r accum
in pinned order exp gold descent xp scout ac (t[] deleted; AC block moved
last; user rejected helper extraction — inline phases only), dead illegal
param dropped. Export surface: 30 named keys + 21 verb counters. Also
NETHACK_APPEARANCE census from objects.c: ~191 shuffled appearance glyphs /
~171 real identities; scrolls 41 labels for 21 types (20 SCROLL(None) decoys)
— quantifies disc-swap/collapse payoff.
COMMITTED 2026-08-12: 5c-nethack 88493f74 "style + logging cleanup" (additive
on 9b468e8c, no rewrite; cleanup branch f3f41a12 same tree). FINAL GATE PASS
on committed tree. src/ + scripts/ ZERO delta (wandb + warm-start removed
from main per user; local-patch material, see wandb-bridge memory). PR = 12
files: ocean/nethack + configs + tests + weights(full1b_s701). Awaiting user
push; PR_DESCRIPTION.md in scratchpad current.
RE-FOLD 2026-08-12 (final): 5c-nethack 4eb16ebf "style + logging cleanup"
(replaced unpushed 88493f74; cleanup branch cfd51b64 same tree). Late changes:
default.ini FULLY reverted to upstream except wandb-key removal (sweep pinning
= local patch now, see no-hand-edited-hypers memory); nethack.ini reorganized
([env] = 7 coefs + "# flags" scout_ready/ac_nospell w/ 1-line comments,
verb_eps sweep blocks commented out + moved to file bottom, user dropped muon
momentum comment + dead num_threads line). Tests left in their own table
style (deliberate). FINAL GATE PASS on committed tree. Awaiting user push.
PR TARGET CORRECTION (2026-08-12): true base = upstream/5c (PufferAI), NOT
4.0 (stale local ref; merge-base a392d21c). upstream/5c already carries an
older merged nethack (PR #624) — this PR UPDATES it. True src footprint vs
upstream/5c (all pre-ed566bb4, all justified, KEEP): puffercpu.h +12 =
max-subtraction softmax fix (upstream STILL UNFIXED — overflowed heads sample
index 0); algo.cu +39 + pufferl.cu +80 = verb-eps floor (default off,
eval forces 0); default.ini adds verb_eps keys only (upstream's own dormant
`wandb = False` line RESTORED — removal was based on stale-4.0 confusion).
5c-nethack = 87d42de2 (amended). PR_DESCRIPTION updated: target 5c, real
shared-infra section.
FINAL FINAL (2026-08-12): 5c-nethack = b881552d (puffercpu comment dropped,
user call: max-subtraction self-evident). Gate PASS on b881552d. Ready for
user push + PR to upstream/5c.
VERB-EPS FINAL SHAPE (2026-08-12, all gates PASS incl two risky device-helper
extractions — same-TU inlining preserved fmad): ALL eps state+math in one
algo.cu block (g_veps_dev, init_verb_eps, verb_eps_update(primitives),
verb_eps_load/mix/logp sampling helpers, verb_eps_train_logp training helper);
pufferl.cu = wiring only (~41 lines: 3 Hypers fields+reads, init call, update
call, kernel param + 3 taps + last-legal fallback, eval verb_eps=0); anneal
ae>=1 special-case branch REMOVED (proven+gated equivalent). 5c-nethack HEAD
after each amend — check git log; needs force-with-lease (remote holds early
draft 4eb16ebf).
OPT-IN RESTRUCTURE (final eps shape v2, all gates PASS): both kernels now
preserve upstream lines verbatim — mixture applied via if/else with the
original expression as the else-arm (algo fwd), save/scale/restore sandwich
around the untouched grad loop (algo bwd), if/else in sample_logits CDF +
logp (pufferl). Only 3 modified upstream lines remain: kernel signature +
launch (param add) and sampled=A-1 -> last-legal fallback (bug fix).
5c-nethack tip moves with each amend — use git log, force-with-lease to push.
2026-08-11 eve: asyncdepth2_s301 250M DONE (depth config on modern stack,
wandb encoders/asyncdepth): score 2611, mean max_depth 10.04, depth>=10 59%,
>=15 3.1%, pure diver (94.5% combat deaths, 0 starved, death_ac 4.8, ac_coef
0/scout_ready 0 era-faithful). Beats old asyncdepth_s301 (9.75/2332) same
seed+budget. Config saved as ocean/nethack/depth.ini (commit 732816a3 with
depth_ge_*->depth_5/10/15 rename; cp to config/ to use). Terminal ckpt cert
PENDING (DIVE-11 target: certified depth >= 11). Fork 44b709096+HEAD: exit-
status + getenv diagnostics silenced (commit local, NEEDS USER PUSH). Binary
on disk = wandb-patched (uncommitted). Old `puffer` on PATH = stale venv
script, use ./puffer.
DEMO TTY PARITY (c5e439b1, gate PASS): demo renders the engine's real 24x80
tty screen (tty_chars/colors/cursor via libtmt; fills gated on non-NULL bufs
— training binds NULL via nethack_*_sink pattern). Colors 0-15 CLR, +16 =
reverse; cursor[0]=row. Demo uses NETHACK_BASE_OPTIONS + statuslines:2
(nethack_options_override, NULL in training; DEFAULT = BASE+"!status_updates"
byte-identical). Custom map/msgs/status renderers deleted (-73 lines); inv
pane kept. Branch commits since push: 732816a3, 8ed9ac8e, 966ec882?, c5e439b1
(check log; also "demo loads resources weights by default"). PHASE 2 PLANNED
(awaiting user OK): Tab = policy step/hold, Shift+Tab/F2 = 20Hz, Ctrl+Q quit,
ALL other keys raw to the game (no macro layer in human path) = human
takeover anytime.
OVERNIGHT 2026-08-11->12 (nightq3, lean per user: NO certs): depth1b_s301
(depth.ini @1B, wandb encoders/depth1b) then dswap1b_s701+s702 (champion +
NH_DISC_SWAP=1 @1B, group dswap1b — seeds PAIRED with full1b 9424/7747).
Questions: depth-at-1B toward DIVE-11; disc-swap score cost at scale.
Certs on demand later. Earlier queue w/ certs killed (user call). Config
copy at config/depth.ini (untracked).
QUEUE EXPANDED (user: 5×1B per disc type): nightq4 chains after Q3 —
dswap1b + full1b alternating seeds 703/704/705. Panels: dswap 701-705 all
fresh; no-swap = EXISTING full1b_s701/702 (9424/7747, bit-repro valid) +
fresh 703-705. ~9-11h total, done mid-morning. Verdict = 5v5 paired
disc-swap score cost at 1B (the open score ablation) + depth1b_s301 DIVE-11
read. All wandb encoders.

**2026-08-12 PR #626 MERGED UPSTREAM.** upstream/5c commit 4291c357 merged
FinlaySanders/5c-nethack at 7a27e937 — the NetHack stack (cleanup, verb-eps
trainer, depth config, mask options, resources weights) is now official
PufferLib. 5c migration campaign COMPLETE. Local 5c-nethack = upstream +
3 newer commits (c5e439b1 tty demo, 78992d7d spell/inv demo, 28a92bab
wandb+burnin) + merge 3af934aa; gate PASS post-merge. Follow-up PR when
user wants the demo/wandb extras upstream.

**2026-08-25 WORKTREE SWAP (critical for orientation)**: the two dirs are
linked worktrees of ONE repo and were SWAPPED at user request:
/puffertank/pufferlib = branch 5.0-nethack (upstream/5.0 + port, commit
6756d964 "nethack v5", 5.0 CLI --base.seed= form, binaries rebuilt);
/puffertank/pufferlib-50 = branch 5c-nethack (19ea7bd5 "decoder dot";
its binaries are STALE 5.0-builds until rebuilt). 5c-nethack tracks
origin/5c-nethack and was up-to-date at swap time (5c commits are on the
fork remote). Untracked 5c leftovers (fleet arms nethack_v5sp2/
v5ab_ctrl, docs, declab data refs) still live in /puffertank/pufferlib
and remain runnable (self-contained + same vendor .so).
