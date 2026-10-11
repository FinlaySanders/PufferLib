# Object-presence summary for the post-movement check

Decision: **isolated experiment complete; not promoted to the live engine**.

## Change and hypothesis

The previous flat-layout query reads compact pile summaries instead of object
lists. Its later monster pickup check still reads the original floor-object
pointer, which became a sampled hotspot. The hypothesis is that query savings
partly defer the first object-data access to that later check.

This candidate maintains an any-object-present bit in the existing tile summary
and uses it at that one post-movement check in m_move. Actual pickup code still
uses the original objects. Existing pile insertion/removal/replacement updates
maintain the bit; level clearing resets it and reconstruction uses the existing
object placement path. All other OBJ_AT consumers remain unchanged.

The bit fits in the existing two-byte summary. All previous context field offsets
and the 175,832-byte total context are unchanged. This avoids a new layout-size
confound. The verification build compares the bit against the actual object list
at every modified consumer and every queried cell.

## Fresh paired CPU replay comparison

| Environments | Previous flat query SPS | Object-presence SPS | Change |
|---:|---:|---:|---:|
| 512 | 286,929 | 289,489 | +0.89% |
| 2,048 | 211,954 | 213,733 | +0.84% |

The comparator is flat_movement_query, not movement_masks, upstream, or stock
Python NLE. Both builds use ordinary GCC LTO with the same options. Same 512
mature recorded streams, repeated four times for 2,048 environments; standard
one-action scheduling, 24 pinned workers, four submitters. Each fresh process
warms 8,192 decisions before plain/profile/profile/plain 1,024-decision windows
restored from the same snapshot. Engine order A-B-B-A at each size. Only plain
windows contribute to throughput; every trial is retained in trials.csv.
No builds or heavy analysis ran alongside timing. These are CPU replay results,
not full-training measurements or a matched PGO comparison.

At 2,048 environments the process averages are 211,986 and 211,921 SPS for
the control versus 213,709 and 213,757 for the candidate: both repeat comparisons
show a small gain. The 512 control averages drift from 289,111 to 284,748 while
candidate averages are 289,744 and 289,235; the sub-percent 512 mean is therefore
less conclusive. Do not interpret these replay results as a production speedup.

## Cost attribution

Estimated CPU microseconds per policy decision. Query includes its helpers;
other movement excludes query; rest excludes both. Stack proportions are scaled
by independently sampled unprofiled thread-clock times. Intervals use 2,000
bootstrap resamples over the 512 original games, keeping copies and captures
together. They do not account for machine drift or systematic profiler bias.

| Environments | Work | Previous flat query | Object-presence | Change | Game-bootstrap 95% interval |
|---:|---|---:|---:|---:|---:|
| 512 | Neighbour query | 11.52 | 10.44 | -1.08 | [-2.52, +0.45] |
| 512 | Other movement | 32.44 | 31.28 | -1.16 | [-3.26, +1.02] |
| 512 | Rest of step | 49.98 | 51.32 | +1.34 | [-1.12, +3.67] |
| 2,048 | Neighbour query | 14.73 | 14.46 | -0.27 | [-1.15, +0.57] |
| 2,048 | Other movement | 42.34 | 40.09 | -2.25 | [-3.67, -0.89] |
| 2,048 | Rest of step | 73.66 | 75.09 | +1.43 | [+0.11, +2.86] |

The targeted check shrinks as predicted. At 2,048 environments, samples in its
compiled instruction region correspond to 2.08us per decision in the control
and 0.08us in the candidate. The old floor-pointer test has 266 samples; the new
bit-test region has ten samples total, five in each process. The corresponding
m_move self-cost falls from 20.65 to 18.68us and other movement falls by 2.25us.
At 512 the check region falls from 0.87 to 0.09us, with fewer samples and weaker
category-level evidence. inspect_hotspots.py and hotspots.json retain the exact
instructions, offsets, counts and calibration.

This supports the lost-warming explanation: avoiding the later object-pointer
access removes the hotspot without making the context larger or restoring the
original query's pile walks. It is a targeted intervention, but it still does not
directly identify the hardware cache level or exclude generated-code effects.

The whole-step gain is smaller than the local saving. At 2,048 the sampled rest
of the step grows by 1.43us, spread across several functions (including observation
construction), while query cost changes by -0.27us with an interval spanning zero.
Those estimates have profiling uncertainty and do not establish a specific new
regression. rest_function_deltas.json records the individual sample attributions.
The defensible outcome is a repaired local hotspot and a roughly 0.8% native
throughput improvement, not recovery of the entire earlier warm/cold gap.

Per-process estimates, sample counts, native clocks and raw stacks are retained.
Any inference about cache warming is indirect; sampled PCs are not hardware
cache-miss counters. A zero-sample maintenance category does not mean free upkeep.

## Validation

- Ten golden/fuzz/status/interleaved/shuffled suites passed across release and
  verification builds.
- 524,288 immutable late-window hashes matched across
  both builds, including release code without reference-reading checks.
- 16,777,216 score-policy and 16,777,216 depth-policy
  decisions matched the immutable expected hashes: **33,554,432
  total, zero mismatches**. Checks cover observations, rewards, termination and
  action masks. Ordered movement candidates, flags and relevant side effects
  are additionally compared with the original query in the verification build.
- Context size/offset checks passed and all 2,048 combinations of the summary
  fields preserved the new bit and existing fields independently.
- 3,885 protected source/library/live/reference files are unchanged.
  No expected trajectories were regenerated. No live engine change, commit,
  push, training run or goal was started.

## Artifacts

- presence.patch: four-file change relative to flat_movement_query.
- prepare.py, build_validate.py, check_layout.py, measure.py, analyze.py: workflow.
- measurements.json, trials.csv, analysis.json, functions.csv, stack_samples.csv,
  native_env.csv and runs/*: timing, sample attribution and exact commands.
- proofs.json, root checks/movement_object_presence_verify.json and root
  depth/checks/movement_object_presence_verify/result.json: trajectory checks.
- source_manifest.json, SUMMARY.json, integrity.json and layout.json: source,
  library identity, protected-file and layout checks.
