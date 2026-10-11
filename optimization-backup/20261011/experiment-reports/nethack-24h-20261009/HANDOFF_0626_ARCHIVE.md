# Active goal — 2026-10-10T06:26:13.310434+00:00

Read original attachment/objective before continuing. Start 2026-10-09 22:30:39 UTC, deadline 2026-10-10 22:30:39 UTC. Remains ACTIVE. No new goal/commits/pushes/PRs/default changes/subagents. Serialize heavy work; minute chat updates; verified PIDs only. Previous user prompt-only turn was no progress; this continuation made concrete progress with completed timing comparisons, new diagnostic evidence and a CPU candidate.

## Live job — poll first

Unified exec session **59409**, `python screen_weight_cache.py 2048`, launched 06:24:44 UTC. Four sequential native restored-window comparisons: base_a, candidate_a, candidate_b, base_b;2048env/32unpinned workers;warm8192;two512-decision windows/run. Expected total~3min. Uses original current engine SOURCE compiled fresh ordinaryLTO for baseline and candidate. Results `weight_cache/SCREEN_2048.json` and pending `_SUMMARY.json`; each native run under `native_pool/runs/weight_cache_2048_*`. Do not launch another heavy job until terminal. Check actual process if session polling expires.

All earlier sessions terminal:45602(envpages),56659/93970(emptydiagnostic),54292/25669/59612(emptycachebuild/check/screen),11191(weightcensus),65452(weighttrace),20607(epochcensus),84743/20001/18793(weightcachebuild/check/512screen).

## Best full training unchanged

COMBINED_DIRECT_SUMMARY:194071.687->210221.722SPS,+8.322%INCLUDING24->32workers;fixed24 +3.896%. Memory8840->8290MiB. 80replay/frozenactor/countproofs exact. CombinedGPUroundingchanges, nolearningequivalenceclaim. Secondary4.31Mdepthmodel+3.861%repeat;shortlive stability finite but trajectories/updates diverge. Exact cleanwait variant andconditionalprioritydetails in HANDOFF_0529_ARCHIVE.md and HANDOFF_0624_ARCHIVE.md.

Fast env: PUF_CUDA_WAIT=block,PUF_POOL_WORKERS=32,PUF_OUTPLACE=1,PUF_OUTPLACE_RANK=1,PUF_SCAN_ROW=3,PUF_SCAN_TILE=4,NH_EMBED_REDUCE=7,NH_IDENTITY_WARP=1,NH_FUSED_BR=1,NH_PASS_FAST=3,NH_SFEAT_FAST=1,PUF_INFER_PRIORITY=1. OthernewflagsOFF;removePUF_ROLLOUT_DETAILforheadline.
Current trainer experimental source/binary env_pages_v36;SHA1d626672950bd3e3a4b9a4fe49c1c6d5fb06562b699271e347d7e3ba1b4f5149. EnginecandidateISNOTintegratedintoit;dynamicLD_LIBRARY_PATHoverrideavailableinrun.py --env for latergates. Defaultengine is /puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/build.

## New promising lead — inventory weight

1. `weight_repeat_study/COUNTS.json`:1,048,576 maturepolicydecisions,25,012,446 inv_weight calls,1,027,124,291 inventoryentries.99.21%consecutiveweighttotalsidentical. Originalcomputationsunchanged. Existingupdate_inventorynotification+headpointer+throwsrocksvaliditywouldhit24,783,173callsbutmiss9,203totalchanges. Thusnotification-onlycacheunsafe.
2. `weight_change_trace/SUMMARY.json`:576 first16/worker sampled mismatch stacks.486observedbyencumber_msg/moveloop;90byeating/statuscallbacks. Theseareobservationsites,NOTexactmutationstacks/populationfrequencies. Source recalc_wt(src/eat.c~309)changesfoodowtwithoutnotification.
3. `weight_epoch_study/COUNTS.json`:addinvalidationsafterrecalc_wt andevery nle_step after nh_cur binding.23,366,924hits/25,012,446calls(93.421%),0wrongconsecutivesumsinmaturewindow. Notcompletecoverageproof.
4. `prepare_weight_cache.py` creates `weight_cache/source`, `build`, `verify`. 24B appendedpernh_ctx:headpointer,valid,sum,rocks. Cacheonlyrawtrueinternalcarriedweightsum. `weight_cap()` still executes everycall withoriginalsideeffects;publicappearance-based `nle_weight` unchanged. Invalidateonupdate_inventory,recalc_wt(afterstore),nle_step(aftercontextbinding). Guardheadpointer+throws_rocksformability.
5. NLE_WEIGHT_VERIFY recomputeseveryoriginalweightwalkandpanicsifcachedhitdiffers. Bothverifyandfastpassall5golden/fuzz/status/interleaved/shuffledsuites(10total;52.7sec). Verifieralsoexecutes512gameswarm8192+mature2048withunchangedendstate/turncount. CurrentmatchesdoNOTproveallmutationcoverage.
6. `weight_cache/SCREEN_512_SUMMARY.json`:base281507.49,candidate287323.36SPS,+2.06597%;control drift−.57797%.Allcandidatewindows286390–287805abovebothcontrols280441–282380,butneedrepeat/driftqualification. All8nativewindowendpoints/turncountsidentical. Advance2048screen;NOTretained.
7. `weight_cache/CANDIDATE.json`:baselineSHA8bbe38bf248e60f88f884ad9d56dabc6990ec753d925bc43a893e77703713610,candidatebcb2c33c92970be4132cf940d7a5e0bed36b46ef43859b6418e11d7369fe9a0c,verify1af0e17846189f4245aee0b853f58b1f4d40369faac6897e607f85864e61bae3.

Nextif2048useful:broaderstaticinvalidationaudit(thesetriggersareprovisional),fullsaved-decisioncorpus+depth+verification,matchedfreshPGO(baseandcandidateownfeedbackfromsameinputs),thenfullmaturepipelineinterleavedcontrols. RelevantPGOhelpers `build_current_workload_pgo.py` and old movement_followthrough_20261009 build scripts;do NOTreuseincompatiblePGOcounts. If2048loses/noheadroom,parkwithoutlongvalidation.

Potentialinvalidationrisksnotsettled:temporaryquantity/owtchanges,containerweightupdates,inventorymerges/deletion beforeUI notification. Readsrc/pickup.c carry_count~1275:temporaryobjquantityupdates are restored beforemessages;its max_capacitycall precedesthem,so notautomaticallyaviolation. Mustauditactualreadordering,notassumebasedonassignments. No productioncachedeployed.

## Closed this turn

ENV_PAGES_FULL_SUMMARY:control210353.732SPS,aligned-0.201%,huge+.109%,drift-.346%. ENV_PAGES_MAPPING confirms0vs337920KiBAnonHugePages(full330MiB);RSS+3776KiB. All80replayproofs/actor/countsexact. Park,noextendedupdates. ThiswaswrapperarraynotenginecontextTHP.

`floor_empty_study/COUNTS.json`:39,951,908initialfloorqueries;25.75%empty;64slotmemo couldanswer19.81%ofallinitialqueries,noneoveremptyfloorindex. LengthweightedhitmetricNOTactualworkfraction. `floor_empty_candidate` adds1KiB/contextandgeneration-keyednegativecache;682201independentquerycomparisonsincludingrepeats/mutations/overflow/wrapand5quickgatespass. SCREEN_512_SUMMARY281557->281362SPS,-.069%,drift+.101%,8nativeendpointsexact. Park,noPGO/fullcorpus/trainingtest.

## Current CPU evidence and previous closed GPU work

CURRENT_CPU32_PROFILE.txt/native_pool/runs/current_cpu32_profile:20381samples;m_move18.7%,sched_yield17.5%,mfndpos10.1%,pack_obs4.2%,newsym3.8%,fill_obs3.6%,encumber_msg2.1%. Flatsharesarenotwallattribution;nativeharnesswrapperisolderCPUcopy,enginecurrentPGO.
Previousentityinference+17.9%isolatedconverted+.62%full;trainingentity+2.97%GPUconverted+.32%full;poolbackward+.68%GPU. Parked. Manylayout/prefetch/schedulerideasalreadyclosed;readLEDGERandoldREPORTbeforetryingagain.

## Integrity/harness

16protectedfilesunchanged in integrity_475min.json, checked_at timestampauthoritative. Source mainrepohaspreexistingdrone/depth/articleuntrackedchanges;untouched. Allnewworkinexperimentdirectory. Currentenginebaseline `floor_empty_base` freshlybuiltfrom retainedPGOsource WITHOUTPGOforpairedscreen.
Harness run.py/campaign.py/build.py unchangedsemantics. Full fixed2048env/4buffers/H128/batch262144/mb4096/113updates;512uniqueactionstreamsrepeated4xlimitation. Native snapshot_test.run canoverrideengine/workers/pin/binary. DiagnosticprogramSPSexcludedfromperformanceclaims. Build trainer `python build.py LABEL -DPUF_MUON_OUTPLACE -lcuda`.
