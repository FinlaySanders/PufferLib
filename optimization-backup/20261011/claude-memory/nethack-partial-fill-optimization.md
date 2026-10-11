---
name: nethack-partial-fill-optimization
description: fast-nle partial-fill obs export (028a6a6cc) — fill_obs was 33% of engine Ir (21 fills/step); opt-in partial + nle_obs_refresh; +12% train SPS; new bench baseline 5e7d1fc73eabda61
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-07-21T16:34:08.762Z
---

2026-07-21 fast-nle commit 028a6a6cc (LOCAL, not yet pushed): **partial-fill obs export**.
PROFILE FINDING (callgrind 16env x 6000 steps, init-amortized): fill_obs = 33.7% of ALL
engine Ir — it runs at EVERY input yield (~21 fills/env-step under the 22-verb env's
multi-key steps: prompt ESC chains, item letters, menu answers, Elbereth ~12 keys) but the
env only reads misc/message between keys. nle_objects called 39M times (~20/fill =
inv_state build), deepest_lev_reached 1/fill (2.2%).

FIX: (1) nle_obs.partial (char, appended to struct end, default 0 = opt-in per fork
CLAUDE.md "no hash changes without opt-in flag"): in-game fills export only
prog_state/misc/message; skips internal/glyph-dirty-copy/underfoot/blstats/inv_*
/screen_desc; dirty_rows_/last_*_buf_ accumulation untouched. Honored only when
`in_moveloop && !gameover` so boot/death fills stay byte-identical (death obs zeroing
semantics preserved). (2) nle_obs_refresh(nle,obs) API (nle.c, mirrors nle_step's TLS
dance minus the jump) -> NetHackRL::rl_fill_obs_direct (rl_bot_direct pattern) = one full
fill at the step boundary without stepping. ENV (pufferlib nethack.h, in the "more verbs"
commit's follow-up — NOT yet committed pufferlib-side): obs.partial=1 in bind_obs;
nle_obs_refresh at c_step tail (after handle_prompts, before TIME/reward reads, guarded
`stepped && !done`) + reset tail (before prev_* seeds which read blstats).

MID-STEP STALENESS AUDIT (why it's semantically safe): item prompts answer with
inv_letters from the STEP-START fill = the inventory the policy acted on; letters stable
across atomic-WEAR takeoff; handle_prompts/answer_menu/parse_candidates read misc+message
(always filled); death fills bypass partial (gameover guard) so killer internal[9]/[10] +
zeroed-blstats semantics intact.

RESULTS: random-policy bench 1env 109K->185K (+70%), 16env 124K->138K (+11%), 512env flat
(~102K, that regime = fresh-episode + memory-bandwidth-bound); reset_bench step 8.1->6.9us;
TRAINING smoke 374K->419K SPS (+12%, same box/config/phase). GATES ALL GREEN: 34/34 goldens
x {sequential, interleaved, thread-shuffled}, no-globals strict, clang-format-12'd,
**env-level bench hash 5e7d1fc73eabda61 bit-identical with opt-in active** (= NEW bench
baseline for the 22-verb env; old 9f4a3c413981143a was the 14-verb env, obsolete).

GOTCHAS RE-LEARNED: (a) STALE REPLAY BINARY — appending a field to nle_obs makes any
replay_golden binary compiled against the OLD header read garbage `partial` (1-byte
overread) -> all 34 goldens "fail" with a CONSTANT init hash (27427df4...); ALWAYS
recompile build/replay_golden after nletypes.h changes (same lesson as "rebuild replayer
after settings struct change"). (b) callgrind toggle-collect=c_step collects 0 (fcontext
stack switches break it) — profile plain. (c) 16-env fresh-init profile is DOMINATED by
nle_start (option parsing 48% incl!) — an artifact; per-episode reset measured 0.15ms =
~18 steps = NEGLIGIBLE (re-confirms old snapshot-reset cancellation; don't chase option
caching). (d) random bench turn_advance 1.3% at 16env but 26% at 512x200 (fresh eps) —
workload mix is scale-dependent.

MEASURED STEP-PATH PROFILE POST-FIX targets (next levers, trained-workload verify needed):
strstr 2.4% (env-side msg_contains chains), nethack_pack_obs 2.3% (env mask fill),
mfndpos 1.8%, memset 1.8%, dog_move, flush_screen/putsyms tty-state ~4%, printf-family ~4%
(pline formatting), deepest_lev_reached now 1/step (was 21x). Bench/probe compile line +
methodology: see [[nethack-fast-nle-migration]] (clang cmd), fnle_bench.c/reset_bench.c in
scratchpad (14-head action stream, seed=i, srand-LCG 42).

PUSH STATE: fast-nle main local 028a6a6cc + edf8885f3 ahead of origin — push from VS Code
terminal (tmux askpass gotcha, see [[git-push-credentials]]). Pufferlib env-side
partial/refresh edits UNCOMMITTED (needs the new engine symbol — commit together with a
fast-nle bump/push, else other boxes fail to link nle_obs_refresh).

2026-07-21 5x CAMPAIGN KICKOFF — VERIFICATION FOUNDATION (user: "5x needs a clearer
verification strategy incl. easily running stock NLE"): STOCK-DIFF HARNESS SHIPPED
(edf8885f3, tools/stock_diff.sh): one command records fresh goldens from a PINNED stock
build at any seeds + replays vs current fork, first-divergent-step. Stock setup on
pufferbox3 (scratchpad/stock-nle, EPHEMERAL — recreate per header comment): git worktree
@2319f298 + tools/stock_record.patch + `CC=clang CXX=clang++ uv pip install -e .` +
faketime.so shim; STOCK_NLE_DIR env var points to it. EMPIRICAL: gcc-built stock DIVERGES
from clang-stock per-seed (3/4 seeds failed incl. init hash; seed 4245 even dies t102 clang
vs survives t332 gcc) — clang is mandatory, exactly why DETERMINISM.md pins it. Fresh
clang recordings (seeds 4242-4245, 7777-7778) all replay identically vs the
partial-fill-modified fork.
5x PATH (assessed, measured bases): (1) whole-box bandwidth 1.5-2x (hot/cold ctx split,
map SoA, viz narrowing — halving working set doubled the box), (2) per-step instr 1.3-1.5x
(can_reach memoize/gettrack bbox 1.8x-late-game prior art, vision incremental, tty/pline
trim), (3) env-layer 1.05-1.1x (strstr chains, mask fill), (4) rollout/train overlap
1.5-1.9x (phases sequential Env45/Train51), (5) reserve: no-op-step auto-advance ~2x but
CHANGES SEMANTICS (opt-in only). Compounded 3.5-5x plausible; fronts 1-2 are the invasive
surgeries the harness exists for. VERIFICATION GAPS CLOSED (2026-07-21 later): (1) FUZZ CORPUS: 78 recordings, all roles x
seed bases 5000/6100/7300 x 2500 steps, in scratchpad/fuzz_goldens (EPHEMERAL — regen via
fuzz_record.sh pattern; recording ~5min). (2) --actions-file in record_goldens.py
(committed 6d78fbe02): ground-truth ANY keycode stream through stock. (3) trained-oracle:
DEFERRED — demo net is stale for 22-verb arch; pragmatic proxy = --actions-file with an
env-recorded keystroke dump (instrument obs.action logging when needed). AutoAscend fresh
recordings deferred (needs clone; 3 aa_* goldens already in fixed corpus).
SURGERY LOG: (A) can_reach_location memo + gettrack skip-ahead ALREADY IN FORK (prior-art
ported earlier — creach_core + windowed seen; don't redo). (B) 6d78fbe02: rl_print_glyph
skips tty_print_glyph per map cell when !ttyDisplay->nle_emit (tty mirror state churn with
no consumer; obs come from store_* arrays). Gated: 34x3 + 78/78 fuzz + no-globals + bench
hash 5e7d1fc73eabda61 unchanged. SPS ~flat on random bench AND training smoke (418.3K vs 419K — the
tty-skip is Ir-real but wall-clock-neutral here; training SPS is train-phase+bandwidth
bound at ~419K, per the campaign's own finding "env phase no longer the training
bottleneck"). LESSON: further ENGINE instruction cuts won't move TRAINING SPS on this box
— the training-SPS levers are front-4 (rollout/train overlap, pufferlib vecenv/cuda side,
up to 1.9x) and front-1 (touched-bytes for the multithread ceiling).
FRONT-1 ROUND 1 SHIPPED (commit 5 on fork, after 6d78fbe02): mmap'd nh_ctx (was calloc —
heap reuse after free returns the chunk DIRTY -> full-struct memset write-storm per reset
= 60% of LL wr misses at 341envs; fix in tools/gen_ctx.py emitter + regen, sys/mman.h
must precede hack.h or accessor macros mangle libc protos) + lazy TMT vterminal (was
built+cleared per reset = ~22% wr misses; nle_write's tty-obs gate meant it NEVER got
bytes in RL configs; lazy at init/tty_emit + on-demand at gated tmt_write). MEASURED:
LL misses -30% (12.9->9.1M), wr misses -39% (9.28->5.64M), whole-box wall only +1-2%
(501->505-511K) => at the 22-verb random workload the box has BW headroom at 8184 envs
(NOT saturated like the 14-verb-era 0.69M profile) — reset-path miss cuts bank as
headroom; wall-clock gains need the DEEPER-play regime (vision/viz step-path = next).
Remaining wr misses: savelev/restore bwrite + vision. 501K baseline / 505-511K now;
1377 resets per 341x400 bench = ~125-step episodes = reset-heavy vs training's ~1600.
FRONT-1 KICKOFF MEASUREMENTS (2026-07-21 end of session): whole-box baseline (24 pinned
procs x 341 envs x 60 steps, current 22-verb env + all engine commits) = **561K SPS
aggregate** — THE number front-1 must beat. SPS-MEASUREMENT CAVEAT (user): training SPS
DECREASES over a run then levels off (early policies are cheap — short shallow episodes;
converged play = deeper/longer = slower env steps). All same-phase smoke comparisons
(374->419K) are directionally fine but the LEVELED-OFF SPS is the honest number — confirm
the +12% at convergence on the next full run. Same bias in the 60-step whole-box baseline
(fresh-env early-game state); re-baseline front-1 with longer runs (341x500+) and, once
available, an actions-file trained-workload stream (historical 0.69M was the 14-verb env, not
comparable). globals.def ALREADY HAS a heat taxonomy ('hot' = touched every step, packed
first, prefetch-covered; gen_ctx.py generates struct from it) — the hot/cold split is NOT
greenfield: the task is AUDITING the hot/cold classifications against measured cachegrind
DLmr/DLmw at 341+ envs and re-tiering misclassified fields, then map SoA (levl.typ plane)
+ viz/gbuf narrowing. Next session starts there.
COORDINATION (user, 2026-07-21): front-4 overlap is BEING DONE BY ANOTHER PERSON — do not
touch pufferlib vecenv/train scheduling; stay engine-side. MY NEXT FRONT = touched-bytes
(front-1): (a) hot/cold split of nh_ctx — globals.def X-macro generates the struct, so
reorder by per-step touch frequency (cachegrind DLmr/DLmw per field region grounds it;
"hot fields packed first" is already the design intent per fork CLAUDE.md — audit how true
it is); (b) map SoA: levl[][].typ into its own plane (spatch mechanical rewrite); (c)
viz_array/gbuf narrowing; (d) deepest_lev_reached cache (1/step now, small). Gauntlet per
change: 34x3 goldens + 78 fuzz + stock_diff fresh seeds + no-globals + bench hash
5e7d1fc73eabda61 + multithread parallel-proc bench (the METRIC for front-1 is whole-box
aggregate SPS — 24-proc pinned bench pattern from [[nethack-env-speed-campaign]], NOT
single-thread). Engine cuts still pay
on whole-box env throughput once bandwidth headroom exists. NEXT SURGERY (by
trained-workload Ir): vision_recalc+left/right_side ~16% (incremental vision = the big
one), mfndpos 7%, m_move 5.7%, pline/printf ~4%, env-side strstr/pack_obs ~4.7%; then
front-1 bandwidth (hot/cold ctx split, map SoA, viz narrowing) + front-4 rollout/train
overlap (pufferlib-side).
