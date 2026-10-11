# Three followups to parallel Muon

Baseline: validated four-stream Muon, gradient pipelining and 32 CUDA connections,
with the same mature 15.55M NetHack score policy, engine, shared pool and recorded
action corpus as the preceding experiment. No production edits.

1. Measure independent matrix-update costs on the saved real rollout. Greedily
   assign matrices, longest first, to the least-loaded stream. Arithmetic unchanged.
2. Cache the three weight-only encoder tables per rollout buffer. Refresh on the
   first decision of each horizon, after each actor weight snapshot. Training still
   recomputes them every forward. Preserve reusable first/subsequent-step graphs.
3. Group identical-shaped Muon matrices and use batched GEMMs with disjoint scratch.
   Preserve five Newton–Schulz steps and global clipping. Changed GEMM selection
   must pass exact updates before performance can qualify.

Correctness: saved 113-update comparison against the known exact baseline, then
1,808 live updates plus rollout/state checks for viable variants. Reject any
nonfinite or nonmatching candidate. GPU screen uses restored saved batches and
interleaved controls. Require >=1% repeatable GPU gain for optimizer variants.
Caching affects inference, so screen it directly in the frozen full pipeline.
Full screens: 80 batches, timing 64–78; compare fresh controls with unchanged
observation hashes and actor. Confirm >=1% gains with interleaved repeats.
Do not combine gains arithmetically; test any promising combination explicitly.
