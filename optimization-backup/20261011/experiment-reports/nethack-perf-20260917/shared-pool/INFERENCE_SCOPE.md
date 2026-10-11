# Native inference equivalence scope

Candidate03 engine, fixed depth4B checkpoint, eight environments.

* One buffer: originalWS vs repairedsharedpool traces AND raw observation sidecars match byte-for-byte (proof-1.json).
* Four buffers, defaultCUDAgraphs: WS vs pool differs first at sampled action events. The unchangedWS binary repeated against itself also differs first at action events (four-buffer-ws-self-comparison.json). Observations/keys/rewards before those first events match. Exactnativefourbufferdefault gate therefore FAILS onbaseline too; it is not waived.
* Four buffers, base.cudagraphs=-1: twoWSrepeats andsharedpool match entire trace hashes (no-graphs-results.json). This diagnostic isolates graph-enabled path dependence but does not yet identify its precise cause. Do not call defaultCUDAgraphdeterminism fixed.
* Separate fixed-action replay checks engine observations, complete policy observations/masks, rewards and termination under eachscheduler. This distinguishes engine scheduling correctness from stochastic inference reproducibility.

The first pool runner stopped at the failedgate. It produced no pooltraining/performance evidence. Later corrected pthreadreplay and warmtrain are distinct experiments with the above limitation documented.
