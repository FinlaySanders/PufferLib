# Current NetHack cuBLAS benchmark

Upstream PufferLib 5.0 (6ffa5b10) versus candidate.patch, with CUBLAS_DEFAULT_MATH in both.

| Version | Aggregate training SPS | Repeat checkpoint equality |
|---|---:|---|
| Upstream | 110,615 | No |
| Current patch | 129,673 | Yes |

Measured throughput improvement: 17.23%. Candidate does not match upstream checkpoints. Upstream also fails its own repeat equality, so this experiment cannot attribute all numerical divergence to the patch or establish a unique upstream reference trajectory. All runs exit successfully and all saved weights are finite.

Protocol: RTX 4090, serial upstream/candidate/candidate/upstream, seed 901, 8,388,608 training steps per run, default NetHack config (15,552,136 parameters, 512 agents, 32 threads). All start from resources/nethack/fixwt4b_s705.bin; saved initial weights verified byte-identical. Normal gradients and updates are applied. Time updates 16–30: 3,932,160 steps per run, excluding startup, evaluation, checkpoint saving and first-half warmup. This repeats the earlier short resumed-training protocol; it is not a frozen-policy late-game benchmark. Different learned trajectories can alter simulator workload, so the number is an observed whole-training improvement, not an isolated kernel speedup.

Both variants use the same engine library from /puffertank/experiments/nethack-perf-20260917/variants/candidate14-lto-local (SHA256 70fe544048cd5f9e159d98be3222f35536e508299228e88f61a3c10c968bc403), matching the earlier cuBLAS experiment. NH_ZT_MASK=0, NH_DISC_SWAP=0, OMP_NUM_THREADS=32. Thus “upstream” refers to the trainer source, with the engine held constant.

Full commands, hashes, and timings: results.json, summary.json, validate.py and per-run logs. Numerical differences: weight-comparison.json. Production working tree unchanged.
