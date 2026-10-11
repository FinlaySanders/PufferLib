# New compatibility findings

1. The saved out-of-place Muon/cuBLASLt implementation does not preserve current 4 MiB/default-math update bits. Removing only PUF_MUON_OUTPLACE restores exact master/momentum/update equality after 1,808 updates. It is excluded.

2. The mature frozen-policy test using 4B s705, seed 901, epsilon zero and 512 environments repeats deterministically within each build, but engine61 differs from the current engine at the epoch-16 observation boundary. Epochs 0–15 match. `isolate_engine` (baseline trainer + engine61) reproduces the same difference; `isolate_gpu` (retained GPU flags + current engine) matches the baseline through epoch 22. Main queued measurements are paused at the scheduler while earlier engine snapshots are checked. Existing engine61 timings are provisional, not a validated behaviour-preserving speedup.

See per-run command.json, result.json and run.log for exact binaries, engine hashes, frozen-weight proofs and observation hashes. No live source was changed.
