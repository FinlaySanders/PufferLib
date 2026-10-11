# NetHack observed training crash: isolated fix verified

Completed 2026-10-05 08:58 UTC. The minimal gameplay fix is
`fire-trap-hpmax.patch`, applied to this experiment's `source/src/trap.c` and
built in `build/libnethack.so` (SHA-256
`94247c31e88d468953d276ccaea18d1f1e9f2fefd7e6e15c14de22759bf51402`).
No production PufferLib files were modified, and no PR or push was made.

## Cause and crash evidence

`thitm()` can kill and life-save a monster during a fire trap. The old code
then lowered its maximum HP below its restored positive HP, sometimes below
zero. Level catch-up later capped HP to that negative maximum and
`dmonsfree()` freed the monster while the level's monster map still pointed to
it. A later allocation could reuse the block for another game's monster;
map lookups then returned a stale or foreign pointer.

- The saved B-game trace reproduces the invalid maximum HP and the subsequent
  free while B's map still holds the block. See `replay-b-watch71.gdb.log`,
  `replay-free71.gdb.log`, and `replay-b-free-index.log`.
- The original `attack_checks()` SIGSEGV was at `attack_checks+308`, where it
  dereferenced a noncanonical `mtmp->data` pointer. A focused CPU harness,
  `replay_stale_attack.c`, replays B's **hashed** saved trace through the map
  free and reaches that same instruction and signal with the freed block's
  noncanonical data word (`replay-stale-attack-baseline.gdb.log`).
- The live lookupcheck job found B's `m_at(24,17)` returning A's live monster
  pointer; focused paired CPU replay reproduced allocator reuse at the same
  stale map address (`replay-pair-compare.log`).

## Fix and verification

The patch retains the `rn2(num + 1)` draw and clamps post-fire maximum HP to
at least current HP after `thitm()` returns false. In the focused patched B
replay, the affected map cell holds a live monster with valid data and positive
HP (`replay-stale-attack-patched.log`). The patched replay traverses all 2805
saved B actions without panic or map-integrity assertion. Its first digest
divergence is at event 2690, when the formerly freed monster survives; later
recorded actions follow a changed trajectory.

The sole capped patched training run, seeded as the historical failure run,
reached its 560M-step target and exited normally. The previous observed
failures were near 530M. No `GRID_*`, `INVALID_ATTACK_MONSTER`, `OWNER_*`,
signal, assertion, or panic diagnostic appeared in
`/puffertank/experiments/nethack-crash-patched-targeted-20261005/training.log`.
The Python supervisor ended during the 90-minute Codex session rollover, so
its `STATUS.json` is stale; GDB's log records the inferior's normal exit.
GDB's subsequent `No stack` came from its unconditional post-run backtrace
command. The supervisor, GDB, and training PIDs are gone, and no GPU compute
process remains.

All 19 stable stock goldens pass paired, interleaved, thread-shuffled replay
with the patch (`shuffled-patched.log`). The other 15 stock goldens mismatch
identically with patched and unpatched libraries (`golden.log` and
`golden-unpatched.log` are byte-for-byte identical).

The original older A-game trace has no state hashes and ends before the
faulting turn, so the exact freed allocation at that historical SIGSEGV is
not directly proven. The matching instruction-level CPU reproduction, the
stale-map causal chain, and the completed patched stress run support this fix
for the observed failure mode. They do not rule out unrelated future crashes.
