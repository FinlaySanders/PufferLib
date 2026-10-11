# Seed-2907 patched 1B stress run

The trainer exited normally with code 0 at 2026-10-05 21:07:10 UTC, after its dashboard reached 999.8M steps and zero time remaining. The final checkpoint is `checkpoints/nethack/patched_s2907_r2/0000000999817216.bin`. The log passed the historical baseline seed-2907 failure region at about 847.8M steps and contains no `OWNER_*`, `GRID_FREE`, `INVALID_ATTACK`, SIGSEGV, or SIGABRT diagnostic. No fault trace or `signal.json` was produced.

The run used the original seed-2907 training command with isolated output directories and the corrected diagnostic engine copied to `lib/libnethack.so` (SHA-256 `ad1007c6a0c3880a00f5866b99304423d6483c72fff90fefadce8c7689f132a3`). The game fix clamps the post-fire-trap maximum monster HP; the tracker fix clears a watched pointer after a verified free. `command.json` records the exact command and environment. `inferior_exit.json` records exit code 0. `STATUS.json` records `gdb_rc: 1` because the capture script attempted `bt full 32` after the inferior had exited normally; GDB replied `No stack.` This is a capture-script post-exit error, not a training failure.

This completion is stress evidence for the patched build on seed 2907, not a deterministic replay of the original baseline failure or proof that the other anonymous `-11` exits share the same cause. Their original records have no fault stack or trace.
