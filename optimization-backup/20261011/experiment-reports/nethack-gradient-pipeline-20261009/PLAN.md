# Gradient pipelining experiment

Isolated copy of the current optimized trainer from the grouped-rollout study.
Keep standard four-buffer scheduling and all retained GPU flags. Use the latest
validated movement engine only as a common environment library. No production
source, retained artifact, branch or commit changes.

## Candidates

- 0: baseline; recurrent dW side stream unchanged.
- 1: three NetHack decoder dW products on the existing side stream.
- 2: sixteen encoder dW products whose source arrays remain valid until the
  existing arch_backward join.
- 3: both.

Four encoder products remain serial: projection (concat overwritten by dX),
local-input projection (x_local overwritten), monster token projection and
floor-item token projection (token arrays overwritten). Preserve original
arithmetic, independent output buffers, stream-owned cuBLAS workspaces and the
join before the global gradient norm/optimizer.

## Gates

1. Capture one full genuine mature rollout at epoch64: 2048 environments,
   horizon128, minibatch4096, 113 updates, 15.55M score checkpoint, standard
   settings. Save input actions/log-probabilities/masks/rewards/values/terminals,
   initial recurrent states, model parameters and optimizer momentum. This
   collection is one-time; 2048 streams duplicate the 512 recorded streams.
2. One complete updating graph from identical saved state for each mode.
   Exact comparisons of first/last raw gradients, final weights/master weights,
   optimizer momentum and update buffers; reject any non-finite output.
3. GPU-only full PPO graph screen: two warmups, ten measured graph replays per
   process, modes 0/1/2/3/3/2/1/0. Restore saved state outside each timed graph.
   Final timestamp follows the existing all-dW join and optimizer completion.
   This is a screening measurement without concurrent inference or CPU work,
   not an end-to-end SPS claim. Keep unchanged arithmetic and private workspaces.
4. Only candidates with repeatable >=1% graph speedup proceed to standard
   frozen full-pipeline ABBA tests with concurrent inference and simulation.
   Confirm with a live-update exact-state comparison before retention.

Record commands, input/binary hashes, clocks/power, all trials and failed gates.
No fresh engine golden/fuzz suite is needed: only neural scheduling changes.
