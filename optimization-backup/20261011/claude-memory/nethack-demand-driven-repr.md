---
name: nethack-demand-driven-repr
description: "PROVEN demand-driven representation — same encoder: digger reads stairs R²=0.995 / merchant 0.03; double dissociation; encoder design acquitted"
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-22T06:16:40.520Z
---

2026-08-21 interp capstone (record+analyze on 3 checkpoints, byte-identical
encoder arch; reports in tools/interp/out/{incum_fresh,sc0386,dmine50}):

| | farmer (idemb) | merchant (0386) | digger (mine50) |
|---|---|---|---|
| downstairs dx R² | 0.63 | 0.03 | **0.995** |
| global dead /128 | 108 | 122 | **33** |
| local dead /256 | 15 | 11 | **0** |
| inv_pool dead /128 | 74 | 78 | **117** |
| death-in-20 probe | 0.833 | **0.920** | 0.821 |
| wield-swap KL | 0.009 | **0.69** | — |

Double dissociation: spatial alive+inventory dead (digger) vs spatial
dead+inventory alive (merchant). Same architecture. Representation supply
follows objective demand at whatever fidelity demand justifies. Encoder
design is ACQUITTED — "the encoder can't see X" is always "no objective
paid for X". Dead dims = gradient starvation (atrophy), NOT capacity
triage (capacity arms bl128/glbpos null-to-harmful; all policies near the
demand floor, none near the ceiling; prio-trained keeps more dims alive:
108 vs 122 dead, n=1 pair — sampling machinery sustains representation).

USER CORRECTION (2026-08-21) — two-factor model: utilization = demand x
ACCESSIBILITY. The lnc precedent: launcher-match demand existed (28,764
launcher-less ammo throws) but the wielded-x-ammo conjunction was
max-pool-buried; the obs bit made launchers get USED immediately —
though score-null (+40/6,869@1B) because bows are weak. Accessibility
engineering (surfacing hard conjunctions/post-pool identities) is the
ONE live representation lever; validate behaviorally (epdump census),
never by 217M score. Vetted candidates: direct wielded-item channel
(0386 wield-KL 0.69 = demand exists, max-pool-buried = access poor),
item base-value for the merchant (flat ~45/sale), nle_obj_at (probe
demand first). Protocol: concat accessibility probe + clumsy-behavior
demand check -> build only high-demand+low-access -> behavioral cert.
Other consequences: blanket representation arms stay dead (20-arm null
ledger); credit machinery ([[nethack-prio-scaling]]), reward vectors
(user territory), consumers with own credit paths (pointer pattern).

**thr AT 1B = FIRST POSITIVE ENCODER RESULT + NEW 1B RECORD (2026-08-22)**:
thr1b_s311/s312 (puffer_thrw, 5c+prio, engine-truth threat features)
certed **7,365 / 7,189** vs paired idemb 7,035/6,929 → +330/+260 (mean
+295, both seeds positive). thr was +63 NULL at 217M — the 217M screen
was the wrong instrument for access arms too. Supports the user's
access-limit thesis: threat access + late-phase credit = usable. 7,365
is the new all-time multi-role 1B record. n=2 paired; a 3rd seed or the
217M-vs-1B contrast makes it a paper-grade finding. "Better policy would want
everything" fails because features only earn gradient through actions
that differ (forced-retreat: geometry actively taught away), strategies
are absorbing basins (bimodal-verbs), joint credit multiplies variance.
Proposed decisive next: DISTILL the three specialists into one student —
removes exploration/credit, isolates pure representability. Suite is
cheap now: record CKPT 24000 OUTDIR + analyze.py OUTDIR (~10 min,
deterministic replay, bit-reproducible). NH_EPDUMP census: burnin 4000 +
8K episodes = behavioral profile in ~2 min ([[nethack-cert-protocol]]).
