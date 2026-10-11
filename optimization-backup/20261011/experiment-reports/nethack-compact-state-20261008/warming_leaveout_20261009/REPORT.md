# Selective warming omission study

Hardware counters are not required to narrow the relevant data groups causally. This bounded diagnostic leaves one group out of the previously effective pre-reading recipe, using the unchanged retained engine and ordinary one-action stepping.

## Results

Normal steps take 127.92 us; burst16 steps take 77.13 us. Full selected-data preparation reduces those to 87.54 and 76.61 us. The matched normal-minus-burst gap shrinks from 50.79 to 10.92 us: 39.87 us removed, consistent with the earlier result. This is not an optimization: preparation itself costs 73.26 us for a normal sampled step, versus 0.65 us for the timing-only control.

| Group omitted from full preparation | Extra step time, us | Game bootstrap 95% interval | Preparation saved, us |
|---|---:|---:|---:|
| context and grids | +17.31 | +16.72 to +17.87 | +26.75 |
| entity records | +0.10 | -0.19 to +0.40 | -1.57 |
| inventories and contents | +2.80 | +2.42 to +3.18 | +3.55 |
| saved coroutine stack | -0.17 | -0.58 to +0.26 | +0.85 |
| lazy allocations | +7.34 | +6.98 to +7.72 | +15.23 |
| nle context | -0.00 | -0.33 to +0.33 | +13.44 |

The largest conditional effects are the main game context including grids (+17.31 us), separately allocated auxiliary state (+7.34 us), and inventories/container contents (+2.80 us). The next useful experiment is to subdivide the first two groups into named fields/allocations. The current test does not identify one field or claim that these times are directly recoverable by a layout change.

The explicit saved-stack and NLE-context warming passes contribute no measurable incremental benefit in this recipe. Explicit full entity-record reads also add no measurable benefit here. This does NOT mean entity accesses are free: the inventory/content pass traverses the floor and monster lists and touches their headers, while other groups overlap at cache-line/page granularity. Omitting a pass also changes preparation order, pressure and elapsed preparation time. The estimates are conditional intervention effects, not an additive accounting of physical stalls. Their sum need not equal the whole benefit. Null estimates apply to this combination and workload only; jointly omitting several groups still needs a test.

## Protocol

- Retained engine SHA256: `2a5cfac52f27a7430383c00e0c2a84ae96cdc12c64c2decbb993aeea8ec2ce84`.
- 2048 instances repeat 512 distinct recorded games four times; warm 8192 decisions/game, measure the next 256. Original 24-worker pinned configuration, deterministic approximately 1/64 sample of steps. The aggregate estimates include both core types; individual trial P/E splits are in trials.csv.
- Two repetitions per condition in forward/reverse order. Twenty timing cases; 120.83 seconds total including 39.14 seconds of initial preparation. All cases restore the same single-thread snapshot, private game files and inherited file offsets, and settle before measuring.
- Eight proof cases, 512 games x 64 decisions each: 262,144 immutable per-decision hashes match, zero mismatches. All 28 proof/timing endpoint checks match their respective windows.
- Intervals bootstrap the 512 original games, grouping duplicate copies and repetitions, 2,000 resamples. They do not measure independent-machine uncertainty. Control step timing changes 127.49 to 128.36 us across the pass; full warming changes 87.72 to 87.36 us. The 17.31/7.34/2.80 us effects repeat in both orders; sub-us differences should not be treated as established gains.
- Instrumentation is harness-only. No engine or production changes, commits, pushes, PMU/host-setting changes, or new retained optimization. Preparation is reported explicitly. Timing only during sampled steps; displayed step latency is not end-to-end training throughput.

## Scope and next step

This adds a practical prioritization without claiming exact cache-level, TLB, branch or instruction-side attribution. Subdivide core context and auxiliary allocations, then require a native ordinary-rollout benefit including all upkeep before retaining any implementation. Small isolated floor-index changes have already been tested and did not recover the broad gap; do not repeat them under a new name.

All 8 protected production files, 1290 retained-source files, engine library and immutable reference hashes are unchanged. No experiment from this study remains running. Sources/build commands, protocol.json, raw logs/commands, CSVs, results.json and validation.json are in this directory.
