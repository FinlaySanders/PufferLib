---
name: nethack-challenge-binding
description: "The real NetHackChallenge-v0 binding: architecture, the four bugs found by building it, and what the challenge interface costs us"
metadata:
  type: project
---

2026-09-11: the policy now runs on the genuine `NetHackChallenge-v0` gym environment, not just on our own stock-NLE harness. Built in the scratchpad as `nle_stock/nh_gym_backend.c` + `nh_gym_runner.c` -> `libnhagent.so`, driven by `nle_stock/nhc_agent.py`. Build with `nle_stock/build_gym.sh` (compiles from the `wt_gate` worktree, so it picks up the pending obs changes).

**Why:** the claim against AutoAscend is only meaningful on the interface AutoAscend was scored on. Our stock harness dlopens libnethack.so itself; the challenge env does not let you do that, and building the real thing exposed four defects that the harness hid.

**Architecture.** The fork env already talks to the engine only through NLE's own C API (`nle_start/nle_step/nle_obs_refresh/nle_end` plus fork-only introspection hooks). So the binding is a sibling of `nh_stock_backend.c`: same file shape, but the engine transport is a callback into Python instead of a dlopened library. Python owns `gym.make('NetHackChallenge-v0')` and does nothing but `reset()` and `step()`; C asks for a key, Python steps the env and copies the observation back through `nhg_fill()`. Probe keystrokes and policy keystrokes go through the identical path, so the challenge counts them all. The policy is the CPU forward pass in `ocean/nethack/nethack.c` (`nethack_net_forward` + `demo_step_once`), not the CUDA trainer.

**What building it found** (all four were invisible to the stock harness):
1. **Identity was always Archeologist.** NLE's gym `reset()` (nle/env/base.py) presses SPACE up to 1000 times until `_in_moveloop`, which dismisses the "You are a neutral female human Valkyrie" welcome line before the first observation is returned. `dr_identity_from_text` therefore found nothing and fell through to role 0 / race 0. This is NOT a `nolegacy` effect: our own rc sets nolegacy too and still shows the line, because our C backend returns the very first observation instead of stepping past it. Fixed with `dr_identity_probe()`: send `^X` (Command.ATTRIBUTES, in the published action set, costs zero game time), parse "a level 1 female human Rogue" and "You are chaotic,", then ESC the paged window.
2. **Enter was being dropped.** The challenge action set carries Enter only as carriage return (13); our macros emit newline (10). Unmapped keys were falling back to ESC, ~550 times an episode, cancelling prompts. Now aliased 10 -> 13.
3. **Episodes were truncated at 1000 keys.** `NH_STOCK_STALLCAP` defaults to 1000; the certs set it to 1e6 and the binding did not. Under the challenge the environment owns the no-progress rule (10,000 steps), so we must not pre-empt it.
4. **`NH_STOCK_TERRAIN_PROBE` was off**, where the certs set it on.

**What the challenge interface costs.** `NetHackChallenge-v0` refuses `seed()` by design ("NetHackChallenge doesn't allow seed changes"), so the bit-exact replay parity test cannot be run through it; parity stays measurable only on the seedable stock harness. Three engine-memory crutches the stock backend uses are unreachable here: the clear-to-end-of-screen capability (`NH_STOCK_CLEAREOS`, which the cert scripts DO set), turning `dark_room` off during probes, and restoring the engine's `toplines` across a probe group (the binding restores only the observation copy). `NH_STOCK_NODARKFIX` / `NH_STOCK_NOTOPL` were added to `nh_stock_backend.c` to price the last two on the replay corpus.

**Probe budget.** The reconstruction costs about 10-14 env steps per policy step (roughly 12 probes). That is charged against the challenge's 1e6 step cap (not binding: long games use ~50K) and, more importantly, against the 10,000-step no-progress abort, which it makes about 12x more aggressive in policy-step terms. Observed max no-progress runs are 12-31, so it is not biting yet, but it is the thing to watch if wedges return.

**How to apply:** run `nle_stock/gym_batch.sh` (W workers x EPS episodes -> jsonl) and `nle_stock/gym_analyze.py <dir>`. The driver wraps the env in `OnlyResetStep`, which raises on any access other than reset/step, so conformance is checkable rather than asserted. Scores come from the challenge env's own blstats (last live reading; NLE blanks blstats on the terminal step), not from our bookkeeping. Related: [[nethack-stock-nle-bridge]], [[nethack-cert-protocol]], [[nethack-pending-obs-changes]].


## 2026-09-11 — cross-backend determinism PROVEN, and the difference list is complete

The challenge env blocks seeding only by monkeypatching three methods on its Nethack object (`nle/env/tasks.py`); `env.unwrapped.nethack._pynethack.set_initial_seeds()` still works. Instrumentation only; scored runs stay unseeded.

**Self-determinism.** Under the real clock the binding reproduces some games and not others (seed 4242 identical across 4 runs, 2386 keys; seed 4243 differed in all 4). Freezing `time()`/`localtime()` with an LD_PRELOAD (`nle_stock/fixclock.so`) makes every episode reproduce. Cause: NetHack reads the real clock for moon phase, night, Friday 13th and `u.ubirthday`; the fork and `nh_stock_backend.c` both fake it (GOT redirection, "deterministic under everything"), NLE does not.

**Cross-backend.** `nle_stock/nhc_direct.py` drives `nle.nethack.Nethack` directly (raw keys, no gym wrapper) and `nle_stock/nh_cpu_stock` runs the same CPU policy on the C backend. With every difference pinned, one seeded episode gave: **4297 keys IDENTICAL**, and over 1440 boundaries blstats / glyphs / inv / inv_state / inv_true / misc **0 mismatches**; message 1 mismatch (boundary 0 only); internal 100% (that is `internal[7]`, which the challenge does not export and which the worktree policy no longer reads since the hunger gate moved to `blstats`). Residual: the Python side sends one extra Enter at episode start because the first observation's prompt state differs.

**The complete difference list** (each now a switch): wall clock `NH_STOCK_FIXEDCLOCK`; option string as a literal instead of an rc file `NH_STOCK_LITERALOPTS`; screen_descriptions + rawout `NH_STOCK_NOSDESC`; print_glyph redraw hook `NH_STOCK_NOREDRAW`; room-sort total order `NH_STOCK_STOCKSORT`; dark_room poke `NH_STOCK_NODARKFIX`; engine toplines restore `NH_STOCK_NOTOPL`; seed `NH_STOCK_FORCESEED`; same libnethack build and hackdir (`/puffertank/nle-stock/nle/`); same policy implementation on both sides; identity probe conditional on the welcome line.

**Crutch pricing** (532-game replay corpus, exact matches): control 332/529, no dark_room 333/529, no toplines 330/532. Both crutches are worth nothing, so the binding loses no fidelity by lacking them.


## 2026-09-11 13:15 — reset bug found and fixed; backends now identical across episodes

`nh_gym_backend.c` kept one static `GInst` and cleared only the fields that looked per-episode on reset. `nh_stock_backend.c` `calloc`s a fresh `Inst` for every episode, so nothing survives there. The saved top line + probe mark, the virtual --More-- text, the raw channel buffers and the bound DObs pointers were all carrying over, and every episode after the first played differently from the same game started fresh. Fix: memset the whole struct at `nle_start`, preserving only the finished-episode counters and `ep`.

**Verification (pinned config: frozen clock, `NH_PIN_RAND`, literal options, no sdesc, no redraw hook, stock sort, crutches off, same libnethack):** three consecutive Python episodes on seed 777 each give 11908 keys, md5 827feaa03e81 — byte-identical to the C backend's three identical episodes. The two backends are the same machine across episodes, not just on the first.

**How it was isolated, and two false starts worth remembering.** (1) Comparing two identically-seeded episodes does NOT test for leaks by itself: the policy samples from libc `rand()`, a stream shared across episodes. Pin it (`ctypes.CDLL(None).srand(0)` at reset, `NH_PIN_RAND` in `nh_cpu_fork.c`). (2) A truncated keylog from a timeout looks exactly like a divergence — check for EOF before concluding. (3) Spearman(index, score) over episodes pooled across workers treats clustered data as independent and inflates z by ~sqrt(cluster size); use one vote per worker.

**Measurement traps hit repeatedly in this session:** comparing arms with different numbers of completed episodes per worker biases the slower arm down badly (episode length correlates with score) — always restrict every worker to the same k. And `nh_cpu_fork`/`nh_cpu_stock` default to `name:Agent-mon-hum-neu-mal`, i.e. **Monk only**; the challenge randomises all 13 roles. Set `NH_MULTI=1`. Per-role medians span ~950 (Healer) to ~24000 (Rogue), so a Monk baseline is not a baseline.

**Paired fork vs stock, all roles, same seeds, NLE options (CPU policy both sides):** at n=191 fork higher in 113 pairs, p = 0.014 — the reconstruction DOES cost something. The cleaner number is the CUDA certs: fork 9,448 vs stock 8,136 median (14k episodes, all roles), about 14%. An earlier n=48 reading (p=0.19) was quoted as 'free'; it was not.

**Throughput (why certs run on the C backend):** python binding 264 eps/hour on 16 procs; stock C backend CPU 395 eps/hour on 8 procs; box vec cert 512 agents ~1530 eps/hour per GPU. The determinism result is what licenses certifying on C and validating with a smaller binding sample.


## 2026-09-11 14:30 — CPU forward pass is materially weaker than the CUDA policy (OPEN)

Same weights (2B champion), NLE options, all roles, 200 eps each: fork+CUDA mean 14,365; fork+CPU port mean 6,141 (median 2,026). This, not the reconstruction, is why the Python binding scores low: `libnhagent.so` runs the demo's CPU port (`ocean/nethack/nethack.c`), the certs run CUDA. Ruled out with evidence: checkpoint misalignment (consumption lands exactly on the file, padding after the 12-elem pointer-head tensor is in the file), missing blocks, activation mismatch (both ReLU), sampling (both softmax; CUDA adds a 0.01 verb ε-floor). Live: precision — CUDA runs `__nv_bfloat16` activations (no `-DPRECISION_FLOAT`), the port is fp32. Rounding the port's layer outputs to bf16 (`-DDEMO_BF16`, `nh_cpu_fork_bf16`) lifts it to median 6,569 / mean 10,415 at n=68 but paired p=0.22 and it is still below CUDA, so precision is at most part of the answer. The `-DPRECISION_FLOAT` CUDA build is bitrotted (scores 0, prays and dies) so the reverse test is unavailable. Consequence: the binding validates conformance only, NOT the cert number, until this is resolved. The public demo runs this same CPU path.


## 2026-09-11 19:20 — the low rung-4 medians were a cross-episode ratchet, not the CPU port or the reconstruction

Every multi-episode rung-4 batch (`pkgnle`, `pkgours`, `run4`, `fixed_pkgnle`: 187–320 eps) had episode-1 medians of 6.5–11K (= rung 3) and episodes-2+ medians of ~1.4K, decaying with index; 14/16 workers in the 320-ep batch collapse permanently. `single` (one episode per process) gave 7,210 = rung 3. **Cause:** `cant_hold` (nethack.h) is set from the handless-polymorph refusal message and cleared only by "You return to…"; `nethack_do_reset` never cleared it, so a hero dying polymorphed masked WIELD/THROW/ENGRAVE for every later game in the process. `wt_gate` had the same omission, so every CPU-path multi-episode number before 2026-09-11 19:10 is invalid (box vec certs unaffected: no `cant_hold` there). Fixed with `env->cant_hold = 0` in `nethack_do_reset`; confirmation batch `results/gym/fixed_reset_pkgnle` (16×20) running. The 14:30 "CPU forward pass is materially weaker" entry above is therefore superseded: the CPU port was later verified faithful on matched seeds, and the remaining rung-4 deficit was this ratchet.

**Why the earlier verification missed it:** the byte-identical-episodes check ran `nhc_direct.py`, which calls `nhg_zero_state()` + `srand(0)` at every reset and bypasses the gym env; production `nhc_agent.py` does neither. Verify on the driver that produces the numbers. **Analyzer traps fixed in `gym_analyze.py`:** `plen` is cumulative per worker (ratios need deltas); pooled samples taken mid-run over-represent short games (use equal-k per worker); always print episode-1 vs episodes-2+ medians — a gap there is a state leak.
