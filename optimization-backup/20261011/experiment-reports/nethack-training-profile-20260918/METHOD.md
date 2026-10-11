# Fixed-policy full-training profile

Baseline: retained engine61 and original pool83, 24 shared workers plus4 submitters,512 games,4 buffers. Same policy architecture/PPO/config as retained benchmarks. Two starting policies: normal random initialization and fixed4B score checkpoint s705. Optimizer starts fresh in both.

Profiling-only code preserves forward, loss, backward, gradient clipping, optimizer momentum/Newton–Schulz/update and BF16 cast operations. Optimizer updates and cast outputs go to separate scratch parameter buffers. Forward/backward and actor-copy paths read unchanged policy weights. Scratch buffers initialize once outside measurement. This adds about93MB of parameter storage; no restore copy per minibatch. Full-run checkpoint hashes must equal saved initial weights. Late initial weights must also equal original s705 bytes.

Smoke proof: one million training steps in each condition, final and initial checkpoint SHA256 identical. These establish fixed policy weights, not a real resumed learning run. Hidden recurrent states and game states evolve normally.

Separate graph-level and node-level Nsight captures: graph capture gives lower-overhead CPU phase attribution; node capture measures individual GPU kernels but can inflate graph-launch costs. Record game-age markers inside traces. Captures use13s interior of15s traced windows. CPU ranges overlap across threads; GPU training and inference overlap. Interval unions/intersections are required; summed durations cannot be read as serial wall time. Graph envelopes include internal gaps and are not SM occupancy.

This answers workload bottlenecks for fixed early/mature behavior, avoiding policy degradation during profiling. It does not measure long-run learning or prove actual optimizer state was restored. Initial evolving-policy attempt and its failed required-checkpoint startup are preserved; neither is used for fixed-policy conclusions. Production checkout unchanged.
