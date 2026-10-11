---
name: nethack-5-0-scaling
description: "5.0 \"4.4K cap\" FALSIFIED — 0386 certed 5,807@1B; sweep #1 was the worst scaler (winner's curse); 0386 follow-ups"
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-21T06:04:51.930Z
---

## 2026-09-11 — claim-config 2B (claim2b_s501-504), the weights we would claim with

Config: package tree `/workspace/PufferLib_pkg` (lib bdb9896bd881, puffer feb7d8c938b0),
`NH_NLE_OPTS=1` (full NLE default option string), 2B steps, driver `certq/box_claim2b.sh`.

In-run final scores: s501 15,977 | s502 16,618 | s503 16,579 | s504 13,816.
s501/502/503 all reached a clean 2B (`0000001999896576.bin`). **s504 exited at
1.57B with rc=0**, two hours short, no OOM (476 GB free), 48h timeout not hit —
unexplained one-off; its cert is NOT claim-grade. Every cert arm now logs
`trained_steps` so unequal runs cannot be silently compared.

FORK-interface baselines (14K eps, burn-in drop 4000, `certq/base/`):
- s503 seed7  mean 16,027 (se 205) median 9,432
- s503 seed11 mean 16,417 (se 209) median 9,623
- s502 seed7  mean 16,795 (se 209) median 10,248

Median is the competition's ranking metric; AutoAscend's winning median = 5,300.

**RESULT 2026-09-11 23:08 — all certs done.** STOCK challenge certs (the claimable
number, `certq/box_chalcert_2b_q.sh` -> `certq/chal2b/`, 10K eps, burn-in 4000):

| lane | stock median | aborts | non-aborted median | fork median |
|------|-------------|--------|--------------------|-------------|
| s501 | 6,862 | 19.2% | 8,245 | 9,922 |
| s502 | 7,397 | 16.8% | 8,450 | 10,248 |
| s503 | **7,600** | 12.8% | 8,400 | 9,432 / 9,623 |
| s504 (1.57B, not claim-grade) | 6,957 | 15.8% | 7,932 | - |

Three claim-grade seeds 6,862-7,600 (mean 7,286) = **1.29-1.43x AutoAscend's 5,300**.
1B stock reference was 6,846-7,270, so 2B buys little on the claim metric.

TWO FINDINGS THAT MATTER:
1. **Non-aborted medians are flat (8,245-8,450, spread 205) while abort rate varies
   12.8-19.2%.** The policies play equally well; abort rate alone sets the claim
   number. Stalling is THE lever on the claimable score, not policy strength.
2. **Fork rank INVERTS stock rank.** Fork: s502 > s501 > s503. Stock: s503 > s502 >
   s501. s503 is worst on fork, best on stock. Fork has 0 aborts so it cannot see the
   variable that decides the claim -> **never select the claim policy by fork score.**

Interface cost on identical weights (s503): fork 9,432 -> stock 7,600, -1,832 (-19.4%).
Splits ~800 aborts + ~1,030 residual (probe budget degrades even completed episodes:
non-aborted stock 8,400 still trails fork 9,432).

Stock NLE package verified byte-identical to clean upstream before certing:
537 files, `84c24e5a811b3298`, excluding build dirs (an earlier "mismatch" was a
find sweeping in build artifacts, not a real edit).


2026-08-21 overnight screen (wandb encoders group `sweep1b`): 8 okitstime
candidates verbatim at 1B on 5.0, seed 311. The "5.0 trainer caps score
~4.4K" claim (built on 0331 + incumbent-transplant) is FALSIFIED:

0386 **5,807** (+1,466 vs native cert, still climbing at 1B; ent 0.0056
highest of slate, horizon 256 only-one, γ 0.99933) · 0383 5,083 · 0376
5,043 · 0387 4,811 · 0353 4,567 · 0392 4,303 (depth 8.5 diver). Sweep #1
0331 was the WORST scaler (~4.1K flat) — winner's curse picked the most
budget-overfit config; never judge a trainer by one config.

Standing results it revises: inc50 drift (incumbent on 5.0: 4,149/4,256
vs 5c-no-prio 5,189/5,695) = config×trainer interaction, NOT a universal
tax — 0386 on 5.0 beats the incumbent-no-prio on 5c. Prio result
(±1.5K @1B on 5c, [[nethack-prio-scaling]]) is 5c-internal and stands.
Low entropy does NOT preclude 1B scaling on 5.0 (all slate ent ≤0.0056)
— weakens the entropy-necessity story.

Follow-ups launched (f0386 chain): sw0386_1b_s312/s313 (n=3), c0386_1b_s311
(0386 on 5c = +prio cross), sw0386_2b_s311 (2B probe), censuses at tail.

**5.0 NONDETERMINISM ROOT-CAUSE HUNT 2026-08-24 (user-directed)**: NOT
fixed upstream — upstream/5.0 head (ba238f8c, 77 commits ahead) drifts
identically. BISECTED: trigger = train.horizon=256 ALONE (2M repro!);
default h=64/nethack h=128 fully deterministic (local snapshot == upstream
head, same hash fe1f4c07 — 77 commits didn't touch default-path
trajectories). EXONERATED: mingru _row kernels (drift persists with the
T>=256 dispatch disabled — fd4bfaf2 'parallelize t>=128' neither cause
nor fix), vec threading (drifts at num_threads=1), env coefs, agent
count, scalar hypers, minibatch, replay_ratio. => GPU-side, shape-
conditional at horizon-256 (candidates: cublasLt algo autotune at those
GEMM shapes, uninit padding entering compute, GAE/advantage kernels).
Non-256 horizons (129/192) CRASH (divisibility asserts) — valid probe
grid = powers of 2 only. CONSEQUENCE: every 0386-config 5.0 run
(horizon 256) incl. 5,807 was single-draw statistical; deterministic-5.0
workaround = horizon 128. MINIMAL UPSTREAM REPRO: 2×'./puffer train
--base.seed=X --train.total_timesteps=2048000 --train.horizon=256' →
checkpoint hash mismatch (5.0 nethack build; ~40s each). Worktrees:
$SCRATCH/pl50up @ upstream/5.0 (test rig, algo.cu edit reverted).

**2026-08-25 UPSTREAM PORT (branch 5.0-nethack, uncommitted)**: fresh
branch off upstream/5.0 @ ba238f8c in /puffertank/pufferlib-50 (prio-era
wip stashed "prio-era wip"). Payload = current 5c nethack (V5+SPELL2+
qnorm decoder): copied nethack.{c,cu,h}+netlib.h+2 test files;
glyph_map/macros/fs identical; nethack_policy.cu kept upstream (same
action space). Port fixes: obs_t typedef moved before pufferenv.h
include (50's pufferenv needs it); harness build() links raylib
(-L raylib/lib -lraylib + rpath — pufferl.cu include pulls
WindowShouldClose). Vendor updated to pushed fork head 1d7ab70 +
rebuilt. VALIDATED: build clean, 4M smoke sane, gradcheck FULL PASS,
determinism double-run bit-identical @33M ref 873bc744d4833b62
(--base.seed=777, horizon 128; horizon-256 bug still open upstream),
demo via ./build.sh nethack --cpu. Config kept upstream's ini. CLI form:
./puffer train --base.seed=N --train.total_timesteps=M. Commit pending
user.

**2026-08-25 HORIZON-256 NONDETERMINISM ROOT-CAUSED (framework, not env)**:
NOT horizon-specific — trigger = async(Cleanba overlap) AND num_buffers>=2
AND horizon*num_buffers > total_agents (pristine cells: h256nb4 ✗ h128nb8 ✗
h256nb2 ✓ h256nb1 ✓ h128nb4 ✓ sync-any ✓; boot rollout det). REPRODUCES ON
BREAKOUT -> upstream 5.0 framework bug, all envs. Entry: overlapped-rollout
inference FP jitter — obs EQUAL, values+actions differ at first flip
(pristine first flip t=114 buf2); unconsumed-head flips self-heal (Philox
per-agent counters resync), consumed flips diverge trajectories.
compute-sanitizer memcheck: 19K x cudaErrorMemoryAllocation on
cudaMallocAsync INSIDE cublasGemmEx (libcublas.so.13) at 8/24GB used —
cuBLAS silently falls back to different algos per call. NOT FIXED by: ws
32M->256M->2G, mempool release-threshold retain, CUBLAS_WORKSPACE_CONFIG
(int+ext), pedantic math, pinned legacy algo (GemmEx IGNORES algo param on
modern cuBLAS), graphs-off, mingru-row-off (both exonerated pristine).
GemmEx status = SUCCESS throughout (silent). Remaining fix candidates:
explicit cublasLt algo pinning (the 5c trainer approach — why 5c is
bit-deterministic) = upstream surgery. MITIGATIONS: keep
horizon*num_buffers <= total_agents (h256 needs nb<=2; SPS cost small) or
base.async=0 (SPS 251K->114K, -55%). All 0386-config (h256 nb4) history =
single-draw. Diag tooling: PUF_DIAG_HASH/PUF_DIAG_GRID patches (removed),
small repro: total_agents=128 h256 nb4 @524K steps.

**2026-08-25 REWARD CLAMP FACTS (user-corrected)**: per-step total reward
IS hard-clamped to ±1 in ALL trainers (5c pufferl.cu ~1508, upstream 5.0
head pufferl.cu ~1469 in the train-transpose path, and the 0386-era
a03a6dfb). The Aug-14 upstream refactor deleted only the COMMENT — I
wrongly declared the clamp removed by grepping comment text; verify
KERNEL CALLS not comments. Range logic under clamp: descent>=1 saturates
(sweep max 1.0 correct), gold ~0.1 near-saturating, exp_coef 0.01 makes
100+-exp kills binary (sweep min lowered to 0.001). Sweep-ini prep final:
ac_coef/scout_ready/ac_nospell REMOVED (bit-neutral, ref 873bc744
re-verified), sweep ranges = committed + scout min 1e-4 + exp min 0.001.

**2026-08-26 overnight n=6 V5@1B (IVA-bwd binary, 0386 score config): INLINE 10K CERTS (verified: 5.0 train DOES run the inline eval — Steps/Epoch freeze while score re-accumulates; [metrics] last point = cert) 6237/6098/5064/7214/5621/6556, MEDIAN 6,168 — clearly above old-arch 5,807@1B; record rolling 7,214 (sc1b_s504).** Runs ~93-121min each; late-run env-bound signature confirmed live in trainmon TSVs (GPU% →45, SPS →145-160K). DEPTH LANDMINE: ocean/nethack/depth.ini holds the prio-era 0306 recipe (h=512 mb8192) — at 1B on clean 5.0+V5 it flat-lines (dp1b_s501: score 163, depth 2.1, stable shallow equilibrium from early). The CERTIFIED 5.0 depth config is **mine50e_1b_s311** (commit 1aaf6722 on nethack-5, cert depth 10.78@1B, prio_alpha=0, agents=256 h=256 mb=4096 lr .000609 descent .808, masks on); its flag set saved at /tmp/mine50e.flags + scratchpad mine50e_1b_s311.clean.ini. depth.ini NOT yet fixed. depth×V5 test never completed (dp1b_s502 killed by user at 2min). Aug 17-18 dmulti1b_s73/74 (d10.4/9.05@1B) were the prio-patched trainer (α=.259) + old arch — NOT evidence about the current tree. SUPERVISOR LANDMINE: run_in_background leaves TWO bash processes for a driver script — pkill by name or kill ALL pids from ps -ef, then watch 100s for respawns (retry loops resurrect killed trainers on spare seeds); also a watch script's own bash -c cmdline self-matches pgrep -f patterns — verify with pgrep -x puffer + nvidia-smi compute-apps.

**2026-08-26 depth×V5 RESOLVED: mine50e @250M on V5 = max_depth 8.90 final (peak rolling 9.54), score ~1,100, eplen ~1,400 (dp250_s502, rc=0)** — near its 1B cert (10.78) despite compressed anneal. Depth is healthy on V5; dp1b_s501's flat-line was ONLY the wrong-recipe (depth.ini) error. No prio dependency for the certified config.

2026-09-04 22:06 OVERNIGHT QUEUE (user: "queue overnight a bunch of 1B runs testing out the configs"): sequential 1B runs on the
local 4090 via scratchpad/nh1b_chain2.sh reading nh1b_queue.txt; log logs/nethack/nh1b_queue.log, certs in logs/nethack/<run>.ini
[metrics] env/score last value. Order: sw0236_1b_s311, champ_1b_s311 (control = champ2b_s901 config), sw0212_1b_s311,
sw0292_1b_s311, sw0236_1b_s312, sw0367_1b_s311, sw0347_1b_s311. Flags = the sweep ini's [policy][vec][env][train] verbatim
(num_layers truncates: puf_ini_get returns double -> int, so 4.526 -> 4, 2.999 -> 2, exactly as the sweep ran them).
Sweep (211.72.13.201, alias vast) left running to completion at user request: 409/1200 trials, best 4,695 (run 236), flat since.

CURRENT 1B BASELINE (user-corrected 2026-09-05: the 9,111/9,264 v3fb record was 5c-era AND SINGLE-ROLE (Monk; multi_role did not exist until the 5.0 merge 2da3f7bf on 08-16) -> never compare it with multi-role runs): champion config (512x3, lr 0.00154,
gamma 0.99933) at 1B on the current 5.0 trainer certs 5,745-8,016 across the 09-01..09-03 arms (k32/acc/code/msgw2),
typical 6,000-7,500; 2B 7,523-8,405. Compare sweep configs at 1B against ~6.5K, never against 9,111. Champion control
REMOVED from the overnight queue (chain3 / nh1b_queue2.txt) since this reference exists.

**2026-09-06 sweep #2 (vast, config/nethack.ini multi-role, 1200 trials, ~970 done 20:40) + seed panel on the DRONE box (/workspace/sweeps/nh, 3 fresh seeds each, 10K final eval):** t865 (1024x3, 269M, 12.4M params) sweep 5619 -> seeds 5465/5269/5158 (REPRODUCES, mean 5297); t781 (1024x4, 417M) 5371 -> 5216/5168/5248; t899 (1024x4, 298M) 5372 -> 5310/5268/4752; t894 (1024x5) 4948 -> 5102/5214/4780 (beats sweep); t742 (1024x3, 301M) 5652 -> 5416/4969/4397 (lucky; NOT the pick); t916 4984 -> 4482/4117/3775 (weak). NEW BEST t973 = 5838 (1024x4, 333M, 15.55M params): a DIVER (max depth 8.3, depth-10 24%, depth-15 13%, gold 158, buys 5/ep sells 11/ep, engraves 61, throws 54, new tiles 1051; reward: descent 0.85, floor 0.19, exp 0.05, gold 0.10, xp 0.74, death_penalty 0; lr 0.00085 clip 0.42 ent 0.0083 gae 0.75); its shop use is mostly CHURN (54% of sales are items bought earlier that episode, net +20 gold/ep) because high-water gold makes spending free; 3-seed replay queued. Width ladder (best per width): 1024 5652, 512x5 t947 5430 (5.9M params), 256x4 t453 3990 (2.2M), 128x5 t643 2532 (1.4M); <=64 wide never learned (untuned random-phase trials). Score-vs-budget frontier (finals only): ~+1000 per doubling to 300M, score ~ steps^0.44; 1024 vs 512 costs ~8% wall time. Terminal demo: `NH_WEIGHTS=resources/nethack/nethack_t973_weights.bin NH_MULTI=1 ./nethack_demo_t973` (binary built from committed 97416d02 ocean/nethack via clang + vendor/fast-nle/build; the demo main is in nethack.c and infers arch from the weight count; ./build.sh nethack --cpu builds the eval runner, not the demo). Constellation page build/web/constellation_nethack (3 tables incl. finals-only + seed panel); frontier artifact https://claude.ai/code/artifact/cc1fed7c-be63-41f7-aef1-b3e927d4ed5e.
**22:30 update:** t973 fresh seeds 5659/5320/6516 (+s103 pending) = mean 5832 = sweep score -> REAL best config, wide seed spread; its best seed (6516) is the SHALLOWEST (depth 5.8) and non-trading, so score is from fighting/XP, not depth or shops (the sweep run's dive+shop style was seed-specific). t988 (1024x3, 236M, sweep 5772) does NOT reproduce: 4162/5285/3565 (mean 4337, -25%) -> lucky. t453 (256x4, 2.2M params) 4070/3738/3705 vs 3990 (real ~3840); t643 (128x4, 1.4M) 2406/2603/2505 vs 2532 (real). Sub-2K trials (t23, t810) dropped by user. Drone free sweep killed at 929/1200 (user).
**22:45 FINAL t973 four-seed replay:** 5659/5320/5260/6516 (mean 5689, sd 580) vs sweep 5838; depth 5.8-6.6, exp_points 1100-1410 — score tracks experience points, not depth. Drone box idle after this (no sweeps running); vast sweep ~995/1200.
**OVERNIGHT 2026-09-06 22:39 (drone box, /workspace/sweeps/nh, script nh_long.sh, log long.log, queues q2B.txt/q1B.txt, ids rt_<1B|2B>_<trial>_s<seed>, checkpoints checkpoints/nethack/rt_*):** 2B lane (GPUs 0-3): t973 s201/s202, t865 s201, t781 s201. 1B lane (GPUs 4-7, then 2B workers join when their queue empties): wave1 t973/t865/t781/t947; wave2 t453, t643, t973 s202, t973 s203 with lr halved (0.000425); wave3 assorted long sweep runs t899, t894, t742, t877, t965, t845, t672, t875. ~95K SPS each at 8-way sharing: 1B ~3 h, 2B ~6 h; all 20 runs done by ~08:00-10:00. Prior: identity-embed multi-role record 7035@1B, 2B flat; short-budget sweep winners were the worst scalers.
**LOCAL BOX overnight (22:43):** six sequential 1B seeds of t643 (128x4, 1.4M params; user wanted the ~1-1.5M class, NOT t453) in the worktree $S/wt_97416d02 (trainer built there; vendor/fast-nle symlinked; NETHACKDIR exported; script nh_1B_small.sh, log local_1B.log, results logs/nethack/rt_1B_0643_s301..306.ini). ~175K SPS at 24 threads on this 32-thread box (30/32 threads no faster) -> ~1.6 h per seed, ~10 h total. Landmine: ./build.sh nethack --cpu builds the eval runner, and building in the main tree overwrites the user's tracked `puffer` binary — build in a worktree.
**OVERNIGHT RESULTS (07:55):** 1B one seed each: t899 10578 (PB on every ledger; 1024x3 effective, 3.6 h; tempo: 3805 steps/21.6K turns, engraves 60 vs t781 348, eats 71 vs 384, exp 2314), t781 9097, t865 8887, t947 (512x5) 8337, t894 6495, t453 (2.2M) 6390, t643 (1.4M) 4574; local t643 1B seeds 4715/4657/4721/4440 (+2 pending). 2B: t781 7391 (< its 1B). Standalone headless eval (no burn-in) reads ~22% low: calibration t781 1B ckpt 6967 vs inline 9097 (x1.31), t865 7048 vs 8887 (x1.26). Dead-run checkpoints (standalone, x1.28 => inline-equivalent): t973 2B@1.44B 5212 (~6.7K), t865 2B@1.18B 5855 (~7.5K), t973 1B@524M 5352/4601 (~6.9K/5.9K), t973 2B@524M 3791 (~4.9K) => t973 is a poor scaler (~6-7K) AND leaks; t865/t781 look like they degrade past ~1B. Queued: t899 1B seeds 202/203 + 2B seed 201. Eval mode on the box: `./puffer_nethack eval <ckpt> --headless <trial args>` with NETHACKDIR exported.
**08:20 wave-3 1B:** t742 11457 (NEW PB; the "lucky" 300M trial scales best), t877 10287, t965 6189; local t643 1B s305 4555 (5 seeds 4440-4721). t973 600M gdb-probe flat at 4.30 GB through 387M (no large-allocation catch yet); t973 300M probe flat 4.29 GB at 300M.
**LOCAL t643 (128x4, 1.4M) 1B six seeds:** 4715/4657/4721/4440/4555 (mean 4618, sd 119) + seed 306 died at ~650M with no eval (see nh_1B_small.nohup for the signal). 1B nearly doubles its 300M 2500. Wave-3 1B: t845 8210, t672 8283, t875 5678. 600M t973 probe (seed 13, 600M schedule) NEVER leaked (4.30 GB flat, gdb caught nothing) -> leak needs the exact 1B-schedule trajectory; exact replay of the overnight seed-201 1B run launched with gdb (nh_leak_probe4.sh, gdb_catch_rep201.log, catch mremap/mmap>=256MB/SIGSEGV).

OVERNIGHT 09-06/07 RESULTS (drone box, q1B/q2B lanes, inline final 10K eval; id score depth): 1B: 0742 11457 (RECORD), 0899 s201/202/203 10578/10965/7493 (mean 9679, sd 1900), 0877 10287, 0781 9097, 0865 8887, 0947 8338, 0672 8283, 0845 8210, 0894 6495, 0453 6390, 0965 6189, 0875 5678, 0643 4574 (small model, poor). 2B: 0781 7391 (WORSE than its 1B 9097). DIED without a final score: t973 1B s201/s202/s203 and 2B s201/s202, 2B 0865 (the leak class; last checkpoints burn-in evaluated in eval_dead.log). t742 s202/s203 1B + t899 2B still running at 11:20 (gpu0/6/2); leak replay probe on gpu3 at 992M steps RSS 4.3 GB, not reproduced yet.
DEAD-RUN DETAIL: last ckpts t973 1B s201 524M, s202 524M, s203 999.8M (training complete, died in/before final eval), 2B t973 s201 1.44B, s202 524M, 2B 0865 1.18B. Burn-in evals of dead ckpts: t973 1B s201@524M 6555, t973 2B s201@1.44B 6625 -> t973 confirmed ~6.6K non-scaler. Burn-in re-evals reproduce inline finals within 0.5%: 0899 10535, 0781 9060, 0742 11461, 0865 8888.

2026-09-07 12:44 t742 1B SEED PANEL (drone box, inline 10K finals): s201 11457, s202 11072, s203 11247 -> mean 11259, sd ~190: the 11K result REPRODUCES; t742 = hidden 1024 x 3 layers, sweep #2 trial 0742 (args in scratchpad prof/t742_args.txt). t899 2B lane still running.

2026-09-07 12:57 t1122 PANEL LAUNCHED (user request): sweep #2 trial 1122 = NEW SWEEP TOP 6358 @210M (1024x4, lr 7.2e-4, gamma 0.99921, replay 1.78; ini copied to drone trials/sweep_1788766770910_1122.ini). Queue q1122.txt: native 209,751,856 steps seeds 201-203 (ids rt_0B_1122_s20N) + 1B seeds 201-203 (rt_1B_1122_s20N); lane nh_long.sh on gpus 0,6; nh_1122_fill.sh hands each leak-lane GPU (1,3,4,5,7) to the queue when its lane ENDs. vast sweep still running (1166 trials at 12:45).

2026-09-07 14:05: t973 1B finals from the leak lanes: s301 10488, s303 7519 (more pending) -> t973 is a scaler after all; the 6.6K figure was mid-run checkpoints. t1122 native seeds 5967/5796 (sweep 6358).

2026-09-07 14:25: RELEASE CONFIG = t742 (user: "commit the one that gets 11k consistently, default 1B"): config/nethack.ini on 5.0-nethack-release now carries t742 env/policy/train values verbatim (1024x3, lr 1.876e-3, gamma 0.999744, lambda 0.6466, replay 1.297, clip 0.1183, vf 0.1, gn 0.178, horizon 512; rewards gold 0.0338 exp 0.0602 floor 0.2256 score 0.00105 scout 0.00417 xp 1 descent 1 death -0.2907) with total_timesteps 1_000_000_000; smoke 2M OK; amended into the single release commit 850b8f1e (force-push needed). t973 1B FIVE-SEED PANEL (leak lanes): 10488, 9906, 7519, 11027, 12916 -> mean 10371, sd ~2000, NEW RECORD 12916 (s305). t742 1B mean 11259 sd 190 stays the consistent pick; t973 has the higher ceiling. t899 2B still running at 14:25.

2026-09-07 14:31 t899 2B s201 FINAL 9943 (rolling had read ~12K; 1B seeds 10578/10965/7493 mean 9679) -> 2B = 1B for t899, no gain; t781 2B 7391 vs 1B 9097 was a loss. 2B ledger: 0781 -1.7K, 0899 +0.3K, 0865/0973 died. Drone box after 14:31: t1122 lanes only (native s203 + 1B s201-203 via filler), rest idle.

2026-09-07 16:40 SWEEP: 1195 trials, workers dropped 9 -> 5 (unexplained; check the sweep driver), NEW TOP trial 1190 = 7364 @289M (1024x5, lr 2.06e-3, gamma 0.99977, replay 1.81, clip 0.226, vf 0.1, depth 4.4) = exactly the t742 pattern (high lr, gamma ~0.9998, vf 0.1). t1122 native seeds 5967/5796/4366 (mean 5376 vs sweep 6358); 1B lanes at ~400-470M.

2026-09-07 17:15 SWEEP #2 FINISHED: max_runs 1200 reached, driver exited, vast box IDLE (8 GPUs). Final top: 1190 7364 @289M (1024x5), 1122 6358 @210M, 0973 5838 @333M, 1109 5806, 1036 5793, 0988 5772, 0742 5652. All 1200 inis pulled to scratchpad const_nh/logs/nethack (1176 at the time; re-pull for the last 24). Drone box: t1122 1B lanes at 560-640M, 5 GPUs idle.

2026-09-07 17:20 t1122 1B: s201 13255 (NEW RECORD), s202 12401, s203 in final eval -> t1122 (1024x4, lr 7.2e-4, gamma 0.99921, replay 1.78, clip 0.325, vf 0.40) scales BEST of all configs (t742 mean 11259, t973 mean 10371). Native repro was 5967/5796/4366. The low-LR "fast starter" hypothesis is refuted for 1122: it is both the sweep top and the 1B top.

2026-09-07 17:25 t1122 1B THREE SEEDS: 13255 / 12401 / 13216 -> mean 12957, sd ~480: best config at 1B by ~1.7K over t742 and consistent. SWEEP GOTCHA: ./puffer sweep refuses to start if a config value lies outside its [sweep.*] range ("Default sweep value outside its sweep range: env.alpha_vel") -- the shipped drone config has alpha_vel = alpha_action = 0.0, which a log_normal range cannot contain; set base values inside the ranges (0.003) before sweeping.

2026-09-08 overnight (drone box, q_night.txt via nh_night.sh): t1190 ("7k config", sweep #2 top native 7364, 1024x5 lr 2.06e-3 gamma 0.99977 vf 0.1 mb 8192) at 1B = 13117 / 11156 / 12448 (mean 12240, seeds 201-203) — second to t1122 (12957), within seed noise; seeds 204-205 + 1122 2B x3 + 1109/1036/0988/1193/1084/1045 1B queued. Vast box gone; sweep #2 inis live in /puffertank/constellation_nethack/data/nethack_sweep2_inis.tar.gz.
2026-09-08 ~04:00: t1109 (512x7, lr 7.05e-4, gamma 0.99972, lambda 0.70, vf 0.10, replay 2.08; native 5806) s201 1B = 13935 — NEW single-seed RECORD (prev 13255 t1122 s201); seeds 202/203 queued in q_night.txt. Narrow-deep net, first such leader.
2026-09-08 ~07:00: t1122 2B s201 = 16042 — NEW RECORD by 2.1K over any 1B run (t1122 1B mean 12957); 2B scaling WORKS for 1122 (t899/t781 2B were flat/worse). 2B seeds 202/203 queued. Next lever: 4B of t1122, and t1109 2B once its 1B seeds confirm.
2026-09-08 09:00 t1122 2B s201 standalone cert (puffer_cert, burnin 4000 + 10K, eval_agents 512): mean 16200 (inline 16042), MEDIAN 9990, p10 986, p90 38838, max 230415 (t742 1B cert: mean 11310 / median 7496). Cert invocation gotcha: `./puffer_cert eval --headless --base.load_model_path=... --base.eval_episodes=10000 --base.eval_agents=512 --base.burnin_games=4000 --policy.hidden_size=1024 --policy.num_layers=4` with `burnin_games = 0` temporarily under [base] in config/default.ini; without --headless it opens the terminal renderer; positional key=value args are rejected. Dump lines now carry killer name + 3 trailing ints (analyze.py parser patched).
2026-09-08 ~13:00: t1122 2B s202 = 16987 (NEW RECORD); 2B two seeds 16042/16987 mean 16515 — 2B gain over 1B (12957) is +3.5K and consistent. t1084 1B 7442, t1193 8639, t1036 10556, t0988 10897 all out. 1122 2B s203 queued.

2026-09-08 20:2x 2B s203 LANDED 17,077 -> 1122 2B three seeds 16,042 / 16,987 / 17,077, mean 16,702 (sd 560); 1122 1B five seeds mean 13,220; 2B gain +3,480 is 3-seed robust. Arms still running: oracle s301/s302, GELU s301/s302, SiLU s301 (results in /workspace/sweeps/nh/long.log).

2026-09-08 22:57 4B BATCH LAUNCHED (user call): rt_4B_1122_s201..s208, one lane per GPU on the drone box (script /workspace/sweeps/nh_4B.sh, timeout 100000 s, ids in long.log), 1122 recipe --train.total_timesteps=4000000000 (total_timesteps is a long, 4e9 is safe), ~108K SPS each at start -> ~10-12 h + 10K-episode final eval, expected ~10:00-11:00 09-09. rss_guard (120 GB) running; box 503 GB RAM / 104 GB disk free. Baselines: 2B three seeds mean 16,702; 1B seven seeds mean 13,094. Oracle arm cancelled+removed the same evening; GELU/SiLU null.

2026-09-09 10:29: user call: killed 4B lanes s205-s208 by PID (GPUs 4-7 to drone); s201-s204 continue (started 22:47 09-08, ~18.5 h expected, land ~17:00 UTC 09-09).
2026-09-09 15:55 4B (t1122, 4 surviving seeds s201-s204, GPUs 0-3): s202 FINAL 17,749 (rc=0); s201 4.0B rolling 19.4K, s204 4.0B rolling 18.8K (final evals running), s203 3.9B rolling 13.3K (~30 min behind); SPS 71-115K, 17 h uptime. 2B 3-seed mean was 16,702; per-lane finals land in /workspace/sweeps/nh/long.log.
2026-09-09 15:56 4B s204 FINAL 18,883.
2026-09-09 16:14 4B s201 FINAL 18,597 (eval 10 min). Three 4B finals so far: 17,749 / 18,883 / 18,597 (mean 18,410) vs 2B 3-seed mean 16,702 (+10%); s203 pending (~16:45).
2026-09-09 16:38 4B PANEL COMPLETE (t1122 recipe, seeds 201-204): 18,597 / 17,749 / 18,883 / 17,391 = mean 18,155 sd 700, every seed above the best 2B seed (17,077); 2B 3-seed mean 16,702 -> +8.7% for 2x budget; 1B 5-seed mean 13,220 -> 2B +26%, 4B +9% (diminishing but still scaling). All 4B lanes done; GPUs 0-7 free on the drone box.
