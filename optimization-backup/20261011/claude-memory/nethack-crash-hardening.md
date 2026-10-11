---
name: nethack-crash-hardening
description: "Overnight sweep crash 2026-07-07 root-caused: NLE panic->dosave0 SIGSEGV killed run 20; fixes: no emergency save, arena 512MB+panic reserve, sweep driver reaps dead children"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5d4abbbc-50c6-4248-8a99-94fb927393d2
  modified: 2026-07-19T10:36:38.905Z
---

Overnight sweep crash 2026-07-07 (~20 runs in, ~02:29): env 756 (dlvl 11, step 9056) hit
`alloc()` panic inside `restmonchn` (level-file restore), then NetHack's panic() attempted an
emergency save (`dosave0`) on the half-restored state and SIGSEGV'd in
`do_light_sources->get_mon_location`. Process died; sweep driver then hung forever on
`result_queue.get()` (no timeout, no child-liveness check). Diagnosis chain: sentinel crash
file `nle_crash_<pid>.txt` + `addr2line -e libnethack.so -f <offset>` on the anonymous
frames (no line info, but function names resolve — `+0x43d3c`=alloc, `+0x1df181`=restmonchn).

Key architecture facts learned (vendored NLE fork, [[nethack-env-setup]]):
- alloc.c: NetHack alloc/free replaced by per-env bump arena, free() is a NO-OP; memory
  returns only at episode end (nle_end munmaps). Was capped 64MB -> panic on exhaustion.
  Bump arenas have no redzones: small overruns silently corrupt neighbor allocations
  (possible source of the garbage monster-size that alloc panicked on).
- panic() ends in really_done(PANICKED=11) -> nle_done -> graceful episode end. The ONLY
  reason panics killed the process was dosave0. how_done=11 logs as death_other.
- Level files are per-env isolated: fqn_prefix is per-ctx (nle.c:518 sets LEVELPREFIX to the
  env's mkdtemp vardir); s_lock is empty so files are ".<ledger>". CHDIR/VAR_PLAYGROUND
  compiled out. mread panics loudly on short reads (DEF_MREAD_SHORT) — a garbage-content
  read means content corruption, not truncation.
- Measured arena burn (arena_probe, random policy): ~0.28MB peak/episode, 9KB per level
  transition — 64MB exhaustion needs a ~200x heavier episode, so corrupt-length is as
  plausible as exhaustion. Next occurrence will disambiguate via recorded panic_msg
  (used= vs req=).

Fixes shipped (all verified):
1. vendor end.c panic(): message formatted + nle_sentinel_set_panic FIRST; dosave0 block
   removed (NLE can't restore saves anyway). Panic now = graceful episode end.
2. vendor alloc.c: per-env arena 64->512MB (MAP_NORESERVE = virtual-only cost), overridable
   via NLE_PER_ENV_ARENA_BYTES; 8MB panic reserve (min(8MB, cap/4)) unlocked when
   program_state.panicking — really_done allocates, without reserve an exhaustion panic
   would nest-panic->NH_abort. Exported nle_arena_ctx_used/cap(ctx) getters (out-of-tree
   code must NOT poke nle_ctx_t fields — layout depends on build flags; probe read garbage).
3. pufferl.py sweep loop: result_queue.get(timeout=60) + reap runs with any dead rank
   (terminate stragglers, observe is_failure=True, continue); train() returns proc handles.

End-to-end verified: NLE_PER_ENV_ARENA_BYTES=400000 probe run -> mid-episode panic ->
how_done=11, process survived, later episodes normal, no crash file. Training smoke clean.

Probe pattern (scratchpad arena_probe.c): standalone env binary via README's clang command
(-I ocean/nethack added), typedef boolean/schar + `#define nle_ctx nle_globals` before
nethack.h if including nle.h — but prefer the exported getters.

## 2026-07-12: wild-read crash class FULLY CHARACTERIZED (seed-777 forensics)
- Reproducer: puffer train nethack --seed 777 (factorized build, oracle f3ed7d29 era) — ALL crashing configs die at epoch 2310-2316 (same game event, ~76M steps): O3 plain/perturb/gdb, O0 gdb x2, single-thread. Clean configs (ASAN lib; O0+gdb+MALLOC_PERTURB_) complete 200M with BIT-IDENTICAL finals (1638.921 both) => game math never depends on the read value.
- MECHANISM: one deterministic in-game event derefs a garbage non-null pointer from level.monsters (m_at) — crash sites newsym display.c:863 and attack_checks uhitm.c:158, BOTH adjacent to is_worm_tail checks (stale worm-segment cell is the prime suspect; upstream 3.6.x had wormno/segment bugs). Read is behaviorally inert; SEGV depends purely on whether the wild address is mapped (ASLR luck). Explains: rare "random" sweep deaths hours-in, goldens/oracle always clean, ASAN clean (wild address lands in mapped shadow), crash-site variability.
- NOT: use-after-free (ASAN clean), cross-thread race (1-thread crashes), uninit-behavior divergence (finals bit-match).
- Next-session hunt plan: newsym crash gave cell (52,11) — game-state-stable anchor. Two-phase gdb: run to crash, identify ctx/env; rerun with hardware watchpoint on that ctx's level.monsters[52][11] to catch the WRITER of the garbage pointer. Or diff fork worm.c against NetHack 3.6.7/3.7 worm fixes. Artifacts in scratchpad: gdb_*.log, asan_seed777.log, s777_*.log. ASAN recipe: build-asan + LD_PRELOAD="libasan.so build-asan/libnethack.so" ASAN_OPTIONS=protect_shadow_gap=0:detect_leaks=0 (CUDA-compatible).
- Sweep mitigation until fixed: crashes are layout-luck, ~rare; sweep driver should observe dead child as failure and continue rather than raise (proposed earlier, not yet applied).

## 2026-07-12 (cont): wild-read bug LOCALIZED via grid-consistency checker
- Instrumented engine (worm.c nle_gridcheck, gated NLE_GRIDCHECK=1; hooks in mon.c movemon after dochug/fightm/dmonsfree + allmain.c after rhack/goto). Forward pass: every non-null level.monsters cell must map to an on-chain monster's mx,my or worm seg. Inverse pass: every live monster must be registered at its own mx,my. Trajectory-preserving (pure reads).
- SEED-777 CULPRIT (deterministic, moves=3828, cell stays desynced every turn after): monster is DOUBLE-REGISTERED — mndx 114 (baby purple worm, wormno=0), tame=16 peaceful=1, mx,my=(52,10)=HERO cell, correctly on grid at (52,10) BUT stale duplicate at (52,11) [its pre-swallow cell]. So a swallower reached the hero's cell without its old grid cell cleared, and the desync persists (tame swallower not being released?). The (52,11) stale ptr is the wild read that later SEGVs newsym/attack_checks.
- Checked stock paths, all correctly remove+place: gulpmu (mhitu.c:1804), expels->mnexto (mhitu.c:222), hero-pet swap (hack.c:1865). Bug is a FORK modification to one of these or an unread path. Inverse-checker run (s777_gc4.log) will name the exact tag+actor at first desync = origin. mtame=16+swallow is contradictory (tame mons don't attack) => worm swallowed while hostile then got tamed mid-engulf (farm-mode item spam), exercising a rare state combo.

- INSTRUMENTATION GOTCHA (cost a cycle): level.monsters is PER-ENV (nh_cur macro) but a naive `signed char nle_gw_tag[COLNO][ROWNO]` global tag array is SHARED across all ~8 concurrent envs -> env B's remove_monster stamps the global tag while env A's grid legitimately holds its worm; tag reads back as cross-env garbage (saw lastwriter=2/remove on a non-null cell = impossible unless aliased). Any per-cell side-channel for grid debugging MUST be per-env (key by nh_cur) or run single-thread. Replaced with nle_cell_log(op,x,y,m) hardcoded to watch cell (52,11), printing nh_cur + moves + backtrace on every place/remove — filter CELLLOG by the crashing ctx (from GRIDCHECK[dochug] line) to get the write sequence + culprit stack. Confirmed via grep: only raw level.monsters writes are the 3 zeroing sites (mklev/save/restore) + steed.c place_monster; no untracked non-null writer -> the phantom is a tracked place that a later relocation stranded, exact stack pending gc6.

- CORRECTION: mndx 114 baby purple worm has AT_BITE only (NO AT_ENGL) + speed 3 -> CANNOT swallow, CANNOT act twice/turn. So NOT a swallow bug. Worm is double-registered: correct at (52,10)=hero cell (inverse checker silent) + stale (52,11). A non-swallow/non-steed/non-displacer monster on the hero's exact cell => swap-places (hack.c:1865) or displacement leftover, OR mx,my itself corrupted to hero pos. gc6 only watched (52,11) [saw place at moves=3828 via dog_move, never removed]; need the (52,10) writes to see the pairing — gc8 watches both cells + logs Conflict flag + u.ux/uy, backtrace on (52,11) writes. Culprit backtrace so far: place_monster <- dog_move (two offsets 0x1942/0x1978) <- m_move <- dochug; remove <- dog_move+0x207d. Suspect dogmove.c newdogpos ALLOW_U branch (line 1196-1203: conflicted pet attacks hero, mattacku + return 0, skips the remove_monster(omx,omy)+place_monster at 1212-1213) — but bite doesn't move worm, so mechanism still unconfirmed pending gc8 (52,10) sequence.

## 2026-07-12 RESOLVED: wild-read crash = stale-omx in dog_move commit
ROOT CAUSE (definitive, via DOGCOMMIT logger): dogmove.c dog_move() captures omx,omy = pet's position at function ENTRY (line ~899). If the pet is relocated during the same dog_move (displaced toward hero; grid+mx,my stay in sync), the move-commit `remove_monster(omx, omy)` clears the STALE entry cell (already empty, no-op) instead of the pet's real cell (mtmp->mx,my). Pet then place_monster'd at nix,niy -> its real cell left with a live grid pointer = phantom monster. Later newsym()/attack_checks() deref that stale level.monsters[][] ptr -> SEGV when the wild address is unmapped (ASLR-luck; hence rare, ASAN-clean since ptr is valid heap, crash-site-variable). Repro: baby purple worm (mndx 114) pet, seed 777, ~76M steps / game-move 3828. Observed: omx,omy=(51,10) mx,my=(52,11) nix,niy=(52,10) grid[51][10]=NULL grid[52][11]=worm.
FIX (dogmove.c:1212, goldens-safe — bit-identical to stock unless pet moved mid-dog_move): `if (level.monsters[omx][omy]==mtmp) remove_monster(omx,omy); else remove_monster(mtmp->mx,mtmp->my);`. 34 goldens PASS. This is the sweep-killer / random-hours-in-crash class — same root as the GPU-0 sweep death and tinybox kills.
FORENSIC METHOD (reusable): grid-consistency checker in worm.c (fwd: every non-null level.monsters cell owned by on-chain mon; inv: every live mon at its own mx,my), gated NLE_GRIDCHECK; then per-cell write logger with backtrace; then DBLREG detector in place_monster (fires when placing a mon still registered elsewhere); then DOGCOMMIT logger (omx vs mx divergence). GOTCHA: per-cell tag arrays must be per-env (level.monsters is nh_cur-per-env); multi-thread stderr interleaving garbles concurrent backtrace lines — trust DBLREG/DOGCOMMIT single-line records over CELLLOG sequences. Wrong hypotheses killed by data: orphaned worm segment (fork worm.c is stock), conflicted swallow (baby purple worm has AT_BITE only, no AT_ENGL; Conf=0).

- VALIDATED: seed 777 with the fix ran PAST the crash point (epoch ~2310) to epoch 4583+ with ZERO segfaults (previously died there 6/6 runs). Fork working tree = 4 files: src/dogmove.c (fix) + nletypes.h/winrl.cc/pynethack.cc (item-state export). Ready to commit+push to fast-nle fork (like 5678c7a7c) when user wants. Debug build trees (build-asan/build-o0) removed.

## 2026-07-19: find_mac/xkilled crash — DISTINCT from the dog_move wild-read
- SIGSEGV in find_mac() at `int base = mon->data->ac`. Dumped: mon=0x7de65056edd0, mon->data=0x3bba6d0145b741d0 (GARBAGE non-null pointer; nmon looked valid, m_id=267 -> PARTIAL single-field corruption). Path: domove->attack->known_hitum->hmon->hmon_hitmon->xkilled->experience->find_mac = a plain MELEE KILL. NOT the action-expansion (champion shares this path; expansion just happened to reach the state; ~1 crash in 4 runs / ~1.4B steps).
- PROXIMATE CAUSE (confirmed): xkilled() [mon.c] line 64 mondead(mtmp) -- code's OWN comment line 78 "note: mondead can change mtmp->data" and saves mdat -- then line 153 experience(mtmp) re-reads live mtmp->data via find_mac(mtmp) instead of mdat -> derefs invalidated data. Stock NetHack code, latent.
- ULTIMATE ORIGIN NOT traced: why mondead leaves data garbage. NOTE nhfree() calls REAL free() (alloc.c:138) => the old "free is a no-op bump arena" claim (2026-07-07 entry above) is likely STALE; free-then-reuse IS possible now. Could be reuse-after-free OR mondead assigning a bad ptr (revive/newcham/gremlin/golem paths mutate ->data, mon.c:526/532/941/1081). Unconfirmed.
- Reproduced 2x deterministically under gdb: seed 43 --train.ent-coef 0.0026 on the 22-verb expansion build, faults ~301M steps. Method: gdb -batch -ex run -ex bt (libnethack.so has symbols; core_pattern read-only=apport so no core, gdb-run instead). gdb overhead minimal (~390K vs 450K SPS).
- FIX (goldens-gated): experience()/find_mac() use pre-mondead mdat, OR validity-guard mon->data, OR compute XP before mondead(). Low impact: checkpoints every ~16M steps, sweep driver reaps dead children.

2026-07-23 NEW INTERMITTENT SEGV CLASS (post panic-fix, pre-existing across
binaries): ~10-15% of 180M runs die mid-run (aj5bgg5x, ked649r5@32M,
j4lc9n9l@131M on pre-release binaries; release-anchor s43 rfg3l67c@156.9M).
KEY FACT: training is bit-deterministic per seed×binary (twin s44 runs scored
3604.11181640625 identically) => each crash is a DETERMINISTIC REPRO: rerun the
same seed on the same binary under gdb (or with faulthandler + core dumps) and
it faults at the same step. s43 on release tree 82fddbc8 = repro at ~156.9M
(~17 min). dmesg/coredumps unavailable in container; use gdb-wrapped launch.
GDB REPRO RESULT (2026-07-23, s43@156.9M, deterministic ✓): SIGSEGV in engine
kill-XP path: find_mac<-experience<-xkilled<-hmon_hitmon<-attack<-domove.
Faulting insn movsbl 0xb(%rax) = mon->data->ac (permonst.ac @ +0xb) => dead
monster's mtmp->data invalid at XP calc (use-after-free or corruption; hero
melee kill). Other threads healthy — single-env game state, not a race.
Unknown: fork-introduced (arena-free / mmap-ctx / typ-plane suspects) vs stock
3.6.6 bug. NEXT: rebuild libnethack RelWithDebInfo (-g, same -O), rerun repro
with bt full + print *mtmp / *mtmp->data / arena-poison check => file:line +
which pointer rotted. Repro cmd = gdb-wrapped puffer train, seed 43, release
tree 82fddbc8; ~20 min/cycle. Full dump: scratchpad/gdb_s43.log.
ROOT CAUSE 90% LOCALIZED (2026-07-23, debug-symbol gdb repro): victim env
suspended mid-xkilled at the kill-message yield (fog cloud killed from inside,
wasinside=1, nocorpse => spoteffects SKIPPED — only mondead+plines between valid
mdat capture and the fault). mtmp chunk shows glibc TCACHE FREE SIGNATURE:
qword0 == addr>>12 (safe-linked NULL next — mtmp=0x7de5880d7d20 -> 0x7de5880d7
EXACT), qword1 = tcache key; mid-struct fields still intact (mnum=105 ✓ mx/my ✓)
=> chunk free()d, not overwritten. ONLY engine free() of monsters outside
dmonsfree = nle_end truncation-reset teardown (freedynamicdata, nle.c:630).
Same-env reset abandons the coroutine (never resumes) => the resumed victim
must have been freed by ANOTHER env's teardown = the cross-env teardown bug
nle.c:617's anchor comment already half-fixed (nh_cur/current_nle_ctx anchored).
All __thread migrated to ctx (grep clean) => residual shared reachability in
freedynamicdata (suspect: a chain still process-global — audit migrating_mons/
mydogs/timers/lights ownership + add dealloc_monst ownership assert).
NEXT: fork-side audit + assert; crash rate ~10-15%/180M run, PRE-EXISTS release.
Debug build kept at vendor/fast-nle/build-dbg. Dumps: scratchpad/gdb_s43.log,
gdb_s43_dbg.log. Release engine restored + demo seed-7 verified after.
HUNT PAUSED 2026-07-23 (user: too slow). PROGRESS BEYOND ROOT-CAUSE NOTE ABOVE:
(1) dealloc_monst ownership-registry run: ZERO violations yet same-step crash =>
the fatal free does NOT go through dealloc_monst — a stale pointer of some
OTHER type frees the recycled monster chunk. (2) free()-interposer run: mere
LD_PRELOAD shifted heap layout -> glibc "malloc(): unsorted double linked list
corrupted" abort at 13.8M instead => bug fires LAYOUT-DEPENDENT and likely
often/silently; the 156.9M event is just when it lands somewhere fatal.
(3) ASan engine build ready: build-asan/ (RelWithDebInfo + -fsanitize=address
via direct CMAKE_*_FLAGS — the ENABLE_ASAN option is Debug-gated, doesn't
apply); run recipe: swap build-asan/libnethack.so into build/, LD_PRELOAD=
/lib/x86_64-linux-gnu/libasan.so.8 ASAN_OPTIONS="protect_shadow_gap=0:
detect_leaks=0:malloc_context_size=24:abort_on_error=1" puffer train (any
seed; quarantine makes first UAF loud with alloc+free+access stacks — the
free stack names the culprit). Killed after ~4 min; full run needs 40-60 min
unattended — RESUME = overnight/idle ASan run. Instrumentation patch saved:
scratchpad/mreg_instrumentation.patch; build-dbg/ + build-asan/ kept in
vendor/fast-nle. Release .so restored + demo seed-7 verified after.
KILL GOTCHA: pkill -f "puffer train" from a background Bash SELF-MATCHES the
task's own shell cmdline and kills the relaunch too — kill by explicit PIDs.
ASAN PASS 1 (2026-07-24, bank pipeline): CAUGHT heap-UAF at mon.c:2464
(mtmp->mpeaceful in xkilled tail) at THE SAME 157M event under a completely
different heap => bug is TRAJECTORY-DETERMINED (13.8M shim abort reclassified:
shim-induced noise). Freed by SAME THREAD T50 (OMP worker) during the same
kill => the free is INSIDE xkilled's own window. CORRECTIONS: (a) 'nocorpse
skips spoteffects' was WRONG — nocorpse is the kill FLAG, species trait checked
later; fog-cloud kill DOES run spoteffects(TRUE) => free lives inside
spoteffects; (b) mreg run did NOT exonerate dealloc_monst — same-ctx first
frees look legal to the registry; culprit likely a legitimate-looking
dealloc_monst via some spoteffects-reachable path (dmonsfree call sites all
checked: movemon/savelev/bones/wizmakemap/makemaz — none obviously reachable;
needs the backtrace). ASan alloc/free stacks truncated to interceptor frame
(no LTO in build; FP unwind broke anyway) => PASS 2 RUNNING with
fast_unwind_on_malloc=0 malloc_context_size=30 (asan_hunt2.sh, self-restoring)
— same event expected at 157M with full free stack.
BUG FOUND AND FIXED (2026-07-24, ASan pass 2 fast_unwind_on_malloc=0): full
free stack = free<-dealloc_monst<-dmonsfree<-savelev<-goto_level<-deferred_goto
<-level_tele<-level_tele_trap<-dotrap<-spoteffects<-xkilled. STORY: hero kills
engulfer THAT SITS ON A LEVEL-TELEPORT TRAP; spoteffects lands hero on trap;
level_tele's immediate deferred_goto (stock scroll-naming workaround,
teleport.c ~1025 "can't defer until end of turn") executes goto_level->savelev
->dmonsfree freeing the whole level incl. the monster xkilled still holds;
xkilled tail (mpeaceful read, experience->find_mac) = UAF. STOCK 3.6.6 BUG.
FIX (fork commit pending): program_state.in_killer_spoteffects (new per-ctx
field, decl.h) set around xkilled's spoteffects(TRUE) call (mon.c); level_tele
skips the immediate deferred_goto when set (teleport.c) -> change executes at
moveloop's u.utotype check, same semantics as the existing mon_moving deferral.
domagicportal/trapdoor paths already defer-only (checked). GATES: goldens
34/34 identical, no-globals OK, env fingerprint 71021f6ac6b5864a unchanged,
demo seed-7 reproduces; proof run rel180_s43_fixed in flight (expect it to
pass 156.9M and finish). NOTE: fixed engine = new binary => future scores
re-roll vs the release-bank numbers (cross-stack doctrine).
PROOF + COMMIT (2026-07-24): rel180_s43_fixed completed full 179.4M (score
3442.9) through the 4x-fatal 156.9M event => fix verified end-to-end. Fork commit 76f699e1c (user-authored, no trailer), PUSHED to origin 2026-07-24
(push worked from session this time — live VS Code helper).
The intermittent-crash class that killed ~15% of long runs all campaign is
CLOSED (any distinct future crash = new investigation). build-dbg/ and
build-asan/ kept in vendor/fast-nle for future hunts.
FIX VALIDATION COMPLETE (2026-07-24, fix180 batch, user capped at 4 seeds):
s43 3442.9 completes (was deterministic crash), s44/s45/s46 = 3842.6/3868.4/
3202.6 BIT-IDENTICAL to pre-fix runs => fix provably no-op outside the bug
state. Fork pushed (76f699e1c = origin/main). Crash chapter CLOSED.
SECOND UAF FIXED (2026-07-24, fork commit 21e7e0b53, pushed): shapeshifter
expel variant of the teleport UAF. newcham->expels (engulfing shapeshifter
changes form) calls spoteffects(TRUE) -> level-tele trap -> level_tele
immediate deferred_goto -> savelev/dmonsfree frees mtmp that expels/newcham
still ref. ASan heap-UAF mhitu.c:259. FIX generalized the 76f699e1c guard:
program_state.in_killer_spoteffects RENAMED in_mon_spoteffects, now set around
BOTH monster-context spoteffects (mon.c xkilled + mhitu.c expels); level_tele
defers when set. Found via CAST-verb A/B crash (cast336_s43 segv@48M, 2.4min
= cheapest engine repro yet; crash UNRELATED to cast). Gates: goldens 34/34,
no-globals, seed-43 cast-arch proof ran clean 60M (was crash@48M). LESSON:
the teleport-UAF has a FAMILY of triggers (every monster-context spoteffects
with live mtmp) — audited all 22 spoteffects sites; the 2 monster-context ones
(xkilled, expels) are now both guarded; rest are hero-context (u.utotype
handled normally). ASan/dbg builds kept in vendor/fast-nle for future hunts.

2026-07-25 THIRD-CRASH HUNT SET UP, DEFERRED TO OVERNIGHT (user cancelled the
~5h run). Bug: etc1B_s46 real segv @925M (was tracking ~5800). Resume-from-
checkpoint hunt ABANDONED (user correct: resume re-seeds envs -> does NOT replay
the deterministic trajectory -> gambles on the recurring class; 112M deep play
no-catch showed it's not frequent enough). CORRECT METHOD = seed-46 from scratch
under ASan (deterministic -> guaranteed catch at ~925M). READY TO RELAUNCH:
bash scratchpad/crashhunt2.sh (seed 46, total-timesteps 1B, ASan engine build-
asan swapped into build/libnethack.so, full unwind opts, self-restores release
after). ~5h (SPS 66K early dropping to ~30-40K deep). ASan engine rebuilt from
current source 21e7e0b53 (both prior UAF fixes in) so this targets a 3rd bug.
Release engine restored + demo verified after cancel; box clean. build-asan &
release backup (scratchpad/libnethack.so.release.crashhunt) kept.
