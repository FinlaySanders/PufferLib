---
name: nethack-env-speed-campaign
description: "Env-side CPU optimization campaign 2026-07-07: trajectory-hash methodology, memset skip, LTO, tty/inventory gates shipped; hot/cold split is the open front; tinybox sweep topology fixes"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5d4abbbc-50c6-4248-8a99-94fb927393d2
---

Goal: maximize NetHack env SPS under massive vectorization, PRESERVING all game behavior
(user constraint — rules out pettype:none, game-logic pruning, reimplementation).

**Verification methodology (use for every vendor change):** scratchpad `nethack_bench.c` —
single-thread multi-env stepper; `nethack_bench <envs> <steps> hash` FNV-hashes every step's
obs+reward+terminal with deterministic seeds (`env->rng = i`, action stream srand(42)).
Baseline hash `0605958790010d05` (16 envs × 3200 steps) — must match after every change.
Build via README clang cmd + `-I ocean/nethack`. Bench also reports avg reset ms (terminal
steps timed separately). perf blocked in container (paranoid=4, even root); gprofng display
segfaults; use valgrind callgrind/cachegrind (Ir deterministic; NOT comparable across the
LTO boundary — LTO changed Ir +7% at flat wall-clock).

**CRITICAL scaling fact (measured 2026-07-07): the box is memory-bandwidth-bound, not
core-bound.** Pinned parallel bench procs (341 envs each): 1 proc 171K SPS, 4 procs (distinct
P-cores) 4×110K=441K, 24 procs 24×28.7K=690K — flat aggregate ceiling ~0.7M env-only SPS,
per-proc rate UNIFORM across P/E cores (= shared-resource limit, not compute). Naive
cores×single-thread (≈4M) is wrong. Consistent with training rollout's ~470K env phase.
Confirming experiment: SAME 24 procs with 64 envs each (1536 total) = 1.37M agg (57K/proc)
vs 341 envs each (8184 total) = 0.69M — halving working set doubled the box. Tinybox EPYC
(8ch DDR4 ~200GB/s, 256MB L3 in 16MB/CCX islands) is structurally ~5-7× better shaped for
the thousands-of-envs regime than the 14900K (2ch, 36MB monolithic).
Consequence: per-step TOUCHED BYTES is the currency that raises whole-box SPS — hot/cold
split, chain slot reuse, viz/gbuf layout directly lift the ceiling; instruction-level wins
(PGO, inlines) mostly help below saturation. 1M env-only/box needs ~1.5× bandwidth
efficiency. Full-training 1M additionally needs rollout/train overlap (phases are
sequential: Env 45%/Train 51% at 212K SPS, N=8192) + train-side kernel work (417K
samples/s on a 676K-param model = launch-bound).

**Measured landscape (14900K, single thread):** 1 env 5.0µs/step (~200K SPS), 64 envs
5.8µs, 512 envs 6.7µs — the 35% inflation is cache working-set tax, THE remaining target
(task: hot/cold split of nle_ctx_t + level data; cachegrind cg512.out/cg1.out ground it).
Steady-state profile post-gates is ~pure game logic: mfndpos 6.5%, can_reach_location 6.3%,
vision_recalc 5.4%, isok 4.4% (still not inlined by LTO — candidate: static inline in
header), m_move, dog_move, onscary, is_moat/is_pool/is_lava ~6%. Reset = 0.13ms avg
measured → snapshot-reset idea CANCELLED (saves noise; earlier ~2ms assumption was wrong).

**Shipped in vendor/nle (all trajectory-hash-verified bit-identical, training smoke clean):**
1. alloc.c `nle_arena_calloc` skips memset for chunks above `s_arena_hwm` (new nle_ctx_t
   field, updated in alloc(), preserved across fast-reset restore; util builds keep plain
   memset via #ifdef NLE_USE_ARENA_FREE). -8.6% Ir on fresh-env workload.
2. LTO: cmake needs `-DCMAKE_POLICY_DEFAULT_CMP0069=NEW -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON`
   (without the policy default it silently applies only to helper libs — check
   `src/.../nethack.dir/flags.make` for -flto). Gain ~1-3% (hot loops are cache-bound;
   is_pool etc. called via fn pointers). Surfaced real decl mismatches: fopen_datafile,
   nle_yield (-Wlto-type-mismatch) — worth fixing.
3. tty emission gate: `nle_ctx_t.tty_emit` precomputed at nle_start (tty obs bound OR
   ttyrec — fixes exp_039's silent ttyrec break); nle_putchar/nle_xputs check it;
   `ttyDisplay->nle_emit` mirrors it (set in wintty.c tty_startup via
   nle_wants_tty_output()), gates xputc/xputs in termcap.c. CRITICAL: tty STATE updates
   (curx/cury, more() pacing) must keep running — only byte emission is skipped.
4. winrl.cc update_inventory_method: skips doname/let_to_name string builds when no inv_*
   obs bound, but KEEPS obj_to_glyph(otmp, rn2_on_display_rng) calls — display-RNG stream
   must stay byte-identical (hallucination draws). inventory_ consumed only by fill_obs.

**Sweep topology fixes (pufferlib, shipped):** sweep children get `cpu_affinity` core
blocks (exp_args, applied via sched_setaffinity in _train + torch.set_num_threads);
num_threads = max(1, //concurrent); num_buffers clamped to num_threads (vecenv floors
workers/buffer at 1 → silent single-threading; warning added in vecenv.h). Root cause of
tinybox 6×4090 sweeps at 70K SPS/run: 32//6=5 threads vs num_buffers=6 → 1 worker/buffer,
plus 6 unpinned torch pools. Perf validation pending on tinybox.

**Round 2 shipped (all hash-verified, cumulative 1-env 200.6→232.3K SPS +16%, 512-env
148.6→171.5K +15%, train smoke 161.5→174.2K):**
5. isok+dist2 static inline in extern.h (K&R defs removed from cmd.c/hacklib.c) — biggest
   single win, +6-8%. LTO had NOT inlined them.
6. is_pool/is_lava/is_pool_or_lava/is_ice/is_moat static inline at hack.h tail, guarded
   `#ifdef NLE_H` w/ extern fallback (decl.c, drawing.c, lev_main.c include hack.h before
   nle.h → levl macro's current_nle_ctx unresolved there; `E` macro is #undef'd by then —
   use plain extern). +1-2%.
7. winrl.cc dirty-row fill_obs: `dirty_rows_` 21-bit mask set in store_glyph/
   store_mapped_glyph/clear/load_mirror; fill_obs copies only dirty rows (obs rows persist
   between fills); baseline branch + reveal_map overlay force all-dirty. fill_obs was 42%
   of all D1 write misses. +5% at 512 envs (scale-specific, 1-env unchanged).

Cachegrind ground truth (matched 400K-step workloads): LLd misses 143K (16 envs) → 19.3M
(512 envs) — the 35% tax fully explained by LL+D1+TLB. CAUTION: valgrind's ~128GB client
space dies at env #253 with 512MB arenas — profile 512 envs with
NLE_PER_ENV_ARENA_BYTES=67108864 (sentinel exits 0 on that abort, masking it!).
Remaining DLmr targets at 512 envs: inv_weight 11.6% (invent chain walk/step), dog_move
7.1%, vision_recalc 6.6%+21.9% DLmw (viz array rebuild), mfndpos 4.9%,
deepest_lev_reached 4.8% (recomputed per botl!), nh_timeout 4.5%, weight_cap 3.8%.
**Slot-reuse allocator SHIPPED (alloc.c): 16B size header per per-env chunk, 128
exact-size bins ≤2KB on ctx (snapshot-coherent), NLE_ARENA_REUSE=0 kill switch. Two-stage
hash gate passed: headers-only (+16B addr shift) AND reuse both = golden hash → game is
address-independent, no UAF unmasked. Mechanism verified: 11KB→5KB arena growth per level
transition. BUT zero SPS delta on random-policy bench (shallow episodes barely scatter) —
payoff expected only on deep trained episodes; verify via trained-checkpoint replay later.
Also measured: resumes/action = 1.030 (98.3% exactly 1) — run-to-decision engine
refactors (other-agent proposal) are near-worthless for this wrapper.**
Next: map SoA (typ plane via spatch levl[E1][E2].typ), hot/cold ctx split, viz_array/gbuf
narrowing, deepest_lev_reached cache, kernel ~5% (mapping reuse).

Env obs binding (ocean/nethack nethack_bind_obs): glyphs, blstats, chars, message, misc,
internal ONLY — tty_*/inv_*/colors/specials/screen_descriptions NULL, which is what the
gates key on. Related: [[nethack-crash-hardening]] (same uncommitted vendor repo — commit
both together), [[nethack-training-profile]].

2026-08-02 SPEED ROADMAP REVISION (user challenge, correct): quiescent-turn
batching upside is CAPPED — background monster simulation IS farming income
(spawn->path->arrive = the paycheck); awake monsters must be fully
simulated, sleeping ones are already cheap early-outs whose wake checks
consume RNG. Invariance-preserving savings = vision-recalc-when-static +
timers/bookkeeping only (~1.2-1.5x, NOT 3-5x). Any bigger gain =
approximation that distorts spawn/approach dynamics = touches exactly what
farming depends on. => Tier 0 per-function turn profile under farming load
is MANDATORY before any engine bet. Also key accounting (macro-removal
debate): price speed in GAME TURNS not steps — champion 61M turns/min vs
nomacro 18M (macros amortize fill+forward over ~20 turns; 10K-step episode
cap also 7x richer under macros). Wall-clock-to-score levers = async sweep
+ H2D delta + hot-loop micro-opt; NOT action removal, NOT aggressive
batching.
