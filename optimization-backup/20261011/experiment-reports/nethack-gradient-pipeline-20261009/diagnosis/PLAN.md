# Diagnose gradient-pipeline regression

Keep the saved checkpoint, recorded game actions, engine, minibatch and all model arithmetic fixed. No edits to production sources.

1. Capture NVTX + CUDA graph/API/copy timelines of the pipelined case. Separate host work, GPU execution, and queue delays.
2. Reproduce without Nsight to exclude trace artifacts.
3. Change only CUDA_DEVICE_MAX_CONNECTIONS to 32 and compare identical unprofiled mature windows. Compare a baseline under the same setting; repeat any useful result.
4. Trace the altered setting and baseline as needed to localize the causal change. Use node tracing or lightweight per-collector timers if graph tracing leaves ambiguity.
5. Keep all windows, show profiling perturbation, and distinguish observed queuing from undocumented driver internals. Save report and raw traces; don't promote code based on a standalone speedup.

Observed so far: one inference graph queues for 420.960 ms then executes in 0.808 ms; a post-inference record_step kernel waits about 363 ms before its ~9 us execution. This establishes device-side queue delay rather than a slow environment step or a long inference kernel. Whether the queue limit is causal remains under test.
