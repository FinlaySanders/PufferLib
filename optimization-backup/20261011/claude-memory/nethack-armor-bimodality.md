---
name: nethack-armor-bimodality
description: "Armor: causally worth ~600-680 within a wearer policy (WEAR-mask ablation), but seed/basin quality spans ±600 between policies, hiding it from cross-seed reads. Bimodality = real points lost."
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-06T06:49:04.245Z
---

Armor-use investigation, resolved 2026-07-27 in two stages. My first conclusion
("armor ~score-neutral, marker not cause") was WRONG — corrected by the user's
pushback and the eval-time WEAR-mask ablation.

**DEFINITIVE — eval-time WEAR-mask ablation** (spell5 final checkpoints, each
evaluated normal vs NETHACK_MASK_WEAR=1, ~50M steps ≈ 21-30K episodes/arm,
SE ≈ ±20):
- s44: 4746 → 4069 = **-677** (wears 5.60)
- s46: 4695 → 4063 = **-631** (wears 5.05)
- s45: 5480 → 5263 = **-217** (wears 4.53; late adopter, also has CAST route)
- s43 control: 5310 → 5257 = -53 (wears 0.32) ✓ method validated
- s73 control: 4941 → 4956 = +15 (wears 0.03) ✓
**Armor is causally worth ~600-680 to a committed wearer policy.** Channel:
unarmored takes damage ~10% faster per turn (same total damage, shorter life:
game_time -10%) → less farming → less score. Damage TOTALS look flat — the
rate is what moves; this is why the first probe read missed it.

**The synthesis (both prior views were part-right):** armor adds ~600 WITHIN a
policy; seed/basin quality spans ~±600 BETWEEN policies (s43 non-wearer 5310
normal-arm beats s44 wearer 4746). Cross-seed comparisons (n=5 groups, flip
tables, pooled +164) are blind to armor because basin noise is the same size.
The gate1 five (425-433: perfect wears↔score ordering) were seeing the real
effect; the spell5 five (ρ≈-0.1) had it swamped. Non-wearing seeds leave
~600 on the table → fixing the wear bimodality IS worth real points.

**Still true (from the category probes):** opportunity not the issue (WEAR
legal 60-67% of steps); knowledge not the issue (every policy wears only
Monk-safe helm/boots/cloak/gloves, suits+shields ~0 everywhere); difference is
purely verb-head propensity (3.7-4.6 vs 0.03-0.29 wears/1K legal steps);
~50% of wears are AC-neutral swap churn. Non-wearers sit at the bare-Monk
min_ac ~3.9 floor; wearers reach 0.8-2.4. min_ac ≈ binary basin classifier.

**Gating enabled wearing:** pre-gating record: 0/42 completed runs wear
(incl. all-time bests 5685/5627/5570 armor-less); gating era: 6/10. Plausible:
gated slot-heads sharpen from few samples instead of drowning in all-step
entropy/gradient noise. (This also explains why armor "arrived with" the
gating score jump — common cause across eras, causal within.)

**Probe infra gotchas:** short eval windows have survivorship/length bias
(long= best episodes never complete → biased AGAINST long-episode policies);
use ~50M steps (100K/env) so tail bias ~2%. Ablation flag: mask_wear on env
via NETHACK_MASK_WEAR (binding.c my_init getenv → nethack.h compute_mask
mask[WEAR]=0), opt-in, dormant otherwise. Per-category wear logging
(wear_suit..wear_shirt, wear_noac, wear_opportunity) in Log — log-only,
training-neutral.

**Next levers (armor consistency now worth ~600):** make every seed a wearer —
WEAR auto-target macro (slot choice automated, verb learnable), per-head
entropy floor on the gated verb head, and/or held-AC potential reward. Fresh
10-seed A/B running (fresh-spell5 / fresh-gate5, seeds 201-205) measures how
often the basin lottery drops the 600. fsp_s201 segfaulted (exit 139, no panic
msg — deterministic per seed, substitute seed 206). Also: verify entropy
fingerprint gated≈0.5 vs ungated≈9-10 to check gating was really on
(caught a mislabeled gate0 run this way: worldly-oath-421).

2026-08-05 CORRECTION — BIMODALITY NEVER WENT AWAY: I claimed "armor is no longer
bimodal" off 4 runs that all happened to wear (5.8-9.6/ep). Wrong: wandb wears across
big groups still spans the full range — reward-abl n=100 0.16-16.28, shop-econ n=9
0.01-17.14, newstack n=21 0.79-12.58. The coin flip is intact on the current stack. n=4
CANNOT detect a basin-odds change in a quantity that noisy (needs ~8-10/arm). Same n=4
trap as the rc0_xp episode. ALSO: eps is NOT what makes rare verbs cook — the mixture
m=(1-eps)p+eps/K is an UNBIASED estimator of the on-policy gradient (frequency boost
eps/K x attenuation (1-eps)p/m cancels exactly to p*grad-log-p), so eps shifts variance
and critic coverage, NOT the expected update. My "gradient dead-zone" story was wrong.
Zap adoption is itself bimodal and flips independently of eps (noeps s208 took off to
4.0/ep, s210 stayed at 0.6; both eps-on twins flat).

2026-08-06 ac_coef IS THE WIN — CERTIFIED AT TWO BUDGETS. Restored the pruned
ac_coef potential term (t = ac_coef*(prev_ac - ac), telescopes to
ac_coef*(ac_start - ac_end), non-farmable) at 1.0. Certified paired deltas:
250M s301 +130, s302 +497; 1B s401 +804, s402 +55. Mean +372 +-174 SE, 4/4
positive but spread 15x — suggestive, not conclusive (sign test p=0.125).
1B ac arm 8086.6/7717.2/7494.7; controls 7282.3/7662.3 (mean 7472) which
REPRODUCES the sc1b baseline 7393+-229 => comparison is anchored. ac1b_s401
8086.6 is level with the all-time-best 5c-1b-carry cohort (8055 top-3 mean).
MECHANISM: min_ac 0.04-0.53 in ac arm vs 0.82-1.24 controls, against a prior
population pinned at 1.1-1.3 at every budget — the term reliably moves the
thing it targets. BUT at 1B game_time barely moves (+292/-95), so the gain is
NOT "armor -> longer life" as I claimed; more likely less damage per fight =
more fighting inside the same lifespan. Note ready2 (readiness obs feature)
showed an 800-pt spread between its own two seeds at 250M — armor basin still
alive and still the dominant noise source in every read.

2026-08-05 SEED-MATCHED PAIRS (group epspair, same binary both arms, killed at 2 of 3
pairs once the answer was clear). Training tails, mean of last 30 rows:
- s301: eps0 6138 (wears 5.56, ac 3.0) | epsON 6590 (wears 8.26, ac 3.0) = -452
- s302: eps0 5186 (wears 0.53, ac 4.7) | epsON 6329 (wears 7.90, ac 2.8) = -1143
s302 is the first clean causal pair on this question: SAME seed + binary, eps0 lands in
the basin and epsON does not, wears/ac/score all moving together. Basin tally at 250M:
1/5 in eps0, 0/3 in epsON. So eps=0 does NOT restore the July regime (97-100%
non-wearers) — it restores a ~20% tail, ~-1100 per occurrence = ~-220 expected, which
alone justifies keeping verb_eps=0.005. NOT a contradiction of the unbiasedness math
above: eps shifts VARIANCE and critic coverage, and which basin you land in is exactly
a variance-driven outcome. Still open: 2 pairs can't separate a 20% rate from 10%
(needs ~8/arm), and no 1B data where eps runs 4x longer in absolute steps.
