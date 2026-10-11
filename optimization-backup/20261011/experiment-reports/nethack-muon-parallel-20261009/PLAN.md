# Parallel Muon after fixing CUDA work queue contention

Retest independent matrix orthogonalization on 1, 2, and 4 streams. Both sides
use CUDA_DEVICE_MAX_CONNECTIONS=32, NH_GRAD_PIPELINE=3, and the latest validated
engine/worker pool. This measures the incremental effect of parallel Muon.

The global gradient norm, clipping, Nesterov, batched matrix normalization,
five Newton–Schulz iterations, flat weight update and weight cast are unchanged.
Matrix operations fork after normalization and join before the weight update.
Side streams have private matrix scratch buffers and cuBLAS handles/workspaces.
The one-stream control adds no GPU event nodes. Parameter ordering and matrix
arithmetic remain unchanged. Scheduling is round-robin by matrix registration.

## Gates, decided before measuring

1. On the saved mature rollout, compare gradients, updates, momentum, FP32
   master weights, and BF16 parameters against the previously validated serial
   result, after 113 real updating minibatches. Check finite values.
2. Only passing variants proceed to an interleaved GPU graph screen:
   1, 2, 4, 4, 2, 1 streams; 2 warmups and 10 measured full PPO graphs/process.
3. A candidate needs at least 1% mean GPU speedup, with both candidate process
   averages faster than both controls. Only then run full-pipeline ABBA.
4. Full-pipeline runs use 96 batches, measuring the 31 batches 64–94; confirm
   identical recorded-action observation hashes and frozen actor checkpoint.
5. Confirm the winner with 16 live-updating batches (1,808 PPO updates), checking
   all batch observation hashes and final checkpoint/optimizer state exactly.

Performance uses the 15,552,136-parameter score checkpoint, 2,048 environments,
horizon 128, minibatch 4,096, and 113 PPO updates/batch. The engine follows saved
actions while inference and the full PPO pipeline execute. For timing, the actor
stays frozen and optimizer writes go to scratch. These are compute benchmarks,
not on-policy training runs or score evaluations.

All experimental changes are isolated under this directory. Production source,
previous experiment source, engine, checkpoint and saved rollout are unchanged.
Per-run command manifests, GPU telemetry and logs live in runs/.

## Run

prepare.py has already created the isolated source copy. Build flags are the
previous validated flags plus PUF_MUON_PARALLEL, without PUF_MUON_OUTPLACE.
Run python screen.py, then python confirm.py only if the GPU gate passes.
