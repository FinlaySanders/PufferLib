# Active NetHack 24-hour throughput goal — 2026-10-10 02:06 UTC

Read `/root/.codex/attachments/45e8ae2b-9569-441d-b536-ceced1640e37/pasted-text-1.txt` before continuing. Start2026-10-09 22:30:39UTC, deadline2026-10-10 22:30:39UTC. Goal ACTIVE. Do not create another, pause, or complete early. Target277778SPS on15.55M mature-score full pipeline. Earlier user request for another goal prompt was answered; the explicit active-goal continuation then resumed this objective.

## Live job / immediate next steps

Unified exec **session6229**: `python campaign.py NET32_CONFIRM.json`.
The first run net32_base_a was verified alive just after02:06UTC throughACTIVE.jsonand/proc.
Jobs: originalbaseline24workers;cleanblocking24;cleanblocking32;originalbaseline24.
This directly measures the retained wait fix plus validated worker configuration against the fixed starting binary, without adding historical percentages. Same15.55M/2048games/horizon128/mb4096/113updates;80epochs,measure64–78. Inspect every80observationproofs/frozenactor andbatchsize; calculateearlywindow separately ifuseful. No heavybuild/profile/nativework duringcampaign. Poll6229 andverifyPID; do not restart on a quiet poll.

Aftercompletion, summarizeintoNET32_CONFIRM_SUMMARY.json. Keep implementation-only blocking gain separate from extra worker tuning. Clean32workers already passed2097152live steps/904updates byte-exact. If combined gain is useful, secondarydepth workload is the next representative check; its model/config is different and should be labelled. Do not prematurely complete the24hgoal.

Previous session8898 COHORT_ONE_COMBO.json is terminal:controlmean206243.041,candidate126748.185SPS (-38.544%).All80proofs match. COHORT_ONE_COMBO_SUMMARY.json records rejection. Lostbuffer overlap dominates; no furthercohort variants/longtrainingchecks withoutnew evidence.

Otherterminal sessions:65817(workerGPUcombos),85457(immutablefields),72313(workerliveproof),9116(sharednames),23634(nativeISA),42140(cohortsmoke). No other heavy job queued. NativeSTATUS idle.

## Retained implementation winner unchanged

RETAINED.jsonv1: cleanblockingCUDAhostwaits,6linepatch,+3.2479% maturefullSPS (194195.55→200502.87),~0.722Bsteps/hour. `clean_wait/`, `binaries/clean_wait`. Earlyneutral,depthroughlyneutral.113maturebatchupdates plus8livebatches/904updates/2097152steps exact includingrollouts,RNN,optimizer,weights. All80matureobsproofs exact. No production/default changes. Do not countconfiguration gains as retainedimplementation.

## Completed this turn

### CPU worker configuration — useful and live-exact

WORKER_FULL_SUMMARY.json:
24workercontrols199231.589SPS,drift0.0365%;28workers203725.001(+2.255%);32workers204374.666(+2.581%). Tail~43.7→9.02/2.56ms. All80proofs/frozenactor,batch262144,mb4096,113updates unchanged. Previousnative worker screen:28+2.154%,32+4.238%,20−2.409%.

WORKER_LIVE_PROOF.json:32workers onclean_wait/blocking matches existing24worker clean_live_block_v2 for2097152livepolicy steps/904actualupdates. initial/finalweights,allrollouthashes,RNN/optimizerstate/obsproofs byte-identical. Runtime18s, not a speed measurement. CONFIG_CANDIDATES.json updated. NET32_CONFIRM is now running to obtain direct clean combined throughput.

### GPU combinations with32workers — still modest end-to-end

WORKER_COMBO_SUMMARY.json:
32workerplaincontrols205112.600/203871.393,mean204491.996,drift−0.605%.
-4buffers+GPUcombo205853.009SPS,+0.666%;tail137.19ms vs2.22mscontrols.
-8buffers+GPUcombo207596.148SPS,+1.518%;tail109.67ms.
Allocation8840.1→8256.1/8412.1MiB. All80proofs/actors match. Numericalrounding changes remain; no live-equivalence claim forcombo. Notretained asimplementationwinner. FasterGPUgraph stillmainly createsrolloutwait.

### Three engine/compiler screens — parked

Each uses matchedordinaryGCC/LTO (nevercompareordinarycandidate againstPGOcontrol),24pinnedworkers,2048games, two512decisionrestoredtrials/case. Everycase endpointobs/turns/age matches. Firstpairgate+0.8%;allbelowgate, no longerproof/PGO/fulltrainingchecks spent.

1. `IMMUTABLE_OBJECT_READS.patch/.json`, `immutable_objects/`, `immutable_objects_screen.py`:287selectedimmutableitemfieldreads fromsharedbaseline,leavesappearance/discovery/material/probability/directionprivate. 214519.120→215718.995SPS,+0.559%. Smoke64seeds×2codecs128save/restorecycles,4522752fieldchecks,23318shuffledindices,hashff9c660fd292cbbf.
**Historical audit found this mechanism alreadytested assharedobjs/static_object_meta onolderengines incompact-state-20261008/REPORT.md, also~0.59%/null. Currentrecheckonlatestsource addedlittle. Closed acrosscampaigns;do not repeat.**
2. `SHARED_NAMES.patch/.json`, `shared_names/`, `prepare_shared_names.py`, `shared_names_screen.py`:sharedreadonlyname/descriptionreads;solemutablefruitname remainsprivate. Headeraccessors andhelperino_init.c. 214963.525→214493.705SPS,−0.219%. Smoke4870656checks,includingexactname/descriptionpointerequality andprivatefruitoverride;128roundtrips hashff9c660fd292cbbf. Distinctfromfieldprototype,also closed.
3. `NATIVE_ISA.json`, `native_isa/`, `native_isa_screen.py`:unchangedengine source compiled-march=native -mtune=native -ffp-contract=off,nofastmath. 214173.830→214302.210SPS,+0.060%. Sameinvariants/endpoints;closed.

Originalimmutablefield smoke source preserved inimmutable_objects/smoke.c. Sharedtemplateimmutable_objects_smoke.c.in waslaterextendedwithname/descriptorchecks. Dirscontaincommands,source/binaryhashes,buildlogs,smokes,rawnativecases. Existingfloor_boxes/controlordinarybuild reusedafterbytecheckingbase/source dirs. No priorbaselinefilesmodified.

## Key current configuration/artifacts

R=/puffertank/experiments/nethack-24h-20261009
Baselineengine `/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/build`.
Weights `/puffertank/pufferlib/resources/nethack/fixwt4b_s705.bin` SHA6541c5212ae4aae45e3c419bec2bf150883c457188117743d546cfb1d62a2718.
Actions `/puffertank/experiments/nethack-comprehensive-20261008/actions`.
2048gamesrepeat512distincttrajectories×4 (limitation). Default24workers+4submitters. NH_GRAD_PIPELINE3,CUDA_DEVICE_MAX_CONNECTIONS32,Muon4lanes. Model1024×4,15552136params. Frozenactor; alltrainingwork executes,optimizerwriteintoscratch. Noeasierpolicy/workload substitute.
Immutablecompletion_workspace_v13 binary is the currentgatedprototype. FullGPUcombo:
PUF_SCAN_ROW=3,PUF_SCAN_TILE=4,NH_EMBED_REDUCE=7,NH_IDENTITY_WARP=1,NH_FUSED_BR=1,PUF_OUTPLACE=1.
SomeFP32reductionorders differ; localinteger scatter alone provedexact. Combinedembedding113updates:masterrelL23.89e-5,BF16params2.49e-4,momentum0.1315,lastgrad0.2858. ComboisolatedGPU~13.2%gainbutlittlefullgain;don'tclaimidenticalupdates.

## Prior closed work / avoid repeats

OldHANDOFF archivedat handoff_archive/HANDOFF_before_20261010_0205.md. LEDGER.md/STATUS.md containhistory.
-8buffers×256 repeated+1.48/+1.21%;withGPUcombo+2.06/+2.05%at24workers. Separateconfiguration,no livevalidation.
-FusedsmallMuon v15<=64 isolatedGPU+2.49%,full+0.079%;~968MiBlessallocation;parked. NontrivialBF16rounding, no furtherlongvalidation.
-Registerprefetchedscans slower;currentworkloadPGO+.377%;floorboxes+.249%;affinity,largercuBLASworkspaces,boundedlead/fairpriority/completionbatch/sampledclocks neutral/slower.
-Historicalhugepages,contextslabs,broadprefetch/packing,sharedobjectmetadata tested. Readoldercompact-state REPORT.md before proposingthem again.
-HigherCUDAinferencepriority alreadytested in nethack-overlap-20261009/REPORT.md,+0.61%unconfirmed; no blind repeat. Otheroptimizer/encoder overlapsandbatchedGEMMs closed. Ifrevisiting, require concretechangedbottleneck andnewhypothesis.
-No PMUcounters (perf_event_paranoid4). Existingfullgap accounting atcompact-state-20261008/full_gap_20261009/REPORT.md:130.70→79.87usnormal/burst,98.2%insidepuf_step;read-onlyprewarmingcloses78.4%gapbutcostsmorethansaves. Notproof of specificcachelevel/TLBcause.

## Harness / safeguards

run.py full LABEL --binary=... --epochs=80 --start=64 --env=PUF_CUDA_WAIT=block
run.py time LABEL --binary=... --trials=4 ...
run.py full ... --epochs=8 --start=1 --update --env=PUF_LIVE_AFTER_WARM=1 forliveproof;thisremovesreplayinput.
Non4bufferscurrentlyallowedonlyfrozenfullscore;don'tremoveguardwithoutaudit.
4epochsmoketerminalboundaryrepeatspriorobs;compareto4epochruns/combo_smoke,not80epochterminal.
Native: python native_pool/snapshot_test.py LABEL 2048 '0:512,0:512' --engine BUILD
Nativeworkerexperiments optional --workers32 --unpin;default24/pinned unchanged.
16protectedproduction/priorfilesunchanged inintegrity_212min.json. No pushes/PRs/defaultchanges. StoponlyverifiedPIDs. Serializeheavybuilds/profiles/timings. Livecommentaryroughlyeveryminute. Keepgoalactiveuntildeadline;finalauditthenreportfullscope honestly.
