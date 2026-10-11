# NetHack environment/minibatch sweep

Full training computation with fixed policy parameters, on RTX 4090 (24 GiB). Widths 224 and 512, four recurrent layers: 1,981,736 and 5,097,608 parameters. Environment counts 512, 1024, 2048, 4096; learner minibatches 4096, 16384, 32768. Horizon 512, replay ratio 1.78021395, four rollout buffers, 24 environment pool workers, asynchronous two-slot training. Engine61, pool83, cuBLAS workspace fix and head sampler retained.

Recorded actions from mature s705 games replace host actions after policy inference. Each of four buffers repeats its original 128-game cohort at higher environment counts. This holds age and composition fixed; larger counts are repeated trajectories, not independent games. Full inference, PPO forward/backward and optimizer computation execute. Optimizer updates scratch parameters; main network parameters stay fixed. This is a synthetic throughput benchmark, not an on-policy learning experiment or evidence of learning quality.

Before GPU timing, replay 12,288 decisions per game on CPU. Run 16 full-pipeline epochs, measuring epochs 8–13; the final epoch is excluded because it has no next rollout. Compare observation hashes at epochs 7, 13, 15 to corresponding recorded-teacher epochs 31, 37, 39. Assert each repeated cohort has identical observations. Require final checkpoint hash to equal initial checkpoint hash.

Completion tails use host timestamps of train_impl returning and the last rollout worker finishing. They distinguish which branch finishes last but are not GPU-kernel timing breakdowns. Device memory is queried each epoch and includes CUDA context and graph allocations; it is not an instrumented transient peak. Failed allocations are reported as failures without throughput.

Increasing minibatch size reduces optimizer updates per batch (integer floor of replay_ratio * rollout_batch / minibatch), so speed comparisons do not imply an equivalent learning recipe. No production source changes.

## Large-batch transpose fix in isolated harness

The first 1,024-environment attempts failed during CUDA graph capture. Inspection found signed 32-bit overflow in both the observation transpose launch element count and kernel indexing once T * B * observation_size exceeds INT_MAX. The benchmark now dispatches a 64-bit-indexed observation transpose only above that threshold; the 512-environment path is unchanged. A GPU test checked all 2,411,724,800 output elements against their expected source pattern with zero errors. Original failed attempts are retained under before-wide-*; their timings are excluded. This fix has not been applied to production.
