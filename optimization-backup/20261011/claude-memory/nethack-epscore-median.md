---
name: nethack-epscore-median
description: "NH_EPSCORE per-episode score dump + VERIFIED arch-era fingerprint table (815dd8e4=15589568 / pre-CAST drift=15619520 / CAST-era=15696576) + era worktrees; medians: ac1b 6472/8004, rcminf 5630/7123"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-06T18:04:37.828Z
---

**NH_EPSCORE hook** (2026-08-06, in working tree): env var = output path; nethack_add_log
appends "score max_depth how" per episode. Inert unless set. Median/percentiles need it —
all other logging (wandb, eval TUI) is means-only.

**Arch-size fingerprint table** (checkpoint bytes → era), each row VERIFIED by loading:
- 15,589,568 = commit 815dd8e4 (Aug 1 "wandb integration"), clean committed tree —
  reward-abl era (rcminf/rc0_* seeds 207-214). Verified by BIT-EXACT recert (7122.821).
- 15,619,520 = pre-CAST Aug 5-6 working tree (c6ddd303 + drift) — ac1b/ctl1b/carry0/
  noscarry. NO commit matches it; use the reconstructed wt_precast (verified 8003.8 vs
  certified 8086.6, ≈1 SE).
- 15,696,576 = CAST-era current tree (spell obs + CAST verb + embedding) — castf/cemb/
  aa/zb/zbf onward.
- HEAD c6ddd303 (Aug 3 21:45) builds an arch that matches NEITHER checkpoint family
  (afternoon commits grew it past 15,589,568; ac1b-era drift moved past HEAD). The
  committed resources/nethack_weights.bin blob size is a DEMO layout, NOT a checkpoint
  size — never infer arch from it (that mistake cost a failed recert attempt).

SILENT-SHIFT LANDMINE: loading a BIGGER checkpoint into a SMALLER-arch binary does NOT
assert (fread fills and succeeds) — garbage policy, plays ~random (mean ~7). Same-size
different-layout ALSO loads silently and plays random. Only smaller-file loads assert.
ALWAYS gate cross-era loads on reproducing the certified mean.

**Era worktrees** (in scratchpad, each with epscore patch, own ./puffer): wt_815dd8e4
(reward-abl era), wt_precast (ac1b era), plus wtera.sh = the era-hunt ladder pattern
(probe 75s partial eval; wrong era asserts or scores ~0, right era scores thousands).

**Distributions** (n≈10K certified evals):
- ac1b_s401 (1B, mean 8004): median 6472, p10 1185, p25 3394, p75 10778, p90 16388,
  p99 30933, max 71481. Mean ≈ p60.
- rcminf_s214 (250M champion control, mean 7123 = lucky top of 8-seed cohort 6380±443):
  median 5630, p10 1136, p25 3037, p75 9666, p90 14656, p99 28134, max 61340.
Quote MEDIANS vs autoascend (their public numbers are medians).

**PAIRING DIES AT ARCH BOUNDARIES (2026-08-08):** any param-count change reseeds
init streams for every tensor — cross-era "same seed" runs are fresh lottery
draws, NOT matched pairs. Era-crossing comparisons must be unpaired cell-mean vs
family distribution (SE ~±220 at n=5 vs ±150 paired). Caught on the wobs cell:
apparent per-seed drift −78/−236/−647 was void pairing; proper read = null.
Also: NH_EX_RAW-class landmine — CUDA inlines its own copies of layout constants
(netlib's NETHACK_EXTRA_INTS vs nethack.cu NH_EX_RAW); every obs-layout change
must touch BOTH or all offsets shift (uniform gradcheck failure = the tell).

**2026-08-24 v51b_s701 (v5 record) PROPER STANDALONE CERT + PROTOCOL
FINDING**: burnin_games is a DEAD ini key in the pruned trainer (default.ini
has it; nothing reads it) — old-protocol burnin reproduced via NH_EPSCORE
dump slice (eval 14K/30K episodes, discard first 4000). Hook re-added to
nethack.h (env-var gated, inert; eval binary nethack_v5ce = NH_V5+hook).
CONVERGED standalone steady-state: mean 7,860±62 (windows 7847/7856/7868/
7857 — end-censoring is TINY, +22 from 14K to 30K), median ~4,450, p10 363,
p25 1,364, p75 10,776, p90 19,084, p99 47,887, max 157,935; depth median 2,
p90 6, max 29; 20% of episodes <1,000.
**INLINE CERTS ARE WARM-START BIASED +~1,000**: inline 8,919 vs converged
standalone 7,860 — the train-end eval counts long in-flight TRAINING
episodes (length-biased carryover), inflating the mean ~12% at this skew.
End-censoring (the fresh-start worry) measured negligible. ALL inline certs
share the bias -> cross-run comparisons stay valid; absolute means are
protocol-relative. Cold-start eval with NO burnin biases DOWN (7,501 at
10K) — the 4000-episode discard matters.

**2026-08-24 WARM-START BIAS IS POLICY-DEPENDENT — SCOREBOARD CORRECTION**:
standalone (burnin-slice, paired eval seeds) vs inline offsets: v5 1B
+1059/+615, v5 331M +477; noaux 1B +181/+110, noaux 331M +17. v5 runs
longer episodes -> bigger length-biased carryover inflation. CORRECTED
5c TABLE (standalone means): 1B v5 7,860±62 / 7,891±104 (Δseeds only 31!)
vs noaux 8,003±90 / 6,711±72 (Δ1,292); paired: s701 −143, s702 +1,180 ->
v5 1B edge +519±~650 NOT established at n=2. 331M s701: v5 5,046±60 vs
noaux 4,745±54 -> +301 real (was +761 inline). KEY NEW FINDING: v5
COLLAPSES SEED VARIANCE (both seeds same basin; medians ~4,400) while
noaux seeds split basins — v5's robustness may matter more than its mean.
Medians: noaux s701 5,129 beats v5 ~4,450 (v5 trades typical-episode for
tail). ALL cross-arch inline comparisons suspect when episode-length
distributions differ; recert standalone before claiming. 5.0 v550-vs-0386
inline gaps (+374) NOT yet recertified (5.0 era worktree lacks the EPSCORE
hook — port it). Eval binaries: nethack_v5ce (V5), nethack_labe (LAB
noaux). Standalone evals share the ini default eval seed pool -> paired.

**2026-08-24 CORRECTION — PRIOR ENTRY'S SCOREBOARD WAS WRONG (user caught
it)**: the standalone eval binary (nethack_v5ce) was built AFTER the
integer-octant sector edit, but ALL 5c fleet binaries (nethack_v5c etc.)
were built BEFORE it — the two schemes carve the same 8 wedges with
DIFFERENT LABELS, so v5ce fed trained policies a PERMUTED terrain radar
(-600..-900 pts; noaux has no terrain -> unaffected, which faked the
"policy-dependent bias"). Matched-binary (nethack_v5ce2, atan2 sectors +
EPSCORE) TRUE TABLE: v5 1B s701 8,753±106 med 5,384 / s702 8,378±102 med
5,074; noaux 8,003±90 med 5,129 / 6,711±72 med 4,560; 331M v5 5,424±57
med 3,438 vs noaux 4,745±54 med 2,854. Warm-start inline offsets UNIFORM
and small (+17..+181) — inline certs are FINE for comparisons. v5 1B
edge CONFIRMED bias-free: paired +750/+1,667 (mean +1,208 ≈ inline).
RETRACT: "variance collapse" + "median worse" + "policy-dependent bias"
claims from the mismatched binary. INCIDENTAL: scrambling the terrain
radar costs a trained v5 policy ~900 pts = direct evidence the terrain
branch carries real 1B value. verb_eps CLEARED (eval path ignores it;
evals bit-deterministic). LANDMINE RULE: eval binaries must be built
from the EXACT source state of the training binary — sector labels are
arch state; 5c tree KEEPS atan2 (matches artifacts), 5.0 port = octant
(its own runs consistent); reconcile at promotion.
