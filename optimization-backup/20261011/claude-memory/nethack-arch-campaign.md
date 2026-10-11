---
name: nethack-arch-campaign
description: Encoder architecture sweep (2026-07) verdict — arch is NOT the 3500->4000 lever; seed knob + smem gotchas
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-14T10:49:46.102Z
---

**PRAYER-CLOCK NULL (3-seed), VALKYRIE −2660 (2026-07-17). Champion committed as HEAD 43747f2c "hp_frac, more masking".** CORRECTION: the s43 +198 was SEED NOISE, not a win — prayer-clock does NOT replicate. paired: s43 +198, s44 −139 (opposite signs); 3-seed prayer-clock mean 4342 (4456/4281/4288) == hp_frac champion mean 4339 (4258/4421). REVERTED (not added to champion). LESSON (recurring, cost me twice this session): at the ±100-200 scale a single seed is meaningless — paired noise is MUCH wider than the ~54 I'd quoted (2 seeds gave +198 vs −139, swing 337); believe nothing <~+300 until 2+ seeds agree in sign. Corollary: "env not exhausted" (which I'd claimed off the +198) is WITHDRAWN — env/encoder small features are noise-dominated & averaging null. What's ROBUST: the STACK vs baseline (+~1000 on BOTH s43 3259->4258 and s44 3518->4421); stair-mask (+521, 2/2 clean mode-conversion). Per-feature isolated increments (movement +113, hp_frac +364) are single-seed only — champion stack is solid but exact attribution is noisy. 5k needs a MODE-scale lever (like stair-mask was) = reward dive-vs-level (sweep), NOT more ±100 env features. Pushing for 5k, env-only. (1) **turns-since-prayer** into extra[0] (current game TIME - last_pray_time, clamped [0,2000]; NON-privileged proxy for the ublesscnt timeout a human tracks by counting turns; encoder already log1p-reads j==45; nethack.h-only, no gradcheck): s43 **4257.7 -> 4455.9 (+198, ~+3.7 sigma)**, max_depth 4.10->4.33. WIN — VALIDATES the reward-supported-action law (prayer availability signal -> rewarded response: time prayers for heal/food, dodge 2% smite). So env/encoder NOT exhausted — the "signal the net lacks + REWARDED response" vein still pays; both wins (hp_frac, prayer-clock) improve PRAYER = the agent's highest-leverage rewarded action (heal+food engine). Verifying s44(control 4420.5)/s73; patch scratchpad/prayerclock.patch. (2) **Valkyrie** (dwarf-Val-fem-law role, nethack.h opts): s43 **1597.6 (−2660), max_depth 1.358 (doesn't even dive)** — class is CO-TUNED with the Monk reward/config+diving-discovery dynamics; swapping class resets ALL tuning -> needs its own reward sweep (out of scope). Class-change is a dead end env-only. patch scratchpad/valkyrie.patch.

**OVER-EXTENSION NULL — representation needs a REWARD-SUPPORTED action (2026-07-17). [SUPERSEDED: env NOT exhausted, prayer-clock +198 above]** over_extension = depth/xp_level (RATIO, genuine hp_frac-class uncomputable signal, tied to the measured under-levelled death mechanism), on champion, s43: 4226.7 vs 4257.7 = **−31 (null, −0.6 sigma)**. THE KEY LESSON completing the representation arc: a signal only helps if the agent has a REWARD-SUPPORTED response. hp_frac(+364): low-HP -> pray/heal is directly rewarded (survive, avoid death penalty) => win. over-extension(null): high ratio -> "hang back and level" FIGHTS descent_coef (diving pays, caution doesn't) => no rewarded response => the (correct, uncomputable) signal is inert. So even a perfectly-designed hp_frac-class feature is null when the reward doesn't back the response. REPRESENTATION LEDGER (all on the champion, seed 43, sigma≈54): hp_frac +364 (ONLY win, had rewarded action), depth-embed −129, rescale −108, over-extension −31. => ENV/ENCODER IS EXHAUSTED. 5k requires the REWARD lever (descent_coef 1.888 vs xp_coef 0.281 -> make caution/leveling pay) = the max_depth sweep's domain. Champion stays 4258/4421; commit masks+logging+hp_frac.

**RESCALE ARM NULL-NEGATIVE — scale hypothesis FALSIFIED (2026-07-17).** Rescaled squashed monotonic stats to operative range (depth /50->/10, xp /30->/10, hp&hpmax /200->/50) on the hp_frac champion, s43: 4149.9 vs champion 4257.7 = **−108 (~−2 sigma)**, reverted. depth+xp are NOT ratio'd (pure scalars), so their rescale is a CLEAN test: fixing the squash did NOT help. => the "over-downscaling is very harmful" hypothesis (user's, reasonable) does NOT hold for these stats; hp_frac's +364 was the RATIO/varying-denominator (a genuinely uncomputable decision signal), NOT scale. VERDICT: THREE representation arms beyond hp_frac now (depth-embed −129, rescale −108, over-extension untested) — only hp_frac (giving a decision-critical signal the net literally can't compute) worked; rescaling/embedding stats the net can already roughly use just perturbs a tuned setup for a mild net negative (same as arch-sweep "bigger=slightly worse at fixed budget"). REPRESENTATION VEIN BEYOND hp_frac IS ~TAPPED. Remaining lever = reward-balance (descent_coef 1.888 vs xp_coef 0.281 -> dives faster than it levels -> under-leveled deaths), owned by the max_depth SWEEP (other box, ~24h). Clean unconfounded science still open (optional): rescale hp/hpmax WITHOUT hp_frac vs dirdive 3893 to fully isolate scale-vs-ratio; but doesn't change what ships (hp_frac champion either way).

**DEPTH-EMBED NULL-NEGATIVE — theory-only reps don't reliably pay (2026-07-17).** 16-bin depth one-hot (per-level embedding via bl_w cols) on top of hp_frac, s43: 4128.7 vs hpfrac control 4257.7 = **−129 (~−2.4 sigma)**, reverted (restored hpfrac champion via hpfrac.patch). LESSON: hp_frac won (+364) because it fixed a MEASURED behavioral gap (no HP-emergency response, confirmed by prayers_low_hp/death_combat moving); depth-embed was motivated by pure representation THEORY (squashed depth/50, false ordinality) with NO measured symptom, and failed. => re-weight the stat-audit: bet on features backed by a measured death mechanism (over-extension depth-vs-xp_level is the one such candidate), treat "this scalar is squashed" items (dnum/dlevel/cap embed) as LOW probability. WHY depth-embed hurt (learning curves, s43): depth-climb LAGGED badly — at the training point where control hit max_depth 2.76, depth-embed was still ~1.1 (both slower start AND lower finish 3.88 vs 4.10). MECHANISM = the one-hot DESTROYS ORDINAL GENERALIZATION: scalar depth/50 generalizes "deeper->reward/danger" to unvisited depths for free (so the stair-mask discovery loop descend->reward->value-credits fires immediately), but a one-hot gives each depth an independent bl_w column untrained until visited, so credit doesn't transfer across depths + cold deep bins inject noise; keeping the scalar too made it worse (net leans on the lower-training-loss memorizing one-hot, generalizes worse). SHARPENED RULE: one-hot/embed ONLY for NON-monotonic/categorical (dnum branch, hunger, buc, glyphs) where cross-value generalization is meaningless; KEEP SCALAR for monotonic/ordinal where you need to generalize across the range (depth->danger, xp->strength). COROLLARY: xp_level EMBED is wrong too (monotonic->breaks generalization); rescale-to-operative-range MAYBE, embed NO. over-extension feature stays valid = SCALAR difference depth-xp_level (generalizes); dnum-embed survives (truly categorical). Depth vs dlevel: equal in main dungeon (dnum 0), diverge in branches; depth=absolute (the "Dlvl:" number), so depth is the right operand for over-extension; dnum(branch) complements it, dlevel is ~redundant with depth for a shallow diver. One-hot-into-bl_w == embedding (col of bl_w per value); explicit embed_w table only needed for large/factored vocab (glyphs 5977, kind+sub factored) — small flat vocabs (depth16/hunger7/buc4) use one-hot-into-existing-linear, no new tensor.

**4000 REACHED (2026-07-17).** Original goal (3500->4000) hit reproducibly via THREE non-privileged env/encoder changes, all found by behavioral analysis (action-count/stat diffs), NOT arch. Seed-43 ladder: baseline 3259 -> +stair-mask 3780 -> +movement-mask 3893 -> +hp_frac **4258** (+999 total). hp_frac replicates: s43=4258, s44=4421 (both >4000; s73 running). Commit these together (stair mask already committed as bc5be93b; movement-mask + logging + hp_frac uncommitted on top).

**hp_frac WIN — RATIO REPRESENTATION, not information (2026-07-17).** Added hp_frac=hp/hpmax and ene_frac to bl_feats (src/nethack.cu: NH_BL_FEAT 78->80, NH_BL_HP=10/NH_BL_ENE=14, appended as forward-only tail in nh_blstats_kernel — NO backward kernel since blstats are non-learnable inputs; gradcheck bl_w clean, lone inv1s_w FD-fail is the known max-pool noise shifted by proj_w resize; obs_size UNCHANGED 4184 since derived in-encoder). Clean paired s43: dirdive 3893 -> hp_frac **4257.7 (+364, ~+6.7 sigma vs within-seed sigma≈54)**. MECHANISM CONFIRMED 2/3: prayers_low_hp 0.274->0.380 UP, death_combat 0.854->0.798 DOWN (both predicted); ups_hurt flat (agent learned to pray-heal not flee). WHY (TWO confounded causes, not fully separated): (a) SCALE/conditioning [user's, likely dominant] — hp/200,hpmax/200 squash to [0,0.2] for a maxhp~40 Monk vs one-hots at 1.0, so HP is a 5-10x quieter, weak-gradient signal (NOT a bf16-resolution loss — bf16 relative precision is scale-invariant; it's optimization conditioning); (b) RATIO/varying-denominator [mine, overstated] — a linear unit CAN represent a fixed-ratio threshold relu(a*hp-b*hpmax), so "linear can't do ratios" is WRONG; what it can't do is track danger as hpmax GROWS with level (hp/fixed != danger). hp_frac fixes both at once so the +364 can't be attributed cleanly. DISTINGUISHING ARM (untested): rescale hp,hpmax to ~[0,1] (/50) with NO ratio — recovers gain=>scale, flat=>ratio. Connects to depth/50 squashing (norm constant for theoretical max wastes operative range). GENERALIZES: rescale decision-critical VARYING stats to operative range (not theoretical max) + provide ratios/geographic categoricals = follow-ups. patches: scratchpad hpfrac.patch (src+tests), dirmask.patch, stairmask.patch.

**METHODOLOGY THAT WORKED (the meta-lesson): analyze runs to find weak points.** Every win came from diffing behavioral stats (action counts, death causes, prayer breakdown) between good/bad runs — NOT from arch sweeps (12 GPU-hrs, null) or blind capacity. Killed 3 wrong hypotheses cheaply BEFORE building (PRAY-mask: agent prays 96% for FOOD not waste; Elbereth-spam: demo artifact from per-episode state reset — C demo unreliable for fine rates, use probe_ckpt.py real vec path; prayers_low_hp metric measured wrong axis). PITFALLS: (1) eval_log() is CUMULATIVE (never cleared) + 512 envs start synchronized -> completion-order sampling biases early n toward SHORT/low-score episodes; need n>>512 (10k) for absolute stats, but RATIOS are n-robust; log() clears each call (windowed, safe). (2) C demo carries hidden state a whole episode (~26x the horizon-64 training regime) -> off-distribution, unreliable for rates. (3) always pair on SEED (within-seed sigma≈54 vs across-seed 291). LOGGING FIX shipped: death_other else-binding bug (was "not combat", double-counting starved/smited/truncated); added prayers_starving/prayers_trouble (nethack_in_trouble replicates pray.c: hunger>=WEAK(3), cond bits 0x1F, hp<=5||hp*divisor<=min(hpmax,15*xlev) divisor 5/6/7/8/9 by xlev). Measured: smite 2.1%, truncated 4.1% (10K cap DOES bind — earlier "0%" was low-n artifact).

**BREAKTHROUGH — STAIR-MASK CONVERTS FARMERS TO DIVERS, +522 SCORE (2026-07-17).** THE fix for 3500->4000. `DOWN`/`UP` were ALWAYS legal but are no-ops unless standing on the matching stairs/ladder, so off-stairs picks are wasted turns -> the policy drives DOWN to ~zero probability and then CANNOT descend even when ON a staircase. MEASURED (demo, 10 eps, ~26.3K actions): farmer picks DOWN **3 times**; diver s102 picks it **5455**. The entire farm/dive bifurcation is whether DOWN keeps probability mass. FIX (ocean/nethack/nethack.h mask builder, ~20 lines, env-side, NON-privileged — `underfoot_glyphs=1` puts terrain under hero in obs): mask DOWN unless underfoot glyph ∈ {DNSTAIR 2383, DNLADDER 2385}; UP unless ∈ {UPSTAIR 2382, UPLADDER 2384}. (cmap: GLYPH_CMAP_OFF 2359 + S_upstair 23/S_dnstair 24/S_upladder 25/S_dnladder 26; verified via probe vs generated pm.h/onames.h.) RESULT **2/2 REPLICATED** (paired, same seeds, 358906224): s43 3258.7 -> **3780.4 (+521.7)** depth 1.156->**3.827**; s44 3518.4 -> **3664.6 (+146.2)** depth 1.165->**3.717**; **mean 3388.6 -> 3722.5 (+334.0)**. Matches/exceeds the 3800 champion s102 (3816 @ 3.687). Gain is NON-uniform (s44 gained less because its farmer baseline was already the best at 3518) — what's uniform is the DESTINATION ~3700-3800. **ALSO COLLAPSES VARIANCE**: the 3 divers score 3816/3780/3665 = **3754 ± 79** vs the old mixed population's sigma≈291 — the "seed lottery" was MODE, and the mask de-randomizes it. **DEPTH WALL ~3.7-3.8**: all 3 divers plateau there (s43m hit 3.83 at 25% of training then flat for the remaining 75%) => a real wall, not a budget limit. Wall = SURVIVAL (death_mon_level 1.37->1.86, death_maxhp 38.4->41.2 = dying to stronger monsters deeper). Divers also LEARN to pray in trouble unprompted (prayers_low_hp 0.028->0.213/0.290, ~8-10x). => remaining ~280 to 4000 = lever (b) deepen divers; THIS is where hp_frac / prayer-timing / depth-encoding finally bind (a diving regime exists to test in now; use s43+mask or s44+mask as the A/B vehicle). Also `prayers_low_hp` 0.028->0.213 (7.6x — fixes the death-tail's never-prays behavior); `illegal_actions` 4.36->2.53. Even the DIVER wasted ~27% of actions on off-stairs DOWN/UP no-ops, so the mask should ALSO deepen existing divers (untested arm: s102+mask).

**STATS METHODOLOGY — PAIR ON SEED (corrects the ±570 claim below).** Across-seed sigma≈291 is dominated by MODE and is the WRONG yardstick. **Within-seed** (same seed, 9 different encoder archs) seed43 = 3179.7/3207.1/3218.3/3220.9/3242.1/3258.7/3267.1/3307.9/3352.9 -> **mean 3250.5, sigma≈54**. So PAIRED same-seed A/B is powered to ~±100, and stairmask's +522 is **~+10 sigma** = decisive on ONE seed. Corollary: the arch campaign's paired nulls WERE valid (arch really does move score <~100); the earlier "we learned nothing from any of them" was an OVERCORRECTION. Arch couldn't change the MODE, which is where all the score lives. Always pair on seed; use max_depth (farmer 1.152±0.011 vs diver 3.7, ~100 sigma apart) as the mode readout instead of noisy score.

**ROOT CAUSE FOUND — FARM-vs-DIVE IS SEED-GATED EXPLORATION, NOT CONFIG (2026-07-17, supersedes the "cfg1 always farms" claim below, which is WRONG).** Reproduced wandb's 3800 exactly: seed102 on stock HEAD 8215eb9c + committed cfg1 -> **score=3815.95, max_depth=3.687**. Score and depth are THE SAME AXIS: every farming seed (max_depth≈1.15) scores 3105-3518; the one diving seed (3.687) scores 3816. So cfg1 DIVES FINE on seed 102 — there is no cfg2 needed, **seed 102 IS the diver** (use it as the A/B vehicle for diving work). LEARNING CURVES tell the story: s102 climbs monotonically 1.0->1.25->1.56->2.0->3.0->3.7 (plateau, peaks 4.28), compounding descent all run; s43 hovers 1.0-1.3 the ENTIRE run and NEVER discovers descent. => **exploration bifurcation w/ positive feedback**: descent_coef=1.888 is the highest-weighted coef so ANY early descent compounds, but finding the downstairs is sparse (`>` needs you ON the stairs). "Seed variance" = P(discover descent early) ≈ 1/4. PATH TO 4000 = two separable levers: (a) raise P(dive) -> mean 3431->~3800 (+370, zero model change; exploration problem — note **anneal_ent_coef=0** so entropy is FLAT at 0.0052 all run; also descent/scout balance or stairs-finding shaping); (b) raise divers' depth ceiling 3.7 -> deeper (survival wall — THIS is where hp_frac/prayer/AC/depth-rep finally bind; the earlier "stat rep is inert" verdict was measured on FARMING runs at depth 1.15 and does NOT apply to a diver). SWEEP CAVEAT: metric=max_depth but mode is seed-gated, so Protein fits SEED NOISE not config quality — needs multi-seed per suggestion or a de-randomized discovery.

**SEED VARIANCE DOMINATES EVERYTHING (2026-07-17, critical).** Identical code (HEAD 8215eb9c) + identical committed cfg1 config, only seed differs: s73=3148, s43=3259, s44=3518, **s102=3800** (wandb encoders/sweep-cfg1-340m, 340M). mean=3431, sample **sigma≈291**, spread 652. Consequences: (1) **there is NO 3500 ceiling** — stock baseline already hits 3800 on a good seed; (2) a 2-seed-vs-2-seed A/B has SE(delta)≈291 -> **95% CI ≈ ±570**, so EVERY arm this campaign (9 arch + dirmask −246) was UNDETECTABLE, not merely "null within ±350" — we learned nothing from any of them; detecting a real +200 needs **~34 seeds/arm** at 340M = infeasible; (3) the Protein sweep uses `metric: score` on SINGLE runs -> it is partly **fitting seed noise**; a "winning" config may just be a lucky seed. REFRAME: gap is mean 3431 -> best-seed 3800 -> 4000, i.e. mostly **VARIANCE not capability**. Same process finds a 3800 policy on one seed and 3148 on another = likely multi-modal strategy discovery; making the good outcome reliable is worth ~+370 on the mean with ZERO arch/representation work. NEXT: diff s102's learning curve + behavioral stats (max_depth/eats/rests/gold/xp/damage_taken/deaths) vs s73/s43 to find what 102 learned differently. Never again run a 2-seed A/B and call it a verdict.

Ran a 9-experiment encoder-architecture sweep on the nethack config (committed cfg1, [[nethack-env-setup]]) to push score 3500->4000. **Verdict: architecture is not the lever.** Every arm is null within the seed-noise floor (see above — the floor is ±570, WIDER than the ±350 originally estimated); the controlled baseline@340M alone spans seed43=3259 / seed44=3518 / seed73=3148 (mean(43,44)=3388.5), a swing bigger than any arch effect.

Arms (2-seed mean(43,44) vs 3388.5, wandb project `encoders`): crop11 3364(−24), locwide512 3286(−102), B1+B2-combine 3231(−157), fuse1024 3203(−185), glb-deep 3177(−211), fuse-2layer 3056(−332); B1 fuse512 paired Δ≈−7; B2/A1 ~null/neg. Bigger nets trend slightly negative (mild under-train at fixed 340M budget = 358906224 steps). All CUDA arms gradcheck-verified (finite-diff + torch parity ~1e-8).

GOTCHAS discovered:
- **SEED KNOB: `--train.seed` is a NO-OP** (silently ignored; pufferl.py never reads seed). Base `--seed` (default 73) is the real training seed -> HypersT.seed. All "s42"-labelled runs actually ran seed 73. Verify any flag actually changes the run (compare early-epoch trajectory).
- **PATCH KERNEL SMEM WALL**: nh_patch_max_bwd_kernel static __shared__ is at the 48KB limit. navP1-32(78KB) & glbwide256(63KB) BUILD FAIL. Any patch-INTERNAL mod (nav-meanpool, patch-2layer, wider NH_P1/NH_GLB_HID) needs a dynamic-smem rewrite. Post-pool mods (glb-deep) are fine.
- Structural-insertion pattern (fuse/loc1/glbh/fuse2) is mechanical: add weight+bias, act, wgrad/bgrad (muon walks weight&grad lists pairwise by shape), init kaiming, reg_params/reg_train/reg_rollout, forward mm+bias_relu, backward relu_bias_bwd+puf_mm_tn_splitk+puf_mm_nn, extend nh_bias_flush_kernel by a d-slot (bias at END of bacc), + gradcheck harness (test_nethack_cuda.cu TENSOR_ACC/GRAD_ACC + test_nethack_encoder.py WEIGHT_NAMES/enc_names/getw/torch-ref). inv1_b FD-fail in gradcheck is pre-existing max-pool noise (torch-clean).

REAL lever for 4000 (arch exhausted): farm-vs-dive is REWARD-gated not perception-gated — cfg1 always farms (~3400 ceiling); cfg2 dives (depth4.5, higher ceiling) with the SAME encoder. And the failure tail's prayers_low_hp≈0 is obs-limited (ublesscnt prayer-clock ablated, nethack.h ~L329). To chase 4000: diving-capable reward config (descent/death coefs) and/or un-ablate ublesscnt. Full campaign log: session scratchpad CAMPAIGN.md / RESULTS.txt.

MOVEMENT-MASK NULL (2026-07-17): masked direction heads into seen walls (glyph 2360-2370, EXCLUDE S_stone=2359=unexplored) in nethack.h mask builder. 2-seed mean(43,44)=3142.1 vs baseline 3388.5 = −246 (s43 −79, s44 −413) — null-to-negative, trained policy already avoids walls + shared dir head clips wanted kick/zap/dig. REVERTED to clean baseline; diff saved scratchpad/dirmask.patch (git apply to restore). GLYPH_CMAP_OFF=2359 (=NUM_OBJECTS 453 + 5*NUMMONS+1), is_cmap_wall=cmap 1..11; verified via probe vs generated pm.h/onames.h.

STAT-BRANCH AUDIT (2026-07-17): blstats rep is `nh_blstats_kernel`->78-dim bl_feats (25 norm scalars: log1p for score/gold/exp/time idx 9/13/19/20, linear else; 7 hunger onehot; 13 cond bits; 1 prayer-cooldown [ZEROED=ablation]; 14 prev-act onehot; 18 inv-class counts) -> bl_w linear 78->64 = bl_out; concat gets BOTH bl_out(64)+raw bl_feats(78). Verdict: encodings are fine OR inert — the farming champion occupies a DEGENERATE stat-corner (depth≈1.15, burdened_frac≈0.001, align/hd frozen) so re-encoding near-constant inputs is a no-op (why every stat tweak = noise, same wall as arch from input side). Real gaps: (a) hp_frac / ene_frac — ratio the shallow linear+MinGRU can't synth from separate scalars, hp varies every fight; (b) time log1p loses tail resolution for pacing (no un-logged fallback); (c) geographic depth/dlevel/dnum + cap(encumbrance) + align are mis-typed (linear scalar for low-card categoricals; should embed/one-hot like hunger) but INERT under farming. KEY (user): the SWEEP is metric=max_depth (diving) so diving configs WILL be sampled — poor depth rep HANDICAPS them and biases the sweep AGAINST diving. So the diving-subset {geo-embeddings, cap onehot, hp_frac, turns_since_last_prayer} IS on the sweep's critical path. Encoder is FIXED across sweep (shared infra, not swept) -> land once + re-baseline + confirm no farming regress, THEN sweep. DE-RISK: A/B the rep on cfg2 (known diver) FIRST — if it helps the diver, bake into sweep encoder; null on diver = diving limited by reward/danger not perception. dirmask.patch also a cfg2-A/B candidate (more exploration=more wall-bumps when diving). AC ÷10 principled (monotonic/signed) but under-used: wears≈0.2/ep, agent under-armors = BEHAVIOR/reward gap not encoding.

2026-08-13 OVERNIGHT ARCH TRIO (all inline-10K-eval'd, paired vs certified
full panel {305:6981, 306:6937, 307:7287, 309:6835, 310:6645}):
- **pileent** (pile-underfoot 8-glyph obs + param-free e_eff max channel, env
  fingerprint 9349f202): 6447/6280/6089/6965/7391, paired mean −303, spread
  −1198..+746 → noise-to-mildly-negative; matches old entity-channel inertia.
- **meanch** (raw-rep mean channels appended for inv/spell/pile, uniform-share
  backward): 4569/4512/4470 = paired **−2552 CATASTROPHIC 3/3** — AUTOPSY
  2026-08-13: v1's inv mean included the ~45 EMPTY slots whose relu'd PAD
  reps are learned+nonzero → channel ≈82% pad vector AND backward hammered
  the pad embedding via 45 slots/sample → drifting pad rep corrupts empty-
  slot semantics branch-wide. Spell side immune (empty keys exact zeros).
  → v1 result INVALID as a test of mean pooling. **mean2** v2 (pad-masked,
  count-normalized inv mean + /8 spell mean, champion hid16 base, no pile,
  binary ./puffer_mean2, det 1539a697): 3 seeds queued 2026-08-13.
- **hid32** (NH_INV_HID/NH_SPKEY 16→32 revert, ON TOP of pile): 7566/7334/7305
  = **+333 vs champion controls (3/3), +1130 vs same-seed pileent (3/3)** —
  the 16-dim bottleneck optimization traded away real score. Binary saved as
  ./puffer_hid32 (built WITH pile obs); clean hid32-only arm (champion, no
  pile) is the decisive follow-up before any commit. Perf cost: 46.8KB smem
  config (the old pre-optimization shape).
- full1b fills: s704 8527, s706 8994 (s705 DIED silent engine-segv @466M —
  2/day class); certified no-swap 1B panel now n=5: {9586,7927,8512,8527,
  8994} mean 8709 sd 620.
Binaries preserved: puffer_pile/puffer_meanch/puffer_hid32/puffer_champ;
tree = pile-max uncommitted; nethack.cu.pilemax backup in scratchpad.
pkill/heredoc landmine: NEVER write+launch a driver script in one command —
the harness wrapper's cmdline embeds the script text and self-matches wait
patterns (deadlocked 3x on 2026-08-12/13). Write file in one command, launch
by path in the next.

2026-08-13 PM RESULTS:
- **hid32c clean panel COMPLETE** (champion + NH_INV_HID 32, no pile):
  +223/+689/−1339(armor-trap s307, min_ac −3.64 but stat conflates spellprot)/
  +635/+695 = 4/5 pos, median +635, non-trap mean +561, SPS cost ≤5%.
  COMMIT-GRADE pending 1B confirmation pair. Binary ./puffer_hid32c.
- **mean2 trio** (pad-masked count-normalized inv mean + /8 spell mean, tail
  +32 dims, champion base): +189/+419/−171 = +146 mean, 2/3 — mild lean,
  not decisive; park, retest on whatever base wins. Binary ./puffer_mean2.
- **SWEEP EARTHQUAKE**: their-box sweep (async base, ac_coef 0 unswept,
  Joseph regime dims) trial sweep_1786612105278_0209 CERTIFIED inline eval
  **8,697 (n=10,010) at 217M** — beats champion baseline 6,970 by +1,727 at
  smaller budget, ≈ champion 1B panel mean, exceeds all-time 250M archive max
  7,937. Config = coupled small-step regime: minibatch 4096, horizon 128,
  agents 512, lr 0.00077, clip 0.10 (floor), vf_clip 0.01 (floor), vf_coef 4
  (max), ent 0.023, momentum 0.987, gamma 0.998, lambda 0.27, replay 1.69,
  217M; reward exp 0.113/xp 0.24/descent 0.76/gold 0.0027/scout 0.010/death
  −0.32/ac 0; profile: search20 827, game_time 11,748, wears 9.3 with NO ac
  reward (small-step regime learns delayed verbs unaided — bimodal-verb
  implication). Exact config saved config/val0209.ini; 5-seed validation
  panel val0209 RUNNING (champ binary, fresh seeds 305-310, ~23min each).
  Decision: mean > ~7,600 → new base recipe, rebase hid32/mean2 onto it.
  Sweep-side notes: wandb eval/score rows missing (watcher --idle 180 closes
  before inline eval; true evals in trial .ini metrics); suggestion cost cap
  3600 still limits budgets ≲500M.

2026-08-13 EVE — **0209 VALIDATION COMPLETE: NEW BASE RECIPE.** Panel (fresh
seeds, exact config, champ binary): 9527/8387/9072/9037 = **mean 9,006 ±469
(n=4), +2,036 over champion 6,970, at 217M** (s310 lost @104M to the silent
engine-segv class — 3rd this week). Every seed beats the old config's
all-time archive max (7,937). Anatomy: shallower (d5.5-5.7), lower rate
(0.69-0.73/turn), wins on lifespan 12-13K turns; search20 870-943; wears
~7.5 with ac_coef 0; s307 did NOT armor-trap here (9,072). Config =
config/val0209.ini (committed? NO — untracked... verify). γ/tempo caveat:
part of gain = macro discount arbitrage (γ per decision; SEARCH20 = γ^19
subsidy) — SMDP research program defined: Phase 0 tau telemetry COMMITTED
(tau0/1/2_4/5_9/10_19/20p buckets); Phase 1 = turn-aware gamma
(train.turn_gamma, γ_turn^τ in GAE/vtrace, calibrate γ_turn=γ^(1/6.5))
pending build; user rejected macro removal after cap/compute analysis.
Next queue: hid32+0209 combo ×3, s311 replacement, 0209@1B overnight.

2026-08-13 — **NOMACRO ABLATION (user-ordered): mask SEARCH20+RUN on 0209
recipe** (env.mask_search20=1 env.mask_run=1, pre-existing knobs, group
nomacro, same seeds/binary): certified 2,661 / 2,771 / 2,366 = **mean 2,599
±171 (n=3)** (first s307 died 13s in — collateral from my concurrent fpgate
on shared GPU, lesson: NEVER run builds/probes while a panel seed is
launching; rerun clean). vs control 9,006 = **−6,400 (−71%%): macro
clock-exchange is load-bearing**; depth pivot replicated 3/3 (8.9/8.5/7.6).
**CAP-100K A/B (user-ordered prep for turn-γ): NH_MAX_STEPS env override
committed 7033bdb0** (default 10000 unchanged, fpgate PASS). Matched-seed
single-variable test, 0209 recipe s305, cap 100K: **certified 10,064 (n=10K)
vs control 9,527 = NEW ALL-TIME CERTIFIED RECORD at any budget** (prev best
9,586 @1B). No harm confirmed; +537 within basin noise (±469), don't claim
causal gain from n=1. Control truncated episodes in 10/1552 windows (first
82.5M, ≤1.4%/window — the farm-streak tail); cap-100K run truncated ZERO.
Cap cleared for turn-γ arms. Cap-200 probe + nomacro 2.78% truncation =
knob verified live both directions. Full quartet: +537/+960/+1069/−580 =
mean +496, t≈1.3 (adopted on mechanism, not significance). **QUANTILE
VERDICT (paired same-env 6K-ep evals, 3 seed pairs): distribution-wide,
NOT tail** — p50 +9.4/+18.6/+11.5%, gains flat p25→p90, p99 gains SMALLEST;
mechanism = truncation-as-terminal value poisoning repaired (matches
`// truncation reported as terminal too` in puf_step). ENTHRONED eb74da7d:
nethack.ini = 0209 recipe + async + eps sweep re-enabled + exp_coef sweep
max 0.2; netlib cap default 100000; new fpgate era ref 703c4adf… (old
champion ref retired, in fpgate.sh comment). D-line turns column DEAD
(blstats teardown at done — known gotcha, walked into again); score/eplen
from tracked stats, valid. s309 AUTOPSY: control was the panel's top farm
basin (34 truncation windows from 58M — most marathon-heavy; rolling 10,094);
cap arm forked at 58M (first would-be truncation flips RNG) into a diver-lean
mid basin (d6.3, game_time −13%, search20 841 vs 955) — paired eval −552
mean, uniform −4-8% all quantiles, entropy healthy, NO cap-specific
fingerprint = basin lottery. Paired 4-pair summary: +845/+1286/+900/−552 =
mean +620 (t≈1.5). SAFETY VERDICT: cap adopted — correctness fix (truthful
value targets), stable 5/5 runs, EV +500-600, one negative = ordinary basin
variance. Definitive causal certificate would need ~8-10 pairs; not queued.

WEAR-churn (idle-mass sink post-macro): accelerates with episode length
(5.8→31 wears/1K steps by quintile, top-5%% eps 132; WEAR macro = atomic
swap, internal takeoff uncounted) — structural PG sink (cost ~150-250
turns/ep, below noise floor → no gradient; entropy 0.0229 feeds it), inflated
by macro-tuned hypers; SEARCH20 = the PRODUCTIVE idle sink (design law). (single-turn camping
tried early then abandoned; farming unaffordable at 1 turn/decision; 10K-step
cap would bind at the score tail). BUT the survivor PIVOTED TO DESCENT:
mean max_depth 8.5-8.9 with ZERO reward changes — deepest score-config depth
ever (wall was 6.5) — direct behavioral proof that macro economics suppress
decision-dense strategies. Dual verdict: SEARCH20 = +6.3K score AND the
depth suppressor. τ forensics (see tempo-hygiene memory: Monk-Fast 25% free
actions, no zero-turn pathology; SEARCH20 mean τ 12.25, elementary ~0.76 →
true subsidy ratio ~16×) refined Phase-1 calibration; zero-turn "spam" alarm
RETRACTED (speed physics + rolling-stat inflation, not an exploit).

**2026-08-14 OVERNIGHT: 1B SCALING CONFIRMS, ALL-TIME RECORD 12,864.**
new1b_s305 (enthroned base, 1B) certified **12,864** (+2,800 over its 217M
control 10,064; old-era 1B mean 8,709). Curve: fast to ~6K by 150M, PLATEAU
150-400M (schedules are FRACTIONS of total_timesteps: verb_eps_anneal_start
0.4 → ε constant to 400M; lr stretched 4.6×), then anneal-endgame takeoff.
eps0_1b_s306 (verb_eps=0 from scratch, 1B): **12,466** — ε ≈ neutral at 1B.
BUT eps0 at 217M = **−1,950**: 7,966/6,714/7,799/7,736 (s309 died @41M,
unexplained, no segv trace in logs — only casualty of a 17-run night on the
fixed engine) vs controls 9,502 → ε's value is BUDGET-DEPENDENT: essential
at 217M, redundant at 1B. FOOD/PRAYER ECONOMY: champion prays 10.6-11.5/ep
= max sustainable pray-at-weak cadence (hunger cycle ~1,000 turns > cooldown
median ~350 — hunger one-hot is the visible timer for the hidden cooldown,
same pattern as spellprot recadence). Lifespan ~13-14K turns ALL classes =
prayer-cadence ceiling; classes self-select depth to equalize hazard →
class value = kill-rate/turn only. USER LEVER (untested): prayers→HP-heals
+ eat farm corpses (floor_eats 1.5-3/ep only!); panic-prayers at death fail
because cooldown spent on food; coupled-behavior valley; prize ≈ fainting
class + chip deaths. Next: 1B-ckpt prayer/eat mix + prayer-outcome census.

**MULTI-ROLE CAMPAIGN (challenge protocol) 2026-08-14: BUILT + BASELINE.**
./puffer_multi (patch scratchpad/multi_role.patch + vendor nle_identity
accessor): engine-random role/race/gender/align per reset (options
role:random..., PICK_RANDOM validity), identity read-back, 13+5+2 one-hots
in extra (align via blstats), role_ix log stat (~6 = mixing OK).
multi217_s305 certified **3,718 mean** (= AutoAscend challenge mean 3,821
at SANITY budget); per-episode: median 2,081, p25 829 (n=10K merged) —
MEDIAN GAP = CONSISTENCY GAP (AA median 5,337 > its mean; scripted bot =
tight distribution; our farmer right-skewed in every role, p50≈0.6×mean).
Transfer PROVEN: Priest 231%% of specialist at 1/13 compute; generic-melee
roles 86-93%%; idiosyncratic-strategy roles (Ran 59%%, Tou 61%%) dilute
worst. Identity effects (within-role, n~100-300/cell): Orc Bar +842 (poison
res!), GNOME universal tax −1,000..−1,600, Elf lifts casters/rogues,
Chaotic Wiz +1,515 vs Neu (unexplained), Mon-Hum-Cha best cell 7,761.
Ledger artifact: claude.ai/code/artifact/6d5a60ed-72b2-4015-afd5-c559d650af5c
multi1b_s305 RELAUNCHED (first attempt died 123M — likely my concurrent
eval; GPU exclusive now). ac_coef quartet aborted mid-way: pri +76 null
(wears unmoved), hea +385 (+24%%), wiz/cav not run.

**MULTI-ROLE 1B LANDMARK: certified mean 6,608 — AutoAscend challenge mean
(3,821) beaten by +73%% with ONE policy under the full protocol.**
Per-episode (n=6,038): mean 5,915 / median 3,685 (AA median 5,337 still
ahead — consistency gap narrowed 2,081→3,685; p25 829→1,190). Per-role:
ELEVEN OF THIRTEEN ROLES EXCEED THEIR 217M SPECIALISTS (Pri 426%%, Kni
186%%, Cav 160%%, Sam 153%%, Bar 152%%, Hea 150%%, Rog 124%%, Mon 110%%,
Val 109%%, Wiz 104%%, Ran 103%%; below: Tou 83%%, Arc 82%%). Multi-Monk
11,106 = 86%% of the dedicated 1B monk at 1/13 role-compute. Both
underperformance mechanisms closed by budget (Ranger 103%% — niche
strategies recovered too); Tourist/Arc = the only residual dilution.
Median frontier: needs floor-raising (p25 class), possibly non-uniform
role sampling or median-shaped objective (reward territory). Curve was
STILL climbing at 1B cutoff — 2B is live headroom.

**FULL 13-ROLE TABLE (single seeds, 217M):** Monk 10,064 / Valk 7,643 /
Barb 6,605 / Sam 5,254 / Arc 4,769 / Ran 4,693 / Rog 4,613 / Cav 4,400 /
Kni 3,562 / Wiz 3,329 / Tour 2,705 / Hea 1,592 / Pri 1,035. Uniform mean
4,636 / median 4,613 vs AutoAscend challenge mean 3,821 (beaten, by
specialist ensemble) / median 5,337 (short). Priest anomalously low
(investigate); Healer ≈ its starting gold. Round-2 s306 seeds in flight.

**2026-08-15 re-confirmation at hidden-512, embed-champion base (217M, vs idb
controls 3,520 s401 / 3,894 s402).** Two bottleneck widenings, both null:
- entity bottleneck NH_INV_HID 16→32 (inventory slot rep AND spell keys share
  the width; also widens the pointer-decoder key/query space): s401 3,638
  (+118). s402 killed.
- global patch bottleneck NH_P1 16→32 (800 numbers per 5x5 patch): s402 4,020
  (+126), s401 3,568 (+48), mean +87.
Both are inside noise (the provably-inert bok bit scored +425 on s401). Widths
are made overridable via -DNH_INV_HID_DIM / -DNH_P1_DIM, default 16, flag-off
fingerprint verified 486f55e1 each time.
**Two smem landmines found widening P1** (both silent, both fixed in-tree):
(1) nh_patch_max_bwd_kernel staged 4 arrays scaling with P1 = 78KB > 48KB —
dW2 now accumulates straight to global (fixed-point adds are order-free, so
P1=16 stays bit-identical); (2) nh_dT_patch_scatter_kernel requests
NH_HOT_G * NH_TROW int64 of DYNAMIC smem = 64KB at P1 32 — the launch fails
SILENTLY and only glb1_w's gradient comes out wrong (0.44 rel err while every
neighbour is 1e-6). NH_HOT_G is now derived from the 48KB ceiling. Lesson:
widening any arch constant needs a gradcheck, not just a clean compile.
