---
name: obs-features-normalized
description: "All encoder obs features must be strictly normalized to [-1,1]; raw obs ints are transport, scaling lives in the encoder (CUDA + demo parity)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-08T12:47:45.271Z
---

Every feature entering the net must lie strictly in [-1, 1].

**Why:** user convention (2026-08-08, caught the encumbrance-percent design at 0-3+
before it shipped); keeps feature scales uniform for the trunk.

**How to apply:** raw obs ints are transport only — normalize at the encoder feature
stage, in BOTH ocean/nethack/nethack.cu and the demo forward (ocean/nethack/nethack.c),
which must stay bit-consistent. For unbounded quantities prefer a bounded squash that
keeps gradient where decisions happen (e.g. encumbrance = softsign(ratio-1): wall at 0,
strictly (-1,1), no flat clip) over linear-clip. See [[nethack-env-setup]].

**v5 audit 2026-08-23**: violations found+fixed — lmtab dx/20 dy/10
(±3.9/±2 -> dx/78 dy/20), sector log1p (0-6.7 -> /log1p(1659)), stream
dx/40 dy/11 tails (±1.95 -> hard clamp, near-field untouched), inv spe
x0.1 + quan log1p x0.5 tails (-> clamp/7, /log1p(127)). KEY LESSON:
linear rescale to true range = provable parity with validated features
(verified: terrain row reproduced); SOFTSIGN squash REJECTED by
measurement (cost .05 far-field precision — nonlinear reparam is not
free when far field carries signal). Squash-over-clip law refined:
squash for whole-range features, clamp for rare tails of validated
features, linear rescale as default.

**v5 regression sweep GREEN (all branches, final scalings)**: terrain/
crop/streams/inventory all at reference. Two catches: streams need the
certified 96-epoch budget (40ep false-negatived .84 vs .94); inventory
QUANTITY must be min(q,30)/30 linear-capped — log1p/log1p(127) regressed
ammo-count .88->.76-.79 across two seeds (log-squash on count features
loses magnitude signal). Hazard passthrough sanity 1.00.
