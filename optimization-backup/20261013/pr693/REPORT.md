# PR 693 ("workspace fix", per-stream cuBLAS workspace) — stability check for upstream merge, 13 October 2026

PR: FinlaySanders/PufferLib branch `cublas` @ 3719caaa (2 commits: 1cb95a8a "cublas fix", 3719caaa "small cleanup"), base PufferAI/PufferLib `5.0` @ 6ffa5b10
(unchanged since; mergeable clean). Diff: src/algo.cu (+/-), src/pufferl.cu (+7/-1), tests/profile_kernels.cu (3 call sites); 49+/26-.
What it does: replaces two thread_local cuBLAS handles (32 MB workspace each, cublasSetStream per GEMM) with a per-thread table of (stream, handle,
4 MB workspace) registered once per stream (cublas_init_stream), looked up by stream at each GEMM. Fixes the workspace-sharing race between
concurrent streams (cublasSetStream resets the workspace) that produced the cudaGraphLaunch assertion under multi-buffer rollout.

## Method
Clean worktrees of the PR head (/puffertank/pr693) and its base (/puffertank/pr693-base), built with the repo's own build.sh (vendor/fast-nle cloned and
built by build.sh: engine e7f6568), binaries puffer_nethack and puffer_breakout each. No experiment-stack code. Tests run back to back on the idle 4090.

## Results
(filled in as the chain completes — scratchpad pr693/results.txt is the raw ledger)

## Code review of the change (read, not run)
Correct by construction for every GEMM path in the tree: all puf_mm / puf_mm_tn / puf_mm_nn call sites (algo.cu, nmmo3, craftax, osrs) pass the
rollout or train stream they run on; the only other stream is g_dw_stream, registered alongside stream 0 in cublas_init_handle; the main thread also
registers train_stream (create_pufferl) and, for GPU-backend envs, streams[0]; each CPU rollout worker thread registers its own stream in its own
thread_local table before any capture. Handle lookup asserts on an unregistered stream, and the build keeps asserts on (no -DNDEBUG), so a missed stream
fails loudly rather than silently. cublasSetStream precedes cublasSetWorkspace (SetStream resets the workspace), which is the bug the PR fixes.
Trainer lifetimes: eval / bot-ladder / selfplay-pool trainers are created only after close_pufferl(pufferl) and one at a time, so resetting the main
thread's table in cublas_init_handle never orphans a live trainer's streams. Sweep trials are forked children with their own tables.
Pre-existing, not regressions: (a) handles and workspaces are never destroyed, so each create_pufferl on a thread leaks its predecessors' (base leaked
2 x 32 MB per re-init, the PR 3-4 x 4 MB plus handle state — smaller); (b) g_dw_stream and its events are recreated per cublas_init_handle; (c)
tests/profile_kernels.cu does not compile on base either (100 unrelated errors).
Notes for the maintainer: CUBLAS_MAX_STREAMS = 8 is ample for current paths (main thread ≤ 4, workers 1 each) but is a hard assert if a future path
registers more; the 4 MB workspace equals cuBLAS's own default on pre-Hopper parts (bit-identical gate here on Ada) but is below the 32 MB cuBLAS
recommends on Hopper, where it may change algorithm choice and speed for large GEMMs — consider 32 MB on sm_90+.

## Results (13 Oct, clean worktrees, idle 4090; raw ledgers: scratchpad pr693/{results,matrix,matrix2,nethack_det}.txt)
### NetHack determinism and speed (the PR's claim) — 5M steps, seed 73, two runs per tree, final-checkpoint sha256
| config | base deterministic | PR deterministic | PR = base | SPS base → PR |
|---|---|---|---|---|
| shipped: horizon 512, 4 buffers, async | NO (47d6c9e55b8bf786 / f9103a1389ba5196; scores 42.5 / 66.5) | yes (d8b8187a790c67c8 x2, score 49.370) | n/a | 114K → 178K (+56%) |
| horizon 512, 4 buffers, async off | NO (7680f29cac2a40bf / 15687274bbc7f0a5) | yes (d420156dd7d90235 x2) | n/a | 88K → 124K (+41%) |
| horizon 512, 1 buffer, async | yes | yes | IDENTICAL (0c28ad9c32e7bf52) | 163K → 163K |
| horizon 128, 4 buffers, async | yes | yes | IDENTICAL (c655deabe0ddc266) | 176K → 176K |
| gate: 2M steps, seed 42, async off, 1 buffer | yes | yes | IDENTICAL (b77d4f402f2a8ec6) | 23 s → 21 s |
Reading: upstream is nondeterministic whenever several rollout streams coexist (4 buffers) and the GEMMs are large (horizon 512), regardless of async;
the PR is deterministic in every configuration and bit-identical to upstream wherever upstream is deterministic. The same shared-workspace path also
serialised the multi-stream rollout: +56% training SPS at the shipped config, unchanged elsewhere. This corrects the 7 Sept note that attributed the
shipped config's irreproducibility to a pipeline scheduling race.
Pre-existing (both trees): at the shipped config the inline eval after training creates a second ~15 GB trainer without freeing the first and OOMs on a
24 GB card (alloc_create: cudaMalloc failed); eval_episodes=0 or a small eval_agents avoids it. Checkpoints are written before the eval.
### Other environments — default ini, seed 73, two runs per tree (10M steps) and one long run per tree
10M x2: breakout, breakout (GPU backend), pong, squared, tetris, connect4, drone, cartpole: deterministic on both trees and IDENTICAL across trees.
snake and asteroids: nondeterministic on BOTH trees at 10M (2-buffer async; see env pass below for whether the PR changes this at longer budgets).
Long: breakout 300M 61da9aac0ce2d5b8 both (score 776.247 both; 14.8M vs 15.0M SPS); breakout GPU backend 300M 6fb0445bfd7b6c8c both (786.911; 42.5M vs 42.2M);
pong 50M identical (20.995; 7.6M SPS both).

## Not run (stopped 13 Oct 22:30 to return the box to the NetHack speed program; verdict unaffected)
Long-budget pass for snake/squared/tetris/connect4/drone/cartpole/asteroids (10M x2 per tree done; long runs only for breakout/breakout_cu/pong);
GPU co-tenancy stress; the 32 MB-workspace hash comparison (worktree /puffertank/pr693-ws32 is built-ready: run scratchpad pr693/ws32.sh);
the 20M shipped-config speed pair (5M pair: 114K → 178K).
## Verdict
Good to merge. Deterministic at the shipped NetHack config where upstream is not; bit-identical to upstream wherever upstream is deterministic;
+56% SPS at horizon 512 x 4 buffers; no new defects. PR text should state the mechanism and the speedup; maintainer note on the Hopper workspace size.
