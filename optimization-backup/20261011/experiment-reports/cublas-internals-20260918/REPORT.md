# cuBLAS internal trace: why upstream NetHack and Craftax diverge

Baseline: upstream 5.0 6ffa5b10, RTX 4090, BF16, seed 901. Diagnostics live here; the production working diff is unchanged.

## Directly observed mechanism

Upstream assigns a private workspace during handle initialization but then calls cublasSetStream before each GEMM. This resets the workspace to cuBLAS's default pool. During concurrent CUDA graph capture, some calls get workspace-dependent split-K algorithms, while later calls get zero-workspace algorithms. The capture scheduling order varies between buffers, so the fallback affects different timesteps across runs. Captured graphs retain those different arithmetic paths.

This is now observed in captured kernel nodes and cuBLASLt's own logs, rather than inferred solely from repeatability controls.

## NetHack: byte-for-byte proof

At timestep 372, buffer 2 in the samples pair, the first differing operation is GEMM #6, the character-statistics encoder projection (bl_feats @ bl_w.T):

- A: 128 x 134 BF16, byte-identical across runs.
- B: 64 x 134 BF16, byte-identical across runs.
- C: 128 x 64 BF16, 3,323 of 8,192 outputs differ; maximum absolute difference 0.001953125.
- Earlier GEMM input/output digests match. Later operations inherit the difference.

The split-K capture uses cutlass_80_wmma_tensorop_bf16_s161616gemm_bf16_32x32_64x1_tn_align2 plus cublasLt::splitKreduce_kernel. The alternative uses cutlass_80_wmma_tensorop_bf16_s161616gemm_bf16_16x16_128x1_tn_align2 without the extra reduction.

cuBLASLt logger explicitly reports these alternatives for the same shape:

| Path | Algorithm configuration | Workspace |
|---|---|---:|
| Split-K | algoId=23; tile 32x32; stages 64x1; REDUCTION_SCHEME_OUTPUT_TYPE; numSplitsK=8 | 98,304 bytes |
| Non-split | algoId=23; tile 16x16; stages 128x1 | 0 bytes, null pointer |

The configured split count and actual launch-grid z are not identical: this shape launches six nonempty K partitions. The output-type reduction and changed accumulation grouping explain different BF16 rounding.

### Standalone reproduction

repro.cu takes the actual saved A/B matrices and calls one captured cublasGemmEx, with CUBLAS_DEFAULT_MATH and identical dimensions/transposes/alpha/beta.

- Explicit zero workspace reproduces samples run 1's C byte-for-byte.
- Explicit 4 MiB workspace reproduces samples run 0's C byte-for-byte.
- Both produce the exact corresponding kernel names seen inside training.

This reproduction contains no game engine, PPO, action RNG or recurrent state.

Commands (from this directory):

    nvcc repro.cu -lcublas -lcuda -o repro
    ./repro 0 repro-zero.bin
    ./repro 4194304 repro-4m.bin

A.bin/B.bin hold raw BF16 bit patterns. first-gemm-0.npz and first-gemm-1.npz retain both complete input/output samples.

### Capture capacity and horizon

Across six instrumented upstream first-rollout traces, exactly 1,505 of 2,048 step graphs captured the four workspace-dependent split-K operations; 543 captured their zero-workspace alternatives. The transition falls around timestep 360–397 depending on buffer scheduling. In the logged capture, the target GEMM likewise has 1,505 nonzero-workspace calls and 543 zero-workspace calls.

A separate memory trace still showed over 12 GiB free at transition: this is not ordinary physical GPU memory exhaustion. The precise internal default-pool/graph resource policy causing the cutoff has not been identified. The count is an observation for this setup, not a general cuBLAS limit.

This explains why shorter captures can avoid the problem, but does not establish the historical horizon*num_buffers>total_agents expression as a cuBLAS rule or an indexing bug.

### Workspace restoration control

Changing only the GEMM wrapper to restore its private workspace after cublasSetStream (4 MiB supplied) gives all 2,048 graphs the split-K path. Both repeats have identical GEMM digests, complete sampled matrices, values, log probabilities, actions, rewards and terminals. This CPU-only diagnostic is distinct from the production per-stream-handle implementation, whose full training repeatability was checked separately.

## Craftax

Preserved training captures show the same split-K/non-split selection difference. Initial rollout and first update match; divergence begins in the prefetched second rollout, while the next training checkpoint consequently differs.

The first differing GEMM in the hash pair is step 376 (second rollout step 120), buffer 0, GEMM #0: the encoder projection, M=512, N=1024, K=1635. Both input tensors have identical dual 64-bit integer digests; output digests differ. This is checksum evidence, not a full-matrix byte comparison like NetHack.

Graph records show the encoder kernel changing from cutlass_75_tensorop_bf16_s1688gemm_bf16_64x128_tn_align1 with grid z=4 plus splitKreduce_kernel to the same main kernel with grid z=1 and no reduction. The decoder also changes between split-K and non-split variants. Learner graph kernel-name/grid signatures match across the traced repeats.

Earlier graph-only Craftax attempts allowed final evaluation to overwrite the training graph log files. Those files are excluded from the internal-kernel conclusion. craftax-capture-* and craftax-hash-* stop after the fourth training checkpoint and preserve the relevant graph slots 0–511.

## Files

- matrix-proof.json, craftax-digest-proof.json: first-divergence evidence.
- samples-*/: full NetHack matrices, GEMM digests and graph metadata.
- driver-*/, hash-*/: independent traces reproducing algorithm divergence.
- private-*/: workspace-restoration control.
- craftax-capture-*/, craftax-hash-*/: Craftax training graphs and intermediate rollout evidence.
- workspace-log-excerpt.txt: compact cuBLASLt log excerpt; lt-full.log: full 73 MB trace.
- repro.cu and repro-*.log/bin: standalone exact-output reproduction.
- setup.py and subsequent *_setup.py / *_run.py scripts: scratch instrumentation transformations.

Initial runtime-only graph queries could not identify driver-created cuBLAS kernels. Conclusions use the corrected CUDA driver API (cuGraphKernelNodeGetParams and cuFuncGetName), with checked return codes.

No changes were made to the live branch. No broad claim of determinism across other devices/toolkits/configurations is implied.


## Follow-up: allocation failure isolated

See ../cublas-pool-rule-20260918/REPORT.md. CUPTI confirms error 2 from CUDA async allocation at the fallback threshold. A bare CUDA reproducer isolates a finite graph virtual-address reservation budget: 1505 retained 32 MiB slots, 752 for 64 MiB, 376 for 128 MiB. This supersedes explanations based only on generic pool contention. Physical VRAM remains available. Exact internal driver budget policy is not established.

Exact driver budget now traced: see follow-up in ../cublas-pool-rule-20260918/REPORT.md. On this device/driver, budget is twice CUDA total device memory, rounded to 32 MiB. Debugger overrides move bare CUDA failure to exactly 64 or 4096 allocations; increasing it removes cuBLAS fallback in 2500 captures.
