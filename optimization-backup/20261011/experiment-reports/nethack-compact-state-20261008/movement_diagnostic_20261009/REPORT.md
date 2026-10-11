# Focused movement diagnosis — 9 October 2026

The user requested measurement of the cause before further optimisation variants. Pause quota/layout guessing; the next experiment should explain a measurable cost in the movement path.

## What is already measured

The fresh short native statistical profile contains 5,367 samples. Monster processing is 61.9% inclusive. `m_move` and `mfndpos` account for 19.9% and 18.4% self samples, respectively (38.2% combined before rounding). The earlier longer profile agrees: 62.6% inclusive and 38.4% combined self. These percentages overlap and must not be added.

This analysis reuses the paired 2048-game normal/burst profiles from locality_recheck_20261009. It does not run another benchmark or alter the engine. Annotated disassembly was produced in about six seconds per profile. Sampling shares are time attribution, not exact hardware stall counts.

## More specific evidence

A small standalone C helper, compiled against the current retained headers, confirms these layout offsets:

- Terrain grid: context +0x9af8, six bytes per cell. The terrain-type byte is +2.
- Floor-object pointer grid: context +0xc258, eight bytes per cell.
- Monster pointer grid: context +0xf6d8, eight bytes per cell.
- Object type: object +0x1e; coordinates at +0x1c/+0x1d.

Some of the largest individual sample sites in the two movement functions immediately follow these reads:

| Sample PC | Preceding operation verified in disassembly |
|---|---|
| 0x1ac364 | Floor-object pointer grid load in mfndpos |
| 0x1ac300 | Terrain-type byte load in mfndpos |
| 0x1ac4c8 | Monster pointer grid load in mfndpos |
| 0x1a6ee7 | Monster pointer grid load in m_move |
| 0x1a6e8f | Floor object's type load in m_move |

This points toward movement's data reads and their dependent checks, rather than establishing that the sampled test/branch/store instruction itself is intrinsically expensive. Sampling attribution can lag a load. No single listed PC accounts for the whole movement cost. Raw normal/burst sample counts are not directly comparable because the profile durations and sample totals differ.

Prior read-only selective prewarming established a causal data-locality penalty on an earlier engine: all selected groups reduced timed step CPU latency from141.33 to90.93 microseconds, but preparation cost54.59 microseconds. That was not a usable speedup. It does not supply an exact current-engine cache/TLB/branch breakdown or justify adding independent category effects.

## Measurement limitation

A fresh `perf stat -e cycles,instructions,cache-misses,branch-misses -- true` probe fails with no permission to enable cycles. `/proc/sys/kernel/perf_event_paranoid` is4. Hardware cache, branch and TLB counters are unavailable in this environment. No host settings were changed. The retained release library has no DWARF source-line sections, so the mapping above uses current compiled structure offsets and surrounding assembly, not fabricated line attribution.

## Next diagnostic and acceptance rule

Use the short matched mature replay to measure movement work frequency and sampled CPU latency separately: calls/decision, neighbours examined, floor objects scanned, and time in neighbour checks versus object selection. Preserve all original decisions and RNG draws; instrumentation is isolated and its overhead must be quantified. Use thread-local counters rather than contended global counters.

Then use a controlled read-only warming intervention targeted to the implicated data, reporting both preparation and function latency. The aim is to distinguish expensive repeated work from waiting for data, not to market prewarming as an optimisation. If needed, collect on a host exposing hardware counters to separate cache/TLB misses and branch stalls directly.

Before the next implementation candidate, require a concrete statement: this path costs X microseconds per decision, an isolated intervention removes Y, and the proposed implementation avoids the intervention's extra work. Do not infer a large speedup merely from a smaller allocation or the overall burst gap.

No new optimisation or causal timing result is claimed in this note. Raw disassembly, instruction samples, compile command and verified offsets are beside this file. No production edits, engine builds, commit, push or running job.
