---
name: nethack-calendar-effect
description: CORRECTION 2026-09-13 - the wall-clock (moon phase / night) effect on NetHack score was never established; the one controlled real-vs-fake-clock test was null, the phase arms were invalid replicates
metadata:
  type: project
---

Stock NetHack reads the wall clock (phase_of_the_moon: new moon = cockatrice hiss petrifies, full = +1 Luck; night(),
midnight(), Friday 13th). Pinning the clock IS needed for game-for-game reproducibility of stock runs (self-determinism
finding). But its effect on aggregate score is NOT established:
- Controlled test 2026-09-12 (NetHack new-moon day; 2B derive v3, strict seed 21, 6,000 games each): real clock
  canary3_2b_s21 14,559 (se 391) / 8,730 vs fake per-game date claim2b_fakeclock_s21 14,439 (se 405) / 8,799 -> null.
- The leaky-4B "fullmoon/neutral/newmoonday" arms (20,519 / 19,753 / 19,705) all ran the same 2020 date (dev
  FIXEDCLOCK ignored the epoch) = three replicates of one condition; +-2% mean spread at 6K games is replicate noise.
- "real new-moon-night = -9%" was an uncontrolled single observation (leaky 4B gym, night of 09-11), not a result.
- 2026-09-13 fixed-4B gym certs ran on the real clock during NetHack phase 0 (11-14 Sep 2026) and matched the fork
  within noise (median +2.6%, mean -1.0%).

**Why:** earlier notes/handoff quoted the -9% as if causal; the user asked "did we decide the moon/night clocks were the
cause" - answer is no. The gaps of that week were the sticky cant_hold mask (-12%/-19%) and derive reconstruction errors.

**How to apply:** describe the clock as a reproducibility issue, never as a measured score effect, unless a paired
pinned-vs-real test at >=10K games shows otherwise. Related: [[nethack-cert-ledger]], [[nethack-handoff-2026-09-12]].
