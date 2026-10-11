# Repeated monster movement predicates

Hypothesis: after the retained layout changes, mfndpos remains 14.7% self CPU
time and m_move 13.6%. Remove repeated pure checks within a single movement
decision, without changing the neighbouring-cell order or random draws.

Three independent candidates on retained compact_pool:

- move_invariants: hoist the hero's visibility/displacement and source-door
  diagonal restrictions; lazily compute can_fog at most once when a door is
  actually encountered. can_fog only reads species, genocide status, hero
  protection and carried objects. mfndpos cannot change those values; it can
  update the monster's mux/muy, which remain read dynamically. Preserve eel
  retries and all destination-specific checks. Booleanise the displacement
  bitmap explicitly rather than truncating it into an unsigned char.
- scary_once: separate generic fear immunity from square-dependent checks,
  and lazily reuse generic immunity during one neighbour scan. Shopkeepers
  and priests keep the original onscary calls at every square, including their
  room-query scratch-buffer behaviour. Keep position, scroll, altar and
  engraving predicates dynamic, including the updated apparent hero position.
  Other callers retain the original onscary interface and semantics.
- keys_once: check a monster's inventory once for either unlocking tool,
  instead of up to three m_carrying traversals. These are read-only presence
  tests returning a Boolean; neither selected object identity nor traversal
  order is observed. Credit cards still count only for unlocking.

No candidate is retained yet. Quick golden/fuzz/interleaved gates precede
short native screens. Full score/depth every-decision gates, repeated timing,
early-game checks and frozen-policy pipeline validation remain required before
retention. Native timings must not overlap builds or other benchmarks.
