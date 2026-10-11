# Full movement-neighbour subsystem experiment

The isolated implementation is complete. It does not improve measured CPU replay
throughput beyond the existing movement bitsets. Parked; production and retained
engine are unchanged. This result tests the materialized movement-grid design
below, not every possible authoritative state-layout redesign.

## Scope actually implemented

- A persistent 32-bit movement record per square: terrain/passwall/dig/door rules,
  pool/lava/altar, boulder/garlic/scare-scroll presence, first trap type and presence,
  and whether the first visible region is poison gas.
- Write-side invalidation for terrain aliases/type setters, floor list mutations
  and in-place item-type changes, trap creation/deletion/type/position changes,
  region geometry/lifetime/list changes, and bulk level restore. Compiler-assisted
  source audit in writes.json: 298 individual expressions in 40 C files, plus
  explicit header/list/bulk hooks. Candidate changes 48 files overall.
- Domain rebuild on first use after invalidation; its full cost is timed. Payload
  6,724 bytes per game before alignment, in addition to existing column bitsets.
- Query-local capability context with cached equipment/fear predicates; the query
  consumes compact records rather than separate terrain, pile, trap, and gas walks.
- Ordinary monsters, pets, and priests/shopkeepers all use this query through the
  unchanged mfndpos API. Candidate order, hero-memory updates, caller choices,
  and RNG order are preserved on the validated corpora.

Original NetHack records remain authoritative for the rest of the game. This is
an integrated derived representation for the neighbour-query subsystem, not a
rewrite of every movement action or all monster AI. Rare temple, monster-interaction,
and Elbereth-text rules retain their existing helpers. See SCOPE.md and REPRODUCE.md.

## Native screen

Matched ordinary GCC LTO on both arms. Control is movement_masks, NOT stock NLE
or upstream PufferLib, and NOT the retained PGO library.

| Environments | Bitset CPU SPS | Subsystem CPU SPS | Change | Control drift |
|---:|---:|---:|---:|---:|
| 512 | 281,967 | 283,904 | +0.69% | -1.39% |
| 2,048 | 209,744 | 206,986 | -1.31% | +0.17% |

A-B-B-A fresh processes, three 512-decision snapshot trials per process, after
8192 warmup decisions; 24 engine workers, four submitters. Ordinary one-step
interleaving. All trials retained. 2048 instances replicate 512 recorded games;
these are repeated workload timings, not independent training seeds or episodes.
512's small positive mean is below its control drift and is not an established win.
No GPU inference, training SPS, 8192-environment claim, or extrapolated 2x speedup.

A second native harness, bracketing its profile cases with unprofiled timing,
measured 209,894 versus 206,706
SPS at 2048 (-1.52%). Raw cases: measurements.json, runs/, screen.json, trials.csv.

## Profile

Calibrated CPU-clock stack samples, microseconds per decision. Exclusive categories
avoid adding nested inclusive times; values are estimates, not hardware-counter
attribution. The neighbour-query category includes grid rebuilds. No claim that
cache misses or rebuild overhead alone explain the result.

| Arm | Whole step CPU µs | Neighbour query | Remaining movement | Other work | Stack samples |
|---|---:|---:|---:|---:|---:|
| Bitset | 132.41 | 18.26 | 39.25 | 74.90 | 4,301 |
| Subsystem | 134.06 | 17.23 | 40.87 | 75.95 | 4,418 |

The sampled query time changes only from roughly 18.3 to 17.2 microseconds; with
about 4,300–4,400 stack samples, this is not evidence of a large or precisely
resolved saving. Existing helper work has mostly moved into the compiled query:
its self time rises while its separate callees disappear. Broader movement and
other engine work still dominate. The profile does not isolate rebuild costs or
establish a particular hardware cause for the small whole-step slowdown.

Function-level inclusive/self samples are in functions.csv. PMU remains unavailable.
The new compiled neighbour function is 8,499 bytes versus 6,612 bytes (LTO symbols);
this is a code-size observation, not proof of an instruction-cache bottleneck.

## Correctness and integrity

- Both release and old/new comparison builds pass all five quick suites: golden,
  fuzz, status option, interleaved environments, and shuffled environments.
- Both match immutable late-window decision hashes: 524,288 checks total.
- Verification build full score corpus: 16,777,216 decisions, zero differences.
- Verification build full depth corpus: 16,777,216 decisions, zero differences.
- The verification build checks compact facts against original records and compares
  old/new ordered neighbours, flags, and mux/muy on every query. Expected hashes
  were never regenerated.
- 1,301 protected files unchanged, including live user edits, retained
  source/library and immutable score reference.

## Decision

Keep this as a reproducible negative experiment. Do not promote it, add its tiny
512 mean to earlier gains, or discard the existing bitset improvement. There is
no demonstrated incremental throughput benefit from this grid implementation.
Fresh PGO and full training-pipeline benchmarks were not run because the native
screen did not justify promotion. A future redesign must remove measured work or
reduce total touched state, accounting for its update costs; a larger cache alone
is not an evidenced route to the remaining locality gap.
