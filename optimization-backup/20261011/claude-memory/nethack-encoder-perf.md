---
name: nethack-encoder-perf
description: "NetHack encoder speedup state (2026-07-07) — table-fused patch encoder shipped, SPS 328K; kernel lessons (divergent relu bwd, ld16 gram, failed scatter redesigns)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 87694700-8c87-49fd-b419-5c3a6ff36277
---

2026-07-07 session (uncommitted on `nethack` branch): built the **table-fused patch encoder** — NETHACK_ENCODER=patch now decisively fastest. RTX 4090, 2M-step captures via profile_nethack.sh:

| | conv (7/7 am baseline) | conv now | patch now |
|---|---|---|---|
| SPS | 266K | 275K | **328K** |
| Train ms/epoch | 637 | 604 | **498** |
| encoder ms/epoch | 259 | 227 | **127** |
| optimizer | 59 | 59 | 59 (was 113 pre-gram-fix) |

What shipped (src/ocean.cu, kernels.cu, muon.cu; all gradchecked via tests/test_nethack_{encoder,mixer}.py):
- Patch/mixer stem fused embed+stem via glyph table T (5977x576=6.9MB L2-resident, same trick as conv's glyph_T): `nhm_stem_table_kernel` fwd 127µs; killed gather(203µs)+stem GEMM+two 115MB gath buffers. Backward via `nhm_dT_scatter_kernel` (9 taps, 307µs vs conv's 25-tap 852µs) which also applies the stem relu mask on the fly AND accumulates stem bias grad (masked grad never written back).
- `nh_relu_bias_bwd_kernel` fuses relu-backward + bias-grad, one atomic per thread via fixed-column trick ((grid*block)%dim==0 → nh_colsum_grid); used by conv + patch + mixer for proj/bl/conv1 biases. `nh_bias_flush_kernel` casts the packed fp32 accumulators once.
- NHM_CONCAT padded 3245→3248 (**breaks old patch/mixer checkpoints**, proj_w now Hx3248): odd row width pushed proj GEMMs off tensor cores.
- proj wgrad → puf_mm_tn_splitk (both conv+patch); generalized `cublasLtGemmDense` in kernels.cu (Lt heuristic + 64MB ws); muon NS GEMMs use it.
- `muon_gram_small` in muon.cu for tall gram with C<=16 (glyph embed d=16): 103µs→~15µs, 5 NS calls/param/iter. At C=32 cublas wins (27.7 vs 13µs) — condition is `tall && M <= 16`.

Hard-won kernel lessons:
- **Divergent store-vs-load branch** in relu-backward-style kernels (`if (out<=0) grad[i]=0; else acc+=grad[i]`) runs ~3x slower (419µs vs 140) on real ~50%-masked data; synthetic benches with 0% masking hide it completely. Fix: branch-free select + unconditional store.
- **cublas is pathological for ld=16 tall-skinny grams** (X^T@X, X=(5977,16)): 103µs vs 7µs, ALL of GemmEx/Lt-heuristic pick the same bad kernel; alignment/graphs/compute-type are NOT the cause (all tested). Diagnostic: grid 1x1xZ with a 128x64 tile ⇒ output ≤128x64 — that's how the shape was identified as embed-gram, not proj-gram.
- **dT scatter redesigns that FAILED** (both slower than the shipped smem-atomic design at 852µs): (a) warp-owns-taps + plain smem read-add-write → ld/st same-address latency chain, 2072µs; (b) warp-per-tap + register accumulators w/ uniform slot branch → 1166µs even at 100% hot. The old design's smem atomics are pipelined fire-and-forget; don't "fix" them.
- Kernels measure ~equal in-graph vs standalone; nsys --cuda-graph-trace=node does not distort kernel times (verified vs no-nsys dashboard).

Tools: standalone encoder bench (builds real ocean.cu, skewed glyphs, B=8192) at scratchpad bench_nethack.cu — session-tied dir, copy into tests/ if wanted. bench_gram2.cu reproduces the ld16 gram pathology.

Next levers (train phase, patch): mingru 232ms/epoch = 46% of train is THE bottleneck now; copy/cast 68ms (select_copy 504µs/iter replay-buffer gather at ~50GB/s, scattered-row-bound); encoder residue: nhm_concat 111µs + slice 120µs/iter avoidable by writing stem output directly into concat slice (needs separate g_concat buffer since backward relu mask reads forward concat); stem_table 127µs is L2-bound floor. Score A/B RESOLVED: patch +200 over conv, SOTA depth 5.73 — see [[nethack-mixer-encoder]].

LATE-RUN DYNAMICS (why encoder speedups fade over a run): early captures are ~random policy (episode len ~95, env c_step 221-250ms/epoch, TRAIN-bound 2:1). By epoch ~988 of the SOTA run: episode len 591, depth 5.7, env 693ms = 56% of wall vs Train 492ms → EVALUATE-bound. Env step cost grows ~3x as policies improve (more map explored, more entities, vision/pathing on deeper levels; profile_nethack.sh's env mode already warns trained policies step slower). Train-phase costs are constant per epoch, so encoder wins dilute late. Late-run SPS lever = env-side ([[nethack-env-speed-campaign]] hot/cold split, per-buffer OMP workers) or rollout/train overlap — benchmark env work against TRAINED checkpoints, not random policy.

## 2026-07-13: inventory unified-16 (NH_INV_HID 32->16) — the big encoder win
Profiling (artifact 2e0ce400) showed the inventory branch = 17.5% of GPU (enc/inv 8.2 + encB/inv 9.3), biggest single component after data-movement. Root cause: pooled max ran through the 32-dim decoder keys (2x the patch encoder's 16-dim bottleneck). Fix: NH_INV_HID 32->16 — one 16-dim per-slot rep now doubles as BOTH the pool bottleneck AND the decoder pointer key (patch-encoder style, unified). Cascades cleanly (all shapes symbolic in NH_INV_HID: inv1_w 16x32, inv1s_w 16x17=272, inv2_w 128x16, dec k_w 16x16, NH_QDIM 80, NH_INV_FLAT 880 — all mult-of-8; smem/loops auto-shrink). Gradcheck PASS (inv1_w added to fd_skip — feeds max-pool, FD-noisy at 16-dim ties, torch-exact 1.2e-6). ORACLE 71f23e53889c6a3f x2 (supersedes f74af441). Demo DEMO_INV_HID 16.
MEASURED (nsys median ns, 32->16): inv_max 15840->8224 (1.9x), inv_gather 8288->4448 (1.9x), inv_table 10848->3712 (2.9x), dec ptr3_cos 9504->3520 (2.7x), dec rownorm 2688->1568 (1.7x). Backward inv_max_bwd (OLD 4.4ms/inst, the single biggest kernel) INFERRED ~2x (identical 16-dim halving: half atomics + half smem->2x occupancy) — nsys DROPS backward events on the fast 16-dim run (buffer saturates during rollout before the train backward; slower 32-dim run captured it fine; use ncu --kernel-name for exact). Est branch: inv 17.5%->~10%, decoder 7.3%->~4%.
- SFEAT NOW BIGGEST FORWARD INV KERNEL (9.6k, UNCHANGED — 17 feats regardless of NH_INV_HID). v2 win = fuse nh_inv_sfeat into the gather (inline from obs bytes, recompute in backward), ~another 5-9k. Not done yet.
- PROFILING GOTCHA: nsys -t cuda drops kernel events when the GPU outruns its flush (fast runs lose the backward/training-phase kernels). Slower builds capture everything. Use ncu for a specific hot kernel, or the median-per-instance from a capture that got it.
- GEMM/backward attribution needs fine NVTX (temporary, NH_NVTX-gated, reverted). Method + the flamegraph build scripts in scratchpad (build_report.py/assemble.py/analyze_prof.py).
- 200M VALIDATION: unified-16 holds score — train 1879.9/depth 1.094 (carried-state farm) vs 32-dim's ~1823 at the same 200M point. 16-dim keys do NOT hurt quality. SPS cold ~300-355K (early readings, >= 32-dim 309K), drifts to ~150K over the sustained run = 4090 thermal throttle (GPU idle/clean after), NOT a regression — smaller kernel-faster model can't be slower on-GPU. Inv-2x confirmed by profile; branch ~17% of GPU so SPS uplift is ~10%, masked by thermals. Weights bin = u16 200M ckpt.
