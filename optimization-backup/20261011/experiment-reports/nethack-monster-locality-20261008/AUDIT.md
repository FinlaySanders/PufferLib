# Monster pool lifetime and behavior audit

Baseline: ../nethack-locality-target-20261008/engines/persist/source.

## Allocation paths

All monster allocation uses newmonst(): normal creation and cloning in makemon.c, level/bones restoration in restore.c, saved object traits and copies in mkobj.c. All callers already initialize/restore the record. The pool intentionally does not add zeroing.

There are two raw record deallocation sites: dealloc_monst in mon.c and free_omonst in mkobj.c. Both now return the record to the owning game's pool after their existing mextra cleanup. Other mon-related free calls release extension structs, names or region-ID arrays and remain ordinary frees.

Each block holds 64 stable, unmodified 144-byte struct monst records. Freed nmon storage links available slots; live nmon chains and traversal order are unchanged. Block growth never moves live records. Pool ownership lives in nh_ctx, not in thread-local allocation arenas, so worker migration cannot change which pool receives a record. The engine's existing nle_end first reanchors nh_cur to the game being closed.

The generated nh_ctx_free calls nh_mon_pool_release using the explicit context pointer, including after nh_cur is cleared. All blocks and pool metadata are freed there. Freed slots are reused within an episode. Memory follows peak concurrent monster-record count, rounded up to 64, and resets at episode teardown. Extension allocations retain existing teardown behavior.

## Compatibility

No struct monst fields, sizes, offsets, enum values, saved level formats, scheduling, RNG, observations or policy code change. Existing sizeof(struct monst)==144 compile-time checks in save.c and restore.c still pass. The new private context field is represented in globals.def and generated source/header files.

## Profile interpretation

The hot movemon guard flag lies at offset 65, after nmon, movement and HP fields. Swapping the guard conditions really does make GCC test mx first (confirmed by disassembly), but initial timing shows no benefit. Samples around m_move additionally identify object inventory and floor-item scans; mfndpos additionally touches object and terrain grids. Pooling monster records cannot remove those other accesses. Statistical instruction samples are not hardware cache-miss counts.

## Additional profile-supported candidate

The hot inventory comparison against type 198 is the credit-card search in monhaskey. That function scans up to three times for credit card, skeleton key and lock pick. The onepass_keys candidate returns the same boolean after one traversal. m_carrying only traverses minvent and returns a matching pointer; no RNG or mutation is involved. The caller never receives or observes the selected item, so changing which matching tool is encountered first cannot change behavior. Credit cards remain forbidden when for_unlocking is false.

## Compact monster occupancy grid

monster_grid adds an unsigned-byte empty/nonempty plane used only by MON_AT. m_at continues to read the authoritative pointer directly (the compiled baseline has no buried-monster filtering). Both placement paths, place_monster and place_worm_seg, update it, as does remove_monster. Initial map generation, level restore, level save/free and final dynamic-data teardown clear it with the pointer grid. A search of src/include/win found no other pointer-grid writes or whole-level copying. Grid updates do not change monster iteration order or data.

The optional NLE_MON_VERIFY build checks occupancy against the actual pointer on every MON_AT lookup, independent of NDEBUG. Full replay is required before retaining a winner. The extra plane is 1680 bytes per game; it reduces the read footprint of boolean checks from a 13440-byte pointer grid, but pointer lookups remain necessary when the monster itself is used.
