# Improved movement queries on the original flat terrain layout

Decision: **small native gain, but surrounding movement offset persists; isolated, not promoted**.

## Change

Restored the movement_masks baseline's six-byte terrain record, flat 80x21 terrain
array and separate one-byte cached-type plane. The improved direct query predicates,
query-local monster capabilities, bulk neighbour filter, and mutation-driven
pile/trap/gas summaries remain. Summaries are now a separate two-byte-per-tile array
(3,360 bytes), appended in the cold context section. No lazy invalidation or full-map
reconstruction on queries was introduced. Summaries clear at level transitions and
update at the same mutation sites as the tiled design.

The raw/cached terrain-type distinction and its update points are preserved. Each
query loads the original/candidate cached terrain types from the restored plane.
The boundary behavior of the original flat type plane is restored. All original
level/hero/inventory/etc context fields have their baseline offsets; the nh_lazy
pointer table moves by 3,360 bytes to accommodate the added array. The new context
is 175,832 bytes versus baseline 172,472 and tiled 174,848. This is not a claim of
lower total memory than either earlier design.

The migration changes 10 files versus the tiled prototype. Earlier
NH_TILE access conversions and safe bounds/field-copy fixes remain; NH_TILE now
resolves to the original flat array. The two-byte entity summary is derived state;
its consumers are verified against original object/trap/region records.

## Fresh paired native comparison

| Environments | Baseline CPU replay SPS | Flat query SPS | Change |
|---:|---:|---:|---:|
| 512 | 283,942 | 289,013 | +1.79% |
| 2,048 | 211,017 | 213,456 | +1.16% |

Both engines use ordinary GCC LTO. Baseline is movement_masks, not upstream or
stock Python NLE. Same 512 mature recorded streams, repeated four times for
2,048 games. Standard one-action scheduling, 24 pinned workers, four submitters.
Each independent process warms 8,192 decisions, then restores the same snapshot
for plain/profile/profile/plain 1,024-decision windows. Engine order A-B-B-A at
each size; only plain windows contribute to throughput. All timing trials retained.
No builds or heavy analysis run concurrently with timing. No PGO or full-training
speed claim is made.

The measured gains are small. In particular, the two 2,048-environment baseline
processes average 211,986 and 210,049 SPS, while the candidate processes average
213,146 and 213,766 SPS. All are included; the reported +1.16% should not be read
as a tightly established production speedup. This experiment has not compared
matched PGO builds or measured training throughput.

## Cost decomposition

Estimated microseconds of CPU time per policy decision. Exclusive categories;
query includes its helpers, other movement excludes query, rest excludes both.
Stack proportions are calibrated with independent unprofiled thread-clock samples.
Negative changes mean cheaper. Intervals bootstrap by the 512 original games,
keeping repeated copies and captures together, 2,000 draws.

| Environments | Work | Baseline | Flat query | Change | Game-bootstrap 95% interval |
|---:|---|---:|---:|---:|---:|
| 512 | Neighbour query | 13.16 | 11.52 | -1.64 | [-3.25, -0.04] |
| 512 | Other movement | 30.66 | 32.94 | +2.27 | [+0.02, +4.74] |
| 512 | Rest of step | 51.22 | 48.92 | -2.30 | [-4.73, +0.06] |
| 2,048 | Neighbour query | 17.49 | 13.89 | -3.60 | [-4.53, -2.66] |
| 2,048 | Other movement | 39.42 | 42.62 | +3.20 | [+1.91, +4.41] |
| 2,048 | Rest of step | 74.33 | 73.31 | -1.02 | [-2.33, +0.35] |

Restoring the flat terrain and original hot-field offsets did **not** remove the
surrounding movement cost increase. At 2,048 environments the query saves 3.60us
per decision, but other movement adds 3.20us, leaving only 0.40us saved across
movement as a whole. At 512, the corresponding estimates are 1.64us saved and
2.27us added. The remaining step categories contribute to the small whole-step
gain, with wider uncertainty in their attribution. Thus the hypothesis that
restoring the original terrain layout would recover the movement offset is not
supported by this experiment. The measured offset still needs a more specific
cause; this does not establish a general cache explanation or implicate the
locally maintained summaries by themselves.

The summary-maintenance category has no sampled stacks, which does not mean
maintenance is free. Its helpers are short and may be inlined into callers.

The tiled design's previous matched comparison is documented in
../primary_movement_costs_20261009/REPORT.md: at 2,048 it reduced query cost by
2.66us but increased other movement by 3.07us. Compare the fresh baseline-relative
changes above to that pattern; the tiled engine was not re-timed concurrently in
this experiment. Whole-program results and these estimates do not isolate a
particular hardware cache, TLB or instruction cause. PC attribution is affected
by inlining and observer overhead; bootstrap intervals exclude neither machine
drift nor systematic profiler bias. See analysis.json for per-capture estimates,
sample counts, profile overhead and repeat drift.

## Correctness and integrity

- Ten golden/fuzz/status/interleaved/shuffled suites pass across release and
  reference-comparison builds.
- 524,288 immutable late-window decision hashes match across both builds.
- 16,777,216 score-policy and 16,777,216 depth-policy decisions
  match the immutable baseline, **33,554,432 decisions total, zero mismatches**.
  Hashes cover observations, rewards, termination and masks. The verification
  build additionally compares ordered neighbours/flags, hero-memory side effects,
  and summary contents against original entity records at every query.
- A million randomized legacy save/copy round trips pass. Every terrain coordinate,
  cached-type pointer update, local/legacy pointer case, and cross-column cached-type
  lookup is tested. Layout checks confirm six-byte cells and two-byte summaries.
- offsets.json checks all pre-existing context field offsets against the baseline;
  only the lazy table offset and total context size differ.
- 2,593 of 2,594 protected entries unchanged, including
  all baseline/tiled source and library files, eight live files and the immutable
  score reference. Only the generated gen_ctx Python bytecode cache refreshed
  when the layout check imported it; integrity.json records this exception. No expected
  trajectories regenerated, live engine replacement, commit or push.

## Follow-up: a specific floor-object access hotspot

Further inspection of the same native captures narrows the offset. At 2,048
environments, about 3.03us of the 3.20us increase in other movement is attributed
to m_move's own compiled instructions. A single hotspot at m_move+0x7e5, the test
immediately following the load of level.objs[x][y] for the post-movement OBJ_AT
check, grows from 1 sample to 298 samples (148 and 150 in the two candidate
processes). Calibrated as before, that is about +2.29us per decision. At 512 the
same hotspot grows from zero to 28 samples, about +0.86us. The load, its address
calculation, the following test, and the floor-object array's context offset are
unchanged between the binaries. The neighbour query is a separate called function
in both builds, so this particular hotspot is not the query being renamed by
inlining. See floor_object_hotspot.json.

The baseline neighbour query reads OBJ_AT for candidate tiles and walks relevant
object piles. The new query uses pile summary bits instead, while m_move still
reads the original floor-object pointer after movement. A concrete explanation
consistent with these observations is that the old query was warming object data
needed later; the new query avoids that access, and later movement pays the first
access cost instead. This is stronger evidence than a generic terrain-layout
explanation, but sampled PCs do not directly measure cache misses or prove this
causal mechanism, nor does this one hotspot explain every remaining difference.

A focused next intervention is to maintain an any-object-present summary bit and
use it for this empty-tile check, retaining the original object-list access for
actual pickups. The current three special-object bits are not enough: an ordinary
object can be present with all three bits zero. No such intervention has been
implemented or timed here.

## Artifacts

- from_tiled.patch and from_baseline.patch: final changes; source_manifest.json
  and SUMMARY.json identify final source/library hashes.
- prepare.py, build_validate.py, check_layout.py: implementation and initial gates.
  The first compile caught four level-reset summary clears still using old fields;
  final source and preparation script both include that correction.
- measure.py, analyze.py, measurements.json, analysis.json, trials.csv: raw timings
  and cost decomposition. Each runs/* directory contains command/library hashes,
  logs, native clocks and stack captures.
- proofs.json, root checks/flat_movement_query_verify.json and root
  depth/checks/flat_movement_query_verify/result.json: trajectory results.
- layout_test.c, layout_checks.log, offsets.json: layout and serialization checks.
- integrity.json: protected-file check.
