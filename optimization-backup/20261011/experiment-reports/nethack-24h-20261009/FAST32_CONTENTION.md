# Collection contention on the faster GPU variant

The first full-pipeline screen favors higher inference priority: 210,022 versus 206,754 SPS (+1.58%). Fresh controls differ by 0.13%. This is an incremental result on the experimental GPU combination with 32 CPU workers, not a result for the retained clean baseline. Reverse-order confirmation measured +1.36% (209,884 versus207,069SPS; controls0.46%drift). Priority also preserves all live rollout, recurrent, optimizer and weight bits after2,097,152steps/904updates. Clean-stack applicability is being measured separately.

| Arm | SPS | Change | Exposed rollout tail |
|---|---:|---:|---:|
| Four Muon streams, normal inference priority | 206,754 | — | 188 ms |
| Higher inference priority | 210,022 | +1.58% | 162 ms |
| Two Muon streams | 206,697 | −0.03% | 142 ms |

Reducing the tail alone is insufficient: two Muon streams make PPO take longer, leaving total throughput flat and early-game throughput lower. That arm is parked. All 80 observation boundaries, frozen actor hashes and training work counts match in every arm. No model, environment count, horizon or minibatch change.

A fresh two-epoch node trace identified an opportunity: inference graph spans averaged 1.69 ms during PPO overlap versus 0.39 ms without it. Summed inference-kernel durations were 0.715 versus 0.378 ms. These phase groups are observational; tracing changes timing, and graph spans include scheduling gaps. They do not prove an exact causal decomposition. The unprofiled priority experiment supplies the intervention.

In the opening control and priority arm, per-buffer inference event time fell from 195.4 to 109.2 ms per horizon. Environment-stage wall time rose from 879.0 to 952.4 ms, while copy time stayed near 69 ms. Environment-stage time includes waiting for the shared CPU pool; this does not establish that individual game steps became more expensive. These durations overlap across buffers and are not additive pipeline wall-clock shares.

Source: FAST_INFER_PRIORITY.patch; immutable binary inference_priority_v22. Each actor stream reads back priority −5 versus the default0. CUDA runtime headers state that graphs instantiated without UseNodePriority use launch-stream priority; the current captures use flags0.

Artifacts: GPU_CONTENTION_FULL_SUMMARY.json; runs/fast32_profile_node/profile.json and contention.json; FAST32_PROFILE_PROOF.json; GPU_PRIORITY_SMOKE_SUMMARY.json. PRIORITY_CONFIRM.json and PRIORITY_LIVE.json define the pending gates.

Earlier bounded screens remain closed: buffer focus −0.22% full throughput despite +7.09% native; collector sleep +0.81%; collector plus main-thread finish sleep +0.23%. None clears the 1% full-pipeline continuation gate.

POOL_TIMING.patch is a prepared, unbuilt diagnostic to measure pool claim, tail and reader-drain wall/CPU time without Nsight. It must run with matched timing-disabled controls before its measurements support another scheduler experiment.

The corrected GPU combination itself is not bit-identical to the clean path: first-gradient relative L2 difference0.000970, final gradient0.434 after113updates, master weights0.000388 and BF16parameters0.000848. All recorded states are finite. These checks do not establish equal learning quality. SeeCORRECTED_COMBO_PROOF_SUMMARY.json.

Clean32-worker GPU path: priority203394SPS versus204213SPS controls (−0.401%,controldrift−0.114%). PriorityisconditionalonthefastGPUcombination,notageneraldefault. Detailedphaseanalysisusespost-traincounter65..79tomatchouter-loopSPSepochs64..78;olderderivedphasewindowwasoffbyone,SPSandallcorrectnessproofsareunaffected.
