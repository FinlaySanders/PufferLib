# Three optimisation followups to parallel Muon

All tests are isolated. The baseline already includes four-stream Muon, gradient pipelining, 32 CUDA connections, the retained engine and shared worker pool. No production changes.

## Muon scheduling

Measured all 36 independent matrix updates using a saved genuine mature rollout. Timings use eight post-warmup samples per matrix on one stream; they are scheduling estimates, not additive costs under concurrent execution.

The original round-robin estimated loads were [1.4479359760000001, 1.120768008, 1.078783995, 1.0639359990000001] ms; longest-first greedy placement gives [1.1822080025000001, 1.1791360015000003, 1.164287981, 1.1857919929999998] ms. Despite that better estimated balance, the full GPU PPO graph gets slower:

| Schedule | GPU PPO graph ms | Throughput change | Exact after 113 updates |
|---|---:|---:|---|
| Round-robin control | 1149.771 | — | Yes |
| Cost-balanced, largest first | 1168.846 | -1.63% | Yes |

A second test keeps the original matrix submission order and changes only stream assignment. Its fresh-control results appear below. CUDA streams share GPU resources, so equal isolated-cost sums do not guarantee a faster concurrent schedule; these tests do not isolate the exact resource responsible.

## Rollout encoder table cache

Caches the effective glyph embedding and two inventory projection tables separately in each rollout buffer. The first inference of every horizon rebuilds them after the actor-weight snapshot; subsequent inferences reuse them. Training still rebuilds the tables every forward. First/subsequent reusable CUDA graphs preserve this distinction.

| Process | Full-pipeline SPS | Exposed rollout tail ms |
|---|---:|---:|
| full_baseline_0 | 193,105 | 91.352 |
| full_cache_0 | 193,434 | 88.734 |
| full_baseline_1 | 193,461 | 86.027 |

Cache gain is **+0.08%**, below the predeclared 1% continuation gate and within the control spread. No useful full-pipeline gain demonstrated; the cache was not retained. This is one candidate screen bracketed by two controls, not a formal confidence interval.

The cache and control match bit for bit after 1,808 live optimizer updates: master weights, momentum, updates, final checkpoint, all recorded environment observation hashes, and complete final rollout tensors including sampled actions, log probabilities, values, masks, rewards, terminal flags and recurrent states.

## Batched Muon GEMMs

The broad implementation groups equal-shaped matrices, uses pointer-array batched GEMMs with disjoint scratch, and retains global clipping, normalization and all five Newton–Schulz iterations. It failed exact matching. The first raw gradient matches the control, but the subsequent optimizer state and updates differ, so the implementation cannot qualify under the current exactness requirement.

Narrowed the test to small matrices, then tested each small shape individually:

| Grouping | Exact after 113 updates |
|---|---|
| All equal-shaped matrices | No |
| batched_small | No |
| batch_16x32 | Yes |
| batch_64x16 | No |
| batch_64x64 | No |
| batch_16x48 | Yes |

Only exact variants proceeded to timing. No speedup is claimed for a variant that changes update bits.

## Refined GPU screen

Fresh interleaved controls; two warmups and ten measured complete PPO graph executions per process. Each graph performs 113 optimizer updates from a restored saved batch.

| Variant | GPU graph ms by process | Throughput change |
|---|---:|---:|
| baseline | 1154.055, 1155.601 | +0.00% |
| balanced_order | 1162.558, 1163.704 | -0.71% |
| batch_16x32 | 1154.536, 1153.183 | +0.08% |
| batch_16x48 | 1152.897, 1152.807 | +0.17% |

## Scope and artifacts

RTX 4090; 15,552,136-parameter fixed 4B score model, 2,048 environments, horizon 128, minibatch 4,096, 113 optimizer updates per rollout, 24 pool workers plus four submitters. Mature environment actions follow four copies of 512 recorded streams. Full timing runs freeze the actor and send optimizer writes to scratch while executing the complete pipeline. They measure compute throughput, not learning or score.

Full-pipeline screens run 80 batches and time batches 64–78, after games reach the established mature workload. GPU-only timing measures the full PPO graph, not end-to-end SPS. Updating proofs are separate from frozen performance runs. Failed GPU screens do not progress to expensive full-pipeline timing.

The first per-matrix timing attempt used internal captured CUDA events, which cannot supply the requested elapsed times, and exited on an assertion. The corrected diagnostic uses external event nodes. Timing instrumentation is disabled in all headline benchmark runs; failed artifacts remain under v1_*.

PILOT.json, BENCH.json, REFINEMENTS.json and RESULTS.json preserve decisions and measurements; matrix_costs.json contains all cost samples. Per-run command manifests, binary hashes, logs, state hashes and GPU telemetry are in runs/. Sources, preparation scripts and patches are retained; source/puffer_initial preserves the initial benchmark binary before refinements. Protected production and previous experiment files are unchanged.
