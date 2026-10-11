# NetHack throughput status

Updated 2026-10-10T10:22:03.971416+00:00. Requested original512 inference-priority, overlap-kernel, and ready-request batching tests COMPLETE. Original goal remains paused. No new optimization promoted.

Primary remains512 environments / horizon512 / fourbuffers /32workers /15.55Mmodel. Keep both entity fusions from entity512_20261010 (previous +3.07%) and high-priority independent inference. Fresh priority ABBA: high 228,613 SPS, normal 211,891 (-7.31%). Ready-request dispatcher: 222,981 SPS versus fresh independent 228,476 (-2.41%). No production defaults/source changed.

Matched profiled PPO kernels take about13% longer under overlap; inference kernels about2.5x, with only16us initial ready wait versus546us graph duration. Normal priority creates long intra-inference gaps and exposed rollout wait. Larger batches save35–56% isolated forward time but dispatcher overhead/lost concurrency makes this implementation slower overall; batch-size BF16 outputs also differ, so not a behavior-preserving candidate.

Read overlap512_20261010/REPORT.md, SUMMARY.json, ANALYSIS.json, KERNELS.csv and INTEGRITY.json. All64 replay observation proofs match; 19protectedfiles unchanged. GPU/profiler timing sums are not additive wall time. 2048remainssecondary; main pipeline remains GPU/overlap limited, not the earlier2048CPU-limited regime.

## Previous handoff

# NetHack throughput status

Updated 2026-10-10T09:52:53.898679+00:00. User-requested entity fusion comparison COMPLETE. Original goal remains paused. No jobs running.

Primary remains 512 environments / horizon 512 / four buffers / 32 workers / 15.55M model. Fresh two-repeats-per-arm results: current stack 221,217 SPS; inference fusion 222,594 (+0.62%); training-forward fusion 226,354 (+2.32%); both 228,005 (+3.07%, 0.821B steps/hour). PPO finishes last in all timed epochs. Both is a user-selected keeper in the isolated experiment; production defaults are unchanged.

Saved-batch 113 updates and combined 1,808-update pipeline comparisons match checked gradients, parameters, optimizer and rollout/recurrent state exactly. Full B=128 inference outputs exact. All 64 observation hashes in all eight timing runs match the original reference. Bounded tests, no learning-quality or universal numerical-equivalence claim. All protected production/reference files unchanged.

Read entity512_20261010/REPORT.md, SUMMARY.json, CHECK_SUMMARY.json and CANDIDATE.json. Primary runner/batch remain PRIMARY_BENCHMARK.json, run_primary.py and original_config_20261010/mature_1024.bin. 2048/H128 remains a secondary scaling test. The smaller 5.10M model previously measured 282,968 SPS separately; its learning quality is untested.

## Prior primary-configuration handoff

# NetHack optimization handoff — 2026-10-10T09:03:59.245530+00:00

## User correction: primary workload is ORIGINAL512/H512

The latest user explicitly clarified that2048environments was only a scalability test. Main optimization target is original512environments, horizon512, fourbuffers, batch262144, minibatch4096,32workers allowed,15.55Mmodel (1024wide/fourlayers). Use PRIMARY_BENCHMARK.json and run_primary.py/campaign_primary.py. 2048/H128 and5.10M models are secondary. This correction supersedes earlier benchmark-priority choices in the goal text and older reports.

Original24hgoal remains paused. This bounded benchmark correction is COMPLETE. No jobs queued or running; sessions72748(ABBA) and7875(profiles/capture/GPUtiming) terminalrc0. Production config already matchedoriginal512/H512, so no production configuration/source was changed. No new optimization promoted.

## Current primary results

Read original_config_20261010/REPORT.md.
- ABBA64epoch full runs, warm24, time24–62. Original512 unique recorded trajectories, withoutreplication. Full inference/PPO/optimizer compute, frozenactor/scratchupdates.32workers andexisting sleepingmainwait inbothsizes. Same latestengine/GPUflags.
- 15.55M:221684.3/221178.1SPS, mean221431.2 (.797Bsteps/hour). PPOphase1.181s; rolloutsready~182msBEFOREPPOcompletes. GPUtraining/overlap is the primarybottleneck HERE.
- 5.10M(width512/layers4):282689.7/283246.3SPS, mean282968.0 (1.019B/hour). +27.79%versuslarge. PPOphase641ms then282msrolloutwait. Smaller policy learningquality UNTESTED; randomfrozenweights onteacheractions.
- Graphtraces24–25: largePPOgraph1184.84ms,~95.55ms remainsafterlastcollector; small635.62ms plus379.82msremainingcollection. Profilersaddoverhead;exclude theirlauncherSPS. Largeinference .614ms allunderPPO; small.393msunderPPO/.180outside.
- Freshoriginal-sizedGPU-onlybatch saved original_config_20261010/mature_1024.bin. Five full113-update trials1031.986ms (~254019equivalentSPSifcollectionfree), below278ktarget. Use thisbatchforprimaryfastGPUscreens, notrootmature_batch.bin(whichis2048/H128).
- All64obsproofsforfourfullruns exact against historicalcomprehensive/replay_score_all_2 andacrosssizes. Frozenactorbytesunchanged. Profileprefix27/capture24 proofs match; finalprofileepoch repeats priorobsbecause no prefetch, expected.16protectedfilehashesunchanged.

## Configuration distinction

Prior2048/H128modelsize result209k→215k(+2.9%) andCPUdominance are validforTHATscalingworkload, notprimary. Differentgame-agewindowsalso preventassigningallcross-configSPSdifference solelytoenvcount. Primary uses restored historicalwarm24/measured24–62 window; scalingusedwarm64/measured64–78 atH128.

Exactcommands/hashes in runs/original512_*/command.json. ORIGINAL512.json and ORIGINAL512_TRACE.json recordcampaigns. Renamelabelsbeforerunning. run_primary.py defaults64epochs/start24 andprimarybatchshape;oldrun.py/run_model.pypreservedasscalingharnesses. Experimental CUDAsource remainsv36; immutableattribution_v37 binaryusedwithdiagnosticbypassesdisabled. No pushes,commits,PRs,defaultsorunrelatedfileschanged.

## Prior scaling handoff (historical, secondary)

# NetHack throughput status — 2026-10-10T08:51:13.238532+00:00

User-requested 5M model comparison COMPLETE. Original 24-hour goal remains paused. No benchmark, profiler, monitor, or training run remains active. Sessions 44211 (ABBA full timings) and 40161 (capture/GPU-only/profile) exited rc0. No production changes; working experimental source remains v36. The existing immutable attribution_v37 binary was used for both sizes with bypass flags OFF.

## Latest result: 5.10M versus 15.55M

Read model5m_20261010/REPORT.md. Width 512 versus 1024, four layers, same encoder internals, 2048env/4buffers/H128/batch262144/mb4096/113PPOupdates/32workers. Existing PUF_FINISH_SLEEP enabled identically in both arms. Small model frozen/random; large uses trained s705. Same mature recorded actions; full GPU training compute writes scratch weights.

- ABBA full results: large209010.9, small214717.0, small215159.7, large208739.3SPS. Means208875.1 versus214938.3: +2.903%. This is a model/configuration comparison, NOT a new implementation optimization.
- PPO host phase1.0777s→.5522s; exposed rollout tail .1728s→.6629s. Same workload still takes~1.22s/batch with smaller GPU work.
- Isolated GPU training5trials .513218s small versus .970953s prior large diagnostic.
- Small graph trace: PPOGPU .54989s; lastcollector tail~697.8ms, env/pool592.94ms(85.0%),GPUwait77.45ms(11.1%). Profile overhead separate; exclude profile launcher79.9kSPS (includes profilerstopoverhead).
- Inference .51088ms duringPPO versus .26079 outside,1.96x; earlierlarge .87665/.36990,2.37x. Thus contention falls butCPUremainslimiting.
- Small reaches~.774Bsteps/hour; does not hit1B/hour. Learning quality untested.
- All four80epoch full runs have exactly matching observation hashes and unchanged actorbytes. Capture64 and profilefirst67 hashesalso exact; finalprofileepoch67 hasno prefetch so repeats66, expected. Frozenrandominitialweights exactacross smallruns/capture/profile/GPUload.
- All16protectedproduction/historicalfilehashesunchanged: model5m_20261010/INTEGRITY.json.

Reproduce via MODEL5M.json / MODEL5M_DETAIL.json and campaign_model.py; isolated run_model.py adds width/batchfile options (runner.patch saved). Source, defaults, commits, branches unchanged. Do not rerun labels without changing them. No jobs queued. LIQUID_FULL_REPEAT.json remains unlaunched.

## Previous attribution handoff

# NetHack throughput status — 2026-10-10T07:32:07.554847+00:00

The existing original 24-hour goal is PAUSED according to get_goal. User explicitly requested a bounded profile and attribution experiment; that task is COMPLETE. Do not create a replacement goal. Original objective /root/.codex/attachments/45e8ae2b-9569-441d-b536-ceced1640e37/pasted-text-1.txt. Original deadline 2026-10-10 22:30:39 UTC.

## Running now

No benchmark or diagnostic monitor remains running; GPU compute-app list empty at finish. Sessions 35410(profile),41896(build),42503(main8runs),47688(monitor),69875(sleep3runs),10345(monitor),55175(GPUtiming) all terminal rc0. Old HANDOFF sessions81622 etc are stale. The previously prepared LIQUID_FULL_REPEAT.json has NOT been launched; user redirected to attribution.

## Result

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
