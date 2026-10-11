# NetHack head-parallel action sampler

Implemented and tested in isolated score/depth source copies. Production trainer files are unchanged.

## Change

One 32-thread block handles each environment; one lane handles each action head. Lane0 generates exactly the original ordered sequence of Philox uniforms. Every head retains the original serial masked log-sum-exp, CDF and legal-action fallback. After all selections, lane0 accumulates used-head log-probabilities in the original order. The 21-head variant retains the separate identify log-probability component and unchanged post-step finishing logic.

This changes parallel execution only. It does not skip unused heads, change RNG consumption, approximate exponentials, reorder floating-point reductions, change masks, or alter PPO.

## Evidence

* `test.log`, `test-depth.log`: 728,448 bit-exact environment samples each, across batch sizes1,7,31,32,33,128,129,512,1024. Compare all head actions, environment actions, log-probabilities, values and full Philox states. Identify variant also compares both float32 log-probability components.
* Cases include ordinary/tied/extreme logits, single-legal-action and entirely masked heads, masked final categories, epsilon0/0.05/0.3/1, conditional-head maps enabled/disabled, and repeated draws from advancing states.
* `native/results.json`: the actual 4B score and depth policies produce identical complete trace and raw observation hashes with old/new samplers. Eight environments, four buffers, CUDA graphs disabled for this deterministic integration check; existing graph-enabled baseline nondeterminism is not claimed fixed.
* Synthetic CUDA-graph kernel ABA: score128 batch108.6us→9.22us (11.8x), identify128 batch114.6us→9.28us (12.3x). Batch512 gains16.0x/16.5x. These are isolated kernel measurements on synthetic inputs, not whole-training speedups.
* Loaded-policy baseline/candidate/baseline training: see `summary.json` and `training/results.json`. Both arms use the retained engine and work-stealing scheduler, same pretrained4B weights and original PPO/rewards, fresh optimizer. Only sampler selection differs. Each arm verifies input weights, finite metrics and its final checkpoint. Report the measured latter half, with game ages and baseline drift.

## Whole-training result

| Workload | Baseline before | Head-parallel | Baseline after | Throughput change | Baseline drift |
|---|---:|---:|---:|---:|---:|
| Depth, 2,097,152 measured steps | 10.876 s | 10.773 s | 10.942 s | +1.26% | +0.61% |
| Score, 8,388,608 measured steps | 75.363 s | 75.495 s | 75.494 s | -0.09% | +0.17% |

These are the latter halves of4M depth /16M score runs, each loaded from its actual4B checkpoint. Score game ages average23,310 /24,420 /24,701 turns, so this is not a randomly initialised early-game test. The score training result is effectively unchanged. Depth shows a small gain; these are single ABA comparisons, not multi-seed statistical estimates. Existing graph-enabled sampling nondeterminism remains a limitation of exact workload matching in training.

The kernel optimisation is retained as an isolated, opt-in patch because it removes substantial sampling work while passing exact correctness checks. It is not claimed to accelerate score training in this asynchronous configuration. Faster inference can overlap PPO without shortening an epoch; further training acceleration should target the profiled small-grid GEMMs. Standalone evaluation throughput was not benchmarked here.

## Delivery

`patches/current.patch` is the21-head sampler change; `patches/score.patch` is its20-head version. They exclude the test-main harness. The current patch passes `git apply --check` against `/puffertank/pufferlib`, without applying it. Enable with `NVCC_EXTRA=-DPUF_HEAD_SAMPLER` in a NetHack build. Both compiled branches retain the original sampler as a reference/fallback; other environment builds are outside the scope of this optional define.

Tested binaries: `source/puffer_heads` (20-head score), `depth-source/puffer_heads` (21-head depth/current architecture). Their matching `puffer_baseline` binaries omit the sampler define. These experimental binaries also have the earlier isolated work-stealing, loading/timing and recording hooks; do not replace the production trainer wholesale with these source copies. Apply only the sampler patch when integrating.

No production edits, commits or pushes were performed. The standing restriction on editing production `src/pufferl.cu` remains in force.
