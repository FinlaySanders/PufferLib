# Dry-tile monster liquid fast path

Current native profile attributes about 2% of samples to minliquid; this is
not a wall-clock fraction. Every moving monster enters the function. On a
dry ordinary tile with a non-eel species, all original effects are absent.
An early type switch may avoid the repeated terrain queries, Juiblex-level
test and monster/hero checks. This is a cheap bounded candidate, not an
expectation of a large gain. Golden/replay smoke checks precede timing;
broader special-terrain verification follows only if timing is useful.
No weight-cache change is included.

Water, lava, fountain, raised drawbridge and all eel species retain the
original code, including RNG calls, special levels and mounted behavior.
The guard uses the existing compact terrain type plane; its coherence
with the primary tile is already a baseline invariant, but must be checked
on replay before retention. Production files remain untouched.
