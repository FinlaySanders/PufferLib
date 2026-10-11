# Active 24-hour NetHack throughput goal — updated 2026-10-10 01:34 UTC

Read the objective attachment before work:
`/root/.codex/attachments/45e8ae2b-9569-441d-b536-ceced1640e37/pasted-text-1.txt`
Copy: OBJECTIVE.txt. Start2026-10-09 22:30:39UTC, deadline2026-10-10 22:30:39UTC.
Goal remains ACTIVE; no new goal was created. The user asked for another goal prompt in an intervening turn; that was answered without clearing/replacing this goal. Latest explicit goal continuation resumed this objective.

## Running now

Unified exec **session8053**, `python worker_full_driver.py`, awaits/runs WORKER_FULL.json:
1. workers_full_base_a:24workers
2. workers28_full:28workers
3. workers32_full:32workers
4. workers_full_base_b:24workers

Immutable completion_workspace_v13 binary; blockingCUDAwaits,4buffers,2048games,horizon128,mb4096,113updates,80epochs with64–78mature timing. Driver checks all80observationboundaryproofs, unchangedfrozenactor, batch/update counts. Writes WORKER_FULL_SUMMARY.json. Poll8053 and verify ACTIVE.json PID through /proc/ps. Do not restart because a poll is quiet.

All preceding sessions are terminal:69702(buffer first screen),89245(fusedsmoke/build/GPU),62943(fusedfull),67743(bufferconfirmation),40492(nativeworkers).
No other heavy job queued after WORKER_FULL. Native screen is finished, not merely waiting. No builds/profiles/native timings during the current GPU campaign.

## Retained implementation winner

RETAINED.json unchanged v1: blockingCUDAhostwaits, clean6linepatch, +3.2479% full mature SPS (194195.55->200502.87), about0.722Bsteps/hour. Earlyneutral,depthroughlyneutral.113realupdates onmaturebatch and8livebatches/904updates/2097152steps match exactly. clean_wait/ and binaries/clean_wait contain source/patch/binary. Do not add configuration gains or isolatedGPU gains to this percentage.

## Completed this continuation

### Buffer configurations (replicated, separate from fixed headline configuration)
BUFFER_SUMMARY.json / BUFFER_CONFIRM_SUMMARY.json / CONFIG_CANDIDATES.json.
-8buffersx256, same2048games: +1.478%, repeat+1.210%.
-8buffers plus GPUcombo: +2.063%, repeat+2.047%, ~203.5kSPS.
-16buffers,4active,128stepcohorts: -8.05%;withcombo -7.51%. Reject.
-Controls drift+.203% firstscreen,-.318% repeat. All80proofs/actors match. No live/numericaltraining equivalence claim for changedinferencepartition.
-Combo flags: PUF_SCAN_ROW=3,PUF_SCAN_TILE=4,NH_EMBED_REDUCE=7,NH_IDENTITY_WARP=1,NH_FUSED_BR=1,PUF_OUTPLACE=1.
-Combo adds only~0.6–0.8% beyond8buffers; allFP32tree-reduction andoutplace rounding caveats persist. Not promoted to defaults.

### Fused small Muon (parked)
Prepared source via prepare_muon_fused_small.py (NON-IDEMPOTENT, already applied to isolated source/algo.cu).
Immutable binary muon_fused_v15 SHA62f558bba57693e56dc5ddcc220b82405dcf486287d4bcfe1428d6177bc4a874.
OneCTA/matrix, all5Newton-Schulz iterations in sharedmemory, BF16 intermediates, same coefficients/scaling. Runtime PUF_MUON_FUSED_SMALL=32 or64. Other matrices stillcuBLAS, globalnorm/clipping/Nesterov/flatweightupdate unchanged. Source isBF16-only experimental.
-Standalone muon_fused_smoke.py:66cases,58635values,22845differentBF16values,allfinite. WorstrelativeL2 .0459814 on63x7rank1stress; worstproductionshape .0164511 (64x16random). Broadsmokegate5%detects layout/scale; does NOT establish identicalupdates.
-GPU graph1156.05ms controls: <=32+0.649%,<=64+2.488% (1127.98ms).
-Fullpipeline<=64: controls199213.272SPS,candidate199369.968 (+0.0787%). Rollouttail42.38->69.08ms consumes almostall28.07msGPU savings. Peakreportedallocation8840.1->7872.1MiB (968MiBless).
-All80observations/actorsmatch,113updates maintained. Parkfor throughput; do NOT spendlongtrainingchecks on thisloser. No update-level equivalence claim.
-Artifacts MUON_FUSED_GPU_SUMMARY.json,MUON_FUSED_FULL_SUMMARY.json,muon_fused_smoke/.

### CPU worker count (native gain, full test now running)
WORKER_COUNT_SUMMARY.json.
Unpinned24worker controls221620.645SPS,drift+.3425%;20workers216281.585 (-2.409%),28workers226395.370 (+2.154%),32workers231013.145 (+4.238%). Two restored512decisiontrials/case,2048games; endpoints ccd51f25c735f59a,turns7221472,age27769.58 identical acrossallcases.
Added optional workers/pin arguments to native_pool/snapshot_test.py; defaults remain24/pinned. CLI --workers N --unpin. Existing pinnedmappingsupports<=24 only. No nativebinary/source changes were needed.
Hypothesis: blockingCUDAwaits changedCPUcompetition; additionalworkers mayhide latency/useSMT. Full pipeline mustconfirm, because nativeGPU-free result alone is insufficient.

## Next engine candidate prepared, NOT APPLIED

IMMUTABLE_OBJECT_READS.patch and .json:
Source baseline `/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/source`.
287directimmutablepropertyreads across56files redirected to `object_defaults` (=objects_baseline inlibrary,objects inutilities).
Selectedclass,weight,cost,damage,skills,armorvalues,flags,nutrition,delay,property. No directfieldassignmentwrites found in audit. Baselineper-gametable mixesimmutablemetadata withmutableappearance/discovery fields; sharedreads mayreduceprivateworking-set traffic andpermitliteral-indexconstantfolding.
Excludedoc_dir (WAN_NOTHING randomized!),oc_prob,material/color/toughness,indices/names/discoveries. Alias accesspaths andnestedindexbrackets unchanged. Whole-table initialization/save/restore stillneedruntimeinvariantchecks; sourceaudit is not proof.
Firstgenerator stopped onlegacy nonUTF8sourcebeforewriting; retryusedlosslessLatin1 patchbytes. No sourcecopy/edit/build/timing yet. Keeppatchbytesencodingwhenapplying.
Next: afterheavycampaign finishes, choosefullworkerfollowup ifuseful, then isolatedenginecopy/buildmatchedplainGCC/LTObaselineandcandidate; quickinvariant/replaysmoke; nativefirstpairgate; onlywinners meritPGO/fullcorpus/fulltraining. Existingfloor_boxes/ builderrecipe canbe reused. No unnecessaryrepeat ofoldPGO/compactlayoutnulls.

## Other closed candidates and constraints

STATUS.md and LEDGER.md contain old screens. Current-workloadPGO native+.377% parked; register-prefetchedscans slower; floorbbox+.249% parked; affinity/largerworkspaces/leadbatch/fairpriority/cohorts fixed4buffers null/slower. Sharedrow scan,embeddingreductions,outplaceMuon have isolatedGPU wins but littlefullthroughput; keep available for later fasterCPU stack, notretaineddefaults.
Protectproduction and prior experiment sources;16files unchanged inintegrity_184min.json. No pushes/PR/defaultchanges. StoponlyverifiedPIDs. Serialize heavywork. Roughlyminute commentary. Keep goalactive throughdeadline and preserve objective.

## Useful commands

`python campaign.py SPEC.json` (immutable unique runlabels).
`python run.py full LABEL --binary=... --epochs=80 --start=64 --env=PUF_CUDA_WAIT=block`
`python run.py time LABEL --binary=... --trials=4 --env=PUF_CUDA_WAIT=block`
`python build.py LABEL -DPUF_MUON_OUTPLACE` (onlyidle, snapshots/hashes).
`python native_pool/snapshot_test.py LABEL 2048 '0:512,0:512' --engine ENGINE/build --workers 28 --unpin`

Current full harness supports --buffers4/8/16 only; non4currentlyrestrictedtofrozenfullscore. Do not silentlyremoveguard forlivevalidation; firstauditmapping and document rounding/trajectory scope. Smoke4epochs terminalproof repeats previousboundary: compareequal-length4epochreference, not80epochlastboundary.
