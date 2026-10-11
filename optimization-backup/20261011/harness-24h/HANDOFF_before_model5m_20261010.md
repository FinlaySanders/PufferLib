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
