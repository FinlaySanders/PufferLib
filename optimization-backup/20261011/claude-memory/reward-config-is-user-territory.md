---
name: reward-config-is-user-territory
description: never change reward config/terms or launch multi-hour campaigns on my own initiative — propose and wait; approvals are narrow
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-04T14:28:05.851Z
---

2026-08-04: after "we need to find things that boost perf" I restored six pruned reward terms and launched a 4×1B campaign without asking. The user stopped it: "you made a big change without permission. undo it." Full revert followed.

**Why:** the reward config is a design surface the user personally owns — they directed the prune, hand-set the ranges, and ruled "the sweep will find the coeff, this is not our task." Reversing a user-made design decision is a scope change even when the evidence for it is good. Multi-hour GPU commitments are also theirs to spend. A day of "kill that and do X" approvals is a sequence of narrow, specific consents — not standing authority to originate big moves.

**How to apply:** analysis and proposals are always welcome — propose the experiment, its cost, and the decision it informs, then WAIT. Only implement reward/config/campaign-scale changes the user explicitly ordered ("try X", "do it", "add both"). Small approved-scope code (a stat, a fix to something they flagged) remains fine. See [[no-hand-edited-hypers]], [[pufferl-off-limits]].
