# Movement subsystem follow-through

The combined rework improves mature CPU replay by 0.99% at 512 environments and 0.84% at 2048 with matched PGO. The frozen full-training pipeline is effectively unchanged: mature score -0.02%, depth +0.04%. The cursor-tail experiment is a timing null and is parked. This is a validated small CPU improvement, with no demonstrated training-throughput improvement in these configurations.

All four requested steps are complete. Changes remain isolated; the live repository and retained engine are unchanged.

## Direct combined measurement

Baseline is movement_masks, immediately before the terrain/query subsystem rework. Candidate is movement_object_presence: flat terrain plus query summaries and the post-movement object-presence bit. These gains are incremental to that baseline, not gains over upstream or the original retained engine.

24 pinned workers, four submitters, 8192 ordinary warmup decisions per environment, two restored 1024-decision windows per process. Fresh processes in A-B-B-A order, ordinary GCC Release/LTO, no PGO. All endpoints agree.

| Environments | Before SPS | Combined SPS | Gain | Control drift |
|---|---:|---:|---:|---:|
| 512 | 284,256 | 290,155 | +2.08% | +0.51% |
| 2048 | 211,837 | 215,188 | +1.58% | -0.47% |

## Remaining movement phases

Sparse TSC scopes sample approximately one decision in 64. Counts cover actual floor searches. Diagnostic instrumentation changes code layout and adds timer/counter work; the following microseconds are diagnostic estimates, not production timings and must not replace the unchanged-binary profile. No thread migration/coroutine-crossing samples are silently included.

| Phase | 512 diagnostic us/decision | 2048 diagnostic us/decision |
|---|---:|---:|
| Object seeking | 14.87 | 18.76 |
| Neighbour queries | 13.84 | 16.22 |
| Destination selection | 9.03 | 8.80 |
| Movement/attack execution | 3.91 | 3.72 |
| Post-movement work | 7.32 | 9.07 |
| Setup, goals, flags and residual instrumentation | 24.12 | 25.56 |

The unchanged-binary profile from object_presence_20261009 remains the production reference: at 2048, neighbour queries are about 14.46 us/decision, other movement 40.09 us, and all remaining engine/observation work 75.09 us. The complete cost is distributed; neither moving a monster nor repeated SIMD tail checks dominate it.

The census finds about 37.9 floor searches and 211 iterator calls per policy decision. Those evaluate about 823 eight-entry coordinate blocks plus 139 scalar entries; about 146 vector entries revisit the preceding block. This is roughly 2.2% of vector lanes, so removing it has a limited ceiling. There are about 0.30 index rebuilds and 44 rebuilt object records per decision.

The diagnostic and disabled-instrumentation variants match 524,288 immutable mature hashes. Eight sampled decisions at 2048 were rejected for scheduling/timing interference; no crossing scopes were observed. Raw per-environment counts, timers, empty-scope calibration and mode-off overhead are in phases/.

## Focused experiment and gate

Candidate movement_cursor_advance skips the already-rejected tail of an eight-entry coordinate block when bounds are unchanged. It retains original list order, rebuild invalidation, changing-bound handling, overflow fallback and eligibility/RNG order. No extra persistent metadata. Patch: cursor.patch.

Both original and candidate pass 582,201 cursor queries against a scalar linked-list reference, including signed/extreme bounds, vector tails, overflow, query changes and live list mutations. Valgrind reports zero errors/leaks. Candidate passes the five unchanged golden/fuzz/status/interleaved/shuffled suites.

| Environments | Control SPS | Cursor SPS | Gain | Control drift |
|---|---:|---:|---:|---:|
| 512 | 289,994 | 289,768 | -0.08% | +0.33% |
| 2048 | 215,121 | 215,178 | +0.03% | +0.53% |

Predeclared screen: at least 1% at 2048, both candidate process means above both controls, and no more than 0.5% regression at 512.
Decision: PARK cursor candidate. Final source for validation: movement_object_presence.

## Matched PGO

Both sides were freshly built with identical compiler options and exactly the same eight score plus eight depth profile recordings. Profile-input hashes match. Sources, PGO inputs, profile data hashes, commands and libraries are archived separately. These profiles are trained on historical recordings; the measured replay uses the newer mature corpus. Only the known unexercised utility has missing-profile warnings; no coverage mismatch.

| Environments | Before PGO SPS | Final PGO SPS | Gain | Control drift |
|---|---:|---:|---:|---:|
| 512 | 317,687 | 320,816 | +0.99% | +0.44% |
| 2048 | 222,294 | 224,161 | +0.84% | +0.01% |

## Frozen full-training pipeline

2048 environments, horizon128, four buffers, 24 CPU workers, single GPU. Real policy forward/backward and PPO work, with optimizer application disabled. Environment actions are replayed from mature score/depth recordings, mapped to four copies of 512 original streams. Each process performs 96 batches; early epochs3–14 and mature epochs64–94 are reported. Same model and exact environment batches on both sides. This measures compute throughput, not learning quality or 2048 independent new games.

Each workload runs A-B-B-A serially with GPU occupancy checked first. Score uses the frozen 15.55M policy; depth uses its own smaller trained policy and recorded environment settings.

| Policy | Window | Before SPS | Final SPS | Gain | Control drift |
|---|---|---:|---:|---:|---:|
| score | early | 186,846 | 186,410 | -0.23% | -0.62% |
| score | mature | 184,956 | 184,914 | -0.02% | -0.28% |
| depth | early | 343,275 | 342,803 | -0.14% | +0.03% |
| depth | mature | 342,669 | 342,795 | +0.04% | +0.08% |

See pipeline.json for individual repeats, rollout/PPO tails, wall times, GPU monitoring and all batch proofs. Small gains comparable to between-process variation should be treated as neutral; CPU replay gains are not added to training gains.

## Correctness and preservation

- Each fresh PGO library matches 16,777,216 score and 16,777,216 depth decision hashes: 67,108,864 checks across both libraries, zero differences. Expectations were not regenerated.
- Both fresh PGO libraries pass all five golden/fuzz/status/interleaved/shuffled suites.
- All 96 environment-batch proofs agree across four processes for each of the two frozen policies; each final actor is byte-identical to its loaded checkpoint.
- All 6,469 protected source/library/reference files are unchanged. No live code edit, retained-engine change, commit or push.

## Interpretation

The flat/query-summary rework has a measurable ordinary-LTO gain, reduced to about 1% after PGO. In both full-pipeline workloads the measured mature rollout tail is zero: PPO finishes later. That is consistent with the engine gain being hidden by overlap, rather than shortening the critical path. Early pipeline windows change -0.23% for score and -0.14% for depth; there is no useful end-to-end gain here. The focused cursor-tail idea removes real redundant work but must earn its keep in native timing. PGO and full-pipeline numbers above are the deciding evidence for deployment; localized timer reductions do not establish an end-to-end gain.

Remaining cost is in repeated object seeking, neighbour eligibility and setup/goal work, plus the larger non-movement share. Hardware cache/TLB counters are still unavailable; this investigation does not claim a complete hardware miss-level decomposition or a hidden 2x cache fix.

The reviewable combined source diff is combined.patch. changed_files.json also records a differing generated Python bytecode cache, excluded from the source patch.

Artifacts: combined.patch, combined/, phases/, cursor/, selection.json, pgo_pair.json, pgo/, pipeline.json, cursor.patch, all commands and integrity manifests.
