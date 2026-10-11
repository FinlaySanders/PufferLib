---
name: nethack-action-expansion-campaign
description: "autonomous campaign expanding NetHack action/obs space (friend's \"verb set incomplete\" lead) toward score 6000"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-07-23T16:15:19.966Z
---

Goal: push NetHack agent score champion 4339 (seeds 43/44 = 4258/4421) -> **6000**, autonomously. Env/encoder only (reward is the separate-box sweep). Log ALL runs to wandb **project 'encoders'**. Friend's lead: verb+slot pointer arch is right, but the VERB SET was incomplete (no takeoff/apply/drop/puton/...). See [[no-class-pruning-action-space]], [[nethack-arch-campaign]], [[nethack-env-setup]].

**Run cmd** (this box pufferbox3/4090, deterministic; reward sweep is on a SEPARATE box):
`puffer train nethack --seed S --train.total-timesteps 358906224 --wandb --wandb-project encoders --wandb-group <rung>`
358906224 = 2x config default, reaches LR anneal (matches champion 4258/4421 protocol). ~13-20 min/run @ ~450K SPS. Build: `./build.sh nethack` (guard: nvidia-smi compute-apps==0 first). Gradcheck: `python tests/test_nethack_encoder.py` (must print RESULT: PASS). Eval each ckpt via scratchpad/probe_ckpt.py (real vec path, n=10k score + telemetry).

**RESULT R1-core (autopickup OFF): s43=3698 (probe n2800) = -560 REGRESSION vs champ 4258.** Mechanism: pickups learned to 0.01 (credit-chain too long) -> no food/gold acquisition -> starves, prayer-farms food (prayers_starving 10.1). Skipped s44 (clear regression). => acquisition loss > verb gain. Pivoted to R1-wide (autopickup ON + wide pickup_types $[%!)/="(?+* + DROP wornreq 0->2 + PICKUP mask gu_obj||gu_corpse). RESULT R1-wide (autopickup ON wide): s43 probe ~3550 (peaked 3846, plateaued 3695) = ALSO ~600-750 REGRESSION, ≈ R1. => acquisition is NOT the cause; the ACTION-SPACE EXPANSION itself (22 verbs/690-wide/12 heads) is a WORSE OPTIMUM at 358M budget. Equip/tool verbs (puton/apply/remove/wield) ≈0 even with items -> dead weight + convergence tax. TWO configs agree.
CHAMPION CONTROL DONE: retrained champion s43 on this box = **4257.686 log (=remembered 4258 exactly, NO DRIFT) / ~4160 probe**. => R1/R1-wide are REAL regressions (−460/−660). **ACTION-EXPANSION ABANDONED** (rigorous negative: 690-wide/12-head = worse optimum + dead equip/tool verbs). Tree = CHAMPION (reverted). Expansion saved scratchpad/R1_expansion.patch. R2/R3 (more verbs/heads) MOOT — would only add more tax.

**STRATEGIC CONCLUSION**: env/encoder now looks CAPPED ~4258 for this reward config (action-expansion was the last big lever; arch null, ±100-200 features noise). Champion ceiling mechanism confirmed (control telemetry): dives depth 4.2 @ xp 6.3 = UNDER-LEVELED, 87% combat deaths. 6000 lever = REWARD dive-vs-level (descent 1.888 >> xp 0.281) = the SEPARATE-BOX max_depth sweep's domain. ENT-COEF RE-SWEEP TEST (user hypothesis: regressed b/c hypers swept for 5 heads not 12): ent_coef 0.0052->0.0026 -> probe ~3582, entropy STILL ~10 (didn't sharpen). => ent_coef NOT the culprit; top single hyper falsified. Full joint re-sweep untested but upside-capped ~champion (verbs unused). 4 expansion runs all ~3500-3700 (acq-off/acq-wide/ent-lo). ACTION-EXPANSION not tuning-fixable via ent_coef and not the 6000 path. Tree=champion (reverted again). Surfaced scope fork: 6000 lever = REWARD (dive-vs-level); sweep >24h old likely done; awaiting steer whether reward is in scope here. Env/encoder honest best-remaining = minimal READ-only (only new verb that fires), but ~champion not 6000.

NORMALIZATION / NMMO-EMBED A/B CONCLUDED (2026-07-19, NULL): user push on obs scaling ("strictly in [-1,1]" + "how does nmmo scale"). Findings: (1) NMMO3 barely normalizes -- one-hots the map, bucket+EMBEDS player scalars (nn.Embedding 128->32) AND feeds them raw unnormalized (0-127), reward raw (0-255); literal "TODO you scale wrong" comment. Proves net absorbs raw scale via linear layer. (2) bf16 is SCALE-INVARIANT (float relative precision) -> "hp/200 too small" is NOT info-loss; the real scale effect is grad conditioning, which bl_w already absorbs. hp_frac won via the RATIO (nonlinearity), not scale. (3) A/B/C @180M s43 log-perf (champion @180M baseline ~3438): CLAMP (strict [-1,1] on every blstat feat, champion scales) = 3697.9; Arm A (recalibrate: log depth/xp/dlevel, hp/hpmax /150, cap /5) = 3624.1; Arm B (Arm A scales + zero-init one-hot embeds depth32/xp32/dnum8 added to bl_feats, bl_w+proj_w embed cols zero-init'd = ekind_w idiom, generalization-safe additive) = 3596.8. ALL within ~100 on same seed << +-300 noise. Isolations: recalibrate (A vs clamp) -74, embed (B vs A) -27 -- BOTH NULL. => strict normalization + NMMO-style discrete embedding are NOT score levers (network absorbs scale; embed adds no usable nonlinearity at dlvl~3.8). CLAMP is the only keeper (neutral now, deep-play-safe, free). Caveats: single seed (tight same-seed clustering argues real-neutral); Arm B embeds zero-init (slow-grow) so 358M could give more time but campaign prior = representation null. GENERALIZATION PRINCIPLE (user's key steer): embeddings destroy ordinality -> no extrapolation to unseen depth; NEVER replace an ordinal scalar; only embed nominal (dnum) or additive+zero-init beside the kept scalar. Lever remains REWARD sweep.
N=4 MULTI-SEED FINAL (2026-07-19, s43-46, all NULL): baseline(champ+clamp) mean 3509, A(recalibrate) 3480 (-29), dnum-only 3497 (-11), B(embed-all depth/xp/dnum) 3679 (+171). dnum "win" EVAPORATED: seed-matched vs A was +98/+80/+77 then s46 -184 -> +18 mean = n=3 LUCK (user's push for seeds caught it). B highest mean but NOT real: per-seed vs baseline -101/+469/+529/-213 (sign flips), p~0.20, ANTI-correlated with baseline (high where base low) = seed-artifact not signal. VERDICT: normalization/embedding NULL; adopt champion+CLAMP only (clamp neutral+deep-safe+free, the one keeper); drop recalibrate/dnum/depth-xp. Patches saved scratchpad/{armA_full,dnum_only,armB_full}.patch. LESSON: n=3 "consistent sign" is NOT robust; need n>=4. NMMO deep-dive: NMMO (most-ablated env in lib) embeds ALL player scalars (shared Embedding(128,32)) AND feeds raw = B's additive design; but NMMO is unsolved + also has undertrained high buckets, so not proof; embed+scalar is a common default not a correctness proof. NEXT (user pick): THREAT DELTA feature = mons[glyph_to_mon(g)].mlevel - hero_xp, pooled max(visible)+max(adjacent), 2 scalars -> encoder. FAIR: base mlevel is fn(visible species/glyph) like hp_frac; use baked species->mlevel table (glyph->species->static base, NEVER live mtmp->m_lev which=privileged true level; NO monster HP=hidden). libnethack.so exports mons (D sym); mlevel in permonst.h:45; glyph macros in display.h (GLYPH_MON_OFF=0, glyph_to_mon, glyph_is_normal_monster); gen via hack.h-including generator like scratchpad/gen_glyph_map.c. Reward-supported (flee/pray vs 87% combat death) = better prior than dnum but still just-one-AB expectations. Entity channel was reverted 2026-07-14 b/c tested PRE-stair-mask (agent rarely descended) not b/c threat useless -> retest vs current champion (which descends+dies to combat).

APPROVED AUTONOMOUS CAMPAIGN (2026-07-19, run ALL one-by-one, log wandb 'encoders', n=4 vs champion+clamp baseline 3509 unless noted; drive arm-by-arm via completion notifications; each arm: implement->gradcheck PASS->build->run seeds->report->advance). BUILD GOTCHA: never rebuild _C.so while a seed-sweep runs (later seeds load wrong .so); gradcheck compiles its OWN test lib so it's safe during a run. Patches: scratchpad/threat_pooled.patch (=A1), R1_expansion.patch (all 7 verbs), armA/dnum/armB_full.patch.
PHASE A threat delta ladder (factorial): A1 POOLED = 2 scalars max(visible)+max(adjacent) mlevel[glyph]-hero_xp, /10 clamp, in extra block. RESULT n=4: 3266 vs base 3509 = -242 REGRESSION (seeds -405/+47/-490/-121, neg 3of4). Threat HURTS under descent reward (steers toward caution/flee when it needs to fight through to descend) = reward-regime-dependent liability, not null. gradcheck was PASS + layout verified so not a bug. => threat likely needs a survival-rewarding regime; A2/A3 run anyway to complete factorial. A2 PER-ENTITY = per-tile threat in the 9x9 loc crop: modify nh_local_gather_kernel to add threat_w[NH_EMBED_DIM] (zero-init) * (mlevel[cropglyph]-hero_xp) to the gathered embedding -- IN-ENCODER, NO obs change (crop already has glyph id, xp in blstats); needs nh_mon_mlevel table on GPU (__constant__) + threat_w weight + backward + gradcheck. NO pooled scalars. A3 BOTH = A2 + re-add A1 pooled scalars. Factorial: A1=is precomputed max useful; A2=can conv extract it / does spatial help; A3=interaction.
A2 PER-ENTITY ABANDONED (2026-07-20): hand-written CUDA (threat_w modulation in loc gather + crop_threat buffer + threat_w reduction backward) hit an unresolved forward-corruption bug (torch vs cuda out diff 20.4 even at threat_w=0, gather-read-neutralized, buffer-padded; not alignment/modulation/mlevel). Reverted. WIP saved scratchpad/nethack_A2_wip.cu. Given A1=-242 low-value, not worth more debugging. Lesson: hand-written new-weight+kernel encoder changes are high bug-risk; VALIDATED PATCHES (like R1_expansion) apply+gradcheck clean, prefer those.
PHASE B REFRAMED (user hypothesis 2026-07-20): the R1 -600 "convergence tax" may be MOSTLY autopickup-off + BAD MASKING, not head count. EVIDENCE: R1_expansion.patch has the DOWN/UP gu_obj leniency (m[DOWN]=0 only if !gu_obj && not-on-stairs) = the EXACT stair-mask-breaking bug that tanked depth in manual-pickup arc (object underfoot -> DOWN legal everywhere -> policy no-ops instead of descending). R1-core also had autopickup OFF (starvation). R1-wide -600 was under-seeded n=1-2 (n=3 lies). CORRECTED TEST RUNNING (be4wnzkua, expansion-corrected, n=4 s43-46): apply R1_expansion.patch (12 heads/22 verbs, gradcheck PASS) + FIX DOWN/UP to stair-only + narrow pickup_types (match champion) + autopickup ON. If NEUTRAL vs champ 3509 -> tax was a MYTH (verbs ~free with correct masking); if regresses -> head-count tax real. patch saved scratchpad/expansion_corrected.patch.
RESULT corrected-expansion n=4: 3412/3149/3252/3389 = mean 3301 vs champ 3509 = -208 CONSISTENT (all 4 below). => old -600 was ~390 stair-mask-bug+autopickup + ~208 REAL RESIDUAL. NOT head-count tax (idle masked heads = free by construction, 0 gradient; user confirmed). Residual = MIS-USABLE ACTIVE VERBS self-harm w/ no reward correction (long credit chain): WIELD (weapons picked up, wielding kills Monk martial arts = high-freq high-cost, dominant), DROP (discards useful items), TAKEOFF (low-freq but asymmetric: removes good cloak). Monk starts unarmored. KEY INSIGHT: problem is ASYMMETRIC downside (rare-but-costly + delayed/diffuse penalty RL cant attribute) -> MASK beats hope-it-learns.
MASKED-EXPANSION arm RUNNING (bkd5whsw3, expansion-masked n=4): corrected-expansion + m[WIELD]=0 always (Monk) + m[DROP]=0 unless blstats[NLE_BL_CAP]>0 (encumbered-only). env-only (nethack.h), no gradcheck. Tests if WIELD-off+DROP-encumbered erases the -208. patch scratchpad/expansion_masked_delta.patch. TAKEOFF left legality-only (corrective use: undo bad armor).
RESULT masked-expansion n=4: 3244/2853/3187/3239 = mean 3131 vs champ 3509 = -378, vs corrected 3301 = -170 (within noise p~0.17, s44 outlier). => MASKING WIELD/DROP DID NOT HELP -> verb mis-use REJECTED as the residual cause. The ~-200 residual is the 12-HEAD DECODER ITSELF (init RNG perturbation + muon orthogonalizes the whole bigger dec_q_w/dec_k_w so dead rows subtly shift active-head updates = the crack in "free by construction"), NOT verb harm. Marginal (champ variance 3301-3698, corrected -208 p~0.09). Likely a 180M-screen artifact -> may shrink at 358M. So old -600 = ~390 stairmaskbug+autopickup + ~200 uncertain decoder-size cost; verbs ~harmless.
WIDE-PICKUP UTILITY arm RUNNING (b0pn8jwbq, expansion-wide-masked n=4): wide pickup_types $[%!)/=\"(?+* + WIELD-off + DROP-encumbered + IDENTIFIED-ONLY use masks (user directive: no using unidentified items). head_needid[12]={0,0,1,0,1,0,1,0,0,1,1,0} masks QUAFF/ZAP/PUTON/APPLY/READ slots where inv_state byte6 typeknown==0. Tests: do the verbs HELP (PUTON/READ/APPLY now have items) by MORE than the ~200 decoder cost? env-only. patch scratchpad/expansion_wide_masked.patch. If score UP vs champ -> expansion is a NET WIN, "abandoned" flips.
RESULT wide-masked n=4: 2905/2532/2924/2772 = mean 2783 vs champ 3509 = -726 WORSE than every narrow arm. => giving verbs ITEMS + wide pickup HURT badly. CONFOUND (my error): id-mask was applied to QUAFF/ZAP (champion verbs) too -> quaffing unknown potion when desperate = real survival gamble, zap-to-ID standard; nerfing champion's QUAFF/ZAP likely hurt. CLEAN RE-RUN launched (bovi913jy, expansion-wide-clean n=4): head_needid now {0,0,0,0,0,0,1,0,0,1,1,0} = id-mask ONLY new verbs PUTON/APPLY/READ, QUAFF/ZAP restored to champion. Disambiguates QUAFF/ZAP-nerf vs wide-pickup-distraction. patch expansion_wide_masked.patch (wide) -> edit head_needid for clean.
ACTION-EXPANSION ARC (all n=4 @180M vs champ 3509): old R1 -600 (buggy) -> corrected(narrow) -208 -> masked(WIELD/DROP) -378 -> wide-masked -726. EVERY step of adding item-capability got WORSE. Strong support for REWARD-SUPPORT LAW: capabilities (verbs+items) WITHOUT reward crediting good use = net DISTRACTION (agent fiddles instead of descending). => REWARD is the lever, action space alone is net-negative. Decoder ~-200 residual (12 heads, marginal) + item-distraction. If clean re-run also negative -> action line CLOSES with "verbs need reward-support (sweep's job)".
PHASE B action isolation (SUPERSEDED by REFRAMED test above unless that regresses): base=champion autopickup ON, add ONE verb+head each from R1_expansion.patch, ALWAYS n=4 (user 2026-07-19: run 4 seeds in ALL cases, no n=3 screen -- dnum showed 3 consistent seeds then s46 reversed). B1 WIELD, B2 TAKEOFF, B3 PUTON, B4 REMOVE, B5 APPLY, B6 READ (2 variants: 6a read-any legality-only, 6b mask-unidentified oc_name_known -- answer generalizes to QUAFF unknown potions), B7 DROP. Answers: which verb regresses (per-verb delta) + "is it just autopickup" (these keep autopickup ON so any regression = verb/head tax not acquisition; autopickup-off=-600 starvation already settled).
PHASE C (user directive, AFTER A+B): analyze NMMO(src/ocean.cu, most-ablated env in lib) vs this nethack env representational gaps, run derived experiments autonomously. Key gap: NMMO decomposes each tile into ~10 orthogonal semantic channels (terrain/season, item type/tier, entity type/element/comb_lvl-delta/hp-bucket, anim, dir) one-hot->conv; nethack collapses tile to 1 composite glyph token (factored kind/sub embed is partial move). Threat delta = first channel. Phase C = test further per-tile decomposition toward NMMO multi-channel + obs modalities NMMO exploits we don't. Derive exact list from analysis + A/B/threat results, don't pre-commit. FAIR constraint always: only observable-derived (base mlevel yes, true m_lev/monster HP no).

MANUAL-PICKUP ARC CONCLUDED (2026-07-19): autopickup is ESSENTIAL. Manual pickup (autopickup off, isolated PICKUP verb) = 2841 vs champ-baseline@180M 3438 (-600) at SAME depth (4.24). Cause = STARVATION: agent won't grab food (autopickup off + pickup reward too weak/distant) -> prayer-farms food -> long low-value episodes (eplen 2446 vs 1350). The earlier "depth collapse to 1.1" was MY BUG: DOWN/UP mask leniency (legal when item underfoot) + littered floor (autopickup off) re-broke the stair-mask -> fixed with stair-only mask -> depth recovered. So autopickup doesn't affect depth directly. FIX for -600 = just autopickup ON (champion has it). Wide-autopickup+DROP does NOT help without PUT-ON/APPLY/READ use-verbs (extra items = dead weight) = the expansion (tax). Telemetry gold/inv_items added (saved scratchpad/pickup_plus_telemetry.patch, reapply for sweep-winner validation). SWEEP PLAN locked: metric=score, narrow autopickup, champion action space; validate top-K multi-seed on THIS box + screen for degenerate farming. Deep-capability (wide autopickup + use-verbs) = post-sweep DEEP test only.

AUTOPICKUP-DEFAULT GOTCHA (2026-07-19, telemetry caught it): removing "autopickup" from NETHACK_DEFAULT_OPTIONS does NOT disable it -- the option DEFAULTS to TRUE (fast-nle options.c:121). Must use "!autopickup" to turn off. => R1/R1-wide "autopickup off/on" were actually narrow-autopickup vs wide-autopickup (BOTH ON); the -450/-660 regression is still the VERB TAX (conclusion holds, labels wrong). Manual-pickup isolation runs bwnug615e/b67ww3oyy were INVALID (autopickup on). Added gold + inv_items telemetry (Log/Stats/my_log + probe_ckpt keys) -> exposed it (inv_items 21 vs starting ~8). FINDING: gold=49.5 = only 1.5% of ~3350 score at dlvl4 -> score is EXPERIENCE-dominated (kills+depth), gold/items minor shallow. Redo pickup exp with "!autopickup" (bmbjhlu2o).

WATCHER-BUG LESSON: NEVER launch training with `nohup ... &` inside run_in_background (double-detaches; harness notifies on the wrapper not the trainer). NEVER use `pgrep -f "puffer train"` as a completion watcher (matches its OWN command line -> never exits, stalled 10h). CORRECT: launch `puffer train ...` directly via run_in_background (no nohup/&) -> harness tracks the trainer, notifies on real exit.

**R1 CORE = built + validated (gradcheck PASS, builds, smoke no-crash, verbs fire).** Changes:
- autopickup OFF (removed from NETHACK_DEFAULT_OPTIONS); PICKUP verb (,) gated on object-underfoot glyph [1906,2359).
- +7 slot verbs: TAKEOFF(T) PUTON(P) REMOVE(R) WIELD(w,reversible unwield via w-) APPLY(a,dig-down via '>') READ(r) DROP(d). WEAR tightened to unworn.
- verbs 14->22, NH_HEADS 5->12, NH_TAU_PAD 8->16, NH_DEC_PAD 24->32, NH_BL_FEAT 80->88, MY_ACTION_MASK 690, NUM_ATNS 14.
- masks LEGALITY-only (oclass bitmask + worn/wield bit from inv_state byte5). DOWN/UP object-aware (item on stairs doesn't block descent). EAT keeps floor-food exception.
- telemetry: pickups/takeoffs/putons/removes/wields/applies/reads/drops in Log+Stats+my_log.
- Files: ocean/nethack/nethack.h (enum,mask,switch,options,Log,Stats), binding.c (ACT_SIZES,MASK,my_log), src/nethack.cu (4 defines), tests/test_nethack_encoder.py (dims + bl_w dynamic + prevact range(22)), ocean/nethack/nethack.c (demo dims). NOT committed.

**LADDER (additive, gated on 2-seed mean >= prior within noise AND new verbs fire in telemetry):**
- R1 CORE: training now (s43, then s44).
- R2 TIER-2: +fire/quiver/open/close/untrap (reuse dir/slot heads).
- R3 TIER-3: +tty/menu obs + menu-select head + loot/tip/offer (+cast/enhance need known-spell/skill obs). BIG: obs-side change.
- Beyond: analyze weak points, invent more -> 6000.
Regression on both seeds -> diagnose (convergence tax vs capability-hurt; prime suspect = autopickup-off, ablate by turning it back on). Full spec: scratchpad/nethack_action_audit.md + verbset_expand_spec.md. Results table: scratchpad/RESULTS_6k.md.

SEED TRAP (recurring): never trust 1 seed at <±300; champion mean 4339. TRAVEL/JUMP cut (need 2D pointer, not worth it). dir head still 8-way (down/up/self deferred).

2026-07-21 MASKING+PICKUP SWEEP — BOTH AXES NULL (plain E, n=5 s43-47, vs E 3240/champ 3502): PICKUP: narrow $[%!)/ OPTIMAL; pkmin($%!) -359, pkwide(all) -428, pkoff(manual !autopickup) -429 — narrow validated, NOT a lever (even minimal worse => agent benefits grabbing throw/wear material). MASKING (the WIELD/DROP "bug fixes"): wieldoff -70, dropenc -109(s43=1843 outlier ->-367 raw), both -69 — all NULL, recover NONE of the -242. => the expansion -242 is EMERGENT/diffuse from the full 22-verb space being usable, NOT specific self-harm verbs (dead-heads masking ALL 8 recovered it; masking a subset slightly HURTS by perturbing the verb head). CORRECTION: WIELD is REVERSIBLE (nethack.h:903 unwield handler: re-select wielded weapon via W_WEP bit inv_state byte5&2 -> w then '-'; agent sees it via sfeat f[10]) — my "irreversible bug" audit was WRONG. Current masks+narrow pickup = NEAR-OPTIMAL, no masking/pickup score lever exists. Only lever = REWARD (per-outcome-stat support + descent-vs-level balance sweep). ORCHESTRATION BUG LESSON: bash single-quote '\n' passes LITERAL backslash-n to python -> invalid C -> silent build-skip (masking arms failed first run); use $'...' ANSI-C quoting OR python .replace('\\n','\n'). Results scratchpad/RESULTS_6k.md.
2026-07-21 358M PAIRED CONFIRMATION (final 22-verb config vs champion, n=3 s43-45): final 3770/3954/3847 (mean 3857) vs champ 4258/4421/3878 (mean 4185) = **-329 mean** (per-seed -488/-467/-31). => the -242 tax does NOT shrink at full budget (larger), NOT a 180M undertraining artifact. Magnitude champion-seed-sensitive (champ spread 543; s45 was a weak champ seed -> near-neutral pair). Full telemetry: depth a WASH (3.79 both, NOT camping); "dies 28% sooner" was s43-ONLY (s44/s45 eplen match) -> survival-duration NOT the universal mechanism; the consistent discriminator is ENGRAVES (Elbereth, champ ~2x: 23.4 vs 11.5; s44 27.6 vs 0.99) = under-reinforced survival behavior (Elbereth unsupported); rest matched (prayers/rests/quaffs/throws/eats). Tax is REAL but DIFFUSE (expansion plays a less-sharp same-game + ~7.6 drops/ep). Confirms reward-support (not masking) is the fix.
2026-07-21 REWARD-SUPPORT IMPLEMENTED (user decided "it has to be reward support" -> put in Protein sweep). 3 terms added to 22-verb config: (1) heal_coef GAIN-ONLY HP restored by a heal verb (prev_action==QUAFF||PRAY && hp_delta>0) -> credits QUAFF/PRAY, sidesteps symmetric-HP cowardice (hp 0.005 turtled); targets recovery-deficit death mechanism. (2) status_coef SYMMETRIC potential phi=-popcount(blstats[NLE_BL_CONDITION] & NETHACK_COND_BAD=0x3FF, afflictions STONE..HALLU) -> lights APPLY(unicorn horn)/PRAY-cure/QUAFF-cure (only term that activates dead APPLY); symmetric auto-punishes contracting a bad status. (3) ac_coef RE-OPENED (was 0) -> WEAR/TAKEOFF/PUTON/REMOVE, let sweep decide if armor pays. prev_action==current verb at reward time (set nethack.h:1014 before reward :1025). telemetry heal_hp/cures (Stats+Log+binding, same pattern as swaps/min_ac). config: heal_coef=0.01/status_coef=0.1 defaults + 3 sweep.env blocks (heal log_normal .002-.05, status .02-1.0, ac .005-.3). PRINCIPLE (do NOT add per-verb bad-usage penalty): symmetric potentials auto-punish bad effects via the state (cursed armor->AC up, bad potion->hp_coef/status); credit OUTCOMES not presses (null press earns 0, no spam); id-mask/gamble is +EV survival tool (yolo-zap); explicit penalty = double-count + cowardice. Catastrophic-irreversible (cockatrice eat) handled by MASK not reward. Verbs w/ NO live outcome (WIELD/DROP/UP) get NO coef -> entropy-inert, not swept. Next reward gap = disengagement (ELBERETH/REST/READ-teleport) but RISKY (threat-delta -242 fought descent). Built+gradcheck PASS+6M smoke crash-free (verbs 22, NH_DEC_OD 690). READY TO SWEEP on pufferbox3.
2026-07-21 PICKUP PILE-GRAB-ALL SHIPPED (user: "shouldn't the action pick up everything?" -> yes): multi-item piles were a SILENT FREE NO-OP — ',' opens the tty selection menu, which yields inside xwaitforspace with misc[XWAIT] set, and handle_prompts' xwait-drain ESC'd it penalty-free, zero-turn, zero items (probe: 2 dropped items, recovered 0/2, clock stalled; NOT wedged — drain dismisses cleanly). Menus were NEVER reachable: only non-autopicked classes in multi-piles affected (autopickup already scoops all matching $[%!)/ silently, incl thrown-dagger recovery). FIX in PICKUP case (nethack.h): after nle_step(','), while XWAIT (<=2 rounds) send '.' (MENU_SELECT_ALL, in resp via default_menu_cmds) then '\r' (confirm); on a plain --More-- the '.' just bells and RET dismisses (safe on every xwait variant). Probe: 2/2 recovered in ONE press, 1 turn, illegal_delta=0, no wedge. Note singles-pickup already pocketed corpses (raw ','), so pile-grab-all adds no new corpse issue (APE >corpse still keeps autopickup off corpses for floor-eat). PROBE GOTCHAS: inv_letters/inv_state arrays are EMPTY at c_reset, populate on first c_step (mask sees empty inv at episode step 1); hero starts ON upstairs (',' there = "stairs solidly fixed"); dropping shifts inv slot indices (re-find by letter). pickup_probe.c pattern in scratchpad (compile: -I ocean/nethack -I vendor/fast-nle/include -I vendor/fast-nle/build/_deps/deboost_context-src/include -L vendor/fast-nle/build -lnethack -rpath -ldl -lm).
2026-07-21 VERB-MECHANICS AUDIT (triggered by pickup-menu bug; user "are all verbs working as expected?"): the menu bug exposed a CLASS of broken paths — any verb effect raising a menu or non-yn prompt. FOUND+FIXED: (1) PUTON-ring was MECHANICALLY BROKEN since R1: do_wear.c:1938 yn_function("Which ring-finger, Right or Left?","rl",'\0') — auto-'y' invalid -> abort ('\0' default). Fix: macros.h handle_prompts 'ringq' exemption ("ight or Left" -> answer 'r', no illegal penalty, pray-style). Ring probe: 5/5 worn zero-penalty, REMOVE 4/5 (1 fail = correct cursed-ring weld). (2) READ-identify menu was silently ESC'd (scroll consumed, nothing identified): nethack_answer_menu(env) helper (select-all '.'+RET, <=2 rounds, safe on plain --More--) now called in PICKUP + READ cases. NOT extended to APPLY (bag "Do what?" PICK_ONE menu still ESC'd — deferred; select-all is a no-op in PICK_ONE so the helper can't fix it). APPLY DIRECTION (correction): dig-down was ALREADY atomic since R1 (APPLY case answered "n what direction" with hardcoded '>') — my "two-step unlearnable" read was WRONG; applies=0.000 is pure ACQUISITION gap ('(' not autopicked, Monk starts toolless, manual PICKUP rare). 2026-07-21: upgraded to digger-override — inv_glyphs[slot]-1906 == 234(PICK_AXE)|50(MATTOCK) -> '>' (descent-aligned dig), else sampled dirkey (mirror/stethoscope planar). No slot masking for direction tools (direct tools never raise the prompt; masking would kill the horn). ABLATION RE-READS: PUTON "dead verb" was partly UNUSABLE not unlearned (amulets-only worked; rings aborted); pkoff/manual-pickup arms (-429/-560) ran with multi-pile pickup broken -> mildly confounded but starvation-mechanism conclusion stands (food = mostly single items); expansion tax -242/-329 UNaffected (narrow autopickup on, PICKUP 0.077/ep, rings scarce). ring_probe.c in scratchpad. User retuned config defaults: ac_coef=0.01 heal_coef=0.001 status_coef=0.01 (nonzero) + widened sweep ranges (heal .001-.1, ac .01-.5). Patch now 779 lines incl macros.h.
2026-07-21 DNUM ONE-HOT SHIPPED (user: "dnum should be embedded" — nominal per the generalization principle, scalar dnum/10 imposed fake branch ordering): NH_BL_SCALE[23] zeroed (dead scalar, layout stable) + 8-wide dnum one-hot appended to bl_feats (NH_BL_FEAT 88->96, clamp 0-7, NH_BL_DNUM=23); kernel new tail branch after hp/ene_frac; test torch reference mirrored (zeros 96, scale 0.0, one-hot loop). NOTE: differs from the earlier NULL dnum A/B (that added one-hot BESIDE the live scalar, zero-init'd, and was seed-noise-null n=4; this REPLACES the fake-ordinal scalar = correctness change, expected neutral). SCALING AUDIT (user "anything badly scaled?"): str pair FINE (winrl exports STR25 3..25 /25, STR125 3..125 /125 — verified, my >1 worry wrong); real excursions = AC/10 (deep -15 -> -1.5), hp/200 (deep 300 -> 1.5), inv oclass counts *0.125 (20 stacks -> 2.5); logs all fine (<=1.2). KEY FIND: the n=4-validated CLAMP keeper ("adopt champion+CLAMP", 2026-07-19) was NEVER MERGED into the tree — kernel had bare v*scale. NOW SHIPPED: strict [-1,1] clamp on every bl feat at kernel tail + np.clip mirror in test. GRADCHECK GOTCHA: inv1_b FD-check failed 2% after the feature shift — max-pool near-tie artifact (torch ref 7.5e-07 OK); inv1_b added to fd_skip alongside inv1_w/inv2_w/glb1_* (was an omission in the skip set). Gradcheck PASS, smoke clean. Patch 848 lines.
2026-07-21 GETOBJ-WEDGE BUG FOUND+FIXED (user hunt for "the spam loop"; probe = masked-
random policy histogramming illegal+zero-turn per verb, scratchpad spam_probe.c): a
mis-gated macro (e.g. ELBERETH's 'E' mid-combat-message-backlog) leaves a GETOBJ live;
handle_prompts auto-'y'd EVERY yn-flagged prompt, but getobj polls VIA yn_function
wanting an item LETTER -> 'y' = "You don't have that object." -> re-prompt -> UNBREAKABLE
zero-turn loop for the episode remainder (probe: 91% of ALL actions illegal+zero-turn
once wedged; = run-14's 1785 illegal/ep signature; wedged episodes silently died in ALL
prior runs incl champion). FIX (macros.h): commit 'y' ONLY when msg contains "[yn"
(real y/n prompts render choices; getobj renders "[letters or ?*]"), else ESC. ALSO:
UP masked at depth<=1 (dlvl-1 climb = always-declined no-return prompt = guaranteed
zero-turn no-op, was 31% of UP presses). Post-fix probe: illegal+zt 91%->~1.5%; smoke
illegal_actions 20/ep -> 1.7/ep (12x). Residual known: APPLY 33% (container PICK_ONE
menu, deferred), KICK 3.9% (peaceful declines, unobservable, by design). ENV BEHAVIOR
CHANGED -> old bench hash 5e7d1fc73eabda61 stale, re-baseline after A/B. A/B running
(val-wedgefix-180m n=4 s43-46) vs same-day default baseline 3278 (s43-46: 3587/3135/
3087/3303; champion 3509). VALIDATION-DAY CONTEXT: default stack (fixes+dnum+clamp+small
coefs) = E-level 3278 ~= 3301, ALL week's deltas score-neutral; tinybox 3900 s73 runs =
ONE deterministic high draw (same-seed bit-identical replicas; this box s73=3203; vec
topology exonerated — threads 10 vs 32 = bit-identical 3203.497); score=f(seed, software
stack), cross-box absolutes never comparable. User's direction: hunt hp_frac/stair-mask-
class wins (small observable features + degenerate-action masks); candidate list: dist-to-
known-downstairs + explored-frac scalars, Elbereth-active-underfoot flag, adjacent-hostile
count (threat-regression caveat), Elbereth-adjacent mask.
2026-07-21 WEDGE-FIX A/B NULL (val-wedgefix-180m n=4: 3199/3249/3075/3240 mean 3191 vs
baseline 3278 = -87 noise). KEEP as hygiene (illegal 15-36 -> 6-10/ep at convergence).
ENGRAVES-BIMODALITY NOT wedge-avoidance (still bimodal both arms: 16.7/2.7/0.004/3.4 vs
15.7/0.01/37.6/0.01) = a per-seed bistable strategy. ENGRAVE-SCORE LINK (49-run wandb
scan): high-engrave(>8) 3355 vs low(<2) 3055, corr 0.22; ALL 4300+ runs engrave heavily
(champ-358m: 16/36/62); BUT the 1848 camper engraved 61/ep at depth 2.2 — Elbereth is
dual-use (divers survive with it, campers hide with it).
2026-07-22 WANDB API GOTCHA (user caught my false "config bug" claim): run objects from
paginated `api.runs()` listings return EMPTY `.config` — configs ARE logged (nested env/
train/sweep dicts); must `api.run(entity/proj/id)` full-fetch (or json_config) per run.
pufferl.py wandb.init(config=args) works fine — briefly patched it on the false theory,
REVERTED byte-identical (also: pufferl.py = train-side, other person's overlap domain,
do not touch). Sweep run->coef mapping IS recoverable from wandb.
2026-07-22 VARIANCE MINER (scratchpad/variance_miner.py, rerunnable ~1min; full csv
variance_miner.csv): within-config cross-seed CV + pooled z-corr with score over 189
modern-schema encoders runs / 26 cells. CONFIRMS payload = depth x xp (max_xp +.87,
depth family +.52..+.63, damage_taken +.88 = engagement volume wins, death_mon_level
+.63 = die deep not shallow). NEW: episode_length -.42 + truncated -.34 (bistable cv
.94) = camp/rest-farm style LOSES, score-RATE not longevity is binding -> EPISODE-CLOCK
obs feature (cap-fraction visible) promoted to next patch; death_starved -.46 = top
death-census question (fainting-lock hypothesis); fiddle-verb cluster wields -.42
(557/ep spam seed!) reads -.30 takeoffs -.35 wears -.27 all bistable-negative = the
-242 tax visible as SYMPTOM basins (masking already proven null -> reward-support or
nothing); cures +.42 n=13, prayers_low_hp +.25 = early direction-support for heal/status
coefs. Caveat: corr!=cause (damage/death_mon_level are consequences).
2026-07-22 PRAY-TIMER NULL (user-called at n=2: +170/-134 vs ctrl, marker prayers_low_hp
FLAT 0.36/0.38 vs ctrl 0.33 — feature didn't bind the emergency-prayer mapping; s45
killed mid-run, s46 skipped). Census-motivated feature hunt now 0-for-3 today (distfeat
-432, clock demoted pre-run, pray null) — elbflag pattern: sensible observable, no
behavioral leverage. D'-PROBE RUNNING (task booo1qe2y, ab_dprime.sh, chained on bisect
lock; val-dprime-180m s43-46): _C_dprime.so = full tree with ALL 4 new feats zeroed
(ctrl-equivalent) + 8 expansion verbs masked + slot heads 5-11 pinned s[0]=1 (proven-
inert dead-head config). vs ctrl bank 3492. VERDICT: dprime ~= 3492 -> verb tax GONE on
current stack (all-verbs vindicated, polish it); dprime >= ~3650 -> tax persists ->
adopting D' masking = biggest available win (+230-class) while sweep hunts verb support.
NEXT-AFTER: adjacent-hostile-count feat (census-remotivated: 34% deaths with adj>=2,
burst mechanism = crowding not mlevel; distinct from failed mlevel-delta).
2026-07-22 ARMCAT NULL (n=4: +371/-113/-315/-253 = mean -78 vs enh2 bank; wears still
seed-scattered 0.03-0.97, wear-heaviest seed scored worst — armor non-lever at this
depth regardless of legibility). KEPT in canonical (zero obs cost). MINER RERUN (12
cells/60 runs incl today's banks): de-luck well DRY — no new clean target; NEW but
confounded: enhances corr +0.71 n=8 (exposure-confound w/ kills; cells disagree; if
ENHANCE revisited -> skill-rank obs is the refinement). DAY LEDGER: distfeat -432 cut |
clock demoted | pray null cut | D' null (tax gone) | enhance null kept | armcat null
kept — obs/capability polish EXHAUSTED at 180M/depth-4. 2026-07-23 CLEANUP PHASE 2 (all fingerprint-gated, 71021f6ac6b5864a unchanged through
EVERY step): file layout now drone-mirrored: netlib.h 226 (ALL static data: constants,
glyphs, action enum, VerbHead table, options, Log/Stats, NETHACK_VERB_STAT name table) |
macros.h 231 (keystroke dialogue: prompts + item_use + wield + elbereth + auto_enhance)
| nethack.h 663 (env: struct, mask, obs, logging, reset, reward, execute, c_step) |
binding.c 69. KEY REFACTORS: verb-counter ARRAY (verb_uses[22] in Log+Stats, add_log
loop, binding name-table loop — wandb keys preserved); item_use/do_use_item MERGED (fe0
snapshot dissolved); auto_enhance absorbed do_enhance (no do/wrapper pairs rule);
verb fns inlined into execute's uniform 22-case switch (rule: functions only for shared
code or control flow); decode inlined into c_step; defensive clamps removed (trust the
sampler; load-time dim check is the guard); gold term = invariant form (prev stores
clamped net). TELEMETRY CUTS (user-approved): use/valid_slot_mean (+hot-path
bookkeeping), prayers_trouble (+nethack_in_trouble fn DELETED), reward_saturated,
regen_ticks, pack_full_frac, enhances_martial, depth, death_burst_turns (+last_ok_turn),
enh_armings, ups_hurt. KEPT burdened_frac. RENAMES (wandb keys change!): swaps ->
armor_swaps; REST verb -> SEARCH20, key "rests" -> "search20". Census CSV lost burst +
armings cols (scratchpad analyzers' indices stale). Comments = drone grammar: section
dividers + unit annotations + rare facts.
2026-07-23 NETHACK.H QUALITY PASS (drone-style bar: simple contained code, brief
comments; ALL fingerprint-gated, hash 71021f6ac6b5864a unchanged throughout): (1)
extractions — mask blob -> underfoot_glyph/mask_slots/mask_dirs/compute_mask, WEAR swap
-> wear_takeoff_conflict, census logger -> census_line; (2) comment diet ~10 paragraph
blocks -> one-liners (rationale/history dropped); (3) VERB TABLE refactor — VerbSpec
row per verb (cmd/head/gates/ocmask/wornreq/offsetof-stat), shared item path + 40-line
irregulars-only switch, mask_slots reads the same table; four hand-aligned verb copies
-> enum+table. nethack.h 1300->1050 lines. Stats offset-0 guard: valid_moves at 0, no
verb row uses stat=0 unguarded. NEXT: macros.h + nethack.cu same treatment.
2026-07-23 RELEASE BASELINE COMPLETE (val-cleantree-180m, HEAD build, 179M): s43-46 =
3516/3604/3906/3424 mean 3613; DEFAULT INVOCATION (seed 73 from config) = 3628.9 =
exact-repro anchor for README. Clean bank -163 vs corpse bank 3775 (same semantics by
fingerprint proof, pure init re-roll, 3/4 seeds lower — quote clean bank for the
shipping binary, cite spread caveat). Remaining cleanup: section headers, decoder
constant naming, comment sweep — all fingerprint-gated (free); then commit decomposition
+ fork push + docs per the phased plan.
2026-07-23 SIGBUS GOTCHA (self-inflicted twice-over): an orphaned (`& disown`) relaunch
of ab_clean.sh cp'd the arm .so over pufferlib/_C.so WHILE the default run had it
mmap'd — cp truncates the SAME inode -> mapped code pages vanish -> trainer dies SIGBUS.
RULES: (1) .so swaps must be atomic cp-to-tmp + mv (new inode, old readers keep pages);
(2) never & disown (harness-untracked, third occurrence); (3) one script per pipeline,
no cross-script GPU races. ab_final.sh (task b2tzq749i) = clean bank s44-46 + default-
invocation run, swap_so() atomic. Clean-tree baseline so far: s43=3516 (re-roll of
corpse s43 3820, in-noise as fingerprint proof predicts; user: shipping binary gets its
OWN 4-seed bank, corpse numbers not transferable for quoting).
2026-07-23 STRIP PROVEN SEMANTICS-PRESERVING (user push: "check determinism vs what we
had before"): scratchpad/fingerprint2.c = LAYOUT-AWARE semantic fingerprint (per-block
hashes via each version's own offset macros, shared 22-verb sampling); pre-strip headers
reconstructed in scratchpad/prestrip/ by reverse-applying the strip edits. RESULT: all 4
seeds bit-identical pre vs post (71021f6ac6b5864a) => strip changed layout only; residual
diff = shapes/init-RNG (D'-class noise). Bank's role reduced to release-baseline quotes.
PROTOCOL UPGRADE: semantic fingerprint covers layout-changing refactors too; banks now
ONLY for changes altering what the policy can see/do.
2026-07-23 DETERMINISM PROTOCOL (user mandate: check before/after EVERY change):
ocean/nethack/tools/env_fingerprint.c — fixed masked-random policy, 4 seeds x 3000
steps, FNV over obs+reward+terminal+mask every step. POST-STRIP BASELINE =
71021f6ac6b5864a. RULE: identical fingerprint + gradcheck PASS => provably behavior-
preserving => NO bank needed (refactors free); differing => semantic change => 4-seed
bank mandatory. Encoder pure-refactors: exact torch reference in gradcheck harness.
2026-07-23 CORPSE-EAT VERDICT +191 (n=4: -18/+544/+349/-111 vs autoclaim bank; mean
3775 = best-ever 180M; ADOPTED — also fixed mask-vs-macro contradiction). Converged
equilibrium ~= old profile (mid-run corpse-heavy exploration settled back; gain =
food-margin not prayer displacement). EATING-HABITS CENSUS (census4, per-episode):
top-quartile eps of EVERY policy eat ~1.0/1kT + pray ~1.1/1kT (universal rhythm — no
one wins by eating more); discriminator = RESERVES (end-empty 30% best vs 44% worst,
faint-terminations 18-20% vs 29%); for good policies fainting = the marathon-ender
(their top eps faint MORE than bottom — supply ceiling terminates the right tail).
CLEANUP PHASE (user priority: code quality/succinctness in env+cuda, NOT asset rescue/
docs): DEAD-CODE STRIP DONE — removed distfeat/clock/pray/armed-bit obs plumbing (extra
ints 25->20, obs 4204->4184), ENHANCE verb REMOVED from action space (22 verbs again;
auto-claim env-side does the claiming, do_enhance macro kept), dead cooldown slot 45
dropped, nethack_letter_is_corpse deleted, kernel REWRITTEN with named NH_F_* cumulative
offsets (NH_BL_FEAT=97=25+7+13+22+18+2+8+2; bl_w 64x97=6208 %8 OK), stale header/layout
comments fixed. Gradcheck PASS, no-wedge smoke OK. HEAD NOW BUILDS THE SHIPPING CONFIG
(no ritual edits). CONFIRMATION BANK RUNNING (task brw3y2uqh, ab_clean.sh, val-cleantree-
180m s43-46, _C_cleantree.so = plain build output) vs corpse bank 3820/4045/3751/3485.
2026-07-23 AUTO-CLAIM VERDICT: +210 (n=4: +244/+73/-41/+565 vs armcat bank; mean 3584 =
BEST-EVER 180M bank; claims uniform 1.22-1.31 every seed — bistability engineered out).
FIRST POSITIVE ARM of campaign; ADOPTED into canonical (_C_autoclaim.so = canonical arm
binary; autoclaim runs = new paired bank). SPELLBOOK/CAST STATE (user scouting): READ
studies books (class mask 9|10) but NO cast verb (R3-deferred) -> book reads = pure
risk; every Monk STARTS with a pre-learned spell (u_init: healing/protection/sleep 1/3
each) never castable — all three map onto death taxonomy (heal=Pw-clock recovery
independent of prayer lockout; protection=burst mitigation; sleep=pack disable). CAST
sketch: 'Z'+'a' (one spell early), dir head for rays, self '.', mask on Pw>=cost
(ene in obs); casting burns nutrition; Monk unarmored = low fail. Awaiting user go.
2026-07-23 ENHANCE OPPORTUNITY CENSUS (census2: armings counter = enh_ready 0->1 edges;
5 final ckpts x 10K eps): ARMING IS UNIVERSAL (83-87% of eps arm >=1 for EVERY policy);
claim rate is the whole difference: stars 98%/98.8% vs non-claimers 1.4%/2.0% (die with
unclaimed 84%!) -> PURE POLICY GAP, bistable learned press. Virtuous cycle visible
(claimers also GENERATE more armings 1.4-1.6 vs 0.85-0.91). USER DECISION: AUTO-CLAIM
(no strategic content — free, always good, no competing slot use; precedent autopickup/
pile-grab-all/atomic-wear). WIRED: c_step tail block (after drain+refresh, never mid-
prompt): on enh_ready -> do_enhance + drain + re-refresh; ENHANCE verb permanently
masked (dead head, D'-free); armed-bit obs feat now constant-0 (plumbing kept).
Verified: debug trace claims++ per armed step; 20K-step force probe no wedge (its
claims=0 print = per-episode-stats gotcha AGAIN — probes must print TOTALS not
env.stats). A/B RUNNING (task bsrds6i0g, ab_autoclaim.sh, val-autoclaim-180m s43-46
@default 179M) vs armcat bank 3594/3429/3443/3031. Expected if causal: several hundred;
telemetry check: enhances/ep should ~= armings/ep ~1 for ALL seeds. NOTE canonical
nethack.h now also carries the gated NETHACK_DEATH_LOG block + armings counter
permanently (inert in training).
2026-07-23 FULL-BUDGET RESULTS (canon_all, s43-47 paired): 358M = 3836/4601/4088/3757/
4116 mean 4079 | 500M = 4189/4173/5267/4484/4619 mean 4547. Paired 500-358 deltas
+354/-427/+1180/+727/+504 = MEAN +467 (+11.5%), 4/5 positive (t~1.8). BUDGET LEVER
ALIVE: 180M~3450 -> 358M 4079 -> 500M 4547, ~linear +3.3/Msteps, no bend through 500M;
naive 6000 extrapolation ~930M steps. CAMPAIGN RECORD 5267 (s45@500M); 500M mean beats
dead-stack champ 358M mean 4185. DEPTH FLAT (~4.0-4.3 both budgets) — gains = richer
shallow play, depth wall persists. ENHANCE-BASIN TRACKS SCORE WITHIN PAIRS 4/5:
block-best runs are the heaviest enhancers (s44@358M 1.42/4601; s45@500M 1.56/5267);
s44 LOST the basin at 500M (1.42->0.01) and was the only negative pair (-427) — same
seed, more budget, fewer claims = exposure-confound can't explain -> skill-rank obs
feature case STRENGTHENED (the one remaining feature bet). GPU free ~04:40.
FULL-BUDGET PLAN (user, FINAL final form — 3-part chain TORN DOWN at user request,
replaced by ONE flat script): scratchpad/canon_all.sh (task bobv1346n, lock
/tmp/canon_all.lock): seeds 43-47 @358M (canon-358m) then SAME seeds @500M (canon-500m,
first-ever 500M, anneal stretches) = paired budget-scaling. Resumable .done markers,
GPU gate + .so cp per run, one lock. ~6.5h from 21:43. Reading: per-seed 500-358 deltas
= does budget still pay; loose external ref = dead-stack champ 358M 4258/4421/3878.
Canonical arm binary: _C_armcat.so. re-anchors
full-budget level (old champ 358M 4258/4421/3878 = DEAD-STACK reference, loose only);
also tests whether enhance compounds at depth (more advances in longer games). Remaining
levers after: sweep exp-corner validation, adjacent-count (weak precedent), depth
itself.
2026-07-22 ENHANCE-2 VERDICT NULL (n=4: -359/-74/+132/+140 = mean -40 mixed): armed-bit
fix RECOVERED arm-1's -475 (same-seed +120/+399) — hidden-mask principle CONFIRMED.
Verb KEPT (functional, ~100% martial selection, score-neutral, no-class-pruning
principle; upside deferred to deeper play). CANONICAL CONFIG now = 23-verb + enhance +
armed-bit; enh2 runs (3223/3542/3758/3284 mean 3452) = the PAIRED BANK for next arms
(chaining rule: next arm binary must differ from _C_enhance2.so ONLY by its feature —
dead feats stay zeroed-but-packed, NEVER stripped, or the bank re-rolls). ARMCAT ARM
RUNNING (user question spawned it): per-slot armor-category one-hot (suit/shield/helm/
gloves/boots/cloak/shirt) from slot glyph via baked table — src/nethack_obj_armcat_dev.h
(sed device copy of ocean header), NH_SFEAT 17->24 (16x24=384 %8 OK), kernel reads slot
glyph from obs directly, ZERO obs-layout change; test parses the header + object-glyph
inv sampling for coverage (inv[::2] from [1906,2359)) + inv1s_w shape hardcode updated.
Gradcheck PASS. val-armcat-180m s43-46 vs enh2 bank. ORPHAN GOTCHA REPEATED: `cmd &`
at end of a && chain backgrounds the WHOLE chain -> harness notifies on wrapper; A/B
runs orphaned (works, but unmonitored) -> watcher until-loop armed on the inherited
output file (task bindtgjmz). Never put & inside a run_in_background command.
2026-07-22 ENHANCE ARM-1 KILLED AT n=2: -480/-473 paired BUT mechanism VERIFIED
(enhances 0.22/0.60 per ep, enhances_martial ~= 98% -> message/mask/macro/selection all
work). DESIGN FLAW DIAGNOSED: the ENHANCE mask keyed on enh_ready which was NOT in the
obs — the ONLY mask in the env keyed to hidden state (every other: hunger/glyphs/inv,
all observable). Non-stationary invisible legality = flickering verb-head legal set +
entropy noise. PRINCIPLE: any mask's predicate MUST be visible in obs. FIX: enh-armed
bit exported (extra[24], EXTRA_INTS 25, obs 4204, NH_BL_FEAT 105 = 64x105=6720 %8 OK),
gradcheck PASS. ARM-2 RUNNING (task biwl30tiz, ab_enhance2.sh, val-enhance2-180m
s43-46, _C_enhance2.so = 23-verb + armed-bit live + dist/clock/pray zeroed) vs ctrl
bank. If STILL ~-475 -> hidden-mask wasn't the harm, kill the verb entirely.
2026-07-22 D' VERDICT: VERB TAX GONE. n=4 paired vs ctrl bank: +167/-29/-323/+187 =
mean +0.5 (D' 3492.5 vs ctrl 3492.0) — champion action space and full 22-verb suite
statistically IDENTICAL on current stack. The -242 tax (C/E/D/D' era, old stack)
DISSOLVED with stack drift; do NOT adopt masking; all-verbs is the config, polish it.
(Also proves early-seed reads lie: s43 +167 alone looked tax-alive.) ENHANCE A/B
RUNNING (task b6eqyvdes, ab_enhance.sh, val-enhance-180m s43-46): _C_enhance.so =
23-verb all-verbs + ENHANCE, dist/clock/pray feats zeroed, vs ctrl bank. GATE at first
seed: enhances/ep > 0 and enhances_martial tracking it (if 0.000 at xp~6 -> macro broken,
stop the arm).
2026-07-22 ENHANCE VERB BUILT (user catch: Monk never claims skill-ups — #enhance was
deferred to R3 and never wired; agent banks martial-arts practice forever at Basic,
highest cap in game = Grand Master). UNLIKE the taxed verbs: dense within-episode payoff
(kill speed -> xp/score), argument-less (no slot head), targets census burst mechanism.
Impl: verb 23 NETHACK_ACT_ENHANCE, NH_ACTIONS 23 (decoder lin rows 32 = pad exactly,
NH_BL_FEAT 104, all symbolic — binding/dims auto), macro nethack_do_enhance in macros.h,
mask gated on env->enh_ready flag set by topline "more confident in your" (weapon.c
give_may_advance_msg) cleared on press; telemetry log/stats enhances. EXTCMD GOTCHA:
'#' prompt is NOT getlin-flagged (misc[GETLIN]=0) — gate on topline "# " instead;
autocomplete fills after 'e','n'; extra chars accepted; '\r' executes; skill menu =
XWAIT, 'a' = first advanceable (letters only on advanceable), ESC-drain safe when none.
Gradcheck PASS; extcmd_probe traced every keystroke; force-probe 800 presses no-wedge;
POSITIVE advance unprovable pre-training (random walk never levels: no slots at xlvl 1)
-> VALIDATE via enhances/ep telemetry at first run (if xp~6 and enhances=0.000 ->
broken). Canonical tree saves updated (save_full_* incl macros.h). ENHANCE A/B base
cut at launch per D' verdict (interim +167/-29).
2026-07-22 BISECT VERDICT = NEITHER: oldeng_s43 (E_old ada28c71a + P_new ctrl.so) =
3628.2 vs elbflag 3452.0 (E_old+P_old) vs ctrl 3581.8 (E_new+P_new). => BOTH deltas
break bit-identity independently — engine commits AND the vecenv vecprof timing
instrumentation (the only P-side source diff) each re-roll 180M-step trajectories.
Bit-exact repro across ANY rebuild difference is dead; only same-binary runs replicate.
+259 shift NOT attributable to engine (old engine scored HIGHER with new P on this
seed); filed as re-roll scatter + drifted level, ~1/16 luck residual. RULES: fresh
paired controls after any binary difference incl. instrumentation; gauntlet = correctness
gate NOT training-neutrality gate; no further attribution GPU. Engine auto-restored to
main + rebuilt (trap verified).
2026-07-22 ENGINE BISECT QUEUED (task btpljja1t, ab_bisect.sh, chained on ab_pray lock):
rerun ctrl_s43 with engine at ada28c71a (elbflag-era = pre-mfndpos/typ-plane; delta
under test = 991a9a251 + f99a097ce + 401e98598 + c385dfe77). Bit-determinism verdict:
==3451.983 exact -> engine delta broke bit-identity (gauntlet coverage hole; patch with
trained-policy recordings); ==3581.806 -> engine bit-neutral, +259 cause elsewhere
(vecprof? then investigate); neither -> both deltas behavior-relevant. Script restores
engine HEAD + rebuild via EXIT trap either way. User prior: "just small determinism
changes" (zero-mean chaos + 1/16 luck) — bisect distinguishes.
2026-07-22 DEATH CENSUS RESULTS (20K eps, ctrl_s43+s44 ckpts; csvs+analyzer in
scratchpad): mix combat 86.1% (score 3472) | other 7.8% (4342!) | trunc 3.9% (4108!) |
starved 2.2% (2902). NARRATIVE REVISIONS: (1) under-leveled diving WRONG — only 7.9% of
combat deaths have killer mlev>=victim xp; real mechanism = BURST COLLAPSE: median 9
turns from >=75%hp to dead (52% <=10t), 34% with adj>=2, killers = low-level pack/multi-
attackers (rothe 5.7%, hill orc 5.7%, soldier ant 3.7% @depth5.2, dwarf, gas spore 3%
instakill of early chars; mnum0 unattributed-DIED 17%); 27.3% die fighting while Weak+
(hunger-cycle coupling). (2) trunc episodes are TOP-decile outcomes (4108) -> miner's
truncated -.45 was style-marker not per-episode harm -> EPISODE-CLOCK DEMOTED/HELD.
(3) 'other' decomposed: POISONED 1084 (5.4%, score 4143, ant/bee poison RNG — fix =
poison-resistance strategy, parked) + WRATH how=100 457 (2.3%, score 4642 = BEST bucket:
top farmers press PRAY while clock armed -> smited) + STONING 21 @8208. PRAY-TIMER
TRIPLE-SUPPORTED: 56% combat deaths <=400t since prayer (median 291t, locked-out heal),
72% starvation deaths had prayer READY (median 587t) and unpressed, wrath = pressing
when NOT ready. PRAY ARM RUNNING (task bcgso9xlu, ab_pray.sh, val-praytimer-180m
s43-46, _C_praytimer.so = full tree with dist+clock feats ZEROED in kernel, pray feat
live) vs ctrl bank 3582/3616/3626/3144 mean 3492. ALSO: ctrl bank vs elbflag arm same
seeds = +259 ALL-4-POSITIVE (engine round shifted trajectories favorably despite
goldens; gauntlet-pass != training-neutral in EITHER direction). CWD GOTCHA: bash cwd
persists across calls — a stray `cd vendor/fast-nle` broke ./build.sh later; use
absolute cd in compound commands.
2026-07-22 PRIORITY RESET (user: consistency focus, census BEFORE more feature runs):
distfeat KILLED at n=2 (-583/-281; reading: descent-assist polishes the WRONG behavior —
binding failure is under-leveled diving, so navigation aids amplify it; recovery/budget
features fit the failure modes). distfeat_s45/s46 skipped via .done markers; ctrl bank
n=4 (s43-46) finishing = paired baseline for all next arms. DEATH CENSUS RUNNING (task
bwp2p68lp, chained on ab_dist lock): _C_census.so = ctrl-layout build + gated
NETHACK_DEATH_LOG per-episode CSV in nethack_add_log (13 cols incl killer_mnum/mlev,
since_pray via last_pray_time telemetry) + probe_ckpt 10K eps on ctrl_s43+s44 final
ckpts (dirs resolved via wandb run ids) + census_analyze.py (killer species top-15 via
gen_entity_names table, prayer-cooldown lockout test, burst anatomy, starvation). Build
dance: full-feature source SAVED as scratchpad/save_full_nethack.{h,cu} + save_full_test
.py, ctrl-state rebuilt by exact-string reversal, RESTORED BY FILE COPY (never re-edit).
Census verdict gates: pray-timer arm (ctrl base) then clock arm (ctrl base), 4 runs each
vs ctrl bank; arm variants to be built by feature-zeroing from full tree (accepted
shape-noise class) or hunk reversal.
2026-07-22 PRAY-TIMER FEATURE BUILT (user fairness line: ublesscnt NEVER exportable —
engine info; fair variant = turns-since-OWN-last-PRAY from blstats TIME + press history):
last_pray_time in struct (reset 0 = "clock armed at start", matches real init), set at
PRAY press pre-step; extra[23]=TIME-last (EXTRA_INTS 24, obs 4200); NH_BL_FEAT 103, feat
min(elapsed/1024,1). Gradcheck PASS, pray_probe.c 600 steps 0 mismatch. MOTIVATION (the
food-prayer analysis): prayer clock is STOCK (can_pray: major trouble needs ublesscnt
<=200, success re-arms rnz(350)); policy prays-for-food at exactly clock capacity
(10.2/ep over ~3000 turns), rational because farming demand >> shallow food economy and
Monk meat = adjalign(-1) (alignment<0 kills prayer, eat.c violated_vegetarian); REAL cost
= food-prayers re-arm cooldown so combat-emergency prayer answers "too soon"
(prayers_low_hp 0.33 vs 87% combat deaths) and the shared cooldown is INVISIBLE ->
pray-timer feature lets policy arbitrate. DISTFEAT n=2: s43 -583, s44 -281 (both paired
negative, ctrl running hot 3582/3616) -> ab_clock UNQUEUED (was on distfeat base; task
stopped, lock cleared); decision at n=4 verdict: if distfeat negative, rebuild clock+pray
arms on CTRL base (feature-zeroing variants or hunk reversal) and chain those instead.
MID-RUN LOG GOTCHA (recurring): pull_metrics on a log without .done marker = mid-run
curve value, NEVER a final (ctrl_s45 2202 example).
2026-07-22 EPISODE-CLOCK FEATURE BUILT+QUEUED (miner-motivated: truncated -.34 bistable,
episode_length -.42): extra[22]=stats.length (EXTRA_INTS 23, obs 4196), NH_BL_FEAT 102
= clock feat steps/10000 (bl_w 64x102=6528 %8 OK). Gradcheck PASS; clock_probe.c 1500
steps 0 mismatches incl eager-reset boundaries. CHAINED A/B ab_clock.sh (task bvkp5zaf1):
waits on /tmp/ab_dist.lock release, then n=4 s43-46 group val-distclock-180m with
scratchpad/_C_distclock.so; PAIRED CONTROL = the distfeat arm (bit-identical stack minus
clock — chaining trick: each feature A/Bs vs the previous arm while stack frozen, only
4 new runs each). Tree now = distfeat+clock state. ab_dist.sh cp's arm .so per run so
mid-A/B rebuilds of _C.so are harmless (only this script's cp determines what runs).
2026-07-22 DISTFEAT A/B RUNNING (score pivot after SPS-campaign pause; top remaining
hp_frac-class candidate): +3 bl_feats = downstair-seen bit, Chebyshev dist to nearest
REMEMBERED downstair (env scans obs glyphs 2383/2385 vs blstats x,y; -1 sentinel -> feat
1.0; /32 clamp), explored non-stone cell count (/1024). Env: 2 new extra ints
(NETHACK_EXTRA_INTS 20->22, obs 4184->4192), NH_BL_FEAT 98->101 (bl_w 64x101=6464 %8 OK).
Gradcheck PASS; dist_probe.c (scratchpad) 4000-step: packed ints == ground-truth rescan,
dist==0 <-> DOWN-legal every step (k=0 mismatch = deferred-reset artifact, pre-existing).
A/B ab_dist.sh (task bsj9m5u1x): n=4 s43-46, ctrl vs distfeat, group val-distfeat-180m
project encoders, arms swap prebuilt _C.so (scratchpad/_C_ctrl.so/_C_distfeat.so — avoids
git surgery on tree with other uncommitted work); tree left in FEATURE state. FRESH-CTRL
NECESSITY EMPIRICALLY CONFIRMED: ctrl_s43=3581.806 vs elbflag_s43=3451.983 — NOT the
bit-exact replica golden-gated engine changes would imply; some post-elbflag change
(mfndpos/typ-plane/mmap-ctx beyond gauntlet coverage, or vecprof) diverges one trajectory
somewhere and chaos does the rest. => goldens-pass does NOT guarantee cross-stack score
comparability; ALWAYS rerun controls after ANY engine/vec change (don't root-cause the
divergence, it's moot with paired controls). elbflag-arm mean 3233 (3452/3274/3301/2905)
usable only as loose history, never as paired control.
BASH GOTCHA: `local a=$1 log=x_${a}` expands ${a} BEFORE assignment (set -u abort) —
split local declarations.
2026-07-21 ELBERETH-ACTIVE FLAG SHIPPED (user: incentivize don't mask; de-luck the
strategy via LEGIBILITY): engine internal[6] (ex-disp-seed slot) = underfoot engraving
state 0/1/2 (2 = sengr_at("Elbereth",strict) = EXACTLY what onscary respects incl
engr_time drying); env extra[0] (ex-ublesscnt zeroed slot, no obs-layout break) carries
it; +2 bl_feats (any-engraving, active-Elbereth) NH_BL_FEAT 96->98, slot-45 cooldown feat
now dead-zero. PROBE GOLD: 60 engraves -> 47 active / 13 TYPO'D DUDS (22% of fingertip
Elbereths are fuzzymatch-failing scribbles monsters IGNORE — invisible to the agent until
now; the macro's typo-rewrite doesn't always fire). Gates: goldens 34/34 (internal not
hashed), no-globals, gradcheck PASS (kink_tol 2e-4 -> 2e-5 after a loc_w FD kink-crossing
false-fail — torch ref 9.8e-08 authoritative; 2nd data-shift FD artifact after inv1_b).
A/B RUNNING val-elbflag-180m n=4 s43-46 vs wedgefix control 3191 (env now = wedgefix+flag).
GOTCHA: re.sub replacement strings ESCAPE-PROCESS \n — use string slicing for C codegen.
INCOMPLETE-PATCH GOTCHA (bit us 2026-07-21 restore): assemble_final.sh saved final_allverbs.patch via `git diff HEAD -- <4 files>` OMITTING src/nethack.cu + tests -> re-applying gave 22-verb env but CHAMPION decoder (output_dim 690 != expected 297) -> runtime abort. Fix: also `git apply --include=src/nethack.cu --include=tests/... expansion_corrected.patch`. NEW COMPLETE patch = scratchpad/allverbs_plus_rewards.patch (725 lines, ALL 6 files incl src/nethack.cu + tests + armcat header). Always diff ALL touched files when saving a config patch.
2026-07-20 ATOMIC-WEAR + ARMOR THREAD DONE: Delta-AC reward (ac_coef, potential phi=-AC, symmetric) = validated reward TERM — drives wears 17x (0.027->0.31, CONSTRUCTIVE proof of reward-support law) but net ~neutral: AC only -0.2 (baseline Monk unarmored AC ~4.36 FLAT already good + depth-4 armor scarcity; NOT the swap barrier). Atomic WEAR built+verified (baked glyph->armcat src/nethack_obj_armcat.h via gen_obj_armcat.c [flags -Iinclude -Ibuild/include -DDLB, use objects_baseline[] NOT objects[]=uninit-segv]; WEAR auto-T-occupant then W in 1 step; swaps 0.03-1.3/seed FIRE, no hang) — score 3083 = non-atomic, still below E 3260. Armor = real-but-weak lever for Monk. Full Delta-AC+atomic+AC-log = scratchpad/deltaac_full.patch + tree edits. Armor action-support now COMPLETE (user goal: reasonable support for eventual use). REWARD-SUPPORT MAP: direct=MOVE/RUN/DOWN/KICK/EAT/QUAFF/PRAY/THROW/WEAR/PUTON; weak-gamble=ZAP/READ/QUAFF-unidentified(NOT masked-id-mask was a regression,removed; jsuarez yolo-zap legit)/REST/SEARCH/ELBERETH/PICKUP; none=UP/WIELD(monk-neg)/APPLY/DROP. Next reward gap=per-OUTCOME-STAT terms (resistances/status-cure/identification) not per-verb — each lights up multiple verbs like Delta-AC did.
2026-07-20 ARC CLOSED — C/E/D/D' decomposition (n=4, s43-46, 180M, paired): champion 3502 | D'(arch-only,0-entropy) 3588 (+86) | D(dead-heads,+entropy) 3544 (+42) | E(verbs usable) 3260 (-242). SPLIT: D'-C=+86 HEADS FREE; D-D'=-44 entropy-footprint-of-unused-heads (tiny, within noise, directionally confirms entropy-summing); E-D=-285 USAGE (only robust effect ~2sigma). Sum +86-44-285=-243≈E-C. => adding the 12-head action space is FREE; entire -242 is ITEM USAGE and it's DIFFUSE (new verbs barely fire: wields 0.003/reads 0.002; NOT wasted turns, NOT Elbereth-collapse=seed-noise; telemetry too seed-noisy to pin 1 mechanism). Champion behavioral gaps (base180): wears 0.025/ep (~never armors, damage 296/ep) = REWARD gap (AC/resists observable per jsuarez, no AC reward term); engraves(Elbereth) 0.8-25/ep wildly seed-dependent, UNMASKED. LEVER for utility = reward-supported item use, top pick Delta-AC(non-body slots: cloak/boots/gloves/helm/rings — pure Monk win; body-armor nuance self-corrects since unarmored intrinsic is IN the AC stat). jsuarez confirms: no-identify=>no item access (yolo-zap legit, id-mask on QUAFF/ZAP was correctly a mistake); NMMO shared-embed-all-stats was a CONVENIENCE HACK ("pretty crap network") not a template => our null embedding result vindicated, we already do the smarter per-stat thing. Reward audit: descent 1.888 saturates clamp(+1/level), survival badly underweighted (hp 0.019, NO AC term), death -0.63 ~ descent +1 => tolerates suicidal diving. Cheap masking-hygiene candidate: Elbereth-to-adjacent-monster (kills no-threat wasted-turn spam) but likely neutral (engraving doesn't track score). [prior detail below]
2026-07-20 DEAD-HEADS ISOLATION + ENTROPY CONFOUND (user pushed "surely adding actions changes something?"): audited what changes when verbs are added even if MASKED. muon LR scale (muon.py:130 `sqrt(max(1,rows/cols))`) is UNCHANGED 5->12 heads — every decoder matrix stays rows<cols=512 (dec_lin_w (32,512) padded-invariant; dec_q_w (HEADS*16,512)=80->192 both <512; dec_k_w (16,16); dec_tau 1D). So NOT an LR mismatch. The REAL channel = ENTROPY: `_entropy(logits).sum(0)` over ALL multi-discrete heads (torch_pufferl.py:79), masked-to-legal (mem line 85). 5->12 slot heads adds up to 7 entropy terms (DROP head = all-oclass -> many legal slots -> real entropy); inflates entropy bonus (effectively higher ent_coef) AND gives dead heads entropy-gradient (NOT 0-rows -> they couple into active heads via muon whole-matrix orthogonalization). Team already knew (line 81 "ent_coef range predates 7-head entropy summing"); #69 halved ent_coef 0.0052->0.0026 -> no recovery, entropy stayed ~10 (real but not naively tunable). CONSEQUENCE for isolation: dead-heads arm D (verbs masked, normal slot masks) has D-C = arch + entropy-scaling (CONFOUNDED). Clean fix = D' = also force the 7 new slot heads (5-11) to single legal slot (memset slot region, s[0]=1) -> zero entropy/entropy-grad -> truly inert. DECOMPOSITION (all on corrected-expansion base + 180M n=4 seeds 43-46): E-D=usage, D-D'=entropy-scaling, D'-C=PURE architecture (init-RNG noise only). Scripts: scratchpad/deadheads_run.sh (D, group expansion-deadheads) chained -> deadheads_noent_run.sh (D', group expansion-arch-only). E=corrected-expansion -208; C=champion ~3509@180M. Clean-wide s43=2778 (~-731, QUAFF/ZAP restore did NOT recover wide -726 -> wide-pickup distraction, not the id-mask nerf, is the dominant wide cost).
2026-07-23 RELEASE ANCHOR: default-config reproduction number for the shipped tree
(commit 82fddbc8 "simpler readme" — post-cleanup, shared files reverted to upstream,
no cublasLt, static OMP schedule) = **3397.4** (c0qhcife, encoders/release-anchor,
seed 73, 179.4M). Prior same-seed clean_default was 3628.9 (8lkvw66j) but on a
different binary (guided sched + Lt) — delta -231 is within single-seed noise +
trajectory re-roll; c0qhcife is THE number to reproduce against. Late-phase SPS
164K (static sched). wandb GOTCHA rediscovered: upstream pufferl logs NOTHING
without --wandb; project flag --wandb-project encoders (default is puffer4).
2026-07-23 ANCHOR PAIR COMPLETE (release tree 82fddbc8): s73=3397.4 (c0qhcife),
s44=3842.6 (hc6anz9u); vs prior binary -231/+238 SYMMETRIC => re-roll confirmed,
numerics/regression worry closed (GemmEx-for-Lt + static-sched neutral). s43 =
deterministic segv @156.9M on this binary (rfg3l67c, kept as crash record) — gdb
repro available, see [[nethack-crash-hardening]].
2026-07-24 500M BEHAVIORAL DECOMPOSITION (rel500 bank, what the 5570 record did):
TOP-2 (s47 5570, s43 4995) share a 3-part learned package the rest lack:
(1) ELBERETH 17-23 engraves/ep (s44=0.00, s46=7.2) — the 180M elbflag verdict
"dust Elbereth not worth it, engraves->0" REVERSES at 500M/depth-4.5: survival
tool becomes worth it when diving deeper; (2) CORPSE ECONOMY: floor_eats ~1.9
(2-3x others) + pickups 3.7-4.4 + DROPS 19-23/ep (drops = 0.00 for ALL three
laggards — drop-based pack management co-discovered only by the top 2);
(3) EARLY DEPTH COMMITMENT: s47 at depth 4.5 by 300M (others 3.2-3.9), score
lead already +1200 at 200M => early package discovery = more anneal time to
consolidate. s43 learned it late (480M window surge 5647). PATHOLOGY: s46
(worst, 4191) burned 841.84 wields/ep = ~38% of steps on wield/unwield
toggling — a null-action attractor from WIELD reversibility (monk wield
useless); candidates: entropy floor / reward-support fix, NOT masking (verb
legality fine). Laggard profiles: s44 no-Elbereth+fast-episodes, s45
Elbereth-but-no-corpse-economy+slow-episodes. Depth still ~4.5 ceiling; sokoban
0.00 everywhere.
2026-07-24 ETC336 CONFIG VALIDATED (n=4, 248M, fixed engine, group val-etc336):
5259.6/3887.6(curve 4256, cut mid-climb)/4383.3/5445.9 = mean 4744, TWO seeds
>5200 — beats the old-config 500M pool mean (4632, n=11) at ~1/3 wall clock
(same ~20min/run as 180M: replay_ratio 1.39->1.04 nets +38% steps free).
Config = eternal-cloud-336 (sjpsh3dj, nethack-verbage sweep) promoted into
nethack.ini (uncommitted): xp_coef 2x, scout 4x, ac 5x, exp/3, death -0.82,
ent 0.0084, 248M budget. DEPTH CEILING BROKEN: 4.5 -> 5.1-6.3; sokoban first
nonzero (0.01-0.06). MECHANISM: reward pays the previously-luck-gated deep
package from the START (depth 5.3 + 500 tiles by 30M vs old 1.7/93) => the
de-lucking thesis solved by REPRICING, not entropy tricks. NEW FINDINGS:
(1) max_xp_level r=0.96 with score (old pool n=11) — THE tracker; game_time
0.58; behavioral markers wash out (throws 0.01, engraves -0.18, drops via
pile-engagement=pickups-coupled, burden NULL — mechanism hunts closed).
(2) Winner profile within-config: xp/game_time order = score order (n=4:
winners s43/s46 = throws>13 + tiles<420 + heavy engraves; laggards s44/s45 =
tiles>560 over-extension, s44 lost throwing entirely = toolkit luck remains).
(3) new_tiles SIGN-FLIPS between configs (+0.80 old, negative new) — scout
possibly now overpaid; over-extension canary. fix180_s47=3689.772 = 5th
bit-identity witness. NEXT (discussed, not launched): budget/anneal stretch
(~600M = old-500M wall clock; s44 was cut mid-climb +800/50M), sweep continues
from etc336 center breeding for xp+game_time, watch tiles as canary.
2026-07-24 THREAT FEATURE A/B: FAILED (decisive n=2, s45/s46 cancelled). Built
per-entity threat: (A) static species-danger prior 0.1*(mlevel+1)*w_threat as
4th E_eff summand (fused, zero runtime), (B) xp-relative per-cell delta via
g1_xy-style side-channels in crop+patch (w_dloc 32, glb1_pthr 16x25, thr
planes). Table ocean/nethack/mon_mlevel.h (regen from scratchpad
gen_mon_mlevel.c). Gradcheck PASS (torch-mirrored). RESULT on etc336 config:
thr336_s43=4997 (control 5260, winner either way); thr336_s44 reproduced the
EXACT laggard phenotype (depth 6.5, throws 0.000 extinct at ~30M, engraves 2,
score-track ~control). Checkpoint forensics: ||w_threat||=0.12 ||w_dloc||=0.23
||glb1_pthr||=1.4 vs E-rows ~5.6 => channels ENGAGED but priced ~5-10%,
behavior unchanged. VERDICT: the runner basin is NOT an information deficit —
it's incentive structure (descent/scout pay now, death credit diffuse at
gamma=.997). Observability can't fix credit assignment; matches elbflag
null; ">"-mask precedent differed (removed a fake CHOICE, not an info gap).
CAMPAIGN LAW reconfirmed: representation null, reward shapes behavior.
30M TOOL-EXTINCTION FORK is the remaining de-luck target — lever is sweep-side
(early-entropy schedule / reward ratios), NOT env-side. Feature disposition:
revert tree to release state after s44 finishes, save diff as scratchpad/
threat_feature.patch (well-gated implementation, re-attachable).
THROW SKILL VERIFIED REAL (demo message probe, s46 ckpt): ~60% connect, kills
floating eye + gas spore = textbook ranged targets, not noise. s44's
extinction = losing the only safe counter to those monsters.
2026-07-24 MASKING SURGERY SERIES on s44 (etc336 config, the laggard seed) —
all three variants failed to lift it; asymmetry of the search pair now
empirical: (1) mask SEARCH only: spectacular 20M redirect (search20 74/ep vs
control 3.8, score +56% early, THROWING RETAINED through consolidation) but
CONVERGED BACK to control trajectory by 143M (killed; trap real but shallow).
Fingerprint 588ccf2cacd64f32. (2) +WIELD+WEAR masks: no visible change (killed
early; fp bdfaceb376460902). (3) mask SEARCH20 only (force granular): final
2967 = CONTROL -921, max_depth 7.07 (deepest ever), throws 33.6, searches 74
— hyper-aggressive equilibrium that can't convert depth; SEARCH20's turn
compression is LOAD-BEARING (converts depth->xp/score via banked game-time);
single SEARCH is removable junk but not the disease. Fp c264f92d3d1342a8.
CONCLUSION: s44's ceiling survives reward reshape (etc336), observability
(threat), and action-space surgery (3 masks) — slow-value-learner seeds are a
TRAINING-DYNAMICS problem; remaining lever = early-entropy schedule (sweep
side). Masks all UNCOMMITTED; tree to be restored to release fingerprint
71021f6ac6b5864a.
2026-07-24 CAST VERB A/B (Z key, action 22->23, bl_feat 97->98, dec rows fill
the 32 pad; fp d74fbd1e184f86bf; gradcheck PASS): ADOPTION NULL — casts
0.001-0.004/ep at convergence in all finishers (despite hp-reward support;
READ->CAST chain + energy scarcity too rare to survive consolidation). Scores
= re-roll scatter (s44 5094!! vs control 3888 with casting UNUSED = strongest
basin-is-trajectory-luck evidence yet; s45 3971/s46 4347). DISPOSITION: revert
to patch after the crash below is fixed. cast336_s43 SEGFAULTED @48M (2.4 min
wall = cheapest repro ever): backtrace mon_break_armor<-newcham<-
decide_to_shapeshift<-mcalcdistress = SHAPESHIFTER-BURSTS-ARMOR stock bug,
UNRELATED to cast (no spell frames; trajectory-determined UB like the teleport
UAF; debug build dodges it — build-layout-dependent). Likely explains some
historical unattributed crashes. ASan repro in flight. SEQUENCING: fix engine
bug BEFORE reverting CAST (the repro lives on the cast arch).
2026-07-24/25 OVERNIGHT 1B CAMPAIGN (group val-1B, release engine w/ both UAF
fixes; killed after 6/12 runs, user satisfied). BUDGET SCALES TO 1B, NO PLATEAU:
etc336 @1B: s43=5685 (NEW RECORD, oovxaq8w), s44=5627, s45=5381, s46 CRASHED
@925M (was tracking 5837@851M/5759@891M -- headed for ~5800). etc336 mean 248M
4744 -> 1B ~5560 (finished) = +~800 over 750M (~+1.1/Mstep, slower than early
+3.3 but still climbing); depth 4.5 ceiling -> 6.2. firefly @1B: s43=4835,
s44=5006 (depth ~5.0, lifted from 4400@150M, still < etc). dash @1B not reached.
=> etc336 @ ~1B is the strongest known config; 6000 plausibly reachable w/ more
budget but per-Mstep gain shrinking. CRASH: ONE real segv (etc1B_s46 @925M,
"core dumped"; s43's "crash" was orphan-kill artifact NOT real). No core saved
(apport owns core_pattern, read-only, no root). DETERMINISTIC -> reproducible
via seed46/1B under gdb ~1.5h. Likely 3rd stock spoteffects-family UAF (2 fixed
today: teleport 76f699e1c, shapeshifter 21e7e0b53) or new class. Crash rate
~1/6 completed runs at 1B (more chances than 250M). Repro+fix DEFERRED (user
happy with campaign; hunt later w/ proven playbook).
2026-07-25 CONSUMED-HEAD GATING = REAL DE-LUCK LEVER (n=4, etc336, 250M, paired,
user-authorized shared-backend edit). Chat-agent found: PPO loss/sample sum
logprob+entropy+grad over ALL 14 heads incl. ~11 UNCONSUMED per step (verb uses
only verb+1 slot+maybe dir). Offline decomp (converged 1B ckpt): 95.5%
unconsumed-head entropy at 10+ items — explains the campaign-long "LOSS_ENT~10
unmoved by ent_coef". FIX: env exposes per-(verb,head) consume map (weak symbol
env_head_consume_map in binding.c); pufferlib.cu gates logprob/entropy/grad in
BOTH sample_logits + ppo_loss_compute to consumed heads only. Gated on
PUFFER_HEAD_GATING (one binary, both arms). GOTCHA FOUND+FIXED (user caught via
identical 5329.221 scores): getenv truthy for empty string -> control arm
(PUFFER_HEAD_GATING=) was ALSO gated -> both arms identical. Fixed: require
hg[0]!='0' + driver unsets for control. RESULT (gated/control): s44 5558/4276
(+1282), s45 4967/4677 (+290), s46 5232/3865 (+1367), s43 5329/4507 (+822).
mean 5272/4331 = +940 EVERY seed positive. Gated 3/4 >=5232 + 1 @4967 (~all >5k,
TIGHT spread 592); control 0/4 >5k (spread 812). Biggest deltas rescued
low-basin controls. Wins DESPITE ent_coef exploration handicap (gated entropy
~2 vs 7 at 5M; same ent_coef => less bonus => effect understated). REVISES my
prior (I predicted gating wouldn't move basin — WRONG). MECHANISM: clean pointer/
toolkit-head grad lets under-converged seeds reach good basin at 250M not 1B.
Patch scratchpad/head_gating.patch (180L). CAVEATS: 1 config/budget; SHARED
BACKEND (off-limits) => evidence packet for train owner, not ship-here. NEXT:
seed-73 n=5 running; then re-center sweep on gated backend (raise ent_coef range
~5-10x since entropy now ~10x smaller, open anneal_ent_coef).
