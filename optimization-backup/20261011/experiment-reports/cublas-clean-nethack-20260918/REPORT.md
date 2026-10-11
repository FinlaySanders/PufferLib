# Clean-engine NetHack determinism recheck

Deferred optimizations excluded; original artifacts preserved (PRESERVED.md). No production edits, stash deletion, branch changes or pushes.

- Upstream trainer: upstream/5.0 at 6ffa5b10dbbbe4d1e8288367c7d9d3acd3bad4a2; built with no source instrumentation or checkpoint injection.
- Candidate: candidate.patch, only the cuBLAS changes.
- Engine: fresh Release build from clean fast-nle e7f6568568242745a7f7ebd8f730367123522cac; engine SHA256 7881e86e083b10c971d373c0351d56d7fa0df5f4bc3bba6743c32f61e77e8cc2. Both binaries link to this fresh build. No optimized LD_LIBRARY_PATH or old data-directory override. Fresh engine build/dat used.
- Normal random initialization; no pretrained checkpoint loaded. Default NetHack config, seed 901, 8,388,608 steps, 512 agents, 32 threads, RTX 4090.
- Serial upstream / candidate / candidate / upstream. All four runs exited 0, had finite saved FP32 weights, and no nonfinite loss logs.

| Comparison | Byte-identical final checkpoints |
|---|---|
| Upstream repeat | No |
| Candidate repeat | Yes |
| Upstream versus candidate | No |

The discrepancy persists without the deferred engine optimizations or checkpoint-loading harness. This does not isolate its cause: next investigation should locate the first divergent operation/state in two upstream runs. Repeatability of the candidate is not a proof of bitwise equivalence to upstream. Breakout and 2048 prior successful equivalence checks remain separate evidence.

Commands/hashes: validate.py and results.json. Summary: summary.json. Original working tree unchanged throughout.
