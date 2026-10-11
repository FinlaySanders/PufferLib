# Why compact floor metadata did not produce a large speedup

The previous patch reduced repeated field loads, but scarcely reduced the data
touched by a game step. Direct source-access tracing identifies a concrete cause:
rebuilding the floor index reads the full object list first, and subsequent game
logic still consumes object fields after the compact search filter. An incremental
index prototype removes the rebuild traffic, but has not established a large
native throughput improvement. No production change or new retention.

## Matched access trace

512 games, four ordinary decisions each after 8192 warmup decisions/game; the
same actions and endpoint (e19798d5fd4e1c2e, 14191 world turns). Static worker
assignment in the tracing harness avoids the known Clang TLS/coroutine issue.
These are source-level access callbacks and distinct virtual 64-byte lines per
decision, **not hardware cache misses or bytes fetched from RAM**. Clang uses
fine-grained bitfield instrumentation and explicit memcpy/memmove/memset wrappers
on both sides. Native timing uses separate GCC Release/LTO binaries.

| Build | All data lines/step | Floor-object lines/step | Floor load callbacks/step |
| --- | ---: | ---: | ---: |
| Original | 835.56 | 60.62 | 3449.0 |
| Compact metadata | 832.89 | 54.65 | 2656.1 |
| Incremental original index | 811.08 | 36.02 | 3305.3 |

Compact metadata cuts floor load callbacks by 23%, but total distinct lines by
only 0.32%. It adds 4.29 metadata lines/step. Original first touches include
29.56 floor-object lines/step in nh_fobj_build (48.8% of floor-object lines).
The compact version still touches 31.70 in packing/building, while touch_artifact,
can_carry and other later consumers fetch records skipped by its search filter.
Thus fewer source loads did not mean a comparably smaller working set.

The incremental prototype keeps the original representation/readers and updates
the derived pointer/coordinate arrays at insertion, removal and replacement.
It preserves floor-list order, the same generation changes and live-list fallback
for existing cursors. Bulk edits and capacity overflow still invalidate/rebuild.
No extra metadata array or type/class setters. Patch: incremental.patch.

In this trace it eliminates rebuild first touches, reduces floor-object lines
40.6%, and total lines 2.93%. Some reads move to later consumers: m_move first
touches rise from 14.98 to 17.70 lines/step. This is measurable waste removed,
but its footprint is a small part of the whole step.

Raw categories, first-touch symbols/sites and paired game-bootstrap 95% intervals
are in access.json and incremental_access.json. Intervals describe game sampling,
not uncertainty in native timing or hardware misses. Categories are registered at
the start of each step; new allocations, freed/reused addresses and shared boundary
lines limit fine attribution. This four-decision window is a diagnostic sample,
not a complete training distribution. The initial metadata trace mistakenly reused
category501; it is preserved as capture_ambiguous_metadata_id and **excluded**.
Reported results use the rebuilt/recollected trace with unique category9000.

## Native cost of the old patch

2048 environments, 24 workers, four submitters, 8192 warmup then 512 ordinary
one-action decisions/game. A-B-C-C-B-A fresh-process order; two restored snapshot
trials per process. B maintains metadata but uses the original search logic.
C uses the complete compact readers. All use ordinary GCC LTO, not PGO.

| Build | Mean SPS | Relative to control | Trial range |
| --- | ---: | ---: | ---: |
| monmove_utilityguard | 205,690 | +0.00% | 205,521–205,774 |
| floor_metadata_bookkeeping | 204,635 | -0.51% | 203,912–205,058 |
| floor_metadata_utility | 204,124 | -0.76% | 201,160–206,534 |

Bookkeeping alone costs roughly 0.5%. The complete version is not a reliable win;
its second process is slower than its first. These contrasts include compiler and
layout effects and are not an exact division of cycles between machine instructions.
Earlier independent screens at512/2048/8192 were also approximately flat; see
../floor_metadata_20261009/REPORT.md. No cache-miss or thermal cause is asserted
for the timing variation.

## Native incremental-index screen

Same workload and compilation settings, A-I-I-A process order, two trials/process.
Separate preparation and snapshots per binary; no stacks transferred across builds.

| Build | Mean SPS | Relative to control | Trial range |
| --- | ---: | ---: | ---: |
| monmove_utilityguard | 205,495 | +0.00% | 205,009–205,855 |
| floor_index_incremental | 207,017 | +0.74% | 206,934–207,084 |

This is a CPU replay screen, not a training speedup. It does not recover the large
diagnostic burst/warm-cache uplift. The complete gap spans other object consumers,
monster and terrain state, observations and other engine work. Hardware cache/TLB
miss counters remain unavailable, so exact miss-level attribution is unresolved.
Directly reducing measured accesses narrows the question; it does not guarantee
that those accesses were the expensive misses.

## Correctness and scope

- Five unchanged golden/fuzz/status/interleaved/shuffled suites pass.
- Incremental mutation/ordering test: PASS incremental insert/remove/replace/relocate/cursor/bulk/overflow queries=2136431 returned=2131331.
  Valgrind reports zero errors and no leaks.
- 262,144 immutable per-decision hashes match,
  including observations, rewards, terminal state and masks.
- All 20 timing endpoints/turn counts match.
- Eight protected production files,1290 retained source files, retained PGO library
  and original hash reference are unchanged; integrity_after.json.

The incremental prototype is left isolated for review. Full-corpus/depth replay,
fresh PGO, fresh-process confirmation without snapshot restoration and frozen
training-pipeline gates have not been run for it. It is **not a new default**.
All commands, hashes, patches and raw results remain alongside this report or in
../fast_loop_20261009/runs/floor_diagnosis_* and floor_incremental_*.
