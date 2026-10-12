# NetHack rollout scheduler: cache residency without losing balance — 12 October 2026

Question (user, 12 Oct 12:30): is there a rollout scheduler that keeps each core's games L2-resident (the +20-26% per-core prize measured in the
11 Oct cohort matrix) and still balances P/E cores and per-game variance, under realistic inference latency? Answer: yes at ≳ 40 games per core,
no below it. CPU replay harness, bit-exact (every arm reproduces the pool control's final-observation hash), 8 passes, ~200 arms, one afternoon.

## Result (2048 games, 24 workers pinned one per physical core, tile_signed_pgo engine, fast protocol: warm 8192 decisions/game, measure 2048)
| inference round trip (window / forward) | today's pool | hybrid scheduler | gain |
|---|---:|---:|---:|
| 350 / 350 us (window = forward: today's forward size and launch rate, 5M-like) | 333.5K | 370.2K | +11.0% |
| 800 / 800 us (15M-like) | 291.2K | 308.9K | +6.1% |
| 200 / 350 us (2x today's launch rate) | 333.5K | 374.5K | +12-14% |
| 100 / 150 us (lean forward) vs pool at 150 us | 345K | 381-390K | +10-13% |
Reproduced across passes 3-8 (pool run-to-run spread 1.7-1.8%); wall/busy 0.95-0.98; 4-7% of ticks borrowed; hashes identical.
Population scaling (pass 9): 4096 agents +13.8% (372.0K vs 326.9K) / +11.9% at 800 us; 8192 agents +11.7% (368.0K vs 329.5K); the env side of this box
saturates at ~370K from 2048 up (24 cores x 63 us), pool flat at ~330K; zero-latency bound 453-457K (52 us L1-warm step).
512 games: +13..+20% at an 800 us round trip (depending on segment length), −2..−9% at 350 us → stay on the pool below ~40 games/core.
Zero-latency bound of the design: +13% wall / 420-450K per core at 2048 — the hybrid collects ~85-90% of it at realistic latency.

## The design (replay_sched.c, final: SCHED_C=1 SCHED_LAZY=1 SCHED_BORROW_US=0 SCHED_EVENT=1, segment = batch horizon, window = forward)
1. Ownership: every game has an owner core (round-robin at start; moves only at segment tails). Cores pinned one per physical core.
2. Stepping, per core: keep an ACTIVE set of own games (those started on this segment). Step whichever active game has its actions back. If none:
   activate one more own game (lazy growth — the hot set becomes exactly as large as the latency demands, ~8 games at 350 us, ~16 at 800 us).
   If all own games are active and none is ready: step ONE tick of any other core's ready game (borrow; the owner keeps it), found through
   event-driven ready buckets while spinning; never sleep.
3. Inference: every window W, gather every game whose observations are ready into one forward; W = forward time → one stream keeps up and the GPU
   sees forwards of today's size at today's rate. Per-cohort latency = W + F.
4. Segment = batch horizon; at its barrier a finished core steals a whole cohort from the holder with the most remaining work if it has ≥ 2 pending,
   else splits its last cohort in half (steal-half); borrowed pieces return and merge at the barrier; ownership migrates only when counts differ by ≥ 2.
Knobs that fell: in-flight count (fixed A over-borrows: −60..+9%), ownership weights / migration tuning (null), group-synchronous refill (minor),
borrow threshold (0..60 us identical), cohort size (1 = 2 > 4 > 8), segment length at 2048 (neutral), FIT rule (= plain at 350, −2..6 pts at 800).

## Why it works (each measured separately)
Residency is per core: ~60 KiB touched per step; same games again = 76 us/step, 21 others in between = 100, 64 = 128. The pool trades residency for
balance by design. Ownership alone cannot collect it: residency and latency hiding compete for the games in flight per core (passes 1-2 tied/lost).
Splitting the two jobs collects it: own games 93-95% of the time (residency), borrowed cold ticks (1.3-1.4x, self-measured) fill the latency gaps
instead of idling, tail steal/split fixes P/E imbalance at 3-5% instead of the 13-25% static ownership lost on 11 Oct.
Why not at 512: Little's law — 24 cores x 550 us / 65 us ≈ 300 games must be in flight; 21 own games per core run out; the pool's 4x128 pipeline is
exactly balanced for that shape. Not an implementation flaw (event-driven readiness changed nothing there).

## What it is worth in training
Rollout SPS only; nothing has run in the trainer. Shows up where collection binds: 5M at 2048/4096 (~+10% training SPS expected), half of it at
15M/2048, nothing at 15M/512 (GPU-bound, and the pool stays there anyway). With the window = forward rule the GPU traffic is unchanged; the gather/
scatter copies and padding to a fixed graph batch are unmeasured costs. Fixed agent count caps SPS at agents/(step + round trip) regardless of
scheduler (512 agents: ~830K); on a bigger box at 512 agents the round trip binds before cores do.

## Trainer realisation (trainer infra → experiment copy + handoff patch)
Per-game ownership table in the env pool; lazy activation; borrow-when-idle via a ready queue fed by the inference thread; windowed gather into a
fixed-shape (padded) forward every F us; per-agent trajectory/recurrent state unchanged; select by agents per worker (≥ 40 → hybrid, else pool).
Gate: identical per-agent action sequences under a frozen policy (BATCH_PROOF), then the fast-protocol A/B at 5M/2048 and 5M/4096.

## Novelty
Composition, not parts: owner-first stealing (Cilk work-first; Acar/Blelloch/Blumofe locality of work stealing), steal-half (Hendler/Shavit),
cost-aware tasks (already in env_pool.h), time-windowed inference batching (SEED RL / EnvPool / Sample Factory). Not seen applied to env stepping as
cache-affine tasks with demand-grown in-flight sets and borrow-only-when-idle; no literature search was done.

## Files
replay_sched.c (all variants; builds replay_sched{,2..6} via build.sh [engine] [suffix]); replay_pool.c (trainer pool emulation: env_pool.h from
trainer_cohort, 4x128 groups, 64-tick turns, per-buffer round trip); analyze.py; screen{,2..8}.sh; screens*/summary.txt + per-arm logs; PROGRAM.md (ledger).
