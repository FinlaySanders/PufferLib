---
name: nethack-collapse-anatomy
description: "Full collapse forensics (2026-08-07, 217+24 run census): early squeeze universal+harmless, acute late collapse = self-healing optimizer accident, NO chronic 2B erosion; ε-rebirth theory refuted (softmax soft floor reseeds)"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-07T16:12:40.524Z
---

Collapse forensics over 270 jsonl logs (217 runs ≥180M censused; 24 long runs ≥600M). Three distinct phenomena, previously conflated:

**1. Early consolidation squeeze (20-44M) — universal transient, NOT the lottery.**
Delayed-payoff family (throw/wear/cast/engrave/drop + PRAYER, a 6th member) undershoots
its own final equilibrium (trough <0.35×late rate) in 85-95% of runs; immediate verbs
spared (eats 26%, quaffs 40%). 190/217 runs undershoot 4+ family verbs. Loosely
synchronized (median within-run trough spread 18.8M): drops/prayers ~26M, wears 29M,
throws/casts 32M, engraves 38M. Recovery ordering = difficulty: wears/drops ~35M,
throws 45M, engraves 61M (slowest; stays dead in ~2/4 modern seeds). Mechanism:
softmax winner-redistribution when core competence (move/fight/eat) crystallizes —
entropy 2.4→trough ~0.4-0.7 at 36M, then REBOUNDS as verbs rebirth.
**Severity does NOT predict final score** (17 cohorts, pooled pairwise 54% = coin flip)
— everyone squeezes, everyone mostly recovers by 250M; final equilibrium rates are
what correlates (throws_rate +0.53 etc.), not transient depth.

**2. ε-rebirth theory REFUTED (causal, from noeps/epoff logs).** verb_eps=0 runs rebirth
everything anyway (throws→26/ep, engraves→18-29/ep): the softmax soft floor (entropy
bonus keeps logits finite, p~1e-4 × 250M steps = thousands of samples) reseeds without ε.
ε's real value = recovery SPEED/reliability on hard verbs (epoff wears rec 31/58/105M,
one dead at 0.5/ep vs epon 45/57M; paired A/B ε worth ~+800). Insurance on rebirth
quality, not a life/death switch.

**3. Acute late collapse — rare, instantaneous, self-healing optimizer accident.**
Only 3/24 long runs (fh1b_s502@411M, sc1b_s404@470M, sc1b_s407@265M). s502 microscope:
entropy 0.28→0.042 and score 5,800→75 in 0.4M steps (a few updates), EVERYTHING dies
at once (valid_moves 1400→195, all verbs→0) = total policy degeneration, not verb
pruning. Entropy overshoots on recovery (0.42 vs 0.30 baseline), full recovery in
~2.5M steps; s502 then set the all-time record (8,748). Pre-crash signature: entropy
wobbles UP (0.35-0.42) 1-2M before the fall. Cost ≈ 3M steps ≈ nothing at 1B.
Trigger unconfirmed: loss/kl and loss/clipfrac log flat 0.000 in ALL runs (broken
channels) — can't see ratio blow-up. 2/3 events shortly after ε-anneal start (400M);
n too small to convict.

**4. NO chronic 2B erosion.** twob_s601-603 climb monotonically the whole 2B
(4.2-4.7K→7.0-7.5K), verbs/depth/game_time all stable-or-rising, entropy settles
0.16-0.22. The "2B plateau" is diminishing returns, not degradation.

Implications: cohort entropy-watch = log acute events, don't panic (self-healing);
the anti-collapse lever is NOT ε-floor-forever (chronic risk overstated); fixing the
dead kl/clipfrac logging (train-side, [[pufferl-off-limits]] — propose patch) is the
one instrument gap blocking the acute-trigger diagnosis. Squeeze-era env gates (make
early verb use honest, e.g. throw-gate) remain the only lever that moved a specific
verb's squeeze — tg gate v2 SPLIT verdict: -996 on strong seed (s304, never deep-dipped;
gate only removed exposure) but +489 on weak seed (s307 6,960 vs 6,471: skipped the throw
dip entirely, throws never suppressed, transfer probe +77) — mean-negative,
variance-increasing, EXCLUDED from cohort env; see [[nethack-bimodal-verbs]] LAW.
Related: [[nethack-tempo-hygiene]], [[nethack-env-setup]].
