# NetHack mask and passthrough ablations — consolidated results (29 Sep – 6 Oct 2026)

Question: which of the hand-written action masks, exploration aids and encoder passthroughs are load-bearing for the current
NetHack policy, and which can be removed to simplify the action interface? Campaigns were planned in
`NETHACK_ABLATIONS_audit-20260929.md` (repo-root NETHACK_ABLATIONS.md) and run by a separate agent; per-campaign RESULTS.md,
manifests and per-run results.json are alongside this file. Final checkpoints of every run are on the host disk
(`~/puffertank/nethack-backup-20261011/misc/mask-campaigns/`), not in git.

Protocol (all training campaigns): 1B steps per run, paired seeds 2901–2905 (failed runs replaced by fresh seeds), identical binary,
engine, architecture and hyperparameters; evaluation with the training masks, seed 7, 6,000 fork games per policy, first 4,000
discarded, 2,000 retained. Baseline seed spread is the yardstick: 13,199–13,438 mean.

## 1. Individual removals (nethack-mask-ablations-20260929, 27 runs)

| Variant | Seeds | Mean score (per seed) | Verdict |
|---|---|---|---|
| baseline | 5 | 13,199 / 13,438 / 13,422 / 13,398 / 13,364 | reference |
| no handless-form mask (cant_hold belief) | 5 | 13,133 / 13,668 / 14,761 / 13,081 / 13,950 | within noise |
| no hostile-ray restriction (THROW/ZAP direction preference) | 5 | 14,443 / 12,873 / 12,751 / 13,466 / 13,549 | within noise |
| no strategic item restrictions (satiated eating, book rereading, shop affordability) | 5 | 13,457 / 13,312 / 12,461 / 13,735 / 14,209 | within noise |
| zero-time refusal mask ON in training | 5 | 12,648 / 13,132 / 13,009 / 12,442 / 13,892 | within noise, slightly low |
| no RUN / SEARCH20 | 1 | 4,893 (depth 8.63) | collapses score; the remaining 4 seeds were cancelled |
| no verb epsilon | 1 | 9,261 | large loss; remaining seeds cancelled |

## 2. Combined removal (nethack-mask-combined-20261002, 5 retained + 2 replacement runs)

Handless + hostile-ray + strategic item restrictions all removed: 14,202 / 13,147 / 12,583 / 14,080 / 13,118 — within the
baseline spread. The three strategic masks are not load-bearing individually or together.

## 3. Nearby-entity passthroughs removed (nethack-nearby-pass-20261002, 5 runs)

Nearest-monster, nearest-floor-item and underfoot-item summaries zeroed (pooled streams and inventory passthroughs kept):
12,930 / 13,585 / 13,126 / 13,169 / 12,388 — within noise, marginally below baseline. The frozen-policy probe
(nethack-nearby-probe-20261003) shows the pooled streams only partially encode those targets (held-out R² 0.55–0.83 from pooling
alone vs 1.00 with the passthrough), so the passthroughs carry information the policy does not need for score.

## 4. Zero-time mask at evaluation (frozen policies, stock C backend)

Six checkpoints, mask off → on: Δ mean −7.8% … +6.4% (−893, +808, −1,177, +172, +46, +842); clockless 10,000-step timeouts
14–26 → 0–1 per 2,000 games; no-turn actions 8.5% → 5.8%. Net: no consistent score effect, large hygiene gain. It shipped opt-in
(`NH_ZT_MASK`, off in training, on in stock/Python eval).

## What this says about what to work on

- Load-bearing: RUN/SEARCH20 macros and the verb-epsilon exploration mixture. Do not remove either without a replacement; any
  change to them needs its own paired-seed study.
- Removable for simplicity: handless belief, hostile-ray preference, the three strategic item restrictions, the nearby-entity
  passthroughs. None moved score beyond seed noise at 1B, alone or combined. Removing them is an interface cleanup, not a win.
- The audit's untested candidates remain: accessory/inventory passthrough panels, identity encoding and the 16-d item bottleneck,
  pooling variants, message encoder width, pointer-decoder normalisation (see sections "Architecture candidates" of the audit).
- Measurement note: a 1B, five-seed screen resolves ≈ ±600 on a 13.4K mean; effects smaller than that are invisible here and
  need 2B+ or more seeds (see the 2B/4B scaling records in the main ledger).
