---
name: nethack-reward-ab
description: "Depth-delta vs floor-reward A/B verdict — depth-delta wins on variance, floor payment reverted"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-07-30T05:36:51.362Z
---

Descent-reward A/B (2026-07-29), matched seeds 207-211, champion knobs (gating, eps 0.005, a40):
- **Depth-delta** (`r += descent_coef*(depth-max_depth)`): group ovn-eps05-a40 = 6165.7/6215.6/6076.6/5980.3/6134.3 → **6114.5 ± 90**
- **Floor payment** (`r += descent_coef` per new unique (dnum,dlevel)): fr_s207+frf = 6241.6/6289.3/6132.8/5250.4/6134.9 → **6009.8 ± 430**
- Paired (floor−depth): +76, +74, +56, **−730 (s210 farmer basin)**, +1 → floor's small consistent edge is wiped by one crater seed in five. Floor payment *created* the farmer/explorer strategy bimodality without buying mean.

**1B validation (2026-07-30, b1-depthrew, a=0.2, seeds 401-405):** 6932/7371/7274/6985/7473 → **7207 ± 238, record 7473** (old record 6740). CAVEAT: floor 1B is n=1 — the other two long-1B runs CRASHED at 65M/170M (pre-hardening infra), their 2741/4359 are partial-run artifacts, NOT craters. Honest read: depth +467 vs the single floor point (~2σ), crater evidence is the 250M paired cell only. Depth scaling 6114→7207 (+1093); floor 6010→6740 (+730, n=1). death_spike still ~0.60 at 1B — combat-spike profile scale-invariant.

**Verdict: depth-delta is the default.** Working tree holds the revert (floor payment removed, `floors` still logged as metric; committed tree still pays per-floor — user to commit). No rerun was needed: the a40 cell predates the floor commit and forensics/floors logging are bit-preserving, so a fresh depth arm bit-exactly replays it (dd_s207 == rose-totem-514 == 6165.7 proved it; dd chain killed as redundant).

Gotcha for future A/Bs: before queueing a "new" cell, check whether an old cell is byte-equivalent under bit-determinism — reward/logging commits after a run don't invalidate it if the diff is log-only. See [[nethack-bimodal-verbs]], [[no-hand-edited-hypers]].

2026-08-05 BUDGET LEVER DIES ABOVE 1B (campaign killed at 3/10 seeds, user call): 2B
certified 6910/6735/7281 = **6975 ± 275** vs same-family 1B sc1b **7393 ± 229** — flat-to-
slightly-down, so the ~linear staircase (180M 3500 -> 358M 4100 -> 500M 4550 -> 1B 7393)
BENDS between 1B and 2B. "Train longer" is no longer a fallback answer on this config
family. Secondary, from the same runs: death_weak climbs with schedule (13-19% @250M ->
26-27% @2B) = longer episodes, food clock takes a bigger share — the sharpest remaining
lead on the 87% combat wall, and the one component that's SUPPLY-fixable. Zaps (1.9-6.8/
ep) and discoveries (9-10/ep) keep growing with schedule while score doesn't = knowledge
stack activates but isn't worth points at depth ~6. Also validates the newcham segv fix:
6B+ steps, zero crashes (old rate ~1/150M would have killed ~4 runs). 2B-era pair
preserved (scratchpad/puffer_2b + lib2b_libnethack.so); 3 ckpts banked, s604 partial dropped.
