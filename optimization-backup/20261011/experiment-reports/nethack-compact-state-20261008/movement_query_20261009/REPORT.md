# Movement query follow-up — 9 October 2026

## Outcome

The existing bulk terrain/occupancy filter remains the useful candidate. Extending
its occupancy bits to the rest of the neighbour query did not establish an
additional speedup. Park that extension. No retained/default engine or production
file changed; no commit, push or training job was started.

The measurement also rules out a large maintenance penalty as the sole explanation
for the filter's smaller gain at 2,048 environments. Updating the bits with the
original query unchanged is approximately flat at 512 and a small cost at 2,048.
This counterfactual includes the changed state layout and compilation, not a pure
timer around individual stores.

## Controlled cost comparison

Matched ordinary GCC LTO, identical mature recorded decisions 8192..8703,
24 workers plus four submitters. A=original retained source, M=same added bitset
state and writes but original mfndpos, B=existing bitset filter. Order A-M-B-B-M-A
at each size. Each process uses its own prepared snapshot; trials restore game
files and file offsets. 2,048 instances repeat 512 unique games four times.

| Environments | Original SPS | Maintain only SPS | Maintain vs original | Existing filter SPS | Filter vs original |
|---:|---:|---:|---:|---:|---:|
| 512 | 261,309 | 260,848 | -0.18% | 283,573 | +8.52% |
| 2,048 | 203,674 | 202,393 | -0.63% | 209,717 | +2.97% |

These are CPU replay rates, not full training rates, and not comparisons to
unmodified upstream. Sampling/profile support in the wrapper is identical across
arms. Native rows exclude stack collection. Timing repetitions reuse the same
states and are not independent episode samples.

The first 512-filter capture had unstable native calibration: 250361 and 279934
SPS (11.8% apart). It remains archived with an exclusion reason. The entire
capture was repeated, yielding 284075 and 283532 SPS; the independent reverse
process gave 284396 and 282290. No game state or reference was changed. All other
cost-comparison arm means repeat within 0.4% across their two processes.

## Where query time goes

Unchanged binaries profiled with the existing per-thread CPU-clock signal/stack
collector. Approximately 1/64 decisions are selected deterministically; separate
unprofiled step clocks calibrate stack proportions. No data-warming intervention
is enabled. Engine layouts differ, but the helper never dereferences engine
layout fields on this no-warming path.

At 2,048 environments, estimated inclusive neighbour-query time is about
25.1 us/decision original, 24.9 us with maintenance only, and 16.7 us with the
filter. Across those captures there are 4529, 4477 and 4323 stack samples.
Original-to-filter whole-step sampled CPU time falls only about 3.8 us on average.
Thus sampled attribution suggests offsets elsewhere in the step; it does not
identify their hardware cause or establish that a particular other function
regressed. Maintenance does not explain the entire difference.

At 512 the corresponding query estimates are 21.7, 20.6 and 14.8 us, based on
only 790, 828 and 746 stack samples. Treat these as coarse locations of cost.
Remaining movement excludes neighbour-query stacks; remaining step excludes both.
Inclusive function times in functions.csv overlap and must not be added.
PC sampling, core placement and observer effects prevent exact causal accounting;
no hardware cache/TLB counter evidence is claimed.

## Implemented experiment: consume occupancy throughout the query

Source: ../engines/movement_occupancy_query/source.
Patch: ../engines/movement_occupancy_query/changes_from_masks.patch.

Only mfndpos_masked changes. It constructs one raw neighbour-occupancy mask, keeps
the hero exceptions in a separate early-rejection mask, and uses the raw bits for
orthogonal occupancy during diagonal/worm checks and destination occupancy.
The actual monster pointer is still loaded when aggression/displacement needs it.
worm_cross itself remains unchanged. No additional persistent state, allocation,
write hook or invalidation is introduced beyond the previous filter prototype.

Occupancy does not change within this query. Perceived hero coordinates can
change, so those tests remain live, in their original order. Candidate ordering,
interaction flags and RNG calls are unchanged. The common query serves ordinary
movement, pets, and priest/shopkeeper movement without changing caller decisions.

## Incremental performance screen

Control is the existing movement_masks prototype, not the original engine.
Same ordinary-LTO compilation and matched window, standard scheduling, three
snapshot trials per fresh process, A-B-B-A. All endpoints match.

| Environments | Existing filter SPS | Extended query SPS | Increment | Control drift |
|---:|---:|---:|---:|---:|
| 512 | 283,861 | 283,794 | -0.02% | +0.06% |
| 2,048 | 209,703 | 206,616 | -1.47% | +0.83% |

There is no established additional gain. Several short trials are noisy: the
first 2,048 candidate process ranges from 196043 to 210907 SPS, while its second
ranges from 210208 to 210907. The leading control also has a low 204114 trial
beside two around 211k. All these native screen trials are retained in the table;
do not call the negative mean a precisely established regression. At 512 the
paired mean is flat. No larger confirmation campaign is warranted for this
candidate from these results.

## Behaviour and integrity

- Five golden/fuzz/status/interleaved/shuffled suites on each of maintenance-only,
  extended-query release, and extended-query verification builds: all 15 pass.
- Verification compares old and new ordered neighbours, flags and mux/muy effects
  on every query, as well as maintained bitsets against the original map grids.
- Each of those three builds matches 262,144 immutable per-decision hashes:
  **786,432 checks, zero differences**. Hashes cover observations, reward,
  terminal and action masks. No expected outputs regenerated.
- Every diagnostic and native trial has matching endpoints for its population.
- **3,885 protected files checked, zero changes**, including production
  files, retained/candidate sources and libraries, and the immutable reference.

This is bounded correctness evidence, not a proof for every possible game state.
Because the new extension is parked, it was not escalated to fresh PGO, full
score/depth corpora or frozen-policy training. The older bitset candidate's
33.55-million-decision validation remains separately documented and is not
credited to this new extension.

## Architectural implication

This completed one small data-flow change from already-audited writers through
all occupancy checks in mfndpos. It was behaviour-preserving on the checked
workloads, but removing these additional grid reads did not pay off measurably.
The pointer grid remains necessary elsewhere and on occupied interactions, and
the new mask arithmetic/extra live value also has a cost. Those are plausible
reasons, not separately measured causal attributions.

Keep the earlier bulk-rejection prototype. Do not expand this cache merely for
consistency, or repeat the older global occupancy-plane experiment (also flat).
The remaining query and movement costs still include terrain details, floor
search, fear, traps and other state. Any larger redesign should specify the
original data it will stop fetching across a complete operation, including its
remaining consumers, before another implementation. This experiment establishes
neither a large further speedup nor failure of all subsystem-oriented designs.

## Artifacts

- setup.py, measure.py, repeat_profile.py, analyze.py: maintenance control and profiles.
- measurements.json, analysis.json, functions.csv, runs/: raw comparison and stacks.
- prepare_query.py, screen_query.py, query_screen.json, query_trials.csv: extension and screen.
- query_screen.log, query_details.log: validation and timing commands/results.
- protected-before.json, integrity.json, and engine source manifests: integrity.
- ../MOVEMENT_ARCHITECTURE.md: design boundaries and source map.
