# Next substantial NetHack optimization: decision review

## Recommendation

For the requested standard-rollout engine work, the next substantial experiment should be bulk movement candidate filtering: obtain an ordered neighbour mask from terrain exclusions and current occupancy, then run the full rules only on survivors. This targets repeated work in the largest measured engine region. The new census and early-occupant-rejection screen below support the direction, but do not establish that the larger rewrite will produce a large gain. Keep the original path for capability combinations and interactions that the filter cannot safely exclude.

A separate, already measured route to larger gains is limiting the number of games actively advancing at once, while retaining every game and collecting the same complete training batch. That changes collection and is outside the preferred standard-rollout approach. It is an existing prototype, not a new speedup found in this turn. Do not silently substitute it for the requested engine work.

The prior grouped-rollout study used the older opt61-final engine. In its controlled 5.10M workload, 2048 resident games with 512 active games, four concurrent 128-game inference batches, and 128-step chunks ran at 211600 versus 165176 SPS (+28.1%). It executed real inference and all learner computation, with recorded actions and fixed weights. Thus it was not the future-action burst diagnostic. That magnitude must not be assumed for the newer engine.

Its bitwise limit matters: changing from 4x512 to 16x128 inference partitions changed floating-point forward results and eventual sampled actions. Keeping the same 16x128 partition and changing only scheduling matched real-update tests. Keeping the old four-buffer partition gave only about 2% with two active streams; one active stream regressed. The old live 15.55M-policy +8.6% comparison had diverging trajectories and is not a matched causal estimate.

Prior evidence: `/puffertank/experiments/nethack-grouped-rollouts-20261008/REPORT.md`.

No large new engine gain has yet been established. The strongest new incremental candidate is earlier movement rejection, measured below. Do not promise a 2x engine gain from the proposed candidate-mask work.

## New measurement: where a movement fast path could apply

512 distinct mature recorded games, 8192 warmup decisions each, then 512 decisions per game: 262144 checked decisions. Census counters are collected inside an isolated ordinary-LTO engine. Their timings are not used as performance measurements; extra reads and counters perturb execution. The census reproduces every immutable decision hash.

| Count | Per policy decision |
|---|---:|
| moves | 99.212 |
| neighbour_calls | 95.568 |
| cells | 762.572 |
| rock | 308.658 |
| room_corridor | 422.706 |
| object_cell | 28.497 |
| monster_cell | 181.168 |
| accepted | 256.025 |

Ordinary-monster guard coverage is 85.87% of neighbour calls. It excludes wall walkers/diggers, diagonal-restricted monsters, eels, temples, rogue levels, gas at the origin, and doorway origins. Only 14.97% of complete neighbourhoods also pass the exploratory simple-cell classification. These are diagnostic classes, not sufficient correctness conditions for replacing the whole function: tight squeezing and line flags still require handling.

Rock accounts for 40.48% of cells; occupied cells for 23.76%. These overlap. Only 33.57% of examined cells are finally accepted. This supports examining rejection order and eventually bulk candidate generation rather than assuming an entire-call shortcut applies everywhere. Counts are not fractions of CPU time.

## New native test: reject blocked occupants early

The isolated candidate changes only `src/mon.c`. After the existing rock rejection, it rejects an occupied neighbour when neither monster attacks nor displacement are permitted. Purple worms and monsters with displacement abilities keep the original path, as do the real and apparent hero positions. Confusion/blindness flag adjustments happen before the guard is derived. It skips later door/gas/diagonal/scary-square checks only for an already impossible occupied destination. The remaining ordering and game state transitions are unchanged.

Matched ordinary GCC-LTO builds; 24 workers plus 4 submitters; standard one-action scheduling. Each size uses control-A, candidate-A, candidate-B, control-B, with two snapshot trials per fresh process. Warm 8192 then settle 128 ordinary decisions. 2048 instances duplicate the same 512 streams four times. This is CPU replay, not training throughput. Snapshot trials are repeats, not independent games.

| Environments | Control SPS | Candidate SPS | Change | Control drift |
|---:|---:|---:|---:|---:|
| 2048 | 204,284 | 208,855 | +2.24% | +0.30% |
| 512 | 263,052 | 273,470 | +3.96% | +0.13% |

The first 512-game candidate process stopped at the harness thread_count()==1 assertion before snapshotting or measurement. The entire 512 block was rerun with new labels and the assertion unchanged; the failed attempt is preserved and excluded. This was not an observed game-state divergence.

This establishes a modest candidate worth preserving, not the sought large next step. It is parked pending fresh PGO, fresh-process confirmation, full score/depth trajectory checks and full-pipeline tests. No production change or retention claim.

Movement and neighbour checks cost roughly 47us of the roughly 131us ordinary step in the existing full-gap profile. Halving that entire region would imply about 22% CPU throughput improvement if everything else stayed fixed; this is an Amdahl scenario, not a measured achievable gain. Neighbour finding alone is about 17% of the separate flame-graph profile. Optimizing a fraction of it cannot credibly promise a 2x overall win.

## Concrete next gate

1. Prototype a conservative eight-neighbour candidate mask. For monsters unable to walk through or dig rock, discard those rock cells in bulk. For monsters unable to attack/displace occupants, discard occupied cells except the real/apparent hero positions. Preserve the original x/y candidate order. Retain the existing full logic for doors, gas, traps, fear, tight squeezing, special abilities and all survivors.
2. Measure the complete cost, including maintaining terrain/occupancy summaries on changes. The existing terrain setter and monster placement/removal paths need an exhaustive writer audit; avoid replacing authoritative game state with an unchecked cache. First compare filter outputs against the original selection and preserve immutable trajectory/RNG expectations.
3. Screen under ordinary scheduling against the current source with matched compilation. Require a repeatable >=5% native gain for the substantial-change track. Reject quickly if extra maintenance or memory traffic cancels the eliminated checks. The census is not evidence that 66% of neighbour CPU time can be removed.
4. For a winner, perform fresh PGO, full score/depth trajectory and early-game gates, then frozen-policy full-pipeline comparisons on both the CPU-limited small-model workload and the real 15.55M policy. Report CPU and end-to-end gains separately.
5. If collection changes become acceptable, revisit the already proven grouped prototype on the latest engine, comparing both a fixed new inference partition and the old partition. Its historical +28% must be remeasured before projecting to 8192 resident games.

## Validation and state

Census: 262144 immutable per-decision hashes, zero differences. Candidate: all five golden/fuzz/status/interleaved/shuffled suites, plus 262144 mature decision hashes, zero differences. All native endpoints match. These are bounded checks, not full corpus validation or a proof for all game states.
1299 protected/source/library files and the immutable reference remain unchanged. No production changes, commits, pushes or new goal. All experiment jobs finished.

Artifacts: `prepare.py`, `instrumentation.patch`, `counter_names.json`, `per_game.csv`, `totals.json`, `runs/census512/`; candidate patch and timing data are in `../engines/neighbour_prefilter/`. Exact engine/harness hashes and commands are recorded per run.
