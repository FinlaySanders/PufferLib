---
name: nethack-gold-buy-design
description: "Gold/shop reward design space — buy-penalty removal fails two ways (refund pump, cost-blindness); spread impossibility; high-water = working design"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-12T16:58:42.517Z
---

2026-08-12 gold quartet (group goldtrio, champion stack + gold_coef 1.0,
250M s305, control = certified 6,970; env-var opt-in modes in nethack.h
reward + macros.h sale capture; all uncommitted working-tree):

- **plain delta (goldp): 5,649** — sells 14.8/ep, buys 0.02. High gold price
  alone = worse policy that sells a lot ("sells but never buys" reproduced).
- **buy-free v1 (full refund, NH_GOLD_BUYFREE): WIREHEAD at 87M** (score 477,
  39 buys/ep). Exploit = income laundering through the CLAMP: g=max(0,
  gold−start) makes income below start-gold reward-invisible but the refund
  paid full price → every coin funneled through a purchase = +1 free reward.
  NOT sell-back cycling (sells 0.9). Patch: refund capped at
  min(bought, actually-penalized loss).
- **free-buy v2 (NH_GOLD_FREEBUY, start_gold absorbs spend + resale-pool
  offsets sale income at (P+1)/2 ceiling): COST-BLIND at 107M** (score 446,
  37 buys/ep, sells 0.65, turns/step 2.1). No pump exists — but score still
  charges spend while reward sees a no-op → PG buys freely, drains gold,
  stops farming. IMPOSSIBILITY: fully-free buying + rewarded sale income
  fails EITHER as a pump (any positive purchase channel + shopkeeper spread)
  OR as reward/score divergence. Buying must carry some cost signal.
- **high-water (NH_GOLD_HIGHWATER): 5,745** — buys 1.20/ep (20× plain), sells
  12.2, score level with plain. The working design: implicit spend cost
  (income muted until mark re-crossed), structurally pump-proof.
- **half-exempt (NH_GOLD_BUYEXEMPT, 0.5 refund capped): cycle-safe (f ≤
  sellback ratio 0.5)** — result pending.

Context: id-oracle (NH_ID_ORACLE, engine-side) = NULL both regimes (score
−82, depth +0.07): farmer already used all items via trial-by-use, diver
uses none. Item knowledge inert; item VALUE/pricing is the live lever.
All gold-1.0 arms ≈ −1,300 vs champion: gold mispricing dominates any
buying gain at this dose.

**Why:** reward-hacking case studies + the design constraint for any future
shop/buy reward work. **How to apply:** never ship a purchase channel whose
reward sign can go positive (pump) or whose cost is invisible (blindness);
high-water is the proven-safe base; pkill lesson: driver scripts launched
via heredoc self-match their wait patterns (launch by path only).
