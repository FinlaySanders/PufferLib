# Primary movement-state redesign

Implemented and validated in an isolated engine. Decision: **parked; no demonstrated material incremental gain**.
Production, the movement-mask baseline, and the retained production engine are unchanged.

## What actually changed

This replaces primary terrain storage, rather than adding another full movement cache.
The original 6-byte terrain records and separate cached-type array become 8-byte cells,
arranged in aligned 4-column x 2-row blocks. Both logical terrain types remain, with their
original update timing; the separate array is removed. All terrain readers, writers,
column pointer walks, and room-neighbour indexing now use this representation.
The change touches 75 files, including generated context layout.

Cells also hold boulder/garlic/scare-scroll presence, trap type/presence, and first-visible
poison-gas membership. Object insertion/removal/type changes and trap changes update
only affected cells. Region changes update affected rectangles, including the priority
change caused by swapping the last region into a removed list slot. Level load/release
clears or restores the summaries. There is no validity flag, separate facts grid, or
whole-map rebuild on movement queries. Existing movement-column bitsets remain.

Monster neighbour selection reads the cells. Ordinary monsters, pets, and priests use
the same unchanged query API. Object/trap identity records, monster records, and their
lists still exist: this is a primary terrain/spatial-facts redesign, not a rewrite of
all entity storage or all monster AI. The summaries of entity occupancy remain derived
from those records and are checked against them in the verification build.

The consumer reads these fields directly and computes only predicates needed by each
branch. The first implementation reconstructed a complete temporary terrain-fact word
for every queried cell; that version lost 7.15% at 512 and 3.15% at 2,048. It remains
separately recorded in `../primary_movement_20261009/REPORT.md`. No cache or world-map
rebuild was reintroduced by this direct-consumer variant.

## Memory cost

Bytes per game, excluding separately allocated entities and other subsystems:

| Engine | Cell | Level struct | Main context |
|---|---:|---:|---:|
| movement_masks | 6 | 37,664 | 172,472 |
| movement_subsystem | 6 | 37,664 | 179,200 |
| primary_movement_direct | 8 | 41,664 | 174,848 |

The new padded tile grid is 14,080 bytes versus 11,760 for the old terrain plus type
plane. Context size increases by 2,376 bytes versus movement_masks, but is 4,352 bytes
smaller than the previous failed shadow-cache design. This was a locality and work
elimination hypothesis, not a claim of smaller total state than the baseline.

## Native CPU replay screen

Matched ordinary GCC LTO, compared with **movement_masks**, not upstream NLE, a stock
Python interface, or a PGO build. A-B-B-A, three 512-decision timed windows per process,
24 engine workers and four submitters. Each process warms the same games for 8,192
decisions; timed collection uses ordinary one-step interleaving. The 2,048 instances
repeat the same 512 captured game streams four times. All measurements are retained.

| Environments | Baseline CPU SPS | Redesign CPU SPS | Change | Baseline drift |
|---:|---:|---:|---:|---:|
| 512 | 284,463 | 284,632 | +0.06% | +0.25% |
| 2,048 | 212,594 | 213,882 | +0.61% | -0.26% |

These are engine-replay rates, not training SPS. Repeated windows within a process
are correlated; they are not independent training seeds. No fresh PGO, GPU inference,
full trainer timing, or 8,192-environment claim is made.

## Correctness

- Ten quick suites pass: goldens, fuzz, status options, interleaved environments,
  and shuffled environments, on both release and reference-comparison builds.
- 524,288 immutable late-window decision hashes match across the two builds.
- Final verification build: 16,777,216 score-policy and
  16,777,216 depth-policy decisions, **zero mismatches**. Each decision
  compares observation, reward, termination, and action-mask hashes. The verification
  build also compares original/new ordered neighbours and hero-memory side effects,
  and checks tile summaries against original object/trap/region queries.
- A million randomized legacy-save round trips preserve all terrain fields and keep
  derived metadata separate. Every tile coordinate and cached-type pointer update is
  tested, including local/legacy pointers and cross-column reads.
- Compiler-assisted pointer audit covers 29 files; remaining indexed expressions are
  reviewed SET_TYP_P base-address calculations. All real old levl/locations/type-plane
  accesses have been removed from compiled C/C++ sources.
- 8 protected live files and 1,291 baseline
  files remain unchanged; expected trajectory hashes were not regenerated.

During migration the tests caught unmigrated column walks, three indexed room reads,
beam bounces relying on flat-array cross-column type reads, and an unused pre-bounds-check
terrain read in object scattering. The former reads preserve the original logical
lookup; scattering now reads terrain only after its existing bounds check. These are
compatibility fixes required by the new layout, not changes to intended game mechanics.
The explicit boundary helper rejects reads beyond the complete logical map; the tested
corpora do not require such undefined legacy accesses. Tests establish equality on
these corpora, not a proof covering every possible NetHack game.

## Artifacts

- `candidate.patch`, `source_manifest.json`, `changed_files.json`: final source.
- `screen.json`, `trials.csv`: all timing and late-window hash checks.
- root `depth/checks/primary_movement_direct_verify/result.json`, root `checks/primary_movement_direct_verify.json`: full checks.
- `layout_test.c`, `layout_result.log`, `pointer_audit*.json`: layout/reader audit.
- `../primary_movement_20261009/prepare_direct.py`: direct consumer implementation
  on top of the fully validated primary-layout source; earlier migration scripts are
  in that same predecessor directory.
- `REPRODUCE.md`: build and validation commands. Diagnostic failure logs are retained
  separately; final results above come from the corrected source.
