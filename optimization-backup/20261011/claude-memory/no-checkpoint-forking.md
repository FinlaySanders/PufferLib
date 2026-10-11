---
name: no-checkpoint-forking
description: "Checkpoint-fork A/B designs rejected — \"forking never works\" on this trainer; use from-scratch paired seeds"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-20T13:10:00.823Z
---

User verdict (2026-08-20, prio ablation design): "Forking never works." Do not
propose resume-from-checkpoint A/Bs (load_model_path continuations) for
training experiments on this stack.

**Why:** resumed continuations aren't comparable to the original trajectory
(optimizer/anneal/replay state resets); the user has seen this fail before.

**How to apply:** causal training A/Bs = from-scratch paired seeds (same seeds
both arms, bit-deterministic trainer makes arms differ only by the flag), at
the budget where the hypothesized effect lives. See [[nethack-cert-protocol]],
[[no-hand-edited-hypers]].
