---
name: pufferl-off-limits
description: "Never edit pufferlib/pufferl.py (train-side, owned by the other person) — reverted twice on user instruction"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-07-23T18:51:00.880Z
---

pufferlib/pufferl.py is off-limits: it is train-side shared infra owned by the
rollout/train person, not part of the nethack env scope.

**Why:** Two incidents. (1) Patched it chasing a wandb "config bug" that was
actually paginated-API behavior — user: "you should not change pufferl.py",
reverted byte-identical. (2) 2026-07-23 release audit found +51 committed lines
(sweep hardening: dead-run detection, cpu_affinity, num_buffers clamp,
target_key metric fix) — user: "we cannot change pufferl", reverted to the 4.0
merge-base version. Patch saved: scratchpad/pufferl_sweep_hardening.patch
(useful fixes; offer to the train-side owner instead). Consequence of revert:
sweeps from this tree hang on dead runs and hardcode env/score as the metric —
accepted.

**How to apply:** Treat ALL shared train infra as read-only: pufferl.py,
src/vecenv.h, config/default.ini, pufferlib/sweep.py (user 2026-07-23: "all
those cannot be changed"). All four reverted to the 4.0 merge-base; fixes live
as scratchpad patches to hand to the owner: pufferl_sweep_hardening.patch,
vecenv_guided.patch (schedule guided +15% hybrid cores + NUM_ATNS assert),
default_ini_sweep_pins.patch (arch/horizon sweep pins), sweep_py_match_keys
.patch, vecprof.patch. Consequences accepted: static schedule (slower rollout
on 14900K), sweeps re-expose arch dims + env/score metric + can hang on dead
runs. The env's shared-file footprint must stay: build.sh case, ocean.cu
registration, models/pufferlib.cu activation_size hook, .gitignore vendor
lines — those are required plumbing, approved implicitly by the release audit.
Related: [[nethack-sps-campaign]] (vecprof patch), [[nethack-crash-hardening]].

**EXCEPTION (2026-08-08, user-granted):** sections commented as experimental
Nethack-only features ARE editable — src/algo.cu has the marked block (consumed-
head gating ~1349, verb-eps floor ~1385, and now PUFFER_ENT_VERB_ONLY verb-only
entropy). Everything else in pufferl.cu/algo.cu stays off-limits.

- Trainer reward clamp: src/pufferl.cu train_epoch_gpu clamps ALL rewards to [-1,1] (clamp_precision_kernel) before training, unconditionally. Any env reward or terminal penalty beyond that is silently capped. Found 2026-09-07 via the drone oob_penalty ladder (see [[drone-web-demo-rng]]).
