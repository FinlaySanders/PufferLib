# Fine-grained data-warming experiment

The locality penalty is distributed. We narrowed the previous main-context
and auxiliary-allocation effects to named fields; no one small field explains
the large normal-vs-burst difference. The strongest individual conditional
effects are the object-type table, terrain and monster grid.

| Omitted group | Added step time, us | Game-bootstrap 95% interval |
|---|---:|---:|
| object types | 4.91 | 4.55 to 5.25 |
| terrain | 4.79 | 4.38 to 5.20 |
| monster grid | 3.95 | 3.61 to 4.31 |
| remaining context | 3.61 | 3.31 to 3.95 |
| vision | 2.94 | 2.65 to 3.26 |
| floor object grid | 2.74 | 2.37 to 3.11 |
| glyph buffer | 2.63 | 2.34 to 2.94 |
| rng | 1.63 | 1.34 to 1.94 |
| lookup caches | 1.43 | 1.12 to 1.77 |
| hero and flags | 1.17 | 0.85 to 1.51 |
| other lazy allocations | 0.56 | 0.25 to 0.87 |

Normal sampled step time is 127.86us. Preparing the selected data reduces
that to 86.83us, but preparation costs 73.89us itself. This is a causal
diagnostic, not a useful prefetch implementation or end-to-end speedup.
Omissions are relative to the full preparation recipe, not standalone
speedup predictions. Effects overlap and must not be added. The old full
helper measured 87.15us, a 0.33us difference from the new full helper; small
effects must be read against this instrumentation/control sensitivity.

## Method and scope

2048 instances repeat 512 distinct recorded games four times. After 8192
decisions per game, each condition measures the next 256 decisions. Twenty
four pinned workers and four submitters use normal one-action scheduling.
Sample rate is approximately 1/64. Fourteen conditions are run in forward
then reverse order (28 timing cases), from the same process snapshot with
private game files and inherited descriptor offsets restored. Preparation
and step time are measured separately. The main pass took 158.99 seconds,
including initial preparation. This is CPU replay, not training throughput.

Main context size is 171816 bytes. Named groups cover terrain, floor-object
grid, monster grid, hero/flags, RNG, vision, lookup caches and all remaining
context. The reader omits accesses to physical 64-byte lines intersecting
each group. Shared boundary lines count in both omissions. Auxiliary groups
are object types (lazy slot40), glyph buffer (slot15), and all other lazy
allocations. layout.json and layout.txt record the exact spans.

Intervals cluster by the 512 original games, grouping copies and repeats;
2000 bootstrap resamples. They quantify workload uncertainty, not arbitrary
machine drift. Warming also changes timing and cache pressure; this does
not identify exact hardware cache levels, TLB misses or physical stall
cycles. No hardware counters or host-setting changes were required.

## Equivalence and next candidate

Fourteen proof cases cover 458752 immutable per-decision hashes, with zero
mismatches. All proof and timing endpoints match. All8 protected production
files,1290 retained-source files, the retained engine and reference hashes
are unchanged. No production patch, commit or push was made.

The next bounded candidate is a compact persistent public-object-glyph
lookup. It avoids repeated object-type-row reads in glyph export/public
weight pricing, with invalidation on identity and appearance changes.
Unlike the rejected per-fill memo, entries can survive across steps. Its
upkeep and lookup overhead must be included in native timing, and it must
match golden/fuzz/interleaved/shuffled trajectories before consideration.
See ../engines/public_glyph_cache/ for the independent candidate result.
