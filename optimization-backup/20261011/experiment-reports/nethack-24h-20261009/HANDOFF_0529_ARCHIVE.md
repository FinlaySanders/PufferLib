# Active goal — latest continuation 2026-10-10T05:29:35.519419+00:00

Original objective/deadline unchanged; read OBJECTIVE.txt and original attachment. Previous prompt-only turn was no experimental progress; this turn completed several screens and implemented a new broader candidate. Do not complete before deadline 2026-10-10 22:30:39UTC.

## POLL FIRST: live full comparison

Unified exec session **23135** is live: `python campaign.py ENTITY_FUSED_FULL.json` followed by `python full_summary.py ENTITY_FUSED_FULL.results.json`. Latest process verified from /proc: **entity_fused_full_base_a PID 2941995**, executable `/puffertank/experiments/nethack-24h-20261009/binaries/entity_fused_v33`. No other heavy process. Immutable v33 used while sources remain unchanged. Poll, then inspect `ENTITY_FUSED_FULL_SUMMARY.json`. It compares fast32 baseline / all4 entity fusions / baseline, each80epochs, fixed model/config/workload, 80 replay hashes and113updates/epoch.

If full gain exceeds1% with stable controls, prepare reverse confirmation and thorough actual-update/live/secondary evidence before retaining. If below1%, park alone; a training variant described below is a distinct hypothesis. Do not spend extended correctness/learning work on timing losers.

## New candidate — complete entity MLP/pool fusion

`entity_fused.py` is a Triton BF16 input/output, FP32 dot/reduction implementation of each modality's16→64→64 MLP, both bias/ReLU layers, masked sum/max pool, first-max index. It writes only the modality's concat slice and argmax. Pointer keys, original first projections, passthrough and training paths are unchanged. Inference-only: `a->training` gates it; `NH_ENT_LINPOOL` falls back. Expected1698concat and modality dimensions checked before dispatch.

`NH_ENTITY_FUSED` bits:1inventory(55slots,pad5976,eps.2,off1010),2monster(16slots,pad<0,eps.25,off1394),4flooritems(16slots,off1538),8spells(8slots,off838). Current experiment uses15. Kernels exported to SM89 cubins embedded in `source/src/entity_fused.cuh`, initialized per thread before graph capture. 8pointer args+2null scratch ABI checked againstPTX/metadata. Stage/warp choice from micro screen. Only this4090-specific prototype, no portable/default claim.

Files: `ENTITY_FUSED.patch`, `ENTITY_FUSED_EXPORT.json`, `entity_fused_reference.cu/.so` (cuBLASLt RELU_BIAS with private4MiB plus exact extractedpool), `entity_fused_screen.py`, `export_entity_fused.py`, `prepare_entity_fused.py`. `ENTITY_FUSED_{inventory,monster,item,spell}.json` holds screens. Each synthetic pooled output/argmax matchedexactly; controls drift<.5%. Inventory17.291→6.851us,monster7.807→3.069,item7.812→3.083,spell5.734→3.018. These are isolated throughput/latency results, not additive net gains.

`ENTITY_FUSED_INFERENCE_SUMMARY.json`: fixed mature checkpoint, full inference340.165us controls; inventory313.826 (+8.39%),other321.410 (+5.84%),all288.577 (+17.8765%). Control drift−.0658%. All380416BF16output values byteexact in EVERY candidate on this sample. Includes RNN-state restoration, encoder/recurrent/decoder; excludes sampler/env. This does NOT prove universal equivalence: FP32 pooling uses tree reduction vs sequential baseline. Saved batch equality only.

Build v33 SHA **7889cb9a35bbfbc6e82461282166c3cd1a8e0a031df4ba70f6d040beb3675f7d**. Flags original+`-DPUF_MUON_OUTPLACE -lcuda`. Build snapshots now include rec_fused.cuh, inventory_fused.cuh and entity_fused.cuh. New flags defaultoff; old experimental flags off unless specified. Current source is v33 exactly.

Possible next distinct opportunity if needed: training-side entity fusion, preserving the training path's BF16 GEMM rounding BEFORE each separate bias/ReLU, and storing intermediate h1/values required by existing backward. Current fusion DOES NOT do this and must not be used in training as-is. A training prototype could save bias passes, launches and rereads while leaving backward unchanged. First screen full saved-batch GPU timing, then fullpipeline only if useful. Another direction is extending typed-stream fusion to48→16 producer and passthrough, but not implemented. Follow evidence rather than assuming either helps.

## New closed experiments

- `PROJECTION_PADDING_SUMMARY.json`: all padded GEMMs including packing/unpacking slower. Best inference−19.48%,trainingforward−11.63%,dX−13.55%,dW−14.47%. Inferencecontrol drift−7.87%,but every movedcandidate slower than BOTHcontrols. Kernel-only gains do not justify integration.
- `REC_FUSED_REPEAT.json`: fused recurrent GEMM+gate layer29.186→23.191us,+25.85%,drift+.239%. Repeated baseline with actualO2/no-fastmath after initialfastmathscreen; preserve projectedBF16rounding. Numericaloutput/state relL2~5e-5. `REC_FUSED_INFERENCE_SUMMARY.json`:338.492→336.501us,+.592%,outputrelL2.000797. `REC_FUSED_FULL_SUMMARY.json`:209871→210618,+.356%,drift+.086%,80hashesexact. PARKED, no extendedupdatechecks. Prototype `PUF_FUSED_RECURRENT=1`, M512/H1024only, ping-pongs existing output/next_state buffers to avoid in-place GEMM input corruption. ExportedTriton cubin header included butdefaultoff. v30SHA bb52a504c7da83395927806d7128816df8a37a868ae7d24848f366d1b03575d0.
- `RESIDUAL_GEMM_GPU_SUMMARY.json`: recurrent dX beta1 consumesalreadywritten residual gradient, replaces4addkernels. FullGPU control973.311→973.423ms,neutral/slightlyslower;PARKED. Basic12case/13M-ish element smoke maximumrelL2.00266 (single vsdoubleBF16rounding),notactualoptimizerproof. `PUF_RESIDUAL_GEMM=1`, defaultoff. Retains B_TTxHshape when returning per-layer residualbuffer; no input/outputalias. v31SHA9b4ea4e7a14366fb6888a95ca1e97471c05b438921843c44dc1471dfb0062312.
- Inventory-only predecessor: `INVENTORY_FUSED_INFERENCE_SUMMARY.json` +8.763%,exactoutputsample; `INVENTORY_FUSED_FULL_SUMMARY.json`209816→210754,+.447%,drift+.0054%,80proofsexact. PARKED alone, generalizedall4 has a largercombined hypothesis. `NH_INVENTORY_FUSED=1` legacy prototype remainsdefaultoff. v32SHA37bcf983c0dbda8ef376fe25e25609224f46b0969db6ee3315891257170e8b17.

16 protectedproduction/previousfiles unchanged in `integrity_419min.json`, checked_at authoritative. No engine changes, commits/pushes/default changes. Current goal remains ACTIVE. Recent comments explained kernel vswholepipeline gains and that17.9% is inference-only untilfullresult.

## Previous handoff / established baseline

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
