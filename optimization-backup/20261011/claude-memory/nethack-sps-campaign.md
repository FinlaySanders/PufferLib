---
name: nethack-sps-campaign
description: "AUTONOMOUS env-SPS campaign, target 1M train SPS on current config (from ~419K); starts when val-elbflag-180m A/B completes; prime lead = training env phase looks effectively single-threaded"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-07-23T18:37:31.251Z
---

MANDATE (user 2026-07-21): after val-elbflag-180m finishes (task brh9o5evu, report its n=4
result vs wedgefix control 3191 first), run an AUTONOMOUS aggressive env-performance
campaign. Target **1M training SPS under the current config** (22-verb env, 512 agents,
horizon 64, this box). Big changes authorized without asking. PROFILE OVER MANY STEPS —
perf varies as training progresses (early cheap episodes vs converged play; SPS declines
then levels off) — so measure at multiple training stages / long windows, not 6M smokes.

PRIME LEAD (found 2026-07-21, unverified): training dashboard Env 304ms/epoch at
convergence ≈ EXACTLY the single-thread cost of a 512-env x 64-horizon epoch (fnle_bench
512 = 103K SPS single-thread -> 318ms). Suggests env phase runs effectively
single-threaded despite vec num_threads=32. vecenv.h:258: num_workers = num_threads /
num_buffers = 32/4 = 8 per buffer (NOT the <1 floor gotcha), schedule(guided) at :300 —
so mechanism unclear: measure env-phase wall vs --vec.num-threads directly (short runs,
GPU) + perf/timing inside static_omp_threadmanager. If parallelism is broken/serialized,
fixing it alone ≈ 3x -> ~1M SPS.

CAMPAIGN PLAN:
1. A/B result first (valef_s43-46.log scores vs 3191; also engraves bimodality check —
   did the flag de-luck Elbereth? + depth canary for camping).
2. Measure: (a) env-phase wall vs num_threads (e.g. 1/4/8/16/32) on short runs;
   (b) long-window training profile at MULTIPLE STAGES (resume late checkpoints or run
   30-60M and window the dashboard SPS/Env ms); (c) keys-per-step distribution (coroutine
   round-trips per RL step — partial-fill cut fill cost, round-trips remain);
   (d) callgrind move-biased trained-like workload for engine step path.
3. Levers by expected size: fix vec env-phase parallelism (3x if broken); reduce
   keys/step (prompt chains); engine vision_recalc incremental (16% trained-workload Ir),
   mfndpos/m_move; level save/restore cost on stair transitions (savenames was 10% DLmr);
   env-layer mask-fill single-pass + strstr chain gating (~4.7%).
4. Gates per change: goldens 34/34 x3 modes + 78 fuzz + stock_diff fresh seeds +
   no-globals + gradcheck (if encoder touched) + training smoke + n>=1 180M behavior
   spot-check (score in family band). Env-level bench hash: STALE (wedge-fix + elbflag
   changed obs) — record NEW baseline first, then gate.
BUILD DISCIPLINE: never rebuild _C.so or vendor/fast-nle/build/libnethack.so while ANY
training run is live (later seeds load the new lib). Use scratchpad copies for
experimentation while GPU busy. fnle_bench/reset_bench/spam_probe/*.c in scratchpad;
compile line in [[nethack-partial-fill-optimization]]. Whole-box bench = 24 pinned procs
x 341 envs x 500 steps (front-1 metric, baseline 501-511K). Engine perf state (partial
fills, mmap ctx, lazy vterminal, tty-skip = 5 unpushed fast-nle commits) also in
[[nethack-partial-fill-optimization]]. Env changes uncommitted on pufferlib side:
wedge-fix [yn gate + depth<=1 UP mask + elbereth flag (engine internal[6] + extra[0] +
2 bl_feats, NH_BL_FEAT 98).

MEASURED 2026-07-21 (20M-step runs, seed 7, matched phase): thread scaling 8/16/32 ->
142/184/254K SPS (4x threads = 1.8x; saturating, NOT broken/single-threaded — prime lead
FALSIFIED as "broken", confirmed as "saturating"). Env phase 58-70% of wall at ALL thread
counts = THE bottleneck. SPS is strongly phase-dependent (254K @20M vs 419K early smoke).
=> path to 1M: cut per-step env cost (engine step path + env layer + keys/step) AND
improve scaling (bandwidth: front-1 items; sync: fewer barriers). ELBFLAG A/B RESULT
(for the record): score +42 null; engraves -> 0.00 ALL seeds (bimodality resolved to
consistent NON-engraving — de-lucking worked, verdict "dust Elbereth not worth it");
depth up ~4.08. Flag kept; ELBERETH verb now no-live-outcome class. Long-window profile
run launched (seed 7, 180M, default threads, profile180.log in scratchpad) — read its
SPS/Env-ms trajectory by stage for the campaign's cost model.
KEYS/STEP MEASURED (masked-random, keys_probe.c in scratchpad — the #define nle_step
interpose trick): ELBERETH 6.0, REST 3.3, THROW/PUTON/ZAP ~3, APPLY 2.6, WIELD/UP/DOWN
2.0, READ/PICKUP ~1.9, EAT/PRAY ~1.8, WEAR 1.6, moves ~1. Trained-policy mix ≈1.3-1.5
keys/step -> round-trip reduction = moderate lever (20-30% of env phase), not the 3x.
Elbereth now unused by policy (post-elbflag verdict) so its 6.0 is moot. NEXT per plan:
read profile180.log stage-resolved SPS/Env-ms; then engine step-path callgrind on
move-biased workload (vision/mfndpos) = the main per-step cost target; then scaling
(bandwidth/sync). Remember: rebuild libs only when GPU idle; profile run (seed 7,
sps-profile group) occupies GPU ~15-25 min from 2026-07-21 ~20:15.
DIVE-CYCLE PROFILE (walk_bench.c 16x3000, mixed depth, reset-heavy): FLAT — top items
mfndpos 4.3, strcmp 3.3 (option-parse per episode), dog_move 3.0, vision 2.6, strncmpi
2.6, vfscanf 2.6 (level load), memset 2.3, pack_obs 2.3, m_move 2.1, fill_obs 2.0,
match_optname 2.0. Game-logic total ~12%; reset-path ~10% (amortizes away in converged
long episodes); NO single >5% lever. CONVERGED floor = 180K SPS (profile180: SPS 295->181K,
Env 390->490ms as play deepens). ARCHITECTURAL READ: engine step path = death-by-cuts
(~1.3x realistic); the 5.5x needs (a) SCALING REPAIR (1.8x-of-4x lost to sync/bandwidth —
biggest owned lever; investigate vecenv barriers + buffer handoff, try more envs per
thread block, hugepages, NUMA pinning), (b) reset-path option-parse cache (helps early
phase + short-episode regimes), (c) the opt-in auto-advance ~2x reserve (changes step
semantics — user opt-in required), (d) engine cuts as accumulation. walk_bench/keys_probe
in scratchpad. NEXT CONCRETE: instrument vecenv env-phase (where do the lost 2.2x go —
per-thread busy vs barrier wait), then attack accordingly.
USER STEER (2026-07-22): SCALING REPAIR = TOP PRIORITY. Config runs 512 envs (not
2048-4096) BECAUSE MORE ENVS MADE SPS WORSE — consistent with the measured
working-set/bandwidth wall (24 procs x 64 envs = 1.37M agg vs x341 envs = 0.69M: halving
working set doubled the box). TWO coupled problems: (1) at 512/32t, scaling saturates
1.8x-of-4x with only 16 envs/thread (small working set) -> likely SYNC/barrier or shared-
bandwidth, instrument busy-vs-wait per thread (vecenv.h has per-buffer accum timing
infra ~line 226); (2) at 2048-4096 envs the per-env touched-bytes wall bites -> front-1
work (hot/cold ctx split via globals.def heat audit, map SoA levl.typ plane, viz/gbuf
narrowing) is what UNLOCKS big env counts, which also helps GPU batch util + the other
person's overlap work. SUCCESS METRIC: SPS at 512 envs AND make 2048 envs SPS-positive.
VEC INSTRUMENTATION ROUND 1 (2026-07-22, vecenv.h busy/wall prof ADDED — uncommitted,
NLE_VEC_PROF=1 to print): (a) OMP_WAIT_POLICY=passive = +7% (257->275K @32t) — ADOPT
(cheap); (b) thread sweep PASSIVE: 16/20/24/32 -> 195/227/238/275K — still monotonic,
nproc=32 (14900K 8P+16E, HT) so raw oversubscription falsified; (c) intra-region
parallel-eff 5.5x of 8 workers (69%) consistent all buffers; (d) OPEN CONTRADICTION:
cumulative env-region wall ~527ms/epoch/buffer at 100-epoch mark CANNOT fit dashboard-
implied ~127ms epochs — either my prof accounting or timer scope is wrong (prof_wall
cumulative, prints at prof_n%6400 per MANAGER thread) — FIX: per-window (reset on print)
+ print prof_n + epochs-completed cross-check vs dashboard Env ms. Runs may have TIMED
OUT before completing (timeout 240 vs 20-25M @ true wall) — check agent_steps reached,
don't trust tail SPS as run-complete. NEXT: fix prof windows -> reconcile -> then
straggler analysis (p99 chunk time) + net_callback/EVAL_GPU share + H2D DMA overlap;
candidate fixes: per-step join removal (persistent team + spin-free handoff), chunk-size
tuning, worker pinning OMP_PROC_BIND=close/spread, E-core vs P-core placement.
PROFILER RECONCILED (windowed, 2026-07-22, late-phase ~30M seed 7): epoch wall ~320ms;
env region = 265ms/epoch/buffer with 4 buffers CONCURRENT (overlap 3.3x) = env_share
81-89% of each buffer's elapsed; eff 5.7-6.1x/8w; utilization ~23.6/32 threads; SPS 97K
at this phase (32768/0.32s ✓ consistent). Dashboard Env-ms ≈ per-buffer region wall ✓
reconciled (my accum-delta read was invalid — trainer resets accum per epoch).
THE CENTRAL ANOMALY, now sharp: per-env-step thread-time in situ = ~190-230us vs 9.7us
single-thread standalone AT THE SAME 512-env working set (fnle_bench 512 = 103K SPS)
— a 20-25x in-situ inflation. NOT preemption (passive, 32 workers = 32 hw threads);
NOT working set alone (bench proves 9.7us @512 envs single-thread); whole-box 24-proc
bench shows 5x inflation (48us) from pure membw sharing -> remaining ~4x suspects:
concurrent OMP teams interference, HT sharing on 8 P-cores (8Px2HT+16E), CUDA/torch
host threads + pinned-memory DMA on the same memory controller, false sharing on
vec->rewards/terminals/obs rows (adjacent envs' obs slices share cache lines with DMA).
DECISIVE NEXT PROBE: --vec.num-buffers 1 (single OMP team, 32 workers, GPU serialized)
per-step busy vs 4-buffer: drops to ~50us => concurrent-team/DMA interference (fix:
worker pinning per buffer OMP_PROC_BIND, buffer->core-block affinity, or 2 buffers);
stays ~200us => per-thread membw contention (fix: front-1 touched-bytes reduction).
Also try OMP_PLACES=cores OMP_PROC_BIND=spread, and 2-buffer config. NLE_VEC_PROF
instrumentation REVERTED from src/vecenv.h during 2026-07-23 release cleanup (shared
infra, timing ran even with the env var unset); saved as scratchpad/vecprof.patch —
reapply with `git apply` when the campaign resumes (scratchpad is /tmp: if wiped, the
patch is 30 lines re-derivable from the description above — per-c_step clock_gettime
busy reduction + windowed NLE_VEC_PROF report every 3200 hsteps).
BUFFER-COUNT PROBE — CAMPAIGN WIN #1 (2026-07-22, late-phase ~30M seed 7, matched
windows): num_buffers 4/2/1 -> SPS 97/248/210K; per-env-step busy 200/49/59us; eff
69/71/70%. **CONCURRENT-TEAM+DMA INTERFERENCE CONFIRMED as the dominant inflation (4
teams = 3.4-4x per-step cost); num_buffers=2 = sweet spot (some GPU overlap, half the
interference) = 2.56x late-phase SPS from config alone (97->248K).** Residual 49us vs
9.7us single-thread = ~5x membw sharing (matches whole-box bracket) -> next lever =
front-1 touched-bytes. ADOPT: OMP_WAIT_POLICY=passive + --vec.num-buffers 2 (semantics:
rollout forward group size changes 128->256, per-env math identical, training minibatch
composition unchanged — still do one 180M behavior check, score-in-band). REMAINING to
1M from 248K: ~4x = touched-bytes (hot/cold ctx, levl.typ SoA, viz narrowing) x OMP
placement tuning (OMP_PLACES=cores PROC_BIND, HT/P-vs-E policy) x engine cuts. History
note: profile.sh always forced num-buffers=1 (the CUDA memory) — the interference was
invisible to every past profile.
BUF2 ADOPTED (2026-07-22): behavior check killed early per user (partial sanity strong:
s43 score 3506 @144M, in-band-high); buf2+passive = the shipped config. SPS noise
quantified: settled 166±21K CV12% (straggler lottery + episode-composition waves) —
ALWAYS window-means. PLACEMENT PROBE FALSIFIED: global OMP_PLACES=cores+PROC_BIND
close/spread with 2 CONCURRENT teams = 24-26K SPS (10x WORSE — both teams bind the same
global places and stack on the same cores). Correct form = per-buffer DISJOINT core-block
pinning in code (thread_init hook + sched_setaffinity per worker; cf sweep cpu_affinity
infra) — parked as a code item, moderate expected gain. NEXT: async resets (pull
level-gen out of step barriers via pending_reset pre-execution between barriers —
semantics-identical, targets the 29% straggler gap AND the SPS variance), then the
heat-audit/SoA touched-bytes main body.
FROM-CHECKPOINT PROTOCOL (2026-07-22, THE fast method — user: full runs too slow):
--load-model-path <180M ckpt> + 12M steps = converged workload in ~2min, STATIONARY
(sd~0). checkpoints/nethack/p2zq6zsq/0000000179437568.bin = seed-7 profile180's final.
RESULTS (final windows): b2 epoch 102ms -> ~320K SPS, busy 40us/step; b4 epoch 91ms ->
~360K SPS, busy 37.5us/step. => AT CONVERGED WORKLOAD THE BUFFER EFFECT ≈ NIL (b4
slightly BETTER). "Campaign win #1 (2.56x)" was PHASE-SPECIFIC (mid-training ~30M
dive-onset regime where b4 hit 200us/step interference — mechanism suspect: reset-storm
+ mmap/munmap TLB-shootdown IPIs + mklev bursts across 4 teams; unproven). REVISED
recommendation: keep b4 default; b2 only if mid-training phase matters; passive stands.
NEW CENTRAL ANOMALY — LONG-RUN SLOWDOWN: same policy/config/box: fresh-process
from-checkpoint = 320-360K, but in-run at 180M (profile180 tail) = 181K, valb2@144M =
166K => ~2x degradation over a run's lifetime. SUSPECTS: heap fragmentation/RSS aging
(180M steps of alloc churn -> locality decay; slot-reuse allocator relevance!), torch
allocator growth, page-table/THP decay, wandb accumulation. NEXT PROBE: run ONE long run
and snapshot SPS + /proc RSS/pagetables periodically; or from-checkpoint LONG (60M+) to
see decay onset without policy drift. If fragmentation confirmed -> fix = arena/pool
reuse (fast-nle slot-reuse allocator was shipped for old vendor; fast-nle uses plain
malloc — port it) => potentially 2x AT CONVERGENCE = the real campaign win.
AGING RESOLVED (2026-07-22) — USER WAS RIGHT: no unbounded process aging; the "2x decay"
was WARMUP-PROTOCOL ARTIFACT. Model: from-checkpoint runs start with SYNCHRONIZED SHALLOW
env populations; over ~8-10min they reach the true steady-state episode mix (deep levels,
full monster populations). Busy/step: 21us (fresh) -> 37-40 (3min, the "320-360K" reads)
-> 70us PLATEAU (~100M+, =176-199K SPS) == in-run 166-181K ✓ ALL long measurements agree.
Allocator swap null ✓ RSS flat ✓ leaf profiles fresh-vs-aged SAME SHAPE (mfndpos/m_move/
onscary/movemon ~30% of leaves, inv_weight/t_at/sobj_at grow modestly) => steady-state
deep play is simply ~7x costlier than shallow (monster simulation dominates). CONVERGED
TRUTH: ~180K SPS floor, buffer effect ≈ nil at steady state (weakly b4>=b2), passive +7%.
PROTOCOL RULE: from-checkpoint measurements need >=8-10min warmup before windows count.
TOOLS: sigprof.so LD_PRELOAD sampler (scratchpad, NLE_PROF_DELAY/SECS/OUT) — works where
ptrace/perf blocked; leaf-frame extraction via awk first-line-after-separator.
REVISED 1M PATH from true 180K floor (5.5x): monster-path engine work mfndpos/m_move/
onscary/movemon = 30% of steady-state samples = TOP target now; + membw/touched-bytes
(front-1); + stragglers/async resets; + scaling; realistic verified path ~2-2.5x ->
360-450K; 1M likely NEEDS the opt-in no-op auto-advance reserve + overlap (other person).
Be honest with user about this gap.
MFNDPOS SURGERY R1 (2026-07-22, fork commit 7): merged garlic+boulder sobj_at pair into
one pile walk per candidate cell. Gauntlet green. Steady-state (warmed >=10min): busy
68-73 -> 50-58us/step, SPS ~206-226K vs 176-199K plateau (+10-15%, noise caveat — deep
piles are fat, the double walk was real). DESIGNED-DEFERRED next items: (a) inv_weight
memo (3% leaves, wide invalidation surface: quan/owt/invent/weight_cap-attrs — use
inv_gen counter bumped at addinv/freeinv/useup/splitobj/merged/setworn, goldens catch
misses); (b) levl.typ write-through mirror plane (helps mfndpos body+vision+dog_move —
the front-1 flagship; write sites via SET_TYP macro sweep, coherence gated by 112
recordings); (c) t_at trap-presence bitmap (2.4% leaves). m_move body itself = dispatch,
optimize via callees.
TYP PLANE SHIPPED (2026-07-22, fork commit 8): 1.7KB schar plane in ctx; rebuild at
vision_reset + write-through at 175 converted sites (SET_TYP_XY/SET_TYP_P variadic
macros, hack.h tail — E-macro-undef gotcha: use plain extern there); SET_TYP_P
bounds-check makes foreign-pointer writes safe; NLE_TYP_VERIFY=1 fill_obs hard-compare.
Readers so far: is_pool family + mfndpos. GATES ALL GREEN incl verify-mode 112/112.
MEASUREMENT HUMILITY (echo of tinybox lesson): warmed-window protocol run-to-run
variance ±20-30% — the mfndpos "+10-15%" AND the typ-plane read (194K, 71-77us — looks
like regression-or-noise) are BOTH inside noise; resolving ~10% effects needs n>=3
INTERLEAVED A/B runs per arm (~60min). NEXT: (1) convert the big readers (vision_recalc
viz loops, dog_move/m_move terrain checks) — the plane's real payoff; (2) THEN one
proper n=3 interleaved A/B of (pre-mfndpos | mfndpos | +plane+readers) to size the
whole engine round honestly. GOTCHA: NEVER clang-format .py files (mangled
record_goldens.py, was committed broken in 6d78fbe02, repaired in commit 8).
TYP PLANE V2 LANDED (2026-07-22, fork commit 9 = bfaa84189, replaces broken f99a/401e):
regenerable via scratchpad/convert_typ.py from base 991a9a251. WAR STORY — 4 bugs found
by the gauntlet: (1) COMMA-OPERATOR statements ("typ = POOL, rmflags = 0") captured
whole as macro value -> typ got LAST expr (0=STONE); fix = brace-wrapped split. (2) my
first comma-splitter broke single-statement if/for bodies (2 stmts escape the body).
(3) "lev++->typ = ROOM" post-inc form missed by regex + same for-body trap. (4) THE
SUBTLE ONE: SET_TYP_P v1 cast the pointer to rm* for the WRITE — struct damage (shk.c
repair records) has its own .typ; writing through rm* corrupted damage records at rm's
typ offset -> shop walls repaired to STONE ~50K steps deep (aa_7010 @52983, revealed
later than written). Fix: write through the CALLER's pointer type, rm-cast only for the
plane index. DEBUG METHOD THAT CRACKED IT: replayer NLE_REPLAY_DUMP_STEPS/DUMP_DIR
per-component obs dumps at the divergent step, diffed base-vs-new (one glyph: wall->
stone -> shk repair suspect list). ALSO: regeneration from base re-clobbered the
record_goldens.py repair (re-fixed, amended) — regenerating trees resurrect old bugs;
check collateral files. faketime.so must live in $STOCK_NLE_DIR. Gauntlet final: 34+78
verify-mode identical, interleaved+shuffled, stock-diff rc=0 explicit, no-globals.
N=3 INTERLEAVED A/B RUNNING (ab_engine.sh, task bcgp0xl25, ~70min): base 6d78fbe02 vs
HEAD bfaa84189 (mfndpos+plane), 3 warmed rounds each alternating, seed-7 ckpt protocol;
analyze last-3 vecprof windows per run (busy/step + elapsed/epoch).
CAMPAIGN PAUSED (2026-07-22, user: pivot back to SCORE): n=3 engine A/B KILLED before
completion — engine-round wall-clock effect UNRESOLVED (only ab_base_r1.log survives
clean in scratchpad). Tree left at HEAD c385dfe77 (typ plane v2), rebuilt, golden-
verified. ORCHESTRATION LESSONS this session: a "failed" background task's SCRIPT can
survive and keep running (two A/B orchestrators raced checkouts + SIGKILLed each other's
trainers) — always ps-check before relaunching, lockfile added to ab_engine2.sh. RESUME
POINT when campaign continues: run ab_engine2.sh (locked, resumable) to finish the n=3;
then per decision framework: >=+10% -> viz narrowing next; null -> cached-logits no-op
skip (semantics-preserving, ~1.2-1.3x) then the auto-advance opt-in question (1.15-1.5x,
comparability break). 9 unpushed fast-nle commits now (partial fills, stock-diff harness,
tty-skip+recorder, mmap+lazy-vt, mfndpos, typ-plane v2 + fixes).
2026-07-23 FORK HASH REWRITE (Claude co-author trailers stripped pre-push, trees
identical, backup branch backup-pre-strip): c385dfe77->3fcd7d8e4, 401e98598->
d674b9e20, f99a097ce->3d501049c, 991a9a251->c3086da1a, ada28c71a->cd6873dc7,
6d78fbe02->2afcfa636, edf8885f3->f17aeba39, 028a6a6cc->81208cf10. Old hashes in
earlier notes map through this table.

2026-08-04 async CLOSED for score: maintainer's co-adapted async recipe (5d508154: 256 agents/horizon 512/lr 0.00176/clip 0.48/ent 0.019/no-eps, momentum=their beta1 0.9695) x our score coeffs = STABLE (no 50M collapse — collapse was hyper mismatch) but plateaus ~3300-3400 by mid-250M, sags to ~3100 = half of sync champion 6200. Async trainable-but-inferior on every hyper set we own; +8% SPS ceiling (env-bound) not worth a dedicated sweep. Sync stays.

PROFILE 2026-09-05 (user: "use the local box to profile training; env slows over time; note async"):
- ENV-BOUND THROUGHOUT under async. champ2b_s901 per epoch (131K steps): rollout 0.79s early -> 1.02s at 1.75B,
  of which env 0.56 -> 0.79s (+41%), model fwd 0.13 -> 0.11, copy 0.03; GPU train step flat 0.44 -> 0.42s and fully
  hidden. SPS 174K -> 130K as mean episode length 1,058 -> 2,706 turns. Same shape in sw0367 (env 1.11 -> 1.54s).
  My earlier "train-bound" read used the inline-EVAL epoch row (last column of the 5-point series) -- never do that.
- Per env-step on a worker (128 envs/buffer, 8 OMP workers, static 16-env chunks): 138us early -> 194us late.
- WHERE: callgrind (trained demo, Sep 2 data): puf_step = 1.37M Ir/step; engine 95% of it, env layer ~5%;
  inside engine movemon->dochug->m_move->mfndpos = 83%. Cost scales with monsters on level -> that is the slowdown.
- Late-regime rollout-only (eval from 2B ckpt, 3000 games, len ~1,930): threads 8/16/32 -> 64/87/118K steps/s
  (saturating 1.36x per doubling; Sep-2 early regime 142/184/254K). Early rollout-only ~312K -> late 118K = 2.6x.
- Buffers (26M scratch, async, true SPS by uptime): 1/2/4 -> 203/245/246K. The Sep-2 "buf1 530K" was the eval-row
  SPS artifact. Async vs sync at scratch: 246K vs 201K (+22%). Scheduling (static/dynamic/ws/lock-free) and thread
  count showed no gain on Sep 2 (envprof util 97%: no straggler problem early).
- GOTCHAS: `train` has NO warm-start (load_model_path is eval/match only) -> late-regime profiling = `puffer eval`
  from a late checkpoint; perf_event_paranoid=4 and read-only sysctl -> use callgrind on the demo; /usr/bin/time and
  bc absent -> use dashboard Uptime + CUDA_EVAL games x episode_length.
LATE-GAME ENGINE-ONLY PROFILE (callgrind --toggle-collect=nle_step, trained demo 14K steps, 5 eps, 2026-09-05,
scratchpad/prof/cg_late_{incl,self}.txt): movemon 76% incl (dochug 72, m_move 58, mfndpos 17, dog_move 17 = PETS,
distfleeck 7.5, onscary 7.1, can_reach_location 5, dogfood 3.4, gettrack 2.4); hero domove 15% (newsym 6, vision 3.5);
message/--More-- path ~8% (vpline 8, xwaitforspace 7.7, nethack_drain_prompts 7.4, update_topl 7, more 7).
Self: mfndpos 11.6, m_move 10.2, onscary 5.0, newsym 4.0, dog_move 2.1, RNG 2.6, gettrack 1.7, money_cnt 1.55 (only
used for Xorns in set_apparxy -> hoist = free exact win), inv_weight 1.4, visible_region_at 1.1, sobj_at .9, t_at .9.
Bit-exact potential from hoisting/memoizing (onscary per turn, dog reachability per turn, region early-out,
money_cnt/inv_weight caching) ~15-25% of engine, NOT 2x. Levers that don't change game rules but do change the RL
interface: turns/step (5.6 now: runs/searches) and --More-- keypress round trips (~8%). Hardware: 12 P-core equiv.
CONCURRENCY SCAN 2026-09-05 (eval from 2B ckpt, late regime, taskset-pinned): P-cores 1/2/4/8 threads at 32 envs
per worker -> 5.5/11.7/23.5/43.8K steps/s = PERFECTLY LINEAR, per-worker ~175us/step constant. Agents 64..512 on 8
P-cores: no change -> NO cache-capacity or contention problem. Core mix: 8 P-cores 55.8K, +HT 68.7K (+23%),
16 E-cores 69.2K (E ~0.7x P), all 32 threads 103.9K. The Sep-2 "43us single-thread" was not comparable.
=> late-game env step really costs ~170us of engine work (5.6 turns x ~30us); throughput = cores x 1/170us.
Parallel agents cannot speed movemon (monsters move in RNG-dependent order within a game); more cores scale linearly.
CACHEGRIND 2026-09-05 (engine rows, trained late-game demo, P-core cache model): D1 miss 0.63% of accesses (2.5/kIr),
LL miss 0.12/kIr -> NOT memory-bound; struct sizes monst 144B obj 96B rm 8B nh_ctx 214KB. Branch mispredicts 4.75%
of branches = 9.5/kIr; mfndpos 18.7/kIr (9.8%), m_move 13.1, newsym 16, vision_recalc 18.4, should_displace 16.9%
rate, gettrack 10%. mfndpos+m_move = 46% of engine mispredicts. => engine is branch/compute-bound; allocator
locality / hot-cold split RETIRED as levers; PGO + per-turn cell bitmaps (branch -> table lookup) are the levers.
