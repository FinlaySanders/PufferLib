# NetHack training GEMM optimisation

## Retained candidate

**Restore the cuBLAS handle’s private workspace after setting its stream, and disallow reduced-precision reductions.** No architecture, optimiser formula, reward or hyperparameter changes. The patch is prepared but not applied to production.

On loaded 4B score-policy training, measured time falls from **35.36 s to 26.17 s**: **26.0% less time / 35.1% higher throughput**. Measured throughput is 111,214 → 150,253 steps/s. This is relative to the already optimised engine/work-stealing/head-sampler baseline, not the original pre-campaign trainer.

## End-to-end comparisons

Each arm runs 32 updates / 8,388,608 training steps from the same fixed 4B s705 checkpoint, with a fresh optimiser. Measure updates 16–30 (3,932,160 steps); exclude warmup and the last update, which does not prefetch another rollout. 512 environments, 32 CPU workers, normal async configuration. No profiler during these timings.

| Candidate | Measured seconds | Status |
|---|---:|---|
| baseline-a | 35.299 | Baseline before |
| workspace | 26.250 | Fast, but excessive actual-gradient error |
| split | 26.336 | FP32 partial split-K; no additional benefit over simpler fix |
| both | 26.210 | Combined; no additional benefit |
| baseline-b | 35.414 | Baseline after |
| strict | 25.846 | Retained candidate |
| lt | 27.120 | Large-operation Muon tuning; rejected on whole-training speed |
| workspace-d | 26.630 | Workspace-only later control |
| strict-repeat | 26.495 | Retained candidate repeat |

Baseline drift: 0.33%. Strict-candidate repeat drift: 2.51%. The loaded policy produces mature games: mean game age during the timed blocks is roughly 22,000–24,000 turns. This is a performance experiment, not a new score certificate or a guarantee of unchanged long-run learning.

## Root cause

The trainer allocates a 32 MiB workspace for each cuBLAS handle, but `cublasSetStream` unconditionally resets the handle to the default workspace pool. Every dense GEMM calls it. Restoring the already allocated private workspace after that call allows cuBLAS to use faster algorithms in the large captured training graph. Main and side-stream handles retain separate workspaces; inference workers use thread-local handles.

Official reference: [cuBLAS cublasSetWorkspace](https://docs.nvidia.com/cuda/cublas/index.html#cublassetworkspace).

## Numerical validation

- Explicit split-K: 9 representative shapes × 6 configurations, checked against an FP32 pedantic GEMM reference. Eight coordinates per shape additionally checked using CPU FP64 accumulation. Partial results and their deterministic final reduction use FP32; final output is BF16.
- Workspace-only passed random tests but failed the actual-training gradient gate: relative error 0.476% for one inventory gradient. It is not the retained candidate.
- Strict workspace and explicit FP32 split-K were checked on actual s705 training inputs for all seven distinct expensive gradient shapes. Both passed. Strict workspace relative errors range from about 0.12% to 0.19%, consistent with BF16 output rounding.
- The final gate requires relative L2 error below 0.3% and every element within `0.004*abs(reference) + 0.001*reference_RMS` of the FP32 reference. The original max-error/RMS test was inappropriate for sparse, heavy-tailed gradients; it was replaced with this BF16 rounding-aware elementwise bound while tightening the L2 requirement. The failing workspace-only configuration remains rejected.
- All full timing arms finished, loaded the checkpoint byte-for-byte, wrote final checkpoints, and passed finite-log checks. Graph-enabled timing uses normal training; the reference checker uses graph-disabled training (`--base.cudagraphs=-1`). In this tree zero still enables graphs, which caused an initial checker failure; that failed log is preserved.
- Different cuBLAS algorithms/reduction orders can change rounding. These changes are **not bitwise-equivalent training**. No long training/score-equivalence claim is made.

## Muon experiments

- Searched up to 64 cuBLASLt heuristic algorithms for each of 61 distinct Muon shapes, keeping BF16 tensors and FP32 computation.
- The initially selected small-matrix algorithms failed the complete five-step Newton–Schulz check on a structured input (29.1% relative output difference). Rejected; the tolerance was not relaxed.
- Restricting the candidate to the large 3072×1024 output GEMM passed 24 complete five-step tests (8 shapes × dense/sparse/structured inputs). The selected GEMM was about 8.5% faster in isolation, but its whole-training arm was slower than workspace-only controls. Rejected.
- Parameter batching was not implemented: the algorithm-selection experiment did not yield a retained end-to-end gain, and batching would require a separate optimiser-workspace refactor and numerical validation.

## Profile after the retained fix

A fresh warmed 10-second CUDA/NVTX trace reports a mean complete PPO graph span of **1.548 s**, versus **2.398 s** in the earlier detailed profile. The new capture contains 5 complete PPO graphs. GPU kernel-active union is 8.294/10 seconds; this is activity, not SM occupancy.
Gaps between PPO graphs (ms): 296.5, 335.0, 281.9, 341.1. See `profile-strict/summary.json` for inference overlap and kernel breakdown. Profile timings are not used for the throughput claim.

PPO no longer runs back-to-back: rollout completion now consumes a visible tail between updates. This identifies collection (simulation plus inference) as a new co-limiter; the CUDA-only trace does not separate CPU simulation from inference scheduling well enough to assign the entire tail to the engine.

## Artifacts

- `workspace-strict.patch`: minimal proposed patch, `git apply --check` passed; not applied.
- `training/*/result.json`: commands, per-update timing, game age and completion status.
- `strict_check.log`, `both_check2.log`: actual-gradient reference checks.
- `split.csv`, `workspace.csv`, `lt-bench.log`, `muon-check.log`: microbenchmarks and numerical tests.
- `muon-check-rejected.log`, `lt-config-rejected.bin`, `workspace_check-numeric-failure.log`: rejected candidates and evidence.
- `profile-strict/timeline.nsys-rep`, `timeline.sqlite`, `summary.json`: updated profile.
- `source/`: isolated builds; production git diff unchanged.
- `RESULTS.json`, `MANIFEST.json`: summary and checksums.
