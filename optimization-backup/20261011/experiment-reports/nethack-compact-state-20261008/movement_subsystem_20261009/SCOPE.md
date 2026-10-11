# Full movement-neighbour subsystem experiment

Boundary: mfndpos, used by ordinary monsters, pets, and priest/shopkeeper movement.
Replace its terrain semantics, pile classification, trap search, and visible-gas
queries with one persistent 32-bit facts grid. Track the mutations that feed each
domain. Build a mover context once per query; use lazy per-query equipment predicates.
Keep occupancy columns and ordered x-major results. All three callers consume the
new query through the existing API; their selection rules and random draws stay intact.

This is a complete neighbour-query data-flow experiment, not a rewrite of all AI.
Monster interactions, temple membership, and the rare Elbereth text lookup retain
existing semantic helpers. The actual/apparent hero position update stays ordered.
The original query remains compiled into the verification build, which compares
ordered positions, flags, and hero-memory side effects on every call. Verification
also compares packed facts against the original source data.

Grid domains are invalidated after mutations and rebuilt on demand. Initial version
uses domain-wide invalidation (simple and conservative). Rebuild costs count in the
benchmark. If these dominate, per-cell invalidation is a separate follow-up; no claim
of an authoritative replacement of all NetHack storage.

Controls: ordinary LTO movement_masks and ordinary LTO retained engine. Screens use
512/2048 environments, identical recorded actions and windows, ordinary one-step
interleaving, A-B-B-A process order. No grouped collection or policy changes.
Quick golden/fuzz/interleaving checks and immutable decision hashes precede timing.
PGO/full replay/real pipeline gates required before promotion; no production edits.
