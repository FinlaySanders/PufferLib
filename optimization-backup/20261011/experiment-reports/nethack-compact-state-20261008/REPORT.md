# NetHack compact state and scheduling campaign

Active, open-ended campaign. Baseline: retained persist engine (glyph16 + persistent floor index on opt61). Production files untouched.

## Experiments

| Candidate | Hypothesis | Status |
|---|---|---|
| property32 | Halve property records to reduce frequently accessed hero state | Quick gates pass; <1% initial gains, not retained |
| local-first | Drain own lanes across ready buffers before stealing | +0.03%, parked |
| lookahead prefetch | Overlap loading next assigned game with current game | Broad prefetch -0.7% to -5.0%, parked |

The current retained compiled engine is rawglyph_pgo; RETAINED_SOURCE.json preserves its ordinary-LTO source reference. See RETAINED.json and the confirmation sections below. Earlier entries preserve the chronological decisions. Fresh starting controls, exact commands and hashes are recorded in BASELINE.json and runs/.

## First native screens

All timings below use standard recorded-action rollouts, not bursts. 2048-game screens replay the same512 unique trajectories four times; timing repeats are machine repeats, not additional independent games.

| Candidate | Control SPS | Candidate SPS | Difference | Interpretation |
|---|---:|---:|---:|---|
| property32,2048 |200931|201701|+0.38%|Small, unconfirmed; not retained|
| property32,512 |283108|285839|+0.96%|Small, unconfirmed; not retained|
| local-first,2048 |201510|201579|+0.03%|Null, parked|
| reserve-next,no prefetch |201510|201274|-0.12%|Reservation control|
| lookahead hero/RNG |201274|199870|-0.70%|No gain|
| lookahead hero/RNG/map/glyph |201274|192138|-4.54%|Regression; fetching broad arrays is costly|

All completed screens reproduce final hash b97835c62aaf388f and identical world-turn counts for their environment count. These are end-state checks; they are not a replacement for the full every-decision gate before retention. Property32 also passes all quick gates and preserves the legacy hero save format. Prefetch overhead is included in SPS but excluded from the per-step timer, so SPS is the deciding measurement.

Independent prototypes prepared: terrain16 (8->6-byte terrain cells, legacy save conversion) and obj88 (32-bit equipment/migration flags in the old padding, 96->88-byte objects, original quantities/age preserved and legacy save conversion). Both built and passed 34 goldens, 26 fuzz trajectories, status-disabled, interleaved and shuffled quick gates. Both native windows matched end-state hashes. Object and terrain save-format conversions pass focused roundtrip tests. No full every-decision gate has been run for these unretained prototypes.

## Object-layout follow-up

Initial 512 screen (+8.4%) did not reproduce. Three fresh controls: 291,181, 286,537, 304,982 SPS; three candidates: 298,199, 287,755, 287,086 SPS. Candidate mean vs these controls: -1.09%. The ranges overlap substantially. Parked as a throughput optimization; measure source-touched lines to understand why allocation savings did not yield a reliable gain.

Layout checks: object sizeof96->88, glibc usable104->88; terrain cell8->6, grid13440->10080; hero2400->1584 for property32. Legacy record roundtrips passed.

Next: shared immutable object metadata (284 read sites; appearance, discovery, material, probability and direction stay per game) and next-monster prefetch within a game.

## Further independent screens

Shared immutable object metadata (284 reads) gives 199,702 SPS at2048 and295,362 at512. Next-monster prefetch gives201,344 and287,740. Both are inside observed control spread; parked without promotion. All quick gates and native end-state checks pass.

The obj88 source-level trace compares exactly the first four mature decisions in512 matching games (2,048 decisions). Mean touched footprint61.0741->60.1505 KiB (-1.51%). Hero inventory5.6271->4.9955; monster inventory1.4193->1.1354; floor objects4.0413->4.0081. This explains why reducing allocation size did not deliver a large overall speedup. Source instrumentation excludes libc/spills/wrapper and is not a hardware miss counter. Raw captures, commands and categorized CSV: trace_obj88/.

Hot context packing: the first candidate failed the initial golden replay. A debugger watch identified an existing lock-state overlay requiring an adjacent region. Excluding that entire region restores all quick gates. The repaired candidate moves70 small fields (778 payload bytes), leaving types and initializers unchanged. Native measurements are pending. Details in LAYOUT_CONSTRAINT.md.

Prepared monster120: narrow bounded strategy/trap/equipment/state bitmaps to32bits and reorder tail fields; preserve64-bit world time and32-bit HP/timeouts. Target144->120bytes, legacy save conversion. Pending compilation, layout/roundtrip check, gates and timings.

## Latest layout screens and next hypotheses

Repaired hotpack:202,868 SPS at2048;287,436 at512. Mon120:202,119 SPS at2048;287,450 at512. Both reproduce the unchanged final observation hash and world-turn counts. The fresh2048 control is201,458 SPS, making these small, unconfirmed differences. Neither is retained.

Monster layout is120bytes, usable allocation120 instead of baseline144/152. Legacy144-byte wire representation roundtrips correctly, including the all-traps sentinel and full-width HP/time values.

The compact bundle combines property32, obj88, terrain16, mon120, separate glyph/dirty planes and compact inventory export. It passes all quick gates and the monster conversion test. Its native screen is running. This tests aggregate footprint reduction and any cache-capacity threshold; independent percentages are not added.

Prepared next candidate monhot keeps the120-byte record but places movement/status fields in its first48bytes, aiming to reduce the number of lines needed by common monster-loop checks. This is distinct from merely narrowing cold tail masks. Source generation is prepared; no performance claim yet.

Earlier main-context huge pages were already measured in nethack-memory-locality-20261008 (4GiB huge pages verified, small gain but expensive reset/RSS). Do not repeat that idea without a different target or new evidence.


## Compact combination confirmation

Two fresh2048 controls average200,274 SPS; two compact-bundle runs average208,520 (+4.12%). Two longer512 controls (8192 measured decisions/game) average295,707; candidates309,735 (+4.74%). The independent short512 window was noisy and initially negative. Four early512 pairs average456,419 vs463,867 (+1.63%), but individual results range441–471k controls and442–489k candidates; no consistent early regression or reliable early gain established.

All these windows have identical final observations and world-turn counts. The full16,777,216-decision comparison is now running; the bundle remains unretained pending that gate and full-pipeline measurements. Expanded legacy monster roundtrip passes. The next independent candidate monhot is being built while correctness replay runs; no native performance measurement will overlap those jobs.

## First full-pipeline comparison

The compact bundle passes16,777,216 unchanged-reference decision hashes with zero differences. Golden/fuzz/status/interleaved/shuffled gates and expanded monster save conversion also pass.

Actual frozen4B score policy (15,552,136 parameters),2048 environments, original four buffers, horizon128, batch262144, minibatch4096,24 workers; inference and full PPO/optimizer computation, recorded mature actions. Baseline179,743 SPS; bundle183,468 (+2.07%). Rollout-tail wait0.0472->0.0111 seconds/batch. All96 batch observation proofs and both initial/final weight hashes match. This is the first pair; confirmation is pending. Exact settings and library hashes are in run command manifests. Native CPU and full training gains are deliberately kept separate.

monhot passed the quick gates and expanded legacy conversion test; native timing is in progress. Next prepared candidate is per-game object allocation, aimed at heap locality rather than smaller records (OBJECT_POOL_AUDIT.md).

## Object allocation and aligned monster follow-ups

monhot alone is parked:197,007 SPS at2048 and294,278 at512 (8192 measured decisions/game), below recent controls. Quick gates and legacy conversion pass, and native hashes/turns match; smaller/hotter-looking layout alone is insufficient.

objpool preserves the original96-byte record but allocates each game's objects in128-slot blocks. All quick gates pass. The lifecycle test checks growth, reuse, four-game isolation and80 teardowns; Valgrind reports zero errors and zero definite/indirect/possible leaks (84,889 bytes remain reachable in library/runtime allocations). Native screens are running.

A distinct monhot_pool prototype is prepared:120-byte records occupy aligned128-byte slots, ensuring the leading48-byte status/movement region actually sits in one physical cache line. Plain malloc did not guarantee that alignment. It reuses the previous per-game monster-pool lifetime integration. This is a new hypothesis combining field placement and physical alignment, not a claim that the parked standalone pool won. Pending build and tests.

The footprint instrumentation is extended to include explicit memcpy/memmove/memset spans in both a fresh baseline and candidate trace. This prevents loop-to-memcpy transformations from appearing to eliminate reads merely because the earlier instrumentation omitted library calls. These diagnostic builds are excluded from native timings.


## Object pool first native screen

Per-game object storage:204,479 SPS at2048 and307,666 at512 with8192 measured steps. These are about+2.1% and+4.0% against recent controls, but remain single screens without fresh adjacent repeats. Native end-state hashes and world-turn counts match. RSS at2048 is1,484,180 KiB vs latest control1,465,268 (+1.3%). A compact_bundle+objpool source combination is prepared, not yet built; gains will be measured directly, not added.

## Full-pipeline confirmation

Reverse-order pair:178,673->182,572 SPS (+2.18%), following+2.07% in the first pair. Pooled across the two timing repeats:179,208->183,020 (+2.13%). Both pairs have96 matching batch proofs and identical frozen weight hashes. Early windows (batches3–14) were-0.50% and+0.44%, effectively flat. This is the actual15.55M score policy with all inference/PPO/optimizer work, driven by fixed mature score actions; it is not a smaller random-net timing.

Source-access baseline and candidate captures including explicit memory-copy operations are underway. monhot_pool and compact_pool are being built and correctness-tested concurrently with the instrumented diagnostic capture; no native timings overlap those jobs.

## Retained compact bundle

Retained in the isolated experiment tree; production remains untouched. Two2048 native pairs give+4.12%, two longer512 pairs+4.74%, and two15.55M full-pipeline pairs+2.13%. Early full-pipeline performance is flat across the two pairs. The unchanged-reference16,777,216-decision gate passes, both96-batch training proofs match, and weights remain identical.

Revised traces include explicit memory-copy operations on both sides:62.0968->53.9135 KiB/decision (-13.18%) over the same2048 mature decisions in512 games. Four-step per-game union78.9274->71.0681 KiB. Biggest reductions: glyph buffer3.1503 KiB, inventory-export backing storage about2.65 KiB (resolved by first-touch PCs in fill_obs), hero state0.7161, monster records0.6940, hero inventory0.6234, monster inventory0.2788, terrain0.2155. Inventory cache adds0.2152 KiB in the RL port. Raw category attribution depends on shared cache-line boundaries; these are traced access lines, not hardware cache misses. Both instrumented final states match the independently recorded unchanged-native reference.

Artifacts: RETAINED.json, COMPACT_SUMMARY.json, compact_source_hashes.json, trace_compact_bundle_copies/comparison.csv, trace_unclassified_attribution.json. All combined gains remain relative to the original persist baseline, not an updated denominator.


## First follow-up combination screens

Fresh long512 baseline295,136 SPS. Aligned hot-prefix monster pool305,755 (+3.60%); compact state+object pool320,398 (+8.56%). Both match the original long-window end-state hash and28,706,962 world-turn advances. These are single screens, not retained. The aligned and compact pools also pass all quick gates, expanded monster legacy roundtrips, and Valgrind lifecycle checks with zero errors/lost allocations.2048 confirmation screens are running; repeated timing and every-decision checks remain required before retention.

Integrity recheck: all1282 original baseline source files and all8 protected live source files match starting hashes (integrity_final.json).


## Current native measurements

Single screens until explicitly repeated. Standard replay; overhead included in SPS. Warm/measured decisions are per game.

| Run | Workload | Games | Warm | Measured | Decisions/s | Sampled step CPU us |
|---|---|---:|---:|---:|---:|---:|
| baseline2048_a | score | 2048 | 8192 | 2048 | 200,931 | 139.56 |
| baseline2048_b | score | 2048 | 8192 | 2048 | 198,998 | 140.69 |
| baseline2048_c | score | 2048 | 8192 | 2048 | 201,458 | 139.04 |
| baseline2048_d | score | 2048 | 8192 | 2048 | 199,089 | 140.47 |
| baseline2048_e | score | 2048 | 8192 | 2048 | 198,885 | 141.11 |
| baseline2048_f | score | 2048 | 8192 | 2048 | 199,029 | 140.67 |
| baseline512_a | score | 512 | 8192 | 2048 | 283,108 | 96.49 |
| baseline512_b | score | 512 | 8192 | 2048 | 291,181 | 93.77 |
| baseline512_c | score | 512 | 8192 | 2048 | 286,537 | 95.34 |
| baseline512_d | score | 512 | 8192 | 2048 | 304,982 | 89.45 |
| baseline512_e | score | 512 | 8192 | 2048 | 305,159 | 89.51 |
| baseline512_early_a | score | 512 | 0 | 2048 | 470,632 | 56.33 |
| baseline512_early_b | score | 512 | 0 | 2048 | 443,572 | 59.53 |
| baseline512_early_c | score | 512 | 0 | 2048 | 440,993 | 60.75 |
| baseline512_early_d | score | 512 | 0 | 2048 | 470,478 | 56.74 |
| baseline512_early_e | score | 512 | 0 | 2048 | 416,555 | 63.06 |
| baseline512_long_a | score | 512 | 8192 | 8192 | 296,043 | 92.94 |
| baseline512_long_b | score | 512 | 8192 | 8192 | 295,371 | 93.15 |
| baseline512_long_c | score | 512 | 8192 | 8192 | 295,136 | 92.99 |
| baseline512_long_d | score | 512 | 8192 | 8192 | 295,579 | 92.99 |
| clang_lto_512_control_a | score | 512 | 8192 | 8192 | 326,945 | 84.07 |
| clang_lto_tls_512_control_a | score | 512 | 8192 | 8192 | 348,617 | 78.83 |
| compact_bundle512_early_a | score | 512 | 0 | 2048 | 443,281 | 60.08 |
| compact_bundle512_early_b | score | 512 | 0 | 2048 | 489,063 | 54.42 |
| compact_bundle512_early_c | score | 512 | 0 | 2048 | 480,989 | 55.37 |
| compact_bundle512_early_d | score | 512 | 0 | 2048 | 442,135 | 59.92 |
| compact_bundle_2048_a | score | 2048 | 8192 | 2048 | 207,131 | 134.95 |
| compact_bundle_2048_b | score | 2048 | 8192 | 2048 | 209,909 | 133.59 |
| compact_bundle_512_a | score | 512 | 8192 | 2048 | 296,752 | 91.60 |
| compact_bundle_512_long_a | score | 512 | 8192 | 8192 | 312,078 | 87.97 |
| compact_bundle_512_long_b | score | 512 | 8192 | 8192 | 307,392 | 89.44 |
| compact_pool512_early_a | score | 512 | 0 | 2048 | 499,572 | 52.84 |
| compact_pool_2048_a | score | 2048 | 8192 | 2048 | 214,295 | 131.04 |
| compact_pool_2048_b | score | 2048 | 8192 | 2048 | 215,842 | 129.91 |
| compact_pool_512_long_a | score | 512 | 8192 | 8192 | 320,398 | 85.59 |
| compact_pool_512_long_b | score | 512 | 8192 | 8192 | 322,430 | 85.13 |
| compact_pool_512_long_c | score | 512 | 8192 | 8192 | 318,973 | 86.01 |
| compact_pool_512_long_d | score | 512 | 8192 | 8192 | 319,191 | 85.98 |
| context_slab_512_candidate | score | 512 | 8192 | 8192 | 325,828 | 84.32 |
| context_slab_512_control_a | score | 512 | 8192 | 8192 | 327,868 | 83.63 |
| context_slab_512_control_b | score | 512 | 8192 | 8192 | 325,228 | 84.39 |
| context_slab_confirm_early_candidate_a | score | 512 | 0 | 2048 | 483,544 | 54.59 |
| context_slab_confirm_early_control_a | score | 512 | 0 | 2048 | 493,277 | 53.51 |
| context_slab_confirm_early_control_b | score | 512 | 0 | 2048 | 461,442 | 57.88 |
| context_slab_confirm_large_candidate_a | score | 2048 | 8192 | 2048 | 220,058 | 127.62 |
| context_slab_confirm_large_candidate_b | score | 2048 | 8192 | 2048 | 218,141 | 128.61 |
| context_slab_confirm_large_control_a | score | 2048 | 8192 | 2048 | 218,738 | 128.38 |
| context_slab_confirm_large_control_b | score | 2048 | 8192 | 2048 | 216,926 | 129.94 |
| floor_bounds_once_512_candidate | score | 512 | 8192 | 8192 | 323,521 | 84.85 |
| floor_bounds_once_512_control_a | score | 512 | 8192 | 8192 | 321,625 | 85.27 |
| floor_bounds_once_512_control_b | score | 512 | 8192 | 8192 | 322,301 | 85.25 |
| fobj_bytes_512_candidate | score | 512 | 8192 | 8192 | 323,040 | 84.84 |
| fobj_bytes_512_control_a | score | 512 | 8192 | 8192 | 321,592 | 85.31 |
| fobj_bytes_512_control_b | score | 512 | 8192 | 8192 | 321,715 | 85.37 |
| fobj_hit_prefetch_512_candidate | score | 512 | 8192 | 8192 | 321,018 | 85.45 |
| fobj_hit_prefetch_512_control_a | score | 512 | 8192 | 8192 | 323,389 | 84.95 |
| fobj_hit_prefetch_512_control_b | score | 512 | 8192 | 8192 | 322,078 | 85.26 |
| fobj_inline_512_candidate | score | 512 | 8192 | 8192 | 326,191 | 84.11 |
| fobj_inline_512_control_a | score | 512 | 8192 | 8192 | 328,167 | 83.64 |
| fobj_inline_512_control_b | score | 512 | 8192 | 8192 | 324,976 | 84.49 |
| fobj_nonrock_2048_candidate | score | 2048 | 8192 | 2048 | 219,417 | 127.78 |
| fobj_nonrock_2048_control_a | score | 2048 | 8192 | 2048 | 221,788 | 126.60 |
| fobj_nonrock_2048_control_b | score | 2048 | 8192 | 2048 | 215,695 | 129.74 |
| fobj_nonrock_512_candidate | score | 512 | 8192 | 8192 | 330,505 | 83.08 |
| fobj_nonrock_512_control_a | score | 512 | 8192 | 8192 | 329,470 | 83.30 |
| fobj_nonrock_512_control_b | score | 512 | 8192 | 8192 | 322,723 | 85.04 |
| gcc_tune_native_512_candidate_a | score | 512 | 8192 | 8192 | 329,724 | 83.24 |
| gcc_tune_native_512_candidate_b | score | 512 | 8192 | 8192 | 327,789 | 83.80 |
| gcc_tune_native_512_control_a | score | 512 | 8192 | 8192 | 332,784 | 82.60 |
| gcc_tune_native_512_control_b | score | 512 | 8192 | 8192 | 328,353 | 83.67 |
| glyph_dirty_bits_512_candidate_a | score | 512 | 8192 | 8192 | 326,577 | 84.08 |
| glyph_dirty_bits_512_candidate_b | score | 512 | 8192 | 8192 | 326,635 | 84.22 |
| glyph_dirty_bits_512_control_a | score | 512 | 8192 | 8192 | 328,728 | 83.41 |
| glyph_dirty_bits_512_control_b | score | 512 | 8192 | 8192 | 327,989 | 83.69 |
| glyph_fill_memo_512_candidate | score | 512 | 8192 | 8192 | 318,833 | 86.22 |
| glyph_fill_memo_512_control_a | score | 512 | 8192 | 8192 | 328,384 | 83.62 |
| glyph_fill_memo_512_control_b | score | 512 | 8192 | 8192 | 322,907 | 85.12 |
| glyph_fused_export_512_candidate_a | score | 512 | 8192 | 8192 | 333,451 | 82.49 |
| glyph_fused_export_512_candidate_b | score | 512 | 8192 | 8192 | 332,458 | 82.76 |
| glyph_fused_export_512_control_a | score | 512 | 8192 | 8192 | 332,083 | 82.64 |
| glyph_fused_export_512_control_b | score | 512 | 8192 | 8192 | 333,223 | 82.40 |
| glyph_fused_tail8_512_candidate_a | score | 512 | 8192 | 8192 | 331,791 | 82.81 |
| glyph_fused_tail8_512_candidate_b | score | 512 | 8192 | 8192 | 329,217 | 83.73 |
| glyph_fused_tail8_512_control_a | score | 512 | 8192 | 8192 | 332,855 | 82.53 |
| glyph_fused_tail8_512_control_b | score | 512 | 8192 | 8192 | 327,776 | 83.88 |
| grid_tiles_both_2048_a | score | 2048 | 8192 | 2048 | 214,960 | 130.49 |
| grid_tiles_control2048_a | score | 2048 | 8192 | 2048 | 220,219 | 127.24 |
| grid_tiles_control2048_b | score | 2048 | 8192 | 2048 | 215,559 | 129.74 |
| grid_tiles_mon_2048_a | score | 2048 | 8192 | 2048 | 217,223 | 129.21 |
| hotpack_2048_a | score | 2048 | 8192 | 2048 | 202,868 | 138.09 |
| hotpack_512_a | score | 512 | 8192 | 2048 | 287,436 | 95.04 |
| interest_first_512_candidate | score | 512 | 8192 | 8192 | 330,614 | 82.96 |
| interest_first_512_control_a | score | 512 | 8192 | 8192 | 342,472 | 80.19 |
| interest_first_512_control_b | score | 512 | 8192 | 8192 | 323,439 | 84.84 |
| inv_export_fused_512_candidate_a | score | 512 | 8192 | 8192 | 335,155 | 82.08 |
| inv_export_fused_512_candidate_b | score | 512 | 8192 | 8192 | 335,252 | 81.93 |
| inv_export_fused_512_control_a | score | 512 | 8192 | 8192 | 328,233 | 83.71 |
| inv_export_fused_512_control_b | score | 512 | 8192 | 8192 | 334,168 | 82.09 |
| inv_export_known_first_512_candidate_a | score | 512 | 8192 | 8192 | 327,965 | 83.80 |
| inv_export_known_first_512_candidate_b | score | 512 | 8192 | 8192 | 327,991 | 83.82 |
| inv_export_known_first_512_control_a | score | 512 | 8192 | 8192 | 327,784 | 83.80 |
| inv_export_known_first_512_control_b | score | 512 | 8192 | 8192 | 329,863 | 83.10 |
| invweight_prefetch_512_candidate | score | 512 | 8192 | 8192 | 327,555 | 84.01 |
| invweight_prefetch_512_control_a | score | 512 | 8192 | 8192 | 327,125 | 84.12 |
| invweight_prefetch_512_control_b | score | 512 | 8192 | 8192 | 329,810 | 83.33 |
| keys_once_512_a | score | 512 | 8192 | 8192 | 319,917 | 85.84 |
| large_followup_control_a | score | 2048 | 8192 | 2048 | 218,983 | 128.34 |
| large_followup_control_b | score | 2048 | 8192 | 2048 | 217,336 | 128.99 |
| large_followup_monster | score | 2048 | 8192 | 2048 | 220,448 | 127.12 |
| large_followup_slab | score | 2048 | 8192 | 2048 | 221,084 | 126.77 |
| localfirst2048_a | score | 2048 | 8192 | 2048 | 201,579 | 139.28 |
| lookahead_mode0_2048_a | score | 2048 | 8192 | 2048 | 201,274 | 139.06 |
| lookahead_mode1_2048_a | score | 2048 | 8192 | 2048 | 199,870 | 138.62 |
| lookahead_mode2_2048_a | score | 2048 | 8192 | 2048 | 192,138 | 140.00 |
| lookahead_mode3_2048_a | score | 2048 | 8192 | 2048 | 191,161 | 132.73 |
| mon120_2048_a | score | 2048 | 8192 | 2048 | 202,119 | 138.76 |
| mon120_512_a | score | 512 | 8192 | 2048 | 287,450 | 95.08 |
| mon_grid16_2048_gridtest | score | 2048 | 8192 | 2048 | 217,998 | 128.74 |
| mon_grid16_512_candidate | score | 512 | 8192 | 8192 | 326,723 | 84.01 |
| mon_grid16_512_control_a | score | 512 | 8192 | 8192 | 323,906 | 84.77 |
| mon_grid16_512_control_b | score | 512 | 8192 | 8192 | 327,693 | 83.86 |
| mon_grid32_2048_gridtest | score | 2048 | 8192 | 2048 | 214,856 | 130.48 |
| mon_grid32_512_gridtest | score | 512 | 8192 | 8192 | 327,822 | 83.69 |
| mon_grid_control2048_a | score | 2048 | 8192 | 2048 | 217,197 | 128.63 |
| mon_grid_control2048_b | score | 2048 | 8192 | 2048 | 217,143 | 129.31 |
| mon_grid_control512_a | score | 512 | 8192 | 8192 | 328,274 | 83.79 |
| mon_grid_control512_b | score | 512 | 8192 | 8192 | 323,189 | 84.99 |
| mon_neighbor_prefetch_512_candidate | score | 512 | 8192 | 8192 | 329,327 | 83.41 |
| mon_neighbor_prefetch_512_control_a | score | 512 | 8192 | 8192 | 330,016 | 83.33 |
| mon_neighbor_prefetch_512_control_b | score | 512 | 8192 | 8192 | 333,557 | 82.31 |
| mon_occupancy_bits_2048_a | score | 2048 | 8192 | 2048 | 215,233 | 130.23 |
| mon_occupancy_bits_512_a | score | 512 | 8192 | 8192 | 320,877 | 85.52 |
| mon_occupancy_bytes_2048_a | score | 2048 | 8192 | 2048 | 214,764 | 130.29 |
| mon_occupancy_bytes_512_a | score | 512 | 8192 | 8192 | 321,489 | 85.29 |
| mon_occupancy_control2048_a | score | 2048 | 8192 | 2048 | 214,328 | 130.84 |
| mon_occupancy_control2048_b | score | 2048 | 8192 | 2048 | 214,808 | 130.52 |
| mon_occupancy_control512_a | score | 512 | 8192 | 8192 | 318,113 | 86.25 |
| mon_occupancy_control512_b | score | 512 | 8192 | 8192 | 320,179 | 85.75 |
| mon_split64_score512_candidate_a | score | 512 | 8192 | 8192 | 323,727 | 84.68 |
| mon_split64_score512_candidate_b | score | 512 | 8192 | 8192 | 325,690 | 84.21 |
| mon_split64_score512_control_a | score | 512 | 8192 | 8192 | 327,385 | 83.92 |
| mon_split64_score512_control_b | score | 512 | 8192 | 8192 | 331,596 | 82.84 |
| monhot_2048_a | score | 2048 | 8192 | 2048 | 197,007 | 142.22 |
| monhot_512_long_a | score | 512 | 8192 | 8192 | 294,278 | 93.44 |
| monhot_pool_2048_a | score | 2048 | 8192 | 2048 | 200,741 | 139.48 |
| monhot_pool_512_long_a | score | 512 | 8192 | 8192 | 305,755 | 90.04 |
| monmove_guard_pgo_combined_score2048_candidate | score | 2048 | 8192 | 2048 | 227,435 | 123.20 |
| monmove_guard_pgo_combined_score2048_original | score | 2048 | 8192 | 2048 | 196,687 | 143.09 |
| monmove_guard_pgo_combined_score512_candidate | score | 512 | 8192 | 8192 | 367,676 | 74.80 |
| monmove_guard_pgo_combined_score512_original | score | 512 | 8192 | 8192 | 294,520 | 93.52 |
| monmove_guard_pgo_confirm2048_candidate_a | score | 2048 | 8192 | 2048 | 231,951 | 121.05 |
| monmove_guard_pgo_confirm2048_candidate_b | score | 2048 | 8192 | 2048 | 230,520 | 121.66 |
| monmove_guard_pgo_confirm2048_control_a | score | 2048 | 8192 | 2048 | 227,575 | 123.50 |
| monmove_guard_pgo_confirm512_candidate_a | score | 512 | 8192 | 8192 | 370,412 | 74.20 |
| monmove_guard_pgo_confirm512_candidate_b | score | 512 | 8192 | 8192 | 363,673 | 75.46 |
| monmove_guard_pgo_confirm512_control_a | score | 512 | 8192 | 8192 | 362,373 | 75.90 |
| monmove_guard_pgo_confirm512_control_b | score | 512 | 8192 | 8192 | 360,310 | 76.22 |
| monmove_guard_pgo_depth2048_candidate_a | depth | 2048 | 8192 | 2048 | 470,399 | 59.40 |
| monmove_guard_pgo_depth2048_control_a | depth | 2048 | 8192 | 2048 | 463,304 | 60.44 |
| monmove_guard_pgo_depth2048_control_b | depth | 2048 | 8192 | 2048 | 462,198 | 60.46 |
| monmove_guard_pgo_early512_candidate_a | score | 512 | 0 | 2048 | 570,418 | 46.23 |
| monmove_guard_pgo_early512_control_a | score | 512 | 0 | 2048 | 553,527 | 46.96 |
| monmove_guard_pgo_early512_control_b | score | 512 | 0 | 2048 | 546,790 | 47.76 |
| monmove_line_2048_candidate | score | 2048 | 8192 | 2048 | 220,494 | 127.37 |
| monmove_line_2048_control_a | score | 2048 | 8192 | 2048 | 219,410 | 128.36 |
| monmove_line_2048_control_b | score | 2048 | 8192 | 2048 | 217,230 | 129.06 |
| monmove_line_512_candidate | score | 512 | 8192 | 8192 | 334,824 | 81.96 |
| monmove_line_512_control_a | score | 512 | 8192 | 8192 | 340,469 | 80.66 |
| monmove_line_512_control_b | score | 512 | 8192 | 8192 | 329,586 | 83.20 |
| monmove_pgo2048_candidate | score | 2048 | 8192 | 2048 | 231,684 | 120.98 |
| monmove_pgo2048_control_a | score | 2048 | 8192 | 2048 | 230,556 | 121.79 |
| monmove_pgo2048_control_b | score | 2048 | 8192 | 2048 | 228,877 | 122.73 |
| monmove_pgo512_candidate_a | score | 512 | 8192 | 8192 | 368,548 | 74.59 |
| monmove_pgo512_candidate_b | score | 512 | 8192 | 8192 | 369,279 | 74.34 |
| monmove_pgo512_control_a | score | 512 | 8192 | 8192 | 360,335 | 76.14 |
| monmove_pgo512_control_b | score | 512 | 8192 | 8192 | 355,997 | 77.12 |
| monmove_pgo512_soak_a | score | 512 | 8192 | 8192 | 363,204 | 75.62 |
| monmove_pgo512_soak_b | score | 512 | 8192 | 8192 | 354,716 | 77.46 |
| monmove_pgo512_soak_c | score | 512 | 8192 | 8192 | 363,503 | 75.56 |
| monmove_pgo_combined_score2048_candidate | score | 2048 | 8192 | 2048 | 227,120 | 123.58 |
| monmove_pgo_combined_score2048_original | score | 2048 | 8192 | 2048 | 197,886 | 141.16 |
| monmove_pgo_combined_score512_candidate | score | 512 | 8192 | 8192 | 366,171 | 75.06 |
| monmove_pgo_combined_score512_original | score | 512 | 8192 | 8192 | 294,243 | 93.57 |
| monmove_pgo_confirm2048_candidate_a | score | 2048 | 8192 | 2048 | 228,573 | 122.85 |
| monmove_pgo_confirm2048_candidate_b | score | 2048 | 8192 | 2048 | 229,474 | 122.31 |
| monmove_pgo_confirm2048_control_a | score | 2048 | 8192 | 2048 | 225,935 | 124.39 |
| monmove_pgo_confirm512_candidate_a | score | 512 | 8192 | 8192 | 368,770 | 74.54 |
| monmove_pgo_confirm512_candidate_b | score | 512 | 8192 | 8192 | 360,281 | 76.27 |
| monmove_pgo_confirm512_control_a | score | 512 | 8192 | 8192 | 354,001 | 77.53 |
| monmove_pgo_confirm512_control_b | score | 512 | 8192 | 8192 | 360,095 | 76.36 |
| monmove_pgo_depth2048_candidate_a | depth | 2048 | 8192 | 2048 | 469,940 | 59.53 |
| monmove_pgo_depth2048_control_a | depth | 2048 | 8192 | 2048 | 463,267 | 60.36 |
| monmove_pgo_depth2048_control_b | depth | 2048 | 8192 | 2048 | 463,360 | 60.21 |
| monmove_pgo_early512_candidate_a | score | 512 | 0 | 2048 | 565,950 | 46.78 |
| monmove_pgo_early512_control_a | score | 512 | 0 | 2048 | 485,783 | 54.54 |
| monmove_pgo_early512_control_b | score | 512 | 0 | 2048 | 522,217 | 50.11 |
| monprefetch_2048_a | score | 2048 | 8192 | 2048 | 201,344 | 139.04 |
| monprefetch_512_a | score | 512 | 8192 | 2048 | 287,740 | 95.07 |
| monster_steady_control_a | score | 512 | 8192 | 8192 | 322,687 | 85.10 |
| monster_steady_control_b | score | 512 | 8192 | 8192 | 322,091 | 85.21 |
| monster_steady_line_a | score | 512 | 8192 | 8192 | 327,982 | 83.80 |
| monster_steady_line_b | score | 512 | 8192 | 8192 | 327,592 | 83.95 |
| monster_steady_soak_a | score | 512 | 8192 | 8192 | 322,210 | 85.15 |
| monster_steady_soak_b | score | 512 | 8192 | 8192 | 323,481 | 84.93 |
| monster_steady_soak_c | score | 512 | 8192 | 8192 | 322,901 | 85.15 |
| monster_steady_worm_a | score | 512 | 8192 | 8192 | 324,136 | 84.75 |
| monster_steady_worm_b | score | 512 | 8192 | 8192 | 324,124 | 84.60 |
| move_context_512_candidate | score | 512 | 8192 | 8192 | 324,530 | 84.59 |
| move_context_512_control_a | score | 512 | 8192 | 8192 | 325,910 | 84.21 |
| move_context_512_control_b | score | 512 | 8192 | 8192 | 325,736 | 84.43 |
| move_invariants_512_a | score | 512 | 8192 | 8192 | 321,414 | 85.48 |
| move_load_reuse_512_candidate_a | score | 512 | 8192 | 8192 | 329,243 | 83.45 |
| move_load_reuse_512_candidate_b | score | 512 | 8192 | 8192 | 328,916 | 83.49 |
| move_load_reuse_512_control_a | score | 512 | 8192 | 8192 | 333,787 | 82.26 |
| move_load_reuse_512_control_b | score | 512 | 8192 | 8192 | 327,957 | 83.83 |
| movement_bundle_2048_candidate_a | score | 2048 | 8192 | 2048 | 219,517 | 128.04 |
| movement_bundle_2048_candidate_b | score | 2048 | 8192 | 2048 | 220,267 | 127.69 |
| movement_bundle_2048_control_a | score | 2048 | 8192 | 2048 | 219,039 | 128.20 |
| movement_bundle_2048_control_b | score | 2048 | 8192 | 2048 | 214,664 | 130.83 |
| movement_bundle_512_candidate_a | score | 512 | 8192 | 8192 | 334,969 | 81.84 |
| movement_bundle_512_candidate_b | score | 512 | 8192 | 8192 | 332,535 | 82.62 |
| movement_bundle_512_control_a | score | 512 | 8192 | 8192 | 331,519 | 82.90 |
| movement_bundle_512_control_b | score | 512 | 8192 | 8192 | 327,732 | 83.87 |
| movement_control512_a | score | 512 | 8192 | 8192 | 320,319 | 85.61 |
| movement_control512_b | score | 512 | 8192 | 8192 | 318,719 | 86.20 |
| movement_size_512_candidate_a | score | 512 | 8192 | 8192 | 320,328 | 85.65 |
| movement_size_512_candidate_b | score | 512 | 8192 | 8192 | 314,228 | 87.35 |
| movement_size_512_control_a | score | 512 | 8192 | 8192 | 349,233 | 78.71 |
| movement_size_512_control_b | score | 512 | 8192 | 8192 | 329,282 | 83.52 |
| obj88_2048_a | score | 2048 | 8192 | 2048 | 202,245 | 138.77 |
| obj88_512_a | score | 512 | 8192 | 2048 | 306,946 | 89.14 |
| obj88_512_b | score | 512 | 8192 | 2048 | 298,199 | 91.72 |
| obj88_512_c | score | 512 | 8192 | 2048 | 287,755 | 94.87 |
| obj88_512_d | score | 512 | 8192 | 2048 | 287,086 | 95.03 |
| objclass24_score2048_candidate | score | 2048 | 8192 | 2048 | 217,630 | 129.54 |
| objclass24_score2048_control_a | score | 2048 | 8192 | 2048 | 217,138 | 129.72 |
| objclass24_score2048_control_b | score | 2048 | 8192 | 2048 | 215,385 | 130.02 |
| objclass24_score512_candidate | score | 512 | 8192 | 8192 | 322,554 | 85.13 |
| objclass24_score512_control_a | score | 512 | 8192 | 8192 | 321,311 | 85.34 |
| objclass24_score512_control_b | score | 512 | 8192 | 8192 | 321,635 | 85.37 |
| objclass32_512_a | score | 512 | 8192 | 8192 | 324,690 | 84.65 |
| objclass_control512_a | score | 512 | 8192 | 8192 | 324,477 | 84.49 |
| objclass_control512_b | score | 512 | 8192 | 8192 | 321,541 | 85.37 |
| objhead32_512_headscreen | score | 512 | 8192 | 8192 | 321,919 | 85.33 |
| objhead32_slots_512_headscreen | score | 512 | 8192 | 8192 | 320,243 | 85.80 |
| objhead_control2048_a | score | 2048 | 8192 | 2048 | 217,461 | 129.10 |
| objhead_control2048_b | score | 2048 | 8192 | 2048 | 214,183 | 130.78 |
| objhead_control512_a | score | 512 | 8192 | 8192 | 325,170 | 84.45 |
| objhead_control512_b | score | 512 | 8192 | 8192 | 319,241 | 86.08 |
| objhot_512_long_a | score | 512 | 8192 | 8192 | 317,833 | 86.23 |
| objpool_2048_a | score | 2048 | 8192 | 2048 | 204,479 | 137.45 |
| objpool_2048_b | score | 2048 | 8192 | 2048 | 205,947 | 136.08 |
| objpool_512_long_a | score | 512 | 8192 | 8192 | 307,666 | 89.29 |
| objstate10_2048_candidate_a | score | 2048 | 8192 | 2048 | 224,329 | 125.06 |
| objstate10_2048_candidate_b | score | 2048 | 8192 | 2048 | 224,187 | 125.44 |
| objstate10_2048_control_a | score | 2048 | 8192 | 2048 | 225,216 | 124.65 |
| objstate10_2048_control_b | score | 2048 | 8192 | 2048 | 218,991 | 128.50 |
| objstate10_512_candidate_a | score | 512 | 8192 | 8192 | 337,551 | 81.33 |
| objstate10_512_candidate_b | score | 512 | 8192 | 8192 | 330,828 | 83.02 |
| objstate10_512_control_a | score | 512 | 8192 | 8192 | 342,630 | 80.39 |
| objstate10_512_control_b | score | 512 | 8192 | 8192 | 328,703 | 83.53 |
| pile_cache_512_candidate | score | 512 | 8192 | 8192 | 321,920 | 85.28 |
| pile_cache_512_control_a | score | 512 | 8192 | 8192 | 328,677 | 83.50 |
| pile_cache_512_control_b | score | 512 | 8192 | 8192 | 322,718 | 85.01 |
| pile_cache_nonempty_512_candidate | score | 512 | 8192 | 8192 | 317,668 | 86.34 |
| pile_cache_nonempty_512_control_a | score | 512 | 8192 | 8192 | 328,719 | 83.39 |
| pile_cache_nonempty_512_control_b | score | 512 | 8192 | 8192 | 323,028 | 84.93 |
| pile_summary_512_candidate | score | 512 | 8192 | 8192 | 321,926 | 85.31 |
| pile_summary_512_control_a | score | 512 | 8192 | 8192 | 322,252 | 85.40 |
| pile_summary_512_control_b | score | 512 | 8192 | 8192 | 322,169 | 85.24 |
| property32_2048_a | score | 2048 | 8192 | 2048 | 201,701 | 138.97 |
| property32_512_a | score | 512 | 8192 | 2048 | 285,839 | 95.46 |
| raw_combined_base2048_a | score | 2048 | 8192 | 2048 | 199,151 | 140.79 |
| raw_combined_base512_a | score | 512 | 8192 | 8192 | 296,153 | 92.81 |
| raw_combined_raw2048_a | score | 2048 | 8192 | 2048 | 217,573 | 128.86 |
| raw_combined_raw512_a | score | 512 | 8192 | 8192 | 328,866 | 83.47 |
| raw_early_candidate | score | 512 | 0 | 2048 | 498,209 | 53.29 |
| raw_early_control_a | score | 512 | 0 | 2048 | 497,189 | 52.47 |
| raw_early_control_b | score | 512 | 0 | 2048 | 495,610 | 53.70 |
| rawglyph_only_2048_headscreen | score | 2048 | 8192 | 2048 | 216,908 | 129.45 |
| rawglyph_only_512_long_a | score | 512 | 8192 | 8192 | 321,924 | 85.26 |
| rawglyph_pgo_2048_candidate | score | 2048 | 8192 | 2048 | 228,827 | 122.87 |
| rawglyph_pgo_2048_control_a | score | 2048 | 8192 | 2048 | 217,319 | 129.60 |
| rawglyph_pgo_2048_control_b | score | 2048 | 8192 | 2048 | 217,041 | 129.14 |
| rawglyph_pgo_512_candidate | score | 512 | 8192 | 8192 | 361,078 | 76.07 |
| rawglyph_pgo_512_control_a | score | 512 | 8192 | 8192 | 321,589 | 85.37 |
| rawglyph_pgo_512_control_b | score | 512 | 8192 | 8192 | 325,344 | 84.38 |
| rawglyph_pgo_combined_score2048_candidate | score | 2048 | 8192 | 2048 | 224,412 | 125.09 |
| rawglyph_pgo_combined_score2048_original | score | 2048 | 8192 | 2048 | 196,821 | 141.84 |
| rawglyph_pgo_combined_score512_candidate | score | 512 | 8192 | 8192 | 359,919 | 76.34 |
| rawglyph_pgo_combined_score512_original | score | 512 | 8192 | 8192 | 296,711 | 92.61 |
| rawglyph_pgo_early512_candidate | score | 512 | 0 | 2048 | 520,887 | 50.82 |
| rawglyph_pgo_early512_control | score | 512 | 0 | 2048 | 506,913 | 52.18 |
| rawglyph_pgo_repeat2048_candidate | score | 2048 | 8192 | 2048 | 227,227 | 123.61 |
| rawglyph_pgo_repeat2048_control | score | 2048 | 8192 | 2048 | 217,143 | 129.23 |
| rawglyph_pgo_repeat512_candidate | score | 512 | 8192 | 8192 | 360,023 | 76.14 |
| rawglyph_pgo_repeat512_control | score | 512 | 8192 | 8192 | 327,548 | 83.88 |
| scary_once_512_a | score | 512 | 8192 | 8192 | 321,203 | 85.38 |
| schedule_control2048_a | score | 2048 | 8192 | 2048 | 201,510 | 138.99 |
| sharedobjs_2048_a | score | 2048 | 8192 | 2048 | 199,702 | 140.24 |
| sharedobjs_512_a | score | 512 | 8192 | 2048 | 295,362 | 92.35 |
| species64_512_long_a | score | 512 | 8192 | 8192 | 318,507 | 86.08 |
| static_object_meta_512_candidate | score | 512 | 8192 | 8192 | 323,301 | 85.00 |
| static_object_meta_512_control_a | score | 512 | 8192 | 8192 | 321,331 | 85.59 |
| static_object_meta_512_control_b | score | 512 | 8192 | 8192 | 321,488 | 85.42 |
| terrain16_2048_a | score | 2048 | 8192 | 2048 | 199,090 | 140.99 |
| terrain16_512_a | score | 512 | 8192 | 2048 | 284,819 | 95.95 |
| trap_neighbor_bits_512_candidate_a | score | 512 | 8192 | 8192 | 270,304 | 101.57 |
| trap_neighbor_bits_512_candidate_b | score | 512 | 8192 | 8192 | 269,251 | 102.07 |
| trap_neighbor_bits_512_control_a | score | 512 | 8192 | 8192 | 321,978 | 85.43 |
| trap_neighbor_bits_512_control_b | score | 512 | 8192 | 8192 | 271,104 | 101.25 |
| trap_neighbor_bits_precondition | score | 512 | 8192 | 8192 | 334,706 | 82.09 |
| trap_neighbor_bits_repeat512_candidate | score | 512 | 8192 | 8192 | 269,134 | 102.01 |
| trap_neighbor_bits_repeat512_control_a | score | 512 | 8192 | 8192 | 270,431 | 101.55 |
| trap_neighbor_bits_repeat512_control_b | score | 512 | 8192 | 8192 | 270,517 | 101.43 |
| trap_neighbors_512_candidate_a | score | 512 | 8192 | 8192 | 334,471 | 82.23 |
| trap_neighbors_512_candidate_b | score | 512 | 8192 | 8192 | 329,504 | 83.36 |
| trap_neighbors_512_control_a | score | 512 | 8192 | 8192 | 341,579 | 80.46 |
| trap_neighbors_512_control_b | score | 512 | 8192 | 8192 | 327,826 | 83.77 |
| vision_direct_512_candidate | score | 512 | 8192 | 8192 | 318,495 | 86.17 |
| vision_direct_512_control_a | score | 512 | 8192 | 8192 | 321,762 | 85.32 |
| vision_direct_512_control_b | score | 512 | 8192 | 8192 | 322,669 | 85.05 |
| visited_bits_2048_a | score | 2048 | 8192 | 2048 | 216,298 | 130.04 |
| visited_bits_512_a | score | 512 | 8192 | 8192 | 322,584 | 85.05 |
| visited_control_2048_a | score | 2048 | 8192 | 2048 | 215,448 | 130.37 |
| visited_control_2048_b | score | 2048 | 8192 | 2048 | 215,866 | 130.04 |
| visited_control_512_a | score | 512 | 8192 | 8192 | 322,860 | 84.96 |
| visited_control_512_b | score | 512 | 8192 | 8192 | 324,639 | 84.57 |
| visited_lazy_2048_a | score | 2048 | 8192 | 2048 | 215,034 | 130.52 |
| visited_lazy_512_a | score | 512 | 8192 | 8192 | 321,786 | 85.25 |
| worm_gate_512_candidate | score | 512 | 8192 | 8192 | 331,221 | 82.82 |
| worm_gate_512_control_a | score | 512 | 8192 | 8192 | 342,252 | 80.30 |
| worm_gate_512_control_b | score | 512 | 8192 | 8192 | 324,587 | 84.51 |

## Compact object pool confirmation

Two reverse-order pairs now confirm the compact layout plus object pool: 512_long +8.82%, 2048 +8.1%. All native final states and world-turn counts match. The immutable16,777,216-decision score reference also matches with zero differences. Full15.55M training comparisons, depth-policy coverage and source-access footprint checks are underway. This combination is not retained yet.

The aligned hot-prefix monster pool is parked: its2048 screen was only+0.93%, despite+3.60% at512. Prioritise the stronger object-pool combination.


First full-score pipeline pair for compact_pool:179805.70->184421.49SPS (+2.567%),96matching batch hashes, fixed weights. Rollout tail45.3->2.79ms; earlywindow-0.408%. Reverse order pending. The independent depth capture also passes16,777,216every-decision hashes. depth/runs/baseline2048_a is excluded for overlap with the species64 build; rerun cleanly before interpreting its candidate comparison.


## Retained compact layout plus object pool

Two score CPU pairs: +8.82% at512long and+8.10% at2048 against the original persist baseline. Two full15.55M score-pipeline pairs: 179826->184508SPS (+2.60%). Early pipeline windows-0.408%,+0.401%: flat. All96batch proofs per pair match, frozen weights unchanged. Separate4.3M depth pipeline:343772->343974SPS (+0.059%, flat), with all96batch proofs matching. CPU headroom improves without a depth training gain because GPU work already covers the rollout. Clean depth2048control404176,candidate448317(+10.92%); candidate repeated447906. First control excluded for build overlap.

Both score and depth pass16,777,216every-decision observations/rewards/terminals/masks:33,554,432total. Golden/fuzz/status/interleaved/shuffled and pool lifetime checks pass. Utility-only cleanup guard fixes the Clang level-compiler link; GCC native library is byte-identical before/after (checks/compact_pool_utility_fix.json).

Accessed-line footprint including copies:62.0968->53.0538KiB per decision(-14.56%). Repeated alone after a first diagnostic private-directory warning; the repeat has no warning and exactly matches the independent unchanged native final state. Original diagnostic retained in capture_first/. Native/full-pipeline logs have no such warnings.

Latest retention:RETAINED.json,COMPACT_POOL_SUMMARY.json,compact_pool_source_hashes.json. Baseline1282files and8protected live files unchanged. No production edits, commits or pushes.

## Further short screens

Against compact_pool at512long:species64-0.18%,objhot-0.39%,rawglyph_only+0.89%. Allquick gates and native final states match; species dump381records identical, item serialization roundtrip passes. None clears the predeclared1% score screen, so none is retained.

## Visited-map screen

Both wrapper candidates pass all67,108,864 decision comparisons in total, plus the first-visit boundary property test. The bitset reduces Env167968->75104bytes; lazy clearing keeps layout unchanged but avoids touching unused floor rows.

| Candidate | Score512 | Score2048 | Depth2048 | Depth RSS saved |
|---|---:|---:|---:|---:|
| visited_bits | -0.36% | +0.30% | +0.59% | 194.2MiB |
| visited_lazy | -0.61% | -0.29% | +0.89% | 151.5MiB |

Screens are against compact_pool, not the campaign starting baseline. No throughput retention yet. Raw manifests and outputs: wrappers/SUMMARY.json, runs/visited*, depth/runs/visited*.

## Movement and redundant glyph follow-up

Three independent movement candidates on compact_pool pass all five quick gates and the long512 native end-state/turn comparison. Changes versus the two adjacent controls: move_invariants +0.593%, scary_once +0.527%, keys_once +0.124%. All are parked below the1% screening gate; no full decision comparison or retention. See MOVEMENT_AUDIT.md, movement_screen512.json and isolated patches.

The previously parked rawglyph_only candidate is more useful on the independent depth workload: controls448131/448173, candidate454926 (+1.51%). Same end-state/turns. This is one measurement and needs a repeat/full decision gates before retention.

## Compact object-type table and glyph validation

objclass32 keeps all fields while reducing454 records from40 to32bytes and aligning the table64bytes. All static values agree,256 legacy40byte conversion patterns pass, and all quick gates pass. Score512 screen: +0.52%; parked below the1% gate.

rawglyph_only repeats its depth benefit in reverse order: +1.512%, +1.418%. All33,554,432 score/depth every-decision hashes match the unchanged original references. Full pipeline and early timing still pending; not retained.

## Object hot-prefix follow-up

Two new object layouts concentrate the common fields in32bytes while retaining88byte records and96byte save records. objhead32 uses the existing pool; objhead32_slots uses32byte-aligned96byte allocation slots (extra padding) to keep each hot prefix on one line. Both pass all quick gates,256 save-roundtrip patterns and80 context lifecycles. The aligned pool also passes Valgrind with zero errors/lost allocations. Native screens are running. No retention. See OBJECT_HEAD_AUDIT.md and checks/object_heads_layout.json.

Object-head512 results: objhead32 -0.089%, objhead32_slots -0.609%. Controls ranged319241–325170SPS; neither candidate has a reliable win, both parked. No full decision gate was spent on these rejected variants.


## Raw glyph validation in progress (9 October)

The glyph-cache removal passed the full original score and depth decision corpora (33,554,432 comparisons, zero differences). The 2048 score screen is +0.50% vs bracketed compact_pool controls, too small for an independent strong score claim; two depth comparisons remain +1.51% and +1.42%. Early512 is +0.36% (flat). Fresh direct combined CPU pairs versus original persist: score512long +11.05%, score2048 +9.25%, depth2048 +12.90%. These are fresh single pairs; distinguish them from the repeated prior compact_pool measurements.

Serial queue validate_rawglyph.py is running the frozen score and depth full pipelines. RETAINED.json remains compact_pool pending those results and the source-access trace. No production edits, commits or pushes. Integrity recheck: all1282 original source files and8 protected live files unchanged.

Next prepared experiment: compact derived monster occupancy, bit and byte variants. It tests answering empty-neighbour queries without fetching the full pointer-grid line. Monster allocation and pointer identity remain unchanged; extra placement/removal writes are the tradeoff. Scripts are prepared but not executed while the timing queue runs.


## Retained removal of redundant glyph cache

The redundant display-glyph cache and overwritten copy are removed. Public canonical mapping remains eager and unchanged. Retained for the repeated incremental depth CPU improvement (+1.512%, +1.418%); score2048 incremental screen +0.503% is small/uncertain. Early CPU +0.365% is flat.

Fresh direct combined pairs against original persist: score512long +11.046%, score2048 +9.250%, depth2048 +12.905%. These are single fresh pairs; previous compact_pool repeated results remain archived separately. Full frozen15.55M score pipeline179629->184444SPS (+2.681%), effectively the same as compact_pool's+2.604%. Full4.3M depth pipeline342178->342597SPS (+0.123%, flat). No claim of an additional training gain from glyph cleanup. All96batch proofs match in each workload, frozen weights unchanged.

All33,554,432 original score/depth decision checks and golden/fuzz/status/interleaved/shuffled gates pass. Source-access trace matches independent native state with no warnings:62.0968->52.6693KiB/decision against original persist, and53.0538->52.6693 against compact_pool. This is an accessed-line footprint, not hardwarecache misses.

Authoritative current artifacts:RETAINED.json,RAWGLYPH_SUMMARY.json,rawglyph_source_hashes.json. Prior retained engine archived asRETAINED_compact_pool.json. Isolated only; no production edits, commits or pushes.

## Compact monster grids and occupancy filters: parked

Controls and candidates were serialized, using the same mature score actions.
All final observations, ages and world-turn counts match. These are short
screens, not full per-decision validation or retained gains.

| Candidate | Reference | 512 long | 2048 | Decision |
|---|---|---:|---:|---|
| Occupancy bitmap | compact_pool | +0.542% | +0.310% | Park |
| Occupancy bytes | compact_pool | +0.734% | +0.091% | Park |
| 16-bit monster handles | rawglyph_only | +0.283% | +0.381% | Park |
| 32-bit lifetime handles | rawglyph_only | +0.642% | -1.066% | Park |

The 16-bit design reduces the spatial grid from13440 to3360 bytes, but adds a
fixed registry and per-move reference accounting. The32-bit design uses6720
bytes plus a dynamic lifetime registry, avoiding per-move reference counts.
Both grow monster records120->128 bytes and add an indirect load on lookup.
The16-bit registry allocates20172 bytes; its larger total context is deliberate,
because the hypothesis concerns accessed state, not reserved size.

Both handle designs pass34goldens,26fuzz cases,status-disabled,interleaved and
shuffled checks. The16-bit property test covers1Mupdates,aliasing,full-map
capacity,copied/stale handles,teardown after record freeing and256 legacy-save
roundtrips underASan/UBSan. The32-bit test additionally covers8192 live
registrations,reuse and80actualcontext lifecycles;Valgrind reports0errors,0leaks.
Full16.8M/33.6Mper-decision gates intentionally not spent on weak screens.
Results: mon_grid16_screen512.json,mon_grid_screen512.json,
mon_grid_screen2048.json,mon_occupancy_screen512.json,
mon_occupancy_screen2048.json. Code and hashes preserved in ARTIFACTS.json.

Next: trace the16-bit layout to test actual accessed-footprint reduction, then
screen a simpler4x2direct-pointer tile layout, without registries or changed
monster records. This is a different locality mechanism, not another retry of
the flat handle implementation.

The16-bit trace matches the pinned native four-step state without warnings.
Versus retained rawglyph, accessed monster-grid lines fall2.477->1.227KiB/step,
while monsterrecords rise3.510->3.701 and unclassified(includingregistry)
2.387->2.891. Total52.669->51.746KiB/step(-1.753%).
This is modest total footprint reduction despite a75%smaller allocated grid,
and does not demonstrate fewer hardware misses. Nativeperformance wasflat.

## Direct-pointer spatial tiles: parked

4x2aligned64-byte groups preserve pointer identity and120-byte monster records,
without handle bookkeeping. Allocation per grid grows13440->14080 bytes due to
padding. Both monster-only and monster+object versions pass the exhaustive1680
coordinate bijection/alignment check,1Mrandomupdates underASan/UBSan, and all
five quick suites (golden,fuzz,status-disabled,interleaved,shuffled). All indexed
source accesses audited; actual accessor arguments are evaluated once.

2048mature score screen: controls220219/215559SPS (about2.1%drift), monster-only
217223(-0.305%vsbracketedmean), both214960(-1.344%). End-state hashes and total
world turns match. No convincing win; park both. These are screening results,
not precise regression estimates. No full decisioncorpus gate spent on them.
Source/library/patch hashes in ARTIFACTS.json, timings grid_tiles_screen2048.json.
Theinitialempty run directory from incorrect runnerargument setup is preserved
asgrid_tiles_control2048_a_setup_failed; no nativeprocessran in that attempt.

Next: byte coordinates in persistentfloorindex. Nativeobjectcoords are signed
bytes but derivedcache currently widens them toshort. Candidate keeps signed
bytes and filters16ratherthan8coordinatesperSSE2block. Preservesorder,invalidations
andoverflowfallback; independent list-reference property test prepared.

Tiletrace matches pinned native four-step state without warnings. Bothgrids
reduce totalaccessed footprint52.669->51.313KiB/decision(-2.575%);monstergrid
2.477->1.907,objectgrid1.979->1.503. This measuredfootprint benefit didnot
produce anative speedup; extraindexarithmetic remains a plausible cost, not a
proved attribution. Source-access counts are nothardwaremiss counters.

Byte-floor-index prototype built.582201 differentialqueries (578601matches)
agree exactly fororiginalandcandidate, againstanindependent linked-list walk.
Testscoverallsignedcoordinatevalues,vector tails,0..2600objects(including
2048overflow),extreme/invertedbounds,changedbounds,listmutationsandinvalidations.
Valgrindbothruns0errors,0leaks. Golden/fuzz/status/interleaved/shuffledpass.
Native512longscreen inprogress;notretained.

Byte-floor-index512longscreen:321592/321715control,323040candidate,+0.431%.
Closelyagreeingcontrols but below0.75%screeningthreshold;park,no2048/fullhashrun.
Reusing existingcompact_poolprofile:nh_fobj_next960/22967samples. Annotated
assembly divides into307rebuild,426SIMD-scan+hit-return,156setup/cachedmask/return,
71scalar-tail samples. This bounds how much wider comparisons alone can help;
these code ranges do not prove exact causal latency (sampling can land after
loads). Artifacts:fobj_compact_pool_disasm.txt,fobj_profile_parts.json.

Next prototype vision_direct preservesbothvisibilitybuffersandtheirrow-pointer
interface, adding a typed directmatrixpointer forcansee/couldsee/templit. Allfour
bufferselectionassignments updateit. Removesone dependentrow-pointerload without
changingvisibilitylogic. Builtandpassedallfivequickgates;native512screenrunning.
Production8andbaseline1282protectedsourcehashesrecheckedandunchanged.

Visibility-pointer512screen:321762/322669control,318495candidate(-1.154%).
Allendstatehashes/worldturnsmatch. Park;nofullcorpusgate. Addedpointer/direct
indexing didnotpayoffinthisscreen;do not inferthat removing a dependentload
necessarilyimprovesruntime.

Reusedexistingcompact_poolCPUprofile atinstructionlevel, without anewbroad
profile: movement_instruction_hotspots.json,mfndpos_compact_pool_disasm.txt,
m_move_compact_pool_disasm.txt. Samplehotspotsincludegrid-pointerloads,terrain
loads,linkeditemsearches,andselectedfloorobject'stypecheck(193samples). These
are statisticalsamplelocations,not precisehardwaremissattribution.
Nextcandidate:fobj_hit_prefetch, basedonrawglyph_only, prefetchesthe nextalready
spatiallyfilteredobject'stypebefore returningthecurrentone. Mask/listorderand
RNGunchanged. Build/quickgates/native512screen inprogress.

Filtered-object prefetch passedallquickgates;512longscreen controls323389/322079,
candidate321018(-0.532%). Endstate/worldturncountsidentical. Park;no retained
change and nofullcorpusspending. Allnewcandidatecode/libraries preserved.

Next unimplemented hypothesis: exclude ROCK from the monster-interest index,
because m_move skips it immediately. This could avoid repeated objecttype loads
and shrink queries, unlike wider SIMD or prefetching. Must first quantify the
fraction of entries/results that are rocks and audit type transitions. Initial
source review finds poly_obj replaces pointers through invalidate-aware
replace_object; fracture_rock extracts/replaces floor objects; petrified eggs
are carried or placed via place_object. This is an incomplete audit, not proof
that caching ROCK membership is safe. A verifier must check filtered order and
membership under mutations before any production-level claim or retention.

## Rock-return diagnostic and filtered index

Mature score replay, 512 games, canonical8192 warmup then2048 measured
decisions per game. Diagnostic counters are enabled only after warmup; its
timing is excluded from native comparisons. End state matches original
b97835c62aaf388f/7230092turns. Counts:2421941engine keys,39951908query starts,
196577038returned objects,37995715rocks(19.329%). Index rebuilds323737
visited48159414objects including7367807rocks(15.299%). No overflow/fallback.
Source and binary hashes:ARTIFACTS.json; exact invocation:diag_rocks/command.json;
raw counts:diag_rocks/counts.json.

This changes the next action: test skipping ROCK at index construction instead
of immediately after every hit. fobj_nonrock preserves order and includes a
filtered fallback and verification path, plus explicit floor invalidation at
the two in-place ROCK stores. Candidate audit:engines/fobj_nonrock/AUDIT.md.
All five quick gates pass. Native screen and focused differential tests pending.

Rock-filter outcome:512long+1.352% (controls329470/322723,candidate330505),
2048+0.309% (controls221788/215695,candidate219417). Control variation exceeds
the apparent benefit. Parked; do not claim a speedup. Focused independent
reference test:483277queries/478477matches, hash6a9d1588580fdbb1, identical to
original helper with consumer rock-skipping. Includes all-rock/mixed lists,
5000-entry overflow, dynamic bounds and mid-cursor type/list mutations with
invalidation. Valgrind both0errors0leaks. Full corpus gates not run for this
weak candidate.

## Reapplying profile-guided compilation

Historical overnight campaign retained PGO with real benefits, but the current
CPU-scaling/compact-state comparisons deliberately rebuilt everything with
ordinary LTO to isolate source changes. Current flags confirm no PGO. Reapply
PGO to exactly rawglyph_only source as a separate compiler experiment; this
is not a newly discovered source optimisation. Use historical eight score and
eight depth recording streams for profiling, then test our standard mature
512/2048 workloads and exact gates. Profiling inputs/builds/hashes are archived
under engines/rawglyph_pgo; script build_rawglyph_pgo.py. Instrumented collection
is not a native performance result. No compiler win claimed until measured.

Initial PGO screen512long: controls321589/325344,candidate361078SPS,
+11.627%. End-state/age/turns match; all five quick gates pass.
2048screen and repeat/full-corpus/full-pipeline checks remain pending.
Keep compiler optimisation distinct from source-only experiments: ordinary-LTO
source comparisons are useful for screening, but final retained combinations
must also include and revalidate the best compiler recipe.

PGO confirmation native repeats (rawglyph_only controls):
- rawglyph_pgo_repeat512: +9.914% (360022.58 vs 327547.87SPS).
- rawglyph_pgo_repeat2048: +4.644% (227227.00 vs 217143.08SPS).
- rawglyph_pgo_depth2048: +1.680% (463404.69 vs 455749.44SPS).
- rawglyph_pgo_early512: +2.757% (520887.31 vs 506912.56SPS).
All end-state hashes, ages and turns match. First2048bracket+5.363%
with0.128%controlspread. Early and immutablefullcorpuschecks pending.
Executable .text shrank3326658->2090994bytes(37.14%); allocation/layoutofgame
state is unchanged. This is code-size evidence, not proof of hardware cache
miss reduction. Do not use Clangsource-tracecounts to attribute a GCCPGOeffect.

PGO validation completed:early512+2.757%,sameendstate. Immutable score
16777216anddepth16777216per-decisionhashes match withzerodifferences. Depth
hashsha c49749f881041273bdea7e1552d37c8f8f79974157375607c412a9179eb33f24.
Allfivequickgatespass. Score repeats512+9.914%,2048+4.644%;depth2048firstpair
+1.680%. This validates a CPUcandidate, not a full-training speedup claim.
RAWGLYPH_PGO_SUMMARY.json collects evidence. Pending directcombinedCPUbaseline
and frozenfullpipeline scripts are prepared, not yet run. No retentionmanifest
changed; rawglyph_only remains the retained source/native reference.

Current turn classification:progress. Measured newrock-filterheadroom, rejected
a weak implementation onnativeevidence, restored andvalidated a promising
compiler optimisation onthecurrentcompactsource. Live8, originalsource1282and
retainedsourcemanifestrechecked unchanged; no productionedits/commits/pushes.

## PGO combined frozen-pipeline validation

First originalpersist-scorebaseline179462.85SPS,candidate184790.42(+2.969%).
All96batchproofsmatch and15.55Mactorweightsremainidentical. Earlywindow
187344->186554(-0.422%,flat). CPUtimeoverwhole96epochrun3779.39->3422.70s,
wall143.10->140.12s. Maturemeasuredrollouttail0.04967->0;PPOtail0.00096->0.13602s.
These are stage-tailcounters, not a new hardwareprofile. Secondbaselineand
depthpair stillrunning. Priorcompactsource-onlyfullresult184444SPSis similar;
no evidenceyetfor additionalPGOfull-traininggain despite CPUreplaybenefit.

Completed score bracket:179367.80controlmean->184790.42SPS(+3.023%),
control drift-0.106%. Depth342167.33->342568.37SPS(+0.117%,flat),early+0.109%.
All96batchproofs/unchangedactorhashespassforbothworkloads. Full96epochdepth
CPUtime2005.28->1829.51s;moreCPUheadroomwithoutameasuredtrainingthroughputgain.
Single-workload/directnativecombinedpairs nowrunning. No additionalPGOtraining
speedup overcompactsource-onlyclaimed.

## Retained compact engine with profile-guided compilation

PGO restored on source-identical rawglyph_only. Repeated incremental score CPU gains: 9.91–11.63% at512 and4.64–5.36% at2048. All33,554,432score/depth decision hashes and five quick gates pass.

- Direct combined rawglyph_pgo_combined_score512: 296710.73 -> 359919.41SPS (+21.303%). Single fresh pair.
- Direct combined rawglyph_pgo_combined_score2048: 196820.96 -> 224411.88SPS (+14.018%). Single fresh pair.
- Direct combined rawglyph_pgo_combined_depth2048: 403089.22 -> 462459.55SPS (+14.729%). Single fresh pair.

Full15.55M score pipeline: 179368 -> 184790SPS (+3.023%), control drift -0.106%.
Full4.3M depth pipeline: 342167 -> 342568SPS (+0.117%). All96batchproofs match and actors remain unchanged in both workloads.

The extra PGO CPU benefit does not establish an additional training gain over earlier compact-source results. RETAINED.json selects the best compiled combination; RETAINED_SOURCE.json preserves the ordinary-LTO source reference for fair quick source screens. Regenerate PGO for promising changed sources. No production edits, commits or pushes. Goal remains active.

## Fresh PGO profile and floor-query experiments

New2048 profile has21571samples: m_move19.1%, mfndpos16.4%, movemon7.0%, pack_obs4.7%, fill_obs4.5%, newsym3.9%, floor iterator3.0%, encumber_msg3.0%. Inlined attribution differs from ordinary LTO. Statistical PCs are not precise cache-miss attribution. Native timing ledger excludes this profiled run. Raw profile and instruction annotations archived.

floor_bounds_once removes only the coordinate predicate immediately after an already bounds-filtered iterator return. All five quick gates pass.512long controls321625/322301SPS,candidate323521(+0.484%); control drift0.210%. Parked below screening threshold, no full corpus gate.

Next pile_summary fuses scare-scroll/garlic/boulder presence scans within one neighbour calculation. Stack-local only, no persistent invalidation burden. First build hit a flags macro name collision, corrected to bits; failed compiler log archived. Build, quick gates and native screen underway.

Pile-summary screen: controls322252/322169SPS,candidate321926(-0.088%),control drift-0.026%. All five quick suites pass and native state/turns match. Flat; parked without full corpus or PGO rebuild. Combining logical scans did not improve native throughput.

Next move_context captures the game-context pointer on function entry in m_move/mfndpos, testing whether repeated TLS loads survive compiler optimisation. Experimental lexical aliases only in isolated copies. State layout and mutable field reads unchanged. Build, quick gates and source-only screen underway.

Context-pointer screen: controls325910/325736SPS,candidate324530(-0.397%),control drift-0.053%. All five quick suites and native state match. Parked; caching the context pointer did not improve throughput. Static generated-code counts are in move_context_codegen.json; they do not measure dynamic load latency.

Floor-iterator inlining screen: controls328167/324976SPS,candidate326191(-0.117%),control drift-0.972%. Five quick suites and native state/turns match. Parked; no reliable throughput improvement. Full corpus and PGO rebuild not justified. Historical pack115 monster-distance precomputation already had flat GPU rollout results (+0.232%,1.302%control drift); do not repeat without new evidence.

Item-interest-first candidate passed five quick suites and native state/turn checks. Controls342472/323439SPS,candidate330614(-0.703%). The5.558%control drift prevents a causal regression claim; no reliable gain and parked. Next pile_cache tests persistent three-bit floor summaries, invalidated on existing floor mutations and audited in-place erasure/fracture. Adds2000B/game; native benefit and verification still unproved.

Persistent pile cache screens: ordinary version -1.160% (controls328677/322718,candidate321920); bypass-empty version -2.518% (controls328719/323028,candidate317668). Both passed five quick suites and native end-state/turn checks. Neither provides throughput evidence for retention. They add2000B/context and clear320B on floor invalidation; the specific regression mechanism is not proved. Focused differential source/checker were prepared but NOT RUN; full hashes and verified-query replay intentionally not spent on rejected candidates. No production changes.

Next inspect existing retained-PGO fill_obs samples at instruction level; do not collect a new broad profile. These samples may identify a different observation-export target after the movement micro-optimisations failed to pay off.

### Per-fill public glyph memo — parked

`glyph_fill_memo_screen512.json`: memoising public object glyph mapping only within one fill preserved all five quick suites and native final states. Score512 long controls 328384/322907 SPS, candidate318833 SPS (-2.092%, control drift-1.668%). No reliable benefit; no full-corpus or PGO validation spent.

### Monster-field diagnostic and instrumentation limitation

`monster_field_trace/REPORT.md` records2048 mature decisions/53119 touched monster-record steps. Native reference hash/turn count matches. Common scalar fields guided `monmove_line`: aligned first-line movement/status/worn/strategy/eating, inventory/tracking second. The trace cannot justify treating bitfields as cold: disassembly confirms clang coverage omitted some bitfield loads. Raw traced byte/line totals, including earlier diagnostics, are incomplete source-access counts, not hardware misses. Flags are forced hot. `mlstmv` source review corrected the earlier audit: its movemon use is guarded by the rare parked-vault-guard condition.

monmove_line build and five quick suites pass; source-only native bracket running. No retention or full-corpus claim.

monmove_line is parked: controls340469/329586SPS, candidate334824SPS (-0.061%, controls drift-3.197%). No reliable win. All five quick suites and native state/turns match. No extended lifecycle or full-corpus validation run for this rejected candidate.

### Stabilized monster candidate comparison

Earlier first/middle/last brackets drifted3–5%, prompting one uninterrupted sequence with three soak passes then control/worm/layout/layout/worm/control. Controls322687/322091SPS drift0.185%. Aligned movement layout327982/327592SPS: **+1.674%** against322389 control mean. Worm absence gate324136/324124: **+0.540%**. All final state/turn proofs match. `monster_steady_comparison.json` is authoritative. This changes monmove_line from parked to2048 confirmation, not retention. Save-format boundary roundtrip and80 aligned allocator lifecycle contexts under Valgrind pass. Worm gate remains parked pending a stronger reason; full mask validation not run.

Prepared `context_slab`: several contexts per2MiB slab, addressing the earlier one-hugepage-per-game experiment's RSS waste. Source only, not built/tested yet. Generator integration deliberately pending screen outcome; see its AUDIT.md.

monmove_line2048 first bracket: controls219410/217230SPS, candidate220494SPS, **+0.996%**, controls drift0.994%. All final proofs match. Modest candidate, not retained; needs repeated2048 and combinedPGO checks before any gain claim beyond this screen.

context_slab512: controls327868/325228SPS,candidate325828 (-0.220%, drift0.805%). RSS964408KiB vs about939000KiB; minorfaults11756 vs about44500. All five quick gates and native states match. This does not establish actual huge-page coverage;2048 screen and live process smaps observation pending. Threaded lifecycle source prepared, not run.

### Larger follow-up and allocator checks

`large_followups.json`:2048 controls218983/217336SPS (0.752%drift), packed context slabs221084SPS(+1.341%), aligned monster layout220448SPS(+1.049%). Monster candidate repeats its earlier220494SPS closely; no combined-build retention yet. All native final states/turn counts match. Slab RSS1553452KiB versus1461696KiB firstcontrol.

Context allocator passes46488 threaded lifetimes (eight threads, repeated growth/reuse/zeroing/teardown), including Valgrind zero errors and zero definitely/indirectly/possibly lost bytes.84889B library/runtime allocations remain reachable. `context_slab_memory_probe.json` separately verifies2048 contexts in171 arenas:350208KiB actual AnonHugePages, returning to zero after cleanup. This is a direct allocator probe, not replay timing or a hardware TLB-miss measurement. An attempted live-replay smaps read was declined by its warmup-time guard before reading; no native smaps evidence claimed.

`monmove_clean` copies the measured layout and moves monster-pool cleanup outside the unrelated NLE_OBJECTS_GLOBAL conditional. The benchmark does not set that option, so its preprocessed cleanup order is unchanged. Original measured source left untouched. `build_monmove_pgo.py` builds fresh profiles for this source; no current retention/source/library changed.

Fresh monmove_pgo build completed with152 profile files and source equality to monmove_clean. Only recover utility has a missing-profile warning, same as retained build. Matched PGO comparison launched via compare_monmove_pgo.py; no result or retention claimed yet.

## Monster PGO confirmation and immutable metadata prototype

First matched-PGO comparison:512 +3.001% (358166 ->368913SPS),2048 +0.857% (229716 ->231684SPS). Fresh512 repeat +2.094% (357048 ->364526SPS), with individual measurements variable. All five quick suites and both immutable full-action corpora pass:16,777,216 decisions each, zero mismatches. Remaining reversed2048/early/depth/native and full-pipeline gates are pending; retained engine remains rawglyph_pgo. Scripts compare_monmove_pgo.py and confirm_monmove_pgo.py preserve exact controls and results.

Prepared static_object_meta as a separate ordinary-LTO screen.284 direct immutable field reads in53files use existing shared const definitions. Wand-of-nothing oc_dir is randomised and explicitly excluded, as are appearance/discovery/material/toughness/color/probability fields. Table allocation/save format remain unchanged. Audit/access inventory/patch/source hashes are under engines/static_object_meta. Unbuilt, no correctness/performance claim.

context_slab_clean repairs generator provenance in a separate copy. gen_impl reproduces the measured slab implementation byte-for-byte; runtime source otherwise unchanged. No unrestricted regeneration of the manually compacted headers. generator-parity.json records the scoped check. No new runtime claim or retention.

## Confirmed monster-layout CPU benefit; full pipeline underway

monmove_pgo_confirmation.json completes both immutable corpora with zero
differences. Fresh score512 bracket:357048 ->364526SPS,+2.094%, after the
first+3.001%. Reversed2048 candidate/control/candidate:225935control versus
228573/229474candidate,+1.367%, after the first+0.857%. Depth2048:463314
control mean versus469940candidate,+1.430%; controls drift0.020%. Early512
shows no regression; the short bracket has7.5%control drift, so do not treat
its+12.3% as a precise early gain. Full frozen score/depth pipeline is running
under validate_monmove_pgo_pipeline.py, session88960. No retention yet.

static_object_meta ordinary-LTO512:321331/321488controls,323301candidate,
+0.5885% with+0.0487%control drift. Five quick suites and final state/turn
proofs pass. This is small; sharing targets larger working sets, so the next
source screen also tests2048, alongside a repeated context_slab comparison.
compare_shared_locality2048.py is prepared but not launched. No full-corpus
or freshPGO validation spent on this unconfirmed metadata candidate.

The bitfield diagnostic has a concrete repair in the small probe: default
Clang emits i56 without callbacks; fine-grained accesses emit i8 with callbacks.
Full engine recapture has not been performed; old coverage limitations remain.

## Metadata duplicate audit and next diagnostic

The early campaign already tested exactly the same284 immutable read sites
as sharedobjs on persist. The latest static_object_meta rechecks the idea on
compact rawglyph_only, not a new optimisation mechanism. Its+0.5885%512 result
does not justify further confirmation after the earlier null. Park it; do not
launch compare_shared_locality2048.py. confirm_context_slab.py retains only the
independent packed-context confirmation and early/reset check.

Prepared trace_fine_candidate.py to compare rawglyph_only and monmove_clean
with the repaired bitfield instrumentation and explicit memory-copy tracing.
Both sides must use the same fine-grained flag, as it changes load spans. This
will quantify accessed lines for the new monster layout and guide whether a
separate cold allocation is worth implementing; it is not a hardware-miss or
native-speed measurement. Not launched while pipeline timings are running.

## Completed monster full-pipeline comparison

score: controls[185392.5218831571, 184884.14689953683], candidate184684.23SPS, -0.2453% against rawglyph_pgo. All96batch proofs and frozen actor hashes match.
depth: controls[342431.6386816542], candidate342341.64SPS, -0.0263% against rawglyph_pgo. All96batch proofs and frozen actor hashes match.
These are effectively flat results, not an extra full-training speedup. Both score controls differ by0.27%; the score candidate is0.25% below their mean. CPU rollout wait is zero. Direct combined native comparison and matched fine-bitfield footprint trace are now running serially; no retention yet.

## Utility guard exposed by diagnostic compiler

Final measurements completed: combined CPU score512+24.4453%, score2048+14.7728%, depth2048+16.4474% versus original already-optimised persist, fresh single pairs. monmove_pgo full training remains effectively flat versus rawglyph_pgo.

Session19262 terminated rc1 after baseline trace succeeded: Clang lev_comp could not link nh_mon_pool_release. monmove_clean moved cleanup outside the old utilities guard, and GCC LTO had hidden the unresolved unused function. Earlier source-cleanup rationale was incomplete. Retention is held. New monmove_utilityguard source defines NLE_LEVEL_COMPILER only on lev_comp, guards its monster-pool cleanup, and aligns generator cleanup order with checked-in implementation. Native nh_ctx_gen.c preprocessor bytes equal the measured source; old sources/binaries/results untouched. Fresh diagnostic build is running (session79005).

Paired fine-bitfield diagnostic completed: same2048decisions/512games and unchanged window-end observation/turn proof. Monster records3.6643 ->2.5088KiB touched per step (-31.53%); total53.4546 ->52.2225KiB (-2.305%). Four-step game union69.8235 ->68.5940KiB. These are instrumented access lines, not hardware misses or native speed. Fine-grained flag used on both sides. Utility repair compiles successfully with Clang. Context slab repeated2048screen launched session75606; no competing heavy work.

monmove_utilityguard generator gen_impl now exactly equals checked-in nh_ctx_gen.c. Prepared unbuilt mon_split64 based on that guarded layout: hot64/cold64 arrays in each monster pool block; m_ap_type moved cold to keep hot fields within64bytes. Explicit member-access conversion excludes saved polearm context m_id and preserves all legacy converter members. Four stack/embedded ownership cases and clone/trait-copy helpers included. Source preparation initially encountered a historical non-UTF8 source comment; archived failed preparation and used byte-preserving Latin1 transformation. No compilation/performance claim yet.

## Packed-context confirmation: park

context_slab_confirmation.json: controls218738/216926SPS, candidates220058/218141: +0.582%, less than0.828%control drift and0.87%candidate spread. ExtraRSS~95MiB. Earlier512flat; early short bracket+1.296% but6.45%control drift, not a meaningful gain. End-state/turn proofs match. Park both context_slab and generator-clean variant. No combinedPGO/full-corpus escalation for this weak candidate.

Next serialized job: screen_mon_split64.py, session55044. Builds guarded ordinary-LTOcontrol and split candidate, runs quick immutable suites plus save/copy/lifecycle/Valgrind tests, then matched512 bracket;2048 only if512 does not show a clear regression.

## Separate monster hot/cold arrays: reject

mon_split64 passes five quick immutable suites and new ownership/save/lifecycle tests. Extremal HP/time/flags roundtrips preserve144-byte legacy saves; copies own distinct cold records; hero/stack cases checked;80 context lifetimes and pool reuse pass Valgrind withzero errors/no leaks. Compilation caught two mimic-description table members sharing monster field names; fixed and failed logs preserved.

Native512ordinaryLTO: controls327385/331596SPS, split323727/325690SPS. -1.451%, with1.286%control drift. Both candidates are below both controls. Reject per predeclared>1%regression gate; no2048/freshPGO/fullcorpus escalation. Splitting each monster into two64-byte records did not improve throughput on this screen. Added indirection is a plausible cost, not a measured attribution.

Fresh guarded movement-first validation is prepared in validate_guarded_monmove.py: regeneratePGO,quickgates,fullscore/depthhashes,nativeconfirmation,fullfrozenpipelines,directcombined measurements. Source-only utility guard leaves native preprocessor tokens unchanged; final binary still receives its own measurements. Previous monmove_pgo candidate remains unretained because its source failed the Clang utility build. Retained remains rawglyph_pgo.

## Retained aligned monster movement layout

All33,554,432score/depth decision hashes and five quick suites match. Repaired utility cleanup guard; Clang diagnostic and native builds pass.

monmove_guard_pgo_confirm512: 361342 -> 367042SPS (+1.578%).
monmove_guard_pgo_confirm2048: 227575 -> 231235SPS (+1.608%).
monmove_guard_pgo_early512: 550159 -> 570418SPS (+3.682%).
monmove_guard_pgo_depth2048: 462751 -> 470399SPS (+1.653%).
Full frozen score: 184921 -> 184757SPS (-0.089%), against previous rawglyph_pgo. All96batch proofs/actor hashes match.
Full frozen depth: 343230 -> 342577SPS (-0.190%), against previous rawglyph_pgo. All96batch proofs/actor hashes match.
Direct combined monmove_guard_pgo_combined_score512: 294520.35 -> 367675.93SPS (+24.839%), fresh single pair against original persist.
Direct combined monmove_guard_pgo_combined_score2048: 196687.48 -> 227435.10SPS (+15.633%), fresh single pair against original persist.
Direct combined monmove_guard_pgo_combined_depth2048: 404143.99 -> 470743.89SPS (+16.479%), fresh single pair against original persist.

Paired source-access trace uses repaired bitfield instrumentation on both sides; see MONMOVE_GUARD_PGO_SUMMARY.json. Instrumented footprint is not a hardware-miss measurement. RETAINED_SOURCE.json now points to source-identical monmove_utilityguard ordinary-LTO comparator; previous references archived. No production edit, commit or push. Ongoing goal remains active.

## Separate object metadata names: initial screen

Hot record40->24bytes plus8B/type custom-name array in the same per-game allocation.454staticrecordvalues match the prior reference;256legacy40-byte save roundtrips,80context name-isolation/suppression checks andValgrind pass, as do allfivequickreplay suites.512controls321311/321635SPS,candidate322554SPS: +0.336%,control drift0.101%. Too small for retention alone;2048screen in progress. All native final observations and world-turn counts match. Matched ordinaryLTO comparison against rawglyph_only; no combinedPGO or fullcorpus claim yet.

Objectmetadata24 final2048 bracket:217138/215385controls,candidate217630SPS(+0.633%,control drift-0.808%). Parked as a small unconfirmed gain; no fullcorpus/PGO validation. Paired source-access diagnostic will test whether hot-record shrink actually changes touched lines.

## Targeted prefetch screens and metadata footprint

Inventory-next prefetch:512 -0.278%,control drift+0.821%. Next-monster-neighbour grid prefetch:512 -0.741%,drift+1.073%. All five quick suites and native final state/turn proofs pass. Both rejected; no fullcorpus or PGO escalation.

Objectmetadata24 paired fine-bitfield/copy trace:2048decisions across512games, unchanged window and final proof. Total accessed footprint53.4546->52.8450KiB/step(-1.1405%); lazy40 object-metadata category3.5153->2.9229KiB(-16.8514%). This is accessed source lines, not hardware misses. Native +0.34%512/+0.63%2048 remains a small unconfirmed benefit; parked.

New movement_bundle tests four earlier subpercent simplifications jointly on retained monmove_utilityguard:per-call predicates/fear checks,one inventory-key scan,and redundant floor bounds removal. Exact component patches applied with zero fuzz. This is a direct new joint test, not summed percentages. Five quick gates pass; native screening runs in session29323.

## Joint movement simplification: tentative, parked

512controls331519/327732,candidates334969/332535SPS:joint+1.252%,control drift-1.142%.2048controls219039/214664,candidates219517/220267SPS:joint+1.402%,control drift-1.997%. All candidate repeats exceed all controls, but the headline effect depends substantially on lower trailing controls. Park unconfirmed; no retained gain or fullcorpus/PGO escalation. Five quick suites and all native endpoint/turn proofs pass.

Next isolated screen:glyph_fused_export, merges raw map copy with SSE2classification/mapping in the existing fill. Maintains eager discovery and underfoot semantics. Current profile identifies fill_obs4.5%self; avoided pass is only a portion of that. No claimed gain yet.

## Fused glyph copying/classification: initial null

Five quick gates and native endpoint proofs pass.512controls332083/333223,candidates333451/332458SPS: +0.0906%,control drift+0.3433%. Park null; no2048 or fullcorpus escalation. New glyph_fused_tail8 follows the concrete per-row scalar-tail tradeoff:one overlapping end-aligned SSE2block replaces seven scalar cells perrow. Repeated overlap mapping is pure and all accesses remain inbounds. Screen launched serially in session12965; no attribution/performance claim yet.

## Vector-tail followup and inventory-export screens

Vector-tail512controls332855/327776,candidates331791/329217SPS:+0.0572%,control drift-1.5258%. Five quick suites and endpoints match. Park null; no2048/fullcorpus escalation. The scalar-tail followup does not rescue fusedglyph export.

Two independent inventory-export prototypes on current retained source: inv_export_known_first delays shows_spe type predicates until the item known bit is true; inv_export_fused emits identified-type glyphs from the same walk/predicate already used for inv_state, keeping a standalone fallback. Profile locations158/106samples motivate these read reductions, not claims of hardware misses. Serial driver run_inv_export_screens.py launched; no native claim yet.

## Inventory screens closed; compact per-game item state

Known-first checks:512 -0.2570%,control drift+0.6343%. Fused inventory output:512+1.2086%,control drift+1.8081%. Both five quick suites and endpoints match; parked, no retained gain.

objstate10 splits shared type definitions from mutable state, reducing per-game stride40->10B plus8B/type name pointers. Compiles and passes all five quick suites,454 unchanged definition records,116224 field-level legacy save conversions,80 context name/discovery/direction-isolation checks and Valgrind. Full saved-game interoperability is not yet tested. Python import exposed an inherited unresolved monster-pool cleanup symbol; matching the existing object-pool guard to metadata-build mode fixes the scope of the cleanup. Rebuild/check pending; no native gain claimed.

## Compact item state: native and access-footprint result

objstate10 five quick suites and native end-state/turn proofs pass.454 static
records unchanged,116224 field-level legacy conversions,80 context isolation
checks andValgrind pass. Actual savenames/restnames sections cross-read in both
directions with ordinary retained engine, externalcomp andzerocomp(eight
readbacks); this is not a complete saved-game interoperability claim. Python
extension/rlmain build and metadata import pass after isolated inherited pool
cleanup guard repair. Native engine hash unchanged by that guard repair.

512ordinaryLTO controls342630/328703,candidates337551/330828SPS: -0.4402%,
control drift-4.0648%.2048controls225216/218991,candidates224329/224187SPS:
+0.9700%,control drift-2.7642%. Park unconfirmed,no fullcorpus/PGO escalation.

Matched fine-bitfield/copy diagnostic:2048decisions across512games, same
window/ticks/obs e19798d5fd4e1c2e and14191worldturns. Private item metadata
lazy40 3.51285->1.90506KiB/step;shared-library data3.45096->5.52591KiB/step.
Total52.22250->52.69238KiB/step(+0.900%). Four-step per-game union68.59399->
69.05591KiB(+0.673%);whole512game batch union31.75159->30.88159MiB(-2.740%).
Thus shrinking mutable records40->10B(+separate8Bnames) does not translate to
large total-access reduction. Source accesses, not hardware misses; no claim
that shared reads necessarily miss caches. DetailedJSON/CSVunder
trace_objstate10_fine_copies.

Next move_load_reuse removes repeated carrying-load/capacity computation only
within m_move's nonmutating target-search. Existing0.5%can_carry and19.1%m_move
profile suggests a small cheap test. Allquickgates pass; native screen running
session85803. No retained gain claimed.

Local carrying-load reuse:512 -0.5419%,control drift-1.7465%;allfivequickgates/nativeendpoints match. Parknull. Next nativecompiler screen uses availableClang18+LTO against retained ordinaryGCC+LTO;branch-heavy movement dominates existingprofile. Runtimeengine logic unchanged;sourceonlyhas metadata guard repair. NoPGO reused andno fastmath/nativeISAflags. Screening live session90853.

## Native Clang ThinLTO rejected; TLS-address option insufficient

Both clang_lto and clang_lto_tls compile and pass all five quick suites, but
standard512-env24-worker replay immediately crashes before any valid timing.
GDB shows rhack caches the address of a thread-local slot across a yield.
After migration that address differs from the current worker's &nh_cur.
The old slot's context reports WIN_MESSAGE=-1 while the current game's value
is1; the current C++window instance matches current_nle_ctx.

Disabling Clang18 tls-load-hoist at compilation and the LLVMgold backend
does not remove this cached-slot code or the failure. The flag's first
placement broke CMake's non-LTO compiler probe; repaired target-only linker
flags build successfully, but native correctness still fails with the same
direct TLS evidence. See both engines' gdb_tls_slot.log and recipe/patches.
No performance claim. Retained GCC engine remains unchanged. These quick
suites alone do not cover coroutine migration; standard replay is essential.

Next movement_size is an isolated GCC size-oriented compilation screen for
m_move and mfndpos only, motivated by their combined35%self profile and
roughly23KB of ordinary compiled code. No cache-miss attribution claimed.

## Two GCC compiler screens: no retained gain

movement_size applies optimize(Os) only to m_move/mfndpos. Combined function
size23168->12965bytes(-44.04%). Five quick suites/native endpoints match.
512controls349233/329282SPS,candidates320328/314228SPS: -6.479%, control
drift-5.713%; both candidates belowbothcontrols. Reject. Smaller code alone
does not establish a speedup or identify instructioncache as the bottleneck.

gcc_tune_native keeps x86-64ISA and uses GCC's native alderlake cost/scheduling
model. Five quick suites/native endpoints match.512controls332784/328353,
candidates329724/327789SPS: -0.548%,control drift-1.332%. Park null.
No2048/freshPGO/fullcorpus escalation for either.

Next glyph_dirty_bits shrinks display changedflags1680->336bytes/game and
visits marked cells in original order, rereading live bits/bounds aftereach
callback. ASan+UBSan comparison with byteflag scan passed1755941 boundary
andcast checks,52054 simulated callbackvisits,8192row-isolation trials.
Native/quickgate screen pending in session48889. No claimed throughput gain.

## Display bitset rejected; virtual-page footprint guides next experiment

glyph_dirty_bits: allfivequickgates plus boundary/callbacksanitizer checks pass.
Native512controls328728/327989SPS,candidates326576.92/326634.68SPS: -0.534%,
control drift-0.225%. No2048/PGO/fullcorpus escalation. Retained unchanged.

Reused matched fine-bitfield/copy captures; no new profiling run. Retained
ordinary source touches87.41 distinct virtual4KiBpages perstep,70.41 excluding
records classified assharedlibrary. Per-game four-stepunion103.30pages.
Compactobjstate10 touches88.49all/67.18nonlibrarypages; its extra sharedmetadata
reads offset much of the privatefootprint reduction. These are pageoccupancy
counts, NOT TLBmisses or physicalmapping/THP measurements. Nonlibraryincludes
unknown/threadregions, not all strictlyper-gameprivate. Categorypagesoverlap.
See touched_pages/results.json,frames.csv,LIMITATIONS.md.

Firstunclassifiedpagetouch attribution highlights t_at(1.18pages/step), alongside
TTY/bookkeeping/string/TLS accesses. Combined with existing mfndpos native
loop samples, this motivates trap_neighbors: replace repeated trap-listwalks
for candidatecells with one local scan. Nine pointers, no persistent cache,
firstmatch/listorderpreserved. Audited fear/sanctuary/gas/carrying predicates
do not mutate traplist. Fivequickgates pass; native512screenrunning. Optional
perquery comparison code isprepared but NOT yetrun. No gain claimed.

## Trap lookup screens and a timing confound

Nine-pointer trap_neighbors:512controls341579/327826SPS,candidates334471/
329504SPS; -0.811%,control drift-4.026%. Fivequickgates/endpoints match;
park inconclusive, nofullcorpus/PGO escalation.

Nine-bit trap_neighbor_bits:fivequickgates/endpoints pass. An extra excluded
precondition replay334706SPS was followed by controls321978/271104SPS and
candidates270304/269251SPS. Headline-9.025%cannot be causally attributed to
the patch:the unchanged control itself slowed15.800%, and the late control
is close to both candidate values. Same workload/hashes/worldturns.
Actual processcheck showed only our replay doingheavywork; CPUidentity is
stilli9-14900K,governor powersave,maxperf100,no_turbo0. One sysfs sample
showedP~3.8GHz/E~3.2GHz andreportedpackage56C; this is not sufficient to
identify a thermal/power cause. No systemsettings changed.

Repeat trap_neighbor_bits withoutrebuild, bracketA/B/A,isrunning in session
32933. Full sourceoracle andretention gates remainunrun because no useful
nativegainhasbeenestablished. Retainedproduction/experimentalbaseline unchanged.

## Stable trap-bit repeat closes the confounded screen

Without rebuilding, A/B/A512 controls270431/270517SPS, candidate269134SPS:
-0.4954%,control drift+0.0320%. All endpoints/worldturncounts match. Reject
trap_neighbor_bits; the original-9.025%ratio is NOT its measured causal cost.
No fullcorpus/PGO/early/training gate escalation.

The now-stable control offers a useful chance to resolve movement_bundle's
prior+1.2–1.4%inconclusive results. Candidate/library hashes match original
quickgate/native runs; no rebuild or redundant quickgate run.
confirm_movement_bundle_native.py launchedserially, session1368. It repeats
512ABBA then2048only if gain>0.75%andaboveabsolutecontroldrift. No win
or retentionclaimed before result. Production/retained sources unchanged.

## Stable movement confirmation and persistent trap filter

movement_bundle unchanged binary: stable ABBA gives +0.8367% at512 with
-0.2156% control drift, and +0.5042% at2048 with -0.1239% drift. All native
endpoint/world-turn proofs match. This is a small provisional ordinary-LTO
gain, not a retained PGO or full-training improvement. A fresh PGO recipe is
prepared; its source includes the metadata-only pool cleanup guard repair.

trap_bitmap appends a210-byte per-game presence filter. Actual maketrap and
deltrap, retyping, connected pits, bounds, duplicates and context switching
passed5595762 oracle comparisons and Valgrind with0errors/0leaks. Synthetic
relocation does not prove water-level relocation coverage. Allfiveimmutable
quick suites pass.512controls270907/270104SPS,candidates269576/269198:
-0.4133%,control drift-0.2966%; both candidates belowbothcontrols. Reject;
no fullcorpus/PGO/training escalation.

engr_bitmap independently tests the same absence-filter idea on engravings.
Its directed tests passed4628244 comparisons,8contexts,actual engraving-section
save/restore with zerocomp/externalcomp,andValgrind0errors. A test harness
initially lacked the private head_engr macro; fixed that test declaration,
without changing engine code. Fivequickgates pass; native screen running.

cursor_format_guard is prepared but unbuilt: xputs(tgoto(...)) currently
formats via Sprintf even when xputs discards output. Guard the two formatting
calls with the existing nle_emit flag while retaining cursor bookkeeping.
Existing native profile assigns cmov about0.4%cumulative; expect a modest
ceiling, not a large win. No new profile or throughput claim.

## Engraving and suppressed-cursor screens closed

engr_bitmap:512 -0.11994%,control drift+0.15324%; no useful native gain.
cursor_format_guard:fivequickgates pass,512 -1.62145%,control drift-0.48410%.
Both candidate runs were below both controls; no retention. Candidate runs
also had more involuntary switches, so the result does not isolate an
instruction-level cause. No expensive full-trajectory/PGO escalation.

Next last_window_string retains only the last RL window string, the only
string consumed by fill_obs. Separate TTY history/menus are unchanged.
Prepared source and mutation audit exist; start native screen next.

## 9 October: remaining locality gap rechecked

User-requested follow-up is complete. No experiment from this follow-up is still running. Full results: locality_recheck_20261009/REPORT.md.

- Latest retained monmove_guard_pgo engine: ordinary vs burst16 at identical mature windows gives +21.44% CPU throughput at512 and +67.04% at2048. Two serial repeats per arm, stable controls. Burst uses known future actions; diagnostic, not a training speedup.
- Paired profiles show distributed savings across movement/neighbour checks, observations, inventory and floor-object access.
- Simple common-buffer ordering: +0.09%, parked.
- Recheck preferred ready buffer after useful work: repeated ordinary one-action CPU replay216301→236933 SPS (+9.54%) at2048. At512 mature it loses3.74% and4.68%; short early results are noisy (-1.02%,+3.50%). More voluntary context switches accompany the small-population regression.
- Every-step proof:4,194,304 scheduler hashes match existing immutable reference; separate burst proof1,048,576 hashes match. Observations/reward/terminal/masks included.
- Full frozen-policy pipeline:185406→185017 SPS (-0.21%, flat single pair), all96 batch-state proofs and actor hashes match; zero measured rollout-tail wait on both arms.15.55M model,2048 agents,4 buffers,horizon128,batch262144,mb4096,24 workers,96epochs.
- No new default retained. Prototype/header patches and isolated pipeline copy remain reviewable. Best continuation is reducing waiting/imbalance while preserving the large-population locality gain; broad SIMD is secondary. Do not claim +67% is available to ordinary training or +9.54% is a training gain.
- Integrity:8 protected live files,1290 retained source files and retained library unchanged. The isolated pipeline source differs only in src/env_pool.h. No production edits/commits/pushes.

Previous last_window_string job also finished:512+0.853%,2048+0.551% (2048 control drift0.875%). Not retained; earlier live-session note is obsolete. Movement-bundle freshPGO recipe remains prepared but unrun.



## 9 October: faster benchmark loop tested

User-requested measurement study complete; no test jobs remain. Platform goal stayed paused. See fast_loop_20261009/REPORT.md and summary.json.

- Untimed warm chunks of128 plus128 ordinary settle decisions cut2048 preparation71.5->39.8s; chunk512 was not faster. Measured ordinary SPS and endpoints unchanged.
- A bare process fork was INVALID: private game files and inherited seekable offsets were missing from the snapshot. Fixed by restoring both, with worker/OpenMP teardown and a verified single-thread parent before fork.
- Restored short native trials:512 envs x2048 decisions take~4s/trial,2048 x512 take~6.5s/trial including restore/settle/cleanup. Four-trial runtime A-B-B-A costs16s/26s after one-time10s/39s preparation.
- Known scheduler effect: short2048+9.74%,long2048+9.43%,512-4.01%. Control repeat ranges0.07-0.15%, descriptive only. Short5s profile5367samples recovers same major hotspots (monster turns61.9%inclusive,movement+neighbours38.2%self).
- 6,291,456 immutable per-decision hashes match,0differences. All8 protectedlivefiles,1290retainedsourcefiles,retainedlibrary and referencehash unchanged.
- Use this CPU-only short screen to prioritize/reject ideas; longer fresh-process/golden/fuzz/fullcorpus/frozen-training gates before retention. No engine optimisation promoted here.
- snapshot_test.py supports --engine BUILD_DIR for new source binaries. Each binary needs its own preparation/snapshot; do not reuse saved stacks across different engines. Fixed trial batch per invocation, not a resident server. Runtime ABBA measured here uses two flags in one binary; fresh compiled candidates still need separate paired controls. Memory-layout changes need fresh-process confirmation for COW effects.


## 9 October: first fast-loop candidates screened

focus_quota_20261009/REPORT.md: bounded ready-buffer recheck quotas4/16 tested serially, two native repeats per mode at512 and2048. Quota4:+4.44%2048/-1.32%512; quota16:+7.32%/-2.10%; unbounded:+9.04%/-3.58%. Both quotas parked: soften but do not solve locality/waiting tradeoff. All16 native endpoint/turn proofs match; expensive full gates intentionally not rerun for parked variants. No new retention or production changes; no job remains.

Remaining priorities: scheduler placement/contention rather than further arbitrary quotas; prepared movement_bundle PGO check (ordinary-LTO provisional+0.5–0.8%); new trace-guided working-set reductions only with a concrete target. Broad prefetching/SIMD/structure shrinking had many flat or negative screens; consult ledger before repeating.


## 9 October: user requests causal diagnosis before more candidate patches

Latest direction: stop proposing arbitrary scheduler/layout variants; identify the cause and quantified headroom first. movement_diagnostic_20261009/REPORT.md reuses current normal/burst instruction samples and verifies context/object offsets with the retained headers. Strong sample clusters immediately follow terrain, floor-object pointer, monster pointer and item-type reads inside m_move/mfndpos. These are diagnostic leads, NOT precise cache-stall attribution. Fresh perf probe confirms counters unavailable (paranoid4); no host settings changed. No new replay/engine build. Next: sampled movement call/path counts and CPU latency, then selective read-only warming of implicated accesses with prep cost reported. Require quantified cost removed before implementing another optimisation. No job remains.



## 9 October: movement locality measured; diagnostics complete

movement_causal_tsc_20261009/REPORT.md completes the user-requested causal investigation. Exact movement work counts match across512/2048 and ordinary/burst. Unchanged retainedPGO2048 step128.90us; read-only warming floor-object records saves9.73us (prep+11.93us), all5groups saves20.96us (prep+21.34us), no net optimisation. Sampled inner TSC scopes in ordinary-LTO diagnostic: movement89.64->77.58us normal->burst, floorsearch17.54->14.43us with floorrecord warming; overlap/overhead caveats inreport.3,407,872 immutabledecisionhashes match,0differences. NestedCPUclock attempt discarded; inner-TSC path timers still perturb sampledsteps, so causal effect confirmed independently on unchangedengine.8protectedfiles,1290retainedsources,library/referencehash unchanged. No jobs remain; platform goal not resumed. Next target is specific floor-object metadata reads/invalidation, with measured few-us path budget; no patch retained.


## 9 October: compact floor metadata tested through 8192 envs; parked

floor_metadata_20261009/REPORT.md: two isolated prototypes from retained source.
4-byte packed type/class/coordinates in existing floor index, plus53 type/class
store invalidations; second passes cached fields into searches_for_item. Extra8KiB/game.
Ordinary-LTO paired screen first512-0.38%/2048-0.45%; complete512+0.38%/2048+0.58%/8192+0.25%.
No substantial win; no PGO/full-corpus/training promotion. Retained monmove_guard_pgo unchanged.
Matched256-decision control window:512=261115SPS,2048=202814,8192=202614;
CPU137.96us/decision at both2048/8192. Peak8192RSS4413MiB,zero major faults.
8192duplicates512 independent recorded streams16x; CPU replay, not live training.
Both5quick suites pass; each262144immutabledecision hashes match. Independent floor
index974402query test including automatic type/class invalidation passes; reference
and firstprototype Valgrind0errors0leaks. All42nativeendpoints match.
8productionfiles,1290retainedsources,retainedlib/reference hashes unchanged.
Patches,commands,rawresults,integrity and complete source manifest archived in experiment.
No jobs remain; platform goal was not resumed. Result limits this cached-view idea;
it does not establish that broader authoritative-state compaction cannot help.

## 9 October: compact metadata failure measured directly

Completed user-requested diagnosis; see floor_metadata_diagnosis_20261009/REPORT.md and summary.json. No experiment left running; no new retention.

- Matched fine-grained source-access traces (512 mature games x4 decisions, explicit memory-operation callbacks, original endpoint exact): compact metadata cuts floor load callbacks23% but all distinct64B data lines835.56->832.89 (-0.32%). Floor lines60.62->54.65; extra metadata4.29lines/step. These are NOT hardware cache misses. Initial category501 collision corrected to9000 and recollected; old ambiguous trace excluded.
- Original floor-index rebuild accounts for29.56/60.62 floor first-touch lines. Compact version still reads full records during index packing/building and later consumers; reducing repeated loads did not remove the same fraction of memory footprint.
- Native GCC LTO bookkeeping-only control vs original at2048: -0.51%. Full metadata flat/unreliable (secondprocessslower), consistent with previous null screens. A-B-C-C-B-A,2trials/process, same warm8192/measure512.
- New isolated floor_index_incremental updates original cached pointer/coordinate arrays on place/remove/split/replace, preserving chain order and cursor-generation fallback; bulk/overflow invalidation retained. No extra metadata/type setters.
- New trace: floor lines60.62->36.02 (-40.6%), total835.56->811.08 (-2.93%); rebuild firsttouches disappear in this window. Native2048 A-I-I-A,2trials/process:205495->207017SPS (+0.74%). Small provisional CPUreplay gain, not a training result. Not promoted; no freshPGO/fullcorpus/depth/frozenpipeline gates.
- Correctness: all5quickgolden/fuzz suites,2136431independentindexqueries,Valgrind0errors/noleaks,262144immutableperdecisionhashes exact;20nativewindows endpoints match. Protected8productionfiles,1290retainedsources,retainedPGOlib,reference unchanged.
- Next: examine a larger measured source of avoidable traffic, or explicitly combine/confirm this small prototype if worthwhile. Do not present it as resolving the large warm/burst locality gap or compare ordinaryLTO directly to retainedPGO.

## 9 October: full normal-versus-burst gap accounting

User-requested diagnostic completed; full_gap_20261009/REPORT.md and SUMMARY.json. No production edits or new retained optimization. Full functional time budget established; hardware causes are not completely separated.

- Retained engine, 2048 instances / 512 unique mature recorded games, warm8192/measure512. Native normal214945 vs burst16 353806SPS (+64.6%). All-step CPU130.70->79.87us/decision:50.83us gap,98.2% inside puf_step; outside CPU only0.90us of gap. Accounting perturbs gap by~0.4us. Exclusive PC profile partitions entire budget, no nested inclusive addition. Biggest: monster movement12.78us, player/core6.21us, engine observation5.09us, burden4.26us, display4.03us, other monster3.69us, floorindex2.58us.
- Broader warm reads locate real data locality: paired normal/burst tests reduce step gap50.71->10.93us, closing39.78us (78.45%, game-bootstrap95%38.42-41.21us). Object-type table (lazy40) and glyph buffer(lazy15) were missed when warming context pointers alone; individually save4.34/1.96us of next-step time. Do not sum overlapping interventions.
- Preparation is NOT a production win: targeted normal-step read preparation costs68.48us for40.66us saving. Burst changes78.28->77.40us. Read+same-value-write ownership warm is slightly worse, residual11.89us. Fixed worker ownership reduces step latency but throughput drops213k->131k.
- Final single-P-worker warm test leaves8.99us residual (45.33vs36.34us) versus11.44us with original mixed-corelayout in same128-decisionwindow. Migration/concurrentengineworkers cannot explain all residual. Do NOT call remaining cycles cache, frontend, or TLB without evidence. PMU unavailable, host settings unchanged. Single/core comparisons change frequency/composition; effects cannot be added into unique physical-cause decomposition.
- 983040 immutable per-decision hashes exact; all native/proof endpoints match. Protected8productionfiles,1290retainedsourcefiles,retainedPGOlib/reference unchanged. Profilewrapperbinary rebuilt foraffinity cases; rely on modulelevelwrappercategory and unchangedenginefunctionsymbols, not oldwrappersourcelines.
- Clear next target: reduce/retain actual repeatedly touched data across ordinary policy-dependent steps while keeping utilization. Floor-only compaction cannot recover distributedheadroom; earlier totalaccesslinecuts0.32%/2.93% explain small wins. No blindprewarm or fixedownership default. Remaining9-11us stillrequirescausalattribution.


## Movement follow-through — 2026-10-09

All four requested steps completed: direct combined timing, movement phase census, cursor-tail screen, matched fresh PGO and frozen full-pipeline controls. See [report](movement_followthrough_20261009/REPORT.md) and [results](movement_followthrough_20261009/RESULTS.json). Live source and retained engine unchanged.
