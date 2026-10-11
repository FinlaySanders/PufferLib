# Further overlap experiments

Baseline is four-stream Muon plus the existing gradient pipeline, on 32 CUDA
connections. The preceding full-pipeline result was 193.4k SPS; rollouts now
finish after PPO in mature games. Production sources stay untouched.

Candidates:

1. Prioritize GPU inference streams so CPU simulation gets its next actions sooner.
2. Copy inference outputs into rollout storage on a separate stream, while actions
   are returned to the CPU and simulation advances. Before reusing the one-step
   staging buffers, inference must wait for their archive copy. Drain copies at
   the horizon boundary before exposing the batch to training.
3. Overlap the next minibatch's encoder forward with the previous optimizer's
   remaining matrix updates. Keep global clipping/Nesterov/normalization intact.
   Update and cast all encoder weights first, then start the encoder. Join all
   remaining matrix updates and apply/cast their weights before the next recurrent
   and decoder forward. Every minibatch still uses the same fully updated weights.
   A fenced control performs the same split update without overlapping the work.

Checks before throughput claims:

- Match the saved-batch reference exactly after 113 real updates, including first
  and last raw gradients, momentum, parameter updates, FP32/BF16 weights; finite values.
- Match 16 updating batches (1,808 updates), including final checkpoint, optimizer,
  all recorded-action observations, actions, values, log probabilities, rewards,
  terminals, masks and recurrent-state hashes.
- GPU-only A/B/B/A-style interleaving for optimizer/forward changes, using the same
  saved mature batch, two warmups and ten measurements per process.
- Full-pipeline screens for passing collection candidates, then repeat promising
  variants with returning controls. Measure batches 64–94 after the same prefix.
- Only combine candidates that show a repeatable benefit individually.

Workload is unchanged: 15.55M score model, 2,048 environments, horizon 128,
minibatch 4,096, 113 PPO updates per rollout, 24 CPU pool workers and 4 submitters.
Simulation follows recorded actions. For throughput the model stays frozen while
optimizer work writes scratch weights; correctness tests apply real updates.
