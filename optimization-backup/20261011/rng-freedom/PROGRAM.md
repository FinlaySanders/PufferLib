# NetHack RNG-stream freedom program — opened 2026-10-11 15:20 UTC

## Decision
User, 2026-10-11: "I'm happy to experiment with RNG order freedom. If that's a real lever it should be exploited."
Reverses the bit-exact contract that governed every engine pass since the fast-nle migration. Rules stay fixed;
the RNG stream (which draw happens when, and how a 64-bit word maps onto [0,x)) is free.

## Contract — what "rules unchanged" means from here on
Every decision procedure must produce the same probability distribution over outcomes given the same game state as
stock NLE. Trajectories for a given seed may differ. Verification tiers for non-bit-exact layers:
- T1 per-procedure twin: analytic proof or Monte-Carlo (1e6 trials, chi-square) that old and new procedures have the same outcome distribution.
- T2 crash/invariant gates: the fuzz/status/interleaved/shuffled suites run without hash comparison (no panics, desyncs, asserts).
- T3 fixed-policy distributional eval: one trained checkpoint on old vs new engine, 10K episodes, score median/mean, death causes, depth,
  turns — within the cert SE (≈90 on score).
- T4 paired-seed learning A/B from scratch (user rule) before any default changes.
Bit-exact layers (counters, deterministic restructures) keep the old gates (goldens, corpus obs b79eb25d93ca6d29, full gate).

## Measurement protocol
- The corpus replay cannot time a diverging engine: replayed actions go off-policy and the game regime changes. Timing is the trainer
  fast protocol: cohort regime 5M/4096 (collection-bound, largest env share), ABBA ctrl_a cand_a cand_b ctrl_b via campaign_ablate.py,
  SPS from sps_from_log.py, single-run noise ±1.2%. 15M/2048 secondary. Both engines non-PGO for sizing; PGO vs PGO before landing.
- Bit-exact instrumentation layers (rc*) run the 82 s corpus replay (512x32768) for counts and must reproduce the obs hash.
- perf counters are disabled in the container (perf_event_paranoid 4): no cycle profiles; clock sizing is by ABBA only.

## Sizing facts carried over (engine-scaling program)
520K instructions/step; 6.88 game turns/step (115,413,681 turns / 16,777,216 steps); ~96-99 monster moves/step ≈ 14 per game turn;
monster turn ≈ 310K instructions (60%): mfndpos 86K (~117/cell × 8 cells × 96 calls), m_move 93K, dochug 25K, movemon 21K, object scan 23K.
RNG self cost 15K is the isaac64 refill only: the 64-bit modulo in every draw is one instruction and invisible to the instruction census
that sized all earlier work. That is the first thing to measure on the clock.

## Levers — sized by what the freedom actually unlocks
- L1 RND modulo → multiply-high (arm rm1). Per draw a 64-bit DIV (15-40 cycles, worse on E-cores) becomes one MUL. Rules: uniform on [0,x)
  with bias x/2^64, same order as the modulo's own bias. Gain = draws/step × divide cost.
- L2 fewer draws, identical distributions: reservoir `!rn2(++chcnt)` → one rn2(accepted) for wanderers (uniform over accepted either way);
  the `rn2(4*(cnt-j))` track draws stay (their probability depends on cnt). Gain = (accepted − 1) draws per wander move.
- L3 lazy legality for wanderers (rejection sampling over the 8 neighbours) would cut mfndpos per-cell work ~3x, but cnt enters the
  probabilities (track avoidance, jcnt) and should_displace needs the full list → needs a cheap legality-only pass first. Design after the census.
- L4 deterministic restructures of mfndpos/m_move/dochug stay bit-exact-verifiable and were exhausted in Phase 3 (−6%); freedom adds nothing there.
- Not unlocked: skipping, deferring or approximating monsters — that changes rules.

## Arms
- rm1 = mt7 + multiply-high in RND and rn2_on_display_rng (built 15:27, 9 s via compile cache). ABBA vs mt7 at 5M/4096: chain_rng0.sh →
  campaign_rm1.log, runs/rm1_5m4k_*. Expect PROOF cand != ctrl (new stream) and ctrl_a == ctrl_b.
- rc1 = mt7 + global relaxed-atomic counters, dumped by a destructor as NH_CENSUS: 0 RND draws, 1 movemon calls, 2 monsters iterated,
  3 monsters moved, 4 dochug, 5 m_move, 6 m_move→mfndpos, 7/8/9 appr −1/0/+1, 10 Σ reservoir chcnt, 11 track draws, 12 moves chosen,
  13 mfndpos (all callers), 14 draws inside movemon, 16+c histogram of cnt (0..9). Census replay must reproduce obs b79eb25d93ca6d29 / turns 115413681.

## Landmines
- build_candidate.py copies from movement_object_presence when engines/<name>/source is missing: always create the source dir (copy of mt7) first.
- Counters are global relaxed atomics: fine for counts, never for timing.
- A diverging engine's replay log is not comparable to the corpus; only the RESULT line's sanity (no crash) means anything there.

## rm1 result (15:30 UTC) — L1 refuted
ABBA 5M/4096 cohort, non-PGO: ctrl_a 323,521 | cand_a 323,737 | cand_b 327,514 | ctrl_b 322,726 → +0.77%, inside single-run noise (±1.2%).
PROOF ctrl_a==ctrl_b, cand!=ctrl (new stream, as expected). rc1 build (13 s, ended 15:27:57) overlapped only ctrl_a's warm-up (window = batches 15-20).
The 64-bit divide per draw is hidden by out-of-order execution or the draw count is small; the census will say which. Not a lever on its own;
fold multiply-high into whatever lands next (free), never ship it alone (it costs the bit-exact gates for nothing).
L2 (reservoir → single draw) is bounded by the same number and is dropped as a standalone arm.

## rc1 census (15:36 UTC; bit-exact: obs b79eb25d93ca6d29, turns 115413681; 364 s under atomic contention)
Per policy step (÷16,777,216): RND draws 519.8 (315 inside movemon = 61%); movemon passes 11.6 (6.88 game turns → 1.7 passes/turn);
monster-list visits 314, of which 105 move (fmon ≈ 27 monsters, 9 move per pass); dochug 104; m_move 90.8; m_move→mfndpos 86.8;
mfndpos all callers 86.85 (dog_move etc. negligible). appr split at the selection loop: approach +1 57.3 (66%), flee −1 20.1 (23%),
wander 0 9.3 (11%). Σ reservoir chcnt 44 (= 4.7 accepted candidates per wander move); track-avoid draws 57 (0.74 per approach/flee move:
the cell the monster came from is almost always a legal candidate); moves chosen 72 of 86.8 (17% stuck).
Legal-cell histogram cnt=0..8: 16.9 / 18.4 / 18.5 / 13.7 / 10.4 / 9.7 / 4.6 / 3.8 / 4.1 % → mean 2.74 legal cells per query (3.3 given cnt>0).
READING: 520 draws/step at ~1 per 1,000 instructions — the divide is hidden by out-of-order execution (rm1 +0.8%). The monster turn is
~3K instructions per moving monster spread over 15+ functions; only the per-cell neighbour evaluation (mfndpos 990/call, m_move loop)
has a freedom-dependent algorithm: evaluate cells lazily in preference order and stop at the first acceptable one. Draws for tracked
cells whose outcome cannot change the choice may be skipped (distribution-preserving) — that skip is what makes the lazy approach
path cheap (0.74 tracked legal cells per move would otherwise force the full list). Expected: (c_eval+1)/(k+1) ≈ 1.6 evaluations
instead of ~5-6 for the 83% of queries with a legal cell → −35..40K instr/step (−7%) plus the per-cell mispredicts → +6-9% SPS. Not a 500K lever.
Also visible: 2/3 of movemon's list visits are monsters that cannot move this pass (21K/step, 4%) — a movers list is bit-exact work, ≤3%.

## lz0 (15:40 UTC) — bit-exact refactor, the no-regret step
mfndpos_masked split mechanically into nh_mfnd_begin (per-call context: mover, flags, capability booleans, candidate mask) and
nh_mfnd_cell (the loop body verbatim: continue→return 0, info[cnt]→inf, accept→return 1; 16 rejection exits), plus a thin loop with
the eel wantpool retry. Generated by make_lz0 (inline python in the session; the engine dir holds the result). Built in 9 s, no errors,
same warning set as mt7. Gates: corpus replay must give obs b79eb25d93ca6d29 / turns 115413681, then check.py --quick. chain_lz0.sh.

## lz1 design — lazy preference-ordered selection (not built; needs the user's call on leaving the bit-exact contract)
In m_move, replace `cnt = mfndpos(...)` + the selection loop:
1. nh_mfnd_begin → context + candidate bits (bit = 3*dx+dy, ascending = the original scan order). `avoid` (unicorn/noteleport) → full path.
2. appr = +1: order candidates by (dist2 to goal asc, bit asc) — the original is argmin with ties to the first in scan order
   (`nearer` strict, `!mmoved` baseline). appr = −1: (dist2 desc, bit desc) — argmax with ties to the last (`!nearer` = ≥).
   Walk the order; per cell nh_mfnd_cell. Illegal → next. Legal and (trackmask bit set) → FALLBACK (the original draws rn2(4*(cnt−j))
   with j < jcnt = min(MTSZ, cnt−1): needs cnt). Legal and ALLOW_MDISP without ALLOW_M → FALLBACK (needs should_displace on the full
   list). Otherwise it is the choice: chi = 0, info[0] = flags, nix/niy = cell. Zero draws.
   Why skipping the other tracked cells' draws preserves the rules: a tracked legal cell that comes after the pick in preference order
   loses on (distance, tie) whether or not its draw would have skipped it, so the draw's outcome cannot change the choice.
3. appr = 0 (wander): sample candidate bits without replacement (rn2(popcount) per pick); illegal → next; MDISP w/o ALLOW_M →
   FALLBACK to compute better_with_displacing once, then continue; first accepted = the choice. Reservoir sampling and
   sampling-without-replacement-until-accepted are both uniform over the accepted set. Draws ≤ candidates (today: one per accepted).
4. No legal cell after exhausting the order → eel retry (c.wantpool = FALSE, rerun) exactly as the full path; else mmoved = 0.
5. FALLBACK = evaluate all candidates into poss/info (nh_mfnd_cell loop) and run the original selection loop verbatim.
Cost model: 83% of queries have a legal cell; expected evaluations (c_eval+1)/(k+1) ≈ 1.6 vs ~5-6 → −35..40K instr/step (−7%),
fewer per-cell mispredicts; stuck queries (17%) still evaluate everything. Fallback rate unknown (previous cell preferred over the
best cell only when the monster is oscillating); the twin build will count it.
Twin (-DNH_LAZY_VERIFY): after a non-fallback lazy choice, snapshot the core RNG ctx, run the full list + original loop into shadow
variables, restore the RNG; appr ≠ 0 → assert identical (nix, niy, info); appr = 0 → assert the choice is in the accepted set with equal
flags. LAZY_MISMATCH lines, not panics. Offline: 1e6-trial chi-square of the sampler on random masks. Then trainer ABBA vs mt7.
What is given up: the golden/corpus hash gates no longer apply to lz1 and everything after it; T2-T4 of the contract replace them.

## rc2 turn attribution (15:57 UTC; bit-exact: obs b79eb25d93ca6d29, turns 115413681)
Turns by hero state at moves++: occupation 81.3% (counted search is an occupation in 3.6; eating ≈4% of it), running 6.8%, count-repeat 0.0011%, plain 12.0%.
Corpus steps: SEARCH20 42.6%, RUN 19.5%, other 37.8%. Turns per SEARCH20 step ≈ 12.6; per RUN step ≈ 2.4; per other step ≈ 2.8.
Cost model: instr/step = F + T·turns with F ≈ 120K (obs/display/hero), T ≈ 57K per turn (movemon inclusive 73% of 520K over 6.88 turns) → 512K at 6.88 turns/step (520K measured).
No-macro, same game turn-for-turn (one decision per former macro turn): steps ×6.2, 1.11 turns/step, 183K instr/step → env side ×2.8 steps/s, ×0.45 game turns/s.
GPU cap (ledger, 5M/2048): PPO 0.54 s per 262,144-step batch → 485K SPS whatever the env does; 5M/4096 the same ratio. Realised no-macro SPS ≤ 485K (+50% over 320K) unless the sweep buys a cheaper PPO (bigger minibatch).
Matched wall-clock: macro agent 320K×6.88 = 2.2M game turns/s; no-macro ≤ 485K×1.11 = 0.54M → ≈4.1x less game time per hour, 1.5x more decisions.

## Macro-removal throughput (user question 16:00 UTC: are RUN/SEARCH20 biasing the policy; would a no-macro agent be competitive at matched wall-clock after a re-sweep?)
- First ABBA (ablate_nomacro.json, --env.mask_search20=1 --env.mask_run=1, 5M/2048 and 5M/4096): all eight runs within 1% of each other and
  BATCH_PROOF cand==ctrl. NULL BY CONSTRUCTION: the fast protocol (--base.profile=1, loaded.bin) replays a recorded action stream, so the
  action space cannot matter. The overrides were accepted (puf_ini_put exits on unknown keys). LANDMINE: any arm that changes which actions
  get taken (masks, verb_eps, action-space edits) needs PUF_LIVE_AFTER_WARM=1 on every arm; the proof hashes then differ by design.
- Second ABBA (ablate_nmlive.json, live sampling from the width-512 frozen random model on all four arms per regime): chain_nmlive.sh.
  Young-policy regime: a near-uniform policy picks SEARCH20/RUN ~10% of steps and young levels rarely interrupt a search, so expect
  turns/step ≈ 3 with macros vs ≈ 1.2 without → env side ×1.6, realised SPS capped by PPO (485K at 5M).
RESULT (16:12 UTC, live sampling on all arms; BATCH_PROOF lines are not emitted in live mode, so the chain's "proof" line is vacuous):
5M/2048: ctrl 260,828 / 260,879 | masks 251,842 / 252,193 → −3.4%. 5M/4096: ctrl 211,486 / 209,725 | masks 202,729 / 202,576 → −3.8%.
Rollout tail 0.49 → 0.53 s, PPO tail 0.465 s both. Live mode itself runs 260K vs 320K replay (young random policy: short games, resets).
READING: in the young regime a SEARCH20 step is 20 cheap turns on a near-empty level with no view change, so it is at most as expensive as the
move/verb steps that replace it; removing the macros does not speed the env up there. The mature-regime estimate stands on the census
(12.6 turns per SEARCH20 step, 55K instr per mature turn): 520K → ~183K instr/step, env side ×2.8, but PPO caps 5M at ~485K (+50%) and
15M/2048 is bound by the actor forward per step (263K) so gains nothing. Game turns per hour: 0.25x (5M) to 0.16x (15M).

## Do cohorts speed up other envs? (17:02 UTC; envs/ — trainer_cohort source with 5 envs dropped in; flags -DPUF_ENV_POOL -DPUF_PERF_LOAD
## -DPUF_MUON_PARALLEL -DPUF_MUON_BATCH_NORM -DPUF_MUON_OUTPLACE; NetHack-only sites guarded: nh_refresh_tables, blstats ages, PUF_BYTE_OBS, head sampler)
2048 agents × horizon 128 (batch 262,144), 32 epochs, window 11..30, 24 pinned pool workers, live sampling from the random init.
| env | control 4×512 | 16×128 all active | 16×128 cohort g4 s64 | cohort vs control | cohort vs 16 active |
| breakout | 13.47M / 12.52M | 5.95M | 4.10M / 4.25M | −68% | −30% |
| drone | 6.16M / 6.15M | 5.69M | 4.56M / 4.41M | −27% | −21% |
| craftax (train.gpus=1) | 762K / 762K | 609K | 623K / 626K | −18% | +2.5% |
| nethack 5M (ledger) | 240K | — | 302K | +26% | — |
Not measurable here: moba (host OOM-killed at startup every time, 70 GB anonymous memory held outside this container), chess (self-play,
perf-load path asserts), nmmo3 (1024 agents per env, no 128-agent buffer possible).
READING: the cohort shape has two parts. 128-agent buffers cost every env that is GPU-launch-bound (forward latency is the same for 128 and
512 agents, so 4x the launches): −55% breakout, −8% drone, −20% craftax. The restriction to 4 active buffers then costs the launch-bound envs
again (less concurrency to hide launches: −30%, −21%) and helps only where the env step dominates and per-game state overflows L2: +2.5%
craftax, +26% NetHack. So cohort = NetHack-class envs (≥50 µs CPU step, 100s of KB state, >512 agents) only; default off everywhere else,
and the sweep-friendly form must be "agents per buffer = 128, 4 active" gated on the env, not a global default.

## Cohorts at each env's NATIVE shape (17:12 UTC; envs/native_arms.sh; agents/horizon/minibatch untouched, 24 pinned pool workers on all arms)
| env (native) | arm | buffers × agents | active | SPS |
| breakout 4096 × h32 mb65536 | native | 1 × 4096 | 1 | 11.07M / 11.12M |
| | chalf | 2 × 2048 | 1 | 8.86M (−20%) |
| | cquarter | 4 × 1024 | 1 | 6.57M (−41%) |
| | c128 | 32 × 128 | 4 | 3.89M (−65%) |
| drone 8192 × h64 mb16384 | native | 8 × 1024 | 8 | 6.99M / 6.98M |
| | chalf | 16 × 512 | 8 | 6.89M (−1.4%) |
| | cquarter | 32 × 256 | 8 | 6.66M (−4.7%) |
| | c128 | 64 × 128 | 4 | 4.31M (−38%) |
| craftax 2048 × h256 mb32768 (train.gpus=1) | native | 4 × 512 | 4 | 761K / 759K |
| | chalf | 8 × 256 | 4 | 661K (−13%) |
| | c128 | 16 × 128 | 4 | 631K (−17%) |
READING: env work per batch is identical across arms; the cost is forwards per batch ∝ 1/buffer size, and a forward's latency barely falls with
fewer agents (launch/contention-bound). With the buffer size preserved the cohort is no slower (drone 16×512/8 active −1.4%) but has nothing to
gain unless per-game state overflows L2 — none of these envs' does. The NetHack recipe (128/buffer, 4 active) exists because 512 resident games
with 4 pipeline stages forces 128-agent forwards, affordable only when the env step dwarfs the forward. Making cohorts free for light envs needs
the forward batch decoupled from the buffer (gather the active buffers' obs into one forward) — the dynamic-batching design the ledger rejected
for NetHack because the env dominated there. Verdict: cohort default OFF; enable per env (NetHack-class), never as a sweep-wide default.

## Actor forward anatomy, 15M model (17:45 UTC; fwd/ — nsys node traces, --base.async=0 so PPO and rollout alternate; fwd_split.py splits each
## buffer cycle at its largest gap into forward proper vs env phase; fwd_util.py = GPU utilisation + launch structure)
| shape | forward proper (median wall / busy) | kernels | env phase / cycle per buffer | rollout s/epoch | PPO s/epoch |
| 16 × 128, cohort g4 s64 | 195 µs / 191 µs | 57 | 726 µs / 933 µs | 0.60 | 0.83 |
| 4 × 512 | 327 µs / 324 µs | 58 | 6.4 ms / 6.7 ms | 0.89 | 0.83 |
Linear fit: forward = 151 µs fixed + 0.34 µs/row → at 128 rows 77% of the forward is launch-floor cost (57 kernels × ~2.7 µs), not work.
Launch structure per forward: 1 cudaGraphLaunch + 1 cudaLaunchKernel + 5 cudaMemcpyAsync + 5 cudaEventRecord + 1 cudaStreamSynchronize — the
host side is already minimal; inside the graph the nodes run back-to-back (busy ≈ wall). GPU during rollout (c128): inference kernels busy 60%,
one kernel at a time 43%, two 4%, none 51% — the four active buffers' forwards barely overlap, and the pool (726 µs per 128-game env phase) binds:
rollout alone = 0.60 s/epoch ≈ 440K SPS at 15M/2048.
CORRECTION to the 16:xx reading: the earlier "933 µs forward" and "12 µs gaps" were the buffer cycle; the September 1155 µs likewise. The
production 263K at 15M/2048 is not forward latency: it is GPU sharing in async mode — rollout 0.60 → 1.00 s and PPO 0.83 → 0.98 s when they
run concurrently, because 57 tiny dependent kernels per forward (2048 forwards per epoch) queue behind PPO's GEMMs at every node and PPO's
GEMMs lose SMs to them. PUF_INFER_PRIORITY=1 is already on.
LEVER (sized): fuse the forward from 57 kernels to ~10-12. Chains visible in the trace: prologue (cast_rew_term, cast, zero_term_state) → fold into
the first encoder kernel; patch/terrain chain (eff_embed, decode, crop, loc3_gather, 2 GEMM, terr_feat, 2 GEMM) → 1-2; inventory chain
(2 inv_decode, 2 inv_table, inv_sfeat_packed, inv_gather, entity_fused) → 1; message (msg_ids, msg_pool) → 1; two token encoders (lab_tok, GEMM,
entity_fused, min_sgate) → 1 each; spell (spkey, entity_fused, sp_doorstep) → 1; idemb_warp; recurrent block 4 × (GEMM 12 µs + mingru_gate 3 µs) →
one persistent M=128 kernel streaming 16 MB of weights (~20 µs at 900 GB/s) or 4 fused GEMM+gate; decoder (GEMM, 2 splitK, GEMM, ptr_rownorm,
ptr3_cos, dec_assemble) + sampler → 2. Expected forward alone 195 → ~80-100 µs; the larger effect is contention: fewer, longer kernels queue
less behind PPO and steal fewer SMs from it. Target: async epoch → max(rollout ≈ 0.65, PPO ≈ 0.85) → ~300-310K at 15M/2048 (+15-18%);
15M/512 (champion) gains PPO relief only (same 2048 forwards/epoch), order +5-10%, unmeasured. Numerics change → determinism reference moves.
Not a lever: forward batch size (512 rows = 327 µs: fixed cost dominates either way); host launch path (already one graph).

## Contention measured (17:55 UTC; fwd_c128_async = same 15M/2048 cohort config in production async mode, node trace)
| mode | forward proper median wall / busy | p10 / p90 | env phase | cycle | rollout s/epoch | PPO s/epoch |
| sync (PPO and rollout alternate) | 195 / 191 µs | 184 / 274 | 726 µs | 933 µs | 0.60 | 0.83 |
| async (production) | 744 / 652 µs | 418 / 1137 | 752 µs | 1587 µs | ≈0.99 (epoch 0.986) | 0.98 |
The forward stretches 3.8x under PPO; 460 of the 550 µs stretch is inside kernel durations (blocks waiting for SMs held by PPO's GEMM blocks,
which run to completion), ~90 µs is inter-node gaps. 57 kernels = 57 chances to wait; PUF_INFER_PRIORITY only orders new blocks. Env phase is
unchanged (CPU). Mechanism for the lever confirmed: fewer, fatter kernels wait fewer times; expected contended forward ≈ 195 + ~10 waits
≈ 300-400 µs → cycle ≈ 1.1 ms → rollout ≈ 0.7 s → epoch bound by PPO ≈ 0.85-0.9 s → 290-310K at 15M/2048 (+10-18%). PPO itself recovers part of
0.98 → 0.83 as inference stops interleaving at 57 points per forward. Alternative without kernel work: SM partitioning (green contexts) — gives the
forward its 195 µs but taxes PPO permanently; worse than fusion. Champion-shape (512 × 512, mb 4096) sync/async graph traces pending → PPO stretch there.

## Headroom from GPU sharing, both 15M regimes (18:10 UTC; graph traces fwd_champ_{sync,async}, node traces fwd_c128{,_async})
| regime | rollout alone | PPO alone | production epoch (async) | PPO contended | forward alone → contended | perfect-overlap bound | headroom |
| 15M/2048 cohort, mb 8192 | 0.60 s | 0.83 s | 0.99 s (263K) | 0.98 s | 195 → 744 µs | 0.83 s (316K) | +20% |
| 15M/512×512 champion, mb 4096 | 0.83 s | 0.99 s | 1.14 s (230K; ledger 229K) | 1.14 s | 183 → 546 µs | 0.99 s (264K) | +15% |
In both, the rollout is fully hidden only on paper: 2048 forwards × 57 kernels per epoch interleave with PPO (68-70% of PPO busy time overlapped by
inference graphs), PPO loses 14-18%, the forward 3-4x. The bound is PPO-alone; fusion of the forward (57 → ~10 kernels) is the lever for the
interference term; the PPO-alone term is optimizer work (Muon 42% of PPO kernel time per the September profile) and the sweep's minibatch choice.
5M regimes: no GPU headroom of this kind (env-bound).

## Mechanism probes (18:25 UTC; binary cohort_fx = trainer_cohort + PUF_INFER_DUMMY/PUF_INFER_BURN graph-node injections; 15M/2048 cohort, fast protocol)
ctrl 264,798 / 263,289 | PUF_CACHE_TABLES=1 (−3 kernels/forward) 264,175 (0%) | +50 trivial 1-block kernels/forward 257,160 (−2.6%; rollout became the
tail by 28 ms) | +100 232,325 (−12%) | +1 kernel holding 16 SMs ~80 µs 261,128 (−1.1%). All proofs identical (injections inert, cache exact).
READING: kernel COUNT is not what PPO pays for (doubling it costs <3%, mostly via rollout length); steady SM occupancy costs ≈ proportionally
(2% of SM-seconds → −1.1%). The fusion estimate (+15-18%) assumed count; FALSIFIED. Clocks identical under load (2.72 GHz, 408 W ctrl vs 389 W
dummy100). Actor-weight L2 persistence (ACTOR_CACHE 16/32 MiB, Oct 9) was neutral → weight traffic is not the channel.
rec128 screen (REC128_SCREEN.json): Triton fused GEMM+gate at M=128 best (32,32,32,2w) 12.1 µs vs cuBLAS+gate 10.6 µs → SLOWER (−12%); at M=512
it had won +26%/layer. Recurrent fusion at 128 rows: dead. Remaining hypothesis: WIDE short kernels (cast 2391 blocks, zero_term_state 2048,
decode 830, concat 849, inv_gather 440, lab_tok 384×2, assemble 372, cos 330 …) fill all SMs for 1-3 µs and stall PPO's GEMM waves; the 1-block
dummies could not show that. Probe: PUF_INFER_DUMMY_BLOCKS (wide dummies). If confirmed, the fix is numerics-exact grid narrowing, not fusion.

## Wide-kernel probe (18:33 UTC; cohort_fx2, 15M/2048): the interference channel is grid WIDTH
ctrl 264,572 / 262,824 | +50 kernels × 1 block −2.6% (earlier) | +50 × 128 blocks 249,024 (−5.9%, rollout became tail) | +20 × 2048 blocks 226,088
(−14.6%, PPO 0.98 → 1.12 s) | +50 × 2048 blocks 178,871 (−32%, rollout 1.46 s). PPO loses ≈3.4 µs per wide short kernel launch (0.14 s / 20×2048);
the real forward has ~15 launches of 300-2,400 blocks (cast 2391, record_step ~2092, zero_term_state 2048, concat 849, decode 830, eff_embed 748,
inv_gather 440, lab_tok 384×2, inv_table 374×2, dec_assemble 372, cast mask 371, ptr3_cos 330, loc3_gather 324) → predicts ≈0.10 s of PPO's
0.15 s loss. Wide 1-3 µs kernels fill every SM and stall PPO's GEMM waves; narrow kernels do not. FIX = grid narrowing (grid-stride loops, launch
capped at PUF_NARROW_BLOCKS, inference only; identical per-element math → proofs must match): narrow/make_narrow.py (13 kernels in nethack.cu,
16 launches) + the pufferl.cu pass (cast obs/mask, zero_term_state ×2, record_step). Binary cohort_nw2. Ladder 16/32/64/128 at 15M/2048, then
champion shape 512×512 mb4096 with 32/64.

## Narrowing result (18:43 UTC) and the SM-time attribution — fusion/narrowing direction closed
nw ladder 15M/2048 (cohort_nw2, all proofs identical = numerics exact): ctrl 263,693 / 262,560 | cap 16: 232,043 (−12%, rollout tail 160 ms) |
32: 252,652 (−4%) | 64: 260,793 (−1%) | 128: 262,581 (0%). PPO time unchanged at every cap → the wide-kernel channel is not launch width per se.
SM-time attribution (fwd_c128 sync node trace, inference streams only; SM.us = duration × min(blocks,128)): per 128-row forward 212 us kernel
time, 14,804 SM.us = 116 us of the whole GPU → 2048 forwards/epoch = 24% of the GPU's SM-seconds; PPO loses 15-18% ≈ 2/3 of that (the burn probe
gave the same ratio: 2% SM-seconds → −1.1%). Top: Kernel2 (15 GEMMs) 21.5%, entity_fused ×4 10.7%, mingru_gate ×4 (512 blocks, 2.9 us) 10.0%,
sampler 9.3%, msg_pool 8.0%, inv_table ×2 7.2%, terr_feat 4%, lab_tok ×2 4%; wide (≥300 blocks) short (<6 us) elementwise kernels = 40%.
Kernels sit at the ~2-3 us launch floor, so SM-time ≈ floor × blocks: narrowing trades blocks for time (same SM-time); fusion removes ~320 SM.us
(2% of inference SM-time ≈ 0.3% SPS) per wide kernel removed — ~15 candidates → ≤ +5% for a multi-day job. CLOSED as the lever.
THE LEVER: fewer forwards. A 512-row forward costs 1.7× a 128-row one (327 vs 195 us), so 4×128 spend ~2.5× the SM-time of 1×512. Shape with
512-row forwards and partial residency, no code: 4 buffers × 512, cohort 2 active (1024 resident, depth 2; the 15M forward ~0.6 ms contended hides
under the 1.5 ms pool step). Ledger priors: 1024 resident cost 4 points of the cohort's 12 at 15M (b16c8s32 +8%); b8c2s32 (256-row, depth 2) −7.5%
from bubbles. Queued ablate_big.json: ctrl(16×128 g4 s64), b4c2s64, b4c2s128, b8c4s64, b8c4s128, b4plain (4×512 no cohort = old control), ctrl.

## Champion narrowing + big-forward shapes (18:52 UTC) — GPU-side inference program CLOSED
Champion 512×512 mb4096 (cohort_nw2): ctrl 228,343 / 227,971 | cap 32: 224,887 | cap 64: 225,861 (−1%); proofs identical. Null, as at 2048.
Why narrowing cannot cut SM-time: floor-bound kernels take ~2.5 us whatever the grid; a grid > 128 blocks capped at 128 still fills every SM and
runs longer; capped at 32-64 the duration grows ~proportionally (latency/bandwidth-bound) → SM-time flat. Only fewer launches or fewer forwards cut it.
Big-forward shapes 15M/2048 (cohort_d8): ctrl 16×128 g4 s64 262,939 / 261,497 | 4×512 c2 s64 237,206 (−9.7%, rollout tail 186 ms; PPO ≈0.93 s) |
4×512 c2 s128 238,546 | 8×256 c4 s64 255,038 (−2.9%) | 8×256 c4 s128 255,679 | 4×512 plain 223,360 (−15%, the pre-cohort control).
PPO does speed up with 4× fewer forwards (0.98 → 0.93 s) but 1024 resident games cost the rollout more than PPO gains. The recipe stands.
VERDICT: inference-side work (fusion, narrowing, bigger forwards, table cache, L2 persistence, recurrent fusion) cannot lift 15M/2048 above the
~263K it sits at; the bound is PPO-alone 0.83 s (316K) and the gap to it is inference SM-time that only a ~2x cheaper forward in SM-seconds would
close — a full encoder/recurrent/decoder rewrite worth ≤ +5-10% by the attribution. Next GPU lever is PPO itself (Muon 42% of PPO kernel time;
minibatch choice is the sweep's). Numerics-exact narrowing patch retained (narrow/narrowing.patch) for the record; default off.

## Component attribution ladders (19:18-20:10 UTC; ablate_attrib.json + ablate_attrib2.json, binary cohort_d8, fast protocol, cumulative build-up from stock everything = repo-HEAD proxy; full-stack controls bracket each regime)

## 15m512: 116,429 -> 228,340 (1.96x); full-stack control before the ladder 229,485 (drift -0.5%)
  step                 SPS     delta     pct  share  component
  L0_alloff        116,429                           stock engine, no GPU flags, 1 lane, no overlap, no priority, 32 workers
  L1_engine        182,697   +66,268  +56.9%    59%  + engine mt7 (bit-exact ladder, PGO)
  L2_gpukernels    208,157   +25,460  +13.9%    23%  + GPU fast kernels + entity fusions
  L3_lanes4        228,352   +20,195   +9.7%    18%  + Muon 4 lanes
  L4_gradoverlap   229,591    +1,239   +0.5%     1%  + gradient overlap, 32 connections
  L5_prio_block    228,431    -1,160   -0.5%    -1%  + inference priority, blocking waits
  L6_pool24pin     228,340       -91   -0.0%    -0%  + pool 24 workers, pinned

## 5m512: 122,826 -> 330,451 (2.69x); full-stack control before the ladder 328,991 (drift +0.4%)
  step                 SPS     delta     pct  share  component
  L0_alloff        122,826                           stock engine, no GPU flags, 1 lane, no overlap, no priority, 32 workers
  L1_engine        278,855  +156,029 +127.0%    75%  + engine mt7 (bit-exact ladder, PGO)
  L2_gpukernels    300,574   +21,719   +7.8%    10%  + GPU fast kernels + entity fusions
  L3_lanes4        299,254    -1,320   -0.4%    -1%  + Muon 4 lanes
  L4_gradoverlap   292,809    -6,445   -2.2%    -3%  + gradient overlap, 32 connections
  L5_prio_block    308,528   +15,719   +5.4%     8%  + inference priority, blocking waits
  L6_pool24pin     330,451   +21,923   +7.1%    11%  + pool 24 workers, pinned

## 15m2k: 129,859 -> 262,521 (2.02x); full-stack control before the ladder 262,826 (drift -0.1%)
  step                 SPS     delta     pct  share  component
  L0_alloff        129,859                           stock engine, no GPU flags, 1 lane, no overlap, no priority, 32 workers
  L1_engine        217,212   +87,353  +67.3%    66%  + engine mt7 (bit-exact ladder, PGO)
  L2_gpukernels    218,020      +808   +0.4%     1%  + GPU fast kernels + entity fusions
  L3_lanes4        215,963    -2,057   -0.9%    -2%  + Muon 4 lanes
  L4_gradoverlap   203,079   -12,884   -6.0%   -10%  + gradient overlap, 32 connections
  L5_prio_block    230,402   +27,323  +13.5%    21%  + inference priority, blocking waits
  L6_pool24pin     223,821    -6,581   -2.9%    -5%  + pool 24 workers, pinned
  L7_cohort        262,521   +38,700  +17.3%    29%  + cohort 16/32 x 128, 4 active, 64 steps

## 5m2k: 131,647 -> 322,865 (2.45x); full-stack control before the ladder 320,250 (drift +0.8%)
  step                 SPS     delta     pct  share  component
  L0_alloff        131,647                           stock engine, no GPU flags, 1 lane, no overlap, no priority, 32 workers
  L1_engine        234,896  +103,249  +78.4%    54%  + engine mt7 (bit-exact ladder, PGO)
  L2_gpukernels    236,697    +1,801   +0.8%     1%  + GPU fast kernels + entity fusions
  L3_lanes4        237,591      +894   +0.4%     0%  + Muon 4 lanes
  L4_gradoverlap   230,525    -7,066   -3.0%    -4%  + gradient overlap, 32 connections
  L5_prio_block    237,731    +7,206   +3.1%     4%  + inference priority, blocking waits
  L6_pool24pin     229,434    -8,297   -3.5%    -4%  + pool 24 workers, pinned
  L7_cohort        322,865   +93,431  +40.7%    49%  + cohort 16/32 x 128, 4 active, 64 steps

## 5m4k: 159,626 -> 350,011 (2.19x); full-stack control before the ladder 346,065 (drift +1.1%)
  step                 SPS     delta     pct  share  component
  L0_alloff        159,626                           stock engine, no GPU flags, 1 lane, no overlap, no priority, 32 workers
  L1_engine        252,413   +92,787  +58.1%    49%  + engine mt7 (bit-exact ladder, PGO)
  L2_gpukernels    257,025    +4,612   +1.8%     2%  + GPU fast kernels + entity fusions
  L3_lanes4        257,444      +419   +0.2%     0%  + Muon 4 lanes
  L4_gradoverlap   247,101   -10,343   -4.0%    -5%  + gradient overlap, 32 connections
  L5_prio_block    253,325    +6,224   +2.5%     3%  + inference priority, blocking waits
  L6_pool24pin     244,343    -8,982   -3.5%    -5%  + pool 24 workers, pinned
  L7_cohort        350,011  +105,668  +43.2%    56%  + cohort 16/32 x 128, 4 active, 64 steps

## 15m2k, second ordering (scheduling before GPU); baseline stock 129,859
  M1_engine        215,898   +86,039  +66.3%  stock + engine
  M2_sched         214,598    -1,300   -0.6%  + scheduling block (priority, waits, pool 24 pinned, cohort)
  M3_gpukernels    245,617   +31,019  +14.5%  + GPU fast kernels + entity fusions
  M4_lanes4        258,307   +12,690   +5.2%  + Muon 4 lanes
  M5_gradoverlap   262,271    +3,964   +1.5%  + gradient overlap, 32 connections
  ctrl_b           262,839      +568   +0.2%  full stack control after

## Scaling grid: agents and minibatch (20:12-20:40 UTC; ablate_scale.json, full stack + cohort recipe scaled per shape (buffers = agents/128, 4 active,
## steps = min(64, horizon)), fast protocol; controls 264,453 / 262,345 at 15M/2048 mb8192)
Agents at constant batch 262,144:
| agents × horizon | 15M (mb 8192) | 5M (mb 4096) |
| 512 × 512 | 264,682 | 323,753 |
| 1024 × 256 | 264,692 | 317,039 |
| 2048 × 128 | 263,102 | 323,273 |
| 4096 × 64 | 261,291 | 353,995 |
| 8192 × 32 | 260,373 | 404,703 |
Minibatch at 2048 × 128: 15M 4096 237,107 | 8192 263,102 | 16384 260,859 | 32768 258,784 (PPO tail 1.13 → 0.89 → 0.77 → 0.71 s: past 8192 the
contended rollout binds at ~265K). 5M 4096 323,273 | 8192 314,106 | 16384 306,816 | 32768 299,239 (rollout-bound throughout; larger mb slightly worse).
Minibatch at the champion 512 × 512, 15M: 4096 227,336 | 8192 263,312 | 16384 268,650 | 32768 264,476 (+16% for the first doubling, then flat).
Batch 524,288 = 4096 × 128 (11-epoch runs, 3-batch windows, ±2%): 15M mb 8192 263,252 | 16384 280,620 | 32768 275,720; 5M mb 8192 406,271 |
16384 382,550 | 32768 374,432 (today's ladder: 5M 4096×128 mb 4096 = 350,011).
READINGS: (1) 15M is PPO/interference-bound everywhere: the agent scan is flat 260-265K at constant batch; minibatch 4096 → 8192 is worth +11-16%
at either shape, more gives nothing at batch 262K; the 524K batch with mb 16384 is the best 15M point seen (281K, +7%). (2) 5M is rollout-bound:
minibatch cannot help (curves fall), but agents at constant batch do — 2048 → 4096 → 8192 = 323K → 354K → 405K, and 4096 × 128 at mb 8192 = 406K;
~405K is where the 5M env side with the cohort lands once PPO is small relative to the epoch. Shorter horizons at constant batch change the learning
problem (BPTT window, GAE truncation) — a sweep/A-B question, not a free speedup. (3) Memory: 524K-step batches fit; 8192 × 128 does not.
