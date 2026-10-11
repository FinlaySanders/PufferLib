---
name: nethack-identity-obs
description: discovered-type obs channel (inv_true_glyphs) built+validated 2026-08-04; ABI-skew landmine (lib rebuild under live chain); A/B group idobs
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-04T14:08:22.461Z
---

Identity-obs channel shipped locally 2026-08-04 (task #109, uncommitted pile with [[nethack-tip-verb]] until sweep concludes). Motivation: `shuffled_glyph` maps ALL object glyphs to appearance unconditionally — identification was invisible (typeknown bit said "known", never WHAT). Post-ID names live in inv_strs (unencoded). Use-ID also scores +10 (`more_experienced(0,10)` at engrave/quaff/read/zap sites) — earlier "items score 0" claim conflated this with carried-value-at-death.

**Design** (4th application of the gate-on-hero-knowledge pattern: bknown/cknown/lknown/oc_name_known):
- fast-nle: `short *inv_true_glyphs` in nle_obs (before `partial`), winrl.cc fill = `(dknown && oc_name_known) ? GLYPH_OBJ_OFF+otyp : NO_GLYPH` — the xname display rule, mirrors inv_state st[6]. Blind pickups stay hidden via dknown.
- obs: NETHACK_OFF_INVTRUE block (55×int16), obs 4184→4294.
- encoder: second table T_true = E @ invt_w^T reusing main glyph embed; slot pre-act += T_true[gt] with pad slots HARD-ZERO (skip in gather + skip_pad in scatter backward); invt_w (16×32) ZERO-INIT (ekind idiom, exact no-op at start). Demo mirrored (loading order after inv1s_w; ENC_FIXED formula +512).
- Key property probe-verified (scratchpad/probe2 PROBE_ID=1): appearance re-rolls per episode, true glyph stable across episodes = item knowledge finally stationary/transferable; unknown pickup shows app/5976.
- Validation: goldens 34/34, gradcheck PASS (invt_w 6.5e-07), id-probe.

**ABI-SKEW LANDMINE (cost: tipgold1_s208 invalidated + 4 dead evals)**: rebuilding libnethack.so with a CHANGED nle_obs struct while a train/eval chain is live = running trainers keep mapped pages (survive) but any process LAUNCHED after (evals, next chained train) mixes old binary + new .so → garbage/empty results, exit-0 plausible-looking runs. RULES: (1) binary+lib move as a matched pair, never rebuild either under a queued chain; (2) before an obs/ABI change, snapshot the pair (cp puffer → puffer_<era>; stash new edits → rebuild → cp libnethack.so aside → pop) so old-arch checkpoints stay evaluable via `LD_PRELOAD=<era>.so puffer_<era>`; (3) TIP-era pair lives in scratchpad tiplib/ + puffer_tip.

A/B: group idobs n=4 (207/208/210/211) vs tip arms + sc025 bank; census read = quaffs/reads/putons/zaps/heal_hp (informed use of id-masked verbs), score guardrail.

**ROUND 2 (idobs2, built same day, gated pipeline $SP/idobs2.sh):**
- Map true glyphs: `maybe_true_glyph` in winrl.cc (store_glyph + hero-tile site) keeps the RAW glyph when `oc_name_known` — farlook-public (discovered floor items readable). Opt-in `NLE_TRUE_GLYPHS` env var (per-instance read at NetHackRL ctor; goldens run flag-off, unchanged); env setenv's it in do_reset. Replacement-not-sum is OK on the map (one token/tile, no key bindings, natural churn, zero H2D cost vs +3.3KB for a second plane).
- Discoveries telemetry: `nle_discoveries` accessor (counts oc_name_known over 453 types), env->disc0 at reset, episode delta logged as "discoveries" — the knowledge-economy census key.
- ENGRAVE_ID = verb 25 (direct {-1}, mask 733): masks on unidentified-wand-in-pack (class 11, typeknown 0), macro auto-selects first such wand, E + letter + elbereth-style prompt loop writing "x". Fire/lightning/digging makeknown (+10 score each).
- Verb-count landmine family again: NUM_ACTIONS 25, NH_ACTIONS 25, ini 733; DEC_PAD/BL_FEAT now derive automatically (73→74 rows still pads 80; bl feat 102, 64×102 %8 ok).

**CERTIFIED VERDICTS 2026-08-04 (250M, s207/s208 vs sc025 bank 6180/5950):**
- idobs2 (TIP+identity+map+engrave+telemetry) = **6201/6079 — score-neutral-to-positive, NO expansion tax**. discoveries ~7.9/ep. tips unadopted (ε-floor) under baseline gold — dormant capability, harmless.
- discid (discovery_coef=1.0) = **5379 (−822 same-seed)** — coef 1.0 heavy overdose (gold1 pattern); mechanism PROVEN responsive (zaps 20×, pickups 18× of non-autopicked classes, engrave 2×, reads elevated) but discoveries barely rose (redistribution not amplification). Dose = sweep's job; discovery_coef knob in ini default 0.
- ENGRAVE_ID gotchas: only fire/lightning/digging formally ID (+10 score, engrave.c:900 more_experienced); tell-only types NEVER flip typeknown → once-per-letter episode bitmask (engid_tested) prevents charge-draining re-tests; engrave-test consumes charges ("too worn out" at 0).
- **Killer census (probe3k, species via internal[KILLER_MNUM])**: discid dies to Minetown watch 3.4% (watchman+captain), idobs2 0% — ranged attacks have NO "really attack?" prompt and the ray dirmask counted peacefuls as targets. FIXED: nle_peaceful_at accessor + hostile-only ray (peaceful in line blocks the shot). Vault guards ~1%. Shopkeeper deaths ZERO (shop protections hold). Ant family + pack humanoids still the core (burst collapse stable at 1B: 87% combat, killer mlev 2.7, starved 0.4%).
- death_weak stat added (died at Weak+ hunger, any death type) — decomposes hunger-assisted combat deaths; July coupling was 27%.
- 1B insight: zap adoption is SCHEDULE-dependent (1B cohort 2.4-8/ep, all seeds; 250M ~0.1) — lr/ε anneal fractions of total_timesteps keep exploration alive; "wands barely used" was a 250M artifact. CAST's 250M null likely same artifact — revisit at 1B.
- Eval-vs-mask rule: eval checkpoints under the mask semantics they trained with (hostile-ray landed AFTER the day's evals).


**FINAL CERTIFIED LEDGER 2026-08-04 (evening)**: msgconv (width-5 conv over trigram seq, zero-init proj, gradcheck-verified incl. randomized-P backward) = ARCH-NULL (+5/+150 seed-matched vs idobs2; s211 SEGV @131M = 2nd engine segv today, bit-reproducible on current binary — gdb repro is top infra priority). TIP-era evals via preserved pair (LD_PRELOAD; mask-size 733-vs-732 verified harmless, bit-identical re-eval): tip_s207 6361 (180M ckpt), tip_s208 **6873** = best certified IN THE POST-PRUNE FAMILY ONLY — retired lineage certified 6938±405 at 250M, so today's best draw ~= old family's MEAN (the -600 gap visible at 250M, not just 1B). Both TIP-only arms beat both fuller-stack arms seed-matched (identity/engrave additions possibly small tax vs lucky basins — undetermined, needs n). tipgold1_s207 3579: gold 1.0 taught DIVING (depth 8.86 deepest certified, sells 2.9/ep) NOT tipping (tips 0.000) — TIP unadopted under every reward tried. death_weak certifies 13-19%. idobs_s207 = uncertifiable orphan (era binary lost; era snapshots now standard: puffer_tip, puffer_msgconv in scratchpad).
