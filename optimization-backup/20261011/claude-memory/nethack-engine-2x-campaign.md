---
name: nethack-engine-2x-campaign
description: "2026-09-05 exact-engine speed campaign CLOSED: engine 1.32x bit-exact (LTO+PGO+7 hoists, build-b7pgo) = +28% late-regime rollout, ~0 early (GPU-bound); policy-golden harness (NH_KEYTRACE_DIR, rr_replay +-1%); async=0 flags-file gotcha; hand-off diffs in scratchpad prof/"
metadata:
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
---
User mandate 2026-09-05: "make nethack itself fast ... aim for 2x ... don't stop till we're at 2x", game behaviour bit-exact.
MEASURED DECOMPOSITION (champion 1B ckpt, late regime, 4090 box):
- engine (nle_step) = 15-20 us per engine KEY, ~2.03 keys per RL step -> ~35 us/RL step; unaffected by env count
  (rr_replay N=6..384: 17-20 us) or 8 threads sharing L3 (15.6 us) -> cache locality is NOT a lever (again).
- full env step (puf_step: wrapper + engine) = 35 us single-thread demo replay; inside the real vec loop
  (NH_STEP_TIMER=1 in puf_step): 8 P-core threads mean 68 us (p50<16, p99<262, max 17 ms resets); 32 threads mean 101 us.
- eval bench (43.7K SPS, 8 threads, 1 buffer) = 183 us per worker-step -> env step is ~37% of it; the rest is GPU
  forward + copies + python + sync. Training env region (0.79 s/epoch, 32 thr) = 193 us per worker-step vs puf_step
  ~101 us -> ~half of the env region is outside puf_step (barrier imbalance / E-core+HT stragglers / omp overhead).
- engine-only capacity: 1.01M keys/s at 32 threads (497K RL steps/s) vs training env-phase 166K steps/s.
=> exact engine work caps at ~+20-30% training SPS; the 2x lives in the rollout scheduling (pufferl.cu, off-limits:
   patch + hand off) and reset hiding. The earlier "engine = 83%" claim came from an engine-only callgrind and was wrong.
HARNESS (all under scratchpad prof/, recipes):
- Recorder: ocean/nethack NH_KEYTRACE_DIR=<dir> writes each episode as a fast-nle golden (keys only, "init 0"),
  NH_ACT_RECORD/NH_ACT_REPLAY=<file> record/replay the demo's action vectors (demo runs env-only, no CPU policy).
  Goldens need new metas (time_seed, underfoot_glyphs=1, true_glyphs=1) parsed by patched tests/replay_golden.c
  and tests/replay_multi.c (env uses time_seed=seed, replay_golden defaults core+1 -> different game otherwise).
  Hash with NLE_REPLAY_UPDATE=1 against the PRODUCTION lib, mv .new -> .golden. 6 episodes / 28,444 keys from
  NH_MULTI=1 NH_SEED=7 nethack_demo 14000 0; replays identically in all 3 modes.
- rr_replay.c: round-robin N envs x T threads, --partial mirrors the env's obs.partial=1, --hash gates.
  Timing precision +-1% (vs eval bench +-6%; eval bench also can't isolate the engine). ONLY time on a quiet box.
- eng_chain.sh <tag> [ref]: LTO side build -> 34 goldens x3 + policy goldens x3 -> rr timing vs ref.
  pgo_build.sh <tag>: LTO+PGO (profile = policy workload) same gates. gate_lib.sh, bench_lib.sh (eval bench).
GOTCHA (2026-09-05 PM): scratchpad prof_champ_flags.txt carries --base.async=0, but every real run (champ2b_s90x,
sw*_1b, k32) trains with async = 1 (config default). Sync probes understate SPS ~40% (189.9K vs 314.6K async, same
12M probe) and show a fake 'train phase not overlapped 34%'. Always sed async=0->1 (or drop the flag) for probes.
TRAINING PROBE (champion cfg 512 agents/32 thr/4 buffers, early regime, NH_STEP_TIMER in a 12M-step train, SYNC):
SPS 181K; env region 49% of epoch, puf_step mean 41 us; workers are in puf_step 67% of the env region (not 97%).
Engine ~60% of puf_step time -> ~20% of an early-regime epoch (~30% late). fastmod RNG (rnd.c, magic table
include/nh_fastmod_tab.h from prof/gen_fastmod.py, verified 8e8 checks) = batch b4.
FINAL (us/key, rr_replay quiet box, bit-exact on 40 goldens x3 modes): production 16.54; LTO 15.10; +money_cnt/gas hoists
14.68; +NH_ONSCARY inline + were gate 14.58; +track 3x3 prefilter (b3) 14.31; +fastmod RNG 14.47 (NEUTRAL, reverted:
Raptor Cove div is fast); LTO+PGO 13.25; b3+PGO 12.73 = 1.30x. TRAIN A/B (12M steps, champion cfg, interleaved x2):
prod 189.0/189.9K SPS -> b3pgo 204.1/204.8K (+8%), env region 320->265 ms/epoch (-17%). ASYNC (real config) A/B: early-regime train 313.8/314.2K -> 315.0/316.3K (+0.5%: GPU-bound, sm-util mean 80%, >=95%
half the time); LATE-regime rollout-only (eval 2B ckpt, async nb4 32thr, identical games) 106.6/108.1K -> 138.4/138.4K
steps/s (+28%, wall 16.3->12.7 s). Recorded 2B profile (rollout 1.02 s, env 0.79 s, train 0.42 s hidden) predicts
~+20% SPS late; no late training A/B possible (train has no warm start). Verdict: 2x on the engine
is NOT reachable by exact micro-opts (flat profile); delivered 1.30x = +28% late rollout, ~0 early. Hand-off: prof/handoff_fastnle_engine_MINE.diff
(11 files), handoff_env_side.diff (recorder/timer/act-replay diagnostics), handoff_fastnle_tests.diff (driver metas);
final lib vendor/fast-nle/build-b3pgo (production build/ untouched). pgo_build.sh reproduces it from the tree. Profile is FLAT: no source line >1.1%; per monster-turn ~4.6K Ir
(mfndpos 1.1K, m_move 0.84K, newsym 0.4K, distfleeck 0.5K, onscary 0.33K, gettrack 0.2K); 56 monster-turns/RL step.
ROUND 2 (2026-09-05 PM, "proceed with more optimisations"): wrapper is FREE in time (26 us/RL step total vs
~25.8 us of engine keys single-env): packer K-nearest restructure and an unchanged-cell skip were both byte-identical
(NH_OBS_HASH gate in the demo, ref hash da195d84b9f76028 over 14K steps, same for prod and b3pgo engines) but
time-neutral -> reverted (backup prof/nethack_h_with_packer_skip.bak). Ir != time here. Engine b5 = should_displace
gate + NH_MINLIQUID inline (-2.3% quiet). b6 = plain onscary in distfleeck (arg is always the hero square) +
pile-bit guard before sobj_at in onscary. b7 = track prefilter as per-column 32-bit masks (nh_track_bits).
REJECTED: reordering lined_up() in m_move -- it calls rn2(25) when Upolyd (RNG side effect in a "predicate").
FINAL quiet ladder (us/key): prod 16.55, b3 14.46, b5 14.16, b6 14.14, b7 14.04, b3+PGO 12.9, b7+PGO 12.5 = 1.32x.
Late rollout A/B (async nb4 32thr, 2B ckpt, identical games): prod 111.7/109.2K, b3pgo 138.7/136.8K, b7pgo
141.3/140.9K steps/s (+28%). Candidate lib = vendor/fast-nle/build-b7pgo. TIMING GOTCHA: never time within ~60 s
of a -j32 build (thermal: same lib reads 17-18 then 12.5); chains now sleep 60 before timing; use the last reps/min.
RESET-AHEAD (2026-09-05 late, user: "build the reset-ahead"): env-side (ocean/nethack/nethack.h, NH_RESET_AHEAD=<helpers>,
default 2, 0=off). Helper pool ends the old ctx, nle_start()s the next game (next LCG seed) into a per-env staging obs,
and runs the boot prompt drain (same loop as nethack_drain_prompts); the terminal step swaps ctx, memcpys the staging
obs, writes the drain keys to the key trace, then continues the reset tail. EXACTNESS: byte-identical in the demo
(60K-step hash + 25 traces) and in the vec (256 agents/1277 eps and 512 agents/3559 eps, 0 diverged). LANDMINE:
a second vardir per env (to avoid level-file collisions) made 9/256 envs diverge from their 2nd episode on,
deterministically -- unexplained, but a SINGLE vardir is provably safe (getlock() is compiled out under RL_GRAPHICS,
a parked game writes no level files, LFILE_EXISTS is in-memory, no panic saves) and identical. RESET COST CORRECTION: the 0.6-1.7 ms 'mean reset' was inflated by the 256 boot resets firing at once
(3+ ms each under contention); per-phase timing (boot split out): in-episode sync reset 381 us (nle_end 47, nle_start 317, tail 17);
reset-ahead swap 39 us; boot resets 2.5 ms each (256 at once, synchronous by design). 512 agents, 3000 eps, identical
games: 149.8K -> 150.3K steps/s (+0.4%). A 0.3 ms reset on one thread rarely extends a region whose slowest thread
is already ~0.6 ms from ordinary heavy steps -> the 33% idle is per-thread variance + P/E/HT heterogeneity. The 33% idle in the env region is NOT resets; it is per-thread work variance + P/E/HT heterogeneity
under the static split (dynamic distribution is the remaining lever; prof/pufferl_sched.patch from Sep 2 exists).
Helpers are not starved (1276/1277 swaps ready).
GOTCHA (self-kill x3): never pgrep/grep a literal that also appears in the same command line (kills the tool
shell, exit 143/144); match /proc cmdline prefixes and exclude the shell's ancestors, or use pid files.
DYNAMIC SCHEDULING (2026-09-05 evening, prof/pufferl_sched.patch = the tree's pre-existing M src/pufferl.cu;
build with NVCC_EXTRA=-DPUF_ENV_DYN=<chunk>): late-regime rollout 512 agents identical games: static 147.4/149.3K ->
dynamic,1 166.0/166.4K (+12%). Early regime: SPS unchanged (GPU-bound) but Env region 244->351 ms and step mean
36->39 us = lost core locality with chunk 1. The Sep-2 "no gain" verdict was early-regime only. Chunk sweep (late 512): static 149K, dyn1 165K (+11%),
dyn4 159K (+7%, no early locality loss: Env 248 ms), dyn8 149K (16 chunks < 32 threads), guided 166K (+12.7%,
Env 329 ms early). WORK-STEALING WINS (home block per worker + steal from other blocks' tails via per-worker atomics; guarded
#ifdef PUF_ENV_WS in prof/pufferl_sched_ws.patch, build NVCC_EXTRA=-DPUF_ENV_WS=1): late 512 agents 167.9/168.7K
(+13.6% vs static 148K, dyn1 166K); early regime Env 216 ms (static 244, dyn1 351) -> no locality loss, better
balance. Recommend this variant for the hand-off. Trainer source left at the pre-existing sched patch (33 lines).
Reset-ahead under the dynamic schedule: off 164.0/164.5K vs on 165.0/165.7K (+0.7%) -> default set to OFF
(NH_RESET_AHEAD=0 unless set); kept as opt-in. NET LATE-REGIME ROLLOUT: production 116K -> 168K = 1.45x.
COMBINED (one config, 512 agents late, identical games): production+static 116K -> b7pgo+static 147K (+27%) ->
b7pgo+dyn1 165K (+43%, wall 50.5 -> 35.4 s). Scheduling is train-side (pufferl.cu) = hand-off, not committed.
STEP TAIL (late 512 agents, 6.95M steps, NH_STEP_TAIL in the timer): steps >1 ms = 4,505 (0.065%): 1-2 ms 4221,
2-4 145, 4-8 32, 8-16 75, 16-32 32, max 20.6 ms; time in >1 ms steps = 1.2% of all step time. Of the 284 >2 ms:
220 level changes (mklev), 56 multi-turn actions, 8 other. Upper bound on region stall under work-stealing ~10-15%
(each heavy step extends its region), realistically less with 4 buffers overlapping; mklev total ~1 s of 35 s ->
not worth engine work. Remaining late-regime cost = per-buffer pipeline (forward + copies + fork/join per 0.25 ms
of env work).
PIPELINE PROBES (late 512, puffer_ws build): threads per buffer 32/16/8 -> 173.5/127/90K (4 buffers x 32 OMP
threads oversubscribe 32 CPUs but that is NOT waste: buffers' env phases are mostly sequential, each needs all
32 workers); OMP_WAIT_POLICY=passive 168.5K, GOMP_SPINCOUNT=10000 168.6K (no effect); buffers 2/4/8/16 ->
160/173/182/164K (nb8 +5%; nb16 = 1 env/thread, fork-join bound). Env work is ~45-55% of CPU time; the rest is
per-buffer pipeline latency (forward launch, D2H, sync, H2D, fork/join per ~0.34 ms of env work). Next real lever
= decouple env stepping from buffer regions (persistent worker pool + global ready-queue, EnvPool-style) in
pufferl.cu; upper bound ~+60% late. Training nb>4 needs the cuBLAS-workspace nondeterminism trigger resolved.
BUFFER CYCLE (late 512, nb4, 32 thr, ws schedule, PUF_CYCLE_PROF side build): per buffer per step:
fwd+D2H+sync 0.46 ms, env region 1.8 ms (!), upload 0.03 ms. CORRECTION: vec->num_workers = num_threads / num_buffers -> each buffer has 8 DEDICATED
OMP workers (no oversubscription); region = 128 envs / 8 threads = 1.34 ms + stragglers. A buffer's 8 workers idle
during its 0.46 ms forward+sync (20% of the 2.3 ms cycle) -> shared pool across buffers is the fix. CPU-bound ceiling ~500K
steps/s vs 173K. Rollout forward is already CUDA-graphed per step (rollout_graphs). -> pool prototype.
SHARED ENV POOL (prof/pool_edit.py -> pufferl_sched_ws_pool*.patch, -DPUF_ENV_POOL=1): 32 persistent workers,
per-worker home sets (env i -> worker i % 32) stolen across workers AND buffers; buffer threads submit + help + wait.
EVAL late 512 nb4 identical games: ws 171.8/175.2K -> pool 191.5/199.9K (+13%); pool nb2 201.8K, nb8 178.8K.
LANDMINE v1: workers spun (pause + sched_yield, never slept) -> in TRAINING the learner thread starved: 12M probe
took 2m32s vs 46s while the panel printed a bogus SPS 516.9K with Evaluate 0 ms. Always read Uptime, not the SPS
row, for side builds. v2 = idle workers block on a condvar after ~50 us of spinning; submit broadcasts -> EVAL -20% (136K vs 170K:
wake-up latency at a 0.3 ms cadence) and TRAINING still 1m41s vs 46s: in async training the rollout never pauses,
32 workers + 4 buffer threads stay runnable on 32 CPUs, the learner (37th thread) starves; OMP teams avoid it because
a buffer's 8 workers sleep during its forward wait. v3 = pool size total - buffers - 1 (PUF_POOL_RESERVE), spin
~1-2 ms (PUF_POOL_SPIN=200000) before sleeping.
v3 RESULT: eval late 512 nb4 186.1/204.8K vs ws 167.3/169.0K (+16%, run-to-run spread), nb8 199.3K; TRAINING
probe 58.4 s vs ws 45.8 s (-27%: learner still starved), learning metrics normal. Sweeping reserve x spin next.
SWEEP (reserve x spin; train probe wall / late eval): r5s200K 58.4s/186-205K; r8s200K 44.5s/185K; r12s200K 43.9s/201.6K;
r16s200K 44.0s/185.5K; r5s20K 46.6s/170K; r8s20K 45.0s/193.5K. WINNER reserve=12 (20 workers + 4 helping buffer
threads), spin 200K: training 4% faster than ws (early regime, GPU-capped) and late eval 201.6K = +20% over ws,
1.74x over production (116K, same config, identical games). Default baked into prof/pool_edit.py; hand-off =
prof/pufferl_sched_ws_pool.patch (183 lines, build NVCC_EXTRA=-DPUF_ENV_POOL=1; PUF_POOL_RESERVE/PUF_POOL_SPIN
env overrides). Trainer source in the tree untouched (pre-existing 33-line sched patch only).
LIMIT (2026-09-05 end): pool utilization measured (PUF_POOL_PROF side build): 20 workers 95.7% busy, mean step
83.9 us under full 32-thread load (vs 26 us single-thread: HT siblings + E-cores + all-core clocks = physical).
The rollout is CPU-bound on this box: ceiling ~250K steps/s late with every logical CPU stepping; at ~210K the
rest is the learner's reserve. Remaining multipliers: per-step CPU cost (engine flat, ~5% exact left), keys per
RL step (2.03: prompt drains -> interface change, not exact, user's call), cores per GPU (linear), and then the
learner cap (~310K SPS late from the recorded 0.42 s train step). Trainer source in tree untouched.
BOX CHECKS (user: "this box is fast"): governor powersave/intel_pstate, turbo on; under 32-thread load P-cores hold
5.2 GHz, E-cores 4.2 GHz for 30 s (two dips were sensor artifacts; engine throughput flat at 1.16M keys/s); package
temp 86-92C; throttle counters not exposed; RAPL not visible; THP = madvise (sysfs read-only); RAM 123 GB.
Next tries: PUF_CUDA_BLOCKING (cudaDeviceScheduleBlockingSync so buffer threads/learner sleep in CUDA waits ->
smaller pool reserve) and a 2 MB huge-page per-env ctx (prof/thp_edit.py, exact) via pgo_build b8pgo.
RESULTS: PUF_CUDA_BLOCKING (cudaDeviceScheduleBlockingSync, guarded, in prof/pufferl_sched_ws_pool_bs.patch): training
probe reserve 5/8/12 -> 45.7/43.5/43.4 s (pool3 without it: 58.4/44.5/43.9); late eval r5 190K, r12 207.9K (+3%).
Makes the pool insensitive to the reserve; recommended build -DPUF_ENV_POOL=1 -DPUF_CUDA_BLOCKING=1, reserve 12.
THP ctx (b8pgo): exact (40 goldens) but AnonHugePages stayed 0 and the 2 MB stride between ctxs aliases cache sets:
engine harness 32 thr x 1024 envs 28.1 -> 35-37 us/key (-25%), late eval -2%. REJECTED (source restored).
TRAINING BOUND (pool+blocking sync, reserve 12, 12M early probe): GPU sm-util mean 91% (>=90% for 39 of 56 s),
uptime 43.4 s = ~0.42 s/epoch = the learner's train step -> EARLY REGIME IS NOW GPU/LEARNER-BOUND (was 80% util,
46.7 s). LATE regime: rollout 208K steps/s = 0.63 s per 131K-step epoch vs learner 0.42 s -> CPU/rollout-bound by
~1.5x; GPU would sit ~67% busy. A long run is GPU-bound early, CPU-bound late; cores fix late, learner speed fixes early.
GPU RESIDENCY OF ROLLOUT FORWARDS (pool+bs): late rollout alone keeps the GPU busy: nb1 145K/25%, nb2 195K/50%,
nb4 206K/66% sm-util (useful forward kernel time is only ~75 ms/epoch). Early TRAINING probe: nb1 48.2 s/59%,
nb2 39.1 s/77%, nb4 43.4 s/91% -> nb2 = +11% training SPS on top, config only (needs the pool; with static OMP
nb2 was worse), and nb2 is outside the cuBLAS nondeterminism trigger (horizon*nb = 512 = agents). Copies are ~3%
(obs H2D 548 MB/epoch in 33 ms, actions D2H 10 MB): not a lever. Late regime is GPU-contended too (rollout 66% +
learner 0.42 s), not purely CPU-bound.
SAMPLING KERNEL (user: "do the sampling kernel"): nsys of the rollout forward (nb2): 79 launches/forward, 4.5 us
mean; sample_logits = 39% of forward GPU time at 140 us/call (one THREAD per agent walking 730 logits x 20 heads
serially, 256 threads on the whole GPU). prof/samp_edit.py adds sample_logits_warp (PUF_SAMPLE_WARP): warp per
agent, lanes stride the masked loads/max/exp, lane 0 keeps RNG draw order, cumsum, legal snap, logprob. Two-pass
logsumexp instead of streaming -> mathematically identical, NOT bit-identical (rounding). Side build puffer_samp
(pool+bs+warp); patch prof/pufferl_sched_ws_pool_bs_samp.patch. RESULTS: 140 -> 33.1 us/call (13% of forward
GPU time, was 39%); rollout GPU busy nb2 51->42%, nb4 67->60%; late eval throughput unchanged (CPU-bound): nb4
208.8->211.8K with IDENTICAL games (3047/1923.049), nb2 202->201K (one boundary flip); early training probe nb2
39.0 -> 37.0 s (-5%, ~324K SPS), deterministic per binary. Recommended build now: -DPUF_ENV_POOL=1
-DPUF_CUDA_BLOCKING=1 -DPUF_SAMPLE_WARP=1, num_buffers=2, reserve 12.
TRAIN-STEP PROFILE (nsys, nb2, 10 s): GPU 101% busy, 1.79M launches (179K/s, 5.6 us mean) -> launch-bound tiny
kernels. Flat: nh_bias_relu 6.4% (199K launches!), cutlass small GEMMs ~15%, splitKreduce 3.3% (181K), sample_warp
3.4%, cache_imp_and_v 3.1% (373 us, per-row serial like the old sampler), relu_bias_bwd 2.7%, ppo_loss 2.0%
(239 us), nh_loc3_scatter 1.9% (233 us), idemb_grad 1.5%. Targets in order: (1) cuBLASLt RELU_BIAS epilogue
(prof/lt_edit.py, NH_MM_LT, ocean/nethack/nethack.cu = env territory), (2) warp rewrites of cache_imp_and_v and
ppo_loss, (3) DRELU_BGRAD epilogue for the backward, (4) mingru per-timestep fusion (project-sized).
LANDMINE: the rollout forward is CUDA-graph captured (pufferl_forward cudaStreamEndCapture assert) -> any cudaMalloc
(or other non-capturable call) inside a first-use path of the encoder crashes the run. cuBLASLt v1 allocated a
workspace lazily -> crash; v2 uses workspace-free algos (NULL, 0). Also v1's nsys showed MORE launches (914K vs 539K
in 8 s): the Lt heuristic picked multi-kernel algos for these small GEMMs -> if v2 does not cut launches, drop it.
IMP WARP (prof/imp_edit.py, PUF_IMP_WARP, src/algo.cu cache_imp_and_v): 373 -> 38.8 us/call (3.1% -> 0.3% of
train GPU time); early training probe nb2 36.8/36.7 -> 36.4/36.5 s (-0.8%, within noise). Kernel-level returns are
now ~1% each (ppo_loss_compute 310 us = 2.6% next, skipped). The structural cost is 179K launches/s of tiny
per-timestep kernels (mingru) -> fusion project, not a patch.
LT v2 (workspace-free): forward launches 539K -> 392K per 8 s (-27%), kernel time 22 -> 19%; training probe 36.7 ->
35.0 s (-4.5%); late nb4 207 -> 225K (games differ: numerics). BUT nondeterministic run to run (score 224 vs 203):
plans keyed by shape only -> the two buffer threads shared one cublasLt desc and each call overwrote its bias
pointer (race). v3: plans keyed by (M,N,K,bias ptr), bias set at creation, mutex on creation, 256 plans.
LT v3 RESULT: deterministic (3 probes identical), training probe 36.7 -> 35.5 s (-3.5%), forward launches -27%.
EARLY-REGIME TRAINING LADDER (12M-step probe wall, uptime incl ~5 s startup): static async 46.7 s -> pool+bs r12
43.4 -> nb2 39.1 -> +warp sampler 37.0 -> +imp warp 36.4 -> +Lt epilogue 35.5 s = 1.32x (about 338K SPS).
Rollout-only comparisons across kernels with different numerics are apples/oranges (different games).
HAND-OFF: prof/handoff_trainer_all.patch (pufferl.cu + algo.cu + nethack.cu, all guarded), build
NVCC_EXTRA="-DPUF_ENV_POOL=1 -DPUF_CUDA_BLOCKING=1 -DPUF_SAMPLE_WARP=1 -DPUF_IMP_WARP=1 -DNH_MM_LT=1 -lcublasLt",
num_buffers=2, PUF_POOL_RESERVE 12 default. Numerics: sampler/imp/Lt are not bit-identical to the old kernels
(rounding order), but each binary is deterministic run to run. Tree sources untouched (33-line sched patch only).
LAUNCH-BOUND QUESTION (user): minibatch 2048/4096/8192/16384 -> probe 37.1/35.3/36.5/37.6 s, GPU 84/76/70/72%:
halving learner launches does NOT shorten the epoch at nb2 -> the learner is not the bound there. Pool util in the
early TRAINING probe = 51% (mean step 33.8 us), buffer fwd+d2h+sync = 0.75 ms per cycle in training (0.46 in eval):
forwards queue behind learner kernels -> early regime is per-buffer LATENCY-bound (neither CPU nor GPU saturated);
nb4 = 41.5 s at 90% GPU (contention). Cycle model: 0.75 fwd + ~0.5 env = 1.25 ms per 256 steps x 2 buffers ~ 410K
ceiling vs ~340K measured. Levers: rollout stream priority over the learner (PUF_ROLLOUT_PRIO, testing), then
forward fusion (fewer/shorter kernels -> shorter queue) -> est. +30-40% early, ~+10% late (late pool is 96% busy).
ROLLOUT STREAM PRIORITY (PUF_ROLLOUT_PRIO, prio_edit.py; patch handoff_trainer_all_prio.patch): early probe
35.5 -> 33.3 s (-6%, deterministic), nb4 41.5 -> 40.3 s, late rollout unchanged (identical games). EARLY LADDER now
46.7 -> 33.3 s = 1.40x. KEYS/STEP ANATOMY (28,444 keys / 14,000 steps): prompt drains are only 0.13 keys/step (6%);
'2','0','s' = SEARCH20 count prefix in 32% of decisions (3 cheap keys, 20 turns) -> keys/step is NOT a lever;
turns/step (5.6) is the CPU cost and is the policy's choice (user: fixed). CPU side is at the wall late (pool 96%).
DATA-ORIENTED SPIKE (user: rewrite the game for parallelism from the ground up; agreed to a 2-day spike on
mfndpos first): cross-game SIMD is impossible (divergent control flow); the real lever is per-game instruction
count. b8do = mfndpos loop with level-globals (rogue/juiblex/sokoban), door state and monster traits hoisted once per
call, one struct rm load + one m_at per cell, is_pool/is_lava inlined; identical test order/accept set/info bits.
Decision rule: if mfndpos self Ir drops >=2x and gates pass -> the subsystem rewrite (movement = 60% of engine) is
credible at 1.4-1.6x engine; if ~1.3x -> flat profile wins, answer is cores. Backup prof/mon_c_before_do.bak.
SPIKE VERDICT: b8do bit-exact (40 goldens x3) but mfndpos self Ir 753M vs 707M-equivalent baseline (no change
once inlined helpers are attributed); total 4.81G vs 4.81G-ish. LTO had already hoisted the level-global compares
(loop-invariant code motion) and inlined is_pool/is_lava; the ~125 Ir per candidate cell are the ~15 inherent
tests + loads. A data-oriented rewrite only pays if it changes WHAT is computed (precomputed per-cell attribute
planes with incremental maintenance at every door/wall/drawbridge mutation site) -> maybe 2x on mfndpos, ~1.2-1.3x
engine overall for the whole movement subsystem, with real exactness risk. NOT a 2x. Source reverted to b7
(copy of the restructured loop in prof/mon_c_b8do.c).
mfndpos CLOSED 2026-09-05 (user "do it" on the attribute-plane idea; plane NOT built, premise refuted):
- b9bl branch-light (static tests as mask arithmetic, one reject branch, hoists): exact 40/40 x3; Ir 240M->401M,
  sim mispredicts 3.99M->3.52M per 6000 demo steps; wall neutral (min 14.56 vs 14.70 us/key).
- b10pf branch-free 3x3 prefilter + ctz survivor loop: exact; Ir 585M (2.4x), mispredicts -46%; wall +9% SLOWER.
- Line map (cachegrind --branch-sim): mispredicts sit on the combined reject, the loop exits and the monster/
  diagonal tests; the real core predicts them fine — the function is instruction-bound, not mispredict-bound.
- Static-test share of mfndpos Ir ~25% -> a maintained attribute plane (97 doormask + 10 wall_info + 9 drawbridge
  write sites) caps at ~2% of engine time. Not worth 2 days + 116 hook sites. mon.c restored to b7 (prof/
  mon_c_before_do.bak); variants kept as prof/mon_c_b9bl.c, mon_c_b10pf.c, mon_c_b8do.c. No hw counters here
  (perf_event_paranoid=4) so wall time via eng_chain is the only judge.
PER-VERB COST (2026-09-05, NH_STEP_TIMER + NH_VERB_TIME in nethack.h, policy-golden replay 14K steps, b7pgo,
quiet core): 36.2 us/step, 6.09 game turns/step, 5.9 us/turn. SEARCH20 = 32% of steps but 63% of sim time (14.5
turns each, 4.9 us/turn); RUN 21% (3 turns); MOVE 8% (14 us/step). Marginal turn ~5 us, per-step fixed ~9 us (pack,
keys, display). => sim cost is turns-per-decision (policy/action design, user-fixed); exact levers left ~15-20%.
PACKER OPT (2026-09-05, ocean/nethack/nethack.h, exact: NH_OBS_HASH 14K da195d84b9f76028 + 56K 73daa5c78640676b
unchanged): per-step packer 4.2 -> 2.4 us of a 36 us step. AVX2 cell pass (target attr + __builtin_cpu_supports
dispatch, scalar tail; 4 disjoint glyph classes -> blend order free; hero cell as linear index guarded for
out-of-range blstats) 1.28 -> 0.67 us; fused item-cell scan; item tokens: stable counting sort by Chebyshev d ==
repeated first-minimum selection (fallback if d>255) 1.32 -> 0.11 us; mask shortcuts (class-set skip, weld hoist)
exact but neutral (mask 0.98 us = slots predicate 0.60 + moverefine 0.27, left). NH_PACK_PHASES/NH_MASK_PHASES/
NH_VERB_TIME timers under NH_STEP_TIMER. Demo replay step 36.2 -> 34.4 us (-5%). End-to-end late rollout A/B (identical games, 3 alternating pairs):
plain static build 142.0 -> 142.8K (noise); pooled build (reserve 12, nb4) 186.9 -> 190.5K = +2%, every pair
positive. In the tree (uncommitted, hand-off prof/handoff_env_side.diff); nvcc compiles nethack.h as C++ via
pufferl.cu -> file-scope statics must be declared once (the duplicate tentative def broke the old-side build).
AGENT COUNT + PLACEMENT (2026-09-05, pooled build): in-rollout env step mean grows with resident games (32 thr,
20 workers): 128 ag 58.6us / 256 67.2 / 512 75.3 / 1024 106 (p50 16->16->33->66) = cache-capacity footprint, ~22%
already paid at 512. Late eval bench: 256 ag 189.6K, 512 213.1K (+12%), 1024 158K, 2048 147K. Early 12M probe:
512/h256 33.1s, 1024/h256 36.4s, 1024/h128 36.1s, 2048/h64 43.0s, 2048/h256 CRASH (cudaStreamEndCapture assert in
train_impl at batch 524K). => 512 is the sweet spot on the current rollout; more agents lose. DIAGNOSIS 2026-09-05 (per-CPU timer + key split):
core mix identical at 512 vs 1024 (P 8% / HT 34% / E 58% of steps) but every core type +40-50%; engine key 29.8->42.4
us, packer cell pass 1.2->2.2 us (cold data); tracks TOTAL agents not envs/buffer (nb2/4/8 same). Engine-only rr with
the champion's DEEP goldens (prof/late_goldens, 8 longest, 6000 keys/env, 1 thread): 64 env 15.1 / 256 15.4 / 1024
18.2 us/key => per-game working set of late games exceeds cache; small on one idle core, x3 in the 20-worker shared-
L3 rollout. Old demo goldens were shallow (flat). EARLY regime too: 40M probe 512 104.8s vs 1024 116.8s (-11%); in-training env step 38.4 -> 62.5 us, engine key 8.6 ->
15.6 us (+81%) at 1024 => the 36MB L3 is the binding constraint above ~512 resident games in BOTH regimes (shared by 20
workers + learner + pinned obs). Cure = cut per-step touched bytes per game (measure by structure first: lackey on the
demo; then hot/cold nh_ctx split, obs/tty writes), or a big-L3 host (3D V-cache / EPYC), or accept 512. BUT engine-only rr_replay with the OLD goldens is FLAT: 1 thread 4->1024
envs 24->14.9 us/step, 8 P-cores 64->4096 envs 26.3->23.7 (rr at 32 thr is barrier-confounded, don't use). So the
rollout gradient is NOT the engine's footprint; it is rollout-side (P/E/HT core mix under the pool, wrapper/trainer
buffers, or pool behaviour at 1024) and undiagnosed. Next diagnostic: per-worker step means (PUF_POOL_PROF) by core
type at 512 vs 1024, and trainer per-buffer costs at 1024. Config survey: repo default 4096 agents/h64/batch 262K/mb
8192; nethack 512/h256/131K/mb 4096 = smallest agents+minibatch, longest horizon; 1024/h256 would be a median batch.
Placement (nh_ctx_gen.c env-var switches,
gated exact, kept as prof/nh_ctx_gen_c_placement.c, reverted): THP now GRANTED (1GB AnonHugePages) = -5% (2MB-
aligned ctx aliasing), set coloring neutral, THP+color neutral -> TLB/aliasing are not the footprint cost; only
shrinking the per-step working set would be (hot/cold split, multi-day, unproven). sizeof(nh_ctx)=216KB.
Partial fill (nle_obs_refresh/obs.partial) IS in the fork and used by the wrapper.
COLD-TRAFFIC BUDGET (2026-09-05, cachegrind D1=32K LL=64K = per-game L3 share at ~600 games; demo replay 4000 steps,
prof/cgfp_demo_small.out): ~770 LL data misses/step after removing ld.so/startup noise. Wrapper+obs path ~45%:
memcpy 109 (fill_obs glyph/char copies + packer glyph copy), nh_cell_pass 80 (glyphs+terr+obj_mem), fill_obs 84,
nethack_pack_obs 47, puf_step_inner 17. Engine ~55%: mfndpos 62, vision 49, isaac64 30 (2KB RNG refill),
rhack/newsym/wipe_engr/timeout ~17 each, calc_capacity+encumber 23. Engine-only with the same tiny LL: 234/key,
i.e. the wrapper traffic evicts the engine set between keys -> engine misses x5-7 in the full step. PLAN (exact by
obs hash): fill_obs writes glyphs straight into the pinned obs slot (no env->glyphs copy, rebind at sync/reset/
reset-ahead), NULL chars if unused, drop terr_mem (never read), compact env struct hot fields -> ~-25% cold traffic
(~+9% late SPS at 512, moves the cliff). Deeper: engine-side layout (viz arrays, monster structs), days.
ZERO-COPY CUT 1 SHIPPED (2026-09-05, in tree, hand-off prof/handoff_env_side.diff): glyphs bound into the pinned
obs slot (nethack_bind_glyphs, re-bound on slot move with a carry copy, glyphs_local fallback), chars filled only
when a renderer asks (nethack_want_chars), terr_mem deleted, obj_mem lines rewritten only on change, env struct
regrouped hot-first (cold: chars, glyphs_local, settings x2, vardir, reset-ahead). Exact: obs hash 14K+56K
unchanged, identical games in the vec A/B. Pooled late rollout, 3 pairs @512: 196.0 -> 207.4K (+5.8%), env step
79.6 -> 74.8 us, ENGINE key time 70.9 -> 67.3 us/step (less eviction); 2 pairs @1024: 150.4 -> 163.6K (+8.8%).
Cachegrind small-LL misses only -3% (writes -14%) -> the simulator underweights the real effect. Next cuts are
engine-side (vision arrays, RNG refill, monster/object arena) or more wrapper obs shrinkage.
LOOP ITER 1 (2026-09-05 22:xx, per-game arena, fast-nle NH_ARENA): include/nh_arena.h + src/nh_arena.c (64MB
MAP_NORESERVE per game, 16B classes to 1KB, per-class free lists, zero on hand-out, libc fallthrough), alloc() hook,
global.h free() macro -> nh_arena_free_hook (range check on current_nle_ctx's arena), nle_ctx_t.arena, nle_start
creates, nle_end destroys; define scoped to the nethack target (global define broke util tools at link). LANDMINE:
nh_ctx_free in nle_end frees ctx heap members -> must run BEFORE arena destroy and BEFORE clearing current_nle_ctx,
else arena blocks hit libc free -> SEGV only at scale (512 envs; 16-env repro was clean). First-pass gates passed
LTO+PGO, hashes exact, KEPT 2026-09-05 23:00: pooled A/B (lib swap b7pgo -> b7arpgo, puffer_pool_zcnew, identical games): 512 ag
210.1 -> 219.6K (+4.5%, pairs +3.8/+2.7/+7.2), env step 73.7 -> 70.2 us, engine key 66.3 -> 62.8; 1024 ag 163.9 ->
166.9K (+1.8%, both pairs +). Gates exact LTO+PGO, hashes exact. Fork tree now carries the arena (NH_ARENA on for the
nethack target); candidate lib build-b7arpgo; hand-off prof/handoff_fastnle_engine_arena.diff (incl. new files).
Cumulative today at 512: 187 -> 220K pooled (+17%): packer, zero-copy obs, arena.
LOOP ITER 2 (2026-09-05 23:1x): profile of the current build on the champion's deep golden (53.4K Ir/key): movemon 62%,
m_move 39%, mfndpos 15.6%, distfleeck 12.3%, onscary 9.8% (17 calls/key), sengr_at 5.6% + fuzzymatch("Elbereth") 5% ->
queue item 5 chosen. Built nh_elb_plane[COLNO][ROWNO] (globals.def hot, gen_ctx.py regenerated) = engr present &&
!HEADSTONE && fuzzymatch Elbereth, maintained in nh_engr_plane_fix/sync + after in-place wipeout_text in
wipe_engr_at, checked in nh_engr_plane_verify (NLE_PLANE_VERIFY); nh_elbereth_at(x,y) adds the engr_time<=moves gate;
callers onscary (monmove.c) and mon.c:2920 switched. Items 2-4 skipped with evidence: per-line cold misses after the
two cuts are diffuse (largest line ~9/step), vision top line 1.7/step, RNG refill cannot shrink exactly. Chain
item_b7el (LTO gate vs b7ar -> PGO vs b7arpgo -> hashes -> pooled A/B) running; generic driver prof/item_chain.sh. LANDMINE: make_engr_at called nh_engr_plane_fix BEFORE storing
engr_txt/type -> the flag read a NULL text -> every replay segfaulted (gate showed empty OK lines, not a mismatch);
fix moved after the field stores (exact for the pointer plane too). Smoke: 1 golden + 6 shuffled w/ PLANE_VERIFY OK.
ITER 2 RESULT (23:2x): Elbereth plane EXACT (gates LTO+PGO, hashes) but A/B null: 512 pairs +2.8/-1.9/-0.2% (mean
+0.2%), 1024 +1.6/+0.7%; PGO single-thread 16.21->16.06. Deep-golden profile share (onscary+sengr_at+fuzzymatch
~15% of that game) does not carry to the champion eval mix. REVERTED per every-pair rule; variant saved
prof/elb_variant/elbereth_plane.diff (re-apply if the agent's Elbereth use grows). Fork tree back to arena state.
A/B NOISE FLOOR: pairs scatter +-2-3% at 512 -> only >=3% effects pass; queue items 6-7 (est 1-2%) are below it ->
skipped; exploring bigger levers (trainer-side/GPU forward) next.
ITER 3 EXPLORE (23:2x) early-regime GPU capture (nsys, 6M steps pooled nb2 512ag, prof/fwd_early.nsys-rep): 4.04M
launches/17s (235K/s), 126 kernels, 22.6s kernel time (131% aggregate busy); rollout streams 15/16: 55 kernels &
365us kernel time per 256-agent forward, stream util 31%; learner streams 1044/1046 18%. Top: bf16 gemm_relu 6.9%,
sample_logits_warp 4.6% (28us!), small wmma gemms 3-5us x1M, splitKreduce 336K x1.7us, nh_* encoder kernels ~10/
forward (~80us), mingru_gate 112K. => early regime = launch-throughput bound; fusion (encoder nh_* in nethack.cu =
env territory; gemm split-K off, mingru fuse, sampler = train side) ~+25% early. NOT the late-regime lever (CPU-
bound) -> parked. Next: worker pinning (PUF_POOL_PIN) side build A/B for late regime (core-mix lever).
ITER 3 RESULT: worker pinning REFUTED (side build puffer_pool_pin, same binary, arena lib, identical games): unpinned
221K/167K (512/1024); PIN=1 (cpu=w: 16 P-threads + 4 E) 180K/158K (-19%/-5%); PIN=3 (P-threads only, 20 workers on 16
CPUs) 36K/33K (-84%: oversubscribed spinners). Cause: buffer threads/learner/CUDA threads are unpinned spinners that
collide with pinned workers. Next: pin v2 = workers on P-threads AND buffer threads on E-cores (no collisions),
variants 16 workers vs 24 (16 P + 8 E).
ITER 4 RESULT: collision-free placement REFUTED too (puffer_pool_pin2, PIN=4: workers on P-threads 0-15 then E 24-31,
buffer threads on E 16-23): 512 base 218K vs 16 P-workers 150K (-31%, step 87us: HT pairs) vs 24 workers 195K (-11%);
1024: 167 / 138 / 172K (+3%). The kernel's dynamic placement beats static maps; scheduling lever CLOSED. Exact
late-regime levers >=3% are exhausted; remaining: reserve/nb retune probe (env vars), then validation probes of the
day's stack under training (12M/40M early regime, old lib vs arena lib). GPU fusion parked as non-exact numerics.
ITER 5 RESULT (00:0x): retune flat: reserve 8/10/12 = 224/224/222 & 210/222/217K (noise), 14 worse (213/205), nb2 200K,
nb8 216/220 ~ nb4 -> keep reserve 12 nb4. Training probes (zero-copy pooled binary): early 12M 31.0/31.2s (b7pgo) vs
31.2/31.4s (arena) and 40M 98.1 vs 97.9s -> arena neutral early (GPU/latency-bound), as expected; early 12M went
33.1 (morning) -> 31.0s from packer+zero-copy. DAY TALLY: late pooled 512: 187 -> 220K (+17.6%); early 12M probe
46.7 (campaign start) -> 31.0s. Next: one BUNDLE iteration of sub-noise exact items (Elbereth plane + winrl colors/
specials skip + mask slot predicate); if it fails the every-pair bar, stop the loop and report.
ITER 6 (00:2x) BUNDLE b7bun = Elbereth plane (re-applied via HEAD-copy + patch; the saved diff was vs HEAD and
overlapped the b7 hoists) + winrl.cc store_mapped_glyph skips chars_/colors_/specials_ writes when the obs binds
none (nle_get_obs()); mask-slot predicate dropped from the bundle (wrapper-side, would need a binary A/B, ~0.7%).
Smoke: shuffled+PLANE_VERIFY OK, 14K hash exact. Chain item_b7bun (vs b7ar / b7arpgo) running. If the bundle fails
the every-pair bar: stop the loop and report (exact late-regime levers exhausted at the noise floor).
ITER 6 RESULT (00:5x): bundle EXACT (gates LTO+PGO, hashes) but null: 512 pairs +0.5/-1.7/-0.5%, 1024 +0.7/+0.7%;
PGO single-thread 16.10->15.47. REVERTED (fork == arena state, verified). LOOP STOPPED 2026-09-06 ~01:00: exact
late-regime levers exhausted at the +-2-3% pair-noise floor. Night ledger: kept = arena (+4.5%/+1.8%); refuted =
Elbereth plane, bundle, static pinning x2, reserve/nb retune; parked = GPU launch fusion (early regime ~+25%, non-
exact numerics, needs user call). Final state: fork tree = arena (build-b7arpgo candidate lib), wrapper = zero-copy
(hand-off prof/handoff_env_side.diff + handoff_fastnle_engine_arena.diff), trainer sources restored (sched patch only).
**Why:** the user asked for 2x on the engine; the honest answer needs the decomposition above.
**How to apply:** engine A/Bs go through eng_chain/pgo_build (never the eval bench); framework levers are hand-off
patches. Related: [[nethack-sps-campaign]], [[nethack-training-profile]], [[nethack-env-speed-campaign]].
