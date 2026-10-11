# Visited-tile storage experiments

The current captured wrapper, frozen trainer source, and live production source all implement first-visit scout reward. The only visited cell operations are a zero/nonzero test and storing1. A stale comment about XP-level values does not describe the executable code. All uses of visited, visited_key and n_visited_floors in the wrapper were checked before proposing a bitset.

visited_bits preserves the64 floor slots, key lookup order, coordinate checks, first-visit reward and maximum-floor behaviour; stores eight zero/one claims per byte. Full reset still clears everything. It reduces the map from106176 to13312bytes; no game or model representation changes.

visited_lazy leaves the byte representation and Env size intact. Reset clears hot scalar stats and sets n_visited_floors=0. A row is cleared immediately before its slot is first used in the new episode. No stale row/key can be read through the live-floor prefix. This isolates the cost of clearing never-used floor rows from packing.

These are isolated wrapper/harness copies. No production/training source was edited. Score and depth harness variants preserve their respective environment settings. Every-decision observations/rewards/terminals/masks must match original immutable references; then native screens, and full frozen-pipeline validation only if a meaningful speedup emerges.
