# Latency program (14 Oct 2026): shrink the inference round trip so the per-core hot set (rotation) can fall from ~12 to 2-4 games

Premise (measured): workers are ~92% busy; the per-step cost carries a rotation tax (P-core cycles/Kinstr 350 @rot1, 392 @rot4, 434 @rot16);
the hot-set cap is set by round trip / step (cap = 1.25 rt/step + 1 ≈ 12 at rt 390 us, step 50 us); the forward is graph-captured already, so
rt is GPU time for 512 rows (+ DMA + wake-ups). Question: what is the round trip for 128-256-row forwards (8-16 slots), and does a smaller cap
then pay? Decision rule: SPS at 5M/2048 above the 4-slot/cap-12 control in the same session, with SCHED_STATS cap_mean and rt_us explaining it.
Second measurement: the E-core rotation ladder (16 of 24 workers are E-cores) — the P-core ladder may understate the prize.

## 10:05 — forward anatomy (nsys timeline of fast32_profile_node, pool path, hidden 1024 x 4 layers, 512-row buffers) and the scheduler's sizing
One inference forward = 67 kernels back to back (GPU busy 371 us = span 376 us: NOT launch-gap bound); minGRU 4 x (gemm 29-33 us on a 48-block
grid + gate 6 us) = 145 us, ~20 cutlass matmuls 2-16 us, inventory/encoder kernels ~60 us, sample 12, record 8. These are latency/occupancy floors
of small kernels, not FLOPs. The fused recurrent prototype (rec_fused.cuh) is B=512/H=1024-only (embedded cubin) and off.
Scheduler path (sched_forward_body): the forward is captured for R = agents/slots = 512 rows per slot but fills n ≈ 121 rows on average
(SCHED_INFER rows_per_forward=121.3, forward_us=483 at 4 slots) → ~4x oversized GPU work per forward; 3300 forwards/s x ~0.4 ms GPU = the GPU
is saturated by 4 overlapping low-occupancy chains, which inflates every forward's latency, which sets rt (393 us), which sets the hot cap (12),
which sets the rotation tax (~22% of step cycles). Lever: size the forward to the rows actually used (more slots → smaller R, or row buckets),
cut the GPU time per forward ~3-4x, let rt and the cap fall. The slots x cap sweep (stage 1) is the first measurement.

## 10:12 — stage 1 results (E/P ladders + slots x cap sweep, 5M/2048)
Ladder (one worker, 128 games): P-core rot1 36,724 / rot4 32,680 / rot16 29,529 steps/s (−11% / −19.6%); E-core 23,960 / 21,915 / 20,544 (−8.5% / −14.3%).
Sweep: s4 cap12 394K & 368K (fwd 479-490 us, rt 372-389, rows/fwd 120) | s8 adaptive 332K (fwd 683, rt 533) | s16 adaptive 253K (fwd 1409, rt 1047)
| s16 cap4 253K (borrow 82%) | s8 cap6 318K | s4 cap6 363K (borrow 65%).
Reading: rows per forward stay ~120 whatever the slot count, and forward latency grows with concurrent slots → the GPU is bound by kernel count
(~3,300 forwards/s x 67 kernels ≈ 220K dependent launches/s at 3-5 us occupancy each), not by rows. More slots cannot shrink the forward; a
smaller cap starves at the current rt. The lever is the number of kernels per forward (fusion / persistent kernel). Next: mock-forward
experiment — replace the forward body with K tiny kernels (recorded actions make the outputs irrelevant) to measure SPS/rt/cap vs K.

## 10:14 — stage 2: mock-forward sweep (sched_v14: PUF_SCHED_MOCK_FORWARD=K replaces the whole forward body with K dependent 128x256-thread
kernels of ~64 FMAs; recorded actions make the outputs irrelevant). Arms: real cap12 (x2 control), K = 67 / 20 / 10 / 4 / 1 with adaptive cap,
K = 10 cap 4. Reads: SPS, forward_us, rt_us, cap_mean, step_us (pure engine step = the rotation tax), P/E per-core step cost.
Decision rule: if K ≤ 10 with adaptive cap lifts SPS ≥ 8% over the real forward, build the fused inference forward (≤ 10 launches) for the
5M/512 config; validate by tolerance vs the current forward and a learning-curve pair; then consider the persistent-kernel form.

## 10:18 — stage 2 results: mock forward, 5M/2048, same session (real forward = 67-kernel chain)
real cap12 382.6K / 380.7K (fwd 447-490 us, rt 373-380, cap 12, hot set 11.7) | K=67 374.9K (fwd 212, rt 208, cap 4.0) | K=20 400.5K (fwd 148,
rt 174, cap 4.4) | K=10 410.1K (fwd 123, rt 129, cap 3.3, hot set 7.9) | K=4 419.4K (fwd 77, rt 98, cap 2.8, hot set 5.5) | K=1 407.7K (fwd 47,
rt 73, cap 2.2: too tight, borrow 33%) | K=10 cap4 414.8K.
Per-core step cost (noisy ±5 us run to run): E 68.5/62.7 → 55.9 at K=4; P 52.2/47.4 → 45.4.
Reading: a forward of ~4-10 launches (~80-120 us) is worth +8-10% SPS at 2048 over the current scheduler (+18-20% over the pool) by letting
the hot set fall to ~3 games; below rt ≈ 100 us the cap gets too tight for the borrow/park mechanics (K=1 loses). The slot/gather structure
(slot threads, DMA, D2H, sync) is still in place in the mock; a persistent kernel would also remove those. Next: the same mock at 4096/8192
agents vs pool and vs real scheduler, to see whether the latency path is also what makes the scheduler win at larger populations.

## 10:25 — stage 3: populations (horizon 64/32, buffers 32/64, same session)
4096: pool 406.0K | sched real 412.0K (fwd 514, rt 388, cap 12) | mock K=4 455.0K (fwd 86, rt 96, cap 2.8, hot set 6.1) → +12% over pool.
8192: pool failed (training-graph instantiate at 64 buffers with this binary; the 2026-10-13 map had pool 451K here) | sched real 427.8K (fwd 596,
rt 764, cap 12) | mock K=4 474.2K (fwd 117, rt 185, cap 6.1, hot set 8.9) → +11% over the scheduler, ~+5% over the earlier pool.
Reading: the latency path scales with population; with the engine E (+4.8%) and header C (+1.3%) on top, 8192 lands at ~500K on this box.
DECISION: build the fused inference forward in exact-first stages: A = fold the 7 scheduler housekeeping kernels into 2 and the ~15 obs-only
encoder gather kernels into 1 block-per-row kernel (bitwise identical; LIVE_PROOF must match), B = minGRU 4 layers in one cooperative kernel +
grouped encoder GEMMs + merged entity kernels (tolerance + learning pair), C = decoder/sampler/record fusion. Baseline the launch count first.

## 10:45 — Stage A built (sched_v15): PUF_SCHED_FOLD=1 folds the 7 housekeeping kernels into sched_pre_kernel / sched_post_kernel (same
element-wise ops in dependency order); NH_FRONT_FUSED=1 replaces the 17 observation-only encoder kernels (decode, crop, loc3 gather, terrain,
inventory decode x2 / features / gather, blstats, message ids + pool, monster/item tokens, spell keys, doorstep, identity, pass panel) with one
block-per-row kernel, arithmetic unchanged; PUF_SCHED_GRAPH_INFO prints the captured graph's node count. Validation: live-learning digest must
equal 31e2e3deae720ef4 (stage 6, same config) with flags off AND on; fast-protocol SPS off/on at cap 12 and on with adaptive cap.

## 10:41 — Stage A validated (sched_v15): LIVE_PROOF digest 31e2e3deae720ef4 with flags off AND on (bitwise identical forward); graph nodes
64 → 43; forward_us 484 → 383 (rt 377 → 326). SPS flat: off 381.4K / 366.3K, on cap12 375.5K, on adaptive 367.8K (cap 7.5). Reading: the 21
removed nodes were the cheap ones; the remaining 43 carry ~380 us. Next: per-kernel nsys of the fused forward at 5M to pick the targets.

## 10:52 — per-kernel nsys of the stage-A forward (prof_sched_v15, 17,260 forwards captured; GPU busy 602 us per forward summed, 383 us wall)
cutlass::Kernel2 (cuBLASLt bf16 GEMM) x35.3 per forward, 7.0 us each = 246 us + splitKreduce x11.9 = 39 us → cuBLASLt's algorithm choice at
these shapes (M = 512 slot rows, small N, K up to 1698) is split-K with several ~7 us kernels per matmul: ~13 matmul calls become 47 launches
and 285 us. Then: nh_front_kernel 34, sample_logits_heads 24, bf16 gemm 64x64 x1.3 = 21, entity_fused x4 = 20, inv_table x2 = 13 (per-epoch
→ B0), mingru_gate x4 = 11 (→ B1), nh_min_sgate x2 = 7, sched_post 7 / sched_pre 6, nh_ptr3_cos 6, dec_assemble 3, concat 3, eff_embed 3 (B0),
cast 3, zero_term 3 (B0). Stage B2 = one custom small-GEMM launch per matmul (16x64 tiles, fp32 accumulate, bias/ReLU epilogue) for the
encoder matmuls and the decoder, and a padded-row cutoff (blocks whose scheduler row is padding exit) in every fused inference kernel, so GPU
work scales with the ~110 live rows instead of the 512-row slot. Expected: 47 → 9 launches, ~285 → ~60 us; validation by logprob/value tolerance.

## 10:57 — Stage B (sched_v16) FAILED, diagnosed, rebuilt as v18
sB_live_AB0 digest 916e9cf01bb231f9 ≠ 31e2e3deae720ef4: the table refresh keyed on p->epoch is wrong under async — the actor weights are
copied at every rollout_start while epoch increments when training ends, so whole rollouts ran on stale tables. Fix: actor_param_version bumped
in rollout_start; slot threads refresh on that.
B1 (naive FMA fused minGRU): forward 648 us vs 438 (W tile re-read by 32 row tiles, 2-byte loads) and the numerics dump was keyed by
(slot, forward, row) — rows hold different agents/steps across runs, so the deltas were meaningless. Replaced by a tensor-core wmma GEMM
(bf16 x bf16 → fp32, 64x64 tiles, 16-byte loads when K%8==0) used for every inference matmul (encoder bias/ReLU GEMMs, the minGRU input
projection with the original gate kernel kept, the decoder); dump keyed by (agent, step). Stage D (v18) validates: live digest for A+B0,
forward_us / SPS / nodes with the GEMM path, numerics by (agent, step).

## 11:09 — Stage D (sched_v18): B0 fixed and EXACT (digest 31e2e3deae720ef4 with A+B0; graph 64 → 39 nodes). Tensor-core GEMM path (A+B0+GEMM):
graph 37 nodes but forward 620 us (vs 463 AB0, 400-492 off): the wmma kernel is correct in isolation (test/test_wmma: max dev 1 bf16 ulp, 0 bad
on 7 shapes) but SLOWER than cuBLASLt's split-K pieces (73 us for K=1698 on the scalar path, 13-19 us at K=512). In-trainer numerics: |dvalue|
mean 0.005 (one bf16 ulp of an O(1) activation) — fine; |dlogprob| mean 1.15 even at step 0 = sampled-action flips at softmax boundaries from
bf16 rounding chaos, not a bug. SPS: off 373.9K / 380.4K, AB0 352.1K, all 328.0K, all adaptive 345.3K, all cap6 351.3K → nothing gained.
Reading: node count alone is not the lever; GPU time per forward must fall ~3x (rt < ~180 us per the mock) and my kernels did not deliver it.
Answer to "does the megakernel help / did Joseph miss something": unproven so far; the existing kernels are right for the pool's regime
(hundreds of 512-2048-row forwards/s); the scheduler created the small-batch latency regime (3,300 x 120-row forwards/s). Stage E: cuBLASLt
without split-K (workspace 0, reduction NONE) + slot-handle workspace 0 → one kernel per matmul with no new code; stop-loss if rt stays > 200 us.

## 11:18 — Stage E (sched_v19, no split-K) + CORRECTED per-forward anatomy (slot streams only; the earlier aggregation mixed training kernels)
Stage E: off 394.8K / 380.2K (fwd 484/490, nodes 64) | A+B0 389.5K (fwd 384, rt 300, nodes 39) | A+B0+nosplit 391.0K (fwd 399, nodes 36) |
adaptive 381.7K (cap 8.7, hot set 16.2) | nosplit only 372.9K. No gain; split-K was only 3 kernels per forward.
CORRECTION: the slot forward is R = 128 rows (buffers 16), ~94% filled — not 512; the "4x oversized" and "285 us of GEMM" readings were wrong.
Clean anatomy (stage A engine, per forward, slot streams 18-21, 24,637 forwards): 42 kernels, 282 us summed; one-stream wall first→last
kernel 348 us (gaps 20 us) → the forward IS its serial chain, each kernel inflated by 4-slot contention. cutlass GEMM x15 at 8.0 us = 121 us
(+ splitK 9) | nh_front 35.6 | sample_logits_heads 26.4 | entity_fused x4 = 21.5 | inv_table x2 = 12.8 (B0) | mingru_gate x4 = 12.1 |
sgate x2 = 7.4 | pre 6.7 + post 7.2 | ptr3_cos 4.1 | eff_embed 3.3 (B0) | dec_assemble 2.9 | zero_term 2.9 (B0) | cast 2.4 | concat 2.4 |
rownorm 2.3 | cast_rew_term 1.8. PLUS H2D memcpy x5 per forward = 88.7 us on the slot stream (obs/mask batched DMA, ~600 KB at ~7 GB/s),
serialised ahead of the graph → ~85 us of every round trip is the observation transfer.
Round-trip budget at A+B0 (~300 us): DMA ~85 + chain ~280 (after B0) + D2H/sync ~10 + window wait. Target rt ≤ 150 needs: DMA off the
critical path (stream the row copies as games arrive during the window instead of one batch at close; or compress), GEMMs 130 → ~40 (proper
2-3 us kernels at M=128 or grouped launches), front 36 → ~15 (split for parallelism), sampler 26 → ~8, entities 21 → ~8 (one launch).

## 11:27 — Stage F (sched_v20, PUF_SCHED_BORROW_US): THE MECHANISM, MEASURED IN THE REAL TRAINER
off 380.9K / 367.1K (cap 12, hot set 11.8, P-core 48.0/48.9 us per step, E-core 63.6/64.4) | A+B0 cap12 383.4K (rt 299, P 46.4, E 61.8) |
adaptive, borrow 0/100/300 us: 366.9K / 356.4K / 330.9K (cap 8.5-8.8, hot set 16-17, idle 0.017 → 0.141 s/epoch) |
cap 6, borrow 300 / 1000 us: 221.7K / 200.1K — hot set 5.9, per-step cost P 38.5 / 37.7 us (−20%), E 49.7 / 49.1 us (−22%), but idle
0.61 / 0.75 s per epoch (workers wait for the round trip: rt 308-343 us > 5 x 40 us of own work).
Reading: the rotation tax at hot set 6 is worth −20% per step on both core types (ladder prediction confirmed in situ ≈ +25% SPS at zero
idle), and the only thing between us and it is the round trip: cap 6 needs rt ≲ 200 us, cap 4 ≲ 120 us. Current A+B0 rt ≈ 300 = DMA ~85 +
kernel chain ~200 + overheads. Next: streaming gather (issue each game's obs/mask copies as it arrives during the window instead of one batch
at window close) — exact, scheduler-side, worth up to ~85 us; then the GEMM chain.

## 11:31 — Streaming gather built (sched_v21, PUF_SCHED_STREAM=1 on the batched-DMA path): games are popped as they arrive during the window and
their obs/mask copies issued at once (coalesced to 8 rows or 25 us), so the ~85 us of H2D DMA overlaps the window wait; launch rule unchanged
(oldest row age >= window, or R rows) → exact. Stage G: off / A+B0 / +stream at cap 12, adaptive, cap 8, cap 8 + window 150 us, cap 6 + borrow
300 us; live digest for A+B0+stream (target 31e2e3deae720ef4).

## 11:37 — Stage G (sched_v21, streaming gather): EXACT (live digest 31e2e3deae720ef4) but no round-trip gain
off 384.0K / 369.8K (rt 395/382) | A+B0 382.1K (rt 311, fwd 332) | A+B0+stream cap12 398.5K (rt 372, fwd 397, rows/fwd 81) | adaptive 374.4K
(cap 10.5, rt 445) | cap 8 383.9K (rt 366, rows/fwd 55) | cap 8 window 150 380.1K (rt 288, borrow 51%) | cap 6 borrow 300: 250.3K (idle 0.47
s/epoch vs 0.61 before; P 39.1 / E 50.7 us per step).
Reading: issuing the copies early shrank batches (81 → 55 rows per forward), raised forwards/s and GPU contention, and the round trip did not
fall (372 vs 311). The 398K is the day's best single 2048 number but inside the ±4% session noise.

## CLOSE-OUT of the latency program (11:40)
Established, in the real trainer: the rotation tax is worth −20% per step on P-cores and −22% on E-cores at a hot set of 6 (cap-6 arms, two
sessions), i.e. ~+25% SPS at zero idle; the gate is the inference round trip, which must be ≲ 200 us for cap 6 (≲ 120 for cap 4); it is ~300-
390 us here and did not move below ~290 with any exact change (fold, front fusion, per-rollout tables, no split-K, streaming gather, windows).
The forward is a ~36-42-kernel serial chain of 3-36 us kernels sharing the GPU with the PPO update for ~75% of every rollout (async
overlap), so each kernel runs inflated; the GEMM replacement (correct, tensor cores) was slower than cuBLASLt at these shapes. The mock's
ceiling (+10% at 2048, +12% at 4096, 474K at 8192) remains the measured prize; reaching it needs a resident/persistent inference kernel that the
training kernels cannot stretch, which is a multi-day build with the contention risk unresolved. PARKED. Kept: all stages are env-gated and off
by default in the trainer copy; A+B0+stream are bitwise exact (three live digests) and harmless.
