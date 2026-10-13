# NetHack rollout scheduler — L2 residency without losing load balance (opened 2026-10-12 12:30 UTC, user: "find this")

## Question
Is there a rollout scheduler that keeps each worker's games L2-resident (the +43..70% per-core prize measured by the 2026-10-11
cohort matrix) AND balances P/E cores and per-game variance (the 13-25% of wall that static ownership lost), under a realistic
inference-latency model? Falsifiable: wall SPS vs a latency-matched emulation of today's trainer pool, same engine, same recorded actions,
identical final-observation hash.

## Premise (measured, do not re-derive)
- Hot set per decision ~60 KiB of lines (compact-state traces); 16 games/worker ≈ 1 MB fits the effective L2, 64/worker does not; the
  per-step cost knee is L2 and plateaus from 64/worker (engine-scaling Stage 0). Burst16 (one game hot) = 76 µs/step vs 99.6 (16/worker)
  vs 128 (64/worker) at 32 workers.
- Cohort matrix (static ownership, 32 workers, 2048 games): A1 burst +70% per core, A2 ping-pong at 300-1000 µs latency +38..43% per core,
  A4 (today's 4-buffer pipeline) +11%; static ownership lost 13-25% of wall to P/E imbalance.
- Today's trainer (cohort ini keys 16x128 g4 s64 + 24 pinned workers) already holds a 512-agent resident group = 21 games/worker, i.e. the
  A4 regime; its pool is saturated (91% busy, 97% of busy-capacity). Weighted static P/E ownership was tried and lost (−41%); plain local-first
  lane preference was null at 2048 (never tested at 512). The 15M/512 trainer regime is GPU-bound on this box, so a CPU-side win shows at
  5M, at 2048+ games, and on a GPU-rich box — not in the champion's SPS here.

## Design under test (replay_sched.c)
Cohort = fixed set of C games. Ownership table; a worker alternates up to A of its cohorts (ping-pong) inside a horizon segment of SEG ticks
(barrier at the segment end = batch assembly). Inference: dynamic batching — a cohort finishing a tick at e has actions at
ceil_to_window(e, W) + F (optionally serialized over S streams). Balance: a worker whose cohorts are done for the segment steals the
most-behind idle cohort of the holder with the most remaining work and borrows it; if the victim owns ≥ MIGRATE more cohorts than the thief,
ownership moves permanently (so ownership drifts toward faster cores and settles rather than ping-ponging). Hot set per worker = A×C games;
latency hidden when (A−1)·C·t_step ≥ W+F. Pinned one per physical core (24: P 0,2..14 / E 16..31), like the trainer.
Control (replay_pool.c) = the experiment trainer's env_pool.h (stealing, pinning, 4 helper submitters on P-core siblings), 4 buffers of
128 agents per resident group of 512 taking 64-tick turns, per-buffer round trip F after each buffer tick (W=0: each buffer launches its own
forward). At 512 games this IS the champion's rollout; at 2048 it is the recommended cohort-knob config.
Realistic latencies: 5M-like W=200/F=350 µs; 15M-like W=400/F=800 µs (Stage 4 forward timings under PPO contention). W=400 keeps today's
launch rate; the GPU-side cost of more/smaller forwards is NOT modeled — a 2x launch rate lost 3-5% in the trainer (depth-8 screen).

## Correctness
Smoke (128 games, 4 workers, 64+64 ticks): pool with/without latency and sched at (C,A,steal,migrate,streams) ∈ 6 variants all hash
240e6a6071c57b09. Screen arms must reproduce the pool control's hash at 512 and at 2048 (2048/32-worker lineage hash b97835c62aaf388f was
mt7 + harness_cohort header; tile_signed_pgo is bit-exact with mt7, so the 2048 hash should still be b97835c62aaf388f — a difference is a finding).

## Screen (screen.sh, queued behind the champion campaign + s3002 rerun; ~40 min; screens/summary.txt)
24 workers pinned, warm 8192, measured 2048 ticks (4096 at 512). Per N ∈ {512, 2048}: pool F=0/350/800 (+4x512 layout at 2048);
sched bounds (C16 A1 F0 steal/static, C4 A1 F0); 5M-like (C,A) ∈ {4,3 4,4 8,2 8,3 16,2} + static / pweight 1.25 / 2 streams / no-migrate at C8A3;
15M-like (C,A) ∈ {4,5 8,3 8,4 16,2 16,3} + 2 streams at C8A4; pool F=350 repeat for spread.
## Decision rule
A realistic arm (5M-like or 15M-like latency, STEAL=1) beats the latency-matched pool control by ≥ 10% wall at 2048 AND wall/busy ≥ 0.95
→ the scheduler is found: write the trainer design handoff (ring of cohort slots + dynamic batching + sticky stealing; trainer infra = patch only)
with the measured surface, then a GPU-side forward-rate check. Otherwise: report the realizable residency bound vs today's pool and close.

## Pass 1 RESULT (2026-10-12 13:36 UTC; screens/summary.txt; replay_sched build de270abf; 24 pinned workers; every arm hash-identical to the pool: 512 f6b51710d43700db, 2048 b97835c62aaf388f — tile_signed_pgo reproduces the mt7 lineage hash)
Pool controls (today's trainer rollout, cohort-knob layout): 512: F0 359K / F350 340K / F800 296K; 2048: 353K / 329K / 291K; the pre-cohort 4x512 layout at 2048 = 251K (−24%, matches the trainer's +26% cohort-knob gain).
| arm | 512 wall (vs matched ctrl) | 2048 wall (vs matched ctrl) | per-core (busy) | wall/busy | note |
|---|---|---|---|---|---|
| bound C4 A1 steal (no latency) | 389K (+8.2%) | 400K (+13.2%) | 430K / 420K | 0.90 / 0.95 | balance SOLVED: static ownership 0.79 / 0.88 |
| best 5M-like (W200/F350) | C8A3 326K (−4.0%) | C4A4 331K (+0.7%) | 387K / 393K | 0.84 | idle 0.65-1.2 s of ~13 s |
| best 15M-like (W400/F800) | C8A4 263K (−11%) | C8A4 275K (−5.6%) | 393K / 338K | 0.67 / 0.81 | idle 2-4 s: latency not hidden |
Readings: (1) borrow/split stealing closes the P/E imbalance (wall/busy 0.95 at 2048), so the residency scheduler is no longer limited by balance.
(2) Under realistic latency it ties (5M-like) or loses (15M-like): residency and latency hiding compete for the same resource (games in flight per
core); hiding 350 µs needs ~10 games of other work in flight, 800 µs ~22 → the hot set must be ≥ today's 21, and any late return idles the core.
(3) STREAMS arms (−86..−97%) are a MODEL BUG in pass 1 (F charged per cohort per stream, not per window) — fixed in pass 2 (one forward per window).
(4) pweight / migrate knobs: null (migrations 0-14). (5) The remaining harness artefact is nanosleep slack (~27 µs per cohort tick ≈ half the idle) — fixed in pass 2.
Decision-rule status: NOT met. Pass 2 (precise waits, lazy hot set, per-window forwards, 150 µs lean-forward arm) running; pass 3 (borrow-when-idle hybrid) queued.

## Pass 2 RESULT (2026-10-12 14:05 UTC; screens2/summary.txt; replay_sched2: timer slack 1 us + spin, lazy hot-set growth, per-window forwards; all hashes identical)
2048 games (pool F350 335.7K, F800 291.9K): best 5M-like = C4 lazy W100 346.8K (+3.3%), C2 lazy +2.5%, C4 lazy +1.5%; 15M-like C4 lazy 302.1K (+3.5%);
fast (W100/F150) C4 lazy 369.1K (no matched pool control in this pass; pass 4 adds pool F150); bound C4A1 401.2K. wall/busy 0.87-0.90 for the lazy arms, idle 0.85-1.5 s.
512 games (pool F350 342.9K, F800 297.8K): all lazy/fixed arms −1..−24%; fast C4 lazy 329.5K (< pool F350); bound C4A1 386.7K.
Readings: (1) precise waits + lazy ≈ +2-3% over pass 1 — within the pool's ~2% spread at 2048, still losing at 512. (2) STREAMS=1 collapses (−95%): a single
stream cannot serve a 350 us forward every 200 us window — a real constraint of per-window batching (forward <= window or >= 2 streams); STREAMS=2 ≈ unbounded.
(3) ROOT CAUSE of the residual idle found: a cohort activated mid-segment (lazy growth or per-slot refill after one finishes) must still complete all 64 ticks,
so it runs ALONE at the segment end paying the full round trip per tick; lazy growth manufactures one such straggler per idle event. Even the 150 us-forward arm
at 512 idled 11% for this reason while running +19% per core. Fix = group-synchronous refill (SCHED_GROUPFILL, pass 4) + borrow-when-idle (pass 3).
Decision-rule status: NOT met (+3% < 10%).

## Pass 3 RESULT — borrow-when-idle hybrid (2026-10-12 14:25 UTC; screens3/summary.txt; replay_sched3; all hashes identical) — DECISION RULE MET at 2048
| 2048 games | pool | hybrid (lazy, borrow if wait > 30 us) | wall/busy | borrowed ticks |
|---|---|---|---|---|
| 5M-like W200/F350 | 333.5K | C2 370.8K (+11.2%), C4 359.5K (+7.8%), C8 339.1K (+1.7%) | 0.97 / 0.96 / 0.95 | 4.7% / 4.4% / 5.9% |
| 15M-like W400/F800 | 292.9K | C2 333.8K (+14.0%), C4 322.6K (+10.1%), C8 293.8K (+0.3%) | 0.95 / 0.95 / 0.92 | 6.2% / 7.1% / 8.0% |
Fixed A with eager borrowing (threshold 0): 20-42% of ticks borrowed, gains only +0.5..+8% — eager borrowing erodes residency; the threshold (30-100 us) is
what keeps borrowing to the idle gaps. b100 ≈ b30.
512 games (pool F350 341.9K, F800 302.3K): mixed — C2 lazy b30: −10.8% at F350 / +10.8% at F800; C8 lazy b30 +1.3% / −7.8%; C4A2 b0 +2.0%; ceiling (no latency) is only +8%.
MECHANISM (what enables the win): ownership gives residency (own 2-4 games stepped 93-95% of the time, hot set fits L2); borrowing fills the latency gaps
with ~5-7% cold ticks instead of idle; tail stealing/splitting fixes P/E imbalance at 3-5% instead of 13-25%. Small cohorts are essential (C8 loses the gain).
Status: single runs (pool spread ~2%); pass 4 (group-synchronous refill, fixed A x small C, matched F150 control) running for the repeat + the straggler fix.

## Pass 4 RESULT — repeat + group refill + fixed A (2026-10-12 14:57 UTC; screens4/summary.txt; replay_sched4 (refill bug fixed 14:27, pass restarted); all hashes identical)
REPEAT of the pass-3 winners (lazy growth, borrow if wait > 30 us), 2048 games (pool F350 327.9K / 333.5K repeat = 1.7% spread; F800 290.7K; F150 345.8K):
C2: +13.9% at F350, +15.2% at F800 (pass 3: +11.2 / +14.0); C4: +10.3% / +11.5% (pass 3: +7.8 / +10.1). wall/busy 0.95-0.97, borrowed 4-7%.
Lean forward (W100/F150) vs the matched pool F150: C2 lazy 390.0K = +12.8%; C4A2 gf 363.7K = +5.2%.
512 games (pool F350 338.6K, F800 297.5K, F150 346.9K): C2 lazy b30 −10.8% at F350 (pass 3 −10.8%), +12.3% at F800 (+10.8%); C4 −10.5% / +4.6%;
fast C2 lazy 365.0K = +5.2% vs F150.
Fixed in-flight count + group-synchronous refill + b30 (C ∈ {1,2,4}, A ∈ {2,3,4}): borrow 22-75% of ticks, −60%..+9% — over-borrowing; the hot set must grow
lazily from demand, not be set. Group refill without borrowing: C4A3 −1.0% at 2048 (pass 2: −2.3%) → the mid-segment straggler was a minor leak, not the main one.
DECISION RULE MET TWICE at 2048 (≥ +10%, wall/busy ≥ 0.95). Open: the 512/F350 loss (short waits < 30 us neither borrowed nor avoided) → pass 5
(threshold scan 0/5/10/30/60 us, threshold-free FIT rule with self-measured cold factor, C=1).

## Pass 5 RESULT — knobs (2026-10-12 15:32 UTC; screens5/summary.txt; replay_sched4 (threshold) + replay_sched5 (FIT); all hashes identical)
Borrow threshold 0/5/10/30/60 us: NO EFFECT — 2048: +10.7..+11.4% at F350, +13.2..+14.2% at F800; 512: −11% at F350, +12% at F800 for every value.
→ the knob goes: borrow whenever none of your own is ready. The 512/F350 loss is therefore not short waits; it is the 64-tick segment tail (pass 6).
Threshold-free FIT rule (borrow only a ready cohort whose EWMA cost x self-measured cold factor (≈1.3-1.4) fits the wait): 2048: C1 +11.4% / +12.2%,
C2 +10.7% / +12.9%, C4 +6.1% / +8.3%; 512: C1 −8.4% / +7.2%, C2 −12.2% / +6.0% — matches plain borrowing at F350, gives up 2-6 points at F800 (it refuses
borrows that would overrun the wait; at long latency those borrows were paying). Single-game cohorts (C1) ≥ pairs everywhere → cohort size knob goes too.
Window = today's launch rate (W400 + F350): C2 +8.7% at 2048 (vs +11% at W200). Lean forward (W100/F150) vs matched pool F150: C2 fit +10.5% at 2048.
CURRENT KNOB-FREE DESIGN: per-game ownership, lazy active-set growth, borrow-when-idle (plain or FIT), tail steal/split, segment = batch horizon (pass 6).

## Pass 6 RESULT — segment length (2026-10-12 15:58 UTC; screens6/summary.txt; replay_sched5; all hashes identical)
512 games (pool F350 340.5K, F800 296.2K), C2 lazy b30: seg64 −10.6% / +13.1% → seg512 (champion horizon) −8.8% / +16.6% → seg4096 (no barrier) −2.9% / +19.7%.
C1 fit: −7.9% / +8.4% → −9.3% / +10.2% → −5.2% / +17.7%. The barrier tail was real at 512 (each 64-tick barrier aligns every core's remaining games in
flight with nothing to borrow) but even barrier-free the 350 us case stays −3%: per-core +12% (382K busy vs 340K) eaten by 3.5% idle + ~9% imbalance/overhead
(busy spread 5.37-5.59 s, wall 6.35 s). At 512 the pool is already near L2-resident and its 4-deep pipeline hides 350 us (−6% vs F0), so the prize is small.
2048 games (pool F350 333.4K, F800 290.4K): segment length NEUTRAL — seg64 / seg128 / seg2048: C2 b30 +11.2 / +11.4 / +11.8% at F350; +14.0 / +15.3 / +10.2% at
F800; C1 fit +11.4 / +12.5 / +10.9% at F350. Use the batch horizon as the segment; nothing to tune.
SUMMARY SURFACE (2048, knob-free C1/C2, hashes identical, reproduced): +11-14% at F350, +10-15% at F800, +10-13% at F150; 512: +17-20% at F800 with the
horizon barrier, −3..−9% at F350 (tie at best). Pass 7 running: window = forward (W350/F350, W800/F800) and the big-forward window (W1400/F330 → 512-row forwards).

## Pass 7 RESULT — window vs forward size (2026-10-12 15:44 UTC; screens7/summary.txt; replay_sched5, C1 lazy borrow-when-idle, seg128, 2048 games; hashes identical)
pool F350 329.7K / 335.5K (1.8% spread), F800 288.2K, 4x512 layout F330 251.5K.
W = F (one stream keeps up, forwards = today's size/rate): W350/F350 364.8K (+10.7%); W800/F800 305.0K (+5.9%). W200/F350 374.5K (+13.6%, 2x launch rate).
Big-forward windows (the 11-Oct GPU lever "fewer forwards"): W700/F330 (256-row) 347.3K (+5.3% rollout; GPU side would add ~2-3%); W1400/F330 (512-row)
305.0K (−7.5% rollout; the measured PPO gain from 4x fewer forwards was ~+5% → net ≈ −3%). STREAMS=1 at W1400 identical (one stream suffices).
READING: set the window equal to the forward time. The rollout side then gives +10.7% (5M-like) / +5.9% (15M-like) at 2048 with GPU traffic unchanged;
longer windows to fatten forwards cost more residency than PPO gains. The 15M number is smaller because the 800 us round trip forces ~16 games hot per core.

## Pass 8 RESULT — event-driven readiness (2026-10-12 15:58 UTC; screens8/summary.txt; replay_sched6; hashes identical)
512 games, champion horizon (seg512), C1: ev0 vs ev1 identical within noise — W350/F350 −6.7 / −6.4%; W200/F350 −5.0 / −6.9%; W800/F800 −2.3 / −3.4%; idle 0.8-0.9 s
in both. C2 at W350/F350 ev1: −2.2% (idle 0.27 s). → the 512 idle is NOT sleep latency or scan cost: nothing is ready anywhere. Population-size effect
(Little's law): 24 cores x (550 us round trip / 65 us step) ≈ 300 games must be in flight; at 512 each core owns 21, activates them all, then has nothing
new to add when a readiness gap arrives; at 2048 a dry core starts another of its 85 own games (immediately steppable). The pool's 4x128 pipeline is
exactly balanced for 512/24/350 us (−6% vs F0). SELECTION RULE = mechanism: per-core ownership pays at ≳ 40 games per core (2048/24 = 85 ✓, 1024/24 = 43 borderline, 512/24 = 21 ✗).
2048 games (seg128): ev1 slightly better — W350/F350 +11.0% (ev0 +9.4%), W800/F800 +6.1% (ev0 +4.7%), idle 0.11 vs 0.35 s. Keep event-driven readiness.
HARNESS CAMPAIGN CLOSED 16:00 UTC. Final: REPORT.md.

## Pass 9 RESULT — population scaling (2026-10-12 16:25 UTC; screens9/summary.txt; replay_sched6 final design C1 lazy borrow event seg128, W = F; hashes identical)
| agents | pool F350 | hybrid W350/F350 | pool F800 | hybrid W800/F800 | zero-latency bound |
|---|---|---|---|---|---|
| 2048 | 333.5K | 370.2K (+11.0%) | 291.2K | 308.9K (+6.1%) | 400K |
| 4096 | 326.9K | 372.0K (+13.8%) | 287.5K | 321.7K (+11.9%) | 453K |
| 8192 | 329.5K | 368.0K (+11.7%) | see summary | see summary | 457K |
Env side of this box saturates at ~370K from 2048 agents up (24 cores x ~63 us per L2-warm step); pool flat at ~330K; balance 98% of ideal at scale, idle < 0.1 s.
Step-cost curve vs games in rotation per core: 1 → 52 us (L1), ~4 → 60, ~8 → 63, ~16 → 72, 21 (pool) → 72, 85 → 96 us. The first step (L1 → L2) is structural:
any latency hiding by other games pays it; the hybrid's contribution is staying at 4-16 instead of 21-85. The remaining 18% to the bound is that L1 loss.
Path to 1M: not this box (needs 2.6x core-seconds); per-core residency makes env scale with cores → ~65 cores at this step cost (80-100 server cores),
≥ 4096 agents; GPU: PPO ~485K steps/s at 5M on the 4090 → fine at 1-2M params, H100-class or 2 GPUs at 5M. Next cheap step: run the harness on a big-core box.

## I-cache test (callgrind cache sim, 1 worker, 32 games, 768 ticks, I1/D1 48K 12-way, LL 2 MB; icache/) — I-CACHE REFUTED
per step: I1 misses 1,139 / 1,151 / 1,152 at rotation 1 / 4 / 16 (constant); D1 read misses 235 → 485 → 495, D1 write 118 → 235 → 236; LL misses 7-13.
Rotation costs ~+370 L1 data misses per step ≈ 1-2 us — not the 11 us measured (52 → 63 us). Remaining suspect: branch prediction (census 5.4K
mispredicts/step ≈ 20 us; predictor state is per game). Branch-sim run queued (icache/branch.sh).
Branch-sim (callgrind --branch-sim, same config): conditional mispredicts per step 2,663 / 2,777 / 2,819 at rotation 1 / 4 / 16 (+4-6% ≈ 0.5 us); indirect
mispredicts flat (38/step). BRANCH PREDICTION REFUTED as the rotation cost. Neither I1, D1 nor branch simulation explains the 52 → 63 us step → measuring the
rotation cost natively (1 core and 24 cores, F=0, A = 1/4/16) to isolate it from latency and multi-core effects (icache/native.sh).

## Native rotation cost (icache/native.sh, 2026-10-12 16:45 UTC; replay_sched6 C1 fixed A, group refill, no steal, F=0; hashes identical per config)
1 core, 32 young games (warm 2048): rotation 1 / 4 / 16 → 23.5 / 27.2 / 29.4 us per step (+16% / +25%).
24 cores pinned, 2048 mature games (warm 4096): rotation 1 / 4 / 16 / 64 → 51 / 56 / 62 / 86 us per step (busy 468K / 430K / 387K / 279K); +9% / +21% / +68%.
→ the step-cost curve is confirmed natively: the first step (1 → 4) is +9-16%, 4 → 16 another +11%, 16 → 64 (out of L2) +39%. Cause of the first step
NOT identified: callgrind I1 misses flat, D1 misses +370/step (~1-2 us), branch mispredicts +4-6% (~0.5 us). Needs hardware counters (host perf_event_paranoid).

## TRAINER BUILD (2026-10-12 16:50-17:00 UTC; trainer/ = copy of engine-scaling trainer_cohort/source; DESIGN.md; build.py sched_ctrl (control, unchanged
source, binary c9dac4b0) and sched_v1 (patched); binaries symlinked into nethack-24h-20261009/binaries)
Patch: src/env_sched.h (ownership + lazy active set + borrow-when-idle + timed inference ring, workers never sleep) and pufferl.cu: PUF_SCHED=1 path —
per-agent recurrent state (sched_state) and sampler RNG (sched_rng, initialised per agent exactly as the pool's rng_states[buf][row]); slot threads
gather up to R=agents_per_buf ready agents per window (window = forward-time EWMA or PUF_SCHED_WINDOW_US), upload as one block, run a per-slot
captured graph (gather state/rng → zero_term → snapshot t==0 rows → pufferl_forward_step → scatter state/rng → record_step_scatter to (tt, agent)),
D2H actions, scatter to agents, hand them to owners. Segment = horizon (rollout_start/finish hooks); async write_slot via tt = slot*H + t.
Replay hook for PUF_ACTION_REPLAY indexes the file by the agent's own t. New PUF_LIVE_PROOF (FNV over all host observations per epoch).
SMOKE (fast protocol, 5M/2048, 16x128, 4 slots, 24 pinned workers, 6 epochs): runs; BATCH_PROOF epochs 0-4 IDENTICAL to the pool control
(0375f42a96cddeee, ff5b905b6870fb65, 167efab0075754ff, 05e04c8c49497685, 8c5cbf1f77dee379 — also = the mt7_pgo-engine control of 11 Oct);
rows per forward 121-126; borrow 8-11%; idle ~4% of busy. A/B (ctrl / sched / ctrl repeat, 44 epochs from 32, PUF_STATE_PROOF) running.

## TRAINER A/B #1 (17:05 UTC; fast protocol 5M/2048 16x128, 24 pinned workers, 44 epochs from 32; nethack-24h-20261009/runs/sch_ab_*)
GATE PASSED: BATCH_PROOF identical for all 44 epochs; PUF_STATE_PROOF master / momentum / updates IDENTICAL after 44 epochs of training on the
scheduler's rollouts (rollout.hashes differ only in the per-buffer state buffers, which are staging slots under PUF_SCHED — expected). The gather/scatter
path, per-agent state and RNG are exactly right. SPS: ctrl 322.3K / 323.6K, sched 281.8K (−13%). Stats: workers 94% busy, 80 us per step (pool ≈ 67),
borrow 6-8%, rows/forward 111-113, forwards 2330-2360/epoch (ideal 2097). Hypotheses: (a) longer round trip (window = forward-ewma, forward includes
gather/scatter + 6 H2D) → larger hot set; (b) 4 slot threads spinning + 512 KB memcpy per forward on the P-core SMT siblings 1,3,5,7 hurt workers 0-3
(shared L2 + execution). v2: fwd time + hot-set instrumentation, PUF_SCHED_SLOT_SLEEP_US; knob sweep (window 150/250 us, slot sleep).

## TRAINER knob sweep v2 (17:12 UTC; sched_v2; 5M/2048; ctrl 322-324K)
default 280.8K | window 150 us 277.2K (5031 forwards, 52 rows) | window 250 280.2K | slot sleep 20 us 282.4K | w200+sleep 281.8K | 8 slots 265.1K.
DIAGNOSIS: hot_set_mean = 28-31 games per core (harness design point ~8-10), us_per_step 80; forward_us 428-573 (pool 290-390). The hot set ratchets:
the forward time varies under PPO contention (async), every long round trip makes a worker activate more parked games, and active games stay active for
the rest of the segment. The harness had constant latency and never saw it. Window/slot-thread knobs: no effect (not the mechanism).
FIX (v3): self-tuning cap — per worker round-trip EWMA and step-time EWMA; activate only while in-rotation < K * rt/step (K=1.25 default); a returning
game above the cap is parked again (deactivated). Knob-free: both quantities are measured online.

## TRAINER v3 — self-tuning hot-set cap (17:15 UTC; 5M/2048; ctrl 322-324K)
adaptive k=1.25: 317.7K (cap 9.2, hot set 13.8, 70.2 us/step, borrow 15.5%) | k=1.5: 318.7K (cap 10.8, hot 16.5, 70.1 us, borrow 8.9%) | k=1.0: 317.2K (hot 11.2, borrow 26.7%)
fixed cap 10: 321.2K (hot 9.8, 69.1 us, borrow 35%) | fixed cap 16: 324.1K (hot 15.5, 68.6 us, borrow 13.7%). rt 447-459 us, forward 455-460 us, rows 113-115.
The cap removes the ratchet (hot set 29 → 10-16, step 80 → 69-70 us) and brings the trainer to PARITY with the pool. Not yet the harness gain: the
harness measured 60-63 us/step at this rotation. Remaining suspect = the 4 slot threads' 512 KB host memcpy per forward + spinning on the P-core SMT
siblings 1,3,5,7 (shared L2 with workers 0-3) — the harness had no such threads. v4: zero-copy gather (device kernel reads the pinned host rows by index,
cudaHostAllocMapped), no CPU copy; per-core-type step cost in SCHED_STATS.

## TRAINER v4 (17:20 UTC): zero-copy arms aborted at setup (OBS_SIZE 4184 is not a multiple of 16; gather kernel now copies 8-byte units → v5).
Memcpy variant with per-core-type stats (k=1.5): 318.3K; P-cores 61.3 us/step, E-cores 75.4 (pool steady state 10-11 Oct: P ≈ 59, E ≈ 71); hot set 16.5,
borrow 8.6%. Pool control repeat: 323.9K. → the scheduler's steps cost +4% (P) / +6% (E) over the pool's at a hot set the native curve prices at 62 us.

## TRAINER v6 — zero-copy gather (17:25 UTC; 5M/2048; ctrl 322-324K; BATCH_PROOF identical to the pool)
k=1.5: 325.7K (hot set 16.8, P 60.2 / E 74.7 us per step) | fixed cap 16: 331.5K (+2.4%; hot 15.4, P 58.6 / E 74.0) | k=1.5 + slot sleep: 326.7K.
Zero-copy removes the slot threads' 512 KB CPU memcpy per forward: P-core steps fall from 61.3 to 58.5-60 (= the pool's P cost). E-cores stay 74-75 vs
the pool's 71 (1 MB L2 share, hot set 15-17 x ~55 KB fills it). Forward 456 → 540 us (byte-granular PCIe gather of 612 KB + mask). Leaks: (1) the
segment-start burst (all agents forwarded at t=0) inflates the round-trip EWMA → cap jumps → hot set 2x the steady cap, shrinking slowly; (2) gather cost.
v7: round-trip EWMA ignores t==0 returns; 2-byte gather units (OBS_SIZE 4782 is even).

## TRAINER v7 (17:30 UTC; burst-excluded rt EWMA, 2-byte gather; ctrl 323.2K; BATCH_PROOF identical)
adaptive k1.25 323.8K (hot 14.2, borrow 16.5%) | k1.5 324.2K (hot 16.6, borrow 9.7%) | k2.0 321.4K (hot 20.5, borrow 5.5%) | cap12 328.5K (+1.6%; hot 11.7,
borrow 26.9%) | cap16 329.1K (+1.8%; hot 15.5, borrow 14.6%). P-core steps 57.4-61.0 us (pool ≈ 59); E-core steps 74.5-75.6 at EVERY hot set 12-21 (pool ≈ 71).
Readings: the hot set is no longer the lever at 12-21; cap_mean is an end-of-segment snapshot (short tail round trips) so adaptive hot sets sit ~1.6x it —
the adaptive rule is fine, the design point is just rt/step ≈ 9-10 here. The E-core excess (+4 us) is borrow-cold returns: P-cores exhaust their capped own
work first and borrow E-core games (14-27% of ticks), which return cold to their owners. v8: weighted initial ownership (PUF_SCHED_PWEIGHT: P-core workers
own more games so the speed gap is covered by ownership, not cold borrows) + per-core-type borrow stats; also a 2-slot arm.

## TRAINER v8 — weighted ownership (17:35 UTC; 5M/2048; ctrl 323.2K)
cap16: 330.0K (+2.1%; borrow 14.3%, taken_from_P 8K / from_E 29K: P-cores borrow E games) | cap16 + PWEIGHT 1.25 (P own 98, E own 79): 336.2K (+4.0%;
borrow 15.2% now symmetric 21K/19K; E 73.4 us) | PWEIGHT 1.5: 331.9K | cap12 + pw1.25: 332.3K (borrow 28.5%) | k1.5 + pw1.25: 324.9K (hot 17, borrow 8.7%) |
2 slots: 322.2K (forward 613 us, borrow 24.7%, E 80.4 — fewer inference threads starve the ring).
Per-core: P 57.2 (pool 59), E 73.4-74.8 (pool 71). E-core excess ≈ borrowed cold ticks (E does 10% of its steps on borrowed games, 12% of its own come back
cold); borrowing fills idle, so shrinking it via a bigger hot set (k2.0) loses more. Optimum cap 12-16 + pw1.25 → +3-4% at 5M/2048 (single runs; pool spread 0.5%).
Trainer vs harness: trainer pool steps are ~5 us cheaper than the harness pool emulation, trainer hybrid steps ~5 us dearer than the harness hybrid → the
harness's +11% was partly emulation optimism (no real data movement, no PPO, deterministic latency). Next: repeats + 5M/4096 + 15M/2048.

## TRAINER RESULT — real config shapes (17:50 UTC; fast protocol; sched_v8 cap16 + PWEIGHT 1.25 unless noted; all BATCH_PROOFs identical to the pool)
| shape | pool (cohort knobs, 24 pinned) | scheduler | gain |
| 5M/2048 (16x128, H128) | 323.4K / 323.2K | 335.6K / 335.3K | +3.8% (reproduced) |
| 5M/4096 (32x128, H64) | 354.6K | 364.0K (cap16 plain 360.1K) | +2.7% |
| 15M/2048 (width 1024, real frozen weights) | 237.6K | 215.0K (cap24: 213.6K) | −9.5% |
15M mechanism: inference-bound regime — forward 990-998 us under PPO contention (pool 790), rt 1.2-1.3 ms, workers idle 35% waiting on the GPU, borrow 28%;
the per-forward gather/scatter + PCIe read overhead (+~200 us) is paid 2100 times per epoch. Selection rule holds: pool at 15M (GPU-bound), scheduler at 5M.
Gap to the harness (+11% predicted at 5M/2048): trainer scheduler steps cost P 57 / E 72.5 us (harness ≈ 53 / 69), the pool's P 59 / E 71. Borrowed cold ticks
(15-18% of steps, symmetric after weighting) are the main residual; next: same-L2-cluster borrow preference (E-core clusters of 4 share 4 MB L2).

## TRAINER v9 — same-L2-cluster borrow preference (17:45 UTC): NULL. cluster 334.2K / 335.2K vs no-cluster 335.6K; E-core steps 72.9-73.4 either way;
cap12+cluster 333.3K. The E-core residual (~2 us over the pool) is not cross-cluster coldness. Trainer result settled: +3.8% (5M/2048), +2.7% (5M/4096).
Closing checks: live-action A/B with PUF_LIVE_PROOF (frozen random policy → hashes must match the pool); CUDA batched-memcpy availability for the gather.

## 2026-10-13 22:40 — pending items from 12 Oct landed
LIVE PROOF: PUF_LIVE_PROOF (FNV over all host observations per epoch) IDENTICAL for 44 epochs, scheduler (sched_v9, cap16 pw1.25) vs pool (sched_v9
pool path), live actions from the frozen random policy: the sampler/action-scatter path is bit-exact too. Live SPS 315.2K vs 278.8K (young-game regime).
BATCHED-DMA GATHER (sched_v10, PUF_SCHED_ZERO_COPY=2 = cudaMemcpyBatchAsync of the 2R row copies): first pass (not interleaved, box freshly idle after the
PR tests): batch 365.5K / 369.8K, batch cap12 374.4K, kernel gather 354.3K, ctrl 348.2K; forward 490-494 us (kernel gather 695 in this pass); BATCH_PROOF
identical. Today's control is 8% above yesterday's 323K (thermal state after hours of back-to-back runs yesterday?) → interleaved repeat running.
PR 693 side result (today): the stock upstream trainer gains +56% at the shipped config (h512 x 4 buffers) from the cuBLAS per-stream workspace fix
and becomes deterministic there; the experiment stack already contains that fix.

## 2026-10-13 22:35 — interleaved repeat, batched-DMA gather (sched_v10; 5M/2048 fast protocol; 24 pinned; cap16 pw1.25; BATCH_PROOF identical)
ctrl 347.3K / 346.3K | kernel gather (zero-copy=1) 357.2K / 358.9K (+3.2%) | batched DMA gather (zero-copy=2) 368.8K / 375.6K (+7.3%) | batched + cap12
372.0K / 378.0K (+8.1%). forward 486-499 us with the batch copy vs 700 with the PCIe gather kernel. Step costs today P 47-49 / E 63-64 us (yesterday
57 / 73: the box runs ~15% faster per step after a cool night; relative comparisons within a session only).
READING: replacing the gather kernel with cudaMemcpyBatchAsync halves the per-forward overhead and doubles the trainer gain to +7-8% at 5M/2048.
Next: cap scan 8/10/12/14 with the batch gather; then 5M/4096 and the handoff patch refresh.

## 2026-10-13 22:40 — ROTATION COST ATTRIBUTED (hardware counters via host-side perf attach; 1 P-core, 128 games, 40 s windows; perf_rot/perf_rot*.txt)
| per 1000 instructions | rot 1 | rot 4 | rot 16 | rot 64 |   step us: 27.4 / 30.7 / 34.1 / 35.5
| cycles (CPI x1000) | 350 | 391 | 434 | 450 |
| branch misses | 2.97 | 4.17 | 5.30 | 5.44 |   (miss rate 1.40% → 1.96% → 2.50% → 2.56%)
| L1d load misses | 2.44 | 2.87 | 2.90 | 3.07 |
| L1i misses | 7.10 | 7.29 | 7.74 | 7.87 |
| dTLB / iTLB misses | 0.01 / 0.01 | 0.01 / 0.01 | 0.01 / 0.01 | 0.12 / 0.01 |
| LLC loads | 0.01 | 0.01 | 0.18 | 0.60 |
MECHANISM: the 1 → 16 step is BRANCH PREDICTION — +2.3 mispredicts per 1000 instructions (+78%) ≈ 45-50 of the +84 cycles/Kinstr; L1d misses +19%
(≈ 10-15 cycles); frontend +9%; TLB nil (explains huge pages +1%). The real predictor is history-based and loses the game's control-flow context when
other games run in between; callgrind's simple branch model (+5%) missed it. 16 → 64 adds the L2-overflow regime (LLC loads x3, dTLB x10).
Levers this implies: fewer games per core (the scheduler, done), less data-dependent branching in the monster turn / movement code (engine), or
PGO vs plain comparison (tonight). Instruction cache dominates misses at every rotation (7/Kinstr) — a code-footprint item independent of rotation.

## 2026-10-13 22:45 — cap scan with the batched gather (5M/2048; ctrl 357.9K / 348.8K)
cap8 374.1K | cap10 375.3K | cap12 365.6K (perturbed: step 74 us vs 58 in its neighbours) | cap14 377.1K | cap12+pw1.5 363.9K (also perturbed, 69 us) |
adaptive k1.5 358.1K (hot set 21: the adaptive rule overshoots now that the forward is ~490 us). Optimum is broad, cap 8-14 ≈ +6-8%; keep cap 12-14 fixed
(or adaptive with k≈1.0). Borrow fraction rises as the cap falls (31% at 14, 55% at 8) without hurting throughput — borrowed ticks are cheap when the
borrowed game sits in a shared E-cluster L2 or was just forwarded. Overnight queue (overnight/overnight.sh, LOG.txt) started 22:45: phase D map →
A rotation perf matrix (G1/G3/topdown/record) → B PGO vs plain → C trainer perf pool vs sched → E live LEARNING proof pair → F PR693 ws32.
