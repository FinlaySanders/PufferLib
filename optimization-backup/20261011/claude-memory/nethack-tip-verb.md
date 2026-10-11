---
name: nethack-tip-verb
description: "TIP verb (verb 24, containers) built+validated 2026-08-04; NH_DEC_PAD landmine defused; A/B pending; HOLD COMMIT until sweep done"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-04T10:15:41.286Z
---

TIP verb shipped locally 2026-08-04 (task #108), from the container deep-dive: containers were 100% dead content (40% of room-levels spawn a box, 80% locked/10% trapped, contents avg 2.5-3.5 items incl 7% gold @2.5x level-normal, 6% wand). See [[nethack-mechanics-audit]].

**Implementation** (uncommitted; mask 731→732 breaks sweep-box checkpoint compat — HOLD COMMIT until the reward sweep concludes):
- fast-nle `nle_container_at` (nle.c, after nle_shop_price): counts tippable containers underfoot; skips known-empty (`cknown && !cobj`) and known-locked (`lknown && olocked`) — hero-knowledge gates only, no state leak. Failed tips cost a real turn (dotip returns 1), so this is wasted-action masking per the "no wasted actions" principle. Kick breaks lock → olocked clears → container re-masks in.
- netlib.h: NETHACK_NUM_ACTIONS 24, NETHACK_ACT_TIP=23 `{-1}`, stat "tips"; nethack.h: mask + execute (send `0x80|'T'` = M('T'), the `[yn` auto-commit answers "tip it? [ynq]"); nethack.cu NH_ACTIONS 24; ini action_mask_size 732.
- **NEW LANDMINE DEFUSED**: NH_DEC_PAD was hardcoded 72 (nethack.cu) and DEMO_DEC_PAD 72 (nethack.c) — NH_DEC_LIN went 72→73 and gradcheck caught the silent slice-truncation. Both now derived `(LIN+7)/8*8`. The action-count layout family is: netlib.h enum/table, nethack.cu NH_ACTIONS, DEC_PAD pair, ini mask size.
- Validated: goldens 34/34, gradcheck PASS, scripted probe (scratchpad/probe.c PROBE_SCRIPT=1): keybinding fires ("Never mind." unmasked), mask fires on real chests, empty/locked mask off after first touch, unlocked boxes spill.
- Old ./nethack demo binary (23-action) kept for watching old checkpoints; new-arch checkpoints need a demo rebuild.

A/B: 4 seeds (207/208/210/211 — 209 hangs, see [[nethack-engine-bugs]]) × 250M, group tipab, vs sc025 banked 6180/5950. Primary read = tips/ep adoption + kicks + sale_gold; score is guardrail only (direct EV +50-100 < n=4 noise ±200-300).
