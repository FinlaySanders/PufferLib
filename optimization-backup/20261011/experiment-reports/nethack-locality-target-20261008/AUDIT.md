# Persistent floor-index audit

The baseline already invalidates floor-coordinate/index storage on place_object,
remove_object, splitobj on OBJ_FLOOR, replace_object on OBJ_FLOOR, level clearing,
level restoration/relinking, and save/free paths. It also invalidates at every
nle_step. The candidate removes only that last blanket invalidation.

All direct fobj/level.objlist assignments and &fobj uses were inspected.
Other coordinate writes in detect.c affect contained or monster-carried objects;
container location refreshes in pickup/trap.c preserve coordinates for floor
objects. Thrown/swallowed punishment ball and chain are OBJ_FREE while swallowed
(mhitu.c documents this); placement/removal subsequently uses the usual hooks.
Migrating/buried/new objects are not in the indexed floor chain. Scatter writes
are to scatter_chain records, not floor obj records. Revive records the already
resolved location of a floor corpse, or coordinates of a carried/contained one.
The full context excerpts are in mutation-audit.txt.

Verification build retains NLE_FOBJ_VERIFY: every cached lookup compares all live
floor pointers, order and coordinates before using the index. Mutation-during-
iteration keeps the existing generation-change fallback to the original list.
No changes to RNG draws, iteration order, game state, action processing or thread
scheduling. The verification build passed goldens/fuzz and all 16,777,216 mature replay
decisions before release timing, with zero observation/reward/terminal/mask hash
differences. Every-query consistency verification took 351.9 seconds. Historical trajectory hashes were pinned by the
previous investigation against the unchanged current baseline, not this candidate.

Limits: this is a source audit plus bounded runtime validation, not exhaustive
proof over every NetHack state. Native sample locations implicate the dependent
object-list walk; hardware cache/TLB counters are unavailable, so exact cache-level
miss rates are not claimed.
