---
name: nethack-determinism-gate
description: Reusable NetHack training determinism gate (2M steps, seed 42) with its reference checkpoint hash; the shipped async+4-buffer config is NOT bit-reproducible, async=0 or num_buffers=1 is
metadata:
  type: project
---

2026-09-07. Gate script: scratchpad prof/det_gate.sh (copy in the gate worktree scratchpad/wt_gate, a clean 97416d02 checkout with fast-nle cloned at 1d7ab70 and both built). It trains 2M steps (1,966,080 realised) at seed 42 with `--base.async=0 --vec.num_buffers=1 --base.eval_episodes=256`, then sha256s the final checkpoint. Reference (97416d02 env/trainer + engine 1d7ab70): weights `89c6f91689be3ad7`, score 28.8. Env vars: GATE_BIN (default ./puffer), GATE_ROOT, GATE_GPU, GATE_REF, NETHACKDIR. ~12 s per run on the 4090. Thread count does not change the hash; async=1 alone gives 2d528e5dd000881a (num_buffers=1), async=0 with 4 buffers gives 684644f47d6d6724 — each setting is self-consistent, but the SHIPPED config (async=1, num_buffers=4) is NOT reproducible run-to-run (race in the multi-buffer async pipeline). The main working tree as of 09-07 10:00 (uncommitted speed-campaign instrumentation in nethack.h/.c/macros.h, pufferl.cu sched defines, local engine "tmp" state built 09-02) PASSES the gate (same hash), so those edits are training-bit-exact.

**Why:** the release cleanup (rebase, dropping instrumentation, pinning the engine) must not change training; a 12-second gate catches any drift.
**How to apply:** run `prof/det_gate.sh <id>` from the repo root after every cleanup step; a FAIL means the step changed numerics. Record any intentional numerics change by updating GATE_REF with justification. Related: [[nethack-5.0-scaling]], [[nethack-engine-bugs]].

2026-09-07: release cleanup commit 452c13a7 (post-merge c2a907a3) passes the gate: hash 89c6f91689be3ad7, 18 s wall for the whole 2M-step run. Build the gate binary with `./build.sh nethack puffer_gate` (OUT arg) so the tracked ./puffer binary is never overwritten.

2026-09-07: RELEASE BRANCH 5.0-nethack-release = upstream/5.0 tip 7369a63b + single commit d90ebdb3 "release" (13 files, no weights file: upstream 71373354 removed all policy weights from the repo; resources/**/*weights*.bin is gitignored, weights live in the website repo docs/assets/models). Gate PASS 89c6f91689be3ad7 on that branch, so upstream's pufferl.cu/pufferenv.h changes since cfc2d05f did not change NetHack numerics. Old 12-commit history stays on local 5.0-nethack (452c13a7).
