---
name: general-strategy-over-piecemeal-features
description: "Obs/encoder gaps get a worked-out representational principle, not ad-hoc scalar features added one by one"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-30T13:25:24.641Z
---

2026-08-30: after a worn-count probe finding, I implemented a +10-scalar "armor observability pack" (counts + coverage bits). User: "I don't want that sort of thing... Adding these features one by one is not as good as working out the general strategy. Maybe that's just passing through all the worn armour."

**Why:** ad-hoc scalars patch symptoms; the durable fix is identifying the representational principle the gap violates. The worn-count gap was a symptom of an asymmetry: wielded/quivered get full 40-dim pass-throughs (which is why bow↔arrow worked), worn got a lossy 16-dim mean. Principle articulated: pooling is for unordered multitudes (pack contents); fixed singular equipment slots deserve full-fidelity per-slot pass-throughs (the equipment-panel design: one 40-dim content+state block per armor subclass, zeros when bare — subsumes counts, coverage, per-piece state linearly).

**How to apply:** when a probe reveals missing observability, first map the existing representation's treatment of that family, name the principle being violated, and design the general fix; only fall back to scalars when no structural principle exists. Related: [[formability-first-encoders]], [[explain-results-in-full]].
