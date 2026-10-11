# Active goal handoff, 2026-10-10 00:05 UTC

The24-hour goal remainsactive, deadline2026-10-10 22:30:39UTC. Read OBJECTIVE.txt/originalattachedfile; do not create anothergoal or concludeearly. Previousgoalturn made concreteprogress (retainedwin, proofs, screens).

## Retained

RETAINED.json v1: clean_wait/source, clean_wait/wait.patch (sixlines), binaries/clean_wait (fd37cca70fb8392ae4f77be8c2a2565d5be87650004d05f7d90493e461d7d392), PUF_CUDA_WAIT=block. Freshcleancomparison194195.55→200502.87SPS (+3.2479%). Earlywindow207575→207312 (-0.126%,neutral). Secondarydepthprototype~+0.49%,nearcontrolspread. Savedbatch113updatesexact; live2,097,152steps/904updates exact (allrolloutbuffers/recurrentstates/master/momentum/update/finalcheckpoint). Productionunchanged (16protectedfilechecks pass in integrity_94min.json).

## Running now

Unifiedexec session33348: python campaign.py COHORT_RECHECK2.json. Verify ACTIVE.json PID/processbeforeacting. Started00:04UTC; sevenfullmaturetests (~12min total). Same15.55M,2048envs,4logicalbuffers of512, horizon128,113PPOupdates/batch,24CPUworkers. All usev11+blockingwaits. Order:
1.cohort_full_base_a
2.identity_full (NH_IDENTITY_WARP=1)
3.cohort_two128
4.cohort_two8
5.cohort_two128_reduce (NH_EMBED_REDUCE=7)
6.cohort_two8_reduce (NH_EMBED_REDUCE=7)
7.cohort_full_base_b
Cohorts usePUF_COHORT_BUFFERS=2,STEPS128or8. Newhypothesis: currentGPUisfastenoughthatrolloutwaitisexposed; reducedactivegameworking-setmightnowpay. Actorweightsaresnapshottedbeforeallbuffersarereleased; nochangingpolicyversionmidcohort. Short4epochsmokesmatchfirst3engineboundaries. Donotcompile/profile/runheavyCPUworkduringtimings.

## Latest experiments

Embeddingbackward flags1identity,2kind,4localsharedfixedpoint. CombinedGPU1153→1097ms (+5.14%) but full199373→199493 (+0.060%,null), rollouttail43→97ms absorbsGPUgain. Parkstandalone; cheapGPUarmonlyreusedincohortscreenbecausecriticalpathmaychange. Localflag4alone113updatesbitexact. OtherFP32tree reductions mathematicallysame but roundingdiffers: firstgradientexact; after113updatesmasterrelL2=3.89e-5,params2.49e-4,momentum0.1315,lastgradient0.2858. Rawgradientfile containsFIRST AND LAST minibatches, notfirsttwo. Furthernumericstabilityworkonlyifcombinedfulltimingwins.

Identityforward NH_IDENTITY_WARP=1: onewarp/game writes40features contiguously. Fullinference396.979→388.104us(+2.29%),760832-byteoutputexact; GPUtraining1150.501→1149.828ms(neutral). Fullidentityscreenincludedabove.

Pool PUF_POOL_SLEEP / PUF_POOL_CHECK_CLAIM: synthetic32count/lifecyclecasespass; shortreplaymatches. NewnativeCPU-onlysnapshotharnessunder native_pool (noCUDAforking) runs8restored2048×512trialsin88sec. Sleep+0.013%,read-before-claim-0.037%,both+0.066%: allneutral,reject. Samecurrentengine/nethack.hasfullpipeline; allendpoints/worldturnsmatch. Nativejobfinished; noCPUjobshouldremain.

Fairgenerationpool: full-0.20%,balancedbuffersbutnothroughputgain,reject. Gram-squaretransposedmappingGPU-0.37%,reject. Larger32MiBinferenceworkspaceonlyfirstheuristictested(neutral);candidatecount5butidentitiesnotprovenidenticalto4MiB,so notexhaustivelyrejected.

## Source / harness

Current prototype source/ includesallruntimegatedcandidates. Immutablev11binary identity_warp_v11 (db423c541339a7e4b6af73ca2cbaf4b00095a420ba7cccf40bfe8dc4c594e516); snapshots/v11 andbuildjsonretainexactinputs. Nativepoolsourcepreparedseparately.
run.py livevalidation: PUF_LIVE_AFTER_WARM now removesPUF_ACTION_REPLAY toavoidareplay-only duplicate-copyassertion. Firstlivebaselineclean_live_basefailedthatassertion; retry_v2bothpass. Thisisaharnessfix, notretrainingcrash; recordedbenchmarksunchanged.
compare_state.py comparesBF16/F32states, finitechecks, relativeL2. build_clean_wait.py cleanminimalbinary. monitor_cpu_window.py finished:mainCPU99.4%→12.0% duringmatchinglateepochs, aggregate2833→2708%. NoCPUworkreductionclaimfromunmatchedold12seccaptures.

## Next

Pollsession33348, inspecteachresult (hashes/frozenactors/SPS/tails), summarizefreshcontrols. Dropnull/losingarms. Ifcohortoridentitywins, repeatreverseorder, testsecondaryworkload and actualupdates/liveactions before retention. Retainonlycleanminimalcombinedchanges, measureagainstoriginalfixedbaseline directly. Continueprofilingandtestingthroughdeadline; currentvalidatednetgain3.25%, target278kSPSnotmet.

Allmetadata/commands/sourcehashes/resultsareinLEDGER.md,STATUS.md,RETAINED.jsonand runs/. No push/PR/default/protectedsourcechange. ~22.4hoursremain.
