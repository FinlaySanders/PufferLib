# Active goal handoff — 2026-10-10T00:27:45.657966+00:00

24-hour goal active, deadline2026-10-10 22:30:39UTC, start2026-10-09 22:30:39UTC. Read OBJECTIVE.txt or original attachment before continuing. No token budget. Do not create another goal, pause, or finish early. Prior turn made progress: completed seven full-pipeline comparisons, a native scheduler screen, candidate implementation and correctness smokes. Goal still targets277778SPS with fixed15.55M policy.

## Retained

RETAINED.json v1 unchanged: clean_wait/source, clean_wait/wait.patch, binaries/clean_wait (fd37cca70fb8392ae4f77be8c2a2565d5be87650004d05f7d90493e461d7d392), PUF_CUDA_WAIT=block. Freshcleancomparison194195.55→200502.87SPS(+3.2479%). Earlywindow−0.126% neutral; depthprototype~+0.49%,nearcontrolspread. Savedbatch113updatesexact; live2097152steps/904updates exact, including allrolloutbuffers/RNN/master/momentum/update/checkpoint.16protectedfiles stillunchanged (integrity_116min.json).

## Running / queued — verify live processes before acting

1. Unifiedexec session99135: next_screens_retry.py, currently running `python campaign.py AFFINITY_SCREEN.json` (campaignPID2898888). Root ACTIVE.json identifies currentbenchmark. Six sequential fullscore runs,80epochs/start64, immutable binaries/affinity_v12. First completedcontrol199347SPS; affinity_all200052; affinity_submit198983. affinity_all_reduce was live when this handoff was written, then timing_stride16, then finalcontrol. All useblock waits and same2048games/24workers/4buffers/128horizon/4096minibatch. Do notjudge smallgains before trailingcontrol.

2. Unifiedexec session5314: workspace_completion_screens.py. Confirmed waiting behind that exact campaignPID, checks sixsuccessfulresultartifacts and GPUidle before proceeding. Then builds completion_workspace_v13, runs64-case callback/lifecycle smoke, compiles native_completion harness, runs8 restoredCPUtrials, then WORKSPACE_SCREEN.json GPUtests. Allserialized. Do notlaunch competingbuilds/profiles/timings. Ifearliercampaignfails, driverasserts/stops ratherthancontinuing silently.

Previoussession33348 COHORT_RECHECK2 completed normally. Previousdriver61304 failed at native inherited-affinity assertion (detailsbelow); it isterminal, notstillrunning. Nootherheavyworkwaslaunched.

## Completed results this turn

COHORT_RECHECK2: blockingcontrols199448.95SPS. Identityforward+0.0165%(neutral). Two-buffer cohorts wholehorizon−5.017%, eightsteps−9.563%. With embeddingreductions:−2.924%/−8.730%. Rejectgroups and parkidentitywarp. All80observationboundarychecks and frozenactors match acrosssevenruns (COHORT_VALIDATION.json). SummaryCOHORT_SUMMARY.json. Groupingstillloses evenaftercheaperGPUwork; nofurtherupdatechecks forlosers.

Native boundedgenerationpriority:24pinnedworkers,2048games,512ordinarydecisions each restoredtrial, unchangedcurrentengine. controls223537.1SPS; lead1+0.093%,2−0.028%,4−0.038%,8+0.239%. Allendpoints/worldturnsmatch. Rejectneutral, nofullpipeline/longproof. native_bounded/summary.json, runs/lead2048_screen_v2. Older productive-scan quotas werealso tried under compact-state/focus_quota_20261009; do notrepeat anotherarbitraryquota withoutnew evidence.

TLS investigation closed: engine alreadycompiles NH_TLS_INITIAL_EXEC; no TLScandidate.

## New isolated candidates / source state

v12 binaries/affinity_v12 and snapshots/affinity_v12 archive:
- PUF_CPU_AFFINITY=1: workerIDs0..7 pin toPcore logical0,2,...14; IDs8..23 pinE16..31; submitters1,3,5,7; main9. Mode2 pinsonlysubmitters/main. Sameworker/envcounts. Actual /proc threadmasks verified during affinity_all. Experimental machine-specificplacement, no defaultchange.
- PUF_BUFFER_LEAD=1/2/4/8: sortedreadybufferpriority allowsboundedgenerationlead, retainingreaderleases/counters. Native screen neutral.48synthetic callbacks/lifecyclecases passed.
- PUF_TIMING_STRIDE=16: CUDAmodel/copytiming sampled1/16steps withrotatingphase; scalesdiagnosticmodel/copyestimates. Outerbatch/environmentclocksremainexact; samecompute/actions/streamsyncs. Separateprofiling-overheadcandidate, notfastermodelmath. Fulltestpendingin runningcampaign.
- Combined4epoch smoke (affinity1,lead4,timing16,block) matchesfirst3referenceboundaries andfrozenactor. scheduling_v12_smoke.

source/ NOW additionallycontains pendingv13changes (not partof v12timingbinary):
- PUF_POOL_DONE_BATCH: ep_claim publishesits completedcallbackcount onceattheend ratherthanreleaseRMWpergame. Sameclaimorder; readerleasesandacquire/releasedonepredicatepreserved; lastcompletioncondsignalpreserved. Modes10=batch,11=batch+sleep,12=batch+lead4 in native_completion. Suspectedceilingmodest; musttime.64-case completion_pool_smoke.cpp prepared.
- PUF_CUBLAS_WS_MIB: private streamworkspace4default,8/16/32/64candidates. Sameoperands/compute/mathmode, streamownershippreserved. Allocate max(regularworkspace, optionalrecLtworkspace). GPUtimegate first. New scopeisregulartraining/parallelMuon, unlikeprevious32MiBrec-inference-onlytest. ExpectextraVRAM; anyusefulwinner needsrounding/stabilityvalidation, notassumedexactness.
Scripts prepare_affinity.py, prepare_bounded_pool.py, prepare_timing_sample.py, prepare_completion_batch.py, prepare_workspace_size.py documentchanges. Do notrerunpreparations (non-idempotent assertions/directories).

## Failure and harness correction

Firstnative_bounded run lead2048_screen aborted beforefirsttrial: ep_pin_cpu asserted targetCPUwasintheworker's inherited pthreadmask. Snapshot'sparent/submittersintentionallypin themselves, sothechildworker mustwiden thatinheritedmask, as oldCPU_PIN codealwaysdid. Corrected native_bounded helperrelies on pthread_setaffinity_np success, matchingpriorsemantics. Fulltrainerhelperunchanged andpassedits smoke. Failedartifactretained; retrylabel_v2 successful. Noenginebug/dynamicsmismatch. native_completion usesoriginaldirectCPU_PIN code toavoidthischeck.

Initial prepare_timing_sample.py assertedthatH2Dtimingsweren'tscaled, butexistingdormantcodealready scaledthem. Scriptfailedbeforewrite; fixedassertion andpreparedsuccessfully. Nocandidate timed frompartialedit.

native_bounded/SOURCE.json and native_completion/SOURCE.json storeharnesssourcehashes; command.json ineachrun hasbinary/libraryhash. Firstfailednativebinarywasrebuilt withcorrectedcheck; firsthash/sourcepreparations remainrecorded. FullGPUbinariesand snapshotsimmutable.

## Next actions

Poll99135/ACTIVE.json, then analyze AFFINITY_SCREEN withfreshtrailingcontrol, boundaries/frozenactors, tails/memory. Dropnulls. Ifawinner emerges, reverse-orderrepeat, secondarydepth andliveupdatechecks, thenpreparecleanminimalpatch; donotpromoteallprototype source.

Poll5314 afteraffinitycampaignfinishes. Reviewnativecompletioncountertiming; onlyescalateusefulrepeatablewins. ReviewWORKSPACE_SCREEN GPUtimings; dropclearloosers beforeprotractedcorrectnesswork. Largerworkspacecanchangealgorithm/roundingandVRAM; quantifyifuseful. Keepchatupdatesroughlyeveryminute. Allheavyworkserialized.

## Existing harness and old findings

run.py full usesrealinference/fullPPOwithfrozenactor andrecordedactions; --update --env=PUF_LIVE_AFTER_WARM=1 performsactualsampledupdates (runnerremovesreplayinput). time/proof load mature_batch.bin;113PPOupdates,2warmups fortiming. ProofrawgradfilecontainsFIRST AND LASTminibatches. --workload=depth secondary. build.py archives sourcehashes andimmutablebinary, refusesGPUbusy. campaign.py loadsjoblistonce; editingitsJSONdoesnotalteranexistingqueue.

Currentbaselineengine is movement_object_presence_pgo_followthrough/build, librarySHA b4bb7be577622a9abb12163b5b91ec4d42ca472cf69909773692e1c24c839c05. Fixedworkload2048 repeats512 recordedstreams4times; do notclaim2048independentgames. Noenginechangesinthisturn.

Earlierparkedideas andproofs remaininLEDGER.md/STATUS.md/HANDOFF_0005_archive.md: embeddingGPU+5.14%butfull+0.06%(tailabsorbswin); localintegerreduction113updatesexact, FP32identity/kindreductionscause laterroundingdrift; fusedencoder/scantile/outplaceMuonisolatedwinsallfullneutral; fair/fixedprioritypoolrejected; pooltail-sleep/exhausted-claimreadsneutral. Donotblindlyrepeat. BroaderCPUgapaccounting under compact-state/full_gap_20261009 explainsdistributedlocality; nohardwarePMUcountersavailable and noestablishedsinglehidden2xfix.
