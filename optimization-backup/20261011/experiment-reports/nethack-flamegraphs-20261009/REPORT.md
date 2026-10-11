# NetHack CPU flame graphs

Open **index.html** in a browser. It is self-contained and works offline; no server, external scripts or installation needed. Click frames to zoom and use the search box or function shortcuts. Download individual SVGs from the page. SVG files, folded stacks, CSVs and summary.json are also included separately.

## Views

- Normal, burst16 and prepared-data normal stepping.
- Normal minus burst: width uses normal CPU time; red means more exclusive CPU time in normal, blue means less.
- Normal minus prepared data: highlights call paths sensitive to the data-warming intervention.
- All initial widths use the same microseconds-per-decision scale. Hover percentages within individual profiles refer to that profile; compare the absolute time figures across conditions.

## Measurements

| Condition | Unprofiled CPU µs / decision | Preparation µs / sampled decision | Stack samples |
|---|---:|---:|---:|
| normal | 128.587 | 0.645 | 8,458 |
| burst | 77.456 | 0.436 | 5,063 |
| warmed | 87.893 | 67.037 | 5,779 |

The base preparation timer includes about 0.4–0.6 µs of measurement overhead. Preparing game data is expensive and excluded from the step flame graph: this is not a proposed optimization. Burst replay requires known future actions and is not an ordinary training mode.

## Collection and limits

Retained engine SHA256: `2a5cfac52f27a7430383c00e0c2a84ae96cdc12c64c2decbb993aeea8ec2ce84`. Same recorded actions and unchanged engine as the preceding full-gap study. 2048 instances duplicate 512 distinct games four times. Warm 8192 decisions/game; measure 1024 per case. Three unprofiled calibration cases and two stack-profile repeats per condition. One fixed deterministic subset of approximately 1/64 decisions is selected identically in every condition.

Hardware and software `perf` events are unavailable here (`perf_event_paranoid=4`; `perf stat -e cpu-clock -- true` is denied). No host settings were changed. The collector uses per-thread CPU-clock timers at approximately 971 Hz, on dedicated signal stacks, and gperftools' libunwind-backed stack-trace API. Signals are retained only while puf_step is running on selected decisions. Preparation, scheduler waiting, warm-up and output writing are excluded.

The unwinder captures a signal handler and trampoline before the interrupted stack. Those two profiler frames are validated and stripped; compiler clone suffixes are normalized. NetHack coroutine stacks naturally terminate at `trampoline`, while direct caller-side work is rooted at `step_at`. The common `game step` root is a phase label, not an invented physical caller. Inlining and tail calls reflect the compiled binary. A handful of unresolved frame occurrences remain explicitly labelled; zero unwind fallbacks, depth-limit truncations or buffer drops occurred.

Stack proportions are scaled to unprofiled step times. Profiling adds about 7.4%/7.0%/8.1% to the sampled normal/burst/prepared steps; the separate calibration prevents charging this total overhead to the displayed times. This does not eliminate all sampling or observer effects. Fine differences and rare stacks should not be treated as established regressions. Large costs agree with the earlier higher-count program-counter profiles.

These flame graphs locate CPU execution cost. They do not count cache misses or independently distinguish cache levels, TLB misses, branch prediction or instruction delivery. Inclusive widths overlap vertically: do not sum a caller and its children. The CSV of self-time differences provides nonoverlapping function estimates.

## Tools and validation

- Collector: per-thread POSIX CPU timers + [gperftools](https://gperftools.github.io/gperftools/cpuprofile.html) with libunwind, operating on the unchanged engine.
- Renderer: [Brendan Gregg's FlameGraph](https://github.com/brendangregg/FlameGraph), commit `41fee1f99f9276008b7cd112fca19dc3ea84ac32`. Local display adaptations preserve fractional microseconds, make the artificial total frame show actual profile time under a common width scale, and use each profile's actual total for hover percentages. The embedded version tolerates browsers rejecting URL-history updates in srcdoc. Counts and stack structure are unchanged.
- 196,608 immutable per-decision hashes checked, zero mismatches. The nine main measurement cases match observations and world-turn endpoints. Engine and 8 protected production files unchanged.
- Browser-tested search and zoom in all five views, plus reset. A screenshot is included as preview.png.

## Reproduction

The complete experimental directory contains stacks.c/h, snapshot.c, diag.c, env_pool.h, setup.py, run.py, analyze.py, render.py, check_browser.py and finish.py. Raw stacks and memory maps are under runs/profiles2048. Each run's command.json records commands, environment and binary/library hashes. The plotting inputs are `*.folded`; their units are CPU microseconds per decision (`*.ns_per_decision.folded` explicitly use nanoseconds). `*.samples.folded` contain raw sample counts.

This portable folder contains the viewer, SVGs, summary, validation and folded/CSV data. No production changes were made and no optimization was retained.
