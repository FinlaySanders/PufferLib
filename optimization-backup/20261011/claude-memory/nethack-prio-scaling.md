---
name: nethack-prio-scaling
description: "CLOSED 2026-08-22 - prio DROPPED (user decision, maintainer frame: tuning-context not mechanism); 5c finding stands as science; port dormant at alpha=0"
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-22T06:44:50.919Z
---

**CHAPTER CLOSED (user decision, 2026-08-22)**: prio dropped completely.
Rationale: maintainer says 5.0 >= 5c everywhere -> gap = tuning context;
prioritization-proper on 5.0 = +443 n=1 / ~0 s312; 0386 does not need it;
5c's +1,540 = "helps a stack tuned with prio on" (never tuned 5c at
alpha=0 - necessity unshown). Survives: the 5c paired finding (science),
the loss-semantics lesson (configs are tuned to an advantage-scale
context; never transplant across it), the v3 port (worktree, alpha=0
default = inert, patch saved). Cancelled unfinished: psamp 2x2
(prio_norm=0 arms), prio0_1b_s313, inc50p3_1b_s313. The 5c champion
keeps its native prio untouched. Historical record below. EPITAPH (user insight): prio was a
short-horizon-era mechanism — priority = sum|adv| over a segment, so
resolution dilutes as horizon grows (sharp at h=64, blurred at h=512);
MinGRU made long horizons cheap, horizons grew, the design context
dissolved ("least cleaned... better method in 5.0" comment). Fits: the
one big prio win (5c incumbent) is h=128, the shortest-horizon config in
the zoo. No prio x horizon factorial was run.

2026-08-20 paired ablation (wandb encoders group `prio`, fingerprint-gated
binary, config diff = prio_alpha only): incumbent config, `prio_alpha=0`
vs 0.598, same seeds as idemb1b refs.

| cell | s311 | s312 |
|---|---|---|
| ON @1B (idemb1b) | 7,035 | 6,929 |
| OFF @1B (prio0_1b) | 5,189 | 5,695 |
| paired diff | −1,846 | −1,234 |

OFF @217M: 3,497/3,804 vs panel 3,789 → null (−139). Signature: free at
short budget, ~−1.5K at 1B ≈ half the incumbent's 217M→1B climb. Matched
curves to ~350M; ON's late surge (>600M) doesn't happen without prio.
OFF kept full ent 0.0229 + ε → entropy alone is NOT sufficient for
scaling; prio converts rare-event advantage into gradient late (β<0.61
annealed = biased objective, not just variance reduction). Caveat: ON n=8
has a low tail (5,513/5,327) overlapping OFF; paired same-seed diffs
carry the claim; third OFF seed would tighten.

Context that led here: time-scaled sweeps always zero prio+entropy
(anewhope3 winner α=0.108/ent 0.0014; okitstime 0331 ent 0.0026, certs
winner's-cursed ~+470: native rerun 3,915 vs cert 4,384) and their
winners never scale (swp_dt 4,077@337M → 3,711@1B). Incumbent = ohyeah2
sweep run 0209 (full-hyper space incl prio 0-1 → chose 0.6; val0209 n=4
~9,006@236M monk era; "217M screens" = 0209's chosen budget).

**PORT SHIPPED 2026-08-21 (v3, worktree /puffertank/pufferlib-50, patch
scratchpad/prio_port_50.patch ~600 lines)**: adv-prepass(frozen V) → CDF
→ per-mb sample+gather (incl. recurrent states) behind prio_alpha>0;
slice path bit-identical at α=0 (hash 8d8082a0 across all 3 versions).
5.0 gotchas solved: whole-epoch cudagraph → anneal_beta via device ptr;
priorities from frozen snapshot while 5.0's live-GAE... **THE BUG ARC**:
v1 (live per-mb GAE kept) −434@200M — prio-hot rows' targets chase
themselves; v2 (frozen targets, no norm) −1,095@300M; v3 (frozen +
**per-minibatch advantage standardization** = the piece 5c had in
ppo_adv_mean_var that 5.0's loss lacked) **+298@300M, +859@1B**:
inc50p3_1b_s311 = 5,008 vs no-prio 4,149 (v1 3,460). 5.0+prio ≈ 5c
no-prio (5,189); remaining −2K to 5c full = drift residue + prio
shortfall (+859 vs 5c's +1,846). LESSON: prio needs post-sampling mb
standardization or the PG step inflates as the CDF sharpens.
Transplants: inc50_1b s311/s312 = 4,149/4,256 (was called "drift −1,240";
REFRAMED 08-22 per maintainer input (5.0 ≥ 5c on every env): it is a
TUNING-CONTEXT MISMATCH — 5c configs are tuned for standardized+frozen
loss semantics; matching semantics (α=0.01 arm) recovered +416; residual
~−600 presumed further context mismatch, not trainer deficiency. Judge
5.0 only with natively-tuned configs; next: rewards+prio sweep seeded on
0386 ON 5.0).
Acceptance pair: inc50p3 5,008/4,461 → +859/+205 (mean +532), s313
running. **DECOMPOSITION + LANDMINE (08-22 night)**: inc50a01 (α=0.01 ≈
no prioritization, v3 loss path) = 4,565 → the LOSS PATH
(standardization+frozen targets) carries ~+416 of the incumbent's gain;
prioritization adds ~+440 on top (s311). **0386+prio CRATERS: 1,665 /
1,109** (vs 5,560 without) — 5.0-sweep-tuned configs expect RAW
advantages; v3's standardization rescales their effective PG step →
blowup. The port's α>0 path imposes 5c loss semantics: safe for 5c-tuned
configs, breaks 5.0-tuned ones. Fix candidates: per-config lr rescale, or
a flag to disable standardization. ε findings same night: 0386 without
ε craters to 3,991 (−1,570 — ε load-bearing for score on 5.0);
mine50+ε depth 10.78 vs 10.60 (mild positive).
See [[nethack-env-setup]], [[no-checkpoint-forking]],
[[nethack-5.0-scaling]].
