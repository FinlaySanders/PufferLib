# Why the primary movement redesign is approximately flat

The native profiles support a specific offset: the neighbour query gets cheaper,
but surrounding monster movement gets more expensive. New summary-maintenance
bodies are much too small in this workload to explain the several-microsecond
offset. This narrows the earlier explanation; maintenance was a hypothesis,
not the measured cause.

## Cost breakdown

Microseconds of CPU time per policy decision; negative change means cheaper.
Categories are exclusive. The query category includes its called helpers;
other movement excludes query stacks; rest excludes both. Whole-step CPU time
comes from independent sampled thread clocks without stack collection. Native
stack proportions are scaled by those clocks, not nested timers around every
query.

| Environments | Work | Baseline | Redesign | Change | Game-bootstrap 95% interval for change |
|---:|---|---:|---:|---:|---:|
| 512 | Neighbour query | 14.24 | 12.62 | -1.62 | [-3.21, +0.05] |
| 512 | Other movement | 30.91 | 33.14 | +2.23 | [-0.01, +4.46] |
| 512 | Rest of step | 49.86 | 49.86 | +0.00 | [-2.41, +2.41] |
| 512 | Whole step | 95.02 | 95.62 | +0.60 | [+0.36, +0.88] |
| 2,048 | Neighbour query | 17.64 | 14.99 | -2.66 | [-3.60, -1.74] |
| 2,048 | Other movement | 39.83 | 42.90 | +3.07 | [+1.78, +4.43] |
| 2,048 | Rest of step | 73.92 | 72.61 | -1.32 | [-2.67, +0.03] |
| 2,048 | Whole step | 131.39 | 130.49 | -0.90 | [-1.10, -0.70] |

At 2,048 the estimated query saving is about 2.66us and the increase in other
movement about 3.07us. The rest of the step is modestly cheaper. At 512 the
same pattern appears, but category intervals include zero; its attribution
is weaker. The sub-percent whole-program result remains approximately flat.

PC sampling attributes about 2.44us of the larger-population offset to m_move's
own compiled instructions, with another 0.46us in newsym reached from movement.
These are exclusive sample estimates, not independently timed regressions.
Inlining can move cost between symbol names: for example, disappearing onscary
samples do not by themselves prove its work was eliminated. The combined query
category is the relevant measurement. Likewise, dosearch/dosearch0 trade places
between builds, so individual-symbol changes must not be read as work changes.

## Summary-maintenance check

A separate isolated copy times the four new helper bodies: pile updates, trap
updates, level entity-summary clearing, and gas-rectangle updates. Counts are
collected on all measured decisions; timings on the same deterministic 1/64
sample as the native diagnostic. The scope timer uses invariant TSC, calibrated
against CLOCK_MONOTONIC_RAW. Samples with significant descheduling or changed
CPU are rejected. The empty-scope cost is reported, not silently subtracted.

| Environments | Maintenance us/decision | Game-bootstrap 95% interval | Helper calls/decision | Empty-scope budget us/decision |
|---:|---:|---:|---:|---:|
| 512 | 0.0498 | [0.0416, 0.0594] | 0.620 | 0.0066 |
| 2,048 | 0.0748 | [0.0649, 0.0859] | 0.620 | 0.0062 |

The helper-body times include clock overhead. They do not include every call-site
argument/where check, nor the existing terrain/occupancy bitset maintenance; those
remain in the native whole-step profiles. They also do not measure the memory or
addressing cost of reading the new layout. No gas updates were selected for timing
in this window despite occasional counted calls: this is a workload average,
not a guarantee about gas-heavy levels. Component counts, timings, dropped scopes
and uncertainty are in maintenance_analysis.json and maintenance_env.csv.

Instrumentation calibration, same diagnostic library and harness, in
inactive/count-only/sparsely-timed order and then reverse:

| Environments | Inactive hooks SPS | Counts only SPS | Counts + timing SPS |
|---:|---:|---:|---:|
| 512 | 283,197 | 283,073 | 281,337 |
| 2,048 | 212,395 | 212,371 | 212,344 |

These are diagnostic-overhead measurements, not optimization results. Query
attribution above uses the unchanged native binaries, not this instrumented copy.

## Native throughput

| Environments | Baseline CPU replay SPS | Redesign CPU replay SPS | Change |
|---:|---:|---:|---:|
| 512 | 283,656 | 281,747 | -0.67% |
| 2,048 | 210,908 | 212,487 | +0.75% |

Both are the same ordinary-GCC-LTO builds used in the prior redesign screen.
The baseline is movement_masks, not upstream NetHack. Standard one-action
interleaving, 24 pinned workers, four submitters; 512 unique recorded games,
repeated four times at 2,048 environments. Each process warms 8,192 decisions.
A-B-B-A at each size, each process containing plain/profile/profile/plain
1,024-decision windows restored from the same snapshot and files. No data-warming
intervention is enabled. No other builds or heavy analysis run during timing.

This window is twice as long as the preceding 512-decision speed screen. The
512 result changes sign within a percent; it does not establish a meaningful
regression or win. These are CPU replay rates, not full training SPS.

## Interpretation and remaining uncertainty

The redesign did improve its targeted query. The saving is being cancelled in
other consumers of the changed state. Locality, addressing, and generated-code
changes remain possible reasons for the m_move offset. This experiment does not
separate them and is not evidence for a particular cache level or TLB mechanism.
The compiled m_move size is essentially unchanged, so simple code-size growth is
not an established explanation either.

A useful next isolated comparison would retain the cheaper query predicates while
restoring the old flat terrain/type layout, rather than expanding this redesign.
That would test whether the query improvement can be kept without the surrounding
movement cost. No such variant was implemented in this diagnostic.

## Reliability and artifacts

- Four native stack captures per arm/population. Total samples: baseline/redesign
  3,089/3,145 at 512 and 17,188/16,867 at 2,048. No unwind fallbacks.
- Stack collection reduces throughput by about 3-5%; whole-step calibration is
  taken from separate unprofiled windows. Residual observer effects remain.
- 2,000 bootstrap resamples cluster by the 512 original games, grouping all copies
  and repeat captures. Intervals describe workload/sample uncertainty; they do
  not establish immunity to hardware drift or profiling bias.
- 1,048,576 immutable per-decision hashes match, zero differences, covering native
  stack collection for both engines and inactive/timed maintenance diagnostics.
  All timing endpoints match. Expected hashes were not regenerated.
- 2,594 protected source/library/live/reference files are unchanged.
  No production patch, commit, push, new training run or goal was started.
- analysis.json, native_env.csv, stack_samples.csv, functions.csv,
  exclusive_function_deltas.csv retain the native decomposition and raw samples.
- maintenance_analysis.json, maintenance_env.csv, maintenance_instrumentation.patch
  retain the direct helper measurement and its source change.
- runs/*/command.json and run.log record exact binaries, library hashes,
  environment settings, raw clocks and stack files. profile.py, analyze.py,
  setup_maintenance.py, measure_maintenance.py and analyze_maintenance.py reproduce
  the work in a fresh output directory.
