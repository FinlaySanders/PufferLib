---
name: nethack-bimodal-verbs
description: "Root cause of behavior basins: delayed-payoff verbs are absorbing states of on-policy PG; census shows 5 bimodal verbs (wear/engrave/cast/throw/drop); coin-count ladder to 6000; attack = legal-verb ε-floor"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-07-31T19:44:03.614Z
---

Root-cause analysis of behavioral basins (2026-07-27), extends
[[nethack-armor-bimodality]]. Fresh-seed experiment: groups fresh-spell5 +
fresh-gate5, seeds 201-205 per arm, gated 250M; arm 2 on committed HEAD
CHECKSUMMED bit-exact (fgverify2_s43 = 5329.22119140625 — requires explicit
--train.total-timesteps 250000000; the config default 247765094 changes the
LR-anneal schedule and re-rolls the whole run — that accidental variant scored
5877, best-ever s43, heavy wearer).

**MILESTONE: fg_s204 = 6000.62 terminal eval — campaign target hit.** Fresh
seed 204, committed gate stack, standard config, all-coins-won basin (wears
5.35/min_ac 1.21, engraves 29.8, drops 21.2, throws 2.1).

**Fresh results:** spell arm: wearers 5542/5241, non 4706/4360. gate arm:
wearers 6001/5731/5520, non 5505 (s203 = non-wearer both arms; s202 flipped
non→wear across stacks +1025). Wearer cohort mean 5509 vs non 4857 = +652 ≈
the ablation's causal 600-680. NOTE fg_s203 5505 armor-less: strong non-armor
routes exist; armor is +600 typical, not a prerequisite. Crash rate on fresh
seeds: 2/11 segfaults (fsp_s201 spell-stack ~150M, fg_s205 gate-stack ~60M,
exit 139 no panic msg, deterministic per seed×stack — substitute seeds, don't
rerun; future hardening target).

**Verb census (20 gated 250M runs) — BIMODAL basins are the norm:**
- drops: 0.00-0.03 (4 runs) | 2.5-17.7 (16) — 56x gap
- engraves(Elbereth): 0.02-0.04 (3) | 1.5-38 (17) — 32x
- casts: ~0 (7/9 spell runs) | 0.94-1.65
- throws: 0.00-0.13 (5) | 1.9-9.6 — 14x
- wears: 0.00-0.49 | 2.25-5.9
UNIMODAL (immediate payoff → no coin): quaffs, prayers, eats, pickups,
search20. DEAD everywhere: zaps, wields, putons, removes, takeoffs.
**Cohort weights:** wear +404, engrave +416 (the two big coins), drop +91,
throw +69. Coin-count ladder: 4-coin runs mean 5570 (incl both records),
3-coin ~5300, 2-coin ~4940.

**ROOT CAUSE:** delayed-payoff verbs are absorbing states of on-policy policy
gradient: (1) rich-get-richer — a verb learns only when sampled; P(verb)→0
stops the correcting data (gating makes downstream heads fully frozen);
(2) credit gap — armor/Elbereth pay via survival over 1000s of steps,
invisible to advantage estimates in the 20-60M decision window (immediate
signal ~0.15/ep vs turn-cost noise → early luck decides the sign);
(3) entropy anneal closes re-exploration by ~60M (s45's 180M escape = rare).
Immediate-payoff verbs have zero credit gap → unimodal. Every future verb
(shop/wish/offer) will flip the same coin unless fixed structurally.

**PLANNED ATTACK — legal-verb probability floor (ε-floor):** verb head as
mixture π' = (1-ε)·softmax + ε·uniform(legal), trained THROUGH the mixture
(logprobs on π', PPO consistent). ε≈1% → every legal verb ~1-2 samples/ep
forever, absorbing state destroyed; gating routes the floor's samples to the
right heads. ~20 lines in the sampling/logprob path (pufferlib.cu — ours),
sweepable ε, eval can set ε=0. A/B: 5 fresh seeds (207-211) certified gate
stack vs n=7 reference; success = 5/5 wear AND engrave basins, mean ≥5600,
spread collapse. Sibling option: adaptive per-head entropy floor (softer).
Per-verb reward shaping (held-AC etc.) = whack-a-mole fallback only.

**ε-FLOOR RESULT (2026-07-27 overnight, arm 1 of matrix):** ovn-eps1 (1%,
anneal→0 last 20%, gated, 250M, seeds 207-211): **6115/6374/5675/5851/6308 —
mean 6064 ± 298, 5/5 all-coins** (wears 5.2-12.1, engr 20-23, drops 28-52,
min_ac 0.30-1.07). Arm MEAN beats the old all-time single-run record (6001);
worst seed (5675) beats the old wearer-cohort mean (~5500). Bimodality
eliminated in-arm; std halved vs mixed basins. Pre-registered SUCCESS → ε=1%
is lock-in candidate as the new stack default. G1 dormancy passed
(5329.221 bit-exact, flags off). Implementation: mixture in sample_logits +
PPO-side mixture logprob w/ grad scale (1-eps)p/p'; eps in device scalar
(cudagraph-safe), verb_eps_update() in bindings rollouts(); entropy on bare
softmax. GOTCHAS hit: build.sh does NOT rebuild engine after source revert
(stale spell-ABI libnethack → instant fill_obs segv — force cmake
--clean-first); ini int-typed defaults make CLI reject float overrides (use
0.0 not 0 for new env coefs). Matrix continues: holdac/entfloor/eps03/
firstwear overnight + dose extension {0.5,2,3}% chained after.

**FULL MATRIX RESULT (2026-07-28 05:57, 25 runs, 1 substitution
holdac_s211→212 segv):** same seeds 207-211 per arm, gated, 250M:
- **eps1 (ε=1%): 6064 ± 298, 5/5 all-coins** — WINNER
- eps03 (ε=0.3%): 5915 ± 329 — armor 5/5, Elbereth 4/5, drops 4/5 (secondary
  coins need the bigger floor)
- firstwear (+0.2/new-min-AC pt): 5610 ± 342 — armor 5/5(!) but Elbereth 3/5,
  drops 4/5; converts its own coin well, others lottery
- holdac (+0.0005/step·(10-AC)): 5264 — armor 4/5, Elbereth 3/5 (two runs
  engr=0.0); s207 stayed non-wearer while collecting the hold stream = credit
  CANNOT fix an unsampled verb
- entfloor (hinge λ=0.05 @0.5nat): 5263 ± 693 — armor 4/5, Elbereth 5/5,
  **drops KILLED 3/5 (0.0 exactly, worse than baseline 16/20)** — soft
  pressure distorts the equilibrium; hard floor doesn't
Reference bank ~5470. VERDICT: exploration was the binding constraint;
verb-specific rewards fix ~their own verb only (whack-a-mole confirmed
empirically); guaranteed sampling (mixture) strictly dominates soft entropy
pressure. ε dose monotone 0→0.3%→1%; dose extension {0.5,2,3}% running
(chained, done ~10:30). eps1 depth 6.63 vs ref 6.16: score comes from
surviving richer, NOT diving — farm-vs-dive still unexploited on top of this.

**ε DOSE CURVE (2026-07-28, 5 seeds each, gated 250M, seeds 207-211):**
0%(bank)~5470 · 0.3%→5915 · **0.5%→6183±115 (PEAK, new best arm)** ·
1%→6064±298 · 2%→5222 · 3%→5247. Clean single peak at 0.5%; over-exploration
tax ~-900 by 2% then plateaus. Constant-ε phase carries a real mid-training
tax (~600-800 below no-ε runs mid-run — forced pray/descend/wield knock-ons,
softer policy) fully refunded at anneal: eps runs climb ~+1400 in last 20% vs
~+700 baseline LR-endgame; NEVER judge an ε run pre-anneal; constant-ε-forever
would eat the tax permanently. Dead verbs (wields/zaps ~1/ep) in telemetry
during floor phase = the floor's own forced samples, NOT policy (softmax P≈0);
they drop to exactly 0.00 at anneal while adopted verbs (wears) RISE — what
survives the anneal is policy-owned. eps1 depth 6.63: gains are Mines-branch
(Minetown 50% vs 30%, deep-mines 23% vs 11%) — armor loot loop; main-dungeon
D5+ flat ~45%, Sokoban flat ~3% = untouched frontiers. Longer runs alone do
NOT fix bimodality (val-1B 0/8 wearers at 1B pre-gating; absorbing state has
no expiry) but compose: ε@1B = next big shot after schedule freeze.
RUNNING: anneal-start test at winning dose (PUFFER_VERB_EPS_ANNEAL_START knob
added; default 0.8 preserved): ovn-eps05-a60 / ovn-eps05-a40 vs ovn-eps05
(@0.8, 6183) — G1C dormancy gate re-verified before arms. Winner becomes stack
default + spec for the 1B run.

**LIVELOCK FAILURE MODE (2026-07-28, a60_s210):** engine can LIVELOCK (infinite
loop, 565% CPU, wandb silent 2h) as well as segfault — a degenerate state the
panic-hardening doesn't cover, and exit-139 substitution logic can't catch
(process never exits). Cost 2h of pipeline. Mitigation: run drivers should wrap
trainers in `timeout 2400` (runs take ~19 min); session-level watchdog monitor
on `puffer train` elapsed>35min. Also: killing a run mid-arm gives exit 137 →
driver moves to next seed WITHOUT substitution (arm ends n-1). Livelock cause
unknown (fresh-seed trajectory-specific like the segfaults; ~1 in ~60 runs).

**ANNEAL-START RESULT + DEFAULT DECISION (2026-07-28):** at eps=0.5%/250M:
a80=6183±115 (n=5), a60=6094 (n=4, s210 LIVELOCKED), a40=6115±90 (n=5).
Statistical wash → the floor's work is done in the first ~100-150M ABSOLUTE
steps; extra floor is neutral rent at 250M. **USER DECISION: a40 =
PUFFER_VERB_EPS_ANNEAL_START=0.4 is the new default for 250M-class runs.**
LR interaction (user raised): LR cosine is FRACTION-scheduled → a40 commits at
LR≈0.65 base (validated fine); for 1B use anneal-start 0.2-0.3 (200-300M
absolute floor; commit at LR 0.90-0.79 = mild extrapolation of a40); if 1B
post-anneal climb doesn't appear by ~450M, revert long runs to fractional
coupling. ent_coef anneal is OFF in config (no 3-way schedule tangle).
Current stack defaults: PUFFER_HEAD_GATING=1, PUFFER_VERB_EPS=0.005,
PUFFER_VERB_EPS_ANNEAL_START=0.4 (250M runs).

**SCALE RESULTS (2026-07-29 overnight, floor-reward stack, eps 0.5% gated):**
- 250M arms: ~6100-6180 · **1B (l1b_s301, a=0.2): 6740 = ALL-TIME RECORD**
  (+367 over best 250M-era run; game_time 9082, XL 7.0, all coins)
- **4B (l4b_s303, a=0.08): 5990 — WORSE than 1B.** Over-converged turtle:
  engraves 62 (2x the 1B), wears down to 4.9, minetown reach collapsed 50%→21%,
  floors 5.67, truncated 7% (!), game_time 9136 ≈ same as 1B.
**THE 10K-STEP EPISODE CAP NOW BINDS**: game_time plateaus ~9100 at both 1B
and 4B; 4B spent its extra compute sharpening defensive Elbereth-camping
inside the cap instead of exploring. Scale law: 250M→1B +550, 1B→4B -750;
peak ≈1B under current cap. IMPLICATION: longevity-farming is mined out —
the lever is now score-per-turn efficiency and DEPTH economy (dive gating,
Sokoban, racket), NOT more optimization. (Cap is a campaign constant per
score-objective definition.) l1b_s302 + a60_s210-style livelocks: 3rd
livelock killed by watchdog v3 in 11 min. 1B n=1 (s302 livelocked).

**CERT REFERENCE UPDATE (2026-07-29 05:05):** the recert target for the
committed floor-reward stack is now (seed 207, gated, eps=0.5%, a40) =
**6241.59765625** (fr_s207; champverify4 reproduced it bit-exactly). The old
6165.7109375 target belongs to the pre-floor-reward stack — stale after the
floor-reward commit. RECERT4 "failure" was actually a pass vs the wrong
constant. ULP GOTCHA: changing float expression forms in eps math (e.g.
(ae-frac)/(ae-a) with float ae vs (1.0-frac)/(1.0-a) double) re-rolls
trajectories — dormant paths must preserve byte-identical arithmetic
(recert3 caught this). END-knob now: ae>=1.0 uses the original expression.

**CAP CORRECTION (2026-07-29):** truncation = 10,000 ENV STEPS (stats.length,
nethack.h:598); game_time = NetHack TURNS (uncapped). Typical episode: ~2,470
steps ~ 9,100 turns (~3.7 turns/step via search20 20:1 compression) — dies at
~25% of the step cap. The ~9,100-TURN plateau across 1B/4B is a DEATH plateau
(survival economics: food-radius depletion + wandering-monster attrition at
XL7/depth6), NOT the cap. The cap only binds the 7% truncated turtle tail
(10K steps ≈ 35K+ turn marathons) that the 4B over-invested in. Raising the
cap would not help the mean. Frontier unchanged but sharper: make descending
profitable (fresh floors > dried farming radius); understand the 9K-turn
death wall (food vs attrition).

**SCHEDULE x DOSE GRID COMPLETE (2026-07-29 12:25, all 250M gated
floor-reward, seeds 207-211):**
- two-phase 20→40 @0.5%: 6063±448 (ceiling 6673 = 250M RECORD; floor 5465)
- two-phase 20→40 @1.0%: 6018±208 — clusters MERGED (dose-before-cutoff
  controls strategy polarization; no stars, no duds)
- two-phase 10→30 @0.5%: 6047±388 n=4 (ceiling 6626; 1 segv sub + 1 livelock)
- two-phase 30→60 @0.5%: 5882±382
- (fade-to-end refs: a40 6115±90 old-reward; fr fade a40 ~6242/6022 n=2)
VERDICT: all schedule shapes statistically level on MEAN (~5900-6100); the
real knob is VARIANCE STRUCTURE: clean-phase @0.5% = high-ceiling lottery
(polarizes farmer-vs-explorer commitment at the cutoff); @1% or fade-to-end
= consistent ~6000-6100. The ε tail is a strategy-diversity regularizer, not
just rent. Schedule tuning is now EXHAUSTED as a mean-lever — remaining
levers are economy/capability (altar-ID conversion, death wall, depth).
Livelock #3 (tpa_s209) watchdog-killed in 12 min; kill exit 137 not
substituted (n=4 arm) — future drivers: treat 137 as substitutable (done in
altar chain).

**DIR-ε ROUTING FLOOR (2026-07-30, direps1 — the state-level extension):**
PUFFER_DIR_EPS mixture on the LAST head (dirs), same anneal as verb floor,
implemented in pufferlib.cu (dormancy recert PASS). At 0.005 + SHOPBUY: mean
6185±377 (+70 vs a40, +215 vs mechanism-only shp arm 5970±219). **Durably
fixed the browse stage ARM-WIDE**: bare-policy probes (ε off) show quotes
~4.5/ep on BOTH probed seeds vs champion 0.00 — the wander floor permanently
reshaped the walking distribution. s209 scored 6728 (best-ever 250M;
+497 vs arm-mate under same-instrument probe) but it's a BETTER CORE BASIN,
not a behavior adoption: its training-telemetry pays 0.159 / reads 2.55
were TRAINING-TIME ARTIFACTS (mixture actions + window lag) — bare-policy
pays ~0.001, reads ~0.4, same as arm-mates. **METHOD LAW: training-summary
verb telemetry near/after anneal CANNOT attribute behavior; only matched
bare-policy probes count** (C demo port also suppresses marginal verbs —
fine for routes/score, not verb forensics; GPU probe is the instrument).
PROBE BIAS (user-caught): fixed-NROLL vec probes cold-start (short episodes
complete first) AND censor in-flight longs at cutoff → completed-episode
mean biased LOW on a right-skewed score dist; paired A/Bs fine, absolute
levels understate. Fix = first-K-episodes-per-env with no cutoff; measured
small (+64) at NROLL=400. **BIGGER probe hazard — STATE DRIFT (dose-response on 1B champ). FINAL
NUMBERS = STEADY-STATE all-completed means (first-2-per-env comparisons
are contaminated by a ~−400 COLD-START penalty — the policy is adapted to
warm mid-window starts, so clean-zero episode starts are themselves
off-distribution; this masked memory effects in early-window comparisons):
wipe@8=6783±139 (−731), @16=6961±140 (−553), @64(training)=7514±87
(≈ train-final 7473 ✓), @256=7464±148 (≈0), never=6913±142 (−601; paired
eps3-40 estimate −500±130, onset ~3rd carried episode, flat to ep40) +
read-spam 6-20x (Q1 0% → Q4 99%). **CHAMPION USES ITS FULL 64-STEP WINDOW
(shorter wipes cost 550-730) AND NOTHING BEYOND (256≈64) — memory is
ceiling-limited by wipe semantics, NOT by task/arch → longer trained
windows (5c carry/horizon-256) plausibly buy real capability.** Probes
MUST wipe (probe_armor.py: reset_state=True default; HZN/RSTATE knobs).
Stock pufferl eval()/match() = carry-forever + horizon=1 = the corrupting
regime (upstream flag). Training semantics source-verified: state zeroed
top of EVERY rollouts() call (=horizon steps, all envs, never episode-
aligned), no done-masking, new episodes inherit dead episodes' state
within a window. **UPSTREAM 5c (PufferAI, HEAD 67a69341 — our fork ports only its FIRST
commit) has EPISODE-ALIGNED CARRY SEMANTICS: zero_term_state kernel (state
zeroed per-env at terminals every step), carry across rollout boundaries
(reset_every_horizon=0 in its nethack.ini), initial_states snapshots so
TBPTT segments init from true carried state (horizon 256 = gradient
truncation, NOT memory wipe). Full-episode memory, clean resets. Our
champion's ≤16-step vestigial memory = plausibly rational adaptation to
our unaligned-wipe semantics. PORT CANDIDATE (src/pufferlib.cu+bindings.cu,
gate-able under reset_every_horizon knob, upstream code as reference);
co-adapted 5c hypers (lr 0.0022/ent 0.10/clip 0.2/γ 0.99816/horizon 256)
say the A/B wants sweep support.** Unbiased champion eval (first-2-per-env, n=1024, matched
semantics): 7108±354 med 5873 ≈ training-final 7473 within CI.** Episode
decomposition: rate RISES with lifespan (0.72 d1 → 0.95 d10 → 1.02 top-1%,
compounding returns to survival); bottom 2 deciles = infant mortality
(turn ~1400, dlvl 2, XL 2.7, 44% trap/poison + dwarf burst, food-irrelevant);
top decile dies at 21.6K turns 33% fainting (food clock); truncation trivial
(2-5%) even in top 1% — cap raise worthless. s209 "reads" = spellbook
re-memorization + junk, no scroll economy. Instrument ladder for 1B champ: train-final
7473 / vec probe 6903 (biased low) / C demo train-sem 4533 / episode-sem
3976 — port forward-pass drift dominates the demo gap (needs re-goldening);
demo state modes: NH_STATE_MODE=train mimics training's 64-step wipes
(reset_state=True zeroes rollout state every iteration, NEVER on done →
trained policies have max ~64-step memory; reset_state=False A/B = open idea).
Shop funnel status: enter ✓ (habit, 0.9/ep demo) → browse ✓ (4.5 quotes/ep
durable) → afford-mask ✓ → CHOOSE PICKUP = still absorbing for every seed.
floor_eats +40% in 3 seeds (training-window; unverified bare). Prices ARE
observable (message text + gold blstat + affordability mask bit in obs).

**THROW THREAD (2026-07-31):** 2B seeds forked on throw adoption (5-21/ep);
causal mask ablation (eval, per-ckpt on/off, steady-state probes): throwing
worth ~18 pts per throw/ep (heavy thrower −370 when blocked) — buys score
RATE not lifespan. Target-gate (THROW legal only with non-pet mon on 8-ray
≤8 tiles, NETHACK_THROW_GATE, dormant in tree): eval tax on mature throwers
−70/−120 (v1 misses invis-marker/warning/detect glyph targets — legit
blind-throws exist; NO target-leading, throws resolve instantly); training
arm NULL 6107±369 vs 6114±90 with adoption SUPPRESSED (two 0.0-throw seeds).
**LAW: legality gates and ε-floors are ANTAGONISTS in training — a context
gate on a coin-verb blocks the floor's sampling exactly where adoption must
be seeded. Gates OK for always-useless contexts; never for coin-verbs.**
**AIM-ASSIST RESULT (2026-07-31, throwaim1 — LOCK-IN CANDIDATE): env-side
throw redirection (NETHACK_THROW_AIM: chosen ray empty → nearest target ray,
gate-v2 accept-set, APPLY-digger precedent) = exposure-preserving fix:
6293/6536/6848/6282/6956 → mean 6583±311 vs 6114±90 = +468, 5/5 positive,
TWO all-time 250M records (6956!), throws uniform 23-28/ep — LOTTERY CLOSED.
RECIPE: exposure (ε) + mechanism + CLEAN CREDIT (auto-aim) = universal
adoption; the payoff-noise of unaimed throws was the coin-flip all along.
WIELD dead-verb mask (deadmask1): NULL +20 (6135±90) — single-verb ε
dilution unmeasurable; action-count concern retired.**
Also: verb-ε per-verb exposure = ε/K(legal) — adding actions dilutes the
floor; ours/5c sweeps both landed loose-clip+low-ent (ours clip 1.0 = range
BOUNDARY, suspect; 5c interior 0.48, ent 0.019, range caps 0.9/0.1);
anneal_ent_coef never swept by either lineage = the open ε-free cell.

**THROW DIR-MASK (2026-07-31, the user's true design): shadow mask row** —
MY_ACTION_MASK += NETHACK_NUM_DIRS; env fills throw-dirs (target rays, v2
accept-set; all-1 if no target = verb exposure preserved; dormant = exact
dirs copy); sampler+PPO fwd/bwd shift mask base by A for the LAST head when
verb==11 (chess-safe via mask_stride>logits-width check). **STRIDE LANDMINE
FOUND+FIXED: PPOKernelArgs hardcoded mask_stride_n/t from A_total (logits
width) — correct only while mask rows == logits rows; growing the mask row
misaligned every minibatch mask row after the first → PPO trained on garbage
legality → policy dead from update 1 (recert 2.04!) while rollout sampling
(correctly strided from shape[2]) looked innocent. Fix: stride from
mb_action_mask.shape[2]. UPSTREAM-RELEVANT (shared ancestry). Bisect method:
10M smokes discriminate (broken 0.27 vs healthy 122.379) in 90s.** Demo
gotcha: nethack.c allocs its own mask — must include shadow width. Recert
PASS bit-exact post-fix. **ARM REJECTED, KILLED EARLY BY USER at n=3**
(s210 mid-run, s211 never ran): clean seeds 6368/5243/5918 mean 5843 —
below a40 6115, floor 750 under any depth-delta sibling arm's worst.
**CRATER MECHANISM (curve forensics, td_s208 vs its aim twin): throw-
escalation feedback loop** — throws 15→34→**47.7** (peak 173M) →40 while
wears collapsed 14.8→3.4 in lockstep and game_time cratered −2800 vs twin;
aim twin stable 17-32 band; good seed s310 flat ~26 never escalated (1-in-3
instability). Mechanism: dir logits are decoded in PARALLEL with the verb
(can't condition on sampled verb) → multi-target throw steps write monster-
relative aim gradients into the head that steers walking → monster-seeking
walk drift (movement MECHANICS unaffected — valid_moves/illegals normal;
STRATEGY contaminated; Elbereth-panic 30+ vs twin 4-11) → more throw
opportunities → more aim gradient. Under aim-assist the conflict never
existed: optimal shared-head policy = pure movement, env supplies aim.
NOTE: the action mask is NOT an obs feature (sampler/PPO only). PREDICTION
for pervdir (#105): escalation mode should vanish (aim gradients
quarantined in THROW's own head); if it still escalates, the loop runs
through the verb head → constrain the mask itself (nearest-ray/range).

**PER-VERB DIR HEADS (queued 2026-07-31, group pervdir1, task #105):** user
design — split the shared dir head into 6 per-verb dir heads (MOVE RUN KICK
THROW ZAP APPLY), NUM_ATNS 14→19, logits/mask 690/698→730/730. Rationale:
under a shared head, throw-aim credit and movement priors contaminate each
other (aim-assist's garbage-attributed dir logprob was consumed into PPO on
every throw; movement gradients dominate throw aim). Per-verb heads +
head-gating = each dir head trains only on its verb's steps; THROW's own
mask row carries the target rays NATIVELY (shadow row + kernel verb==11
conditionals go dormant — all three sites width-guarded, mask==logits width
again, stride-landmine class gone). Impl: netlib.h nethack_dir_head() map +
NETHACK_DIR_HEADS; nethack.h mask rows (wall-base ×6, THROW row under
NETHACK_THROW_DIRMASK) + c_step per-verb dir read; binding.c sizes/consume;
nethack.cu NH_DIRHEADS=6, NH_DEC_LIN 31→71, NH_DEC_PAD 32→72; demo mirrored
(19 heads, DEMO_DEC_PAD 72 — old checkpoints fail its weight-count assert,
expected). Arch change ⇒ NO bit-exact recert vs 6165.71 possible — control =
td arm itself (same NETHACK_THROW_DIRMASK=1, single variable = head
structure). Validation = build-after-td-chain + 10M smoke (healthy ~100class
vs broken 0.27-class) then 5×250M. Scripts pervdir_phase1/2.sh in
scratchpad; full tree patch banked (tree_with_pervdir.patch). DO NOT rebuild
while a chain is mid-flight — later seeds pick up the swapped .so.
**LANDMINE #2 FOUND+FIXED (2026-07-31): `MAX_ATN_HEADS 16` (kernels.cu:79)**
— PPO kernel's per-head STACK arrays (head_logsumexp/entropy/act/used,
pufferlib.cu ~982) are MAX_ATN_HEADS wide; 19 heads silently overflowed
local memory → garbage gradients while ROLLOUT SAMPLING stayed perfectly
legal (0/20006 mask violations under NETHACK_DEBUG_ACT probe — new env-var
knob in c_step, logs verb,slot,dir,maskbits, skips reset transients). First
smoke: score 1.17@10M, illegal RATCHETING 1.2→8560/ep, eplen→10K cap 91%,
applies 1657/ep = policy LEARNED the freeze exploit (mask-legal prompt-loop
actions cost no game time, dodge death, truncate at cap) because real play
couldn't be learned through corrupt gradients. Same family as the stride
landmine: kernel-side hardcode dormant until the env grows; UPSTREAM-
RELEVANT. Fix: 16→32 + runtime guard (num_atns > MAX_ATN_HEADS → exit(1))
at PPO args site. Post-fix smoke 120.06@10M ≈ old-arch 122.4 ✓. DEBUG-probe
gotcha: first instrument counted episode-first steps (action sampled from
pre-reset obs vs post-reset mask) as fake violations — 4.7%≈1/22 uniform;
always skip was_reset/length<3 rows.
**PERVDIR ARM RESULT (2026-07-31 19:27, pervdir1, 5/5 clean, zero crashes):
6403/6281/6408/6427/6984 = 6501±276 — pv_s211 6984 = NEW ALL-TIME 250M
RECORD (beats aim 6956, honest aim, no env crutch).** vs aim 6583±311 =
statistical TIE on mean; vs a40 +386; vs td shared-mask +658. ESCALATION
MODE DEAD: s208 recovered 5243→6281 (+1038), all throws 23-33 stable band,
ALL FIVE long-lived (gt 9092-9332 — no wanderer dud; honest dir credit
seems to also kill the farm-vs-wander basin variance: 4/5 seeds within
±70, s211 the record outlier). Record recipe (s211): throws 32.9, wears
8.2, min_ac 0.62, engr 21, gt 9295 = farm-tight+armor+throw package.
PROMOTION CANDIDATE over aim-assist: same mean, honest weights, record
ceiling, cleaner infra (mask==logits width, shadow machinery dormant).
Checkpoints: checkpoints/nethack/<wandb-id>/ (pv_s211 = wb3fi0u6).
Ablation probe (s211 ckpt, bare ε=0, NROLL=600): mask-on 6860 / mask-off
6622 = **−238 with throws 32.5→44.3** vs aim-assist's −357+total spray —
the THROW-dir head owns the aim; mask trims marginal empty-ray throws.
**USER PROMOTED TO CHAMPION 2026-07-31 + committed; PUFFER_HEAD_GATING and
NETHACK_THROW_DIRMASK flipped DEFAULT-ON (=0 disables), bit-verified
(smoke 120.05810546875 identical flagged vs unflagged). Champion recipe = ZERO
FLAGS (2026-07-31 later: eps 0.005 + anneal-start 0.4 ALSO defaulted in
code, bit-verified 120.05810546875 flag-free; =0 disables each). PROBE
GOTCHA: bare-policy evals must now EXPLICITLY set PUFFER_VERB_EPS=0
(probe_armor.py has setdefault('PUFFER_VERB_EPS','0')).
NEW RECERT REFERENCE: pv_s207 = **6403.1904296875** (seed 207, ZERO
flags, explicit --train.total-timesteps 250000000; recert_defaults_s207
reproduced bit-exactly 2026-07-31). Dead reward coefs DELETED (starve_coef,
ac_hold_coef, first_wear_coef — full plumbing: ini, binding, struct,
reward lines), bit-verified via smoke 120.05810546875; old 6165.71/6241.60 constants are
STALE (pre-arch-change). Probe-result parsing gotcha: backend.log() returns
NESTED {"env": {...}} keys, not flat "env/score".**

**SEARCH20 IS LOAD-BEARING (2026-07-30, masked-SEARCH20 ablation):** masking
the 20-turn macro (NETHACK_MASK_SEARCH20=1, env-var-gated mask in tree) is a
huge consistent LOSS: champion hypers s207=4140 (−2026); γ-corrected arm
(--train.gamma 0.9989 ≈ same per-TURN discount at the new ~1.7 turns/step)
n=3 = 4204/4555/4535, mean 4431 vs 6153 baseline (−1722). γ fix restored
LIFESPAN (7-7.9K turns, trunc→9%) but the farm NEVER re-emerged (single-turn
searches stuck at ~130-146/ep vs ~8000-turn-equivalent champion farming);
policies pivot to diving (floors ~7.2) at rate 0.59/turn vs 0.78. READING:
the macro-action is a CREDIT BUNDLER — one 13-turn commitment makes
sit-and-farm discoverable/reinforceable as a unit; 13 chained single-turn
searches never line up under exploration noise. Inverse of the naive
credit-granularity hypothesis. Timescale gotcha for any step-semantics
change: γ/λ/horizon/ε-dose are all per-STEP, swept at ~4 turns/step —
removing search20 silently crushes the value half-life 3x (0.99737 →
400-turn half-life). Hand corrections can confirm but not refute; a fair
trial needs a sweep. VERDICT: search20 stays.

**FORENSICS ARM + VARIANCE REVISION (2026-07-29 15:28):** fade-to-end
floor-reward n=5: 6242/6289/6133/5250/6135 = 6010±430 — vs two-phase 6063±448:
DEAD TIE on both mean AND variance. REVISES the grid conclusion: the schedule
was NOT the polarizer — **the FLOOR REWARD is** (old-reward fade arms were
±90-130; both floor-reward schedules are ±430-450 with farmer/explorer duds).
The strategy-tension variance follows the reward, not the schedule.
**Death forensics x6 policies: spike fraction 0.59-0.62 EVERYWHERE** (hp_t5
~0.68, hunger 0), invariant across schedule/seed/strategy — burst-death is
structural. Next: checkpoint-eval death sweep across the whole policy zoo
(incl 4B turtle) for the search20-vs-spike correlation test (queued after
altar 2x2). Gate-hygiene lessons: wandb summary sync races false-fail gates
(retry queries); never pgrep a pattern contained in the monitor's own cmdline.
