# Movement cost and locality diagnosis — 9 October 2026

## Findings

The extra cost of a larger population is not extra movement work in this matched replay. At512 and2048 games, movement calls, neighbour visits, returned floor-object candidates, search passes and accepted neighbours are exactly equal per original game and per decision. The same is true for ordinary versus burst16 stepping. This is a controlled comparison of the same recorded actions/states, not a comparison of independently sampled game populations.

On the unchanged retained PGO engine at2048 games, the sampled baseline step takes **128.90 microseconds of CPU time**. Read-only warming of floor-object records removes **9.73us**, with a game-clustered bootstrap interval8.96–10.55us. Warming all five selected groups removes **20.96us (16.3%)**. This establishes a data-locality penalty for these groups. It does not identify a particular cache level, TLB miss count or branch-stall count.

**No optimisation is retained.** Preparing the warmed data costs about as much as the step saves. All-five net saving is **-0.38us**, interval-0.96 to+0.20us. Small positive net effects for grids in this sampled diagnostic are not an all-step throughput result.

## Causal warming test: unchanged retained binary

24 pinned workers,4 pinned submitters,2048 envs (512 unique recorded games repeated4x), warm8192 decisions, measure512 decisions/env; ordinary one-action stepping. Each intervention has two trials in forward/reverse order with bracketing controls. Timing/prewarming occurs on the same deterministic1/64 sample of steps, leaving the normal surrounding workload intact. Each trial starts from the restored CPU snapshot, game files and file-descriptor offsets. Engine SHA256 remains `2a5cfac52f27a7430383c00e0c2a84ae96cdc12c64c2decbb993aeea8ec2ce84`.

| Data read before the step | CPU time removed from step, us (95% game bootstrap) | Extra preparation, us | Net CPU saving, us |
|---|---:|---:|---:|
| Terrain + type plane | 2.58 (2.26–2.90) | 2.25 | +0.33 |
| Floor-object pointer grid | 1.72 (1.43–2.03) | 2.45 | -0.73 |
| Monster pointer grid | 1.91 (1.62–2.19) | 2.29 | -0.38 |
| Floor-object records | 9.73 (8.96–10.55) | 11.93 | -2.20 |
| Monster records | 4.16 (3.72–4.60) | 4.19 | -0.03 |
| All three grids | 7.48 (7.08–7.87) | 6.14 | +1.34 |
| All five groups | 20.96 (19.84–22.14) | 21.34 | -0.38 |

Positive net means preparation plus step is cheaper. Group effects overlap and must not be added. The intervals resample512 original games, grouping all4 copies and repeated trials,2000 bootstrap samples; they measure variation across this corpus, not uncertainty across hardware/machine conditions. The reported preparation increment subtracts the same no-op preparation timing in control.

The P/E-core split supports the result independently: unchanged-engine step latency falls from115.55 to100.68us on P cores and141.09 to114.46us on E cores when all five groups are warmed. Core assignment is dynamic, not an exactly paired hardware execution. Few samples are excluded for preemption. Details and all per-core measurements are in measurements.csv.

## How much movement work occurs?

For the matched8192–8704 window, per policy decision:

-99.212 monster-movement entries.
-95.568 neighbour-finding calls.
-762.572 neighbouring cells examined.
-181.992 floor-object candidates returned to the search loop.
-38.142 floor-item search passes.
-256.025 accepted neighbour positions.

These are counts of the specified instrumented sites. They are not counts of all object accesses, instructions or cache misses. This mature recorded-action corpus can advance several game turns per policy decision. Exact count comparisons are in work_checks.json. Native warming has no engine counters; its zero counter fields are placeholders, and its correctness is checked with trajectory hashes.

## Timed paths and the remaining burst gap

The isolated instrumented engine has the same retained source but an ordinary GCC-LTO build, not fresh PGO. Its disabled-hook and counter overhead are measured below. Scope times contain instrumentation; they are diagnostic attribution, not exact retained-engine production costs.

| Instrumented path, us per sampled decision at2048 | Ordinary | Burst16 | Difference |
|---|---:|---:|---:|
| m_move, inclusive | 89.64 | 77.58 | 12.06 |
| mfndpos, inclusive | 35.89 | 32.70 | 3.19 |
| Floor-search block, inclusive | 17.54 | 13.07 | 4.46 |

These scopes overlap: m_move includes much of the neighbour and floor-search work. **Do not add their times.** The total sampled step falls from164.60 to125.34us, while the inclusive m_move saving is only12.06us. Thus movement does not explain the entire burst benefit; substantial cost is outside this measured scope. Do not attribute the residual to one cache or structure without another diagnostic. Burst16 consumes known future actions and is diagnostic only, not a viable ordinary training rollout change.

Within the same instrumented build, warming floor-object records cuts the floor-search block from17.54 to14.43us/decision. Warming all three grids cuts neighbour finding from35.89 to32.24us. This gives concrete paths to target, with gains in the few-microsecond range, rather than evidence for a2x win from compressing one grid.

The matching short512 window executes exactly the same work per decision as2048. Its instrumented sampled CPU time is135.82us versus164.60us at2048. The different default long512 window is not used to establish this equality.

## Instrumentation and rejected first attempt

The first diagnostic used CLOCK_THREAD_CPUTIME_ID inside every sampled nested scope. At roughly100 movement calls per policy decision, this inflated sampled steps severely (~330us). That attempt was stopped using verified owned PIDs, its private snapshot files removed, and its timings excluded. Files remain in sibling movement_causal_20261009 for audit.

The replacement uses invariant TSC for inner scopes, validated against a20ms CLOCK_MONOTONIC_RAW interval. An empty scope measures about22ns. Whole-step/preparation measurements still use the thread CPU clock. Stage timings are discarded when a sampled step has wall time above CPU time by more than10%+2us; scopes crossing a puf_step generation or physical CPU binding are excluded. Scope wall timing cannot distinguish individual hardware stall classes. Calibration does not remove all perturbation, including added branches, counters, register pressure and code layout.

| Games | Ordinary LTO control SPS | Diagnostic hooks disabled | Counts only | Counts + sparse timing | Disabled-build difference |
|---|---:|---:|---:|---:|---:|
| 512 | 263,065 | 247,122 | 239,637 | 239,886 | -6.06% |
| 2048 | 204,118 | 196,198 | 193,925 | 193,711 | -3.88% |

Native performance numbers here calibrate the diagnostic, not an optimisation. The modified build perturbs throughput4–6% with hooks disabled; this is why the causal warming result was independently confirmed by a harness-only helper against the unchanged retained PGO library. Sparse inner timing adds little overall overhead because it runs on1/64 steps, but it still raises the measured sampled steps by roughly23us. Absolute inner-scope costs must therefore be treated cautiously. Some interim log parsing overlapped diagnostic trials; no final unchanged-engine timing was run concurrently with builds or analysis.

Hardware PMU access remains denied (perf_event_paranoid4); no host settings were changed. Selective read-only warming establishes data-locality sensitivity, but does not isolate cache-vs-TLB mechanisms or instruction/branch contributions to the residual burst gap.

## Correctness and integrity

3,407,872 per-decision hashes match the pre-existing immutable reference, **zero differences**. They cover observations, rewards, terminal flags and masks, for sampled timing and all-group warming, including the unchanged-engine helper. All native endpoint checks and all counted-work comparisons passed. Scope is the tested mature score corpus, not full game-state proof; no engine change is being promoted, so full golden/fuzz/depth/training gates were not rerun.

All8 protected production files, all1290 retained source files, the retained library and reference hash remain unchanged. No production edits, commit or push. No diagnostic job remains.

## Next implementation decision

The strongest measured single data target is access to floor-object records. A justified next candidate is to reduce the full-object reads required during movement's floor-item search, starting with the object-type/coordinate reads already implicated by disassembly and the existing packed floor index. First identify exactly which metadata would need caching and every invalidation point; do not assume a smaller allocation helps. Require a fresh native comparison and unchanged trajectory hashes.

Budget expectations against the measured path saving: the instrumented floor-search block recovers about3us when its records are warmed; the unchanged-engine whole-step effect is about10us because those records also serve other code. The full10us is not automatically available from editing that single loop, and the20.96us combined effect is not an achieved speedup or a hard upper bound on all locality improvements.

Other justified targets are neighbour-grid accesses and costs outside m_move. The current measurements do not support another arbitrary scheduler quota or claiming that one structural rewrite will capture the full burst gap.

Artifacts: protocol.json, build_commands.json, instrumentation.patch, source-manifest.json, native_warm_commands.json, each runs/*/command.json and raw run.log/result.json, measurements.csv, effects.json, work_checks.json, final_summary.json, integrity.json. The snapshot/warming utilities are isolated diagnostic tools, not changes to production training.
