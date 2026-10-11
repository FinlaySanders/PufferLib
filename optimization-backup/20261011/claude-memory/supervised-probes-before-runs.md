---
name: supervised-probes-before-runs
description: "Arch/encoder capacity questions get quick supervised probes (klab/fentlab pattern), not 250M RL runs, unless the user asks for runs"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-29T13:05:01.264Z
---

For architecture/encoder capacity questions, the user wants quick supervised probes (klab/fentlab pattern: synthetic or dumped-frame tasks, minutes on GPU), NOT full RL runs. 2026-08-29: I queued a FENT validation chain with gradcheck + A/A + bench + two 250M RL A/B runs; the user interrupted and said "Kill any full runs testing this, I just want a quick supervised probe" — and wanted it scheduled on the GPU after the current queue.

**Why:** full runs cost hours of GPU for questions a probe answers in minutes; the RL A/B is only warranted after the supervised gate passes AND the user asks for it. Also echoes [[no-hand-edited-hypers]] economy thinking.

**How to apply:** when an arch variant question arises, build the supervised harness first (deep-vs-variant on the sharpened klab task family: hinge/product/conditional-count/gated-max under the real pooling), schedule it in the GPU queue like any other job, report R² tables. Propose RL runs only on explicit request. Related: [[nethack-branch-lab]] klab lessons (ranking tasks forgiving — tasks must hinge on the interaction).
