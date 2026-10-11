# Current continuation state

Read /root/.codex/attachments/77588057-88fc-4790-a032-23973b2ab1b5/pasted-text-1.txt first. Ongoing goal; no completion from a report. Isolated copies only, no production edits/commits/pushes. Serialize heavy work; commentary at least once/minute.

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

## 9 October: movement locality measured; diagnostics complete

movement_causal_tsc_20261009/REPORT.md completes the user-requested causal investigation. Exact movement work counts match across512/2048 and ordinary/burst. Unchanged retainedPGO2048 step128.90us; read-only warming floor-object records saves9.73us (prep+11.93us), all5groups saves20.96us (prep+21.34us), no net optimisation. Sampled inner TSC scopes in ordinary-LTO diagnostic: movement89.64->77.58us normal->burst, floorsearch17.54->14.43us with floorrecord warming; overlap/overhead caveats inreport.3,407,872 immutabledecisionhashes match,0differences. NestedCPUclock attempt discarded; inner-TSC path timers still perturb sampledsteps, so causal effect confirmed independently on unchangedengine.8protectedfiles,1290retainedsources,library/referencehash unchanged. No jobs remain; platform goal not resumed. Next target is specific floor-object metadata reads/invalidation, with measured few-us path budget; no patch retained.

## 9 October: user requests causal diagnosis before more candidate patches

Latest direction: stop proposing arbitrary scheduler/layout variants; identify the cause and quantified headroom first. movement_diagnostic_20261009/REPORT.md reuses current normal/burst instruction samples and verifies context/object offsets with the retained headers. Strong sample clusters immediately follow terrain, floor-object pointer, monster pointer and item-type reads inside m_move/mfndpos. These are diagnostic leads, NOT precise cache-stall attribution. Fresh perf probe confirms counters unavailable (paranoid4); no host settings changed. No new replay/engine build. Next: sampled movement call/path counts and CPU latency, then selective read-only warming of implicated accesses with prep cost reported. Require quantified cost removed before implementing another optimisation. No job remains.

## 9 October: first fast-loop candidates screened

focus_quota_20261009/REPORT.md: bounded ready-buffer recheck quotas4/16 tested serially, two native repeats per mode at512 and2048. Quota4:+4.44%2048/-1.32%512; quota16:+7.32%/-2.10%; unbounded:+9.04%/-3.58%. Both quotas parked: soften but do not solve locality/waiting tradeoff. All16 native endpoint/turn proofs match; expensive full gates intentionally not rerun for parked variants. No new retention or production changes; no job remains.

Remaining priorities: scheduler placement/contention rather than further arbitrary quotas; prepared movement_bundle PGO check (ordinary-LTO provisional+0.5–0.8%); new trace-guided working-set reductions only with a concrete target. Broad prefetching/SIMD/structure shrinking had many flat or negative screens; consult ledger before repeating.

## 9 October: faster benchmark loop tested

User-requested measurement study complete; no test jobs remain. Platform goal stayed paused. See fast_loop_20261009/REPORT.md and summary.json.

- Untimed warm chunks of128 plus128 ordinary settle decisions cut2048 preparation71.5->39.8s; chunk512 was not faster. Measured ordinary SPS and endpoints unchanged.
- A bare process fork was INVALID: private game files and inherited seekable offsets were missing from the snapshot. Fixed by restoring both, with worker/OpenMP teardown and a verified single-thread parent before fork.
- Restored short native trials:512 envs x2048 decisions take~4s/trial,2048 x512 take~6.5s/trial including restore/settle/cleanup. Four-trial runtime A-B-B-A costs16s/26s after one-time10s/39s preparation.
- Known scheduler effect: short2048+9.74%,long2048+9.43%,512-4.01%. Control repeat ranges0.07-0.15%, descriptive only. Short5s profile5367samples recovers same major hotspots (monster turns61.9%inclusive,movement+neighbours38.2%self).
- 6,291,456 immutable per-decision hashes match,0differences. All8 protectedlivefiles,1290retainedsourcefiles,retainedlibrary and referencehash unchanged.
- Use this CPU-only short screen to prioritize/reject ideas; longer fresh-process/golden/fuzz/fullcorpus/frozen-training gates before retention. No engine optimisation promoted here.
- snapshot_test.py supports --engine BUILD_DIR for new source binaries. Each binary needs its own preparation/snapshot; do not reuse saved stacks across different engines. Fixed trial batch per invocation, not a resident server. Runtime ABBA measured here uses two flags in one binary; fresh compiled candidates still need separate paired controls. Memory-layout changes need fresh-process confirmation for COW effects.

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

## Completed this goal turn
- clang_lto_tls: repaired target-specific LLVMgold flags; compiled/5quickgatespassed but native migratingcoroutines stillcrash. GDB confirms stale TLSslotaddress acrossworker migration, oldslotWIN_MESSAGE=-1/current1. Disabling tls-load-hoist ineffective. Bothplain/disabledClangrecipes rejected; retainedGCC unaffected. Logs engines/clang_lto*/gdb_tls_slot.log. No validClangtiming.
- movement_size: m_move+mfndpos code23168->12965B (-44%), native512-6.479%; bothcandidatesbelowcontrols, reject. Fivequickgates/endpoints pass.
- gcc_tune_native: mtunealderlake, originalx86-64ISA; native512-0.548%within1.332%drift. Parknull. Fivequickgates/endpoints pass.
- glyph_dirty_bits: flags1680->336B/game, originalupdateorder/callbacksemantics. ASan+UBSan1755941 boundary/castchecks,52054callbackvisits,8192row-isolationtrials pass;5quickgates/endpoints pass;native512-0.534%with0.225%drift. Reject.
- trap_neighbors:9-pointer localmap withinmfndpos; native512-0.811%with4.026%drift;park. 5quickgates/endpoints pass.
- trap_neighbor_bits:9presencebits,originalt_atonhits. InitialABBAconfoundedby15.8%unchangedcontrolslowdown;do NOTattributeheadline-9%topatch. Immediatewithout-rebuildABA controls270431/270517,candidate269134: -0.495%,drift0.032%. Reject. Fivequickgates/endpoints pass. OptionalNLE_TRAP_NEIGHBOR_VERIFY NOTRUN;no expensivegatesforrejectedcandidates.
- Reused source-access captures for virtual4Kpagecounts. Retained87.41all/70.41nonlibrarypagesperstep;objstate10 88.49/67.18. NotTLBmisses,notphysicalmapping/THP;nonlibraryincludesunknown/threadregions. touched_pages/{results.json,frames.csv,unclassified_attribution.json,LIMITATIONS.md}. Existingnativeinlinedtraploop evidence plus t_atfirst-page attribution motivated thetraptests.
- Hardwarestill14900K; no competingheavyjob. A sysfs sampleP3.8/E3.2GHz/package56C does NOT prove slowdowncause. No governors/power/syssettingschanged.

## Retained and integrity
RETAINED.json remainsmonmove_guard_pgo; RETAINED_SOURCE ordinarymonmove_utilityguard. Previous33.55Mdecision,early,frozenpipeline gatesstand. No new winretained thisturn. Protected8livefiles,1282originalfiles,bothretained1290filemanifestsandlibraryhashesunchanged: integrity_compiler_dirtybits_turn.json.
Inherited metadata Pythonmodule poolcleanupguard needs NLE_OBJECTS_GLOBAL instead ofNLE_LEVEL_COMPILER in generator/generatedsource; prototypesrepairit, retainedsource notedited. Runtimeenginehashbefore/afterguardrepairidenticalinobjstate10.

## Other prior parked ideas
objstate10 fullsectionsavenames/restnames8crossreadbacks andextraunit/Valgrind pass;nativegainunconfirmed; sourceaccessbatchunion-2.74%only. move_load_reuse null. Inventoryknownfirst/fused nullorwithinnoise. Consult ARTIFACTS.json/REPORT.md before repeatinganidea. latest_native_table.md refreshedbeforecurrentbundleconfirmation.

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

## 9 October: interactive flame graphs

Requested viewer complete: /puffertank/experiments/nethack-flamegraphs-20261009/out/index.html (self-contained offline HTML), portable archive /puffertank/experiments/nethack-flamegraphs-20261009/nethack_flamegraphs.tar.gz. Five interactive views (normal, burst, prepared data, two differentials), zoom/search/browser checks pass. Same retained engine; 196,608 immutable hashes exact; all9mainendpoints match; protected production/source/library/reference unchanged.

Per-thread CPU timers with gperftools/libunwind; perf cpu-clock denied. 2048instances,512uniquegames,warm8192/measure1024,two stack captures/condition plus unprofiled calibrations. Stack samples normal8458/burst5063/warmed5779; CPU128.587/77.456/87.893us perdecision. Preparation excluded explicitly; warming costs more than saves. Profilingselectedsteps adds7–8%; shown widths calibrated against unprofiled runs. Largest extra costs again m_move/mfndpos, fill_obs, encumber_msg, newsym. Real coroutine call stacks; no cache-miss attribution. Report and exactmethod in /puffertank/experiments/nethack-flamegraphs-20261009/REPORT.md. No new optimization retained.

## 9 October: counter-free warming omission study

Completed warming_leaveout_20261009/REPORT.md. Unchanged engine, 2048 instances / 512 unique games, warm8192/measure256,20 forward/reverse timing cases. Full warm closes39.87us of50.79us gap; warm costs73.26us so not an optimization. Omitting context+grids loses17.31us, lazy allocations7.34us, inventories2.80us; explicit entity-record/stack/NLE-context warm has no measurable incremental effect in this combination. Effects overlap; inventory traversal itself touches entity headers; nulls do not mean those accesses are free or that joint omission is safe to infer. Next: subdivide core context and auxiliary allocations.262144 immutable hashes exact,28 endpoints match,8 protected/1290 retained files+library/reference unchanged. No jobs remain; platform goal not resumed.

## 9 October: finer locality groups

Completed warming_fields_20261009/REPORT.md. Full warm127.86->86.83us but costs73.89us; no speedup claimed. Conditional omission penalties: object types4.91us, terrain4.79, monster grid3.95, remainder3.61, vision2.94, floor grid2.74, glyph buffer2.63, RNG1.63, lookup caches1.43, hero/flags1.17, otherlazy0.56. Distributed effects, overlapping/nonadditive.28timing+14proof cases;458752 immutable hashes exact;8protected+1290retained files and library/reference unchanged. Isolated persistent glyph-cache candidate launched, result to follow in engines/public_glyph_cache. No platform goal resumed.

## 9 October: persistent public glyph cache

park; no new optimization retained. See engines/public_glyph_cache_release/REPORT.md. diagnostic-capable:512env +0.33% (control drift+0.29%) / diagnostic-capable:2048env +0.08% (control drift-0.23%) / release:512env +0.47% (control drift-0.00%) / release:2048env +0.34% (control drift-0.24%). Both builds5quick gates+262144immutable hashes each; diagnostic-capable build5original-lookup verification suites. All endpoints match; protected production, retained source/library and reference unchanged. No full PGO/training claim.

##9 October: co-located movement tiles

Tested movement_tile16; parked, no new retention. 2048env -0.07% (control drift-0.17%) / 512env -0.23% (control drift+0.28%).16B cell combines6B terrain+existing cached type+monster pointer; total context171816->173568B. All5quick suites,262144 immutable decisions and1M ASan/UBSan updates+save roundtrips pass. All endpoints match.8protected production+1290retained files+library+reference unchanged. See engines/movement_tile16/REPORT.md. No jobs remain. No goal resumed.

## 9 October: next-step review and movement census

Completed movement_fastpath_census_20261009/REPORT.md. 262144 decisions:99.21 movement entries,95.57 neighbour calls,762.57 cells per decision;40.48%rock,23.76%occupied(overlap),14.97%whole-call simple classification. New neighbour_prefilter changes only mon.c; all5quick suites+262144hashes pass. 2048 ordinaryLTO +2.238% (control drift+0.296%). 512 ordinaryLTO +3.960% (control drift+0.134%). Parked, noPGO/fullcorpus/pipeline retention. Next standard-rollout candidate: bulk eight-neighbour terrain/occupancy rejection, ordered survivors through original full logic; no large gain established yet. Prior grouped collector remains larger proven alternative (+28.1%olderengine/controlled5M; newinferencepartitiondoesnotmatcholdbitwise), butchangescollectionandwasNOTretestedhere.1299protected/source/libfiles+referenceunchanged. Nojobs/newgoal/productionedits/commits/pushes.

## 9 October: bulk movement candidate bitsets

Implemented isolated movement_masks and fresh movement_masks_pgo. PGO matched
standard snapshot rollout results: 512 env +8.16%; 2048 env +2.53%. See engines/movement_masks/REPORT.md.
656-byte derived bitset payload; terrain and occupancy setters audited including
worms, mounts, water-level changes and level restore/clear. Full original rules and
candidate order preserved for survivors. Verification build compares old/new
ordered outputs and hero-image side effects at every mfndpos call.
Three builds pass all5quick suites; release+verification each262144 immutable
decisions; PGO fullscore+depth33,554,432 decisions exact.1M ASan/UBSan helper updates
pass. Protected 1301 files/reference unchanged. No production edits,
default retention, commits, pushes or goal resumed. Before retention: fresh
non-snapshot/early timing and frozen full-pipeline checks. No jobs remain.

Movement-mask follow-up: equal 512-decision windows confirm +8.19% at512 vs prior +2.53% at2048. Sampled puf_step CPU92.56->85.76us vs129.13->125.88us: saving6.80 vs3.25us. Not merely dilution/window mismatch; locality leading hypothesis, exact attribution still open. See movement_masks/matched_window_summary.json and report appendix. No jobs/source changes.

## 9 October: movement query data-flow follow-up

movement_query_20261009/REPORT.md: maintenance-only control + stack profiles complete. Added-summary/layout cost about0.2%512/0.6%2048, too small to explain smaller large-population filter gain. Query profile improves at both sizes; offsets outside query remain approximate, not hardware-causal attribution. New movement_occupancy_query reuses raw occupancy bits for diagonal/destination tests; no new state/writers. Parked: incremental512-0.024%,2048 noisy nonpositive mean.15quick suites +786432immutable decisions exact. Existing movement_masks candidate and retained monmove_guard_pgo unchanged. No newPGO/fullcorpus/training promotion. All protected sources/libraries/livefiles/reference unchanged. No experiment jobs remain.

## 9 October: full neighbour-query subsystem trial

movement_subsystem_20261009/REPORT.md. Implemented integrated compact terrain/pile/trap/gas grid, write-side invalidation, query-local capabilities and all mfndpos callers through unchanged API. Native LTO versus existing bitsets: 512 +0.69% (below control drift); 2048 -1.31%; separate native harness -1.52%. Parked, no promotion/PGO/training claim. 10 quick suites, 524,288 late checks and 33,554,432 full score/depth decisions exact in reference-comparison build. 1,301 protected files unchanged. No production changes, commits, pushes or new goal.

## 9 October: primary movement-state redesign

/puffertank/experiments/nethack-compact-state-20261008/primary_movement_20261009/REPORT.md

parked; no robust incremental gain across both workloads. 512 envs -7.15%, 2048 envs -3.15%. 33,554,432 full score/depth decisions exact. Primary grid replaced, separate type plane removed, local entity-summary writers, no shadow facts grid or query rebuild. No production edits, commits or pushes.

## 9 October: primary movement-state redesign

/puffertank/experiments/nethack-compact-state-20261008/primary_movement_direct_20261009/REPORT.md

parked; no demonstrated material incremental gain. 512 envs +0.06%, 2048 envs +0.61%. 33,554,432 full score/depth decisions exact. Primary grid replaced, separate type plane removed, local entity-summary writers, no shadow facts grid or query rebuild. No production edits, commits or pushes.

## 9 October: primary movement cost decomposition

/puffertank/experiments/nethack-compact-state-20261008/primary_movement_costs_20261009/REPORT.md

Unchanged native A-B-B-A profiles:2048 query17.64->14.99us, othermovement39.83->42.90us, rest73.92->72.61us; total131.39->130.49us. Main offset m_move own PCs. Direct sparse upkeep measurement in report; too small to account for3us offset.512 similar direction but weaker intervals. No hardware-cause attribution. 1048576 immutable hashes exact, no live/retained edits.

## 9 October: improved query on original flat terrain

/puffertank/experiments/nethack-compact-state-20261008/flat_query_20261009/REPORT.md

small native gain, but surrounding movement offset persists; isolated, not promoted. 512 envs +1.79%, 2048 envs +1.16%. 33,554,432 score/depth decisions exact. Old six-byte flat terrain/type plane restored; two-byte summaries maintained locally. No live changes.

## 9 October: object presence at the post-movement check

/puffertank/experiments/nethack-compact-state-20261008/object_presence_20261009/REPORT.md

512 envs +0.89%, 2048 envs +0.84% versus previous flat query. 33,554,432 score/depth decisions exact. isolated experiment complete; not promoted to the live engine.
