---
name: nethack-spell-channel
description: "Spell entity encoder + CAST pointer head — full inv-parity spell channel (built, gradcheck+goldens validated)"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-25T10:15:42.192Z
---

Built the full spell entity channel so CAST is observable + pointer-decoded, parallel to the inventory item channel (the "entity encoder just like inventory items" the user asked for). Part of the [[nethack-action-expansion-campaign]]; env details in [[nethack-env-setup]].

**Monk DOES start with a spell** (I was wrong to say otherwise) — a random level-1 spell (Sleep/Healing/Protection by seed), castable once energy ≥ 5 (fresh Monk has 4 energy, cost 5). So casting is a frequent early capability, and WHICH spell informs WHEN to cast (Sleep→enemy adjacent, Heal→low HP) — which is why the trunk pool earns its keep, not just the pointer.

**7 layers (all done unless noted):**
- L1 engine export (vendor/fast-nle): `nle_spell_row()` in spell.c (non-static, after percent_success) exports per known-spell [glyph=GLYPH_OBJ_OFF+sp_id, sp_lev, know_bin(KEEN bands 0-5), fail%=100-percent_success, castable]. New nle_obs fields `spell_glyphs`/`spell_state` **appended at struct END** (ABI-safe) + winrl.cc fill gated on `obs->spell_glyphs && !nle_partial`. NLE_SPELL_SIZE=16, NLE_SPELL_STATE_FIELDS=4.
- L2 obs layout (netlib.h/nethack.h): spell region appended after message (OFF_SPELL=4184, OFF_SPELLST=4216, OBS_SIZE 4184→**4280**). Mirrored NH_SPELL_OFF/NH_SPELLST_OFF in nethack.cu.
- L3 action space: **15 heads** now (verb|12 slots|dir|**spell**), spell head appended at index 14 (dir stays 13). CAST.head=-1 still; c_step reads actions[14] as spellslot. env_head_consume_map row for CAST = {verb, dir(13), spell(14)}. Spell mask block (legal iff castable). Macro nethack_do_cast sends Z + spellet(slot)='a'+slot (accelerator is tied to spl_book index, NOT menu sort order — dospellmenu).
- L4 CUDA encoder trunk (nethack.cu): spell1_w/b/s_w, spell2_w/b weights; nh_spell_{decode,sfeat,gather,max,max_bwd} kernels; reuses nh_inv_table (NH_SPELL_HID==NH_INV_HID==16) + dTinv_scatter + rownorm. NH_SPELL_POOL=64 appended to concat (proj_w grows); bias_acc + nh_bias_flush_kernel extended (+spell1/spell2).
- L5 CUDA pointer head: q_spell_w, spell_k_w; nh_sptr_{cos,dq,dkmat} (single head, tau slot NH_SPTAU=12 of the padded 16); output [verb|slots|dir|**spell(16)**|value], NH_DEC_OD 691→**707**. nh_spell_ptr_keygrad global feeds spell_out grad.
- L6 CPU reference (nethack.c NethackNet / DEMO_* constants) — **NOT DONE**: still 14-head/691, stale. Only the standalone `./nethack` demo uses it; TRAINING (_C.so = binding.c + bindings.cu) does not, so training is unaffected. Do L6 before using the demo probe.
- L7 validation: **gradcheck PASS** (test_nethack_encoder.py extended with spell branch in torch replica + test_nethack_cuda.cu wrappers; all spell weights/keygrad/grad_input <1e-6). **Goldens 34/34 PASS** (spell buffer unbound in goldens → byte-identical). 8M smoke: 15 heads, no crash.

**GOTCHA — zero-turn cast exploit (fixed):** `castable` initially only checked energy+sp_know. But spelleffects() rejects zero-turn (return 0, no energy spent) also on hunger (u.uhunger<=10), strength (ACURR(A_STR)<4), and rejectcasting (Stunned/!can_chant/!freehand). A starving Monk had CAST masked-available but every cast aborted free → random policy spammed it (smoke casts=**1028**/ep, probe 99.9% zero-turn). Fix: castable now mirrors ALL zero-turn rejections (pure predicates, SPE_DETECT_FOOD/RESTORE_ABILITY exempt). After: probe 80% turn-consuming, smoke casts=0.12/ep early (self-limiting by energy). check_capacity (encumbrance) returns 1 (turn elapses) so NOT gated.

**GOTCHA — engine struct change:** adding nle_obs fields mid-struct + fast incremental build → mixed layouts (partial offset shifted) → goldens diverged with INIT mismatch. Fix: append at struct end + `cmake --build ... --clean-first`. build.sh only rebuilds engine if libnethack.so missing — force manually after engine edits.

**A/B RESULT (2026-07-25, killed at seed 43 ~144M by user, "accept the null"):** casts spiked to ~28/ep in early exploration then COLLAPSED to ~0.00 and stayed — the Monk policy ABANDONS CAST. Decays to ~0 (vs blind-CAST's 0.45 residual) precisely because the castable fix removed the phantom hungry-abort casts. Score tracked the ~5300 baseline (channel is score-NEUTRAL, not harmful). Verdict = the learnable-first equilibrium: a melee, energy-limited Monk correctly declines to cast. Castable moments are genuinely rare for an ACTIVE Monk (low-energy/hungry/stunned = when casting physically can't happen), plus chicken-and-egg (rare casts → verb head learns to avoid CAST before the pointer learns to aim → abandonment). The channel is CORRECT + reusable infrastructure; the Monk is just not a caster. To make CAST actually matter would need either a caster class (Wizard/Priest — breaks baselines) or bootstrapping a "landed-cast" reward to break the chicken-and-egg (declined for now).

**REVERTED to GATED-PRE-CAST 2026-07-25** (user: "revert back to what was before we started adding cast but after the fixes"). Cast/spell fully removed from BOTH repos; engine rebuilt to committed (goldens 34/34). Then RE-APPLIED just the consumed-head gating fix (the user's de-lucked 5319 baseline): `src/pufferlib.cu` gating hunks (git apply --include from the patch) + a hand-written 14-head `env_head_consume_map` in `binding.c` for the committed 22-verb/14-head action space (verb|12 slots|dir; directional set MOVE/RUN/KICK/THROW/ZAP/APPLY, no CAST). _C.so rebuilt, 14 heads, symbol linked, clean. Working tree now = committed + gating only (pufferlib.cu + binding.c). The full cast+spell work is saved as durable patches at `/puffertank/spell-cast-patches/`:
- `pufferlib_spell_cast.patch` (git diff HEAD, pufferlib repo — spell channel + CAST verb + **consumed-head gating in pufferlib.cu**)
- `fastnle_spell_cast.patch` (git diff HEAD, vendor/fast-nle — engine spell export + castable fix)
- `nethack2.ini`/`nethack3.ini` copies (saved sweep configs, kept in place too as untracked)
To restore: `git apply` each patch in its repo, rebuild engine (`cmake --build ... --clean-first`) + `_C.so`. NOTE the revert also removed the gating (coupled to the cast consume-map; can't stand alone on the committed action space) — it's in the pufferlib patch if you want to re-derive just that de-lucking piece. L6 (demo CPU ref) was never done.

**GATING COMMITTED then SPELL RE-APPLIED 2026-07-25.** User committed the gating alone as `4405b25d head gating` (pufferlib.cu + a hand-derived 14-head consume-map in binding.c) — the clean gated baseline, verified to bit-reproduce gate1_s43=5329.221 exactly (training here IS bit-deterministic; my earlier "diverges run-to-run" claim was a misaligned-log-sampling artifact — retracted). Then user said "put back the spell casting and run the seeds": re-applied the cast/spell on top by `git apply`-ing the fastnle patch + the cast-only pufferlib files (netlib/macros/nethack.h/nethack.c/nethack.cu/tests), and hand-editing binding.c 14→15-head (NUM_ATNS 15, ACT_SIZES+spell, consume-map dir→[13] + spell head [14] on CAST). Left the committed pufferlib.cu gating untouched (generic — reads the 15-head map fine). Rebuilt engine(clean)+_C.so, goldens 34/34, 15 heads, casts fire. Ran the 5-seed A/B: project encoders, group `spell-cast-5seed`, tags spell5_s{43,44,45,46,73}, 250M, gated. **RESULT (final, paired vs gate1 no-cast):** s43 5475(+146), s44 5127(-432), s45 5518(+551), s46 4895(-337), s73 4958(-549). spell mean 5194.6 vs no-cast 5318.7 = **-124 (within the ±550 per-seed basin-reroll noise → score-NEUTRAL, not a regression).** Casts: **1/5 seeds retained casting** (s45 1.65/ep, also top scorer) — the other 4 abandoned it (→~0). Verdict = channel is correct + neutral; CAST is learnable-but-basin-dependent for a melee Monk (RL uses it only occasionally). Confirms the earlier single-seed null with n=5.

**FINAL VERDICT — RETRIAL UNDER ε (2026-07-28, group spell-eps05, ε=0.5%
gated 250M seeds 207-211):** 5746(c1.39)/5651(c0)/6053(c1.86)/5997(c0)/
6151(c0) = mean 5919±212 vs no-spell eps05 6183 → **-264**. With guaranteed
exploration (absorbing-state excuse eliminated): 2/5 seeds keep casting at a
ceremonial ~1.4-1.9/ep, 3/5 abandon at the anneal. Third consecutive negative
comparison (-124 paired, -366 partial, -264 final). **CHANNEL DROPPED
definitively for the Monk** — correct infrastructure, rationally-priced-
near-zero verb (one weak L1 spell; READ→learn-book pipeline dies because
unknown-book reading is dangerous + books rare). Archived in
/puffertank/spell-cast-patches/ + scratchpad spellsave/. Revisit only for a
caster class or if a book-supply feature ships.

**2026-08-10 V3 COMMITTED — pointer arch SHIPPED, boundary tax gone:** v2's
positional head + naive embeds replaced by content-keyed pointer: relu slot
reps `relu(spk_w·[e_eff(book)|known,lev/7,fail/100,know/20000])` 16-dim,
inv-idiom pool `relu(max_s(spk2_w·rep)+b)` (16 concat dims, NH_CONCAT 730),
dot CAST head `q13·rep/4` (NH_QHEADS 13, DEC_LIN 75, obs 4442, net −880
params vs naive). Boundary tax was kaiming fan-in dilution over v2's dead
columns — v3null 7,137 == eps10 7,136 (tax GONE), v3full 6,999 (channel
neutral @250M). 1B: v3fb {9,111 RECORD, 7,743}, v3fbc carve {8,559, 8,695}
vs old best 8,302 — carve wins on adoption-reliability (no-carve drew an
abandoner). Record's second-spell use audited genuine-but-trace: 152 slot-1
casts of 11 spells across ~24/20K episodes, message-verified (detect
monsters 4/4, create monster visible, confuse 11 ok) — supply is THE
bottleneck → books arm (`NH_SPELL_BOOKS=1`, STILL NEVER RUN) is next; plan =
v3cb books ×5 first, control cell only if delta ambiguous (100-400).
COMMITTED: pufferlib d802a161 (spell v3 + wedge drain fix + gated watchdog +
demo mirror + config winners verb_eps 0.01/ac_nospell 1.0), fast-nle fork
30abdf752 (boomhit, 256KiB fibers, spells2, boulder UAF, true-glyphs).
NH_SPELL now DEFAULT ON (=0 legacy), flip validated bit-exact 8,583.463
pre/post on v3fbc_s702@hardened binary. Demo weights = v3fbc_s702 1B ckpt.
Eval-noise decomposition (user-vetted): per-cert SE ≈ 90 (10K eps, ep-std
~9K); seed sigma 250-450 dominates cells; headline numbers get 40K-episode
evals from now on. 1B pairs seeds 703-705 unrun. wandb env/<verb> = TRAIN
rolling stats, ε-inflated — adoption claims need eval castlog.

**2026-08-09 SPELL CHANNEL V2 (built+validated, VERDICT: score-neutral, commit-eligible):** slot-faithful `nle_spells2` (exports forgotten spells, know=0 = re-read cue; old accessor HID them + compacted indices = slot-letter mismatch), 33-int spell block (count + 8×[id,lev,fail,know]), 8×32 e_eff book embeds in concat (NH_CONCAT 1002, obs 4442), 20th head = positional 8-way linear (NOT a pointer — deliberate: uniform-55-key kernel machinery too costly for 8 stable slots; content lives in trunk, order-DEPENDENT — pointer-v3 is the books-arm prerequisite). Flag-gated NH_SPELL (off = legacy info-parity); NH_SPELL_BOOKS separately gates '+' autopickup (never yet run). Gates: goldens 34/34, gradcheck PASS, SPS 268K off / 234K on. **A/B on eps0.01-nocarve, 6 paired seeds: mean −89±188 = NEUTRAL**; treatment cell 6,518 n=7, control 6,688 n=7. Depth-drift scare (treatment seeds deep+tough, s306: 48% d8+, AC −4.54) RESOLVED — profile appeared flag-off too (s311); it's a basin class of the config, both sides. s306 blank-probe: dive lives in weights (flag-off eval → deeper+poorer 4,415). Slot head PROVEN live in wild: 469 casts from slots 1-7 (floor books, no autopickup). **ARCH-BOUNDARY COST −300..−430** vs eps10 on matched seeds — NOT free; suspect init scale of new params; every future run on this arch pays it — investigate before commit. RETENTION = EPISODE CLOCK insight: sp_know/20000 is the policy's first time signal (bf16 quantum ≈ 80 turns); explicit turns-elapsed obs is a candidate feature for depth campaigns. Discipline forensics (era castlogs): ALL carve+ε adopters cast like the 7,941 (prophylactic prot ~full HP, damage-conditioned others) — 7,941's edge was BASIN not skill; consistency lever = 1B horizon (11/11 1B/2B seeds adopted every verb; dead verbs are a 250M budget artifact). Era worktrees: wt_wobs (pre-spell, bit-verified 7,159.132), wt_commit (pre-wobs, acsp era). discswap built+flag-gated (NH_DISC_SWAP: discovered identity REPLACES appearance glyph), chain script ready, unrun. Seed-308 landmine: deterministic engine segv at 81.9M on spnull2/at 49M on sc0125 (trajectory-dependent — spfull2_s308 completed fine); use s309 as sub; gdb candidate.

**2026-08-10 EVE — c250 control cell + BOOKS ARM LAUNCHED:** committed-stack
250M baseline (bare launch, group val-commit): c250_s{305,306,307,309,310} =
{7331, 7059, 6378, 6362, 7050}, mean 6836±197SE — regression-free vs v3full
6999 / eps10 7136; clean farm(3)/dive(2) split. All seeds eval-verified
balanced casters (castlog: 5-11 casts/ep, prot/sleep/heal ~50/25/25, zero
wedges; cast volume tracks farming style). 13-run correlation matrix: score
axis = farm-vs-dive (death_weak +0.69 = LONGEVITY marker, prayers_fed +0.62
vs max_depth −0.56, armor −0.53 — Simpson vs the causal WEAR ablation).
Food census (champion): 28.7% deaths Weak+, 46% with ZERO food (supply),
54% carrying ~2.4 items (fainting = too-late class); buys 0.003/ep because
delta-gold reward FINES purchases — high-water gold re-test proposed,
parked as future work. reads split shipped: reads_scroll/reads_book stats.
ALTAR_ID verb: 0 uses across entire lineage (dead verb; adopted chains all
start passively via autopickup — the books-arm thesis). BOOKS ARM RUNNING:
c250b_s{305-310} × 250M, NH_SPELL_BOOKS=1 on train AND certs (env parity),
group books, castlogs captured per cert; paired vs c250; done ~19:45.

**2026-08-10 NIGHT — BOOKS v1 KILLED (waste loop), READ HYGIENE + books2:**
books v1 pairs {−1025, −928, +641} = basin lottery + a READ WASTE FURNACE:
34.5K/44.8K early book-reads were "know it quite well already" re-studies —
the drain auto-'y's the engine's own "read anyway?" prompt into full
multi-turn re-study of FRESH spells (turns+hunger burn, not a frozen
wedge; blind reads = minor zero-turn class). s310-control's 2.3 reads/ep
"habit" = same waste. FIX (uncommitted): nethack_slot_usable READ block —
blind masks both readable classes; book slot masked when its spell know >
2000 (engine KEEN/10 threshold), matched via inv_true DISCOVERIES channel
(inv_glyphs is the shuffled APPEARANCE — first mask attempt matched
otyp against appearance and never fired; probe caught it). Probe validated:
quite-well 34,260→4, learning events visible ("add sleep/create monster to
repertoire"). books2 cell b2_s{305-310} launched (group books2, hygiene
mask + NH_SPELL_BOOKS=1, castlog certs). CONFOUND NOTE: books2 vs c250
differs by autopickup AND hygiene mask — hygiene-only cell is the
follow-up if books2 wins. Read telemetry split reads_scroll/reads_book
shipped; NH_READLOG hook added. c250 CONTROL CELL (complete): {7331, 7059,
6378, 6362, 7050} mean 6836±197.

**2026-08-10 LATE — books2 VERDICT + basin-lottery decomposition:** b2 cell
(books + read-hygiene) pairs vs c250: {+434, +162, +962, +160, −705}, mean
+203±267 = NOT significant. BUT decomposition is clean: non-flipped pairs
= +160/+162/+434 (hygiene dividend ~+160-430); the two basin FLIPS cancel
(s307 dive→farm +962, s310 farm→dive −705; flip signature = max_depth +
min_ac swing; dive tax ~700-1000 at 250M). ANY env change re-rolls basins →
paired cells carry ±700-1000 flip variance; readout discipline: classify
pairs by profile (depth/AC), estimate from non-flipped. b2_s305 = 7,764 =
250M LINEAGE RECORD. Leak checks clean: d_score% > d_return% all pairs (no
shaping exploit), not deeper, no gold/xp channel shift — pure turn-economy
gains. s307 read-spike = BLANK spellbooks (turn-consuming REST-like no-op,
self-pruned, return 1 = takes time → stays legal per free-refusals-only
mask rule). Zero slot-1 casts at 250M certs (supply ceiling 0.1-0.2
books/ep = learn events don't consolidate at this budget; 1B is the real
books test). Hygiene-v2 audit: WIELD-welded (wield.c:280 return 0, never
expires) + TAKEOFF-known-cursed (do_wear.c:1605 return 0; first probe on
unknown BUC consumes a move per line 1978 → mask known-cursed only) both
verified zero-turn, unbuilt. WIELD terminal ~0 = CORRECT Monk equilibrium
(user), not gradient damage. c250h hygiene-only attribution cell LAUNCHED
(group hygiene, ~23:20 done); 1B interleave (val + books-at-1B) proposed,
awaiting user.

**2026-08-11 AM — OVERNIGHT LADDER DONE, NEW ALL-TIME RECORD:** night2
ladder: c250h {7636,7216,5907,6134,s310 crash-lost} 6723 / hv2 (wield-weld +
takeoff-cursed masks) 6721 / scr (+'?') 6834 / full (NH_ALLPICK) 6845 — ALL
FLAT vs control 6836 at 250M (basin lottery ±700 swamps; the +160 hygiene
dividend did NOT replicate — retracted; b2-vs-c250h matched farm pairs
{+128,+5,+388} = also noise). full uniquely 5/5 farm (loot richness anchors
farming — variance reducer). Adoption dose-responsive: scroll reads 0.2→1.2
(scr)→2.5(full)/ep; books ≤0.1 everywhere at 250M. 1B on auto-picked winner
full: **full1b_s701 = 9,423.744 ALL-TIME RECORD** (shallowest profile ever:
depth 6.54, ep_len 2100, min_ac −1.45, sells 0.27/ep = 4× shop economy,
scroll reads 4.1/ep book 0.44/ep, applies 0.00 oddity; 57% of reads = blank-
scroll REST loop, rest = real identify economy: enchant armor/mapping/remove
curse vs destroy-armor/amnesia/punishment tax); full1b_s702 = 7,746.554 →
pair mean 8,585 ±wide == carve champion 8,627 (NOT established better; n=2).
record recipe: committed stack + read-hyg + v2 masks binary + NH_ALLPICK=1,
seed 701, ckpt checkpoints/nethack/full1b_s701/. COMMIT PROPOSED (record
stack wholesale, flags stay opt-in; demo-weights question open) — awaiting
user word. c250h_s310 = deterministic crash class (exit 245 ×2).

**2026-08-11 MIDDAY — disc-swap cell + CHAMPION COMBO 1B:** dsw cell (vs hv2
same-binary control): {6510, 7532, 7544, 6195, 7138} mean 6984 = +263±232
n.s., BUT 5/5 FARM (second diver-suppressing cell after full-autopickup;
pattern: obs/env enrichment stabilizes the farm basin) + strongest top-3 of
any same-binary cell. User prefers disc-swap (substrate for future glyph-
merge/identification work; NH_APPEARANCE_COLLAPSE spec'd but unbuilt:
collapse shuffled-appearance unknowns to per-class glyph, EXCEPTIONS clear
potion/unlabeled scroll/plain book/gems (fixed+informative), obs-pack-only,
losses = wand tells + price-ID; blank-scroll REST behavior verified turn-
consuming empirically, 94.7% delta≥1, max same-t run 3). champ1b pair
LAUNCHED: NH_ALLPICK=1 NH_DISC_SWAP=1, seeds 701/702, group champ1b, direct
control = full1b {9424, 7747} same binary/seeds. If it holds: champion
recipe = base+allpick+discswap; then commit pending code (read-hyg + v2
masks + telemetry), consider default-flips, demo weights. Era-strand: dsw
changes obs — eval old ckpts WITHOUT flag, champ ckpts WITH. Rings/amulets
= dead verb pair across ALL arms (putons/removes 0.00) — future arm.

**2026-08-13 SPELLBOOK CENSUS (NH_INV_CENSUS, 2 record ckpts, 3K eps each):
books arm premise KILLED — acquisition is fine, STUDY is the gap.** Full
autopickup means 46-63%% of episodes DIE HOLDING >=1 spellbook (mean
0.55-0.73), yet only 4.3%% ever know a 2nd spell. No env lever exists (books
flow in; READ study is a pure delayed-payoff decision the policy declines,
reads_book 0.04/ep). NH_SPELL_BOOKS was never built and nothing to build.
The +700-850 spell-draw-lottery prize remains but needs the policy to STUDY —
either the small-step recipe cracks it with budget (watch reads_book at 1B)
or it needs a reward nudge (user territory, not proposed). SLOT WALL (same
census): items-at-death p50 36-37, p90 50, 16-18%% of episodes >=48 slots,
5-6%% hard-full at 52-53 — late-game autopickup silently refuses in the BEST
episodes; weight binds far less (burdened-at-death 5-9%%). Slots-used scalar
obs = candidate small addition (precedent: encumbrance-margin obs). Census
hook: NH_INV_CENSUS=prefix, C lines (items books spells burden eplen score),
snapshot pre-death each live step (blstats-teardown-safe), uncommitted.

**2026-08-24 SPELL SUMMARY = INV-MAX FAILURE MODE, PROVEN (v51b_s701,
200K real frames, checkpoint-weight numpy branch replica validated vs
live actstats corr 1.000)**: per-slot KEYS represent spells near-
perfectly (book identity AUC .97-1.00, n_spells R2 .97, min_fail .76,
max_level .74, forgetting-soon AUC .92) — but the spk2 MAX-POOL trunk
summary DESTROYS it (identity AUC .18-.24 i.e. ANTI-predictive, n_spells
.11, fail/level ~0; only one book survives .93; half the 16 dims dead).
The trunk was never OFFERED spell info — "spell channel neutral" lore
reframed: casting works only because the CAST pointer bypasses the pool
and reads intact keys. Knockout-null + half-dead dims fully explained.
FIX CANDIDATE (v5.1): replace spk2 max with the certified inv2 recipe
(masked-sum x0.2 or attn) — untested whether trunk spell-awareness buys
score, but the delivery failure is now proven, not the demand. Probe
infra: NH_OBSDUMP=path:stride env hook (nethack.h, 5c) + checkpoint
reg-order weight extraction (encoder-first, fp32; offsets validated).
**FIX VALIDATED OFFLINE 2026-08-24**: parameterless Σkeys (16d, deletes
spk2 max entirely) recovers n_spells .94, identity AUC .93-1.00,
forgetting .91 (vs pooled .11/.2/.24); extremum stats (min_fail/max_lev)
.57 vs keys' .76 — full recovery needs isum-idiom or +1 attn query.
Spell-fix = the inventory playbook in miniature: attention for retrieval
was never the issue here (CAST pointer covers it); the TRUNK summary just
needs sum not max. v5.1 shelf change, ~5 lines + gradcheck.
**SPELL-LAB ARCH SWEEP 2026-08-24 (8 arms, frozen deployed keys + trained
summary+readout, 200K frames, joint 9-target objective)**: WINNER isum32
(relu(W·key) masked-sum x0.2, 32d): n_spells .98, identity AUC .91-1.00,
max_lev .54, forget .85. summax32 (isum16‖max16) close 2nd, best max_lev
.61. Trained max16 (incumbent idiom) still UNDERDELIVERS even when
optimized for the task (n_spells .80, identity .67-.87) — the idiom is
the problem, not RL training. sum16-free strong except extrema. attn2x16
mid (no win at this width). scratch control (retrain keys): identity
best but scalars poor — deployed keys are GOOD, keep them (pointer
compat). min_fail caps ~.5 for all 16-32d summaries vs .76 from full
keys — extremum-of-scalars fundamentally wants more width or a query.
V5.1 SPEC: replace spk2 max with isum32 (params 16x32+32, concat +16
dims); summax32 if castability matters.
**NH_SPELL2 IMPLEMENTED + 1B LAUNCHED 2026-08-24**: final design = keys
selection-only (unchanged); trunk gets ss_w(32x36) sum channel over RAW
slot inputs (bypasses the measured 16d key bottleneck: per-slot category
.72/level .41 in-key vs 1.0 raw; isum-raw beat isum-keys: escape .87 vs
.52) + 4 doorstep scalars [min_fail,max_lev,n/8,min_ret] (empty book ->
[1,0,0,1]); spk2 max DELETED. dkeys = pointer-only (nh_sp2_dk); sum-path
embed grads via nh_sp2_dE (mirror of spkey_dE, both into dE_i). Spell
slice 16->36, concat 1006->1026. VALIDATED: fpgate defaults PASS x2,
NH_TEST_SPELL2 gradcheck FULL PASS (ss_w/ss_b FD 8e-4, torch 4e-8; V5 +
default arms re-PASS; spk_w/spk2 now in enc_names all arms; terr parity
check reworked for atan2 replica w/ boundary tolerance — lm exact,
sector flips <2%), 8M smoke SPS 191K. RUN: v5sp2_1b_s701 (seed 701 =
same-seed vs 8,919 inline / 8,753 standalone), binary nethack_v5sp2
(atan2 era ✓ comparable), group v51b. Harness gotcha: dec_check had its
own nh_numel_spk2_b call.
**NH_SPELL2 1B RESULT 2026-08-24 — DID NOT BEAT THE RECORD (n=1)**:
v5sp2_1b_s701 cert 7,815 inline / 7,898±88 standalone med 5,158 vs
same-seed record 8,919 / 8,753±106 med 5,384 -> −855±138 standalone
(~6σ vs eval noise, but ONE seed and an arch change re-randomizes the
basin; slightly beyond the ±600 basin-noise lore). Curves interleaved
through 780M (+73); the deficit is the FINAL 200M endgame. MECHANISM:
spell-slice knockout on the sp2 ckpt = −113 (7,477 vs 7,590 cold-paired)
— the trunk used the clean spell channel only MARGINALLY (old broken
channel: −1). Verdict so far: delivery was fixed (proven), demand looks
weak at this play regime — the terrain pattern again (offered ≠ wanted),
this time possibly with a small integration cost. Decision needs s702
pair or acceptance of the null; NH_SPELL2 stays a flag, NOT promoted.
**"LIB ERA BREAK" RETRACTED 2026-08-25 — was a measurement artifact.**
The Aug-24 bisect compared 66M-form repro ckpts against the record's
1B-form ckpt: with anneal_lr=1 the lr schedule depends on
train.total_timesteps, so a 66M-form ckpt can NEVER hash-match a
1B-form ckpt. All 66M repros agreeing (364e4cbd) while "failing" vs
f5bd6868 is exactly the no-change signature. PROOF: matched-command 1B
repro (v51b_s701r, current lib post-kit-rebuild) reproduces the record
run's 32M ckpt BIT-EXACT (8df9df83cec0f96c). Also proven en route:
goldens 34/34 on the rebuilt lib; pure-addition lib rebuilds are
trajectory-neutral (minus-2-fns rebuild == current-era hash). =>
sp2_701 7,815 vs record 8,919 is a clean same-seed comparison after
all (but an arch change re-rolls the basin, so still n=1). With ctrl
draws {8920,8507,7774,7482} (s701/702/705/706) mean 8171 sd ~700, the
old pair was a fortunate draw, sp2 {7815,7916} mildly low/null.
LESSONS (replacing the retracted rule): (1) ckpt-hash comparisons are
valid MATCHED-COMMAND ONLY — total_timesteps/anything feeding schedules
must match (run_id/binary-name proven irrelevant); (2) before declaring
an era break, repro with the ORIGINAL full command; (3) archiving
libnethack.so per era is still cheap hygiene (kept: scratchpad
libnethack.so.era364).
