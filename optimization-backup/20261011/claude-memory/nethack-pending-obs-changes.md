---
name: nethack-pending-obs-changes
description: Running list of observation/env changes and which training lanes contain them; as of 2026-09-11 18:50 the repo carries every claim-tree edit plus one repo-only change (cant_hold) that no lane has trained with
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-09-11T18:44:44.197Z
---

Observation and environment changes that alter what the policy sees or which actions are masked, and which lanes actually contain them. A policy trained without a change is trained against a different interface than the one it is certed on. Keep this current: add a line the moment a change lands, strike it when a lane that contains it starts. The full weights/tree/cert table is `scripts/nle_stock/LEDGER.md` (see [[nethack-cert-ledger]]).

**Why:** changes accumulated across a long session in separate memory entries, so no single place said what a given run contained. That is how weights got certed against an interface they never saw, and how the local repo ended up both *missing* two claim-tree edits (hunger gate, `NH_EPLOG`) and *carrying* one the claim tree lacks (`cant_hold`) — discovered only by diffing the trees on 2026-09-11.

## State on 2026-09-11 18:50

**Claim tree** = box `/workspace/PufferLib_pkg` (pufferlib `97416d02` + 6 hand edits; inner engine `1d7ab70` + 6 hand edits; lib `bdb9896bd881`). Trained `pkg_s401-403`, `iso_s404/405/411`, `pkgnle_s406/407`, `claim2b_s501-504`. Contains ALL of:
1. public-band hunger gate on CAST (`blstats[NLE_BL_HUNGER] >= 3`, was `internal[7] <= 10`)
2. hallucination conceals the underfoot square (`nle_abl()` gates in winrl.cc + derive rule)
3. prayer cooldown removed from the export (`internal[5] = 0`)
4. engraving belief concealed while hallucinating (`nle_engr_*` fields + `Blind || Hallucination`)
5. canonical twins generalized (`gem_canon`)
6. `pile_limit:0` in netlib.h; `NH_NLE_OPTS` / `NH_KEEP_PILELIMIT` in fs.h
7. public-obs inventory weight in `nle.c` (containers empty, eaten food half)
8. `NLE_GETPOS_NORMAL` gate in `do_name.c` (harness only, no training effect)
9. `NH_EPLOG` per-episode hook in `nethack.h` (cert tooling, no training effect)

**Local repo** `/puffertank/pufferlib` (`c7590188`, inner engine `10236329b`): items 1–9 all present as of 18:46 (1, 7, 8, 9 ported that minute; the rest earlier). Plus one **repo-only** change:
- **`cant_hold`** (`nethack.h`, 7 sites): masks WIELD/THROW/ENGRAVE when polymorphed into a form that cannot hold. **No lane has trained with it.** User judged it minor (2026-09-11) and chose to keep it rather than revert; it is the first pending item for the next training run.

Also differs, by design, not a pending change: repo `log.perf` = depth/50, claim tree `log.perf` = score. Metric definition only; [[reward-config-is-user-territory]].

Older lanes (`rt_1B_1122new_s30x`, `rt_1B_1122pub`, `rt_1B_1122nleopts`) ran on box `/workspace/PufferLib` (lib `44dd5b181dc3`) which lacks items 1, 3, 4, 7 — do not cert them against the current derive.

**How to apply:** before launching the next training run from the repo, the box must run a clone of this branch (not a hand-edited snapshot), rebuild lib + `puffer` + stock binary, and log `git rev-parse HEAD` + dirty count for both pufferlib and the inner engine in the lane's START line. Then strike `cant_hold` here. Related: [[nethack-cert-ledger]], [[nethack-stock-nle-bridge]], [[no-hand-edited-hypers]].

## 2026-09-11 23:00 — first lanes on the one tree
`nlestock4b_s601-604` (4B, claim config, NLE opts) train on pufferlib `nle-stock` **`423ced55`** + engine `dfbdc84c8` from `/workspace/pufferlib`. They contain everything above PLUS `cant_hold` **with its per-episode reset and the extended trigger texts** (WEAR masked too) — A/B on 6,000 paired strict episodes: aborts 3.7% → 1.5%, score unchanged (P=0.51). They do NOT contain the zero-time memory mask (`NH_ZT_MASK=1`, opt-in): v1's "world unchanged" test (x, y, depth, clock) misreads a fast hero's extra-speed actions as refusals and cost −8% at equal completion. v2 must define "unchanged" over the whole observation (map, blstats, inventory, no new message) before it can be default. Nothing else is pending for training; all remaining work (reconstruction) is eval-side.

## 2026-09-12 09:12 — 4B lane groups
- `nlestock4b_s601-604` (tree `423ced55`): **sticky** extended `cant_hold` — the version that cost 12 %/19 % on stock certs (clear message dropped); fork-side cost bounded ≤ 2–3 % (rung 1 equal across trees), so kept running.
- `nlestock4b_nomask_s607/608` (tree `a51b1953`, `NH_NO_CANT_HOLD=1`): **no form mask at all**, otherwise identical. User's call ("my instinct would just be to remove it"). The 4-vs-2 rung-1/rung-3 comparison at the end measures the training-side cost of the mask directly. `s605/606` (sticky build) were stopped at 393M to make room.
- Eval side: `cant_hold` now expires after 100 turns by default (`a51b1953`); `NH_CANT_HOLD_STICKY=1` reproduces the old cert behaviour; `NH_NO_CANT_HOLD=1` removes it.
