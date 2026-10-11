# Frozen nearby-entity probe

Compare baseline seed 2901 and the matched 1B policy trained without nearby-entity passthroughs. Freeze both policies; train only linear ridge and small MLP readouts. Decode the policy's own nearest-monster, nearest-floor-item and underfoot 16-dimensional summaries from the corresponding 128-dimensional sum/max pool. Also fit direct-summary readouts as ceiling controls.

Use a common saved observation corpus from score and depth policies. Hold out entire environment streams, using the same assignment across both policy families to avoid putting episodes from the same stream on opposite sides. Sample every eighth observation and suppress consecutive identical token lists. Fit only multi-entity scenes; underfoot reconstruction also requires an underfoot item. Save sample counts and max-pool routing statistics.

This is a first representational probe, using one matched training-seed pair and historical off-policy data. Activations are reconstructed in FP32 from frozen weights and checked against the actual C demo stream computation. The initial 64-state check matches within 3.6e-7; the full run checks another 256 states for each model. Native BF16 bitwise equality is not claimed. Strong decoding means the information is accessible, not that the policy causally uses it.

The detached `nethack-nearby-probe` scheduler waits for all five passthrough runs and evaluations to complete, their queue lock to be released, and an idle GPU. The probe then runs on two CPU threads, with CUDA disabled. The fresh baseline replication remains held separately for the speedup review.

Status: `STATUS.json`; logs: `scheduler.log`, `run.log`; outputs: `RESULTS.md`, `results.json`, `routing.json`, `corpus.json`, `validation.json`. `PLAN.json` pins the scripts. No production sources or running campaign artifacts are changed.
