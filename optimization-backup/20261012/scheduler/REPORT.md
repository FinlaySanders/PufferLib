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

## Trainer realisation (same day, 16:50-17:50 UTC) — trainer/ (experiment copy of the engine-scaling trainer_cohort source; handoff = trainer/pufferl_sched.patch + src/env_sched.h)
PUF_SCHED=1: per-game ownership with weighted initial assignment (P-core workers 1.25x), lazy active set with a self-tuning cap (round-trip EWMA /
step EWMA, segment-start burst excluded, returning games above the cap are parked), borrow-when-idle (busiest other worker, same-L2-cluster preference
optional), workers never sleep; S=4 inference slots gather up to 128 ready agents per window (window = forward-time EWMA), zero-copy gather kernel reads
the pinned host rows by index (no CPU copy), per-slot captured graph (gather state/RNG → zero_term → snapshot t==0 → forward → scatter → record to
(time, agent)), D2H actions scattered to agents. Per-agent recurrent state and sampler RNG; replay hook indexes recorded actions by the agent's own t.
GATES: BATCH_PROOF identical to the pool at every shape (44 epochs each); PUF_STATE_PROOF (master weights, Muon momentum, gradient updates after 44
epochs of training on the scheduler's rollouts) IDENTICAL. The scheduler changes wall time only.
RESULT (fast protocol, 24 pinned workers, cap 16 + P-weight 1.25): 5M/2048 +3.8% (335.6K / 335.3K vs 323.4K / 323.2K); 5M/4096 +2.7% (364.0K vs 354.6K);
15M/2048 −9.5% (215.0K vs 237.6K: inference-bound regime, forward ~1 ms under PPO contention, +200 us per-forward overhead paid 2100x/epoch, workers idle
35%). Selection rule: scheduler at 5M-like (collection-bound) shapes with ≥ 40 agents per worker; pool otherwise.
WHY LESS THAN THE HARNESS (+11%): (1) the ratchet — variable forward latency made the lazy hot set grow to 29 games (fixed by the cap: 80 → 68 us/step);
(2) the slot threads' 512 KB CPU memcpy per forward on the P-core SMT siblings (fixed by zero-copy: P-core steps 61 → 57 us); (3) borrowed cold ticks at
15-18% of steps (E-core steps 72.5 vs the pool's 71) — borrowing fills idle, so a bigger hot set loses more than it saves; (4) the harness's pool emulation
was ~5 us/step pessimistic and its hybrid ~5 us optimistic (no real data movement, no PPO, deterministic latency). Per-core: P 57 us (pool 59), E 72.5 (pool 71).

## Engine step map with hardware counters (14 Oct, host-side perf attach; overnight/function_map.txt, perf_rot/results/)
Rotation cost mechanism: per 1000 instructions from rotation 1 to 16, cycles 350 → 434, conditional-branch mispredicts 2.99 → 5.30 (indirect/return
flat), resteer cycles 20 → 34.5, L1d misses 2.42 → 2.90, L1i misses 7.2 → 7.8, TLB nil. Branch prediction is ~60% of the rotation cost, data cache ~15%.
PGO halves I-cache misses (12.8 → 7.2/Kinstr) at the price of +15% mispredicts; net +13% speed per step.
Function map (cycles / mispredicts / I-cache shares at rotation 16): m_move 23.5 / 28.9 / 15.2; mfndpos_masked 13.8 / 12.8 / 4.9; nethack_pack_obs
7.4 / 9.1 / 3.5; movemon 5.2 / 4.1 / 3.1; nh_fobj_next 4.5 / 4.5 / 2.3; newsym 4.0 / 2.9 / 3.7; dochug 3.7 / 2.8 / 3.1; isaac64 RNG 3.4 / - / -;
fill_obs 2.4 / 3.7 / 2.3; moveloop 2.3 / 1.5 / 8.6. Rotation-sensitive (mispredict increase per Kinstr): m_move +0.57, pack_obs +0.31, mfndpos +0.25,
fill_obs +0.15, nh_fobj_next +0.15. Targets: monster movement (m_move + mfndpos = 37% of cycles, 42% of mispredicts), observation packing (pack_obs +
fill_obs = 10% / 13%), I-cache layout of m_move + moveloop + flush_screen (27% of I-cache misses).
Scheduler by population (same-session pool controls, batched gather, cap 12): 1024 +2.9%, 2048 +6-7% (3 pairs), 4096 0%, 8192 −5%, 15M/2048 −2%,
15M/4096 −2%. Live learning proof (150 epochs, weights updating, 2048 agents, 4 buffers): identical observation hashes every epoch, pool vs scheduler.
Trainer-level (live 24-worker process): engine mispredict distribution identical under pool and scheduler (m_move 28%, mfndpos 13%, pack_obs 11%);
the scheduler's slot threads account for 17.4% of process cycles (spinning on P-core SMT siblings) and worker spin loops 3.9% — the next scheduler
experiment is a sleeping slot wait or a different slot-thread pin, judged by P-core 0-3 vs 4-7 step cost. Process-wide counter rates are diluted by
each design's spin style and are not an engine comparison.
