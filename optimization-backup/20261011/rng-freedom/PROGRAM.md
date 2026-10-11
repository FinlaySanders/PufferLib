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
