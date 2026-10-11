# Reproduce the isolated prototype

Source base: ../engines/movement_masks/source (not production and not stock).
Candidate: ../engines/movement_subsystem/source.

In a fresh candidate directory, copy that source base, then run:

1. instrument_writes.py — Clang AST scan of 87 C files, preserving byte offsets,
   macro argument ranges, expression values, and write ordering. writes.json is
   the source-location audit; no Clang errors are allowed.
2. prepare.py — add the context grid, header/type/list/bulk-restore invalidations,
   per-query context, replacement query, and original-query verification build.
3. fix_macros.py — make four legacy fountain macros expression-safe and avoid
   invalidating an empty gas-region domain every world turn.
4. ../build_engine.py movement_subsystem
5. validate.py — build NH_MOVEMENT_MASK_VERIFY and run the five quick suites on
   both that build and release.
6. screen.py — immutable late-window hashes on both builds, then native A-B-B-A
   timings at 512 and 2048 environments with three identical snapshot trials.
7. profile.py, analyze_profile.py — native bracketing timings and CPU-clock
   stack samples at 2048 environments on both bitset and subsystem builds.

These scripts intentionally refuse or assert on conflicting inputs in several
places. They are experiment artifacts, not a production build entry point.

The generated patch is candidate.patch. Original authoritative NetHack records
remain for the rest of the game. The movement subsystem now consumes its own
materialized view. This adds 6,724 bytes of derived state per game, before alignment,
on top of the already-present occupancy/terrain columns. No saved-game format
change, reordered movement candidate, or policy/trainer change is intended.

Rare temple, engraving, and monster-interaction rules still call their existing
helpers. All ordinary, pet, and special movement callers invoke the replacement
mfndpos through the unchanged API. Verification executes the old and new queries
and checks output order, per-square flags, and mux/muy side effects. It also checks
every queried movement record against original terrain, piles, traps, and regions.

Domain-wide invalidation is conservative, including irrelevant changes to some
local construction records. Rebuild cost is deliberately included in native timing.
If this loses performance, that is evidence about this implementation rather than
proof that every possible compact/authoritative movement architecture is unhelpful.
