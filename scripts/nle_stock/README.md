# Stock-NLE bridge and NetHackChallenge-v0 binding

Runs the PufferLib NetHack policy on **unmodified stock NLE**, and on the real
`NetHackChallenge-v0` gym environment, so results can be claimed against agents
scored on the competition interface.

## The ladder

| rung | engine | fork-only hooks | options | seedable |
|---|---|---|---|---|
| 1 fork | vendor `fast-nle`, linked | read engine memory | ours | yes |
| 2 fork + derive harness | fork engine | both, side by side | ours | yes |
| 3 stock C backend | stock `libnethack.so`, dlopened per env | reconstructed | ours | yes |
| 4 python binding | stock NLE inside `NetHackChallenge-v0` | reconstructed | NLE's | no |

Every rung presents NLE's own C API (`nle_start` / `nle_step` / `nle_obs_refresh` /
`nle_end` plus the fork introspection hooks), so the env, observation packer,
action masks and policy above them are identical in all four.

## Files

- `nh_derive.h` — the reconstruction. Rebuilds every fork-only hook (shop price,
  terrain underfoot, peacefulness, spells, weight, intrinsics, containers, food)
  from stock's public observation using probe keystrokes. `nh_tables.h` holds the
  static object/glyph tables.
- `nh_stock_backend.c` — rung 3. dlopens a private memfd copy of stock
  `libnethack.so` per env. Carries the switch panel below.
- `nh_gym_backend.c` + `nh_gym_runner.c` — rung 4, built into `libnhagent.so`.
  Engine transport is a callback into Python; every keystroke, policy action and
  reconstruction probe alike, is one counted `env.step()`.
- `nhc_agent.py` — the challenge driver. Wraps the env in `OnlyResetStep`, which
  raises on any access other than `reset`/`step`, so conformance is checkable
  rather than asserted. `nhc_direct.py` drives `nle.nethack.Nethack` directly with
  raw keys, for equivalence testing.
- `fixclock.c` — `LD_PRELOAD` freezing `time()`/`localtime()`. NetHack consults the
  real clock (moon phase, night, Friday 13th, `u.ubirthday`); the fork and the C
  backend fake it, NLE does not, so scored challenge runs are irreproducible by
  construction and pinning the clock is what makes replay possible.

## Switch panel (`nh_stock_backend.c`)

Makes rung 3 imitate rung 4 exactly. `NH_STOCK_`: `STRICT` (1e6 step cap +
10,000 no-progress abort, probes charged to both), `LITERALOPTS` (NLE's literal
option string instead of an rc file), `NOSDESC`, `NOREDRAW`, `STOCKSORT`,
`NODARKFIX`, `NOTOPL`, `REALCLOCK`, `FIXEDCLOCK`, `FORCESEED`, `SIMPLELOG`,
plus `TERRAIN_PROBE`, `STALLCAP`, `CLEAREOS`.

## Gotchas that cost real time

- **Link the worktree's `libnethack.so`, not the main tree's.** A mismatched engine
  gives blank observations, every step terminal, and a score of exactly 0. Check
  with `ldd`.
- **`ulimit -n 65536`** before any run with many envs: each dlopens a private memfd.
- **Dungeon seeds differ by path.** `init()` sets `seed = 0xCAFEBEEF + env->rng`,
  and `rng` is the *env index* in the vec path but `rand()` in the demo path. Two
  paths therefore play different dungeons. Per-episode score SD is ~13,600, so an
  unpaired n=200 comparison can only resolve ~24% of the mean — pair on the seed.
- **`--base.seed` must be in the eval arguments**, not just the run name, or arms
  replay identical games.
- Comparing arms with different completed-episode counts biases the slower one
  down hard; restrict every worker to the same k.
- `NH_MULTI=1` for all 13 roles in the CPU binaries; they default to Monk only.

## Diagnostics

`nh_encdiff` / `nh_taildiff` / `nh_grudiff` (stage-by-stage CPU-vs-CUDA diffs),
`nh_agree` / `nh_allheads` (per-head argmax agreement against a logged trajectory),
`nh_trace2` (hidden-state traces), `nh_cpu_fork` (CPU policy on the fork engine).
