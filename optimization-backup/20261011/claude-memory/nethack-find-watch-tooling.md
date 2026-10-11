---
name: nethack-find-watch-tooling
description: 2026-09-13 working "find good runs in the vec eval, then watch one by skipping to it" tooling (puffer_find, NH_EPLOG env/ordinal addressing, NH_WATCH_ENV/EP); render-mode verb_eps=1 gotcha
metadata:
  type: project
---

Working since 2026-09-13 (user asked for the vec-eval find -> skip-to-episode watch workflow, video deferred).
Tooling lives in scripts/nle_stock/watch/ (untracked): find_watch_tooling.patch (nethack.h hook + the demo's composite
renderer extracted from nethack.c into ocean/nethack/nethack_view.h, shared by demo and watch hook; demo output verified
byte-identical after the extraction; nethack_view.h is intent-to-add in git),
env-var gated, NOT committed - `git diff ocean/nethack/nethack.h` shows it applied), nh_find.sh / nh_rank.sh /
nh_watch.sh, README. Binary ./puffer_find (built via `./build.sh nethack puffer_find`; ./puffer untouched).

- NH_EPLOG line = `env ep score how time role race gender max_depth last_turn`; episodes addressed as (env index, per-env
  ordinal). Two runs of `--vec.num_buffers=1 --base.async=0` are byte-identical (verified 155 eps).
- NH_WATCH_ENV/NH_WATCH_EP draw that one episode from inside the headless eval (puf_step hook) with the demo's composite
  view (~125x48 terminal); colour/inv-string sinks are bound only on the watched env (shared buffers, 128 envs); NH_WATCH_MS pacing,
  NH_WATCH_STOP exits at its end. Verified: env 18 ep 1 (64 agents, seed 73) replays to the logged 42443 / Dlvl 9 exactly; env 111 ep 8 (128 agents) also exact after skipping 7 episodes (116 s).
- agents + seed must match between find and watch runs.
- Vec eval is fast: 64 envs, 155 episodes (incl. 80K-turn games) in 13 s.

**Why:** `./puffer eval` render mode is unusable for nethack: eval_make sets train.verb_eps=1 and nethack_policy.cu reads
that as the literal epsilon -> uniform random verbs; render also forces 1 env. That's pufferl.cu (off-limits), so the
watch is done inside the env instead. The ./nethack demo can't replay vec episodes (different RNG streams: C rand vs Philox).

**How to apply:** for "show me a great game": nh_find -> nh_rank -> nh_watch with the same agents/seed. Prefer low
ordinals (replay reaches them fast). Related: [[nethack-handoff-2026-09-12]], [[vec-backend-for-big-evals]], [[pufferl-off-limits]].

**Candidates (fixed 4B s705, 128 agents, seed 73, log scripts/nle_stock/watch/find_128agents_seed73.ep, 3011 eps):**
rich+deep: env72 ep18 165,063/Dlvl10; env113 ep20 90,898/Dlvl11; env111 ep8 86,780/Dlvl11 (replay-verified); env30 ep20
61,722/Dlvl12; env70 ep4 66,424/Dlvl11 (low ordinal = fast to reach). Deepest env66 ep5 Dlvl13 (18,642). Top score env15
ep14 284,760 at Dlvl4 (shallow farm). Replay must run the batch through the earlier episodes: ~10 s per ordinal unpaced.

**2026-09-13 later: instant replay via action log (supersedes the slow vec re-run for watching).** NH_ACTLOG=<dir> in the
find pass records (verb, slot, dir) 3 bytes/step per env (env<j>.act); eplog gained `steps act_off` (cols 11-12).
`nh_replay.sh <eplog> <env> <ep> [ms]` runs ./nethack in NH_REPLAY_* mode: env_open, rng=j, seed=0xCAFEBEEF+j,
nethack_do_reset K times (episode K's seed = LCG^K), then feeds the recorded actions through the same puf_step; the
in-step hook draws the composite view (nethack_watch_quiet while skipping). Verified: replay's own eplog line (cols 1-11; act_off differs by construction) identical to the find line for
env18 ep1 and env25 ep4 of the 64-agent seed-73 run, ~1 s each. nh_replay.sh prints FAITHFUL/MISMATCH itself. NH_MULTI=1 must match the eval's multi_role=1.
Rendering (chars/colors/inv_strs bindings) is RNG-neutral (display RNG) - replays with them bound reproduce exactly.

**PAUSED 2026-09-13 ~16:20 (user: "we'll come back to this").** Tree restored to 78f446fe for ocean/nethack; ./nethack
rebuilt clean; ./puffer_find binary left in place (has recorder). Code saved in git `stash@{0}` ("nethack find/watch
tooling ...", includes untracked nethack_view.h via -u) AND scripts/nle_stock/watch/ (find_watch_tooling.patch 797 lines,
nethack_view.h copy, nh_find/nh_rank/nh_replay/nh_watch.sh, README, ranking logs find_128agents_seed73.ep and
find_512agents_seed73_10k.ep). Actions for the 10K run: /tmp/reg/vid/deep10k.ep.acts (152 MB, /tmp only).
Resume: `git stash apply stash@{0}` (or `git apply scripts/nle_stock/watch/find_watch_tooling.patch`), then
`./build.sh nethack --cpu` and `./build.sh nethack puffer_find`.
10K/512/seed73 results: deepest Dlvl 14 (env237 ep3, 53,700; replays only via vec path - demo replay diverges late,
the one known case), Dlvl 13 x1, 12 x13, 11 x30, 10 x40; no Dlvl 25+. Rich+deep: env273 ep19 208,389/Dlvl11 (30K steps),
env216 ep10 201,672/Dlvl11, env38 ep21 138,641/Dlvl12, env489 ep4 136,000/Dlvl11.
OPEN: 1/18 sampled episodes (env237 ep3) does not reproduce alone in the demo but does in the 512-env vec re-run ->
some engine state carried across games within the vec process (per-thread?), rare. Demo trace of the divergent replay:
/tmp/reg/vid/trace_demo_237_3.txt (dies at step 6615, T 41304, Dlvl 13, vs original 6660 steps / T 42117).
