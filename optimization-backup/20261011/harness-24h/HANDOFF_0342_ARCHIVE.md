# Active NetHack 24-hour goal — 2026-10-10 03:42 UTC

Read /root/.codex/attachments/45e8ae2b-9569-441d-b536-ceced1640e37/pasted-text-1.txt. Start2026-10-09 22:30:39UTC, deadline2026-10-10 22:30:39UTC. Keepexistinggoalactive;donotcreateanotherorcompleteearly. Target277778SPS onexisting15.55M mature-scorefullpipeline.

## Live work — poll first

Unifiedexecsession24401: python campaign.py PRIORITY_CONFIRM.json. Four80epochruns: priority_confirm_priority_a, base_a, base_b, priority_b. Openingcandidateverifiedstarted. Immutablebinaryinference_priority_v22 SHA76bcd084541e9ef9de2ff5a61eb032ea6f299bdfd9ddfd62c766450bbe215012. Sourcehaschangedforunbuiltdiagnostic;donotrebuildv22.

Afterterminal: python full_summary.py PRIORITY_CONFIRM.results.json. If repeatedprioritygainclears1%withstablecontrols, runPRIORITY_LIVE.json (8epochs/2097152liveactions/904actualupdatesperarm;fastcombobaselinevspriority), compareallstatefiles,rollouthashes,andcheckpoints exactly. ThenCORRECTED_COMBO_PROOF.json pairs113savedmaturebatchupdates forplainvsactualcorrectedGPUcombination, quantifyingfloatingdifferences. Do notsubstituteolderboth-fusionproof. Ifspeedrepeatfails,parkwithoutfurtherlongvalidation.

Ifprioritypasses: assessapplicabilityonclean32workerstack separately; maincleanbaselinehaslittlerollouttailsoitmaynotbenefit. OverallGPUcombo remainsnumericalexplorationuntilcorrectedactualupdates/stabilitychecked. Keepconditionalcandidate separatefromretaineddefaultclaim.

## Completed this continuation

FOCUS_FAST32_SUMMARY.json: native+7.09%focusgain failsfullpipeline:206060.7vs206511.9SPS,−0.218%,controls0.273%drift. All80proofsexact. Parkfocus.

FINISH_SLEEP_FULL_SUMMARY.json: cleanlybracketedfast32controls206379.2,drift0.0566%;collectoridlesleep208051.0(+0.810%);collector+newmainfinishsleep206845.4(+0.226%). All80proofsexact. Below1%gate,park. FINISH_SLEEP.patch, immutablefinish_sleep_v21 SHAbd756069b85472192d7fd5a0d293f158d2ce625346864b04f80699038efbc9f8. Noextraexpensivelosertrainingchecks.

FAST32_PROFILE.json terminal. FreshcorrectedfastGPU32workertrace captures2matureepochs,226PPOupdates/1024inferencegraphs.67commonobservationboundariesexact;final68thepochhasnoprefetch,properlyexcluded. analyze_contention.py includesexistinganalyze_profile.py andpartitionsNVTX/kernelgraphspansbyoverlapwithPPO. Inferencespan1.6915mswithPPO(n767)vs0.3901mswithout(n255);summedkernel0.7152vs0.3781ms. CPUenv7.31vs7.34ms. Pooltail1.93msoverall. Observationalandtrace-perturbed,notspeedclaim. Artifactsruns/fast32_profile_node/{profile,contention}.json.

GPU_CONTENTION_FULL_SUMMARY.json: fast32controls206754.287SPS,drift0.1313%;higherinferencepriority210021.521,+1.58025%;twoMuonlanes206696.702,−0.02785%,park. Earlytwolanes232023vs~238389slower. All80obsproofs/actors/countsmatch. Prioritytail161.8vs188.1ms. Unprofiledeventmodel195.61→109.24ms/envwall879.67→953.77ms/copy~69ms. Envwallincludespoolqueueing,notengineCPUcost. FAST32_CONTENTION.md explains. Actorpriorityreadbacks−5all4streams vsnormal0. CUDAheadersconfirmgraphlaunchpriorityappliesunlessUseNodePriority;oursflags0.

## Prepared next diagnostic — not yet built

prepare_pool_timing.py alreadyrun;NON-IDEMPOTENT,donotrerunblind. POOL_TIMING.patch addsoptionalPUF_POOL_TIMING inisolatedenv_pool.h/pufferl.cu. EPTiming64Blinealignedperbuffer,solewriterduringep_run;mainreads/resetsafterallcollectorswaiting. Fourpairsofwall+submitterCPUclocks per512gamepoolcall,publication/claim,tailandreader-drain. Defaultoff. Noengine/action/model/schedulingsemanticchanges.

Sourcecurrentincludesdiagnosticafterv22snapshot. Buildpython build.py pool_timing_v23 -DPUF_MUON_OUTPLACE onlywhenGPUidleandprioritygatesdone. Runshortsmokecomparingoff/ontobaselineobservationhashes;thenPOOL_TIMING_FULL.json 80epochsoff/on/off toquantifyoverheadandunprofiledwaitbudget. Do notproposecost-orderingschedulerunlesswaitbudgetisreal;Nsighttailmaybeanartifact.

## Retained and historical constraints

RETAINED.jsonv1 unchanged: clean_wait,PUF_CUDA_WAIT=block,~2.5–3.2%matureimplementationgain,113savedupdatesand904liveupdatesexact. NET32_CONFIRM_SUMMARY.json directlybaseline24→cleanblock32:204349vs194245SPS,+5.20%. Workerconfigurationseparateandliveexact. No production/defaultchanges.

Critical FUSION_DISPATCH_AUDIT.md: oldv2..v19mode1fusedinferenceANDPPO, mode2neither due trainingflagassignedbeforezero-init. Fixedv20+:mode1inferenceonlyand113PPOupdatesexactvsplain. Oldcombo+1.03/+1.13%fulland13.4%firstgradientdifferenceapplytoboth-pathfusion;notactualnewcombo. Correctedfusionindividually+0.111/+0.222%full,null. ActorL2+0.065/+0.124%null.

Fastcomboenv: PUF_CUDA_WAIT=block,PUF_POOL_WORKERS32,PUF_OUTPLACE1/RANK1,PUF_SCAN_ROW3/TILE4,NH_EMBED_REDUCE7,NH_IDENTITY_WARP1,NH_FUSED_BR1,NH_PASS_FAST3,NH_SFEAT_FAST1. Config2048env/4buffers/H128/batch262144/mb4096/113updates;scoremodel1024x4/15552136params;frozenactor,replay512uniquegamesrepeated4x. Nativewarm8320/measure1920alignsfull64..78.

ReadLEDGER.mdandoldercompact-stateREPORT.md beforehypothesizingalready-testedlayout/prefetch/workspace/overlapchanges. Manyclosedmechanisms. Protected16filesunchangedinintegrity_303min.json. Serializeheavywork,stoponlyverifiedPIDs,updatesroughlyonce/minute. Terminalhandles88102,49398,72673,79546,85287,22428,32366,45254;donotpollagain. Current24401islive.
