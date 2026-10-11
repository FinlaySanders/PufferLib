---
name: nethack-engine-bugs
description: Deterministic engine hang (seed 209) + heal-arm segvs — reproducers for a gdb session
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-13T21:00:45.964Z
---

2026-08-02, r2 build (ed566bb4), champion config 250M runs: three engine
incidents, all deterministic-reproducible:
- **seed 209 HANG x2**: baseline `./puffer train nethack base.seed=209`
  wedges ~161M (main thread spins 100% in userspace inside an env step,
  OMP workers parked; GPU 0%, jsonl stops). Second run stalled at same
  region — bit-deterministic reproducer.
- **heal-arm SEGVs**: `env.heal_coef=0` seed 207 died 66M, seed 210 died
  215M (exit 245 = -11). REPRO CONFIRMED 2026-08-02 09:35: heal s207 segv at EXACTLY 66M again (3 incidents, all deterministic). Config changes shift game-state distribution into engine landmine states; nothing semantic about heal_coef itself.
- No behavioral anomaly precedes any of them (prayer rates normal for the
  build: ~7/ep everywhere, mostly prayers_starving — prayer is a routine
  FOOD strategy now, NOT the rare backstop of the food-clock era).
Container blocks ptrace even as root; perf not installed. Debug path:
debug-build + run seed 209 from scratch under gdb (deterministic → same
wedge point), or add a watchdog/SIGALRM backtrace dump to the engine.
Related: [[nethack-crash-hardening]] (panic paths covered; hangs and raw
segvs are not).

2026-08-02 ~10:30 ROOT CAUSE + FIX (heal segv): gdb-launched repro (attach
blocked in container, but launching children works; FIRST attempt failed
because capping total_timesteps changes schedules = different trajectory —
repro must be byte-exact config). Backtrace: inhishop <- tended_shop <-
dosounds <- moveloop. tended_shop reads rooms[].resident UNGUARDED and
inhishop derefs ESHK -> segv on stale shopkeeper (dealloc'd mextra, isshk
uncleaned — the EXACT pathology already documented+guarded in next_shkp/
shop_keeper; tended_shop was the missed third site, hit every turn via
dosounds' shop scan; also reachable from bones.c/uhitm.c). FIX: has_eshk
guard in tended_shop (vendor/fast-nle/src/shk.c) matching sibling pattern.
Goldens 34/34 bit-identical, 2M smoke 25.828 bit-identical. NEEDS FORK
COMMIT in vendor/fast-nle. s209 hang: possibly same corruption family
expressed as loop; gdb+timed-INT probe running (fix changes s209 RNG
stream via tended_shop's rn2-consumption change on garbage-boolean paths,
so completion != proof of fix — only a re-wedge is informative).

2026-08-02 09:59 FIX CONFIRMED: heal_s207 byte-exact repro passed 113.8M
(3x prior segv at 66M). tended_shop guard fully validated (goldens 34/34 +
2M smoke bit-identical + repro survival). PENDING: fork commit in
vendor/fast-nle; s209 gdb hang probe running.
ASYNC AUDIT (same morning): machinery CORRECT (actor snapshot real+consumed,
slot bookkeeping right, ratio-fill-1.0 deliberate). Collapse = hypers:
async KL 100x sync from epoch 0 (0.023 vs 0.0002), entropy crashed by 25%
mark -> premature convergence. Champion clip_coef=1.0 swept under sync
(ratio always ~1, clip inert); async starts ratios displaced -> runaway.
TEST QUEUED-PENDING: async + clip 0.2 (maybe lr x0.5) should recover most
score; if so async ~1.9x speed becomes usable via small hyper fork.

2026-08-02 ~11:00 SECOND BUG FOUND+FIXED (s209 hang): gdb+timed-INT capture
worked — worker wedged in alter_cost <- bill_dummy_object <-
costly_alteration <- touchfood <- doeat (eating billed shop food).
ROOT CAUSE: alter_cost's scan advances with next_shkp(shkp, TRUE) but
next_shkp starts AT the given monster => returns same shk forever when the
object is billed by a LATER shopkeeper (2 shops with active bills). One-token
fix: next_shkp(shkp->nmon, TRUE), matching the file's own idiom. Introduced
by NLE-lineage commit c7099cd77 ("alteration of shop-owned objects (trunk
only)") — PREDATES our fork; affects NLE upstream + possibly NetHack trunk.
Goldens 34/34 (completed trajectories can't contain never-returning states).
COMPLIANCE per fast-nle CLAUDE.md non-negotiable #1: both shk.c fixes change
behavior ONLY where stock segfaults/hangs (no defined stock behavior there);
frame fork commits accordingly. vendor/nle July-3 dirty clone = the
liujonathan24 PRIOR-ART reference checkout (per CLAUDE.md) — KEEP.
Chained verification: task bw6qj5jrs (2M smoke + rcbase_s209 completion,
which also restores the pruning matrix control).

2026-08-04 SEGV ROOT-CAUSED + FIXED (3rd UAF on the newcham path, stock 3.6.6 bug):
crashes cost 2 runs in one day (tip_s207 @192M, msgconv_s211 @131M; exit 245 = 256-11).
gdb (batch, run-to-crash, `bt full` + `thread apply all bt`) on the SAME binary — no
rebuild, bit-determinism is the repro — landed at newcham+1052, `mov (%r12),%r12` with
r12 = 0x70be403f1 (5-byte truncated ptr), i.e. the mon.c:3810 "former giants can't carry
boulders" loop walking a stale `otmp2 = otmp->nobj`. MECHANISM (do.c:158-200): the
boulder is dropped on mtmp's OWN square; if mtmp is pit-trapped, flooreffects crushes it
with its own rock (context.mon_moving -> mondied, else hmon->killed) -> m_detach ->
relobj moves the whole inventory to the floor -> bury_objs buries/frees it -> the cached
successor dangles. Needs ex-giant shapeshifter + >=2 boulders + pit + non-rock-throwing
new form => ~1 per 150M steps. FIX (vendor/fast-nle mon.c, uncommitted): rescan from
mtmp->minvent after each drop instead of caching nobj, `while (!DEADMONSTER(mtmp))`;
terminating because every boulder is obj_extract_self'd before the drop. GATES: goldens
34/34 bit-identical, check_no_globals.sh OK (needs the lib as argv[1]), seed-211 cleared
131M and ran to 164M clean. Siblings already fixed: 76f699e1c (engulfer kill), 21e7e0b53
(shapeshifter expel) — both spoteffects->level-change routes, guarded by
in_mon_spoteffects; this one is a different route (flooreffects->monster death) that the
guard cannot cover. UPSTREAM: report with alter_cost hang.

**2026-08-09 BOOMHIT CRASH CLASS SOLVED+FIXED:** gdb capture (v3null_s304, deterministic at ~98M): SIGSEGV `throw_obj → throwit → boomhit → m_respond`, all libnethack.so. Root cause: boomhit's flight loop advances bhitpos along the curve and calls m_at/TYP_AT BEFORE any bounds check — boomerang thrown near a map edge steps off-grid, m_at reads the monster grid OOB, m_respond(garbage) segfaults (upstream fixed in 3.7). Fix shipped in vendor/fast-nle/src/zap.c: isok() guard before m_at, retreat+break like a wall hit. Goldens 34/34; seed-304 repro survives 10min+ past former crash point. Likely the seed-211/seed-308 "2/day" class (all crash sites seed-linked via dungeon boomerang spawns; sc0125_s308 at 49M + spnull2_s308 at 81.9M plausibly same site). VENDOR BUILD GOTCHA (bit us AGAIN): after any vendor rebuild, ./puffer MUST be rebuilt — regenerated nh_ctx headers make the old binary segv at boot instantly (1-line log, core dump before first print = this signature). PKILL SELF-MATCH (again): pattern with run_id matched own shell, exit 144 aborted a compound command — kill by explicit PID only.

**2026-08-10 KEY-EATING MODAL WEDGE SOLVED+FIXED (the "8,364 StF casts" artifact):** deterministic eval env froze at t=10,079 after eating a tainted corpse — every subsequent action swallowed silently (no bell: gdb break tty_nhbell = 0 hits full run; no turn; empty topline; misc=0,0,1 xwait). Root cause: a getpos-class modal (position picker — only ESC exits; eats letters AND '\r' silently) + drain_prompts' repertoire gap (ESC only for yn; xwait/getlin got '\r' only) → 64 wrong keys/step forever. Bounded by step cap (env recovers on truncation — NOT a permanent zombie; ~1/14K episodes, one wasted episode-tail each). FIX SHIPPED: (1) drain alternates '\r'/ESC; (2) always-on stall watchdog: game-turn frozen 96 steps AND a misc modal flag set → 8×ESC burst (gated on modal flags — behavioral free-action loops like wall-punching are the policy's business, left to the step cap). Validated: wedge episode recovers, StF casts drop to scattered real ones. FORENSICS-TOOLBOX built along the way: CASTLOG env=%p + CASTRES post-cast topline (in-macro capture — pack-time capture reads empty, message consumed), NH_CASTTRACE per-keystroke topline, NH_STALLLOG, NH_MSGLOG (demo). LANDMINE: wandb env/<verb> = rolling TRAIN stats (ε-inflated, phase-averaged) — terminal-policy adoption MUST be verified by eval castlog (spnull2_s702 "12.9 casts" trained vs ZERO at eval). Slot-1+ pointer casting VERIFIED WORKING (detect monsters etc. real at eval); genuine elective second-spell use is rare (book supply = bottleneck → books arm). ptrace attach blocked in container (yama scope 1 RO) — gdb must SPAWN the target.

2026-08-10 CAST WEDGE VARIANT SURVIVES THE SHIPPED FIX (open): fresh
NH_CASTLOG census of v3fbc_s702 on the committed hardened binary (d802a161)
shows 48 wedged episodes in ~14.5K (~1/300 for this heavy-caster profile;
the drain/watchdog validation had only covered v3fb_s701). Signature: one
env, game-turn + hp + pw + fail all FROZEN across ~9K CASTLOG attempts
(e.g. env t=2629 sid=348 hp=12/47 pw=33/35 x9,277), CASTRES topline EMPTY
-> silent key-eating modal entered via the CAST macro's own key path; no
misc flag set, so the gated stall watchdog is blind to it and the \r/ESC
drain alternation never runs. Bounded by step-cap truncation as before.
Repro: the census eval command is bit-deterministic; next step is
NH_CASTTRACE keystroke forensics on a wedged env, then either extend the
watchdog gate (frozen turn + frozen topline + repeated CAST) or guard the
macro. Wedge (env,t,sid)-cell exclusion (>=50 casts, t>100) is the census
hygiene rule for all castlog stats — buckets in awk need k+0 (string-key
comparison silently garbles histograms).

2026-08-10 CAST-WEDGE ROOT CAUSE + FIX (closes the entry above): gdb
breakpoint-on-getpos over the deterministic census (spawn-under-gdb,
commands{bt;continue}) caught 1,641 entries: 1,636 = DETECTION MAP BROWSE
(object_detect/monster_detect/gold/food <- peffects <- dopotion; a few via
scrolls), 3 = crystal ball apply, 1 = controlled scroll-teleport. Quaffing a
detection potion drops into an interactive getpos cursor-browse ("(For
instructions type a '?')") that raises NO misc flag -> policy keys eaten
silently; episodes escape only if an exit key ('.',',',';',':',ESC) happens
to be sent — pure CAST spam never exits => the ~1/300 wedges. FIX (both in
tree, uncommitted): (1) fork do_name.c getpos() returns immediately
(abort, or hero square when force) — kills browse/crystal/teleport-control
modals at the root; (2) nethack.h stall watchdog gate widened to
unconditional at 96 frozen steps (ESC burst is a no-op in normal play).
Goldens: 6 aa_* (AutoAscend streams) diverge at the key after "#te\r"
(#terrain browse) = intended change; added NLE_REPLAY_UPDATE=1 mode to
replay_golden.c (writes <golden>.new), re-pinned with byte-identical action
streams; 34/34 OK. replay_golden is NOT a cmake target — hand-compile:
gcc -O2 -I include -I build/include -I build/src
-I build/_deps/deboost_context-src/include tests/replay_golden.c -o
build/replay_golden -ldl.

BUILD LANDMINE (cost a wasted 1B run): `./build.sh nethack --gpu` ALWAYS
fails ("nethack.cu must typedef obs_t") — the correct command is plain
`./build.sh nethack` (ENV_HEADER=nethack.h; PUFFER_NETHACK pulls the CUDA
in). A `cmd > log && echo OK || tail log` chain exits 0 on failure — READ
the build log / require the OK marker before trusting any rebuild. The
NH_SPELL-default-flip "bit-exact parity" (8,583.463 twice) was two runs of
the SAME old binary — retracted as flip validation (it did prove s702 has
zero slot-1+ eval casts). commit_s702 1B ran 85 min in legacy spell-off
mode on the stale binary — killed; commit2_s702 relaunched on the true
committed stack + getpos fix.

2026-08-10 SECOND WEDGE CLASS = STUN ZERO-TURN CAST LOOP (the real one; the
getpos fix was necessary but covered only 37/48 wedges): fiber bt of a live
wedge showed rhack->get_count->readchar = MAIN PROMPT, not a modal. Per-key
trace: Z -> "You are too impaired to cast a spell." (rejectcasting: STUNNED;
zero-turn, no message clock, no Pw) -> macro's 'a' lands at main prompt ->
opens APPLY getobj prompt -> dir key invalid -> drain closes -> repeat.
SELF-SEALING: stun only expires with game turns; zero-turn refusals advance
none; policy keeps choosing CAST => frozen until step-cap (~9K attempts).
ESC-immune (nothing to escape) => watchdog can't help. The v3 mask rewrite
had DROPPED v1's rejectcasting mirror (kept know/Pw/hunger only). FIX:
mask CAST on condition bits STUN|STRNGL (0x84; CONF stays legal — confused
casts consume the turn honestly) + CAST macro now proceeds past Z only if
the "hich spell" chooser prompt actually opened (misc yn) — any future
unmirrored zero-turn refusal wastes one step instead of wedging + apply-spam.
freehand ("arms are not free") remains unmirrored (not in condition bits;
welded-weapon+shield Monk = rare; the macro gate bounds it now). User's
observation "it used its healing spell while confused and died" was this
bug — I initially explained it away as status-line misreading. Forensics
pattern that worked: watchdog gdb anchor (nh_stall_mark, code-side
conditioned) -> scheduler-locking on -> tbreak NetHackRL::rl_nhgetch ->
continue = backtrace ON the wedged fiber. CASTSTEP tracer was slot>0-gated
(blind to slot-0 wedges) — now traces all slots with misc flags.

2026-08-10 WEDGE SAGA CLOSED — final census (v3fbc_s702, full fix stack):
score 8,468.780, max repeat cell = 3 casts (was 9,363), ZERO wedge cells,
honest cast profile intact (44.4K prot / 23.8K heal / 22.3K sleep). Fix
stack: (1) getpos short-circuit [detection browse, 37/48 wedges]; (2)
nle_cast_blocked/nle_cast_blocked2 engine predicate (stun+chant+freehand+
too-weak) wired into the CAST mask [stun loop 10/48, freehand residual];
(3) CAST macro proceeds past Z only on misc XWAIT (the spell chooser is a
MENU — empty topline, misc=0,0,1; my first gate tested yn+"hich spell" and
broke ALL casting: 6.2M zero-turn chooser spam, score −250 — check the
existing CASTSTEP trace before writing prompt gates); (4) watchdog
unconditional at 96 frozen steps (backstop). Goldens 34/34. All uncommitted
on top of d802a161/30abdf752; commit2_s702 1B killed twice (stale binary,
then user call to free GPU) — restart the 1B validation ONCE on the final
committed stack. Cert-binary bookkeeping: puffer_commit2 = binary of the
killed run; puffer_d802 = committed-tree binary (pre-flip... actually
pre-flip-REBUILD: identical to committed intent, flip untested in it).

2026-08-10 fixes COMMITTED: pufferlib d2b132db "cast wedge fixes"
(mask predicate + macro chooser gate + unconditional watchdog + gdb
anchor), fork b85e9d822 "rl: kill zero-turn cast wedges" (getpos
short-circuit, nle_cast_blocked, replay update mode, aa goldens
re-pinned). Final 1B validation = commit3_s702 (group val-commit),
bare launch on this exact stack; cert gate ≥990M vs {8,559, 8,695}.

**2026-08-13 SEGV CAMPAIGN BREAKTHROUGH — Tourist deterministic reproducer**
(./puffer_tour = Agent-tou-hum-neu-mal binary, seed 999, 3M smoke, crashes
<3M; seed 998 passes; ALSO reproduces vec.num_threads=1). TWO BUGS FOUND:
**BUG 1 FIXED (uncommitted, vendor save.c)**: heap-UAF — touch_artifact
death mid-pickup → done→freedynamicdata frees obj chains but level.objs/
monsters cell arrays in the persistent ctx keep dangling pointers; env
accessors (nle_container_at etc.) walk them post-death. ASan-verified
(alloc: mksobj/mklev; free: saveobjchn←nh_terminate←touch_artifact←pickup).
Fix = memset level.objs/monsters + fobj/fmon=0 after free_current_level in
freedynamicdata (post-final-obs → goldens unaffected). ASan confirms gone.
**BUG 2 SOLVED (same session): stale returncontext after resume-past-death.**
Mechanism: multi-key macro sends a key AFTER the game died mid-macro →
nle_step resumes the DONE coroutine → it wakes inside nethack_exit's
nle_yield(NULL) where `if (notdone)` SKIPS the returncontext update → the
engine's exit path runs on and its next yield jumps through the STALE
record → by then recycled worker-stack frame (locals + stack-protector
canary) → jump_fcontext's ldmxcsr loads reserved bits → #GP (SIGSEGV
si_code=128, si_addr=0 — NOT a paging fault; frame-walker "garbage"
0x0002004800030048 = legit rbp data under -fomit-frame-pointer, red
herring all day). FIX (vendor nle.c, uncommitted): (1) returncontext
update made UNCONDITIONAL in nle_yield; (2) nle_step refuses done games
(obs->done=1, return). Bug-1 fix (save.c level.objs/monsters nulling)
also kept. Full verification: seed-999 reproducer passes 1-thread +
32-thread + seed 998; fpgate PASS 703c4adf (fixes behaviorally invisible
to healthy monk trajectories). Hunt lessons: canaries capturing AFTER the
skipped update shadowed the corrupt state (self-consistent wrongness);
refuted en route: guard-leap, stack size, TLS caching, LTO inlining, mmap
exhaustion, async overlap, freed-nle, jmp_buf. ASan build dir kept:
vendor/fast-nle/build-asan (LD_PRELOAD libasan + LD_LIBRARY_PATH, RUNPATH
overridable). This likely closes the ~1/day cross-class kill class (both
bugs fire on mid-macro/mid-action deaths). Class runs: valk 7,643 / barb
6,605 certified (see arch memory); tour_s305 UNBLOCKED + running.

**2026-09-01 apass1b_s808 SIGFPE**: rc=136 at ~424M steps (40m in), log ends clean mid-dashboard, no error text -> CPU-side engine FPE (divide), same class as heal-arm segvs; APASS is GPU-only, not implicated. Bit-determinism => rerun should reproduce at same step. REPRO QUEUED: apass1b_s808r under batch gdb (bt full + all-threads) via /tmp/apass_1b2.sh after s901+s902; /proc/sys read-only in container (no core_pattern control, apport eats cores) -> gdb-batch is the capture path.

**2026-09-02 ENGINE PLANES (fast-nle, uncommitted in vendor/fast-nle working tree; user-ordered "make all the optimisations, analyse SPS")**: per-cell lookup planes replacing list walks in the monster-AI loop — trap plane (t_at O(1)), engraving plane (engr_at O(1), helpers live in engrave.c because head_engr is file-private), pile summary bits (BOULDER/SCARE/GARLIC/CURSED; sobj_at + cursed_object_at + mfndpos fast paths), compact fobj index (nh_fobj_next_in iterator for m_move item search + dog_goal; NH_FOBJ_CAP 4096, overflow falls back to the list walk), and a cell-first exact fast path in onscary. Write-through hooks: maketrap/deltrap/mkmaze bubble traps; make_engr_at/del_engr/rloc_engr; place_object/remove_object/**splitobj/replace_object** (both bypass place/remove and stalled the index — found by verify), curse/uncurse/bless, fracture_rock, cancel_item, trap.c water/fire otyp changes; nh_planes_clear at level teardown (save.c ×2, mklev clear_level_structures, restore find_lev_obj prelude) — WITHOUT it t_at returned dangling freed traps during mklev (nondeterministic golden failures); nh_planes_sync next to nh_typ_sync but in restore ONLY after find_lev_obj+rest_engravings (the early restore syncs walked garbage → segfault). NLE_PLANE_VERIFY=1 hard-compares every plane at fill_obs (winrl.cc, folded into the existing `verify` static). GATES GREEN on final build: goldens 34/34 plain, verify, interleaved, shuffled+verify, !status_updates; stock_diff fuzz 26/26 (two seed bases); no-globals strict. RESULT (honest): the list walks were only ~3% of a trained-policy step (I had read self cost as inclusive) — paired fixed-seed callgrind: env step Ir −1.3% (onscary −13%, sobj_at −45%, t_at −27%, m_move +3.6% from the index), random-policy shallow +2.6% (maintenance overhead, nh_pile_recompute); eval-mode 2B ckpt paired vs old-lib control 184K→190K (+3%), +4-7% in the deep phases; fresh-policy training 30M within noise (253.7 vs 260.2K). The monster loop's cost is its own per-candidate-cell logic (mfndpos 17%, m_move 13% self), not the walks. LANDMINES: callgrind demo seeds from the clock unless NH_SEED set (unpaired profiles are noise); bench/timing runs during concurrent training are invalid (36→25 µs "gain" was contamination; quiet paired = 19.5 both); `env VAR=.. valgrind` invocation lost the program (2.4M Ir) — use plain prefix assignment; pkill -f self-match (exit 144) x2 more.
2026-09-02/03 NIGHT CRASH TALLY (1B runs, box, 16 env threads, 8 concurrent): 3 of 32 runs died host-side — w512_s801 SIGSEGV @903M, nlp_s803 SIGFPE @50M (relaunch survived the same step → not trajectory-deterministic), linpool_s802 SIGSEGV @644M. ≈9% loss rate per 1B run → the sweep will lose ~1 in 10 runs; both fault classes are the known race-class engine family. No cores captured (ulimit -c 0). Action item: enable core dumps (ulimit -c unlimited + core_pattern) for the sweep, or run the TSAN engine build repro.

**2026-09-07 LONG-RUN CRASHES = MEMORY BLOW-UP (t973 config):** overnight 1B/2B lanes on the drone box: every t973 run died (2 segfaults at ~534M, 2 OOM-kills at 1.3-1.6B, 1 SIGFPE at 32M) plus t865 2B (OOM at 1.3B). Panel logs said rc=0 because `echo "$(date) ... rc=$?"` evaluates $(date) first (logging bug; real signals were in the lane .nohup files). Live specimen rt_1B_0973_s203: RSS 154 GB at 1B steps, 335-354 GB during its final eval (grows ~4 GB/min there vs 0.36 GB/min in training), smaps: 354 GB anonymous private, ONE 116 GB rw-p mapping (a single buffer grown by doubling) + thousands of 128 MB malloc arenas; [heap] only 1.4 GB. Healthy configs (t877/t894/... 1024x4 too) sit at 2-5 GB for the whole run. NOT reproduced by: the single-env terminal demo with the trained t973 weights (107 episodes incl. depth 27, 1.2 kB/episode), or 30M-step training probes (t973 and control both 2.3->4.3 GB then flat). Ruled out by reading: trainer has no unbounded arrays (log_history capped), pinned buffers allocated once, env wrapper has zero heap allocs, engine nle_end frees ctx/tmt/stack, no ttyrec (FILE* NULL), no trace keys. Open: something that appends ~100 B per agent-step for the process lifetime and kicks in late/behaviour-dependent. Armed: gdb catcher (catch syscall mremap / mmap>=256MB) on a 300M t973 probe (gdb_probe_catch.log), 300M RSS curves t973 vs t877 (leak_probe2.log), eval-only test with the trained t973 checkpoint (leak_test.log; eval needs --headless and NETHACKDIR), standalone evals of dead checkpoints + calibration vs known inline scores (eval_dead.log/eval_calib.log; no burn-in key on the box build so standalone reads low).
**09:05 update — NOT t973-specific:** local t643 (128x4) seed 306 was OOM-KILLED on the 123 GB box at 648M steps while seeds 301-305 ran to 1B clean. A solo t973 seed-13 600M-schedule probe never leaked (4.30 GB flat, gdb caught nothing) and the trained-policy eval-only runs never leaked. => a rare per-trajectory event: once hit, one buffer grows without bound for the rest of the process (plus thread-arena growth). Wrapper has NO episode step cap (truncated path never triggered) so a wedged game is immortal; libtmt only resizes at open (24x80) — ruled out. Reproductions with instrumentation: drone box exact replay of the overnight seed-201 1B t973 run with gdb (catch mremap / mmap>=256MB / SIGSEGV -> gdb_catch_rep201.log), local rerun of t643 seed 306 with RSS/min and a gdb attach trigger at >6 GB (wt_97416d02/rerun_s306.log, gdb_local_catch.log). Candidate mechanisms: game stuck in a prompt/modal (stall watchdog ESC bursts every 96 steps) generating per-step growth in engine message/text buffers, or a runaway realloc'd buffer in the engine.

2026-09-07 LEAK PROBE 4 RESULT: "exact replay" of the dead t973 1B seed-201 run (same args, shipped async=1/4-buffer config) ran the full 1B steps at a flat 4.3 GB RSS, no crash. The original died at ~524M after 83 min. Because the shipped config is not bit-reproducible, a same-seed replay is a DIFFERENT trajectory: the leak is a per-trajectory lottery, not a seed property. gdb cannot attach on the vast/drone box (ptrace blocked: yama ptrace_scope / "Inappropriate ioctl"), so catchpoint-based capture is impossible there; the gdb log shows the catchpoints were never armed. Next capture options: (a) in-process LD_PRELOAD mmap/realloc interposer logging any allocation >=256 MB with backtrace() (no ptrace needed), run under several concurrent t973 lanes (leak hits roughly half of them); (b) async=0/num_buffers=1 lanes so a crash becomes replayable. Hypothesis to test: a per-episode buffer that grows per step inside a never-ending episode (handless-lycanthropy zero-time loops run 70K+ steps natively).

2026-09-07 11:36 LEAKCATCH LANES: built scratchpad/leakcatch/leakcatch.c (LD_PRELOAD interposer: malloc/calloc/realloc/posix_memalign/aligned_alloc + direct mmap/mremap >= LEAKCATCH_MIN_MB logged with backtrace(), SIGSEGV/SIGABRT/SIGBUS backtrace; glibc reaches mmap via an internal alias so malloc-family hooks are required; bootstrap arena for dlsym). Verified locally (trainer 2M steps unchanged, 10 baseline CUDA entries) and on the drone box. Driver /workspace/sweeps/nh/nh_leakcatch.sh: 5 t973 1B lanes seeds 301-305 on gpus 1,3,4,5,7, per-lane files lc_lc_0973_s30N.{out,alloc,rss,maps}, watchdog stops a lane by PID past 40 GB RSS after dumping its largest smaps entries; master log leakcatch.log. Box RAM 503 GB. Do not edit nh_leakcatch.sh while it runs (bash reads scripts incrementally).

2026-09-07 14:05 CORRECTION: t973 DOES scale at 1B. Leak-hunt lanes (t973 1B, fresh seeds, interposer on) finished clean: s301 10488, s303 7519 (s302/s304/s305 pending). The earlier "t973 stalls at 6.6K" claim came from burn-in evals of MID-RUN checkpoints of the dead lanes (524M of a 1B schedule, 1.44B of a 2B schedule) which lack the LR-anneal endgame; not comparable to finals. t973 1B is high-variance (7.5K-10.5K so far). Leak: 5 x 1B t973 lanes, ~1B steps each, zero allocations >=64 MB after startup, RSS flat 4 GB -> the leak did not occur in 5/5 fresh 1B lanes (overnight it hit 3/3 t973 1B lanes on the same box; difference: overnight lanes ran 8 concurrent with 2B lanes, and the shipped binary without LD_PRELOAD). Next: 2B lanes with LEAKCATCH_MIN_MB=16.
