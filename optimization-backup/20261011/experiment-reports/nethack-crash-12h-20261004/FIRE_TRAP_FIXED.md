# NetHack training crash: reproduced cause and isolated fix

Completed 2026-10-04 23:03 UTC. The minimal game fix is `fire-trap-hpmax.patch`, applied in this experiment's `source/src/trap.c` and built as `build/libnethack.so`. No production PufferLib files were changed.

## Cause

In `mintrap()`'s fire-trap branch, `thitm()` can kill and life-save a monster, leaving it at positive HP. The following `mhpmax -= rn2(num + 1)` can then make maximum HP negative. On level catch-up, HP is capped to that negative maximum. `dmonsfree()` frees the monster while its level map still points to it. Later allocations can reuse the freed block for another game's live monster; the stale map entry then passes the foreign pointer to combat code.

## Direct evidence

- Unpatched saved B trace: GDB observed monster id 71 maximum HP change 1 -> -5 at turn 910 (`replay-b-watch71.gdb.log`), then free at turn 7941 while B's map (24,17) still held the pointer (`replay-free71.gdb.log`, `replay-b-free-index.log`). CPU replay later panicked on that freed map pointer (`replay-b-lookupcheck.log`).
- The existing instrumented GPU job stopped at `OWNER_BHIT_LOOKUP` around 530M steps. Immediately after B's `m_at(24,17)`, its map returned A's live id 130 pointer; B's context pair was consistent. See `/puffertank/experiments/nethack-crash-lookupcheck-exact-20261004/training.log` line 54793. Its supervisor status is `finished`, and the verified PIDs are gone.
- Focused two-game CPU replay (`replay_pair.c`) reproduced the allocator alias with all unpatched trace digests matching to the relevant events: A's newly allocated pointer and B's stale map pointer were both `0x650ae2e47df0` (`replay-pair-compare.log`). The patched schedule had distinct A and B pointers (`0x5eb053446800` and `0x5eb0534488c0`, `replay-pair-compare-patched.log`).

## Fix and verification

- The patch preserves the same random draw and clamps post-fire maximum HP to at least current HP. GDB shows B's life-saved id 71 remains at HP/max HP 1/1 at turn 910 (`replay-b-patch-verify.log`).
- Patched CPU replay of the latest live B trace traversed all 2805 recorded events without panic or grid-integrity assertion (`replay-b-latest-patched.log`). Its first digest difference is event 2690, turn 7941, precisely where the monster that was formerly freed now survives; subsequent recorded keys follow a different trajectory. This is expected and is not counted as a golden pass.
- Nineteen stable stock goldens passed paired, alternating, thread-shuffled multi-game replay with the patch (`shuffled-patched.log`). The same 15 other stock goldens mismatched with both unpatched and patched libraries (`golden-unpatched.log`, `golden.log`).

This evidence fixes the reproduced fire-trap/map use-after-free and the observed cross-game pointer incident. The older `attack_checks` SIGSEGV had a stale-pointer signature at the same training step range, but its saved trace ends at turn 3302 while the fault was at turn 11988, so that exact fault cannot be replayed from the trace. No patched 1B GPU run was started, in keeping with the requested test strategy. These results do not rule out unrelated crashes.
