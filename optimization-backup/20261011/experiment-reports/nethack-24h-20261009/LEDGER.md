# NetHack 24-hour optimization ledger

Start: 2026-10-09T22:30:39+00:00
Deadline: 2026-10-10T22:30:39+00:00

Fixed baseline: `binaries/baseline`, SHA256 71886d32acb4bfbccc9dca3f978bafb0e62fc7d6b38744749209748b1bb8b8c5. Prior matched mature measurement: 193,181 SPS. Target: 277,778 SPS.

## Experiments

1. Refresh inference and training profile on the current retained stack. Status: preparing a short mature Nsight node capture. No candidate changes yet.

2. Projection+bias+ReLU cuBLASLt fusion. Evidence: 32,768 separate bias/ReLU kernels in 2,048 inference calls; 8.2% of summed inference kernel time. Prototype has inference-only/training-only/both switches. Build v2 and 4-batch smoke passed; first three engine boundaries match baseline and frozen checkpoint is unchanged. Floating-point rounding changes are expected because the intermediate GEMM output no longer rounds before bias addition. GPU screen running.

Projection fusion GPU screen: control 1150.031 ms, training fusion 1149.708 ms (+0.028% throughput). Training-only variant is neutral and will not get further checks. Inference-only full-pipeline screen is running with fresh bracketed controls.

3. Recurrent-scan mapping: current T=128,H=1024,B=32 uses the generic scan; source already contains a tiled implementation but its default gate requires T>=256 for this width. Fresh trace records 184.8 ms forward and 250.5 ms backward summed kernel time over four batches. Hypothesis: test tiled gate precomputation and layout at T=128, keeping the exact recurrence. Host-only force bits (1=forward, 2=backward) prepared. Build deferred until current timing jobs finish.

Projection fusion inference screen: bracketed controls 194525.8 SPS; inference fusion 194860.5 SPS (+0.172%). This is within control spread, so rejected as neutral. All 80 engine boundary hashes and frozen checkpoint agree. No further training validation.

Recurrent scan first screen: controls 1152.801ms; forward tiled 1142.214ms, backward tiled 1148.682ms, both 1139.758ms (+1.14% GPU throughput). Next screen tests time tiles 4/8/16 (32 hidden lanes), plus generic blocks 64/128, on the same saved mature batch. A prototype edit left duplicate else blocks; compile caught this, v5 fixed it before any execution.

Encoder-only harness: 512 saved mature observations, encoder graph only, 256 repeats/trial. Baseline 213.816us, fusion 183.414us; output finite, relative L2 difference 0.003846. Despite isolated improvement, full pipeline remains neutral.

Recurrent scan layout screen (4 measured GPU graphs per case):
- scan_layout_base_a: 1150.449ms (+0.15% vs bracketed controls).
- scan_layout_tile4: 1117.573ms (+3.09% vs bracketed controls).
- scan_layout_tile8: 1123.103ms (+2.59% vs bracketed controls).
- scan_layout_tile16: 1120.796ms (+2.80% vs bracketed controls).
- scan_layout_block64: 1152.257ms (-0.01% vs bracketed controls).
- scan_layout_block128: 1153.687ms (-0.13% vs bracketed controls).
- scan_layout_base_b: 1153.835ms (-0.15% vs bracketed controls).
Tile4 advanced to full-pipeline bracketed screen; other layouts parked. No fusion enabled.

4. Out-of-place Muon: existing prototype was rejected for non-exact floating point on an older stack; it has not been screened on the current parallel-Muon stack. The goal now explicitly permits rounding differences. Add runtime flag PUF_OUTPLACE (requires build define PUF_MUON_OUTPLACE) and preserve original code when disabled. This removes two explicit D2D copies per Newton-Schulz iteration/matrix without changing the equations. Prepared, not built or tested yet.

5. Bias-gradient reduction grid: current profile reports 172ms/4 batches in nh_relu_bias_bwd_kernel. It caps at 1024 CTAs and uses shared then global fixed-point accumulation. Test smaller caps for less reduction/atomic overhead; floating-point summation grouping changes, so quantify only if timing wins. NH_COLSUM_BLOCKS switch prepared; default remains1024.

Full-inference microbench prepared: same saved mature observations and initial recurrent state, restore state inside every graph. Measures encoder+recurrent+decoder, excludes sampler/environment. Source not yet built.

Scan tile4 full pipeline: controls 193623.7 SPS, candidate 193907.6 (+0.147%). Neutral within control spread despite +3.1% isolated GPU. Candidate rollout-tail wait 116.1ms replaces saved GPU time. All engine boundary and frozen checkpoint hashes match. Parked; no further update/learning checks.

6. Revisit preferred-buffer recheck scheduling, with a new critical-path hypothesis: the earlier test gained 9.54% native CPU at2048 but was hidden under old185kSPS GPU training (zero rollout tail). Current parallel Muon exposes86ms rollout tail. The same already-validated scheduling variant may now shorten that tail. Ported only isolated env_pool.h; worker/buffer/env counts unchanged, default disabled. PUF_BUFFER_FOCUS enables it. Requires fresh full-pipeline screen; previous512CPU regression remains a known limitation.

Outplace/column screen completed:
- outcols_base_a: 1153.545ms (+0.014% GPU).
- outcols_outplace: 1130.499ms (+2.053% GPU).
- outcols_cols128: 1192.098ms (-3.221% GPU).
- outcols_cols256: 1161.298ms (-0.654% GPU).
- outcols_cols512: 1149.786ms (+0.341% GPU).
- outcols_base_b: 1153.866ms (-0.014% GPU).
Column caps rejected (128/256 slower;512 +0.34%, too small). Out-of-place Muon advances to full pipeline. Full inference harness smoke completed:398.087us including recurrent-state restoration and excluding sampler.

7. Recurrent inference GEMM: top inference kernel family consumes321.6ms/4 profiled batches (4calls per inference,M512,N3072,K1024). Prepare shape-specific cuBLASLt algorithm-index screen, sameBF16 operands/output and FP32 accumulation,4MiB workspace and FP32 split-K reduction. Full-inference harness permits second-scale screens. Source prepared, not built.

8. CUDA host waiting: observed main thread at101%CPU and four rollout submitters around100% each; pool workers around83%. Installed CUDA13.0.2 runtime documentation says default Auto spins when active contexts <= logical CPUs. New optional PUF_CUDA_WAIT=block/yield changes only context waiting policy, preserving other device flags. Hypothesis: reduce competition with CPU simulation. No speed claim; source prepared, not built.

OVERLAP2 full screen: controls193409.5SPS; outplace194901.0(+0.771%), memory8840.1->8284.1MiB, tail105.2ms. Small positive, needs reverse-order repeat. Focus191292.7(-1.094%), parked. All80observation boundaries and frozen actors match. Focus lowers mean environment-stage time (~1.08s->0.82s) yet hurts total; per-buffer completion instrumentation prepared to distinguish average improvement from tail imbalance.

Recurrent inference algorithm screen: five eligible algorithms at4MiB. Full-inference microbench controls398.136/397.088us. Algorithms0..4:397.564,443.645,399.028,399.852,430.001us. No win; no further checks on these algorithms. Larger-workspace screen would be a separate hypothesis.

9. Larger inference-only workspace: the4MiB recurrent-GEMM heuristic offers only five candidates and none helped. Prepare NH_REC_WS_MIB (4default,32candidate) to permit larger-workspace algorithms only in rec_lt_try; ordinary cuBLAS still receives4MiB. Extra memory is allocated per stream and must be reported. Not built/tested.

10. Symmetric Gram-square mapping: Muon computes G=X^T X or X X^T, then G G. In exact arithmetic G is symmetric, so G G^T has the same result and may select a faster matrix kernel. PUF_MUON_SYMMETRY switches only that multiply to the transposed-right path. It can change floating point because computed G may not be bitwise symmetric; not an exactness claim. Same five coefficients/steps, precision, clipping and momentum. Must measure timing first and quantify numerical stability only if promising. Separate from outplace (outplace takes precedence). Prepared, not built.

WAIT_SCREEN complete: controls194815/194647SPS; block199376(+2.385%), yield194792(neutral). All engine proofs and frozen actors match. Block environment-stage duration~1030ms versus1070ms; model/copy times stable. Outplace repeat193713SPS is slightly slower; not retained for throughput. It still saves556MiB but that is not a training speed gain.

Fixed-priority buffer diagnostic confirms imbalance: buffer completion means863/974/1156/1377ms versus1336–1340ms controls. Fair scheduling now prepared (sort ready regions by submitted generation, retain existing leases/counters/work stealing). Synthetic lifecycle/count smoke passes102800 callbacks for baseline, fixed priority and fair, including non-divisible257-game regions and7workers. No timed fair test yet.

Blocking-wait numerical gate:113real PPO updates on the same saved mature rollout are byte-identical to immutable baseline: master weights, momentum, update buffer, BF16parameters, first/last raw gradient snapshots. This validates actual updates, not only frozen actor checks. State hashes in runs/wait_proof_{base,block}/result.json.

Symmetric Gram-square mapping failed the GPU timing screen: 1157.177ms vs1152.959ms bracketed controls. Reject; no further numerical checks. Larger32MiB inference workspace still exposes only5heuristic candidates, first401.698us vs~398us baseline. Same candidate count does not prove the algorithm identities match; remaining larger-workspace search parked, not exhaustively rejected.

Goal continuation: previous turn only supplied a prompt (no progress). Revalidated objective, idle GPU and no live benchmark; launched WAIT_CONFIRM_FAIR.json at23:28UTC. Blocking repeat CPU sample: main10.3% ofonecore, submitters~79%, poolworkers~86.8%. Matching fresh baseline CPU sample pending.

11. Pool tail sleeping: fresh baseline trace has mean0.376ms in each pool.tail_wait (vs8.82ms total env stage), currently sched_yield-spinning on the submitter. Prototype PUF_POOL_SLEEP waits on the existing region condition; the last completed task signals it, and completion/readers predicates retain acquire/release and mutex protection. Expect a modest ceiling, not a2xfix. Basic callback/lifecycle smoke and full timing required. Prepared, compilation deferred during active timings.

12. Exhausted-claim read check: each of24workers plus submitters scans24victim counters per ready region, always incrementing exhausted counters. Optional PUF_POOL_CHECK_CLAIM first performs a relaxed load and skips atomic RMW once exhausted. Counters are monotonic within a reader-leased generation, so no jobs are skipped; no cross-generation access allowed. Hypothesis is lower coherence traffic in scheduler housekeeping; not a measured cache claim. Prepared, not yet tested.

Clean blocking-wait candidate prepared separately in clean_wait/source from the exact original source (matching baseline binary hash). Only six lines added in pufferl.cu; not built yet.

Blocking reverse-order repeat: 199142.0 vs194059.6SPS (+2.619%). All80observation boundary proofs match. MainCPU10.3% vs100.0%, submitters~79% vs100% over12-second samples; exact workload windows were not aligned, so treat this as scheduling evidence rather than a CPU-work reduction estimate. Fair full smoke first3boundaries match.

13. Embedding backward reductions: the fresh node profile reports~183us identity-table gradients,167us glyph-kind gradients,236us local-class scatter per PPO update. Identity runs only288output threads, each serially scanning4096samples; kind similarly has few threads and long CSR-row sums. Prepare oneCTA/output with a deterministic FP32 tree reduction (rounding differs, no precision/equation change). Local scatter sends every nonzero input to oneof72global64-bit counters; prepare shared fixed-point partials and flush eachblock, converting each contribution before reduction to preserve original integer sums. NH_EMBED_REDUCE bits1/2/4 isolate these. Prepared only; build deferred until the active campaign ends.

Fair scheduler full screen:194226SPS vs194616bracketed controls (-0.20%), all80observation proofs match. Buffer finish times~1340–1346ms, so imbalance is gone but there is no throughputgain. Reject this generation-sort scheduler.

Secondary depth test: 376960.2 vs375134.0SPS (+0.487%), control drift-0.414%. Treat as near-neutral/smallpositive; all80depth observation proofs match and frozencheckpointunchanged. Score gain is not a universal2.5% claim.

Embedding timing screen (4 measured GPU PPO graphs each):
- embed_gpu_base_a: 1151.908ms (+0.095% GPU throughput).
- embed_gpu_identity: 1136.772ms (+1.428% GPU throughput).
- embed_gpu_kind: 1137.435ms (+1.369% GPU throughput).
- embed_gpu_local: 1130.668ms (+1.975% GPU throughput).
- embed_gpu_all: 1096.615ms (+5.142% GPU throughput).
- embed_gpu_base_b: 1154.098ms (-0.095% GPU throughput).
Allthree improve isolatedtraining and combined advances to full pipeline. Clean six-line waitcandidate passes byte-exact113updateproof. Pool sleep/claim variants pass32synthetic count/lifecycle cases (0/1/7/257envs perregion), plus first3live replayboundary checks.

Embedding basic update check: allstatefinite; first PPO minibatch gradient is byte-exact. The stored raw-gradient pair is FIRST AND LAST of113updates (correcting earlier first-two wording). After113updates, combined parallel reductions differ: master relativeL2=3.89e-5, BF16params2.49e-4, momentum0.1315 and last-gradient0.2858. These are not an exact-update candidate; further stability/first-divergence work is required only if full timing is useful. The local fixed-point reduction is expected exact independently; separate check pending.

Live-update validation first baseline aborted in the benchmark's duplicate-replay assertion. PUF_LIVE_AFTER_WARM stopped overriding actions but left PUF_ACTION_REPLAY set, so the harness incorrectly required independent sampled trajectories to remain identical across duplicatedgames. No candidate was involved. Runner now removes replay input explicitly for live validation; final full rollout-state hashes remain available, and all recorded-action benchmark settings/checks are unchanged. Failed artifact retained as clean_live_base. Retry uses _v2 labels.

Clean blocking-wait live validation:8batches,2097152sampled environmentsteps,904PPOupdates. Final full rollout-state hashes match=True; master/momentum/update buffers match=True; finalcheckpoint match=True. These are actual sampled actions and applied updates, separate from frozen timing.

RETAIN v1: clean blocking-wait patch. Full score 200502.9 vs194195.6bracketed controls (+3.248%),80exact observation boundaries,113savedbatchupdates and904liveupdates/2097152sampledsteps allbyte-identical. MatureCPUmain12.0% vs99.4% (matchedepochs64–78); aggregateprocessCPU2708% vs2833%, without treating this as a pureworkreduction. Prototype depth+0.49%, nearcontrolspread. RETAINED.json identifies isolated binary/source/flag. Productionunchanged.

Native2048pool screen complete in88seconds (36sec one-time preparation;8restored512-decision trials). Same currentPGOengine and identical nethack.h as the fullpipeline. Allendpoints/worldturn totals match.
- baseline: 223778.9SPS (+0.000%), repeat range0.037%.
- sleep_tail: 223807.1SPS (+0.013%), repeat range0.229%.
- check_claim: 223697.0SPS (-0.037%), repeat range0.025%.
- both: 223926.8SPS (+0.066%), repeat range0.010%.
Allvariantsneutral; reject tail sleeping and exhausted-claim reads for throughput. No longer CPUproofs/fulltraining checks for these losers.

Local-class shared fixed-point scatter alone passes byte-exact113real PPO update comparison (allweights/momentum/updates/rawfirst-lastgradients). Rounding drift in the combined embedding arm comes from the two FP32 tree reductions, not this integer scatter. Fullcombinedthroughput screen running.

14. Identity embedding forward: profile~17.94us/inference. Original launches only512threads (2CTAs), each serially decodes identity and writes40features with a sample-strided warp access pattern. Prepared NH_IDENTITY_WARP: one warp/sample, lane0 retains identical decoding and broadcasts indices; lanes write feature dimensions contiguously. No arithmetic reduction or model change, expected byte-exact. Separate runtime flag, not built/tested; current v10 performance measurements unaffected.

15. Prepared scheduling recheck after cheaper GPU training: preserve4logical512-game inference buffers,2048games,horizon128 and all training hyperparameters, but service two buffers at once in8-step or128-step cohorts. This existing mechanism preserves GEMM shapes and changes only scheduling. New hypothesis versus older tests: the current four-stream optimizer and embedding reductions expose a rollout tail, whereas old training often hid it. Smaller simultaneously active game working sets may now trade extra GPU scheduling gaps for lower CPU cost. Test both without/with embedding reductions to detect the crossover, using full frozen replay and freshcontrols. Not launched; COHORT_RECHECK.json prepared.

Embedding full comparison: combined199493.3SPS vs199373.3bracketed blocking-wait controls (+0.060%). Despite GPU+5.14%, fulltrainingisneutral. All80observation checks agree and actorfrozen. Park standalone; do not spend further numerical-training checks unless a changed scheduler makes it a useful combinedwinner.

Identity warp inference: 0.396978550→0.388103969ms (+2.287%).

Identity warp time: 1150.501248000→1149.827584000ms (+0.059%).
Fullinferenceoutput760832bytes is exact. Training GPUneutral; onefullinference timinggate pending. COHORT_RECHECK2.json usesv11 for allcases and includes the identity-only case as a separatearm.

Clean wait early window(epochs3–14):207312vs207575SPS (-0.126%, neutral), versus mature+3.248%. This supports a late-workload benefit rather than a universaltraininggain. Cohort8/128 shortsmokes bothmatch first3observationboundaries and frozenactors.

Cohort source audit: rollout_start(PuffeRL*,slot) copies actor_param and synchronizes before releasingany ofthe4buffers. Cohortgates run afterwards; they cannot read later trainingweights mid-rollout. Any timingwinner stillrequires liveupdatecomparison. All16protectedfiles unchanged at~94minutes.

Goal continuation: preceding prompt-only reply made no experimental progress. Re-read objective and verified campaign PID2896611 and benchmark2896874 live. Identity full result is neutral so far; cohort128 slower. Thread-local initial-exec is already enabled in the current engine, so no TLS candidate is warranted.

16. CPU placement: native replay uses explicit24worker placement, but full pipeline currently lets all workers/submitters migrate. On this8P+16E host, prepare PUF_CPU_AFFINITY=1 to pin24workers to8P+16E, four submitters to P siblings1/3/5/7 and main to9. Mode2 pins main+submitters only. Hypothesis: more predictable CPU/GPU submission and game working-set residency, without fixed game ownership or changing parallelism. Configuration-specific scheduling experiment; no gain claim. Same2048envs/24workers/4buffers. Assertions check CPU availability; isolated source only. Do not compile until active timings finish.

17. Bounded buffer lead: fixed-priority rescan gained nativeCPU but caused a slow last buffer; generation-fair scheduling removed that imbalance but was neutral. Prepare bounded priority (PUF_BUFFER_LEAD=1/2/4/8): prefer low-numbered ready buffers while their generations are within a small lead of the slowest, then prioritize laggards. No cohort barrier and allbuffers remain runnable. Hypothesis is preserving useful locality without unlimited head-start/straggler cost. Reader leases/claim counters unchanged. Prepared native snapshot variants and48case callback smoke; not compiled or measured.

18. Sampled rollout timing: current loop records model-start/model-end/copy-end/upload-start/upload-end events and queries elapsed times every step, even in already-captured inference. Existing profile shows substantial CPU submission duration (observer-affected, not a speed estimate). Prepare PUF_TIMING_STRIDE=16: sample1/16steps, rotate phase each horizon, scale model/copy diagnostics; environment and outer-batch clocks remain exact/every-step. Same graphs/actions/syncs/computation. This changes profiling estimates, explicitly separate from simulation/model speed. Not built/tested.

COHORT_RECHECK2 finished. Freshblockingcontrols mean 199449.0SPS; identity_full 199481.9SPS (+0.017%); cohort_two128 189441.9SPS (-5.017%); cohort_two8 180375.6SPS (-9.563%); cohort_two128_reduce 193616.2SPS (-2.924%); cohort_two8_reduce 182036.5SPS (-8.730%). Alltiming arms completed; reject cohort scheduling and parkidentityforward as fullpipeline neutral. No further update checks for these timing losers.
Affinity/bounded-priority/sampled-timing candidatev12 built.48synthetic lifecycle/count cases pass; combined4epoch replay smoke completes. Native bounded-priority screen nowrunning serially before affinitycampaign. Initial timing-preparation script assertion failed before writing any source (it expected unscaledcopy counters, which were already scaled); corrected preparation, no benchmark affected.

Native lead2048_screen failed before its first timing trial: new ep_pin_cpu checked the inherited pthread affinity, but snapshot workers intentionally inherit a narrow parent mask before widening to their established CPU_PIN target. This was an overstrict harness assertion, not an engine mismatch. Native-only helper now relies on pthread_setaffinity_np success, matching prior CPU_PIN semantics. Failed artifact retained; fresh unique retry label lead2048_screen_v2. Fulltrainer helper is unchanged and shortsmoke passed.

19. Batched pool completion publication: source currently performs one release RMW on the same region.done cacheline for every game (512updates/buffer), adjacent to region metadata. Only the final completion count is consumed. Prepare PUF_POOL_DONE_BATCH to publish each ep_claim callback total once after its work, preserving reader leases, release/acquire semantics and optional final condition signal. Suspected ceiling modest (outside-step CPU budget ~2%); possible coherence effects must be measured, not assumed. No game scheduling change within a claim. Prepared64case lifecycle/count smoke and CPU-only snapshot modes10=batch,11=batch+sleep,12=batch+lead4. Not built or timed; no active timing contaminated.

20. Explicit cuBLAS workspace capacity: retained handles own4MiB each. The existing test of32MiB applied only to one recurrent-inference Lt GEMM, not fulltraining/parallelMuon. Prepare PUF_CUBLAS_WS_MIB=8/16/32/64 to test heuristic access to larger scratch space across regular GEMMs while retaining stream ownership, operands, compute type and math mode. ExtraVRAM and numerical differences must be reported for anywinner; no implicit allocator or workspace sharing. Cheap saved-batch GPU timing gate first. Not built/tested; no existing binary modified.

Native bounded-generation priority screen completed: controls223537.1SPS; leads1/2/4/8 gain+0.093%/-0.028%/-0.038%/+0.239%. Allendpoints/worldturns match. Reject as neutral without fulltraining/longerproof. This differs from the older productive-scan quotas (focus_quota_20261009), which are also parked; neither supplies a universal locality fix. COHORT_VALIDATION.json confirms all80boundaries and frozenactors identical across sevenfullruns. Protected16files remain unchanged (integrity_116min.json).

Goal continuation: prior turn made progress (seven fullcomparisons, nativebounded-priorityscreen, candidateimplementations). Rereadobjective and verified sampled-timing benchmarkPID2899385 live.

21. Conservative floor-query block bounds prepared as scripts only: census823 eight-itemcoordinateblocks/decision and211cursorcalls gives a concrete repeated-search target. Build a rectangle for each32consecutive floor-list entries on existingindexrebuild, then reject a wholeblock only if disjoint from the query; leave order, eligibility, RNGcalls and mutationfallback unchanged. Adds512B of per-game accelerationmetadata. Hypothesis: fewercoordinatearrayloads/comparisons on spatiallyclusteredfloorlists; cost includesboundsmaintenance andfailedfilterchecks. Separateordinary-LTO control/candidate,582201-query scalar-reference propertysmoke before a2048CPU timing screen. No sourcecopy/build/run yet; scripts prepare_floor_boxes.py/floor_boxes_screen.py must wait for active timings. Fullgolden/fuzz/PGO/corpus gates onlyifnative timing is useful.

AFFINITY_SCREEN finished: controls199347.1/200551.4SPS(mean199949.3),drift+0.604%. affinity_all +0.051%; affinity_submit -0.483%; affinity_all_reduce -0.017%; timing_stride16 +0.396%. All80boundaryproofs andactorsmatch. Parkall: no reliable end-to-end gain, including sampledprofiling belowcontroldrift. No expensiveupdatechecks. v13 and nativecompletion built;64syntheticcallback/lifecyclecasespass. Nativecompletion screen inprogress, followedby explicitworkspacecapacity GPU screen.

Nativecompletion screen finished: controls223709.2SPS; batchdone−0.065%,batch+sleep+0.124%,batch+lead4+0.138%. Endpoints/worldturnsmatch; allneutral, rejectwithoutfulltraining/longproof. This supports gamework ratherthancompletioncountertraffic as the currentCPUtarget. Floorboxscreen predeclares an initial+0.8% threshold to warrant freshreversecontrols; loser/neutralfirstpair stops withoutprolongedchecks.

Explicitworkspacecapacity GPU screen: bracketedcontrol1152.477ms; ws8 -0.039%; ws16 +0.198%; ws32 -0.349%; ws64 -0.216%. Allneutral/slower. Reject largerworkspace, no fulltraining/numerical escalation. Private4MiB baseline retained.

Floor-block-bounds candidate completed: scalar reference582201queries matches on bothbuilds; native2048 control214560.3 vs candidate215095.4SPS (+0.249%). Below0.8% firstpair gate: park, no reversecontrols/fulltraining/longgolden checks. Ordinary-LTO screen only.

22. Combined GPU hypothesis: scan tile4, embedding reductions, identity-warp inference and inference epilogue fusion each cut isolated GPU costs but individual fullpipeline screens were neutral. Test combined cuts, then add out-of-place Muon, because shared GPU contention may change the overlap boundary nonadditively. Fixed training shape/hypers; existing smoke gates apply, rounding changes explicitly allowed. New GPU/full measurements required; no gain assumed.

Combined GPU screen: baseline1148.911ms, combined1038.662ms (+10.6% GPU throughput), plusoutplace1014.858ms (+13.2%). Advance both to4batch smoke then fullpipeline bracketed comparisons; no end-to-end gain claim yet.

23. Register-prefetched recurrent scan: measured generic scan~102us forward/~139us backward in traced training; current row-tile precomputation gains3.1% GPU but pays shared-memory/barrier costs. Prepare perthread2/4/8step gate preloads followed by original ordered recurrence. Retains BF16 recurrent rounding, terminalreset semantics and FP32 backward carry; no extraactivationbuffer. Independent54case smoke compares oddtails/full128steps and absent/random/allreset masks. Sourceprepared, build/test deferred during fullpipeline timings.

24. Broader current-workload PGO recipe prepared (not run): retained engine feedback uses8historical score+8depth recordings. Reprofile identical source using512current score streams before decision8192, plus originalhistoricalinputs, then time subsequentmaturedecisions. Hypothesis is compiler branch/layout tuning onbroader representativework, not a source/behavior change. Matchedflags, hashallinputs, propertysmoke, native2048 firstpairgate0.8%; no longfullchecksforlosers. Compiler training shares games with native screen but uses precedingstates, so anywinner needs independentworkload confirmation.

Combined fullpipeline final: controls199574.9SPS,drift−0.088%; combined200778.9(+0.603%),plusoutplace200839.6(+0.634%). Rollouttail41.1→148.7/175.7ms. All80observationboundaries andactors match. Small signal below1% normalfullgate, notretained; no expensiveupdatechecks. IsolatedGPUgain10.6–13.2% mostlyhidden.

Registerscan firstsmoke failed a forward-bitwiseassertion; failedtest/source/logs retained. Extended54case diagnostics:300/76884561forward and987/153467739backward values differ; worstrelativeL2 forward1.079e-5,backward3.750e-6; allfinite. Recompile BOTH versions with--fmad=false yields0differences acrosssame230Mvalues, isolating compilercontraction sensitivity. Numericalrounding allowedbygoal; trainingbench retainsnormalflags, no silentprecision/equationchange. Advance toGPUtiming, no retainedcorrectnessclaim.

Register-prefetch scan GPU screen complete: control1152.643ms; regs_gpu_base_a +0.162%; regs_gpu_tile2 -0.499%; regs_gpu_tile4 -0.694%; regs_gpu_tile8 -1.462%; regs_gpu_forward -0.686%; regs_gpu_backward -0.150%; regs_gpu_row4 +2.987%; regs_gpu_base_b -0.161%. Reject allnewregistervariants, no fullpipeline orlongupdatechecks. Existingsharedrowtile4 remainsfaster. Compilercontractiondiagnosticstaughtcorrectnessscope but suppliedno speedup.

25. Buffer-count configuration experiment prepared, notrun: keep2048envs,horizon128,mb4096,113updates,24poolworkers,model andrecordedgames fixed; compare4x512 to8x256 inferencebuffers, optionally withcombined GPU cuts. More independently ready smallerbuffers might reduceCPUidle/stragglers; costs moreGPUlaunches/submitthreads. Existingharness seed/action/hash mapping already uses4fixedteacher groups independently ofbuffer count, so8/16 fit without remapping. run.py explicit--buffers onlyforfrozen scorefulltests, recordedas configurationexperiment; noheadline implementationgainclaim. Sourcebinary unchanged. Smoke8/16 then8full pluscombo ifsafe. Do not launch during PGO work.

PGO512collection deliberately stopped after~5min (verifiedPID2908885 terminated/relisted,driverterminal). Shared atomiccompilerfeedback has high overhead; no gamefailure or timingscore inferred. Debuggerattach unavailable, not bypassed. Generatedlibrary/source preserved, no enginegcda written byabortedpass. Newprofileonlycollector allows64games (first16fromeachoriginalteacherbuffer),4directsubmitters/no pool, emitsprogress every1024decisions. Nativeperformanceharness unchanged. Session80264 resumes remainingrecipe.

Buffer experiment history check: older opt61/5.1M study found16x128ungated−6.4%, grouped4active+28.1%;15.55M livepilot+8.6% haddivergent games. Currentgoal onlyretested same4x512layout cohorts andlost. Add16x128grouped4, with/withoutcombined GPUcuts, to newmatched15.55M/retainedengine screen. This is an explicitpartition/configuration recheck, notclaimednewimplementation or bitwiseold-policybehavior.

BroadercompilerPGO native2048 screen: unchangedsource, propertypassed, endpointsidentical; control223534.9 vs224377.8SPS (+0.377%). Parkbelow0.8% firstpairgate, no longproof/fullpipeline tests. Newprofilerused64currentgames plusoriginal16historicalinputs; initial512passwasstoppedforcost, notincluded.

Buffer8smoke run itselfcompletedrc0,frozenactor,first3boundariesexact. Driverinitiallycomparedthe4batchfinalboundary againstan80batchreference:finalbatch hasno nextprefetch, soitsobs repeatspriorbatch, as doesexisting4buffersmoke. Corrected driver tocompare equal-length4batchreference forsmokes,80batchforfullcases. Failedharnessassertionretained; reusecompletedsmokeartefact, no rerunor weakened trajectoryexpectation.

## 2026-10-10 01:12 UTC — buffer partition screen and fused Muon preparation

Previous turn answered a user request for the next goal prompt; it did not advance the active optimization goal. Revalidated the existing buffer driver as live and resumed experiment work. Preliminary full results: 4-buffer control 199,163 SPS; 8-buffer 202,310; 8-buffer plus combined GPU changes 203,477; grouped 16-buffer 183,321. Closing control and final grouped-combination result remain outstanding. These are configuration experiments, not additions to the retained implementation speedup.

Prepared `muon_fused_smoke.py` to compare the full five-iteration BF16 small-matrix update with the existing cuBLAS equations across production shapes plus tall, wide, odd, zero and rank-one inputs. The 5% relative-L2 smoke gate detects layout/scale failures; it is not a claim of identical updates. Kernel precision differences will be quantified. No compilation during active timings. Prepared `MUON_FUSED_GPU.json` for a bracketed GPU graph timing screen after basic validation.

## 2026-10-10 01:16 UTC — buffer screen closed; fused Muon timing

Buffer controls average 199364.4 SPS, drift +0.203%. Eight buffers +1.478%; eight plus GPU combination +2.063%. Both sixteen-buffer grouped arms are slower by about 8%. All 80 observation boundaries match, frozen actors unchanged, 113 updates and minibatch/batch sizes unchanged. Configuration-only results; confirmation pending. Details: BUFFER_SUMMARY.json.

Fused Muon smoke: 66 cases, 58,635 values, 22,845 different BF16 values; max relative-L2 difference 0.0459814, max absolute 0.0332031. Passed broad finite/layout/scale gate, NOT bitwise equivalence. Built immutable muon_fused_v15; bracketed GPU screen running. Further numerical analysis only if timing warrants it.

## Next CPU capacity screen prepared (not launched)

Blocking CUDA waits changes competition for CPU time, but the inherited 24-worker choice has not been re-screened in this goal. Hypothesis: modestly more workers can hide memory latency / use spare SMT capacity, or fewer workers can reduce scheduling/coherence overhead. Added optional worker count and unpinned mode to the isolated native snapshot harness; defaults remain 24/pinned and syntax passes. Prepared worker_count_screen.py: 24-control,20,28,32,24-control, two identical restored 512-decision trials each, all unpinned to match full-pipeline scheduling. No training/environment-count/horizon changes. Cross-configuration terminal observations/turns/age must match. Run only after GPU timing campaigns finish; follow up only a repeatable useful native signal.

## 2026-10-10 01:23 UTC — fused Muon closed; confirmation running

Fused <=64 matrices: isolated graph 1156.050 -> 1127.984 ms (+2.488% throughput). Full mature controls 199189.523 / 199237.021 SPS (mean199213.272), candidate199369.968 (+0.0787%). Rollout tail grows from about42.38ms to69.08ms, replacing almost all28.07ms isolated GPU savings. Peak reported allocation8840.1 -> 7872.1MiB (968MiB lower). All80observationboundaryproofs/actors match,113updates maintained. Park for throughput; no long numerical/training tests.

Buffer confirmation started in session67743, four full runs in reversed candidate order with fresh controls. Native worker-count screen queued behind its completed validated summary in session40492; no concurrent timing.

## 2026-10-10 01:28 UTC — next engine candidate: immutable object metadata reads

Prior full-gap profile identifies the per-game object-type allocation as a recurring data-read cost. Source audit finds no direct field writes for selected immutable properties (class, weights, cost, damage, skills, armor values, flags, nutrition, delay, property). Prepared IMMUTABLE_OBJECT_READS.patch and .json: 287 direct reads across56files (including shared header accessor), redirected to existing objects_baseline while utilities retain objects. This may reduce private working-set reads and allow constant folding; no speed claim. It deliberately leaves dynamic appearance/material/color/toughness, discoveries/names, probabilities, and oc_dir untouched: WAN_NOTHING.oc_dir is randomized. First preparation stopped on legacy nonUTF8 file; losslessLatin1 retry succeeded, no source files modified. Alias accesses and nested-index expressions remain unchanged. Must check whole-table initialization/save/restore invariants and replay before retention. Candidate not applied/built/timed yet.

## 2026-10-10 01:34 UTC — repeated buffers and worker capacity

Eight-buffer confirmation: +1.210% alone, +2.047% with GPU combination; first screen +1.478% / +2.063%. Controls drift -0.318% in confirmation. All80observationboundaries/actor hashes match,113updates maintained. CONFIG_CANDIDATES.json records these separately; no default promotion or numerical/live-training equivalence claim.

Native worker-count controls average221620.645 SPS, drift+0.3425%. Twenty workers216281.585 (-2.409%);28workers226395.370 (+2.154%);32workers231013.145 (+4.238%). Two restored512-decision trials each, same2048games, all unpinned, all cross-case observations/turns/age match. This is CPU-only, not full training. Worker full campaign now running session8053:24control,28,32,24control, fixed4buffers and sameGPUstack. No CPU/native/profile/build work overlaps it.

## 2026-10-10 01:42 — worker configuration full screen
Previous prompt-only turn made no experimental progress; resumed from authoritative completed benchmark. WORKER_FULL_SUMMARY.json: 24-worker controls 199231.59SPS;28 workers203725.00 (+2.255%);32 workers204374.67 (+2.581%). Control drift0.0365%. All80 observation proofs and frozen actor hashes equal; batch262144,mb4096,113updates unchanged. Exposed tail~43.7ms→2.56ms. Configuration result, not added to retained implementation gain. Next: fresh32-worker controls around GPUcombo with4/8buffers; hypothesis reduced exposed CPU wait allows isolatedGPU wins to become useful end-to-end.

## 2026-10-10 01:49 — 32-worker GPU combination
WORKER_COMBO_SUMMARY.json:32-worker controls mean204491.996SPS (205112.600/203871.393, drift-0.605%). GPUcombo fourbuffers205853.009SPS (+0.666%);eightbuffers207596.148 (+1.518%). Tail~2.22ms becomes137.19/109.67ms. Allocation8840.1→8256.1/8412.1MiB. All80 observation proofs and actors match,113updates unchanged. Not retained as fixed-configuration implementation win. ExtraCPUcapacity does not materially change the earlier conclusion: fasterGPU graph exposes more rollout wait. Single32-worker8buffer combo screen; live/numerical validation pending.

Immutable object-read prototype built with ordinaryGCC/LTO against reused byte-verified control source. Both standalone checks pass64seeds ×2codecs =128save/restore cycles,4,522,752fieldchecks,23,318shuffleddescriptionindices; normalizedtablehashff9c660fd292cbbf. Checks include dynamic names/discoveries. Nativepair now running; no timing claim yet. See immutable_objects/.

Immutable item fields native screen:control 214519.120SPS,candidate 215718.995SPS,+0.5593%. Allendpointobs/turns/age match. Below0.8%first-pairgate;parked immediately,nofullpipeline orlongertrainingtests.
Next prepared SHARED_NAMES.patch/.json:read staticstringnames/descriptions fromsharedtable, exceptfruit name remainsprivate. Sourceaudit found sole runtime assignment inoptions.c. Add exactname/descriptioncheckstoinvariant smoke,includingfruitoverride. Notbuilt/testedyet.

WORKER_LIVE_PROOF.json:32workers cleanblockingbinary matches24worker reference for2,097,152livepolicy steps/904actualupdates:initial/finalweights,allrollout hashes,RNN and optimizer state,observationproofs exact. Actuallearningvalidation18s;notusedforspeedclaim. Configcandidate remainsseparate fromretainedimplementation percentage.

Sharedname/description screen:control214963.525SPS,candidate214493.705SPS,-0.2186%. Passed64seeds/128roundtripswithprivatefruitoverrideandexactname/descriptionpointerchecks,4,870,656checks,andnativeendpoints. Parkedbelowgate.
Historical audit:compact-state-20261008/REPORT.md records sharedobjs andstatic_object_meta (same284immutablefields onearlier engines) already null. Current287-readscreen repeatedthismechanism onlatestsource;its+0.56%doesnotjustifyfurtherconfirmation. Addtoclosedlistacrosscampaigns;nosuchrepeatwithoutnewcausalevidence. Names/descriptionprototype isdistinct,also nowclosed. Hugepages/contextslabs,broadprefetchandgenericfieldpackingalreadytested;donotrepeat.

## 2026-10-10 01:58 — bounded code-generation and scheduling hypotheses
NATIVE_ISA.json builds unchangedengine source with-march=native -mtune=native -ffp-contract=off, nofastmath, sameGCC/LTO vsordinarycontrol. Existing branch/bit-heavy profile supports a cheapcode-generation screen; no specificspeedclaim. Smoke64seeds/128roundtrips exact, nativepairrunning.
Prepared COHORT_ONE_COMBO.json (not launched):oneactive512-gamebuffer,32workers,fullGPUcombo. Earliercohorts used2active512-gamebuffers or4active128-gamebuffers; bothslow. This closes the single512batch corner while preservingGEMMshape. Hypothesis:512gamesmayfitsharedcacheworking set and avoidfour128-sample inferenceoverheads. Existingfullinference~0.397ms/512samples andnative512vs2048gap motivate onlya boundedtest, not predicted speedup. GPUcombo isneeded because plainGPUtraining alreadycaps~205kSPS. Usefreshcombo32workercontrols andsame80obsproofs. Donotrepeatothercohortvariantsifthisfails.

NativeISA screen closed:control214173.830,candidate214302.210,+0.0599%. Runtimeinvariant andendpointchecks passed. Parked immediately; no newPGO/fuzz/fullpipeline validation spent.

## 2026-10-10 02:06 — single-active buffer closed
COHORT_ONE_COMBO_SUMMARY.json:controls206217.426/206268.655SPS,mean206243.041;candidate126748.185SPS (-38.544%). All80observationproofs/frozenactor/batch/updatecounts match. Reject;lost overlap dominates. No furthercohort/performance-loser training checks. Launch NET32_CONFIRM.json for directbaseline/block24/block32/baseline comparison using clean binaries.

## 2026-10-10 02:15 — direct combined comparison completed
Prior goal turn made progress (workerproof and3CPUscreens,cohortrejection);verifiedNET32PIDliveandcontinued. NET32_CONFIRM_SUMMARY.json recordsfreshoriginalbaseline/cleanblocking24/cleanblocking32/originalbaseline. Controlsmean194245.092SPS, drift0.4425%; blocking24199173.887,blocking32204349.219; directcombinedgain5.2017%,incrementalworkerconfiguration2.5984%. All80obsproofs/frozenactor/trainingcounts match. Mainimplementationandconfiguration keptseparate.

## 2026-10-10 02:18 — continuation audit and next candidate
Previous reply supplying a requested goal prompt was no experiment progress; revalidated actual objective, deadline, idle GPU and completed NET32 artifacts. Resume existing goal. Inventory passthrough kernels repeat equipment selection per output dimension: measured inference18.07us, PPO-forward78.97us and backward36.52us. Candidate computes integer selection metadata once per sample, retaining slot/addition/rounding order. Isolated source prepared; exact extracted-reference smoke precedes timing.

## 2026-10-10 02:21 — inventory metadata screen
PASS_FAST_SCREEN_SUMMARY.json: extracted-original smoke320cases/14,003,200forward+38,508,800backwardvalues byte-exact, includingguards/all8disablemasks/NaNflags/accessorypanelonandoff. Savedmaturefullinference outputexact; 0.395689→0.388314ms (+1.899%throughput). Full113updateGPUgraph1148.937→1141.205ms (+0.678%);forwardalone+0.647%,backwardalone+0.203%. Freshfullpipelinecontrols/candidate now test whether inference latency savings exposeanyend-to-endbenefit. No longupdateproofyet.

Pass metadata full screen: {"control_sps": 199287.21192250805, "control_drift_percent": -0.05475170348900882, "rows": [{"label": "pass_full_base_a", "sps": 199341.78343360568, "gain_percent": 0.02738334816929644, "tail_ms": 44.48927246666667}, {"label": "pass_full_both", "sps": 199743.0480361418, "gain_percent": 0.22873324847907384, "tail_ms": 50.07014266666666}, {"label": "pass_full_base_b", "sps": 199232.64041141042, "gain_percent": -0.02738334816929644, "tail_ms": 42.19967533333333}], "observation_proofs_exact": true, "frozen_actor_unchanged": true, "status": "Screen only; no full training proof"}

## 2026-10-10 02:28 — feature stores and combined inventory screen
PASS_FAST parked individually: +0.229% fulltraining;tail43.34→50.07ms absorbs mostGPUtrain savings. SFEAT_FAST_SCREEN_SUMMARY.json:96smokecases/17,332,032values acrossBF16/FP32 byteexact. Savedinference logitsbyteexact. Packedscalarfeaturestores:3.163%inference and0.877%GPUgraphgain; contiguousflatoutput2.476%inference and0.727%GPUgraph. Packedwinsboth. First directcombined test usesPASS3+SFEAT1, default24workers; do not addisolatedpercentages. No newretainedcandidate yet.

## Next bounded GPU hypothesis — alternative Muon Lt heuristics
Historical nethack-train-loop-20260918 rank1~192656 vs187261SPS was rejected underthen-strictcheckpointmatching. Currentgoal explicitlypermits equivalentrounding exploration. This rescreen usescurrent4MiBperstreamworkspaces/fourparallelMuonstreams, ratherthan theolder32MiB/serialcontext. OUTPLACE_RANK.patch onlyaddsoptionalheuristicselection; BF16operands/output,FP32compute/reduction, fiveNSiterations andequationsunchanged. Prepared24case finite/scale/layoutsmoke againstordinarycuBLAS, withCinputunchangedcheck. BuildandGPUtimingsqueuedafterinventoryfullcampaign; no speedclaimorlongupdatevalidationyet.

Combined inventory full screen: {"control_sps": 199290.8011277347, "control_drift_percent": 0.0647696984181545, "rows": [{"label": "inv_combo_full_base_a", "sps": 199226.28199672524, "gain_percent": -0.03237436481983158, "tail_ms": 43.1788286}, {"label": "inv_combo_full_both", "sps": 199321.39974025707, "gain_percent": 0.015353750574131908, "tail_ms": 67.81789466666667}, {"label": "inv_combo_full_base_b", "sps": 199355.3202587442, "gain_percent": 0.03237436481984268, "tail_ms": 41.12795193333333}], "observation_proofs_exact": true, "frozen_actor_unchanged": true, "status": "Park if below1% gate; no long training proof"}

## 2026-10-10 02:35 — inventory closed; rank1 GPU lead
INV_COMBO_FULL_SUMMARY.json: combinedPASS3/SFEAT1 +0.0154%fullSPS, tail42.15→67.82ms. Park; no longtrainingproof. OUTPLACE_RANK smoke24cases/24,414,208values finite, Cinputsunchanged;5001BF16differences,maxrelativeL2 0.00140955. GPUcontrols1155.651ms;rank0 1132.318,rank1 1086.940,rank2 1108.576,rank3 1140.597. Rank1+6.322%vsplain/+4.175%vsrank0. Fullscreenrank1aloneandcombinedGPUcutsnext,24workersfixed. Theseareexploratoryroundingvariants,notretainedupdates.

## 2026-10-10 02:45 — full rank screen closed
Previous user-requested prompt turn was no experimental progress. Revalidated objective/deadline; session68313 terminal rc0. {"control_sps": 199353.6399503789, "control_drift_percent": 0.1908448667174767, "rows": [{"label": "rank_full_base_a", "sps": 199163.59320337954, "gain_percent": -0.0953314657543669, "tail_ms": 42.426474866666666, "memory_mib": 8840.1}, {"label": "rank_full_rank1", "sps": 199810.93871016166, "gain_percent": 0.22939072489298606, "tail_ms": 115.3443336, "memory_mib": 8292.1}, {"label": "rank_full_combo", "sps": 201415.98263575058, "gain_percent": 1.0345146875095912, "tail_ms": 245.54154073333333, "memory_mib": 8264.1}, {"label": "rank_full_base_b", "sps": 199543.68669737826, "gain_percent": 0.0953314657543558, "tail_ms": 38.686355, "memory_mib": 8840.1}], "observation_proofs_exact": true, "frozen_actor_unchanged": true, "status": "Rank1 alone below gate; combined variant clears 1% first-screen gate, confirmation required"}
Fresh combined-variant confirmation prepared. No retained change yet.

## Actor L2 priority hypothesis prepared
GPU_CACHE_PROPERTIES.json: L2 72MiB,maxpersist49.5MiB;actorweights31,104,272bytes (~29.66MiB). Prototype ACTOR_CACHE.patch gives onlyactorstreams/rolloutgraph kernels a persistingwindow overactorparam,with16/32MiBsetasideandboundedhitratio. Graphnodeattribute readback verifiesapplication;noarithmetic/streamorderchanges. Defaultoff. No priorcampaignmatchfor thishypothesis. Preparationonlyduringrankconfirmtiming; buildafterGPUidle. Documentation inACTOR_CACHE_SOURCE.json.

## 2026-10-10 02:51 — rank combination confirmation and numerical audit
OUTPLACE_RANK_CONFIRM_SUMMARY.json: +1.131% fullmature gain vsfresh199474SPS controls,drift0.0755%;early240238vs~207966SPS(+15.5%). All80obsproofs/actors/countsexact. Actual113savedbatchupdates finite, but combinedfirstgradientrelativeL2=0.13398,last0.39560; masterweights0.000509,BF16params0.000989,momentum0.29573,updates0.48785. These are not tinygradientdifferences; do not retain under an equivalence claim. Six componentproofs prepared toidentifythefirst-gradientchange; no speedlosertrainingcampaign involved. Actorcachev19built;4epochsmokecampaignrunning separately.

## 2026-10-10 02:54 — experimental dispatch bug found and corrected in source
RANK_COMPONENT_PROOFS_SUMMARY.json isolates first-gradient change toNH_FUSED_BR=1 (13.38%);otherinferenceoptions exact,scan0.097%. In nethack_encoder_reg_train, training=true preceded *a={}, overwriting flag. Intended inference-onlyfusion had therefore also changedPPOforward. M4096fusedplanlogs corroborate. Swappedassignment afterzero-init in isolatedsource, TRAINING_FLAG_FIX.patch/.json. Previousfusion/combinedtimingsremainmeasurements ofboth-pathfusion, notofintended inference-only arm; no suchcandidatewasretained. Mustreruncorrectedcombination, old+1.13%notretained. Currentactorcachecampaignhasfusionoffsois unaffected. Regressiongate:mode1savedbatchupdatesmustmatchbaselineexactly. BuildafterGPUidle.

Dispatch audit additionally finds oldbr_gpu_train_a/b mode2 were no-ops (1149.35/1150.07ms), so their null does not testtraining-onlyfusion. Prepared corrected mode1savedbatchexact regression and mode2 GPU timing, plus inference-only microtiming. These require a freshbinaryaftercurrentcachetimings finish.

## Next conditional scheduling hypothesis prepared, not launched
FOCUS_FAST32.json: bounded recheck of existing PUF_BUFFER_FOCUS with32workersandcorrectedGPUcombination. Historical native2048focus+9.54% butfull185kSPSwithzerotailwasflat; currentfastGPUcombinationhas~244mstailand32workers. NewhypothesisisthatpreviouslyhiddenCPUgaincanpaywhenGPUtrainisfaster;fixedpriorityimbalancepreviouslyobservedmaystilldefeatit. Onefreshcontrol/focus/controlfullscreen, all80proofs, no newcohortbarriers orenginechanges. Explicitconfiguration32workers retainedseparately. Ifneutral/slower, parkagainwithout furtherlocalityvariants. OnlyrunafterdispatchregressionandcorrectedGPUtimings.

## 2026-10-10 03:01 — actor L2 reservation closed
ACTOR_CACHE_FULL_SUMMARY.json: controls199240.624SPS,drift−0.1424%;requested16MiB(actual18MiB)+0.0645%;requested32MiB(actual36MiB)+0.1236%. Bothbelowcontrolvariationand1%gate;park. All80obsproofs/actors/countsexact;4buffergraphs82kernelseachhadaccesspropertiesreadbackchecked. No longtrainingchecksforloser. Earlywindow32MiB~1%slower. No evidenceofusefulfullpipelinegainfromthiscachepolicy.

## 2026-10-10 03:03 — dispatch fixed and isolated gates passed
BR_FIXED_PROOF_SUMMARY.json: mode1inference-only has allfive savedstatefilesbyteexact after113updates, includingfirst/lastgradients. NoPPO fusedplanscreated. Correctedtimings: {"BR_FIXED_GPU": {"control_ms": 1153.969408, "rows": [{"label": "br_fixed_gpu_base_a", "mean_ms": 1153.85856, "gain_percent": 0.009606723375177317}, {"label": "br_fixed_gpu_train", "mean_ms": 1135.979776, "gain_percent": 1.5836225591396413}, {"label": "br_fixed_gpu_base_b", "mean_ms": 1154.080256, "gain_percent": -0.009604877947066992}]}, "BR_FIXED_INFERENCE": {"control_ms": 0.39858900375000006, "rows": [{"label": "br_fixed_inf_base_a", "mean_ms": 0.39865399900000004, "gain_percent": -0.016303674405127033}, {"label": "br_fixed_inf_infer", "mean_ms": 0.36841399225, "gain_percent": 8.1905172264803}, {"label": "br_fixed_inf_base_b", "mean_ms": 0.3985240085, "gain_percent": 0.016308992335156702}]}, "inference_output": {"elements": 380416, "different": 284848, "relative_l2": 0.0073846960840616895, "max_abs": 3.0, "finite": true}}
Advanceinference-only andtraining-only tofullpipeline. Inferenceoutputroundingquantified; frozenactions preserved forspeed. No learningequivalenceclaim.

## 2026-10-10 03:11 — corrected fusion full results and aligned CPU test
BR_FIXED_FULL_SUMMARY.json: controls199206.848SPS,drift0.02594%;infer-only+0.11064%,train-only+0.22211%. Parkindividuallybelow1%gate. FUSION_DISPATCH_AUDIT.md explainsoldflagfailure, affectedmeasurements, exactregressionproof andfloatingdifferences.
NativeCPUharnesspreparedwithoptional128stepbarrier, noenginechanges. Fullasyncbootmeans measuredclocks63→78 corresponddecision8320→10240; nativewarmnow8320,measure1920. Newfivecase32worker/unpinnedstudy compares normal/focus bothwithoutandwith128stepbarriers, closingnormalcontrol.512game/256step lifecycle smoke matchedallendpoints. Fullstudy live under session95581. Originalnativebinary untouched.

## 2026-10-10 03:14 — scheduling gain survives horizon boundary
NATIVE_HORIZON_SUMMARY.json: normal32workercontrols231923.765SPS,drift0.1696%;focus248365.28(+7.089%). Adding128stepbarriers:normal231748.55,focus247218.20(+6.675%). Allendobsb97835c62aaf388f and27,098,456worldturns match acrossaligned8320..10240window. Boundaryeffectdoesnotexplainmostfocusgain. CPUperstep137→125uswithbarrier. Singlecasespervariant,unfencedcontrolsrepeat. Thisclears0.8%nativegate;FOCUS_FAST32 fullcampaign launched afterallCPUwork finished. Uses32workersandcorrectedmode1GPUcombo, config/roundingcaveats explicit. No newretention.

## 2026-10-10 03:23 — continuation and focus closed
Previous prompt-only goal turn made no experiment progress. Re-read objective and polled session88102: terminalrc0. FOCUS_FAST32_SUMMARY.json: controls206511.871SPS,drift0.2726%;focus206060.698SPS,-0.2185%,tail193.83msvs190.92. All80obsproofs/actor/counts exact. Native+7.09% did not translate;parkbufferfocusagain,no loserupdatevalidation. FINISH_SLEEP prototype verified and build launched after GPUidle. Tests horizon-boundary mainwait and collectoridlesleep, distinctfrom previouslytestedCUDA/pooltailwaits.

## 2026-10-10 03:30 — horizon sleep screen closed
FINISH_SLEEP_FULL_SUMMARY.json:controls206379.232SPS,drift0.0566%;collectoridlesleep208051.005(+0.8100%);collector+mainfinishsleep206845.361(+0.2259%). Tail190.70→179.45/186.20ms. All80observationproofs/frozenactor/batch/updatecounts exact. Collectorresultisasmallpositivesignalbutbelowpredeclared1%fullgate;parkboth,noexpensiveupdatevalidation. No retained change. Next freshnodeprofileofcorrectedfastGPU32workerstack,2matureepochs, toidentifycurrentcriticalpath;serializedaftertimings.

Profile analysis extension prepared: analyze_contention.py partitions inference andpoolNVTXrangesbyobservedPPOgraphspanoverlap, reportskernel-sumvsspanlatency andreaderdrain/tail. Observationalphasecomparison,notcausalproof;nodecaptureperturbsruntime. Syntaxcheckpassed; runaftercaptureterminal.

## 2026-10-10 03:33 — fresh fast-stack contention evidence
FAST32_PROFILE.json terminalrc0;226PPOupdates/1024inferencegraphs in2matureepochs. contention.json: inferencemeanspan1.6915mswithPPO(n767)vs0.3901mswithout(n255),summedkernel0.7152vs0.3781ms,post-submitwait0.1838vs0.0777ms. CPUenv7.3102vs7.3430ms;pooltail1.93msallphases. TheseareobservationalgroupsandnodetracingperturbsSPS. Unprofiledfullmodelevents~196ms/horizon corroborate slowerconcurrentinference qualitatively. Nextboundedcausaltest: highpriorityactorstreamonfastGPU/32workers, and2vs4Muonstreams separately. Priorpriority+0.61% onslowerstackdoesnotestablishcurrentresult;newstackhaslargeexposedtail. FAST_INFER_PRIORITY.patch onlyisolatedstreamcreation pluspriorityreadback. No speedclaimyet.

Priorityv22built SHA76bcd084541e9ef9de2ff5a61eb032ea6f299bdfd9ddfd62c766450bbe215012. 4epochbaseline/prioritysmokebyteexactobs/frozenactor;allfouractorstreamsreportpriority−5vsnormal0. GPU_CONTENTION_FULL.json launched under session45254; control/highpriority/twoMuonlanes/control, each80epochs. Nootherheavywork. integrity_303min.json confirms16protectedfilesunchanged.

Priorityfirstarm210021.5SPSvsopening206618.6(+1.647%,closingcontrolpending). Unprofiledper-buffer modeltime195.61→109.24ms,envwall879.67→953.77ms,copy68.57→68.96ms. Theseoverlapandenvwallincludesqueueing;donotcallthisincreasedengineCPUcost. Two-lane arm206696.7SPS(~flat). Prepared PRIORITY_CONFIRM.json(reverseABBAfourruns)andPRIORITY_LIVE.json(8epochs/904appliedupdates each), tolaunchonlyifclosingcontrolkeeps>1%gain. CORRECTED_COMBO_PROOF.json separatelyquantifiesactualcorrectedGPUstacknumerics;oldboth-fusionproofisnotthesamecandidate.

POOL_TIMING.patch/source/spec prepared whiletimingsran;sourceonly,notbuilt. Optionalfourmonotonic+threadCPUclockpairsper512-gamepoolcall,64Bcachelinealignedone-writerperbuffer. Logsclaim+publication,tail,readerdrainaftercollectorjoin;noengine/arithmetic/schedulingchange. Newtracepooltail1.93mscouldbetracing/schedulingartifact;requireunprofiledconfirmationbeforelongest-firsttaskexperiment. Timingoverheadmustbemeasuredagainstsamebinaryoffcontrols. Defaultoff. Buildonlyaftercurrentpriorityvalidationjobsfinish.

## 2026-10-10 03:42 — priority clears first full gate
GPU_CONTENTION_FULL_SUMMARY.json:controls206754.287SPS,drift0.1313%;priority210021.521,+1.58025%;twoMuonlanes206696.702,−0.02785%. All80obsproofs/actors/countsexact. Prioritytail161.8vs188.1ms;twolanes141.6msbuts lowerPPOoffsetit. Two-lanearmparked,nolongvalidation. PRIORITY_CONFIRM.json fourreverse-ABBAfullruns launchedsession24401. Follow withliveproof/correctedcomboupdatequantificationonlyifrepeatclearsgate. No newretainedimplementationyet.

Priorityconfirmationfirstcandidatefinished210104.813SPS,nowcontrolpriority_confirm_base_aliveunderPID2931358. Session24401pending. Currentturnmadeprogress:twocompletedscreens,newprofile,priorityinterventionclearedfirstgate;goalremainsactive.

## 2026-10-10 03:45 — continuation audit
Previous goal turn made concreteprogress (closedfocus/horizonwaits, freshtrace, priorityfirstscreen). Re-readobjective,deadlineandpolledsession24401live. Preparedvalidate_priority.py toverifyliveflags(noactionreplay/nooptimizerfreeze),actual904updates,initial/finalchangedweights,fullrolloutfieldcoverage,allstate/checkpointhashesandfinitechecks. ExecutionawaitsrepeatgateandPRIORITY_LIVE completion.

## 2026-10-10 03:50 — priority repeat passes
PRIORITY_CONFIRM_SUMMARY.json: candidate210104.813/209663.533,mean209884.173;controls206591.185/207546.653,mean207068.919,drift0.4625%. Repeatedgain1.3596%,all80proofs/actors/work-countsexact. PRIORITY_LIVE andCORRECTED_COMBO_PROOF areexecutingsequentiallysession46797. Clean32applicabilityspecprepared(PRIORITY_CLEAN32.json),notlaunched. POOL_TIMING_FULL nowusespriority1inallarms,probingcurrentleadwithmatchedinstrumentationoff/on/off;historybeforechangeinprepare_pool_timing.py. Buildv23onlyafteractiveGPUvalidationfinishes.

## 2026-10-10 03:52 — priority live-exact, correctedcomboquantified
PRIORITY_LIVE_PROOF.json: 2097152actualsampledsteps/904appliedupdates perarm. Priorityvsnormalonidenticalcorrectedfaststack matchesallrolloutfieldhashes,RNNstate,master,momentum,updates,finalcheckpoint byteforbyte;finite. Noactionreplayoroptimizerfreezeflags,weightschangedfrominitial. Thisvalidatesscheduler,notGPUcombovsclean.
CORRECTED_COMBO_PROOF_SUMMARY.json:113maturebatchupdatesfinite; firstgradientrelativeL2 0.00097033,last0.434244;master0.00038845,BF16params0.000848,momentum0.25092,updates0.42156. Roundingchangesremainmaterialinlategradients;notanexactlearningclaim. Singlecoldprooftimings1155.78/975.22msarenotbenchmarks.
Builtoptionalpooltimingv23SHA251cf4c7d10801e321d6e8b43c0b4ddc04f811f91778d2cb2a4cab7e65875014,notyetrun. PRIORITY_CLEAN32.json launchedsession46096toassessapplicabilitywithoutotherGPUoptimizations;80epochbase/priority/base. Runpooltimingsmoke/fullonlyaftercleancampaigndone.

## 2026-10-10 03:58 — cleanapplicabilityandphasealignment
PRIORITY_CLEAN32_SUMMARY.json: controls204213.465SPS,priority203394.389(−0.401%),drift−0.114%. All80proofs/counts/actorsmatch. ConfirmspriorityisconditionalonfasterGPUstack;notageneraldefault.
Founddetailcounteroffset:train_implincrementspufferl->epochbeforeROLLOUT_DETAIL,soSPSouterepochs64..78requirecounter65..79. phase_summary.pycorrectsandregeneratesphasebreakdowns;SPSneveraffected. Correctedfirstprioritymodel195.36→109.18ms,envwall879.05→952.36ms. OldFINISH_SLEEP_PHASESmarked superseded.

## 2026-10-10 04:04 — pool tail confirmed and cost-order hypothesis
Previous prompt-only goal turn was no progress. Re-read objective and polled live session68352 to terminal. POOL_TIMING_FULL: controls209795.834SPS, drift−0.2243%; timing210437.122(+0.306%). All80obs/actor/counts exact. Pool claim655.912ms,tail286.222ms,drain0.614ms per128-step buffer; submitterCPU509.495/111.374/0.145ms. Large tail survives lightweight instrumentation. Per-buffer values overlap, not total wall attribution. Newcostorder experiment: measure prior per-env wall durations, sort expensive games first without changing environment order or striped stealing. Timer-only control separates overhead; sort may hurt locality. Source prepared, build/smoke/full next.

## 2026-10-10 04:10 UTC — copy graph prepared
COPY_GRAPH.patch/source/spec prepared during cost-order timing, not compiled. Mode1 captures four fixed-address H2D transfers into one reusable upload graph at the original loop position. Mode2 additionally includes action D2H in inference graph; same final stream sync protects download and rollout archive. Initial/final uploads retained. Model/copy phase attribution shifts in mode2; total SPS is comparable. Live-sampled frozen-policy smoke required before full timing, since replay alone cannot detect bad sampled-action download. No additional heavy process started. COMBINED_DIRECT/DEPTH specs prepared to close pending combined-baseline and secondary-workload evidence after candidate screens.

## 2026-10-10 04:12 UTC — cost-order scheduler closed
POOL_COST_FULL_SUMMARY.json: controls209900.673SPS,drift+0.1304%; per-task measurement209906.457(+0.0028%), expensive-first sorting207270.074(−1.2533%). All80observations/actors/work-counts exact. Sort increasesclaimwall676.19vs662.34ms,tail296.29vs287.66ms; does not solve observed tail. Park, no longliveupdatechecks. v24SHA5d1ce715451478fc7293610da69d324423ab23ef8d73dc8bd4d7ba101a74ccfc. Nextbuildcopygraphv25aftercampaignterminal.

## 2026-10-10 04:14 UTC — copy graph smoke harness corrected
Frozen live-action smoke runs completed, but validator expected BATCH_PROOF lines that are intentionally replay-only. All three rows lacked them, so gate failed even for the control; no candidate behavior failure inferred. Re-running short four-epoch smoke with actual updates to use existing full final-state/rollout hash output. Unique labels preserve original artifacts. If all final states match, proceed to full timing; no source correction needed. Session95382 owns live smoke then conditional full campaign. Immutable v25SHA792952f24e5cb4109292b11911c37a9ff10db1a6b2a9ac60045dcf58874962f6.

## 2026-10-10 04:17 UTC — copy-graph live smoke passed
COPY_GRAPH_SMOKE_PROOF.json: all three variants match final two-slot rollout hashes (observations/actions/logprobs/values/rewards/terminals/masks/initialRNN), env observations, per-bufferRNN, weights and optimizer states after1,048,576 live steps/452 applied updates. Initialcheckpoint differsfromfinal, replay/freezeabsent. Fulltimingbase209574SPS; uploadarmcurrentlyinmaturewindow. No speedclaimyet.

## 2026-10-10 04:21 UTC — copy graphs closed; exact bias candidate prepared
COPY_GRAPH_FULL_SUMMARY.json: controls209713.043SPS,drift+0.1326%; uploads209501.777(−0.1007%),both210104.856(+0.1868%). All80observations/actors/work-counts exact; preceding1,048,576live-step452update smoke finalstateexact. Both below1%gate, park with no longer update checks. Mode2phase labels includeD2Hinmodeltime.
BIAS_DIRECT.patch prepared only: tracedReLU+biasbwd88.27ms/226updates. Widecolumns(dim>=256) haveonecolumnperCTAthread, so sharedaccumulatorzeroing/twobarriers/staging redundant. Keepgrid, perthreadFP32sumorder, BF16mask/stores andfixed-pointquantization; directglobalintegeradd. Narrowcolumns unchanged. Actualkernel extraction60cases prepared; build/runonlynowGPUidle, then interleavedGPUtiming.

## 2026-10-10 04:23 UTC — direct bias reduction closed
Actualkernel60case smoke matches55,389,172maskedgradient elements andintegerbiasaccumulators exactly. FullsavedbatchGPUcontrols974.234ms,candidate973.794ms,gain0.0452%;neutral. Parkwithoutfullpipeline/longupdateproof. V26SHA4ff35d1f8d4ac76a022a096d84851a02724bba5a9be6bbe9d767eca38428a911. No new retainedwinthisturn. Launchdirectcombinedbaselinecomparisonwithimmutablev22, keeping24vs32workersseparate;then depthsecondarycomparison.

2026-10-10 04:26 UTC: direct opening baseline completed194159.559SPS. Session46326 now runs combined_direct_fast24, PID2935265 verified live/exe=inference_priority_v22. Closing control and secondary depth remain queued. This goal turn made concrete progress: completed pool timing diagnosis, closed three candidate families, verified copy live-equivalence and extracted-kernel exactness, started direct/secondary comparisons. Goal remains active.

## 2026-10-10 04:31 UTC — training GEMM algorithm screen prepared
Previousgoalturn made concreteprogress and verifiedactivecombinedcampaign; rereadobjectiveandpolledsession46326live. Cachedprofilepointerdecoder kernels are only~42usforward,43usdq,34usdk perupdate,so notfirstpriority. RecurrentlargeGEMMs dominatehundredsofmsintrace. PriorLtsearchwasinferenceonly. Preparedstandalone three-shapeM4096/H1024 forward,dX,dW algorithm screenwithsame4MiBworkspace/BF16io/FP32compute+reduction. HotdataGPUtimingisaprescreen,notnetclaim. No compile/runwhilecombineddirect/depthisactive.

## 2026-10-10 04:32 UTC — combined direct comparison
COMBINED_DIRECT_SUMMARY.json: originalfixedbaseline194071.687SPS, control drift−0.0905%. CorrectedGPUcombo+priority+blocking24workers201632.615(+3.8959% fixed-worker implementation comparison);32workers210221.722(+8.3217% including worker configuration). Memory8840.1→8290.1MiB;tail81.34→219.12/157.79ms. Earlycontrols~208008SPS,candidates237085/238786. All80replayproofs/frozenactors/113updates match. NumericalcaveatCORRECTED_COMBO_PROOF_SUMMARY applies; not exact-learningclaim. Depthsecondarylive under session46326.

## 2026-10-10 04:34 UTC — secondary depth screen complete
COMBINED_DEPTH_SUMMARY: controls382411.371SPS,combo397559.166(+3.961%),all80obs/actor/work-countsexact. Controlsdrift+0.5247%,slightlyabove0.5%repeatgate,so reverseABBAconfirmationpreparedbeforedefaultrecommendation. Depthlive8epochsanityalsoprepared,onlyifrepeatpasses. Directmain+8.32%includesworkerconfiguration;+3.90%fixed24workers;notadditivegains. MicroGEMMscreen running serializednextunder session14212.

## 2026-10-10 04:42 UTC: secondary confirmation and training GEMM candidate
Depth combined repeat:382,949→397,736SPS,+3.861%,control drift+.151%,80 observation checks exact. Short live depth sanity completed finite; final master relativeL2.024706,momentum2.8083,updates1.4012 after divergent live trajectories. This is stability evidence only, not update equivalence or learning quality.
Training GEMM isolated repeat: recurrent dW synthetic hot operands172.896→157.567us,+9.728%,control drift+.090%. Candidate runs162.960 and152.174us differ substantially, but both beat controls172.818/172.973. Forward/dX neutral. Missingcstring in repeat build fixed before running. Preparing shape-specific actual training dispatch for only3072x1024x4096 TN, BF16/FP32,4MiB limit,algorithm30 zero workspace. CPU-only source edits occurred while secondarylivecheck ran; build/timing serialized after it.

## 2026-10-10T04:43:13.706595+00:00: recurrent dW actualGPU screen
Actual-header graph smoke passed two seeds6,291,456outputs finite,relativeL2~.002123. v27SHA07bdccb7638a11624dee5ed37f893fe4a2b68cf5b5e11d1412131f8e433bc463. Fullsaved-batch GPUcontrol969.551ms→965.279ms,+0.443%,control drift+0.182%. Dispatch ID30confirmed in trainer. Parkedbelow1%gate, noextendedtrainingchecks. TRAINING_DW_GPU_SUMMARY.json/TRAINING_DW_LT.patch. Next refreshcurrentbest priority-onprofile.

## 2026-10-10T04:49:06.067402+00:00 message shards closed; weight traffic candidate
MSG_SHARDS_GPU_SUMMARY.json:control969.655ms,4shards+0.128%,8shards-0.099%,drift+0.207%.64case integer+BF16smoke exact16,777,216values. Park, nolongproof.
Currentprioritynodeprofile completed226updates/1024infergraphs. Concurrent inference mean.9014ms versus.3824withoutPPO, compared1.6915msbeforepriority;observational/tracingoverhead caveat. Messagebwd138.28us remainedbutshardsdidnotpay. Separate fullweightcast~105us/update rereads62MBmasterweights. Twoexplicit modesprepared: fusefinalupdate+cast, or fuseaspectscale/update/cast ineachmatrixfinalstore,retainingBF16roundingofupdate and streamjoin. Secondmodeassertsnoalternatefused/batchedMuon. Goal islowerglobaltraffic andearliermatrixcompletion; basicexactsmokethenGPUtiming.

## 2026-10-10T04:53:15.794764+00:00 weight fusion closed
Control968.102ms;globalfusion+0.451%,per-matrixfusion+0.074%,control drift+0.127%. Parkedboth. Firstsmoke found smallmasterroundingdifferences inper-matrixmode (max1.19e-7,relL2~8e-9), then restoringoriginal dynamicdecayexpressionmadeall20cases/12,849,236update/master/parametertriplesexact. Failedartifactsretained.
NextGramhalfworkhypothesis:forR3072/C1024 recurrentMuon GramX^TX, blocktriangularpartition2/4/8 reducesdensework25/37.5/43.75% plusmirrorcost. Thisisnotpreviousbatchingofindependentmatrices:computesfewerblockproducts. BF16inputs/output,FP32compute unchanged,roundoff maydiffer. StandalonecuBLASbatchedscreenbeforetrainerintegration.

## 2026-10-10 04:55 UTC: triangular Gram screens
GRAM_TRIANGLE_SCREEN.json: partitioned cuBLAS batched2/4/8tiles all47.8–50.1us vscontrols43.15/39.54us. Controlsdrift−8.37%; allcandidatesstillworsethanbothcontrols, parkimplementation.
GRAM_TRITON_SCREEN.json: halftriangle customkernels32/64/128tiles,4/8warps,3/5stages. Best64tile/K32 about40.35us vsbaseline40.35/39.62us (firsttrialclockdrift);full64tile/K64 42.31us versushalf41.26us. EveryoutputmatchescuBLASonthissample. No usefulgain, no integration. Similarfull/half timesmotivate onebounded splitK screen: moreactiveblocks,FP32partialreductionandmirrorincluded,2/4/8splits. No reducedprecision. Currentlyrunninggram_triton_split.py;allheavyworkserialized.

## 2026-10-10T04:59:00.996076+00:00 split Gram closed
GRAM_TRITON_SPLIT.json:longerwarmupcontrol39.702us,drift+0.198%. Bestcandidate46.315us (-14.28%), remaining55–82us. Allfinite,FP32partialmerge relativeL2~.000205,maxabsolute16 onsyntheticdiagonal~3000 (BF16quantization). Extra scratch+reductionmoreexpensive;closeapproachwithouttrainerintegration.
Projectionshapeverifiedfromexistingmatrixcapture id18=1024x1698;sourcecomment1410isstale. NewGEMMscreencovers4096x1024x1698 forward,4096x1698x1024 dX,1024x1698x4096 dW. SameBF16/FP32/private4MiB;longer100graphwarmup before5trials. Notretuningpreviousrecurrentwinner orrepeatingindependentbatchedGEMMs.

## 2026-10-10T05:02:07.349998+00:00: projection screen and turn handoff
PROJECTION_GEMM_SCREEN_SUMMARY.json: forward +.266%, dX +.190%, dW +.121% isolated; controls drift +.304/+.209/−.023%. Park all algorithms without trainer integration. MODEL_DIMENSIONS.json and resolve_model_dimensions.py verify current NH_CONCAT1698, NH_BL_FEAT134, message256, accessory160. Initial parser omitted comma declarations and then selected the inactive #else panel arm; both caught before writing metadata, corrected with explicit active-flag checks. Old source1410 comment is stale.
Previous prompt-only turn was no progress; objective reread and live71950 poll revalidated current work. This continuation made progress: secondary applicability validated, current profile refreshed, several new mechanisms screened and rejected with artifacts. Goal remains active; all heavy processes now terminal. Protected16files unchanged in integrity_390min.json; checked_at authoritative.

## 2026-10-10T05:03:54.657491+00:00 projection padding screen
Previous goal turn classified progress; current objective/status re-read and GPUidle verified. Actual logicalwidth1698. Standaloneprivate4MiBcuBLAS compares1704/1712/1728/1792paddedwidths forinference/trainforward/dX/dW, bothincludingmovementandkernel-onlyceiling. Correctness comparesalllogicaloutputs finite/relativeL2 beforetiming, extraentrieszero. No model/optimizer/sourceintegration changes.

## 2026-10-10T05:08:38.194107+00:00 — padding closed; recurrent inference fusion
Previous user-requested prompt turn made no experimental progress. Re-read original objective and polled session34132: terminalrc0. Projection padding including moves loses all shapes (best inference−19.48%,forward−11.63%,dX−13.55%,dW−14.47%); inference controls drift−7.87%, but every moved candidate is slower than both controls. Kernel-only gains are not end-to-end gains. Park generic packing without trainer integration.
Next bounded hypothesis: fuse recurrent inference GEMM and minGRU gates, preserving BF16 rounding of projected values and state. Current trace has4 GEMMs plus4 gates per inference. In-place x/out alias in layers2+ requires ping-pong output if integrated; do not write GEMM output over its input. Standalone Triton screen against exact extracted CUDA gate/private4MiB cuBLAS before any integration.

## 2026-10-10T05:10:52.591640+00:00 recurrent fusion passes isolated gate
Initial screen usedfastmath onextractedreference; reran withtrainerO2/no-fastmath before advancing. REC_FUSED_REPEAT:baseline29.186us,64x32/BK32/4warp3stage23.191us(~25.85%throughputgain),drift+.239%. Output/state relativeL2~5.1e-5/5.3e-5,notbitwiseexact. ExportedSM89cubin withBF16intermediateprojectionrounding retained. DriverABI has2extra nullscratchargs verified fromPTX/metadata. Integration usesexisting next_state allocationasping-pong toavoidGEMMin-placealias; onlyM512/H1024inference,trainingunchanged. Build/inference/fullgatesnext.

## 2026-10-10T05:13:07.058647+00:00 recurrent integration screen; residual candidate prepared
REC_FUSED_INFERENCE_SUMMARY: fullinference338.492→336.501us,+.592%,control drift−.184%. Alloutputsfinite,14,280/380,416BF16valuesdifferent,relativeL2.000797. Onefullpipelinebracket running tocheckcontention behavior; notretained. Next independentGPUcandidateprepared: recurrentbackward dX GEMM beta1 reads scan.grad_input asresidual,eliminates4addkernels~133us traced/update. Preserve outwardB_TTxHshape whilepointingtoeachlayerresidualbuffer. Changesrounding (single GEMM outputround vs GEMMBF16thenaddBF16),nooptimizer/equationchange. Build/smoke deferreduntilactivefulltimingsfinish.

## 2026-10-10T05:17:14.290338+00:00 recurrent fusion closed; residual smoke
REC_FUSED_FULL_SUMMARY:209871→210618SPS,+.356%,drift+.086%,80obs/actors/workcounts exact. Below1%fullgate,parknoextendedupdatecheck. Standalone25.85%gainshrunkto.59%wholeinferenceand.36%fullpipeline.
Residualsmoke {"cases": 12, "elements": 12781173, "maximum_relative_l2": 0.0026594291175487668}. ProceedshortGPUtiming;notanactualgradient/stabilityproof.

## 2026-10-10T05:18:53.701601+00:00 residual fusion closed; inventory branch fusion
{"control_ms": 973.3110784, "control_drift_percent": 0.08030584845497568, "candidate_ms": 973.4234112, "gain_percent": -0.011539973120378022, "status": "Parked: no GPU timing gain; no extended update proof or fullpipeline test."}
Next hypothesis: fuse inventory16→64→64 MLP andmasked55-slot sum/maxpool into one kernel pergame. Baseline is currentinference fused-bias/ReLUcuBLASLt plus exactpool, notslowerunfusedcontrol. Optionalintermediatestores separated;inference doesnotconsume them. Pointerkeys/inventoryrepresentation/trainingmath unchanged. TritonFP32sumtree maychange rounding,maxwinner differencesmustberecorded. Standalone screenfirst.

## 2026-10-10T05:20:43.856288+00:00 inventory fusion advances
StandaloneMLP/pool17–18→6.79us,allpooledvalues/argmaxexactonsyntheticinputs;openingcontroldrift−7%butclearwinagainsteithercontrol. Actualcheckpoint wholeinference {"control_ms": 0.3396126092, "candidate_ms": 0.3122506438, "gain_percent": 8.762821132092103, "control_drift_percent": -0.39770139474462063, "output": {"elements": 380416, "different": 0, "relative_l2": 0.0, "max_abs": 0.0, "finite": true}, "control_outputs_equal": true}. Advancefullpipelinebracket. Inferenceonly, existingtrainingstates untouched. Immutablev32SHA37bcf983c0dbda8ef376fe25e25609224f46b0969db6ee3315891257170e8b17.

## 2026-10-10T05:23:24.184810+00:00 entity generalization prepared
Inventoryactualinference338–340→312us,+8.763%,all380416outputBF16elementsidenticalonmaturebatch. Fullbracketlive under session71195. Prepared entity_fused.py + entity_fused_reference.cu/entity_fused_screen.py forsame16→64→64pool on16monsters/16flooritems/8spells. Matrixproducer 48→16/keygeneration remainsoriginal. EachbranchrespectsitsPAD/EPS/OFF. No compilation/heavytest whilefulltimingsactive; no integrationyet.

## 2026-10-10T05:25:35.913419+00:00 broader fusion rationale
Inventoryonly fullcandidate210754SPS vsopening209811(+.45%,closingcontrolpending): likelybelowretentiongate. The generalizedentityscreenisnotclaimingthisasaretainedwinner. Hypothesisistoremove sameoverheadfromallfourmodalities, largercollectiveinferencegain,thenoptionallytraining withoriginalBF16pre-biasroundingandintermediatestores. Keepisolatedcomponentandcombinedpipelineclaimsseparate.

## 2026-10-10T05:28:19.973674+00:00 entity fusion actual inference
{"control_ms": 0.3401649148, "control_drift_percent": -0.06576222620755523, "output_elements": 380416, "rows": [{"label": "entity_fused_inference_base_a", "microseconds": 340.2768016, "gain_percent": -0.032881113103777615, "different": 0, "relative_l2": 0.0, "max_abs": 0.0, "finite": true}, {"label": "entity_fused_inference_inventory", "microseconds": 313.82602479999997, "gain_percent": 8.392831670600188, "different": 0, "relative_l2": 0.0, "max_abs": 0.0, "finite": true}, {"label": "entity_fused_inference_other", "microseconds": 321.40994679999994, "gain_percent": 5.835217045000318, "different": 0, "relative_l2": 0.0, "max_abs": 0.0, "finite": true}, {"label": "entity_fused_inference_all", "microseconds": 288.5773478, "gain_percent": 17.87651296724544, "different": 0, "relative_l2": 0.0, "max_abs": 0.0, "finite": true}, {"label": "entity_fused_inference_base_b", "microseconds": 340.053028, "gain_percent": 0.03290275068510429, "different": 0, "relative_l2": 0.0, "max_abs": 0.0, "finite": true}]}
Inventoryonlyfullresult+.447%,drift+.0054%,80replayproofsexact;notretainedalone. Allfourbranchesv33hasfreshstandalonecontrolsdrift<.5%,pooledoutputs/argmaxexactonsyntheticcases. Fullpipelinecombinedscreenisnext. Trainingunchanged,NH_ENTITY_FUSEDbits1inv/2monster/4item/8spell,inferenceonly.

## 2026-10-10T05:31:40.183042+00:00 continuation and training-side candidate
Previous goal turn made concrete progress: recurrent/residual/inventory screens closed, all4entityinference fusion implemented andfullpipelinecomparisonstarted. Originalobjective reread; session23135 polledlive (no restart). Next preparation: training-side16→64→64MLP/pool fusion preservingBF16GEMMround beforebias andstoringh1/v neededbyexistingbackward. Currentinferencekernelcannotbeusedunchangedfortraining. ShortGPUtimingfirst; no simultaneousheavywork.

## 2026-10-10T05:38:44.739302+00:00 — inference fusion closed; training variant screened
Previous prompt-only turn was no experimental progress; objective reread and session23135 polledterminal. ENTITY_FUSED_FULL:209817.493→211118.677SPS,+.62015%,control drift+.32645%,80replayproofs/frozenactor exact. Parkinference-only standalone under1%gate. No extendedtrainingchecks.
TrainingvariantpreservesBF16pre-biasrounding,storesh1/vfororiginalbackward. Screeninventory130.583→63.726us,monster42.000→13.685,item42.016→13.679,spell24.870→12.920. Control drift<.6%. Pooledoutputs/argmaxexactonrandomsample;inventory11intermediateVvaluesdiffer(relativeL2~4.9e-6),otherbranchessampleexact. Private4MiBcuBLAS+separatebiasbaseline. Firstreferencecompilemissingcublas_v2.h;fixedbeforetests.
Built isolatedentity_train_v34, immutableSHA96d43249e2e9e4ab3fd648aed774cb782ae865d0992abb4db5331fb10ce369e9. NH_ENTITY_TRAIN_FUSEDbits1/2/4/8separatefrominferenceflags;a->training&&!nh_fused_br_activeplusdimensionguard. Newheaderinbuildsnapshot. SavedGPUtimingcampaignsession50178running. No engine/production changes.

## 2026-10-10T05:42:28.031256+00:00 — training GPU screen and next hypothesis
ENTITY_TRAIN_GPU_SUMMARY:969.743→941.807ms,+2.9663%,drift+.21374%. Inventory+1.715%,otherthree+1.264%. Fullbaseline/trainonly/both/baseline80epochcomparisonrunning(session97618). Sourcev34immutable.
Preparedpool_bwd_candidate.cuh/pool_bwd_micro.cu/pool_bwd_screen.py;NOTcompiledorrun. Profilecontains4poolroutingcalls/update~41.82usmean,followedbybias/ReLU. Mode1specializesN/PAD/OFFtoavoidruntime64bitdivision;mode2fuseswithbias/ReLU,keepsBF16DVroundbeforeReLUandexactsamegrid/threadfloataccumulationandfixedpointquantization. ProposedmicrochecksBF16bitsandint64biasacross4branches,B1/17/512/4096. Serializedexecutionafteractivefulltimings.

## 2026-10-10T05:46:09.901463+00:00 — training fusion closed
{"control_sps": 210091.24069682002, "control_drift_percent": -0.02631291766455046, "rows": [{"label": "entity_train_full_base_a", "sps": 210118.88490141093, "gain_percent": 0.01315818998413043, "tail_ms": 163.4270826, "memory_mib": 8290.1, "early_sps": 240175.97159404846}, {"label": "entity_train_full_train", "sps": 210766.65608795587, "gain_percent": 0.32148669734903823, "tail_ms": 188.90778226666666, "memory_mib": 8266.1, "early_sps": 244810.5959730813}, {"label": "entity_train_full_both", "sps": 211066.6776244851, "gain_percent": 0.46429204969697935, "tail_ms": 195.42962706666665, "memory_mib": 8266.1, "early_sps": 246199.901328228}, {"label": "entity_train_full_base_b", "sps": 210063.59649222915, "gain_percent": -0.013158189984119328, "tail_ms": 159.84892846666668, "memory_mib": 8290.1, "early_sps": 239403.98679565877}], "observation_proofs_exact": true, "frozen_actor_unchanged": true, "scope": "Frozen-actor replay throughput; not by itself an update-equivalence or learning-stability proof"}
TrainingGPU+2.966% converts tofull+.3215%;training+inference+.4643%. Stablecontrols−.0263%. Rollouttail161.64→188.91/195.43ms,absorbingGPUgain. All80replayproofs/frozenactor/countsmatch. PARKbothunder1%fullgate. PreparedENTITY_TRAIN_PROOFspec NOTRUN;noextendedtrainingcheckfortimingloser.
Nextpoolbackwardmicrocompilation/smokestartedafterfullsession97618terminal. No otherheavywork.

## 2026-10-10T05:48:23.885369+00:00 — pool backward micro and integration
POOL_BWD_SCREEN:32checks/56,252,160BF16gradientbitsplusbiasint64exact. B1/17/512/4096,all4branches,randommasksandall-padfirstgame. Baseline→specialize→fuse us:inventory89.51→80.32→48.52;monster31.18→27.05→14.05;item31.25→27.29→14.46;spell19.27→17.22→10.50. Control drift<.46%.
IntegratedNH_POOL_BWD0baseline/1specialize/2fuse(defaultoff),NH_ENT_LINPOOLfallback;templateusesactualN/PAD/OFF,guardfeaturewidth64. Samebiasgridandfixedpointorder. Spellbiasmemsetsnowbeforepoolrouting(independenttensors);allotherlaunchordersretained. Firstv35buildfailedbecauserealfrom_floatismacroandtemplatecommasseparatedarguments;parenthesizedexpressionfixedv35b(noequationchange). CurrentGPUtimingcampaignsession89044running. No extendedtrainingproofyet. Newheaderinsnapshots.

## 2026-10-10T05:52:15.379636+00:00 — pool backward closed; shift back to rollout critical path
{"control_ms": 970.1327871999999, "control_drift_percent": 0.14156166963759098, "rows": [{"label": "pool_bwd_time_base_a", "milliseconds": 969.4466048, "gain_percent": 0.07078083481879549}, {"label": "pool_bwd_time_specialized", "milliseconds": 968.7863296, "gain_percent": 0.13898395950280307}, {"label": "pool_bwd_time_fused", "milliseconds": 963.5387392, "gain_percent": 0.6843573311307471}, {"label": "pool_bwd_time_base_b", "milliseconds": 970.8189696, "gain_percent": -0.07068077792945493}], "decision": "Park: fused GPU training +0.684%, specialization +0.139%; no full timing or extended update proof."}
Session89044terminalrc0. No extendedproof orfulltiming forGPUgainunder1%. Immutablepool_bwd_v35bSHA73c3404ea50246cebb3635f4ac5203df2a4a98d59ce79bd887dd6606cc69ec35. Currentturnmadeprogress:closedallentityinference,trainingforward,poolbackwardwithmeasuredoutcomes. No newretainedwinner. All16protectedfilesunchanged.

## 2026-10-10T05:59:33.519004+00:00 — current CPU profile and wrapper-page hypothesis
Previousgoalturn PROGRESS:entityforward/backwardcandidatesclosed. Originalobjectiveread;GPUidleverified. Session76069current32-workerPGOnativeprofileterminal. 20,381samples: m_move18.7%self,mfndpos10.1,pack_obs4.2,fill_obs3.6,encumber_msg2.1,nle_weight.7;17.5%sched_yieldincluded(flatprofilesharesarenotCPUwallattribution). Unprofiled1024stepcontrols230943/232378SPS;profile2048step231187notaperformancenumber. ProfileCURRENT_CPU32_PROFILE.txt andnative_pool/runs/current_cpu32_profile/cpu.prof.
Historicalaudit:inventoryexportfusionandknown-firstalreadytested;move_load_reusealready null. Do not repeat. Distinctnewtest:contiguousEnvWRAPPERarrayhugepages,notenginecontextallocationtestedpreviously(2MiB/gameorcontextslab). Mode0oldcalloc/realloc,mode1alignedanonymousmmap+NOHUGEPAGE,mode2same+HUGEPAGE. Adds<2MiBpaddingtotal,notpergame;noeagerfullmemset. NeedverifyactualAnonHugePagesbeforeattributinganythingtoTHP. Mappercleanupafterpuf_close;defaultunchanged. IsolatedENV_PAGES.patch/source/src/env_pages.h;buildv36/smokesession44904.

## 2026-10-10 06:07 UTC — wrapper hugepages closed; empty-query census prepared
ENV_PAGES_FULL_SUMMARY:210354 controlSPS,aligned−.201%,huge+.109%,control drift−.346%. ActualAnonHugePages330MiB/330MiB versus0inNOHUGEcontrol;RSS+3776KiB. All80replayproofs/frozenactor/workcountsexact. Parknoextendedupdateproof. Session45602terminalrc0.
Nextdistincthypothesis: repeated initial floor-coordinate queries that findnothing. Diagnosticonly performs original iterator then simulates16/64/256-entry empty-query memo keyed bybounds+floor-generation;countercalls warmup-disabled, no skippedoriginalwork. Need measurehitcoverage beforeprototype. Sourceisolatedfloor_empty_study;enginebuildinprogress. Previousprompt-onlygoalturnNO_PROGRESS;thiscontinuationcompletedpendingcomparisonandinitiatednewevidencecollection.

## 2026-10-10 06:10 UTC — empty-query census supports a bounded prototype
39,951,908 initial spatial queries,10,285,731empty(25.75%),zero queries over an empty floor index. Simulated16/64/256entrymemo hits13.24/19.81/21.51% ofallinitialqueries;64entries avoids repeatedscanfor7,913,985queries. Diagnosticstillrunsoriginaliteratorandassertsallwould-behitsareempty;nativeendpoints/turnsexact. DiagnosticSPSexcluded. WeightedindexlengthmetricNOTactualworkfraction.
Candidate adds1KiB/context at end(noexistingfieldoffsetchanges),64interleavedkey/generationentries;generationwrapclearsmemo. Onlyinitialquerieswithcanonical8-bitboundsandnonempty/nonoverflowindexparticipate. BuildtwofreshmatchedordinaryLTOengines,currentPGOsourcebasebutNOinheritedPGOdata. Basicproperty+quickgatesrunning;timingsnextifpass.

## 2026-10-10 06:17 UTC — empty-query cache parked; repeated weight work measured
Empty-query candidate: matched ordinaryLTO512env/32workers281557→281362SPS(−.069%),control drift+.101%. All8nativewindowendpointsexact. 682201independentqueries including100000repeated/mutatingqueries,generationwrap,overflow,invertedbounds pass;5quickgolden/fuzzsuitespass. PARKnoPGO/fulltraining/fullcorpusspending.
Newweightdiagnostic:25012446inv_weightcalls/1027124291visitedinventoryentries in1048576maturepolicydecisions. Consecutivesumidentical24815076/25011716(99.21%). Existingupdate_inventorygeneration+headpointer+throwsrocks wouldhit24783173callsbut9203ofthesehavechangedtotals. Therefore notificationonlycacheisUNSAFE,notimplemented. Originalcomputationsunchanged;endstate/turnproofmatch. Codeweight_repeat_study.py/artifactweight_repeat_study/COUNTS.json. Traceofmissedchangesrunning next, diagnosticlogonly. All16protectedfilesunchanged.

## 2026-10-10T06:22:41.795294+00:00 — weight invalidation trace and candidate
576sampledfirst16/worker stale-value stacks mostlyencumber_msg/moveloop;remaining90samplesend-eating/statuscallbacks. Theseareobservationpoints,notexactmutationtracesnorpopulationfrequencies. Source recalc_wt changesfoodowt withoutupdate_inventory. Additionalfoodweight+everyengine-stepinvalidation testeddiagnostically:23366924/25012446calls(93.421%) eligible,0wrongconsecutivetotalsinthismaturewindow. Notcompletecoverage.
Preparedweight_cache prototypeonly:24B/context at end,cachetrueinternalcarriedweightsum;keepweight_cap execution/sideeffectseverycall. Guardheadpointer/formrockability. Invalidationsupdate_inventory,recalc_wt,nle_stepafterbinding. Existingpublicappearance-basednle_weight UNCHANGED. Fast+NLE_WEIGHT_VERIFYbuildscomplete;quickgatesandmaturereplayverifierinprogress. Needtimingfirstthenbroaderstaticinvalidationaudit/fullcorpus/depth/PGO/fullpipelineifwin. No production/default changes.

## 2026-10-10T06:26:13.310434+00:00 — weight cache passes first timing screen
SCREEN_512_SUMMARY:281507.49→287323.36SPS,+2.066%,control drift−.578%;allcandidatewindowsbeatbothcontrols,butprovisional.10quickgatesandwarm+mature512cacheverifierpass;all8timedendpointsexact. Native2048comparisonrunning under session59409. No retention or fulltrainingclaim. CurrentturnPROGRESS;goalremainsactive,16protectedfilesunchanged.

## 2026-10-10T06:32:00.271383+00:00 — weight cache at2048 and matchedPGO gate
PreviousgoalturnPROGRESS:completedtwo nullscreens,measuredinventoryweightreuse,implementedandcheckedcandidate,started2048screen. Originalobjectivere-read;session59409polledterminal. SCREEN_2048_SUMMARY219843.19→221991.71SPS,+.9773%,control drift+.1803%. Allcandidatewindowsaboveallcontrols;16nativewindowendpointsover512+2048exact. SmallgainjustifiesoneboundedmatchedPGO/fullpipelinecheck;notretained.
FreshPGObaseandcandidatebuilds running serially under session24221, same historical8score+8depth recordedinputs as retainedPGO, eachownprofilecounters,coverage-mismatchfatal. PreparedWEIGHT_CACHE_FULL.json,NOTRUNuntilPGObuildcomplete. Allfullconfig/model/actor/actionsfixed;fourbracketed80epochruns. Iffullgainnotuseful,parkwithoutfullmutationaudit/extendedlearningchecks.

06:38 UTC — Matched PGO builds complete; identical profile inputs verified. First full launcher rejected LD_LIBRARY_PATH before spawning benchmark (no timing data). Experimental run.py now explicitly allows that override; retry uses new labels to preserve failure evidence.

2026-10-10T06:41:01.473126+00:00 — Full campaign live session6247, baseline mapping verified weight_pgo_base library and candidate mapping verified weight_pgo_candidate. Dry-tile monster liquid guard script prepared only, based on minliquid profile and disassembly (original dry path loads compact type, primary tile type, dungeon state, steed and monster classes). Eels/water/lava/fountain/raised drawbridge retain original handling.

2026-10-10T06:44:37.809724+00:00 — Weight-cache matched-PGO full screen complete: 210159.5->211830.9SPS (+0.795%), control drift-0.586%.80obs/frozenactor/counts exact each. Small positive candidate, parked below1% full gate and needs repeat plus broader invalidation audit; not retained. Dry-tile minliquid fastpath now isolated and building.

2026-10-10T06:46:34.473733+00:00 — Dry-tile minliquid early-return candidate:34goldens+26fuzz passed,512env screen 281547.5->285244.3SPS (+1.313%),controlsdrift+0.785%. All candidate windows above all controls;8endpoints/turncounts exact. Drift is above0.5%, so provisional. Advance2048screen, not retained. Candidate avoids cold primary-tile/dungeon/steed checks only for non-eels on ordinary dry terrain; wet/fountain/drawbridge/eel paths unchanged.

2026-10-10T06:50:29.327236+00:00 — Prior goal turn PROGRESS:weight full gate closed and drytile candidate tested. Current2048 drytile screen complete:219306.905->221153.855SPS,+0.8422%,control drift+.1742%;all8endpoints/turncounts exact and candidate windows all exceed controls. Small but stable; one bounded matched-PGO/full gate justified by simple no-state-added guard and possible compiler interaction. Not retained. CandidatePGObuild now live;reuseunchanged freshlymatched weight_pgo_base as control,identical16feedbackinputs. LIQUID_FULL.json prepared only.

2026-10-10T06:56:41.207835+00:00 — Read-only candidate audit while full liquid timings run: intermediate observation deferral already enabled (obs.partial=1 plus nle_obs_refresh at wrapper decision boundary), so do not re-propose it. Existing pool tail sleeping/check-claim/batched completion are measured neutral; current flat sched_yield sample share is not fresh evidence for repeating them. Terrain-query script prepared only; no concurrent build/benchmark.

2026-10-10T06:59:54.346809+00:00 — Interrupted for user progress question. Full drytile comparison terminal, all80proofs/actor/workcounts exact. Timing INCONCLUSIVE: base212083->198513SPS (-6.399%drift), candidates212087/210797. Naive3%gain must NOT be claimed. Final baseline tail rises to238ms; new editorprocesses observed nearfinalwindow, correlationnotproof. ReversedABBA repeat prepared; no retained change.

## 2026-10-10T07:14:56.212680+00:00 — user-requested rollout attribution
Existing goal tool reports PAUSED; user explicitly authorized this bounded profile/experiment task. No new goal created, no autonomous goal resumed via tool. No live old drytile job; reversed repeat remains unlaunched.
New graph-level Nsight trace attribution_graph_20261010 completed: 2 mature epochs, 2048envs/4buffers/32workers/15.55M actor, same actions. Last collector tail after PPO GPU completion215.3/216.9ms; env/pool176.9/183.8ms (~82-85%), GPUwait32.8/26.5ms, submit3.5/4.4ms,upload1.7/1.8ms. Inference GPUgraph spans.877ms duringPPO vs.370outside. Configured profiling SPS78k is contaminated by profiler-stop overhead OUTSIDE measured BATCH_PERF; actual two captured BATCH_PERF epochs1.289/1.291s, do not call that a 3x profiler slowdown.
Isolated attribution_v37 adds no-training and no-inference switches AFTER64identicalwarmepochs. No-inference requires no-training+frozenactor+savedactions. Baseline flags off unchanged. BinarySHA1aaf25f9a6b9fc0512c2902e917036561768f7c86b79ca20cde35a1cc5f695bb. Production unchanged.
ATTRIBUTION.json8serialized80epochruns live under session42503. Firstcontrol209782.8SPS;rolloutonly220044.4SPS. All80obsproofs/actorhashesmatch originalbest. Livecounterfactualcpu+transfers(noinference/noPPO),then24/16worker full controls, reversedcounterfactual repeats and final32control. CPUproc monitor session47688 lowcost1Hz, no profiling or builds concurrent with timings. Artifacts attribution_20261010/PLAN.md,DIAGNOSTIC.patch,TRACE.json,summarize.py.

## 2026-10-10T07:32:07.554847+00:00 — attribution complete

Read attribution_20261010/REPORT.md for full evidence, commands and limitations.
- Full32-worker repeated controls209782.8/210775.8SPS; mean210279.3; drift+.4733%.
- Full24workers202260.5; full16workers183494.6SPS.
- PPO-disabled repeated collection220044.3/220794.7SPS.
- PPO+inference-disabled repeated engine+transfers221832.8/222354.5SPS.
- No-PPO main thread spins~.96logicalCPU, versus~.20 in full training. Repeat with existing PUF_FINISH_SLEEP: full210846.3, noPPO224876.5, noPPO/noinfer225966.5SPS. These bypasses are DIAGNOSTICS, NOT training speedups. No GPU clocks locked; noPPO lowersSM~2715→2520MHz.
- Two graph-level Nsight mature epochs: lastcollector waits~216ms afterPPOgraph; env/pool180.38ms(83.5%),GPUwait29.61ms(13.7%),submission3.96ms,uploadsubmission1.76ms. Env includes worker waits; no proof of a scheduler defect or specificcachecause. Normal unprofiled full tail~161ms. ProfileoverallSPS78.8k includes profiler-stop overhead; excluded. Actual captured batchtimes1.289/1.291s.
- InferenceGPUgraphspan .877ms duringPPO vs .370outside.
- Isolated fullGPUtraining5trials970.953ms/113updates:269986 equivalentSPS if rollouts free. Target278k requires943.718ms/batch: CPUcollectionneeds~23%morethroughput;GPUtrainingalso~2.9%more,plusoverlapmargin.
- All11 full/bypass runs:80observationhashesexact andfrozenactorhashunchanged. NoPPOexecutedupdates0 despitelegacyBATCH_PERF configured113 field. Architecture15.55M,2048env,4buffers,H128,batch262144,mb4096 fixed. Existing512unique recordedstreams repeated4x remainsbenchmarklimitation.

Conclusion: CPU environment/pool path currently sets pace. GPU contention still real, and GPUtraining becomesconstraint ifCPU catchesup. Do not equate finaltailfractionwithfractionofalltrainingwork. No new optimization promoted.

## Code/artifacts

Production/historical16protectedfilesunchanged (attribution_20261010/INTEGRITY.json). Diagnosticv37 exists only in isolated immutablebinary/snapshot; source/src/pufferl.cu restored byte-for-byte to env_pages_v36 after tests. Originalbeforecopy and DIAGNOSTIC.patch in attribution_20261010. Source now remainsv36; nextbuildmustnotassume diagnosticflags arestillinstalled. Binary attribution_v37 SHA1aaf25f9a6b9fc0512c2902e917036561768f7c86b79ca20cde35a1cc5f695bb.

Best optimization headline remains COMBINED_DIRECT_SUMMARY194072→210222(+8.32%including24→32workers),+3.90%fixed24workers; rounding/learning-equivalence qualifications unchanged. Read HANDOFF_before_attribution_20261010.md and LEDGER.md for parkedweightcache/drytilecandidates and other old experiments. No commit,push,PR,defaults,or unrelatedfiles changed.

## 2026-10-10T08:51:13.238532+00:00 — 5M model-size configuration test

15.55M→5.10M by width1024→512, layers4 unchanged. ABBA means208875→214938SPS (+2.903%), all80observationhashesexact and actorsfrozen. GPUalone971→513ms; rollouttail173→663ms. CPU remainsmainconstraint. Configuration/compute experiment only; frozenrandomsmallmodel, same teacheractions, learningquality untested. Nothing promoted. See model5m_20261010/REPORT.md. No jobs remain.

## 2026-10-10T09:03:59.245530+00:00 — user restores original512/H512 as primary

Main15.55M/512env/H512/fourbuffers/batch262144/32workers.2048isscalingonly. ABBA15.55M221431→5.10M282968SPS(+27.79%),sameoriginalmaturewindow. LargePPOlast;smallrolloutslast. ThiscorrectspreviousCPU-bottleneckgeneralizationfrom2048. All64obsproofsexact,modelsfrozen. Learningqualitynotmeasured,nonewoptimizationpromoted. Primarybatchsavedforfastscreens;GPU-onlylarge1031.986ms. See original_config_20261010/REPORT.md. Nojobsremain.

## 2026-10-10T09:52:53.898679+00:00 — Entity fusion retested on original 512 regime

Eight isolated full-pipeline runs complete: baseline221217, inference222594(+.623%), training226354(+2.322%), both228005(+3.068%). Both repeats exceed both controls; control drift-.642%. PPO last, zero rollout tail. 113-update and 1808-update combined checks exact in all checked gradients/state/rollouts; B128 inference exact. All protected files unchanged. Candidate remains isolated; no defaults, commits or pushes. All jobs terminal. Read entity512_20261010/REPORT.md.

User selected both entity fusions to keep. CANDIDATE.json records this; production defaults remain unchanged. Original 512-env configuration is still GPU-critical: mean PPO phase 1146.63 ms, rollouts ready 157.29 ms earlier, zero exposed rollout tail.

## 2026-10-10T09:59:14.181078+00:00 — Current primary overlap comparison
Bothfusions isolatedPPO 996.345/997.234ms (5warmtrials/process), mean996.790ms vsfullPPOhost1146.629ms;149.839ms/+15.032%gap, notpureavoidablecontention. Highinferencepriority stillon, chosenfor2048; normalpriority512 isnextplausibleexperiment, nottested/promoted. Artifacts entity512_20261010/OVERLAP_COMPARISON.json. All jobs terminal.


## 2026-10-10T10:22:03.971416+00:00 — requested512 overlap experiments

Primary remains512 environments / horizon512 / fourbuffers /32workers /15.55Mmodel. Keep both entity fusions from entity512_20261010 (previous +3.07%) and high-priority independent inference. Fresh priority ABBA: high 228,613 SPS, normal 211,891 (-7.31%). Ready-request dispatcher: 222,981 SPS versus fresh independent 228,476 (-2.41%). No production defaults/source changed.

Matched profiled PPO kernels take about13% longer under overlap; inference kernels about2.5x, with only16us initial ready wait versus546us graph duration. Normal priority creates long intra-inference gaps and exposed rollout wait. Larger batches save35–56% isolated forward time but dispatcher overhead/lost concurrency makes this implementation slower overall; batch-size BF16 outputs also differ, so not a behavior-preserving candidate.

Read overlap512_20261010/REPORT.md, SUMMARY.json, ANALYSIS.json, KERNELS.csv and INTEGRITY.json. All64 replay observation proofs match; 19protectedfiles unchanged. GPU/profiler timing sums are not additive wall time. 2048remainssecondary; main pipeline remains GPU/overlap limited, not the earlier2048CPU-limited regime.

