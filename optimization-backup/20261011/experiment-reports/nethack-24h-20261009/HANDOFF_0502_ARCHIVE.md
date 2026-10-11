# Active NetHack24-hour throughput goal

Updated 2026-10-10T05:02:07.349998+00:00. ReadOBJECTIVE.txt and original attachment. Start2026-10-09 22:30:39UTC; deadline2026-10-10 22:30:39UTC. Target277778SPS with15.55Mscorepolicy. Keep active untildeadline.

## Process state

**No heavy process is live.** nvidia-smi checked empty. Terminal handles:71950,50662,17472,72574,27706(firstsmokefailed),71480,6151,58767,39867,86057,93661. Do not restart these. Current isolatedsource/binary **weight_cast_v29**, SHAae68e681cb1afbb8b20c496da49189dafce40ee5eeb9fd2e108f903bea9ac916. All newprototypes defaultoff. No production changes.

## Established evidence

COMBINED_DIRECT_SUMMARY.json: baseline194071.687→combined32workers210221.722SPS,+8.321685%. Fixed24workers201632.615,+3.895946%. Drift−.090515%,80observations/actor proofs exact. Memory8840→8290MiB. Do not add isolated gains. GPUcombination changes rounding; no learning-equivalence claim.

DEPTH_COMBO_CONFIRM_SUMMARY.json: cleanblocking32 mean382948.892→397736.096,+3.8614%,drift+.1507%,80proofs exact. COMBINED_DEPTH_VALIDATION.json: two8epoch/2,097,152step/904actualupdate live runs finite. Finalmaster relativeL2.024706,momentum2.8083,updates1.4012 after divergent live actions. Short stability only. Smaller depth architecture is not theheadline15.55M model. PRIORITY_CANDIDATE.json updated.

RETAINED.json unchanged: cleanblockingCUDAhostwait exact113savedbatch/904liveupdates. NET32_CONFIRM_SUMMARY.json clean24→32stack+5.20%. GPUcombination corrected sincev20; FUSION_DISPATCH_AUDIT.md explains prior erasedtrainingflag. CORRECTED_COMBO_PROOF_SUMMARY.json has actual113update rounding differences. PRIORITY_LIVE_PROOF.json confirms priority on samefastGPUstack finalstateexact904updates. Prioritycleanstack−.401%. Immutablefastbinary inference_priority_v22 SHA76bcd084541e9ef9de2ff5a61eb032ea6f299bdfd9ddfd62c766450bbe215012.

## Newly closed mechanisms

- TRAINING_DW_GPU_SUMMARY.json: synthetic recurrentdW algorithmID30 +9.7%, actualsavedbatchGPU969.551→965.279ms,+.443%,drift+.182%. Parked. Actual-header graphsmoke2seeds6.29Moutputs finite/relativeL2.002123. NH_TRAIN_DW_LT=1 matches onlyBF16/TN/3072x1024x4096/alpha1/beta0,ID30/workspace0 asserted. Newtrain_dw_lt.cuh is inbuildsnapshotlist. v27SHA07bdccb7638a11624dee5ed37f893fe4a2b68cf5b5e11d1412131f8e433bc463.
- MSG_SHARDS_GPU_SUMMARY.json:4shards+.128%,8shards−.099%.64actual-kernel cases exact16,777,216integer/BF16values. NH_MSG_SHARDS defaults1, allocation expands onlywhenon. v28SHAe1fc3cc3f6610a02dd732747d7066ac3c6edf301cd0a4b2db9d1fe684fb11ffa. Parked.
- WEIGHT_CAST_GPU_SUMMARY.json:globalupdate/cast+.451%,per-matrixstore/apply/cast+.074%,control968.102ms/drift+.127%. Firstper-matrixsmoke found compilercontraction difference fromliteral1 vsdynamicwd_scale. Restoredoriginalexpression:20cases/12,849,236update/master/parametertriples exact. Failedartifacts *.first, diagnosticlog2, correctedlog3/WEIGHT_CAST_SMOKE.json. PUF_FUSED_WEIGHT_CAST=1global/2per-matrix; mode2 assertsnoalternatefused/batchedMuon. Parked; no extendedupdateproof for timinglosers.
- GRAM_TRIANGLE_SCREEN.json: compute blocktriangle throughcuBLASbatched thenmirror. All47.8–50.1us vscontrols43.15/39.54; drift−8.37% but allcandidatesworsethanbothcontrols. Different hypothesis from earlier independentmatrixbatching:actuallylessarithmetic. Parked.
- GRAM_TRITON_SCREEN.json:customhalfGram32/64/128tiles,4/8warps,3/5stages. Best40.35us vscontrol39.99mean; alloutputs matchcuBLASonthissample. No usefulgain.
- GRAM_TRITON_SPLIT.json:2/4/8Ksplits for moreparallelism. Longerwarmupcontrol39.702us/drift+.198%,best46.315us(−14.28%),others55–82us. IncludesFP32partials+mirror. Allfinite,relativeL2~.000205. Closeapproach; NOtrainerintegration. Tritoninstalled. gram_reference.so suppliesprivate4MiBcuBLASreference.
- PROJECTION_GEMM_SCREEN_SUMMARY.json:forward/dX/dW actual1698-wideprojection algorithms neutral,best+.266/+.190/+.121%,control drift+.304/+.209/−.023%. No integration. MODEL_DIMENSIONS.json and resolververify NH_CONCAT1698 withactiveflags. Initialresolverissuescaught/fixed; nearby1410sourcecommentstale. Matchesearliermatrix_costs.json id18=1024x1698.

## Current profile and next action

PRIORITY32_PROFILE.md; runs/priority32_profile_node/profile.json,contention.json,kernels.csv.226PPOupdates/1024inferences/2matureepochs. Inferencespan.9014msduringPPO vs.3824without; summedkernels.7554/.3726. Beforepriorityspan1.6915/.3901; observationalcross-tracecomparison, notcausalwallshares. CPUenv7.836/7.337ms,pooltail~2.17ms. Weightupdate154us,cast105us,messagebwd138us; testedfusion/shardingclosedabove. NsightheavilyperturbsSPS; don'tquoteprofiled66kSPSasthroughput.

Plausible NEXT bounded screen: physicalpadding of1698-wideprojection operands toalignedstrides, INCLUDING packing/unpacking. Irregularstride picks align2kernels. Logicalparametercount/checkpoints/modelstayunchanged. First syntheticforward/dX/dW withmovementcost againstprivate4MiBcuBLAS; onlyintegrateifuseful. Noimplementationyet, noassumedwin. Orfollowothercriticalpathevidence. Do not repeatrejectedGram/batching/scheduler ideas withoutnewhypothesis.

## Harness and constraints

Fastenv inPRIORITY_CANDIDATE.json. Fixed2048env/4buffers/H128/batch262144/mb4096/113updates.512unique recordedtrajectoriesrepeated4xlimitation. run.py/campaign.py/build.py/full_summary.py/summarize.py/compare_state.py. Build~7s,GPUtime~9s,full80score~110s/depth~58s. proof113actualupdates;livefull8/start1/update/PUF_LIVE_AFTER_WARM=1. Snapshotallnewheaders. Serializeheavywork/builds; stoponlyverifiedPIDs. No defaults/commits/pushes/PRs.

16protectedfiles unchanged in integrity_390min.json, checked_at authoritative. Currentturnprogress; goalunfinished,~17.5hoursremaining.
